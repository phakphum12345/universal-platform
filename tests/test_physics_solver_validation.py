import pytest

from universal_platform.engineering.errors import SolverError
from universal_platform.engineering.linear_solver import solve_linear
from universal_platform.engineering.simulation import solve_static_linear_system
from universal_platform.engineering.provenance import EvidenceKind, EvidenceStatus
from universal_platform.engineering import (
    PhysicsDomain,
    PhysicsInput,
    PhysicsMethod,
    PhysicsProblem,
    PhysicsSolverRegistry,
    Quantity,
    register_builtin_physics_solvers,
)


def test_linear_solver_matches_independent_exact_two_by_two_reference():
    # Exact solution of [[4, 1], [1, 3]] x = [1, 2] is [1/11, 7/11].
    result = solve_linear([[4.0, 1.0], [1.0, 3.0]], [1.0, 2.0])

    assert result.solution == pytest.approx((1 / 11, 7 / 11), abs=1e-12)
    assert result.residual_inf <= 1e-12
    assert result.method == "gaussian-elimination-partial-pivoting"


def test_linear_solver_uses_row_pivoting_for_zero_diagonal():
    result = solve_linear([[0.0, 2.0], [1.0, 1.0]], [4.0, 3.0])

    assert result.solution == pytest.approx((1.0, 2.0))
    assert result.residual_inf == pytest.approx(0.0)


def test_linear_solver_fails_closed_for_singular_system():
    with pytest.raises(SolverError, match="Singular"):
        solve_linear([[1.0, 2.0], [2.0, 4.0]], [3.0, 6.0])


def test_static_linear_system_reports_algebraic_evidence_and_limits():
    result, evidence = solve_static_linear_system(
        [[4.0, 1.0], [1.0, 3.0]], [1.0, 2.0]
    )

    assert result.status is EvidenceStatus.PASS
    assert result.values == pytest.approx((1 / 11, 7 / 11), abs=1e-12)
    assert evidence.kind is EvidenceKind.SIMULATION
    assert evidence.status is EvidenceStatus.PASS
    assert any(
        "not finite-element analysis" in limitation
        for limitation in evidence.limitations
    )
    assert any(
        "No geometry, material constitutive law, boundary-condition or mesh validation"
        in limitation
        for limitation in evidence.limitations
    )
    assert evidence.metadata["residual_inf"] <= 1e-12


def test_physics_problem_boundary_conditions_and_assumptions_survive_as_evidence():
    registry = register_builtin_physics_solvers(PhysicsSolverRegistry())
    problem = PhysicsProblem(
        "stress-boundary-evidence",
        PhysicsDomain.STRUCTURAL,
        PhysicsMethod.ANALYTICAL,
        (
            PhysicsInput("force", Quantity.of(1000, "N")),
            PhysicsInput("area", Quantity.of(100, "mm") * Quantity.of(100, "mm")),
        ),
        validity_range="uniform axial load and constant cross-section",
        assumptions=("uniform axial stress",),
        boundary_conditions=("uniaxial tensile load", "lateral surfaces traction-free"),
    )

    result = registry.solve(
        problem,
        solver_id="builtin.axial-stress",
        allowed_licenses=("Apache-2.0",),
        dependency_check=lambda dependencies: not dependencies,
    )

    assert result.evidence.metadata["assumptions"] == ("uniform axial stress",)
    assert result.evidence.metadata["boundary_conditions"] == (
        "uniaxial tensile load",
        "lateral surfaces traction-free",
    )
