# Architecture — team-pipeline

Stack: Python 3.11+, `uv`, Typer (CLI), Jinja2 (templates), `pytest`, `ruff`,
type checker (`mypy` or `pyright`). No DB of our own — Hermes owns the board.

## 1. Module map

```text
src/team_pipeline/
  __init__.py
  cli.py            # Typer app; thin — parses args, calls services, formats output
  config.py         # paths, profile names, defaults, board slug, env reads
  idea.py           # IdeaRecord + normalize(raw|file) -> IdeaRecord  (FR1)
  workflow.py       # Workflow/TaskSpec/Edge models + load("full-sdlc")  (FR2,FR3)
  graph.py          # DAG helpers: topo_sort, validate_acyclic, multi-parent  (FR3)
  kanban_client.py  # wraps `hermes kanban` subprocess; KanbanClient protocol  (FR5)
  roles.py          # ROLES registry: step-key -> RoleContract  (FR4, design §6)
  templates.py      # render(role, IdeaRecord) -> body via Jinja2  (FR9)
  validators.py     # validate(artifact_text, role) -> ValidationResult  (FR10)
  planner.py        # build_plan(idea, workflow) -> Plan (tasks+edges+assignees) (FR7)
  runner.py         # create_pipeline(plan, client) ; status() ; summarize()  (FR5,FR8)
  doctor.py         # preflight checks  (FR11)

templates/          # Jinja2 artifact templates (.md.j2)
  pm_spec.md.j2  ux_design.md.j2  architecture.md.j2  impl_task.md.j2
  senior_dev_review.md.j2  junior_qa_report.md.j2  senior_qa_audit.md.j2
  handoff.md.j2

tests/
  test_idea.py  test_workflow.py  test_graph.py  test_roles.py
  test_templates.py  test_validators.py  test_planner.py
  test_kanban_client.py  test_runner.py  test_cli.py  test_doctor.py
  conftest.py        # FakeKanbanClient fixture, sample IdeaRecord
examples/
  prompt-regression-lab/   # case study: generated_graph.yaml + artifacts
```

## 2. Core data models (Pydantic or dataclasses — lean dataclasses, stdlib)

```python
@dataclass(frozen=True)
class IdeaRecord:
    title: str
    slug: str
    one_line: str
    repo_path: Path | None

@dataclass(frozen=True)
class TaskSpec:
    step_key: str          # "pm","ux","arch","impl","review","fix","jqa","sqa","handoff"
    title_tmpl: str        # "PM spec for {title}"
    profile: str           # "pm-agent" ...
    workspace: str         # "scratch" | "worktree:..." | "dir:..."
    branch: str | None
    template: str          # template filename
    role: str              # validator role key

@dataclass(frozen=True)
class Workflow:
    name: str              # "full-sdlc"
    tasks: tuple[TaskSpec, ...]
    edges: tuple[tuple[str, str], ...]   # (parent_step, child_step)

@dataclass
class PlannedTask:
    spec: TaskSpec
    title: str             # rendered
    body: str              # rendered
    assignee: str
    workspace: str
    idempotency_key: str   # f"pipeline:{slug}:{step_key}"

@dataclass
class Plan:
    idea: IdeaRecord
    tasks: list[PlannedTask]
    edges: list[tuple[str, str]]         # by step_key; resolved to ids at create

@dataclass
class CreatedTask:
    step_key: str
    task_id: str
    title: str
    assignee: str

@dataclass
class ValidationResult:
    ok: bool
    role: str
    missing: list[str]     # missing sections
    evidence_failures: list[str]
```

## 3. KanbanClient boundary (the key seam for TDD)

`kanban_client.py` defines a `Protocol` so tests inject a `FakeKanbanClient`.
This is the dependency-injection point that keeps the whole pipeline testable
without a live board (global CLAUDE.md: real behavior over mocks, DI to stay
testable).

```python
class KanbanClient(Protocol):
    def init(self, board: str) -> None: ...
    def create(self, title: str, *, body: str, assignee: str, parents: list[str],
               workspace: str, branch: str | None, idempotency_key: str,
               skills: list[str], board: str) -> str: ...   # returns task_id
    def link(self, parent_id: str, child_id: str, *, board: str) -> None: ...
    def list(self, *, board: str, root: str | None) -> list[dict]: ...
    def assignees(self) -> list[str]: ...
    def version(self) -> str: ...

class HermesKanbanClient:   # real impl: subprocess + --json parsing
    ...
class FakeKanbanClient:     # records calls, returns deterministic ids "t1","t2"...
    ...
```

**Subprocess contract (HermesKanbanClient):**
- builds `["hermes","kanban", sub, ...]`; always passes `--json` where supported.
- `create` → run, parse stdout JSON, return the id field.
  **UNVERIFIED — A1/R2:** confirm the id key by running one real
  `hermes kanban create "probe" --json` against a scratch board before wiring;
  capture the JSON to `tests/fixtures/create.json` and assert the parser against it.
