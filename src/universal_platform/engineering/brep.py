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
        if not isinstance(self.edge_uses, tuple) or len(self.edge_uses) < 3:
            raise InvalidModelError("faceted BRep loops require at least three edge uses")
        if any(not isinstance(item, BRepEdgeUse) for item in self.edge_uses):
            raise InvalidModelError("BRep loop edge_uses must contain BRepEdgeUse records")
        if len({item.edge_id for item in self.edge_uses}) != len(self.edge_uses):
            raise InvalidModelError("a BRep loop cannot repeat an edge")


@dataclass(frozen=True, slots=True)
class BRepFace:
    face_id: str
    outer_loop_id: str
    inner_loop_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.face_id, str) or not _ID.fullmatch(self.face_id):
            raise InvalidModelError("BRep face_id must be a stable lowercase identifier")
        if not isinstance(self.outer_loop_id, str) or not _ID.fullmatch(self.outer_loop_id):
            raise InvalidModelError("BRep face requires an outer loop identifier")
        if not isinstance(self.inner_loop_ids, tuple) or any(
            not isinstance(item, str) or not _ID.fullmatch(item) for item in self.inner_loop_ids
        ):
            raise InvalidModelError("BRep face inner_loop_ids must be an immutable tuple of stable identifiers")
        if len(set(self.inner_loop_ids)) != len(self.inner_loop_ids) or self.outer_loop_id in self.inner_loop_ids:
            raise InvalidModelError("BRep face cannot repeat its outer or inner loops")


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

    SCHEMA_VERSION: ClassVar[str] = "2.0"
    PROFILE: ClassVar[str] = "FACETED_POLYGONAL_PLANAR_SHELL_V2"

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
                {"face_id": item.face_id, "outer_loop_id": item.outer_loop_id,
                 "inner_loop_ids": list(item.inner_loop_ids)} for item in self.faces
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
        legacy_v1 = (
            value["schema_version"] == "1.0"
            and value["profile"] == "FACETED_TRIANGULAR_PLANAR_SHELL_V1"
        )
        current_v2 = (
            value["schema_version"] == cls.SCHEMA_VERSION
            and value["profile"] == cls.PROFILE
        )
        if not (legacy_v1 or current_v2):
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
            expected_face_fields = {"face_id", "outer_loop_id"} if legacy_v1 else {
                "face_id", "outer_loop_id", "inner_loop_ids"
            }
            if not isinstance(raw, Mapping) or set(raw) != expected_face_fields:
                raise InvalidModelError("BRep face has missing or unknown fields")
            inner_ids = () if legacy_v1 else raw["inner_loop_ids"]
            if not isinstance(inner_ids, (list, tuple)):
                raise InvalidModelError("BRep face inner_loop_ids must be an array")
            faces.append(BRepFace(raw["face_id"], raw["outer_loop_id"], tuple(inner_ids)))
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


def _orient2(a: tuple[Fraction, Fraction], b: tuple[Fraction, Fraction],
              c: tuple[Fraction, Fraction]) -> Fraction:
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])


def _on_segment(a: tuple[Fraction, Fraction], b: tuple[Fraction, Fraction],
                point: tuple[Fraction, Fraction]) -> bool:
    return (
        _orient2(a, b, point) == 0
        and min(a[0], b[0]) <= point[0] <= max(a[0], b[0])
        and min(a[1], b[1]) <= point[1] <= max(a[1], b[1])
    )


def _segments_intersect(
    a: tuple[Fraction, Fraction], b: tuple[Fraction, Fraction],
    c: tuple[Fraction, Fraction], d: tuple[Fraction, Fraction],
) -> bool:
    o1, o2, o3, o4 = _orient2(a, b, c), _orient2(a, b, d), _orient2(c, d, a), _orient2(c, d, b)
    if o1 == 0 and _on_segment(a, b, c):
        return True
    if o2 == 0 and _on_segment(a, b, d):
        return True
    if o3 == 0 and _on_segment(c, d, a):
        return True
    if o4 == 0 and _on_segment(c, d, b):
        return True
    return (o1 > 0) != (o2 > 0) and (o3 > 0) != (o4 > 0)


