"""Bounded exact-grid Boolean operations for axis-aligned faceted BRep boxes.

This is a deliberately narrow 3D Boolean reference implementation. It accepts
only BRepSolid inputs that are exact axis-aligned box shells and emits one or
more closed triangular faceted BRep components. It is not a general 3D CSG or
curved-surface Boolean kernel.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from fractions import Fraction
from hashlib import sha256
from itertools import product
import json
import re
from typing import ClassVar, Mapping

from .brep import BRepSolid, brep_from_triangle_mesh
from .brep_multishell import BRepMultiShellSolid, _point_inside_mesh
from .errors import InvalidModelError
from .geometry import Vec3
from .mesh import TriangleMesh, validate_triangle_mesh

_ID = re.compile(r"^[a-z0-9]+(?:[._/-][a-z0-9]+)*$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_MAX_INPUTS = 16
_MAX_GRID_CELLS = 32_768


class BRepBooleanOperation(str, Enum):
    UNION = "UNION"
    INTERSECTION = "INTERSECTION"
    DIFFERENCE = "DIFFERENCE"
    SYMMETRIC_DIFFERENCE = "SYMMETRIC_DIFFERENCE"


@dataclass(frozen=True, slots=True)
class _BoxBounds:
    minimum: tuple[Fraction, Fraction, Fraction]
    maximum: tuple[Fraction, Fraction, Fraction]


@dataclass(frozen=True, slots=True)
class BRepBooleanResult:
    operation: BRepBooleanOperation
    input_solid_ids: tuple[str, ...]
    input_source_sha256: tuple[str, ...]
    components: tuple[BRepSolid, ...]
    grid_cell_count: int
    result_sha256: str

    SCHEMA_VERSION: ClassVar[str] = "1.0"
    ALGORITHM_VERSION: ClassVar[str] = "exact-axis-aligned-brep-box-grid-v1"

    def __post_init__(self) -> None:
        if not isinstance(self.operation, BRepBooleanOperation):
            raise InvalidModelError("BRep Boolean operation is unsupported")
        if not isinstance(self.input_solid_ids, tuple) or len(self.input_solid_ids) < 2:
            raise InvalidModelError("BRep Boolean requires at least two input solid IDs")
        if len(self.input_solid_ids) != len(self.input_source_sha256):
            raise InvalidModelError("BRep Boolean input ID and digest counts must match")
        if any(not isinstance(item, str) or not _ID.fullmatch(item) for item in self.input_solid_ids):
            raise InvalidModelError("BRep Boolean input IDs must be stable identifiers")
        if len(set(self.input_solid_ids)) != len(self.input_solid_ids):
            raise InvalidModelError("BRep Boolean input solid IDs must be unique")
        if any(not isinstance(item, str) or not _SHA256.fullmatch(item) for item in self.input_source_sha256):
            raise InvalidModelError("BRep Boolean input digests must be lowercase SHA-256")
        if not isinstance(self.components, tuple) or any(not isinstance(item, BRepSolid) for item in self.components):
            raise InvalidModelError("BRep Boolean components must be an immutable tuple of BRepSolid")
        if isinstance(self.grid_cell_count, bool) or not isinstance(self.grid_cell_count, int) or self.grid_cell_count < 0:
            raise InvalidModelError("BRep Boolean grid_cell_count must be a non-negative integer")
        if not isinstance(self.result_sha256, str) or not _SHA256.fullmatch(self.result_sha256):
            raise InvalidModelError("BRep Boolean result_sha256 must be lowercase SHA-256")
        if len({item.solid_id for item in self.components}) != len(self.components):
            raise InvalidModelError("BRep Boolean component solid IDs must be unique")
        expected = _result_digest(
            self.operation, self.input_solid_ids, self.input_source_sha256,
            self.grid_cell_count, self.components,
        )
        if self.result_sha256 != expected:
            raise InvalidModelError("BRep Boolean result digest does not match its content")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.SCHEMA_VERSION,
            "algorithm_version": self.ALGORITHM_VERSION,
            "operation": self.operation.value,
            "input_solid_ids": list(self.input_solid_ids),
            "input_source_sha256": list(self.input_source_sha256),
            "components": [item.to_dict() for item in self.components],
            "grid_cell_count": self.grid_cell_count,
            "result_sha256": self.result_sha256,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, object]) -> "BRepBooleanResult":
        required = {
            "schema_version", "algorithm_version", "operation", "input_solid_ids",
            "input_source_sha256", "components", "grid_cell_count", "result_sha256",
        }
        if not isinstance(value, Mapping) or set(value) != required:
            raise InvalidModelError("BRepBooleanResult snapshot has missing or unknown fields")
        if value["schema_version"] != cls.SCHEMA_VERSION or value["algorithm_version"] != cls.ALGORITHM_VERSION:
            raise InvalidModelError("unsupported BRepBooleanResult version")
        try:
            operation = BRepBooleanOperation(value["operation"])
        except (TypeError, ValueError) as exc:
            raise InvalidModelError("unsupported BRep Boolean operation") from exc
        for name in ("input_solid_ids", "input_source_sha256", "components"):
            if not isinstance(value[name], (list, tuple)):
                raise InvalidModelError(f"BRepBooleanResult {name} must be an array")
        components = tuple(BRepSolid.from_dict(item) for item in value["components"])
        return cls(
            operation, tuple(value["input_solid_ids"]), tuple(value["input_source_sha256"]),
            components, value["grid_cell_count"], value["result_sha256"],
        )


def _result_digest(
    operation: BRepBooleanOperation,
    input_ids: tuple[str, ...],
    input_digests: tuple[str, ...],
    cell_count: int,
    components: tuple[BRepSolid, ...],
) -> str:
    payload = {
        "algorithm_version": BRepBooleanResult.ALGORITHM_VERSION,
        "operation": operation.value,
        "input_solid_ids": list(input_ids),
        "input_source_sha256": list(input_digests),
        "grid_cell_count": cell_count,
        "component_digests": [item.source_geometry_sha256 for item in components],
    }
    return sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def _fraction(value: float) -> Fraction:
    return Fraction.from_float(float(value))


def _box_bounds(solid: BRepSolid) -> _BoxBounds:
    xs = sorted({_fraction(item.position.x) for item in solid.vertices})
    ys = sorted({_fraction(item.position.y) for item in solid.vertices})
    zs = sorted({_fraction(item.position.z) for item in solid.vertices})
    if len(xs) != 2 or len(ys) != 2 or len(zs) != 2 or len(solid.vertices) != 8:
        raise InvalidModelError("BRep Boolean v1 supports only eight-vertex axis-aligned box solids")
    if {(x, y, z) for x, y, z in product(xs, ys, zs)} != {
        (_fraction(item.position.x), _fraction(item.position.y), _fraction(item.position.z))
        for item in solid.vertices
    }:
        raise InvalidModelError("BRep Boolean input is not a complete axis-aligned box")
    vertices = {item.vertex_id: item.position for item in solid.vertices}
    edges = {item.edge_id: item for item in solid.edges}
    loops = {item.loop_id: item for item in solid.loops}
    plane_counts: dict[tuple[int, Fraction], int] = {}
    for face in solid.faces:
        loop = loops[face.outer_loop_id]
        points = []
        for use in loop.edge_uses:
            edge = edges[use.edge_id]
            vertex_id = edge.start_vertex_id if use.forward else edge.end_vertex_id
            points.append(vertices[vertex_id])
        coords = [
            (_fraction(point.x), _fraction(point.y), _fraction(point.z))
            for point in points
        ]
        planes = [
            (axis, coords[0][axis])
            for axis in range(3)
            if coords[0][axis] == coords[1][axis] == coords[2][axis]
        ]
        if len(planes) != 1:
            raise InvalidModelError("BRep Boolean input contains a non-axis-aligned face")
        axis, value = planes[0]
        limits = (xs, ys, zs)[axis]
        if value not in (limits[0], limits[-1]):
            raise InvalidModelError("BRep Boolean face is not on a box boundary plane")
        plane_counts[(axis, value)] = plane_counts.get((axis, value), 0) + 1
    expected_planes = {(0, value) for value in xs} | {(1, value) for value in ys} | {(2, value) for value in zs}
    if set(plane_counts) != expected_planes or any(count != 2 for count in plane_counts.values()):
        raise InvalidModelError("BRep Boolean input must have two triangular faces on each of six box planes")
    return _BoxBounds((xs[0], ys[0], zs[0]), (xs[1], ys[1], zs[1]))


def _inside(point: tuple[Fraction, Fraction, Fraction], bounds: _BoxBounds) -> bool:
    return all(bounds.minimum[axis] <= point[axis] < bounds.maximum[axis] for axis in range(3))


def _operation_value(values: tuple[bool, ...], operation: BRepBooleanOperation) -> bool:
    if operation is BRepBooleanOperation.UNION:
        return any(values)
    if operation is BRepBooleanOperation.INTERSECTION:
        return all(values)
    if operation is BRepBooleanOperation.DIFFERENCE:
        return values[0] and not any(values[1:])
    return sum(values) % 2 == 1


def _components(cells: set[tuple[int, int, int]]) -> tuple[tuple[tuple[int, int, int], ...], ...]:
    remaining = set(cells)
    result = []
    while remaining:
        seed = min(remaining)
        remaining.remove(seed)
        found = {seed}
        pending = [seed]
        while pending:
            i, j, k = pending.pop()
            for neighbor in ((i-1,j,k),(i+1,j,k),(i,j-1,k),(i,j+1,k),(i,j,k-1),(i,j,k+1)):
                if neighbor in remaining:
                    remaining.remove(neighbor)
                    found.add(neighbor)
                    pending.append(neighbor)
        result.append(tuple(sorted(found)))
    return tuple(result)


def _component_mesh(
    cells: tuple[tuple[int, int, int], ...],
    occupied: set[tuple[int, int, int]],
    xs: tuple[Fraction, ...],
    ys: tuple[Fraction, ...],
    zs: tuple[Fraction, ...],
    *,
    solid_id: str,
    frame_id: str,
    length_unit: str,
    source_digest: str,
) -> TriangleMesh:
    quads: list[tuple[tuple[Fraction, Fraction, Fraction], ...]] = []
    for i, j, k in cells:
        x0, x1, y0, y1, z0, z1 = xs[i], xs[i+1], ys[j], ys[j+1], zs[k], zs[k+1]
        faces = (
            ((i-1,j,k), ((x0,y0,z0),(x0,y0,z1),(x0,y1,z1),(x0,y1,z0))),
            ((i+1,j,k), ((x1,y0,z0),(x1,y1,z0),(x1,y1,z1),(x1,y0,z1))),
            ((i,j-1,k), ((x0,y0,z0),(x1,y0,z0),(x1,y0,z1),(x0,y0,z1))),
            ((i,j+1,k), ((x0,y1,z0),(x0,y1,z1),(x1,y1,z1),(x1,y1,z0))),
            ((i,j,k-1), ((x0,y0,z0),(x0,y1,z0),(x1,y1,z0),(x1,y0,z0))),
            ((i,j,k+1), ((x0,y0,z1),(x1,y0,z1),(x1,y1,z1),(x0,y1,z1))),
        )
        for neighbor, quad in faces:
            if neighbor not in occupied:
                quads.append(quad)
    coordinates = sorted({point for quad in quads for point in quad})
    indices = {point: index for index, point in enumerate(coordinates)}
    vertices = tuple(Vec3(float(x), float(y), float(z)) for x, y, z in coordinates)
    triangles = []
    for quad in quads:
        a, b, c, d = (indices[point] for point in quad)
        triangles.extend(((a, b, c), (a, c, d)))
    mesh = TriangleMesh(
        solid_id, frame_id, length_unit, "BREP_BOOLEAN", source_digest,
        vertices, tuple(triangles),
    )
    validation = validate_triangle_mesh(mesh)
    if not (validation.valid and validation.watertight and validation.consistently_oriented):
        raise InvalidModelError("3D Boolean boundary mesh failed closed manifold validation: " + "; ".join(validation.issues))
    return mesh


def boolean_axis_aligned_brep_solids(
    solids: tuple[BRepSolid, ...],
    operation: BRepBooleanOperation,
    *,
    result_id_prefix: str = "boolean.result",
) -> BRepBooleanResult:
    """Evaluate set Boolean operations for 2..16 axis-aligned box BRep solids.

    The exact coordinate grid is partitioned at every input box boundary.
    UNION, INTERSECTION, first-minus-rest DIFFERENCE and odd/even XOR are
    evaluated cellwise. Face-connected output components are emitted as
    independent closed faceted BRep solids. Point/edge-only contacts therefore
    remain separate components rather than being silently welded.
    """
    if not isinstance(solids, tuple) or not 2 <= len(solids) <= _MAX_INPUTS:
        raise InvalidModelError(f"BRep Boolean requires an immutable tuple of 2..{_MAX_INPUTS} solids")
    if any(not isinstance(item, BRepSolid) for item in solids):
        raise InvalidModelError("BRep Boolean inputs must be BRepSolid records")
    if not isinstance(operation, BRepBooleanOperation):
        raise InvalidModelError("BRep Boolean operation must be a BRepBooleanOperation")
    if not isinstance(result_id_prefix, str) or not _ID.fullmatch(result_id_prefix):
        raise InvalidModelError("result_id_prefix must be a stable lowercase identifier")
    if len({item.solid_id for item in solids}) != len(solids):
        raise InvalidModelError("BRep Boolean input solid IDs must be unique")
    frame_unit = {(item.frame_id, item.length_unit) for item in solids}
    if len(frame_unit) != 1:
        raise InvalidModelError("BRep Boolean inputs must share the same frame and length unit")
    bounds = tuple(_box_bounds(item) for item in solids)
    xs = tuple(sorted({value for item in bounds for value in (item.minimum[0], item.maximum[0])}))
    ys = tuple(sorted({value for item in bounds for value in (item.minimum[1], item.maximum[1])}))
    zs = tuple(sorted({value for item in bounds for value in (item.minimum[2], item.maximum[2])}))
    cell_count = (len(xs)-1) * (len(ys)-1) * (len(zs)-1)
    if cell_count > _MAX_GRID_CELLS:
        raise InvalidModelError(f"BRep Boolean grid exceeds the {_MAX_GRID_CELLS}-cell resource limit")
    occupied: set[tuple[int, int, int]] = set()
    for i, j, k in product(range(len(xs)-1), range(len(ys)-1), range(len(zs)-1)):
        center = ((xs[i]+xs[i+1])/2, (ys[j]+ys[j+1])/2, (zs[k]+zs[k+1])/2)
        memberships = tuple(_inside(center, item) for item in bounds)
        if _operation_value(memberships, operation):
            occupied.add((i, j, k))
    source_ids = tuple(item.solid_id for item in solids)
    source_digests = tuple(item.source_geometry_sha256 for item in solids)
    source_pairs = tuple(zip(source_ids, source_digests))
    if operation is not BRepBooleanOperation.DIFFERENCE:
        source_pairs = tuple(sorted(source_pairs))
    digest_ids = tuple(pair[0] for pair in source_pairs)
    digest_sources = tuple(pair[1] for pair in source_pairs)
    components: list[BRepSolid] = []
    for index, cells in enumerate(_components(occupied)):
        component_payload = {
            "algorithm_version": "exact-axis-aligned-brep-box-grid-v1",
            "operation": operation.value,
            "input_solid_ids": list(digest_ids),
            "input_source_sha256": list(digest_sources),
            "cells": [list(cell) for cell in cells],
            "grid": [[str(value) for value in axis] for axis in (xs, ys, zs)],
        }
        component_digest = sha256(json.dumps(component_payload, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
        mesh = _component_mesh(
            cells, occupied, xs, ys, zs,
            solid_id=f"{result_id_prefix}.{index:03d}",
            frame_id=solids[0].frame_id,
            length_unit=solids[0].length_unit,
            source_digest=component_digest,
        )
        components.append(brep_from_triangle_mesh(mesh))
    component_tuple = tuple(components)
    result_digest = _result_digest(operation, digest_ids, digest_sources, cell_count, component_tuple)
    return BRepBooleanResult(
        operation, digest_ids, digest_sources, component_tuple, cell_count, result_digest,
    )


def _signed_mesh_volume(mesh: TriangleMesh) -> Fraction:
    total = Fraction(0)
    for face in mesh.triangles:
        points = tuple(
            tuple(_fraction(value) for value in (
                mesh.vertices[index].x, mesh.vertices[index].y, mesh.vertices[index].z
            ))
            for index in face
        )
        a, b, c = points
        cross = (
            b[1] * c[2] - b[2] * c[1],
            b[2] * c[0] - b[0] * c[2],
            b[0] * c[1] - b[1] * c[0],
        )
        total += sum(a[i] * cross[i] for i in range(3))
    return total / 6


def _split_boundary_shells(mesh: TriangleMesh) -> tuple[tuple[bool, TriangleMesh], ...]:
    """Split an oriented boundary mesh by shared edges; normalize each shell outward.

    The bool is True for a cavity boundary (negative orientation in the composed
    material mesh). Every extracted component is converted to a positive-volume
    standalone shell so it can be represented by the existing BRepSolid model.
    """
    edge_faces: dict[tuple[int, int], list[int]] = {}
    for face_index, face in enumerate(mesh.triangles):
        if len(set(face)) != 3:
            raise InvalidModelError("Boolean output contains a degenerate triangle")
        for a, b in ((face[0], face[1]), (face[1], face[2]), (face[2], face[0])):
            edge_faces.setdefault(tuple(sorted((a, b))), []).append(face_index)
    adjacency: dict[int, set[int]] = {i: set() for i in range(len(mesh.triangles))}
    for attached in edge_faces.values():
        if len(attached) != 2:
            raise InvalidModelError("Boolean output shell edge incidence is not exactly two")
        first, second = attached
        adjacency[first].add(second)
        adjacency[second].add(first)
    remaining = set(adjacency)
    components: list[tuple[bool, TriangleMesh]] = []
    while remaining:
        seed = min(remaining)
        remaining.remove(seed)
        face_ids = {seed}
        pending = [seed]
        while pending:
            current = pending.pop()
            for neighbor in adjacency[current]:
                if neighbor in remaining:
                    remaining.remove(neighbor)
                    face_ids.add(neighbor)
                    pending.append(neighbor)
        selected_faces = tuple(mesh.triangles[index] for index in sorted(face_ids))
        used_vertices = tuple(sorted({index for face in selected_faces for index in face}))
        remap = {old: new for new, old in enumerate(used_vertices)}
        vertices = tuple(mesh.vertices[index] for index in used_vertices)
        triangles = tuple(tuple(remap[index] for index in face) for face in selected_faces)
        component_id = f"{mesh.solid_id}.shell.{len(components):03d}"
        component_digest = sha256(json.dumps({
            "parent": mesh.source_geometry_sha256,
            "component": len(components),
            "triangles": [list(face) for face in triangles],
        }, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
        component_mesh = TriangleMesh(
            component_id, mesh.frame_id, mesh.length_unit, "BREP_BOOLEAN",
            component_digest, vertices, triangles,
        )
        signed_volume = _signed_mesh_volume(component_mesh)
        if signed_volume == 0:
            raise InvalidModelError("Boolean output contains a zero-volume boundary shell")
        is_cavity = signed_volume < 0
        if is_cavity:
            component_mesh = TriangleMesh(
                component_id, mesh.frame_id, mesh.length_unit, "BREP_BOOLEAN",
                component_digest, vertices,
                tuple((face[0], face[2], face[1]) for face in triangles),
            )
        validation = validate_triangle_mesh(component_mesh)
        if not (validation.valid and validation.watertight and validation.consistently_oriented):
            raise InvalidModelError(
                "Boolean output shell failed closed validation: " + "; ".join(validation.issues)
            )
        components.append((is_cavity, component_mesh))
    return tuple(components)


@dataclass(frozen=True, slots=True)
class BRepMultiShellBooleanResult:
    operation: BRepBooleanOperation
    input_solid_ids: tuple[str, ...]
    input_source_sha256: tuple[str, ...]
    components: tuple[BRepMultiShellSolid, ...]
    grid_cell_count: int
    result_sha256: str

    SCHEMA_VERSION: ClassVar[str] = "1.0"
    ALGORITHM_VERSION: ClassVar[str] = "exact-axis-aligned-multishell-brep-box-grid-v1"

    def __post_init__(self) -> None:
        if not isinstance(self.operation, BRepBooleanOperation):
            raise InvalidModelError("multi-shell BRep Boolean operation is unsupported")
        if not isinstance(self.input_solid_ids, tuple) or len(self.input_solid_ids) < 2:
            raise InvalidModelError("multi-shell BRep Boolean requires at least two input solid IDs")
        if len(self.input_solid_ids) != len(self.input_source_sha256):
            raise InvalidModelError("multi-shell Boolean input ID and digest counts must match")
        if any(not isinstance(item, str) or not _ID.fullmatch(item) for item in self.input_solid_ids):
            raise InvalidModelError("multi-shell Boolean input IDs must be stable identifiers")
        if len(set(self.input_solid_ids)) != len(self.input_solid_ids):
            raise InvalidModelError("multi-shell Boolean input solid IDs must be unique")
        if any(not isinstance(item, str) or not _SHA256.fullmatch(item) for item in self.input_source_sha256):
            raise InvalidModelError("multi-shell Boolean input digests must be lowercase SHA-256")
        if not isinstance(self.components, tuple) or any(
            not isinstance(item, BRepMultiShellSolid) for item in self.components
        ):
            raise InvalidModelError("multi-shell Boolean components must be immutable BRepMultiShellSolid records")
        if isinstance(self.grid_cell_count, bool) or not isinstance(self.grid_cell_count, int) or self.grid_cell_count < 0:
            raise InvalidModelError("multi-shell Boolean grid_cell_count must be a non-negative integer")
        if not isinstance(self.result_sha256, str) or not _SHA256.fullmatch(self.result_sha256):
            raise InvalidModelError("multi-shell Boolean result_sha256 must be lowercase SHA-256")
        if len({item.solid_id for item in self.components}) != len(self.components):
            raise InvalidModelError("multi-shell Boolean component IDs must be unique")
        expected = _multishell_result_digest(
            self.operation, self.input_solid_ids, self.input_source_sha256,
            self.grid_cell_count, self.components,
        )
        if self.result_sha256 != expected:
            raise InvalidModelError("multi-shell Boolean result digest does not match its content")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.SCHEMA_VERSION,
            "algorithm_version": self.ALGORITHM_VERSION,
            "operation": self.operation.value,
            "input_solid_ids": list(self.input_solid_ids),
            "input_source_sha256": list(self.input_source_sha256),
            "components": [item.to_dict() for item in self.components],
            "grid_cell_count": self.grid_cell_count,
            "result_sha256": self.result_sha256,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, object]) -> "BRepMultiShellBooleanResult":
        required = {
            "schema_version", "algorithm_version", "operation", "input_solid_ids",
            "input_source_sha256", "components", "grid_cell_count", "result_sha256",
        }
        if not isinstance(value, Mapping) or set(value) != required:
            raise InvalidModelError("BRepMultiShellBooleanResult snapshot has missing or unknown fields")
        if value["schema_version"] != cls.SCHEMA_VERSION or value["algorithm_version"] != cls.ALGORITHM_VERSION:
            raise InvalidModelError("unsupported BRepMultiShellBooleanResult version")
        try:
            operation = BRepBooleanOperation(value["operation"])
        except (TypeError, ValueError) as exc:
            raise InvalidModelError("unsupported multi-shell BRep Boolean operation") from exc
        for name in ("input_solid_ids", "input_source_sha256", "components"):
            if not isinstance(value[name], (list, tuple)):
                raise InvalidModelError(f"BRepMultiShellBooleanResult {name} must be an array")
        components = tuple(BRepMultiShellSolid.from_dict(item) for item in value["components"])
        return cls(
            operation, tuple(value["input_solid_ids"]), tuple(value["input_source_sha256"]),
            components, value["grid_cell_count"], value["result_sha256"],
        )


def _multishell_result_digest(
    operation: BRepBooleanOperation,
    input_ids: tuple[str, ...],
    input_digests: tuple[str, ...],
    cell_count: int,
    components: tuple[BRepMultiShellSolid, ...],
) -> str:
    payload = {
        "algorithm_version": BRepMultiShellBooleanResult.ALGORITHM_VERSION,
        "operation": operation.value,
        "input_solid_ids": list(input_ids),
        "input_source_sha256": list(input_digests),
        "grid_cell_count": cell_count,
        "component_digests": [item.source_geometry_sha256 for item in components],
    }
    return sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def boolean_axis_aligned_multishell_solids(
    solids: tuple[BRepMultiShellSolid, ...],
    operation: BRepBooleanOperation,
    *,
    result_id_prefix: str = "multishell.boolean.result",
) -> BRepMultiShellBooleanResult:
    """Exact-grid Boolean for axis-aligned box components with cavity boundaries.

    Each input aggregate must contain only axis-aligned box shells. Material
    membership is outer-box membership minus all cavity-box memberships.
    Output boundary shells are separated by shared edges and reassembled into
    one outer shell plus disjoint cavity shells per material component.
    """
    if not isinstance(solids, tuple) or not 2 <= len(solids) <= _MAX_INPUTS:
        raise InvalidModelError(f"multi-shell BRep Boolean requires an immutable tuple of 2..{_MAX_INPUTS} solids")
    if any(not isinstance(item, BRepMultiShellSolid) for item in solids):
        raise InvalidModelError("multi-shell BRep Boolean inputs must be BRepMultiShellSolid records")
    if not isinstance(operation, BRepBooleanOperation):
        raise InvalidModelError("multi-shell BRep Boolean operation must be a BRepBooleanOperation")
    if not isinstance(result_id_prefix, str) or not _ID.fullmatch(result_id_prefix):
        raise InvalidModelError("multi-shell result_id_prefix must be a stable lowercase identifier")
    if len({item.solid_id for item in solids}) != len(solids):
        raise InvalidModelError("multi-shell BRep Boolean input solid IDs must be unique")
    if len({(item.frame_id, item.length_unit) for item in solids}) != 1:
        raise InvalidModelError("multi-shell BRep Boolean inputs must share the same frame and length unit")

    input_bounds = []
    for solid in solids:
        outer_bounds = _box_bounds(solid.outer_shell)
        cavity_bounds = tuple(_box_bounds(item) for item in solid.cavity_shells)
        input_bounds.append((outer_bounds, cavity_bounds))
    xs = tuple(sorted({value for outer, cavities in input_bounds
                       for bounds in (outer, *cavities)
                       for value in (bounds.minimum[0], bounds.maximum[0])}))
    ys = tuple(sorted({value for outer, cavities in input_bounds
                       for bounds in (outer, *cavities)
                       for value in (bounds.minimum[1], bounds.maximum[1])}))
    zs = tuple(sorted({value for outer, cavities in input_bounds
                       for bounds in (outer, *cavities)
                       for value in (bounds.minimum[2], bounds.maximum[2])}))
    cell_count = (len(xs)-1) * (len(ys)-1) * (len(zs)-1)
    if cell_count > _MAX_GRID_CELLS:
        raise InvalidModelError(f"multi-shell BRep Boolean grid exceeds the {_MAX_GRID_CELLS}-cell resource limit")

    occupied: set[tuple[int, int, int]] = set()
    for i, j, k in product(range(len(xs)-1), range(len(ys)-1), range(len(zs)-1)):
        center = ((xs[i]+xs[i+1])/2, (ys[j]+ys[j+1])/2, (zs[k]+zs[k+1])/2)
        memberships = tuple(
            _inside(center, outer) and not any(_inside(center, cavity) for cavity in cavities)
            for outer, cavities in input_bounds
        )
        if _operation_value(memberships, operation):
            occupied.add((i, j, k))

    source_pairs = tuple((item.solid_id, item.source_geometry_sha256) for item in solids)
    if operation is not BRepBooleanOperation.DIFFERENCE:
        source_pairs = tuple(sorted(source_pairs))
    input_ids = tuple(item[0] for item in source_pairs)
    input_digests = tuple(item[1] for item in source_pairs)
    outputs: list[BRepMultiShellSolid] = []
    for component_index, cells in enumerate(_components(occupied)):
        payload = {
            "algorithm_version": BRepMultiShellBooleanResult.ALGORITHM_VERSION,
            "operation": operation.value,
            "input_solid_ids": list(input_ids),
            "input_source_sha256": list(input_digests),
            "cells": [list(cell) for cell in cells],
            "grid": [[str(value) for value in axis] for axis in (xs, ys, zs)],
        }
        digest = sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
        mesh = _component_mesh(
            cells, occupied, xs, ys, zs,
            solid_id=f"{result_id_prefix}.{component_index:03d}",
            frame_id=solids[0].frame_id,
            length_unit=solids[0].length_unit,
            source_digest=digest,
        )
        shells = _split_boundary_shells(mesh)
        outer_shells = [(is_cavity, shell_mesh) for is_cavity, shell_mesh in shells if not is_cavity]
        cavity_shells = [(is_cavity, shell_mesh) for is_cavity, shell_mesh in shells if is_cavity]
        if not outer_shells:
            raise InvalidModelError("Boolean material component has no positively-oriented outer shell")
        positive_breps: list[tuple[TriangleMesh, BRepSolid]] = []
        for outer_index, (_, shell_mesh) in enumerate(outer_shells):
            brep = brep_from_triangle_mesh(shell_mesh)
            positive_breps.append((shell_mesh, brep))
        assigned: list[list[BRepSolid]] = [[] for _ in positive_breps]
        for cavity_index, (_, cavity_mesh) in enumerate(cavity_shells):
            candidates = []
            for outer_index, (outer_mesh, _) in enumerate(positive_breps):
                classifications = tuple(_point_inside_mesh(vertex, outer_mesh) for vertex in cavity_mesh.vertices)
                if all(value is True for value in classifications):
                    candidates.append(outer_index)
            if len(candidates) != 1:
                raise InvalidModelError("Boolean cavity boundary must be strictly contained by exactly one outer shell")
            normalized_id = f"{result_id_prefix}.{component_index:03d}.cavity.{cavity_index:03d}"
            normalized = TriangleMesh(
                normalized_id, cavity_mesh.frame_id, cavity_mesh.length_unit,
                cavity_mesh.source_kind, cavity_mesh.source_geometry_sha256,
                cavity_mesh.vertices, cavity_mesh.triangles,
            )
            assigned[candidates[0]].append(brep_from_triangle_mesh(normalized))
        for outer_index, (outer_mesh, outer_brep) in enumerate(positive_breps):
            aggregate_id = f"{result_id_prefix}.{component_index:03d}.{outer_index:03d}"
            outputs.append(BRepMultiShellSolid(
                aggregate_id, outer_brep, tuple(assigned[outer_index])
            ))

    components = tuple(outputs)
    result_digest = _multishell_result_digest(operation, input_ids, input_digests, cell_count, components)
    return BRepMultiShellBooleanResult(
        operation, input_ids, input_digests, components, cell_count, result_digest,
    )
