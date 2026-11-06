"""Exact, deterministic triangle-mesh self-intersection diagnostics.

This module analyzes represented IEEE-754 binary64 coordinates as exact
rationals. It is an offline diagnostic, not a mesh repair or CAD kernel.
"""
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from hashlib import sha256
from itertools import combinations
from json import dumps
from typing import Any, ClassVar, Mapping

from .errors import InvalidModelError
from .mesh import TriangleMesh, validate_triangle_mesh

MAX_CANDIDATE_PAIRS = 5_000_000
ALGORITHM_VERSION = "sweep-aabb-exact-rational-v1"
PREDICATE_POLICY_VERSION = "binary64-as-exact-rational-v1"
_CLASSIFICATIONS = {
    "PROPER_INTERSECTION", "COPLANAR_OVERLAP", "UNSHARED_CONTACT",
    "DUPLICATE_FACET", "ADJACENT_FOLDOVER", "ADJACENT_VERTEX_CROSSING",
}
_RESULT_FIELDS = {
    "schema_version", "solid_id", "frame_id", "length_unit",
    "source_geometry_sha256", "mesh_snapshot_sha256", "triangle_count", "algorithm_version",
    "predicate_policy_version", "candidate_pair_count", "candidate_pair_count_complete",
    "checked_pair_count", "candidate_pair_limit", "status", "intersections",
    "unresolved_reasons",
}
_POINT = tuple[Fraction, Fraction, Fraction]
_POINT2 = tuple[Fraction, Fraction]


@dataclass(frozen=True, slots=True)
class MeshIntersection:
    triangle_a: int
    triangle_b: int
    classification: str

    def __post_init__(self) -> None:
        if (isinstance(self.triangle_a, bool) or not isinstance(self.triangle_a, int)
                or isinstance(self.triangle_b, bool) or not isinstance(self.triangle_b, int)
                or self.triangle_a < 0 or self.triangle_b <= self.triangle_a):
            raise InvalidModelError("intersection triangle indices must be ordered non-negative integers")
        if not isinstance(self.classification, str) or self.classification not in _CLASSIFICATIONS:
            raise InvalidModelError("unsupported mesh intersection classification")

    def to_dict(self) -> dict[str, Any]:
        return {"triangle_a": self.triangle_a, "triangle_b": self.triangle_b,
                "classification": self.classification}


