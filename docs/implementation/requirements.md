# Requirements — team-pipeline CLI

Traceability: every requirement has an ID. Tasks (`implementation-plan.md`) and
validation (`validation-plan.md`) reference these IDs. No requirement without a
test.

## Problem statement

A single coding agent given "build X" jumps to code and skips product clarity,
architecture, review, QA, and handoff. `team-pipeline` forces the work through a
durable Hermes Kanban role graph so each stage is produced, checked by the next
role, and validated against a contract — auditable and repeatable.

## Target user

Baha (operator of Hermes + Claude/Codex agents). Runs the CLI locally from a
terminal; watches progress on the Hermes dashboard.

## MVP scope (in)

- **FR1** Normalize a raw idea (string or `--from idea.md`) into a canonical idea
  record (title, slug, one-line, target repo path).
- **FR2** Generate the `full-sdlc` task graph: 9 role tasks with correct titles
  and bodies seeded from role templates.
- **FR3** Wire dependencies as a DAG (see graph in design). Support a task
  depending on multiple parents.
- **FR4** Assign each task to its role profile (`pm-agent`, `ux-designer-agent`,
  `architect-agent`, `junior-dev-agent`, `senior-dev-reviewer`, `junior-qa-agent`,
  `senior-qa-agent`, `release-agent`).
- **FR5** Create the graph via the real Hermes Kanban CLI, capturing task ids.
- **FR6** Be idempotent: re-running `create` for the same idea+board reuses tasks
  (via `--idempotency-key`) instead of duplicating.
- **FR7** `preview` command: print the planned graph (tasks, edges, assignees,
  workspace modes) and the normalized idea **without** touching the board.
- **FR8** `status` command: given a root task id, show each lane's status by
  querying `hermes kanban list --json`.
- **FR9** Per-role artifact templates (Jinja2) rendered into task bodies and/or
  the target repo's `docs/` (e.g. `docs/product/spec.md`).
- **FR10** Validators: check a role artifact for required sections + evidence and
  return pass / blocked-with-reasons. Expose as `team-pipeline validate`.
- **FR11** `doctor` preflight: verify `hermes` is installed, the version, and the
  required subcommands/profiles exist; fail with a clear message otherwise.
- **FR12** Per-role workspace mode: docs roles → `scratch`; implementation/fix →
  `worktree` (+ branch); review/QA → read-only against the dev worktree path.

## Non-goals (out, v1)

- **NG1** No custom web UI / dashboard (use Hermes's existing one).
- **NG2** No reimplementation of the Kanban board, scheduler, or dispatcher.
- **NG3** `team-pipeline` does not itself run `dispatch` or babysit workers in v1;
  it builds the graph and the user runs `hermes kanban dispatch` / the daemon.
- **NG4** No multi-board / multi-tenant orchestration in v1.
- **NG5** No `swarm`-based review/QA fan-out in v1 (documented as a future option).
- **NG6** No automatic merging / PR creation by the tool itself.

## User stories + acceptance criteria

### US1 — Generate a pipeline from an idea
> As Baha, I run one command and get a complete, correctly-wired role graph.

- **AC1.1** `team-pipeline create --idea "Build Prompt Regression Lab" --repo PATH`
  creates 9 tasks assigned to the 8 role profiles (dev appears for both implement
  and fix) with bodies seeded from templates.
- **AC1.2** Dependency edges exactly match the design DAG; PM is the root; Handoff
  is the sink.
- **AC1.3** Command prints a summary table of created task ids + titles.
- **AC1.4** Exit code 0 on success; non-zero with a clear message on any Hermes
  command failure.

### US2 — Safe re-runs
- **AC2.1** Running the same `create` twice does not duplicate tasks (same
  idempotency keys → same ids returned).
- **AC2.2** Partial failure (graph half-created) can be re-run to completion.

### US3 — Preview before committing
- **AC3.1** `preview` prints tasks, edges, assignees, workspace modes, normalized
  idea, and makes **zero** mutating Hermes calls (assert in test via a fake client
  that records calls).

### US4 — Status visibility
- **AC4.1** `status --root-task ID` lists each lane with its current Hermes status
  (triage/todo/ready/running/review/done/blocked).

### US5 — Artifact validation gates
- **AC5.1** `validate docs/product/spec.md --role pm` passes when all required PM
  sections exist (problem, target user, MVP scope, non-goals, acceptance criteria,
  definition of done, risks) and fails listing each missing section.
- **AC5.2** Validators check evidence presence where required (e.g. senior-dev
  review must cite `file:line`; junior QA must include command output blocks).
- **AC5.3** `validate` returns structured result (pass/blocked + reasons) and a
  non-zero exit on blocked.

### US6 — Environment preflight
- **AC6.1** `doctor` reports Hermes presence + version and lists missing required
  profiles; exits non-zero if a hard dependency is absent.

## Definition of done (tool)

- All ACs covered by passing tests (unit + at least one integration test that runs
  against a real scratch Hermes board, or a faithfully-faked client where running
  real Hermes in CI is impractical — decision in validation-plan).
- `ruff`, type checker, `pytest` all green; counts reported.
- README + `docs/` updated; one case study (Prompt Regression Lab) committed under
  `examples/`.
- `doctor` passes on Baha's machine against Hermes v0.16.0.

## Assumptions (must verify before/while coding)

- **A1** `hermes kanban create --json` emits the new task id in a parseable field
  (verify exact key — R2 in research).
- **A2** Role profiles can be created/named in Hermes (`assignees`); if a profile
  is missing, `doctor` flags it and `create` can still proceed with `--assignee`
  by name (Hermes accepts an arbitrary profile name string).
- **A3** `link PARENT CHILD` is the dependency direction the dashboard reads as
  "child blocked until parent done." Verify against one real pair.
