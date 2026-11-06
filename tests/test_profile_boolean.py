import json
import pytest

from universal_platform.engineering.errors import InvalidModelError
from universal_platform.engineering.primitive_geometry import Vec2
from universal_platform.engineering.profile_boolean import (
    ProfileBooleanOperation, ProfileBooleanResult, ProfileLoop, boolean_profiles,
)


def loop(profile_id, coordinates):
    return ProfileLoop(profile_id, tuple(Vec2(x, y) for x, y in coordinates))


def rectangle(profile_id, x0, y0, x1, y1, clockwise=False):
    points = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    if clockwise:
        points.reverse()
    return loop(profile_id, points)


def test_intersection_of_overlapping_convex_profiles_has_exact_area():
    first = rectangle("profile.a", 0, 0, 4, 4)
    second = rectangle("profile.b", 2, -1, 5, 3)
    result = boolean_profiles(ProfileBooleanOperation.INTERSECTION, first, second)
    assert result.area == pytest.approx(6.0)
    assert len(result.regions) == 1
    assert result.regions[0] == (
        Vec2(2.0, 0.0), Vec2(4.0, 0.0), Vec2(4.0, 3.0), Vec2(2.0, 3.0)
    )


def test_difference_partitions_concave_result_into_non_overlapping_convex_cells():
    first = rectangle("profile.a", 0, 0, 4, 4)
    second = rectangle("profile.b", 2, -1, 5, 3)
    result = boolean_profiles(ProfileBooleanOperation.DIFFERENCE, first, second)
    assert result.area == pytest.approx(10.0)
    assert len(result.regions) == 2
    assert all(len(region) >= 3 for region in result.regions)
    assert sum(abs(
        sum(region[i].x * region[(i + 1) % len(region)].y
            - region[(i + 1) % len(region)].x * region[i].y for i in range(len(region))) / 2
    ) for region in result.regions) == pytest.approx(10.0)


def test_union_is_partitioned_into_non_overlapping_convex_cells():
    first = rectangle("profile.a", 0, 0, 4, 4)
    second = rectangle("profile.b", 2, -1, 5, 3)
    result = boolean_profiles(ProfileBooleanOperation.UNION, first, second)
    assert result.area == pytest.approx(22.0)
    assert len(result.regions) == 3


def test_disjoint_and_touching_profiles_have_stable_empty_intersections():
    first = rectangle("profile.a", 0, 0, 1, 1)
    disjoint = rectangle("profile.b", 2, 0, 3, 1)
    touching = rectangle("profile.c", 1, 0, 2, 1)
    assert boolean_profiles(ProfileBooleanOperation.INTERSECTION, first, disjoint).regions == ()
    assert boolean_profiles(ProfileBooleanOperation.INTERSECTION, first, touching).regions == ()


def test_containment_handles_union_intersection_and_difference():
    outer = rectangle("profile.outer", 0, 0, 10, 10)
    inner = rectangle("profile.inner", 2, 2, 8, 8)
    assert boolean_profiles(ProfileBooleanOperation.UNION, outer, inner).area == pytest.approx(100)
    assert boolean_profiles(ProfileBooleanOperation.INTERSECTION, outer, inner).area == pytest.approx(36)
    diff = boolean_profiles(ProfileBooleanOperation.DIFFERENCE, outer, inner)
    assert diff.area == pytest.approx(64)
    assert len(diff.regions) >= 1


def test_clockwise_input_is_normalized_and_equivalent_inputs_are_deterministic():
    first = rectangle("profile.a", 0, 0, 4, 4, clockwise=True)
    second = rectangle("profile.b", 2, 1, 5, 3)
    a = boolean_profiles(ProfileBooleanOperation.UNION, first, second)
    b = boolean_profiles(ProfileBooleanOperation.UNION,
                         rectangle("profile.a", 0, 0, 4, 4),
                         rectangle("profile.b", 2, 1, 5, 3, clockwise=True))
    assert a.to_dict() == b.to_dict()


def test_result_snapshot_round_trips_and_rejects_tampering():
    result = boolean_profiles(
        ProfileBooleanOperation.DIFFERENCE,
        rectangle("profile.a", 0, 0, 4, 4),
        rectangle("profile.b", 2, -1, 5, 3),
    )
    snapshot = json.loads(json.dumps(result.to_dict()))
    assert ProfileBooleanResult.from_dict(snapshot).to_dict() == snapshot
    with pytest.raises(InvalidModelError, match="area"):
        ProfileBooleanResult.from_dict(dict(snapshot, area=999))
    with pytest.raises(InvalidModelError, match="missing or unknown"):
        ProfileBooleanResult.from_dict(dict(snapshot, unexpected=True))


def test_rejects_concave_self_intersecting_and_invalid_inputs_fail_closed():
    with pytest.raises(InvalidModelError, match="convex"):
        loop("profile.concave", [(0, 0), (3, 0), (1, 1), (3, 3), (0, 3)])
    with pytest.raises(InvalidModelError, match="convex simple"):
        loop("profile.star", [(0, 3), (2, -2), (-3, 1), (3, 1), (-2, -2)])
    with pytest.raises(InvalidModelError, match="at least three"):
        loop("profile.short", [(0, 0), (1, 0)])
    with pytest.raises(InvalidModelError, match="ProfileLoop"):
        boolean_profiles(ProfileBooleanOperation.UNION, "not-a-loop", rectangle("profile.b", 0, 0, 1, 1))


def test_boolean_operation_requires_explicit_enum():
    with pytest.raises(InvalidModelError, match="ProfileBooleanOperation"):
        boolean_profiles("UNION", rectangle("profile.a", 0, 0, 1, 1),
                         rectangle("profile.b", 0, 0, 1, 1))


def test_profile_boolean_result_schema_declares_strict_v1_contract():
    from pathlib import Path
    schema_path = Path(__file__).parents[1] / "schemas" / "geometry" / "profile-boolean-result.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    assert schema["properties"]["schema_version"]["const"] == "1.0"
    assert schema["properties"]["operation"]["enum"] == ["UNION", "INTERSECTION", "DIFFERENCE"]
    assert schema["additionalProperties"] is False
    assert schema["properties"]["regions"]["items"]["minItems"] == 3


def test_public_profile_boolean_exports_are_canonical():
    from universal_platform.engineering import ProfileBooleanOperation as PublicOperation
    from universal_platform.engineering import ProfileBooleanResult as PublicResult
    from universal_platform.engineering import ProfileLoop as PublicLoop
    from universal_platform.engineering import boolean_profiles as public_boolean_profiles
    from universal_platform.engineering.profile_boolean import (
        ProfileBooleanOperation, ProfileBooleanResult, ProfileLoop, boolean_profiles,
    )
    assert PublicOperation is ProfileBooleanOperation
    assert PublicResult is ProfileBooleanResult
    assert PublicLoop is ProfileLoop
    assert public_boolean_profiles is boolean_profiles
