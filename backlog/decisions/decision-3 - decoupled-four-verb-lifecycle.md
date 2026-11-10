---
id: decision-3
title: Decouple lifecycle verbs from orchestrator YAML templates
date: '2026-11-10'
status: accepted
---

## Context

Tightly coupling `workloop` to generated `.archon/workflows/*.yaml` templates
adds template-engine maintenance burden and prevents teams from invoking the
same loop from GitHub Actions, `doit`, `just`, or local shell loops.

## Decision

Drop `.archon/` template rendering (`minijinja`) and expose four composable
verbs (`open`, `exec`, `verify`, `close`) plus user-defined shell hooks in
`workloop.toml` (`setup`, `next_task`, `gates`, `review`, `merge`, `release`).

## Consequences

Any orchestrator (`archon`, GitHub Actions, cron, or interactive shell) can
drive `workloop` in four lines without built-in ecosystem presets.
