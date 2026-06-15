# Repo Engineering Review — team-pipeline (PR #1)

- **Target:** `ZeekrBaha/hermes-ai-software-team-pipeline` PR #1 (`feat/implement-team-pipeline` → `master`)
- **Reviewed at:** 2026-06-14 20:10 local, against PR head `8c901f5`
- **Diff size:** 45 files, +4749 / −0

## About

A Python (uv) Typer CLI, `team-pipeline`, that turns a one-line product idea into a Hermes Kanban
task graph: it renders eight role artifacts (PM, UX, Architect, Junior/Senior Dev, Junior/Senior QA,
Release) from a fixed 9-task `full-sdlc` DAG and creates/links them on a Hermes board via a subprocess
client. 13 source modules, 280 tests.

## Verdict

**Strong, mergeable foundation — not yet ship-ready against a real Hermes.** Code is clean, well-decomposed,
and genuinely TDD-built; all advertised gates pass (280 tests, ruff, mypy). But the two pieces that touch the
real outside world — board selection and the "hermes not installed" path — are wrong, and both slipped through
because tests only exercise the in-memory fake. Fix those two, add CI, then ship.

## What Was Done Well

- **Genuine TDD discipline (not just "has tests").** Commit history shows per-task RED→GREEN with explicit
  fix/refactor follow-ups: `7a3b2dd T7: add HermesError tests (TDD gap)`, `5391780 T3: fix regex bugs`,
  `8efad3a T8: refactor _topo_sort_steps → graph.topo_sort_raw`. 25 behavior-focused test files, 280 tests,
  run in <1s.
- **All claimed gates verified green** (run locally, not trusted from the PR body):
  - `uv run pytest tests/` → **280 passed in 0.98s**
  - `uv run ruff check src/ tests/` → **All checks passed!**
  - `uv run mypy src/` → **Success: no issues found in 13 source files**
- **Security-conscious subprocess use.** `HermesKanbanClient._run` builds `cmd` as a list and calls
  `subprocess.run(cmd, capture_output=True, text=True)` with **no `shell=True`** — no shell-injection surface
  even with attacker-controlled idea text. There is even a regression test asserting it
  (`tests/test_kanban_client.py:254-255` → `assert c.kwargs.get("shell") is not True`).
- **Clean architecture / good progressive disclosure.** Thin CLI (`cli.py` parses + formats only), pure
  planner (`build_plan`), `Protocol` + `FakeKanbanClient` / real `HermesKanbanClient` split, deterministic
  idempotency keys (`pipeline:<slug>:<step>`). Dependency direction flows one way (cli → runner/planner →
  client); no lower layer reaches up.
- **Thoughtful edge handling in `idea.py`**: NFKD unicode transliteration, word-boundary slug truncation at
  40 chars, empty-slug guard (`EmptyIdeaError`).
- **Design docs exist** under `docs/implementation/` (requirements, design, architecture, validation report).

## What Was Done Badly

### High — `--board` is silently dropped against real Hermes (correctness)
`board` is threaded through the whole stack (CLI flag → `runner.create_pipeline(..., board=board)` →
`client.create(..., board=board)`), but the **real** client never forwards it. In
`src/team_pipeline/kanban_client.py` the only use of `board` is inside the **Fake's** recorded call dict
(`kanban_client.py:118`). `HermesKanbanClient.create/init/link/list` build their arg lists without ever
appending `--board`, and `init` ignores its argument entirely:

```python
def init(self, board: str) -> None:
    self._run(["kanban", "init"])          # board unused
# create(): args = ["kanban","create",title,"--body",...,"--json"]  → no --board
```

Effect: `team-pipeline create --board my-board ...` always operates on Hermes' default board. The flag is
advertised in `--help` but has no effect. **Uncaught** because no test asserts `--board` appears in the real
client's subprocess args (the Fake records it, so fake-level tests pass).

### High — `doctor` crashes when hermes is not installed (the case it exists to detect)
`run_doctor` assumes `client.version()` raises `HermesError` when hermes is absent (docstring:
"If that raises HermesError, hermes is absent"), and only catches that:

```python
try:
    hermes_version = client.version()
    hermes_present = True
except HermesError:
    hermes_present = False
```

But the real `HermesKanbanClient.version()` does `subprocess.run([self._hermes, "--version"], ...)` with no
guard. A missing binary raises **`FileNotFoundError`**, not `HermesError`, so `doctor` — the command whose
entire job is to report "✗ hermes not found" — throws an uncaught traceback instead. `test_doctor.py:31-33`
simulates absence by raising `HermesError`, which the real client never does → the real failure mode is
untested. Classic fake-vs-real divergence.

### Medium — no CI enforcement
`.github/` is empty. The Makefile defines `test`/`lint`/`type`, but nothing runs them on PR, so the green
gates depend on the author running them by hand. For a repo whose PR sells "ruff clean, mypy clean, 280
tests," a GitHub Actions workflow running those three on every push is the missing safety net.

