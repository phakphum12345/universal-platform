import json

import pytest

from universal_platform.engineering.errors import InvalidModelError
from universal_platform.engineering.mechanism_model import (
    FrameReference, JointKind, JointModel, LinkModel, MechanismModel,
)
from universal_platform.engineering.mechanism_mobility import (
    ConstraintJacobian, MobilityFormulation, SingularityStatus,
    analyze_mechanism_mobility, estimate_nominal_mobility,
)


def make_model(link_ids, edge_specs, model_id="test-mechanism"):
    links = tuple(LinkModel(item, "r1", f"frame/{item}") for item in link_ids)
    frames = (FrameReference("world"),) + tuple(
        FrameReference(f"frame/{item}", "world", item) for item in link_ids
    ) + (FrameReference("joint-frame"),)
    joints = tuple(
        JointModel(
            joint_id, kind, parent, child, "joint-frame",
            (0.0, 0.0, 1.0) if kind in (
                JointKind.REVOLUTE, JointKind.PRISMATIC, JointKind.CYLINDRICAL,
                JointKind.HELICAL,
            ) else None,
            "rad" if kind in (JointKind.REVOLUTE, JointKind.HELICAL) else (
                "m" if kind is JointKind.PRISMATIC else None
            ),
        )
        for joint_id, kind, parent, child in edge_specs
    )
    return MechanismModel(model_id, "rev-1", links, joints, frames)


def four_bar():
    return make_model(
        ("ground", "crank", "coupler", "rocker"),
        (
            ("j1", JointKind.REVOLUTE, "ground", "crank"),
            ("j2", JointKind.REVOLUTE, "crank", "coupler"),
            ("j3", JointKind.REVOLUTE, "coupler", "rocker"),
            ("j4", JointKind.REVOLUTE, "rocker", "ground"),
        ),
    )


def planar_four_bar_jacobian(rank=8, rows=8):
    base = []
    for index in range(rows):
        base.append(tuple(
            1.0 if col == index else 0.0 for col in range(9)
        ) if index < rank else tuple(0.0 for _ in range(9)))
    return ConstraintJacobian(
        tuple(f"c{i}" for i in range(rows)),
        tuple(f"q{i}" for i in range(9)),
        tuple(base), "configuration/assembly-A", "test:analytic-fixture",
    )


def test_planar_four_bar_nominal_kutzbach_count_is_one():
    estimate = estimate_nominal_mobility(four_bar(), MobilityFormulation.PLANAR, ground_link_id="ground")
    assert estimate.free_body_dof == 9
    assert estimate.nominal_joint_constraints == 8
    assert estimate.estimated_dof == 1
    assert estimate.formula == "M = 3*(N-1) - sum(3-f_i)"


def test_spatial_revolute_pair_nominal_dof_is_one():
    model = make_model(
        ("ground", "link"),
        (("j1", JointKind.REVOLUTE, "ground", "link"),),
    )
    estimate = estimate_nominal_mobility(model, MobilityFormulation.SPATIAL, ground_link_id="ground")
    assert estimate.free_body_dof == 6
    assert estimate.nominal_joint_constraints == 5
    assert estimate.estimated_dof == 1


def test_planar_formulation_rejects_spatial_only_joint_types():
    model = make_model(
        ("ground", "link"),
        (("j1", JointKind.SPHERICAL, "ground", "link"),),
    )
    with pytest.raises(InvalidModelError, match="not supported by the PLANAR"):
        estimate_nominal_mobility(model, MobilityFormulation.PLANAR, ground_link_id="ground")


def test_local_mobility_uses_jacobian_rank_not_kutzbach_count():
    result = analyze_mechanism_mobility(
        four_bar(), MobilityFormulation.PLANAR, planar_four_bar_jacobian(), ground_link_id="ground",
        reference_constraint_rank=8,
    )
    assert result.nominal.estimated_dof == 1
    assert result.jacobian_rank.estimated_rank == 8
    assert result.local_mobility == 1
    assert result.redundant_constraint_count == 0
    assert result.singularity_status is SingularityStatus.NOT_DETECTED


def test_redundant_constraint_rows_are_reported_separately():
    result = analyze_mechanism_mobility(
        four_bar(), MobilityFormulation.PLANAR,
        planar_four_bar_jacobian(rank=8, rows=9), ground_link_id="ground",
        reference_constraint_rank=8,
    )
    assert result.jacobian_rank.estimated_rank == 8
    assert result.local_mobility == 1
    assert result.redundant_constraint_count == 1
    assert result.redundant_constraints_detected


