"""Small dependency-free dimensional quantity system.

Base dimensions are length, mass, time, electric current and temperature.
Values are stored in SI base units; source unit is retained for traceability.
"""
from __future__ import annotations
from dataclasses import dataclass
from math import isfinite
from typing import Any, ClassVar, Mapping
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
    "N": (1.0, (1, 1, -2, 0, 0)), "kN": (1e3, (1, 1, -2, 0, 0)),
    "Pa": (1.0, (-1, 1, -2, 0, 0)), "kPa": (1e3, (-1, 1, -2, 0, 0)),
    "MPa": (1e6, (-1, 1, -2, 0, 0)), "GPa": (1e9, (-1, 1, -2, 0, 0)),
    "m/s": (1.0, (1, 0, -1, 0, 0)), "m2": (1.0, (2, 0, 0, 0, 0)),
    "m3": (1.0, (3, 0, 0, 0, 0)), "kg/m3": (1.0, (-3, 1, 0, 0, 0)), "V": (1.0, (2, 1, -3, -1, 0)),
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

    SCHEMA_VERSION: ClassVar[str] = "1.0"

    def __post_init__(self) -> None:
        if isinstance(self.si_value, bool) or not isinstance(self.si_value, (int, float)):
            raise EngineeringError("Quantity value must be numeric")
        if not isfinite(float(self.si_value)):
            raise EngineeringError("Quantity value must be finite")
        object.__setattr__(self, "si_value", float(self.si_value))
        if not isinstance(self.dimension, tuple) or len(self.dimension) != 5 or any(
            isinstance(x, bool) or not isinstance(x, int) for x in self.dimension
        ):
            raise EngineeringError("Dimension must be an immutable tuple of five integer exponents")
        if not isinstance(self.source_unit, str) or self.source_unit not in _UNITS:
            raise EngineeringError(f"Unsupported unit: {self.source_unit}")

    @classmethod
    def of(cls, value: float, unit: str) -> "Quantity":
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise EngineeringError("Quantity input must be numeric")
        if not isinstance(unit, str) or unit not in _UNITS:
            raise EngineeringError(f"Unsupported unit: {unit}")
        factor, dimension = _UNITS[unit]
        return cls(float(value) * factor, dimension, unit)

    def to_dict(self) -> dict[str, Any]:
        """Return a deterministic v1.0 SI-value snapshot with source-unit lineage."""
        return {
            "schema_version": self.SCHEMA_VERSION,
            "si_value": self.si_value,
            "dimension": list(self.dimension),
            "source_unit": self.source_unit,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "Quantity":
        """Restore a strict v1.0 quantity snapshot."""
        expected = {"schema_version", "si_value", "dimension", "source_unit"}
        if not isinstance(value, Mapping) or set(value) != expected:
            raise EngineeringError("Quantity snapshot has missing or unknown fields")
        if value["schema_version"] != cls.SCHEMA_VERSION:
            raise EngineeringError("Unsupported Quantity schema_version")
        raw_value = value["si_value"]
        if isinstance(raw_value, bool) or not isinstance(raw_value, (int, float)):
            raise EngineeringError("Quantity si_value must be numeric")
        raw_dimension = value["dimension"]
        if not isinstance(raw_dimension, (list, tuple)) or len(raw_dimension) != 5:
            raise EngineeringError("Quantity dimension must contain five integer exponents")
        if any(isinstance(item, bool) or not isinstance(item, int) for item in raw_dimension):
            raise EngineeringError("Quantity dimension exponents must be integers")
        source_unit = value["source_unit"]
        if not isinstance(source_unit, str) or source_unit not in _UNITS:
            raise EngineeringError(f"Unsupported unit: {source_unit}")
        return cls(float(raw_value), tuple(raw_dimension), source_unit)

    def in_unit(self, unit: str) -> float:
        if not isinstance(unit, str) or unit not in _UNITS:
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
            if other.si_value == 0:
                raise ZeroDivisionError("Quantity division by zero")
            dim = tuple(a - b for a, b in zip(self.dimension, other.dimension))
            return Quantity(self.si_value / other.si_value, dim, "1")
        if float(other) == 0:
            raise ZeroDivisionError("Quantity division by zero")
        return Quantity(self.si_value / float(other), self.dimension, self.source_unit)
