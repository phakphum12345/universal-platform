"""Bounded faceted-B-rep topology v1.0 for closed triangular planar shells.

This is a topology contract and mesh bridge, not a general curved-surface B-rep
kernel or 3D Boolean engine. Exact predicates operate on represented binary64
vertex coordinates via their exact rational values.
"""
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from hashlib import sha256
import re
from typing import ClassVar, Mapping

from .errors import InvalidModelError
from .geometry import Vec3
from .mesh import TriangleMesh, validate_triangle_mesh

_ID = re.compile(r"^[a-z0-9]+(?:[._/-][a-z0-9]+)*$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True, slots=True)
class BRepVertex:
    vertex_id: str
    position: Vec3

    def __post_init__(self) -> None:
        if not isinstance(self.vertex_id, str) or not _ID.fullmatch(self.vertex_id):
            raise InvalidModelError("BRep vertex_id must be a stable lowercase identifier")
        if not isinstance(self.position, Vec3):
            raise InvalidModelError("BRep vertex position must be Vec3")


@dataclass(frozen=True, slots=True)
class BRepEdge:
    edge_id: str
    start_vertex_id: str
    end_vertex_id: str

    def __post_init__(self) -> None:
        if not isinstance(self.edge_id, str) or not _ID.fullmatch(self.edge_id):
            raise InvalidModelError("BRep edge_id must be a stable lowercase identifier")
        if any(not isinstance(value, str) or not _ID.fullmatch(value)
               for value in (self.start_vertex_id, self.end_vertex_id)):
            raise InvalidModelError("BRep edge endpoints must be stable vertex identifiers")
        if self.start_vertex_id == self.end_vertex_id:
            raise InvalidModelError("BRep edge endpoints must be distinct")


@dataclass(frozen=True, slots=True)
class BRepEdgeUse:
    edge_id: str
    forward: bool

    def __post_init__(self) -> None:
        if not isinstance(self.edge_id, str) or not _ID.fullmatch(self.edge_id):
            raise InvalidModelError("BRep edge use requires a stable edge identifier")
        if not isinstance(self.forward, bool):
            raise InvalidModelError("BRep edge-use forward flag must be boolean")


@dataclass(frozen=True, slots=True)
class BRepLoop:
    loop_id: str
    edge_uses: tuple[BRepEdgeUse, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.loop_id, str) or not _ID.fullmatch(self.loop_id):
            raise InvalidModelError("BRep loop_id must be a stable lowercase identifier")
        if not isinstance(self.edge_uses, tuple) or len(self.edge_uses) != 3:
            raise InvalidModelError("faceted BRep v1.0 loops require exactly three edge uses")
        if any(not isinstance(item, BRepEdgeUse) for item in self.edge_uses):
            raise InvalidModelError("BRep loop edge_uses must contain BRepEdgeUse records")
        if len({item.edge_id for item in self.edge_uses}) != 3:
            raise InvalidModelError("a triangular BRep loop cannot repeat an edge")


@dataclass(frozen=True, slots=True)
class BRepFace:
    face_id: str
    outer_loop_id: str

    def __post_init__(self) -> None:
        if not isinstance(self.face_id, str) or not _ID.fullmatch(self.face_id):
            raise InvalidModelError("BRep face_id must be a stable lowercase identifier")
        if not isinstance(self.outer_loop_id, str) or not _ID.fullmatch(self.outer_loop_id):
            raise InvalidModelError("BRep face requires an outer loop identifier")


@dataclass(frozen=True, slots=True)
class BRepShell:
    shell_id: str
    face_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.shell_id, str) or not _ID.fullmatch(self.shell_id):
            raise InvalidModelError("BRep shell_id must be a stable lowercase identifier")
        if not isinstance(self.face_ids, tuple) or not self.face_ids:
            raise InvalidModelError("BRep shell requires an immutable non-empty face list")
        if any(not isinstance(item, str) or not _ID.fullmatch(item) for item in self.face_ids):
            raise InvalidModelError("BRep shell face IDs must be stable identifiers")
        if len(set(self.face_ids)) != len(self.face_ids):
            raise InvalidModelError("BRep shell cannot repeat a face")


