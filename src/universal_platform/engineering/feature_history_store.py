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


@dataclass(frozen=True, slots=True)
class FeatureHistoryRevision:
    history_id: str
    revision: int
    parent_sha256: str | None
    content_sha256: str
    created_at: str
    history: FeatureHistory


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
        if isinstance(timeout_seconds, bool) or not isinstance(timeout_seconds, (int, float)) or timeout_seconds <= 0:
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
            connection.execute(f"PRAGMA user_version = {_STORE_SCHEMA_VERSION}")

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
            connection.execute("COMMIT")
        except Exception:
            if connection.in_transaction:
                connection.execute("ROLLBACK")
            raise
        finally:
            connection.close()
        return FeatureHistoryRevision(
            history.history_id, revision, parent_sha256, digest, now, history
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
                "SELECT revision FROM feature_history_heads WHERE history_id = ?",
                (history_id,),
            ).fetchone()
            if head is None:
                raise KeyError(history_id)
            target = int(head[0]) if revision is None else revision
            if target > int(head[0]):
                raise KeyError(f"{history_id}@{target}")
            rows = connection.execute(
                """
                SELECT revision, parent_sha256, snapshot_json, content_sha256, created_at
                FROM feature_history_revisions
                WHERE history_id = ? AND revision <= ?
                ORDER BY revision
                """,
                (history_id, target),
            ).fetchall()

        expected_parent: str | None = None
        selected: FeatureHistoryRevision | None = None
        if len(rows) != target:
            raise FeatureHistoryStoreIntegrityError("revision sequence is incomplete")
        for expected_number, row in enumerate(rows, start=1):
            stored_number, parent, snapshot_json, stored_digest, created_at = row
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
                history_id, expected_number, parent, stored_digest, created_at, history
            )
            expected_parent = stored_digest
        if selected is None:
            raise FeatureHistoryStoreIntegrityError("requested revision is missing")
        return selected

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
