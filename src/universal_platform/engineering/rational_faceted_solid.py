"""Versioned exact-rational faceted solid artifact (v1).

The profile is additive to legacy binary64 mesh/B-rep formats. This first
implementation accepts one closed, connected, outward-oriented outer shell.
Cavity shells and ambiguous contact configurations are rejected until their
containment semantics have an independently verified implementation.
"""
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from hashlib import sha256
from itertools import combinations
import json
import re
from typing import Any, ClassVar, Mapping

from .errors import InvalidModelError

RationalPoint3 = tuple[Fraction, Fraction, Fraction]
_ID = re.compile(r"^[a-z0-9]+(?:[._/-][a-z0-9]+)*$")
_DIGEST = re.compile(r"^[0-9a-f]{64}$")
_MAX_VERTICES = 100_000
_MAX_TRIANGLES = 200_000
_MAX_PAIR_CHECKS = 5_000_000
_MAX_AGGREGATE_RATIONAL_BITS = 64_000_000
_MAX_SOLID_ID_CHARS = 128
_MAX_FRAME_ID_CHARS = 128
_MAX_LENGTH_UNIT_CHARS = 64
_MAX_SOURCE_ID_CHARS = 256
_MAX_PROVENANCE_RECORDS = 4096
_MAX_METADATA_CHARS = 1_048_576
_FIELDS = {
    "schema_version", "profile", "solid_id", "frame_id", "length_unit",
    "vertices", "triangles", "shells", "source_provenance",
    "algorithm_version", "predicate_version", "resource_counters",
    "exact_signed_volume", "result_sha256",
}


def _cross(a: RationalPoint3, b: RationalPoint3) -> RationalPoint3:
    return (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])


def _sub(a: RationalPoint3, b: RationalPoint3) -> RationalPoint3:
    return (a[0]-b[0], a[1]-b[1], a[2]-b[2])


def _dot(a: RationalPoint3, b: RationalPoint3) -> Fraction:
    return a[0]*b[0] + a[1]*b[1] + a[2]*b[2]


def _volume6(points: tuple[RationalPoint3, RationalPoint3, RationalPoint3]) -> Fraction:
    return _dot(points[0], _cross(points[1], points[2]))


def _rational_pair(value: Fraction) -> list[str]:
    return [str(value.numerator), str(value.denominator)]


def _validate_resource_limits(max_coordinate_bits: object, max_pairwise_checks: object) -> None:
    for label, value, ceiling in (
        ("max_coordinate_bits", max_coordinate_bits, 16384),
        ("max_pairwise_checks", max_pairwise_checks, _MAX_PAIR_CHECKS),
    ):
        if isinstance(value, bool) or not isinstance(value, int) or value < 1:
            raise InvalidModelError(f"{label} must be a positive integer")
        if value > ceiling:
            raise InvalidModelError("resource limit exceeds the supported hard ceiling")


