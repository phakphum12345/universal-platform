"""Durable, revisioned storage for immutable FeatureHistory documents.

The store persists source documents only. It deliberately does not serialize or
rehydrate computed geometry artifacts, solver objects, or executable code.
SQLite transactions provide atomic commits and cross-process optimistic locking.
"""
from __future__ import annotations

from contextlib import closing
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
from math import isfinite
from pathlib import Path
import re
import sqlite3
from typing import Final

from .errors import InvalidModelError
from .feature_history import FeatureHistory

_STORE_SCHEMA_VERSION: Final[int] = 1
_HISTORY_ID: Final[re.Pattern[str]] = re.compile(r"^[a-z0-9]+(?:[._/-][a-z0-9]+)*$")
_HEX_DIGEST: Final[re.Pattern[str]] = re.compile(r"^[0-9a-f]{64}$")


class FeatureHistoryRevisionConflict(RuntimeError):
    """Raised when the caller's expected revision is not the current head."""

    def __init__(self, history_id: str, expected_revision: int, current_revision: int):
        self.history_id = history_id
        self.expected_revision = expected_revision
        self.current_revision = current_revision
        super().__init__(
            f"feature history {history_id!r} is at revision {current_revision}; "
            f"expected revision {expected_revision}"
        )


class FeatureHistoryStoreIntegrityError(RuntimeError):
    """Raised when persisted revision data fails its hash-chain or schema checks."""


class FeatureHistoryNavigationUnavailable(RuntimeError):
    """Raised when no Undo or Redo target is available."""

    def __init__(self, code: str):
        if code not in {"NO_UNDO", "NO_REDO"}:
            raise ValueError("unsupported navigation error code")
        self.code = code
        super().__init__(code)


@dataclass(frozen=True, slots=True)
class FeatureHistoryRevision:
    history_id: str
    revision: int
    parent_sha256: str | None
    content_sha256: str
    created_at: str
    history: FeatureHistory
    operation: str = "legacy"
    source_revision: int | None = None
    target_revision: int | None = None


@dataclass(frozen=True, slots=True)
class FeatureHistoryNavigationState:
    history_id: str
    current_revision: int
    can_undo: bool
    can_redo: bool
    undo_depth: int
    redo_depth: int

    def to_dict(self) -> dict[str, object]:
        return {
            "history_id": self.history_id,
            "current_revision": self.current_revision,
            "can_undo": self.can_undo,
            "can_redo": self.can_redo,
            "undo_depth": self.undo_depth,
            "redo_depth": self.redo_depth,
        }


def _canonical_json(value: object) -> str:
    try:
        return json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise InvalidModelError("feature history snapshot must be finite JSON data") from exc


def _revision_digest(
    history_id: str,
    revision: int,
    parent_sha256: str | None,
    snapshot_json: str,
) -> str:
    envelope = {
        "schema_version": _STORE_SCHEMA_VERSION,
        "history_id": history_id,
        "revision": revision,
        "parent_sha256": parent_sha256,
        "snapshot": json.loads(snapshot_json),
    }
    return sha256(_canonical_json(envelope).encode("utf-8")).hexdigest()


