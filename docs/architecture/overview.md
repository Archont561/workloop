# Architecture Overview

`workloop` separates pure domain logic from CLI presentation and repository
automation across three isolated units.

## Crate boundaries

- [`crates/workloop-core/`](../../crates/workloop-core/README.md) — pure library
  crate with zero CLI or terminal dependencies. In `m-0` (`0.1.0`) it exposes
  canonical version metadata; `m-1` and `m-2` place `workloop.toml` parsing,
  `registry/free-models.json` pool state, `127.0.0.1` HTTP failover routing, and
  review verification here.
- [`crates/workloop/`](../../crates/workloop/README.md) — standalone binary
  crate built on `workloop-core`, `clap`, and `clifacet` (`0.5.0`). Provider API
  keys and GitHub tokens pass through `clifacet::secret::Secret` so credentials
  render as `[redacted]` across logs and failure diagnostics.

## Free-model registry

[`registry/free-models.json`](../../registry/free-models.json) catalogs verified
zero-cost tool-calling endpoints across OpenCode Zen, OpenRouter `:free`,
Mistral Experiment, and Google AI Studio. `tools/policy.py` enforces that the
primary `implement` and `review` pools draw from distinct model families and
distinct provider quota scopes.

## Self-dogfooding via Stage-0 / Stage-1

When `workloop` develops `workloop`, the repository runs a released Stage-0
`workloop` binary from `https://prefix.dev/archont561/archont561` as the outer
supervisor while compiling and testing the Stage-1 candidate inside `./target/`.
A broken candidate build simply fails `hooks.gates` and enters an ordinary
repair cycle without stranding the active supervisor.
