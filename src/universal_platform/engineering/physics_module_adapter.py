"""Policy-gated bridge from ModuleRuntime requests to built-in physics solvers.

Only the three explicitly supported, dependency-free analytical solvers are
exposed. Inputs use canonical, explicit units; evidence and limitations are
returned with each result. This bridge does not sandbox solver code.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from math import isfinite
from typing import Any

from .contracts import ModuleRequest, ModuleResponse
from .errors import InvalidModelError
from .module_registry import ModuleManifest, ModuleOperation, ModuleRegistry
from .module_runtime import ModuleRuntime
from .physics import (
    PhysicsDomain,
    PhysicsInput,
    PhysicsMethod,
    PhysicsProblem,
    PhysicsSolverRegistry,
    register_builtin_physics_solvers,
)
from .quantity import Quantity

MODULE_ID = "org.universal.physics"
SOLVE_OPERATION = "physics.solve"
SOLVE_PERMISSION = "engineering.physics.solve"

# The bridge deliberately accepts only canonical units for these fixed inputs.
_QUANTITY_INPUTS = {
    "builtin.axial-stress": {"force": "N", "area": "m2"},
    "builtin.ohms-law": {"voltage": "V", "resistance": "ohm"},
    "builtin.linear-thermal-expansion": {"length": "m"},
}
_SCALAR_INPUTS = {
    "builtin.axial-stress": set(),
    "builtin.ohms-law": set(),
    "builtin.linear-thermal-expansion": {
        "coefficient_per_kelvin", "temperature_change_kelvin",
    },
}


def _finite_number(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise InvalidModelError(f"{label} must be a finite number")
    number = float(value)
    if not isfinite(number):
        raise InvalidModelError(f"{label} must be a finite number")
    return number


def _text_tuple(value: Any, label: str) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, (list, tuple)):
        raise InvalidModelError(f"{label} must be a list of non-empty strings")
    result = tuple(value)
    if any(not isinstance(item, str) or not item.strip() for item in result):
        raise InvalidModelError(f"{label} must contain non-empty strings")
    if len(result) != len(set(result)):
        raise InvalidModelError(f"{label} must not contain duplicates")
    return result


def _build_problem(inputs: Mapping[str, Any], solvers: PhysicsSolverRegistry) -> tuple[str, PhysicsProblem]:
    solver_id = inputs.get("solver_id")
    if not isinstance(solver_id, str) or solver_id not in _QUANTITY_INPUTS:
        raise InvalidModelError("solver_id is not supported by the built-in physics bridge")

    problem_id = inputs.get("problem_id")
    validity_range = inputs.get("validity_range")
    if not isinstance(problem_id, str) or not problem_id.strip():
        raise InvalidModelError("problem_id must be a non-empty string")
    if not isinstance(validity_range, str) or not validity_range.strip():
        raise InvalidModelError("validity_range must be explicit")

    values = inputs.get("values")
    if not isinstance(values, Mapping):
        raise InvalidModelError("values must be an object")

    expected = set(_QUANTITY_INPUTS[solver_id]) | _SCALAR_INPUTS[solver_id]
    if set(values) != expected:
        raise InvalidModelError("physics inputs do not match the selected solver contract")

    descriptors = {item.solver_id: item for item in solvers.list_solvers()}
    descriptor = descriptors.get(solver_id)
    if descriptor is None:
        raise InvalidModelError("selected physics solver is not registered")

    problem_inputs: list[PhysicsInput] = []
    for name, unit in _QUANTITY_INPUTS[solver_id].items():
        raw = values[name]
        if not isinstance(raw, Mapping) or set(raw) != {"value", "unit"}:
            raise InvalidModelError(f"{name} must contain exactly value and unit")
        if raw["unit"] != unit:
            raise InvalidModelError(f"{name} must use canonical unit {unit}")
        problem_inputs.append(PhysicsInput(name, Quantity.of(_finite_number(raw["value"], name), unit)))

    for name in sorted(_SCALAR_INPUTS[solver_id]):
        problem_inputs.append(PhysicsInput(name, _finite_number(values[name], name)))

    problem = PhysicsProblem(
        problem_id=problem_id,
        domain=descriptor.domain,
        method=descriptor.method,
        inputs=tuple(problem_inputs),
        validity_range=validity_range,
        assumptions=_text_tuple(inputs.get("assumptions"), "assumptions"),
        boundary_conditions=_text_tuple(inputs.get("boundary_conditions"), "boundary_conditions"),
    )
    return solver_id, problem


@dataclass(frozen=True, slots=True)
class PhysicsModuleBridge:
    """Host-configured bridge; the host controls grants and license policy."""

    runtime: ModuleRuntime
    solvers: PhysicsSolverRegistry

    def invoke(self, request: ModuleRequest) -> ModuleResponse:
        return self.runtime.invoke(request)

    def grant(self) -> None:
        self.runtime.grant(MODULE_ID, frozenset({SOLVE_PERMISSION}))

    def revoke(self) -> bool:
        return self.runtime.revoke(MODULE_ID)


def create_builtin_physics_module_bridge(
    *,
    allowed_licenses: tuple[str, ...] = ("Apache-2.0",),
) -> PhysicsModuleBridge:
    """Create a policy-gated bridge for the repository's bounded built-in solvers."""
    if not isinstance(allowed_licenses, tuple) or not allowed_licenses:
        raise InvalidModelError("allowed_licenses must be a non-empty immutable tuple")
    if any(not isinstance(item, str) or not item.strip() for item in allowed_licenses):
        raise InvalidModelError("allowed_licenses must contain non-empty strings")

    solvers = register_builtin_physics_solvers(PhysicsSolverRegistry())
    modules = ModuleRegistry()
    modules.register(ModuleManifest(
        module_id=MODULE_ID,
        version="1.0.0",
        domain="physics",
        operations=(ModuleOperation(
            SOLVE_OPERATION,
            input_schema_version="1.0",
            output_schema_version="1.0",
            required_permissions=(SOLVE_PERMISSION,),
            execution_kind="CALCULATION",
        ),),
        permissions=(SOLVE_PERMISSION,),
        license_id="Apache-2.0",
        maturity="VALIDATED",
    ))
    runtime = ModuleRuntime(modules)

    def solve_handler(raw_inputs: Mapping[str, Any]) -> Mapping[str, Any]:
        solver_id, problem = _build_problem(raw_inputs, solvers)
        result = solvers.solve(
            problem,
            solver_id=solver_id,
            allowed_licenses=allowed_licenses,
            # This bridge supports only built-ins with no external dependencies.
            dependency_check=lambda dependencies: not dependencies,
        )
        return {
            "problem_id": result.problem_id,
            "solver_id": result.solver_id,
            "solver_version": result.solver_version,
            "domain": result.domain.value,
            "method": result.method.value,
            "outputs": {
                item.name: item.quantity.to_dict() for item in result.outputs
            },
            "evidence": result.evidence.to_dict(),
        }

    runtime.register_handler(MODULE_ID, SOLVE_OPERATION, solve_handler)
    return PhysicsModuleBridge(runtime=runtime, solvers=solvers)
