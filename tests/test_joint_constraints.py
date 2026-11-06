import math

import pytest

from universal_platform.engineering.errors import InvalidModelError
from universal_platform.engineering.geometry import Vec3
from universal_platform.engineering.joint_constraints import generate_joint_constraints
from universal_platform.engineering.mechanism_model import (
    CoordinateKind, FrameReference, GeneralizedCoordinate, GeometryPlacement,
    JointCoordinateParameterization, JointFramePlacement, JointKind, JointModel,
    LinkModel, MechanismModel,
)
from universal_platform.engineering.transforms import RigidTransform


def rotation(axis, angle):
    x, y, z = axis
    c, s, t = math.cos(angle), math.sin(angle), 1 - math.cos(angle)
    return (
        (c+x*x*t, x*y*t-z*s, x*z*t+y*s),
        (y*x*t+z*s, c+y*y*t, y*z*t-x*s),
        (z*x*t-y*s, z*y*t+x*s, c+z*z*t),
    )


def matmul(a, b):
    return tuple(tuple(sum(a[i][k]*b[k][j] for k in range(3)) for j in range(3)) for i in range(3))


def make_case(kind, coordinates=(), parameterization=None, *, joint_axis=None):
    parent_frame, child_frame, joint_frame = "frame/parent", "frame/child", "frame/joint"
    axis = joint_axis
    if axis is None and kind in (JointKind.REVOLUTE, JointKind.PRISMATIC, JointKind.CYLINDRICAL, JointKind.HELICAL):
        axis = (0.0, 0.0, 1.0)
    joint = JointModel("joint/main", kind, "link/parent", "link/child", joint_frame, axis)
    model = MechanismModel(
        "model/joint-constraints", "r1",
        (LinkModel("link/parent", "p1", parent_frame), LinkModel("link/child", "p1", child_frame)),
        (joint,),
        (FrameReference(parent_frame, owner_link_id="link/parent"),
         FrameReference(child_frame, owner_link_id="link/child"),
         FrameReference(joint_frame)),
        schema_version="1.2",
        joint_placements=(JointFramePlacement(
            "joint/main", RigidTransform(parent_frame, joint_frame),
            RigidTransform(joint_frame, child_frame),
        ),),
        generalized_coordinates=tuple(coordinates),
        joint_parameterizations=(() if parameterization is None else (parameterization,)),
    )
    return model


def q(name, kind, axis):
    return GeneralizedCoordinate(name, kind, "rad" if kind is CoordinateKind.ROTATIONAL else "m", axis)


def params(*ids, **kwargs):
    return JointCoordinateParameterization("joint/main", tuple(ids), **kwargs)


def body_poses(rotation_matrix=None, translation=(0.0, 0.0, 0.0)):
    return {
        "link/parent": RigidTransform("frame/parent", "world"),
        "link/child": RigidTransform(
            "frame/child", "world", rotation_matrix or (
                (1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)
            ), Vec3(*translation),
        ),
    }


