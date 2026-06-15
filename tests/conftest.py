"""Shared pytest fixtures."""
from __future__ import annotations

import pytest

from team_pipeline.idea import IdeaRecord, normalize_string
from team_pipeline.kanban_client import FakeKanbanClient


@pytest.fixture
def fake_client() -> FakeKanbanClient:
    return FakeKanbanClient()


@pytest.fixture
def sample_idea() -> IdeaRecord:
    return normalize_string("Build Prompt Regression Lab")
