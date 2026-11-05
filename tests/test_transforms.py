import pytest

from universal_platform.engineering.errors import InvalidModelError
from universal_platform.engineering.geometry import BoundingBox, Vec3
from universal_platform.engineering.transforms import RigidTransform

IDENTITY = ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0))
ROTATE_Z_90 = ((0.0, -1.0, 0.0), (1.0, 0.0, 0.0), (0.0, 0.0, 1.0))


def test_identity_transform_preserves_points_and_vectors():
    transform = RigidTransform.identity("world")
    point = Vec3(1.0, -2.0, 3.0)
    assert transform.apply_point(point) == point
    assert transform.apply_vector(point) == point


def test_rotation_and_translation_follow_documented_convention():
    transform = RigidTransform("part", "world", ROTATE_Z_90, Vec3(10.0, 20.0, 0.0))
    result = transform.apply_point(Vec3(2.0, 0.0, 4.0))
    assert (result.x, result.y, result.z) == pytest.approx((10.0, 22.0, 4.0))
    vector = transform.apply_vector(Vec3(2.0, 0.0, 4.0))
    assert (vector.x, vector.y, vector.z) == pytest.approx((0.0, 2.0, 4.0))


def test_inverse_round_trip_recovers_point():
    transform = RigidTransform("part", "world", ROTATE_Z_90, Vec3(10.0, -3.0, 2.0))
    point = Vec3(0.25, 4.0, -1.5)
    recovered = transform.inverse().apply_point(transform.apply_point(point))
    assert (recovered.x, recovered.y, recovered.z) == pytest.approx((point.x, point.y, point.z))


def test_composition_matches_sequential_application():
    first = RigidTransform("A", "B", ROTATE_Z_90, Vec3(1.0, 2.0, 0.0))
    second = RigidTransform("B", "C", IDENTITY, Vec3(-4.0, 1.0, 3.0))
    point = Vec3(2.0, 0.0, 1.0)
    sequential = second.apply_point(first.apply_point(point))
    composed = first.then(second).apply_point(point)
    assert (composed.x, composed.y, composed.z) == pytest.approx(
        (sequential.x, sequential.y, sequential.z)
    )
    assert first.then(second).from_frame == "A"
    assert first.then(second).to_frame == "C"


def test_composition_rejects_mismatched_frames():
    with pytest.raises(InvalidModelError, match="Cannot compose"):
        RigidTransform.identity("A").then(RigidTransform.identity("C"))


def test_transformed_bounds_enclose_all_transformed_corners():
    bounds = BoundingBox(Vec3(0.0, 0.0, 0.0), Vec3(2.0, 1.0, 1.0))
    transform = RigidTransform("part", "world", ROTATE_Z_90, Vec3(3.0, 4.0, 0.0))
    result = transform.apply_bounds(bounds)
    assert (result.minimum.x, result.minimum.y, result.minimum.z) == pytest.approx((2.0, 4.0, 0.0))
    assert (result.maximum.x, result.maximum.y, result.maximum.z) == pytest.approx((3.0, 6.0, 1.0))


@pytest.mark.parametrize("rotation", [
    ((2.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)),
    ((1.0, 0.5, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)),
    ((-1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)),
    ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, float("nan"))),
])
def test_rejects_non_rigid_or_invalid_rotation(rotation):
    with pytest.raises(InvalidModelError):
        RigidTransform("a", "b", rotation)


def test_rejects_empty_frame_names():
    with pytest.raises(InvalidModelError):
        RigidTransform(" ", "world")
