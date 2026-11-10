# Using workloop with Archon

[Archon](https://github.com/coleam00/Archon) and `workloop` solve different
halves of the same problem, and they compose without either owning the other.

- **Archon** is a harness builder. It runs a YAML graph of nodes, gives every
  run its own Git worktree, pauses for human approval, and mixes deterministic
  shell steps with agent steps.
- **`workloop`** is a model and policy layer. It exposes four verbs, keeps
  provider credentials out of child processes, rotates across free model pools
  when an upstream throttles, and applies the review policy you configured.

`workloop` supplies no scheduler, and Archon supplies no rate-limit failover.
Wiring the two together gives a run that can survive a `429` in the middle of a
task and still stop for a human before it merges.

## The boundary

The rule this repository already enforces is that `workloop` never generates or
depends on `.archon/` files. Both [`AGENTS.md`](../../AGENTS.md) and the
`decision-3` record under `backlog/decisions/` state it.
Archon is one supported supervisor among several, on the same footing as GitHub
Actions, `cron`, or a four-line shell loop. Using Archon is a configuration
choice in `workloop.toml`. It is never a build dependency.

| Responsibility | Archon | workloop |
| --- | --- | --- |
| Phase graph, node ordering, branches | yes | no |
| Git worktree per run | yes | no. One state file per working directory |
| Human approval gate | yes (`wait`) | yes, for release only |
| Provider choice and failover | one provider per node | yes, pools in `registry/free-models.json` |
| Credential isolation | passes node environment | yes, only the proxy URL reaches the child |
| Review policy | review node as written | distinct-family pools or bot polling |
| Task selection | issue or dispatch trigger | `hooks.next_task` over `backlog/` |

Read the `workloop` column as intent: at `0.1.0` only `version` and `help` are
implemented. `WKL-002` and `WKL-003` deliver the verbs this guide drives.

## Workflow shape

Archon nodes call `workloop` verbs as ordinary shell steps. The example below is
illustrative. Check the node keys against the
[Archon documentation](https://archon.diy/docs) for your version.

```yaml
# .archon/workflows/workloop-task.yaml
name: workloop-task
description: Run one backlog task through the workloop lifecycle.

nodes:
  - id: open
    bash: "workloop open m-1"

  - id: implement
    depends_on: [open]
    loop:
      prompt: "Continue the task described in .workloop/prompt.md."
      until_bash: "workloop verify"
      max_iterations: 6
      fresh_context: true

  - id: approve
    depends_on: [implement]
    wait:
      attention: "Review the diff and the verification report."
      form: approval

  - id: close
    depends_on: [approve]
    when: "$approve.output.decision == 'approve'"
    bash: "workloop close"
```

Each node maps to one verb, and each verb keeps its own exit code, so a failed
node has exactly one cause to report.

## What each node inherits

| Node | Archon supplies | workloop supplies |
| --- | --- | --- |
| `open` | an isolated worktree and branch | `hooks.setup`, then the next backlog card |
| `implement` | iteration limit and fresh context | the `127.0.0.1` proxy in front of the agent CLI |
| `approve` | the pause and the decision form | nothing. This gate belongs to Archon |
| `close` | the run's Git branch | `hooks.merge`, then the release pause |

## Install hooks that speak both tools

`workloop.toml` holds no presets, so the backlog and the repository gates are
wired by hand:

```toml
[hooks]
setup     = "sh scripts/restore.sh"
next_task = "pixi run --locked backlog task list -s 'To Do' --plain | head -n 1"
gates     = "pixi run --locked fmt-check && pixi run --locked clippy && pixi run --locked automation check_policy"
merge     = "gh pr merge --squash --auto --delete-branch"
release   = "pixi run --locked automation changelog"

[review]
mode = "pool"
```

The proxy is the part Archon cannot replace. `workloop exec` binds an ephemeral
listener and points the agent CLI at it through `OPENAI_BASE_URL`. The provider
key stays in the parent process, the child receives a placeholder, and an
upstream `429` triggers rotation to another pool entry instead of ending the
node.

## Provider support for the proxy

Archon injects node and codebase environment variables into a provider only when
that provider declares support for it, and it warns instead of failing when a
provider does not. This decides whether an Archon agent node can reach
`workloop`'s localhost proxy directly.

| Archon provider | Injects environment | Route to the proxy |
| --- | --- | --- |
| Claude | yes | through `workloop exec`, which owns the child environment |
| Codex | yes | through `workloop exec` |
| Pi | yes | through `workloop exec`, or a custom provider in `models.json` |
| OpenCode | no | `workloop exec` only. Archon refuses `baseUrl` for this provider |
| Copilot | yes | through `workloop exec` |

The practical reading is that the proxy is reached by **wrapping the agent
command**, which is what `workloop exec` does, and not by configuring a base URL
inside Archon. That keeps the boundary in one place: Archon never learns a
provider URL, and `workloop` never learns an Archon path.

## Four rules that keep the layers apart

1. **One retry loop.** Do not point Archon's `until_bash` at the same commands
   `workloop verify` already runs, or each iteration retries both. Let
   `workloop` own repair inside a task and Archon own progress across tasks.
2. **Worktrees belong to Archon.** `workloop` must not create branches. Once a
   loop opens its own branch, `.workloop/state.json` and the worktree disagree
   about which directory is the run.
3. **One approval authority.** Use Archon's `wait` gate before a merge and the
   `workloop` release pause before a public release. Never both for one
   decision.
4. **Keys stay in configuration.** Archon passes an environment per node. Only
   `OPENAI_BASE_URL` and a placeholder key belong in the agent node's
   environment, which is what `WKL-002` criterion 2 requires.

## Parallel runs

Archon already isolates runs by worktree, which is the isolation `workloop`
deliberately does not implement. Two caveats follow from that split:

- **Claim the task before the run starts.** `hooks.next_task` is a query. Two
  runs dispatched together can select the same card. Set the card to
  `In Progress` from the dispatching step, or pass a scope so each run never
  queries.
- **Expect provider pools to be shared.** Every run draws on the same free
  pools. The quota scopes in `registry/free-models.json` are what stop one
  throttled provider from stalling every run, and
  [`tools/policy.py`](../../tools/policy.py) enforces that implementation and
  review never share a family.

## Verify the integration

After the first run, confirm the boundary held:

```sh
# No orchestrator templates were created inside the repository
git status --short .archon

# The proxy, not a provider key, reached the child process
workloop exec --role implement -- sh -c 'printf "%s\n" "$OPENAI_BASE_URL"'

# The card moved only when its criteria were proven
pixi run --locked backlog task list --plain
```

## Limits to state honestly

- **The verbs are not implemented yet.** `WKL-002` (proxy) and `WKL-003`
  (verbs) are the work that makes this guide executable. Until they land,
  Archon's own providers remain the simpler path.
- **Archon isolates Git state, not the runtime.** Its isolation providers
  reserve a container backend, but only the worktree provider is implemented
  today. For a sandboxed runtime, run `workloop` inside a restored
  `pixi-sandbox` environment.
- **Archon refuses a base URL on its OpenCode provider.** A changelog entry for
  `assistants.opencode.baseUrl` records that every OpenCode run already rejected
  that key, so pointing Archon's OpenCode node at a localhost proxy is not
  supported. Use `workloop exec`, which sets the proxy URL for the child
  process, instead of configuring a base URL in Archon.
- **Environment injection varies by provider.** Archon injects configured
  environment variables only where the provider declares that it supports them,
  and its OpenCode provider declares no support. The table above is read from
  Archon's provider sources, so check it again after an upgrade.

## See also

- [Backlog as a knowledge base](backlog-as-knowledge-base.md) — the cards
  `next_task` selects from.
- [Decoupled four-verb lifecycle](../concepts/decoupled-lifecycle.md) — verb
  behavior and hook names.
- [Pixi task catalog](../reference/pixi-tasks.md) — the locked commands used in
  hooks.
- `decision-6` under `backlog/decisions/` records the binding stance: Archon is
  a supported supervisor, never a dependency.