@pytest.mark.parametrize(("kind", "coords", "mapping", "values", "expected_rotation", "expected_translation"), [
    (JointKind.FIXED, (), None, {}, None, (0.0, 0.0, 0.0)),
    (JointKind.REVOLUTE, (q("q/theta", CoordinateKind.ROTATIONAL, (0,0,1)),), params("q/theta"), {"q/theta": 0.4}, rotation((0,0,1),0.4), (0,0,0)),
    (JointKind.PRISMATIC, (q("q/x", CoordinateKind.TRANSLATIONAL, (1,0,0)),), params("q/x"), {"q/x": 0.25}, None, (0.25,0,0)),
    (JointKind.CYLINDRICAL, (q("q/theta", CoordinateKind.ROTATIONAL, (0,0,1)), q("q/z", CoordinateKind.TRANSLATIONAL, (0,0,1))), params("q/theta","q/z"), {"q/theta":0.2,"q/z":0.3}, rotation((0,0,1),0.2), (0,0,0.3)),
    (JointKind.HELICAL, (q("q/theta", CoordinateKind.ROTATIONAL, (0,0,1)),), params("q/theta",pitch_m_per_rad=0.01), {"q/theta":0.2}, rotation((0,0,1),0.2), (0,0,0.002)),
    (JointKind.SPHERICAL, (q("q/x",CoordinateKind.ROTATIONAL,(1,0,0)),q("q/y",CoordinateKind.ROTATIONAL,(0,1,0)),q("q/z",CoordinateKind.ROTATIONAL,(0,0,1))), params("q/x","q/y","q/z",coordinate_convention="EULER_INTRINSIC_XYZ"), {"q/x":0.3,"q/y":0.0,"q/z":0.0}, rotation((1,0,0),0.3), (0,0,0)),
    (JointKind.PLANAR, (q("q/x",CoordinateKind.TRANSLATIONAL,(1,0,0)),q("q/y",CoordinateKind.TRANSLATIONAL,(0,1,0)),q("q/theta",CoordinateKind.ROTATIONAL,(0,0,1))), params("q/x","q/y","q/theta"), {"q/x":0.2,"q/y":0.3,"q/theta":0.1}, rotation((0,0,1),0.1), (0.2,0.3,0)),
    (JointKind.UNIVERSAL, (q("q/x",CoordinateKind.ROTATIONAL,(1,0,0)),q("q/y",CoordinateKind.ROTATIONAL,(0,1,0))), params("q/x","q/y"), {"q/x":0.2,"q/y":0.3}, matmul(rotation((0,1,0),0.3),rotation((1,0,0),0.2)), (0,0,0)),
])
def test_generates_and_evaluates_all_joint_families(kind, coords, mapping, values, expected_rotation, expected_translation):
    model = make_case(kind, coords, mapping)
    generated = generate_joint_constraints(model)
    result = generated.evaluate(body_poses(expected_rotation, expected_translation), values)
    assert result.all_satisfied, result.to_dict()
    assert len(result.residuals) == 6
    assert all(item.passed for item in result.residuals)
    assert len({item.constraint_id for item in generated.definitions}) == 6


def test_generates_stable_ordered_six_component_definitions_and_snapshot():
    model = make_case(JointKind.REVOLUTE, (q("q/theta",CoordinateKind.ROTATIONAL,(0,0,1)),), params("q/theta"))
    first = generate_joint_constraints(model)
    second = generate_joint_constraints(model)
    assert first.to_dict() == second.to_dict()
    assert [item.component for item in first.definitions] == [
        "translation_x","translation_y","translation_z","rotation_x","rotation_y","rotation_z"
    ]
    assert first.definitions[0].unit == "m"
    assert first.definitions[-1].unit == "rad"


def test_reports_pose_mismatch_as_fail_without_hiding_residuals():
    model = make_case(JointKind.FIXED)
    result = generate_joint_constraints(model).evaluate(body_poses(translation=(0.01,0,0)), {})
    assert not result.all_satisfied
    assert result.residuals[0].passed is False
    assert result.residuals[0].value == pytest.approx(0.01)
    assert result.to_dict()["residuals"][0]["status"] == "FAIL"


def test_generation_fails_closed_for_missing_joint_placement_or_parameterization():
    model = make_case(JointKind.REVOLUTE)
    with pytest.raises(InvalidModelError, match="explicit parameterization"):
        generate_joint_constraints(model)
    model = make_case(JointKind.REVOLUTE, (q("q/theta",CoordinateKind.ROTATIONAL,(0,0,1)),), params("q/theta"))
    model = MechanismModel(model.model_id, model.revision, model.links, model.joints, model.frames,
                           schema_version="1.2")
    with pytest.raises(InvalidModelError, match="placements for every joint"):
        generate_joint_constraints(model)


def test_evaluation_requires_exact_pose_and_coordinate_coverage():
    model = make_case(JointKind.REVOLUTE, (q("q/theta",CoordinateKind.ROTATIONAL,(0,0,1)),), params("q/theta"))
    generated = generate_joint_constraints(model)
    with pytest.raises(InvalidModelError, match="cover exactly the model links"):
        generated.evaluate({"link/parent": body_poses()["link/parent"]}, {"q/theta": 0.0})
    with pytest.raises(InvalidModelError, match="cover exactly the model coordinates"):
        generated.evaluate(body_poses(), {})
    with pytest.raises(InvalidModelError, match="finite numeric"):
        generated.evaluate(body_poses(), {"q/theta": True})


def test_body_pose_frame_mismatch_and_nonpositive_tolerance_fail():
    model = make_case(JointKind.FIXED)
    generated = generate_joint_constraints(model)
    poses = body_poses()
    poses["link/child"] = RigidTransform("wrong-frame", "world")
    with pytest.raises(InvalidModelError, match="must map from frame"):
        generated.evaluate(poses, {})
    with pytest.raises(InvalidModelError, match="translation_tolerance_m"):
        generate_joint_constraints(model, translation_tolerance_m=0.0)
