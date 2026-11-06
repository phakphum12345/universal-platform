"""Deterministic, dependency-free triangle meshes for supported analytic primitives.

Meshes are emitted in the source solid's local coordinate frame. This module
provides tessellation and topological checks only; it is not a B-rep kernel,
collision engine, manufacturing validator, or physical verification tool.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from json import dumps
from math import acos, ceil, cos, isfinite, pi, sin, sqrt
from typing import Any, ClassVar, Mapping

from .errors import InvalidModelError
from .geometry import Vec3
from .primitive_geometry import BoxSolid, CylinderSolid, ExtrudedProfileSolid
from .quantity import LENGTH, Quantity


def _finite(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(float(value)):
        raise InvalidModelError(f"{label} must be a finite number")
    return float(value)


def _source_digest(solid: BoxSolid | CylinderSolid | ExtrudedProfileSolid) -> str:
    payload = dumps(solid.to_dict(), sort_keys=True, separators=(",", ":"), allow_nan=False)
    return sha256(payload.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class TriangleMesh:
    """Immutable triangle mesh with explicit frame, unit and source provenance."""

    solid_id: str
    frame_id: str
    length_unit: str
    source_kind: str
    source_geometry_sha256: str
    vertices: tuple[Vec3, ...]
    triangles: tuple[tuple[int, int, int], ...]
    chordal_tolerance: float | None = None

    SCHEMA_VERSION: ClassVar[str] = "1.0"

    def __post_init__(self) -> None:
        if not isinstance(self.solid_id, str) or not self.solid_id.strip():
            raise InvalidModelError("mesh solid_id is required")
        if not isinstance(self.frame_id, str) or not self.frame_id.strip():
            raise InvalidModelError("mesh frame_id is required")
        if not isinstance(self.length_unit, str) or not self.length_unit:
            raise InvalidModelError("mesh length_unit is required")
        try:
            if Quantity.of(1.0, self.length_unit).dimension != LENGTH:
                raise InvalidModelError("mesh length_unit must have length dimension")
        except Exception as exc:
            if isinstance(exc, InvalidModelError):
                raise
            raise InvalidModelError(f"unsupported mesh length_unit: {self.length_unit}") from exc
        if not isinstance(self.source_kind, str) or self.source_kind not in {"BOX", "CYLINDER", "EXTRUDED_PROFILE"}:
            raise InvalidModelError("mesh source_kind must be BOX, CYLINDER or EXTRUDED_PROFILE")
        if (not isinstance(self.source_geometry_sha256, str)
                or len(self.source_geometry_sha256) != 64
                or any(ch not in "0123456789abcdef" for ch in self.source_geometry_sha256)):
            raise InvalidModelError("mesh source_geometry_sha256 must be a lowercase SHA-256 digest")
        if not isinstance(self.vertices, tuple) or not self.vertices or any(
            not isinstance(vertex, Vec3) for vertex in self.vertices
        ):
            raise InvalidModelError("mesh vertices must be a non-empty immutable tuple of Vec3")
        if not isinstance(self.triangles, tuple) or not self.triangles:
            raise InvalidModelError("mesh triangles must be a non-empty immutable tuple")
        for face in self.triangles:
            if (not isinstance(face, tuple) or len(face) != 3
                    or any(isinstance(index, bool) or not isinstance(index, int) for index in face)):
                raise InvalidModelError("each mesh triangle must contain three integer indices")
        if self.chordal_tolerance is not None:
            tolerance = _finite(self.chordal_tolerance, "mesh chordal_tolerance")
            if tolerance <= 0:
                raise InvalidModelError("mesh chordal_tolerance must be positive")
            object.__setattr__(self, "chordal_tolerance", tolerance)
        if self.source_kind == "BOX" and self.chordal_tolerance is not None:
            raise InvalidModelError("exact box tessellation must not declare chordal_tolerance")
        if self.source_kind == "CYLINDER" and self.chordal_tolerance is None:
            raise InvalidModelError("cylinder tessellation requires an explicit chordal_tolerance")
        if self.source_kind == "EXTRUDED_PROFILE" and self.chordal_tolerance is not None:
            raise InvalidModelError("straight profile tessellation does not declare chordal_tolerance")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.SCHEMA_VERSION,
            "solid_id": self.solid_id,
            "frame_id": self.frame_id,
            "length_unit": self.length_unit,
            "source_kind": self.source_kind,
            "source_geometry_sha256": self.source_geometry_sha256,
            "chordal_tolerance": self.chordal_tolerance,
            "vertices": [{"x": v.x, "y": v.y, "z": v.z} for v in self.vertices],
            "triangles": [list(face) for face in self.triangles],
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "TriangleMesh":
        expected = {
            "schema_version", "solid_id", "frame_id", "length_unit", "source_kind",
            "source_geometry_sha256", "chordal_tolerance", "vertices", "triangles",
        }
        if not isinstance(value, Mapping) or set(value) != expected:
            raise InvalidModelError("TriangleMesh snapshot has missing or unknown fields")
        if value["schema_version"] != cls.SCHEMA_VERSION:
            raise InvalidModelError("Unsupported TriangleMesh schema_version")
        raw_vertices, raw_triangles = value["vertices"], value["triangles"]
        if not isinstance(raw_vertices, (list, tuple)) or not isinstance(raw_triangles, (list, tuple)):
            raise InvalidModelError("TriangleMesh vertices and triangles must be arrays")
        vertices = []
        for raw in raw_vertices:
            if not isinstance(raw, Mapping) or set(raw) != {"x", "y", "z"}:
                raise InvalidModelError("TriangleMesh vertex requires x, y and z")
            vertices.append(Vec3(_finite(raw["x"], "vertex x"), _finite(raw["y"], "vertex y"), _finite(raw["z"], "vertex z")))
        triangles = []
        for raw in raw_triangles:
            if not isinstance(raw, (list, tuple)) or len(raw) != 3:
                raise InvalidModelError("TriangleMesh face must contain exactly three indices")
            triangles.append(tuple(raw))
        return cls(
            value["solid_id"], value["frame_id"], value["length_unit"], value["source_kind"],
            value["source_geometry_sha256"], tuple(vertices), tuple(triangles), value["chordal_tolerance"],
        )


@dataclass(frozen=True, slots=True)
class MeshValidationResult:
    valid: bool
    watertight: bool
    consistently_oriented: bool
    vertex_count: int
    triangle_count: int
    boundary_edge_count: int
    nonmanifold_edge_count: int
    winding_conflict_count: int
    degenerate_triangle_count: int
    signed_volume: float
    surface_area: float
    issues: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "valid": self.valid,
            "watertight": self.watertight,
            "consistently_oriented": self.consistently_oriented,
            "vertex_count": self.vertex_count,
            "triangle_count": self.triangle_count,
            "boundary_edge_count": self.boundary_edge_count,
            "nonmanifold_edge_count": self.nonmanifold_edge_count,
            "winding_conflict_count": self.winding_conflict_count,
            "degenerate_triangle_count": self.degenerate_triangle_count,
            "signed_volume": self.signed_volume,
            "surface_area": self.surface_area,
            "issues": list(self.issues),
        }


def validate_triangle_mesh(mesh: TriangleMesh) -> MeshValidationResult:
    """Check triangle indices, degeneracy, closed two-manifold edges and winding."""
    if not isinstance(mesh, TriangleMesh):
        raise InvalidModelError("validate_triangle_mesh requires a TriangleMesh")
    count = len(mesh.vertices)
    edge_uses: dict[tuple[int, int], list[int]] = {}
    issues: list[str] = []
    degenerate = 0
    area = 0.0
    volume = 0.0
    xs = [v.x for v in mesh.vertices]
    ys = [v.y for v in mesh.vertices]
    zs = [v.z for v in mesh.vertices]
    scale = max(max(xs)-min(xs), max(ys)-min(ys), max(zs)-min(zs), 1e-300)
    origin = mesh.vertices[0]
    for face_index, face in enumerate(mesh.triangles):
        if any(index < 0 or index >= count for index in face):
            issues.append(f"FACE_INDEX_OUT_OF_RANGE:{face_index}")
            continue
        a, b, c = face
        if len({a, b, c}) != 3:
            degenerate += 1
            issues.append(f"DEGENERATE_TRIANGLE:{face_index}")
            continue
        va, vb, vc = mesh.vertices[a], mesh.vertices[b], mesh.vertices[c]
        ab = (vb.x-va.x, vb.y-va.y, vb.z-va.z)
        ac = (vc.x-va.x, vc.y-va.y, vc.z-va.z)
        cross = (
            ab[1]*ac[2]-ab[2]*ac[1],
            ab[2]*ac[0]-ab[0]*ac[2],
            ab[0]*ac[1]-ab[1]*ac[0],
        )
        twice_area = sqrt(sum(value*value for value in cross))
        if twice_area <= 1e-14 * scale * scale:
            degenerate += 1
            issues.append(f"DEGENERATE_TRIANGLE:{face_index}")
        else:
            area += 0.5 * twice_area
            pa = (va.x-origin.x, va.y-origin.y, va.z-origin.z)
            pb = (vb.x-origin.x, vb.y-origin.y, vb.z-origin.z)
            pc = (vc.x-origin.x, vc.y-origin.y, vc.z-origin.z)
            cross_bc = (
                pb[1]*pc[2]-pb[2]*pc[1],
                pb[2]*pc[0]-pb[0]*pc[2],
                pb[0]*pc[1]-pb[1]*pc[0],
            )
            volume += sum(pa[i]*cross_bc[i] for i in range(3)) / 6.0
        for start, end in ((a, b), (b, c), (c, a)):
            key = (min(start, end), max(start, end))
            edge_uses.setdefault(key, []).append(1 if start < end else -1)
    boundary = sum(1 for uses in edge_uses.values() if len(uses) == 1)
    nonmanifold = sum(1 for uses in edge_uses.values() if len(uses) > 2)
    winding = sum(1 for uses in edge_uses.values() if len(uses) == 2 and sum(uses) != 0)
    if boundary:
        issues.append("BOUNDARY_EDGES_PRESENT")
    if nonmanifold:
        issues.append("NONMANIFOLD_EDGES_PRESENT")
    if winding:
        issues.append("INCONSISTENT_EDGE_WINDING")
    if volume <= 1e-14 * scale**3:
        issues.append("SIGNED_VOLUME_NOT_POSITIVE")
    watertight = boundary == 0 and nonmanifold == 0
    oriented = winding == 0 and volume > 1e-14 * scale**3
    valid = not issues
    return MeshValidationResult(
        valid, watertight, oriented, count, len(mesh.triangles), boundary,
        nonmanifold, winding, degenerate, volume, area, tuple(issues),
    )


def tessellate_box(solid: BoxSolid) -> TriangleMesh:
    """Return an exact, outward-oriented 12-triangle surface for a box."""
    if not isinstance(solid, BoxSolid):
        raise InvalidModelError("tessellate_box requires a BoxSolid")
    x, y, z = solid.dimensions.x, solid.dimensions.y, solid.dimensions.z
    vertices = (
        Vec3(0, 0, 0), Vec3(x, 0, 0), Vec3(x, y, 0), Vec3(0, y, 0),
        Vec3(0, 0, z), Vec3(x, 0, z), Vec3(x, y, z), Vec3(0, y, z),
    )
    quads = (
        (0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4),
        (3, 7, 6, 2), (0, 4, 7, 3), (1, 2, 6, 5),
    )
    faces = tuple(face for quad in quads for face in (
        (quad[0], quad[1], quad[2]), (quad[0], quad[2], quad[3])
    ))
    return TriangleMesh(
        solid.solid_id, solid.frame_id, solid.length_unit, "BOX", _source_digest(solid),
        vertices, faces,
    )


def tessellate_cylinder(solid: CylinderSolid, chordal_tolerance: float) -> TriangleMesh:
    """Tessellate a local +Z cylinder using an explicit maximum radial chord error."""
    if not isinstance(solid, CylinderSolid):
        raise InvalidModelError("tessellate_cylinder requires a CylinderSolid")
    tolerance = _finite(chordal_tolerance, "chordal_tolerance")
    if tolerance <= 0:
        raise InvalidModelError("chordal_tolerance must be positive")
    ratio = min(tolerance / solid.radius, 1.0)
    half_angle = acos(1.0 - ratio)
    if half_angle <= 0.0:
        raise InvalidModelError("chordal_tolerance is below floating-point resolution for this radius")
    segments = max(3, ceil(pi / half_angle))
    if segments > 100000:
        raise InvalidModelError("requested cylinder chordal_tolerance exceeds the 100000-segment resource limit")
    bottom = tuple(Vec3(solid.radius*cos(2*pi*i/segments), solid.radius*sin(2*pi*i/segments), 0.0) for i in range(segments))
    top = tuple(Vec3(point.x, point.y, solid.height) for point in bottom)
    vertices = (Vec3(0.0, 0.0, 0.0), Vec3(0.0, 0.0, solid.height)) + bottom + top
    bottom_center, top_center = 0, 1
    lower_start, upper_start = 2, 2+segments
    faces: list[tuple[int, int, int]] = []
    for i in range(segments):
        j = (i+1) % segments
        li, lj = lower_start+i, lower_start+j
        ui, uj = upper_start+i, upper_start+j
        faces.append((bottom_center, lj, li))
        faces.append((top_center, ui, uj))
        faces.append((li, lj, uj))
        faces.append((li, uj, ui))
    return TriangleMesh(
        solid.solid_id, solid.frame_id, solid.length_unit, "CYLINDER", _source_digest(solid),
        vertices, tuple(faces), tolerance,
    )

def _profile_cross(a: Any, b: Any, c: Any) -> float:
    return (b.x-a.x)*(c.y-a.y) - (b.y-a.y)*(c.x-a.x)


def _profile_signed_area(points: tuple[Any, ...]) -> float:
    origin = points[0]
    return sum(
        (points[i].x-origin.x)*(points[(i+1) % len(points)].y-origin.y)
        - (points[(i+1) % len(points)].x-origin.x)*(points[i].y-origin.y)
        for i in range(1, len(points)-1)
    ) / 2.0


def _inside_or_on_triangle(point: Any, a: Any, b: Any, c: Any, epsilon: float) -> bool:
    return (
        _profile_cross(a, b, point) >= -epsilon
        and _profile_cross(b, c, point) >= -epsilon
        and _profile_cross(c, a, point) >= -epsilon
    )


def _triangulate_simple_profile(points: tuple[Any, ...]) -> tuple[tuple[int, int, int], ...]:
    """Deterministic ear clipping for validated straight-edged simple loops."""
    if len(points) < 3:
        raise InvalidModelError("profile triangulation requires at least three vertices")
    scale = max(
        max(point.x for point in points)-min(point.x for point in points),
        max(point.y for point in points)-min(point.y for point in points),
        1e-300,
    )
    epsilon = 1e-14 * scale * scale
    area = _profile_signed_area(points)
    if abs(area) <= epsilon:
        raise InvalidModelError("profile triangulation rejects numerically degenerate area")
    remaining = list(range(len(points)))
    if area < 0:
        remaining.reverse()
    result: list[tuple[int, int, int]] = []
    while len(remaining) > 3:
        ear_found = False
        for position, current in enumerate(remaining):
            previous = remaining[position-1]
            following = remaining[(position+1) % len(remaining)]
            a, b, c = points[previous], points[current], points[following]
            if _profile_cross(a, b, c) <= epsilon:
                continue
            if any(
                _inside_or_on_triangle(points[index], a, b, c, epsilon)
                for index in remaining if index not in {previous, current, following}
            ):
                continue
            result.append((previous, current, following))
            remaining.pop(position)
            ear_found = True
            break
        if not ear_found:
            raise InvalidModelError("profile triangulation could not find a non-degenerate ear")
    a, b, c = (points[index] for index in remaining)
    if _profile_cross(a, b, c) <= epsilon:
        raise InvalidModelError("profile triangulation ended with a degenerate final triangle")
    result.append(tuple(remaining))
    return tuple(result)


def tessellate_extruded_profile(solid: ExtrudedProfileSolid) -> TriangleMesh:
    """Tessellate a straight-edged, hole-free simple extrusion by deterministic ear clipping."""
    if not isinstance(solid, ExtrudedProfileSolid):
        raise InvalidModelError("tessellate_extruded_profile requires an ExtrudedProfileSolid")
    if solid.holes:
        raise InvalidModelError("profile mesh v1.0 does not yet support through-hole loops")
    if solid.arc_sweeps_rad:
        raise InvalidModelError("profile mesh v1.0 supports straight edges only")
    points = solid.profile
    cap_triangles = _triangulate_simple_profile(points)
    count = len(points)
    lower = tuple(Vec3(point.x, point.y, 0.0) for point in points)
    upper = tuple(Vec3(point.x, point.y, solid.height) for point in points)
    vertices = lower + upper
    faces: list[tuple[int, int, int]] = []
    for a, b, c in cap_triangles:
        faces.append((c, b, a))
        faces.append((a+count, b+count, c+count))
    boundary_indices = list(range(count))
    if _profile_signed_area(points) < 0:
        boundary_indices.reverse()
    for position, i in enumerate(boundary_indices):
        j = boundary_indices[(position+1) % count]
        faces.append((i, j, j+count))
        faces.append((i, j+count, i+count))
    return TriangleMesh(
        solid.solid_id, solid.frame_id, solid.length_unit, "EXTRUDED_PROFILE",
        _source_digest(solid), vertices, tuple(faces),
    )
