# Releasing

Releases stay synchronized across `Cargo.toml`, `pixi.toml`, `package.json`, and
`crates/workloop/recipe/recipe.yaml`.

1. **Bump synchronized versions:**

   ```sh
   python -m tools.versions --set 0.2.0
   pixi run --locked automation version_check
   ```

   `tools.versions` is the same validator `version_check` runs, so the bump and
   the check cannot disagree about the five sites it syncs.

2. **Regenerate `CHANGELOG.md` from Conventional Commits:**

   ```sh
   pixi run --locked automation changelog
   pixi run --locked automation changelog_check
   ```

   `CHANGELOG.md` renders at **release time**, not on every merge. No gate in
   CI or `lefthook` calls `changelog_check`, so the committed file keeps a single
   `[Unreleased]` section until a release regenerates it. Run `changelog` before
   tagging, and commit the result with the version bump.

3. **Dry-run Conda and PyPI artifacts locally:**

   ```sh
   pixi run -e packaging --locked package
   pixi run -e pypi --locked package-pypi
   ```

4. **Tag after human approval:** push `vX.Y.Z` to trigger
   [`.github/workflows/release.yml`](../../.github/workflows/release.yml), which
   publishes Conda artifacts to `https://prefix.dev/archont561/archont561` and
   builds Python wheels via `maturin`.

## What the release workflow actually publishes

| Artifact | Platforms | Where |
| --- | --- | --- |
| Conda package | `linux-64`, `osx-arm64` | `https://prefix.dev/archont561/archont561` |
| Python wheel and sdist | the runner's platform | GitHub Actions artifacts |

The recipe, `pixi.toml`'s `[feature.packaging]` platform list, and the matrix in
`release.yml` all name the same two targets. `linux-aarch64`, `osx-64`, and
`win-64` are explicitly unsupported (`decision-8`): a user on one of them builds
from source with `cargo install --path crates/workloop`. Adding a platform is a
single pull request that adds the matrix entry, the variant, and the `pixi`
platform together — `python tools/policy.py distribution` fails if only some of
them move. Nothing publishes to crates.io (`decision-7`).
