import pytest

from universal_platform.engineering.errors import InvalidModelError
from universal_platform.engineering.feature_history import FeatureHistory, FeatureKind, FeatureNode, upgrade_feature_history
from universal_platform.engineering.feature_history_editor import (
    suppress_feature,
    unsuppress_feature,
)
from universal_platform.engineering.feature_history_store import SQLiteFeatureHistoryStore


def graph():
    return FeatureHistory(
        "history.suppression",
        (
            FeatureNode.create("output", FeatureKind.MESH, ("middle",)),
            FeatureNode.create("middle", FeatureKind.MESH, ("source",)),
            FeatureNode.create("source", FeatureKind.MESH),
            FeatureNode.create("alternate", FeatureKind.MESH),
        ),
        ("output", "alternate"),
    )


def test_v10_round_trip_is_preserved_and_explicit_upgrade_is_additive():
    original = graph()
    snapshot = original.to_dict()
    restored = FeatureHistory.from_dict(snapshot)

    assert restored.document_version == "1.0"
    assert restored.to_dict() == snapshot
    upgraded = upgrade_feature_history(restored)
    assert upgraded.document_version == "1.1"
    assert upgraded.to_dict()["schema_version"] == "1.1"
    assert upgraded.to_dict()["suppressed_feature_ids"] == []
    assert upgraded.nodes == original.nodes
    assert upgraded.output_feature_ids == original.output_feature_ids
    assert upgrade_feature_history(upgraded) is upgraded


def test_suppression_rejects_active_dependents_without_explicit_cascade():
    with pytest.raises(InvalidModelError, match="active dependents"):
        suppress_feature(graph(), "source")


def test_cascade_suppression_is_immutable_transitive_and_preserves_another_output():
    original = graph()
    updated = suppress_feature(original, "source", cascade=True)

    assert original.suppressed_feature_ids == ()
    assert updated.document_version == "1.1"
    assert updated.suppressed_feature_ids == ("middle", "output", "source")
    assert updated.output_feature_ids == original.output_feature_ids
    assert updated.nodes == original.nodes
    assert set(updated.output_feature_ids) - set(updated.suppressed_feature_ids) == {"alternate"}
    assert suppress_feature(updated, "source") is updated


def test_unsuppress_requires_dependencies_to_be_active_and_never_cascades():
    suppressed = suppress_feature(graph(), "source", cascade=True)

    with pytest.raises(InvalidModelError, match="dependency is suppressed"):
        unsuppress_feature(suppressed, "middle")
    source_active = unsuppress_feature(suppressed, "source")
    assert source_active.suppressed_feature_ids == ("middle", "output")
    middle_active = unsuppress_feature(source_active, "middle")
    assert middle_active.suppressed_feature_ids == ("output",)
    restored = unsuppress_feature(middle_active, "output")
    assert restored.suppressed_feature_ids == ()


def test_suppression_validates_unknown_ids_last_output_and_v11_canonical_form():
    with pytest.raises(InvalidModelError, match="does not exist"):
        suppress_feature(graph(), "missing")
    single_output = FeatureHistory(
        "history.single-output",
        (FeatureNode.create("output", FeatureKind.MESH),),
        ("output",),
    )
    with pytest.raises(InvalidModelError, match="at least one active output"):
        suppress_feature(single_output, "output")
    base = graph()
    raw = base.to_dict()
    raw["schema_version"] = "1.1"
    raw["suppressed_feature_ids"] = ["middle", "source"]
    with pytest.raises(InvalidModelError, match="active feature"):
        FeatureHistory.from_dict(raw)
    raw["suppressed_feature_ids"] = ["source", "source"]
    with pytest.raises(InvalidModelError, match="unique and lexicographically sorted"):
        FeatureHistory.from_dict(raw)


def test_v10_revision_digest_remains_valid_after_reopen_and_v11_edit(tmp_path):
    path = tmp_path / "history.sqlite3"
    store = SQLiteFeatureHistoryStore(path)
    first = store.save(graph(), expected_revision=0)

    reopened = SQLiteFeatureHistoryStore(path)
    restored = reopened.load("history.suppression")
    assert restored.content_sha256 == first.content_sha256
    assert restored.history.to_dict() == graph().to_dict()
    assert restored.history.document_version == "1.0"

    migrated = suppress_feature(restored.history, "output")
    second = reopened.save(migrated, expected_revision=1)
    assert second.revision == 2
    assert second.parent_sha256 == first.content_sha256
    assert second.history.document_version == "1.1"
    assert reopened.load("history.suppression", revision=1).content_sha256 == first.content_sha256
    assert reopened.load("history.suppression", revision=1).history.document_version == "1.0"
