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
    """Compute a deterministic SHA-256 digest of files inside a skill folder."""
    hasher = hashlib.sha256()
    for path in sorted(p for p in skill_dir.rglob("*") if p.is_file()):
        rel = path.relative_to(skill_dir).as_posix()
        hasher.update(rel.encode("utf-8") + b"\0")
        hasher.update(path.read_bytes() + b"\0")
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

    return problems


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


def run_all_policy_checks(root: Path) -> list[str]:
    """Run every repository policy check and return any findings."""
    return [
        *check_repo_invariants(root),
        *check_skills(root),
        *check_backlog_status(root / "backlog"),
        *check_registry(root),
        *check_packages(root),
        *check_advisory_exception(root),
    ]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "check",
        nargs="?",
        default="all",
        choices=("all", "repo", "skills", "backlog", "registry", "packages", "advisory"),
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
