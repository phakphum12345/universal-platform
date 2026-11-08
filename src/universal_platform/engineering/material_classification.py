"""Fail-closed exact point/material classification against closed triangle meshes.

Input binary64 coordinates are interpreted as their exact represented
rationals. Boundary is tested exactly before deterministic odd/even ray tests.
A result is INSIDE or OUTSIDE only when at least two non-degenerate rays agree.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from fractions import Fraction

from .errors import InvalidModelError
from .geometry import Vec3
from .mesh import TriangleMesh, validate_triangle_mesh
from .mesh_intersection import analyze_mesh_intersections

Point3 = tuple[Fraction, Fraction, Fraction]
_DIRECTIONS: tuple[Point3, ...] = (
    (Fraction(1), Fraction(1, 17), Fraction(1, 31)),
    (Fraction(1, 19), Fraction(1), Fraction(1, 37)),
    (Fraction(1, 41), Fraction(1, 43), Fraction(1)),
    (Fraction(1, 23), Fraction(2, 29), Fraction(1)),
    (Fraction(2, 31), Fraction(1), Fraction(3, 47)),
    (Fraction(1), Fraction(3, 53), Fraction(2, 59)),
    (Fraction(3, 61), Fraction(2, 67), Fraction(1)),
)


class MaterialClassification(str, Enum):
    INSIDE = "INSIDE"
    OUTSIDE = "OUTSIDE"
    BOUNDARY = "BOUNDARY"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True, slots=True)
class MaterialClassificationResult:
    classification: MaterialClassification
    ray_directions_tested: int
    valid_ray_count: int
    crossing_counts: tuple[int, ...]
    reason: str | None = None


def _q(value: float) -> Fraction:
    return Fraction.from_float(float(value))


def _sub(a: Point3, b: Point3) -> Point3:
    return tuple(a[i] - b[i] for i in range(3))  # type: ignore[return-value]


def _cross(a: Point3, b: Point3) -> Point3:
    return (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])


def _dot(a: Point3, b: Point3) -> Fraction:
    return sum((a[i]*b[i] for i in range(3)), Fraction(0))


def _point_on_triangle(point: Point3, triangle: tuple[Point3, Point3, Point3]) -> bool:
    a, b, c = triangle
    normal = _cross(_sub(b, a), _sub(c, a))
    if _dot(normal, _sub(point, a)) != 0:
        return False
    drop = max(range(3), key=lambda axis: abs(normal[axis]))
    axes = tuple(axis for axis in range(3) if axis != drop)
    def orient(p: Point3, q: Point3, r: Point3) -> Fraction:
        return ((q[axes[0]]-p[axes[0]])*(r[axes[1]]-p[axes[1]])
                -(q[axes[1]]-p[axes[1]])*(r[axes[0]]-p[axes[0]]))
    area = orient(a, b, c)
    signs = (orient(a, b, point), orient(b, c, point), orient(c, a, point))
    return all(value >= 0 for value in signs) if area > 0 else all(value <= 0 for value in signs)


def _ray_crossings(origin: Point3, direction: Point3,
                   triangles: tuple[tuple[Point3, Point3, Point3], ...]) -> tuple[int, bool]:
    crossings = 0
    for a, b, c in triangles:
        edge1, edge2 = _sub(b, a), _sub(c, a)
        normal = _cross(edge1, edge2)
        determinant = _dot(edge1, _cross(direction, edge2))
        if determinant == 0:
            if _dot(normal, direction) == 0 and _dot(normal, _sub(origin, a)) == 0:
                return crossings, True
            continue
        offset = _sub(origin, a)
        u = _dot(offset, _cross(direction, edge2)) / determinant
        qvec = _cross(offset, edge1)
        v = _dot(direction, qvec) / determinant
        distance = _dot(edge2, qvec) / determinant
        if distance > 0 and u >= 0 and v >= 0 and u + v <= 1:
            if u == 0 or v == 0 or u + v == 1:
                return crossings, True
            crossings += 1
    return crossings, False


def classify_point_against_mesh(
    point: Vec3,
    mesh: TriangleMesh,
    *,
    max_ray_checks: int = 1_000_000,
) -> MaterialClassificationResult:
    """Classify a point against a validated, closed, non-self-intersecting mesh.

    Invalid/open/non-manifold/self-intersecting inputs and unresolved ray
    degeneracies return UNKNOWN. The function never guesses a boundary side.
    """
    if not isinstance(point, Vec3) or not isinstance(mesh, TriangleMesh):
        raise InvalidModelError("classification requires a Vec3 point and TriangleMesh")
    if isinstance(max_ray_checks, bool) or not isinstance(max_ray_checks, int) or max_ray_checks < 1:
        raise InvalidModelError("max_ray_checks must be a positive integer")
    required_checks = len(mesh.triangles) * len(_DIRECTIONS)
    if required_checks > max_ray_checks:
        return MaterialClassificationResult(MaterialClassification.UNKNOWN, 0, 0, (),
                                            "ray-triangle resource budget exceeded")
    topology = validate_triangle_mesh(mesh)
    if not (topology.valid and topology.watertight and topology.consistently_oriented):
        return MaterialClassificationResult(MaterialClassification.UNKNOWN, 0, 0, (),
                                            "mesh is not a valid oriented watertight shell")
    intersections = analyze_mesh_intersections(mesh)
    if intersections.status != "NO_INTERSECTIONS_FOUND":
        return MaterialClassificationResult(MaterialClassification.UNKNOWN, 0, 0, (),
                                            f"mesh self-intersection status is {intersections.status}")
    origin = (_q(point.x), _q(point.y), _q(point.z))
    triangles = tuple(tuple((_q(mesh.vertices[i].x), _q(mesh.vertices[i].y),
                             _q(mesh.vertices[i].z)) for i in face)
                      for face in mesh.triangles)
    if any(_point_on_triangle(origin, triangle) for triangle in triangles):
        return MaterialClassificationResult(MaterialClassification.BOUNDARY, 0, 0, ())
    counts: list[int] = []
    for direction in _DIRECTIONS:
        crossing_count, ambiguous = _ray_crossings(origin, direction, triangles)
        if not ambiguous:
            counts.append(crossing_count)
    if len(counts) < 2 or len(set(count % 2 for count in counts)) != 1:
        return MaterialClassificationResult(
            MaterialClassification.UNKNOWN, len(_DIRECTIONS), len(counts), tuple(counts),
            "insufficient or inconsistent non-degenerate exact ray witnesses",
        )
    classification = MaterialClassification.INSIDE if counts[0] % 2 else MaterialClassification.OUTSIDE
    return MaterialClassificationResult(classification, len(_DIRECTIONS), len(counts), tuple(counts))
