"""Unit tests covering prose rendering, changelog formatting, policy checks, and doit tasks."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
from tools import changelog, claim, coverage_gate, dodo, gherkin_lint, policy, prose, versions
from tools.lib.github_actions import append_summary


def test_github_actions_summary_writes_when_env_set(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    summary_file = tmp_path / "summary.md"
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary_file))
    append_summary("## Gate Passed")
    assert "## Gate Passed" in summary_file.read_text(encoding="utf-8")


def test_github_actions_summary_noop_without_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)
    append_summary("## Ignored")


def test_prose_write_check_list_command_lint_and_sync(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "docs").mkdir()
    (tmp_path / "README.md").write_text("# Demo\n", encoding="utf-8")
    (tmp_path / "docs" / "guide.md").write_text("# Guide\n", encoding="utf-8")
    (tmp_path / "vale.toml").write_text(
        """
min_alert_level = "warning"
sources = ["README.md", "docs"]
packages = ["https://github.com/vale-cli/Microsoft/releases/download/v0.15.1/Microsoft.zip"]
accept = ["workloop", "clifacet"]
vocab = "Workloop"
based_on = ["Vale", "Workloop"]

[rules."Microsoft.We"]
level = "NO"
reason = "No first person."

[rules."Workloop.American"]
extends = "substitution"
level = "error"
message = "Use '%s' instead of '%s'."
ignorecase = true

[rules."Workloop.American".swap]
"behaviour" = "behavior"
""",
        encoding="utf-8",
    )
    assert prose.main(["check"], root=tmp_path) == 1
    assert prose.main(["write"], root=tmp_path) == 0
    assert prose.main(["check"], root=tmp_path) == 0
    assert prose.main(["list"], root=tmp_path) == 0
    assert prose.main(["list", "--format", "json"], root=tmp_path) == 0
    assert prose.main(["command"], root=tmp_path) == 0

    (tmp_path / ".vale.ini").write_text("# drifted\n", encoding="utf-8")
    assert prose.main(["check"], root=tmp_path) == 1
    assert prose.main(["write"], root=tmp_path) == 0

    def fake_run_ok(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        del args, kwargs
        return subprocess.CompletedProcess(["vale"], 0, stdout="{}", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run_ok)
    assert prose.main(["lint"], root=tmp_path) == 0
    assert prose.main(["sync"], root=tmp_path) == 0

    alert_json = json.dumps(
        {
            "README.md": [
                {
                    "Check": "Workloop.American",
                    "Line": 1,
                    "Span": [1, 9],
                    "Message": "Use 'behavior'.",
                }
            ]
        }
    )

    def fake_run_alert(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        del args, kwargs
        return subprocess.CompletedProcess(["vale"], 1, stdout=alert_json, stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run_alert)
    assert prose.main(["lint"], root=tmp_path) == 1
    assert prose.main(["sync"], root=tmp_path) == 1

    def fake_missing(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        del args, kwargs
        raise FileNotFoundError("vale")

    monkeypatch.setattr(subprocess, "run", fake_missing)
    assert prose.main(["lint"], root=tmp_path) == 1


def test_prose_invalid_config_errors(tmp_path: Path) -> None:
    assert prose.scalar(42) == "42"
    assert prose.main(["check"], root=tmp_path) == 1
    (tmp_path / "vale.toml").write_text("not = [valid", encoding="utf-8")
    assert prose.main(["check"], root=tmp_path) == 1

    (tmp_path / "vale.toml").write_text(
        """
min_alert_level = "warning"
sources = ["README.md"]
packages = ["https://example.com/pkg.zip"]
accept = ["workloop"]
vocab = "Workloop"
based_on = ["Vale"]

