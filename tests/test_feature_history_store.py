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
    FeatureHistoryBranch,
    FeatureHistoryNavigationUnavailable,
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
            "DELETE FROM feature_history_revision_actions WHERE history_id = ? AND revision = 1",
            ("document.part",),
        )
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
    with pytest.raises(ValueError, match="positive number"):
        SQLiteFeatureHistoryStore(tmp_path / "invalid.db", timeout_seconds=float("nan"))
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



def test_store_undo_redo_appends_immutable_revisions_and_persists_navigation(tmp_path):
    path = tmp_path / "history.db"
    store = SQLiteFeatureHistoryStore(path)
    first = store.save(history("mesh-a"), expected_revision=0)
    second = store.save(history("mesh-b"), expected_revision=1)
    third = store.save(history("mesh-c"), expected_revision=2)

    undone_once = store.undo("document.part", expected_revision=3)
    assert undone_once.revision == 4
    assert undone_once.history == history("mesh-b")
    assert undone_once.operation == "undo"
    assert undone_once.source_revision == 3
    assert undone_once.target_revision == 2

    undone_twice = store.undo("document.part", expected_revision=4)
    assert undone_twice.revision == 5
    assert undone_twice.history == history("mesh-a")
    assert undone_twice.operation == "undo"
    assert undone_twice.target_revision == 1

    redone_once = store.redo("document.part", expected_revision=5)
    assert redone_once.revision == 6
    assert redone_once.history == history("mesh-b")
    assert redone_once.operation == "redo"
    assert redone_once.target_revision == 4

    redone_twice = store.redo("document.part", expected_revision=6)
    assert redone_twice.revision == 7
    assert redone_twice.history == history("mesh-c")
    assert redone_twice.operation == "redo"
    assert redone_twice.target_revision == 3

    assert store.list_revisions("document.part") == (1, 2, 3, 4, 5, 6, 7)
    assert store.load("document.part", revision=1).content_sha256 == first.content_sha256
    assert store.load("document.part", revision=2).content_sha256 == second.content_sha256
    assert store.load("document.part", revision=3).content_sha256 == third.content_sha256

    reopened = SQLiteFeatureHistoryStore(path)
    state = reopened.get_navigation_state("document.part")
    assert state.current_revision == 7
    assert state.can_undo is True
    assert state.can_redo is False
    assert state.undo_depth == 2
    assert state.redo_depth == 0


def test_store_new_edit_after_undo_clears_redo_and_stale_undo_is_atomic(tmp_path):
    store = SQLiteFeatureHistoryStore(tmp_path / "history.db")
    store.save(history("mesh-a"), expected_revision=0)
    store.save(history("mesh-b"), expected_revision=1)
    store.save(history("mesh-c"), expected_revision=2)

    with pytest.raises(FeatureHistoryRevisionConflict):
        store.undo("document.part", expected_revision=2)
    before = store.get_navigation_state("document.part")
    assert before.undo_depth == 2
    assert before.redo_depth == 0

    store.undo("document.part", expected_revision=3)
    state_after_undo = store.get_navigation_state("document.part")
    assert state_after_undo.can_redo is True
    assert state_after_undo.redo_depth == 1

    edited = store.save(history("mesh-new"), expected_revision=4)
    assert edited.revision == 5
    state_after_edit = store.get_navigation_state("document.part")
    assert state_after_edit.can_redo is False
    assert state_after_edit.redo_depth == 0
    with pytest.raises(FeatureHistoryNavigationUnavailable) as error:
        store.redo("document.part", expected_revision=5)
    assert error.value.code == "NO_REDO"


def test_store_reports_empty_undo_and_redo_stacks(tmp_path):
    store = SQLiteFeatureHistoryStore(tmp_path / "history.db")
    store.save(history(), expected_revision=0)
    with pytest.raises(FeatureHistoryNavigationUnavailable) as undo_error:
        store.undo("document.part", expected_revision=1)
    assert undo_error.value.code == "NO_UNDO"
    with pytest.raises(FeatureHistoryNavigationUnavailable) as redo_error:
        store.redo("document.part", expected_revision=1)
    assert redo_error.value.code == "NO_REDO"


def test_store_backfills_navigation_for_existing_revision_chain_without_rewriting_it(tmp_path):
    path = tmp_path / "history.db"
    store = SQLiteFeatureHistoryStore(path)
    first = store.save(history("mesh-a"), expected_revision=0)
    second = store.save(history("mesh-b"), expected_revision=1)
    with sqlite3.connect(path) as connection:
        connection.execute("DROP TABLE feature_history_navigation")

    migrated = SQLiteFeatureHistoryStore(path)
    state = migrated.get_navigation_state("document.part")
    assert state.current_revision == 2
    assert state.undo_depth == 1
    assert state.redo_depth == 0
    assert migrated.load("document.part", revision=1).content_sha256 == first.content_sha256
    assert migrated.load("document.part", revision=2).content_sha256 == second.content_sha256
    restored = migrated.undo("document.part", expected_revision=2)
    assert restored.history == history("mesh-a")
    assert restored.operation == "undo"


