"""Local, immutable SQLite cache for validated FeatureArtifact snapshots.

The cache stores canonical JSON only. Every load verifies the record envelope,
artifact content digest, schema-specific reconstruction and geometry validation.
Its SHA-256 values detect accidental or partial tampering; they are not signatures
and do not protect against an attacker who can rewrite the entire database.
"""
from __future__ import annotations

from contextlib import closing
from hashlib import sha256
import json
from math import isfinite
from pathlib import Path
import re
import sqlite3
from typing import Final

from .errors import InvalidModelError
from .feature_history import FeatureArtifact

_CACHE_SCHEMA_VERSION: Final[int] = 1
_HISTORY_ID: Final[re.Pattern[str]] = re.compile(r"^[a-z0-9]+(?:[._/-][a-z0-9]+)*$")
_FEATURE_ID: Final[re.Pattern[str]] = re.compile(r"^[a-z0-9]+(?:[._/-][a-z0-9]+)*$")
_HEX_DIGEST: Final[re.Pattern[str]] = re.compile(r"^[0-9a-f]{64}$")


class FeatureArtifactCacheIntegrityError(RuntimeError):
    """Raised when a persisted artifact record fails integrity or schema checks."""


def _canonical_json(value: object) -> str:
    try:
        return json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise InvalidModelError("feature artifact snapshot must be finite JSON data") from exc


def _record_digest(
    history_id: str,
    feature_id: str,
    computation_sha256: str,
    artifact_json: str,
) -> str:
    envelope = {
        "schema_version": _CACHE_SCHEMA_VERSION,
        "history_id": history_id,
        "feature_id": feature_id,
        "computation_sha256": computation_sha256,
        "artifact": json.loads(artifact_json),
    }
    return sha256(_canonical_json(envelope).encode("utf-8")).hexdigest()


