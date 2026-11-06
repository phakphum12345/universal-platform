"""Deterministic diagnostic topology analysis for indexed triangle meshes.

This layer is intentionally separate from validate_triangle_mesh. It reports
shell, vertex-link and coordinate-coincidence diagnostics without modifying
vertices, welding, snapping, or claiming geometric self-intersection freedom.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from json import dumps
from math import dist, floor, isfinite
from typing import Any, ClassVar, Mapping

from .errors import InvalidModelError
from .mesh import TriangleMesh
from .quantity import LENGTH, Quantity

MAX_COINCIDENT_NEIGHBOR_COMPARISONS = 5_000_000
_ANALYSIS_FIELDS = {
    "schema_version", "solid_id", "frame_id", "length_unit", "source_geometry_sha256", "mesh_snapshot_sha256", "vertex_count", "triangle_count", "face_component_count", "face_components",
    "exact_duplicate_vertex_groups", "near_coincident_vertex_groups",
    "nonmanifold_vertex_indices", "unused_vertex_indices",
    "coincident_tolerance", "diagnostic_status", "self_intersection_status", "issues",
}


def _finite_nonnegative(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(float(value)):
        raise InvalidModelError(f"{label} must be a finite number")
    result = float(value)
    if result < 0:
        raise InvalidModelError(f"{label} cannot be negative")
    return result


def _integer_tuple(value: Any, label: str, *, minimum_length: int = 0) -> tuple[int, ...]:
    if not isinstance(value, (tuple, list)):
        raise InvalidModelError(f"{label} must be an array")
    result = tuple(value)
    if len(result) < minimum_length or any(
        isinstance(item, bool) or not isinstance(item, int) or item < 0 for item in result
    ):
        raise InvalidModelError(f"{label} contains invalid indices")
    if tuple(sorted(set(result))) != result:
        raise InvalidModelError(f"{label} must be sorted and unique")
    return result


def _groups(value: Any, label: str, *, minimum_group_length: int) -> tuple[tuple[int, ...], ...]:
    if not isinstance(value, (tuple, list)):
        raise InvalidModelError(f"{label} must be an array")
    result = tuple(
        _integer_tuple(group, f"{label} group", minimum_length=minimum_group_length)
        for group in value
    )
    if tuple(sorted(result, key=lambda group: group[0])) != result:
        raise InvalidModelError(f"{label} must be ordered by the first vertex/face index")
    if len(set(result)) != len(result):
        raise InvalidModelError(f"{label} contains duplicate groups")
    return result


@dataclass(frozen=True, slots=True)
class MeshTopologyAnalysis:
    """Immutable diagnostic snapshot; UNKNOWN self-intersection is never PASS."""

    face_components: tuple[tuple[int, ...], ...]
    exact_duplicate_vertex_groups: tuple[tuple[int, ...], ...]
    near_coincident_vertex_groups: tuple[tuple[int, ...], ...]
    nonmanifold_vertex_indices: tuple[int, ...]
    unused_vertex_indices: tuple[int, ...]
    coincident_tolerance: float
    diagnostic_status: str
    self_intersection_status: str
    issues: tuple[str, ...]

    SCHEMA_VERSION: ClassVar[str] = "1.0"

    def __post_init__(self) -> None:
        if not isinstance(self.face_components, tuple):
            raise InvalidModelError("face_components must be an immutable tuple")
        normalized_components = _groups(self.face_components, "face_components", minimum_group_length=1)
        if normalized_components != self.face_components:
            raise InvalidModelError("face_components must be normalized")
        for label, groups in (
            ("exact_duplicate_vertex_groups", self.exact_duplicate_vertex_groups),
            ("near_coincident_vertex_groups", self.near_coincident_vertex_groups),
        ):
            if not isinstance(groups, tuple) or _groups(groups, label, minimum_group_length=2) != groups:
                raise InvalidModelError(f"{label} must be normalized immutable groups")
        for label, values in (
            ("nonmanifold_vertex_indices", self.nonmanifold_vertex_indices),
            ("unused_vertex_indices", self.unused_vertex_indices),
        ):
            if not isinstance(values, tuple) or _integer_tuple(values, label) != values:
                raise InvalidModelError(f"{label} must be normalized immutable indices")
        tolerance = _finite_nonnegative(self.coincident_tolerance, "coincident_tolerance")
        object.__setattr__(self, "coincident_tolerance", tolerance)
        if self.diagnostic_status not in {"ISSUES_FOUND", "NO_TOPOLOGY_ISSUES_FOUND"}:
            raise InvalidModelError("Unsupported mesh topology diagnostic_status")
        if self.self_intersection_status != "UNKNOWN":
            raise InvalidModelError("self_intersection_status must remain UNKNOWN in schema v1.0")
        if not isinstance(self.issues, tuple) or any(not isinstance(issue, str) or not issue for issue in self.issues):
            raise InvalidModelError("issues must be a tuple of non-empty diagnostic codes")
        expected_status = "ISSUES_FOUND" if self.issues else "NO_TOPOLOGY_ISSUES_FOUND"
        if self.diagnostic_status != expected_status:
            raise InvalidModelError("diagnostic_status does not match the issue list")
        if tuple(sorted(set(self.issues))) != self.issues:
            raise InvalidModelError("issues must be sorted and unique")

    @property
    def face_component_count(self) -> int:
        return len(self.face_components)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.SCHEMA_VERSION,
            "face_component_count": self.face_component_count,
            "face_components": [list(group) for group in self.face_components],
            "exact_duplicate_vertex_groups": [list(group) for group in self.exact_duplicate_vertex_groups],
            "near_coincident_vertex_groups": [list(group) for group in self.near_coincident_vertex_groups],
            "nonmanifold_vertex_indices": list(self.nonmanifold_vertex_indices),
            "unused_vertex_indices": list(self.unused_vertex_indices),
            "coincident_tolerance": self.coincident_tolerance,
            "diagnostic_status": self.diagnostic_status,
            "self_intersection_status": self.self_intersection_status,
            "issues": list(self.issues),
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "MeshTopologyAnalysis":
        if not isinstance(value, Mapping) or set(value) != _ANALYSIS_FIELDS:
            raise InvalidModelError("MeshTopologyAnalysis snapshot has missing or unknown fields")
        if value["schema_version"] != cls.SCHEMA_VERSION:
            raise InvalidModelError("Unsupported MeshTopologyAnalysis schema_version")
        components = _groups(value["face_components"], "face_components", minimum_group_length=1)
        if value["face_component_count"] != len(components):
            raise InvalidModelError("face_component_count does not match face_components")
        issues = value["issues"]
        if not isinstance(issues, (list, tuple)):
            raise InvalidModelError("issues must be an array")
        return cls(
            face_components=components,
            exact_duplicate_vertex_groups=_groups(
                value["exact_duplicate_vertex_groups"], "exact_duplicate_vertex_groups", minimum_group_length=2
            ),
            near_coincident_vertex_groups=_groups(
                value["near_coincident_vertex_groups"], "near_coincident_vertex_groups", minimum_group_length=2
            ),
            nonmanifold_vertex_indices=_integer_tuple(value["nonmanifold_vertex_indices"], "nonmanifold_vertex_indices"),
            unused_vertex_indices=_integer_tuple(value["unused_vertex_indices"], "unused_vertex_indices"),
            coincident_tolerance=value["coincident_tolerance"],
            diagnostic_status=value["diagnostic_status"],
            self_intersection_status=value["self_intersection_status"],
            issues=tuple(issues),
        )


def _valid_face(face: tuple[int, int, int], vertex_count: int) -> bool:
    return (
        len(face) == 3 and len(set(face)) == 3
        and all(0 <= index < vertex_count for index in face)
    )


def _face_components(mesh: TriangleMesh) -> tuple[tuple[int, ...], ...]:
    edge_faces: dict[tuple[int, int], list[int]] = {}
    valid_faces: dict[int, tuple[int, int, int]] = {}
    for face_index, face in enumerate(mesh.triangles):
        if not _valid_face(face, len(mesh.vertices)):
            continue
        valid_faces[face_index] = face
        for start, end in ((face[0], face[1]), (face[1], face[2]), (face[2], face[0])):
            edge_faces.setdefault((min(start, end), max(start, end)), []).append(face_index)

    adjacency: dict[int, set[int]] = {face_index: set() for face_index in valid_faces}
    for uses in edge_faces.values():
        for face_index in uses:
            adjacency[face_index].update(other for other in uses if other != face_index)

    visited: set[int] = set()
    components: list[tuple[int, ...]] = []
    for start in sorted(valid_faces):
        if start in visited:
            continue
        stack = [start]
        visited.add(start)
        component: list[int] = []
        while stack:
            current = stack.pop()
            component.append(current)
            for neighbor in sorted(adjacency[current], reverse=True):
                if neighbor not in visited:
                    visited.add(neighbor)
                    stack.append(neighbor)
        components.append(tuple(sorted(component)))
    return tuple(sorted(components, key=lambda component: component[0]))


def _nonmanifold_vertices(mesh: TriangleMesh) -> tuple[int, ...]:
    link_edges: dict[int, list[tuple[int, int]]] = {}
    for face in mesh.triangles:
        if not _valid_face(face, len(mesh.vertices)):
            continue
        for vertex in face:
            others = tuple(index for index in face if index != vertex)
            link_edges.setdefault(vertex, []).append((others[0], others[1]))

    invalid: list[int] = []
    for vertex, edges in sorted(link_edges.items()):
        adjacency: dict[int, set[int]] = {}
        degree: dict[int, int] = {}
        for first, second in edges:
            adjacency.setdefault(first, set()).add(second)
            adjacency.setdefault(second, set()).add(first)
            degree[first] = degree.get(first, 0) + 1
            degree[second] = degree.get(second, 0) + 1
        nodes = set(adjacency)
        visited: set[int] = set()
        stack = [min(nodes)]
        visited.add(stack[0])
        while stack:
            current = stack.pop()
            for neighbor in sorted(adjacency[current], reverse=True):
                if neighbor not in visited:
                    visited.add(neighbor)
                    stack.append(neighbor)
        degrees = tuple(degree[node] for node in nodes)
        is_cycle = len(nodes) >= 3 and len(visited) == len(nodes) and all(value == 2 for value in degrees)
        endpoints = sum(value == 1 for value in degrees)
        is_path = (
            len(nodes) >= 2 and len(visited) == len(nodes) and endpoints == 2
            and all(value in {1, 2} for value in degrees)
        )
        if not (is_cycle or is_path):
            invalid.append(vertex)
    return tuple(invalid)


def _near_coincident_groups(
    mesh: TriangleMesh, tolerance: float, max_neighbor_comparisons: int
) -> tuple[tuple[int, ...], ...]:
    if tolerance == 0.0:
        return ()
    parent = list(range(len(mesh.vertices)))

    def find(index: int) -> int:
        while parent[index] != index:
            parent[index] = parent[parent[index]]
            index = parent[index]
        return index

    def union(first: int, second: int) -> None:
        root_first, root_second = find(first), find(second)
        if root_first != root_second:
            low, high = sorted((root_first, root_second))
            parent[high] = low

    buckets: dict[tuple[int, int, int], list[int]] = {}
    comparisons = 0
    tolerance_squared = tolerance * tolerance
    for index, vertex in enumerate(mesh.vertices):
        try:
            cell = (
                floor(vertex.x / tolerance),
                floor(vertex.y / tolerance),
                floor(vertex.z / tolerance),
            )
        except (OverflowError, ValueError) as exc:
            raise InvalidModelError("coincident_tolerance is below coordinate bucket resolution") from exc
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for dz in (-1, 0, 1):
                    neighbor = (cell[0]+dx, cell[1]+dy, cell[2]+dz)
                    for other in buckets.get(neighbor, ()):
                        comparisons += 1
                        if comparisons > max_neighbor_comparisons:
                            raise InvalidModelError("near-coincident analysis exceeded its neighbor-comparison limit")
                        first = mesh.vertices[index]
                        second = mesh.vertices[other]
                        if dist((first.x, first.y, first.z), (second.x, second.y, second.z)) <= tolerance:
                            union(index, other)
        buckets.setdefault(cell, []).append(index)

    groups: dict[int, list[int]] = {}
    for index in range(len(mesh.vertices)):
        groups.setdefault(find(index), []).append(index)
    result = []
    for group in groups.values():
        if len(group) < 2:
            continue
        first_point = mesh.vertices[group[0]]
        if all(
            mesh.vertices[index].x == first_point.x
            and mesh.vertices[index].y == first_point.y
            and mesh.vertices[index].z == first_point.z
            for index in group
        ):
            continue
        result.append(tuple(group))
    return tuple(sorted(result, key=lambda group: group[0]))


def analyze_mesh_topology(
    mesh: TriangleMesh,
    *,
    coincident_tolerance: float = 0.0,
    max_neighbor_comparisons: int = MAX_COINCIDENT_NEIGHBOR_COMPARISONS,
) -> MeshTopologyAnalysis:
    """Analyze indexed shell and vertex topology without modifying the source mesh.

    The tolerance is an absolute Euclidean distance in mesh.length_unit. It is
    diagnostic only: no coordinates are welded, snapped or repaired.
    """
    if not isinstance(mesh, TriangleMesh):
        raise InvalidModelError("analyze_mesh_topology requires a TriangleMesh")
    tolerance = _finite_nonnegative(coincident_tolerance, "coincident_tolerance")
    if isinstance(max_neighbor_comparisons, bool) or not isinstance(max_neighbor_comparisons, int):
        raise InvalidModelError("max_neighbor_comparisons must be an integer")
    if not 1 <= max_neighbor_comparisons <= MAX_COINCIDENT_NEIGHBOR_COMPARISONS:
        raise InvalidModelError(
            f"max_neighbor_comparisons must be from 1 to {MAX_COINCIDENT_NEIGHBOR_COMPARISONS}"
        )

    components = _face_components(mesh)
    coordinate_groups: dict[tuple[float, float, float], list[int]] = {}
    for index, vertex in enumerate(mesh.vertices):
        coordinate_groups.setdefault((vertex.x, vertex.y, vertex.z), []).append(index)
    exact_duplicates = tuple(sorted(
        (tuple(indices) for indices in coordinate_groups.values() if len(indices) > 1),
        key=lambda group: group[0],
    ))
    near_groups = _near_coincident_groups(mesh, tolerance, max_neighbor_comparisons)
    nonmanifold = _nonmanifold_vertices(mesh)
    used_vertices = {
        index for face in mesh.triangles if _valid_face(face, len(mesh.vertices)) for index in face
    }
    unused = tuple(index for index in range(len(mesh.vertices)) if index not in used_vertices)

    issues: list[str] = []
    if len(components) > 1:
        issues.append(f"DISCONNECTED_FACE_COMPONENTS:{len(components)}")
    for group in exact_duplicates:
        issues.append("DUPLICATE_VERTEX_COORDINATES:" + ",".join(map(str, group)))
    for group in near_groups:
        issues.append("NEAR_COINCIDENT_VERTEX_COORDINATES:" + ",".join(map(str, group)))
    for index in nonmanifold:
        issues.append(f"NONMANIFOLD_VERTEX_FAN:{index}")
    for index in unused:
        issues.append(f"UNUSED_VERTEX:{index}")
    normalized_issues = tuple(sorted(issues))
    return MeshTopologyAnalysis(
        face_components=components,
        exact_duplicate_vertex_groups=exact_duplicates,
        near_coincident_vertex_groups=near_groups,
        nonmanifold_vertex_indices=nonmanifold,
        unused_vertex_indices=unused,
        coincident_tolerance=tolerance,
        diagnostic_status="ISSUES_FOUND" if normalized_issues else "NO_TOPOLOGY_ISSUES_FOUND",
        self_intersection_status="UNKNOWN",
        issues=normalized_issues,
    )
