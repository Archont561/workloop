# Repository Layout

Structural boundaries are enforced automatically by [`.alint.yml`](../../.alint.yml)
and `tools/policy.py`:

```text
workloop/
├── .agents/skills/            # Locked upstream skills + local session & regain-direction
├── .cargo/audit.toml          # Synced with deny.toml
├── .devcontainer/             # Devcontainer definition
├── .github/workflows/         # CI, security, release, publish-sandbox, relock
├── .readme/README.template.md # readme-md-generator template
├── .vale/styles/              # Generated Workloop style + synced Microsoft & write-good
├── backlog/                   # backlog.md config, specs, ADRs, milestones, tasks
├── crates/
│   ├── workloop-core/         # Pure domain library (src/, features/, tests/)
│   └── workloop/              # CLI binary (clifacet), pyproject.toml, recipe/
├── docs/                      # Canonical contributor & architecture documentation
├── registry/free-models.json  # Verified free open-model pools & quota scopes
├── scripts/                   # restore.sh (pixi-sandbox), bootstrap.sh, install_hooks.sh
├── tools/                     # Centralized doit tasks (dodo.py, features/, tests/)
├── Cargo.toml                 # Rust workspace root (edition 2024)
├── codecov.yml                # >= 90% Rust and tools/ coverage targets
├── doit.cfg                   # Points doit to tools/dodo.py
├── pixi.toml                  # Locked conda-forge + prefix.dev/archont561/archont561
├── pixi-sandbox.toml          # Offline sandbox policy
└── vale.toml                  # Single source of truth for prose linting
```

Root `src/`, `tests/`, `dodo.py`, `pyproject.toml`, `recipe/`, and `automation/`
are forbidden by `.alint.yml`.
