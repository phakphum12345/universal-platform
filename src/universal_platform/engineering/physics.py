"""Central, evidence-producing registry for replaceable physics solver adapters.

The registry dispatches trusted in-process adapters. It does not sandbox third-party
solvers or imply that a passing calculation is a validated engineering design.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from math import isfinite
import re
from threading import RLock
from typing import Callable, Iterable, Protocol

from .electrical import electrical_power, ohms_law
from .errors import EngineeringError
from .materials import PRESSURE
from .mechanics import axial_stress
from .provenance import EvidenceKind, EvidenceRecord, EvidenceStatus, SourceRef
from .quantity import Quantity
from .thermal import linear_thermal_expansion


class PhysicsDomain(str, Enum):
    MECHANICS = "MECHANICS"
    STRUCTURAL = "STRUCTURAL"
    KINEMATICS = "KINEMATICS"
    ELECTRICAL = "ELECTRICAL"
    THERMAL = "THERMAL"
    FLUID = "FLUID"
    ELECTROMAGNETIC = "ELECTROMAGNETIC"
    MATERIALS = "MATERIALS"


class PhysicsMethod(str, Enum):
    ANALYTICAL = "ANALYTICAL"
    NUMERICAL = "NUMERICAL"
    SIMULATION = "SIMULATION"
    OPTIMIZATION = "OPTIMIZATION"


_SEMVER = re.compile(r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)(?:-[0-9A-Za-z.-]+)?$")


@dataclass(frozen=True, slots=True)
class PhysicsInput:
    name: str
    value: Quantity | float

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("physics input name must be non-empty")
        if isinstance(self.value, bool) or not isinstance(self.value, (Quantity, int, float)):
            raise ValueError("physics input must be a Quantity or finite scalar")
        if not isinstance(self.value, Quantity) and not isfinite(float(self.value)):
            raise ValueError("physics scalar inputs must be finite")


@dataclass(frozen=True, slots=True)
class PhysicsProblem:
    problem_id: str
    domain: PhysicsDomain
    method: PhysicsMethod
    inputs: tuple[PhysicsInput, ...]
    validity_range: str
    assumptions: tuple[str, ...] = ()
    boundary_conditions: tuple[str, ...] = ()
    source_refs: tuple[SourceRef, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.problem_id, str) or not self.problem_id.strip():
            raise ValueError("problem_id must be non-empty")
        if not isinstance(self.domain, PhysicsDomain) or not isinstance(self.method, PhysicsMethod):
            raise ValueError("domain and method must use declared Physics enums")
        if not isinstance(self.inputs, tuple) or not self.inputs:
            raise ValueError("inputs must be a non-empty immutable tuple")
        if any(not isinstance(item, PhysicsInput) for item in self.inputs):
            raise ValueError("inputs must contain PhysicsInput records")
        names = [item.name for item in self.inputs]
        if len(names) != len(set(names)):
            raise ValueError("physics input names must be unique")
        if not isinstance(self.validity_range, str) or not self.validity_range.strip():
            raise ValueError("validity_range must be explicit")
        for label, values in (("assumptions", self.assumptions), ("boundary_conditions", self.boundary_conditions)):
            if not isinstance(values, tuple) or any(not isinstance(item, str) or not item.strip() for item in values):
                raise ValueError(f"{label} must be an immutable tuple of non-empty strings")
        if not isinstance(self.source_refs, tuple) or any(not isinstance(item, SourceRef) for item in self.source_refs):
            raise ValueError("source_refs must be an immutable tuple of SourceRef records")

    def input(self, name: str, expected_type: type | tuple[type, ...]) -> object:
        for item in self.inputs:
            if item.name == name:
                if not isinstance(item.value, expected_type):
                    raise EngineeringError(f"input {name} has an incompatible value type")
                return item.value
        raise EngineeringError(f"missing required physics input: {name}")


@dataclass(frozen=True, slots=True)
class PhysicsSolverDescriptor:
    solver_id: str
    version: str
    domain: PhysicsDomain
    method: PhysicsMethod
    license_id: str
    capabilities: tuple[str, ...] = ()
    dependencies: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.solver_id, str) or not self.solver_id.strip():
            raise ValueError("solver_id must be non-empty")
        if not isinstance(self.version, str) or not _SEMVER.fullmatch(self.version):
            raise ValueError("solver version must be semantic MAJOR.MINOR.PATCH")
        if not isinstance(self.domain, PhysicsDomain) or not isinstance(self.method, PhysicsMethod):
            raise ValueError("solver domain and method must use declared enums")
        if not isinstance(self.license_id, str) or not self.license_id.strip():
            raise ValueError("solver license_id must be explicit")
        for label, values in (("capabilities", self.capabilities), ("dependencies", self.dependencies)):
            if not isinstance(values, tuple) or len(values) != len(set(values)):
                raise ValueError(f"{label} must be an immutable tuple without duplicates")
            if any(not isinstance(item, str) or not item.strip() for item in values):
                raise ValueError(f"{label} entries must be non-empty strings")


@dataclass(frozen=True, slots=True)
class PhysicsOutput:
    name: str
    quantity: Quantity

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("physics output name must be non-empty")
        if not isinstance(self.quantity, Quantity):
            raise ValueError("physics output must be a Quantity")


@dataclass(frozen=True, slots=True)
class PhysicsSolverResponse:
    outputs: tuple[PhysicsOutput, ...]
    status: EvidenceStatus
    statement: str
    limitations: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.outputs, tuple) or not self.outputs:
            raise ValueError("solver outputs must be a non-empty immutable tuple")
        if any(not isinstance(item, PhysicsOutput) for item in self.outputs):
            raise ValueError("solver outputs must contain PhysicsOutput records")
        names = [item.name for item in self.outputs]
        if len(names) != len(set(names)):
            raise ValueError("physics output names must be unique")
        if not isinstance(self.status, EvidenceStatus):
            raise ValueError("solver response status must be an EvidenceStatus")
        if not isinstance(self.statement, str) or not self.statement.strip():
            raise ValueError("solver response statement must be non-empty")
        if not isinstance(self.limitations, tuple) or any(not isinstance(item, str) or not item.strip() for item in self.limitations):
            raise ValueError("limitations must be an immutable tuple of non-empty strings")


@dataclass(frozen=True, slots=True)
class PhysicsResult:
    problem_id: str
    solver_id: str
    solver_version: str
    domain: PhysicsDomain
    method: PhysicsMethod
    outputs: tuple[PhysicsOutput, ...]
    evidence: EvidenceRecord


class PhysicsSolver(Protocol):
    descriptor: PhysicsSolverDescriptor

    def solve(self, problem: PhysicsProblem) -> PhysicsSolverResponse: ...


class PhysicsSolverRegistry:
    """Thread-safe registry and policy gate for local solver adapters."""

    def __init__(self) -> None:
        self._solvers: dict[str, PhysicsSolver] = {}
        self._lock = RLock()

    def register(self, solver: PhysicsSolver) -> None:
        descriptor = solver.descriptor
        if not isinstance(descriptor, PhysicsSolverDescriptor) or not callable(getattr(solver, "solve", None)):
            raise TypeError("solver must provide a validated descriptor and solve(problem)")
        with self._lock:
            if descriptor.solver_id in self._solvers:
                raise ValueError(f"solver already registered: {descriptor.solver_id}")
            self._solvers[descriptor.solver_id] = solver

    def list_solvers(
        self,
        *,
        domain: PhysicsDomain | None = None,
        method: PhysicsMethod | None = None,
    ) -> tuple[PhysicsSolverDescriptor, ...]:
        with self._lock:
            descriptors = tuple(solver.descriptor for solver in self._solvers.values())
        return tuple(sorted(
            (item for item in descriptors if (domain is None or item.domain is domain) and (method is None or item.method is method)),
            key=lambda item: item.solver_id,
        ))

    def solve(
        self,
        problem: PhysicsProblem,
        *,
        solver_id: str,
        allowed_licenses: Iterable[str],
        dependency_check: Callable[[tuple[str, ...]], bool],
    ) -> PhysicsResult:
        with self._lock:
            try:
                solver = self._solvers[solver_id]
            except KeyError as exc:
                raise KeyError(f"unknown physics solver: {solver_id}") from exc
        descriptor = solver.descriptor
        if descriptor.domain is not problem.domain or descriptor.method is not problem.method:
            raise ValueError("solver domain/method does not match the physics problem")
        if descriptor.license_id not in frozenset(allowed_licenses):
            raise PermissionError("solver license is not allow-listed")
        if not callable(dependency_check) or not dependency_check(descriptor.dependencies):
            raise PermissionError("solver dependencies are unavailable or not approved")
        response = solver.solve(problem)
        if not isinstance(response, PhysicsSolverResponse):
            raise TypeError("solver returned an invalid response")
        evidence_kind = EvidenceKind.SIMULATION if problem.method is PhysicsMethod.SIMULATION else EvidenceKind.INFERENCE
        evidence = EvidenceRecord(
            kind=evidence_kind,
            status=response.status,
            statement=response.statement,
            source_refs=problem.source_refs,
            method=f"{descriptor.solver_id}@{descriptor.version}",
            limitations=response.limitations,
            metadata={
                "problem_id": problem.problem_id,
                "domain": problem.domain.value,
                "method": problem.method.value,
                "solver_id": descriptor.solver_id,
                "solver_version": descriptor.version,
                "validity_range": problem.validity_range,
                "assumptions": list(problem.assumptions),
                "boundary_conditions": list(problem.boundary_conditions),
            },
        )
        return PhysicsResult(
            problem.problem_id, descriptor.solver_id, descriptor.version,
            problem.domain, problem.method, response.outputs, evidence,
        )


class AxialStressSolver:
    descriptor = PhysicsSolverDescriptor(
        "builtin.axial-stress", "1.0.0", PhysicsDomain.STRUCTURAL,
        PhysicsMethod.ANALYTICAL, "Apache-2.0", ("unit-aware", "first-principles"),
    )

    def solve(self, problem: PhysicsProblem) -> PhysicsSolverResponse:
        force = problem.input("force", Quantity)
        area = problem.input("area", Quantity)
        result = axial_stress(force, area)
        if result.dimension != PRESSURE:
            raise EngineeringError("axial stress solver produced an invalid dimension")
        return PhysicsSolverResponse(
            (PhysicsOutput("stress", result),), EvidenceStatus.PASS,
            "Computed axial stress from the supplied force and cross-sectional area.",
            ("Elementary axial stress only; no stress concentration, buckling, fatigue or code check",
             "Inputs and boundary conditions are caller-supplied; result is not a safety certification"),
        )


class OhmsLawSolver:
    descriptor = PhysicsSolverDescriptor(
        "builtin.ohms-law", "1.0.0", PhysicsDomain.ELECTRICAL,
        PhysicsMethod.ANALYTICAL, "Apache-2.0", ("unit-aware", "dc-circuit"),
    )

    def solve(self, problem: PhysicsProblem) -> PhysicsSolverResponse:
        voltage = problem.input("voltage", Quantity)
        resistance = problem.input("resistance", Quantity)
        current = ohms_law(voltage, resistance)
        power = electrical_power(voltage, current)
        return PhysicsSolverResponse(
            (PhysicsOutput("current", current), PhysicsOutput("power", power)),
            EvidenceStatus.PASS,
            "Computed DC current using Ohm's law and electrical power from voltage and current.",
            ("Ideal lumped DC relation only; no transient, AC, thermal, parasitic or circuit-network analysis",
             "Result is not an electrical safety or compliance certification"),
        )


class LinearThermalExpansionSolver:
    descriptor = PhysicsSolverDescriptor(
        "builtin.linear-thermal-expansion", "1.0.0", PhysicsDomain.THERMAL,
        PhysicsMethod.ANALYTICAL, "Apache-2.0", ("unit-aware", "linear-expansion"),
    )

    def solve(self, problem: PhysicsProblem) -> PhysicsSolverResponse:
        length = problem.input("length", Quantity)
        coefficient = problem.input("coefficient_per_kelvin", (int, float))
        delta_temperature = problem.input("temperature_change_kelvin", (int, float))
        result = linear_thermal_expansion(length, float(coefficient), float(delta_temperature))
        return PhysicsSolverResponse(
            (PhysicsOutput("delta_length", result),), EvidenceStatus.PASS,
            "Computed linear thermal expansion from the supplied length, coefficient and temperature change.",
            ("Constant linear expansion coefficient and uniform temperature change are assumed",
             "No stress, restraint, transient heat transfer or nonlinear material response is modeled"),
        )


def register_builtin_physics_solvers(registry: PhysicsSolverRegistry) -> PhysicsSolverRegistry:
    """Register the bounded built-in analytical solvers without external dependencies."""
    for solver in (AxialStressSolver(), OhmsLawSolver(), LinearThermalExpansionSolver()):
        registry.register(solver)
    return registry
