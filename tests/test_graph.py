"""Tests for graph.py — topo_sort, validate_acyclic, parents (T2)."""
from __future__ import annotations

import pytest

from team_pipeline.graph import parents, topo_sort, topo_sort_raw, validate_acyclic
from team_pipeline.workflow import FULL_SDLC, TaskSpec, Workflow


def _make_mini_workflow(edges: list[tuple[str, str]], step_keys: list[str]) -> Workflow:
    """Build a minimal Workflow with step keys and edges for testing."""
    tasks = tuple(
        TaskSpec(
            step_key=k,
            title_tmpl=k,
            profile="agent",
            workspace="scratch",
            branch=None,
            template="t.md.j2",
            role="r",
        )
        for k in step_keys
    )
    return Workflow(name="mini", tasks=tasks, edges=tuple(edges))


class TestTopoSort:
    def test_returns_nine_step_keys(self) -> None:
        order = topo_sort(FULL_SDLC)
        assert len(order) == 9

    def test_pm_before_ux(self) -> None:
        order = topo_sort(FULL_SDLC)
        assert order.index("pm") < order.index("ux")

    def test_pm_before_arch(self) -> None:
        order = topo_sort(FULL_SDLC)
        assert order.index("pm") < order.index("arch")

    def test_ux_before_impl(self) -> None:
        order = topo_sort(FULL_SDLC)
        assert order.index("ux") < order.index("impl")

    def test_arch_before_impl(self) -> None:
        order = topo_sort(FULL_SDLC)
        assert order.index("arch") < order.index("impl")

    def test_impl_before_review(self) -> None:
        order = topo_sort(FULL_SDLC)
        assert order.index("impl") < order.index("review")

    def test_review_before_fix(self) -> None:
        order = topo_sort(FULL_SDLC)
        assert order.index("review") < order.index("fix")

    def test_fix_before_jqa(self) -> None:
        order = topo_sort(FULL_SDLC)
        assert order.index("fix") < order.index("jqa")

    def test_jqa_before_sqa(self) -> None:
        order = topo_sort(FULL_SDLC)
        assert order.index("jqa") < order.index("sqa")

    def test_sqa_before_handoff(self) -> None:
        order = topo_sort(FULL_SDLC)
        assert order.index("sqa") < order.index("handoff")

    def test_handoff_is_last(self) -> None:
        order = topo_sort(FULL_SDLC)
        assert order[-1] == "handoff"

    def test_cycle_raises_value_error(self) -> None:
        cyclic = _make_mini_workflow(
            edges=[("a", "b"), ("b", "c"), ("c", "a")],
            step_keys=["a", "b", "c"],
        )
        with pytest.raises(ValueError):
            topo_sort(cyclic)


class TestTopoSortRaw:
    """Tests for topo_sort_raw — same coverage as TestTopoSort but via raw API."""

    def _full_sdlc_args(self) -> tuple[list[str], list[tuple[str, str]]]:
        step_keys = [t.step_key for t in FULL_SDLC.tasks]
        edges = list(FULL_SDLC.edges)
        return step_keys, edges

    def test_returns_nine_step_keys(self) -> None:
        step_keys, edges = self._full_sdlc_args()
        order = topo_sort_raw(step_keys, edges)
        assert len(order) == 9

    def test_pm_before_ux(self) -> None:
        step_keys, edges = self._full_sdlc_args()
        order = topo_sort_raw(step_keys, edges)
        assert order.index("pm") < order.index("ux")

    def test_pm_before_arch(self) -> None:
        step_keys, edges = self._full_sdlc_args()
        order = topo_sort_raw(step_keys, edges)
        assert order.index("pm") < order.index("arch")

    def test_ux_before_impl(self) -> None:
        step_keys, edges = self._full_sdlc_args()
        order = topo_sort_raw(step_keys, edges)
        assert order.index("ux") < order.index("impl")

    def test_arch_before_impl(self) -> None:
        step_keys, edges = self._full_sdlc_args()
        order = topo_sort_raw(step_keys, edges)
        assert order.index("arch") < order.index("impl")

    def test_impl_before_review(self) -> None:
        step_keys, edges = self._full_sdlc_args()
        order = topo_sort_raw(step_keys, edges)
        assert order.index("impl") < order.index("review")

    def test_review_before_fix(self) -> None:
        step_keys, edges = self._full_sdlc_args()
        order = topo_sort_raw(step_keys, edges)
        assert order.index("review") < order.index("fix")

    def test_fix_before_jqa(self) -> None:
        step_keys, edges = self._full_sdlc_args()
        order = topo_sort_raw(step_keys, edges)
        assert order.index("fix") < order.index("jqa")

    def test_jqa_before_sqa(self) -> None:
        step_keys, edges = self._full_sdlc_args()
        order = topo_sort_raw(step_keys, edges)
        assert order.index("jqa") < order.index("sqa")

    def test_sqa_before_handoff(self) -> None:
        step_keys, edges = self._full_sdlc_args()
        order = topo_sort_raw(step_keys, edges)
        assert order.index("sqa") < order.index("handoff")

    def test_handoff_is_last(self) -> None:
        step_keys, edges = self._full_sdlc_args()
        order = topo_sort_raw(step_keys, edges)
        assert order[-1] == "handoff"

    def test_cycle_raises_value_error(self) -> None:
        with pytest.raises(ValueError):
            topo_sort_raw(["a", "b", "c"], [("a", "b"), ("b", "c"), ("c", "a")])


class TestParents:
    def test_impl_has_two_parents_ux_and_arch(self) -> None:
        result = parents(FULL_SDLC, "impl")
        assert set(result) == {"ux", "arch"}

    def test_pm_has_no_parents(self) -> None:
        result = parents(FULL_SDLC, "pm")
        assert result == []

    def test_ux_parent_is_pm(self) -> None:
        result = parents(FULL_SDLC, "ux")
        assert result == ["pm"]

    def test_arch_parent_is_pm(self) -> None:
        result = parents(FULL_SDLC, "arch")
        assert result == ["pm"]

    def test_handoff_parent_is_sqa(self) -> None:
        result = parents(FULL_SDLC, "handoff")
        assert result == ["sqa"]


class TestValidateAcyclic:
    def test_full_sdlc_is_acyclic(self) -> None:
        validate_acyclic(FULL_SDLC)  # should not raise

    def test_cycle_raises_value_error(self) -> None:
        cyclic = _make_mini_workflow(
            edges=[("x", "y"), ("y", "z"), ("z", "x")],
            step_keys=["x", "y", "z"],
        )
        with pytest.raises(ValueError):
            validate_acyclic(cyclic)

    def test_self_loop_raises_value_error(self) -> None:
        self_loop = _make_mini_workflow(
            edges=[("a", "a")],
            step_keys=["a", "b"],
        )
        with pytest.raises(ValueError):
            validate_acyclic(self_loop)
