---
name: session
description: Run at the start of every coding session in Archont561/workloop to restore the Pixi environment, install Git hooks, survey backlog tasks, and verify baseline gates. Use when opening a repository checkout or starting a new task.
---

# Session Start (`Archont561/workloop`)

Run this checklist before writing code so you start from a verified baseline and
never duplicate or contradict active `backlog` decisions.

## 1. Verify environment and hooks

```sh
pixi install --locked
pixi run --locked bun-install
pixi run --locked install-hooks
```

Inside offline agent sandboxes where `.pixi-sandbox/` or `scripts/restore.sh` is
present, run `bash scripts/bootstrap.sh --no-fetch` instead.

## 2. Survey backlog state and ADRs

```sh
pixi run --locked backlog board
pixi run --locked backlog task list --plain
```

Read relevant ADRs in `backlog/decisions/` (`decision-1` through `decision-8`)
before proposing new dependencies or CLI surfaces.

## 3. Confirm baseline policy and tests

```sh
pixi run --locked alint
pixi run --locked automation check_policy
pixi run --locked test-tools
pixi run --locked test-all
```
