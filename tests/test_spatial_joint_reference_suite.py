import json
from dataclasses import replace
from pathlib import Path
from math import cos, sin

import pytest

from universal_platform.engineering.geometry import Vec3
from universal_platform.engineering.joint_constraints import generate_joint_constraints
from universal_platform.engineering.joint_jacobian import build_joint_constraint_jacobian
from universal_platform.engineering.mechanism_model import (
    CoordinateKind,
    FrameReference,
    GeneralizedCoordinate,
    JointCoordinateParameterization,
    JointFramePlacement,
    JointKind,
    JointModel,
    LinkModel,
    MechanismModel,
)
from universal_platform.engineering.mechanism_mobility import (
    MobilityFormulation,
    SingularityStatus,
    analyze_geometric_mechanism_mobility,
)
from universal_platform.engineering.transforms import RigidTransform


FIXTURE = Path(__file__).parent / "fixtures" / "spatial_joint_reference_cases.json"


def reference_cases():
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    assert data["schema_version"] == "1.0"
    assert data["formulation"] == "SPATIAL"
    return data["cases"]


def build_reference_model(case):
    kind = JointKind(case["joint_kind"])
    parent_frame, child_frame, joint_frame = "frame/parent", "frame/child", "frame/joint"
    coordinates = tuple(
        GeneralizedCoordinate(
            item["coordinate_id"],
            CoordinateKind(item["coordinate_kind"]),
            item["unit"],
            tuple(item["axis"]),
        )
        for item in case["coordinates"]
    )
    raw_parameterization = case["parameterization"]
    parameterizations = ()
    if raw_parameterization is not None:
        parameterizations = (JointCoordinateParameterization(
            "joint/main",
            tuple(raw_parameterization["coordinate_ids"]),
            pitch_m_per_rad=raw_parameterization.get("pitch_m_per_rad"),
            coordinate_convention=raw_parameterization.get("coordinate_convention"),
        ),)
    model = MechanismModel(
        f"model/spatial-joint/{kind.value.lower()}",
        "revision/1",
        (
            LinkModel("link/parent", "part/parent", parent_frame),
            LinkModel("link/child", "part/child", child_frame),
        ),
        (JointModel(
            "joint/main", kind, "link/parent", "link/child",
            joint_frame,
            None if case["joint_axis"] is None else tuple(case["joint_axis"]),
        ),),
        (
            FrameReference(parent_frame, owner_link_id="link/parent"),
            FrameReference(child_frame, owner_link_id="link/child"),
            FrameReference(joint_frame),
        ),
        schema_version="1.2",
        joint_placements=(JointFramePlacement(
            "joint/main",
            RigidTransform(parent_frame, joint_frame),
            RigidTransform(joint_frame, child_frame),
        ),),
        generalized_coordinates=coordinates,
        joint_parameterizations=parameterizations,
    )
    poses = {
        "link/parent": RigidTransform(parent_frame, "world"),
        "link/child": RigidTransform(child_frame, "world"),
    }
    values = dict(case["coordinate_values"])
    return model, poses, values


def rotation(axis, angle):
    x, y, z = axis
    c, s, t = cos(angle), sin(angle), 1.0 - cos(angle)
    return (
        (c + x*x*t, x*y*t - z*s, x*z*t + y*s),
        (y*x*t + z*s, c + y*y*t, y*z*t - x*s),
        (z*x*t - y*s, z*y*t + x*s, c + z*z*t),
    )


def test_reference_fixture_covers_every_declared_joint_kind_once():
    cases = reference_cases()
    kinds = [item["joint_kind"] for item in cases]
    assert len(kinds) == len(set(kinds))
    assert set(kinds) == {item.value for item in JointKind}


@pytest.mark.parametrize("case", reference_cases(), ids=lambda item: item["joint_kind"].lower())
def test_all_joint_families_generate_deterministic_six_component_constraints(case):
    model, poses, values = build_reference_model(case)
    first = generate_joint_constraints(model)
    second = generate_joint_constraints(model)
    assert first.to_dict() == second.to_dict()
    assert model.joints[0].nominal_dof == case["nominal_dof"]
    assert len(first.definitions) == 6
    assert [item.component for item in first.definitions] == [
        "translation_x", "translation_y", "translation_z",
        "rotation_x", "rotation_y", "rotation_z",
    ]
    assert [item.unit for item in first.definitions] == ["m"] * 3 + ["rad"] * 3
    result = first.evaluate(poses, values)
    assert result.all_satisfied, result.to_dict()
    assert len(result.residuals) == 6
    assert all(item.passed for item in result.residuals)


