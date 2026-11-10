---
id: WKL-004
title: Add pluggable review modes (pool, github-bot, both, command) and Stage-0 canary
status: To Do
assignee: []
created_date: '2026-11-10'
labels:
  - review
  - ci
milestone: m-2
dependencies:
  - WKL-003
priority: medium
---

## Description

Support model-family-separated `pool` review, optional `github-bot` (CodeRabbit)
status and review-thread polling, `both`, and `command`, plus Stage-0/Stage-1
self-dogfooding verification.

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 `pool` review rejects configs where reviewer and implementer share the same model family
- [ ] #2 `github-bot` mode polls check runs and unresolved pull request review threads via `gh api`
- [ ] #3 Stage-0 supervisor runs a Stage-1 `./target/debug/workloop` canary in an isolated temp repo
<!-- AC:END -->
