# Releasing

Releases stay synchronized across `Cargo.toml`, `pixi.toml`, `package.json`, and
`crates/workloop/recipe/recipe.yaml`.

1. **Bump synchronized versions:**

   ```sh
   pixi run --locked python -m tools.versions --set 0.2.0
   pixi run --locked automation version_check
   ```

2. **Regenerate `CHANGELOG.md` from Conventional Commits:**

   ```sh
   pixi run --locked automation changelog
   pixi run --locked automation changelog_check
   ```

3. **Dry-run Conda and PyPI artifacts locally:**

   ```sh
   pixi run -e packaging --locked package
   pixi run -e pypi --locked package-pypi
   ```

4. **Tag after human approval:** push `vX.Y.Z` to trigger
   [`.github/workflows/release.yml`](../../.github/workflows/release.yml), which
   publishes Conda artifacts to `https://prefix.dev/archont561/archont561` and
   builds Python wheels via `maturin`.