def _decimal_digit_ceiling(max_bits: int) -> int:
    # ceil(max_bits * log10(2)); 30103/100000 is a safe upper bound.
    return max(1, (max_bits * 30103 + 99999) // 100000)


def _parse_integer_string(value: object, label: str, max_bits: int) -> int:
    if not isinstance(value, str):
        raise InvalidModelError(f"{label} must be a canonical decimal integer string")
    digits = len(value) - (1 if value.startswith("-") else 0)
    if digits > _decimal_digit_ceiling(max_bits):
        raise InvalidModelError(f"{label} exceeds max_coordinate_bits before integer conversion")
    if not re.fullmatch(r"(?:0|-?[1-9][0-9]*)", value):
        raise InvalidModelError(f"{label} must be a canonical decimal integer string")
    # Parse bounded chunks so valid values near the 16,384-bit hard ceiling
    # do not depend on Python's process-wide decimal-string conversion limit.
    negative = value.startswith("-")
    digits_text = value[1:] if negative else value
    first_width = len(digits_text) % 9 or 9
    try:
        result = int(digits_text[:first_width])
        for offset in range(first_width, len(digits_text), 9):
            result = result * 1_000_000_000 + int(digits_text[offset:offset + 9])
        parsed = -result if negative else result
        if abs(parsed).bit_length() > max_bits:
            raise InvalidModelError(f"{label} exceeded max_coordinate_bits")
        return parsed
    except (ValueError, OverflowError) as exc:
        raise InvalidModelError(f"{label} is not a supported decimal integer") from exc


def _parse_rational(value: object, label: str, max_bits: int,
                    aggregate_budget: list[int] | None = None) -> Fraction:
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        raise InvalidModelError(f"{label} must be a [numerator, denominator] pair")
    numerator = _parse_integer_string(value[0], f"{label} numerator", max_bits)
    denominator = _parse_integer_string(value[1], f"{label} denominator", max_bits)
    if denominator <= 0:
        raise InvalidModelError(f"{label} denominator must be positive")
    numerator_bits = abs(numerator).bit_length()
    denominator_bits = denominator.bit_length()
    if numerator_bits > max_bits or denominator_bits > max_bits:
        raise InvalidModelError(f"{label} exceeded max_coordinate_bits")
    if aggregate_budget is not None:
        next_total = aggregate_budget[0] + numerator_bits + denominator_bits
        if next_total > _MAX_AGGREGATE_RATIONAL_BITS:
            raise InvalidModelError("aggregate rational bit budget exceeded")
        aggregate_budget[0] = next_total
    result = Fraction(numerator, denominator)
    if (result.numerator, result.denominator) != (numerator, denominator):
        raise InvalidModelError(f"{label} must be reduced to canonical form")
    return result


def _axes_overlap(first: tuple[RationalPoint3, ...],
                  second: tuple[RationalPoint3, ...], *,
                  touching_is_overlap: bool = True) -> bool:
    """Conservative exact SAT test; optionally classify touching as overlap."""
    edges_a = tuple(_sub(first[(i+1)%3], first[i]) for i in range(3))
    edges_b = tuple(_sub(second[(i+1)%3], second[i]) for i in range(3))
    normal_a = _cross(edges_a[0], edges_a[1])
    normal_b = _cross(edges_b[0], edges_b[1])
    axes = [normal_a, normal_b]
    axes.extend(_cross(a, b) for a in edges_a for b in edges_b)
    axes.extend(_cross(normal_a, edge) for edge in edges_a)
    axes.extend(_cross(normal_b, edge) for edge in edges_b)
    for axis in axes:
        if axis == (0, 0, 0):
            continue
        a_values = tuple(_dot(point, axis) for point in first)
        b_values = tuple(_dot(point, axis) for point in second)
        if touching_is_overlap:
            separated = max(a_values) < min(b_values) or max(b_values) < min(a_values)
        else:
            separated = max(a_values) <= min(b_values) or max(b_values) <= min(a_values)
        if separated:
            return False
    return True


def _canonical_payload(
    solid_id: str, frame_id: str, length_unit: str,
    vertices: tuple[RationalPoint3, ...],
    triangles: tuple[tuple[int, int, int], ...],
    source_provenance: tuple[tuple[str, str], ...],
    pair_checks: int, volume: Fraction,
) -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "profile": "RATIONAL_FACETED_SOLID_V1",
        "solid_id": solid_id,
        "frame_id": frame_id,
        "length_unit": length_unit,
        "vertices": [[_rational_pair(value) for value in point] for point in vertices],
        "triangles": [list(face) for face in triangles],
        "shells": [{"shell_id": "outer", "role": "OUTER",
                    "triangle_indices": list(range(len(triangles))),
                    "parent_outer_shell_id": None}],
        "source_provenance": [
            {"source_id": source_id, "source_sha256": digest}
            for source_id, digest in source_provenance
        ],
        "algorithm_version": "exact-rational-faceted-solid-v1",
        "predicate_version": "exact-fraction-sat-v1",
        "resource_counters": {
            "vertex_count": len(vertices), "triangle_count": len(triangles),
            "self_intersection_pair_checks": pair_checks,
        },
        "exact_signed_volume": _rational_pair(volume),
    }