@dataclass(frozen=True, slots=True)
class BRepValidationResult:
    valid: bool
    closed: bool
    manifold: bool
    consistently_oriented: bool
    connected: bool
    vertex_count: int
    edge_count: int
    face_count: int
    euler_characteristic: int
    genus: int | None
    signed_volume: float
    issues: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "valid": self.valid,
            "closed": self.closed,
            "manifold": self.manifold,
            "consistently_oriented": self.consistently_oriented,
            "connected": self.connected,
            "vertex_count": self.vertex_count,
            "edge_count": self.edge_count,
            "face_count": self.face_count,
            "euler_characteristic": self.euler_characteristic,
            "genus": self.genus,
            "signed_volume": self.signed_volume,
            "issues": list(self.issues),
        }


@dataclass(frozen=True, slots=True)
class BRepSolid:
    solid_id: str
    frame_id: str
    length_unit: str
    source_geometry_sha256: str
    vertices: tuple[BRepVertex, ...]
    edges: tuple[BRepEdge, ...]
    loops: tuple[BRepLoop, ...]
    faces: tuple[BRepFace, ...]
    shell: BRepShell

    SCHEMA_VERSION: ClassVar[str] = "1.0"
    PROFILE: ClassVar[str] = "FACETED_TRIANGULAR_PLANAR_SHELL_V1"

    def __post_init__(self) -> None:
        if not isinstance(self.solid_id, str) or not _ID.fullmatch(self.solid_id):
            raise InvalidModelError("BRep solid_id must be a stable lowercase identifier")
        if not isinstance(self.frame_id, str) or not self.frame_id.strip():
            raise InvalidModelError("BRep frame_id must be non-empty")
        if not isinstance(self.length_unit, str) or not self.length_unit.strip():
            raise InvalidModelError("BRep length_unit must be non-empty")
        if not isinstance(self.source_geometry_sha256, str) or not _SHA256.fullmatch(self.source_geometry_sha256):
            raise InvalidModelError("BRep source_geometry_sha256 must be lowercase SHA-256")
        for name, values, kind in (
            ("vertices", self.vertices, BRepVertex),
            ("edges", self.edges, BRepEdge),
            ("loops", self.loops, BRepLoop),
            ("faces", self.faces, BRepFace),
        ):
            if not isinstance(values, tuple) or not values or any(not isinstance(item, kind) for item in values):
                raise InvalidModelError(f"BRep {name} must be an immutable non-empty tuple of {kind.__name__}")
            ids = [item.vertex_id if name == "vertices" else
                   item.edge_id if name == "edges" else
                   item.loop_id if name == "loops" else item.face_id for item in values]
            if len(ids) != len(set(ids)):
                raise InvalidModelError(f"BRep {name} identifiers must be unique")
        if not isinstance(self.shell, BRepShell):
            raise InvalidModelError("BRep shell must be a BRepShell")
        result = _validate_brep_topology(self)
        if not result.valid:
            raise InvalidModelError("BRep topology is invalid: " + "; ".join(result.issues))

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.SCHEMA_VERSION,
            "profile": self.PROFILE,
            "solid_id": self.solid_id,
            "frame_id": self.frame_id,
            "length_unit": self.length_unit,
            "source_geometry_sha256": self.source_geometry_sha256,
            "vertices": [
                {"vertex_id": item.vertex_id, "x": item.position.x, "y": item.position.y, "z": item.position.z}
                for item in self.vertices
            ],
            "edges": [
                {"edge_id": item.edge_id, "start_vertex_id": item.start_vertex_id, "end_vertex_id": item.end_vertex_id}
                for item in self.edges
            ],
            "loops": [
                {"loop_id": item.loop_id, "edge_uses": [
                    {"edge_id": use.edge_id, "forward": use.forward} for use in item.edge_uses
                ]} for item in self.loops
            ],
            "faces": [
                {"face_id": item.face_id, "outer_loop_id": item.outer_loop_id} for item in self.faces
            ],
            "shell": {"shell_id": self.shell.shell_id, "face_ids": list(self.shell.face_ids)},
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, object]) -> "BRepSolid":
        required = {
            "schema_version", "profile", "solid_id", "frame_id", "length_unit",
            "source_geometry_sha256", "vertices", "edges", "loops", "faces", "shell",
        }
        if not isinstance(value, Mapping) or set(value) != required:
            raise InvalidModelError("BRepSolid snapshot has missing or unknown fields")
        if value["schema_version"] != cls.SCHEMA_VERSION or value["profile"] != cls.PROFILE:
            raise InvalidModelError("unsupported BRepSolid schema or profile")
        for name in ("vertices", "edges", "loops", "faces"):
            if not isinstance(value[name], (list, tuple)):
                raise InvalidModelError(f"BRep {name} must be an array")
        vertices = []
        for raw in value["vertices"]:
            if not isinstance(raw, Mapping) or set(raw) != {"vertex_id", "x", "y", "z"}:
                raise InvalidModelError("BRep vertex requires vertex_id, x, y and z")
            vertices.append(BRepVertex(raw["vertex_id"], Vec3(raw["x"], raw["y"], raw["z"])))
        edges = []
        for raw in value["edges"]:
            if not isinstance(raw, Mapping) or set(raw) != {"edge_id", "start_vertex_id", "end_vertex_id"}:
                raise InvalidModelError("BRep edge has missing or unknown fields")
            edges.append(BRepEdge(raw["edge_id"], raw["start_vertex_id"], raw["end_vertex_id"]))
        loops = []
        for raw in value["loops"]:
            if not isinstance(raw, Mapping) or set(raw) != {"loop_id", "edge_uses"} or not isinstance(raw["edge_uses"], (list, tuple)):
                raise InvalidModelError("BRep loop has missing or invalid fields")
            uses = []
            for use in raw["edge_uses"]:
                if not isinstance(use, Mapping) or set(use) != {"edge_id", "forward"}:
                    raise InvalidModelError("BRep edge use requires edge_id and forward")
                uses.append(BRepEdgeUse(use["edge_id"], use["forward"]))
            loops.append(BRepLoop(raw["loop_id"], tuple(uses)))
        faces = []
        for raw in value["faces"]:
            if not isinstance(raw, Mapping) or set(raw) != {"face_id", "outer_loop_id"}:
                raise InvalidModelError("BRep face has missing or unknown fields")
            faces.append(BRepFace(raw["face_id"], raw["outer_loop_id"]))
        raw_shell = value["shell"]
        if not isinstance(raw_shell, Mapping) or set(raw_shell) != {"shell_id", "face_ids"} or not isinstance(raw_shell["face_ids"], (list, tuple)):
            raise InvalidModelError("BRep shell has missing or invalid fields")
        shell = BRepShell(raw_shell["shell_id"], tuple(raw_shell["face_ids"]))
        return cls(
            value["solid_id"], value["frame_id"], value["length_unit"], value["source_geometry_sha256"],
            tuple(vertices), tuple(edges), tuple(loops), tuple(faces), shell,
        )