@dataclass(frozen=True, slots=True)
class MeshIntersectionAnalysis:
    """Immutable result tied to the exact input mesh and algorithm policy."""

    solid_id: str
    frame_id: str
    length_unit: str
    source_geometry_sha256: str
    mesh_snapshot_sha256: str
    triangle_count: int
    candidate_pair_count: int
    candidate_pair_count_complete: bool
    checked_pair_count: int
    candidate_pair_limit: int
    status: str
    intersections: tuple[MeshIntersection, ...]
    unresolved_reasons: tuple[str, ...]

    SCHEMA_VERSION: ClassVar[str] = "1.0"
    ALGORITHM_VERSION: ClassVar[str] = ALGORITHM_VERSION
    PREDICATE_POLICY_VERSION: ClassVar[str] = PREDICATE_POLICY_VERSION

    def __post_init__(self) -> None:
        for label, value in (("solid_id", self.solid_id), ("frame_id", self.frame_id),
                             ("length_unit", self.length_unit)):
            if not isinstance(value, str) or not value.strip():
                raise InvalidModelError(f"{label} is required")
        for label, digest in (("source_geometry_sha256", self.source_geometry_sha256),
                              ("mesh_snapshot_sha256", self.mesh_snapshot_sha256)):
            if (not isinstance(digest, str) or len(digest) != 64
                    or any(ch not in "0123456789abcdef" for ch in digest)):
                raise InvalidModelError(f"{label} must be a lowercase SHA-256 digest")
        for label, value in (("triangle_count", self.triangle_count),
                             ("candidate_pair_count", self.candidate_pair_count),
                             ("checked_pair_count", self.checked_pair_count),
                             ("candidate_pair_limit", self.candidate_pair_limit)):
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise InvalidModelError(f"{label} must be a non-negative integer")
        if not 1 <= self.candidate_pair_limit <= MAX_CANDIDATE_PAIRS:
            raise InvalidModelError("candidate_pair_limit is outside the supported range")
        if not isinstance(self.candidate_pair_count_complete, bool):
            raise InvalidModelError("candidate_pair_count_complete must be boolean")
        if self.checked_pair_count > self.candidate_pair_count:
            raise InvalidModelError("checked_pair_count cannot exceed candidate_pair_count")
        if not isinstance(self.intersections, tuple) or any(
            not isinstance(item, MeshIntersection) for item in self.intersections
        ):
            raise InvalidModelError("intersections must be an immutable tuple")
        keys = tuple((item.triangle_a, item.triangle_b, item.classification) for item in self.intersections)
        if tuple(sorted(set(keys))) != keys:
            raise InvalidModelError("intersections must be sorted and unique")
        if any(item.triangle_b >= self.triangle_count for item in self.intersections):
            raise InvalidModelError("intersection record contains an out-of-range triangle index")
        if (not isinstance(self.unresolved_reasons, tuple)
                or any(not isinstance(reason, str) or not reason for reason in self.unresolved_reasons)
                or tuple(sorted(set(self.unresolved_reasons))) != self.unresolved_reasons):
            raise InvalidModelError("unresolved_reasons must be sorted and unique")
        if self.status not in {"NO_INTERSECTIONS_FOUND", "INTERSECTIONS_FOUND", "UNKNOWN"}:
            raise InvalidModelError("unsupported mesh intersection status")
        if self.status == "NO_INTERSECTIONS_FOUND" and (
            not self.candidate_pair_count_complete
            or self.checked_pair_count != self.candidate_pair_count
            or self.intersections or self.unresolved_reasons
        ):
            raise InvalidModelError("NO_INTERSECTIONS_FOUND requires complete, fully resolved candidate coverage")
        if self.status == "INTERSECTIONS_FOUND" and not self.intersections:
            raise InvalidModelError("INTERSECTIONS_FOUND requires at least one classified pair")
        if self.status == "UNKNOWN" and not self.unresolved_reasons:
            raise InvalidModelError("UNKNOWN requires an explicit unresolved reason")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.SCHEMA_VERSION,
            "solid_id": self.solid_id, "frame_id": self.frame_id,
            "length_unit": self.length_unit,
            "source_geometry_sha256": self.source_geometry_sha256,
            "mesh_snapshot_sha256": self.mesh_snapshot_sha256,
            "triangle_count": self.triangle_count,
            "algorithm_version": self.ALGORITHM_VERSION,
            "predicate_policy_version": self.PREDICATE_POLICY_VERSION,
            "candidate_pair_count": self.candidate_pair_count,
            "candidate_pair_count_complete": self.candidate_pair_count_complete,
            "checked_pair_count": self.checked_pair_count,
            "candidate_pair_limit": self.candidate_pair_limit,
            "status": self.status,
            "intersections": [item.to_dict() for item in self.intersections],
            "unresolved_reasons": list(self.unresolved_reasons),
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "MeshIntersectionAnalysis":
        if not isinstance(value, Mapping) or set(value) != _RESULT_FIELDS:
            raise InvalidModelError("MeshIntersectionAnalysis snapshot has missing or unknown fields")
        if value["schema_version"] != cls.SCHEMA_VERSION:
            raise InvalidModelError("unsupported MeshIntersectionAnalysis schema_version")
        if value["algorithm_version"] != ALGORITHM_VERSION or value["predicate_policy_version"] != PREDICATE_POLICY_VERSION:
            raise InvalidModelError("unsupported mesh intersection algorithm/predicate version")
        raw_pairs, raw_reasons = value["intersections"], value["unresolved_reasons"]
        if not isinstance(raw_pairs, (list, tuple)) or not isinstance(raw_reasons, (list, tuple)):
            raise InvalidModelError("intersections and unresolved_reasons must be arrays")
        pairs = tuple(MeshIntersection(
            item["triangle_a"], item["triangle_b"], item["classification"]
        ) for item in raw_pairs if isinstance(item, Mapping) and set(item) == {
            "triangle_a", "triangle_b", "classification"
        })
        if len(pairs) != len(raw_pairs):
            raise InvalidModelError("malformed intersection record")
        return cls(
            solid_id=value["solid_id"], frame_id=value["frame_id"], length_unit=value["length_unit"],
            source_geometry_sha256=value["source_geometry_sha256"],
            mesh_snapshot_sha256=value["mesh_snapshot_sha256"], triangle_count=value["triangle_count"],
            candidate_pair_count=value["candidate_pair_count"],
            candidate_pair_count_complete=value["candidate_pair_count_complete"],
            checked_pair_count=value["checked_pair_count"],
            candidate_pair_limit=value["candidate_pair_limit"], status=value["status"],
            intersections=pairs, unresolved_reasons=tuple(raw_reasons),
        )