- non-zero exit → raise `HermesError(cmd, returncode, stderr)`; `runner` surfaces it.
- never shell=True; args as a list (no injection from idea text).

## 4. Idempotency & re-run (FR6, AC2.x)

- `idempotency_key = f"pipeline:{idea.slug}:{step.step_key}"`, passed to every
  `create`. Hermes returns the existing id if a non-archived task with that key
  exists (Evidence: `--idempotency-key` semantics).
- `runner.create_pipeline` is therefore safe to re-run: each `create` is a get-or-
  create; `link` is idempotent if we check existing children first (or tolerate a
  duplicate-link error — verify Hermes behavior; lean: pre-list children, skip
  existing edges).

## 5. Workspace path strategy (resolves design §8 open item)

- Docs roles (`pm,ux,arch,handoff`): `workspace="scratch"`.
- `impl` + `fix`: `workspace="worktree"`, `branch=f"wt/{slug}-impl"` (fix reuses
  the same branch so it edits the same tree).
- `review,jqa,sqa`: `workspace=f"dir:{impl_worktree_path}"` read-only. The impl
  worktree path is **not known until impl runs**, so v1 takes the safe route:
  these roles default to `scratch` and the role prompt instructs them to operate
  against the repo/branch named in the handoff context, OR (preferred, if Hermes
  resolves worktree path deterministically from branch) compute
  `dir:<repo>/.worktrees/wt-<slug>-impl`. **Decision for v1:** use `scratch` +
  explicit branch reference in the task body; revisit `dir:` once the real
  worktree path format is verified (flag as A-level assumption).

## 6. Control flow per command

- `doctor`: `client.version()` → check ≥ expected; `assignees()` → diff against
  required profiles; check required subcommands via `hermes kanban --help`. Print
  checklist; exit non-zero on hard failures.
- `preview`/`--dry-run`: `planner.build_plan` → format table. Uses `FakeKanbanClient`
  semantics implicitly (makes no mutating call). AC3.1 tested by asserting the real
  client is never constructed / no create/link recorded.
- `create`: `doctor` quick check → `build_plan` → `client.init` → create tasks in
  topo order → map step_key→id → link edges → print summary.
- `status`: `client.list(root=...)` → group by step → table.
- `validate`: read file → `validators.validate(text, role)` → print result, exit
  code from `ok`.
- `summarize`: list lane tasks, pull each artifact path, assemble a handoff-style
  digest (read-only).

## 7. Validators design (validators.py)

- Each role has `REQUIRED_SECTIONS: dict[role, list[str]]` (markdown headings,
  matched case-insensitively, tolerant of `#`/`##`).
- Evidence rules (regex), only where they matter:
  - `senior-dev`: `r"\b[\w./-]+\.\w+:\d+"` (a `file:line` citation) must appear ≥1.
  - `junior-qa`: a fenced code block containing command output must appear ≥1.
  - `junior-dev`: changed-files list heading + a fenced block present.
- Returns `ValidationResult`; `ok = not missing and not evidence_failures`.
- Pure function of text → trivially unit-testable (no I/O).

## 8. Workflow definition (workflow.py)

`full-sdlc` is defined in code (a module-level `FULL_SDLC: Workflow`) for v1.
`preview`/`create` can also **export** the resolved plan to
`generated_graph.yaml` for transparency (plan §10). YAML *import* of custom
workflows is future work (NG-ish), not required for ACs.

## 9. Error handling & boundaries

- All external failure surfaces (subprocess, file read, empty idea) raise typed
  errors caught at `cli.py` and rendered as user-facing messages + non-zero exit.
- No secrets handled. Hermes auth/config is Hermes's concern; we only invoke its
  CLI. Document required env (`HERMES_PROFILE` optional) — names only.
- Idea text is never interpolated into a shell string (args list only).

## 10. Mapping requirements → modules

| FR | Module(s) |
|---|---|
| FR1 | idea.py |
| FR2,FR3 | workflow.py, graph.py |
| FR4 | roles.py, planner.py |
| FR5,FR6 | kanban_client.py, runner.py |
| FR7 | planner.py, cli.py |
| FR8 | runner.py |
| FR9 | templates.py |
| FR10 | validators.py |
| FR11 | doctor.py |
| FR12 | workflow.py (workspace field), planner.py |

## 11. Open architecture decisions (resolve while building, test-first)

1. **A1/R2** create `--json` id field — verify, fixture, then implement parser.
2. dataclasses vs Pydantic — start dataclasses (stdlib, simplest); upgrade only if
   validation needs grow.
3. duplicate-`link` behavior — verify; pre-list children to skip existing edges.
4. real worktree path format for `dir:` review/QA — verify before enabling §5
   preferred path; ship `scratch`+branch-reference fallback first.
