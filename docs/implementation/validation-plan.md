# Validation Plan — team-pipeline

Defined BEFORE coding (skill rule). Two layers: (A) validate the **tool** we build;
(B) the **pipeline-level** validators the tool enforces on role artifacts.

## A. Tool validation (commands + gates)

Run from repo root via `uv`:

| Check | Command | Gate |
|---|---|---|
| Unit + integration tests | `uv run pytest -q` | all green; report counts |
| Lint | `uv run ruff check .` | clean |
| Format | `uv run ruff format --check .` | clean |
| Typecheck | `uv run mypy src` (or `pyright`) | clean |
| Build/import | `uv run python -c "import team_pipeline"` | imports |
| CLI smoke | `uv run team-pipeline --help` | lists all commands |
| Preview no-mutation | covered by `test_cli.py` (AC3.1) | zero create/link calls |

### Acceptance-criteria → test traceability
| AC | Test |
|---|---|
| AC1.1–1.3 | test_runner.py::create_pipeline_builds_graph |
| AC1.4 | test_kanban_client.py::nonzero_exit_raises |
| AC2.1–2.2 | test_runner.py::idempotent_rerun |
| AC3.1 | test_cli.py::preview_makes_no_mutating_calls |
| AC4.1 | test_runner.py::status_groups_by_lane |
| AC5.1–5.3 | test_validators.py::* |
| AC6.1 | test_doctor.py::* |

### Real-Hermes integration (R1/A1 mitigation)
- One gated integration test (`@pytest.mark.integration`) that, when `hermes` is
  present, runs `init` + `create --json` + `link` on a throwaway board slug
  (`tp-itest`) and asserts a parseable id + a real dependency edge, then archives.
- CI without Hermes: marker skipped; unit tests fully cover logic via
  FakeKanbanClient. Document the skip in `validation-report.md` (no silent caps).
- Manual acceptance on Baha's machine: `team-pipeline doctor` green;
  `team-pipeline create --idea "Build Prompt Regression Lab"` produces the 9-lane
  graph visible in `hermes dashboard`.

## B. Pipeline-level validators (what the tool checks on artifacts)

These implement plan §13 and design §6 gates. `team-pipeline validate <file>
--role <r>` returns pass / blocked-with-reasons (non-zero exit on blocked).

| Role | Required sections | Evidence rule |
|---|---|---|
| pm | problem, target user, MVP scope, non-goals, user stories, acceptance criteria, risks, definition of done | ≥1 acceptance criterion; ≥1 non-goal |
| ux | user journey, screens, states, accessibility | all 4 states (empty/loading/error/success) named |
| architect | architecture, data model, API/interface, tech choices, security, test strategy, task split | data model present; test strategy names commands |
| junior-dev | summary, tests, command output, changed files, known limitations | fenced command-output block; changed-files list |
| senior-dev | verdict, P0/P1/P2 issues, required fixes | ≥1 `file:line` citation; explicit merge/no-merge |
| junior-qa | test plan, executed tests, defects, repro steps | fenced command-output block; ≥1 negative/edge case |
| senior-qa | coverage audit, gaps, risk level, ship/no-ship | explicit ship/no-ship line |
| release | what was built, how to run, how to test, changed files, known limitations, next steps | run cmd + test cmd present |

Example blocked output (plan §13):
```text
Pipeline validation: BLOCKED (role=pm)
  - missing section: non-goals
  - missing section: definition of done
  - evidence: no acceptance criteria found
```

## C. Definition of "done" for the build
- Layer A all green; counts reported (e.g. "N passed, M skipped").
- Layer B validators demonstrated on the case-study artifacts.
- `validation-report.md` filled with real command output summaries, the integration
  skip status, and residual risks (R1 Hermes version drift, A1 verified or not).
- No "done" claimed from compile/build alone — at least one real `preview` (and,
  on Baha's machine, one real `create`) must have run and been observed.
