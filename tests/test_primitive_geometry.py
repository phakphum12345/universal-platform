import json
from math import pi
import pytest

from universal_platform.engineering.errors import InvalidModelError
from universal_platform.engineering.frame_graph import FrameGraph
from universal_platform.engineering.geometry import Vec3
from universal_platform.engineering.primitive_geometry import (
    BoxSolid, CylinderSolid, PrimitiveGeometryModel, Vec2,
)
from universal_platform.engineering.transforms import RigidTransform


RZ90=((0.0,-1.0,0.0),(1.0,0.0,0.0),(0.0,0.0,1.0))
RY90=((0.0,0.0,1.0),(0.0,1.0,0.0),(-1.0,0.0,0.0))


def graph_with_frame(frame):
    graph=FrameGraph()
    graph.add_frame(frame)
    return graph


def test_primitive_geometry_model_v1_round_trip():
    graph=graph_with_frame("part")
    model=PrimitiveGeometryModel(graph,(
        BoxSolid("solid.box","part",Vec3(2,3,4),"mm"),
        CylinderSolid("solid.cylinder","part",1,2,"mm"),
    ))
    restored=PrimitiveGeometryModel.from_dict(json.loads(json.dumps(model.to_dict())))
    assert restored.to_dict()==model.to_dict()


def test_box_volume_surface_area_and_local_bounds_use_si_quantities():
    model=PrimitiveGeometryModel(graph_with_frame("part"),(
        BoxSolid("solid.box","part",Vec3(2,3,4),"mm"),
    ))
    assert model.volume("solid.box").si_value==pytest.approx(24e-9)
    assert model.volume("solid.box").dimension==(3,0,0,0,0)
    assert model.volume("solid.box").in_unit("m3")==pytest.approx(24e-9)
    assert model.surface_area("solid.box").si_value==pytest.approx(52e-6)
    assert model.surface_area("solid.box").in_unit("m2")==pytest.approx(52e-6)
    bounds=model.bounding_box("solid.box","part")
    assert bounds.bounds.minimum==Vec3(0,0,0)
    assert bounds.bounds.maximum==Vec3(2,3,4)
    assert bounds.length_unit=="mm"


def test_cylinder_volume_surface_area_and_local_bounds():
    model=PrimitiveGeometryModel(graph_with_frame("part"),(
        CylinderSolid("solid.cylinder","part",1,2,"mm"),
    ))
    assert model.volume("solid.cylinder").si_value==pytest.approx(2*pi*1e-9)
    assert model.surface_area("solid.cylinder").si_value==pytest.approx(6*pi*1e-6)
    bounds=model.bounding_box("solid.cylinder","part").bounds
    assert bounds.minimum==Vec3(-1,-1,0)
    assert bounds.maximum==Vec3(1,1,2)


def test_box_bounds_transform_all_corners_into_target_frame():
    graph=FrameGraph()
    graph.add_transform(RigidTransform("part","world",RZ90,Vec3(10,20,0),"mm"))
    model=PrimitiveGeometryModel(graph,(BoxSolid("solid.box","part",Vec3(2,1,1),"mm"),))
    bounds=model.bounding_box("solid.box","world")
    assert bounds.bounds.minimum==Vec3(9,20,0)
    assert bounds.bounds.maximum==Vec3(10,22,1)


def test_cylinder_bounds_use_exact_rotated_axis_extent():
    graph=FrameGraph()
    graph.add_transform(RigidTransform("part","world",RY90,Vec3(0,0,0),"mm"))
    model=PrimitiveGeometryModel(graph,(CylinderSolid("solid.cylinder","part",1,2,"mm"),))
    bounds=model.bounding_box("solid.cylinder","world")
    assert bounds.bounds.minimum==Vec3(0,-1,-1)
    assert bounds.bounds.maximum==Vec3(2,1,1)


def test_model_rejects_duplicate_solids_unknown_frames_and_mixed_units():
    graph=FrameGraph()
    graph.add_transform(RigidTransform("part","world",length_unit="mm"))
    solid=BoxSolid("solid.box","part",Vec3(1,1,1),"mm")
    with pytest.raises(InvalidModelError,match="solid IDs"):
        PrimitiveGeometryModel(graph,(solid,solid))
    with pytest.raises(InvalidModelError,match="unknown frame"):
        PrimitiveGeometryModel(graph,(BoxSolid("solid.bad","missing",Vec3(1,1,1),"mm"),))
    with pytest.raises(InvalidModelError,match="length units must match"):
        PrimitiveGeometryModel(graph,(BoxSolid("solid.mixed","part",Vec3(1,1,1),"m"),))


