"""BDD step definitions for tools/features/repo_tools.feature."""

from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path

import pytest
from pytest_bdd import given, parsers, scenarios, then, when
from tools import claim, gherkin_lint, policy

scenarios("../features/repo_tools.feature")


@dataclass
class RepoState:
    workspace: Path | None = None
    backlog_dir: Path | None = None
    lint_exit: int = -1
    linted_files: list[Path] = field(default_factory=list)
    problems: list[str] = field(default_factory=list)


@pytest.fixture
def state() -> RepoState:
    return RepoState()


@given("the live workloop repository workspace")
def given_live_workspace(state: RepoState, repo_root: Path) -> None:
    state.workspace = repo_root


@when("the Gherkin linter scans the workspace")
def when_gherkin_scans(state: RepoState) -> None:
    assert state.workspace is not None
    files, _findings = gherkin_lint.lint(state.workspace)
    state.linted_files = files
    state.lint_exit = gherkin_lint.main(["--root", str(state.workspace)])


@then("the Gherkin linter exits with code 0")
def then_gherkin_zero(state: RepoState) -> None:
    assert state.lint_exit == 0


@then("feature files from both crates and tools are linted")
def then_features_discovered(state: RepoState, repo_root: Path) -> None:
    rels = {p.relative_to(repo_root).as_posix() for p in state.linted_files}
    assert any(r.startswith("crates/workloop-core/features/") for r in rels)
    assert any(r.startswith("crates/workloop/features/") for r in rels)
    assert any(r.startswith("tools/features/") for r in rels)


def _write_backlog_fixture(base: Path, *, checked: bool) -> Path:
    backlog_dir = base / "backlog"
    (backlog_dir / "milestones").mkdir(parents=True)
    (backlog_dir / "tasks").mkdir(parents=True)
    (backlog_dir / "milestones" / "m-0.md").write_text(
        "---\nid: m-0\ntitle: Foundation\n---\n",
        encoding="utf-8",
    )
    box = "x" if checked else " "
    (backlog_dir / "tasks" / "wkl-001.md").write_text(
        f"---\nid: WKL-001\nstatus: Done\nmilestone: m-0\n---\n\n- [{box}] Criterion\n",
        encoding="utf-8",
    )
    return backlog_dir


@given("a temporary backlog directory containing a Done task with an unchecked criterion")
def given_unchecked_done(state: RepoState, tmp_path: Path) -> None:
    state.backlog_dir = _write_backlog_fixture(tmp_path, checked=False)


@given("a temporary backlog directory containing a Done task with all criteria checked")
def given_checked_done(state: RepoState, tmp_path: Path) -> None:
    state.backlog_dir = _write_backlog_fixture(tmp_path, checked=True)


@when("the backlog status guard validates that directory")
def when_backlog_validates(state: RepoState) -> None:
    assert state.backlog_dir is not None
    state.problems = policy.check_backlog_status(state.backlog_dir)


@then("the backlog status guard reports at least one problem")
def then_backlog_has_problem(state: RepoState) -> None:
    assert len(state.problems) >= 1


@then("the backlog status guard reports zero problems")
def then_backlog_clean(state: RepoState) -> None:
    assert state.problems == []


@when("the registry validator inspects the workspace")
def when_registry_live(state: RepoState) -> None:
    assert state.workspace is not None
    state.problems = policy.check_registry(state.workspace)


@then("the registry validator reports zero problems")
def then_registry_clean(state: RepoState) -> None:
    assert state.problems == []


@given(parsers.parse('a temporary registry where implement and review share family "{family}"'))
def given_same_family_registry(state: RepoState, tmp_path: Path, family: str) -> None:
    reg_dir = tmp_path / "registry"
    reg_dir.mkdir(parents=True)
    payload = {
        "schema_version": 1,
        "providers": {
            "p1": {"base_url": "https://a.example/v1", "quota_scope": "q1"},
            "p2": {"base_url": "https://b.example/v1", "quota_scope": "q2"},
        },
        "models": [
            {
                "id": "m1",
                "provider": "p1",
                "family": family,
                "context_window": 128000,
                "tool_calling": True,
            },
            {
                "id": "m2",
                "provider": "p2",
                "family": family,
                "context_window": 128000,
                "tool_calling": True,
            },
        ],
        "default_pools": {"implement": ["m1"], "review": ["m2"]},
    }
    (reg_dir / "free-models.json").write_text(json.dumps(payload), encoding="utf-8")
    state.workspace = tmp_path


