"""Tests for KanbanClient Protocol + FakeKanbanClient (T7)."""
from __future__ import annotations

import json
import re
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from team_pipeline.kanban_client import (
    FakeKanbanClient,
    HermesError,
    HermesKanbanClient,
    KanbanClient,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _create(client: FakeKanbanClient, *, idempotency_key: str, title: str = "title") -> str:  # noqa: E501
    return client.create(
        title,
        body="b",
        assignee="a",
        parents=[],
        workspace="scratch",
        branch=None,
        idempotency_key=idempotency_key,
        skills=[],
        board="test",
    )


# ---------------------------------------------------------------------------
# create() — counter + idempotency
# ---------------------------------------------------------------------------


class TestFakeKanbanClientCreate:
    def test_first_create_returns_t1(self, fake_client: FakeKanbanClient) -> None:
        assert _create(fake_client, idempotency_key="k1") == "t1"

    def test_second_create_different_key_returns_t2(self, fake_client) -> None:
        _create(fake_client, idempotency_key="k1")
        assert _create(fake_client, idempotency_key="k2") == "t2"

    def test_idempotency_same_key_returns_same_id(self, fake_client) -> None:
        id1 = _create(fake_client, idempotency_key="k1")
        id2 = _create(fake_client, idempotency_key="k1")
        assert id1 == id2 == "t1"

    def test_idempotency_does_not_advance_counter(self, fake_client) -> None:
        """Repeated key must not consume a counter slot."""
        _create(fake_client, idempotency_key="k1")
        _create(fake_client, idempotency_key="k1")  # duplicate — no new slot
        assert _create(fake_client, idempotency_key="k2") == "t2"

    def test_three_unique_keys_returns_t3(self, fake_client) -> None:
        _create(fake_client, idempotency_key="k1")
        _create(fake_client, idempotency_key="k2")
        assert _create(fake_client, idempotency_key="k3") == "t3"


# ---------------------------------------------------------------------------
# create() — call recording
# ---------------------------------------------------------------------------


class TestFakeKanbanClientCreateCalls:
    def test_create_calls_recorded(self, fake_client) -> None:
        _create(fake_client, idempotency_key="k1")
        assert len(fake_client.create_calls) == 1

    def test_create_call_contains_idempotency_key(self, fake_client) -> None:
        _create(fake_client, idempotency_key="k1")
        assert fake_client.create_calls[0]["idempotency_key"] == "k1"

    def test_create_call_contains_title(self, fake_client) -> None:
        _create(fake_client, idempotency_key="k1", title="My Task")
        assert fake_client.create_calls[0]["title"] == "My Task"

    def test_duplicate_key_still_recorded_as_call(self, fake_client) -> None:
        """Every call is recorded even if it's a duplicate idempotency key."""
        _create(fake_client, idempotency_key="k1")
        _create(fake_client, idempotency_key="k1")
        assert len(fake_client.create_calls) == 2

    def test_two_unique_calls_both_recorded(self, fake_client) -> None:
        _create(fake_client, idempotency_key="k1")
        _create(fake_client, idempotency_key="k2")
        assert len(fake_client.create_calls) == 2


# ---------------------------------------------------------------------------
# init()
# ---------------------------------------------------------------------------


class TestFakeKanbanClientInit:
    def test_init_does_not_raise(self, fake_client) -> None:
        fake_client.init("my-board")  # must not raise

    def test_init_records_board(self, fake_client) -> None:
        fake_client.init("my-board")
        assert "my-board" in fake_client.init_calls

    def test_init_multiple_boards_all_recorded(self, fake_client) -> None:
        fake_client.init("board-a")
        fake_client.init("board-b")
        assert fake_client.init_calls == ["board-a", "board-b"]


# ---------------------------------------------------------------------------
# link()
# ---------------------------------------------------------------------------


class TestFakeKanbanClientLink:
    def test_link_records_edge(self, fake_client) -> None:
        fake_client.link("t1", "t2", board="test")
        assert ("t1", "t2") in fake_client.linked_edges

    def test_link_multiple_edges(self, fake_client) -> None:
        fake_client.link("t1", "t2", board="test")
        fake_client.link("t1", "t3", board="test")
        assert len(fake_client.linked_edges) == 2

    def test_link_preserves_order(self, fake_client) -> None:
        fake_client.link("parent", "child", board="test")
        edge = fake_client.linked_edges[0]
        assert edge == ("parent", "child")


# ---------------------------------------------------------------------------
# list()
# ---------------------------------------------------------------------------


class TestFakeKanbanClientList:
    def test_list_returns_empty_by_default(self, fake_client) -> None:
        assert fake_client.list(board="test", root=None) == []

    def test_list_returns_empty_with_root(self, fake_client) -> None:
        assert fake_client.list(board="test", root="t1") == []


# ---------------------------------------------------------------------------
# assignees() + version()
# ---------------------------------------------------------------------------


class TestFakeKanbanClientMisc:
    def test_version_returns_hermes_version(self, fake_client) -> None:
        assert fake_client.version() == "0.16.0"

    def test_assignees_returns_empty_list(self, fake_client) -> None:
        assert fake_client.assignees() == []


# ---------------------------------------------------------------------------
# Protocol structural check
# ---------------------------------------------------------------------------


class TestKanbanClientProtocol:
    def test_fake_is_instance_of_protocol(self, fake_client) -> None:
        assert isinstance(fake_client, KanbanClient)


# ---------------------------------------------------------------------------
# HermesError
# ---------------------------------------------------------------------------


class TestHermesError:
    def _make(self) -> HermesError:
        return HermesError(
            cmd=["hermes", "kanban", "create"],
            returncode=1,
            stderr="error msg",
        )

    def test_stores_cmd(self) -> None:
        assert self._make().cmd == ["hermes", "kanban", "create"]

    def test_stores_returncode(self) -> None:
        assert self._make().returncode == 1

    def test_stores_stderr(self) -> None:
        assert self._make().stderr == "error msg"

    def test_is_instance_of_exception(self) -> None:
        assert isinstance(self._make(), Exception)

    def test_can_be_caught_as_exception(self) -> None:
        caught = False
        try:
            raise HermesError(
                cmd=["hermes", "kanban", "create"],
                returncode=1,
                stderr="error msg",
            )
        except Exception:
            caught = True
        assert caught


# ---------------------------------------------------------------------------
# HermesKanbanClient — arg builder, JSON parser, error propagation (T9)
# ---------------------------------------------------------------------------


_FIXTURES = Path(__file__).parent / "fixtures"


class TestHermesKanbanClientArgBuilder:
    def test_create_json_fixture_has_id_field(self) -> None:
        """The real create --json fixture has an 'id' field starting with 't_'."""
        data = json.loads((_FIXTURES / "create.json").read_text())
        assert "id" in data
        assert data["id"].startswith("t_")

    def test_create_json_fixture_id_format(self) -> None:
        """id is 't_' followed by exactly 8 lowercase hex characters."""
        data = json.loads((_FIXTURES / "create.json").read_text())
        assert re.match(r"t_[0-9a-f]{8}$", data["id"])

    def test_hermes_error_on_nonzero_exit(self) -> None:
        """HermesKanbanClient._run raises HermesError when subprocess exits non-zero."""
        client = HermesKanbanClient(hermes_path="hermes")
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "command not found"
        with patch("subprocess.run", return_value=mock_result):
            with pytest.raises(HermesError) as exc_info:
                client._run(["kanban", "create", "test"])
        assert exc_info.value.returncode == 1
        assert exc_info.value.stderr == "command not found"

    def test_hermes_no_shell_true(self) -> None:
        """_run never passes shell=True — security requirement."""
        client = HermesKanbanClient()
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""
        with patch("subprocess.run", return_value=mock_result) as mock_run:
            try:
                client._run(["kanban", "init"])
            except Exception:
                pass
            for c in mock_run.call_args_list:
                assert c.kwargs.get("shell") is not True

    def test_assignees_extracts_name_field(self) -> None:
        """assignees() extracts 'name' from each item in the JSON array."""
        client = HermesKanbanClient()
        fake_data = [
            {"name": "pm-agent", "on_disk": True},
            {"name": "ux-agent", "on_disk": False},
        ]
        with patch.object(client, "_run", return_value=fake_data):
            result = client.assignees()
        assert result == ["pm-agent", "ux-agent"]

    def test_init_passes_board_flag(self) -> None:
        """init('myboard') must include '--board' and 'myboard' after 'kanban'."""
        client = HermesKanbanClient()
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""
        with patch("subprocess.run", return_value=mock_result) as mock_run:
            client.init("myboard")
        args = mock_run.call_args[0][0]
        kanban_idx = args.index("kanban")
        assert args[kanban_idx + 1] == "--board"
        assert args[kanban_idx + 2] == "myboard"

    def test_create_passes_board_flag(self) -> None:
        """create(...) must include '--board' and 'myboard' after 'kanban'."""
        client = HermesKanbanClient()
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = '{"id": "t_abcdef01"}'
        with patch("subprocess.run", return_value=mock_result) as mock_run:
            client.create(
                "My Task",
                body="body",
                assignee="pm-agent",
                parents=[],
                workspace="scratch",
                branch=None,
                idempotency_key="k1",
                skills=[],
                board="myboard",
            )
        args = mock_run.call_args[0][0]
        kanban_idx = args.index("kanban")
        assert args[kanban_idx + 1] == "--board"
        assert args[kanban_idx + 2] == "myboard"

    def test_version_raises_hermes_error_on_nonzero_returncode(self) -> None:
        """version() must raise HermesError when the subprocess exits non-zero."""
        client = HermesKanbanClient()
        mock_result = MagicMock()
        mock_result.returncode = 127
        mock_result.stdout = ""
        mock_result.stderr = "hermes: command not found"
        with patch("subprocess.run", return_value=mock_result):
            with pytest.raises(HermesError) as exc_info:
                client.version()
        assert exc_info.value.returncode == 127

    def test_create_raises_hermes_error_when_response_missing_id(self) -> None:
        """create() raises HermesError when JSON response has no 'id' field."""
        client = HermesKanbanClient()
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = '{"status": "ok"}'
        with patch("subprocess.run", return_value=mock_result):
            with pytest.raises(HermesError) as exc_info:
                client.create(
                    "My Task",
                    body="body",
                    assignee="pm-agent",
                    parents=[],
                    workspace="scratch",
                    branch=None,
                    idempotency_key="k1",
                    skills=[],
                    board="myboard",
                )
        assert "missing 'id' field" in exc_info.value.stderr
