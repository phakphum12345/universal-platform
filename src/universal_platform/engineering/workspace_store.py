"""Durable local workspace metadata storage.

Workspace records are metadata only: this store never copies, moves, or deletes
project files. Callers remain responsible for authorization and filesystem
operations. SQLite transactions and optimistic revisions protect metadata
updates from lost writes.
"""
from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from threading import RLock
from typing import Any
from uuid import uuid4

_SCHEMA_VERSION = 1
_MAX_NAME_LENGTH = 120
_MAX_DESCRIPTION_LENGTH = 2000


class WorkspaceStoreIntegrityError(RuntimeError):
    """Raised when persisted workspace metadata cannot be trusted."""


class WorkspaceNotFoundError(KeyError):
    """Raised when a workspace identifier does not exist."""


class WorkspaceRevisionConflict(RuntimeError):
    """Raised when an update is based on a stale workspace revision."""


@dataclass(frozen=True, slots=True)
class WorkspaceRecord:
    workspace_id: str
    name: str
    description: str
    metadata: dict[str, Any]
    revision: int
    created_at: str
    updated_at: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "workspace_id": self.workspace_id,
            "name": self.name,
            "description": self.description,
            "metadata": dict(self.metadata),
            "revision": self.revision,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


def _validate_json_value(value: object, path: str = "metadata") -> None:
    if value is None or isinstance(value, (str, bool, int)):
        return
    if isinstance(value, float):
        if value != value or value in (float("inf"), float("-inf")):
            raise ValueError(f"{path} must not contain non-finite numbers")
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            _validate_json_value(item, f"{path}[{index}]")
        return
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise ValueError(f"{path} object keys must be strings")
            _validate_json_value(item, f"{path}.{key}")
        return
    raise ValueError(f"{path} must contain only JSON-compatible values")


def _canonical_json(value: object) -> str:
    _validate_json_value(value)
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
        allow_nan=False,
    )


def _validate_text(value: object, field: str, maximum: int, *, required: bool) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field} must be a string")
    normalized = value.strip()
    if required and not normalized:
        raise ValueError(f"{field} must not be empty")
    if len(normalized) > maximum:
        raise ValueError(f"{field} must be at most {maximum} characters")
    if "\x00" in normalized:
        raise ValueError(f"{field} must not contain NUL")
    return normalized


