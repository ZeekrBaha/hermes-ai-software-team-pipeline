# Research — Hermes Kanban AI Software Team Pipeline

Date: 2026-06-14
Source idea: `~/Desktop/hermes-kanban-ai-software-team-pipeline-plan.md`
Evidence labels: `Evidence` (verified this session), `Repository fact`, `Assumption`.

## 1. User goal

Build a reusable tool that turns **one product idea** into a reviewed, tested,
handoff-ready software project by running it through a role-based Kanban graph of
specialized agents (PM → Designer → Architect → Junior Dev → Senior Reviewer →
Junior QA → Senior QA → Release), where each role checks the previous role's work.

The buildable MVP (decided with user) is a **Python CLI, `team-pipeline`**, that
generates and wires the Hermes Kanban task graph from an idea, plus the role
contracts, artifact templates, and validators that make each lane auditable.

## 2. Audience

- Primary: Baha — runs Hermes/Claude/Codex agents already; wants portfolio-grade
  AI-QA / agentic-SDLC projects, not toy demos.
- Secondary: anyone reading the portfolio repo / case study on agentic SDLC
  orchestration.

## 3. Success criteria

- `team-pipeline create --idea "..."` produces a correct Hermes Kanban graph
  (9 role tasks, correct dependency edges) in one command, re-runnable safely.
- Each role has a strict written contract; downstream roles consume upstream
  artifacts.
- A validator can mark the pipeline `blocked` with specific reasons when an
  artifact is missing required sections / evidence.
- One real idea (Prompt Regression Lab) runs end-to-end through the graph as a
  case study.
- Repo is TDD-built, `uv`-managed, tests + lint + typecheck green.

## 4. Decisions locked (with user, this session)

- **Scope:** Python CLI generator (Phase 3 of the plan) is the build target.
  Phase 1 (manual) and Phase 2 (Hermes skill) become documented usage modes, not
  the code deliverable.
- **Location:** new repo `~/Desktop/llm-ai-projects/hermes-ai-software-team-pipeline/`.
- **UI:** CLI + markdown artifacts only. Uses Hermes's existing dashboard
  (`hermes dashboard` → `http://127.0.0.1:9119/kanban`). No new UI; no
  `design-system.md`.

## 5. Constraints

