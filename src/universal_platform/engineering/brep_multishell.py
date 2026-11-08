"""Bounded multi-shell faceted solids with explicit cavity semantics.

Each component remains an independently validated v2 single-shell B-rep.
The aggregate applies subtractive orientation to cavity components and fails
closed when containment, shell separation, or mesh intersection is unresolved.
"""
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from hashlib import sha256
import json
import re
from typing import Any, ClassVar, Mapping

from .brep import BRepSolid, triangle_mesh_from_brep, validate_brep_solid
from .errors import InvalidModelError
from .geometry import Vec3
from .mesh import TriangleMesh, validate_triangle_mesh
from .mesh_intersection import analyze_mesh_intersections

_ID = re.compile(r"^[a-z0-9]+(?:[._/-][a-z0-9]+)*$")
_DIRECTIONS = (
    (Fraction(1), Fraction(1, 17), Fraction(1, 31)),
    (Fraction(1, 19), Fraction(1), Fraction(1, 37)),
    (Fraction(1, 41), Fraction(1, 43), Fraction(1)),
)


@dataclass(frozen=True, slots=True)
class BRepMultiShellValidationResult:
    valid: bool
    shell_count: int
    cavity_count: int
    net_signed_volume: float
    intersection_status: str
    issues: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "valid": self.valid,
            "shell_count": self.shell_count,
            "cavity_count": self.cavity_count,
            "net_signed_volume": self.net_signed_volume,
            "intersection_status": self.intersection_status,
            "issues": list(self.issues),
        }


def _q(value: float) -> Fraction:
    return Fraction.from_float(float(value))


def _sub(a: tuple[Fraction, Fraction, Fraction],
         b: tuple[Fraction, Fraction, Fraction]) -> tuple[Fraction, Fraction, Fraction]:
    return tuple(a[i] - b[i] for i in range(3))


def _cross(a: tuple[Fraction, Fraction, Fraction],
           b: tuple[Fraction, Fraction, Fraction]) -> tuple[Fraction, Fraction, Fraction]:
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def _dot(a: tuple[Fraction, Fraction, Fraction],
         b: tuple[Fraction, Fraction, Fraction]) -> Fraction:
    return sum(a[i] * b[i] for i in range(3))


def _point_inside_mesh(point: Vec3, mesh: TriangleMesh) -> bool | None:
    """Exact-rational odd/even ray test; None means all deterministic rays were ambiguous."""
    origin = (_q(point.x), _q(point.y), _q(point.z))
    triangles = tuple(
        tuple((_q(mesh.vertices[index].x), _q(mesh.vertices[index].y), _q(mesh.vertices[index].z))
              for index in face)
        for face in mesh.triangles
    )
    for direction in _DIRECTIONS:
        crossings = 0
        ambiguous = False
        for a, b, c in triangles:
            edge1, edge2 = _sub(b, a), _sub(c, a)
            h = _cross(direction, edge2)
            determinant = _dot(edge1, h)
            if determinant == 0:
                continue
            inverse = Fraction(1, 1) / determinant
            offset = _sub(origin, a)
            u = inverse * _dot(offset, h)
            qvec = _cross(offset, edge1)
            v = inverse * _dot(direction, qvec)
            distance = inverse * _dot(edge2, qvec)
            if distance == 0:
                if u >= 0 and v >= 0 and u + v <= 1:
                    ambiguous = True
                    break
                continue
            if distance > 0 and u >= 0 and v >= 0 and u + v <= 1:
                if u == 0 or v == 0 or u + v == 1:
                    ambiguous = True
                    break
                crossings += 1
        if not ambiguous:
            return crossings % 2 == 1
    return None


