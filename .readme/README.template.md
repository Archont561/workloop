<p align="center">
  <h1 align="center">🔁 <%= projectName %></h1>
  <p align="center">
    <strong>Ship features while you sleep — for $0.</strong><br />
    Turn free open-model tiers, your favorite coding CLI, and GitHub into an autonomous<br />
    <em>task → PR → review &amp; green checks → repair → merge → human approval → release</em> loop.
  </p>
</p>

<p align="center">
  <a href="https://github.com/Archont561/workloop/actions/workflows/ci.yml"><img src="https://img.shields.io/github/actions/workflow/status/Archont561/workloop/ci.yml?branch=main&amp;label=CI&amp;logo=github" alt="CI status" /></a>
  <a href="https://codecov.io/gh/Archont561/workloop"><img src="https://img.shields.io/codecov/c/github/Archont561/workloop?logo=codecov&amp;label=coverage%20%28%E2%89%A590%25%29" alt="Codecov coverage" /></a>
  <a href="https://prefix.dev/channels/archont561"><img src="https://img.shields.io/badge/prefix.dev-archont561%2Fworkloop-f5a623?logo=anaconda&amp;logoColor=white" alt="prefix.dev package" /></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-<%= licenseName %>-blue.svg" alt="License: <%= licenseName %>" /></a>
</p>

<p align="center">
  <a href="#-why-workloop">Why workloop?</a> •
  <a href="#-how-the-loop-works">How the Loop Works</a> •
  <a href="#-decoupled-four-verb-cli">Four-Verb CLI</a> •
  <a href="#-bring-any-agent-any-reviewer-any-shell-hook">Any Agent &amp; Reviewer</a> •
  <a href="#-free-open-model-pools">Free Model Pools</a> •
  <a href="#-repository-status--development">Development</a>
</p>

---

## 💡 Why `workloop`?

Free open-weight coding models in 2026 are genuinely strong — **Devstral**, **Qwen3-Coder**, **DeepSeek**, **GLM**, **MiniMax**, **Nemotron**, and **Gemini Flash** all expose free API tiers with 128K–1M context and tool calling.

Yet wiring them into a reliable, unattended feature pipeline on GitHub breaks down in four predictable places:

1. **Free-tier rate limits (`HTTP 429`) kill multi-file runs.** Pinning a single `:free` endpoint means one burst of tool calls stalls the entire branch.
2. **Self-review is blind.** Asking the same model that wrote a pull request to review its own diff rubber-stamps subtle bugs.
3. **Orchestrator lock-in.** Tools that force a proprietary `.archon/` template or single agent CLI break as soon as you switch between `goose`, `opencode`, `aider`, GitHub Actions, or a local shell loop.
4. **Unbounded autonomy is risky.** Merging small, verified tasks is safe; cutting a public release without a human checkpoint is not.

