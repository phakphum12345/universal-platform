import json
import math
from pathlib import Path

import pytest

from universal_platform.engineering.assembly import Assembly, Joint, JointType, PartOccurrence
from universal_platform.engineering.constraints import Constraint, ConstraintKind, evaluate_constraints
from universal_platform.engineering.electrical import electrical_power, ohms_law
from universal_platform.engineering.geometry import Box, Cylinder, Vec3
from universal_platform.engineering.inverse_kinematics import solve_planar_two_link_inverse_kinematics
from universal_platform.engineering.linear_solver import solve_linear
from universal_platform.engineering.materials import Material
from universal_platform.engineering.mechanics import axial_strain, axial_stress, factor_of_safety
from universal_platform.engineering.planar_four_bar_adapter import PlanarFourBarModelSnapshot, solve_planar_four_bar_model
from universal_platform.engineering.provenance import EvidenceKind, EvidenceRecord, EvidenceStatus
from universal_platform.engineering.quantity import Quantity
from universal_platform.engineering.safety import RiskTier, SafetyGate
from universal_platform.engineering.simulation import solve_static_linear_system
from universal_platform.engineering.thermal import linear_thermal_expansion
from universal_platform.engineering.transforms import RigidTransform


REFERENCE_FILE = Path(__file__).parent / "reference_cases" / "engineering_reference_cases.json"
REGISTRY = json.loads(REFERENCE_FILE.read_text(encoding="utf-8"))


def quantity(spec):
    return Quantity.of(spec["value"], spec["unit"])


def evaluate(case):
    operation, data = case["operation"], case["inputs"]
    if operation == "quantity.convert":
        return quantity(data).in_unit(data["target_unit"])
    if operation == "mechanics.axial_stress":
        area = quantity(data["width"]) * quantity(data["height"])
        return axial_stress(quantity(data["force"]), area).in_unit(data["unit"])
    if operation == "mechanics.axial_strain":
        return axial_strain(quantity(data["extension"]), quantity(data["length"])).si_value
    if operation == "mechanics.factor_of_safety":
        return factor_of_safety(quantity(data["yield_strength"]), quantity(data["applied_stress"]))
    if operation == "electrical.ohms_law":
        return ohms_law(quantity(data["voltage"]), quantity(data["resistance"])).in_unit(data["unit"])
    if operation == "electrical.power":
        return electrical_power(quantity(data["voltage"]), quantity(data["current"])).in_unit(data["unit"])
    if operation == "thermal.linear_expansion":
        return linear_thermal_expansion(
            quantity(data["length"]), data["coefficient_per_kelvin"],
            data["temperature_change_kelvin"],
        ).in_unit(data["unit"])
    if operation == "geometry.box_volume":
        return Box(data["length"], data["width"], data["height"]).volume
    if operation == "geometry.cylinder_volume":
        return Cylinder(data["radius"], data["height"]).volume
    if operation == "linear.solve":
        return list(solve_linear(data["matrix"], data["rhs"]).solution)
    if operation == "simulation.static_linear":
        result, evidence = solve_static_linear_system(data["stiffness"], data["load"])
        return {
            "status": result.status.value,
            "values": list(result.values),
            "residual_inf": result.residual_inf,
            "evidence_kind": evidence.kind.value,
        }
    if operation == "geometry.transform_point":
        transform = RigidTransform(
            "part", "world", tuple(tuple(row) for row in data["rotation"]),
            Vec3(*data["translation"]),
        )
        point = transform.apply_point(Vec3(*data["point"]))
        return [point.x, point.y, point.z]
    if operation == "kinematics.planar_2r":
        result = solve_planar_two_link_inverse_kinematics(
            data["link_1"], data["link_2"], data["target_x"], data["target_y"],
            elbow_branch=data["branch"],
        )
        return {
            "achieved_x": result.achieved_x,
            "achieved_y": result.achieved_y,
            "position_error": result.position_error,
        }
    if operation == "mechanism.planar_four_bar":
        model = PlanarFourBarModelSnapshot(
            model_id="reference/four-bar", model_revision="reference/1",
            ground_link_id="link/ground", input_link_id="link/input",
            coupler_link_id="link/coupler", output_link_id="link/output",
            input_ground_joint_id="joint/A", input_coupler_joint_id="joint/B",
            coupler_output_joint_id="joint/C", output_ground_joint_id="joint/D",
            ground_length=quantity(data["ground_length"]),
            input_crank_length=quantity(data["input_length"]),
            coupler_length=quantity(data["coupler_length"]),
            output_rocker_length=quantity(data["output_length"]),
            input_angle_rad=data["input_angle_rad"], branch=data["branch"],
            tolerance=Quantity.of(1e-9, "m"),
        )
        result = solve_planar_four_bar_model(model)
        point = dict(result.joint_positions_m)["joint/D"]
        return {
            "joint_D_x_m": point[0],
            "joint_D_y_m": point[1],
            "closure_error_m": result.geometry.closure_error,
        }
    if operation == "materials.record":
        material = Material(
            data["material_id"], data["name"], quantity(data["density"]),
            quantity(data["young_modulus"]), data["poisson_ratio"],
            quantity(data["yield_strength"]),
        )
        return {
            "density_kg_m3": material.density.in_unit("kg/m3"),
            "young_modulus_gpa": material.young_modulus.in_unit("GPa"),
            "yield_strength_mpa": material.yield_strength.in_unit("MPa"),
            "poisson_ratio": material.poisson_ratio,
        }
    if operation == "assembly.revolute_joint":
        assembly = Assembly(
            "reference/assembly",
            (PartOccurrence("base", "part/base", "rev/1"),
             PartOccurrence("arm", "part/arm", "rev/1")),
            (Joint("joint/revolute", "base", "arm", JointType.REVOLUTE,
                   Vec3(0.0, 0.0, 1.0), -1.0, 1.0),),
        )
        return {
            "validation_error_count": len(assembly.validate()),
            "nominal_joint_dof": assembly.nominal_joint_dof,
        }
    if operation == "constraints.maximum":
        constraint = Constraint(
            "constraint/length", "length", ConstraintKind.MAXIMUM,
            quantity(data["maximum"]),
        )
        result = evaluate_constraints({"length": quantity(data["actual"])}, (constraint,))[0]
        return {"status": result.status}
    if operation == "safety.physical_action":
        decision = SafetyGate().evaluate(data["action"], RiskTier.PHYSICAL_EXECUTION, approved=True)
        return {"allowed": decision.allowed, "status": decision.status}
    raise AssertionError(f"Unregistered reference operation: {operation}")


