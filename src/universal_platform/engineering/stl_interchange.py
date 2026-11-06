"""Deterministic, dependency-free binary STL export with a strict metadata sidecar.

STL carries triangle coordinates only. The manifest preserves the source frame,
unit, identity, provenance and tessellation tolerance that STL cannot encode.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from math import isfinite, sqrt
import struct
from typing import Any, ClassVar, Mapping

from .errors import InvalidModelError
from .mesh import TriangleMesh, validate_triangle_mesh
from .quantity import LENGTH, Quantity

STL_MANIFEST_SCHEMA_VERSION = "1.0"
MAX_STL_FACETS = 1_000_000
_BINARY_HEADER = b"UNIVERSAL_PLATFORM_BINARY_STL_V1".ljust(80, b"\x00")
_COORDINATE_ENCODING = "IEEE754_BINARY32_LE"
_NORMAL_POLICY = "RECOMPUTED_FROM_QUANTIZED_FACETS"
_MANIFEST_FIELDS = {
    "schema_version", "format", "coordinate_encoding", "normal_policy",
    "solid_id", "source_kind", "source_mesh_schema_version",
    "source_geometry_sha256", "frame_id", "length_unit", "chordal_tolerance",
    "stl_byte_length", "facet_count", "stl_sha256",
    "max_coordinate_rounding_error",
}


def _finite(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(float(value)):
        raise InvalidModelError(f"{label} must be a finite number")
    return float(value)


def _valid_length_unit(unit: str) -> None:
    if not isinstance(unit, str) or not unit:
        raise InvalidModelError("STL manifest length_unit is required")
    try:
        if Quantity.of(1.0, unit).dimension != LENGTH:
            raise InvalidModelError("STL manifest length_unit must have length dimension")
    except Exception as exc:
        if isinstance(exc, InvalidModelError):
            raise
        raise InvalidModelError(f"Unsupported STL manifest length_unit: {unit}") from exc


def _valid_digest(value: Any, label: str) -> None:
    if (not isinstance(value, str) or len(value) != 64
            or any(character not in "0123456789abcdef" for character in value)):
        raise InvalidModelError(f"{label} must be a lowercase SHA-256 digest")


@dataclass(frozen=True, slots=True)
class STLInterchangeManifest:
    """Strict sidecar metadata for one binary STL payload."""

    solid_id: str
    source_kind: str
    source_mesh_schema_version: str
    source_geometry_sha256: str
    frame_id: str
    length_unit: str
    chordal_tolerance: float | None
    stl_byte_length: int
    facet_count: int
    stl_sha256: str
    max_coordinate_rounding_error: float
    schema_version: str = STL_MANIFEST_SCHEMA_VERSION
    format: str = "BINARY_STL"
    coordinate_encoding: str = _COORDINATE_ENCODING
    normal_policy: str = _NORMAL_POLICY

    SCHEMA_VERSION: ClassVar[str] = STL_MANIFEST_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != self.SCHEMA_VERSION:
            raise InvalidModelError("Unsupported STL manifest schema_version")
        if self.format != "BINARY_STL" or self.coordinate_encoding != _COORDINATE_ENCODING:
            raise InvalidModelError("Unsupported STL format or coordinate encoding")
        if self.normal_policy != _NORMAL_POLICY:
            raise InvalidModelError("Unsupported STL normal policy")
        if not isinstance(self.solid_id, str) or not self.solid_id.strip():
            raise InvalidModelError("STL manifest solid_id is required")
        if not isinstance(self.source_kind, str) or self.source_kind not in {"BOX", "CYLINDER", "EXTRUDED_PROFILE"}:
            raise InvalidModelError("STL manifest source_kind is unsupported")
        if self.source_mesh_schema_version != TriangleMesh.SCHEMA_VERSION:
            raise InvalidModelError("Unsupported source TriangleMesh schema version")
        _valid_digest(self.source_geometry_sha256, "source_geometry_sha256")
        if not isinstance(self.frame_id, str) or not self.frame_id.strip():
            raise InvalidModelError("STL manifest frame_id is required")
        _valid_length_unit(self.length_unit)
        if self.chordal_tolerance is not None:
            tolerance = _finite(self.chordal_tolerance, "chordal_tolerance")
            if tolerance <= 0:
                raise InvalidModelError("STL manifest chordal_tolerance must be positive")
            object.__setattr__(self, "chordal_tolerance", tolerance)
        if isinstance(self.stl_byte_length, bool) or not isinstance(self.stl_byte_length, int):
            raise InvalidModelError("STL manifest stl_byte_length must be an integer")
        if isinstance(self.facet_count, bool) or not isinstance(self.facet_count, int):
            raise InvalidModelError("STL manifest facet_count must be an integer")
        if not 4 <= self.facet_count <= MAX_STL_FACETS:
            raise InvalidModelError("STL manifest facet_count is outside the supported resource limit")
        if self.stl_byte_length != 84 + 50 * self.facet_count:
            raise InvalidModelError("STL manifest byte length does not match the binary STL facet count")
        _valid_digest(self.stl_sha256, "stl_sha256")
        error = _finite(self.max_coordinate_rounding_error, "max_coordinate_rounding_error")
        if error < 0:
            raise InvalidModelError("max_coordinate_rounding_error cannot be negative")
        object.__setattr__(self, "max_coordinate_rounding_error", error)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "format": self.format,
            "coordinate_encoding": self.coordinate_encoding,
            "normal_policy": self.normal_policy,
            "solid_id": self.solid_id,
            "source_kind": self.source_kind,
            "source_mesh_schema_version": self.source_mesh_schema_version,
            "source_geometry_sha256": self.source_geometry_sha256,
            "frame_id": self.frame_id,
            "length_unit": self.length_unit,
            "chordal_tolerance": self.chordal_tolerance,
            "stl_byte_length": self.stl_byte_length,
            "facet_count": self.facet_count,
            "stl_sha256": self.stl_sha256,
            "max_coordinate_rounding_error": self.max_coordinate_rounding_error,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "STLInterchangeManifest":
        if not isinstance(value, Mapping) or set(value) != _MANIFEST_FIELDS:
            raise InvalidModelError("STL manifest has missing or unknown fields")
        return cls(
            solid_id=value["solid_id"],
            source_kind=value["source_kind"],
            source_mesh_schema_version=value["source_mesh_schema_version"],
            source_geometry_sha256=value["source_geometry_sha256"],
            frame_id=value["frame_id"],
            length_unit=value["length_unit"],
            chordal_tolerance=value["chordal_tolerance"],
            stl_byte_length=value["stl_byte_length"],
            facet_count=value["facet_count"],
            stl_sha256=value["stl_sha256"],
            max_coordinate_rounding_error=value["max_coordinate_rounding_error"],
            schema_version=value["schema_version"],
            format=value["format"],
            coordinate_encoding=value["coordinate_encoding"],
            normal_policy=value["normal_policy"],
        )


@dataclass(frozen=True, slots=True)
class BinarySTLArtifact:
    """Binary STL payload and the sidecar required to interpret its metadata."""

    payload: bytes
    manifest: STLInterchangeManifest

    def __post_init__(self) -> None:
        if not isinstance(self.payload, bytes):
            raise InvalidModelError("Binary STL payload must be immutable bytes")
        if not isinstance(self.manifest, STLInterchangeManifest):
            raise InvalidModelError("Binary STL artifact requires an STLInterchangeManifest")


def _float32(value: float, label: str) -> float:
    try:
        packed = struct.pack("<f", value)
    except (OverflowError, struct.error) as exc:
        raise InvalidModelError(f"{label} exceeds binary32 coordinate range") from exc
    result = struct.unpack("<f", packed)[0]
    if not isfinite(result):
        raise InvalidModelError(f"{label} is not finite after binary32 quantization")
    return result


def _cross_and_length(a: tuple[float, float, float],
                      b: tuple[float, float, float],
                      c: tuple[float, float, float]) -> tuple[tuple[float, float, float], float]:
    ab = (b[0]-a[0], b[1]-a[1], b[2]-a[2])
    ac = (c[0]-a[0], c[1]-a[1], c[2]-a[2])
    cross = (
        ab[1]*ac[2]-ab[2]*ac[1],
        ab[2]*ac[0]-ab[0]*ac[2],
        ab[0]*ac[1]-ab[1]*ac[0],
    )
    return cross, sqrt(sum(component*component for component in cross))


def export_binary_stl(
    mesh: TriangleMesh, *, max_facets: int = MAX_STL_FACETS
) -> BinarySTLArtifact:
    """Export a validated TriangleMesh as deterministic binary STL plus sidecar."""
    if not isinstance(mesh, TriangleMesh):
        raise InvalidModelError("export_binary_stl requires a TriangleMesh")
    if isinstance(max_facets, bool) or not isinstance(max_facets, int) or not 4 <= max_facets <= MAX_STL_FACETS:
        raise InvalidModelError(f"max_facets must be an integer from 4 to {MAX_STL_FACETS}")
    validation = validate_triangle_mesh(mesh)
    if not validation.valid:
        raise InvalidModelError("binary STL export requires a structurally valid oriented mesh")
    facet_count = len(mesh.triangles)
    if facet_count > max_facets:
        raise InvalidModelError("binary STL export exceeds the configured facet limit")

    quantized: list[tuple[float, float, float]] = []
    coordinate_owner: dict[tuple[float, float, float], int] = {}
    max_error = 0.0
    for index, vertex in enumerate(mesh.vertices):
        point = (
            _float32(vertex.x, f"vertex {index} x"),
            _float32(vertex.y, f"vertex {index} y"),
            _float32(vertex.z, f"vertex {index} z"),
        )
        previous = coordinate_owner.get(point)
        if previous is not None and previous != index:
            raise InvalidModelError("binary32 quantization collapses distinct mesh vertices")
        coordinate_owner[point] = index
        max_error = max(
            max_error, abs(vertex.x-point[0]), abs(vertex.y-point[1]), abs(vertex.z-point[2])
        )
        quantized.append(point)

    xs = [point[0] for point in quantized]
    ys = [point[1] for point in quantized]
    zs = [point[2] for point in quantized]
    scale = max(max(xs)-min(xs), max(ys)-min(ys), max(zs)-min(zs), 1e-300)
    records: list[bytes] = []
    for face_index, face in enumerate(mesh.triangles):
        a, b, c = (quantized[index] for index in face)
        cross, magnitude = _cross_and_length(a, b, c)
        if magnitude <= 1e-14 * scale * scale:
            raise InvalidModelError(f"binary32 quantization degenerates triangle {face_index}")
        normal = tuple(component/magnitude for component in cross)
        values = normal + a + b + c
        if any(not isfinite(value) for value in values):
            raise InvalidModelError(f"triangle {face_index} contains a non-finite binary32 value")
        records.append(struct.pack("<12fH", *values, 0))

    payload = _BINARY_HEADER + struct.pack("<I", facet_count) + b"".join(records)
    manifest = STLInterchangeManifest(
        solid_id=mesh.solid_id,
        source_kind=mesh.source_kind,
        source_mesh_schema_version=mesh.SCHEMA_VERSION,
        source_geometry_sha256=mesh.source_geometry_sha256,
        frame_id=mesh.frame_id,
        length_unit=mesh.length_unit,
        chordal_tolerance=mesh.chordal_tolerance,
        stl_byte_length=len(payload),
        facet_count=facet_count,
        stl_sha256=sha256(payload).hexdigest(),
        max_coordinate_rounding_error=max_error,
    )
    return BinarySTLArtifact(payload, manifest)


def validate_binary_stl_artifact(
    payload: bytes,
    manifest: STLInterchangeManifest | Mapping[str, Any],
    *,
    expected_frame_id: str,
    expected_length_unit: str,
) -> STLInterchangeManifest:
    """Validate a platform STL payload and sidecar against caller-approved context."""
    if not isinstance(payload, bytes):
        raise InvalidModelError("Binary STL payload must be immutable bytes")
    if isinstance(manifest, Mapping):
        manifest = STLInterchangeManifest.from_dict(manifest)
    if not isinstance(manifest, STLInterchangeManifest):
        raise InvalidModelError("STL manifest must be a validated manifest or strict snapshot")
    if not isinstance(expected_frame_id, str) or not expected_frame_id.strip():
        raise InvalidModelError("expected_frame_id is required")
    _valid_length_unit(expected_length_unit)
    if manifest.frame_id != expected_frame_id or manifest.length_unit != expected_length_unit:
        raise InvalidModelError("STL manifest frame/unit does not match caller-approved context")
    if len(payload) != manifest.stl_byte_length:
        raise InvalidModelError("STL payload byte length does not match its manifest")
    if len(payload) < 84 or payload[:80] != _BINARY_HEADER:
        raise InvalidModelError("STL payload has an invalid binary header")
    facet_count = struct.unpack_from("<I", payload, 80)[0]
    if facet_count != manifest.facet_count or facet_count > MAX_STL_FACETS:
        raise InvalidModelError("STL payload facet count does not match its manifest")
    if len(payload) != 84 + 50*facet_count:
        raise InvalidModelError("STL payload has trailing or truncated facet records")
    if sha256(payload).hexdigest() != manifest.stl_sha256:
        raise InvalidModelError("STL payload SHA-256 does not match its manifest")

    for index in range(facet_count):
        offset = 84 + 50*index
        values = struct.unpack_from("<12fH", payload, offset)
        if any(not isfinite(value) for value in values[:12]):
            raise InvalidModelError(f"STL facet {index} contains non-finite values")
        if values[12] != 0:
            raise InvalidModelError(f"STL facet {index} uses unsupported attribute bytes")
        normal = values[:3]
        a, b, c = values[3:6], values[6:9], values[9:12]
        cross, magnitude = _cross_and_length(a, b, c)
        if magnitude <= 0.0:
            raise InvalidModelError(f"STL facet {index} is degenerate")
        normal_length = sqrt(sum(component*component for component in normal))
        if normal_length <= 0.0:
            raise InvalidModelError(f"STL facet {index} has a zero normal")
        alignment = sum(normal[i]*cross[i]/magnitude for i in range(3))/normal_length
        if abs(normal_length-1.0) > 1e-5 or alignment < 1.0-1e-5:
            raise InvalidModelError(f"STL facet {index} normal does not match its quantized winding")
    return manifest
