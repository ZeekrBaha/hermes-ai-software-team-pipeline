"""CLI entry point — thin layer: parse args, call services, format output."""
from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Optional

import typer

import team_pipeline.validators as _validators
from team_pipeline.doctor import format_doctor_result, run_doctor
from team_pipeline.idea import (
    EmptyIdeaError,
    IdeaRecord,
    normalize_file,
    normalize_string,
)
from team_pipeline.kanban_client import HermesError, HermesKanbanClient
from team_pipeline.planner import Plan, build_plan
from team_pipeline.runner import (
    create_pipeline,
)
from team_pipeline.runner import (
    status as _runner_status,
)
from team_pipeline.runner import (
    summarize as _runner_summarize,
)
from team_pipeline.workflow import load as load_workflow

app = typer.Typer(help="Hermes AI Software Team Pipeline CLI.")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _parse_idea(
    idea: Optional[str],
    from_file: Optional[Path],
    *,
    repo_path: Optional[Path] = None,
) -> IdeaRecord:
    """Parse idea from --idea text or --from file.

    Raises EmptyIdeaError if neither is provided or the text is empty.
    Raises FileNotFoundError if from_file does not exist.
    """
    if idea is not None:
        return normalize_string(idea, repo_path=repo_path)
    if from_file is not None:
        return normalize_file(from_file, repo_path=repo_path)
    raise EmptyIdeaError("Provide --idea <text> or --from <file>.")


def _print_plan_table(plan: Plan) -> None:
    """Print a formatted table of planned tasks to stdout."""
    header = (
        f"{'step_key':<12} {'title':<38} "
        f"{'assignee':<22} {'workspace':<12} idempotency_key"
    )
    separator = "-" * 105
    rows = [
        (
            f"{t.spec.step_key:<12} {t.title:<38} "
            f"{t.assignee:<22} {t.workspace:<12} {t.idempotency_key}"
        )
        for t in plan.tasks
    ]
    typer.echo("\n".join([header, separator, *rows]))


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


@app.command()
def doctor() -> None:
    """Run preflight checks (hermes version + required profiles)."""
    client = HermesKanbanClient()
    result = run_doctor(client)
    typer.echo(format_doctor_result(result))
    if not result.ok:
        raise typer.Exit(1)


@app.command()
def preview(
    idea: Optional[str] = typer.Option(None, "--idea", help="Raw idea text"),
    from_file: Optional[Path] = typer.Option(None, "--from", help="Idea markdown file"),
    workflow: str = typer.Option("full-sdlc", "--workflow", help="Workflow name"),
) -> None:
    """Preview the pipeline plan — makes zero Hermes calls (AC3.1)."""
    try:
        idea_record = _parse_idea(idea, from_file)
        wf = load_workflow(workflow)
        plan = build_plan(idea_record, wf)
        _print_plan_table(plan)
    except (EmptyIdeaError, ValueError) as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(1)
    except FileNotFoundError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(1)


@app.command()
def create(
    idea: Optional[str] = typer.Option(None, "--idea", help="Raw idea text"),
    from_file: Optional[Path] = typer.Option(None, "--from", help="Idea markdown file"),
    repo: Optional[Path] = typer.Option(None, "--repo", help="Repository path"),
    workflow: str = typer.Option("full-sdlc", "--workflow", help="Workflow name"),
    board: str = typer.Option("team-pipeline", "--board", help="Kanban board slug"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview only, no calls"),
) -> None:
    """Create the pipeline on Hermes Kanban. Use --dry-run to preview only."""
    try:
        idea_record = _parse_idea(idea, from_file, repo_path=repo)
        wf = load_workflow(workflow)
        plan = build_plan(idea_record, wf)
    except (EmptyIdeaError, ValueError) as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(1)
    except FileNotFoundError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(1)

    if dry_run:
        _print_plan_table(plan)
        return

    try:
        client = HermesKanbanClient()
        created = create_pipeline(plan, client, board=board)
        typer.echo(_runner_summarize(created))
    except HermesError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(1)


@app.command()
def status(
    root_task: str = typer.Option(..., "--root-task", help="Root task ID"),
    board: str = typer.Option("team-pipeline", "--board", help="Kanban board slug"),
) -> None:
    """Show status table for a pipeline rooted at a task."""
    try:
        client = HermesKanbanClient()
        tasks = _runner_status(client, root=root_task, board=board)
        if not tasks:
            typer.echo("(no tasks found)")
            return
        header = f"{'id':<12} {'lane':<12} {'assignee':<22} title"
        separator = "-" * 70
        rows = [
            (
                f"{t.get('id', ''):<12} {t.get('lane', ''):<12} "
                f"{t.get('assignee', ''):<22} {t.get('title', '')}"
            )
            for t in tasks
        ]
        typer.echo("\n".join([header, separator, *rows]))
    except HermesError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(1)


@app.command()
def validate(
    artifact: Path = typer.Argument(..., help="Path to the artifact markdown file"),
    role: str = typer.Option(..., "--role", help="Role key (pm|ux|architect|...)"),
) -> None:
    """Validate an artifact file against its role contract."""
    try:
        if not artifact.exists():
            raise FileNotFoundError(f"File not found: {artifact}")
        text = artifact.read_text()
        result = _validators.validate(text, role)
        if result.ok:
            typer.echo(f"OK — {role} artifact passes all checks.")
        else:
            if result.missing:
                missing = ", ".join(result.missing)
                typer.echo(f"FAIL — missing sections: {missing}")
            if result.evidence_failures:
                failures = ", ".join(result.evidence_failures)
                typer.echo(f"FAIL — evidence failures: {failures}")
            raise typer.Exit(1)
    except FileNotFoundError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(1)
    except ValueError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(1)


@app.command()
def summarize(
    root_task: str = typer.Option(..., "--root-task", help="Root task ID"),
) -> None:
    """Summarize pipeline lanes for a root task."""
    try:
        client = HermesKanbanClient()
        tasks = _runner_status(client, root=root_task, board="team-pipeline")
        if not tasks:
            typer.echo("(no tasks found)")
            return
        lanes: dict[str, list[str]] = defaultdict(list)
        for t in tasks:
            lane = t.get("lane", "unknown")
            lanes[lane].append(t.get("title", ""))
        for lane, titles in lanes.items():
            typer.echo(f"[{lane}] {len(titles)} task(s): {', '.join(titles)}")
    except HermesError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(1)
