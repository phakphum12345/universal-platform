"""Elementary DC electrical calculations with dimensional validation."""
from .quantity import Quantity
from .errors import DimensionMismatchError, EngineeringError

VOLTAGE = (2, 1, -3, -1, 0)
CURRENT = (0, 0, 0, 1, 0)
RESISTANCE = (2, 1, -3, -2, 0)
POWER = (2, 1, -3, 0, 0)

def ohms_law(voltage: Quantity, resistance: Quantity) -> Quantity:
    if voltage.dimension != VOLTAGE or resistance.dimension != RESISTANCE:
        raise DimensionMismatchError("Ohm's law requires voltage [V] and resistance [ohm]")
    if resistance.si_value <= 0:
        raise EngineeringError("Resistance must be positive")
    return voltage / resistance

def electrical_power(voltage: Quantity, current: Quantity) -> Quantity:
    if voltage.dimension != VOLTAGE or current.dimension != CURRENT:
        raise DimensionMismatchError("Power requires voltage [V] and current [A]")
    return voltage * current
