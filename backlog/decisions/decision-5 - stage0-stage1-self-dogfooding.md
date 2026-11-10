---
id: decision-5
title: Stage-0 and Stage-1 split for self-dogfooding workloop
date: '2026-11-10'
status: accepted
---

## Context

When `workloop` develops `workloop`, running `./target/debug/workloop` as the
active supervisor risks stranding the repair loop if an agent commit breaks
compilation or corrupts `.workloop/state.json`.

## Decision

Pin the last released `workloop` binary from
`https://prefix.dev/archont561/archont561` in `pixi.toml` as the immutable
Stage-0 supervisor while building and testing the candidate Stage-1 binary in
`./target/`, verified by a canary smoke check in `hooks.gates`.

## Consequences

Broken candidate builds trigger ordinary `verify` repair cycles under the
known-good Stage-0 supervisor.
