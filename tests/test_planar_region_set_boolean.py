import json
from pathlib import Path

import pytest

from universal_platform.engineering.errors import InvalidModelError
from universal_platform.engineering.planar_boolean import PlanarRegionBooleanOperation as Operation, _stitch
from universal_platform.engineering.planar_region import PlanarRegion
from universal_platform.engineering.planar_region_set_boolean import (
    PlanarRegionSetBooleanResult,
    boolean_planar_region_set,
)
from universal_platform.engineering.primitive_geometry import Vec2


def region(region_id, x0, y0, x1, y1, frame="part", unit="mm"):
    return PlanarRegion(
        region_id, frame, unit,
        tuple(Vec2(x, y) for x, y in ((x0, y0), (x1, y0), (x1, y1), (x0, y1))),
    )


def test_three_region_union_merges_a_chain_into_one_component():
    result = boolean_planar_region_set((
        region("a", 0, 0, 4, 2),
        region("b", 3, 0, 7, 2),
        region("c", 6, 0, 10, 2),
    ), Operation.UNION)
    assert result.area == 20.0
    assert len(result.regions) == 1
    assert result.input_region_ids == ("a", "b", "c")


def test_three_region_intersection_finds_common_area():
    result = boolean_planar_region_set((
        region("outer", 0, 0, 10, 10),
        region("middle", 2, 2, 8, 8),
        region("inner", 4, 4, 6, 6),
    ), Operation.INTERSECTION)
    assert result.area == 4.0
    assert len(result.regions) == 1


def test_set_difference_subtracts_union_of_all_remaining_regions():
    result = boolean_planar_region_set((
        region("plate", 0, 0, 10, 10),
        region("cut-a", 2, 2, 4, 4),
        region("cut-b", 6, 2, 8, 4),
    ), Operation.DIFFERENCE)
    assert result.area == 92.0
    assert len(result.regions) == 1
    assert len(result.regions[0].holes) == 2


def test_three_region_symmetric_difference_uses_odd_even_membership():
    result = boolean_planar_region_set((
        region("a", 0, 0, 1, 1),
        region("b", 3, 0, 4, 1),
        region("c", 6, 0, 7, 1),
    ), Operation.SYMMETRIC_DIFFERENCE)
    assert result.area == 3.0
    assert len(result.regions) == 3


def test_set_union_supports_disconnected_components_and_multiple_holes():
    plate = PlanarRegion(
        "plate", "part", "mm",
        tuple(Vec2(x, y) for x, y in ((0, 0), (12, 0), (12, 10), (0, 10))),
        (
            tuple(Vec2(x, y) for x, y in ((2, 2), (2, 4), (4, 4), (4, 2))),
            tuple(Vec2(x, y) for x, y in ((7, 2), (7, 5), (10, 5), (10, 2))),
        ),
    )
    remote = region("remote", 20, 0, 22, 2)
    result = boolean_planar_region_set((plate, remote), Operation.UNION)
    assert result.area == 111.0
    assert len(result.regions) == 2
    assert sorted(len(item.holes) for item in result.regions) == [0, 2]


def test_set_difference_is_ordered_and_symmetric_difference_cancels_duplicates():
    small = region("small", 2, 2, 4, 4)
    big = region("big", 0, 0, 10, 10)
    assert boolean_planar_region_set((small, big), Operation.DIFFERENCE).regions == ()
    assert boolean_planar_region_set((big, small), Operation.DIFFERENCE).area == 96.0
    assert boolean_planar_region_set((small, small), Operation.SYMMETRIC_DIFFERENCE).regions == ()


def test_set_boolean_requires_two_regions_and_matching_frames_and_units():
    first = region("first", 0, 0, 2, 2)
    with pytest.raises(InvalidModelError, match="at least two"):
        boolean_planar_region_set((first,), Operation.UNION)
    with pytest.raises(InvalidModelError, match="same frame"):
        boolean_planar_region_set((first, region("other", 0, 0, 1, 1, frame="world")), Operation.UNION)
    with pytest.raises(InvalidModelError, match="same frame"):
        boolean_planar_region_set((first, region("other", 0, 0, 1, 1, unit="cm")), Operation.UNION)


def test_set_boolean_snapshot_round_trip_and_strict_schema():
    operands = (region("a", 0, 0, 4, 2), region("b", 3, 0, 7, 2), region("c", 6, 0, 10, 2))
    result = boolean_planar_region_set(operands, Operation.UNION)
    snapshot = result.to_dict()
    assert PlanarRegionSetBooleanResult.from_dict(snapshot).to_dict() == snapshot
    with pytest.raises(InvalidModelError, match="missing or unknown"):
        PlanarRegionSetBooleanResult.from_dict(dict(snapshot, extra=True))
    schema = json.loads((Path(__file__).parents[1] / "schemas" / "geometry" /
                         "planar-region-set-boolean-result.schema.json").read_text(encoding="utf-8"))
    assert set(snapshot) == set(schema["required"])
    assert schema["additionalProperties"] is False



def test_six_way_point_contact_preserves_all_components_and_is_permutation_stable():
    sectors = (
        PlanarRegion("sector-a", "part", "mm", tuple(Vec2(x, y) for x, y in ((0, 0), (3, 0), (2, 1)))),
        PlanarRegion("sector-b", "part", "mm", tuple(Vec2(x, y) for x, y in ((0, 0), (2, 2), (1, 3)))),
        PlanarRegion("sector-c", "part", "mm", tuple(Vec2(x, y) for x, y in ((0, 0), (-1, 3), (-2, 2)))),
        PlanarRegion("sector-d", "part", "mm", tuple(Vec2(x, y) for x, y in ((0, 0), (-2, 1), (-3, 0)))),
        PlanarRegion("sector-e", "part", "mm", tuple(Vec2(x, y) for x, y in ((0, 0), (-2, -2), (-1, -3)))),
        PlanarRegion("sector-f", "part", "mm", tuple(Vec2(x, y) for x, y in ((0, 0), (1, -3), (2, -2)))),
    )
    forward = boolean_planar_region_set(sectors, Operation.UNION)
    reverse = boolean_planar_region_set(tuple(reversed(sectors)), Operation.UNION)
    signature = lambda result: sorted(
        (region.area_exact, tuple((p.x, p.y) for p in region.outer_boundary))
        for region in result.regions
    )
    assert len(forward.regions) == 6
    assert forward.area == 12.0
    assert signature(forward) == signature(reverse)


def test_region_set_result_limitations_match_point_contact_and_branching_behavior():
    result = boolean_planar_region_set((
        region("a", 0, 0, 1, 1),
        region("b", 1, 1, 2, 2),
    ), Operation.UNION)
    limitations = result.to_dict()["limitations"]
    assert "Unambiguous point-only contacts remain separate output components; ambiguous branching, coincident outgoing directions and invalid hole topology fail closed." in limitations
    restored = PlanarRegionSetBooleanResult.from_dict(result.to_dict())
    assert restored.to_dict() == result.to_dict()


def test_stitch_rejects_coincident_outgoing_branching_fail_closed():
    origin = (0, 0)
    first = (2, 0)
    second = (3, 0)
    upper = (1, 2)
    lower = (1, -2)
    directed = {
        (origin, first), (first, upper), (upper, origin),
        (origin, second), (second, lower), (lower, origin),
    }
    with pytest.raises(InvalidModelError, match="coincident outgoing branches"):
        _stitch(directed)


def test_stitch_rejects_unbalanced_boundary_incidence_fail_closed():
    with pytest.raises(InvalidModelError, match="unbalanced boundary incidence"):
        _stitch({((0, 0), (1, 0))})
