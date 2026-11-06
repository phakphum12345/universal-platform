import json

import pytest

from universal_platform.engineering.errors import InvalidModelError
from universal_platform.engineering.frame_graph import FrameGraph
from universal_platform.engineering.framed_coordinates import FramedPoint3, FramedVector3
from universal_platform.engineering.geometry import Vec3
from universal_platform.engineering.transforms import RigidTransform


ROTATE_Z_90 = ((0.0, -1.0, 0.0), (1.0, 0.0, 0.0), (0.0, 0.0, 1.0))


def test_framed_point_and_vector_json_round_trip():
    point = FramedPoint3("tool", Vec3(1.0, 2.0, 3.0), "mm")
    vector = FramedVector3("tool", Vec3(1.0, 2.0, 3.0), "mm")
    restored_point = FramedPoint3.from_dict(json.loads(json.dumps(point.to_dict())))
    restored_vector = FramedVector3.from_dict(json.loads(json.dumps(vector.to_dict())))
    assert restored_point == point
    assert restored_vector == vector
    assert restored_point.to_dict()["kind"] == "POINT"
    assert restored_vector.to_dict()["kind"] == "VECTOR"


def test_point_transform_applies_rotation_and_translation():
    graph = FrameGraph()
    graph.add_transform(RigidTransform(
        "part", "world", ROTATE_Z_90, Vec3(10.0, 20.0, 0.0), "mm"
    ))
    point = FramedPoint3("part", Vec3(2.0, 0.0, 4.0), "mm")
    result = point.transform_to(graph, "world")
    assert result.frame_id == "world"
    assert result.length_unit == "mm"
    assert result.value == Vec3(10.0, 22.0, 4.0)


def test_vector_transform_rotates_without_translation():
    graph = FrameGraph()
    graph.add_transform(RigidTransform(
        "part", "world", ROTATE_Z_90, Vec3(10.0, 20.0, 0.0), "mm"
    ))
    vector = FramedVector3("part", Vec3(2.0, 0.0, 4.0), "mm")
    result = vector.transform_to(graph, "world")
    assert result.frame_id == "world"
    assert result.value == Vec3(0.0, 2.0, 4.0)


def test_frame_bound_values_reject_mismatched_units_and_unknown_frames():
    graph = FrameGraph()
    graph.add_transform(RigidTransform("part", "world", length_unit="mm"))
    point = FramedPoint3("part", Vec3(1, 2, 3), "m")
    with pytest.raises(InvalidModelError, match="units do not match"):
        point.transform_to(graph, "world")
    with pytest.raises(InvalidModelError, match="Unknown coordinate frame"):
        FramedPoint3("missing", Vec3(1, 2, 3)).transform_to(graph, "world")


def test_same_frame_transform_is_identity_without_unit_reinterpretation():
    graph = FrameGraph()
    graph.add_frame("local")
    point = FramedPoint3("local", Vec3(1, 2, 3), "mm")
    assert point.transform_to(graph, "local") is point


@pytest.mark.parametrize(
    "factory",
    [
        lambda: FramedPoint3("", Vec3(0, 0, 0)),
        lambda: FramedVector3("world", Vec3(0, 0, 0), "s"),
        lambda: FramedPoint3("world", (0, 0, 0)),
    ],
)
def test_frame_bound_values_reject_invalid_construction(factory):
    with pytest.raises(InvalidModelError):
        factory()


def test_framed_snapshot_rejects_wrong_kind_and_unknown_fields():
    snapshot = FramedPoint3("world", Vec3(0, 0, 0)).to_dict()
    with pytest.raises(InvalidModelError, match="kind"):
        FramedVector3.from_dict(snapshot)
    snapshot["extra"] = "not-allowed"
    with pytest.raises(InvalidModelError, match="missing or unknown"):
        FramedPoint3.from_dict(snapshot)
