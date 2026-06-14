# Prompt — Developer (core modules)

You implement the core logic modules of `team-pipeline` test-first.

## Scope (only these, per architecture.md)
`idea.py`, `workflow.py`, `graph.py`, `roles.py`, `templates.py`, `validators.py`,
`planner.py`, `runner.py`, `kanban_client.py`, `doctor.py`. Pure logic before the
subprocess boundary; CLI is a separate task.

## Method (mandatory TDD — global CLAUDE.md)
1. Write ONE failing test for the next behavior. Run it. Watch it fail for the
   right reason.
2. Write the simplest code to pass. Run it. Green.
3. Refactor with tests green. Repeat.

## Rules
- `uv` for everything (`uv run pytest`, `uv add ...`). State if `uv` can't be used.
- Inject `KanbanClient` via the Protocol; tests use `FakeKanbanClient` — no live
  Hermes in unit tests (DI over mocks).
- `HermesKanbanClient` uses an args **list** (never shell=True); idea text is never
  interpolated into a shell string.
- Before implementing the `create --json` parser, verify the real id field against
  `tests/fixtures/create.json` (captured from a real probe). Do not hardcode an
  unverified key.
- Simplest code that passes the ACs — no speculative abstraction, no defensive
  bloat. Match existing style.
- Standard library first; only the deps in `pyproject.toml`.

## Don't
- Don't touch `cli.py` (separate task) or templates' content beyond what tests need.
- Don't add features not tied to an FR/AC.

## Report
Changed files, test counts (passed/failed/skipped), `ruff`+type status, which ACs
the change satisfies, any assumption you had to make.
