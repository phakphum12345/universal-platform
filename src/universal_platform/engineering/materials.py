"""Traceable material property record; values are not certified allowables."""
from dataclasses import dataclass
from .quantity import Quantity
from .errors import InvalidModelError
from .provenance import SourceRef

PRESSURE = (-1, 1, -2, 0, 0)
DENSITY = (-3, 1, 0, 0, 0)

@dataclass(frozen=True, slots=True)
class Material:
    material_id: str
    name: str
    density: Quantity
    young_modulus: Quantity
    poisson_ratio: float
    yield_strength: Quantity | None = None
    source: SourceRef | None = None
    notes: tuple[str, ...] = ()

    def __post_init__(self):
        if not self.material_id.strip() or not self.name.strip():
            raise InvalidModelError("Material identity and name are required")
        if self.density.dimension != DENSITY or self.density.si_value <= 0:
            raise InvalidModelError("Density must be positive and use kg/m³ dimensions")
        if self.young_modulus.dimension != PRESSURE or self.young_modulus.si_value <= 0:
            raise InvalidModelError("Young's modulus must be positive pressure")
        if not 0 <= self.poisson_ratio < 0.5:
            raise InvalidModelError("Isotropic Poisson ratio must be in [0, 0.5)")
        if self.yield_strength is not None and (
            self.yield_strength.dimension != PRESSURE or self.yield_strength.si_value <= 0
        ):
            raise InvalidModelError("Yield strength must be positive pressure")
