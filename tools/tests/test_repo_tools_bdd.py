"""BDD step definitions for tools/features/repo_tools.feature."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import pytest
from pytest_bdd import given, parsers, scenarios, then, when
from tools import gherkin_lint, policy

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
