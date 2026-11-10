#!/usr/bin/env bash
set -euo pipefail

if ! command -v pixi >/dev/null 2>&1; then
  curl -fsSL https://pixi.sh/install.sh | bash
  export PATH="${HOME}/.pixi/bin:${PATH}"
fi

pixi install --locked
pixi run --locked bun-install
pixi run --locked install-hooks