def test_primitive_geometry_rejects_invalid_dimensions_and_units():
    with pytest.raises(InvalidModelError):
        BoxSolid("solid.box","part",Vec3(1,-1,1),"m")
    with pytest.raises(InvalidModelError):
        CylinderSolid("solid.cyl","part",True,1,"m")
    with pytest.raises(InvalidModelError):
        CylinderSolid("solid.cyl","part",1,1,"s")


def test_snapshot_rejects_unknown_schema_and_solid_kind():
    graph=graph_with_frame("part")
    model=PrimitiveGeometryModel(graph,(BoxSolid("solid.box","part",Vec3(1,1,1)),))
    data=model.to_dict()
    with pytest.raises(InvalidModelError,match="schema_version"):
        PrimitiveGeometryModel.from_dict(dict(data,schema_version="2.0"))
    data["solids"][0]["kind"]="MESH"
    with pytest.raises(InvalidModelError,match="Unsupported primitive"):
        PrimitiveGeometryModel.from_dict(data)



def test_extruded_profile_volume_surface_area_and_round_trip():
    from universal_platform.engineering.primitive_geometry import ExtrudedProfileSolid, Vec2
    profile = (Vec2(0, 0), Vec2(2, 0), Vec2(2, 1), Vec2(0, 1))
    solid = ExtrudedProfileSolid("solid.extrude", "part", profile, 3, "mm")
    model = PrimitiveGeometryModel(graph_with_frame("part"), (solid,))
    restored = PrimitiveGeometryModel.from_dict(json.loads(json.dumps(model.to_dict())))
    assert restored.to_dict() == model.to_dict()
    assert model.volume("solid.extrude").si_value == pytest.approx(6e-9)
    assert model.volume("solid.extrude").in_unit("m3") == pytest.approx(6e-9)
    assert model.surface_area("solid.extrude").si_value == pytest.approx(22e-6)
    assert model.surface_area("solid.extrude").in_unit("m2") == pytest.approx(22e-6)


def test_extruded_concave_profile_area_and_local_bounds():
    from universal_platform.engineering.primitive_geometry import ExtrudedProfileSolid, Vec2
    profile = (Vec2(0, 0), Vec2(2, 0), Vec2(2, 1), Vec2(1, 1), Vec2(1, 2), Vec2(0, 2))
    solid = ExtrudedProfileSolid("solid.l-bracket", "part", profile, 2, "mm")
    model = PrimitiveGeometryModel(graph_with_frame("part"), (solid,))
    assert solid.area == pytest.approx(3)
    assert solid.perimeter == pytest.approx(8)
    bounds = model.bounding_box("solid.l-bracket", "part").bounds
    assert bounds.minimum == Vec3(0, 0, 0)
    assert bounds.maximum == Vec3(2, 2, 2)


def test_extruded_profile_bounds_transform_vertices_to_world():
    from universal_platform.engineering.primitive_geometry import ExtrudedProfileSolid, Vec2
    graph = FrameGraph()
    graph.add_transform(RigidTransform("part", "world", RZ90, Vec3(10, 20, 0), "mm"))
    profile = (Vec2(0, 0), Vec2(2, 0), Vec2(2, 1), Vec2(0, 1))
    model = PrimitiveGeometryModel(graph, (ExtrudedProfileSolid("solid.plate", "part", profile, 3, "mm"),))
    bounds = model.bounding_box("solid.plate", "world").bounds
    assert bounds.minimum == Vec3(9, 20, 0)
    assert bounds.maximum == Vec3(10, 22, 3)


