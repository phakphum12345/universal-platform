"""Typed, scoped and revisioned local user-preference storage.

This first WP-15F slice deliberately stores non-secret user preferences only.
Provider credentials, tokens and other secrets are rejected and require a
separately approved secret-management design.
"""
from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from threading import RLock


_SCHEMA_VERSION = 1
_SCOPE = "user"
_DEFAULTS: dict[str, object] = {
    "appearance.theme": "system",
    "appearance.density": "comfortable",
    "accessibility.reduced_motion": False,
}
_ALLOWED_VALUES: dict[str, tuple[type, frozenset[object] | None]] = {
    "appearance.theme": (str, frozenset({"system", "light", "dark"})),
    "appearance.density": (str, frozenset({"comfortable", "compact"})),
    "accessibility.reduced_motion": (bool, None),
}


class SettingsStoreIntegrityError(RuntimeError):
    """Raised when settings storage or its audit chain cannot be trusted."""


class SettingsRevisionConflict(RuntimeError):
    """Raised when a settings write is based on a stale revision."""


@dataclass(frozen=True, slots=True)
class SettingsRecord:
    scope: str
    revision: int
    values: dict[str, object]
    updated_at: str | None

    def to_dict(self) -> dict[str, object]:
        effective = dict(_DEFAULTS)
        effective.update(self.values)
        return {
            "scope": self.scope,
            "revision": self.revision,
            "values": effective,
            "sources": {
                key: "user" if key in self.values else "default"
                for key in _DEFAULTS
            },
            "updated_at": self.updated_at,
        }


def _canonical_json(value: object) -> str:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"),
        ensure_ascii=False, allow_nan=False,
    )


def _validate_values(values: object) -> dict[str, object]:
    if not isinstance(values, dict) or not values:
        raise ValueError("values must be a non-empty object")
    unknown = set(values) - set(_ALLOWED_VALUES)
    if unknown:
        raise ValueError("values contains an unsupported setting key")
    normalized: dict[str, object] = {}
    for key, value in values.items():
        expected_type, allowed = _ALLOWED_VALUES[key]
        if type(value) is not expected_type:
            raise ValueError(f"{key} has an invalid value type")
        if allowed is not None and value not in allowed:
            raise ValueError(f"{key} has an unsupported value")
        normalized[key] = value
    return normalized