@dataclass(frozen=True, slots=True)
class RationalFacetedSolid:
    """Immutable exact-coordinate solid with one validated outer shell.

    The exact pairwise SAT gate is conservative: it rejects unresolved
    intersections. It does not claim support for cavities, tangencies,
    branching, or nested material islands.
    """

    solid_id: str
    frame_id: str
    length_unit: str
    vertices: tuple[RationalPoint3, ...]
    triangles: tuple[tuple[int, int, int], ...]
    source_provenance: tuple[tuple[str, str], ...] = ()
    max_coordinate_bits: int = 4096
    max_pairwise_checks: int = _MAX_PAIR_CHECKS

    SCHEMA_VERSION: ClassVar[str] = "1.0"
    PROFILE: ClassVar[str] = "RATIONAL_FACETED_SOLID_V1"
    ALGORITHM_VERSION: ClassVar[str] = "exact-rational-faceted-solid-v1"
    PREDICATE_VERSION: ClassVar[str] = "exact-fraction-sat-v1"

    def __post_init__(self) -> None:
        for label, value, ceiling in (
            ("solid_id", self.solid_id, _MAX_SOLID_ID_CHARS),
            ("frame_id", self.frame_id, _MAX_FRAME_ID_CHARS),
            ("length_unit", self.length_unit, _MAX_LENGTH_UNIT_CHARS),
        ):
            if not isinstance(value, str) or not value.strip():
                raise InvalidModelError(f"{label} is required")
            if len(value) > ceiling:
                raise InvalidModelError(f"{label} exceeds its maximum length")
        if not _ID.fullmatch(self.solid_id):
            raise InvalidModelError("solid_id must be a stable lowercase identifier")
        _validate_resource_limits(self.max_coordinate_bits, self.max_pairwise_checks)
        if not isinstance(self.vertices, tuple) or not 4 <= len(self.vertices) <= _MAX_VERTICES:
            raise InvalidModelError("vertices must contain 4..100000 exact points")
        if not isinstance(self.triangles, tuple) or not 4 <= len(self.triangles) <= _MAX_TRIANGLES:
            raise InvalidModelError("triangles must contain 4..200000 faces")
        if any(not isinstance(point, tuple) or len(point) != 3
               or any(not isinstance(value, Fraction) for value in point)
               for point in self.vertices):
            raise InvalidModelError("vertices must contain exact Fraction 3D points")
        if len(set(self.vertices)) != len(self.vertices):
            raise InvalidModelError("duplicate exact vertices are not canonical")
        if tuple(sorted(self.vertices)) != self.vertices:
            raise InvalidModelError("vertices must be lexicographically canonical")
        aggregate_bits = sum(
            abs(value.numerator).bit_length() + value.denominator.bit_length()
            for point in self.vertices for value in point
        )
        if aggregate_bits > _MAX_AGGREGATE_RATIONAL_BITS:
            raise InvalidModelError("aggregate rational bit budget exceeded")
        for face in self.triangles:
            if (not isinstance(face, tuple) or len(face) != 3
                    or any(isinstance(index, bool) or not isinstance(index, int)
                           or not 0 <= index < len(self.vertices) for index in face)
                    or len(set(face)) != 3):
                raise InvalidModelError("each triangle must contain three distinct in-range indices")
            points = tuple(self.vertices[index] for index in face)
            if _cross(_sub(points[1], points[0]), _sub(points[2], points[0])) == (0, 0, 0):
                raise InvalidModelError("degenerate rational triangle is not permitted")
        if not isinstance(self.source_provenance, tuple):
            raise InvalidModelError("source_provenance must be an immutable tuple")
        if len(self.source_provenance) > _MAX_PROVENANCE_RECORDS:
            raise InvalidModelError("source provenance record count exceeded hard limit")
        metadata_chars = len(self.solid_id) + len(self.frame_id) + len(self.length_unit)
        for item in self.source_provenance:
            if not isinstance(item, tuple) or len(item) != 2:
                raise InvalidModelError("source provenance entries must be (source_id, sha256) pairs")
            source_id, digest = item
            if (not isinstance(source_id, str) or len(source_id) > _MAX_SOURCE_ID_CHARS
                    or not _ID.fullmatch(source_id)
                    or not isinstance(digest, str) or not _DIGEST.fullmatch(digest)):
                raise InvalidModelError("source provenance requires bounded stable IDs and lowercase SHA-256")
            metadata_chars += len(source_id) + len(digest)
        if metadata_chars > _MAX_METADATA_CHARS:
            raise InvalidModelError("aggregate metadata character budget exceeded")
        if tuple(sorted(set(self.source_provenance))) != self.source_provenance:
            raise InvalidModelError("source provenance must be sorted and unique")

        # Closed, consistently oriented edge incidence and edge connectivity.
        incidence: dict[tuple[int, int], list[tuple[int, int, int]]] = {}
        for face_index, (a, b, c) in enumerate(self.triangles):
            for start, end in ((a, b), (b, c), (c, a)):
                key = (min(start, end), max(start, end))
                incidence.setdefault(key, []).append((face_index, start, end))
        if any(len(uses) != 2 for uses in incidence.values()):
            raise InvalidModelError("every rational shell edge must have exactly two incident faces")
        for uses in incidence.values():
            if uses[0][1:] != (uses[1][2], uses[1][1]):
                raise InvalidModelError("rational shell edge uses must have opposite orientation")
        adjacency = [set() for _ in self.triangles]
        for uses in incidence.values():
            first, second = uses[0][0], uses[1][0]
            adjacency[first].add(second)
            adjacency[second].add(first)
        reached = {0}
        stack = [0]
        while stack:
            current = stack.pop()
            for neighbor in adjacency[current] - reached:
                reached.add(neighbor)
                stack.append(neighbor)
        if len(reached) != len(self.triangles):
            raise InvalidModelError("rational outer shell must be edge-connected")

        volume = sum((_volume6(tuple(self.vertices[index] for index in face))
                      for face in self.triangles), Fraction(0)) / 6
        if volume <= 0:
            raise InvalidModelError("rational outer shell must have positive exact signed volume")

        pair_checks = len(self.triangles) * (len(self.triangles) - 1) // 2
        if pair_checks > self.max_pairwise_checks:
            raise InvalidModelError("rational self-intersection pair budget exceeded")
        # Non-adjacent intersections are rejected. Shared-edge adjacent pairs
        # are permitted only when their planes differ or their coplanar third
        # vertices lie on opposite sides of the shared edge.
        for first_index, second_index in combinations(range(len(self.triangles)), 2):
            first_face, second_face = self.triangles[first_index], self.triangles[second_index]
            shared = set(first_face) & set(second_face)
            if len(shared) == 2:
                shared_edge = tuple(shared)
                third_a = next(index for index in first_face if index not in shared)
                third_b = next(index for index in second_face if index not in shared)
                pa, pb = (self.vertices[index] for index in shared_edge)
                da = _cross(_sub(pb, pa), _sub(self.vertices[third_a], pa))
                db = _cross(_sub(pb, pa), _sub(self.vertices[third_b], pa))
                if _cross(da, db) == (0, 0, 0) and _dot(da, db) > 0:
                    raise InvalidModelError("coplanar adjacent rational faces overlap")
                continue
            first_points = tuple(self.vertices[index] for index in first_face)
            second_points = tuple(self.vertices[index] for index in second_face)
            if _axes_overlap(first_points, second_points,
                             touching_is_overlap=not bool(shared)):
                raise InvalidModelError("rational self-intersection or unsupported contact detected")

    @property
    def exact_signed_volume(self) -> Fraction:
        return sum((_volume6(tuple(self.vertices[index] for index in face))
                    for face in self.triangles), Fraction(0)) / 6

    @property
    def self_intersection_pair_checks(self) -> int:
        return len(self.triangles) * (len(self.triangles) - 1) // 2

    def to_dict(self) -> dict[str, Any]:
        payload = _canonical_payload(
            self.solid_id, self.frame_id, self.length_unit, self.vertices,
            self.triangles, self.source_provenance, self.self_intersection_pair_checks,
            self.exact_signed_volume,
        )
        digest = sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        return {**payload, "result_sha256": digest}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any], *,
                  max_coordinate_bits: int = 4096,
                  max_pairwise_checks: int = _MAX_PAIR_CHECKS) -> "RationalFacetedSolid":
        if not isinstance(value, Mapping) or set(value) != _FIELDS:
            raise InvalidModelError("RationalFacetedSolid snapshot has missing or unknown fields")
        _validate_resource_limits(max_coordinate_bits, max_pairwise_checks)
        if (value["schema_version"] != cls.SCHEMA_VERSION
                or value["profile"] != cls.PROFILE
                or value["algorithm_version"] != cls.ALGORITHM_VERSION
                or value["predicate_version"] != cls.PREDICATE_VERSION):
            raise InvalidModelError("unsupported rational faceted solid profile or algorithm")
        for label, item, ceiling in (
            ("solid_id", value["solid_id"], _MAX_SOLID_ID_CHARS),
            ("frame_id", value["frame_id"], _MAX_FRAME_ID_CHARS),
            ("length_unit", value["length_unit"], _MAX_LENGTH_UNIT_CHARS),
        ):
            if not isinstance(item, str) or not item.strip() or len(item) > ceiling:
                raise InvalidModelError(f"{label} is missing or exceeds its maximum length")
        raw_vertices, raw_triangles = value["vertices"], value["triangles"]
        if not isinstance(raw_vertices, (list, tuple)) or not isinstance(raw_triangles, (list, tuple)):
            raise InvalidModelError("vertices and triangles must be arrays")
        if not 4 <= len(raw_vertices) <= _MAX_VERTICES or not 4 <= len(raw_triangles) <= _MAX_TRIANGLES:
            raise InvalidModelError("rational solid geometry count is outside supported hard limits")
        pair_checks = len(raw_triangles) * (len(raw_triangles) - 1) // 2
        if pair_checks > max_pairwise_checks:
            raise InvalidModelError("rational self-intersection pair budget exceeded before coordinate parsing")
        shells = value["shells"]
        if shells != [{"shell_id": "outer", "role": "OUTER",
                       "triangle_indices": list(range(len(raw_triangles))),
                       "parent_outer_shell_id": None}]:
            raise InvalidModelError("v1 supports exactly one outer shell; cavities are unsupported")
        raw_sources = value["source_provenance"]
        if not isinstance(raw_sources, (list, tuple)) or len(raw_sources) > _MAX_PROVENANCE_RECORDS:
            raise InvalidModelError("source_provenance count exceeds supported hard limits")
        metadata_chars = len(value["solid_id"]) + len(value["frame_id"]) + len(value["length_unit"])
        for raw in raw_sources:
            if not isinstance(raw, Mapping) or set(raw) != {"source_id", "source_sha256"}:
                raise InvalidModelError("source provenance record has missing or unknown fields")
            source_id, digest = raw["source_id"], raw["source_sha256"]
            if (not isinstance(source_id, str) or len(source_id) > _MAX_SOURCE_ID_CHARS
                    or not _ID.fullmatch(source_id) or not isinstance(digest, str)
                    or not _DIGEST.fullmatch(digest)):
                raise InvalidModelError("source provenance requires bounded stable IDs and lowercase SHA-256")
            metadata_chars += len(source_id) + len(digest)
        if metadata_chars > _MAX_METADATA_CHARS:
            raise InvalidModelError("aggregate metadata character budget exceeded")
        vertices = []
        aggregate_budget = [0]
        for raw_point in raw_vertices:
            if not isinstance(raw_point, (list, tuple)) or len(raw_point) != 3:
                raise InvalidModelError("each rational vertex must contain three coordinates")
            vertices.append(tuple(_parse_rational(item, "coordinate", max_coordinate_bits,
                                                  aggregate_budget)
                                  for item in raw_point))
        triangles = []
        for raw_face in raw_triangles:
            if not isinstance(raw_face, (list, tuple)) or len(raw_face) != 3:
                raise InvalidModelError("each rational triangle must contain three indices")
            triangles.append(tuple(raw_face))
        sources = [(raw["source_id"], raw["source_sha256"]) for raw in raw_sources]
        counters = value["resource_counters"]
        expected_counters = {
            "vertex_count": len(vertices), "triangle_count": len(triangles),
            "self_intersection_pair_checks": len(triangles) * (len(triangles)-1) // 2,
        }
        if counters != expected_counters:
            raise InvalidModelError("resource counters do not match the geometry")
        result = cls(
            value["solid_id"], value["frame_id"], value["length_unit"],
            tuple(vertices), tuple(triangles), tuple(sources),
            max_coordinate_bits, max_pairwise_checks,
        )
        if value["exact_signed_volume"] != _rational_pair(result.exact_signed_volume):
            raise InvalidModelError("serialized exact volume does not match recomputed geometry")
        expected = result.to_dict()["result_sha256"]
        if value["result_sha256"] != expected:
            raise InvalidModelError("rational faceted solid digest does not match its content")
        return result