### Low — real-client robustness gaps
- `version()` never checks `returncode`; a non-zero exit still returns whatever is on stdout (possibly empty).
- `data["id"]` in `create()` raises a bare `KeyError` if Hermes' JSON lacks `id`; not wrapped in `HermesError`.
  (`json.loads` failures happen to be caught upstream since `JSONDecodeError` subclasses `ValueError`, but
  that's incidental, not designed.)
- In the `create` CLI command, `except FileNotFoundError` is meant for a missing idea file, but would also
  swallow a missing-`hermes` error and mislabel it as a file error.

## README

Exists and is decent for a CLI: Quickstart (prereqs, install, preview/create/validate/doctor), the
`full-sdlc` graph, a role-contract table, a case study, and a Development section. Against the portfolio
numbered-section standard it is **missing**: an explicit Architecture/design overview in the README itself
(it lives only in `docs/implementation/`), a **repo map** (what each of the 13 modules is), tech-stack
rationale, and a **Limitations / Next steps** section — which should name the `--board` and `doctor` gaps
above. Not a UI repo, so no screenshots required. ~8 sections present; content depth is fine, breadth is
short of the standard.

## TDD / Tests

Real TDD evidence, not just test presence: commit log is per-task RED→GREEN with named fix/refactor and an
explicit "TDD gap" backfill. 25 test files covering idea parsing, graph topo-sort, planner, validators,
roles, runner, CLI, doctor, and the real client (via `unittest.mock.patch` on `subprocess.run`). **Coverage
hole:** behaviors that differ between `FakeKanbanClient` and `HermesKanbanClient` are asserted only on the
fake — specifically `--board` forwarding and the missing-binary path — which is exactly where both High bugs
live. Commands run: `uv run pytest tests/` → **280 passed**.

## Lint / Type / CI

- **ruff** configured (`E,F,I`) → `All checks passed!`
- **mypy** configured (non-strict, `ignore_missing_imports`) → `Success: no issues found in 13 source files`
- **CI: none.** No `.github/workflows`. Add one running the three Makefile targets.
- Minor: mypy is `strict = false`; tightening to strict would be cheap on a 13-file codebase.

## Security / Vulnerabilities

- **Confirmed safe:** subprocess calls use list form, **no `shell=True`** (with a guarding test). Idea text
  flowing into `kanban create <title>` cannot inject shell commands.
- **Confirmed:** zero third-party runtime deps beyond `typer` + `jinja2`; small supply-chain surface,
  `uv.lock` committed.
- **Needs runtime verification:** Jinja2 env uses `StrictUndefined` (good) — confirm `autoescape` is not
  relevant here since output is Markdown, not HTML (no XSS surface for a CLI). No secret handling, no network
  calls beyond the local `hermes` subprocess. No `pip-audit`/`uv pip audit` run (not configured); given two
  pinned deps the risk is low.

## How To Improve

1. **Forward `--board`.** Add `--board <board>` to `HermesKanbanClient.create/init/link/list` arg lists, and
   write a test asserting it appears in `subprocess.run`'s args (mirror the existing `shell is not True` test).
2. **Make `doctor` survive a missing binary.** Catch `FileNotFoundError` (or `OSError`) alongside
   `HermesError` in `run_doctor`, and add a real-client test where `subprocess.run` raises `FileNotFoundError`.
3. **Add CI.** One `.github/workflows/ci.yml` running `make test lint type` on push/PR.
4. Harden the real client: check `returncode` in `version()`; wrap `data["id"]` KeyError as `HermesError`;
   narrow the `create` command's `except FileNotFoundError` so a missing `hermes` isn't reported as a file error.
5. Round out the README: add a repo map, a Limitations/Next-steps section, and surface the architecture summary.

## How To Enhance

- **Contract test the fake against the real client** so they cannot drift: one parametrized suite that runs
  the same assertions against `FakeKanbanClient` and a mocked `HermesKanbanClient`. This single change would
  have caught both High bugs.
- Make the workflow DAG data-driven (load from YAML) so `full-sdlc` isn't the only graph; the `--workflow`
  flag already implies pluggability.
- Add `--dry-run` JSON/YAML output (you already emit `generated_graph.yaml` in the case study) so the plan is
  machine-consumable, not just a table.
- Add structured logging around subprocess calls (command + duration + exit code) for observability when
  creating real boards.
- Tighten mypy to `strict = true`.

## Verification

| Check | Command | Result |
|---|---|---|
| Tests | `uv run pytest tests/` | ✅ 280 passed in 0.98s |
| Lint | `uv run ruff check src/ tests/` | ✅ All checks passed! |
| Types | `uv run mypy src/` | ✅ no issues, 13 files |
| Shell-injection guard | inspected `kanban_client.py:_run` + `test_kanban_client.py:254` | ✅ no `shell=True`, tested |
| `--board` forwarding | grep `--board`/`board=` in `kanban_client.py` | ❌ only the Fake records board; real client drops it |
| `doctor` missing-binary | inspected `doctor.run_doctor` + real `version()` | ❌ catches `HermesError` only; real raises `FileNotFoundError` |
| CI | `find .github` | ❌ none configured |
| Dependency audit | not run | ⏭ `uv pip audit` not configured; 2 pinned deps, low risk |

All checks run against a fresh clone of PR head `8c901f5` in a throwaway `/tmp` checkout.