@when("the registry validator inspects that temporary workspace")
def when_registry_temp(state: RepoState) -> None:
    assert state.workspace is not None
    state.problems = policy.check_registry(state.workspace)


@then("the registry validator reports a distinct-family violation")
def then_registry_family_violation(state: RepoState) -> None:
    assert any("distinct model families" in p for p in state.problems)


def _write_audit_fixture(base: Path, *, advisories: str, deny_ignore: str) -> None:
    base.mkdir(parents=True, exist_ok=True)
    (base / "deny.toml").write_text(f"[advisories]\nignore = [{deny_ignore}]\n", encoding="utf-8")
    (base / ".cargo").mkdir()
    (base / ".cargo" / "audit.toml").write_text(f"[advisories]\n{advisories}\n", encoding="utf-8")


@given('a temporary workspace whose audit config carries the unknown "yanked" key')
def given_audit_with_yanked_key(state: RepoState, tmp_path: Path) -> None:
    _write_audit_fixture(
        tmp_path,
        advisories='yanked = "deny"\nignore = ["RUSTSEC-0000-0001"]',
        deny_ignore='{ id = "RUSTSEC-0000-0001" }',
    )
    state.workspace = tmp_path


@given("a temporary workspace whose audit config matches deny.toml exactly")
def given_audit_matching_deny(state: RepoState, tmp_path: Path) -> None:
    _write_audit_fixture(
        tmp_path,
        advisories='ignore = ["RUSTSEC-0000-0001"]',
        deny_ignore='{ id = "RUSTSEC-0000-0001" }',
    )
    state.workspace = tmp_path


@when("the advisory exception guard validates that workspace")
def when_advisory_guard_runs(state: RepoState) -> None:
    assert state.workspace is not None
    state.problems = policy.check_advisory_exception(state.workspace)


@then("the advisory exception guard reports a parse error")
def then_advisory_parse_error(state: RepoState) -> None:
    assert any("cargo-audit rejects unknown" in problem for problem in state.problems)


@then("the advisory exception guard reports zero problems")
def then_advisory_clean(state: RepoState) -> None:
    assert state.problems == []


def _write_claimable_cards(base: Path, ids: list[str]) -> Path:
    backlog_dir = base / "backlog"
    tasks = backlog_dir / "tasks"
    tasks.mkdir(parents=True)
    for card_id in ids:
        (tasks / f"{card_id.lower()}.md").write_text(
            f"---\nid: {card_id}\ntitle: Card {card_id}\nstatus: To Do\n"
            f"milestone: m-1\n---\n\n## Description\n\nBody for {card_id}.\n",
            encoding="utf-8",
        )
    return backlog_dir


@given("a temporary backlog with two unclaimed task cards", target_fixture="state")
def given_two_unclaimed(tmp_path: Path) -> RepoState:
    state = RepoState()
    state.backlog_dir = _write_claimable_cards(tmp_path, ["WKL-101", "WKL-102"])
    return state


@when("two task claims run at the same time")
def when_two_claims(state: RepoState) -> None:
    assert state.backlog_dir is not None
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(claim.claim_next, state.backlog_dir) for _ in range(2)]
        claimed = [future.result() for future in futures]
    state.problems = [card_id for card_id in claimed if card_id is not None]


@then("the task claimer hands each loop a different card")
def then_distinct_cards(state: RepoState) -> None:
    assert len(state.problems) == 2, state.problems
    assert len(set(state.problems)) == 2, state.problems


@then("both claimed cards are marked In Progress")
def then_both_claimed(state: RepoState) -> None:
    assert state.backlog_dir is not None
    statuses = [
        line
        for card in sorted((state.backlog_dir / "tasks").glob("*.md"))
        for line in card.read_text(encoding="utf-8").splitlines()
        if line.startswith("status:")
    ]
    assert statuses == ["status: In Progress", "status: In Progress"]


