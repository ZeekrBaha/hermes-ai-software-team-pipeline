# Design — team-pipeline CLI (UX + role contracts)

No GUI. "UX" here = command surface, output shapes, states, and the strict role
contracts that make the pipeline auditable. Reviewer pass at the bottom.

## 1. Command surface

```text
team-pipeline doctor
team-pipeline preview   --idea "<text>" | --from idea.md  [--workflow full-sdlc]
team-pipeline create    --idea "<text>" | --from idea.md  --repo <path>
                        [--workflow full-sdlc] [--board <slug>] [--dry-run]
team-pipeline status    --root-task <id> [--board <slug>]
team-pipeline validate  <artifact.md> --role <pm|ux|architect|junior-dev|
                        senior-dev|junior-qa|senior-qa|release>
team-pipeline summarize --root-task <id>      # collate lane artifacts → handoff view
```

`--dry-run` on `create` = same as `preview` but in the create code path (records
intended Hermes calls, makes none). Used by tests.

## 2. Primary flow (create)

```text
idea (string|file)
  → normalize        → IdeaRecord{title, slug, one_line, repo_path}
  → load workflow    → Workflow{tasks[], edges[]}   (full-sdlc, declarative)
  → render bodies    → each TaskSpec.body from role template + IdeaRecord
  → preview/confirm  → print graph table
  → kanban_client:
       init board
       for task in topo_order(tasks):
           id = create(title, body, assignee, workspace, branch, idem_key, skills)
       for (parent, child) in edges:
           link(parent_id, child_id)
  → print summary table {step, task_id, assignee, status}
```

## 3. The full-sdlc graph (DAG)

Nodes (step-key → role profile → workspace):

| Step | Title | Profile | Workspace |
|---|---|---|---|
| `pm` | PM spec for `<P>` | `pm-agent` | scratch |
| `ux` | UX/product design for `<P>` | `ux-designer-agent` | scratch |
| `arch` | Architecture plan for `<P>` | `architect-agent` | scratch |
| `impl` | Implement MVP for `<P>` | `junior-dev-agent` | worktree (`wt/<slug>-impl`) |
| `review` | Senior dev review for `<P>` | `senior-dev-reviewer` | dir:`<impl worktree>` (read-only) |
| `fix` | Fix review findings for `<P>` | `junior-dev-agent` | worktree (same branch) |
| `jqa` | Junior QA test pass for `<P>` | `junior-qa-agent` | dir:`<impl worktree>` |
| `sqa` | Senior QA audit for `<P>` | `senior-qa-agent` | dir:`<impl worktree>` (read-only) |
| `handoff` | Final handoff + README polish for `<P>` | `release-agent` | scratch |

Edges (parent → child = child waits for parent):

```text
pm → ux
pm → arch
ux  → impl
arch → impl
impl → review
review → fix
fix → jqa
jqa → sqa
sqa → handoff
```

This matches plan §6.2 / §15. `ux` and `arch` run in parallel after `pm`; both
gate `impl`. (FR3: `impl` has two parents → two `--parent` flags.)

ASCII:

```text
            ┌──> ux ──┐
pm ──┤              ├──> impl ──> review ──> fix ──> jqa ──> sqa ──> handoff
            └──> arch ┘
```

## 4. Output states (every command designs all states)

- **Success:** summary table + green status line + exit 0.
- **Empty:** `status` on a root with no children → "no lanes found for <id>".
- **Loading/long:** `create` prints each step as it is created (streamed), so a
  slow Hermes call is visibly progressing.
- **Error:** any `hermes` non-zero exit → surface the stderr verbatim, the failing
  step, and a remediation hint; exit non-zero. Never swallow Hermes errors.
- **Blocked (validate):** list each failed check with the missing section/evidence;
  exit non-zero.
- **Partial (create):** if a step fails mid-graph, already-created task ids are
  printed so a re-run (idempotent) resumes cleanly.

## 5. Idea normalization rules

- `title`: from `--idea` first sentence or idea.md H1.
- `slug`: kebab-case of title, ascii, ≤ 40 chars.
- `one_line`: first line / explicit `> pitch` if present.
- `repo_path`: `--repo` required for `create`; optional for `preview`.
- Reject empty idea with a clear error (edge case: whitespace-only).

## 6. Role contracts (the heart of the pipeline)

Each contract = **Must produce** (required artifact sections) + **Must not** +
**Consumes** (upstream artifact) + **Gate** (validator checks). Validators in
`validate` enforce the "Must produce" + evidence rules.

