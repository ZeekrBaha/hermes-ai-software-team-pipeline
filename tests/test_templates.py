"""Tests for Jinja2 template rendering (FR9)."""
from __future__ import annotations

import pytest

from team_pipeline.idea import IdeaRecord, normalize_string
from team_pipeline.templates import render


@pytest.fixture
def idea() -> IdeaRecord:
    return normalize_string("Build Prompt Regression Lab")


# ---------------------------------------------------------------------------
# PM template
# ---------------------------------------------------------------------------


def test_render_pm_contains_title_heading(idea: IdeaRecord) -> None:
    result = render("pm", idea)
    assert "# PM Spec:" in result
    assert idea.title in result


def test_render_pm_contains_all_required_sections(idea: IdeaRecord) -> None:
    result = render("pm", idea)
    required = [
        "## Problem",
        "## Target user",
        "## MVP scope",
        "## Non-goals",
        "## User stories",
        "## Acceptance criteria",
        "## Risks & assumptions",
        "## Definition of done",
    ]
    for heading in required:
        assert heading in result, f"Missing heading: {heading!r}"


def test_render_pm_nonempty(idea: IdeaRecord) -> None:
    assert render("pm", idea).strip() != ""


# ---------------------------------------------------------------------------
# UX template
# ---------------------------------------------------------------------------


def test_render_ux_contains_user_journey(idea: IdeaRecord) -> None:
    result = render("ux", idea)
    assert "## User journey" in result


def test_render_ux_nonempty(idea: IdeaRecord) -> None:
    assert render("ux", idea).strip() != ""


# ---------------------------------------------------------------------------
# Architect template
# ---------------------------------------------------------------------------


def test_render_architect_contains_system_architecture(idea: IdeaRecord) -> None:
    result = render("architect", idea)
    assert "## System architecture" in result


def test_render_architect_contains_data_model(idea: IdeaRecord) -> None:
    result = render("architect", idea)
    assert "## Data model" in result


def test_render_architect_nonempty(idea: IdeaRecord) -> None:
    assert render("architect", idea).strip() != ""


# ---------------------------------------------------------------------------
# Junior-dev template
# ---------------------------------------------------------------------------


def test_render_junior_dev_contains_known_limitations(idea: IdeaRecord) -> None:
    result = render("junior-dev", idea)
    assert "## Known limitations" in result


def test_render_junior_dev_nonempty(idea: IdeaRecord) -> None:
    assert render("junior-dev", idea).strip() != ""


# ---------------------------------------------------------------------------
# Senior-dev template
# ---------------------------------------------------------------------------


def test_render_senior_dev_contains_verdict(idea: IdeaRecord) -> None:
    result = render("senior-dev", idea)
    assert "## Verdict" in result


def test_render_senior_dev_nonempty(idea: IdeaRecord) -> None:
    assert render("senior-dev", idea).strip() != ""


# ---------------------------------------------------------------------------
# Junior-QA template
# ---------------------------------------------------------------------------


def test_render_junior_qa_contains_test_plan(idea: IdeaRecord) -> None:
    result = render("junior-qa", idea)
    assert "## Test plan" in result


def test_render_junior_qa_nonempty(idea: IdeaRecord) -> None:
    assert render("junior-qa", idea).strip() != ""


# ---------------------------------------------------------------------------
# Senior-QA template
# ---------------------------------------------------------------------------


def test_render_senior_qa_contains_coverage_audit(idea: IdeaRecord) -> None:
    result = render("senior-qa", idea)
    assert "## Coverage audit" in result


def test_render_senior_qa_nonempty(idea: IdeaRecord) -> None:
    assert render("senior-qa", idea).strip() != ""


# ---------------------------------------------------------------------------
# Release / handoff template
# ---------------------------------------------------------------------------


def test_render_release_contains_what_was_built(idea: IdeaRecord) -> None:
    result = render("release", idea)
    assert "## What was built" in result


def test_render_release_contains_how_to_run(idea: IdeaRecord) -> None:
    result = render("release", idea)
    assert "## How to run" in result


def test_render_release_nonempty(idea: IdeaRecord) -> None:
    assert render("release", idea).strip() != ""


# ---------------------------------------------------------------------------
# Unknown role raises ValueError
# ---------------------------------------------------------------------------


def test_render_unknown_role_raises_value_error(idea: IdeaRecord) -> None:
    with pytest.raises(ValueError, match="unknown-role"):
        render("unknown-role", idea)
