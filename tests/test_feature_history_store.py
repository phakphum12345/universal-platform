from __future__ import annotations

import sqlite3
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest

from universal_platform.engineering.errors import InvalidModelError
from universal_platform.engineering.feature_history import (
    FeatureHistory, FeatureKind, FeatureNode,
)
from universal_platform.engineering.feature_history_store import (
    FeatureHistoryRevisionConflict,
    FeatureHistoryStoreIntegrityError,
    SQLiteFeatureHistoryStore,
)


def history(feature_id="mesh"):
    return FeatureHistory(
        "document.part",
        (FeatureNode.create(feature_id, FeatureKind.MESH),),
        (feature_id,),
    )


def test_store_round_trips_document_and_reopens_durable_database(tmp_path):
    path = tmp_path / "nested" / "history.sqlite3"
    first_store = SQLiteFeatureHistoryStore(path)
    saved = first_store.save(history(), expected_revision=0)

    reopened = SQLiteFeatureHistoryStore(path)
    loaded = reopened.load("document.part")

    assert saved.revision == 1
    assert loaded.revision == 1
    assert loaded.history == history()
    assert loaded.content_sha256 == saved.content_sha256
    assert loaded.parent_sha256 is None
    assert reopened.list_revisions("document.part") == (1,)


def test_store_appends_immutable_revision_chain_and_can_load_prior_revision(tmp_path):
    store = SQLiteFeatureHistoryStore(tmp_path / "history.db")
    first = store.save(history("mesh-a"), expected_revision=0)
    second_history = history("mesh-b")
    second = store.save(second_history, expected_revision=1)

    assert second.revision == 2
    assert second.parent_sha256 == first.content_sha256
    assert second.content_sha256 != first.content_sha256
    assert store.list_revisions("document.part") == (1, 2)
    assert store.load("document.part", revision=1).history == history("mesh-a")
    assert store.load("document.part").history == second_history


def test_compare_and_swap_rejects_stale_writer_without_overwriting_head(tmp_path):
    path = tmp_path / "history.db"
    first_writer = SQLiteFeatureHistoryStore(path)
    second_writer = SQLiteFeatureHistoryStore(path)
    first_writer.save(history("mesh-a"), expected_revision=0)

    with pytest.raises(FeatureHistoryRevisionConflict) as error:
        second_writer.save(history("mesh-b"), expected_revision=0)

    assert error.value.current_revision == 1
    assert first_writer.load("document.part").history == history("mesh-a")
    assert first_writer.list_revisions("document.part") == (1,)


def test_concurrent_store_instances_serialize_writes_with_sqlite_transactions(tmp_path):
    path = tmp_path / "history.db"
    left = SQLiteFeatureHistoryStore(path)
    right = SQLiteFeatureHistoryStore(path)
    left.save(history("mesh-a"), expected_revision=0)
    barrier = Barrier(2)

    def write(store, candidate):
        barrier.wait(timeout=5)
        try:
            return store.save(candidate, expected_revision=1).revision
        except FeatureHistoryRevisionConflict:
            return "conflict"

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(
            lambda pair: write(*pair),
            ((left, history("mesh-b")), (right, history("mesh-c"))),
        ))

    assert sorted(outcomes, key=str) == [2, "conflict"]
    assert left.list_revisions("document.part") == (1, 2)


def test_store_detects_snapshot_tampering(tmp_path):
    path = tmp_path / "history.db"
    store = SQLiteFeatureHistoryStore(path)
    store.save(history(), expected_revision=0)
    with sqlite3.connect(path) as connection:
        connection.execute(
            "UPDATE feature_history_revisions SET snapshot_json = ? "
            "WHERE history_id = ? AND revision = 1",
            ('{"history_id":"document.part","nodes":[],"output_feature_ids":["mesh"],"schema_version":"1.0"}', "document.part"),
        )

    with pytest.raises(FeatureHistoryStoreIntegrityError, match="digest mismatch"):
        store.load("document.part")


def test_store_detects_missing_revision_in_chain(tmp_path):
    path = tmp_path / "history.db"
    store = SQLiteFeatureHistoryStore(path)
    store.save(history("mesh-a"), expected_revision=0)
    store.save(history("mesh-b"), expected_revision=1)
    with sqlite3.connect(path) as connection:
        connection.execute(
            "DELETE FROM feature_history_revisions WHERE history_id = ? AND revision = 1",
            ("document.part",),
        )

    with pytest.raises(FeatureHistoryStoreIntegrityError, match="sequence is incomplete"):
        store.load("document.part")


def test_store_rejects_invalid_inputs_and_unknown_histories(tmp_path):
    with pytest.raises(ValueError, match="filesystem path"):
        SQLiteFeatureHistoryStore(":memory:")
    with pytest.raises(ValueError, match="filesystem path"):
        SQLiteFeatureHistoryStore("file:history.db")
    store = SQLiteFeatureHistoryStore(tmp_path / "history.db")
    with pytest.raises(ValueError, match="non-negative"):
        store.save(history(), expected_revision=-1)
    with pytest.raises(InvalidModelError, match="requires a FeatureHistory"):
        store.save(object(), expected_revision=0)
    with pytest.raises(ValueError, match="stable lowercase identifier"):
        store.load("../outside")
    with pytest.raises(KeyError):
        store.load("missing.document")


def test_store_rejects_future_revision_without_changing_head(tmp_path):
    store = SQLiteFeatureHistoryStore(tmp_path / "history.db")
    store.save(history(), expected_revision=0)
    with pytest.raises(KeyError):
        store.load("document.part", revision=2)
    assert store.list_revisions("document.part") == (1,)

def test_store_detects_head_pointer_digest_tampering(tmp_path):
    path = tmp_path / "history.db"
    store = SQLiteFeatureHistoryStore(path)
    store.save(history(), expected_revision=0)
    with sqlite3.connect(path) as connection:
        connection.execute(
            "UPDATE feature_history_heads SET content_sha256 = ? WHERE history_id = ?",
            ("0" * 64, "document.part"),
        )

    with pytest.raises(FeatureHistoryStoreIntegrityError, match="head digest"):
        store.load("document.part")
