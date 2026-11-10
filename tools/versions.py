#!/usr/bin/env python3
"""Synchronize and validate semantic versions across Cargo, Pixi, Conda, and package.json."""

from __future__ import annotations

import argparse
import json
import re
import sys
import tomllib
from pathlib import Path

SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?$")
RECIPE_REL = Path("crates/workloop/recipe/recipe.yaml")
RECIPE_VERSION_RE = re.compile(r"(^\s*version:\s*)([^\s#]+)", re.MULTILINE)
CARGO_VERSION_RE = re.compile(
    r'(\[workspace\.package\][\s\S]*?^version\s*=\s*")([^"]+)(")',
    re.MULTILINE,
)
WORKSPACE_DEP_RE = re.compile(
    r'(workloop-core\s*=\s*\{[^}]*?\bversion\s*=\s*")([^"]+)(")',
)
PIXI_VERSION_RE = re.compile(
    r'(\[workspace\][\s\S]*?^version\s*=\s*")([^"]+)(")',
    re.MULTILINE,
)


def read_versions(root: Path) -> tuple[dict[str, str], list[str]]:
    """Read manifest versions and verify crates inherit `version.workspace = true`."""
    sites: dict[str, str] = {}
    problems: list[str] = []

    cargo_path = root / "Cargo.toml"
    cargo_data = tomllib.loads(cargo_path.read_text(encoding="utf-8"))
    workspace_pkg = cargo_data.get("workspace", {}).get("package", {})
    cargo_ver = str(workspace_pkg.get("version", ""))
    sites["Cargo.toml"] = cargo_ver

    ws_dep = cargo_data.get("workspace", {}).get("dependencies", {}).get("workloop-core", {})
    if isinstance(ws_dep, dict) and "version" in ws_dep:
        sites["Cargo.toml (workspace.dependencies.workloop-core)"] = str(ws_dep["version"])

    for member in cargo_data.get("workspace", {}).get("members", []):
        member_toml = root / member / "Cargo.toml"
        member_data = tomllib.loads(member_toml.read_text(encoding="utf-8"))
        pkg_ver = member_data.get("package", {}).get("version")
        if pkg_ver != {"workspace": True}:
            problems.append(
                f"{member}/Cargo.toml pins explicit version {pkg_ver!r}; "
                "use `version.workspace = true`"
            )

    pixi_path = root / "pixi.toml"
    pixi_data = tomllib.loads(pixi_path.read_text(encoding="utf-8"))
    sites["pixi.toml"] = str(pixi_data.get("workspace", {}).get("version", ""))

    pkg_path = root / "package.json"
    pkg_data = json.loads(pkg_path.read_text(encoding="utf-8"))
    sites["package.json"] = str(pkg_data.get("version", ""))

    recipe_path = root / RECIPE_REL
    recipe_text = recipe_path.read_text(encoding="utf-8")
    match = RECIPE_VERSION_RE.search(recipe_text)
    if match is None:
        problems.append(f"{RECIPE_REL.as_posix()} is missing `context.version`")
    else:
        sites[RECIPE_REL.as_posix()] = match.group(2).strip("'\"")

    canonical = sites["Cargo.toml"]
    if not SEMVER_RE.match(canonical):
        problems.append(f"Cargo.toml version {canonical!r} is not valid SemVer")

    for site, value in sites.items():
        if value != canonical:
            problems.append(f"version drift in {site}: {value!r} != Cargo.toml {canonical!r}")

    return sites, problems


def bump_versions(root: Path, new_version: str) -> None:
    """Update all synchronized manifest version sites to `new_version`."""
    if not SEMVER_RE.match(new_version):
        raise ValueError(f"invalid semantic version: {new_version!r}")

    cargo_path = root / "Cargo.toml"
    cargo_text = cargo_path.read_text(encoding="utf-8")
    cargo_text, count_pkg = CARGO_VERSION_RE.subn(rf"\g<1>{new_version}\3", cargo_text, count=1)
    cargo_text, _ = WORKSPACE_DEP_RE.subn(rf"\g<1>{new_version}\3", cargo_text, count=1)
    if count_pkg != 1:
        raise RuntimeError("Cargo.toml missing [workspace.package] version")
    cargo_path.write_text(cargo_text, encoding="utf-8")

    pixi_path = root / "pixi.toml"
    pixi_text = pixi_path.read_text(encoding="utf-8")
    pixi_text, count_pixi = PIXI_VERSION_RE.subn(rf"\g<1>{new_version}\3", pixi_text, count=1)
    if count_pixi != 1:
        raise RuntimeError("pixi.toml missing [workspace] version")
    pixi_path.write_text(pixi_text, encoding="utf-8")

    pkg_path = root / "package.json"
    pkg_data = json.loads(pkg_path.read_text(encoding="utf-8"))
    pkg_data["version"] = new_version
    pkg_path.write_text(json.dumps(pkg_data, indent=2) + "\n", encoding="utf-8")

    recipe_path = root / RECIPE_REL
    recipe_text = recipe_path.read_text(encoding="utf-8")
    recipe_text, count_recipe = RECIPE_VERSION_RE.subn(rf"\g<1>{new_version}", recipe_text, count=1)
    if count_recipe != 1:
        raise RuntimeError(f"{RECIPE_REL.as_posix()} missing context version")
    recipe_path.write_text(recipe_text, encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--check", action="store_true", help="Verify manifest versions match")
    group.add_argument("--set", dest="new_version", help="Set all manifests to SemVer")
    args = parser.parse_args(argv)

    if args.new_version is not None:
        try:
            bump_versions(args.root, args.new_version)
        except (RuntimeError, ValueError) as exc:
            print(f"versions: {exc}", file=sys.stderr)
            return 1

    sites, problems = read_versions(args.root)
    if problems:
        for problem in problems:
            print(f"versions: {problem}", file=sys.stderr)
        return 1

    print(f"versions: {sites['Cargo.toml']} synchronized across {len(sites)} site(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
