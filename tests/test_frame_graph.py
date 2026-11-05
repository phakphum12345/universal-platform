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
