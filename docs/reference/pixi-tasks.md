# Pixi Task Catalog

All contributor commands are defined in [`pixi.toml`](../../pixi.toml):

- `pixi run setup` — run `scripts/bootstrap.sh`.
- `pixi run install-hooks` — install `lefthook` hooks (`commit-msg`, `pre-commit`, `pre-push`).
- `pixi run bun-install` — run `bun install --frozen-lockfile`.
- `pixi run backlog` — invoke `backlog.md` CLI (`1.55.3`).
- `pixi run skills` — invoke `skills` CLI (`1.7.6`).
- `pixi run readme` — render `README.md` from `.readme/README.template.md`.
- `pixi run agents-md` — inspect context budget via `@eugeniughelbur/agents-md`.
- `pixi run fmt-check` / `pixi run clippy` / `pixi run test-all` / `pixi run coverage` — Rust workspace checks and `>= 90%` LCOV gate.
- `pixi run lint-python` / `pixi run format-python-check` / `pixi run typecheck` / `pixi run test-tools-cov` — Python `tools/` checks and `>= 90%` coverage gate.
- `pixi run claim` — atomically claim the next unclaimed `backlog/` card for one loop
  (`tools/claim.py`), printing its id; exits `1` when the queue is empty.
- `pixi run automation <task>` — run any `doit` task defined in [`tools/dodo.py`](../../tools/dodo.py) via `doit.cfg`.
- `pixi run alint` / `pixi run sandbox-check` / `pixi run actionlint` / `pixi run lint-toml` / `pixi run deny-offline` — repository structural and security gates.