def _polygon_area2(points: tuple[tuple[Fraction, Fraction], ...]) -> Fraction:
    return sum(
        points[index][0] * points[(index + 1) % len(points)][1]
        - points[(index + 1) % len(points)][0] * points[index][1]
        for index in range(len(points))
    )


def _simple_polygon(points: tuple[tuple[Fraction, Fraction], ...]) -> bool:
    count = len(points)
    if count < 3 or len(set(points)) != count or _polygon_area2(points) == 0:
        return False
    for first in range(count):
        a, b = points[first], points[(first + 1) % count]
        for second in range(first + 1, count):
            if second == first or second == (first + 1) % count or first == (second + 1) % count:
                continue
            c, d = points[second], points[(second + 1) % count]
            if _segments_intersect(a, b, c, d):
                return False
    return True


def _point_in_polygon(
    point: tuple[Fraction, Fraction],
    polygon: tuple[tuple[Fraction, Fraction], ...],
) -> int:
    """Return 1 for inside, 0 for boundary and -1 for outside."""
    inside = False
    for index, first in enumerate(polygon):
        second = polygon[(index + 1) % len(polygon)]
        if _on_segment(first, second, point):
            return 0
        if (first[1] > point[1]) != (second[1] > point[1]):
            crossing_x = first[0] + (
                (point[1] - first[1]) * (second[0] - first[0]) / (second[1] - first[1])
            )
            if crossing_x > point[0]:
                inside = not inside
    return 1 if inside else -1


def _polygons_intersect(
    first: tuple[tuple[Fraction, Fraction], ...],
    second: tuple[tuple[Fraction, Fraction], ...],
) -> bool:
    return any(
        _segments_intersect(
            first[index], first[(index + 1) % len(first)],
            second[other], second[(other + 1) % len(second)],
        )
        for index in range(len(first)) for other in range(len(second))
    )


