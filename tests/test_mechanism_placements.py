import pytest

from universal_platform.engineering.errors import InvalidModelError
from universal_platform.engineering.geometry import Vec3
from universal_platform.engineering.mechanism_model import (
    FrameReference, GeometryKind, GeometryPlacement, GeometryReference,
    JointFramePlacement, JointKind, JointModel, LinkModel, MechanismModel,
    validate_mechanism_model,
)
from universal_platform.engineering.transforms import RigidTransform


def base_model(**changes):
    values = dict(
        model_id="mechanism/placement-demo",
        revision="r2",
        links=(
            LinkModel("ground", "part-r1", "frame/ground", ("geometry/base",)),
            LinkModel("slider", "part-r3", "frame/slider"),
        ),
        joints=(
            JointModel(
                "joint/slide", JointKind.PRISMATIC, "ground", "slider",
                "frame/joint", (1.0, 0.0, 0.0), "m",
            ),
        ),
        frames=(
            FrameReference("frame/world"),
            FrameReference("frame/ground", "frame/world", "ground"),
            FrameReference("frame/slider", "frame/world", "slider"),
            FrameReference("frame/joint", "frame/world"),
            FrameReference("frame/geometry/base", "frame/ground", "ground"),
        ),
        geometry=(
            GeometryReference(
                "geometry/base", "ground", "frame/ground", GeometryKind.ANALYTIC
            ),
        ),
    )
    values.update(changes)
    return MechanismModel(**values)


def placements():
    return (
        JointFramePlacement(
            "joint/slide",
            RigidTransform("frame/ground", "frame/joint",
                           translation=Vec3(0.1, 0.0, 0.0)),
            RigidTransform("frame/joint", "frame/slider",
                           translation=Vec3(0.0, 0.2, 0.0)),
        ),
    ), (
        GeometryPlacement(
            "geometry/base",
            RigidTransform("frame/geometry/base", "frame/ground",
                           translation=Vec3(0.0, 0.0, 0.0)),
        ),
    )


def test_schema_v11_accepts_complete_joint_and_geometry_placements():
    joint_placements, geometry_placements = placements()
    model = base_model(
        joint_placements=joint_placements,
        geometry_placements=geometry_placements,
    )
    result = validate_mechanism_model(model)
    assert result.valid, result.errors
    assert result.joint_placement_count == 1
    assert result.geometry_placement_count == 1
    assert result.joints_without_placement == ()
    assert result.geometry_without_placement == ()


def test_missing_placements_are_reported_not_assumed_identity():
    result = validate_mechanism_model(base_model())
    assert result.valid
    assert result.joints_without_placement == ("joint/slide",)
    assert result.geometry_without_placement == ("geometry/base",)


def test_legacy_schema_v10_remains_valid_without_placement_records():
    result = validate_mechanism_model(base_model(schema_version="1.0"))
    assert result.valid
    assert result.joint_placement_count == 0


def test_schema_v10_rejects_new_placement_records():
    joint_placements, _ = placements()
    result = validate_mechanism_model(
        base_model(schema_version="1.0", joint_placements=joint_placements)
    )
    assert not result.valid
    assert any("require mechanism schema_version '1.1'" in item for item in result.errors)


def test_joint_placement_requires_exact_parent_joint_child_frame_chain():
    joint_placements, geometry_placements = placements()
    bad = JointFramePlacement(
        "joint/slide",
        RigidTransform("frame/slider", "frame/joint"),
        joint_placements[0].joint_to_child,
    )
    result = validate_mechanism_model(
        base_model(joint_placements=(bad,), geometry_placements=geometry_placements)
    )
    assert not result.valid
    assert any("parent source frame must match" in item for item in result.errors)


def test_joint_placement_rejects_unknown_joint_and_duplicate_ids():
    joint_placements, _ = placements()
    unknown = JointFramePlacement(
        "joint/missing", joint_placements[0].parent_to_joint,
        joint_placements[0].joint_to_child,
    )
    result = validate_mechanism_model(base_model(joint_placements=(unknown,)))
    assert not result.valid
    assert any("references unknown joint" in item for item in result.errors)
    result = validate_mechanism_model(
        base_model(joint_placements=(joint_placements[0], joint_placements[0]))
    )
    assert not result.valid
    assert any("Duplicate joint placement" in item for item in result.errors)


def test_geometry_placement_requires_matching_geometry_frame_and_owner():
    _, geometry_placements = placements()
    bad = GeometryPlacement(
        "geometry/base",
        RigidTransform("frame/slider", "frame/slider"),
    )
    result = validate_mechanism_model(
        base_model(geometry_placements=(bad,))
    )
    assert not result.valid
    assert any("destination frame must match geometry reference frame" in item
               for item in result.errors)
    assert any("local frame is owned by another link" in item
               for item in result.errors)


def test_placement_translation_units_are_explicitly_metres():
    joint_placements, geometry_placements = placements()
    bad = JointFramePlacement(
        "joint/slide", joint_placements[0].parent_to_joint,
        joint_placements[0].joint_to_child, "mm",
    )
    result = validate_mechanism_model(
        base_model(joint_placements=(bad,), geometry_placements=geometry_placements)
    )
    assert not result.valid
    assert any("length_unit must be 'm'" in item for item in result.errors)


def test_placement_snapshots_are_deterministic_and_explicit():
    joint_placements, geometry_placements = placements()
    first = joint_placements[0].to_dict()
    second = joint_placements[0].to_dict()
    assert first == second
    assert first["parent_to_joint"]["from_frame"] == "frame/ground"
    assert first["parent_to_joint"]["to_frame"] == "frame/joint"
    assert first["length_unit"] == "m"
    assert geometry_placements[0].to_dict()["geometry_id"] == "geometry/base"
