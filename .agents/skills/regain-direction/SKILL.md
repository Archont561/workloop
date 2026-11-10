---
name: regain-direction
description: Recover context when stuck, after failing gates, or when returning to an in-progress branch in Archont561/workloop. Use when tests, clippy, Vale, alint, or coverage checks fail unexpectedly.
---

# Regain Direction (`Archont561/workloop`)

Stop making speculative edits. Re-anchor on git state, the active backlog card,
and deterministic repository gates.

## 1. Inspect working tree and active task

```sh
git status -sb
git diff --stat
pixi run --locked backlog task list -s "In Progress" --plain
```

## 2. Isolate the failing layer

Run checks from fastest structural policy up to full compilation and coverage:

```sh
pixi run --locked alint
pixi run --locked automation check_policy
pixi run --locked lint-python
pixi run --locked typecheck
pixi run --locked test-tools-cov
pixi run --locked fmt-check
pixi run --locked clippy
pixi run --locked test-all
pixi run --locked coverage
```

## 3. Respect repository boundaries

- Rust library domain logic belongs in `crates/workloop-core/`; CLI presentation
  and `clifacet` wiring belong in `crates/workloop/`.
- Python repository automation lives exclusively under `tools/` via `doit.cfg`
  (`tools/dodo.py`, `tools/features/`, `tools/tests/`).
- Prose rules are authored in `vale.toml` and rendered via
  `pixi run --locked automation prose_sync`.
