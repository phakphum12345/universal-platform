import json
import pytest

from universal_platform.engineering.errors import InvalidModelError
from universal_platform.engineering.frame_graph import FrameGraph
from universal_platform.engineering.geometry import Vec3
from universal_platform.engineering.transforms import RigidTransform


def tx(source, target, x=0.0, y=0.0, z=0.0):
    return RigidTransform(source, target, translation=Vec3(x, y, z))


def test_resolves_direct_and_composed_parent_to_child_path():
    graph = FrameGraph()
    graph.add_transform(tx("world", "base", 1.0, 0.0, 0.0))
    graph.add_transform(tx("base", "tool", 0.0, 2.0, 0.0))
    result = graph.transform_between("world", "tool")
    assert result.apply_point(Vec3(0.0, 0.0, 0.0)) == Vec3(1.0, 2.0, 0.0)


def test_resolves_reverse_path_using_inverse_edges():
    graph = FrameGraph()
    graph.add_transform(tx("world", "base", 1.0, 2.0, 3.0))
    result = graph.transform_between("base", "world")
    assert result.apply_point(Vec3(1.0, 2.0, 3.0)) == Vec3(0.0, 0.0, 0.0)


def test_resolves_sibling_frames_through_common_parent():
    graph = FrameGraph()
    graph.add_transform(tx("world", "left", 1.0, 0.0, 0.0))
    graph.add_transform(tx("world", "right", 0.0, 2.0, 0.0))
    result = graph.transform_between("left", "right")
    assert result.apply_point(Vec3(0.0, 0.0, 0.0)) == Vec3(-1.0, 2.0, 0.0)


def test_same_frame_returns_identity():
    graph = FrameGraph()
    graph.add_frame("world")
    result = graph.transform_between("world", "world")
    assert result.apply_point(Vec3(3.0, 4.0, 5.0)) == Vec3(3.0, 4.0, 5.0)


def test_reports_unknown_frame():
    graph = FrameGraph()
    graph.add_frame("world")
    with pytest.raises(InvalidModelError, match="Unknown coordinate frame"):
        graph.transform_between("world", "missing")


def test_reports_disconnected_frames():
    graph = FrameGraph()
    graph.add_frame("world")
    graph.add_frame("sensor")
    with pytest.raises(InvalidModelError, match="No coordinate-frame path"):
        graph.transform_between("world", "sensor")


def test_rejects_duplicate_frame_identifier():
    graph = FrameGraph()
    graph.add_frame("world")
    with pytest.raises(InvalidModelError, match="already exists"):
        graph.add_frame("world")


def test_rejects_second_parent_for_child():
    graph = FrameGraph()
    graph.add_transform(tx("world", "tool"))
    graph.add_transform(tx("other-root", "other-child"))
    with pytest.raises(InvalidModelError, match="already has a parent"):
        graph.add_transform(tx("other-root", "tool"))


def test_rejects_self_parent_edge():
    graph = FrameGraph()
    with pytest.raises(InvalidModelError, match="own parent"):
        graph.add_transform(tx("world", "world"))


def test_rejects_cycle_when_connecting_existing_tree_nodes():
    graph = FrameGraph()
    graph.add_transform(tx("world", "base"))
    graph.add_transform(tx("base", "tool"))
    with pytest.raises(InvalidModelError, match="cycle"):
        graph.add_transform(tx("tool", "world"))


def test_roots_and_frames_are_reported_as_immutable_views():
    graph = FrameGraph()
    graph.add_transform(tx("world", "base"))
    graph.add_frame("independent")
    assert graph.roots == frozenset({"world", "independent"})
    assert graph.frames == frozenset({"world", "base", "independent"})


def test_existing_root_can_be_attached_under_another_frame():
    graph = FrameGraph()
    graph.add_frame("world")
    graph.add_frame("sensor")
    graph.add_transform(tx("world", "sensor", 0.0, 0.0, 2.0))
    assert graph.roots == frozenset({"world"})
    assert graph.transform_between("world", "sensor").translation == Vec3(0.0, 0.0, 2.0)


def test_frame_graph_versioned_snapshot_round_trip_preserves_geometry_and_units():
    graph = FrameGraph()
    graph.add_transform(RigidTransform("world", "base", translation=Vec3(10, 0, 0), length_unit="mm"))
    graph.add_transform(RigidTransform("base", "tool", translation=Vec3(0, 20, 0), length_unit="mm"))
    snapshot = graph.to_dict()
    restored = FrameGraph.from_dict(json.loads(json.dumps(snapshot)))
    assert restored.to_dict() == snapshot
    resolved = restored.transform_between("world", "tool")
    assert resolved.length_unit == "mm"
    assert resolved.apply_point(Vec3(0, 0, 0)) == Vec3(10, 20, 0)
    assert restored.transform_between("tool", "tool").length_unit == "mm"


def test_frame_graph_snapshot_is_insertion_order_independent():
    first = FrameGraph()
    first.add_transform(RigidTransform("A", "B", length_unit="mm"))
    first.add_transform(RigidTransform("B", "C", length_unit="mm"))
    second = FrameGraph()
    second.add_transform(RigidTransform("B", "C", length_unit="mm"))
    second.add_transform(RigidTransform("A", "B", length_unit="mm"))
    assert first.to_dict() == second.to_dict()


def test_frame_graph_rejects_unknown_schema_and_undeclared_edge_frames():
    snapshot = {"schema_version": "2.0", "frames": ["A"], "transforms": []}
    with pytest.raises(InvalidModelError, match="schema_version"):
        FrameGraph.from_dict(snapshot)
    snapshot = {
        "schema_version": "1.0",
        "frames": ["A", "B"],
        "transforms": [RigidTransform("A", "C").to_dict()],
    }
    with pytest.raises(InvalidModelError, match="undeclared frame"):
        FrameGraph.from_dict(snapshot)


def test_frame_graph_rejects_duplicate_frames_cycles_and_mixed_units():
    duplicate = {"schema_version": "1.0", "frames": ["A", "A"], "transforms": []}
    with pytest.raises(InvalidModelError, match="unique"):
        FrameGraph.from_dict(duplicate)
    cycle = {
        "schema_version": "1.0",
        "frames": ["A", "B"],
        "transforms": [RigidTransform("A", "B").to_dict(), RigidTransform("B", "A").to_dict()],
    }
    with pytest.raises(InvalidModelError, match="cycle"):
        FrameGraph.from_dict(cycle)
    graph = FrameGraph()
    graph.add_transform(RigidTransform("A", "B", length_unit="mm"))
    with pytest.raises(InvalidModelError, match="one length unit"):
        graph.add_transform(RigidTransform("B", "C", length_unit="m"))