class SQLiteWorkspaceStore:
    """SQLite-backed workspace metadata store with revision-checked updates."""

    def __init__(self, database_path: str | Path):
        raw = str(database_path)
        if not raw.strip() or raw in {":memory:", ""} or raw.startswith("file:"):
            raise ValueError("database_path must be an explicit filesystem path")
        self.database_path = Path(database_path).expanduser().resolve()
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = RLock()
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(
            str(self.database_path), timeout=5.0, isolation_level=None
        )
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA busy_timeout = 5000")
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA synchronous = FULL")
        return connection

    def _initialize(self) -> None:
        with self._lock, closing(self._connect()) as connection:
            version = int(connection.execute("PRAGMA user_version").fetchone()[0])
            if version > _SCHEMA_VERSION:
                raise WorkspaceStoreIntegrityError(
                    "workspace database schema is newer than this implementation"
                )
            connection.execute("PRAGMA journal_mode = WAL")
            connection.execute(
                """CREATE TABLE IF NOT EXISTS workspaces (
                    workspace_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT NOT NULL,
                    metadata_json TEXT NOT NULL,
                    revision INTEGER NOT NULL CHECK (revision >= 1),
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )"""
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_workspaces_updated "
                "ON workspaces(updated_at DESC, workspace_id)"
            )
            connection.execute(f"PRAGMA user_version = {_SCHEMA_VERSION}")

    @staticmethod
    def _decode(row: sqlite3.Row) -> WorkspaceRecord:
        try:
            metadata = json.loads(row["metadata_json"])
        except (TypeError, json.JSONDecodeError) as exc:
            raise WorkspaceStoreIntegrityError(
                "stored workspace metadata is invalid JSON"
            ) from exc
        if not isinstance(metadata, dict):
            raise WorkspaceStoreIntegrityError(
                "stored workspace metadata must be a JSON object"
            )
        return WorkspaceRecord(
            workspace_id=row["workspace_id"],
            name=row["name"],
            description=row["description"],
            metadata=metadata,
            revision=int(row["revision"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def create(
        self,
        name: str,
        *,
        description: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> WorkspaceRecord:
        normalized_name = _validate_text(
            name, "name", _MAX_NAME_LENGTH, required=True
        )
        normalized_description = _validate_text(
            description, "description", _MAX_DESCRIPTION_LENGTH, required=False
        )
        if metadata is None:
            metadata = {}
        if not isinstance(metadata, dict):
            raise TypeError("metadata must be an object")
        try:
            metadata_json = _canonical_json(metadata)
        except (TypeError, ValueError) as exc:
            raise ValueError("metadata must contain only valid JSON values") from exc

        workspace_id = str(uuid4())
        now = datetime.now(UTC).isoformat()
        with self._lock, closing(self._connect()) as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                """INSERT INTO workspaces
                   (workspace_id, name, description, metadata_json, revision,
                    created_at, updated_at)
                   VALUES (?, ?, ?, ?, 1, ?, ?)""",
                (
                    workspace_id, normalized_name, normalized_description,
                    metadata_json, now, now,
                ),
            )
            row = connection.execute(
                "SELECT * FROM workspaces WHERE workspace_id = ?",
                (workspace_id,),
            ).fetchone()
            connection.commit()
        return self._decode(row)

    def get(self, workspace_id: str) -> WorkspaceRecord:
        if not isinstance(workspace_id, str) or not workspace_id.strip():
            raise ValueError("workspace_id must be a non-empty string")
        with self._lock, closing(self._connect()) as connection:
            row = connection.execute(
                "SELECT * FROM workspaces WHERE workspace_id = ?",
                (workspace_id,),
            ).fetchone()
        if row is None:
            raise WorkspaceNotFoundError(workspace_id)
        return self._decode(row)

    def list(self, *, limit: int = 100) -> tuple[WorkspaceRecord, ...]:
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 500:
            raise ValueError("limit must be an integer from 1 through 500")
        with self._lock, closing(self._connect()) as connection:
            rows = connection.execute(
                "SELECT * FROM workspaces "
                "ORDER BY updated_at DESC, workspace_id LIMIT ?",
                (limit,),
            ).fetchall()
        return tuple(self._decode(row) for row in rows)

    def update(
        self,
        workspace_id: str,
        *,
        expected_revision: int,
        name: str,
        description: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> WorkspaceRecord:
        if (
            isinstance(expected_revision, bool)
            or not isinstance(expected_revision, int)
            or expected_revision < 1
        ):
            raise ValueError("expected_revision must be a positive integer")
        normalized_name = _validate_text(
            name, "name", _MAX_NAME_LENGTH, required=True
        )
        normalized_description = _validate_text(
            description, "description", _MAX_DESCRIPTION_LENGTH, required=False
        )
        if metadata is None:
            metadata = {}
        if not isinstance(metadata, dict):
            raise ValueError("metadata must be an object")
        try:
            metadata_json = _canonical_json(metadata)
        except (TypeError, ValueError) as exc:
            raise ValueError("metadata must contain finite JSON-compatible values") from exc

        now = datetime.now(UTC).isoformat()
        with self._lock, closing(self._connect()) as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT revision FROM workspaces WHERE workspace_id = ?",
                (workspace_id,),
            ).fetchone()
            if row is None:
                connection.rollback()
                raise WorkspaceNotFoundError(workspace_id)
            current_revision = int(row["revision"])
            if current_revision != expected_revision:
                connection.rollback()
                raise WorkspaceRevisionConflict(
                    f"expected revision {expected_revision}, found {current_revision}"
                )
            connection.execute(
                """UPDATE workspaces
                   SET name = ?, description = ?, metadata_json = ?,
                       revision = revision + 1, updated_at = ?
                   WHERE workspace_id = ? AND revision = ?""",
                (
                    normalized_name, normalized_description, metadata_json,
                    now, workspace_id, expected_revision,
                ),
            )
            updated = connection.execute(
                "SELECT * FROM workspaces WHERE workspace_id = ?",
                (workspace_id,),
            ).fetchone()
            connection.commit()
        return self._decode(updated)


__all__ = [
    "SQLiteWorkspaceStore",
    "WorkspaceNotFoundError",
    "WorkspaceRecord",
    "WorkspaceRevisionConflict",
    "WorkspaceStoreIntegrityError",
]
