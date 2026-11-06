import pytest

from universal_platform.engineering.errors import InvalidModelError
from universal_platform.engineering.planar_boolean import (
    PlanarRegionBooleanOperation as Operation,
    boolean_planar_regions,
)
from universal_platform.engineering.planar_region import PlanarRegion
from universal_platform.engineering.primitive_geometry import Vec2


def region(region_id, outer, holes=(), frame="part", unit="mm"):
    return PlanarRegion(
        region_id, frame, unit,
        tuple(Vec2(x, y) for x, y in outer),
        tuple(tuple(Vec2(x, y) for x, y in hole) for hole in holes),
    )


def rectangle(region_id, x0, y0, x1, y1, **kwargs):
    return region(region_id, ((x0, y0), (x1, y0), (x1, y1), (x0, y1)), **kwargs)


@pytest.mark.parametrize(("operation", "expected_area", "expected_components"), [
    (Operation.UNION, 120.0, 1),
    (Operation.INTERSECTION, 40.0, 1),
    (Operation.DIFFERENCE, 40.0, 1),
    (Operation.SYMMETRIC_DIFFERENCE, 80.0, 2),
])
def test_overlapping_rectangles_all_boolean_operations(operation, expected_area, expected_components):
    first = rectangle("first", 0, 0, 10, 8)
    second = rectangle("second", 5, 0, 15, 8)
    result = boolean_planar_regions(first, second, operation)
    assert result.area == pytest.approx(expected_area)
    assert len(result.regions) == expected_components
    assert result.segment_pair_count > 0
    assert result.max_coordinate_rounding_error == 0.0
    assert result.area_rounding_error == 0.0


def test_union_of_disjoint_regions_preserves_two_components():
    first = rectangle("first", 0, 0, 2, 2)
    second = rectangle("second", 5, 0, 7, 2)
    result = boolean_planar_regions(first, second, Operation.UNION)
    assert result.area == 8.0
    assert len(result.regions) == 2


def test_intersection_of_disjoint_regions_is_empty():
    first = rectangle("first", 0, 0, 2, 2)
    second = rectangle("second", 5, 0, 7, 2)
    result = boolean_planar_regions(first, second, Operation.INTERSECTION)
    assert result.regions == ()
    assert result.area == 0.0


def test_difference_of_contained_region_creates_a_hole():
    first = rectangle("outer", 0, 0, 10, 10)
    second = rectangle("inner", 2, 2, 4, 4)
    result = boolean_planar_regions(first, second, Operation.DIFFERENCE)
    assert len(result.regions) == 1
    assert len(result.regions[0].holes) == 1
    assert result.area == 96.0


def test_intersection_can_eliminate_an_existing_hole():
    ring = rectangle("ring", 0, 0, 10, 10, holes=(((2, 2), (2, 8), (8, 8), (8, 2)),))
    island = rectangle("island", 3, 3, 7, 7)
    result = boolean_planar_regions(ring, island, Operation.INTERSECTION)
    assert result.regions == ()
    assert result.area == 0.0


def test_union_of_edge_adjacent_regions_dissolves_shared_edge():
    first = rectangle("left", 0, 0, 2, 2)
    second = rectangle("right", 2, 0, 4, 2)
    result = boolean_planar_regions(first, second, Operation.UNION)
    assert len(result.regions) == 1
    assert result.regions[0].area_exact == 8


def test_point_touching_union_fails_closed_instead_of_guessing_topology():
    first = rectangle("first", 0, 0, 1, 1)
    second = rectangle("second", 1, 1, 2, 2)
    with pytest.raises(InvalidModelError, match="point-touching|branching"):
        boolean_planar_regions(first, second, Operation.UNION)


def test_boolean_rejects_frame_and_unit_mismatch():
    first = rectangle("first", 0, 0, 2, 2)
    wrong_frame = rectangle("second", 0, 0, 1, 1, frame="world")
    with pytest.raises(InvalidModelError, match="same frame"):
        boolean_planar_regions(first, wrong_frame, Operation.UNION)
    wrong_unit = rectangle("third", 0, 0, 1, 1, unit="cm")
    with pytest.raises(InvalidModelError, match="same frame"):
        boolean_planar_regions(first, wrong_unit, Operation.UNION)


def test_boolean_result_snapshot_is_deterministic_and_binds_inputs():
    first = rectangle("first", 0, 0, 10, 8)
    second = rectangle("second", 5, 0, 15, 8)
    a = boolean_planar_regions(first, second, Operation.INTERSECTION).to_dict()
    b = boolean_planar_regions(first, second, Operation.INTERSECTION).to_dict()
    assert a == b
    assert a["schema_version"] == "1.0"
    assert a["first_region_sha256"] == first.canonical_sha256
    assert a["second_region_sha256"] == second.canonical_sha256
    assert a["region_count"] == 1


def test_boolean_is_invariant_to_input_winding_and_cyclic_start():
    first = rectangle("first", 0, 0, 10, 8)
    reversed_first = region("first", ((10, 8), (10, 0), (0, 0), (0, 8)))
    second = rectangle("second", 5, 0, 15, 8)
    a = boolean_planar_regions(first, second, Operation.UNION).to_dict()
    b = boolean_planar_regions(reversed_first, second, Operation.UNION).to_dict()
    assert a == b


def test_union_preserves_a_hole_and_an_island_inside_that_hole_as_separate_regions():
    ring = rectangle("ring", 0, 0, 10, 10, holes=(((2, 2), (2, 8), (8, 8), (8, 2)),))
    island = rectangle("island", 3, 3, 7, 7)
    result = boolean_planar_regions(ring, island, Operation.UNION)
    assert len(result.regions) == 2
    assert sorted(len(item.holes) for item in result.regions) == [0, 1]
    assert result.area == 80.0


def test_rational_intersections_report_binary64_coordinate_and_area_error():
    triangle = region("triangle", ((0, 0), (3, 0), (0, 1)))
    strip = rectangle("strip", 1, 0, 2, 1)
    result = boolean_planar_regions(triangle, strip, Operation.INTERSECTION)
    assert result.area == pytest.approx(0.5)
    assert result.max_coordinate_rounding_error > 0.0
    assert result.area_rounding_error >= 0.0


def test_result_snapshot_round_trip_and_tamper_rejection():
    first = rectangle("first", 0, 0, 10, 8)
    second = rectangle("second", 5, 0, 15, 8)
    snapshot = boolean_planar_regions(first, second, Operation.DIFFERENCE).to_dict()
    restored = type(boolean_planar_regions(first, second, Operation.DIFFERENCE)).from_dict(snapshot)
    assert restored.to_dict() == snapshot
    with pytest.raises(InvalidModelError, match="missing or unknown"):
        restored.from_dict(dict(snapshot, extra=True))
    with pytest.raises(InvalidModelError, match="does not match"):
        restored.from_dict(dict(snapshot, area=999.0))


def test_result_schema_is_strict_and_tracks_serialized_contract():
    import json
    from pathlib import Path

    first = rectangle("first", 0, 0, 2, 2)
    second = rectangle("second", 1, 0, 3, 2)
    snapshot = boolean_planar_regions(first, second, Operation.UNION).to_dict()
    schema = json.loads((Path(__file__).parents[1] / "schemas" / "geometry" /
                         "planar-region-boolean-result.schema.json").read_text(encoding="utf-8"))
    assert set(snapshot) == set(schema["required"])
    assert schema["additionalProperties"] is False
