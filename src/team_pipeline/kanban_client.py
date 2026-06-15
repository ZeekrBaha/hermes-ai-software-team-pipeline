"""Hermes Kanban API client."""
from __future__ import annotations

import builtins
import json
import subprocess
from typing import Any, Protocol, runtime_checkable

# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class HermesError(Exception):
    """Raised when the hermes CLI exits with a non-zero return code."""

    def __init__(self, cmd: list[str], returncode: int, stderr: str) -> None:
        self.cmd = cmd
        self.returncode = returncode
        self.stderr = stderr
        super().__init__(
            f"hermes {cmd!r} exited {returncode}: {stderr}"
        )


# ---------------------------------------------------------------------------
# Protocol
# ---------------------------------------------------------------------------


@runtime_checkable
class KanbanClient(Protocol):
    """Structural protocol for Kanban board clients."""

    def init(self, board: str) -> None: ...

    def create(
        self,
        title: str,
        *,
        body: str,
        assignee: str,
        parents: list[str],
        workspace: str,
        branch: str | None,
        idempotency_key: str,
        skills: list[str],
        board: str,
    ) -> str: ...  # returns task_id

    def link(self, parent_id: str, child_id: str, *, board: str) -> None: ...

    def list(self, *, board: str, root: str | None) -> builtins.list[dict]: ...  # type: ignore[type-arg]

    def assignees(self) -> builtins.list[str]: ...

    def version(self) -> str: ...


# ---------------------------------------------------------------------------
# Fake (for tests)
# ---------------------------------------------------------------------------


class FakeKanbanClient:
    """In-memory fake implementation of KanbanClient for use in tests.

    - Records every call for later assertion.
    - ``create`` returns ``"t1"``, ``"t2"``, ... (incrementing counter).
    - Honors idempotency: the same ``idempotency_key`` returns the same task_id.
    - ``list`` returns ``[]`` by default (override ``list_result`` on the instance).
    - ``assignees`` returns ``[]``.
    - ``version`` returns ``"0.16.0"``.
    """

    def __init__(self) -> None:
        self._counter: int = 0
        self._idempotency_map: dict[str, str] = {}

        # Call logs
        self.init_calls: list[str] = []
        self.create_calls: list[dict] = []  # type: ignore[type-arg]
        self.linked_edges: list[tuple[str, str]] = []

        # Configurable return value for list()
        self.list_result: list[dict] = []  # type: ignore[type-arg]

    # ------------------------------------------------------------------
    # Protocol implementation
    # ------------------------------------------------------------------

    def init(self, board: str) -> None:
        self.init_calls.append(board)

    def create(
        self,
        title: str,
        *,
        body: str,
        assignee: str,
        parents: list[str],
        workspace: str,
        branch: str | None,
        idempotency_key: str,
        skills: list[str],
        board: str,
    ) -> str:
        # Record every call regardless of idempotency
        call: dict = {  # type: ignore[type-arg]
            "title": title,
            "body": body,
            "assignee": assignee,
            "parents": parents,
            "workspace": workspace,
            "branch": branch,
            "idempotency_key": idempotency_key,
            "skills": skills,
            "board": board,
        }
        self.create_calls.append(call)

        # Honor idempotency: return existing task_id for a repeated key
        if idempotency_key in self._idempotency_map:
            return self._idempotency_map[idempotency_key]

        # New key — allocate the next task_id
        self._counter += 1
        task_id = f"t{self._counter}"
        self._idempotency_map[idempotency_key] = task_id
        return task_id

    def link(self, parent_id: str, child_id: str, *, board: str) -> None:
        self.linked_edges.append((parent_id, child_id))

    def list(self, *, board: str, root: str | None) -> builtins.list[dict]:  # type: ignore[type-arg]
        return self.list_result

    def assignees(self) -> builtins.list[str]:
        return []

    def version(self) -> str:
        return "0.16.0"


# ---------------------------------------------------------------------------
# Real client (T9)
# ---------------------------------------------------------------------------


class HermesKanbanClient:
    """Real Hermes Kanban client using subprocess."""

    def __init__(self, hermes_path: str = "hermes") -> None:
        self._hermes = hermes_path

    def _run(self, args: list[str], *, capture_json: bool = False) -> Any:
        """Run hermes subprocess. Raises HermesError on non-zero exit.

        args: the full argument list AFTER "hermes" (e.g. ["kanban","create",...])
        If capture_json=True, parses stdout as JSON and returns it.
        """
        cmd = [self._hermes] + args
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise HermesError(
                cmd=cmd, returncode=result.returncode, stderr=result.stderr
            )
        if capture_json:
            return json.loads(result.stdout)
        return None

    def init(self, board: str) -> None:
        self._run(["kanban", "--board", board, "init"])

    def create(
        self,
        title: str,
        *,
        body: str,
        assignee: str,
        parents: list[str],
        workspace: str,
        branch: str | None,
        idempotency_key: str,
        skills: list[str],
        board: str,
    ) -> str:
        args = [
            "kanban", "--board", board, "create", title,
            "--body", body,
            "--assignee", assignee,
            "--workspace", workspace,
            "--idempotency-key", idempotency_key,
            "--json",
        ]
        for parent in parents:
            args.extend(["--parent", parent])
        for skill in skills:
            args.extend(["--skill", skill])
        if branch:
            args.extend(["--branch", branch])
        data = self._run(args, capture_json=True)
        try:
            return str(data["id"])
        except (KeyError, TypeError) as exc:
            raise HermesError(
                cmd=args,
                returncode=0,
                stderr=f"create --json response missing 'id' field: {data!r}",
            ) from exc

    def link(self, parent_id: str, child_id: str, *, board: str) -> None:
        self._run(["kanban", "--board", board, "link", parent_id, child_id])

    def list(self, *, board: str, root: str | None) -> builtins.list[dict]:  # type: ignore[type-arg]
        args = ["kanban", "--board", board, "list", "--json"]
        if root:
            args.extend(["--root", root])
        data = self._run(args, capture_json=True)
        return data if isinstance(data, builtins.list) else []

    def assignees(self) -> builtins.list[str]:
        data = self._run(["kanban", "assignees", "--json"], capture_json=True)
        if isinstance(data, builtins.list):
            return [item["name"] for item in data]
        return []

    def version(self) -> str:
        result = subprocess.run(
            [self._hermes, "--version"], capture_output=True, text=True
        )
        if result.returncode != 0:
            raise HermesError(
                cmd=[self._hermes, "--version"],
                returncode=result.returncode,
                stderr=result.stderr,
            )
        return result.stdout.strip()
