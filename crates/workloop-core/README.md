# workloop-core

Core domain library for [`workloop`](../workloop/README.md).

## Current scope

`workloop-core` is an initial scaffold (`0.1.0`) that exposes the crate version
and build metadata used by the `workloop` CLI binary.

```rust
assert!(!workloop_core::VERSION.is_empty());
assert_eq!(workloop_core::version_banner(), format!("workloop {}", workloop_core::VERSION));
```

## Planned scope

Future milestones in [`backlog/`](../../backlog/README.md) place `workloop.toml`
parsing, free-model pool failover state, review-gate aggregation, and the
four-verb session state machine (`open`, `exec`, `verify`, `close`) inside this
crate without coupling to any CLI presentation dependencies.

## License

Licensed under the [MIT License](LICENSE).
