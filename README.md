# Offline sandbox (orphan branch)

Built 2026-11-10T20:28:40Z from commit `eb2c138` for platform `linux-64`.
`pixi.lock` sha256 `59c35713630ef4301ec2924bc718d316852ce97f2a9253a292ac23f0e0d51fb7`.

The verified self-bootstrap binary is stored at `.pixi-sandbox/tools/linux-64/pixi-sandbox`. The branch root intentionally contains documentation only.

| env | platform | packed | unpacked | files |
| --- | --- | ---: | ---: | ---: |
| `default` | linux-64 | 563.7 MiB | 2188.4 MiB | 93 |

Cargo dependencies: **204 crates**, 272.1 MiB (loose) from `Cargo.lock` sha256 `f32371991ebd…`; restore materialises them to `.pixi-sandbox/vendor/`. Built with cargo 1.99.1 (5f94df478 2026-08-27); rustc 1.99.1 (58cf8f9c3 2026-10-13).


## Restore on the disconnected machine

```bash
./.pixi-sandbox/tools/linux-64/pixi-sandbox doctor --branch-location . --verify
./.pixi-sandbox/tools/linux-64/pixi-sandbox restore --branch-location . --output-path <project> --force
# then, from <project> with no network, use pixi as the sole entrypoint:
pixi install --frozen --offline
pixi run --frozen -- cargo build --offline
```

Every manifest blob is verified before it is written into the working tree.
