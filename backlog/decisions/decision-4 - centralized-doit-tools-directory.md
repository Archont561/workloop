---
id: decision-4
title: Centralize Python repository automation under tools/ via doit.cfg
date: '2026-11-10'
status: accepted
---

## Context

Keeping `dodo.py` at the repository root scatters Python automation modules and
tests across top-level directories.

## Decision

Configure `doit.cfg` (`dodoFile = tools/dodo.py`, `cwdPath = .`) so every Python
task, policy check, Gherkin feature (`tools/features/`), and pytest suite
(`tools/tests/`) lives inside `tools/` with a `>= 90%` coverage gate enforced in
`.coveragerc` and `codecov.yml`.

## Consequences

The repository root stays clean (`alint` forbids root `dodo.py` and
`automation/`), and all automation code is linted, typechecked, and covered.
