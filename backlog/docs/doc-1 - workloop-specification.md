---
id: doc-1
title: workloop Specification
type: specification
created_date: '2026-11-10'
---

# workloop Specification

## Purpose

`workloop` turns free open-model endpoints and free cloud tiers into a
predictable GitHub feature delivery loop:

`task -> PR -> review & green checks -> repair -> merge -> next task -> human approval -> release`

## Core Lifecycle Verbs

Rather than generating orchestrator-specific `.archon/` templates, `workloop`
exposes four orchestrator-agnostic verbs configured by `workloop.toml`:

1. `workloop open [scope]` — runs `hooks.setup` and `hooks.next_task`, creating
   or resuming `.workloop/state.json`.
2. `workloop exec [--role implement|review] -- <cmd...>` — starts an ephemeral
   `127.0.0.1` OpenAI-compatible HTTP proxy backed by `registry/free-models.json`
   with automatic HTTP `429`/`5xx` failover and credential redaction via
   `clifacet::secret::Secret`, then runs the arbitrary coding agent command.
3. `workloop verify` — runs `hooks.gates` and the configured `[review]` strategy
   (`pool`, `github-bot`, `both`, or `command`), emitting actionable repair
   diagnostics on non-zero exit.
4. `workloop close` — merges the pull request via `hooks.merge`, advances to the
   next task, or pauses for human approval before `hooks.release`.
