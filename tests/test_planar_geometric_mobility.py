import copy
import json
from dataclasses import replace
from pathlib import Path
from math import cos, sin

import pytest

from universal_platform.engineering.errors import InvalidModelError
from universal_platform.engineering.geometry import Vec3
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
    return json.loads(FIXTURE.read_text(encoding="utf-8"))["cases"]


PLANAR_KINDS = {"FIXED", "REVOLUTE", "PRISMATIC", "PLANAR"}


def build_model(case):
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
    raw = case["parameterization"]
    parameterizations = ()
    if raw is not None:
        parameterizations = (JointCoordinateParameterization(
            "joint/main",
            tuple(raw["coordinate_ids"]),
            pitch_m_per_rad=raw.get("pitch_m_per_rad"),
            coordinate_convention=raw.get("coordinate_convention"),
        ),)
    model = MechanismModel(
        f"model/planar-mobility/{kind.value.lower()}",
        "revision/1",
        (
            LinkModel("link/parent", "part/parent", parent_frame),
            LinkModel("link/child", "part/child", child_frame),
        ),
        (JointModel(
            "joint/main", kind, "link/parent", "link/child", joint_frame,
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
    return model, poses, dict(case["coordinate_values"])


def rotation_z(angle):
    c, s = cos(angle), sin(angle)
    return ((c, -s, 0.0), (s, c, 0.0), (0.0, 0.0, 1.0))


def rotation_x(angle):
    c, s = cos(angle), sin(angle)
    return ((1.0, 0.0, 0.0), (0.0, c, -s), (0.0, s, c))


def cases_for_planar():
    return [item for item in reference_cases() if item["joint_kind"] in PLANAR_KINDS]


@pytest.mark.parametrize("case", cases_for_planar(), ids=lambda item: item["joint_kind"].lower())
def test_planar_plane_frame_mobility_matches_supported_joint_references(case):
    model, poses, values = build_model(case)
    result = analyze_geometric_mechanism_mobility(
        model,
        MobilityFormulation.PLANAR,
        poses,
        values,
        ground_link_id="link/parent",
        configuration_id=f"planar/{case['joint_kind'].lower()}",
        reference_constraint_rank=3,
        plane_frame=RigidTransform("plane/xy", "world"),
    )
    assert result.nominal.estimated_dof == case["nominal_dof"]
    assert result.local_mobility == case["nominal_dof"]
    assert result.jacobian_rank.estimated_rank == 3
    assert result.jacobian_rank.column_count == 3 + case["nominal_dof"]
    assert result.joint_coordinate_count == case["nominal_dof"]
    assert result.singularity_status is SingularityStatus.NOT_DETECTED

    reversed_ground = analyze_geometric_mechanism_mobility(
        model,
        MobilityFormulation.PLANAR,
        poses,
        values,
        ground_link_id="link/child",
        configuration_id=f"planar/{case['joint_kind'].lower()}/reversed",
        reference_constraint_rank=3,
        plane_frame=RigidTransform("plane/xy", "world"),
    )
    assert reversed_ground.local_mobility == result.local_mobility
    assert reversed_ground.jacobian_rank.column_count == result.jacobian_rank.column_count


def test_planar_mobility_requires_an_explicit_plane_frame():
    case = next(item for item in cases_for_planar() if item["joint_kind"] == "REVOLUTE")
    model, poses, values = build_model(case)
    with pytest.raises(InvalidModelError, match="explicit plane-frame contract"):
        analyze_geometric_mechanism_mobility(
            model, MobilityFormulation.PLANAR, poses, values,
            ground_link_id="link/parent", configuration_id="planar/missing-frame",
        )


def test_rotated_and_translated_plane_frame_preserves_planar_joint_mobility():
    case = next(item for item in cases_for_planar() if item["joint_kind"] == "PLANAR")
    model, _, _ = build_model(case)
    plane_id = "plane/tilted"
    plane_to_world = RigidTransform(
        plane_id, "world", rotation_x(0.31), Vec3(1.2, -0.7, 2.1), "m",
    )
    parent_frame, child_frame, joint_frame = "frame/parent", "frame/child", "frame/joint"
    parent_to_plane = RigidTransform(
        parent_frame, plane_id, rotation_z(0.2), Vec3(0.3, 0.1, 0.0), "m",
    )
    parent_pose = parent_to_plane.then(plane_to_world)
    qx, qy, qtheta = 0.1, -0.15, 0.28
    expected_motion = RigidTransform(
        joint_frame, joint_frame, rotation_z(qtheta), Vec3(qx, qy, 0.0), "m",
    )
    placement = model.joint_placements[0]
    parent_joint_to_world = placement.parent_to_joint.inverse().then(parent_pose)
    child_joint_to_world = expected_motion.then(parent_joint_to_world)
    child_pose = placement.joint_to_child.inverse().then(child_joint_to_world)

    result = analyze_geometric_mechanism_mobility(
        model,
        MobilityFormulation.PLANAR,
        {"link/parent": parent_pose, "link/child": child_pose},
        {"q/x": qx, "q/y": qy, "q/theta": qtheta},
        ground_link_id="link/parent",
        configuration_id="planar/rotated-plane",
        reference_constraint_rank=3,
        plane_frame=plane_to_world,
    )
    assert result.local_mobility == 3
    assert result.jacobian_rank.estimated_rank == 3
    assert result.jacobian_rank.column_count == 6


def test_planar_mobility_rejects_out_of_plane_body_origin_and_tilt():
    case = next(item for item in cases_for_planar() if item["joint_kind"] == "REVOLUTE")
    model, poses, values = build_model(case)
    poses["link/child"] = RigidTransform(
        "frame/child", "world", translation=Vec3(0.0, 0.0, 0.01),
    )
    with pytest.raises(InvalidModelError, match="outside the declared plane"):
        analyze_geometric_mechanism_mobility(
            model, MobilityFormulation.PLANAR, poses, values,
            ground_link_id="link/parent", configuration_id="planar/off-plane",
            plane_frame=RigidTransform("plane/xy", "world"),
        )

    poses["link/child"] = RigidTransform(
        "frame/child", "world", rotation_x(0.1),
    )
    with pytest.raises(InvalidModelError, match=r"local \+Z aligned"):
        analyze_geometric_mechanism_mobility(
            model, MobilityFormulation.PLANAR, poses, values,
            ground_link_id="link/parent", configuration_id="planar/tilted-body",
            plane_frame=RigidTransform("plane/xy", "world"),
        )


def test_planar_mobility_rejects_off_plane_joint_anchor_and_axis():
    case = next(item for item in cases_for_planar() if item["joint_kind"] == "PRISMATIC")
    model, poses, values = build_model(case)
    placement = model.joint_placements[0]
    off_plane_parent_to_joint = RigidTransform(
        "frame/parent", "frame/joint", translation=Vec3(0.0, 0.0, 0.02),
    )
    model_with_bad_anchor = replace(
        model,
        joint_placements=(JointFramePlacement(
            "joint/main", off_plane_parent_to_joint, placement.joint_to_child,
        ),),
    )
    with pytest.raises(InvalidModelError, match="Joint frame origin"):
        analyze_geometric_mechanism_mobility(
            model_with_bad_anchor, MobilityFormulation.PLANAR, poses, values,
            ground_link_id="link/parent", configuration_id="planar/off-plane-anchor",
            plane_frame=RigidTransform("plane/xy", "world"),
        )

    bad_case = copy.deepcopy(case)
    bad_case["joint_axis"] = [0.0, 0.0, 1.0]
    bad_case["coordinates"][0]["axis"] = [0.0, 0.0, 1.0]
    bad_model, poses, values = build_model(bad_case)
    with pytest.raises(InvalidModelError, match="must lie in the plane"):
        analyze_geometric_mechanism_mobility(
            bad_model, MobilityFormulation.PLANAR, poses, values,
            ground_link_id="link/parent", configuration_id="planar/out-of-plane-axis",
            plane_frame=RigidTransform("plane/xy", "world"),
        )


def test_planar_mobility_rejects_unsupported_joint_family_and_bad_plane_frame():
    case = next(item for item in reference_cases() if item["joint_kind"] == "CYLINDRICAL")
    model, poses, values = build_model(case)
    with pytest.raises(InvalidModelError, match="not supported by the PLANAR mobility formulation"):
        analyze_geometric_mechanism_mobility(
            model, MobilityFormulation.PLANAR, poses, values,
            ground_link_id="link/parent", configuration_id="planar/cylindrical",
            plane_frame=RigidTransform("plane/xy", "world"),
        )

    supported = next(item for item in cases_for_planar() if item["joint_kind"] == "FIXED")
    model, poses, values = build_model(supported)
    with pytest.raises(InvalidModelError, match="same shared world frame"):
        analyze_geometric_mechanism_mobility(
            model, MobilityFormulation.PLANAR, poses, values,
            ground_link_id="link/parent", configuration_id="planar/wrong-world",
            plane_frame=RigidTransform("plane/xy", "other-world"),
        )
    with pytest.raises(InvalidModelError, match="finite and positive"):
        analyze_geometric_mechanism_mobility(
            model, MobilityFormulation.PLANAR, poses, values,
            ground_link_id="link/parent", configuration_id="planar/bad-tolerance",
            plane_frame=RigidTransform("plane/xy", "world"),
            plane_tolerance_m=0.0,
        )


def test_planar_mobility_requires_metre_based_plane_frame():
    case = next(item for item in cases_for_planar() if item["joint_kind"] == "FIXED")
    model, poses, values = build_model(case)
    with pytest.raises(InvalidModelError, match="must use metres"):
        analyze_geometric_mechanism_mobility(
            model, MobilityFormulation.PLANAR, poses, values,
            ground_link_id="link/parent", configuration_id="planar/non-metre-frame",
            plane_frame=RigidTransform("plane/xy", "world", length_unit="mm"),
        )
