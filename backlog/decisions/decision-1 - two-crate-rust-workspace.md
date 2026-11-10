---
id: decision-1
title: Two-crate Rust workspace (workloop-core + workloop) with Conda and PyPI packaging
date: '2026-11-10'
status: accepted
---

## Context

`workloop` must run inside headless CI runners, local developer shells, and
offline sandboxes without runtime Python or Node.js overhead, while still
publishing cleanly to `prefix.dev/archont561/archont561`, `crates.io`, and PyPI.

## Decision

Split the Rust workspace into `crates/workloop-core` (pure domain library) and
`crates/workloop` (CLI binary, `rattler-build` recipe under
`crates/workloop/recipe/`, and `maturin` `bindings = "bin"` manifest under
`crates/workloop/pyproject.toml`).

## Consequences

Domain logic stays decoupled from CLI presentation crates, and one workspace
version feeds Cargo, Conda, and PyPI artifacts.