def assert_reference_value(actual, expected, tolerance, path="root"):
    if isinstance(expected, dict):
        assert isinstance(actual, dict), path
        for key, value in expected.items():
            assert key in actual, f"{path}.{key} missing"
            assert_reference_value(actual[key], value, tolerance, f"{path}.{key}")
    elif isinstance(expected, list):
        assert len(actual) == len(expected), path
        for index, value in enumerate(expected):
            assert_reference_value(actual[index], value, tolerance, f"{path}[{index}]")
    elif isinstance(expected, (int, float)) and not isinstance(expected, bool):
        assert actual == pytest.approx(expected, abs=tolerance, rel=tolerance), path
    else:
        assert actual == expected, path


def test_reference_registry_is_versioned_unique_and_traceable():
    assert REGISTRY["schema_version"] == "1.0"
    cases = REGISTRY["cases"]
    ids = [item["id"] for item in cases]
    assert len(ids) >= 15
    assert len(ids) == len(set(ids))
    for item in cases:
        assert item["id"].strip()
        assert item["reference"].strip()
        assert item["operation"].strip()
        assert math.isfinite(item["tolerance"])
        assert item["tolerance"] >= 0.0


@pytest.mark.parametrize("case", REGISTRY["cases"], ids=lambda item: item["id"])
def test_engineering_reference_case(case):
    actual = evaluate(case)
    assert_reference_value(actual, case["expected"], case["tolerance"], case["id"])


def test_unknown_evidence_cannot_be_promoted_to_pass_in_reference_pack():
    with pytest.raises(ValueError, match="UNKNOWN evidence cannot have PASS"):
        EvidenceRecord(EvidenceKind.UNKNOWN, EvidenceStatus.PASS, "unverified reference")
