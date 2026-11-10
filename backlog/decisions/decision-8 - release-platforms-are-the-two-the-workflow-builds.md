---
id: decision-8
title: The release platforms are exactly the two the workflow builds
date: '2026-11-10'
status: accepted
---

## Context

`crates/workloop/recipe/recipe.yaml` carried build branches for four platform
families — `unix` and `win`, each with their own `cargo install` prefix — and
`crates/workloop/recipe/variants.yaml` supplied a `c_stdlib_version` for
`linux x86_64`, `linux aarch64`, `osx x86_64`, and `osx arm64`.
`docs/guides/releasing.md` described five Conda platforms
(`linux-64`, `linux-aarch64`, `osx-64`, `osx-arm64`, `win-64`).

The release matrix in `.github/workflows/release.yml` builds two:
`linux-64` on `ubuntu-24.04` and `osx-arm64` on `macos-14`. The PyPI job runs on
`ubuntu-24.04` only.

So three declared platforms had no matrix entry and no consumer. A recipe branch
that no CI job ever executes is not "supported" — it is untested YAML. The
`win` branch in particular uses `%LIBRARY_PREFIX%` and has never run, so no one
can claim what it produces. The same applies to `linux-aarch64` and `osx-64`,
which `pixi.toml`'s `[feature.packaging]` platform list implied were solved and
buildable.

## Decision

Support is the intersection of "the recipe can express it" and "CI builds and
tests it". That intersection is `linux-64` and `osx-arm64`, and both sides of the
repo now say so.

1. **The recipe keeps only reachable branches.** The `win` script branch is
   removed; `unix` covers both shipped targets. `variants.yaml` keeps
   `c_stdlib_version` for `linux` and `osx` without arch pins, matching the two
   targets that consume it.
2. **`pixi.toml` packaging platforms match the matrix.** `[feature.packaging]`
   lists `linux-64` and `osx-arm64`; a platform that is not built is not a
   platform whose `rattler-build` environment is maintained.
3. **PyPI is tagged `py3-none-<platform>`-honest.** The wheel is built on
   `linux-64` only and published as a runner-specific artifact, so the guide says
   "the runner's platform" rather than implying universal coverage.
4. **Adding a platform is a two-file change.** A new target must land as a matrix
   entry and a recipe/variant change in the same pull request. Re-adding one
   without the other is what this record exists to prevent.

## Consequences

- **Downloads match documentation.** `docs/guides/releasing.md` and the recipe
  now describe the same two platforms, so the "two of five" caveat is gone
  rather than perpetually explained.
- **`linux-aarch64`, `osx-64`, and `win-64` are explicitly unsupported.** Users on
  them build from source (`cargo install --path crates/workloop`), which works
  because nothing here is platform-conditional beyond the removed script branch.
- **The gain is honesty, not capability.** Removing dead branches does not add a
  target; it stops three phantom ones from being mistaken for support. Widening
  is cheap later: a matrix entry plus a variant, both reviewable.
- **`check_distribution` enforces the pairing** so the recipe, `pixi.toml`, and
  the matrix cannot drift apart again.

## Verification

```sh
# Recipe, pixi packaging platforms, and the release matrix name the same platforms
python tools/policy.py distribution --root .
```
