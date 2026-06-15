"""Tests for workflow.py — Workflow model + full-sdlc DAG (T2)."""
from __future__ import annotations

import pytest

from team_pipeline.workflow import FULL_SDLC, Workflow, load

EXPECTED_STEP_KEYS = {
    "pm", "ux", "arch", "impl", "review", "fix", "jqa", "sqa", "handoff"
}

EXPECTED_PROFILES = {
    "pm": "pm-agent",
    "ux": "ux-designer-agent",
    "arch": "architect-agent",
    "impl": "junior-dev-agent",
    "review": "senior-dev-reviewer",
    "fix": "junior-dev-agent",
    "jqa": "junior-qa-agent",
    "sqa": "senior-qa-agent",
    "handoff": "release-agent",
}

WORKTREE_STEPS = {"impl", "fix"}
SCRATCH_STEPS = {"pm", "ux", "arch", "review", "jqa", "sqa", "handoff"}


class TestLoadFullSdlc:
    def test_load_returns_workflow(self) -> None:
        wf = load("full-sdlc")
        assert isinstance(wf, Workflow)

    def test_load_unknown_name_raises_value_error(self) -> None:
        with pytest.raises(ValueError):
            load("nonexistent")

    def test_full_sdlc_importable_directly(self) -> None:
        assert isinstance(FULL_SDLC, Workflow)

    def test_load_returns_same_as_constant(self) -> None:
        assert load("full-sdlc") is FULL_SDLC


class TestFullSdlcTasks:
    def test_exactly_nine_tasks(self) -> None:
        assert len(FULL_SDLC.tasks) == 9

    def test_step_keys_match_expected_set(self) -> None:
        keys = {t.step_key for t in FULL_SDLC.tasks}
        assert keys == EXPECTED_STEP_KEYS

    def test_all_profiles_correct(self) -> None:
        profiles = {t.step_key: t.profile for t in FULL_SDLC.tasks}
        for step, expected_profile in EXPECTED_PROFILES.items():
            got = profiles[step]
            assert got == expected_profile, (
                f"step '{step}': expected '{expected_profile}', got '{got}'"
            )

    def test_scratch_workspace_for_docs_roles(self) -> None:
        for task in FULL_SDLC.tasks:
            if task.step_key in SCRATCH_STEPS:
                ws = task.workspace
                assert ws == "scratch", (
                    f"step '{task.step_key}': expected 'scratch', got '{ws}'"
                )

    def test_worktree_workspace_for_impl_and_fix(self) -> None:
        for task in FULL_SDLC.tasks:
            if task.step_key in WORKTREE_STEPS:
                ws = task.workspace
                assert ws == "worktree", (
                    f"step '{task.step_key}': expected 'worktree', got '{ws}'"
                )

    def test_impl_and_fix_have_branch(self) -> None:
        by_key = {t.step_key: t for t in FULL_SDLC.tasks}
        assert by_key["impl"].branch == "wt/{slug}-impl"
        assert by_key["fix"].branch == "wt/{slug}-impl"

    def test_scratch_steps_have_no_branch(self) -> None:
        by_key = {t.step_key: t for t in FULL_SDLC.tasks}
        for step in SCRATCH_STEPS:
            assert by_key[step].branch is None, (
                f"step '{step}' expected branch=None, got '{by_key[step].branch}'"
            )