@pytest.mark.parametrize("case", reference_cases(), ids=lambda item: item["joint_kind"].lower())
def test_all_joint_families_match_reference_jacobian_entries(case):
    model, poses, values = build_reference_model(case)
    generated = generate_joint_constraints(model)
    jacobian = build_joint_constraint_jacobian(generated, poses, values)
    assert jacobian.shape == (6, 6 + case["nominal_dof"])
    assert all(
        isinstance(value, (int, float)) and value == value
        for row in jacobian.values for value in row
    )
    for expected in case["expected_jacobian_entries"]:
        row = next(i for i, row_id in enumerate(jacobian.row_ids)
                   if row_id.endswith(expected["component"]))
        column = next(i for i, item in enumerate(jacobian.columns)
                      if item.variable.variable_id == f"coordinate/{expected['coordinate_id']}")
        assert jacobian.values[row][column] == pytest.approx(expected["value"], abs=2e-6)


@pytest.mark.parametrize("case", reference_cases(), ids=lambda item: item["joint_kind"].lower())
def test_all_joint_families_match_spatial_local_mobility_reference(case):
    model, poses, values = build_reference_model(case)
    result = analyze_geometric_mechanism_mobility(
        model,
        MobilityFormulation.SPATIAL,
        poses,
        values,
        ground_link_id="link/parent",
        configuration_id=f"configuration/{case['joint_kind'].lower()}",
        reference_constraint_rank=6,
    )
    assert result.nominal.estimated_dof == case["nominal_dof"]
    assert result.local_mobility == case["nominal_dof"]
    assert result.jacobian_rank.estimated_rank == 6
    assert result.jacobian_rank.column_count == 6 + case["nominal_dof"]
    assert result.joint_coordinate_count == case["nominal_dof"]
    assert result.singularity_status is SingularityStatus.NOT_DETECTED

    reversed_ground = analyze_geometric_mechanism_mobility(
        model,
        MobilityFormulation.SPATIAL,
        poses,
        values,
        ground_link_id="link/child",
        configuration_id=f"configuration/{case['joint_kind'].lower()}/reversed-ground",
        reference_constraint_rank=6,
    )
    assert reversed_ground.local_mobility == result.local_mobility
    assert reversed_ground.jacobian_rank.column_count == result.jacobian_rank.column_count


def test_nontrivial_joint_frame_placements_preserve_pose_consistency():
    case = next(item for item in reference_cases() if item["joint_kind"] == "REVOLUTE")
    model, _, _ = build_reference_model(case)
    parent_frame, child_frame, joint_frame = "frame/parent", "frame/child", "frame/joint"
    parent_to_joint = RigidTransform(
        parent_frame, joint_frame, rotation((1.0, 0.0, 0.0), 0.37),
        Vec3(0.12, -0.04, 0.08), "m",
    )
    joint_to_child = RigidTransform(
        joint_frame, child_frame, rotation((0.0, 1.0, 0.0), -0.23),
        Vec3(0.02, 0.03, -0.01), "m",
    )
    model = replace(model, joint_placements=(
        JointFramePlacement("joint/main", parent_to_joint, joint_to_child),
    ))
    parent_pose = RigidTransform(
        parent_frame, "world", rotation((0.0, 0.0, 1.0), 0.41),
        Vec3(1.0, 2.0, 3.0), "m",
    )
    q_value = 0.25
    expected_joint_motion = RigidTransform(
        joint_frame, joint_frame, rotation((0.0, 0.0, 1.0), q_value),
        Vec3(0.0, 0.0, 0.0), "m",
    )
    parent_joint_to_world = parent_to_joint.inverse().then(parent_pose)
    child_joint_to_world = expected_joint_motion.then(parent_joint_to_world)
    child_pose = joint_to_child.inverse().then(child_joint_to_world)

    result = generate_joint_constraints(model).evaluate(
        {"link/parent": parent_pose, "link/child": child_pose},
        {"q/theta": q_value},
    )
    assert result.all_satisfied, result.to_dict()


def test_planar_joint_family_is_valid_in_spatial_but_not_implicit_planar_formulation():
    case = next(item for item in reference_cases() if item["joint_kind"] == "PLANAR")
    model, poses, values = build_reference_model(case)
    spatial = analyze_geometric_mechanism_mobility(
        model, MobilityFormulation.SPATIAL, poses, values,
        ground_link_id="link/parent", configuration_id="configuration/planar-joint-spatial",
        reference_constraint_rank=6,
    )
    assert spatial.local_mobility == 3
    with pytest.raises(Exception, match="explicit plane-frame contract"):
        analyze_geometric_mechanism_mobility(
            model, MobilityFormulation.PLANAR, poses, values,
            ground_link_id="link/parent", configuration_id="configuration/planar-formulation",
        )
