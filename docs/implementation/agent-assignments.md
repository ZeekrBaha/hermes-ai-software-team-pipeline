# Agent Assignments — Hermes profiles, models, tools, workspaces

How the 9 pipeline tasks map to Hermes profiles, what model/tooling strategy each
should use, and the workspace/permission posture. Set via
`hermes kanban assign <task_id> <profile>` (or `--assignee` at create).

`doctor` checks these profiles exist (`hermes kanban assignees --json`); missing
ones are flagged. Hermes accepts an arbitrary profile-name string at create time,
so the pipeline still builds if a profile is not pre-registered — but assignment
is cleaner when profiles exist.

| Step | Profile | Model tier (strategy) | Tools / posture | Workspace | Writes files? |
|---|---|---|---|---|---|
| pm | `pm-agent` | strong reasoning (Opus-class) | docs only | scratch | docs artifact only |
| ux | `ux-designer-agent` | strong reasoning/design | docs; optional browse for refs | scratch | docs artifact only |
| arch | `architect-agent` | strong reasoning/coding (Opus-class) | read repo, docs | scratch | docs artifact only |
| impl | `junior-dev-agent` | capable coding (Sonnet/Opus) | edit files, run tests | worktree `wt/<slug>-impl` | YES (code+tests) |
| review | `senior-dev-reviewer` | strong code-review | **read-only** | scratch / dir:(impl tree) | no (review doc only) |
| fix | `junior-dev-agent` | coding | edit files, run tests | worktree (same branch) | YES |
| jqa | `junior-qa-agent` | coding + test runner | run tests/CLI, capture output | dir:(impl tree) / scratch | tests + report |
| sqa | `senior-qa-agent` | strict verification | **read-only**, inspection-first | scratch / dir:(impl tree) | audit doc only |
| handoff | `release-agent` | docs/summary | docs | scratch | handoff doc only |

## Permission posture rationale
- Reviewer + Senior QA are **read-only by default** (design + plan §8/§12.5): they
  must not "fix" code; they cite and recommend. Enforced by profile config and by
  the role prompt ("Must not modify files").
- Implementation + fix run in a **git worktree** for isolation (plan §9). Fix reuses
  the impl branch so the diff accumulates on one branch.
- Docs roles use `scratch` (no repo mutation needed).

## Model strategy notes (plan §8, adapt to availability)
- PM / Architect: prioritize reasoning quality — these set the foundation; cheap
  models here cost more downstream.
- Junior Dev / Fix: capable coding model that follows scope tightly.
- Senior Dev Reviewer / Senior QA: strong critical models; their value is catching
  what the junior missed — do not under-provision.
- These are **defaults**, overridable per Hermes profile config. The pipeline does
  not hardcode model names; it assigns profiles and lets profile config pick models.

## Skills force-loaded per worker (FR: `create --skill`)
- Each role task is created with `--skill <role-skill>` so the worker loads this
  project's role contract at runtime (built-in `kanban-worker` skill + role skill).
  v1: a single `team-pipeline-roles` skill carrying all contracts is acceptable;
  per-role skills are a later refinement.

## Future option — swarm mapping (NG5, documented not built)
The review+QA stages could map to `hermes kanban swarm GOAL --worker
senior-dev-reviewer:... --worker junior-qa-agent:... --verifier senior-qa-agent
--synthesizer release-agent`, getting parallel review/QA → verifier → synthesizer
natively. Deferred from v1 to keep the graph explicit and debuggable.
