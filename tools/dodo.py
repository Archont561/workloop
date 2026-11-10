"""Single `doit` task graph for `Archont561/workloop` (`doit.cfg` -> `tools/dodo.py`)."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import changelog, coverage_gate, gherkin_lint, policy, prose, versions  # noqa: E402

DOIT_CONFIG: dict[str, Any] = {
    "default_tasks": ["check_policy"],
    "verbosity": 2,
}


def _exit_ok(code: int) -> bool:
    return code == 0


def task_version_check() -> dict[str, Any]:
    """Verify synchronized SemVer across Cargo, Pixi, Conda recipe, and package.json."""
    return {
        "actions": [(lambda: _exit_ok(versions.main(["--check", "--root", str(ROOT)])))],
    }


def task_repo_check() -> dict[str, Any]:
    """Verify structural repository invariants (`CLAUDE.md`, `doit.cfg`, forbidden dirs)."""
    return {
        "actions": [(lambda: _exit_ok(policy.main(["repo", "--root", str(ROOT)])))],
    }


def task_skills_check() -> dict[str, Any]:
    """Validate `.agents/skills/` frontmatter and `skills-lock.json` alignment."""
    return {
        "actions": [(lambda: _exit_ok(policy.main(["skills", "--root", str(ROOT)])))],
    }


def task_backlog_check() -> dict[str, Any]:
    """Validate `backlog/` task statuses, milestones, and Done criteria."""
    return {
        "actions": [(lambda: _exit_ok(policy.main(["backlog", "--root", str(ROOT)])))],
    }


def task_registry_check() -> dict[str, Any]:
    """Validate `registry/free-models.json` schema and distinct-family pools."""
    return {
        "actions": [(lambda: _exit_ok(policy.main(["registry", "--root", str(ROOT)])))],
    }


def task_check_packages() -> dict[str, Any]:
    """Verify crate `package.include` lists exclude BDD features and tests."""
    return {
        "actions": [(lambda: _exit_ok(policy.main(["packages", "--root", str(ROOT)])))],
    }


def task_advisory_exception() -> dict[str, Any]:
    """Verify `deny.toml` and `.cargo/audit.toml` match and `rand` is non-runtime."""
    return {
        "actions": [(lambda: _exit_ok(policy.main(["advisory", "--root", str(ROOT)])))],
    }


def task_lint_gherkin() -> dict[str, Any]:
    """Lint every `features/*.feature` file across crates and tools via `gherlint`."""
    return {
        "actions": [(lambda: _exit_ok(gherkin_lint.main(["--root", str(ROOT)])))],
    }


def task_prose_write() -> dict[str, Any]:
    """Render `.vale.ini` and `.vale/styles/Workloop/` from `vale.toml`."""
    return {
        "actions": [(lambda: _exit_ok(prose.main(["write"], root=ROOT)))],
    }


def task_prose_sync() -> dict[str, Any]:
    """Render Vale files from `vale.toml` and sync pinned upstream Vale styles."""
    return {
        "actions": [(lambda: _exit_ok(prose.main(["sync"], root=ROOT)))],
    }


def task_prose_check() -> dict[str, Any]:
    """Check `.vale.ini` and `.vale/styles/Workloop/` for drift from `vale.toml`."""
    return {
        "actions": [(lambda: _exit_ok(prose.main(["check"], root=ROOT)))],
    }


def task_lint_prose() -> dict[str, Any]:
    """Run Vale prose linting across configured documentation and crate READMEs."""
    return {
        "task_dep": ["prose_check"],
        "actions": [(lambda: _exit_ok(prose.main(["lint"], root=ROOT)))],
    }


def task_check_coverage() -> dict[str, Any]:
    """Verify `coverage/lcov.info` meets >= 90% line coverage across both Rust crates."""
    return {
        "actions": [(lambda: _exit_ok(coverage_gate.main(["--root", str(ROOT)])))],
    }


def task_changelog() -> dict[str, Any]:
    """Render `CHANGELOG.md` from Conventional Commits via `convco`."""
    return {
        "actions": [(lambda: _exit_ok(changelog.main(["regen"], root=ROOT)))],
    }


def task_changelog_check() -> dict[str, Any]:
    """Fail if `CHANGELOG.md` has drifted from Conventional Commits history."""
    return {
        "actions": [(lambda: _exit_ok(changelog.main(["check"], root=ROOT)))],
    }


def task_check_policy() -> dict[str, Any]:
    """Aggregate fast repository policy checks."""
    return {
        "task_dep": [
            "version_check",
            "repo_check",
            "skills_check",
            "backlog_check",
            "registry_check",
            "check_packages",
            "advisory_exception",
            "lint_gherkin",
            "prose_check",
        ],
        "actions": [],
    }
