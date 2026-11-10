# Development Setup

## Online setup with Pixi

Install [Pixi](https://pixi.sh) (`>= 0.81.0`), clone the repository, and install
the locked `linux-64` toolchain, Bun packages, Vale styles, and Git hooks:

```sh
pixi install --locked
pixi run --locked bun-install
pixi run --locked automation prose_sync
pixi run --locked install-hooks
```

## Offline sandbox restoration

For ephemeral cloud or agent sandboxes, `pixi-sandbox.toml` defines a
pre-built `developer` bundle and vendored Cargo cache. Run:

```sh
bash scripts/restore.sh
```

Or run `bash scripts/bootstrap.sh` to restore the sandbox (when missing),
install `lefthook` hooks, and execute fast smoke gates (`test-tools` and
`alint`).