def _q(value: float) -> Fraction:
    return Fraction.from_float(float(value))


def _cross(a: tuple[Fraction, Fraction, Fraction],
           b: tuple[Fraction, Fraction, Fraction]) -> tuple[Fraction, Fraction, Fraction]:
    return (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])


def _dot(a: tuple[Fraction, Fraction, Fraction],
         b: tuple[Fraction, Fraction, Fraction]) -> Fraction:
    return a[0]*b[0] + a[1]*b[1] + a[2]*b[2]


def _validate_brep_topology(solid: BRepSolid) -> BRepValidationResult:
    issues: list[str] = []
    vertices = {item.vertex_id: item.position for item in solid.vertices}
    edges = {item.edge_id: item for item in solid.edges}
    loops = {item.loop_id: item for item in solid.loops}
    faces = {item.face_id: item for item in solid.faces}
    if set(solid.shell.face_ids) != set(faces) or len(solid.shell.face_ids) != len(faces):
        issues.append("shell face list must reference every face exactly once")
    edge_incidence: dict[str, list[bool]] = {key: [] for key in edges}
    face_adjacency: dict[str, set[str]] = {key: set() for key in faces}
    loop_owner: dict[str, str] = {}
    used_vertices: set[str] = set()
    signed_volume = Fraction(0, 1)

    for face in solid.faces:
        loop = loops.get(face.outer_loop_id)
        if loop is None:
            issues.append(f"face {face.face_id} references a missing outer loop")
            continue
        if loop.loop_id in loop_owner:
            issues.append(f"loop {loop.loop_id} is owned by more than one face")
        loop_owner[loop.loop_id] = face.face_id
        directed: list[tuple[str, str]] = []
        for use in loop.edge_uses:
            edge = edges.get(use.edge_id)
            if edge is None:
                issues.append(f"loop {loop.loop_id} references a missing edge")
                continue
            edge_incidence[use.edge_id].append(use.forward)
            start = edge.start_vertex_id if use.forward else edge.end_vertex_id
            end = edge.end_vertex_id if use.forward else edge.start_vertex_id
            if start not in vertices or end not in vertices:
                issues.append(f"edge {edge.edge_id} references a missing vertex")
                continue
            directed.append((start, end))
            used_vertices.update((start, end))
        if len(directed) == 3 and any(directed[index][1] != directed[(index+1) % 3][0] for index in range(3)):
            issues.append(f"loop {loop.loop_id} is not a closed connected edge cycle")
        if len(directed) == 3:
            p = [vertices[item[0]] for item in directed]
            a = tuple(_q(v) for v in (p[1].x-p[0].x, p[1].y-p[0].y, p[1].z-p[0].z))
            b = tuple(_q(v) for v in (p[2].x-p[0].x, p[2].y-p[0].y, p[2].z-p[0].z))
            normal = _cross(a, b)
            if normal == (0, 0, 0):
                issues.append(f"face {face.face_id} is geometrically degenerate")
            signed_volume += _dot(
                tuple(_q(v) for v in (p[0].x, p[0].y, p[0].z)),
                _cross(tuple(_q(v) for v in (p[1].x, p[1].y, p[1].z)),
                       tuple(_q(v) for v in (p[2].x, p[2].y, p[2].z))),
            ) / 6

    for loop in solid.loops:
        if loop.loop_id not in loop_owner:
            issues.append(f"loop {loop.loop_id} is not owned by a face")
    if used_vertices != set(vertices):
        issues.append("every BRep vertex must be used by a face")
    closed = True
    manifold = True
    oriented = True
    for edge_id, directions in edge_incidence.items():
        if len(directions) != 2:
            closed = False
            manifold = False
            issues.append(f"edge {edge_id} must be used by exactly two faces")
        elif directions[0] == directions[1]:
            oriented = False
            issues.append(f"edge {edge_id} uses must have opposite directions")

    edge_to_faces: dict[str, list[str]] = {}
    for face in solid.faces:
        loop = loops.get(face.outer_loop_id)
        if loop:
            for use in loop.edge_uses:
                edge_to_faces.setdefault(use.edge_id, []).append(face.face_id)
    for face_ids in edge_to_faces.values():
        if len(face_ids) == 2:
            face_adjacency[face_ids[0]].add(face_ids[1])
            face_adjacency[face_ids[1]].add(face_ids[0])
    connected = False
    if faces:
        visited = {next(iter(faces))}
        pending = list(visited)
        while pending:
            current = pending.pop()
            for neighbor in face_adjacency[current] - visited:
                visited.add(neighbor)
                pending.append(neighbor)
        connected = len(visited) == len(faces)
    if not connected:
        issues.append("BRep shell must be one connected face component")

    euler = len(vertices) - len(edges) + len(faces)
    genus = (2 - euler) // 2 if euler <= 2 and (2 - euler) % 2 == 0 else None
    if genus is None:
        issues.append("shell Euler characteristic is not valid for a connected orientable closed surface")
    if signed_volume <= 0:
        issues.append("oriented shell must enclose positive signed volume")

    valid = not issues and closed and manifold and oriented and connected
    return BRepValidationResult(
        valid, closed, manifold, oriented, connected,
        len(vertices), len(edges), len(faces), euler, genus, float(signed_volume), tuple(issues),
    )