def _q(value: float) -> Fraction:
    return Fraction.from_float(float(value))


def _sub(a: _POINT, b: _POINT) -> _POINT:
    return (a[0]-b[0], a[1]-b[1], a[2]-b[2])


def _cross(a: _POINT, b: _POINT) -> _POINT:
    return (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])


def _dot(a: _POINT, b: _POINT) -> Fraction:
    return a[0]*b[0]+a[1]*b[1]+a[2]*b[2]


def _orient2(a: _POINT2, b: _POINT2, c: _POINT2) -> Fraction:
    return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])


def _project(point: _POINT, drop: int) -> _POINT2:
    axes = tuple(axis for axis in range(3) if axis != drop)
    return (point[axes[0]], point[axes[1]])


def _inside3(point: _POINT, triangle: tuple[_POINT, _POINT, _POINT], strict: bool = False) -> bool:
    a, b, c = triangle
    normal = _cross(_sub(b, a), _sub(c, a))
    signs = tuple(_dot(_cross(_sub(end, start), _sub(point, start)), normal)
                  for start, end in ((a, b), (b, c), (c, a)))
    if strict:
        return all(value > 0 for value in signs) or all(value < 0 for value in signs)
    return all(value >= 0 for value in signs) or all(value <= 0 for value in signs)


def _dedupe_polygon(points: list[_POINT2]) -> list[_POINT2]:
    result: list[_POINT2] = []
    for point in points:
        if not result or result[-1] != point:
            result.append(point)
    if len(result) > 1 and result[0] == result[-1]:
        result.pop()
    return result


def _coplanar_intersection(a: tuple[_POINT, _POINT, _POINT],
                           b: tuple[_POINT, _POINT, _POINT]) -> tuple[tuple[_POINT2, ...], bool]:
    normal = _cross(_sub(a[1], a[0]), _sub(a[2], a[0]))
    drop = max(range(3), key=lambda axis: (abs(normal[axis]), -axis))
    subject = [_project(point, drop) for point in a]
    clip = [_project(point, drop) for point in b]
    orientation = 1 if _orient2(clip[0], clip[1], clip[2]) > 0 else -1
    polygon = subject
    for edge_index in range(3):
        start, end = clip[edge_index], clip[(edge_index+1) % 3]
        if not polygon:
            break
        output: list[_POINT2] = []
        previous = polygon[-1]
        d_previous = _orient2(start, end, previous) * orientation
        for current in polygon:
            d_current = _orient2(start, end, current) * orientation
            previous_inside, current_inside = d_previous >= 0, d_current >= 0
            if previous_inside != current_inside:
                ratio = d_previous / (d_previous-d_current)
                output.append((previous[0]+ratio*(current[0]-previous[0]),
                               previous[1]+ratio*(current[1]-previous[1])))
            if current_inside:
                output.append(current)
            previous, d_previous = current, d_current
        polygon = _dedupe_polygon(output)
    if not polygon:
        return (), False
    area2 = sum(polygon[i][0]*polygon[(i+1) % len(polygon)][1]
                - polygon[(i+1) % len(polygon)][0]*polygon[i][1]
                for i in range(len(polygon))) if len(polygon) >= 3 else Fraction(0)
    return tuple(polygon), area2 != 0


def _segment_plane_point(p: _POINT, q: _POINT, dp: Fraction, dq: Fraction) -> _POINT:
    ratio = dp / (dp-dq)
    return tuple(p[i]+ratio*(q[i]-p[i]) for i in range(3))  # type: ignore[return-value]


