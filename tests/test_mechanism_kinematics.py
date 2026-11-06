import json
from dataclasses import replace

import pytest

from universal_platform.engineering.errors import InvalidModelError
from universal_platform.engineering.mechanism_kinematics import (
    BranchContinuityStatus, MechanismKinematicsInput,
    solve_mechanism_kinematics,
)
from universal_platform.engineering.mechanism_loops import LoopClosureConstraint
from universal_platform.engineering.mechanism_model import (
    FrameReference, JointKind, JointModel, LinkModel, MechanismModel,
)
from universal_platform.engineering.mechanism_mobility import (
    ConstraintJacobian, MobilityFormulation,
)


def make_model(link_ids, edge_specs, model_id="integrated-mechanism"):
    links = tuple(LinkModel(item, "r1", f"frame/{item}") for item in link_ids)
    frames = (FrameReference("world"),) + tuple(
        FrameReference(f"frame/{item}", "world", item) for item in link_ids
    ) + (FrameReference("joint-frame"),)
    joints = tuple(
        JointModel(
            joint_id, JointKind.REVOLUTE, parent, child, "joint-frame",
            (0.0, 0.0, 1.0), "rad",
        )
        for joint_id, parent, child in edge_specs
    )
    return MechanismModel(model_id, "rev-1", links, joints, frames)


def four_bar():
    return make_model(
        ("ground", "crank", "coupler", "rocker"),
        (("j1", "ground", "crank"), ("j2", "crank", "coupler"),
         ("j3", "coupler", "rocker"), ("j4", "rocker", "ground")),
    )


def multi_loop():
    return make_model(
        ("ground", "a", "b", "c", "d"),
        (("j1", "ground", "a"), ("j2", "a", "b"), ("j3", "b", "ground"),
         ("j4", "b", "c"), ("j5", "c", "d"), ("j6", "d", "ground")),
        "integrated-multi-loop",
    )


def make_problem(model, *, configuration_id="cfg/1", branch_id="assembly/left"):
    if model.model_id == "integrated-mechanism":
        coordinate_count, closing_ids = 9, ("j4",)
    else:
        coordinate_count, closing_ids = 12, ("j3", "j6")
    coordinate_ids = tuple(f"q{i}" for i in range(coordinate_count))
    constraint_count = coordinate_count - 1
    constraints = []
    for i in range(constraint_count):
        closure_joint = closing_ids[0] if i < constraint_count // len(closing_ids) else closing_ids[-1]
        constraints.append(LoopClosureConstraint(
            f"c{i}", closure_joint,
            lambda values, name=coordinate_ids[i]: values[name],
        ))
    # Each closing edge must be represented; residuals are zero at the origin.
    values = tuple(
        tuple(1.0 if col == row else 0.0 for col in range(coordinate_count))
        for row in range(constraint_count)
    )
    jacobian = ConstraintJacobian(
        tuple(item.constraint_id for item in constraints),
        coordinate_ids,
        values,
        configuration_id,
        "fixture:analytic-constraint-jacobian",
    )
    return MechanismKinematicsInput(
        model=model,
        ground_link_id="ground",
        formulation=MobilityFormulation.PLANAR,
        coordinate_ids=coordinate_ids,
        configuration_id=configuration_id,
        branch_id=branch_id,
        initial_coordinates={key: 0.0 for key in coordinate_ids},
        loop_constraints=tuple(constraints),
        jacobian=jacobian,
        velocity_bias=tuple(0.0 for _ in constraints),
        acceleration_bias=tuple(0.0 for _ in constraints),
        initial_velocity={key: 0.0 for key in coordinate_ids},
        initial_acceleration={key: 0.0 for key in coordinate_ids},
        velocity_bias_source="fixture:time-derivative-of-constraints",
        acceleration_bias_source="fixture:second-time-derivative-of-constraints",
        reference_constraint_rank=constraint_count,
    )


def test_four_bar_integrates_position_mobility_velocity_and_acceleration():
    result = solve_mechanism_kinematics(make_problem(four_bar()))
    assert result.status == "COMPLETE"
    assert result.position.status.value == "CONVERGED"
    assert result.mobility is not None
    assert result.mobility.nominal.estimated_dof == 1
    assert result.mobility.local_mobility == 1
    assert result.velocity is not None
    assert result.velocity.solver_result.all_constraints_satisfied
    assert result.velocity.solution_uniqueness == "NON_UNIQUE"
    assert result.acceleration is not None
    assert result.acceleration.solver_result.all_constraints_satisfied
    assert result.acceleration.solution_uniqueness == "NON_UNIQUE"


def test_multi_loop_integration_covers_each_loop_closing_joint():
    result = solve_mechanism_kinematics(make_problem(multi_loop()))
    assert result.status == "COMPLETE"
    assert result.position.topology.loop_count == 2
    assert set(result.position.topology.loop_closing_joint_ids) == {"j3", "j6"}
    assert result.mobility is not None
    assert result.mobility.jacobian_rank.estimated_rank == 11
    assert result.velocity is not None
    assert result.acceleration is not None


def test_same_branch_reuses_previous_position_as_continuation_seed():
    first = solve_mechanism_kinematics(make_problem(four_bar(), configuration_id="cfg/1"))
    second = solve_mechanism_kinematics(make_problem(
        four_bar(), configuration_id="cfg/2", branch_id="assembly/left"
    ), previous_result=first)
    assert second.continuity_status is BranchContinuityStatus.CONTINUOUS
    assert second.previous_configuration_id == "cfg/1"
    assert second.position.solver_result.values == first.position.solver_result.values


def test_branch_change_is_explicit_and_uses_new_initial_coordinates():
    first = solve_mechanism_kinematics(make_problem(four_bar(), configuration_id="cfg/1"))
    second = solve_mechanism_kinematics(make_problem(
        four_bar(), configuration_id="cfg/2", branch_id="assembly/right"
    ), previous_result=first)
    assert second.continuity_status is BranchContinuityStatus.BRANCH_SWITCH
    assert second.position.solver_result.values == {
        key: 0.0 for key in second.coordinate_ids
    }


def test_versioned_result_preserves_configuration_and_provenance():
    result = solve_mechanism_kinematics(make_problem(four_bar()))
    snapshot = result.to_dict()
    encoded = json.dumps(snapshot, sort_keys=True)
    assert json.loads(encoded)["schema_version"] == "1.0"
    assert json.loads(encoded)["configuration"]["branch_id"] == "assembly/left"
    assert json.loads(encoded)["provenance"]["jacobian_source"] == (
        "fixture:analytic-constraint-jacobian"
    )
    assert json.dumps(result.to_dict(), sort_keys=True) == encoded


def test_input_contract_rejects_mismatched_jacobian_order_and_bias_shapes():
    problem = make_problem(four_bar())
    bad = replace(problem, velocity_bias=(0.0,))
    with pytest.raises(InvalidModelError, match="velocity_bias length"):
        solve_mechanism_kinematics(bad)


def test_previous_result_from_another_model_revision_is_rejected():
    first = solve_mechanism_kinematics(make_problem(four_bar()))
    changed = make_model(
        ("ground", "crank", "coupler", "rocker"),
        (("j1", "ground", "crank"), ("j2", "crank", "coupler"),
         ("j3", "coupler", "rocker"), ("j4", "rocker", "ground")),
    )
    changed = MechanismModel(
        changed.model_id, "rev-2", changed.links, changed.joints, changed.frames
    )
    with pytest.raises(InvalidModelError, match="previous_result"):
        solve_mechanism_kinematics(make_problem(changed), previous_result=first)
