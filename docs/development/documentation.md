# Documentation Standard

All committed prose in `README.md`, `AGENTS.md`, `CONTRIBUTING.md`, `docs/`, and
`crates/*/README.md` passes three automated checks:

1. **Vale (`vale.toml`)** — `vale.toml` is the single source of truth for prose
   linting. `pixi run --locked automation prose_sync` renders `.vale.ini`,
   `.vale/styles/Workloop/`, and syncs the pinned `Microsoft` (`v0.15.1`) and
   `write-good` (`v0.4.1`) packages. Run `pixi run --locked automation lint_prose`
   to verify zero alerts.
2. **Markdownlint (`.markdownlint-cli2.jsonc`)** — run
   `pixi run --locked docs-lint` to validate heading hierarchy, fenced code
   language tags, and list formatting.
3. **Link checking (`lychee`)** — run `pixi run --locked check-links-offline` to
   verify that every relative file link across Markdown documentation resolves.

When updating `.readme/README.template.md`, regenerate `README.md` via
`pixi run --locked readme`.
