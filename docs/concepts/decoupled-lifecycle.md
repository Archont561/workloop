# Decoupled Four-Verb Lifecycle

`workloop` avoids generating or owning orchestrator-specific `.archon/` YAML
files. Instead, it exposes four composable CLI verbs configured by arbitrary
shell hooks in `workloop.toml` (`m-1` specification in
[`backlog/`](../../backlog/README.md)):

1. `workloop open [scope]` — runs `hooks.setup` (for example
   `sh scripts/restore.sh`) and `hooks.next_task`, recording the selected task
   and branch in `.workloop/state.json`.
2. `workloop exec [--role implement|review] -- <cmd...>` — binds an ephemeral
   `127.0.0.1` OpenAI-compatible failover proxy over `registry/free-models.json`
   and executes any coding agent (`goose`, `opencode`, `aider`, or a custom
   script) with `OPENAI_BASE_URL` pointed at localhost.
3. `workloop verify` — runs `hooks.gates` plus the configured review strategy
   (`pool`, `github-bot`, `both`, or `command`), printing structured failure
   context when repairs are required.
4. `workloop close` — merges verified pull requests via `hooks.merge` and pauses
   for explicit human approval before executing `hooks.release`.

Because each verb is a standalone UNIX command with deterministic exit codes,
teams can wire the loop into `archon`, GitHub Actions, `doit`, or a four-line
POSIX shell loop.
