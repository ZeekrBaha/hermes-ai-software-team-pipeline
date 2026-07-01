# team-pipeline

> **Archived (2026-07-01):** this repo's role graph and Hermes Kanban dependency
> have been ported into
> [agent-fleet-orchestrator](https://github.com/ZeekrBaha/agent-fleet-orchestrator)'s
> `fleet/pipeline/` module, running on that project's own spawn/evidence/merge
> APIs instead of Hermes Kanban. See `docs/implementation/pipeline-consolidation/`
> in that repo for the full port spec and history. No further work is planned here.

A Python CLI that turns a product idea into a complete, reviewed Hermes Kanban role graph — PM → UX → Architect → Junior Dev → Senior Dev Review → Fix → Junior QA → Senior QA → Release.

## Quickstart

### Prerequisites

- Python 3.11+
- [uv](https://github.com/astral-sh/uv)
- Hermes Kanban v0.16.0+

### Install

```bash
git clone <repo> && cd hermes-ai-software-team-pipeline
uv sync
```

### Preview a pipeline (dry-run, no Hermes needed)

```bash
uv run team-pipeline preview --idea "Build Prompt Regression Lab"
```

Output:

```
step_key  title                                               assignee              workspace  idempotency_key
pm        PM spec for Build Prompt Regression Lab             pm-agent              scratch    pipeline:build-prompt-regression-lab:pm
ux        UX/product design for Build Prompt Regression Lab  ux-designer-agent     scratch    pipeline:build-prompt-regression-lab:ux
arch      Architecture plan for Build Prompt Regression Lab  architect-agent       scratch    pipeline:build-prompt-regression-lab:arch
impl      Implement MVP for Build Prompt Regression Lab       junior-dev-agent      worktree   pipeline:build-prompt-regression-lab:impl
review    Senior dev review for Build Prompt Regression Lab  senior-dev-reviewer   scratch    pipeline:build-prompt-regression-lab:review
fix       Fix review findings for Build Prompt Regression Lab junior-dev-agent     worktree   pipeline:build-prompt-regression-lab:fix
jqa       Junior QA test pass for Build Prompt Regression Lab junior-qa-agent      scratch    pipeline:build-prompt-regression-lab:jqa
sqa       Senior QA audit for Build Prompt Regression Lab    senior-qa-agent       scratch    pipeline:build-prompt-regression-lab:sqa
handoff   Final handoff + README polish for Build Prompt...  release-agent         scratch    pipeline:build-prompt-regression-lab:handoff
```

### Create a pipeline on Hermes Kanban

```bash
uv run team-pipeline create --idea "Build Prompt Regression Lab" --repo /path/to/repo
```

### Validate an artifact

```bash
uv run team-pipeline validate docs/product/spec.md --role pm
```

### Run preflight check

```bash
uv run team-pipeline doctor
```

## The full-sdlc Graph

The idea traverses 9 nodes connected by 9 directed edges. The PM step fans out to UX and Architecture in parallel; both converge into Implementation before proceeding linearly through review, QA, and release.

```
         ┌──> ux ──────┐
pm ──────┤              ├──> impl ──> review ──> fix ──> jqa ──> sqa ──> handoff
         └──> arch ─────┘
```

Each node is a Hermes Kanban task assigned to a dedicated agent profile. Edges encode the `depends_on` relationship — a task cannot start until every parent is resolved.

## Role Contracts

| Role | Profile | Must Produce | Evidence Required |
|---|---|---|---|
| PM | `pm-agent` | Problem statement, target user, MVP scope, non-goals, user stories, acceptance criteria, risks, DoD | — |
| UX | `ux-designer-agent` | User journey, screen list, wireframes, a11y notes | — |
| Architect | `architect-agent` | Architecture overview, data model, APIs, module structure, tech choices, security notes, test strategy, task breakdown | — |
| Junior Dev | `junior-dev-agent` | Code + tests, known limitations, changed-files list | Test output block, changed-files list |
| Senior Dev | `senior-dev-reviewer` | Verdict (ship / revise), issues by priority (P0/P1/P2), required fixes | ≥ 1 `file:line` citation per P0/P1 |
| Junior QA | `junior-qa-agent` | Test plan, defect list | Command output block |
| Senior QA | `senior-qa-agent` | Coverage audit, gaps, risk level | Ship / no-ship line |
| Release | `release-agent` | What was built, how to run, how to test, changed files, next steps | Run + test commands |

## Case Study: Prompt Regression Lab

See [`examples/prompt-regression-lab/`](examples/prompt-regression-lab/) for a complete plan output including all 9 task definitions and 9 edges.

The graph YAML was generated with:

```bash
uv run team-pipeline preview --idea "Build Prompt Regression Lab"
```

## Architecture

The CLI is a thin coordinator over six pure-Python layers:

```
cli.py          # Typer commands — parses args, calls services, formats output
├── planner.py  # build_plan(idea, workflow) → Plan  [pure, no I/O]
├── runner.py   # create_pipeline(plan, client) → list[CreatedTask]
├── doctor.py   # run_doctor(client) → DoctorResult
└── validators.py  # validate(text, role) → ValidationResult  [pure]

idea.py         # normalize_string / normalize_file → IdeaRecord
workflow.py     # FULL_SDLC Workflow + load(name)
graph.py        # topo_sort_raw, topo_sort, validate_acyclic, parents
roles.py        # ROLES registry: 8 RoleContracts with required sections + evidence rules
templates.py    # render(role, idea) → str  via Jinja2
kanban_client.py # KanbanClient Protocol + FakeKanbanClient + HermesKanbanClient
config.py       # paths, profile names, defaults (stub)
```

**Key seam:** `KanbanClient` is a `Protocol`; tests inject `FakeKanbanClient` (idempotent, records calls). `HermesKanbanClient` wraps the real `hermes kanban` subprocess using args lists (no `shell=True`).

**Tech stack:** Python 3.11+, uv, Typer, Jinja2, pytest, ruff, mypy. Zero custom DB — Hermes owns the board.

## Limitations & Next Steps

- **Hermes profiles must be pre-created** — `doctor` flags missing ones but cannot create them automatically.
- **Single-board only** — `--board` is forwarded to Hermes but Hermes v0.16.0 is effectively single-tenant in practice; multi-board orchestration is a non-goal for v1.
- **No auto-dispatch** — the tool builds the graph; run `hermes kanban dispatch` to start workers.
- **YAML workflow import** — `full-sdlc` is hardcoded; the `--workflow` flag is a stub for future pluggable DAGs.
- **Review/QA workspace** — reviewer and QA roles default to `scratch`; wiring them to the impl worktree path (`dir:<path>`) requires verifying Hermes worktree path resolution at create-time.

## Development

```bash
make test   # uv run pytest tests/ -v
make lint   # uv run ruff check src/ tests/
make type   # uv run mypy src/
```
