# workloop

Standalone CLI binary for `workloop` — a zero-cost AI feature delivery loop for
GitHub powered by free open models and free cloud tiers.

## Current scope

`workloop` (`0.1.0`) is an initial version-and-help scaffold built on
[`workloop-core`](../workloop-core/README.md) and
[`clifacet`](https://crates.io/crates/clifacet), including credential redaction
for provider API keys and GitHub tokens.

```sh
workloop --version
workloop --help
```

## Planned scope

Upcoming milestones in [`backlog/`](../../backlog/README.md) add the four
orchestrator-decoupled lifecycle verbs (`open`, `exec`, `verify`, `close`), the
localhost OpenAI-compatible 429 failover proxy backed by
[`registry/free-models.json`](../../registry/free-models.json), and pluggable
review gates (`pool`, `github-bot`, `both`, `command`).

## License

Licensed under the [MIT License](LICENSE).
