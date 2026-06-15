"""Tests for runner.py — create_pipeline, status, summarize."""
from __future__ import annotations

import pytest

from team_pipeline.planner import build_plan
from team_pipeline.runner import CreatedTask, create_pipeline, status, summarize
from team_pipeline.workflow import FULL_SDLC

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _step_index(created: list[CreatedTask], step_key: str) -> int:
    """Return the position (topo order) of a step in the created list."""
    for i, ct in enumerate(created):
        if ct.step_key == step_key:
            return i
    raise KeyError(step_key)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def plan(sample_idea):  # sample_idea from conftest: "Build Prompt Regression Lab"
    return build_plan(sample_idea, FULL_SDLC)


@pytest.fixture
def created(plan, fake_client):
    return create_pipeline(plan, fake_client)


# ---------------------------------------------------------------------------
# create_pipeline — basic shape
# ---------------------------------------------------------------------------


def test_create_pipeline_returns_nine_created_tasks(created):
    assert len(created) == 9


def test_create_pipeline_returns_created_task_instances(created):
    for ct in created:
        assert isinstance(ct, CreatedTask)


def test_create_pipeline_each_task_has_non_empty_task_id(created):
    for ct in created:
        assert ct.task_id, f"task_id is empty for step_key={ct.step_key!r}"


def test_create_pipeline_each_task_has_non_empty_step_key(created):
    for ct in created:
        assert ct.step_key


def test_create_pipeline_all_nine_step_keys_present(created):
    step_keys = {ct.step_key for ct in created}
    expected = {"pm", "ux", "arch", "impl", "review", "fix", "jqa", "sqa", "handoff"}
    assert step_keys == expected


# ---------------------------------------------------------------------------
# create_pipeline — client call counts
# ---------------------------------------------------------------------------


def test_create_pipeline_makes_exactly_nine_create_calls(plan, fake_client):
    create_pipeline(plan, fake_client)
    assert len(fake_client.create_calls) == 9


def test_create_pipeline_links_exactly_nine_edges(plan, fake_client):
    create_pipeline(plan, fake_client)
    assert len(fake_client.linked_edges) == 9


# ---------------------------------------------------------------------------
# create_pipeline — topological order
# ---------------------------------------------------------------------------


def test_create_pipeline_pm_before_ux(created):
    assert _step_index(created, "pm") < _step_index(created, "ux")


def test_create_pipeline_pm_before_arch(created):
    assert _step_index(created, "pm") < _step_index(created, "arch")


def test_create_pipeline_ux_before_impl(created):
    assert _step_index(created, "ux") < _step_index(created, "impl")


def test_create_pipeline_arch_before_impl(created):
    assert _step_index(created, "arch") < _step_index(created, "impl")


def test_create_pipeline_impl_before_review(created):
    assert _step_index(created, "impl") < _step_index(created, "review")


# ---------------------------------------------------------------------------
# create_pipeline — edges are correct (pm→ux linked by task_id)
# ---------------------------------------------------------------------------


def test_create_pipeline_pm_to_ux_edge_linked(plan, fake_client):
    created = create_pipeline(plan, fake_client)
    # pm is created first (topo order) → t1; ux second → t2
    pm_id = next(ct.task_id for ct in created if ct.step_key == "pm")
    ux_id = next(ct.task_id for ct in created if ct.step_key == "ux")
    assert (pm_id, ux_id) in fake_client.linked_edges


def test_create_pipeline_impl_review_edge_linked(plan, fake_client):
    created = create_pipeline(plan, fake_client)
    impl_id = next(ct.task_id for ct in created if ct.step_key == "impl")
    review_id = next(ct.task_id for ct in created if ct.step_key == "review")
    assert (impl_id, review_id) in fake_client.linked_edges


# ---------------------------------------------------------------------------
# create_pipeline — idempotency_key format
# ---------------------------------------------------------------------------


def test_create_pipeline_idempotency_keys_contain_pipeline_prefix(plan, fake_client):
    create_pipeline(plan, fake_client)
    for call in fake_client.create_calls:
        assert call["idempotency_key"].startswith("pipeline:")


def test_create_pipeline_idempotency_keys_contain_slug(plan, fake_client, sample_idea):
    create_pipeline(plan, fake_client)
    for call in fake_client.create_calls:
        assert sample_idea.slug in call["idempotency_key"]


# ---------------------------------------------------------------------------
# create_pipeline — branch argument for worktree steps
# ---------------------------------------------------------------------------


def test_create_pipeline_impl_branch_contains_slug(plan, fake_client, sample_idea):
    create_pipeline(plan, fake_client)
    impl_call = next(c for c in fake_client.create_calls if "Implement" in c["title"])
    assert impl_call["branch"] is not None
    assert sample_idea.slug in impl_call["branch"]


def test_create_pipeline_impl_branch_formatted_correctly(
    plan, fake_client, sample_idea
):
    create_pipeline(plan, fake_client)
    impl_call = next(c for c in fake_client.create_calls if "Implement" in c["title"])
    expected_branch = f"wt/{sample_idea.slug}-impl"
    assert impl_call["branch"] == expected_branch


def test_create_pipeline_pm_branch_is_none(plan, fake_client):
    create_pipeline(plan, fake_client)
    pm_call = next(c for c in fake_client.create_calls if "PM spec" in c["title"])
    assert pm_call["branch"] is None


# ---------------------------------------------------------------------------
# create_pipeline — parents always empty at create time
# ---------------------------------------------------------------------------


def test_create_pipeline_parents_empty_at_create_time(plan, fake_client):
    create_pipeline(plan, fake_client)
    for call in fake_client.create_calls:
        assert call["parents"] == []


# ---------------------------------------------------------------------------
# create_pipeline — idempotency (second run returns same task_ids, more calls recorded)
# ---------------------------------------------------------------------------


def test_create_pipeline_second_run_records_18_create_calls(plan, fake_client):
    create_pipeline(plan, fake_client)
    create_pipeline(plan, fake_client)
    # FakeKanbanClient records ALL calls (even repeated idem keys)
    assert len(fake_client.create_calls) == 18


def test_create_pipeline_second_run_same_task_ids(plan, fake_client):
    created1 = create_pipeline(plan, fake_client)
    created2 = create_pipeline(plan, fake_client)
    ids1 = {ct.step_key: ct.task_id for ct in created1}
    ids2 = {ct.step_key: ct.task_id for ct in created2}
    assert ids1 == ids2


# ---------------------------------------------------------------------------
# status
# ---------------------------------------------------------------------------


def test_status_returns_empty_list_by_default(fake_client):
    result = status(fake_client, root="t1")
    assert result == []


def test_status_returns_list_result_when_configured(fake_client):
    fake_client.list_result = [{"id": "t1", "title": "Some task"}]
    result = status(fake_client, root="t1")
    assert result == [{"id": "t1", "title": "Some task"}]


def test_status_uses_default_board(fake_client):
    # Should not raise; default board is "team-pipeline"
    result = status(fake_client, root="t1")
    assert isinstance(result, list)


# ---------------------------------------------------------------------------
# summarize
# ---------------------------------------------------------------------------


def test_summarize_returns_non_empty_string(created):
    result = summarize(created)
    assert isinstance(result, str)
    assert result.strip()


def test_summarize_contains_step_keys(created):
    result = summarize(created)
    for ct in created:
        assert ct.step_key in result


def test_summarize_contains_task_ids(created):
    result = summarize(created)
    for ct in created:
        assert ct.task_id in result


def test_summarize_empty_list():
    result = summarize([])
    assert isinstance(result, str)
    assert result  # non-empty even for empty input
