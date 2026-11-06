import pytest

from universal_platform.engineering.errors import InvalidModelError
from universal_platform.engineering.mechanism_model import (
    CoordinateKind, FrameReference, GeneralizedCoordinate,
    JointCoordinateParameterization, JointFramePlacement, JointKind,
    JointModel, LinkModel, MechanismModel,
)
from universal_platform.engineering.mechanism_mobility import (
    ConstraintJacobian, MobilityFormulation, SingularityStatus,
    analyze_geometric_mechanism_mobility, analyze_mechanism_mobility,
)
from universal_platform.engineering.transforms import RigidTransform


def two_link_model(kind):
    parent, child, joint_frame = "frame/parent", "frame/child", "frame/joint"
    coordinates = ()
    parameterizations = ()
    axis = None
    unit = None
    if kind is JointKind.REVOLUTE:
        axis, unit = (0.0, 0.0, 1.0), "rad"
        coordinates = (GeneralizedCoordinate(
            "q/theta", CoordinateKind.ROTATIONAL, "rad", axis,
        ),)
        parameterizations = (JointCoordinateParameterization("joint/main", ("q/theta",)),)
    elif kind is JointKind.PRISMATIC:
        axis, unit = (1.0, 0.0, 0.0), "m"
        coordinates = (GeneralizedCoordinate(
            "q/x", CoordinateKind.TRANSLATIONAL, "m", axis,
        ),)
        parameterizations = (JointCoordinateParameterization("joint/main", ("q/x",)),)
    model = MechanismModel(
        f"model/{kind.value.lower()}", "revision/1",
        (
            LinkModel("link/parent", "part/1", parent),
            LinkModel("link/child", "part/1", child),
        ),
        (JointModel(
            "joint/main", kind, "link/parent", "link/child",
            joint_frame, axis, unit,
        ),),
        (
            FrameReference(parent, owner_link_id="link/parent"),
            FrameReference(child, owner_link_id="link/child"),
            FrameReference(joint_frame),
        ),
        schema_version="1.2",
        joint_placements=(JointFramePlacement(
            "joint/main", RigidTransform(parent, joint_frame),
            RigidTransform(joint_frame, child),
        ),),
        generalized_coordinates=coordinates,
        joint_parameterizations=parameterizations,
    )
    poses = {
        "link/parent": RigidTransform(parent, "world"),
        "link/child": RigidTransform(child, "world"),
    }
    values = {item.coordinate_id: 0.0 for item in coordinates}
    return model, poses, values


@pytest.mark.parametrize(
    "kind,expected_mobility,expected_variables,joint_coordinate_count",
    [
        (JointKind.FIXED, 0, 6, 0),
        (JointKind.REVOLUTE, 1, 7, 1),
        (JointKind.PRISMATIC, 1, 7, 1),
    ],
)
def test_generated_spatial_mobility_matches_single_joint_reference(
    kind, expected_mobility, expected_variables, joint_coordinate_count
):
    model, poses, values = two_link_model(kind)
    result = analyze_geometric_mechanism_mobility(
        model, MobilityFormulation.SPATIAL, poses, values,
        ground_link_id="link/parent", configuration_id=f"configuration/{kind.value}",
        reference_constraint_rank=6,
    )

    assert result.nominal.estimated_dof == expected_mobility
    assert result.local_mobility == expected_mobility
    assert result.jacobian_rank.estimated_rank == 6
    assert result.jacobian_rank.column_count == expected_variables
    assert result.joint_coordinate_count == joint_coordinate_count
    assert result.singularity_status is SingularityStatus.NOT_DETECTED
    snapshot = result.to_dict()
    assert snapshot["local"]["joint_coordinate_count"] == joint_coordinate_count
    assert snapshot["local"]["body_pose_coordinate_count"] == 6


def test_ground_pose_is_removed_when_ground_link_is_reversed():
    model, poses, values = two_link_model(JointKind.REVOLUTE)
    result = analyze_geometric_mechanism_mobility(
        model, MobilityFormulation.SPATIAL, poses, values,
        ground_link_id="link/child", configuration_id="configuration/reversed-ground",
    )
    assert result.local_mobility == 1
    assert result.jacobian_rank.column_count == 7
    assert result.joint_coordinate_count == 1


def test_generated_geometric_mobility_is_spatial_only_until_plane_contract_exists():
    model, poses, values = two_link_model(JointKind.REVOLUTE)
    with pytest.raises(InvalidModelError, match="explicit plane-frame contract"):
        analyze_geometric_mechanism_mobility(
            model, MobilityFormulation.PLANAR, poses, values,
            ground_link_id="link/parent", configuration_id="configuration/planar",
        )


def test_combined_jacobian_declares_joint_coordinate_variables_explicitly():
    model, _, _ = two_link_model(JointKind.REVOLUTE)
    invalid = ConstraintJacobian(
        ("constraint/1",), ("body/x",), ((1.0,),), "configuration/1",
        "test:invalid", ("coordinate/q",),
    )
    with pytest.raises(InvalidModelError, match="subset of Jacobian variables"):
        analyze_mechanism_mobility(
            model, MobilityFormulation.SPATIAL, invalid,
            ground_link_id="link/parent",
        )


def test_legacy_caller_supplied_body_jacobian_contract_remains_compatible():
    model, _, _ = two_link_model(JointKind.REVOLUTE)
    jacobian = ConstraintJacobian(
        tuple(f"constraint/{i}" for i in range(6)),
        tuple(f"body/{i}" for i in range(6)),
        tuple(tuple(1.0 if row == col else 0.0 for col in range(6)) for row in range(6)),
        "configuration/legacy", "caller:reference",
    )
    result = analyze_mechanism_mobility(
        model, MobilityFormulation.SPATIAL, jacobian,
        ground_link_id="link/parent",
    )
    assert result.local_mobility == 0
    assert result.joint_coordinate_count == 0
