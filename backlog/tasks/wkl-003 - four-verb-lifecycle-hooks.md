---
id: WKL-003
title: Implement open, verify, and close lifecycle verbs with user shell hooks
status: To Do
assignee: []
created_date: '2026-11-10'
labels:
  - cli
  - core
milestone: m-1
dependencies:
  - WKL-002
priority: high
---

## Description

Parse `workloop.toml` (`[hooks]` and `[pools]`), persist `.workloop/state.json`,
and implement `workloop open`, `workloop verify`, and `workloop close`.

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 `workloop open` runs `hooks.setup` and `hooks.next_task` without built-in ecosystem presets
- [ ] #2 `workloop verify` executes `hooks.gates` and emits structured repair diagnostics on failure
- [ ] #3 `workloop close` runs `hooks.merge` and pauses before `hooks.release` until explicit human approval
<!-- AC:END -->
