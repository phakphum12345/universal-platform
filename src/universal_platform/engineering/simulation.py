"""Transparent analytical checks; not a general-purpose FEA/CFD solver."""
from __future__ import annotations
from dataclasses import dataclass
from math import isfinite
from .errors import EngineeringError
from .provenance import EvidenceKind, EvidenceRecord, EvidenceStatus
from .linear_solver import solve_linear

@dataclass(frozen=True, slots=True)
class SimulationResult:
    status: EvidenceStatus
    values: tuple[float, ...]
    residual_inf: float
    method: str
    limitations: tuple[str, ...]

def solve_static_linear_system(stiffness: list[list[float]], load: list[float],
                               *, tolerance: float = 1e-12) -> tuple[SimulationResult, EvidenceRecord]:
    """Solve Kx=f for a user-supplied linear system with no material/FEA inference."""
    if any(not isfinite(float(v)) for v in load):
        raise EngineeringError("Load vector must be finite")
    solved = solve_linear(stiffness, load, tolerance=tolerance)
    status = EvidenceStatus.PASS if solved.residual_inf <= max(tolerance * 100, 1e-10) else EvidenceStatus.FAIL
    limits = ("Analytical linear algebra only; not finite-element analysis",
              "No geometry, material constitutive law, boundary-condition or mesh validation",
              "Result is not a safety certification or physical measurement")
    result = SimulationResult(status, solved.solution, solved.residual_inf, solved.method, limits)
    evidence = EvidenceRecord(EvidenceKind.SIMULATION, status,
        "Solved the supplied linear system Kx=f and checked the algebraic residual",
        method=solved.method, limitations=limits,
        metadata={"residual_inf": solved.residual_inf, "dimension": len(load)})
    return result, evidence