def validate_brep_solid(solid: BRepSolid) -> BRepValidationResult:
    if not isinstance(solid, BRepSolid):
        raise InvalidModelError("validate_brep_solid requires a BRepSolid")
    return _validate_brep_topology(solid)


def brep_from_triangle_mesh(mesh: TriangleMesh, *, solid_id: str | None = None) -> BRepSolid:
    """Build a faceted B-rep topology from one valid, closed triangle shell."""
    if not isinstance(mesh, TriangleMesh):
        raise InvalidModelError("brep_from_triangle_mesh requires a TriangleMesh")
    validation = validate_triangle_mesh(mesh)
    if not (validation.valid and validation.watertight and validation.consistently_oriented):
        raise InvalidModelError("faceted BRep conversion requires a valid, watertight, consistently oriented mesh")
    chosen_id = solid_id or mesh.solid_id
    if not isinstance(chosen_id, str) or not _ID.fullmatch(chosen_id):
        raise InvalidModelError("BRep solid_id must be a stable lowercase identifier")
    vertices = tuple(
        BRepVertex(f"v.{index:06d}", vertex)
        for index, vertex in enumerate(mesh.vertices)
    )
    edge_pairs = sorted({
        (min(a, b), max(a, b))
        for triangle in mesh.triangles
        for a, b in ((triangle[0], triangle[1]), (triangle[1], triangle[2]), (triangle[2], triangle[0]))
    })
    edge_ids = {pair: f"e.{index:06d}" for index, pair in enumerate(edge_pairs)}
    edges = tuple(
        BRepEdge(edge_ids[pair], f"v.{pair[0]:06d}", f"v.{pair[1]:06d}")
        for pair in edge_pairs
    )
    loops: list[BRepLoop] = []
    faces: list[BRepFace] = []
    for face_index, triangle in enumerate(mesh.triangles):
        uses = []
        for a, b in ((triangle[0], triangle[1]), (triangle[1], triangle[2]), (triangle[2], triangle[0])):
            pair = (min(a, b), max(a, b))
            uses.append(BRepEdgeUse(edge_ids[pair], a < b))
        loop_id = f"loop.{face_index:06d}"
        face_id = f"face.{face_index:06d}"
        loops.append(BRepLoop(loop_id, tuple(uses)))
        faces.append(BRepFace(face_id, loop_id))
    return BRepSolid(
        chosen_id, mesh.frame_id, mesh.length_unit, mesh.source_geometry_sha256,
        vertices, edges, tuple(loops), tuple(faces),
        BRepShell("shell.main", tuple(item.face_id for item in faces)),
    )


