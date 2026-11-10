---
id: decision-6
title: Archon is a supported supervisor, never a build dependency
date: '2026-11-10'
status: accepted
---

## Context

`decision-3` refused to generate or couple to `.archon/` workflow templates, and
left the question open from the other direction: if a team already runs
[Archon](https://github.com/coleam00/Archon), may `workloop` depend on it?

The two tools overlap at one seam. Archon schedules a YAML graph, gives every
run its own Git worktree, and pauses for human approval. `workloop` owns model
selection, the localhost failover proxy, credential isolation, and the review
policy. Wiring them together is useful: a run that survives an upstream `429`
mid-task and still stops for a human before merging.

The risk is that an integration turns into a dependency. Once `workloop` reads
`.archon/config.yaml`, resolves Archon's provider names, or writes a workflow
file, every Archon upgrade becomes a `workloop` release, and the orchestrator
neutrality that justified `decision-3` is lost one import at a time.

## Decision

Archon is a **supported supervisor** and a **documented integration**, and it is
never a build, runtime, or test dependency.

1. No crate in this workspace links, spawns, or imports Archon. `cargo deny`
   (`unknown-git = "deny"`) already fails the build if that changes.
2. `workloop` reads no Archon configuration and writes no `.archon/` path. The
   only Archon-specific artifacts are prose in
   `docs/guides/archon-integration.md`
   and that guide's illustrative YAML, which is not committed as a workflow.
3. Integration uses only the public surface the four verbs already promise:
   Archon nodes call `workloop open`, `exec`, `verify`, and `close` as shell
   steps, exactly as GitHub Actions or `cron` would.
4. Archon stays one of several supported supervisors. Documentation that names
   it names at least one neutral alternative in the same section.

## Consequences

- **Portability holds.** A team can delete the Archon workflow and keep the
  same `workloop.toml`; a team that never installs Archon loses nothing but the
  scheduler.
- **Upgrades decouple.** An Archon release cannot break `workloop`, because
  nothing in the build or test graph knows Archon exists.
- **The seam is narrow by design.** Features that would only work under Archon,
  such as reading Archon's approval state directly, are out of scope. Approval
  crosses the boundary as a shell exit code or an environment variable, like any
  other hook.
- **Documentation carries the cost.** Because the integration is prose and
  configuration rather than code, the guide must state limits explicitly,
  including which `workloop` verbs are not yet implemented.

## Verification

The claim is checkable without reading this record:

```sh
# No Archon source or dependency anywhere in the workspace
cargo deny check bans sources

# Nothing in the repository is an Archon workflow artifact
git ls-files | grep -c '^\.archon/' || true
```
