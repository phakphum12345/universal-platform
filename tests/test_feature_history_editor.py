import pytest

from universal_platform.engineering.errors import InvalidModelError
from universal_platform.engineering.feature_history import FeatureHistory, FeatureKind, FeatureNode
from universal_platform.engineering.feature_history_editor import (
    add_feature,
    remove_feature,
    replace_feature,
)


def sample_history():
    return FeatureHistory(
        "history.editor",
        (
            FeatureNode.create("base", FeatureKind.MESH),
            FeatureNode.create("branch", FeatureKind.MESH, ("base",)),
            FeatureNode.create("leaf", FeatureKind.MESH, ("branch",)),
            FeatureNode.create("independent", FeatureKind.MESH),
        ),
        ("leaf", "independent"),
    )


def test_add_feature_returns_new_history_and_can_add_an_output():
    original = sample_history()
    added = FeatureNode.create("extra", FeatureKind.MESH, ("independent",))

    updated = add_feature(original, added, make_output=True)

    assert updated is not original
    assert [node.feature_id for node in original.nodes] == [
        "base", "branch", "leaf", "independent"
    ]
    assert [node.feature_id for node in updated.nodes] == [
        "base", "branch", "leaf", "independent", "extra"
    ]
    assert updated.output_feature_ids == ("leaf", "independent", "extra")
    assert updated.topological_order() == ("base", "branch", "extra", "independent", "leaf") or set(updated.topological_order()) == {
        "base", "branch", "extra", "independent", "leaf"
    }


def test_add_feature_rejects_duplicate_ids_and_missing_dependencies():
    history = sample_history()
    with pytest.raises(InvalidModelError, match="already exists"):
        add_feature(history, FeatureNode.create("leaf", FeatureKind.MESH))
    with pytest.raises(InvalidModelError, match="missing dependency"):
        add_feature(history, FeatureNode.create("orphan", FeatureKind.MESH, ("missing",)))


def test_replace_feature_preserves_stable_identity_and_validates_new_graph():
    history = sample_history()
    replacement = FeatureNode.create("branch", FeatureKind.MESH, ("independent",), {"revision": 2})

    updated = replace_feature(history, "branch", replacement)

    assert updated.nodes[1] == replacement
    assert updated.nodes[2].input_feature_ids == ("branch",)
    assert set(updated.topological_order()) == {"base", "independent", "branch", "leaf"}
    assert history.nodes[1].parameters == {}


def test_replace_feature_rejects_renames_missing_nodes_and_invalid_dependencies():
    history = sample_history()
    with pytest.raises(InvalidModelError, match="preserve"):
        replace_feature(history, "branch", FeatureNode.create("renamed", FeatureKind.MESH))
    with pytest.raises(InvalidModelError, match="does not exist"):
        replace_feature(history, "missing", FeatureNode.create("missing", FeatureKind.MESH))
    with pytest.raises(InvalidModelError, match="missing dependency"):
        replace_feature(
            history, "branch",
            FeatureNode.create("branch", FeatureKind.MESH, ("not-present",)),
        )


def test_remove_feature_rejects_dependents_unless_cascade_is_explicit():
    history = sample_history()
    with pytest.raises(InvalidModelError, match="dependent features"):
        remove_feature(history, "branch")
    updated = remove_feature(history, "branch", cascade=True)
    assert {node.feature_id for node in updated.nodes} == {"base", "independent"}
    assert updated.output_feature_ids == ("independent",)
    assert {node.feature_id for node in history.nodes} == {
        "base", "branch", "leaf", "independent"
    }


def test_remove_leaf_updates_outputs_but_never_allows_an_outputless_history():
    history = sample_history()
    updated = remove_feature(history, "leaf")
    assert updated.output_feature_ids == ("independent",)
    assert "leaf" not in {node.feature_id for node in updated.nodes}

    only_output = FeatureHistory(
        "history.only-output",
        (FeatureNode.create("only", FeatureKind.MESH),),
        ("only",),
    )
    with pytest.raises(InvalidModelError, match="without an output"):
        remove_feature(only_output, "only")


def test_remove_feature_rejects_unknown_target():
    with pytest.raises(InvalidModelError, match="does not exist"):
        remove_feature(sample_history(), "unknown")
