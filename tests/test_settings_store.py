from __future__ import annotations

import sqlite3

import pytest

from universal_platform.engineering.settings_store import (
    SettingsRevisionConflict,
    SettingsStoreIntegrityError,
    SQLiteSettingsStore,
)


def test_settings_defaults_are_typed_and_scoped(tmp_path):
    store = SQLiteSettingsStore(tmp_path / "settings.sqlite3")
    record = store.get()
    assert record.revision == 0
    assert record.to_dict()["values"] == {
        "appearance.theme": "system",
        "appearance.density": "comfortable",
        "accessibility.reduced_motion": False,
    }
    assert set(record.to_dict()["sources"].values()) == {"default"}
    with pytest.raises(ValueError, match="only user settings"):
        store.get("workspace")


def test_settings_update_merges_values_and_persists_with_revision(tmp_path):
    database = tmp_path / "settings.sqlite3"
    store = SQLiteSettingsStore(database)
    updated = store.update(
        {"appearance.theme": "dark", "accessibility.reduced_motion": True},
        expected_revision=0,
    )
    assert updated.revision == 1
    assert updated.values == {
        "appearance.theme": "dark",
        "accessibility.reduced_motion": True,
    }
    assert updated.to_dict()["values"]["appearance.density"] == "comfortable"
    assert updated.to_dict()["sources"]["appearance.theme"] == "user"
    reopened = SQLiteSettingsStore(database)
    assert reopened.get().to_dict() == updated.to_dict()


def test_settings_compare_and_swap_rejects_stale_writer(tmp_path):
    store = SQLiteSettingsStore(tmp_path / "settings.sqlite3")
    store.update({"appearance.theme": "light"}, expected_revision=0)
    with pytest.raises(SettingsRevisionConflict):
        store.update({"appearance.theme": "dark"}, expected_revision=0)
    assert store.get().to_dict()["values"]["appearance.theme"] == "light"


@pytest.mark.parametrize(
    "values",
    [
        {},
        {"appearance.theme": "neon"},
        {"appearance.theme": True},
        {"accessibility.reduced_motion": "false"},
        {"security.api_token": "do-not-store"},
        {"appearance.theme": "dark", "provider.password": "do-not-store"},
    ],
)
def test_settings_reject_unknown_or_wrongly_typed_values(tmp_path, values):
    store = SQLiteSettingsStore(tmp_path / "settings.sqlite3")
    with pytest.raises(ValueError):
        store.update(values, expected_revision=0)


def test_settings_rejects_bool_revision_and_non_user_scope(tmp_path):
    store = SQLiteSettingsStore(tmp_path / "settings.sqlite3")
    with pytest.raises(ValueError):
        store.update({"appearance.theme": "dark"}, expected_revision=True)
    with pytest.raises(ValueError, match="only user settings"):
        store.update({"appearance.theme": "dark"}, expected_revision=0, scope="workspace")


def test_settings_audit_records_changed_keys_without_values(tmp_path):
    store = SQLiteSettingsStore(tmp_path / "settings.sqlite3")
    store.update({"appearance.theme": "dark"}, expected_revision=0)
    events = store.audit_events()
    assert len(events) == 1
    assert events[0]["changed_keys"] == ["appearance.theme"]
    assert "dark" not in str(events[0])
    assert store.verify_audit()


def test_settings_noop_does_not_create_revision_or_audit_event(tmp_path):
    store = SQLiteSettingsStore(tmp_path / "settings.sqlite3")
    first = store.update({"appearance.theme": "dark"}, expected_revision=0)
    second = store.update({"appearance.theme": "dark"}, expected_revision=1)
    assert second.revision == first.revision
    assert len(store.audit_events()) == 1


def test_newer_settings_schema_fails_closed(tmp_path):
    database = tmp_path / "settings.sqlite3"
    connection = sqlite3.connect(database)
    connection.execute("PRAGMA user_version = 99")
    connection.close()
    with pytest.raises(SettingsStoreIntegrityError):
        SQLiteSettingsStore(database)
