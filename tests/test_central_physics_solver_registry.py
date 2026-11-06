from dataclasses import dataclass

import pytest

from universal_platform.engineering import (
    AxialStressSolver,
    LinearThermalExpansionSolver,
    OhmsLawSolver,
    PhysicsDomain,
    PhysicsInput,
    PhysicsMethod,
    PhysicsProblem,
    PhysicsSolverDescriptor,
    PhysicsSolverRegistry,
    PhysicsSolverResponse,
    register_builtin_physics_solvers,
)
from universal_platform.engineering.provenance import EvidenceKind, EvidenceStatus, SourceRef
from universal_platform.engineering.quantity import Quantity


def make_registry():
    return register_builtin_physics_solvers(PhysicsSolverRegistry())


def solve(registry, problem, solver_id):
    return registry.solve(
        problem,
        solver_id=solver_id,
        allowed_licenses=("Apache-2.0",),
        dependency_check=lambda dependencies: not dependencies,
    )


def test_registry_lists_builtin_solvers_by_domain_and_method():
    registry = make_registry()
    items = registry.list_solvers(domain=PhysicsDomain.ELECTRICAL, method=PhysicsMethod.ANALYTICAL)
    assert [item.solver_id for item in items] == ["builtin.ohms-law"]
    assert len(registry.list_solvers()) == 3


def test_axial_stress_solver_returns_unit_aware_result_and_provenance():
    registry = make_registry()
    problem = PhysicsProblem(
        "stress-1", PhysicsDomain.STRUCTURAL, PhysicsMethod.ANALYTICAL,
        (PhysicsInput("force", Quantity.of(1000, "N")),
         PhysicsInput("area", Quantity.of(100, "mm") * Quantity.of(100, "mm"))),
        validity_range="small-strain, uniform axial load",
        assumptions=("uniform axial stress",),
        source_refs=(SourceRef("user-input", revision="v1"),),
    )
    result = solve(registry, problem, "builtin.axial-stress")
    assert result.outputs[0].quantity.in_unit("MPa") == pytest.approx(0.1)
    assert result.evidence.kind is EvidenceKind.INFERENCE
    assert result.evidence.status is EvidenceStatus.PASS
    assert result.evidence.source_refs == problem.source_refs
    assert result.evidence.metadata["solver_id"] == "builtin.axial-stress"


def test_ohms_law_solver_returns_current_and_power():
    registry = make_registry()
    problem = PhysicsProblem(
        "dc-1", PhysicsDomain.ELECTRICAL, PhysicsMethod.ANALYTICAL,
        (PhysicsInput("voltage", Quantity.of(12, "V")),
         PhysicsInput("resistance", Quantity.of(6, "ohm"))),
        validity_range="ideal lumped DC circuit",
    )
    result = solve(registry, problem, "builtin.ohms-law")
    outputs = {item.name: item.quantity for item in result.outputs}
    assert outputs["current"].in_unit("A") == pytest.approx(2)
    assert outputs["power"].in_unit("W") == pytest.approx(24)


def test_linear_thermal_expansion_solver_returns_delta_length():
    registry = make_registry()
    problem = PhysicsProblem(
        "thermal-1", PhysicsDomain.THERMAL, PhysicsMethod.ANALYTICAL,
        (PhysicsInput("length", Quantity.of(2, "m")),
         PhysicsInput("coefficient_per_kelvin", 12e-6),
         PhysicsInput("temperature_change_kelvin", 50.0)),
        validity_range="constant coefficient and uniform temperature change",
    )
    result = solve(registry, problem, "builtin.linear-thermal-expansion")
    assert result.outputs[0].quantity.in_unit("mm") == pytest.approx(1.2)


def test_registry_fails_closed_on_license_dependency_and_solver_mismatch():
    registry = make_registry()
    problem = PhysicsProblem(
        "dc-2", PhysicsDomain.ELECTRICAL, PhysicsMethod.ANALYTICAL,
        (PhysicsInput("voltage", Quantity.of(12, "V")),
         PhysicsInput("resistance", Quantity.of(6, "ohm"))),
        validity_range="ideal DC",
    )
    with pytest.raises(PermissionError, match="license"):
        registry.solve(problem, solver_id="builtin.ohms-law", allowed_licenses=(), dependency_check=lambda deps: True)
    with pytest.raises(PermissionError, match="dependencies"):
        registry.solve(problem, solver_id="builtin.ohms-law", allowed_licenses=("Apache-2.0",), dependency_check=lambda deps: False)
    with pytest.raises(ValueError, match="domain/method"):
        registry.solve(problem, solver_id="builtin.axial-stress", allowed_licenses=("Apache-2.0",), dependency_check=lambda deps: True)


def test_registry_rejects_missing_inputs_and_dimension_errors():
    registry = make_registry()
    missing = PhysicsProblem(
        "bad-1", PhysicsDomain.ELECTRICAL, PhysicsMethod.ANALYTICAL,
        (PhysicsInput("voltage", Quantity.of(12, "V")),),
        validity_range="ideal DC",
    )
    with pytest.raises(Exception, match="missing required"):
        solve(registry, missing, "builtin.ohms-law")
    wrong_dimension = PhysicsProblem(
        "bad-2", PhysicsDomain.ELECTRICAL, PhysicsMethod.ANALYTICAL,
        (PhysicsInput("voltage", Quantity.of(12, "V")),
         PhysicsInput("resistance", Quantity.of(2, "m"))),
        validity_range="ideal DC",
    )
    with pytest.raises(Exception):
        solve(registry, wrong_dimension, "builtin.ohms-law")


def test_problem_and_solver_contracts_reject_ambiguous_metadata():
    with pytest.raises(ValueError, match="validity_range"):
        PhysicsProblem("missing-validity", PhysicsDomain.MECHANICS, PhysicsMethod.ANALYTICAL,
                       (PhysicsInput("force", Quantity.of(1, "N")),), "")
    with pytest.raises(ValueError, match="unique"):
        PhysicsProblem("duplicate", PhysicsDomain.MECHANICS, PhysicsMethod.ANALYTICAL,
                       (PhysicsInput("force", Quantity.of(1, "N")),
                        PhysicsInput("force", Quantity.of(2, "N"))), "static")
    with pytest.raises(ValueError, match="semantic"):
        PhysicsSolverDescriptor("bad", "latest", PhysicsDomain.MECHANICS,
                                PhysicsMethod.ANALYTICAL, "Apache-2.0")


def test_duplicate_solver_registration_is_rejected():
    registry = PhysicsSolverRegistry()
    registry.register(AxialStressSolver())
    with pytest.raises(ValueError, match="already registered"):
        registry.register(AxialStressSolver())
