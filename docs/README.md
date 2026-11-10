# workloop Documentation

Canonical documentation for `Archont561/workloop`.

## Architecture & Concepts

- [Architecture overview](architecture/overview.md) — crate split
  (`workloop-core` and `workloop`), `clifacet` command boundary, free-model
  registry, and Stage-0/Stage-1 self-dogfooding.
- [Decoupled four-verb lifecycle](concepts/decoupled-lifecycle.md) — how `open`,
  `exec`, `verify`, and `close` compose inside any orchestrator (`archon`,
  GitHub Actions, `doit`, or shell loops) without `.archon/` template lock-in.

## Contributor Guides

- [Development setup](guides/development-setup.md) — Pixi installation,
  `pixi-sandbox` offline restoration, Bun tooling, and `lefthook` Git hooks.
- [Running the checks](guides/running-the-checks.md) — Rust, Python `tools/`,
  Vale prose, `alint`, Gherkin, and `>= 90%` coverage gates.
- [Releasing](guides/releasing.md) — version synchronization, `convco`
  changelog generation, Conda (`rattler-build`), and PyPI (`maturin`) builds.
- [Backlog as a knowledge base](guides/backlog-as-knowledge-base.md) — how
  specification, decision records, milestones, and task cards fit together, and
  the frontmatter rules that make the backlog safe to automate.
- [Using workloop with Archon](guides/archon-integration.md) — which tool owns
  which responsibility, the node-to-verb mapping, and the four rules that keep
  the layers apart.
- [Documentation standard](development/documentation.md) — `vale.toml` rules,
  `markdownlint-cli2`, and offline link checking.

## Reference

- [Pixi task catalog](reference/pixi-tasks.md) — locked `pixi run` commands and
  `doit` automation targets.
- [Repository layout](reference/repository-layout.md) — structural rules
  enforced by `.alint.yml`.
