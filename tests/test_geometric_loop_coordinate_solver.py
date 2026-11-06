import pytest

from universal_platform.engineering.errors import InvalidModelError
from universal_platform.engineering.geometry import Vec3
from universal_platform.engineering.geometric_loop_coordinate_solver import (
    GeometricLoopCoordinateSolveStatus,
    solve_geometric_loop_coordinates,
)
from universal_platform.engineering.mechanism_model import (
    CoordinateKind, FrameReference, GeneralizedCoordinate,
    JointCoordinateParameterization, JointFramePlacement, JointKind,
    JointModel, LinkModel, MechanismModel,
)
from universal_platform.engineering.nonlinear_solver import (
    JacobianMethod, NonlinearSolverOptions,
)
from universal_platform.engineering.transforms import RigidTransform


def make_model(link_ids, edge_specs, bounds=None):
    bounds = bounds or {}
    links = tuple(LinkModel(key, "part/1", f"frame/{key}") for key in link_ids)
    frames = [FrameReference(f"frame/{key}", owner_link_id=key) for key in link_ids]
    joints, placements, coordinates, mappings = [], [], [], []
    for joint_id, parent_id, child_id in edge_specs:
        joint_frame = f"frame/joint/{joint_id}"
        parent_frame, child_frame = f"frame/{parent_id}", f"frame/{child_id}"
        frames.append(FrameReference(joint_frame))
        joints.append(JointModel(
            joint_id, JointKind.REVOLUTE, parent_id, child_id,
            joint_frame, (0.0, 0.0, 1.0),
        ))
        placements.append(JointFramePlacement(
            joint_id, RigidTransform(parent_frame, joint_frame),
            RigidTransform(joint_frame, child_frame),
        ))
        coordinate_id = f"coordinate/{joint_id}"
        lower, upper = bounds.get(coordinate_id, (None, None))
        coordinates.append(GeneralizedCoordinate(
            coordinate_id, CoordinateKind.ROTATIONAL, "rad", (0.0, 0.0, 1.0),
            lower_limit=lower, upper_limit=upper, scale=0.5,
        ))
        mappings.append(JointCoordinateParameterization(joint_id, (coordinate_id,)))
    model = MechanismModel(
        "mechanism/coordinate-solver", "revision/1", links, tuple(joints), tuple(frames),
        schema_version="1.2", joint_placements=tuple(placements),
        generalized_coordinates=tuple(coordinates), joint_parameterizations=tuple(mappings),
    )
    poses = {link.link_id: RigidTransform(link.frame_id, "world") for link in links}
    values = {item.coordinate_id: 0.0 for item in coordinates}
    return model, poses, values


def four_bar(bounds=None):
    return make_model(
        ("ground", "crank", "coupler", "rocker"),
        (("j1", "ground", "crank"), ("j2", "crank", "coupler"),
         ("j3", "coupler", "rocker"), ("j4", "rocker", "ground")),
        bounds,
    )


def test_solves_coordinate_values_for_fixed_body_poses():
    model, poses, _ = four_bar()
    initial = {
        "coordinate/j1": 0.1,
        "coordinate/j2": -0.2,
        "coordinate/j3": 0.05,
        "coordinate/j4": 0.15,
    }
    result = solve_geometric_loop_coordinates(model, poses, initial)

    assert result.status is GeometricLoopCoordinateSolveStatus.CONVERGED
    assert result.all_satisfied
    assert result.solver_result.all_constraints_satisfied
    assert result.geometric_evaluation.all_satisfied
    assert all(value == pytest.approx(0.0, abs=1e-7)
               for value in result.coordinate_values.values())
    assert len(result.solver_result.residuals) == 24
    assert result.to_dict()["status"] == "CONVERGED"


def test_incompatible_fixed_body_poses_return_not_converged_with_evidence():
    model, poses, _ = four_bar()
    poses["rocker"] = RigidTransform(
        "frame/rocker", "world", translation=Vec3(0.02, 0.0, 0.0)
    )
    initial = {f"coordinate/j{i}": 0.0 for i in range(1, 5)}
    result = solve_geometric_loop_coordinates(model, poses, initial)

    assert result.status is GeometricLoopCoordinateSolveStatus.NOT_CONVERGED
    assert not result.all_satisfied
    assert not result.geometric_evaluation.all_satisfied
    assert any(item.status == "FAIL" for item in result.solver_result.residuals)


def test_coordinate_bounds_and_characteristic_scales_are_forwarded():
    model, poses, _ = four_bar({"coordinate/j1": (0.05, 0.2)})
    initial = {f"coordinate/j{i}": 0.1 for i in range(1, 5)}
    result = solve_geometric_loop_coordinates(model, poses, initial)

    assert result.status is GeometricLoopCoordinateSolveStatus.NOT_CONVERGED
    assert result.coordinate_values["coordinate/j1"] == pytest.approx(0.05, abs=1e-8)
    assert dict(result.solver_result.variable_scales)["coordinate/j1"] == pytest.approx(0.5)
    assert result.coordinate_values["coordinate/j1"] >= 0.05


def test_rejects_missing_loop_and_incomplete_initial_coordinates():
    model, poses, _ = make_model(
        ("ground", "crank"), (("j1", "ground", "crank"),)
    )
    with pytest.raises(InvalidModelError, match="requires a graph loop"):
        solve_geometric_loop_coordinates(model, poses, {"coordinate/j1": 0.0})

    model, poses, _ = four_bar()
    with pytest.raises(InvalidModelError, match="cover exactly the model coordinates"):
        solve_geometric_loop_coordinates(model, poses, {})


def test_rejects_analytic_option_without_an_exact_analytic_derivative():
    model, poses, _ = four_bar()
    initial = {f"coordinate/j{i}": 0.0 for i in range(1, 5)}
    with pytest.raises(InvalidModelError, match="finite differences only"):
        solve_geometric_loop_coordinates(
            model, poses, initial,
            options=NonlinearSolverOptions(jacobian_method=JacobianMethod.ANALYTIC),
        )
