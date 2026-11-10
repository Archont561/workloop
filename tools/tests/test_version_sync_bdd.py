"""BDD step definitions for tools/features/version_sync.feature."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import pytest
from pytest_bdd import given, parsers, scenarios, then, when
from tools import versions

scenarios("../features/version_sync.feature")


@dataclass
class VersionState:
    workspace: Path | None = None
    exit_code: int = -1
    sites: dict[str, str] = field(default_factory=dict)
    problems: list[str] = field(default_factory=list)


@pytest.fixture
def state() -> VersionState:
    return VersionState()


def _create_temp_workspace(base: Path, ver: str) -> Path:
    (base / "crates" / "workloop" / "recipe").mkdir(parents=True)
    (base / "crates" / "workloop-core").mkdir(parents=True)
    (base / "Cargo.toml").write_text(
        f'[workspace]\nmembers = ["crates/workloop-core", "crates/workloop"]\n\n'
        f'[workspace.package]\nversion = "{ver}"\n\n'
        f'[workspace.dependencies]\nworkloop-core = {{ path = "crates/workloop-core", '
        f'version = "{ver}" }}\n',
        encoding="utf-8",
    )
    for crate in ("workloop-core", "workloop"):
        (base / "crates" / crate / "Cargo.toml").write_text(
            f'[package]\nname = "{crate}"\nversion.workspace = true\n',
            encoding="utf-8",
        )
    (base / "pixi.toml").write_text(
        f'[workspace]\nname = "workloop"\nversion = "{ver}"\n',
        encoding="utf-8",
    )
    (base / "package.json").write_text(
        json.dumps({"name": "workloop-dev", "version": ver}, indent=2) + "\n",
        encoding="utf-8",
    )
    (base / "crates" / "workloop" / "recipe" / "recipe.yaml").write_text(
        f"schema_version: 1\ncontext:\n  name: workloop\n  version: {ver}\n",
        encoding="utf-8",
    )
    return base


@given("the live workloop repository workspace")
def given_live_workspace(state: VersionState, repo_root: Path) -> None:
    state.workspace = repo_root


@given(parsers.parse('a temporary workspace at version "{ver}"'))
def given_temp_workspace(state: VersionState, tmp_path: Path, ver: str) -> None:
    state.workspace = _create_temp_workspace(tmp_path, ver)


@given(parsers.parse('the temporary Conda recipe context version is changed to "{ver}"'))
def given_drifted_recipe(state: VersionState, ver: str) -> None:
    assert state.workspace is not None
    recipe = state.workspace / "crates" / "workloop" / "recipe" / "recipe.yaml"
    recipe.write_text(
        f"schema_version: 1\ncontext:\n  name: workloop\n  version: {ver}\n",
        encoding="utf-8",
    )


@given(parsers.parse('crate "{crate}" pins explicit version "{ver}" instead of inheriting'))
def given_pinned_crate(state: VersionState, crate: str, ver: str) -> None:
    assert state.workspace is not None
    manifest = state.workspace / "crates" / crate / "Cargo.toml"
    manifest.write_text(
        f'[package]\nname = "{crate}"\nversion = "{ver}"\n',
        encoding="utf-8",
    )


@when("the version checker inspects all workspace manifests")
@when("the version checker inspects the temporary workspace")
def when_inspect_versions(state: VersionState) -> None:
    assert state.workspace is not None
    state.sites, state.problems = versions.read_versions(state.workspace)
    state.exit_code = versions.main(["--check", "--root", str(state.workspace)])


@when(parsers.parse('the bump tool updates the temporary workspace to "{new_ver}"'))
def when_bump_versions(state: VersionState, new_ver: str) -> None:
    assert state.workspace is not None
    state.exit_code = versions.main(["--set", new_ver, "--root", str(state.workspace)])
    state.sites, state.problems = versions.read_versions(state.workspace)


@then(parsers.parse("the version check exits with code {code:d}"))
@then(parsers.parse("the bump tool exits with code {code:d}"))
def then_exit_code(state: VersionState, code: int) -> None:
    assert state.exit_code == code


@then("all manifest version sites record the same version")
def then_all_match(state: VersionState) -> None:
    assert len(set(state.sites.values())) == 1
    assert state.problems == []


@then(parsers.parse('the version checker reports drift in "{site}"'))
def then_reports_drift(state: VersionState, site: str) -> None:
    assert any(site in p for p in state.problems)


@then("the version checker reports an explicit crate version pin")
def then_reports_pin(state: VersionState) -> None:
    assert any("pins explicit version" in p for p in state.problems)


@then(
    parsers.parse(
        'the version checker on the temporary workspace reports "{expected}" across all manifests'
    )
)
def then_all_updated(state: VersionState, expected: str) -> None:
    assert state.problems == []
    assert set(state.sites.values()) == {expected}
