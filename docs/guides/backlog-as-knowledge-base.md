# Backlog as a Knowledge Base

`backlog/` is the work-facing knowledge base: what the project must do, why it
decided to do it that way, and how far each piece has progressed. It is not a
scratch pad beside the repository. It is the input that `workloop` reads when it
chooses the next task, and the record a reviewer reads to judge whether the work
is finished.

Contributor documentation answers "how do I build and check this repository". It
lives in [`docs/`](../README.md). The backlog answers "what are we building, in
what order, and on what grounds". Keep the two apart so a task card never turns
into a second architecture page.

## The four record types

| Record | Location | Question it answers | Typical author |
| --- | --- | --- | --- |
| Specification | `backlog/docs/` | What should the product do, stated once? | Maintainer, edited rarely |
| Decision record | `backlog/decisions/` | Why this design and not the alternative? | Whoever made the call |
| Milestone | `backlog/milestones/` | Which outcome does this body of work deliver? | Maintainer |
| Task card | `backlog/tasks/` | What is the next verifiable unit of work? | Anyone, at any time |

Each type carries YAML frontmatter, so `tools/policy.py` can enforce the schema
without a database. The rest of the file is prose for humans and agents.

## Task cards

A task card is the atom the loop consumes. It has an identifier (`WKL-002`), a
title, a status, a milestone, optional dependencies, a description, and a
checklist of acceptance criteria between `<!-- AC:BEGIN -->` and `<!-- AC:END -->`
markers:

```md
---
id: WKL-002
title: Implement localhost OpenAI-compatible 429 failover proxy
status: To Do
milestone: m-1
dependencies:
  - WKL-001
priority: high
---

## Description

Build the ephemeral `127.0.0.1` proxy in `workloop-core`.

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Proxy rotates across pool models on HTTP 429, 502, 503, and timeout
- [ ] #2 Provider credentials never reach child agent environments
<!-- AC:END -->
```

Write acceptance criteria as observable outcomes. A criterion that names a
command, a file, or a test can be verified by a gate. A criterion that names a
feeling cannot, and it blocks the task from ever reaching `Done` honestly.

## The frontmatter contract

Three rules are machine-checked on every push
(`pixi run --locked automation check_policy`, which runs `backlog_check`):

1. **Status vocabulary.** `status` is one of `To Do`, `In Progress`, or `Done`.
   Any other value fails the gate.
2. **Milestone existence.** A named `milestone` must resolve to a file in
   `backlog/milestones/` with a matching `id`.
3. **Done means proven.** A card marked `Done` may not leave an unchecked
   `- [ ]` criterion behind. Finish the criterion, or change the status.

These three rules make the backlog safe to drive automation from: a `Done` card
is a claim the repository already verified, not a note someone typed.

## Commands

The `backlog` CLI owns identifiers, filenames, dependency links, and status
transitions. Use it instead of editing frontmatter by hand:

```sh
# Survey the board and the next unblocked work
pixi run --locked backlog board --plain
pixi run --locked backlog task list -s "To Do" --plain

# Read one card, then claim it
pixi run --locked backlog task 2 --plain
pixi run --locked backlog task edit 2 -s "In Progress"
```

The full command surface, including draft workflows, documents, and decisions,
lives in the [`backlog` skill](../../.agents/skills/backlog/SKILL.md) and its
[command reference](../../.agents/skills/backlog/REFERENCE.md). Those files are
the authority on syntax. This guide is about how the records fit into the loop.

## How the loop consumes the backlog

`workloop` does not invent work. `hooks.next_task` in `workloop.toml` is an
ordinary shell command, so the backlog is the queue:

```toml
[hooks]
next_task = "pixi run --locked backlog task list -s 'To Do' --plain | head -n 1"
```

`workloop open` runs that command, records the selected card in
`.workloop/state.json`, and later verbs use it. Two consequences follow, and
both matter more as parallelism grows:

- **Selection is a query, not a reservation.** Two loops started at the same
  moment read the same `To Do` list and can pick the same card. Claim the card
  (`task edit <id> -s "In Progress"`) before work starts, or give each loop an
  explicit scope so it never runs the query at all.
- **The card is the shared contract between agents.** Because the criteria live
  in the card, the implementer, the reviewer, and the gate all read the same
  definition of finished. Nothing depends on a prompt surviving in a chat log.

## Milestones

A milestone is a scope boundary, not a schedule. Keep it small enough that you
can say whether it is complete without reading the whole backlog, and let task
dependencies carry the ordering. The current milestones
(`m-0`, `m-1`, `m-2`) are sized that way: scaffold, then the proxy and the four
verbs, then review modes and self-dogfooding.

## Decision records

Write a decision record when a choice will be expensive to revisit, and link it
from the task that implements it. Records are append-only history. When a
decision changes, add a record that supersedes the old one and leaves the
original intact, so a reader can still see what was believed at the time and
why it stopped being true. `decision-3` is the clearest example: it records the
refusal to generate orchestrator templates, which every later mention of
Archon in this repository depends on.

## Hygiene

- One record per idea. Duplicated cards split attention and rot separately.
- Reference, do not copy. A card points at
  [`docs/architecture/overview.md`](../architecture/overview.md); it does not
  restate the crate split.
- Close with evidence. The final summary names the gate or file that proves each
  criterion.
- Archive, never delete. Cancelled work keeps its identifier so links and
  history stay intelligible.

## See also

- [Using workloop with Archon](archon-integration.md) — how a card becomes a
  workflow run, and where the two tools divide responsibility.
- [Decoupled four-verb lifecycle](../concepts/decoupled-lifecycle.md) — the
  verbs that consume these records.
