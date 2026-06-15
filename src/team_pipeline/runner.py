"""Pipeline runner — create tasks in topo order, link edges."""
from __future__ import annotations

from dataclasses import dataclass

from team_pipeline.graph import topo_sort_raw
from team_pipeline.kanban_client import KanbanClient
from team_pipeline.planner import Plan


@dataclass
class CreatedTask:
    step_key: str
    task_id: str
    title: str
    assignee: str


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def create_pipeline(
    plan: Plan,
    client: KanbanClient,
    *,
    board: str = "team-pipeline",
    skills: list[str] | None = None,
) -> list[CreatedTask]:
    """Create all tasks in topological order, then link edges.

    - Creates tasks in topo_sort order.
    - Maps step_key → task_id as tasks are created.
    - Links edges (parent_id, child_id) after all tasks are created.
    - Idempotent: re-running with same plan + board doesn't duplicate
      (client honors idempotency_key).
    - Returns list[CreatedTask] in topo_sort order.
    """
    step_keys = [t.spec.step_key for t in plan.tasks]
    order = topo_sort_raw(step_keys, plan.edges)

    # Build step_key → PlannedTask lookup
    task_lookup = {t.spec.step_key: t for t in plan.tasks}

    slug = plan.idea.slug
    id_map: dict[str, str] = {}
    results: list[CreatedTask] = []

    for step_key in order:
        task = task_lookup[step_key]

        # Format branch template with the idea slug (e.g. "wt/{slug}-impl")
        branch = task.spec.branch
        if branch is not None:
            branch = branch.format(slug=slug)

        task_id = client.create(
            task.title,
            body=task.body,
            assignee=task.assignee,
            parents=[],
            workspace=task.workspace,
            branch=branch,
            idempotency_key=task.idempotency_key,
            skills=skills or [],
            board=board,
        )
        id_map[step_key] = task_id
        results.append(
            CreatedTask(
                step_key=step_key,
                task_id=task_id,
                title=task.title,
                assignee=task.assignee,
            )
        )

    # Link edges after all tasks have been created
    for parent_step, child_step in plan.edges:
        parent_id = id_map[parent_step]
        child_id = id_map[child_step]
        client.link(parent_id, child_id, board=board)

    return results


def status(
    client: KanbanClient,
    *,
    root: str,
    board: str = "team-pipeline",
) -> list[dict]:  # type: ignore[type-arg]
    """Return list of task dicts from client.list(board=board, root=root)."""
    return client.list(board=board, root=root)


def summarize(created: list[CreatedTask]) -> str:
    """Return a formatted text summary table of created tasks."""
    if not created:
        return "(no tasks created)"

    header = f"{'step_key':<15} {'task_id':<8} {'assignee':<24} title"
    separator = "-" * 72
    rows = [
        f"{ct.step_key:<15} {ct.task_id:<8} {ct.assignee:<24} {ct.title}"
        for ct in created
    ]
    return "\n".join([header, separator, *rows])