[rules."Microsoft.We"]
level = "NO"
""",
        encoding="utf-8",
    )
    assert prose.main(["check"], root=tmp_path) == 1


def test_changelog_regen_check_print_and_notes(tmp_path: Path) -> None:
    compare_url = "https://github.com/Archont561/workloop/compare/v0.0.0...v0.1.0"
    sample = (
        f"# Changelog\n\n## [0.1.0]({compare_url}) - 2026-11-10\n\n"
        "### Added\n\n* **cli:** scaffold workloop\n"
    )

    def fake_runner(argv: object) -> tuple[int, str]:
        del argv
        return 0, sample

    assert changelog.main(["check"], root=tmp_path, runner=fake_runner) == 1
    assert changelog.main(["regen"], root=tmp_path, runner=fake_runner) == 0
    assert changelog.main(["check"], root=tmp_path, runner=fake_runner) == 0
    assert changelog.main(["print"], root=tmp_path, runner=fake_runner) == 0
    assert (
        changelog.main(
            ["notes", "0.1.0", "--date", "2026-11-10"], root=tmp_path, runner=fake_runner
        )
        == 0
    )

    def failing_runner(argv: object) -> tuple[int, str]:
        del argv
        return 2, "boom"

    assert changelog.main(["regen"], root=tmp_path, runner=failing_runner) == 1


def test_coverage_gate_missing_and_empty_cases(tmp_path: Path) -> None:
    assert coverage_gate.main(["--root", str(tmp_path)]) == 1
    lcov = tmp_path / "coverage" / "lcov.info"
    lcov.parent.mkdir()
    lcov.write_text("TN:\nSF:other/file.rs\nDA:1,1\nend_of_record\n", encoding="utf-8")
    assert coverage_gate.main(["--root", str(tmp_path)]) == 1
    summary = coverage_gate.CoverageSummary(0, 0, {})
    assert summary.percent == 0.0


def test_versions_invalid_semver_rejected(tmp_path: Path) -> None:
    assert versions.main(["--set", "not-semver", "--root", str(tmp_path)]) == 1


def test_live_policy_checks_and_failure_branches(repo_root: Path, tmp_path: Path) -> None:
    assert policy.main(["all", "--root", str(repo_root)]) == 0
    assert policy.main(["skills", "--root", str(repo_root)]) == 0
    assert policy.main(["backlog", "--root", str(repo_root)]) == 0
    assert policy.main(["registry", "--root", str(repo_root)]) == 0
    assert policy.main(["packages", "--root", str(repo_root)]) == 0
    assert policy.main(["advisory", "--root", str(repo_root)]) == 0

    assert policy.check_skills(tmp_path) == ["missing skills-lock.json"]
    (tmp_path / "skills-lock.json").write_text(json.dumps({"skills": {}}), encoding="utf-8")
    assert policy.check_skills(tmp_path) == ["missing .agents/skills/ directory"]

    skill_dir = tmp_path / ".agents" / "skills" / "session"
    skill_dir.mkdir(parents=True)
    assert "skills-lock.json defines no locked skills" in policy.check_skills(tmp_path)

    (tmp_path / "skills-lock.json").write_text(
        json.dumps({"skills": {"audit": {"source": "x"}}}), encoding="utf-8"
    )
    (skill_dir / "SKILL.md").write_text("no frontmatter\n", encoding="utf-8")
    problems = policy.check_skills(tmp_path)
    assert any("missing required project-local skill" in p for p in problems)
    assert any("locked skill 'audit' missing" in p for p in problems)
    assert any("must declare `name` and `description`" in p for p in problems)
    assert len(policy.compute_skill_folder_hash(skill_dir)) == 64

    assert policy.check_backlog_status(tmp_path / "backlog")[0].startswith(
        "missing tasks directory"
    )
    (tmp_path / "backlog" / "tasks").mkdir(parents=True)
    assert policy.check_backlog_status(tmp_path / "backlog") == [
        "backlog/tasks/ contains zero task cards"
    ]
    (tmp_path / "backlog" / "milestones").mkdir(parents=True)
    (tmp_path / "backlog" / "milestones" / "m-0.md").write_text("---\nid: m-0\n---\n", "utf-8")
    (tmp_path / "backlog" / "tasks" / "bad.md").write_text(
        "---\nstatus: Bogus\nmilestone: m-99\n---\n", "utf-8"
    )
    b_problems = policy.check_backlog_status(tmp_path / "backlog")
    assert len(b_problems) == 2

    (tmp_path / "dodo.py").write_text("# forbidden\n", encoding="utf-8")
    assert policy.main(["repo", "--root", str(tmp_path)]) == 1


def test_gherkin_lint_detects_missing_and_invalid_feature(tmp_path: Path) -> None:
    assert gherkin_lint.main(["--root", str(tmp_path)]) == 1
    feat_dir = tmp_path / "features"
    feat_dir.mkdir()
    (feat_dir / "broken.feature").write_text(
        "Feature: Broken\n  Scenario: Missing steps\n    Given only given\n",
        encoding="utf-8",
    )
    assert gherkin_lint.main(["--root", str(tmp_path)]) == 1


def test_dodo_task_factories_expose_actions() -> None:
    assert dodo._exit_ok(0) is True
    assert dodo._exit_ok(1) is False
    task_funcs = [
        dodo.task_version_check,
        dodo.task_repo_check,
        dodo.task_skills_check,
        dodo.task_backlog_check,
        dodo.task_registry_check,
        dodo.task_check_packages,
        dodo.task_advisory_exception,
        dodo.task_lint_gherkin,
        dodo.task_prose_write,
        dodo.task_prose_sync,
        dodo.task_prose_check,
        dodo.task_lint_prose,
        dodo.task_check_coverage,
        dodo.task_changelog,
        dodo.task_changelog_check,
        dodo.task_check_policy,
    ]
    for factory in task_funcs:
        spec = factory()
        assert "actions" in spec


def _write_audit_workspace(root: Path, *, audit_advisories: str, deny_ignore: str) -> None:
    (root / "deny.toml").write_text(f"[advisories]\nignore = [{deny_ignore}]\n", encoding="utf-8")
    (root / ".cargo").mkdir()
    (root / ".cargo" / "audit.toml").write_text(
        f"[advisories]\n{audit_advisories}\n", encoding="utf-8"
    )


def test_advisory_guard_flags_drift_between_the_two_files(tmp_path: Path) -> None:
    _write_audit_workspace(
        tmp_path,
        audit_advisories='ignore = ["RUSTSEC-0000-0002"]',
        deny_ignore='{ id = "RUSTSEC-0000-0001" }',
    )

    problems = policy.check_advisory_exception(tmp_path)

    assert any("advisory ignore mismatch" in problem for problem in problems)
    assert policy.main(["advisory", "--root", str(tmp_path)]) == 1


def _card(base: Path, card_id: str, *, status: str = "To Do", body: str | None = None) -> Path:
    tasks = base / "backlog" / "tasks"
    tasks.mkdir(parents=True, exist_ok=True)
    path = tasks / f"{card_id.lower()}.md"
    path.write_text(
        body
        if body is not None
        else f"---\nid: {card_id}\nstatus: {status}\n---\n\n## Description\n\nBody.\n",
        encoding="utf-8",
    )
    return path


def test_claim_next_returns_none_when_every_card_is_taken(tmp_path: Path) -> None:
    _card(tmp_path, "WKL-201", status="In Progress")
    _card(tmp_path, "WKL-202", status="Done")

    assert claim.claim_next(tmp_path / "backlog") is None
    assert claim.main(["--backlog-dir", str(tmp_path / "backlog")]) == 1


def test_claim_next_missing_backlog_is_an_environment_error(tmp_path: Path) -> None:
    backlog_dir = tmp_path / "backlog"
    (backlog_dir / "tasks").parent.mkdir(parents=True)
    (backlog_dir / "tasks").write_text("not a directory\n", encoding="utf-8")

    assert claim.main(["--backlog-dir", str(backlog_dir)]) == 2


def test_claim_rejects_cards_without_frontmatter_or_id(tmp_path: Path) -> None:
    no_frontmatter = _card(tmp_path, "WKL-203", body="No frontmatter here.\n")
    assert claim.main(["--backlog-dir", str(tmp_path / "backlog")]) == 1
    with pytest.raises(claim.ClaimError, match="no frontmatter"):
        claim.claim(no_frontmatter)

    no_frontmatter.write_text("---\nstatus: To Do\n---\n\nBody.\n", encoding="utf-8")
    with pytest.raises(claim.ClaimError, match="no id"):
        claim.claim(no_frontmatter)


def test_claim_skips_cards_without_frontmatter(tmp_path: Path) -> None:
    _card(tmp_path, "WKL-204", body="Loose notes, no frontmatter.\n")
    _card(tmp_path, "WKL-205")

    backlog_dir = tmp_path / "backlog"
    assert claim.unclaimed_cards(backlog_dir) == [backlog_dir / "tasks" / "wkl-205.md"]
    assert claim.main(["--backlog-dir", str(backlog_dir)]) == 0


def test_claim_rewrites_only_the_status_line(tmp_path: Path) -> None:
    lines = ["---", "id: WKL-206", "title: Keep me", "status: To Do", "milestone: m-1", "---"]
    original = "\n".join([*lines, "", "## Body", "", "Text."]) + "\n"
    card = _card(tmp_path, "WKL-206", body=original)

    assert claim.claim(card) == "WKL-206"

    assert card.read_text(encoding="utf-8") == original.replace(
        "status: To Do", "status: In Progress"
    )
