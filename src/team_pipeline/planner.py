"""Task planning logic."""
from __future__ import annotations

from dataclasses import dataclass

from team_pipeline import templates
from team_pipeline.idea import IdeaRecord
from team_pipeline.workflow import TaskSpec, Workflow


@dataclass
class PlannedTask:
    spec: TaskSpec
    title: str
    body: str
    assignee: str
    workspace: str
    idempotency_key: str


@dataclass
class Plan:
    idea: IdeaRecord
    tasks: list[PlannedTask]
    edges: list[tuple[str, str]]


def build_plan(idea: IdeaRecord, workflow: Workflow) -> Plan:
    """Build a Plan from an idea and workflow.

    Pure function — no I/O, no Hermes calls.
    Renders each task's title and body.
    Sets idempotency_key = f"pipeline:{idea.slug}:{spec.step_key}"
    """
    tasks: list[PlannedTask] = []
    for spec in workflow.tasks:
        title = spec.title_tmpl.format(title=idea.title)
        body = templates.render(spec.role, idea)
        idempotency_key = f"pipeline:{idea.slug}:{spec.step_key}"
        tasks.append(
            PlannedTask(
                spec=spec,
                title=title,
                body=body,
                assignee=spec.profile,
                workspace=spec.workspace,
                idempotency_key=idempotency_key,
            )
        )
    return Plan(idea=idea, tasks=tasks, edges=list(workflow.edges))
