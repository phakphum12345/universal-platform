import pytest

from universal_platform.engineering.mechanism_model import (
    CoordinateKind, FrameReference, GeneralizedCoordinate, JointCoordinateParameterization,
    JointKind, JointModel, LinkModel, MechanismModel, validate_mechanism_model,
)


def make_model(kind, coordinates=(), parameterization=None, **changes):
    axis = (1.0, 0.0, 0.0) if kind is JointKind.PRISMATIC else (0.0, 0.0, 1.0)
    unit = "rad" if kind in (JointKind.REVOLUTE, JointKind.HELICAL) else ("m" if kind is JointKind.PRISMATIC else None)
    values = dict(
        model_id="model/coordinates", revision="r1",
        links=(LinkModel("link/base", "part-r1", "frame/base"), LinkModel("link/moving", "part-r1", "frame/moving")),
        joints=(JointModel("joint/main", kind, "link/base", "link/moving", "frame/joint", axis, unit),),
        frames=(FrameReference("frame/world"), FrameReference("frame/base", "frame/world", "link/base"),
                FrameReference("frame/moving", "frame/world", "link/moving"), FrameReference("frame/joint", "frame/world")),
        generalized_coordinates=tuple(coordinates),
        joint_parameterizations=(() if parameterization is None else (parameterization,)),
    )
    values.update(changes)
    return MechanismModel(**values)


def coordinate(name, kind, axis, unit=None, **kwargs):
    return GeneralizedCoordinate(name, kind, unit or ("rad" if kind is CoordinateKind.ROTATIONAL else "m"), axis, **kwargs)


def parameterization(*ids, **kwargs):
    return JointCoordinateParameterization("joint/main", tuple(ids), **kwargs)


@pytest.mark.parametrize(("kind", "coords", "mapping"), [
    (JointKind.REVOLUTE, (coordinate("q/t", CoordinateKind.ROTATIONAL, (0, 0, 1)),), parameterization("q/t")),
    (JointKind.PRISMATIC, (coordinate("q/x", CoordinateKind.TRANSLATIONAL, (1, 0, 0)),), parameterization("q/x")),
    (JointKind.CYLINDRICAL, (coordinate("q/t", CoordinateKind.ROTATIONAL, (0, 0, 1)), coordinate("q/z", CoordinateKind.TRANSLATIONAL, (0, 0, 1))), parameterization("q/t", "q/z")),
    (JointKind.HELICAL, (coordinate("q/s", CoordinateKind.ROTATIONAL, (0, 0, 1)),), parameterization("q/s", pitch_m_per_rad=0.002)),
    (JointKind.SPHERICAL, (coordinate("q/x", CoordinateKind.ROTATIONAL, (1, 0, 0)), coordinate("q/y", CoordinateKind.ROTATIONAL, (0, 1, 0)), coordinate("q/z", CoordinateKind.ROTATIONAL, (0, 0, 1))), parameterization("q/x", "q/y", "q/z", coordinate_convention="EULER_INTRINSIC_XYZ")),
    (JointKind.PLANAR, (coordinate("q/x", CoordinateKind.TRANSLATIONAL, (1, 0, 0)), coordinate("q/y", CoordinateKind.TRANSLATIONAL, (0, 1, 0)), coordinate("q/t", CoordinateKind.ROTATIONAL, (0, 0, 1))), parameterization("q/x", "q/y", "q/t")),
    (JointKind.UNIVERSAL, (coordinate("q/x", CoordinateKind.ROTATIONAL, (1, 0, 0)), coordinate("q/y", CoordinateKind.ROTATIONAL, (0, 1, 0))), parameterization("q/x", "q/y")),
])
def test_joint_kinds_accept_explicit_parameterization(kind, coords, mapping):
    result = validate_mechanism_model(make_model(kind, coords, mapping))
    assert result.valid, result.errors
    assert result.joint_parameterization_count == 1
    assert result.joints_without_parameterization == ()


def test_fixed_and_legacy_unparameterized_joint_coverage():
    assert validate_mechanism_model(make_model(JointKind.FIXED)).valid
    result = validate_mechanism_model(make_model(JointKind.REVOLUTE))
    assert result.valid
    assert result.joints_without_parameterization == ("joint/main",)


