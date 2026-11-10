---
id: decision-7
title: Conda and PyPI are the only distribution targets
date: '2026-11-10'
status: accepted
supersedes: decision-1
---

## Context

`decision-1` lists three publishing destinations: `prefix.dev/archont561/archont561`,
`crates.io`, and PyPI. The workspace was subsequently built, packaged, and
released against two of them. The crates.io destination was never implemented:
there is no `cargo publish` invocation in `.github/workflows/release.yml`, no
`release` task that pushes to a registry, and no dependency on a published
`workloop` crate from anywhere in this workspace.

That left a live contradiction. `decision-1` promised a channel that does not
exist, so a reader could reasonably expect `cargo install workloop` to work and
be wrong. Records here are append-only, so the fix is a superseding decision
rather than an edit to history.

## Decision

`workloop` publishes to exactly two destinations, and neither is crates.io.

1. **Conda** — `rattler-build` artifacts uploaded to
   `https://prefix.dev/archont561/archont561`, consumed through `pixi` or `conda`.
2. **PyPI** — a `maturin` `bindings = "bin"` wheel and sdist built by the
   release workflow.

Installation from source stays supported and is documented as
`cargo install --path crates/workloop`, which builds the local checkout and
publishes nothing. References to `crates.io` in documentation name third-party
dependencies (`clifacet`) only, never `workloop` itself.

## Consequences

- **`decision-1`'s packaging split stands; its third destination does not.** The
  two-crate workspace, the recipe under `crates/workloop/recipe/`, and the
  `maturin` manifest are unchanged and still correct.
- **No crates.io release ceremony.** Version bumps synchronize Cargo, `pixi.toml`,
  `package.json`, and the recipe, but nothing is tagged for a registry.
- **The crate stays `publish = false`-shaped in practice.** Nothing needs to be
  added to force this; the absence of a publication step is the mechanism, and
  `check_distribution` fails if one reappears without this record reversing.

## Verification

```sh
# No workflow pushes to a crate registry
git grep -n 'cargo publish' -- .github/ tools/ pixi.toml || echo "no crates.io publish step"
```
