"""Task graph construction and traversal helpers."""
from __future__ import annotations

from collections import deque

from team_pipeline.workflow import Workflow


def topo_sort_raw(step_keys: list[str], edges: list[tuple[str, str]]) -> list[str]:
    """Kahn's algorithm: return step_keys in topological order.

    Raises ValueError if a cycle is detected.
    """
    in_degree: dict[str, int] = {k: 0 for k in step_keys}
    children: dict[str, list[str]] = {k: [] for k in step_keys}

    for parent, child in edges:
        children[parent].append(child)
        in_degree[child] += 1

    # Start with all nodes that have no incoming edges.
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
        raise ValueError(
            "Cycle detected in workflow graph: topological sort could not complete."
        )

    return order


def topo_sort(workflow: Workflow) -> list[str]:
    """Return step_keys in topological order.

    Raises ValueError if a cycle is detected.
    """
    step_keys = [t.step_key for t in workflow.tasks]
    return topo_sort_raw(step_keys, list(workflow.edges))


def validate_acyclic(workflow: Workflow) -> None:
    """Raises ValueError if the workflow contains a cycle."""
    topo_sort(workflow)


def parents(workflow: Workflow, step_key: str) -> list[str]:
    """Return all parent step_keys of the given step_key."""
    return [parent for parent, child in workflow.edges if child == step_key]
