"""Pipeline runner — create tasks in topo order, link edges."""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass

from team_pipeline.kanban_client import KanbanClient
from team_pipeline.planner import Plan


@dataclass
class CreatedTask:
    step_key: str
    task_id: str
    title: str
    assignee: str


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _topo_sort_steps(
    step_keys: list[str], edges: list[tuple[str, str]]
) -> list[str]:
    """Kahn's algorithm: return step_keys in topological order.

    Raises ValueError if a cycle is detected.
    """
    in_degree: dict[str, int] = {k: 0 for k in step_keys}
    children: dict[str, list[str]] = {k: [] for k in step_keys}

    for parent, child in edges:
        children[parent].append(child)
        in_degree[child] += 1

    queue: deque[str] = deque(k for k in step_keys if in_degree[k] == 0)
    order: list[str] = []

    while queue:
        node = queue.popleft()
        order.append(node)
        for child in children[node]:
            in_degree[child] -= 1
            if in_degree[child] == 0:
                queue.append(child)

    if len(order) != len(step_keys):
        raise ValueError("Cycle detected in plan graph: topological sort incomplete.")

    return order


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
    order = _topo_sort_steps(step_keys, plan.edges)

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