def _edge_plane_points(source: tuple[_POINT, _POINT, _POINT],
                       target: tuple[_POINT, _POINT, _POINT]) -> set[_POINT]:
    normal = _cross(_sub(target[1], target[0]), _sub(target[2], target[0]))
    distances = tuple(_dot(normal, _sub(point, target[0])) for point in source)
    found: set[_POINT] = set()
    for index in range(3):
        p, q = source[index], source[(index+1) % 3]
        dp, dq = distances[index], distances[(index+1) % 3]
        if dp == 0 and _inside3(p, target):
            found.add(p)
        if dp == 0 and dq == 0:
            if _inside3(q, target):
                found.add(q)
        elif (dp < 0 < dq) or (dq < 0 < dp):
            point = _segment_plane_point(p, q, dp, dq)
            if _inside3(point, target):
                found.add(point)
        elif dq == 0 and _inside3(q, target):
            found.add(q)
    return found


def _on_segment(point: _POINT, a: _POINT, b: _POINT) -> bool:
    direction, offset = _sub(b, a), _sub(point, a)
    if _cross(direction, offset) != (Fraction(0), Fraction(0), Fraction(0)):
        return False
    return all(min(a[i], b[i]) <= point[i] <= max(a[i], b[i]) for i in range(3))


def _pair_intersection(mesh: TriangleMesh, ia: int, ib: int) -> str | None:
    fa, fb = mesh.triangles[ia], mesh.triangles[ib]
    a = tuple(tuple(_q(v) for v in (mesh.vertices[index].x, mesh.vertices[index].y, mesh.vertices[index].z))
              for index in fa)
    b = tuple(tuple(_q(v) for v in (mesh.vertices[index].x, mesh.vertices[index].y, mesh.vertices[index].z))
              for index in fb)
    ta: tuple[_POINT, _POINT, _POINT] = a  # type: ignore[assignment]
    tb: tuple[_POINT, _POINT, _POINT] = b  # type: ignore[assignment]
    common = set(fa).intersection(fb)
    if len(common) == 3:
        return "DUPLICATE_FACET"
    if {tuple(sorted(point for point in ta))} == {tuple(sorted(point for point in tb))}:
        return "DUPLICATE_FACET"
    na = _cross(_sub(ta[1], ta[0]), _sub(ta[2], ta[0]))
    nb = _cross(_sub(tb[1], tb[0]), _sub(tb[2], tb[0]))
    da = tuple(_dot(na, _sub(point, ta[0])) for point in tb)
    db = tuple(_dot(nb, _sub(point, tb[0])) for point in ta)
    if all(value == 0 for value in da) and all(value == 0 for value in db):
        clipped_points, positive_area = _coplanar_intersection(ta, tb)
        if not clipped_points:
            return None
        if positive_area:
            if len(common) == 2:
                return "ADJACENT_FOLDOVER"
            if len(common) == 1:
                return "ADJACENT_VERTEX_CROSSING"
            return "COPLANAR_OVERLAP"
        normal = na
        drop = max(range(3), key=lambda axis: (abs(normal[axis]), -axis))
        if len(common) == 2:
            shared = [mesh.vertices[index] for index in sorted(common)]
            expected = {_project(tuple(_q(v) for v in (point.x, point.y, point.z)), drop)
                        for point in shared}
            return None if set(clipped_points).issubset(expected) else "UNSHARED_CONTACT"
        if len(common) == 1:
            point = mesh.vertices[next(iter(common))]
            expected = _project(tuple(_q(v) for v in (point.x, point.y, point.z)), drop)
            return None if set(clipped_points) == {expected} else "ADJACENT_VERTEX_CROSSING"
        return "UNSHARED_CONTACT"
    points = _edge_plane_points(ta, tb) | _edge_plane_points(tb, ta)
    if not points:
        return None
    if len(common) == 2:
        shared = sorted(common)
        p0v, p1v = (mesh.vertices[index] for index in shared)
        p0 = tuple(_q(v) for v in (p0v.x, p0v.y, p0v.z))
        p1 = tuple(_q(v) for v in (p1v.x, p1v.y, p1v.z))
        return None if all(_on_segment(point, p0, p1) for point in points) else "ADJACENT_FOLDOVER"
    if len(common) == 1:
        index = next(iter(common))
        vertex = mesh.vertices[index]
        expected = tuple(_q(v) for v in (vertex.x, vertex.y, vertex.z))
        return None if points == {expected} else "ADJACENT_VERTEX_CROSSING"
    if len(points) >= 2:
        farthest = max(combinations(sorted(points), 2),
                       key=lambda pair: sum((pair[0][i]-pair[1][i])**2 for i in range(3)))
        midpoint = tuple((farthest[0][i]+farthest[1][i])/2 for i in range(3))
        if _inside3(midpoint, ta, strict=True) and _inside3(midpoint, tb, strict=True):
            return "PROPER_INTERSECTION"
    return "UNSHARED_CONTACT"


