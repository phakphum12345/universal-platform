"""Dependency-free parametric primitives and geometric sanity checks.

These are analytic bounding primitives, not a boundary-representation CAD kernel.
No STEP/STL/mesh export or manufacturability certification is implied.
"""
from __future__ import annotations
from dataclasses import dataclass
from math import isfinite, pi
from .errors import InvalidModelError

@dataclass(frozen=True, slots=True)
class Vec3:
    x: float
    y: float
    z: float

    def __post_init__(self):
        if not all(isfinite(v) for v in (self.x, self.y, self.z)):
            raise InvalidModelError("Vector coordinates must be finite")

@dataclass(frozen=True, slots=True)
class BoundingBox:
    minimum: Vec3
    maximum: Vec3

    def __post_init__(self):
        if any(a > b for a, b in zip(
            (self.minimum.x, self.minimum.y, self.minimum.z),
            (self.maximum.x, self.maximum.y, self.maximum.z))):
            raise InvalidModelError("Bounding box minimum exceeds maximum")

    @property
    def volume(self) -> float:
        return ((self.maximum.x-self.minimum.x) *
                (self.maximum.y-self.minimum.y) *
                (self.maximum.z-self.minimum.z))

@dataclass(frozen=True, slots=True)
class Box:
    length: float
    width: float
    height: float

    def __post_init__(self):
        if not all(isfinite(v) and v > 0 for v in (self.length, self.width, self.height)):
            raise InvalidModelError("Box dimensions must be finite and positive")

    @property
    def volume(self) -> float:
        return self.length * self.width * self.height

    @property
    def bounds(self) -> BoundingBox:
        return BoundingBox(Vec3(0, 0, 0), Vec3(self.length, self.width, self.height))

@dataclass(frozen=True, slots=True)
class Cylinder:
    radius: float
    height: float

    def __post_init__(self):
        if not all(isfinite(v) and v > 0 for v in (self.radius, self.height)):
            raise InvalidModelError("Cylinder radius and height must be finite and positive")

    @property
    def volume(self) -> float:
        return pi * self.radius**2 * self.height

    @property
    def bounds(self) -> BoundingBox:
        return BoundingBox(Vec3(-self.radius, -self.radius, 0),
                           Vec3(self.radius, self.radius, self.height))
