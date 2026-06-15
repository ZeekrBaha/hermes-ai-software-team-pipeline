"""Tests for cli.py — Typer CLI surface (T11)."""
from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from team_pipeline.cli import app
from team_pipeline.kanban_client import FakeKanbanClient

runner = CliRunner()

# ---------------------------------------------------------------------------
# --help
# ---------------------------------------------------------------------------


def test_help_lists_all_commands() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    for cmd in ("doctor", "preview", "create", "validate", "status", "summarize"):
        assert cmd in result.output


# ---------------------------------------------------------------------------
# preview
# ---------------------------------------------------------------------------


def test_preview_prints_plan_table() -> None:
    """preview outputs a table containing step_keys from the full-sdlc workflow."""
    result = runner.invoke(app, ["preview", "--idea", "Build Prompt Regression Lab"])
    assert result.exit_code == 0
    assert "pm" in result.output
    assert "handoff" in result.output


def test_preview_ac3_1_no_error_in_output() -> None:
    """AC3.1: preview makes no mutating Hermes calls — no Error line, exit 0."""
    result = runner.invoke(app, ["preview", "--idea", "Build Prompt Regression Lab"])
    assert result.exit_code == 0
    assert "Error" not in result.output


def test_preview_empty_idea_exits_1() -> None:
    result = runner.invoke(app, ["preview", "--idea", ""])
    assert result.exit_code == 1


def test_preview_from_file(tmp_path: Path) -> None:
    idea_file = tmp_path / "idea.md"
    idea_file.write_text("# My Test Idea\n\nSome description.\n")
    result = runner.invoke(app, ["preview", "--from", str(idea_file)])
    assert result.exit_code == 0
    assert "pm" in result.output


def test_preview_from_missing_file() -> None:
    result = runner.invoke(app, ["preview", "--from", "/nonexistent/idea.md"])
    assert result.exit_code == 1


def test_preview_no_args_exits_1() -> None:
    """preview with neither --idea nor --from should exit 1."""
    result = runner.invoke(app, ["preview"])
    assert result.exit_code == 1


# ---------------------------------------------------------------------------
# create --dry-run
# ---------------------------------------------------------------------------


def test_create_dry_run_exit_0() -> None:
    """create --dry-run behaves like preview: prints plan, exit 0."""
    result = runner.invoke(app, ["create", "--idea", "Build X", "--dry-run"])
    assert result.exit_code == 0
    assert "pm" in result.output


def test_create_dry_run_no_mutating_calls(monkeypatch: pytest.MonkeyPatch) -> None:
    """AC3.1: --dry-run records zero create/link calls on FakeKanbanClient."""
    fake = FakeKanbanClient()
    monkeypatch.setattr("team_pipeline.cli.HermesKanbanClient", lambda: fake)
    result = runner.invoke(app, ["create", "--idea", "Build X", "--dry-run"])
    assert result.exit_code == 0
    assert len(fake.create_calls) == 0
    assert len(fake.linked_edges) == 0


# ---------------------------------------------------------------------------
# validate
# ---------------------------------------------------------------------------

PM_FULL_SECTIONS = """\
# Problem
A problem statement.

# Target user
A target user.

# MVP scope
Core pipeline: PM → senior-dev flow.

# Non-goals
Out of scope for MVP.

# User stories
- As a user I can do X.

# Acceptance criteria
- AC1: the system does Y.

# Risks & assumptions
- Risk 1: dependency on Z.

# Definition of done
All tests pass.
"""


def test_validate_ok(tmp_path: Path) -> None:
    spec = tmp_path / "spec.md"
    spec.write_text(PM_FULL_SECTIONS)
    result = runner.invoke(app, ["validate", str(spec), "--role", "pm"])
    assert result.exit_code == 0


def test_validate_empty_artifact_exits_1(tmp_path: Path) -> None:
    spec = tmp_path / "spec.md"
    spec.write_text("")
    result = runner.invoke(app, ["validate", str(spec), "--role", "pm"])
    assert result.exit_code == 1


def test_validate_file_not_found_exits_1() -> None:
    result = runner.invoke(app, ["validate", "nonexistent.md", "--role", "pm"])
    assert result.exit_code == 1


def test_validate_bad_role_exits_1(tmp_path: Path) -> None:
    spec = tmp_path / "spec.md"
    spec.write_text("# Some content\n")
    result = runner.invoke(app, ["validate", str(spec), "--role", "bad-role"])
    assert result.exit_code == 1


# ---------------------------------------------------------------------------
# status
# ---------------------------------------------------------------------------


def test_status_exit_0(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = FakeKanbanClient()
    monkeypatch.setattr("team_pipeline.cli.HermesKanbanClient", lambda: fake)
    result = runner.invoke(app, ["status", "--root-task", "t_abc"])
    assert result.exit_code == 0


# ---------------------------------------------------------------------------
# doctor
# ---------------------------------------------------------------------------


def test_doctor_runs() -> None:
    """Doctor may exit 0 or 1 depending on hermes install — just verify it runs."""
    result = runner.invoke(app, ["doctor"])
    assert result.exit_code in (0, 1)


# ---------------------------------------------------------------------------
# summarize
# ---------------------------------------------------------------------------


def test_summarize_exit_0(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = FakeKanbanClient()
    monkeypatch.setattr("team_pipeline.cli.HermesKanbanClient", lambda: fake)
    result = runner.invoke(app, ["summarize", "--root-task", "t_abc"])
    assert result.exit_code == 0