@when("the documented-task guard inspects the workspace")
def when_documented_task_guard(state: RepoState, repo_root: Path) -> None:
    state.problems = policy.check_documented_commands(repo_root)


@then("the documented-task guard reports zero missing tasks")
def then_no_missing_tasks(state: RepoState) -> None:
    assert state.problems == []


@when("the distribution guard inspects the workspace")
def when_distribution_guard(state: RepoState, repo_root: Path) -> None:
    state.problems = policy.check_distribution(repo_root)


@when("the distribution guard inspects that temporary workspace")
def when_distribution_guard_temp(state: RepoState) -> None:
    assert state.workspace is not None
    state.problems = policy.check_distribution(state.workspace)


@then("the distribution guard reports zero problems")
def then_distribution_clean(state: RepoState) -> None:
    assert state.problems == []


def _write_release_fixture(base: Path, *, workflow: str, platforms: list[str]) -> Path:
    """Build the minimum tree `check_distribution` inspects."""
    (base / ".github" / "workflows").mkdir(parents=True)
    (base / ".github" / "workflows" / "release.yml").write_text(workflow, encoding="utf-8")
    listed = ", ".join(f'"{p}"' for p in platforms)
    (base / "pixi.toml").write_text(
        "\n".join(["[feature.packaging]", f"platforms = [{listed}]", ""]), encoding="utf-8"
    )
    recipe = base / "crates" / "workloop" / "recipe"
    recipe.mkdir(parents=True)
    (recipe / "variants.yaml").write_text(
        "\n".join(["c_stdlib_version:", "  - if: linux and x86_64", '    then: "2.17"', ""]),
        encoding="utf-8",
    )
    return base


BLESSED_WORKFLOW = "\n".join(
    [
        "jobs:",
        "  conda:",
        "    strategy:",
        "      matrix:",
        "        include:",
        "          - platform: linux-64",
        "            os: ubuntu-24.04",
        "",
    ]
)


@given(
    'a temporary workspace whose release workflow runs "cargo publish"',
    target_fixture="state",
)
def given_workflow_uses_cargo_publish(tmp_path: Path) -> RepoState:
    workflow = BLESSED_WORKFLOW + "      - run: cargo publish -p workloop\n"
    state = RepoState()
    state.workspace = _write_release_fixture(tmp_path, workflow=workflow, platforms=["linux-64"])
    return state


@given(
    'a temporary workspace whose packaging platforms include "win-64"',
    target_fixture="state",
)
def given_unsupported_packaging_platform(tmp_path: Path) -> RepoState:
    state = RepoState()
    state.workspace = _write_release_fixture(
        tmp_path, workflow=BLESSED_WORKFLOW, platforms=["linux-64", "win-64"]
    )
    return state


@then("the distribution guard reports a crates.io publication violation")
def then_crates_violation(state: RepoState) -> None:
    assert any("crate registry" in problem for problem in state.problems), state.problems


@then("the distribution guard reports a platform mismatch")
def then_platform_mismatch(state: RepoState) -> None:
    assert any("do not match the release matrix" in p for p in state.problems), state.problems


@given("a temporary workspace with one locked skill", target_fixture="state")
def given_locked_skill(tmp_path: Path) -> RepoState:
    skill = tmp_path / ".agents" / "skills" / "sample"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text(
        "\n".join(["---", "name: sample", "description: A sample skill.", "---", "", "Body."]),
        encoding="utf-8",
    )
    digest = policy.compute_skill_folder_hash(skill)
    lock = {"version": 1, "skills": {"sample": {"computedHash": digest}}}
    (tmp_path / "skills-lock.json").write_text(json.dumps(lock), encoding="utf-8")
    state = RepoState()
    state.workspace = tmp_path
    return state


@when("the skill folder is edited but skills-lock.json is not")
def when_skill_edited(state: RepoState) -> None:
    assert state.workspace is not None
    skill_md = state.workspace / ".agents" / "skills" / "sample" / "SKILL.md"
    skill_md.write_text(skill_md.read_text(encoding="utf-8") + "\nDrift.\n", encoding="utf-8")
    state.problems = policy.check_skills(state.workspace)