def _validate_brep_topology(solid: BRepSolid) -> BRepValidationResult:
    issues: list[str] = []
    vertices = {item.vertex_id: item.position for item in solid.vertices}
    edges = {item.edge_id: item for item in solid.edges}
    loops = {item.loop_id: item for item in solid.loops}
    faces = {item.face_id: item for item in solid.faces}
    if set(solid.shell.face_ids) != set(faces) or len(solid.shell.face_ids) != len(faces):
        issues.append("shell face list must reference every face exactly once")
    edge_incidence: dict[str, list[bool]] = {key: [] for key in edges}
    edge_to_faces: dict[str, list[str]] = {}
    face_adjacency: dict[str, set[str]] = {key: set() for key in faces}
    loop_owner: dict[str, str] = {}
    used_vertices: set[str] = set()
    signed_volume = Fraction(0, 1)

    for face in solid.faces:
        face_loop_ids = (face.outer_loop_id, *face.inner_loop_ids)
        if len(set(face_loop_ids)) != len(face_loop_ids):
            issues.append(f"face {face.face_id} repeats a boundary loop")
            continue
        face_points: list[list[Vec3]] = []
        for loop_id in face_loop_ids:
            loop = loops.get(loop_id)
            if loop is None:
                issues.append(f"face {face.face_id} references a missing boundary loop")
                continue
            if loop.loop_id in loop_owner:
                issues.append(f"loop {loop.loop_id} is owned by more than one face")
            loop_owner[loop.loop_id] = face.face_id
            directed: list[tuple[str, str]] = []
            points: list[Vec3] = []
            for use in loop.edge_uses:
                edge = edges.get(use.edge_id)
                if edge is None:
                    issues.append(f"loop {loop.loop_id} references a missing edge")
                    continue
                edge_incidence[use.edge_id].append(use.forward)
                edge_to_faces.setdefault(use.edge_id, []).append(face.face_id)
                start = edge.start_vertex_id if use.forward else edge.end_vertex_id
                end = edge.end_vertex_id if use.forward else edge.start_vertex_id
                if start not in vertices or end not in vertices:
                    issues.append(f"edge {edge.edge_id} references a missing vertex")
                    continue
                directed.append((start, end))
                points.append(vertices[start])
                used_vertices.update((start, end))
            if len(directed) != len(loop.edge_uses) or any(
                directed[index][1] != directed[(index + 1) % len(directed)][0]
                for index in range(len(directed))
            ):
                issues.append(f"loop {loop.loop_id} is not a closed connected edge cycle")
            if len({item[0] for item in directed}) != len(directed):
                issues.append(f"loop {loop.loop_id} repeats a vertex")
            if len(points) >= 3:
                face_points.append(points)

        if not face_points or len(face_points) != len(face_loop_ids):
            continue
        outer_points = face_points[0]
        p0 = outer_points[0]
        q0 = tuple(_q(value) for value in (p0.x, p0.y, p0.z))
        normal = (Fraction(0), Fraction(0), Fraction(0))
        for first in range(1, len(outer_points) - 1):
            for second in range(first + 1, len(outer_points)):
                a = tuple(_q(value) for value in (
                    outer_points[first].x - p0.x,
                    outer_points[first].y - p0.y,
                    outer_points[first].z - p0.z,
                ))
                b = tuple(_q(value) for value in (
                    outer_points[second].x - p0.x,
                    outer_points[second].y - p0.y,
                    outer_points[second].z - p0.z,
                ))
                candidate = _cross(a, b)
                if candidate != (0, 0, 0):
                    normal = candidate
                    break
            if normal != (0, 0, 0):
                break
        if normal == (0, 0, 0):
            issues.append(f"face {face.face_id} has a degenerate outer loop")
            continue
        drop_axis = max(range(3), key=lambda axis: abs(normal[axis]))
        keep_axes = tuple(axis for axis in range(3) if axis != drop_axis)

        def project(point: Vec3) -> tuple[Fraction, Fraction]:
            coords = (_q(point.x), _q(point.y), _q(point.z))
            return coords[keep_axes[0]], coords[keep_axes[1]]

        projected_loops: list[tuple[tuple[Fraction, Fraction], ...]] = []
        for points in face_points:
            for point in points:
                delta = tuple(
                    _q(value) - q0[index]
                    for index, value in enumerate((point.x, point.y, point.z))
                )
                if _dot(normal, delta) != 0:
                    issues.append(f"face {face.face_id} boundary loops are not coplanar")
                    break
            projected = tuple(project(point) for point in points)
            if not _simple_polygon(projected):
                issues.append(f"face {face.face_id} contains a degenerate or self-intersecting loop")
            projected_loops.append(projected)
            # Oriented polygon fan contributes the exact signed surface volume.
            p_first = tuple(_q(value) for value in (points[0].x, points[0].y, points[0].z))
            for index in range(1, len(points) - 1):
                p_second = tuple(_q(value) for value in (
                    points[index].x, points[index].y, points[index].z
                ))
                p_third = tuple(_q(value) for value in (
                    points[index + 1].x, points[index + 1].y, points[index + 1].z
                ))
                signed_volume += _dot(p_first, _cross(p_second, p_third)) / 6

        outer_area = _polygon_area2(projected_loops[0])
        for hole_index, hole in enumerate(projected_loops[1:], start=1):
            if _polygon_area2(hole) * outer_area >= 0:
                issues.append(f"face {face.face_id} inner loop {face.inner_loop_ids[hole_index - 1]} has invalid orientation")
            if _point_in_polygon(hole[0], projected_loops[0]) != 1:
                issues.append(f"face {face.face_id} inner loop is not strictly contained by its outer loop")
            if _polygons_intersect(hole, projected_loops[0]):
                issues.append(f"face {face.face_id} inner loop touches or crosses its outer loop")
            for previous in projected_loops[1:hole_index]:
                if _polygons_intersect(hole, previous) or _point_in_polygon(hole[0], previous) == 1 or _point_in_polygon(previous[0], hole) == 1:
                    issues.append(f"face {face.face_id} inner loops overlap or nest")

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

    for face_ids in edge_to_faces.values():
        if len(face_ids) == 2 and face_ids[0] != face_ids[1]:
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

    euler = len(vertices) - len(edges) + sum(1 - len(face.inner_loop_ids) for face in solid.faces)
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
    if any(
        face.inner_loop_ids or len(next(
            loop for loop in solid.loops if loop.loop_id == face.outer_loop_id
        ).edge_uses) != 3
        for face in solid.faces
    ):
        raise InvalidModelError(
            "BRep-to-mesh conversion currently supports triangular faces without inner loops"
        )
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
