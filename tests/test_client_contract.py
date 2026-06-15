"""Contract tests for KanbanClient implementations.

Both FakeKanbanClient (used in tests) and HermesKanbanClient (the real
subprocess-backed client) must honor the same observable KanbanClient contract.
Running one parametrized suite against both guards against fake-vs-real drift:
if a method's return shape diverges, one of the two parametrizations fails here
instead of in production.

The real client's subprocess calls are stubbed by a single ``side_effect`` that
returns canned, well-formed output for whichever subcommand is invoked.
"""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from team_pipeline.kanban_client import (
    FakeKanbanClient,
    HermesKanbanClient,
    KanbanClient,
)

# Shared kwargs for create() — keyword-only on both implementations.
CREATE_KWARGS = dict(
    body="body text",
    assignee="pm-agent",
    parents=[],
    workspace="scratch",
    branch=None,
    idempotency_key="k1",
    skills=[],
    board="team-pipeline",
)


def _hermes_side_effect(cmd, **_kwargs):
    """Return canned, well-formed hermes output based on the subcommand in cmd."""
    result = MagicMock()
    result.returncode = 0
    result.stderr = ""
    if "--version" in cmd:
        result.stdout = "Hermes Agent v0.16.0 (2026.6.5)"
    elif "create" in cmd:
        result.stdout = json.dumps({"id": "t_abcdef01"})
    elif "list" in cmd:
        result.stdout = json.dumps([])
    elif "assignees" in cmd:
        result.stdout = json.dumps([{"name": "pm-agent"}])
    else:  # init, link — no JSON payload
        result.stdout = ""
    return result


@pytest.fixture(params=["fake", "real"])
def client(request):
    """Yield each KanbanClient implementation under a common contract.

    For the real client, subprocess.run is patched so no hermes binary is needed.
    """
    if request.param == "fake":
        yield FakeKanbanClient()
    else:
        with patch("subprocess.run", side_effect=_hermes_side_effect):
            yield HermesKanbanClient()


def test_implements_protocol(client) -> None:
    assert isinstance(client, KanbanClient)


def test_create_returns_nonempty_str_task_id(client) -> None:
    task_id = client.create("A title", **CREATE_KWARGS)
    assert isinstance(task_id, str)
    assert task_id


def test_init_returns_none(client) -> None:
    assert client.init("team-pipeline") is None


def test_link_returns_none(client) -> None:
    assert client.link("t1", "t2", board="team-pipeline") is None


def test_list_returns_list(client) -> None:
    assert isinstance(client.list(board="team-pipeline", root=None), list)


def test_assignees_returns_list_of_str(client) -> None:
    out = client.assignees()
    assert isinstance(out, list)
    assert all(isinstance(name, str) for name in out)


def test_version_returns_str(client) -> None:
    assert isinstance(client.version(), str)
