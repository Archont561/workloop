# Contributing to workloop

`workloop` (`0.1.0`) is an initial two-crate Rust scaffold (`workloop-core` and
`workloop`) for orchestrating zero-cost AI feature delivery loops on GitHub.
Read the specification and ADRs under [`backlog/`](backlog/README.md) before
proposing changes, and distinguish implemented scaffold behavior from planned
milestones (`m-1` and `m-2`).

## Development setup

The locked Pixi workspace targets `linux-64` (`pixi.toml`, `pixi.lock`). Install
Pixi or restore the offline sandbox via `scripts/restore.sh`, then run:

```sh
pixi install --locked
pixi run --locked bun-install
pixi run --locked install-hooks
```

See [the development setup guide](docs/guides/development-setup.md) for offline
sandbox restoration and onboarding details.

## Making changes

1. Survey active tasks and ADRs using `pixi run --locked backlog`. Manage task
   status transitions via the `backlog` CLI.
2. Keep Rust domain code, Gherkin features, and BDD tests inside the owning
   crate (`crates/workloop-core/` or `crates/workloop/`). Keep Python repository
   automation, features, and tests under `tools/` (`tools/dodo.py`,
   `tools/features/`, `tools/tests/`) wired via `doit.cfg`.
3. Write a Gherkin scenario and failing BDD test before adding new user-visible
   behavior.
4. Keep prose under [`docs/`](docs/README.md) aligned with
   [the documentation standard](docs/development/documentation.md).

## Running the checks

```sh
pixi run --locked alint
pixi run --locked automation check_policy
pixi run --locked automation lint_prose
pixi run --locked fmt-check
pixi run --locked clippy
pixi run --locked test-all
pixi run --locked coverage
pixi run --locked lint-python
pixi run --locked format-python-check
pixi run --locked typecheck
pixi run --locked test-tools-cov
pixi run --locked docs-lint
pixi run --locked check-links-offline
pixi run --locked actionlint
```

See [running the checks](docs/guides/running-the-checks.md) for details on every
gate.

## Pull requests

Use Conventional Commits (enforced by `convco` via `lefthook` and CI). Follow
[the pull request template](.github/PULL_REQUEST_TEMPLATE.md) and open proposals
through [the issue forms](.github/ISSUE_TEMPLATE/config.yml).
