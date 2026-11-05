"""Traceable hard constraints and a fail-closed evaluation report."""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from .quantity import Quantity
from .provenance import SourceRef

class ConstraintKind(str, Enum):
    MINIMUM = "MINIMUM"
    MAXIMUM = "MAXIMUM"
    EQUAL = "EQUAL"

@dataclass(frozen=True, slots=True)
class Constraint:
    constraint_id: str
    variable: str
    kind: ConstraintKind
    bound: Quantity
    hard: bool = True
    source: SourceRef | None = None

@dataclass(frozen=True, slots=True)
class ConstraintResult:
    constraint_id: str
    status: str
    message: str

def evaluate_constraints(values: dict[str, Quantity], constraints: tuple[Constraint, ...] | list[Constraint],
                         *, tolerance: float = 1e-9) -> tuple[ConstraintResult, ...]:
    results = []
    for item in constraints:
        value = values.get(item.variable)
        if value is None:
            results.append(ConstraintResult(item.constraint_id, "UNKNOWN", "Variable is missing"))
            continue
        if value.dimension != item.bound.dimension:
            results.append(ConstraintResult(item.constraint_id, "FAIL", "Dimension mismatch"))
            continue
        delta = value.si_value - item.bound.si_value
        ok = (delta >= -tolerance if item.kind is ConstraintKind.MINIMUM else
              delta <= tolerance if item.kind is ConstraintKind.MAXIMUM else abs(delta) <= tolerance)
        results.append(ConstraintResult(item.constraint_id, "PASS" if ok else "FAIL",
                                        "Constraint satisfied" if ok else "Hard/soft bound violated"))
    return tuple(results)