def _mesh_digest(mesh: TriangleMesh) -> str:
    snapshot = dumps(mesh.to_dict(), sort_keys=True, separators=(",", ":"), allow_nan=False)
    return sha256(snapshot.encode("utf-8")).hexdigest()


def _make_result(mesh: TriangleMesh, *, candidate_count: int, complete: bool,
                 checked: int, limit: int, status: str,
                 intersections: tuple[MeshIntersection, ...] = (),
                 unresolved: tuple[str, ...] = ()) -> MeshIntersectionAnalysis:
    return MeshIntersectionAnalysis(
        solid_id=mesh.solid_id, frame_id=mesh.frame_id, length_unit=mesh.length_unit,
        source_geometry_sha256=mesh.source_geometry_sha256,
        mesh_snapshot_sha256=_mesh_digest(mesh), triangle_count=len(mesh.triangles),
        candidate_pair_count=candidate_count,
        candidate_pair_count_complete=complete, checked_pair_count=checked,
        candidate_pair_limit=limit, status=status, intersections=intersections,
        unresolved_reasons=unresolved,
    )


def analyze_mesh_intersections(
    mesh: TriangleMesh, *, max_candidate_pairs: int = MAX_CANDIDATE_PAIRS,
) -> MeshIntersectionAnalysis:
    """Classify all candidate triangle pairs or fail closed with UNKNOWN.

    Predicates use exact rational arithmetic over the input binary64 values.
    A deterministic x-axis sweep over inclusive triangle AABBs is conservative.
    """
    if not isinstance(mesh, TriangleMesh):
        raise InvalidModelError("analyze_mesh_intersections requires a TriangleMesh")
    if (isinstance(max_candidate_pairs, bool) or not isinstance(max_candidate_pairs, int)
            or not 1 <= max_candidate_pairs <= MAX_CANDIDATE_PAIRS):
        raise InvalidModelError(f"max_candidate_pairs must be from 1 to {MAX_CANDIDATE_PAIRS}")
    validation = validate_triangle_mesh(mesh)
    if not validation.valid:
        raise InvalidModelError("mesh must pass validate_triangle_mesh before intersection analysis")

    bounds = []
    for face_index, face in enumerate(mesh.triangles):
        points = [mesh.vertices[index] for index in face]
        bounds.append((
            min(point.x for point in points), max(point.x for point in points),
            min(point.y for point in points), max(point.y for point in points),
            min(point.z for point in points), max(point.z for point in points),
            face_index,
        ))
    ordered = sorted(bounds, key=lambda item: (item[0], item[6]))
    active: list[tuple[float, float, float, float, float, float, int]] = []
    candidates: list[tuple[int, int]] = []
    for current in ordered:
        active = [item for item in active if item[1] >= current[0]]
        for other in active:
            # The x-interval sweep is deliberately a conservative superset:
            # y/z separation is resolved by exact narrow-phase predicates.
            # Counting every active pair makes the resource limit bound the
            # broad-phase pair enumeration itself.
            pair = tuple(sorted((other[6], current[6])))
            candidates.append(pair)
            if len(candidates) > max_candidate_pairs:
                return _make_result(
                    mesh, candidate_count=max_candidate_pairs+1, complete=False,
                    checked=0, limit=max_candidate_pairs, status="UNKNOWN",
                    unresolved=("RESOURCE_LIMIT_EXCEEDED",),
                )
        active.append(current)
    candidates.sort()
    found: list[MeshIntersection] = []
    for checked, (first, second) in enumerate(candidates, start=1):
        classification = _pair_intersection(mesh, first, second)
        if classification is not None:
            found.append(MeshIntersection(first, second, classification))
    intersections = tuple(sorted(found, key=lambda item: (
        item.triangle_a, item.triangle_b, item.classification
    )))
    return _make_result(
        mesh, candidate_count=len(candidates), complete=True, checked=len(candidates),
        limit=max_candidate_pairs,
        status="INTERSECTIONS_FOUND" if intersections else "NO_INTERSECTIONS_FOUND",
        intersections=intersections,
    )
