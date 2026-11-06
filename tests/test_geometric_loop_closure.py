import pytest

from universal_platform.engineering.errors import InvalidModelError
from universal_platform.engineering.geometry import Vec3
from universal_platform.engineering.geometric_loop_closure import (
    GeometricLoopClosureStatus,
    evaluate_geometric_loop_closure,
)
from universal_platform.engineering.mechanism_model import (
    CoordinateKind, FrameReference, GeneralizedCoordinate, JointCoordinateParameterization,
    JointFramePlacement, JointKind, JointModel, LinkModel, MechanismModel,
)
from universal_platform.engineering.transforms import RigidTransform


def make_model(link_ids, edge_specs):
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
        coordinates.append(GeneralizedCoordinate(
            coordinate_id, CoordinateKind.ROTATIONAL, "rad", (0.0, 0.0, 1.0),
        ))
        mappings.append(JointCoordinateParameterization(joint_id, (coordinate_id,)))
    model = MechanismModel(
        "mechanism/loop-fixture", "revision/1", links, tuple(joints), tuple(frames),
        schema_version="1.2", joint_placements=tuple(placements),
        generalized_coordinates=tuple(coordinates), joint_parameterizations=tuple(mappings),
    )
    poses = {link.link_id: RigidTransform(link.frame_id, "world") for link in links}
    values = {item.coordinate_id: 0.0 for item in coordinates}
    return model, poses, values


def four_bar():
    return make_model(
        ("ground", "crank", "coupler", "rocker"),
        (("j1", "ground", "crank"), ("j2", "crank", "coupler"),
         ("j3", "coupler", "rocker"), ("j4", "rocker", "ground")),
    )


def test_evaluates_geometry_for_each_fundamental_loop():
    model, poses, values = four_bar()
    result = evaluate_geometric_loop_closure(model, poses, values)
    assert result.status is GeometricLoopClosureStatus.PASS
    assert result.all_satisfied
    assert result.topology.loop_count == 1
    assert result.topology.loop_closing_joint_ids == ("j4",)
    assert len(result.loops) == 1
    assert result.loops[0].closure_joint_id == "j4"
    assert len(result.loops[0].residuals) == 6
    assert all(item.passed for item in result.loops[0].residuals)
    assert result.to_dict()["status"] == "PASS"


def test_failed_pose_closure_is_reported_without_dropping_residuals():
    model, poses, values = four_bar()
    poses["rocker"] = RigidTransform(
        "frame/rocker", "world", translation=Vec3(0.01, 0.0, 0.0)
    )
    result = evaluate_geometric_loop_closure(model, poses, values)
    assert result.status is GeometricLoopClosureStatus.FAIL
    assert not result.all_satisfied
    assert not result.all_joint_constraints_satisfied
    assert not result.all_loop_closures_satisfied
    assert len(result.joint_evaluation.residuals) == 24
    assert any(not item.passed for item in result.loops[0].residuals)
    assert result.to_dict()["joint_evaluation"]["all_satisfied"] is False


def test_evaluates_multiple_independent_fundamental_cycles():
    model, poses, values = make_model(
        ("a", "b", "c", "d"),
        (("e1", "a", "b"), ("e2", "b", "c"), ("e3", "c", "a"),
         ("e4", "c", "d"), ("e5", "d", "a")),
    )
    result = evaluate_geometric_loop_closure(model, poses, values)
    assert result.status is GeometricLoopClosureStatus.PASS
    assert result.topology.loop_count == 2
    assert tuple(item.closure_joint_id for item in result.loops) == ("e3", "e5")
    assert all(item.all_satisfied for item in result.loops)


def test_result_is_deterministic_under_model_input_reordering():
    edges = (("j1", "ground", "crank"), ("j2", "crank", "coupler"),
             ("j3", "coupler", "rocker"), ("j4", "rocker", "ground"))
    first_model, poses, values = make_model(
        ("ground", "crank", "coupler", "rocker"), edges
    )
    second_model, _, _ = make_model(
        ("rocker", "coupler", "crank", "ground"), tuple(reversed(edges))
    )
    first = evaluate_geometric_loop_closure(first_model, poses, values)
    second = evaluate_geometric_loop_closure(second_model, poses, values)
    assert first.to_dict() == second.to_dict()


def test_rejects_models_without_a_graph_loop():
    model, poses, values = make_model(
        ("ground", "crank"), (("j1", "ground", "crank"),)
    )
    with pytest.raises(InvalidModelError, match="at least one graph loop"):
        evaluate_geometric_loop_closure(model, poses, values)
