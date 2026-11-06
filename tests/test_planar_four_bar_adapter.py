import json
import math

import pytest

from universal_platform.engineering.errors import InvalidModelError, SolverError
from universal_platform.engineering.planar_four_bar_adapter import (
    PlanarFourBarModelSnapshot,
    solve_planar_four_bar_model,
)
from universal_platform.engineering.provenance import EvidenceStatus
from universal_platform.engineering.quantity import LENGTH, Quantity


def model(**overrides):
    values = dict(
        model_id="mechanism/demo-4r",
        model_revision="rev-001",
        ground_link_id="link/ground",
        input_link_id="link/input",
        coupler_link_id="link/coupler",
        output_link_id="link/output",
        input_ground_joint_id="joint/A",
        input_coupler_joint_id="joint/B",
        coupler_output_joint_id="joint/C",
        output_ground_joint_id="joint/D",
        ground_length=Quantity.of(40, "cm"),
        input_crank_length=Quantity.of(10, "cm"),
        coupler_length=Quantity.of(300, "mm"),
        output_rocker_length=Quantity.of(0.3, "m"),
        input_angle_rad=math.pi / 2,
        branch="left",
        tolerance=Quantity.of(1e-6, "mm"),
    )
    values.update(overrides)
    return PlanarFourBarModelSnapshot(**values)


def test_model_adapter_converts_mixed_length_units_to_si_and_maps_stable_ids():
    result = solve_planar_four_bar_model(model())
    assert result.model_id == "mechanism/demo-4r"
    assert result.model_revision == "rev-001"
    assert dict(result.joint_positions_m)["joint/D"] == pytest.approx((0.4, 0.0))
    assert result.geometry.input_joint_x == pytest.approx(0.0, abs=1e-12)
    assert result.geometry.input_joint_y == pytest.approx(0.1)
    assert result.geometry.closure_error <= 1e-9
    assert result.evidence.status is EvidenceStatus.PASS


@pytest.mark.parametrize("branch", ["left", "right"])
def test_model_adapter_preserves_explicit_assembly_branch(branch):
    result = solve_planar_four_bar_model(model(branch=branch))
    assert result.branch == branch
    assert result.geometry.branch == branch


def test_model_adapter_serializes_deterministic_schema_and_provenance():
    result = solve_planar_four_bar_model(model())
    first = result.to_dict()
    second = result.to_dict()
    assert first == second
    assert first["schema_version"] == "1.0"
    assert first["model_revision"] == "rev-001"
    assert first["evidence"]["status"] == "PASS"
    json.dumps(first, sort_keys=True)


@pytest.mark.parametrize(
    "field,value,match",
    [
        ("model_id", "", "identifiers"),
        ("model_revision", " ", "identifiers"),
        ("input_link_id", "link/ground", "link identifiers"),
        ("output_ground_joint_id", "joint/A", "joint identifiers"),
        ("branch", "unknown", "Branch"),
        ("input_angle_rad", float("nan"), "angle"),
    ],
)
def test_model_adapter_rejects_invalid_identity_branch_and_angle(field, value, match):
    with pytest.raises(InvalidModelError, match=match):
        solve_planar_four_bar_model(model(**{field: value}))


def test_model_adapter_rejects_dimension_mismatch():
    with pytest.raises(InvalidModelError, match="LENGTH"):
        solve_planar_four_bar_model(model(ground_length=Quantity.of(1, "s")))


def test_model_adapter_rejects_raw_float_lengths():
    with pytest.raises(InvalidModelError, match="Quantity"):
        solve_planar_four_bar_model(model(ground_length=0.4))


def test_model_adapter_rejects_unreachable_geometry_without_fabricating_result():
    with pytest.raises(SolverError, match="cannot close"):
        solve_planar_four_bar_model(model(
            ground_length=Quantity.of(4, "m"),
            input_crank_length=Quantity.of(1, "m"),
            coupler_length=Quantity.of(1, "m"),
            output_rocker_length=Quantity.of(1, "m"),
            input_angle_rad=0.0,
        ))


def test_model_adapter_rejects_duplicate_link_ids():
    with pytest.raises(InvalidModelError, match="link identifiers"):
        solve_planar_four_bar_model(model(coupler_link_id="link/input"))
