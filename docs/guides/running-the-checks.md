# Running the Checks

Every CI gate can be executed locally through `pixi run --locked`:

| Gate | Command | Requirement |
| --- | --- | --- |
| Structural layout | `pixi run --locked alint` | Zero errors against `.alint.yml` |
| Sandbox drift | `pixi run --locked sandbox-check` | `scripts/restore.sh` & workflows match `pixi-sandbox.toml` |
| Policy & Gherkin | `pixi run --locked automation check_policy` | Versions, skills, backlog, registry, packages, `gherlint`, Vale drift |
| Prose lint | `pixi run --locked automation lint_prose` | Zero Vale alerts across configured sources |
| Markdown & links | `pixi run --locked docs-lint && pixi run --locked check-links-offline` | Clean Markdown and valid relative links |
| Python tools | `pixi run --locked lint-python && pixi run --locked typecheck && pixi run --locked test-tools-cov` | Zero `ruff`/`mypy` errors and `>= 90%` coverage |
| Rust quality | `pixi run --locked fmt-check && pixi run --locked clippy` | Zero formatting diffs and zero pedantic `clippy` warnings |
| Rust BDD & coverage | `pixi run --locked test-all && pixi run --locked coverage` | All unit, BDD, and doc tests pass with `>= 90%` LCOV line coverage |