class SQLiteFeatureArtifactCache:
    """Append-only local artifact cache keyed by history, feature and computation.

    The cache is optional. A caller may pass it to regenerate_feature_history;
    only artifacts with an exact computation-signature match are rehydrated.
    The database path must be an explicit filesystem path; SQLite URI and
    in-memory modes are rejected.
    """

    def __init__(self, database_path: str | Path, *, timeout_seconds: float = 5.0):
        if isinstance(database_path, str) and not database_path.strip():
            raise ValueError("database_path must be a non-empty filesystem path")
        raw_path = str(database_path)
        if raw_path in {":memory:", ""} or raw_path.startswith("file:"):
            raise ValueError("database_path must be a filesystem path, not a SQLite URI")
        if (
            isinstance(timeout_seconds, bool)
            or not isinstance(timeout_seconds, (int, float))
            or not isfinite(timeout_seconds)
            or timeout_seconds <= 0
        ):
            raise ValueError("timeout_seconds must be a positive number")
        self.database_path = Path(database_path).expanduser().resolve()
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self.timeout_seconds = float(timeout_seconds)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(
            str(self.database_path),
            timeout=self.timeout_seconds,
            isolation_level=None,
        )
        connection.execute(f"PRAGMA busy_timeout = {int(self.timeout_seconds * 1000)}")
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA synchronous = FULL")
        return connection

    def _initialize(self) -> None:
        with closing(self._connect()) as connection:
            version = int(connection.execute("PRAGMA user_version").fetchone()[0])
            if version > _CACHE_SCHEMA_VERSION:
                raise FeatureArtifactCacheIntegrityError(
                    "database schema version is newer than this implementation"
                )
            connection.execute("PRAGMA journal_mode = WAL")
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS feature_artifact_cache (
                    history_id TEXT NOT NULL,
                    feature_id TEXT NOT NULL,
                    computation_sha256 TEXT NOT NULL,
                    artifact_json TEXT NOT NULL,
                    record_sha256 TEXT NOT NULL,
                    PRIMARY KEY (history_id, feature_id, computation_sha256)
                )
                """
            )
            connection.execute(
                """
                CREATE TRIGGER IF NOT EXISTS feature_artifact_cache_no_update
                BEFORE UPDATE ON feature_artifact_cache
                BEGIN
                    SELECT RAISE(ABORT, 'feature artifact cache is append-only');
                END
                """
            )
            connection.execute(
                """
                CREATE TRIGGER IF NOT EXISTS feature_artifact_cache_no_delete
                BEFORE DELETE ON feature_artifact_cache
                BEGIN
                    SELECT RAISE(ABORT, 'feature artifact cache is append-only');
                END
                """
            )
            connection.execute(f"PRAGMA user_version = {_CACHE_SCHEMA_VERSION}")

    def save(self, history_id: str, artifact: FeatureArtifact) -> FeatureArtifact:
        """Persist a validated artifact; an identical key is an idempotent save."""
        if not isinstance(history_id, str) or not _HISTORY_ID.fullmatch(history_id):
            raise ValueError("history_id must be a stable lowercase identifier")
        if not isinstance(artifact, FeatureArtifact):
            raise InvalidModelError("save requires a FeatureArtifact")
        if not _FEATURE_ID.fullmatch(artifact.feature_id):
            raise InvalidModelError("artifact feature_id must be a stable lowercase identifier")
        # Rehydrate before persistence so the cache never accepts an unchecked
        # in-memory value or a payload inconsistent with its declared artifact kind.
        validated = FeatureArtifact.from_dict(artifact.to_dict())
        if validated.computation_sha256 != artifact.computation_sha256:
            raise InvalidModelError("artifact computation digest changed during validation")
        artifact_json = _canonical_json(validated.to_dict())
        record_sha256 = _record_digest(
            history_id, validated.feature_id, validated.computation_sha256, artifact_json
        )
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            existing = connection.execute(
                """
                SELECT artifact_json, record_sha256
                FROM feature_artifact_cache
                WHERE history_id = ? AND feature_id = ? AND computation_sha256 = ?
                """,
                (history_id, validated.feature_id, validated.computation_sha256),
            ).fetchone()
            if existing is not None:
                if existing[0] != artifact_json or existing[1] != record_sha256:
                    raise FeatureArtifactCacheIntegrityError(
                        "immutable artifact cache key already contains different content"
                    )
                connection.execute("COMMIT")
                return validated
            connection.execute(
                """
                INSERT INTO feature_artifact_cache
                  (history_id, feature_id, computation_sha256, artifact_json, record_sha256)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    history_id, validated.feature_id, validated.computation_sha256,
                    artifact_json, record_sha256,
                ),
            )
            connection.execute("COMMIT")
        except Exception:
            if connection.in_transaction:
                connection.execute("ROLLBACK")
            raise
        finally:
            connection.close()
        return validated

    def load(
        self,
        history_id: str,
        feature_id: str,
        computation_sha256: str,
    ) -> FeatureArtifact | None:
        """Load an exact computation key, or return None when no cache row exists."""
        if not isinstance(history_id, str) or not _HISTORY_ID.fullmatch(history_id):
            raise ValueError("history_id must be a stable lowercase identifier")
        if not isinstance(feature_id, str) or not _FEATURE_ID.fullmatch(feature_id):
            raise ValueError("feature_id must be a stable lowercase identifier")
        if not isinstance(computation_sha256, str) or not _HEX_DIGEST.fullmatch(computation_sha256):
            raise ValueError("computation_sha256 must be a lowercase SHA-256 digest")
        with closing(self._connect()) as connection:
            row = connection.execute(
                """
                SELECT artifact_json, record_sha256
                FROM feature_artifact_cache
                WHERE history_id = ? AND feature_id = ? AND computation_sha256 = ?
                """,
                (history_id, feature_id, computation_sha256),
            ).fetchone()
        if row is None:
            return None
        artifact_json, stored_record_digest = row
        if not isinstance(artifact_json, str) or not isinstance(stored_record_digest, str):
            raise FeatureArtifactCacheIntegrityError("cached artifact record has invalid storage types")
        try:
            snapshot = json.loads(artifact_json)
            if _canonical_json(snapshot) != artifact_json:
                raise FeatureArtifactCacheIntegrityError("cached artifact is not canonical JSON")
            calculated_record_digest = _record_digest(
                history_id, feature_id, computation_sha256, artifact_json
            )
            if calculated_record_digest != stored_record_digest or not _HEX_DIGEST.fullmatch(stored_record_digest):
                raise FeatureArtifactCacheIntegrityError("cached artifact record digest mismatch")
            artifact = FeatureArtifact.from_dict(snapshot)
        except FeatureArtifactCacheIntegrityError:
            raise
        except Exception as exc:
            raise FeatureArtifactCacheIntegrityError("cached artifact failed schema rehydration") from exc
        if artifact.feature_id != feature_id or artifact.computation_sha256 != computation_sha256:
            raise FeatureArtifactCacheIntegrityError("cached artifact key does not match its record")
        return artifact

    def count(self, history_id: str) -> int:
        """Return the number of immutable cached artifacts for a history."""
        if not isinstance(history_id, str) or not _HISTORY_ID.fullmatch(history_id):
            raise ValueError("history_id must be a stable lowercase identifier")
        with closing(self._connect()) as connection:
            row = connection.execute(
                "SELECT COUNT(*) FROM feature_artifact_cache WHERE history_id = ?",
                (history_id,),
            ).fetchone()
        return int(row[0])
