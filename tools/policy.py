#!/usr/bin/env python3
"""Policy validators for skills, backlog cards, free-model registry, and Cargo manifests."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import tomllib
from pathlib import Path

REQUIRED_LOCAL_SKILLS = frozenset({"session", "regain-direction"})
CANONICAL_STATUSES = frozenset({"To Do", "In Progress", "Done"})
# The complete `[advisories]` surface `cargo-audit` accepts in `.cargo/audit.toml`.
AUDIT_ADVISORY_KEYS = frozenset({"ignore", "informational_warnings", "severity_threshold"})
UNCHECKED_AC_RE = re.compile(r"^\s*-\s*\[\s\]\s+", re.MULTILINE)
FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)


def parse_frontmatter(text: str) -> dict[str, str]:
    """Parse simple scalar YAML frontmatter lines (`key: value`)."""
    match = FRONTMATTER_RE.match(text)
    if match is None:
        return {}
    fields: dict[str, str] = {}
    for raw_line in match.group(1).splitlines():
        if ":" not in raw_line or raw_line.startswith((" ", "\t", "-")):
            continue
        key, _, value = raw_line.partition(":")
        fields[key.strip()] = value.strip().strip("'\"")
    return fields


def compute_skill_folder_hash(skill_dir: Path) -> str:
    """Compute the digest `skills-lock.json` stores for an installed skill folder.

    This mirrors the `skills` CLI exactly (`computeSkillFolderHash` in
    `skills@1.7.6`): files are ordered by relative path, `.git` and
    `node_modules` are skipped, and the hash is fed the relative path bytes
    immediately followed by the file content bytes. There is no separator, so
    adding one here would silently disagree with the installer.
    """
    files = [
        (path.relative_to(skill_dir).as_posix(), path)
        for path in skill_dir.rglob("*")
        if path.is_file() and not {".git", "node_modules"} & set(path.relative_to(skill_dir).parts)
    ]
    files.sort(key=lambda entry: entry[0])
    hasher = hashlib.sha256()
    for relative, path in files:
        hasher.update(relative.encode("utf-8"))
        hasher.update(path.read_bytes())
    return hasher.hexdigest()


def check_skills(root: Path) -> list[str]:
    """Validate `.agents/skills/` and `skills-lock.json`."""
    problems: list[str] = []
    lock_path = root / "skills-lock.json"
    skills_root = root / ".agents" / "skills"

    if not lock_path.is_file():
        return ["missing skills-lock.json"]
    if not skills_root.is_dir():
        return ["missing .agents/skills/ directory"]

    lock_data = json.loads(lock_path.read_text(encoding="utf-8"))
    locked_skills = lock_data.get("skills", {})
    if not isinstance(locked_skills, dict) or not locked_skills:
        problems.append("skills-lock.json defines no locked skills")
        return problems

    present_dirs = {p.name for p in skills_root.iterdir() if p.is_dir()}
    problems.extend(
        f"missing required project-local skill: .agents/skills/{name}"
        for name in sorted(REQUIRED_LOCAL_SKILLS)
        if name not in present_dirs
    )
    problems.extend(
        f"locked skill {name!r} missing from .agents/skills/{name}"
        for name in sorted(locked_skills)
        if name not in present_dirs
    )

    for skill_name in sorted(present_dirs):
        skill_md = skills_root / skill_name / "SKILL.md"
        if not skill_md.is_file():
            problems.append(f".agents/skills/{skill_name}/SKILL.md is missing")
            continue
        meta = parse_frontmatter(skill_md.read_text(encoding="utf-8"))
        if not meta.get("name") or not meta.get("description"):
            problems.append(
                f".agents/skills/{skill_name}/SKILL.md must declare `name` and `description`"
            )
        # A locked skill is byte-fingerprinted by the installer. Reflect that: a local edit either
        # updates the lock deliberately or is reported as drift, so the field is never decorative.
        locked = locked_skills.get(skill_name) if isinstance(locked_skills, dict) else None
        if not isinstance(locked, dict) or not locked.get("computedHash"):
            continue
        actual = compute_skill_folder_hash(skills_root / skill_name)
        if actual != locked["computedHash"]:
            problems.append(
                f".agents/skills/{skill_name} drifted from skills-lock.json "
                f"(expected {locked['computedHash'][:12]}, found {actual[:12]}); "
                "update computedHash in the same change as the edit"
            )

    return problems


def update_skill_hashes(root: Path) -> list[str]:
    """Rewrite `computedHash` for every locked skill from the folder on disk.

    This is the sanctioned path after editing a skill: run it, review the diff it
    produces, and commit the lock beside the edit. It returns the skill names whose
    hash changed, so a caller can report what it touched.
    """
    lock_path = root / "skills-lock.json"
    lock_data = json.loads(lock_path.read_text(encoding="utf-8"))
    changed: list[str] = []
    for skill_name, entry in sorted(lock_data.get("skills", {}).items()):
        skill_dir = root / ".agents" / "skills" / skill_name
        if not skill_dir.is_dir() or not isinstance(entry, dict):
            continue
        digest = compute_skill_folder_hash(skill_dir)
        if entry.get("computedHash") != digest:
            entry["computedHash"] = digest
            changed.append(skill_name)
    lock_path.write_text(json.dumps(lock_data, indent=2) + "\n", encoding="utf-8")
    return changed


def check_backlog_status(backlog_dir: Path) -> list[str]:
    """Validate backlog task statuses, milestones, and Done acceptance criteria."""
    problems: list[str] = []
    tasks_dir = backlog_dir / "tasks"
    milestones_dir = backlog_dir / "milestones"
    if not tasks_dir.is_dir():
        return [f"missing tasks directory: {tasks_dir}"]

    valid_milestones: set[str] = set()
    if milestones_dir.is_dir():
        for ms_file in milestones_dir.glob("*.md"):
            ms_meta = parse_frontmatter(ms_file.read_text(encoding="utf-8"))
            if "id" in ms_meta:
                valid_milestones.add(ms_meta["id"])

    task_files = sorted(tasks_dir.glob("*.md"))
    if not task_files:
        problems.append("backlog/tasks/ contains zero task cards")
        return problems

    for task_file in task_files:
        text = task_file.read_text(encoding="utf-8")
        meta = parse_frontmatter(text)
        status = meta.get("status", "")
        if status not in CANONICAL_STATUSES:
            problems.append(
                f"{task_file.name}: status {status!r} not in {sorted(CANONICAL_STATUSES)}"
            )
        milestone = meta.get("milestone", "")
        if valid_milestones and milestone and milestone not in valid_milestones:
            problems.append(
                f"{task_file.name}: unknown milestone {milestone!r} "
                f"(known: {sorted(valid_milestones)})"
            )
        if status == "Done" and UNCHECKED_AC_RE.search(text):
            problems.append(
                f"{task_file.name}: marked Done while unchecked `- [ ]` criteria remain"
            )
    return problems


def check_registry(root: Path) -> list[str]:
    """Validate `registry/free-models.json` schema and distinct-family review pool invariants."""
    reg_path = root / "registry" / "free-models.json"
    if not reg_path.is_file():
        return ["missing registry/free-models.json"]

    data = json.loads(reg_path.read_text(encoding="utf-8"))
    problems: list[str] = []
    if data.get("schema_version") != 1:
        problems.append("registry/free-models.json: schema_version must equal 1")

    providers = data.get("providers", {})
    models = data.get("models", [])
    pools = data.get("default_pools", {})

    if not isinstance(providers, dict) or not providers:
        return [*problems, "registry/free-models.json: `providers` must be non-empty"]
    if not isinstance(models, list) or not models:
        return [*problems, "registry/free-models.json: `models` must be non-empty"]

    by_id: dict[str, dict[str, object]] = {}
    for entry in models:
        model_id = str(entry.get("id", ""))
        provider = str(entry.get("provider", ""))
        if not model_id or provider not in providers:
            problems.append(f"model {model_id!r} references unknown provider {provider!r}")
            continue
        if entry.get("tool_calling") is not True:
            problems.append(f"model {model_id!r} must support tool_calling = true")
        if int(entry.get("context_window", 0)) < 64000:
            problems.append(f"model {model_id!r} context_window must be >= 64000")
        by_id[model_id] = entry

    impl_pool = pools.get("implement", [])
    rev_pool = pools.get("review", [])
    if not impl_pool or not rev_pool:
        problems.append("default_pools must define non-empty `implement` and `review` lists")
        return problems

    for pool_name, ids in (("implement", impl_pool), ("review", rev_pool)):
        problems.extend(
            f"default_pools.{pool_name} references unknown model {mid!r}"
            for mid in ids
            if mid not in by_id
        )

    if impl_pool[0] in by_id and rev_pool[0] in by_id:
        impl_first = by_id[impl_pool[0]]
        rev_first = by_id[rev_pool[0]]
        if impl_first.get("family") == rev_first.get("family"):
            problems.append(
                "primary implement and review models must belong to distinct model families"
            )
        impl_scope = providers[str(impl_first["provider"])].get("quota_scope")
        rev_scope = providers[str(rev_first["provider"])].get("quota_scope")
        if impl_scope == rev_scope:
            problems.append(
                "primary implement and review models must use distinct provider quota scopes"
            )

    return problems


def check_packages(root: Path) -> list[str]:
    """Verify crate `include` lists omit BDD `features/` and `tests/`."""
    problems: list[str] = []
    cargo_data = tomllib.loads((root / "Cargo.toml").read_text(encoding="utf-8"))
    for member in cargo_data.get("workspace", {}).get("members", []):
        manifest = root / member / "Cargo.toml"
        data = tomllib.loads(manifest.read_text(encoding="utf-8"))
        includes = data.get("package", {}).get("include", [])
        if not includes:
            problems.append(f"{member}/Cargo.toml must declare explicit `package.include`")
            continue
        problems.extend(
            f"{member}/Cargo.toml package.include must not ship BDD specs/tests ({entry!r})"
            for entry in includes
            if "features" in entry or "tests" in entry
        )
    return problems


def check_advisory_exception(root: Path) -> list[str]:
    """Keep `deny.toml` and `.cargo/audit.toml` synced and ensure `rand` is non-runtime."""
    problems: list[str] = []
    deny_data = tomllib.loads((root / "deny.toml").read_text(encoding="utf-8"))
    audit_data = tomllib.loads((root / ".cargo" / "audit.toml").read_text(encoding="utf-8"))

    # `cargo-audit` parses `.cargo/audit.toml` strictly and aborts the Security job on any key
    # it does not know, while `cargo-deny` happily tolerates the same file. The two tools also
    # spell their shared options differently (`audit.ignore` is a string list of advisory ids,
    # `deny.advisories.ignore` a list of tables), so only the keys below may reach the audit
    # file: everything yanked-, severity- or scope-related belongs in `deny.toml` alone.
    audit_advisories = audit_data.get("advisories", {})
    unexpected_keys = sorted(set(audit_advisories) - AUDIT_ADVISORY_KEYS)
    if unexpected_keys:
        problems.append(
            "cargo-audit rejects unknown `.cargo/audit.toml` advisories keys: "
            f"{unexpected_keys} (expected a subset of {sorted(AUDIT_ADVISORY_KEYS)})"
        )

    deny_ids = {
        entry["id"] if isinstance(entry, dict) else str(entry)
        for entry in deny_data.get("advisories", {}).get("ignore", [])
    }
    audit_ids = set(audit_data.get("advisories", {}).get("ignore", []))
    if deny_ids != audit_ids:
        problems.append(
            f"advisory ignore mismatch: deny.toml={sorted(deny_ids)} vs "
            f".cargo/audit.toml={sorted(audit_ids)}"
        )

    lock_path = root / "Cargo.lock"
    if lock_path.is_file():
        lock_data = tomllib.loads(lock_path.read_text(encoding="utf-8"))
        for pkg in lock_data.get("package", []):
            if pkg.get("name") in {"workloop", "workloop-core"}:
                deps = [str(d).split()[0] for d in pkg.get("dependencies", [])]
                if "rand" in deps:
                    problems.append(f"{pkg['name']} depends directly on `rand` in Cargo.lock")
    return problems


# Every `pixi run … <task>` invocation in the files agents read at load time. Skills are
# edited by hand but must stay executable: a documented task that does not exist is a wall,
# not a typo, because an agent follows the instruction literally and fails deterministically.
DOCUMENTED_COMMAND_SOURCES = (
    ".agents/skills/backlog/SKILL.md",
    ".agents/skills/backlog/REFERENCE.md",
    ".agents/skills/session/SKILL.md",
    ".agents/skills/skill-creator/SKILL.md",
)
# `pixi run -e <env>` and `--frozen/--locked` wrappers are stripped before the task name.
PIXI_TASK_RE = re.compile(
    r"pixi run (?:(?:--locked|--frozen|-e \w+) +)*([a-z][\w-]*)",
)
# Subcommands of `doit`, resolved against `tools/dodo.py` task functions.
DOIT_TASK_RE = re.compile(r"automation ([a-z_]+)")


def _declared_pixi_tasks(root: Path) -> set[str]:
    """Collect every task name declared in `pixi.toml`, including feature tasks."""
    manifest = tomllib.loads((root / "pixi.toml").read_text(encoding="utf-8"))
    declared = set(manifest.get("tasks", {}))
    for feature in manifest.get("feature", {}).values():
        declared |= set(feature.get("tasks", {}))
    return declared


def _declared_doit_tasks(root: Path) -> set[str]:
    """Collect every `task_*` factory name defined in `tools/dodo.py`."""
    dodo = (root / "tools" / "dodo.py").read_text(encoding="utf-8")
    return set(re.findall(r"^def task_(\w+)\(", dodo, re.MULTILINE))


def check_documented_commands(root: Path) -> list[str]:
    """Fail when agent-facing instructions name a Pixi or doit task that does not exist."""
    problems: list[str] = []
    pixi_tasks = _declared_pixi_tasks(root)
    doit_tasks = _declared_doit_tasks(root)
    for relative in DOCUMENTED_COMMAND_SOURCES:
        path = root / relative
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        problems.extend(
            f"{relative}: documents missing pixi task {task!r}"
            for task in sorted({m.group(1) for m in PIXI_TASK_RE.finditer(text)} - pixi_tasks)
        )
        problems.extend(
            f"{relative}: documents missing doit task {task!r}"
            for task in sorted({m.group(1) for m in DOIT_TASK_RE.finditer(text)} - doit_tasks)
        )
    return problems


def check_repo_invariants(root: Path) -> list[str]:
    """Verify structural invariants expected alongside `.alint.yml`."""
    problems: list[str] = []
    claude = root / "CLAUDE.md"
    if not claude.is_symlink() or claude.readlink().as_posix() != "AGENTS.md":
        problems.append("CLAUDE.md must be a symlink pointing to AGENTS.md")

    doit_cfg = root / "doit.cfg"
    if not doit_cfg.is_file() or "tools/dodo.py" not in doit_cfg.read_text(encoding="utf-8"):
        problems.append("doit.cfg must set `dodoFile = tools/dodo.py`")

    problems.extend(
        f"forbidden root path exists: {forbidden}"
        for forbidden in ("dodo.py", "src", "tests", "automation")
        if (root / forbidden).exists()
    )
    return problems


RELEASE_WORKFLOW = Path(".github/workflows/release.yml")


def check_distribution(root: Path) -> list[str]:
    """Keep the declared distribution channels and platforms honest.

    Two independent claims are checked, each asserted by a superseding record:
    `decision-7` (no crates.io publication) and `decision-8` (the recipe, the
    `pixi` packaging platforms, and the release matrix name the same targets).
    """
    problems: list[str] = []
    workflow = root / RELEASE_WORKFLOW
    if not workflow.is_file():
        return [f"{RELEASE_WORKFLOW} is missing"]

    workflow_text = workflow.read_text(encoding="utf-8")
    if "cargo publish" in workflow_text:
        problems.append(
            f"{RELEASE_WORKFLOW} publishes to a crate registry; decision-7 keeps "
            "distribution to Conda and PyPI"
        )

    # Platforms actually built: `- platform: <name>` entries in the conda matrix.
    built = set(re.findall(r"^\s*-\s*platform:\s*(\S+)\s*$", workflow_text, re.MULTILINE))
    if not built:
        problems.append(f"{RELEASE_WORKFLOW} declares no conda matrix platforms")

    pixi_cfg = root / "pixi.toml"
    if pixi_cfg.is_file():
        features = tomllib.loads(pixi_cfg.read_text(encoding="utf-8")).get("feature", {})
        declared = set(features.get("packaging", {}).get("platforms", []))
        if declared != built:
            problems.append(
                "pixi.toml [feature.packaging] platforms "
                f"{sorted(declared)} do not match the release matrix {sorted(built)}"
            )

    variants = root / "crates/workloop/recipe/variants.yaml"
    if variants.is_file():
        variant_text = variants.read_text(encoding="utf-8")
        for combo, platform in (("linux and x86_64", "linux-64"), ("osx and arm64", "osx-arm64")):
            if platform in built and combo not in variant_text:
                problems.append(f"variants.yaml has no `c_stdlib_version` for {platform} ({combo})")
        unsupported = {"aarch64": "linux-aarch64", "osx and x86_64": "osx-64"}
        for marker, platform in unsupported.items():
            if platform not in built and marker in variant_text:
                problems.append(
                    f"variants.yaml pins {marker} but {platform} is not built (decision-8)"
                )
        if "win" in variant_text.split("c_stdlib_version", 1)[-1]:
            problems.append("variants.yaml pins win, which the release matrix does not build")
    return problems


def run_all_policy_checks(root: Path) -> list[str]:
    """Run every repository policy check and return any findings."""
    return [
        *check_repo_invariants(root),
        *check_skills(root),
        *check_backlog_status(root / "backlog"),
        *check_registry(root),
        *check_packages(root),
        *check_advisory_exception(root),
        *check_documented_commands(root),
        *check_distribution(root),
    ]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "check",
        nargs="?",
        default="all",
        choices=(
            "all",
            "repo",
            "skills",
            "backlog",
            "registry",
            "packages",
            "advisory",
            "commands",
            "distribution",
        ),
    )
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args(argv)

    dispatch = {
        "all": run_all_policy_checks,
        "repo": check_repo_invariants,
        "skills": check_skills,
        "backlog": lambda r: check_backlog_status(r / "backlog"),
        "registry": check_registry,
        "packages": check_packages,
        "advisory": check_advisory_exception,
        "commands": check_documented_commands,
        "distribution": check_distribution,
    }
    problems = dispatch[args.check](args.root)
    if problems:
        for problem in problems:
            print(f"policy ({args.check}): {problem}", file=sys.stderr)
        return 1
    print(f"policy ({args.check}): ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
