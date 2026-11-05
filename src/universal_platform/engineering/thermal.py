"""Elementary thermal expansion helpers; material coefficient is caller-supplied."""
from math import isfinite
from .quantity import Quantity
from .errors import DimensionMismatchError, EngineeringError

def linear_thermal_expansion(length: Quantity, coefficient_per_kelvin: float,
                             temperature_change_kelvin: float) -> Quantity:
    if length.dimension != (1, 0, 0, 0, 0):
        raise DimensionMismatchError("Length must have dimension [L]")
    if not isfinite(coefficient_per_kelvin) or coefficient_per_kelvin < 0:
        raise EngineeringError("Expansion coefficient must be finite and non-negative")
    if not isfinite(temperature_change_kelvin):
        raise EngineeringError("Temperature change must be finite")
    return Quantity(length.si_value * coefficient_per_kelvin * temperature_change_kelvin,
                    length.dimension, "m")