**`workloop`** is a small, single-binary Rust tool built on [`clifacet`](https://crates.io/crates/clifacet) and distributed via `conda`/`pixi` (`prefix.dev/archont561/archont561`), PyPI (`pipx`/`uvx`), and a from-source `cargo install --path crates/workloop` build:

- 🔀 **Localhost Free-Model Failover Proxy** — spins up an ephemeral `127.0.0.1` OpenAI-compatible router backed by [`registry/free-models.json`](registry/free-models.json) that transparently rotates across free model providers on `429`, `502/503`, or context overflow while keeping API keys redacted via `clifacet::secret::Secret`.
- 🧩 **Four Orchestrator-Decoupled Verbs** — `open`, `exec`, `verify`, and `close` work identically inside a 4-line shell loop, `archon`, GitHub Actions, or `doit` — with **zero** `.archon/` template generation.
- 🕵️ **Pluggable Independent Review** — gate merges on a **second, distinct-family free model** (`pool`), **GitHub PR review bots** such as CodeRabbit (`github-bot`), **`both`**, or your own review script (`command`).
- 🐚 **Zero Built-in Presets** — bring **any** shell commands for environment setup (`sh scripts/restore.sh`, `universe bootstrap`, `npm ci`, `cargo fetch`), task selection, test gates, merge, and release.

---

## 🔄 How the Loop Works

```text
  ┌────────────────────┐
  │ 1. workloop open   │  Runs hooks.setup + hooks.next_task -> .workloop/state.json
  └─────────┬──────────┘
            ▼
  ┌────────────────────┐  Spins up 127.0.0.1 OpenAI 429-failover proxy
  │ 2. workloop exec   │  Runs ANY agent CLI (goose, opencode, aider, custom)
  └─────────┬──────────┘
            ▼
  ┌────────────────────┐  Runs hooks.gates + independent review (pool / github-bot / both)
  │ 3. workloop verify ├───► ❌ Gate or review failed? Feed diagnostics back to `exec`!
  └─────────┬──────────┘
            │ ✅ All checks green & review clean
            ▼
  ┌────────────────────┐
  │ 4. workloop close  │  Merges PR -> advances to next task -> pauses for human release approval
  └────────────────────┘
```

---

## 🧱 Decoupled Four-Verb CLI

Instead of owning your workflow engine, `workloop` exposes four UNIX primitives configured by `workloop.toml`:

```sh
workloop open m-1
until workloop verify; do
  workloop exec --role implement -- goose run --no-session --with-builtin developer -i .workloop/prompt.md
done
workloop close
```

Want [`archon`](https://archon.diy), GitHub Actions, or `cron` to supervise worktrees and approval forms? Call those exact four commands from your existing workflow steps — no template rendering required.

---

## 🔌 Bring Any Agent, Any Reviewer, Any Shell Hook

`workloop.toml` has **no hardcoded language or package-manager presets** — every hook is an ordinary shell command:

```toml
[hooks]
# Arbitrary environment bootstrap: pixi-sandbox today, `universe` tomorrow, or plain `cargo fetch`
setup     = "sh scripts/restore.sh"
next_task = "pixi run --locked backlog task list -s 'To Do' --plain | head -n 1"
gates     = "pixi run --locked fmt-check && pixi run --locked clippy && pixi run --locked coverage"
merge     = "gh pr merge --squash --auto --delete-branch"
release   = "pixi run --locked automation changelog"

[pools]
registry  = "registry/free-models.json"
implement = [
  "opencode/big-pickle",
  "mistral/labs-devstral-small-2512",
  "openrouter/nvidia/nemotron-3-ultra-550b-a55b:free",
  "openrouter/free",
]
review = [
  "google/gemini-2.5-flash",
  "openrouter/cohere/north-mini-code:free",
  "opencode/deepseek-v4.1-flash-free",
]

[review]
# "pool" (default, 100% self-contained) | "github-bot" (e.g. CodeRabbit) | "both" | "command"
mode = "pool"
```

### Supported Coding Agents (via `127.0.0.1` OpenAI Proxy)

| Agent CLI | Example `workloop exec` invocation |
| :--- | :--- |
| **[Goose](https://github.com/block/goose)** | `workloop exec -- goose run --no-session --with-builtin developer -i .workloop/prompt.md` |
| **[OpenCode](https://opencode.ai)** | `workloop exec -- opencode run --file .workloop/prompt.md` |
| **[Aider](https://aider.chat)** | `workloop exec -- aider --yes-always --no-auto-commits --message-file .workloop/prompt.md` |
| **Any custom CLI** | Any script or binary that reads `OPENAI_BASE_URL` + `OPENAI_API_KEY` |

---

## 🆓 Free Open-Model Pools

[`registry/free-models.json`](registry/free-models.json) tracks verified `$0` tool-calling endpoints and enforces **model-family + provider-quota separation** between `implement` and `review` pools (`pixi run --locked automation registry_check`):

| Provider Pool | Example Free Models | Quota Scope |
| :--- | :--- | :--- |
| **OpenCode Zen (`$0`)** | `big-pickle`, `minimax-m3.1-flash-free`, `deepseek-v4.1-flash-free`, `glm-5.3-flash-free` | `opencode-zen` |
| **OpenRouter `:free`** | `nvidia/nemotron-3-ultra-550b-a55b:free`, `cohere/north-mini-code:free`, `openrouter/free` | `openrouter-free-daily` |
| **Mistral Experiment** | `labs-devstral-small-2512` (262K context) | `mistral-experiment` |
| **Google AI Studio** | `gemini-2.5-flash` (1M context) | `google-ai-studio` |

---

## 🛠️ Repository Status & Development

`workloop` is currently at **`m-0` (`v0.1.0` initial scaffold)**:

- **Implemented now (`m-0`):** Two-crate Rust workspace ([`crates/workloop-core`](crates/workloop-core/README.md) + [`crates/workloop`](crates/workloop/README.md)) on `clifacet = "0.5.0"`, `rattler-build` Conda recipe, `maturin` PyPI manifest, `registry/free-models.json` validator, centralized `doit` automation (`doit.cfg` -> `tools/dodo.py`), `pixi-sandbox` offline restore, `vale.sh` prose checks, `alint` structural checks, `skills`, `backlog`, and `>= 90%` Rust + Python coverage gates.
- **Planned next (`m-1` & `m-2`):** Localhost `429` failover proxy, `open`/`exec`/`verify`/`close` verbs, pluggable review adapters, and Stage-0/Stage-1 self-dogfooding. Track progress in [`backlog/`](backlog/README.md) and [`docs/`](docs/README.md).

```sh
pixi install --locked
pixi run --locked bun-install
pixi run --locked alint
pixi run --locked automation check_policy
pixi run --locked automation lint_prose
pixi run --locked clippy
pixi run --locked coverage
pixi run --locked test-tools-cov
```

---

## 📄 License

Distributed under the **<%= licenseName %>** License. See [`LICENSE`](LICENSE) for details.
