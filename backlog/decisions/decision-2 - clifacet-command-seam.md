---
id: decision-2
title: Use clifacet 0.5.0 for CLI command boundaries and credential redaction
date: '2026-11-10'
status: accepted
---

## Context

`workloop` handles sensitive provider API keys and GitHub App tokens across
both headless CI runs and interactive local debugging sessions.

## Decision

Adopt `clifacet = "0.5.0"` (`default-features = false` in `m-0`, enabling
optional `interactive` or `tui` features only behind explicit boundaries) and
route every secret through `clifacet::secret::Secret`.

## Consequences

Credentials automatically redact as `[redacted]` in `Display` and `Debug`
surfaces, and commands remain testable in-process without spawning PTYs.
