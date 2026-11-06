import json

import pytest

from universal_platform.engineering.errors import InvalidModelError
from universal_platform.engineering.frame_graph import FrameGraph
from universal_platform.engineering.mesh import tessellate_extruded_profile, validate_triangle_mesh
from universal_platform.engineering.planar_boolean import PlanarRegionBooleanOperation as Operation
from universal_platform.engineering.planar_region import PlanarRegion
from universal_platform.engineering.planar_region_extrusion import (
    PlanarRegionExtrusionResult,
    extrude_planar_region,
)
from universal_platform.engineering.planar_region_set_boolean import boolean_planar_region_set
from universal_platform.engineering.primitive_geometry import PrimitiveGeometryModel, Vec2


def make_region(region_id, outer, holes=(), frame="part", unit="mm"):
    return PlanarRegion(
        region_id, frame, unit,
        tuple(Vec2(x, y) for x, y in outer),
        tuple(tuple(Vec2(x, y) for x, y in hole) for hole in holes),
    )


def test_planar_region_extrusion_preserves_holes_and_source_provenance():
    region = make_region(
        "plate", ((0, 0), (12, 0), (12, 10), (0, 10)),
        (
            ((2, 2), (2, 4), (4, 4), (4, 2)),
            ((7, 2), (7, 5), (10, 5), (10, 2)),
        ),
    )
    result = extrude_planar_region(region, "solid.plate", 3)
    assert result.source_region_id == "plate"
    assert result.source_region_sha256 == region.canonical_sha256
    assert result.solid.frame_id == region.frame_id
    assert result.solid.length_unit == region.length_unit
    assert result.solid.area == pytest.approx(region.area)
    assert len(result.solid.holes) == 2
    assert result.solid.height == 3.0


def test_planar_region_extrusion_integrates_with_analytic_volume_and_surface_area():
    region = make_region(
        "plate", ((0, 0), (12, 0), (12, 10), (0, 10)),
        (
            ((2, 2), (2, 4), (4, 4), (4, 2)),
            ((7, 2), (7, 5), (10, 5), (10, 2)),
        ),
    )
    solid = extrude_planar_region(region, "solid.plate", 3).solid
    graph = FrameGraph()
    graph.add_frame("part")
    model = PrimitiveGeometryModel(graph, (solid,))
    assert solid.area == pytest.approx(107.0)
    assert solid.perimeter == pytest.approx(64.0)
    assert model.volume("solid.plate").si_value == pytest.approx(321e-9)
    assert model.surface_area("solid.plate").si_value == pytest.approx(406e-6)


def test_planar_region_extrusion_mesh_is_closed_and_watertight_with_multiple_holes():
    region = make_region(
        "plate", ((0, 0), (12, 0), (12, 10), (0, 10)),
        (
            ((2, 2), (2, 4), (4, 4), (4, 2)),
            ((7, 2), (7, 5), (10, 5), (10, 2)),
        ),
    )
    solid = extrude_planar_region(region, "solid.plate", 3).solid
    mesh = tessellate_extruded_profile(solid)
    validation = validate_triangle_mesh(mesh)
    assert validation.valid
    assert validation.watertight
    assert validation.consistently_oriented
    assert validation.boundary_edge_count == 0
    assert validation.nonmanifold_edge_count == 0
    assert mesh.source_geometry_sha256


def test_boolean_region_set_to_extrusion_to_mesh_vertical_slice():
    operands = (
        make_region("a", ((0, 0), (4, 0), (4, 2), (0, 2))),
        make_region("b", ((3, 0), (7, 0), (7, 2), (3, 2))),
        make_region("c", ((6, 0), (10, 0), (10, 2), (6, 2))),
    )
    boolean_result = boolean_planar_region_set(operands, Operation.UNION)
    assert len(boolean_result.regions) == 1
    extrusion = extrude_planar_region(boolean_result.regions[0], "solid.chain", 5)
    assert extrusion.source_region_sha256 == boolean_result.regions[0].canonical_sha256
    mesh = tessellate_extruded_profile(extrusion.solid)
    validation = validate_triangle_mesh(mesh)
    assert validation.valid
    assert validation.watertight
    assert extrusion.solid.area == pytest.approx(20.0)
    assert extrusion.solid.height == 5.0


def test_planar_region_extrusion_snapshot_round_trip_and_tamper_rejection():
    region = make_region(
        "plate", ((0, 0), (8, 0), (8, 6), (0, 6)),
        (((2, 2), (2, 4), (4, 4), (4, 2)),),
    )
    result = extrude_planar_region(region, "solid.snapshot", 2)
    snapshot = json.loads(json.dumps(result.to_dict()))
    restored = PlanarRegionExtrusionResult.from_dict(snapshot)
    assert restored.to_dict() == result.to_dict()
    with pytest.raises(InvalidModelError, match="missing or unknown"):
        PlanarRegionExtrusionResult.from_dict(dict(snapshot, unexpected=True))
    changed = dict(snapshot)
    changed["source_region_sha256"] = "x" * 64
    with pytest.raises(InvalidModelError, match="SHA-256"):
        PlanarRegionExtrusionResult.from_dict(changed)


def test_planar_region_extrusion_rejects_wrong_input_and_invalid_height():
    with pytest.raises(InvalidModelError, match="requires a PlanarRegion"):
        extrude_planar_region(object(), "solid.invalid", 1)
    region = make_region("plate", ((0, 0), (2, 0), (2, 2), (0, 2)))
    with pytest.raises(InvalidModelError, match="height must be positive"):
        extrude_planar_region(region, "solid.invalid-height", 0)


def test_planar_region_extrusion_public_api_is_exported():
    from universal_platform.engineering import PlanarRegionExtrusionResult as PublicResult
    from universal_platform.engineering import extrude_planar_region as public_extrude
    assert PublicResult is PlanarRegionExtrusionResult
    assert public_extrude is extrude_planar_region