class SQLiteSettingsStore:
    """SQLite-backed user settings with CAS revisions and value-free audit."""

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
                raise SettingsStoreIntegrityError(
                    "settings database schema is newer than this implementation"
                )
            connection.execute("PRAGMA journal_mode = WAL")
            connection.execute(
                """CREATE TABLE IF NOT EXISTS settings_current (
                    scope TEXT PRIMARY KEY CHECK (scope = 'user'),
                    revision INTEGER NOT NULL CHECK (revision >= 0),
                    values_json TEXT NOT NULL,
                    updated_at TEXT
                )"""
            )
            connection.execute(
                """CREATE TABLE IF NOT EXISTS settings_revisions (
                    scope TEXT NOT NULL CHECK (scope = 'user'),
                    revision INTEGER NOT NULL CHECK (revision >= 1),
                    values_json TEXT NOT NULL,
                    changed_keys_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    PRIMARY KEY (scope, revision)
                )"""
            )
            connection.execute(
                """CREATE TABLE IF NOT EXISTS settings_audit (
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_json TEXT NOT NULL,
                    previous_sha256 TEXT,
                    event_sha256 TEXT NOT NULL UNIQUE
                )"""
            )
            connection.execute(
                "INSERT OR IGNORE INTO settings_current "
                "(scope, revision, values_json, updated_at) VALUES (?, 0, '{}', NULL)",
                (_SCOPE,),
            )
            connection.execute(f"PRAGMA user_version = {_SCHEMA_VERSION}")

    def get(self, scope: str = _SCOPE) -> SettingsRecord:
        if scope != _SCOPE:
            raise ValueError("only user settings are supported")
        with self._lock, closing(self._connect()) as connection:
            row = connection.execute(
                "SELECT revision, values_json, updated_at "
                "FROM settings_current WHERE scope = ?",
                (scope,),
            ).fetchone()
        if row is None:
            raise SettingsStoreIntegrityError("settings scope is missing")
        try:
            values = json.loads(row["values_json"])
        except (TypeError, json.JSONDecodeError) as exc:
            raise SettingsStoreIntegrityError("stored settings are invalid JSON") from exc
        if not isinstance(values, dict):
            raise SettingsStoreIntegrityError("stored settings must be an object")
        try:
            values = _validate_values(values) if values else {}
        except (TypeError, ValueError) as exc:
            raise SettingsStoreIntegrityError("stored settings violate the schema") from exc
        return SettingsRecord(scope, int(row["revision"]), values, row["updated_at"])

    def update(
        self, values: dict[str, object], *, expected_revision: int,
        scope: str = _SCOPE,
    ) -> SettingsRecord:
        if scope != _SCOPE:
            raise ValueError("only user settings are supported")
        if (
            isinstance(expected_revision, bool)
            or not isinstance(expected_revision, int)
            or expected_revision < 0
        ):
            raise ValueError("expected_revision must be a non-negative integer")
        updates = _validate_values(values)
        now = datetime.now(UTC).isoformat()
        with self._lock, closing(self._connect()) as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT revision, values_json, updated_at FROM settings_current WHERE scope = ?",
                (scope,),
            ).fetchone()
            if row is None:
                connection.rollback()
                raise SettingsStoreIntegrityError("settings scope is missing")
            current_revision = int(row["revision"])
            if current_revision != expected_revision:
                connection.rollback()
                raise SettingsRevisionConflict(
                    f"expected revision {expected_revision}, found {current_revision}"
                )
            current = json.loads(row["values_json"])
            merged = dict(current)
            merged.update(updates)
            changed_keys = sorted(
                key for key, value in updates.items() if current.get(key) != value
            )
            if not changed_keys:
                connection.commit()
                return SettingsRecord(scope, current_revision, current, row["updated_at"])
            revision = current_revision + 1
            encoded = _canonical_json(merged)
            changed_encoded = _canonical_json(changed_keys)
            connection.execute(
                "UPDATE settings_current SET revision = ?, values_json = ?, "
                "updated_at = ? WHERE scope = ? AND revision = ?",
                (revision, encoded, now, scope, current_revision),
            )
            connection.execute(
                "INSERT INTO settings_revisions "
                "(scope, revision, values_json, changed_keys_json, created_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (scope, revision, encoded, changed_encoded, now),
            )
            audit_row = connection.execute(
                "SELECT event_sha256 FROM settings_audit ORDER BY sequence DESC LIMIT 1"
            ).fetchone()
            previous = audit_row["event_sha256"] if audit_row else None
            event = _canonical_json({
                "scope": scope,
                "revision": revision,
                "action": "SETTINGS_UPDATED",
                "changed_keys": changed_keys,
                "timestamp": now,
            })
            digest = sha256(((previous or "") + event).encode("utf-8")).hexdigest()
            connection.execute(
                "INSERT INTO settings_audit "
                "(event_json, previous_sha256, event_sha256) VALUES (?, ?, ?)",
                (event, previous, digest),
            )
            connection.commit()
        return SettingsRecord(scope, revision, merged, now)

    def audit_events(self) -> tuple[dict[str, object], ...]:
        with self._lock, closing(self._connect()) as connection:
            rows = connection.execute(
                "SELECT event_json, previous_sha256, event_sha256 "
                "FROM settings_audit ORDER BY sequence"
            ).fetchall()
        events: list[dict[str, object]] = []
        previous: str | None = None
        for row in rows:
            encoded = row["event_json"]
            if row["previous_sha256"] != previous:
                raise SettingsStoreIntegrityError("settings audit chain is invalid")
            expected = sha256(((previous or "") + encoded).encode("utf-8")).hexdigest()
            if expected != row["event_sha256"]:
                raise SettingsStoreIntegrityError("settings audit chain is invalid")
            try:
                event = json.loads(encoded)
            except json.JSONDecodeError as exc:
                raise SettingsStoreIntegrityError("settings audit event is invalid") from exc
            if not isinstance(event, dict):
                raise SettingsStoreIntegrityError("settings audit event is invalid")
            events.append(event)
            previous = row["event_sha256"]
        return tuple(events)

    def verify_audit(self) -> bool:
        try:
            self.audit_events()
        except SettingsStoreIntegrityError:
            return False
        return True


__all__ = [
    "SQLiteSettingsStore",
    "SettingsRecord",
    "SettingsRevisionConflict",
    "SettingsStoreIntegrityError",
]