def test_extruded_profile_rejects_self_intersection_degenerate_and_duplicate_vertices():
    from universal_platform.engineering.primitive_geometry import ExtrudedProfileSolid, Vec2
    with pytest.raises(InvalidModelError, match="self-intersecting"):
        ExtrudedProfileSolid("solid.bad", "part",
            (Vec2(0, 0), Vec2(2, 2), Vec2(0, 2), Vec2(2, 0)), 1)
    with pytest.raises(InvalidModelError, match="area must be positive"):
        ExtrudedProfileSolid("solid.flat", "part",
            (Vec2(0, 0), Vec2(1, 1), Vec2(2, 2)), 1)
    with pytest.raises(InvalidModelError, match="duplicate vertices"):
        ExtrudedProfileSolid("solid.duplicate", "part",
            (Vec2(0, 0), Vec2(1, 0), Vec2(1, 0), Vec2(0, 1)), 1)
    with pytest.raises(InvalidModelError, match="height must be positive"):
        ExtrudedProfileSolid("solid.height", "part",
            (Vec2(0, 0), Vec2(1, 0), Vec2(0, 1)), 0)


def test_extruded_profile_through_hole_area_surface_and_snapshot():
    from universal_platform.engineering.primitive_geometry import ExtrudedProfileSolid, Vec2
    outer = (Vec2(0, 0), Vec2(10, 0), Vec2(10, 8), Vec2(0, 8))
    hole = (Vec2(2, 2), Vec2(2, 4), Vec2(5, 4), Vec2(5, 2))
    solid = ExtrudedProfileSolid("solid.plate-hole", "part", outer, 3, "mm", (hole,))
    model = PrimitiveGeometryModel(graph_with_frame("part"), (solid,))
    assert solid.area == pytest.approx(74.0)
    assert solid.perimeter == pytest.approx(46.0)
    assert model.volume("solid.plate-hole").si_value == pytest.approx(222e-9)
    assert model.surface_area("solid.plate-hole").si_value == pytest.approx(286e-6)
    restored = PrimitiveGeometryModel.from_dict(json.loads(json.dumps(model.to_dict())))
    assert restored.to_dict() == model.to_dict()


def test_extruded_profile_supports_multiple_disjoint_holes():
    from universal_platform.engineering.primitive_geometry import ExtrudedProfileSolid, Vec2
    outer = (Vec2(0, 0), Vec2(12, 0), Vec2(12, 8), Vec2(0, 8))
    holes = (
        (Vec2(2, 2), Vec2(2, 4), Vec2(4, 4), Vec2(4, 2)),
        (Vec2(7, 2), Vec2(7, 5), Vec2(10, 5), Vec2(10, 2)),
    )
    solid = ExtrudedProfileSolid("solid.multi-hole", "part", outer, 2, "mm", holes)
    assert solid.area == pytest.approx(83.0)
    assert solid.perimeter == pytest.approx(60.0)


@pytest.mark.parametrize("holes", [
    ((Vec2(0, 2), Vec2(0, 4), Vec2(2, 4), Vec2(2, 2)),),
    ((Vec2(8, 2), Vec2(8, 4), Vec2(12, 4), Vec2(12, 2)),),
    ((Vec2(2, 2), Vec2(2, 6), Vec2(8, 6), Vec2(8, 2)),
     (Vec2(3, 3), Vec2(3, 4), Vec2(4, 4), Vec2(4, 3))),
    ((Vec2(2, 2), Vec2(2, 5), Vec2(6, 5), Vec2(6, 2)),
     (Vec2(5, 3), Vec2(5, 6), Vec2(8, 6), Vec2(8, 3))),
])
def test_extruded_profile_rejects_touching_outside_overlapping_or_nested_holes(holes):
    from universal_platform.engineering.primitive_geometry import ExtrudedProfileSolid, Vec2
    outer = (Vec2(0, 0), Vec2(10, 0), Vec2(10, 8), Vec2(0, 8))
    with pytest.raises(InvalidModelError):
        ExtrudedProfileSolid("solid.invalid-hole", "part", outer, 2, "mm", holes)


def test_extruded_profile_snapshot_remains_backward_compatible_without_holes():
    from universal_platform.engineering.primitive_geometry import ExtrudedProfileSolid, Vec2
    model = PrimitiveGeometryModel(graph_with_frame("part"), (
        ExtrudedProfileSolid("solid.legacy", "part",
            (Vec2(0, 0), Vec2(2, 0), Vec2(0, 2)), 1, "mm"),
    ))
    snapshot = model.to_dict()
    assert "holes" not in snapshot["solids"][0]
    assert PrimitiveGeometryModel.from_dict(snapshot).to_dict() == snapshot
