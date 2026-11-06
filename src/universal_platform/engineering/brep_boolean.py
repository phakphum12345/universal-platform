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
        if value not in (xs[0], xs[1]) if axis == 0 else value not in (ys[0], ys[1]) if axis == 1 else value not in (zs[0], zs[1]):
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
    digest_ids = source_ids if operation is BRepBooleanOperation.DIFFERENCE else tuple(sorted(source_ids))
    digest_sources = source_digests if operation is BRepBooleanOperation.DIFFERENCE else tuple(sorted(source_digests))
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