### PM (`pm-agent`) → `docs/product/spec.md`
- Consumes: raw idea.
- Must produce: Problem · Target user · MVP scope · Non-goals · User stories ·
  Acceptance criteria · Risks & assumptions · Definition of done.
- Must not: write code; pick tech stack prematurely (unless idea demands it).
- Gate: all 8 sections present; ≥1 acceptance criterion; ≥1 non-goal.

### UX Designer (`ux-designer-agent`) → `docs/design/ux-plan.md`
- Consumes: PM spec.
- Must produce: User journey · Page/screen list · Wireframe descriptions ·
  Empty/loading/error/success states for each screen · Accessibility notes.
- Must not: add product scope beyond the PM spec.
- Gate: every PM user story maps to ≥1 screen/flow; all four states named.

### Architect (`architect-agent`) → `docs/architecture.md`
- Consumes: PM spec + UX plan.
- Must produce: System architecture · Data model · API/interface boundaries ·
  Module structure · Tech choices (+ rationale) · Security considerations ·
  Test strategy · Implementation task split.
- Must not: implement before spec/design approved.
- Gate: data model present; each acceptance criterion maps to ≥1 planned task;
  test strategy names concrete commands.

### Junior Developer (`junior-dev-agent`) → code + `docs/impl-notes.md`
- Consumes: spec + UX + architecture.
- Must produce: code changes · tests (test-first) · basic docs · real command
  output (test run) · known limitations.
- Must not: skip tests; expand scope beyond the task; broad unrelated edits.
- Gate: tests exist and were run (command output block present); changed-files
  list present.

### Senior Dev Reviewer (`senior-dev-reviewer`) → `docs/reviews/senior-dev-review.md`
- Consumes: implementation diff + acceptance criteria.
- Must produce: verdict (merge/no-merge) · P0/P1/P2 issue list · required fixes ·
  evidence citations as `file:line`.
- Must not: modify files (read-only review).
- Gate: ≥1 `path:line` citation; explicit merge/no-merge line; each issue tagged
  P0/P1/P2.

### Junior QA (`junior-qa-agent`) → `docs/qa/junior-qa-report.md`
- Consumes: fixed implementation.
- Must produce: test plan · executed tests (happy/negative/edge/regression) ·
  defect list · repro steps · real command output / evidence.
- Must not: accept self-reported success without running it.
- Gate: command-output block present; ≥1 negative/edge case listed.

### Senior QA (`senior-qa-agent`) → `docs/qa/senior-qa-audit.md`
- Consumes: junior QA report + implementation.
- Must produce: coverage audit · gaps · risk level · additional tests required ·
  ship/no-ship recommendation.
- Must not: rubber-stamp; must verify junior QA evidence is real.
- Gate: explicit ship/no-ship line; references junior QA findings by item.

### Release (`release-agent`) → `docs/handoff.md`
- Consumes: all prior artifacts.
- Must produce: what was built · how to run · how to test · changed files · known
  limitations · next steps · portfolio README notes.
- Gate: run command + test command present; changed-files list present; real paths.

## 7. CLI framework decision

**Typer** (Click-based) for ergonomics (typed params, auto `--help`, subcommands).
Fallback: stdlib `argparse` to mirror Hermes's own style if Typer adds friction.
Either way the CLI layer is thin — all logic lives in testable modules, so the
framework choice does not affect the core tests.

## 8. Reviewer pass (pre-implementation critique of THIS design)

- **Caught — multi-parent edge:** `impl` depends on both `ux` and `arch`. Confirmed
  `create --parent` is repeatable (research Evidence) → representable. ✓
- **Caught — read-only roles need a path:** review/QA must point at the dev's
  worktree. Design uses `--workspace dir:<impl worktree path>`. Requires capturing
  the impl task's resolved worktree path → `kanban_client` must surface it (the
  `claim` command "prints resolved workspace path"; for build-time we set
  `dir:` explicitly from the branch/path we chose). Risk noted → architecture must
  define how the impl worktree path is computed deterministically from the slug.
- **Caught — idempotency key scheme:** key = `pipeline:<slug>:<step-key>`. Stable
  across re-runs, unique per step. Documented in architecture.
- **Open — validators vs heading-only gaming:** heading presence is weak. v1 gates
  add evidence checks (file:line regex, fenced command-output block presence) on
  the roles where it matters most (dev, review, QA). Accepted as good-enough for
  v1; deeper semantic checks are future work.
- **Open — dispatch ownership:** confirmed build-only (NG3). Design does not call
  dispatch. ✓
