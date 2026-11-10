---
id: WKL-002
title: Implement localhost OpenAI-compatible 429 failover proxy over registry/free-models.json
status: To Do
assignee: []
created_date: '2026-11-10'
labels:
  - core
  - proxy
milestone: m-1
dependencies:
  - WKL-001
priority: high
---

## Description

Build the ephemeral `127.0.0.1` OpenAI-compatible HTTP proxy in `workloop-core`
and expose it via `workloop exec --role implement|review -- <cmd...>`.

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Proxy rotates across configured pool models on HTTP 429, 502, 503, and timeout responses
- [ ] #2 Provider credentials stay inside `clifacet::secret::Secret` and never reach child agent environments
- [ ] #3 Headless `goose`, `opencode`, and custom OpenAI-compatible CLIs complete end-to-end against mock upstreams
<!-- AC:END -->
