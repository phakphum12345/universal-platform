"""Small dependency-free dimensional quantity system.

Base dimensions are length, mass, time, electric current and temperature.
Values are stored in SI base units; source unit is retained for traceability.
"""
from __future__ import annotations
from dataclasses import dataclass
from math import isfinite
from .errors import DimensionMismatchError, EngineeringError

Dimension = tuple[int, int, int, int, int]
DIMENSIONLESS: Dimension = (0, 0, 0, 0, 0)
LENGTH: Dimension = (1, 0, 0, 0, 0)
MASS: Dimension = (0, 1, 0, 0, 0)
TIME: Dimension = (0, 0, 1, 0, 0)
CURRENT: Dimension = (0, 0, 0, 1, 0)
TEMPERATURE: Dimension = (0, 0, 0, 0, 1)

_UNITS: dict[str, tuple[float, Dimension]] = {
    "1": (1.0, DIMENSIONLESS), "m": (1.0, LENGTH), "mm": (1e-3, LENGTH),
    "cm": (1e-2, LENGTH), "km": (1e3, LENGTH), "in": (0.0254, LENGTH),
    "kg": (1.0, MASS), "g": (1e-3, MASS), "s": (1.0, TIME),
    "ms": (1e-3, TIME), "min": (60.0, TIME), "h": (3600.0, TIME),
    "A": (1.0, CURRENT), "mA": (1e-3, CURRENT), "K": (1.0, TEMPERATURE),
    "m": (1.0, LENGTH), "N": (1.0, (1, 1, -2, 0, 0)), "kN": (1e3, (1, 1, -2, 0, 0)),
    "Pa": (1.0, (-1, 1, -2, 0, 0)), "kPa": (1e3, (-1, 1, -2, 0, 0)),
    "MPa": (1e6, (-1, 1, -2, 0, 0)), "GPa": (1e9, (-1, 1, -2, 0, 0)),
    "m/s": (1.0, (1, 0, -1, 0, 0)), "m2": (1.0, (2, 0, 0, 0, 0)),
    "m3": (1.0, (3, 0, 0, 0, 0)), "V": (1.0, (2, 1, -3, -1, 0)),
    "mV": (1e-3, (2, 1, -3, -1, 0)), "W": (1.0, (2, 1, -3, 0, 0)),
    "kW": (1e3, (2, 1, -3, 0, 0)), "J": (1.0, (2, 1, -2, 0, 0)),
    "ohm": (1.0, (2, 1, -3, -2, 0)), "Hz": (1.0, (0, 0, -1, 0, 0)),
}

@dataclass(frozen=True, slots=True)
class Quantity:
    """A finite SI value with a dimensional signature and original unit."""
    si_value: float
    dimension: Dimension
    source_unit: str = "1"

    def __post_init__(self) -> None:
        if not isfinite(self.si_value):
            raise EngineeringError("Quantity value must be finite")
        if len(self.dimension) != 5 or any(not isinstance(x, int) for x in self.dimension):
            raise EngineeringError("Dimension must contain five integer exponents")
        if self.source_unit not in _UNITS:
            raise EngineeringError(f"Unsupported unit: {self.source_unit}")

    @classmethod
    def of(cls, value: float, unit: str) -> "Quantity":
        if unit not in _UNITS:
            raise EngineeringError(f"Unsupported unit: {unit}")
        factor, dimension = _UNITS[unit]
        return cls(float(value) * factor, dimension, unit)

    def in_unit(self, unit: str) -> float:
        if unit not in _UNITS:
            raise EngineeringError(f"Unsupported unit: {unit}")
        factor, dimension = _UNITS[unit]
        if dimension != self.dimension:
            raise DimensionMismatchError(f"Cannot express {self.dimension} in {unit}")
        return self.si_value / factor

    def _same(self, other: "Quantity") -> None:
        if self.dimension != other.dimension:
            raise DimensionMismatchError(f"Incompatible dimensions: {self.dimension} and {other.dimension}")

    def __add__(self, other: "Quantity") -> "Quantity":
        self._same(other)
        return Quantity(self.si_value + other.si_value, self.dimension, "1")

    def __sub__(self, other: "Quantity") -> "Quantity":
        self._same(other)
        return Quantity(self.si_value - other.si_value, self.dimension, "1")

    def __mul__(self, other: float | "Quantity") -> "Quantity":
        if isinstance(other, Quantity):
            dim = tuple(a + b for a, b in zip(self.dimension, other.dimension))
            return Quantity(self.si_value * other.si_value, dim, "1")
        return Quantity(self.si_value * float(other), self.dimension, self.source_unit)

    def __rmul__(self, other: float) -> "Quantity":
        return self * other

    def __truediv__(self, other: float | "Quantity") -> "Quantity":
        if isinstance(other, Quantity):
            dim = tuple(a - b for a, b in zip(self.dimension, other.dimension))
            return Quantity(self.si_value / other.si_value, dim, "1")
        if float(other) == 0:
            raise ZeroDivisionError("Quantity division by zero")
        return Quantity(self.si_value / float(other), self.dimension, self.source_unit)
