from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

import pytest

from universal_platform.engineering.workspace_store import (
    SQLiteWorkspaceStore,
    WorkspaceNotFoundError,
    WorkspaceRevisionConflict,
    WorkspaceStoreIntegrityError,
)


def test_workspace_create_list_get_and_persist_across_reopen(tmp_path):
    database = tmp_path / "workspaces.sqlite3"
    store = SQLiteWorkspaceStore(database)

    created = store.create(
        " CAD Project ",
        description="  Main design  ",
        metadata={"domain": "cad", "tags": ["prototype", "mechanics"]},
    )

    assert created.name == "CAD Project"
    assert created.description == "Main design"
    assert created.revision == 1
    assert created.metadata == {"domain": "cad", "tags": ["prototype", "mechanics"]}
    assert store.get(created.workspace_id) == created
    assert store.list() == (created,)

    reopened = SQLiteWorkspaceStore(database)
    assert reopened.get(created.workspace_id) == created


def test_workspace_update_requires_current_revision_and_preserves_identity(tmp_path):
    store = SQLiteWorkspaceStore(tmp_path / "workspaces.sqlite3")
    created = store.create("Initial")

    updated = store.update(
        created.workspace_id,
        expected_revision=created.revision,
        name="Renamed",
        description="Updated description",
        metadata={"domain": "engineering"},
    )

    assert updated.workspace_id == created.workspace_id
    assert updated.created_at == created.created_at
    assert updated.name == "Renamed"
    assert updated.revision == 2
    assert updated.updated_at >= created.updated_at
    assert updated.metadata == {"domain": "engineering"}

    with pytest.raises(WorkspaceRevisionConflict):
        store.update(
            created.workspace_id,
            expected_revision=created.revision,
            name="Stale write",
        )
    assert store.get(created.workspace_id) == updated


def test_workspace_missing_identifier_is_not_found(tmp_path):
    store = SQLiteWorkspaceStore(tmp_path / "workspaces.sqlite3")
    with pytest.raises(WorkspaceNotFoundError):
        store.get("missing-workspace")
    with pytest.raises(WorkspaceNotFoundError):
        store.update(
            "missing-workspace", expected_revision=1, name="Missing"
        )


@pytest.mark.parametrize(
    ("name", "description"),
    [
        ("", ""),
        ("   ", ""),
        ("x" * 121, ""),
        ("Valid", "x" * 2001),
        ("bad\\x00name", ""),
    ],
)
def test_workspace_rejects_invalid_text(name, description, tmp_path):
    store = SQLiteWorkspaceStore(tmp_path / "workspaces.sqlite3")
    with pytest.raises(ValueError):
        store.create(name, description=description)


def test_workspace_rejects_non_json_metadata_and_non_finite_values(tmp_path):
    store = SQLiteWorkspaceStore(tmp_path / "workspaces.sqlite3")
    with pytest.raises(TypeError, match="metadata must be an object"):
        store.create("Invalid", metadata=["not", "an", "object"])
    with pytest.raises(ValueError, match="non-finite numbers"):
        store.create("Invalid", metadata={"not_finite": float("nan")})
    with pytest.raises(TypeError, match="keys must be strings"):
        store.create("Invalid", metadata={1: "coerced"})
    with pytest.raises(TypeError, match="keys must be strings"):
        store.update(
            store.create("Valid").workspace_id,
            expected_revision=1,
            name="Invalid nested key",
            metadata={"nested": [{"another": {2: "coerced"}}]},
        )


def test_workspace_list_limit_is_bounded(tmp_path):
    store = SQLiteWorkspaceStore(tmp_path / "workspaces.sqlite3")
    store.create("One")
    store.create("Two")
    assert len(store.list(limit=1)) == 1
    for invalid in (0, -1, 501, True, 1.5):
        with pytest.raises(ValueError):
            store.list(limit=invalid)


def test_concurrent_workspace_creates_keep_all_records(tmp_path):
    store = SQLiteWorkspaceStore(tmp_path / "workspaces.sqlite3")
    with ThreadPoolExecutor(max_workers=8) as pool:
        records = list(pool.map(lambda index: store.create(f"Workspace {index}"), range(20)))
    assert len({record.workspace_id for record in records}) == 20
    assert len(store.list(limit=100)) == 20


def test_newer_workspace_schema_fails_closed(tmp_path):
    import sqlite3

    database = tmp_path / "workspaces.sqlite3"
    connection = sqlite3.connect(database)
    connection.execute("PRAGMA user_version = 99")
    connection.close()

    with pytest.raises(WorkspaceStoreIntegrityError):
        SQLiteWorkspaceStore(database)
