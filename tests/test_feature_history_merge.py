from __future__ import annotations

from universal_platform.engineering.feature_history import FeatureHistory, FeatureKind, FeatureNode
from universal_platform.engineering.feature_history_merge import merge_feature_histories


def make_history(history_id, nodes, outputs, suppressed=(), version="1.0"):
    return FeatureHistory(history_id, tuple(nodes), tuple(outputs), tuple(suppressed), version)


def test_three_way_merge_combines_disjoint_node_changes_and_independent_additions():
    base = make_history(
        "part.root",
        (
            FeatureNode.create("a", FeatureKind.MESH, parameters={"value": 0}),
            FeatureNode.create("b", FeatureKind.MESH, parameters={"value": 0}),
        ),
        ("b",),
    )
    source = make_history(
        "part.branch.source",
        (
            FeatureNode.create("a", FeatureKind.MESH, parameters={"value": 1}),
            FeatureNode.create("b", FeatureKind.MESH, parameters={"value": 0}),
            FeatureNode.create("c", FeatureKind.MESH, ("a",)),
        ),
        ("b", "c"),
    )
    target = make_history(
        "part.branch.target",
        (
            FeatureNode.create("a", FeatureKind.MESH, parameters={"value": 0}),
            FeatureNode.create("b", FeatureKind.MESH, parameters={"value": 2}),
            FeatureNode.create("d", FeatureKind.MESH, ("a",)),
        ),
        ("b",),
    )

    result = merge_feature_histories(base, source, target)

    assert result.successful
    merged = result.merged_history
    assert merged is not None
    assert merged.history_id == target.history_id
    nodes = {node.feature_id: node for node in merged.nodes}
    assert set(nodes) == {"a", "b", "c", "d"}
    assert nodes["a"].parameters == {"value": 1}
    assert nodes["b"].parameters == {"value": 2}
    assert merged.output_feature_ids == ("b", "c")
    assert all(
        merged.topological_order().index(dependency) < merged.topological_order().index(node.feature_id)
        for node in merged.nodes for dependency in node.input_feature_ids
    )
    assert merge_feature_histories(base, source, target).merged_history == merged


def test_three_way_merge_accepts_identical_change_on_both_sides():
    base = make_history(
        "part.root",
        (FeatureNode.create("a", FeatureKind.MESH),),
        ("a",),
    )
    changed = FeatureNode.create("a", FeatureKind.MESH, parameters={"width": 4})
    source = make_history("part.source", (changed,), ("a",))
    target = make_history("part.target", (changed,), ("a",))

    result = merge_feature_histories(base, source, target)

    assert result.successful
    assert result.merged_history is not None
    assert result.merged_history.nodes == (changed,)


def test_three_way_merge_reports_divergent_same_feature_edits():
    base = make_history(
        "part.root",
        (FeatureNode.create("a", FeatureKind.MESH, parameters={"width": 1}),),
        ("a",),
    )
    source = make_history(
        "part.source",
        (FeatureNode.create("a", FeatureKind.MESH, parameters={"width": 2}),),
        ("a",),
    )
    target = make_history(
        "part.target",
        (FeatureNode.create("a", FeatureKind.MESH, parameters={"width": 3}),),
        ("a",),
    )

    result = merge_feature_histories(base, source, target)

    assert not result.successful
    assert result.merged_history is None
    assert [(item.category, item.feature_id) for item in result.conflicts] == [("node_content", "a")]


def test_three_way_merge_reports_delete_versus_edit():
    base = make_history(
        "part.root",
        (
            FeatureNode.create("a", FeatureKind.MESH),
            FeatureNode.create("b", FeatureKind.MESH),
        ),
        ("b",),
    )
    source = make_history("part.source", (FeatureNode.create("b", FeatureKind.MESH),), ("b",))
    target = make_history(
        "part.target",
        (
            FeatureNode.create("a", FeatureKind.MESH, parameters={"changed": True}),
            FeatureNode.create("b", FeatureKind.MESH),
        ),
        ("b",),
    )

    result = merge_feature_histories(base, source, target)

    assert not result.successful
    assert any(item.category == "node_content" and item.feature_id == "a" for item in result.conflicts)


def test_three_way_merge_reports_conflicting_presentation_of_shared_addition():
    base = make_history(
        "part.root",
        (
            FeatureNode.create("a", FeatureKind.MESH),
            FeatureNode.create("b", FeatureKind.MESH),
        ),
        ("b",),
    )
    shared = FeatureNode.create("c", FeatureKind.MESH)
    source = make_history(
        "part.source",
        (FeatureNode.create("a", FeatureKind.MESH), shared, FeatureNode.create("b", FeatureKind.MESH)),
        ("b",),
    )
    target = make_history(
        "part.target",
        (shared, FeatureNode.create("a", FeatureKind.MESH), FeatureNode.create("b", FeatureKind.MESH)),
        ("b",),
    )

    result = merge_feature_histories(base, source, target)

    assert not result.successful
    assert any(item.category == "presentation_order" for item in result.conflicts)


def test_three_way_merge_combines_suppression_with_disjoint_parameter_edit():
    base = make_history(
        "part.root",
        (
            FeatureNode.create("a", FeatureKind.MESH),
            FeatureNode.create("b", FeatureKind.MESH, parameters={"width": 1}),
        ),
        ("b",),
    )
    source = make_history(
        "part.source",
        (
            FeatureNode.create("a", FeatureKind.MESH),
            FeatureNode.create("b", FeatureKind.MESH, parameters={"width": 1}),
        ),
        ("b",),
        ("a",),
        "1.1",
    )
    target = make_history(
        "part.target",
        (
            FeatureNode.create("a", FeatureKind.MESH),
            FeatureNode.create("b", FeatureKind.MESH, parameters={"width": 2}),
        ),
        ("b",),
    )

    result = merge_feature_histories(base, source, target)

    assert result.successful
    assert result.merged_history is not None
    assert result.merged_history.document_version == "1.1"
    assert result.merged_history.suppressed_feature_ids == ("a",)
    assert {node.feature_id: node.parameters for node in result.merged_history.nodes}["b"] == {"width": 2}


def test_three_way_merge_rejects_same_history_id_and_returns_serializable_conflicts():
    history = make_history(
        "part.same",
        (FeatureNode.create("a", FeatureKind.MESH),),
        ("a",),
    )
    result = merge_feature_histories(history, history, history)

    assert not result.successful
    assert result.conflicts == ()