def _combined_mesh(solid_id: str, outer: BRepSolid,
                   cavities: tuple[BRepSolid, ...]) -> TriangleMesh:
    components = (outer, *cavities)
    vertices: list[Vec3] = []
    triangles: list[tuple[int, int, int]] = []
    for component_index, component in enumerate(components):
        mesh = triangle_mesh_from_brep(component)
        offset = len(vertices)
        vertices.extend(mesh.vertices)
        if component_index == 0:
            triangles.extend(tuple(offset + index for index in face) for face in mesh.triangles)
        else:
            triangles.extend((offset + face[0], offset + face[2], offset + face[1])
                             for face in mesh.triangles)
    snapshot = {
        "solid_id": solid_id,
        "outer": outer.to_dict(),
        "cavities": [item.to_dict() for item in cavities],
    }
    digest = sha256(json.dumps(
        snapshot, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")).hexdigest()
    return TriangleMesh(
        solid_id, outer.frame_id, outer.length_unit, "IMPORTED_BREP",
        digest, tuple(vertices), tuple(triangles),
    )


def _validate_multishell(solid_id: str, outer: BRepSolid,
                         cavities: tuple[BRepSolid, ...]) -> BRepMultiShellValidationResult:
    issues: list[str] = []
    components = (outer, *cavities)
    ids = [item.solid_id for item in components]
    if len(ids) != len(set(ids)):
        issues.append("component solid IDs must be unique")
    for index, component in enumerate(components):
        result = validate_brep_solid(component)
        if not result.valid:
            issues.append(f"component {index} is not a valid single-shell B-rep")
        if component.frame_id != outer.frame_id or component.length_unit != outer.length_unit:
            issues.append("all shell components must use the same frame and length unit")
    if issues:
        return BRepMultiShellValidationResult(
            False, len(components), len(cavities), 0.0, "NOT_RUN", tuple(issues)
        )

    try:
        meshes = tuple(triangle_mesh_from_brep(item) for item in components)
        combined = _combined_mesh(solid_id, outer, cavities)
        mesh_validation = validate_triangle_mesh(combined)
    except InvalidModelError as exc:
        return BRepMultiShellValidationResult(
            False, len(components), len(cavities), 0.0, "UNKNOWN",
            (f"combined shell validation failed closed: {exc}",),
        )
    if not (mesh_validation.valid and mesh_validation.watertight
            and mesh_validation.consistently_oriented):
        issues.append("combined outer/cavity boundary is not a valid oriented watertight mesh")

    intersection = analyze_mesh_intersections(combined)
    if intersection.status != "NO_INTERSECTIONS_FOUND":
        issues.append(f"shell boundaries are not proven disjoint: {intersection.status}")
    outer_mesh = meshes[0]
    for cavity_index, cavity_mesh in enumerate(meshes[1:], start=1):
        for vertex in cavity_mesh.vertices:
            contained = _point_inside_mesh(vertex, outer_mesh)
            if contained is not True:
                state = "outside or on" if contained is False else "unresolved against"
                issues.append(f"cavity shell {cavity_index} has a vertex {state} the outer shell")
                break
    for first_index in range(len(meshes) - 1):
        for second_index in range(first_index + 1, len(meshes) - 1):
            first_point = meshes[first_index + 1].vertices[0]
            second_point = meshes[second_index + 1].vertices[0]
            first_in_second = _point_inside_mesh(first_point, meshes[second_index + 1])
            second_in_first = _point_inside_mesh(second_point, meshes[first_index + 1])
            if first_in_second is not False or second_in_first is not False:
                issues.append("cavity shells must be pairwise disjoint and non-nested")
    return BRepMultiShellValidationResult(
        not issues, len(components), len(cavities), mesh_validation.signed_volume,
        intersection.status, tuple(issues),
    )


@dataclass(frozen=True, slots=True)
class BRepMultiShellSolid:
    """One material region represented by one outer shell and zero or more cavities."""

    solid_id: str
    outer_shell: BRepSolid
    cavity_shells: tuple[BRepSolid, ...] = ()

    SCHEMA_VERSION: ClassVar[str] = "1.0"
    PROFILE: ClassVar[str] = "FACETED_MULTI_SHELL_SOLID_V1"

    def __post_init__(self) -> None:
        if not isinstance(self.solid_id, str) or not _ID.fullmatch(self.solid_id):
            raise InvalidModelError("multi-shell solid_id must be a stable lowercase identifier")
        if not isinstance(self.outer_shell, BRepSolid):
            raise InvalidModelError("outer_shell must be a BRepSolid")
        if not isinstance(self.cavity_shells, tuple) or any(
            not isinstance(item, BRepSolid) for item in self.cavity_shells
        ):
            raise InvalidModelError("cavity_shells must be an immutable tuple of BRepSolid components")
        result = _validate_multishell(self.solid_id, self.outer_shell, self.cavity_shells)
        if not result.valid:
            raise InvalidModelError("multi-shell BRep is invalid: " + "; ".join(result.issues))

    @property
    def frame_id(self) -> str:
        return self.outer_shell.frame_id

    @property
    def length_unit(self) -> str:
        return self.outer_shell.length_unit

    @property
    def source_geometry_sha256(self) -> str:
        payload = {
            "solid_id": self.solid_id,
            "outer": self.outer_shell.to_dict(),
            "cavities": [item.to_dict() for item in self.cavity_shells],
        }
        return sha256(json.dumps(
            payload, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode("utf-8")).hexdigest()

    def to_mesh(self) -> TriangleMesh:
        return _combined_mesh(self.solid_id, self.outer_shell, self.cavity_shells)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.SCHEMA_VERSION,
            "profile": self.PROFILE,
            "solid_id": self.solid_id,
            "frame_id": self.frame_id,
            "length_unit": self.length_unit,
            "source_geometry_sha256": self.source_geometry_sha256,
            "outer_shell": self.outer_shell.to_dict(),
            "cavity_shells": [item.to_dict() for item in self.cavity_shells],
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "BRepMultiShellSolid":
        required = {
            "schema_version", "profile", "solid_id", "frame_id", "length_unit",
            "source_geometry_sha256", "outer_shell", "cavity_shells",
        }
        if not isinstance(value, Mapping) or set(value) != required:
            raise InvalidModelError("BRepMultiShellSolid snapshot has missing or unknown fields")
        if value["schema_version"] != cls.SCHEMA_VERSION or value["profile"] != cls.PROFILE:
            raise InvalidModelError("unsupported BRepMultiShellSolid schema or profile")
        if not isinstance(value["cavity_shells"], (list, tuple)):
            raise InvalidModelError("cavity_shells must be an array")
        outer = BRepSolid.from_dict(value["outer_shell"])
        cavities = tuple(BRepSolid.from_dict(item) for item in value["cavity_shells"])
        result = cls(value["solid_id"], outer, cavities)
        if (value["frame_id"] != result.frame_id or value["length_unit"] != result.length_unit
                or value["source_geometry_sha256"] != result.source_geometry_sha256):
            raise InvalidModelError("multi-shell snapshot metadata or digest does not match its components")
        return result


def validate_brep_multishell_solid(solid: BRepMultiShellSolid) -> BRepMultiShellValidationResult:
    if not isinstance(solid, BRepMultiShellSolid):
        raise InvalidModelError("validate_brep_multishell_solid requires a BRepMultiShellSolid")
    return _validate_multishell(solid.solid_id, solid.outer_shell, solid.cavity_shells)
