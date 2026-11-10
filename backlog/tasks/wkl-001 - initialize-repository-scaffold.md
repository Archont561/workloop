---
id: WKL-001
title: Initialize repository scaffold, crates, tools, sandbox, Vale, alint, and backlog
status: Done
assignee: []
created_date: '2026-11-10'
labels:
  - architecture
  - cli
  - ci
milestone: m-0
dependencies: []
priority: high
---

## Description

Bootstrap `Archont561/workloop` following house conventions with `crates/workloop-core`,
`crates/workloop` (`clifacet = "0.5.0"`), `doit.cfg` + `tools/`, `pixi-sandbox`,
`vale.toml`, `.alint.yml`, `codecov.yml` (`90%`), `skills`, and `backlog`.

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 `crates/workloop-core` and `crates/workloop` pass `fmt-check`, `clippy`, `nextest`, doctests, and `>= 90%` LCOV coverage
- [x] #2 `doit.cfg` points to `tools/dodo.py` and `tools/` passes `ruff`, `mypy`, `gherlint`, and `>= 90%` pytest coverage
- [x] #3 `pixi-sandbox` (`0.9.0`), `vale.sh`, `alint`, `backlog`, and `skills` pass all verification gates
<!-- AC:END -->