def test_store_fails_closed_on_corrupt_navigation_stack_json(tmp_path):
    path = tmp_path / "history.db"
    store = SQLiteFeatureHistoryStore(path)
    store.save(history("mesh-a"), expected_revision=0)
    store.save(history("mesh-b"), expected_revision=1)
    with sqlite3.connect(path) as connection:
        connection.execute(
            "UPDATE feature_history_navigation SET undo_stack_json = ? WHERE history_id = ?",
            ("{invalid", "document.part"),
        )
    reopened = SQLiteFeatureHistoryStore(path)
    with pytest.raises(FeatureHistoryStoreIntegrityError, match="navigation stack JSON is invalid"):
        reopened.get_navigation_state("document.part")



def test_store_fails_closed_when_navigation_stack_target_is_missing(tmp_path):
    path = tmp_path / "history.db"
    store = SQLiteFeatureHistoryStore(path)
    store.save(history("mesh-a"), expected_revision=0)
    store.save(history("mesh-b"), expected_revision=1)
    store.save(history("mesh-c"), expected_revision=2)
    with sqlite3.connect(path) as connection:
        connection.execute(
            "DELETE FROM feature_history_revision_actions WHERE history_id = ? AND revision = 2",
            ("document.part",),
        )
        connection.execute(
            "DELETE FROM feature_history_revisions WHERE history_id = ? AND revision = 2",
            ("document.part",),
        )
    reopened = SQLiteFeatureHistoryStore(path)
    with pytest.raises(FeatureHistoryStoreIntegrityError, match="references a missing revision"):
        reopened.get_navigation_state("document.part")



def test_store_forks_exact_immutable_revision_into_independent_branch(tmp_path):
    store = SQLiteFeatureHistoryStore(tmp_path / "history.db")
    first = store.save(history("mesh-a"), expected_revision=0)
    store.save(history("mesh-b"), expected_revision=1)

    branch = store.create_branch(
        "document.part", "document.part.experiment", "experiment", fork_revision=1
    )

    assert branch.root_history_id == "document.part"
    assert branch.branch_history_id == "document.part.experiment"
    assert branch.branch_name == "experiment"
    assert branch.fork_revision == first.revision
    assert branch.fork_sha256 == first.content_sha256
    forked = store.load("document.part.experiment")
    assert forked.revision == 1
    assert forked.history.history_id == "document.part.experiment"
    assert tuple(node.feature_id for node in forked.history.nodes) == ("mesh-a",)
    assert store.load("document.part").revision == 2
    assert store.list_revisions("document.part") == (1, 2)
    assert store.list_revisions("document.part.experiment") == (1,)
    assert store.get_branch("document.part.experiment") == branch
    assert store.list_branches("document.part") == (branch,)


def test_store_branch_creation_preserves_suppression_and_source_independence(tmp_path):
    store = SQLiteFeatureHistoryStore(tmp_path / "history.db")
    suppressed = FeatureHistory(
        "document.part",
        (
            FeatureNode.create("base", FeatureKind.MESH),
            FeatureNode.create("dependent", FeatureKind.MESH, ("base",)),
        ),
        ("dependent",),
        ("base", "dependent"),
        "1.1",
    )
    store.save(suppressed, expected_revision=0)
    branch = store.create_branch("document.part", "document.part.try", "try")

    assert store.load(branch.branch_history_id).history.suppressed_feature_ids == ("base", "dependent")
    store.save(history("new-root-feature"), expected_revision=1)
    assert store.load(branch.branch_history_id).revision == 1
    assert store.load(branch.root_history_id).revision == 2


def test_store_rejects_invalid_or_duplicate_branch_identity_and_name(tmp_path):
    store = SQLiteFeatureHistoryStore(tmp_path / "history.db")
    store.save(history(), expected_revision=0)
    with pytest.raises(ValueError, match="branch_name"):
        store.create_branch("document.part", "document.part.bad", "Bad Name")
    with pytest.raises(ValueError, match="branch_history_id"):
        store.create_branch("document.part", "document.part", "other")
    store.create_branch("document.part", "document.part.one", "experiment")
    with pytest.raises(ValueError, match="branch_history_id already exists"):
        store.create_branch("document.part", "document.part.one", "second")
    with pytest.raises(ValueError, match="branch_name already exists"):
        store.create_branch("document.part", "document.part.two", "experiment")
    with pytest.raises(ValueError, match="branching from another branch"):
        store.create_branch("document.part.one", "document.part.nested", "nested")
    with pytest.raises(ValueError, match="fork_revision"):
        store.create_branch("document.part", "document.part.invalid", "invalid", fork_revision=0)


def test_store_additive_schema_migration_preserves_revisions_and_creates_branch_catalog(tmp_path):
    path = tmp_path / "history.db"
    store = SQLiteFeatureHistoryStore(path)
    original = store.save(history(), expected_revision=0)
    with sqlite3.connect(path) as connection:
        connection.execute("DROP TABLE feature_history_branches")
        connection.execute("PRAGMA user_version = 1")

    migrated = SQLiteFeatureHistoryStore(path)
    assert migrated.load("document.part").content_sha256 == original.content_sha256
    assert migrated.list_revisions("document.part") == (1,)
    assert migrated.list_branches("document.part") == ()
    with sqlite3.connect(path) as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 2
        assert connection.execute(
            "SELECT content_sha256 FROM feature_history_revisions WHERE history_id = ? AND revision = 1",
            ("document.part",),
        ).fetchone()[0] == original.content_sha256
