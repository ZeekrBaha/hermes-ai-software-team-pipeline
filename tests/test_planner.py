"""Tests for planner.py — build_plan assembles a Plan from an idea + workflow (T6)."""
from __future__ import annotations

import pytest

from team_pipeline.idea import IdeaRecord, normalize_string
from team_pipeline.planner import Plan, PlannedTask, build_plan
from team_pipeline.workflow import FULL_SDLC, TaskSpec

EXPECTED_STEP_KEYS = {
    "pm", "ux", "arch", "impl", "review", "fix", "jqa", "sqa", "handoff"
}


@pytest.fixture
def idea() -> IdeaRecord:
    return normalize_string("Build Prompt Regression Lab")


class TestBuildPlanReturnType:
    def test_returns_plan_instance(self, idea: IdeaRecord) -> None:
        plan = build_plan(idea, FULL_SDLC)
        assert isinstance(plan, Plan)

    def test_plan_idea_is_same_object(self, idea: IdeaRecord) -> None:
        plan = build_plan(idea, FULL_SDLC)
        assert plan.idea is idea

    def test_plan_has_nine_tasks(self, idea: IdeaRecord) -> None:
        plan = build_plan(idea, FULL_SDLC)
        assert len(plan.tasks) == 9

    def test_plan_edges_match_workflow(self, idea: IdeaRecord) -> None:
        plan = build_plan(idea, FULL_SDLC)
        assert plan.edges == list(FULL_SDLC.edges)


class TestPlannedTaskStructure:
    def test_each_task_is_planned_task_instance(self, idea: IdeaRecord) -> None:
        plan = build_plan(idea, FULL_SDLC)
        for task in plan.tasks:
            assert isinstance(task, PlannedTask)

    def test_each_task_spec_is_task_spec_instance(self, idea: IdeaRecord) -> None:
        plan = build_plan(idea, FULL_SDLC)
        for task in plan.tasks:
            assert isinstance(task.spec, TaskSpec)

    def test_all_nine_step_keys_present(self, idea: IdeaRecord) -> None:
        plan = build_plan(idea, FULL_SDLC)
        step_keys = {t.spec.step_key for t in plan.tasks}
        assert step_keys == EXPECTED_STEP_KEYS


class TestAssignees:
    def test_first_task_assignee_is_pm_agent(self, idea: IdeaRecord) -> None:
        plan = build_plan(idea, FULL_SDLC)
        assert plan.tasks[0].assignee == "pm-agent"

    def test_assignee_matches_spec_profile(self, idea: IdeaRecord) -> None:
        plan = build_plan(idea, FULL_SDLC)
        for task in plan.tasks:
            assert task.assignee == task.spec.profile


class TestTitles:
    def test_all_titles_contain_idea_title(self, idea: IdeaRecord) -> None:
        plan = build_plan(idea, FULL_SDLC)
        for task in plan.tasks:
            assert idea.title in task.title

    def test_pm_task_title(self, idea: IdeaRecord) -> None:
        plan = build_plan(idea, FULL_SDLC)
        pm_task = next(t for t in plan.tasks if t.spec.step_key == "pm")
        assert pm_task.title == "PM spec for Build Prompt Regression Lab"


class TestBodies:
    def test_all_bodies_are_non_empty_strings(self, idea: IdeaRecord) -> None:
        plan = build_plan(idea, FULL_SDLC)
        for task in plan.tasks:
            assert isinstance(task.body, str)
            assert len(task.body) > 0

    def test_pm_body_contains_problem_section(self, idea: IdeaRecord) -> None:
        plan = build_plan(idea, FULL_SDLC)
        pm_task = next(t for t in plan.tasks if t.spec.step_key == "pm")
        assert "## Problem" in pm_task.body


class TestIdempotencyKeys:
    def test_pm_idempotency_key(self, idea: IdeaRecord) -> None:
        plan = build_plan(idea, FULL_SDLC)
        pm_task = next(t for t in plan.tasks if t.spec.step_key == "pm")
        assert pm_task.idempotency_key == "pipeline:build-prompt-regression-lab:pm"

    def test_impl_idempotency_key(self, idea: IdeaRecord) -> None:
        plan = build_plan(idea, FULL_SDLC)
        impl_task = next(t for t in plan.tasks if t.spec.step_key == "impl")
        assert impl_task.idempotency_key == "pipeline:build-prompt-regression-lab:impl"

    def test_idempotency_key_format_all_tasks(self, idea: IdeaRecord) -> None:
        plan = build_plan(idea, FULL_SDLC)
        for task in plan.tasks:
            expected = f"pipeline:{idea.slug}:{task.spec.step_key}"
            assert task.idempotency_key == expected


class TestWorkspaces:
    def test_pm_task_workspace_is_scratch(self, idea: IdeaRecord) -> None:
        plan = build_plan(idea, FULL_SDLC)
        pm_task = next(t for t in plan.tasks if t.spec.step_key == "pm")
        assert pm_task.workspace == "scratch"

    def test_impl_task_workspace_is_worktree(self, idea: IdeaRecord) -> None:
        plan = build_plan(idea, FULL_SDLC)
        impl_task = next(t for t in plan.tasks if t.spec.step_key == "impl")
        assert impl_task.workspace == "worktree"

    def test_workspace_matches_spec_workspace(self, idea: IdeaRecord) -> None:
        plan = build_plan(idea, FULL_SDLC)
        for task in plan.tasks:
            assert task.workspace == task.spec.workspace


class TestPurity:
    def test_calling_twice_gives_same_result(self, idea: IdeaRecord) -> None:
        plan1 = build_plan(idea, FULL_SDLC)
        plan2 = build_plan(idea, FULL_SDLC)
        assert len(plan1.tasks) == len(plan2.tasks)
        for t1, t2 in zip(plan1.tasks, plan2.tasks):
            assert t1.title == t2.title
            assert t1.body == t2.body
            assert t1.idempotency_key == t2.idempotency_key
            assert t1.assignee == t2.assignee
            assert t1.workspace == t2.workspace
