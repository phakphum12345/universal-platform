import json
from fractions import Fraction

import pytest

from universal_platform.engineering.errors import InvalidModelError
from universal_platform.engineering.primitive_geometry import Vec2
from universal_platform.engineering.planar_region import PlanarRegion, PRECISION_POLICY


def _region(region_id="region.plate", outer=None, holes=(), unit="mm", frame="part"):
    if outer is None:
        outer = ((0, 0), (10, 0), (10, 8), (0, 8))
    return PlanarRegion(
        region_id, frame, unit, tuple(Vec2(x, y) for x, y in outer),
        tuple(tuple(Vec2(x, y) for x, y in hole) for hole in holes),
    )


def test_planar_region_normalizes_outer_ccw_holes_cw_and_cyclic_origin():
    a = _region(outer=((10, 8), (10, 0), (0, 0), (0, 8)),
                holes=(((2, 2), (2, 4), (5, 4), (5, 2)),))
    b = _region(outer=((0, 0), (10, 0), (10, 8), (0, 8)),
                holes=(((5, 2), (5, 4), (2, 4), (2, 2)),))
    assert a.to_dict() == b.to_dict()
    assert a.outer_boundary[0] == Vec2(0, 0)
    assert a.holes[0][0] == Vec2(2, 2)


def test_planar_region_area_uses_exact_rational_binary64_predicates():
    region = _region(holes=(
        ((2, 2), (2, 4), (5, 4), (5, 2)),
        ((7, 2), (7, 5), (10-1, 5), (10-1, 2)),
    ))
    assert region.area_exact == Fraction(68, 1)
    assert region.area == 74.0
    assert region.boundary_edge_count == 12
    assert len(region.canonical_sha256) == 64


def test_planar_region_accepts_disjoint_multiple_holes():
    region = _region(holes=(
        ((2, 2), (2, 4), (4, 4), (4, 2)),
        ((7, 2), (7, 5), (10, 5), (10, 2)),
    ))
    assert region.area_exact == Fraction(67, 1)


@pytest.mark.parametrize("outer", [
    ((0, 0), (2, 2), (0, 2), (2, 0)),
    ((0, 0), (2, 0), (1, 0), (1, 2), (0, 2)),
    ((0, 0), (1, 0), (1, 0), (0, 1)),
    ((0, 0), (1, 1), (2, 2)),
])
def test_planar_region_rejects_self_intersection_overlap_duplicates_and_zero_area(outer):
    with pytest.raises(InvalidModelError):
        _region(outer=outer)


def test_planar_region_rejects_holes_outside_touching_crossing_or_nested():
    with pytest.raises(InvalidModelError, match="strictly inside"):
        _region(holes=(((11, 2), (11, 4), (12, 4), (12, 2)),))
    with pytest.raises(InvalidModelError, match="touches or crosses"):
        _region(holes=(((0, 2), (0, 4), (2, 4), (2, 2)),))
    with pytest.raises(InvalidModelError, match="overlap or nest"):
        _region(holes=(
            ((2, 2), (2, 6), (6, 6), (6, 2)),
            ((3, 3), (3, 4), (4, 4), (4, 3)),
        ))


def test_planar_region_rejects_frame_unit_and_precision_policy_errors():
    with pytest.raises(InvalidModelError, match="length dimension"):
        _region(unit="s")
    with pytest.raises(InvalidModelError, match="frame_id"):
        PlanarRegion("region.bad", "", "mm", tuple(Vec2(x, y) for x, y in ((0,0),(1,0),(0,1))))
    with pytest.raises(InvalidModelError, match="precision_policy"):
        PlanarRegion("region.bad", "part", "mm",
                     tuple(Vec2(x, y) for x, y in ((0,0),(1,0),(0,1))), (), "epsilon-1e-9")


def test_planar_region_exact_predicates_survive_large_translation_and_small_features():
    offset = float(2**40)
    region = _region(outer=((offset, offset), (offset+1, offset),
                            (offset+1, offset+1), (offset, offset+1)))
    assert region.area_exact == Fraction(1, 1)


def test_planar_region_strict_snapshot_round_trip_and_tamper_rejection():
    region = _region(holes=(((2, 2), (2, 4), (5, 4), (5, 2)),))
    snapshot = json.loads(json.dumps(region.to_dict()))
    assert PlanarRegion.from_dict(snapshot).to_dict() == snapshot
    malformed = dict(snapshot, extra=True)
    with pytest.raises(InvalidModelError, match="missing or unknown"):
        PlanarRegion.from_dict(malformed)
    wrong = dict(snapshot, precision_policy="unknown")
    with pytest.raises(InvalidModelError, match="precision_policy"):
        PlanarRegion.from_dict(wrong)


def test_planar_region_edge_resource_limit_is_explicit():
    points = tuple(Vec2(i, i % 2) for i in range(2050))
    with pytest.raises(InvalidModelError, match="resource limit"):
        PlanarRegion("region.large", "part", "mm", points)



def test_planar_region_schema_is_strict_and_matches_serialized_fields():
    from pathlib import Path
    schema = json.loads((Path(__file__).parents[1] / "schemas" / "geometry" /
                         "planar-region.schema.json").read_text(encoding="utf-8"))
    region = _region()
    assert set(region.to_dict()) == set(schema["required"])
    assert schema["additionalProperties"] is False