- **Stack (Constraint):** Python 3.11+, `uv` for env/deps/scripts (per global
  CLAUDE.md — `uv` is first choice). `pytest` for tests. `ruff` lint +
  `mypy`/`pyright` typecheck. Jinja2 for artifact templates. `Typer` or stdlib
  `argparse` for CLI (decision deferred to design — lean Typer for ergonomics,
  fall back to argparse to match Hermes's own argparse style).
  - Overrode skill's default web stack (Next.js/Tailwind): not a web app. Recorded.
- **Hard dependency:** Hermes Kanban CLI. The tool shells out to it; it does not
  reimplement the board.
- **TDD mandatory** (global CLAUDE.md): no production code without a failing test
  first.

## 6. Repository / environment facts (Evidence, verified 2026-06-14)

- `hermes` installed: `/Users/baha/.local/bin/hermes`, **Hermes Agent v0.16.0
  (2026.6.5)**. Project root `/Users/baha/.hermes/hermes-agent`, Python 3.11.15.
  (Note: 489 commits behind upstream — pin behavior to v0.16.0; re-verify flags
  before relying on newer features.)
- `uv` installed: `/Users/baha/.local/bin/uv`.
- Portfolio repos live in `/Users/baha/Desktop/llm-ai-projects/`. Related existing
  repos: `promptlab`, `evalforge-synthetic-dataset-generator`, multiple `eval-*`
  harnesses (good downstream targets / case-study material).

### Hermes Kanban command surface (Evidence — `hermes kanban <sub> --help`)

| Command | Signature (relevant flags) | Use in pipeline |
|---|---|---|
| `init` | `kanban init` | ensure `kanban.db` exists (idempotent) |
| `create` | `create TITLE [--body] [--assignee P] [--parent ID]* [--workspace scratch\|worktree\|worktree:<path>\|dir:<path>] [--branch B] [--skill S]* [--idempotency-key K] [--max-runtime D] [--triage] [--initial-status blocked\|running] [--json]` | create each role task; `--json` returns the new task id |
| `link` | `link PARENT_ID CHILD_ID` | wire dependency edges |
| `assign` | `assign TASK_ID PROFILE` | bind role → Hermes profile |
| `assignees` | `assignees [--json]` | list available profiles for validation |
| `list` | `list [--status ...] [--json] [--sort ...]` | status / progress queries |
| `show` | `show TASK_ID` | inspect a task + comments + events |
| `comment` | `comment ...` | append role audit notes |
| `block` / `unblock` | — | gate a lane on validation failure |
| `dispatch` | `dispatch [--dry-run] [--max N] [--failure-limit N]` | spawn workers for ready tasks |
| `swarm` | `swarm GOAL --worker PROFILE:TITLE[:SKILLS]* --verifier V --synthesizer S [--json]` | optional: parallel review/QA fan-out → verifier → synthesizer |
| `specify` | `specify [TASK_ID\|--all]` | auto-flesh triage tasks into specs |
| `decompose` | `decompose [TASK_ID\|--all]` | auto-split a task into children |

Key implications:
- `create --json` → capture task ids; `--parent` is repeatable (a task can depend
  on multiple parents, e.g. Implementation depends on UX **and** Architecture).
- `--idempotency-key` → re-running `team-pipeline create` for the same idea must
  not duplicate tasks. This is the backbone of safe re-runs.
- `swarm` natively models "parallel workers → verifier → synthesizer" — a possible
  later mapping for the review + QA lanes (flagged as a design option, not MVP).
- `--skill` (repeatable) lets the generator force-load this project's role skill
  into the worker that runs each task.

## 7. Risks and unknowns

- **R1 — Hermes flag drift (Evidence-backed risk):** local Hermes is 489 commits
  behind upstream. Flags/JSON shape may differ across versions. *Mitigation:* pin
  to v0.16.0, capture real `--help` in a fixture, add a `team-pipeline doctor`
  preflight that checks `hermes` version + required subcommands.
- **R2 — JSON output shape (Assumption):** `create --json` field name for the new
  task id is not yet confirmed (likely `id` / `task_id`). *Action:* verify by
  running one real `create --json` against a scratch board before coding
  `kanban_client`. Do NOT hardcode until verified.
- **R3 — Idea quality in → garbage out:** a vague idea yields a vague PM spec.
  *Mitigation:* `team-pipeline preview` shows the planned graph + the idea
  normalization before anything is created; validators enforce acceptance-criteria
  presence downstream.
- **R4 — Role prompt fidelity:** roles may drift (junior dev expands scope, senior
  QA rubber-stamps). *Mitigation:* strict role contracts (Section in design) +
  validators that check for required evidence, not just headings.
- **R5 — Scope creep of the tool itself:** the plan lists Phases 1–4. *Mitigation:*
  MVP = graph generation + role templates + validators + one case study. Dashboard,
  swarm-mapping, multi-board orchestration are explicitly Non-Goals for v1.
- **R6 — Workspace isolation:** dev/QA tasks that edit files need `--workspace
  worktree`. *Action:* design must decide per-role workspace mode (docs roles =
  scratch; dev/fix = worktree; review/QA = read-only on the dev worktree path).

## 9. Hermes CLI Verification (A1/R2/A3)

**Verified 2026-06-14 against Hermes Agent v0.16.0.**

### A1 / R2 — JSON field name for task id

Risk R2 ("task id field unconfirmed") is now resolved.

Running `hermes kanban create "team-pipeline-probe-test" --body "probe" --json` returns:

```json
{
  "id": "t_72bc609c",
  "title": "team-pipeline-probe-test",
  "body": "probe",
  "assignee": null,
  "status": "ready",
  "priority": 0,
  "tenant": null,
  "workspace_kind": "scratch",
  "workspace_path": null,
  "branch_name": null,
  "created_by": "user",
  "created_at": 1781485854,
  "started_at": null,
  "completed_at": null,
  "result": null,
  "skills": [],
  "max_retries": null,
  "session_id": null,
  "workflow_template_id": null,
  "current_step_key": null
}
```

**The task id key is `"id"`, value format `"t_<8-hex-chars>"`.** No `task_id` alias exists in the output.

Fixture saved to `tests/fixtures/create.json`.

### A3 — `hermes kanban link` direction

From `hermes kanban link --help`:

```
usage: hermes kanban link [-h] parent_id child_id
```

Direction: **`link <parent_id> <child_id>`** — parent→child (the child depends on the parent completing first).

Verified live: created `t_3a561769` (parent) and `t_9daec9db` (child), ran `hermes kanban link t_3a561769 t_9daec9db`. Output: `Linked t_3a561769 -> t_9daec9db`. The child's `show` output confirms `parents: t_3a561769`.

**Implication for HermesKanbanClient:** call `link(parent_id, child_id)` — never reversed.

### list --json shape

`hermes kanban list --json` returns a JSON array. Each item has the same fields as `create --json` output (id, title, body, assignee, status, priority, tenant, workspace_kind, workspace_path, branch_name, created_by, created_at, started_at, completed_at, result, skills, max_retries, session_id, workflow_template_id, current_step_key).

Fixture saved to `tests/fixtures/list.json` (trimmed to 1 representative item).

### assignees --json shape

`hermes kanban assignees --json` returns a JSON array:

```json
[
  {
    "name": "default",
    "on_disk": true,
    "counts": { "done": 5 }
  }
]
```

Fields: `name` (string), `on_disk` (bool), `counts` (object mapping status → int).

Fixture saved to `tests/fixtures/assignees.json`.

### Summary of resolved unknowns

| Item | Was | Now |
|---|---|---|
| R2: id field name | Assumption: `id` or `task_id` | **Confirmed: `"id"`** |
| A1: id value format | Unknown | **`"t_<8-hex>"`** |
| A3: link direction | Unknown | **`link <parent_id> <child_id>`** (parent→child) |
| list JSON shape | Unknown | **Array of task objects, same schema as create** |
| assignees JSON shape | Unknown | **Array of `{name, on_disk, counts}` objects** |

## 8. Open questions to resolve in design (not decided here)

1. CLI framework: Typer vs argparse. (Lean Typer; confirm in architecture.)
2. Graph definition format: hardcoded `full-sdlc` workflow vs declarative YAML
   workflow files (plan §10 shows `generated_graph.yaml`). Lean: built-in
   `full-sdlc` workflow in code for v1, YAML export for transparency.
3. Does v1 call `dispatch` itself, or only build the graph and let the user run
   `hermes kanban dispatch` / the daemon? Lean: build-only; dispatch is the user's
   explicit action (safer, less magic).
4. Per-role workspace + model strategy (see `agent-assignments.md`).