def test_schema_11_compatibility_and_v12_gate():
    assert validate_mechanism_model(make_model(JointKind.REVOLUTE, schema_version="1.1")).valid
    q = coordinate("q/t", CoordinateKind.ROTATIONAL, (0, 0, 1))
    result = validate_mechanism_model(make_model(JointKind.REVOLUTE, (q,), parameterization("q/t"), schema_version="1.1"))
    assert not result.valid
    assert any("require mechanism schema_version '1.2'" in item for item in result.errors)


def test_coordinate_identity_unit_axis_bounds_and_scale_validation():
    q = coordinate("q/t", CoordinateKind.ROTATIONAL, (0, 0, 2), unit="m", lower_limit=2, upper_limit=1, scale=0)
    result = validate_mechanism_model(make_model(JointKind.REVOLUTE, (q,), parameterization("q/t")))
    assert not result.valid
    assert any("unit must be 'rad'" in item for item in result.errors)
    assert any("axis must be normalized" in item for item in result.errors)
    assert any("inverted limits" in item for item in result.errors)
    assert any("scale must be finite and positive" in item for item in result.errors)


def test_dangling_duplicate_orphan_and_wrong_joint_axis_coordinates_fail():
    q = coordinate("q/t", CoordinateKind.ROTATIONAL, (0, 0, 1))
    duplicate = validate_mechanism_model(make_model(JointKind.REVOLUTE, (q, q), parameterization("q/t")))
    assert any("Duplicate generalized coordinate" in item for item in duplicate.errors)
    dangling = validate_mechanism_model(make_model(JointKind.REVOLUTE, (q,), parameterization("q/missing")))
    assert any("references unknown coordinate" in item for item in dangling.errors)
    wrong = coordinate("q/w", CoordinateKind.TRANSLATIONAL, (0, 1, 0))
    bad = validate_mechanism_model(make_model(JointKind.REVOLUTE, (wrong,), parameterization("q/w")))
    assert any("must be ROTATIONAL" in item for item in bad.errors)
    assert any("align with the declared joint axis" in item for item in bad.errors)


def test_helical_pitch_spherical_convention_and_universal_axes_are_explicit():
    q = coordinate("q/s", CoordinateKind.ROTATIONAL, (0, 0, 1))
    result = validate_mechanism_model(make_model(JointKind.HELICAL, (q,), parameterization("q/s")))
    assert any("requires finite non-zero pitch" in item for item in result.errors)
    coords = tuple(coordinate(f"q/{axis}", CoordinateKind.ROTATIONAL, vec) for axis, vec in (("x", (1,0,0)), ("y", (0,1,0)), ("z", (0,0,1))))
    result = validate_mechanism_model(make_model(JointKind.SPHERICAL, coords, parameterization("q/x", "q/y", "q/z")))
    assert any("explicit supported Euler" in item for item in result.errors)
    same = (coordinate("q/a", CoordinateKind.ROTATIONAL, (0,0,1)), coordinate("q/b", CoordinateKind.ROTATIONAL, (0,0,1)))
    result = validate_mechanism_model(make_model(JointKind.UNIVERSAL, same, parameterization("q/a", "q/b")))
    assert any("must not be parallel" in item for item in result.errors)


def test_planar_basis_and_deterministic_snapshots():
    coords = (coordinate("q/x", CoordinateKind.TRANSLATIONAL, (1,0,0)), coordinate("q/y", CoordinateKind.TRANSLATIONAL, (0,1,0)), coordinate("q/t", CoordinateKind.ROTATIONAL, (0,0,-1)))
    result = validate_mechanism_model(make_model(JointKind.PLANAR, coords, parameterization("q/x", "q/y", "q/t")))
    assert any("right-handed orthonormal basis" in item for item in result.errors)
    q = coordinate("q/t", CoordinateKind.ROTATIONAL, (0,0,1), lower_limit=-1, upper_limit=1, scale=0.5)
    p = parameterization("q/t")
    assert q.to_dict() == q.to_dict()
    assert p.to_dict()["coordinate_ids"] == ["q/t"]
