"""Bounded ISO 10303-21 AP214 faceted-BREP mesh import/export.

The supported profile is one connected, closed, oriented triangle shell encoded
as FACETED_BREP / CLOSED_SHELL / FACE_SURFACE / PLANE / POLY_LOOP. This is not
a general STEP/AP242 translator.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from math import isfinite, sqrt
import re
from typing import Any

from .errors import InvalidModelError
from .geometry import Vec3
from .mesh import TriangleMesh, MeshValidationResult, validate_triangle_mesh

_MAX_FILE_BYTES = 64 * 1024 * 1024
_MAX_ENTITIES = 1_000_000
_MAX_VERTICES = 250_000
_MAX_FACES = 500_000
_UNIT_PREFIX = {"m": "$", "mm": ".MILLI.", "cm": ".CENTI."}
_PREFIX_UNIT = {value: key for key, value in _UNIT_PREFIX.items()}
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_ENTITY_NAME = re.compile(r"[A-Z][A-Z0-9_]*")


@dataclass(frozen=True, slots=True)
class STEPArtifact:
    content: bytes
    content_sha256: str
    source_geometry_sha256: str
    byte_count: int

    def to_dict(self) -> dict[str, object]:
        return {
            "format": "ISO10303-21_AP214_FACETED_BREP",
            "content_sha256": self.content_sha256,
            "source_geometry_sha256": self.source_geometry_sha256,
            "byte_count": self.byte_count,
        }


@dataclass(frozen=True, slots=True)
class STEPImportResult:
    mesh: TriangleMesh
    validation: MeshValidationResult
    file_sha256: str

    def to_dict(self) -> dict[str, object]:
        return {
            "format": "ISO10303-21_AP214_FACETED_BREP",
            "file_sha256": self.file_sha256,
            "mesh": self.mesh.to_dict(),
            "validation": self.validation.to_dict(),
        }


def _step_string(value: str) -> str:
    if not isinstance(value, str) or any(ord(ch) < 32 or ord(ch) > 126 for ch in value):
        raise InvalidModelError("STEP metadata strings must contain printable ASCII only")
    return "'" + value.replace("'", "''") + "'"


def _real(value: float) -> str:
    number = float(value)
    if not isfinite(number):
        raise InvalidModelError("STEP coordinates must be finite")
    return format(number, ".17g")


def _is_connected(mesh: TriangleMesh) -> bool:
    edge_faces: dict[tuple[int, int], list[int]] = {}
    for face_index, (a, b, c) in enumerate(mesh.triangles):
        for start, end in ((a, b), (b, c), (c, a)):
            edge_faces.setdefault((min(start, end), max(start, end)), []).append(face_index)
    adjacency = [set() for _ in mesh.triangles]
    for uses in edge_faces.values():
        if len(uses) == 2:
            adjacency[uses[0]].add(uses[1])
            adjacency[uses[1]].add(uses[0])
    if not adjacency:
        return False
    visited = {0}
    pending = [0]
    while pending:
        current = pending.pop()
        for neighbor in adjacency[current] - visited:
            visited.add(neighbor)
            pending.append(neighbor)
    return len(visited) == len(adjacency)


def export_step(mesh: TriangleMesh) -> STEPArtifact:
    """Export one connected watertight triangle solid as AP214 FACETED_BREP."""
    if not isinstance(mesh, TriangleMesh):
        raise InvalidModelError("export_step requires a TriangleMesh")
    prefix = _UNIT_PREFIX.get(mesh.length_unit)
    if prefix is None:
        raise InvalidModelError("STEP faceted BREP export supports m, mm and cm units only")
    validation = validate_triangle_mesh(mesh)
    if not (validation.valid and validation.watertight and validation.consistently_oriented):
        raise InvalidModelError("STEP solid export requires a valid, watertight, consistently oriented mesh")
    if not _is_connected(mesh):
        raise InvalidModelError("STEP FACETED_BREP profile requires one connected closed shell")
    if len(mesh.vertices) > _MAX_VERTICES or len(mesh.triangles) > _MAX_FACES:
        raise InvalidModelError("STEP mesh exceeds the supported vertex or face bound")
    if not _SHA256.fullmatch(mesh.source_geometry_sha256):
        raise InvalidModelError("STEP source geometry digest must be lowercase SHA-256")

    entities: list[str] = []
    next_id = 1

    def emit(entity_type: str, args: str) -> int:
        nonlocal next_id
        identifier = next_id
        next_id += 1
        entities.append(f"#{identifier}={entity_type}({args});")
        return identifier

    # The point list is emitted explicitly to keep entity numbering stable.
    point_ids = []
    for vertex in mesh.vertices:
        point_ids.append(emit(
            "CARTESIAN_POINT",
            f"'',({_real(vertex.x)},{_real(vertex.y)},{_real(vertex.z)})",
        ))

    face_ids: list[int] = []
    for face in mesh.triangles:
        a, b, c = (mesh.vertices[index] for index in face)
        ab = (b.x-a.x, b.y-a.y, b.z-a.z)
        ac = (c.x-a.x, c.y-a.y, c.z-a.z)
        normal = (
            ab[1]*ac[2]-ab[2]*ac[1],
            ab[2]*ac[0]-ab[0]*ac[2],
            ab[0]*ac[1]-ab[1]*ac[0],
        )
        norm = sqrt(sum(item*item for item in normal))
        edge_norm = sqrt(sum(item*item for item in ab))
        if norm <= 0 or edge_norm <= 0:
            raise InvalidModelError("STEP cannot export a degenerate triangle")
        unit_normal = tuple(item/norm for item in normal)
        reference = tuple(item/edge_norm for item in ab)
        normal_id = emit("DIRECTION", f"'',({_real(unit_normal[0])},{_real(unit_normal[1])},{_real(unit_normal[2])})")
        ref_id = emit("DIRECTION", f"'',({_real(reference[0])},{_real(reference[1])},{_real(reference[2])})")
        placement_id = emit("AXIS2_PLACEMENT_3D", f"'',#{point_ids[face[0]]},#{normal_id},#{ref_id}")
        plane_id = emit("PLANE", f"'',#{placement_id}")
        loop_id = emit("POLY_LOOP", f"'',({','.join(f'#{point_ids[index]}' for index in face)})")
        bound_id = emit("FACE_OUTER_BOUND", f"'',#{loop_id},.T.")
        face_ids.append(emit("FACE_SURFACE", f"'',(#{bound_id}),#{plane_id},.T."))

    shell_id = emit("CLOSED_SHELL", f"'',({','.join(f'#{item}' for item in face_ids)})")
    brep_id = emit("FACETED_BREP", f"{_step_string(mesh.solid_id)},#{shell_id}")
    unit_id = next_id
    entities.append(f"#{unit_id}=(LENGTH_UNIT() NAMED_UNIT(*) SI_UNIT({prefix},.METRE.));")
    next_id += 1
    context_id = next_id
    entities.append(
        f"#{context_id}=(GEOMETRIC_REPRESENTATION_CONTEXT(3) "
        f"GLOBAL_UNIT_ASSIGNED_CONTEXT((#{unit_id})) REPRESENTATION_CONTEXT('',''));"
    )
    next_id += 1
    emit("FACETED_BREP_SHAPE_REPRESENTATION", f"'Universal Platform', (#{brep_id}), #{context_id}")

    description = (
        _step_string(f"UP_FRAME_ID={mesh.frame_id}"),
        _step_string(f"UP_SOURCE_SHA256={mesh.source_geometry_sha256}"),
        _step_string(f"UP_SOURCE_KIND={mesh.source_kind}"),
    )
    header = "\n".join((
        "ISO-10303-21;",
        "HEADER;",
        f"FILE_DESCRIPTION(({','.join(description)}),'2;1');",
        "FILE_NAME('universal-platform.step','2000-01-01T00:00:00',(''),(''),'Universal Platform','Universal Platform','');",
        "FILE_SCHEMA(('AUTOMOTIVE_DESIGN { 1 0 10303 214 3 1 1 }'));",
        "ENDSEC;",
        "DATA;",
    ))
    data = "\n".join(entities)
    content = (header + "\n" + data + "\nENDSEC;\nEND-ISO-10303-21;\n").encode("ascii")
    if len(content) > _MAX_FILE_BYTES:
        raise InvalidModelError("STEP file exceeds the supported byte limit")
    return STEPArtifact(content, sha256(content).hexdigest(), mesh.source_geometry_sha256, len(content))


def _split_top_level(text: str) -> list[str]:
    values: list[str] = []
    start = 0
    depth = 0
    quoted = False
    index = 0
    while index < len(text):
        char = text[index]
        if char == "'":
            if quoted and index + 1 < len(text) and text[index + 1] == "'":
                index += 2
                continue
            quoted = not quoted
        elif not quoted:
            if char == "(":
                depth += 1
            elif char == ")":
                depth -= 1
                if depth < 0:
                    raise InvalidModelError("STEP argument list has unbalanced parentheses")
            elif char == "," and depth == 0:
                values.append(text[start:index].strip())
                start = index + 1
        index += 1
    if quoted or depth != 0:
        raise InvalidModelError("STEP argument list has unterminated string or parentheses")
    values.append(text[start:].strip())
    return values


def _unquote(value: str) -> str:
    value = value.strip()
    if len(value) < 2 or value[0] != "'" or value[-1] != "'":
        raise InvalidModelError("STEP string value is malformed")
    return value[1:-1].replace("''", "'")


def _ref(value: str) -> int:
    match = re.fullmatch(r"#([0-9]+)", value.strip())
    if not match:
        raise InvalidModelError("STEP entity reference is malformed")
    return int(match.group(1))


def _refs(value: str) -> tuple[int, ...]:
    value = value.strip()
    if not (value.startswith("(") and value.endswith(")")):
        raise InvalidModelError("STEP reference set is malformed")
    inner = value[1:-1].strip()
    return tuple(_ref(item) for item in _split_top_level(inner)) if inner else ()


def _numbers(value: str) -> tuple[float, ...]:
    value = value.strip()
    if not (value.startswith("(") and value.endswith(")")):
        raise InvalidModelError("STEP numeric tuple is malformed")
    result = []
    for item in _split_top_level(value[1:-1]):
        try:
            number = float(item)
        except (TypeError, ValueError, OverflowError) as exc:
            raise InvalidModelError("STEP coordinate is not numeric") from exc
        if not isfinite(number):
            raise InvalidModelError("STEP coordinate must be finite")
        result.append(number)
    return tuple(result)


def _scan_instances(data: str) -> dict[int, tuple[str, str]]:
    result: dict[int, tuple[str, str]] = {}
    index = 0
    while index < len(data):
        while index < len(data) and data[index].isspace():
            index += 1
        if index >= len(data):
            break
        if data.startswith("/*", index):
            raise InvalidModelError("STEP comments are outside the supported strict profile")
        match = re.match(r"#([0-9]+)\s*=\s*", data[index:])
        if not match:
            raise InvalidModelError("STEP DATA contains an unsupported token")
        identifier = int(match.group(1))
        if identifier in result:
            raise InvalidModelError("STEP entity identifiers must be unique")
        index += match.end()
        complex_instance = index < len(data) and data[index] == "("
        if complex_instance:
            entity_type = "__COMPLEX__"
        else:
            type_match = _ENTITY_NAME.match(data, index)
            if not type_match:
                raise InvalidModelError("STEP entity type is malformed")
            entity_type = type_match.group(0)
            index = type_match.end()
            while index < len(data) and data[index].isspace():
                index += 1
        if index >= len(data) or data[index] != "(":
            raise InvalidModelError("STEP entity argument list is missing")
        start = index
        depth = 0
        quoted = False
        while index < len(data):
            char = data[index]
            if char == "'":
                if quoted and index + 1 < len(data) and data[index + 1] == "'":
                    index += 2
                    continue
                quoted = not quoted
            elif not quoted:
                if char == "(":
                    depth += 1
                elif char == ")":
                    depth -= 1
                    if depth == 0:
                        index += 1
                        break
            index += 1
        if depth != 0 or quoted:
            raise InvalidModelError("STEP entity has an unterminated argument list")
        raw = data[start+1:index-1]
        while index < len(data) and data[index].isspace():
            index += 1
        if index >= len(data) or data[index] != ";":
            raise InvalidModelError("STEP entity is missing its terminator")
        index += 1
        result[identifier] = (entity_type, raw)
        if len(result) > _MAX_ENTITIES:
            raise InvalidModelError("STEP entity count exceeds the resource limit")
    return result


def import_step(content: bytes) -> STEPImportResult:
    """Import one strict AP214 faceted BREP triangle shell."""
    if not isinstance(content, bytes) or not content or len(content) > _MAX_FILE_BYTES:
        raise InvalidModelError("STEP import requires non-empty bytes within the file-size limit")
    try:
        text = content.decode("ascii")
    except UnicodeDecodeError as exc:
        raise InvalidModelError("STEP subset requires ASCII Part 21 encoding") from exc
    if not text.startswith("ISO-10303-21;") or not text.rstrip().endswith("END-ISO-10303-21;"):
        raise InvalidModelError("STEP Part 21 envelope is invalid")
    data_match = re.search(r"\bDATA;\s*(.*?)\s*ENDSEC;", text, re.DOTALL)
    if not data_match:
        raise InvalidModelError("STEP DATA section is missing")
    header = text[:data_match.start()]
    schema_match = re.search(r"FILE_SCHEMA\s*\(\s*\(\s*'([^']+)'\s*\)\s*\)", header)
    if not schema_match or not (
        "AUTOMOTIVE_DESIGN" in schema_match.group(1)
        or "AP242_MANAGED_MODEL_BASED_3D_ENGINEERING" in schema_match.group(1)
    ):
        raise InvalidModelError("STEP file schema must be AP214/AP242 automotive design profile")
    description_match = re.search(r"FILE_DESCRIPTION\s*\(\s*\((.*?)\)\s*,\s*'2;1'\s*\)\s*;", header, re.DOTALL)
    descriptions: list[str] = []
    if description_match:
        descriptions = [_unquote(item) for item in _split_top_level(description_match.group(1))]

    instances = _scan_instances(data_match.group(1))
    allowed_simple = {
        "CARTESIAN_POINT", "DIRECTION", "AXIS2_PLACEMENT_3D", "PLANE",
        "POLY_LOOP", "FACE_OUTER_BOUND", "FACE_SURFACE", "CLOSED_SHELL",
        "FACETED_BREP", "FACETED_BREP_SHAPE_REPRESENTATION",
    }
    complex_instances = [raw for kind, raw in instances.values() if kind == "__COMPLEX__"]
    if any(kind not in allowed_simple | {"__COMPLEX__"} for kind, _ in instances.values()):
        raise InvalidModelError("STEP file contains an unsupported entity type")
    if len(complex_instances) != 2:
        raise InvalidModelError("STEP profile requires one length unit and one geometric context")
    unit_match = re.search(r"SI_UNIT\s*\(\s*(\$|\.[A-Z]+\.)\s*,\s*\.METRE\.\s*\)", " ".join(complex_instances))
    if not unit_match or unit_match.group(1) not in _PREFIX_UNIT:
        raise InvalidModelError("STEP profile has an unsupported or missing SI length unit")
    length_unit = _PREFIX_UNIT[unit_match.group(1)]

    parsed: dict[int, tuple[str, list[str]]] = {}
    for identifier, (kind, raw) in instances.items():
        if kind != "__COMPLEX__":
            parsed[identifier] = (kind, _split_top_level(raw))

    def get(identifier: int, kind: str) -> list[str]:
        if identifier not in parsed or parsed[identifier][0] != kind:
            raise InvalidModelError(f"STEP reference #{identifier} is not a {kind}")
        return parsed[identifier][1]

    point_entities: dict[int, Vec3] = {}
    for identifier, (kind, args) in parsed.items():
        if kind == "CARTESIAN_POINT":
            if len(args) != 2:
                raise InvalidModelError("STEP CARTESIAN_POINT has invalid arity")
            coordinates = _numbers(args[1])
            if len(coordinates) != 3:
                raise InvalidModelError("STEP Cartesian points must be three-dimensional")
            point_entities[identifier] = Vec3(*coordinates)

    breps = [(identifier, args) for identifier, (kind, args) in parsed.items() if kind == "FACETED_BREP"]
    representations = [(identifier, args) for identifier, (kind, args) in parsed.items()
                       if kind == "FACETED_BREP_SHAPE_REPRESENTATION"]
    if len(breps) != 1 or len(representations) != 1:
        raise InvalidModelError("STEP profile requires exactly one FACETED_BREP and shape representation")
    brep_id, brep_args = breps[0]
    if len(brep_args) != 2:
        raise InvalidModelError("STEP FACETED_BREP has invalid arity")
    solid_id = _unquote(brep_args[0])
    shell_id = _ref(brep_args[1])
    rep_args = representations[0][1]
    if (len(rep_args) != 3 or _refs(rep_args[1]) != (brep_id,)
            or _ref(rep_args[2]) != context_id):
        raise InvalidModelError("STEP shape representation must reference the single FACETED_BREP and geometric context")
    shell_args = get(shell_id, "CLOSED_SHELL")
    if len(shell_args) != 2:
        raise InvalidModelError("STEP CLOSED_SHELL has invalid arity")
    face_ids = _refs(shell_args[1])
    if not face_ids or len(face_ids) > _MAX_FACES:
        raise InvalidModelError("STEP face count is outside the supported bounds")

    vertices_by_id = point_entities
    used_point_ids: set[int] = set()
    triangles_by_ids: list[tuple[int, int, int]] = []
    for face_id in face_ids:
        face_args = get(face_id, "FACE_SURFACE")
        if len(face_args) != 4 or _unquote(face_args[0]) == "":
            # Empty names are valid STEP labels; only arity and booleans matter.
            if len(face_args) != 4:
                raise InvalidModelError("STEP FACE_SURFACE has invalid arity")
        bounds = _refs(face_args[1])
        if len(bounds) != 1:
            raise InvalidModelError("STEP faceted face requires exactly one outer bound")
        if face_args[3] != ".T.":
            raise InvalidModelError("STEP FACE_SURFACE same_sense must be TRUE")
        bound_args = get(bounds[0], "FACE_OUTER_BOUND")
        if len(bound_args) != 3 or bound_args[2] != ".T.":
            raise InvalidModelError("STEP face requires one positively oriented FACE_OUTER_BOUND")
        loop_args = get(_ref(bound_args[1]), "POLY_LOOP")
        if len(loop_args) != 2:
            raise InvalidModelError("STEP POLY_LOOP has invalid arity")
        loop_ids = _refs(loop_args[1])
        if len(loop_ids) != 3 or len(set(loop_ids)) != 3:
            raise InvalidModelError("STEP faceted mesh profile supports triangular POLY_LOOP faces only")
        if any(point_id not in vertices_by_id for point_id in loop_ids):
            raise InvalidModelError("STEP POLY_LOOP references a missing Cartesian point")
        used_point_ids.update(loop_ids)

        plane_args = get(_ref(face_args[2]), "PLANE")
        if len(plane_args) != 2:
            raise InvalidModelError("STEP PLANE has invalid arity")
        placement = get(_ref(plane_args[1]), "AXIS2_PLACEMENT_3D")
        if len(placement) != 4:
            raise InvalidModelError("STEP AXIS2_PLACEMENT_3D has invalid arity")
        location_id, axis_id, ref_id = (_ref(placement[1]), _ref(placement[2]), _ref(placement[3]))
        location = vertices_by_id.get(location_id)
        if location is None:
            raise InvalidModelError("STEP plane placement references a missing Cartesian point")
        axis_args, ref_args = get(axis_id, "DIRECTION"), get(ref_id, "DIRECTION")
        axis, reference = _numbers(axis_args[1]), _numbers(ref_args[1])
        if len(axis) != 3 or len(reference) != 3:
            raise InvalidModelError("STEP plane directions must be three-dimensional")
        reference_norm = sqrt(sum(item*item for item in reference))
        if reference_norm <= 0:
            raise InvalidModelError("STEP plane reference direction must be non-zero")
        p0, p1, p2 = (vertices_by_id[item] for item in loop_ids)
        ab = (p1.x-p0.x, p1.y-p0.y, p1.z-p0.z)
        ac = (p2.x-p0.x, p2.y-p0.y, p2.z-p0.z)
        cross = (ab[1]*ac[2]-ab[2]*ac[1], ab[2]*ac[0]-ab[0]*ac[2], ab[0]*ac[1]-ab[1]*ac[0])
        cross_norm = sqrt(sum(item*item for item in cross))
        axis_norm = sqrt(sum(item*item for item in axis))
        if cross_norm <= 0 or axis_norm <= 0:
            raise InvalidModelError("STEP face or plane has degenerate orientation")
        alignment = sum(cross[i]*axis[i] for i in range(3)) / (cross_norm*axis_norm)
        perpendicular = sum(axis[i]*reference[i] for i in range(3)) / (axis_norm*reference_norm)
        edge_alignment = sum(ab[i]*reference[i] for i in range(3)) / (sqrt(sum(item*item for item in ab))*reference_norm)
        if alignment < 1.0 - 1e-8:
            raise InvalidModelError("STEP face loop orientation does not agree with its plane normal")
        if abs(perpendicular) > 1e-8 or edge_alignment < 1.0 - 1e-8:
            raise InvalidModelError("STEP plane reference direction is not aligned with its face loop")
        if ((p0.x-location.x)**2 + (p0.y-location.y)**2 + (p0.z-location.z)**2) > 1e-16:
            raise InvalidModelError("STEP plane placement must be anchored at the first loop point")
        triangles_by_ids.append(loop_ids)

    if used_point_ids != set(point_entities):
        raise InvalidModelError("STEP profile must not contain unreferenced Cartesian points")
    ordered_point_ids = sorted(used_point_ids)
    point_index = {point_id: index for index, point_id in enumerate(ordered_point_ids)}
    vertices = tuple(vertices_by_id[item] for item in ordered_point_ids)
    triangles = tuple(tuple(point_index[item] for item in face) for face in triangles_by_ids)
    frame_id = "step.model"
    source_digest = sha256(content).hexdigest()
    source_kind = "IMPORTED_STEP"
    for item in descriptions:
        if item.startswith("UP_FRAME_ID="):
            frame_id = item.split("=", 1)[1]
        elif item.startswith("UP_SOURCE_SHA256="):
            source_digest = item.split("=", 1)[1]
        elif item.startswith("UP_SOURCE_KIND="):
            source_kind = item.split("=", 1)[1]
    if not _SHA256.fullmatch(source_digest):
        raise InvalidModelError("STEP source geometry metadata must be a lowercase SHA-256 digest")
    mesh = TriangleMesh(
        solid_id or "imported.step", frame_id, length_unit, "IMPORTED_STEP",
        source_digest, vertices, triangles, None,
    )
    validation = validate_triangle_mesh(mesh)
    if not (validation.valid and validation.watertight and validation.consistently_oriented):
        raise InvalidModelError("STEP import requires a valid, watertight, consistently oriented faceted solid")
    if not _is_connected(mesh):
        raise InvalidModelError("STEP FACETED_BREP profile requires one connected closed shell")
    return STEPImportResult(mesh, validation, sha256(content).hexdigest())