class SQLiteFeatureHistoryStore:
    """Local durable FeatureHistory document store with immutable revisions.

    A caller must pass the revision it previously read (0 for first creation).
    Writes use BEGIN IMMEDIATE and compare-and-swap inside one SQLite
    transaction, so concurrent writers cannot silently overwrite one another.
    The database path is explicit and must refer to a filesystem database;
    in-memory and SQLite URI modes are intentionally unsupported.
    """

    def __init__(self, database_path: str | Path, *, timeout_seconds: float = 5.0):
        if isinstance(database_path, str) and not database_path.strip():
            raise ValueError("database_path must be a non-empty filesystem path")
        raw_path = str(database_path)
        if raw_path in {":memory:", ""} or raw_path.startswith("file:"):
            raise ValueError("database_path must be a filesystem path, not a SQLite URI")
        if isinstance(timeout_seconds, bool) or not isinstance(timeout_seconds, (int, float)) or not isfinite(timeout_seconds) or timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be a positive number")
        self.database_path = Path(database_path).expanduser().resolve()
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self.timeout_seconds = float(timeout_seconds)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(
            str(self.database_path), timeout=self.timeout_seconds,
            isolation_level=None,
        )
        connection.execute(f"PRAGMA busy_timeout = {int(self.timeout_seconds * 1000)}")
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA synchronous = FULL")
        return connection

    def _initialize(self) -> None:
        with closing(self._connect()) as connection:
            existing_version = int(connection.execute("PRAGMA user_version").fetchone()[0])
            if existing_version > _STORE_SCHEMA_VERSION:
                raise FeatureHistoryStoreIntegrityError("database schema version is newer than this implementation")
            connection.execute("PRAGMA journal_mode = WAL")
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS feature_history_revisions (
                    history_id TEXT NOT NULL,
                    revision INTEGER NOT NULL CHECK (revision > 0),
                    parent_sha256 TEXT,
                    snapshot_json TEXT NOT NULL,
                    content_sha256 TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    PRIMARY KEY (history_id, revision),
                    UNIQUE (history_id, content_sha256)
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS feature_history_heads (
                    history_id TEXT PRIMARY KEY,
                    revision INTEGER NOT NULL CHECK (revision > 0),
                    content_sha256 TEXT NOT NULL,
                    FOREIGN KEY (history_id, revision)
                      REFERENCES feature_history_revisions(history_id, revision)
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS feature_history_navigation (
                    history_id TEXT PRIMARY KEY,
                    undo_stack_json TEXT NOT NULL,
                    redo_stack_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY (history_id)
                      REFERENCES feature_history_heads(history_id)
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS feature_history_revision_actions (
                    history_id TEXT NOT NULL,
                    revision INTEGER NOT NULL,
                    operation TEXT NOT NULL CHECK (operation IN ('legacy', 'create', 'edit', 'undo', 'redo')),
                    source_revision INTEGER,
                    target_revision INTEGER,
                    PRIMARY KEY (history_id, revision),
                    FOREIGN KEY (history_id, revision)
                      REFERENCES feature_history_revisions(history_id, revision)
                )
                """
            )
            # Additive, non-destructive migration for databases created before
            # persistent navigation metadata existed.
            for history_id, revision in connection.execute(
                "SELECT history_id, revision FROM feature_history_heads"
            ).fetchall():
                connection.execute(
                    """
                    INSERT OR IGNORE INTO feature_history_navigation
                      (history_id, undo_stack_json, redo_stack_json, updated_at)
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        history_id,
                        _canonical_json(list(range(1, int(revision)))),
                        "[]",
                        datetime.now(timezone.utc).isoformat(),
                    ),
                )
            connection.execute(
                """
                INSERT OR IGNORE INTO feature_history_revision_actions
                  (history_id, revision, operation, source_revision, target_revision)
                SELECT history_id, revision, 'legacy', NULL, NULL
                FROM feature_history_revisions
                """
            )
            connection.execute(f"PRAGMA user_version = {_STORE_SCHEMA_VERSION}")

    @staticmethod
    def _read_navigation_stacks(
        connection: sqlite3.Connection, history_id: str, current_revision: int
    ) -> tuple[list[int], list[int]]:
        row = connection.execute(
            "SELECT undo_stack_json, redo_stack_json FROM feature_history_navigation WHERE history_id = ?",
            (history_id,),
        ).fetchone()
        if row is None:
            undo_stack = list(range(1, current_revision))
            redo_stack: list[int] = []
            connection.execute(
                """
                INSERT INTO feature_history_navigation
                  (history_id, undo_stack_json, redo_stack_json, updated_at)
                VALUES (?, ?, ?, ?)
                """,
                (
                    history_id, _canonical_json(undo_stack), "[]",
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
            return undo_stack, redo_stack
        try:
            undo_stack = json.loads(row[0])
            redo_stack = json.loads(row[1])
        except (TypeError, json.JSONDecodeError) as exc:
            raise FeatureHistoryStoreIntegrityError("navigation stack JSON is invalid") from exc
        if not isinstance(undo_stack, list) or not isinstance(redo_stack, list):
            raise FeatureHistoryStoreIntegrityError("navigation stacks must be JSON arrays")
        for stack in (undo_stack, redo_stack):
            if any(
                isinstance(item, bool) or not isinstance(item, int)
                or item < 1 or item >= current_revision
                for item in stack
            ) or len(stack) != len(set(stack)):
                raise FeatureHistoryStoreIntegrityError("navigation stack contains an invalid revision")
        if set(undo_stack).intersection(redo_stack):
            raise FeatureHistoryStoreIntegrityError("a revision cannot be in both navigation stacks")
        return undo_stack, redo_stack

    @staticmethod
    def _write_navigation_stacks(
        connection: sqlite3.Connection,
        history_id: str,
        undo_stack: list[int],
        redo_stack: list[int],
    ) -> None:
        connection.execute(
            """
            INSERT INTO feature_history_navigation
              (history_id, undo_stack_json, redo_stack_json, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(history_id) DO UPDATE SET
              undo_stack_json = excluded.undo_stack_json,
              redo_stack_json = excluded.redo_stack_json,
              updated_at = excluded.updated_at
            """,
            (
                history_id, _canonical_json(undo_stack), _canonical_json(redo_stack),
                datetime.now(timezone.utc).isoformat(),
            ),
        )

    def get_navigation_state(self, history_id: str) -> FeatureHistoryNavigationState:
        if not isinstance(history_id, str) or not _HISTORY_ID.fullmatch(history_id):
            raise ValueError("history_id must be a stable lowercase identifier")
        with closing(self._connect()) as connection:
            head = connection.execute(
                "SELECT revision FROM feature_history_heads WHERE history_id = ?",
                (history_id,),
            ).fetchone()
            if head is None:
                raise KeyError(history_id)
            current_revision = int(head[0])
            undo_stack, redo_stack = self._read_navigation_stacks(
                connection, history_id, current_revision
            )
        return FeatureHistoryNavigationState(
            history_id, current_revision, bool(undo_stack), bool(redo_stack),
            len(undo_stack), len(redo_stack),
        )

    def save(
        self,
        history: FeatureHistory,
        *,
        expected_revision: int,
    ) -> FeatureHistoryRevision:
        """Append a new immutable revision if expected_revision is still head.

        Use expected_revision=0 to create a history for the first time.
        """
        if not isinstance(history, FeatureHistory):
            raise InvalidModelError("save requires a FeatureHistory")
        if isinstance(expected_revision, bool) or not isinstance(expected_revision, int) or expected_revision < 0:
            raise ValueError("expected_revision must be a non-negative integer")
        snapshot_json = _canonical_json(history.to_dict())
        now = datetime.now(timezone.utc).isoformat()
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT revision, content_sha256 FROM feature_history_heads WHERE history_id = ?",
                (history.history_id,),
            ).fetchone()
            current_revision = int(row[0]) if row else 0
            if current_revision != expected_revision:
                raise FeatureHistoryRevisionConflict(
                    history.history_id, expected_revision, current_revision
                )
            undo_stack, _redo_stack = self._read_navigation_stacks(
                connection, history.history_id, current_revision
            ) if current_revision else ([], [])
            if current_revision:
                undo_stack.append(current_revision)
            redo_stack: list[int] = []
            revision = current_revision + 1
            parent_sha256 = str(row[1]) if row else None
            digest = _revision_digest(
                history.history_id, revision, parent_sha256, snapshot_json
            )
            connection.execute(
                """
                INSERT INTO feature_history_revisions
                  (history_id, revision, parent_sha256, snapshot_json, content_sha256, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (history.history_id, revision, parent_sha256, snapshot_json, digest, now),
            )
            connection.execute(
                """
                INSERT INTO feature_history_heads (history_id, revision, content_sha256)
                VALUES (?, ?, ?)
                ON CONFLICT(history_id) DO UPDATE SET
                  revision = excluded.revision,
                  content_sha256 = excluded.content_sha256
                """,
                (history.history_id, revision, digest),
            )
            connection.execute(
                """
                INSERT INTO feature_history_revision_actions
                  (history_id, revision, operation, source_revision, target_revision)
                VALUES (?, ?, ?, ?, NULL)
                """,
                (
                    history.history_id, revision,
                    "create" if current_revision == 0 else "edit",
                    current_revision or None,
                ),
            )
            self._write_navigation_stacks(
                connection, history.history_id, undo_stack, redo_stack
            )
            connection.execute("COMMIT")
        except Exception:
            if connection.in_transaction:
                connection.execute("ROLLBACK")
            raise
        finally:
            connection.close()
        return FeatureHistoryRevision(
            history.history_id, revision, parent_sha256, digest, now, history,
            "create" if expected_revision == 0 else "edit", expected_revision or None, None,
        )

    def load(
        self,
        history_id: str,
        *,
        revision: int | None = None,
    ) -> FeatureHistoryRevision:
        """Load and verify a revision and every preceding link in its hash chain."""
        if not isinstance(history_id, str) or not _HISTORY_ID.fullmatch(history_id):
            raise ValueError("history_id must be a stable lowercase identifier")
        if revision is not None and (
            isinstance(revision, bool) or not isinstance(revision, int) or revision < 1
        ):
            raise ValueError("revision must be a positive integer")
        with closing(self._connect()) as connection:
            head = connection.execute(
                "SELECT revision, content_sha256 FROM feature_history_heads WHERE history_id = ?",
                (history_id,),
            ).fetchone()
            if head is None:
                raise KeyError(history_id)
            target = int(head[0]) if revision is None else revision
            if target > int(head[0]):
                raise KeyError(f"{history_id}@{target}")
            rows = connection.execute(
                """
                SELECT r.revision, r.parent_sha256, r.snapshot_json, r.content_sha256,
                       r.created_at, a.operation, a.source_revision, a.target_revision
                FROM feature_history_revisions AS r
                LEFT JOIN feature_history_revision_actions AS a
                  ON a.history_id = r.history_id AND a.revision = r.revision
                WHERE r.history_id = ? AND r.revision <= ?
                ORDER BY r.revision
                """,
                (history_id, target),
            ).fetchall()

        expected_parent: str | None = None
        selected: FeatureHistoryRevision | None = None
        if len(rows) != target:
            raise FeatureHistoryStoreIntegrityError("revision sequence is incomplete")
        for expected_number, row in enumerate(rows, start=1):
            stored_number, parent, snapshot_json, stored_digest, created_at, operation, source_revision, target_revision = row
            if int(stored_number) != expected_number or parent != expected_parent:
                raise FeatureHistoryStoreIntegrityError("revision sequence or parent digest is invalid")
            if not isinstance(snapshot_json, str):
                raise FeatureHistoryStoreIntegrityError("revision snapshot is not text")
            try:
                snapshot = json.loads(snapshot_json)
                canonical = _canonical_json(snapshot)
                if canonical != snapshot_json:
                    raise FeatureHistoryStoreIntegrityError("revision snapshot is not canonical JSON")
                calculated = _revision_digest(
                    history_id, expected_number, parent, snapshot_json
                )
                if calculated != stored_digest or not _HEX_DIGEST.fullmatch(str(stored_digest)):
                    raise FeatureHistoryStoreIntegrityError("revision content digest mismatch")
                history = FeatureHistory.from_dict(snapshot)
            except FeatureHistoryStoreIntegrityError:
                raise
            except Exception as exc:
                raise FeatureHistoryStoreIntegrityError("revision snapshot failed schema validation") from exc
            if history.history_id != history_id:
                raise FeatureHistoryStoreIntegrityError("snapshot history_id does not match its record")
            selected = FeatureHistoryRevision(
                history_id, expected_number, parent, stored_digest, created_at, history,
                operation or "legacy", source_revision, target_revision,
            )
            expected_parent = stored_digest
        if selected is None:
            raise FeatureHistoryStoreIntegrityError("requested revision is missing")
        if target == int(head[0]) and selected.content_sha256 != head[1]:
            raise FeatureHistoryStoreIntegrityError("head digest does not match the latest revision")
        return selected

    def undo(self, history_id: str, *, expected_revision: int) -> FeatureHistoryRevision:
        """Append a new revision restoring the next persistent Undo target."""
        return self._restore_from_navigation_stack(
            history_id, expected_revision=expected_revision, operation="undo"
        )

    def redo(self, history_id: str, *, expected_revision: int) -> FeatureHistoryRevision:
        """Append a new revision restoring the next persistent Redo target."""
        return self._restore_from_navigation_stack(
            history_id, expected_revision=expected_revision, operation="redo"
        )

    def _restore_from_navigation_stack(
        self, history_id: str, *, expected_revision: int, operation: str
    ) -> FeatureHistoryRevision:
        if not isinstance(history_id, str) or not _HISTORY_ID.fullmatch(history_id):
            raise ValueError("history_id must be a stable lowercase identifier")
        if isinstance(expected_revision, bool) or not isinstance(expected_revision, int) or expected_revision < 1:
            raise ValueError("expected_revision must be a positive integer")
        if operation not in {"undo", "redo"}:
            raise ValueError("operation must be undo or redo")
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            head = connection.execute(
                "SELECT revision, content_sha256 FROM feature_history_heads WHERE history_id = ?",
                (history_id,),
            ).fetchone()
            if head is None:
                raise KeyError(history_id)
            current_revision = int(head[0])
            if current_revision != expected_revision:
                raise FeatureHistoryRevisionConflict(
                    history_id, expected_revision, current_revision
                )
            undo_stack, redo_stack = self._read_navigation_stacks(
                connection, history_id, current_revision
            )
            source_stack = undo_stack if operation == "undo" else redo_stack
            destination_stack = redo_stack if operation == "undo" else undo_stack
            if not source_stack:
                raise FeatureHistoryNavigationUnavailable(
                    "NO_UNDO" if operation == "undo" else "NO_REDO"
                )
            target_revision = source_stack.pop()
            destination_stack.append(current_revision)

            # The target is immutable. load() validates the complete revision
            # hash chain before its snapshot is copied into the new head.
            target = self.load(history_id, revision=target_revision)
            history = target.history
            snapshot_json = _canonical_json(history.to_dict())
            now = datetime.now(timezone.utc).isoformat()
            revision = current_revision + 1
            parent_sha256 = str(head[1])
            digest = _revision_digest(
                history_id, revision, parent_sha256, snapshot_json
            )
            connection.execute(
                """
                INSERT INTO feature_history_revisions
                  (history_id, revision, parent_sha256, snapshot_json, content_sha256, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (history_id, revision, parent_sha256, snapshot_json, digest, now),
            )
            connection.execute(
                """
                UPDATE feature_history_heads
                SET revision = ?, content_sha256 = ?
                WHERE history_id = ?
                """,
                (revision, digest, history_id),
            )
            connection.execute(
                """
                INSERT INTO feature_history_revision_actions
                  (history_id, revision, operation, source_revision, target_revision)
                VALUES (?, ?, ?, ?, ?)
                """,
                (history_id, revision, operation, current_revision, target_revision),
            )
            self._write_navigation_stacks(
                connection, history_id, undo_stack, redo_stack
            )
            connection.execute("COMMIT")
        except Exception:
            if connection.in_transaction:
                connection.execute("ROLLBACK")
            raise
        finally:
            connection.close()
        return FeatureHistoryRevision(
            history_id, revision, parent_sha256, digest, now, history,
            operation, current_revision, target_revision,
        )

    def list_revisions(self, history_id: str) -> tuple[int, ...]:
        """Return immutable revision numbers currently stored for a history."""
        if not isinstance(history_id, str) or not _HISTORY_ID.fullmatch(history_id):
            raise ValueError("history_id must be a stable lowercase identifier")
        with closing(self._connect()) as connection:
            rows = connection.execute(
                "SELECT revision FROM feature_history_revisions "
                "WHERE history_id = ? ORDER BY revision",
                (history_id,),
            ).fetchall()
        return tuple(int(row[0]) for row in rows)