@then("the skills guard reports drift for that skill")
def then_drift_reported(state: RepoState) -> None:
    assert any("drifted from skills-lock.json" in p for p in state.problems), state.problems


@then("rehashing the lock clears the drift")
def then_rehash_clears(state: RepoState) -> None:
    assert state.workspace is not None
    assert policy.update_skill_hashes(state.workspace) == ["sample"]
    # The fixture declares no REQUIRED_LOCAL_SKILLS, so only drift may be reported.
    assert [p for p in policy.check_skills(state.workspace) if "drifted" in p] == []


TWO_PLATFORM_WORKFLOW = "\n".join(
    [
        "jobs:",
        "  conda:",
        "    strategy:",
        "      matrix:",
        "        include:",
        "          - platform: linux-64",
        "            os: ubuntu-24.04",
        "          - platform: osx-arm64",
        "            os: macos-14",
        "",
    ]
)


@given("a temporary workspace with no release workflow", target_fixture="state")
def given_no_release_workflow(tmp_path: Path) -> RepoState:
    state = RepoState()
    state.workspace = tmp_path
    return state


@then("the distribution guard reports the missing workflow")
def then_missing_workflow(state: RepoState) -> None:
    assert any("release.yml is missing" in p for p in state.problems), state.problems


@given(
    "a temporary workspace whose release matrix declares no platforms",
    target_fixture="state",
)
def given_empty_matrix(tmp_path: Path) -> RepoState:
    state = RepoState()
    state.workspace = _write_release_fixture(
        tmp_path, workflow="jobs:\n  conda:\n    runs-on: ubuntu-24.04\n", platforms=[]
    )
    return state


@then("the distribution guard reports an empty release matrix")
def then_empty_matrix(state: RepoState) -> None:
    assert any("no conda matrix platforms" in p for p in state.problems), state.problems


@given(
    parsers.parse('a temporary workspace whose recipe pins "{marker}" for a "{platform}" target'),
    target_fixture="state",
)
def given_recipe_pins_unbuilt(marker: str, platform: str, tmp_path: Path) -> RepoState:
    state = RepoState()
    state.workspace = _write_release_fixture(
        tmp_path, workflow=TWO_PLATFORM_WORKFLOW, platforms=["linux-64", "osx-arm64"]
    )
    variants = state.workspace / "crates" / "workloop" / "recipe" / "variants.yaml"
    variants.write_text(
        "\n".join(
            [
                "c_stdlib_version:",
                "  - if: linux and x86_64",
                '    then: "2.17"',
                f"  - if: {marker}",
                '    then: "11.0"',
                "",
            ]
        ),
        encoding="utf-8",
    )
    return state


@then(parsers.parse('the distribution guard reports a recipe mismatch for "{platform}"'))
def then_recipe_mismatch(platform: str, state: RepoState) -> None:
    assert any(platform in p or "win" in p for p in state.problems), state.problems


@given(
    "a temporary workspace whose recipe omits the variant pin for osx-arm64",
    target_fixture="state",
)
def given_missing_variant_pin(tmp_path: Path) -> RepoState:
    state = RepoState()
    state.workspace = _write_release_fixture(
        tmp_path, workflow=TWO_PLATFORM_WORKFLOW, platforms=["linux-64", "osx-arm64"]
    )
    return state


@then("the distribution guard reports a missing variant pin")
def then_missing_variant_pin(state: RepoState) -> None:
    assert any("no `c_stdlib_version` for osx-arm64" in p for p in state.problems), state.problems


@given("a temporary workspace with only a release workflow", target_fixture="state")
def given_only_workflow(tmp_path: Path) -> RepoState:
    (tmp_path / ".github" / "workflows").mkdir(parents=True)
    (tmp_path / ".github" / "workflows" / "release.yml").write_text(
        TWO_PLATFORM_WORKFLOW, encoding="utf-8"
    )
    state = RepoState()
    state.workspace = tmp_path
    return state
