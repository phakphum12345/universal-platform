import pytest

from universal_platform.engineering.errors import InvalidModelError
from universal_platform.engineering.mechanism_loops import (
    LoopClosureConstraint, LoopClosureStatus, analyze_loop_topology,
    solve_mechanism_loops,
)
from universal_platform.engineering.mechanism_model import (
    FrameReference, JointKind, JointModel, LinkModel, MechanismModel,
)


def make_model(link_ids, edge_specs):
    links = tuple(LinkModel(item, "p1", f"frame/{item}") for item in link_ids)
    frames = (FrameReference("world"),) + tuple(
        FrameReference(f"frame/{item}", "world", item) for item in link_ids
    ) + (FrameReference("frame/joint"),)
    joints = tuple(
        JointModel(edge_id, JointKind.REVOLUTE, parent, child, "frame/joint",
                   (0.0, 0.0, 1.0), "rad")
        for edge_id, parent, child in edge_specs
    )
    return MechanismModel("mechanism/test", "r1", links, joints, frames)


def four_bar():
    return make_model(
        ("ground", "crank", "coupler", "rocker"),
        (("j1", "ground", "crank"), ("j2", "crank", "coupler"),
         ("j3", "coupler", "rocker"), ("j4", "rocker", "ground")),
    )


def test_four_bar_has_one_fundamental_cycle_and_three_tree_edges():
    result = analyze_loop_topology(four_bar())
    assert result.components == (("coupler", "crank", "ground", "rocker"),)
    assert result.spanning_tree_joint_ids == ("j1", "j2", "j3")
    assert result.loop_closing_joint_ids == ("j4",)
    assert result.loop_count == 1
    # The path follows the closing joint's parent-to-child direction.
    assert result.loops[0].joint_ids == ("j3", "j2", "j1", "j4")
    assert result.loops[0].link_ids[0] == result.loops[0].link_ids[-1]


def test_six_bar_single_loop_topology():
    pairs = (("a", "b"), ("b", "c"), ("c", "d"),
             ("d", "e"), ("e", "f"), ("f", "a"))
    model = make_model(("a", "b", "c", "d", "e", "f"),
                       tuple((f"j{i}", a, b) for i, (a, b) in enumerate(pairs, 1)))
    result = analyze_loop_topology(model)
    assert result.loop_count == 1
    assert len(result.spanning_tree_joint_ids) == 5
    assert result.loop_closing_joint_ids == ("j6",)
    assert len(result.loops[0].joint_ids) == 6


def test_two_independent_cycles_are_deterministic_under_input_reordering():
    edges = (("e1", "a", "b"), ("e2", "b", "c"), ("e3", "c", "a"),
             ("e4", "c", "d"), ("e5", "d", "a"))
    first = analyze_loop_topology(make_model(("a", "b", "c", "d"), edges))
    second = analyze_loop_topology(make_model(
        ("d", "c", "b", "a"), tuple(reversed(edges))))
    assert first == second
    assert first.loop_count == 2
    assert first.loop_closing_joint_ids == ("e3", "e5")
    assert len(first.spanning_tree_joint_ids) == 3


def test_disconnected_and_isolated_links_are_retained():
    result = analyze_loop_topology(make_model(
        ("a", "b", "c", "isolated"), (("j1", "a", "b"), ("j2", "b", "c"))))
    assert result.components == (("a", "b", "c"), ("isolated",))
    assert result.loop_count == 0


def test_parallel_joints_form_a_two_edge_cycle():
    result = analyze_loop_topology(make_model(
        ("a", "b"), (("j1", "a", "b"), ("j2", "b", "a"))))
    assert result.loop_count == 1
    assert result.loops[0].joint_ids == ("j1", "j2")


def test_invalid_model_is_rejected_before_graph_analysis():
    model = four_bar()
    bad = MechanismModel(model.model_id, model.revision,
                         (model.links[0], model.links[0]), model.joints, model.frames)
    with pytest.raises(InvalidModelError, match="invalid mechanism model"):
        analyze_loop_topology(bad)


def test_loop_solver_requires_residuals_for_every_closing_edge():
    model = make_model(
        ("a", "b", "c", "d"),
        (("e1", "a", "b"), ("e2", "b", "c"), ("e3", "c", "a"),
         ("e4", "c", "d"), ("e5", "d", "a")),
    )
    with pytest.raises(InvalidModelError, match="Missing explicit residuals"):
        solve_mechanism_loops(
            model, ("theta",), {"theta": 0.0},
            (LoopClosureConstraint("c1", "e3", lambda values: values["theta"] - 1.0),),
        )


def test_explicit_loop_residuals_use_existing_solver_and_report_converged():
    result = solve_mechanism_loops(
        four_bar(), ("x", "y"), {"x": 1.0, "y": 2.0},
        (LoopClosureConstraint("cx", "j4", lambda values: values["x"] - 1.0),
         LoopClosureConstraint("cy", "j4", lambda values: values["y"] - 2.0)),
    )
    assert result.status is LoopClosureStatus.CONVERGED
    assert result.solver_result.all_constraints_satisfied
    assert result.to_dict()["topology"]["loop_closing_joint_ids"] == ["j4"]


def test_failed_local_solve_is_unknown_not_unreachable():
    result = solve_mechanism_loops(
        four_bar(), ("x",), {"x": 0.0},
        (LoopClosureConstraint("constant", "j4", lambda values: 1.0),),
    )
    assert result.status is LoopClosureStatus.UNKNOWN
