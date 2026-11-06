"""Rigid coordinate transforms for offline 3D engineering models.

Convention: x_to = R_to_from * x_from + t_to_from. Translation is expressed
in the destination frame. Only proper rigid rotations are accepted.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import isclose, isfinite
from typing import ClassVar, Mapping, TypeAlias

from .errors import InvalidModelError
from .geometry import BoundingBox, Vec3
from .quantity import LENGTH, Quantity

Matrix3: TypeAlias = tuple[
    tuple[float, float, float],
    tuple[float, float, float],
    tuple[float, float, float],
]

_IDENTITY: Matrix3 = (
    (1.0, 0.0, 0.0),
    (0.0, 1.0, 0.0),
    (0.0, 0.0, 1.0),
)


def _mat_vec(matrix: Matrix3, vector: Vec3) -> Vec3:
    values = (vector.x, vector.y, vector.z)
    return Vec3(*(sum(row[i] * values[i] for i in range(3)) for row in matrix))


def _mat_mul(left: Matrix3, right: Matrix3) -> Matrix3:
    return tuple(
        tuple(sum(left[row][k] * right[k][column] for k in range(3))
              for column in range(3))
        for row in range(3)
    )  # type: ignore[return-value]


def _transpose(matrix: Matrix3) -> Matrix3:
    return tuple(
        tuple(matrix[column][row] for column in range(3))
        for row in range(3)
    )  # type: ignore[return-value]


def _determinant(matrix: Matrix3) -> float:
    a, b, c = matrix
    return (
        a[0] * (b[1] * c[2] - b[2] * c[1])
        - a[1] * (b[0] * c[2] - b[2] * c[0])
        + a[2] * (b[0] * c[1] - b[1] * c[0])
    )


def _validate_rotation(matrix: Matrix3, tolerance: float) -> None:
    if not isinstance(matrix, tuple) or len(matrix) != 3 or any(
        not isinstance(row, tuple) or len(row) != 3 for row in matrix
    ):
        raise InvalidModelError("Rotation must be an immutable 3x3 tuple matrix")
    if any(
        isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value)
        for row in matrix for value in row
    ):
        raise InvalidModelError("Rotation entries must be finite numeric values")
    product = _mat_mul(matrix, _transpose(matrix))
    for row in range(3):
        for column in range(3):
            expected = 1.0 if row == column else 0.0
            if not isclose(product[row][column], expected, rel_tol=0.0, abs_tol=tolerance):
                raise InvalidModelError("Rotation must be orthonormal (scale and shear are not allowed)")
    if not isclose(_determinant(matrix), 1.0, rel_tol=0.0, abs_tol=tolerance):
        raise InvalidModelError("Rotation must be right-handed with determinant +1")


@dataclass(frozen=True, slots=True)
class RigidTransform:
    """Map coordinates from from_frame into to_frame.

    p_to = rotation * p_from + translation. Coordinates on both frames are
    assumed to use the same length unit; unit conversion is separate.
    """
    from_frame: str
    to_frame: str
    rotation: Matrix3 = _IDENTITY
    translation: Vec3 = Vec3(0.0, 0.0, 0.0)
    length_unit: str = "m"

    SCHEMA_VERSION: ClassVar[str] = "1.0"

    def __post_init__(self) -> None:
        if not isinstance(self.from_frame, str) or not self.from_frame.strip():
            raise InvalidModelError("Transform from_frame identifier is required")
        if not isinstance(self.to_frame, str) or not self.to_frame.strip():
            raise InvalidModelError("Transform to_frame identifier is required")
        if not isinstance(self.translation, Vec3):
            raise InvalidModelError("Transform translation must be a Vec3")
        if not isinstance(self.length_unit, str) or not self.length_unit:
            raise InvalidModelError("Transform length_unit is required")
        try:
            unit = Quantity.of(1.0, self.length_unit)
        except Exception as exc:
            raise InvalidModelError(f"Unsupported transform length unit: {self.length_unit}") from exc
        if unit.dimension != LENGTH:
            raise InvalidModelError("Transform length_unit must have length dimension")
        _validate_rotation(self.rotation, 1e-9)

    @classmethod
    def identity(cls, frame_id: str, length_unit: str = "m") -> "RigidTransform":
        return cls(frame_id, frame_id, length_unit=length_unit)

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.SCHEMA_VERSION,
            "from_frame": self.from_frame,
            "to_frame": self.to_frame,
            "rotation": [list(row) for row in self.rotation],
            "translation": {
                "x": self.translation.x,
                "y": self.translation.y,
                "z": self.translation.z,
                "unit": self.length_unit,
            },
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, object]) -> "RigidTransform":
        expected = {"schema_version", "from_frame", "to_frame", "rotation", "translation"}
        if not isinstance(value, Mapping) or set(value) != expected:
            raise InvalidModelError("RigidTransform snapshot has missing or unknown fields")
        if value["schema_version"] != cls.SCHEMA_VERSION:
            raise InvalidModelError("Unsupported RigidTransform schema_version")
        raw_rotation = value["rotation"]
        if not isinstance(raw_rotation, (list, tuple)) or len(raw_rotation) != 3:
            raise InvalidModelError("RigidTransform rotation must be a 3x3 matrix")
        try:
            rotation = tuple(tuple(row) for row in raw_rotation)
        except TypeError as exc:
            raise InvalidModelError("RigidTransform rotation rows must be sequences") from exc
        raw_translation = value["translation"]
        if not isinstance(raw_translation, Mapping) or set(raw_translation) != {"x", "y", "z", "unit"}:
            raise InvalidModelError("RigidTransform translation requires x, y, z and unit")
        coordinates = (raw_translation["x"], raw_translation["y"], raw_translation["z"])
        if any(isinstance(item, bool) or not isinstance(item, (int, float)) for item in coordinates):
            raise InvalidModelError("RigidTransform translation coordinates must be numeric")
        return cls(
            from_frame=value["from_frame"],
            to_frame=value["to_frame"],
            rotation=rotation,  # type: ignore[arg-type]
            translation=Vec3(*(float(item) for item in coordinates)),
            length_unit=raw_translation["unit"],
        )

    def apply_vector(self, vector: Vec3) -> Vec3:
        """Rotate a vector without applying translation."""
        return _mat_vec(self.rotation, vector)

    def apply_point(self, point: Vec3) -> Vec3:
        """Rotate and translate a point into the destination frame."""
        rotated = self.apply_vector(point)
        return Vec3(rotated.x + self.translation.x,
                    rotated.y + self.translation.y,
                    rotated.z + self.translation.z)

    def apply_bounds(self, bounds: BoundingBox) -> BoundingBox:
        """Enclose all eight transformed corners in a destination AABB."""
        corners = tuple(
            self.apply_point(Vec3(x, y, z))
            for x in (bounds.minimum.x, bounds.maximum.x)
            for y in (bounds.minimum.y, bounds.maximum.y)
            for z in (bounds.minimum.z, bounds.maximum.z)
        )
        return BoundingBox(
            Vec3(*(min(getattr(point, axis) for point in corners) for axis in ("x", "y", "z"))),
            Vec3(*(max(getattr(point, axis) for point in corners) for axis in ("x", "y", "z"))),
        )

    def inverse(self) -> "RigidTransform":
        """Return the inverse mapping from to_frame back to from_frame."""
        inverse_rotation = _transpose(self.rotation)
        inverse_translation = _mat_vec(
            inverse_rotation,
            Vec3(-self.translation.x, -self.translation.y, -self.translation.z),
        )
        return RigidTransform(self.to_frame, self.from_frame,
                              inverse_rotation, inverse_translation, self.length_unit)

    def then(self, next_transform: "RigidTransform") -> "RigidTransform":
        """Compose this A→B mapping followed by a B→C mapping."""
        if self.to_frame != next_transform.from_frame:
            raise InvalidModelError(
                f"Cannot compose {self.from_frame}→{self.to_frame} with "
                f"{next_transform.from_frame}→{next_transform.to_frame}"
            )
        if self.length_unit != next_transform.length_unit:
            raise InvalidModelError("Cannot compose transforms with different length units")
        rotation = _mat_mul(next_transform.rotation, self.rotation)
        translated = next_transform.apply_point(self.translation)
        return RigidTransform(self.from_frame, next_transform.to_frame,
                              rotation, translated, self.length_unit)