def test_rank_drop_against_reference_flags_only_possible_singularity():
    result = analyze_mechanism_mobility(
        four_bar(), MobilityFormulation.PLANAR,
        planar_four_bar_jacobian(rank=7, rows=8), ground_link_id="ground",
        reference_constraint_rank=8,
    )
    assert result.local_mobility == 2
    assert result.singularity_status is SingularityStatus.POSSIBLE_SINGULARITY


def test_singularity_is_unknown_without_regular_reference_rank():
    result = analyze_mechanism_mobility(
        four_bar(), MobilityFormulation.PLANAR, planar_four_bar_jacobian(), ground_link_id="ground"
    )
    assert result.singularity_status is SingularityStatus.UNKNOWN


def test_nominal_overconstraint_does_not_override_local_rank_result():
    model = make_model(
        ("ground", "a", "b"),
        (
            ("j1", JointKind.REVOLUTE, "ground", "a"),
            ("j2", JointKind.REVOLUTE, "a", "b"),
            ("j3", JointKind.REVOLUTE, "b", "ground"),
            ("j4", JointKind.REVOLUTE, "ground", "b"),
        ),
    )
    # 6 free planar coordinates; 8 nominal joint constraints => M=-2.
    jac = ConstraintJacobian(
        tuple(f"c{i}" for i in range(8)),
        tuple(f"q{i}" for i in range(6)),
        tuple(tuple(1.0 if col == row % 6 else 0.0 for col in range(6))
              for row in range(8)),
        "configuration/overconstrained-fixture", "test:fixture",
    )
    result = analyze_mechanism_mobility(model, MobilityFormulation.PLANAR, jac, ground_link_id="ground")
    assert result.nominal.estimated_dof == -2
    assert result.nominal_overconstrained
    assert result.jacobian_rank.estimated_rank == 6
    assert result.local_mobility == 0
    assert result.redundant_constraint_count == 2


def test_jacobian_shape_and_identifiers_are_validated():
    model = four_bar()
    bad = ConstraintJacobian(("c1",), ("q1", "q2"), ((1.0,),),
                             "cfg", "fixture")
    with pytest.raises(InvalidModelError, match="column count"):
        analyze_mechanism_mobility(model, MobilityFormulation.PLANAR, bad, ground_link_id="ground")


@pytest.mark.parametrize("values", [((1.0, float("nan")),), ((1.0, True),)])
def test_jacobian_rejects_non_finite_and_boolean_entries(values):
    model = four_bar()
    jac = ConstraintJacobian(("c1",), ("q1", "q2"), values, "cfg", "fixture")
    with pytest.raises(InvalidModelError, match="finite numbers"):
        analyze_mechanism_mobility(model, MobilityFormulation.PLANAR, jac)


def test_reference_rank_and_tolerance_are_validated():
    model = four_bar()
    jac = planar_four_bar_jacobian()
    with pytest.raises(InvalidModelError, match="reference_constraint_rank"):
        analyze_mechanism_mobility(
            model, MobilityFormulation.PLANAR, jac, ground_link_id="ground", reference_constraint_rank=9
        )
    with pytest.raises(InvalidModelError, match="rank_tolerance"):
        analyze_mechanism_mobility(
            model, MobilityFormulation.PLANAR, jac, ground_link_id="ground", rank_tolerance=0.0
        )


def test_result_snapshot_is_versioned_deterministic_and_has_provenance():
    result = analyze_mechanism_mobility(
        four_bar(), MobilityFormulation.PLANAR, planar_four_bar_jacobian(),
        reference_constraint_rank=8,
    )
    encoded = json.dumps(result.to_dict(), sort_keys=True)
    assert json.loads(encoded)["schema_version"] == "1.0"
    assert json.loads(encoded)["model"] == {
        "model_id": "test-mechanism", "revision": "rev-1", "ground_link_id": "ground"
    }
    assert json.loads(encoded)["configuration_id"] == "configuration/assembly-A"
    assert json.dumps(result.to_dict(), sort_keys=True) == encoded


def test_analysis_requires_explicit_ground_and_full_free_body_coordinate_set():
    model = four_bar()
    jac = ConstraintJacobian(("c1",), tuple(f"q{i}" for i in range(8)),
                             (tuple(1.0 for _ in range(8)),), "cfg", "fixture")
    with pytest.raises(InvalidModelError, match="ground_link_id"):
        estimate_nominal_mobility(model, MobilityFormulation.PLANAR, ground_link_id="")
    with pytest.raises(InvalidModelError, match="coordinate count must match"):
        analyze_mechanism_mobility(
            model, MobilityFormulation.PLANAR, jac, ground_link_id="ground"
        )
