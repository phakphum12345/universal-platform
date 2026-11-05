import math
import pytest

from universal_platform.engineering.quantity import Quantity, LENGTH, TIME
from universal_platform.engineering.errors import DimensionMismatchError, SolverError, InvalidModelError
from universal_platform.engineering.linear_solver import solve_linear
from universal_platform.engineering.geometry import Box, Cylinder
from universal_platform.engineering.assembly import Assembly, PartOccurrence, Joint, JointType
from universal_platform.engineering.geometry import Vec3
from universal_platform.engineering.constraints import Constraint, ConstraintKind, evaluate_constraints
from universal_platform.engineering.provenance import EvidenceKind, EvidenceStatus, EvidenceRecord
from universal_platform.engineering.safety import SafetyGate, RiskTier
from universal_platform.engineering.simulation import solve_static_linear_system


def test_quantity_conversion_and_dimensions():
    assert Quantity.of(25, "mm").in_unit("m") == pytest.approx(0.025)
    assert (Quantity.of(2, "m") + Quantity.of(30, "cm")).in_unit("m") == pytest.approx(2.3)
    with pytest.raises(DimensionMismatchError):
        _ = Quantity.of(1, "m") + Quantity.of(1, "s")


def test_quantity_multiplication_combines_dimensions():
    area = Quantity.of(2, "m") * Quantity.of(3, "m")
    assert area.dimension == (2, 0, 0, 0, 0)
    assert area.si_value == 6


def test_linear_solver_with_pivoting():
    result = solve_linear([[0, 2], [1, 1]], [4, 3])
    assert result.solution == pytest.approx((1, 2))
    assert result.residual_inf < 1e-10


def test_linear_solver_rejects_singular():
    with pytest.raises(SolverError):
        solve_linear([[1, 2], [2, 4]], [1, 2])


def test_parametric_primitives_validate_and_measure():
    assert Box(2, 3, 4).volume == 24
    assert Cylinder(1, 2).volume == pytest.approx(2 * math.pi)
    with pytest.raises(InvalidModelError):
        Box(0, 1, 1)


def test_assembly_joint_contract():
    a = Assembly("a", (PartOccurrence("base", "p1", "r1"), PartOccurrence("arm", "p2", "r1")),
                 (Joint("j1", "base", "arm", JointType.REVOLUTE, Vec3(0, 0, 1), -1, 1),))
    assert a.validate() == ()
    assert a.nominal_joint_dof == 1


def test_constraint_results_are_explicit():
    c = Constraint("c1", "length", ConstraintKind.MAXIMUM, Quantity.of(100, "mm"))
    result = evaluate_constraints({"length": Quantity.of(80, "mm")}, [c])
    assert result[0].status == "PASS"
    assert evaluate_constraints({}, [c])[0].status == "UNKNOWN"


def test_unknown_evidence_cannot_pass():
    with pytest.raises(ValueError):
        EvidenceRecord(EvidenceKind.UNKNOWN, EvidenceStatus.PASS, "unknown")


def test_safety_gate_denies_physical_actions():
    gate = SafetyGate()
    assert not gate.evaluate("motor_control", RiskTier.PHYSICAL_EXECUTION, approved=True).allowed
    assert gate.evaluate("offline_calculation", RiskTier.LOW_CONSEQUENCE).allowed


def test_high_consequence_requires_review_and_approval():
    gate = SafetyGate()
    assert not gate.evaluate("design_review", RiskTier.HIGH_CONSEQUENCE).allowed
    assert gate.evaluate("design_review", RiskTier.HIGH_CONSEQUENCE,
                         approved=True, qualified_review=True).allowed


def test_linear_simulation_emits_limitations_and_evidence():
    result, evidence = solve_static_linear_system([[2, 0], [0, 4]], [4, 8])
    assert result.values == pytest.approx((2, 2))
    assert result.status is EvidenceStatus.PASS
    assert evidence.kind is EvidenceKind.SIMULATION
    assert "not finite-element analysis" in result.limitations[0]
