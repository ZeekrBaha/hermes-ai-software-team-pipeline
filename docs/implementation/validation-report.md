# Validation Report — team-pipeline

Date: 2026-06-14
Branch: feat/implement-team-pipeline

## Test Results

```
============================= test session starts ==============================
platform darwin -- Python 3.11.15, pytest-9.1.0, pluggy-1.6.0
rootdir: /Users/baha/Desktop/llm-ai-projects/hermes-ai-software-team-pipeline
configfile: pyproject.toml
collected 280 items
```

All 280 tests passed across all test modules:

- `tests/test_cli.py` (16 tests)
- `tests/test_doctor.py` (23 tests)
- `tests/test_graph.py` (32 tests)
- `tests/test_idea.py` (23 tests)
- `tests/test_kanban_client.py` (26 tests)
- `tests/test_planner.py` (20 tests)
- `tests/test_roles.py` (58 tests)
- `tests/test_runner.py` (30 tests)
- `tests/test_templates.py` (20 tests)
- `tests/test_validators.py` (16 tests)
- `tests/test_workflow.py` (11 tests) + `tests/test_graph.py` (5 extra)

Total: **280 passed, 0 failed, 0 errors** (0.59s)

## Lint (ruff)

```
All checks passed!
```

## Type Check (mypy)

```
Success: no issues found in 13 source files
```

## CLI Smoke Tests

### --help

```
 Usage: team-pipeline [OPTIONS] COMMAND [ARGS]...

 Hermes AI Software Team Pipeline CLI.

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --install-completion          Install completion for the current shell.      │
│ --show-completion             Show completion for the current shell, to copy │
│                               it or customize the installation.              │
│ --help                        Show this message and exit.                    │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Commands ───────────────────────────────────────────────────────────────────╮
│ doctor     Run preflight checks (hermes version + required profiles).        │
│ preview    Preview the pipeline plan — makes zero Hermes calls (AC3.1).      │
│ create     Create the pipeline on Hermes Kanban. Use --dry-run to preview    │
│            only.                                                             │
│ status     Show status table for a pipeline rooted at a task.                │
│ validate   Validate an artifact file against its role contract.              │
│ summarize  Summarize pipeline lanes for a root task.                         │
╰──────────────────────────────────────────────────────────────────────────────╯
```

### preview --idea "Build Prompt Regression Lab"

```
step_key     title                                                assignee               workspace    idempotency_key
---------------------------------------------------------------------------------------------------------------------
pm           PM spec for Build Prompt Regression Lab             pm-agent               scratch      pipeline:build-prompt-regression-lab:pm
ux           UX/product design for Build Prompt Regression Lab   ux-designer-agent      scratch      pipeline:build-prompt-regression-lab:ux
arch         Architecture plan for Build Prompt Regression Lab   architect-agent        scratch      pipeline:build-prompt-regression-lab:arch
impl         Implement MVP for Build Prompt Regression Lab        junior-dev-agent       worktree     pipeline:build-prompt-regression-lab:impl
review       Senior dev review for Build Prompt Regression Lab   senior-dev-reviewer    scratch      pipeline:build-prompt-regression-lab:review
fix          Fix review findings for Build Prompt Regression Lab  junior-dev-agent       worktree     pipeline:build-prompt-regression-lab:fix
jqa          Junior QA test pass for Build Prompt Regression Lab  junior-qa-agent        scratch      pipeline:build-prompt-regression-lab:jqa
sqa          Senior QA audit for Build Prompt Regression Lab      senior-qa-agent        scratch      pipeline:build-prompt-regression-lab:sqa
handoff      Final handoff + README polish for Build Prompt Regression Lab  release-agent  scratch  pipeline:build-prompt-regression-lab:handoff
```

Zero Hermes calls made (AC3.1 verified).

### doctor

```
✓ hermes installed: Hermes Agent v0.16.0 (2026.6.5) · upstream 242e9cae
Project: /Users/baha/.hermes/hermes-agent
Python: 3.11.15
OpenAI SDK: 2.24.0
Update available: 489 commits behind — run 'hermes update'
✗ missing profiles (8):
    - pm-agent
    - ux-designer-agent
    - architect-agent
    - junior-dev-agent
    - senior-dev-reviewer
    - junior-qa-agent
    - senior-qa-agent
    - release-agent

Overall: FAIL
```

Note: `doctor` correctly detects Hermes v0.16.0 and reports the 8 pipeline profiles as missing (they must be created manually). This is expected behavior on a fresh install — the tool works as designed.

## Coverage by Requirement

| FR | Module | Tests | Status |
|---|---|---|---|
| FR1 | idea.py | test_idea.py (23 tests) | ✓ |
| FR2,FR3 | workflow.py, graph.py | test_workflow.py (11), test_graph.py (32) | ✓ |
| FR4 | roles.py | test_roles.py (58) | ✓ |
| FR5,FR6 | kanban_client.py, runner.py | test_kanban_client.py (26), test_runner.py (30) | ✓ |
| FR7 | planner.py, cli.py | test_planner.py (20), test_cli.py (16) | ✓ |
| FR8 | runner.py | test_runner.py status tests | ✓ |
| FR9 | templates.py | test_templates.py (20) | ✓ |
| FR10 | validators.py | test_validators.py (16) | ✓ |
| FR11 | doctor.py | test_doctor.py (23) | ✓ |
| FR12 | workflow.py, planner.py | test_workflow.py, test_planner.py | ✓ |

## Residual Risks

- R1 — Hermes flag drift: local Hermes is 489 commits behind upstream. HermesKanbanClient is pinned to v0.16.0 behavior. Mitigation: `team-pipeline doctor` checks version.
- R2 — Resolved: `create --json` id field confirmed as "id" via real probe (tests/fixtures/create.json).
- R3 — Idea quality in → garbage out: mitigated by validators and preview command.

## Definition of Done

- [x] All ACs covered by passing tests
- [x] ruff clean
- [x] mypy clean
- [x] pytest green
- [x] README + docs/ updated
- [x] One case study committed (examples/prompt-regression-lab/)
- [ ] doctor passes on real Hermes v0.16.0 with required profiles installed (profiles may need to be created manually)
