"""Tests for KanbanClient Protocol + FakeKanbanClient (T7)."""
from __future__ import annotations

from team_pipeline.kanban_client import FakeKanbanClient, KanbanClient

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