def triangle_mesh_from_brep(solid: BRepSolid) -> TriangleMesh:
    """Rebuild the v1.0 triangular mesh representation from a validated faceted B-rep."""
    if not isinstance(solid, BRepSolid):
        raise InvalidModelError("triangle_mesh_from_brep requires a BRepSolid")
    validation = validate_brep_solid(solid)
    if not validation.valid:
        raise InvalidModelError("cannot mesh invalid BRep: " + "; ".join(validation.issues))
    vertices = tuple(item.position for item in solid.vertices)
    vertex_indices = {item.vertex_id: index for index, item in enumerate(solid.vertices)}
    edges = {item.edge_id: item for item in solid.edges}
    loops = {item.loop_id: item for item in solid.loops}
    triangles = []
    for face in solid.faces:
        loop = loops[face.outer_loop_id]
        starts = []
        for use in loop.edge_uses:
            edge = edges[use.edge_id]
            start = edge.start_vertex_id if use.forward else edge.end_vertex_id
            starts.append(vertex_indices[start])
        triangles.append(tuple(starts))
    mesh = TriangleMesh(
        solid.solid_id, solid.frame_id, solid.length_unit, "IMPORTED_BREP",
        solid.source_geometry_sha256, vertices, tuple(triangles),
    )
    result = validate_triangle_mesh(mesh)
    if not (result.valid and result.watertight and result.consistently_oriented):
        raise InvalidModelError("BRep-to-mesh conversion failed closed mesh validation")
    return mesh
