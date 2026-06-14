# Implementation Plan — team-pipeline

TDD mandatory (global CLAUDE.md): each task is RED → GREEN → REFACTOR. No
production code before a failing test. Tasks are small, ordered by dependency,
each with acceptance criteria + tests + rollback. Build inside-out: pure logic
first, subprocess boundary last, CLI on top.

## Task 0 — Repo scaffold (no business logic)
- Steps: `uv init`; add deps (`typer`, `jinja2`, dev: `pytest`, `ruff`, type
  checker); create `src/team_pipeline/`, `tests/`, `templates/`; `pyproject.toml`
  with scripts; `Makefile` (`make test/lint/type`); `.gitignore`.
- AC: `uv run pytest` runs (collects 0), `ruff` + type checker run clean on empty
  package. Reportable counts.
- Tests: a trivial `test_smoke.py` importing the package.
- Rollback: delete repo dir.
- Note: scaffold/config is the allowed TDD exception (global CLAUDE.md).

## Task 1 — IdeaRecord + normalize (FR1, US-edge cases)
- RED: `test_idea.py` — title/slug/one_line from string; from `idea.md` H1;
  empty/whitespace idea raises; slug kebab+ascii+≤40.
- GREEN: `idea.py`.
- AC: AC for FR1; rejects empty idea.

## Task 2 — Workflow model + full-sdlc + graph (FR2, FR3)
- RED: `test_workflow.py` (9 tasks, right profiles/workspaces), `test_graph.py`
  (topo_sort order valid, acyclic check, `impl` has parents {ux,arch}).
- GREEN: `workflow.py`, `graph.py`.
- AC: AC1.2 edges match design DAG exactly; multi-parent represented.

## Task 3 — Roles registry + contracts (FR4)
- RED: `test_roles.py` — every step_key maps to a RoleContract with required
  sections matching design §6; profiles match the 8 names.
- GREEN: `roles.py`.

## Task 4 — Templates (FR9)
- RED: `test_templates.py` — render(pm, idea) contains all required PM headings +
  idea title injected; each role template renders non-empty with required headings.
- GREEN: `templates.py` + 8 `.md.j2` files.
- AC: rendered bodies carry the role's "Must produce" headings so downstream
  validators can pass on a properly-filled artifact.

## Task 5 — Validators (FR10, US5)
- RED: `test_validators.py` — PM passes with all sections, fails listing each
  missing one; senior-dev fails without a `file:line`; junior-qa fails without a
  command block; `ok` reflects both section + evidence checks.
- GREEN: `validators.py`.
- AC: AC5.1, AC5.2, AC5.3.

## Task 6 — Planner / build_plan (FR7, FR12)
- RED: `test_planner.py` — build_plan(idea, full_sdlc) → 9 PlannedTasks with
  rendered titles/bodies, correct assignees, workspace modes, idempotency keys
  `pipeline:<slug>:<step>`; edges by step_key preserved.
- GREEN: `planner.py`.
- AC: AC3.1 groundwork (pure, no I/O).

## Task 7 — KanbanClient: Fake + Protocol (FR5 seam)
- RED: `conftest.py` FakeKanbanClient (records calls, returns t1..tN);
  `test_runner.py` uses it.
- GREEN: `kanban_client.py` Protocol + FakeKanbanClient.

## Task 8 — Runner: create_pipeline (FR5, FR6, US1, US2)
- RED: `test_runner.py` — create_pipeline(plan, fake) creates tasks in topo order
  with right args; links exactly the design edges; second run with same idem keys
  creates no duplicates (fake honors idempotency); returns CreatedTask list;
  partial-failure re-run resumes.
- GREEN: `runner.py` create_pipeline + status + summarize.
- AC: AC1.1–1.4, AC2.1–2.2, AC4.1.

## Task 9 — HermesKanbanClient (real subprocess) (FR5)
- **Pre-step (verify A1/R2/A3):** run real `hermes kanban init` + `create --json`
  on a throwaway board; save JSON to `tests/fixtures/create.json`; confirm id key,
  link direction, duplicate-link behavior. Record findings in research.md.
- RED: `test_kanban_client.py` — parser maps the fixture JSON → task_id; arg
  builder produces expected argv (incl. repeated `--parent`, `--idempotency-key`,
  `--workspace`); non-zero exit raises HermesError.
- GREEN: `HermesKanbanClient` (subprocess, args-list, JSON parse).
- AC: AC1.4 error surfacing.

## Task 10 — doctor (FR11, US6)
- RED: `test_doctor.py` — reports version, flags missing profiles, exits non-zero
  when hermes absent (inject a fake "which/version" provider).
- GREEN: `doctor.py`.
- AC: AC6.1.

## Task 11 — CLI wiring (Typer) (all FRs surfaced)
- RED: `test_cli.py` (Typer CliRunner) — `preview` makes zero mutating calls
  (AC3.1, assert via fake), prints graph table; `create --dry-run` same; `validate`
  exit codes; `status` table; `--help` lists commands.
- GREEN: `cli.py`.
- AC: AC3.1 fully; command surface from design §1.

## Task 12 — Case study (examples/prompt-regression-lab) + docs
- Run `team-pipeline preview --idea "Build Prompt Regression Lab"` →
  `generated_graph.yaml`; optionally `create` against a real scratch board and
  capture the dashboard screenshot.
- Write README (quickstart, the graph diagram, role contracts table), update
  `docs/`.
- AC: DoD — one idea visibly traverses the graph; README portfolio-ready.

## Task 13 — Validation report
- Run full suite: `make test lint type`; fill `validation-report.md` with command
  output summaries, counts, skipped checks, residual risks (R1 Hermes drift).

## Build order / dependencies
```text
T0 → T1 → T2 → T3 → T4 → T5 → T6 → T7 → T8 → T9 → T10 → T11 → T12 → T13
                         (T4,T5 independent of T3 ordering; keep sequential for clarity)
```

## Per-task definition of done
- New/changed tests green; full suite green; `ruff` + type checker clean.
- Report changed files + command output in the task's completion note.
- No scope expansion beyond the task's ACs.
