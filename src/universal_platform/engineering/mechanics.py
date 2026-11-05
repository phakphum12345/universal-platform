"""Unit-aware elementary mechanics calculations; not a design code checker."""
from __future__ import annotations
from .quantity import Quantity
from .errors import DimensionMismatchError, EngineeringError

FORCE = (1, 1, -2, 0, 0)
AREA = (2, 0, 0, 0, 0)
PRESSURE = (-1, 1, -2, 0, 0)
DIMENSIONLESS = (0, 0, 0, 0, 0)

def axial_stress(force: Quantity, area: Quantity) -> Quantity:
    if force.dimension != FORCE or area.dimension != AREA:
        raise DimensionMismatchError("axial_stress requires force [N] and area [m²]")
    if area.si_value <= 0:
        raise EngineeringError("Cross-sectional area must be positive")
    return force / area

def axial_strain(extension: Quantity, original_length: Quantity) -> Quantity:
    if extension.dimension != original_length.dimension or original_length.si_value <= 0:
        raise DimensionMismatchError("Strain requires compatible lengths and positive original length")
    return extension / original_length

def factor_of_safety(yield_strength: Quantity, applied_stress: Quantity) -> float:
    if yield_strength.dimension != PRESSURE or applied_stress.dimension != PRESSURE:
        raise DimensionMismatchError("Factor of safety requires stress quantities")
    if yield_strength.si_value <= 0 or applied_stress.si_value <= 0:
        raise EngineeringError("Strength and applied stress must be positive")
    return yield_strength.si_value / applied_stress.si_value
