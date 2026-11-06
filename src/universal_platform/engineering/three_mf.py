"""Bounded 3MF Core mesh import/export for validated watertight triangle solids.

This implementation intentionally supports one untransformed mesh object in a
small OPC/ZIP package. Unsupported extensions, components, transforms and extra
package parts fail closed. It is not a complete 3MF implementation.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from io import BytesIO
from math import isfinite
from zipfile import ZIP_DEFLATED, BadZipFile, ZipFile, ZipInfo
import re
import stat
import xml.etree.ElementTree as ET

from .errors import InvalidModelError
from .geometry import Vec3
from .mesh import TriangleMesh, MeshValidationResult, validate_triangle_mesh

_CORE_NS = "http://schemas.microsoft.com/3dmanufacturing/core/2015/02"
_CT_NS = "http://schemas.openxmlformats.org/package/2006/content-types"
_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
_START_PART_REL = "http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"
_MODEL_CONTENT_TYPE = "application/vnd.ms-package.3dmanufacturing-3dmodel+xml"
_PARTS = ("[Content_Types].xml", "_rels/.rels", "3D/3dmodel.model")
_MAX_PACKAGE_BYTES = 64 * 1024 * 1024
_MAX_XML_BYTES = 32 * 1024 * 1024
_MAX_ENTRIES = 8
_MAX_VERTICES = 250_000
_MAX_TRIANGLES = 500_000
_UNIT_TO_3MF = {"mm": "millimeter", "cm": "centimeter", "m": "meter", "in": "inch"}
_UNIT_FROM_3MF = {value: key for key, value in _UNIT_TO_3MF.items()}
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True, slots=True)
class ThreeMFArtifact:
    content: bytes
    content_sha256: str
    source_geometry_sha256: str
    byte_count: int

    def to_dict(self) -> dict[str, object]:
        return {
            "format": "3MF_CORE",
            "content_sha256": self.content_sha256,
            "source_geometry_sha256": self.source_geometry_sha256,
            "byte_count": self.byte_count,
        }


@dataclass(frozen=True, slots=True)
class ThreeMFImportResult:
    mesh: TriangleMesh
    validation: MeshValidationResult
    package_sha256: str

    def to_dict(self) -> dict[str, object]:
        return {
            "format": "3MF_CORE",
            "package_sha256": self.package_sha256,
            "mesh": self.mesh.to_dict(),
            "validation": self.validation.to_dict(),
        }


def _xml_bytes(root: ET.Element) -> bytes:
    return ET.tostring(root, encoding="utf-8", xml_declaration=True, short_empty_elements=True)


def _package_parts(model_xml: bytes) -> tuple[bytes, bytes, bytes]:
    content_types = ET.Element(f"{{{_CT_NS}}}Types")
    ET.SubElement(content_types, f"{{{_CT_NS}}}Default", {
        "Extension": "rels",
        "ContentType": "application/vnd.openxmlformats-package.relationships+xml",
    })
    ET.SubElement(content_types, f"{{{_CT_NS}}}Override", {
        "PartName": "/3D/3dmodel.model",
        "ContentType": _MODEL_CONTENT_TYPE,
    })
    relationships = ET.Element(f"{{{_REL_NS}}}Relationships")
    ET.SubElement(relationships, f"{{{_REL_NS}}}Relationship", {
        "Target": "/3D/3dmodel.model",
        "Id": "rel0",
        "Type": _START_PART_REL,
    })
    return _xml_bytes(content_types), _xml_bytes(relationships), model_xml


def _write_deterministic_zip(parts: tuple[bytes, bytes, bytes]) -> bytes:
    buffer = BytesIO()
    with ZipFile(buffer, "w", compression=ZIP_DEFLATED, compresslevel=9) as archive:
        archive.comment = b""
        for name, content in zip(_PARTS, parts):
            info = ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = ZIP_DEFLATED
            info.create_system = 0
            info.external_attr = 0o600 << 16
            info.flag_bits = 0
            archive.writestr(info, content, compress_type=ZIP_DEFLATED, compresslevel=9)
    return buffer.getvalue()


def export_3mf(mesh: TriangleMesh) -> ThreeMFArtifact:
    """Export one validated watertight mesh as a deterministic 3MF Core package."""
    if not isinstance(mesh, TriangleMesh):
        raise InvalidModelError("export_3mf requires a TriangleMesh")
    unit = _UNIT_TO_3MF.get(mesh.length_unit)
    if unit is None:
        raise InvalidModelError(f"3MF export does not support internal length unit {mesh.length_unit!r}")
    validation = validate_triangle_mesh(mesh)
    if not (validation.valid and validation.watertight and validation.consistently_oriented):
        raise InvalidModelError("3MF solid export requires a valid, watertight, consistently oriented mesh")

    ET.register_namespace("", _CORE_NS)
    root = ET.Element(f"{{{_CORE_NS}}}model", {
        "unit": unit,
        "{http://www.w3.org/XML/1998/namespace}lang": "en-US",
    })
    metadata = {
        "universal-platform:solid_id": mesh.solid_id,
        "universal-platform:frame_id": mesh.frame_id,
        "universal-platform:source_geometry_sha256": mesh.source_geometry_sha256,
        "universal-platform:source_kind": mesh.source_kind,
    }
    for name, value in metadata.items():
        node = ET.SubElement(root, f"{{{_CORE_NS}}}metadata", {"name": name})
        node.text = value

    resources = ET.SubElement(root, f"{{{_CORE_NS}}}resources")
    obj = ET.SubElement(resources, f"{{{_CORE_NS}}}object", {"id": "1", "type": "model"})
    mesh_node = ET.SubElement(obj, f"{{{_CORE_NS}}}mesh")
    vertices = ET.SubElement(mesh_node, f"{{{_CORE_NS}}}vertices")
    for vertex in mesh.vertices:
        ET.SubElement(vertices, f"{{{_CORE_NS}}}vertex", {
            "x": format(float(vertex.x), ".17g"),
            "y": format(float(vertex.y), ".17g"),
            "z": format(float(vertex.z), ".17g"),
        })
    triangles = ET.SubElement(mesh_node, f"{{{_CORE_NS}}}triangles")
    for face in mesh.triangles:
        ET.SubElement(triangles, f"{{{_CORE_NS}}}triangle", {
            "v1": str(face[0]), "v2": str(face[1]), "v3": str(face[2]),
        })
    build = ET.SubElement(root, f"{{{_CORE_NS}}}build")
    ET.SubElement(build, f"{{{_CORE_NS}}}item", {"objectid": "1"})
    model_xml = _xml_bytes(root)
    parts = _package_parts(model_xml)
    content = _write_deterministic_zip(parts)
    if len(content) > _MAX_PACKAGE_BYTES:
        raise InvalidModelError("3MF export exceeds the package byte limit")
    return ThreeMFArtifact(
        content, sha256(content).hexdigest(), mesh.source_geometry_sha256, len(content)
    )


def _parse_xml(data: bytes, label: str) -> ET.Element:
    if len(data) > _MAX_XML_BYTES:
        raise InvalidModelError(f"3MF {label} XML exceeds the size limit")
    upper = data.upper()
    if b"<!DOCTYPE" in upper or b"<!ENTITY" in upper:
        raise InvalidModelError(f"3MF {label} XML must not contain DTD or entity declarations")
    try:
        return ET.fromstring(data)
    except ET.ParseError as exc:
        raise InvalidModelError(f"3MF {label} XML is malformed") from exc


def _read_package(content: bytes) -> dict[str, bytes]:
    if not isinstance(content, bytes) or not content:
        raise InvalidModelError("3MF import requires non-empty package bytes")
    if len(content) > _MAX_PACKAGE_BYTES:
        raise InvalidModelError("3MF package exceeds the byte limit")
    try:
        with ZipFile(BytesIO(content), "r") as archive:
            entries = archive.infolist()
            if len(entries) > _MAX_ENTRIES:
                raise InvalidModelError("3MF package contains too many entries")
            names = [entry.filename for entry in entries]
            if len(names) != len(set(names)):
                raise InvalidModelError("3MF package contains duplicate part names")
            if set(names) != set(_PARTS):
                raise InvalidModelError("3MF package has missing or unsupported parts")
            total = 0
            for entry in entries:
                name = entry.filename
                if (name.startswith("/") or "\\" in name or "\x00" in name
                        or any(part in {".", ".."} for part in name.split("/"))):
                    raise InvalidModelError("3MF package contains an unsafe part path")
                mode = (entry.external_attr >> 16) & 0o170000
                if mode == stat.S_IFLNK or entry.flag_bits & 0x1:
                    raise InvalidModelError("3MF package must not contain symlinks or encrypted parts")
                total += entry.file_size
                if total > _MAX_PACKAGE_BYTES:
                    raise InvalidModelError("3MF uncompressed package size exceeds the limit")
                if entry.file_size and entry.compress_size == 0:
                    raise InvalidModelError("3MF package contains an invalid compressed part")
                if entry.compress_size and entry.file_size / entry.compress_size > 500:
                    raise InvalidModelError("3MF package compression ratio exceeds the safety limit")
            return {name: archive.read(name) for name in _PARTS}
    except BadZipFile as exc:
        raise InvalidModelError("3MF package is not a valid ZIP archive") from exc


def import_3mf(content: bytes) -> ThreeMFImportResult:
    """Import a single untransformed, watertight 3MF Core triangle mesh."""
    parts = _read_package(content)
    content_types = _parse_xml(parts["[Content_Types].xml"], "content-types")
    if content_types.tag != f"{{{_CT_NS}}}Types":
        raise InvalidModelError("3MF Content_Types root is invalid")
    overrides = content_types.findall(f"{{{_CT_NS}}}Override")
    defaults = content_types.findall(f"{{{_CT_NS}}}Default")
    if (len(overrides) != 1 or len(defaults) != 1
            or overrides[0].attrib != {"PartName": "/3D/3dmodel.model", "ContentType": _MODEL_CONTENT_TYPE}
            or defaults[0].attrib != {
                "Extension": "rels",
                "ContentType": "application/vnd.openxmlformats-package.relationships+xml",
            }):
        raise InvalidModelError("3MF package content types are missing or unsupported")

    relationships = _parse_xml(parts["_rels/.rels"], "relationships")
    if relationships.tag != f"{{{_REL_NS}}}Relationships":
        raise InvalidModelError("3MF package relationships root is invalid")
    rels = relationships.findall(f"{{{_REL_NS}}}Relationship")
    if len(rels) != 1 or rels[0].attrib.get("Type") != _START_PART_REL or rels[0].attrib.get("Target") != "/3D/3dmodel.model":
        raise InvalidModelError("3MF package must identify exactly one primary 3D model part")

    root = _parse_xml(parts["3D/3dmodel.model"], "model")
    if root.tag != f"{{{_CORE_NS}}}model":
        raise InvalidModelError("3MF model root namespace is unsupported")
    if set(root.attrib) - {"unit", "{http://www.w3.org/XML/1998/namespace}lang"}:
        raise InvalidModelError("3MF model has unsupported root attributes")
    unit_name = root.attrib.get("unit", "millimeter")
    length_unit = _UNIT_FROM_3MF.get(unit_name)
    if length_unit is None:
        raise InvalidModelError(f"3MF unit {unit_name!r} is not supported by the internal unit registry")
    metadata: dict[str, str] = {}
    for item in root.findall(f"{{{_CORE_NS}}}metadata"):
        name = item.attrib.get("name", "")
        if name in metadata:
            raise InvalidModelError("3MF model contains duplicate metadata names")
        metadata[name] = item.text or ""

    children = list(root)
    resources = [item for item in children if item.tag == f"{{{_CORE_NS}}}resources"]
    builds = [item for item in children if item.tag == f"{{{_CORE_NS}}}build"]
    if len(resources) != 1 or len(builds) != 1:
        raise InvalidModelError("3MF model requires exactly one resources and one build element")
    if children.index(resources[0]) > children.index(builds[0]):
        raise InvalidModelError("3MF resources must be defined before build items")
    if any(item.tag not in {f"{{{_CORE_NS}}}metadata", f"{{{_CORE_NS}}}resources", f"{{{_CORE_NS}}}build"} for item in children):
        raise InvalidModelError("3MF model contains unsupported extension elements")

    objects = resources[0].findall(f"{{{_CORE_NS}}}object")
    if len(objects) != 1 or len(list(resources[0])) != 1:
        raise InvalidModelError("3MF import supports exactly one mesh object and no other resources")
    obj = objects[0]
    if set(obj.attrib) - {"id", "type"}:
        raise InvalidModelError("3MF object has unsupported attributes")
    object_id = obj.attrib.get("id")
    if obj.attrib.get("type", "model") != "model":
        raise InvalidModelError("3MF object type must be model")
    if len(list(obj)) != 1 or list(obj)[0].tag != f"{{{_CORE_NS}}}mesh":
        raise InvalidModelError("3MF object must contain exactly one mesh and no components")
    items = builds[0].findall(f"{{{_CORE_NS}}}item")
    if (len(items) != 1 or len(list(builds[0])) != 1
            or items[0].attrib != {"objectid": object_id}):
        raise InvalidModelError("3MF build must contain one untransformed item for the mesh object")

    mesh_node = list(obj)[0]
    vertices_nodes = mesh_node.findall(f"{{{_CORE_NS}}}vertices")
    triangles_nodes = mesh_node.findall(f"{{{_CORE_NS}}}triangles")
    if (len(vertices_nodes) != 1 or len(triangles_nodes) != 1
            or len(list(mesh_node)) != 2
            or set(child.tag for child in list(mesh_node)) != {
                f"{{{_CORE_NS}}}vertices", f"{{{_CORE_NS}}}triangles"
            }):
        raise InvalidModelError("3MF mesh requires exactly one vertices and triangles element")
    if (any(child.tag != f"{{{_CORE_NS}}}vertex" for child in list(vertices_nodes[0]))
            or any(child.tag != f"{{{_CORE_NS}}}triangle" for child in list(triangles_nodes[0]))):
        raise InvalidModelError("3MF mesh contains unsupported vertex or triangle elements")
    raw_vertices = vertices_nodes[0].findall(f"{{{_CORE_NS}}}vertex")
    raw_triangles = triangles_nodes[0].findall(f"{{{_CORE_NS}}}triangle")
    if not raw_vertices or len(raw_vertices) > _MAX_VERTICES:
        raise InvalidModelError("3MF vertex count is outside the supported bounds")
    if not raw_triangles or len(raw_triangles) > _MAX_TRIANGLES:
        raise InvalidModelError("3MF triangle count is outside the supported bounds")

    vertices: list[Vec3] = []
    for raw in raw_vertices:
        if set(raw.attrib) != {"x", "y", "z"}:
            raise InvalidModelError("3MF vertex requires exactly x, y and z")
        coordinates = []
        for axis in ("x", "y", "z"):
            try:
                value = float(raw.attrib[axis])
            except (TypeError, ValueError, OverflowError) as exc:
                raise InvalidModelError(f"3MF vertex {axis} must be numeric") from exc
            if not isfinite(value):
                raise InvalidModelError(f"3MF vertex {axis} must be finite")
            coordinates.append(value)
        vertices.append(Vec3(*coordinates))

    triangles: list[tuple[int, int, int]] = []
    for raw in raw_triangles:
        if set(raw.attrib) != {"v1", "v2", "v3"}:
            raise InvalidModelError("3MF triangle requires exactly v1, v2 and v3")
        try:
            face = tuple(int(raw.attrib[key]) for key in ("v1", "v2", "v3"))
        except (TypeError, ValueError, OverflowError) as exc:
            raise InvalidModelError("3MF triangle indices must be integers") from exc
        if any(index < 0 or index >= len(vertices) for index in face):
            raise InvalidModelError("3MF triangle index is outside the vertex array")
        triangles.append(face)

    solid_id = metadata.get("universal-platform:solid_id", "imported.3mf")
    frame_id = metadata.get("universal-platform:frame_id", "3mf.model")
    source_digest = metadata.get("universal-platform:source_geometry_sha256", sha256(parts["3D/3dmodel.model"]).hexdigest())
    if not _SHA256.fullmatch(source_digest):
        raise InvalidModelError("3MF source geometry metadata must be a lowercase SHA-256 digest")
    mesh = TriangleMesh(
        solid_id, frame_id, length_unit, "IMPORTED_3MF", source_digest,
        tuple(vertices), tuple(triangles), None,
    )
    validation = validate_triangle_mesh(mesh)
    if not (validation.valid and validation.watertight and validation.consistently_oriented):
        raise InvalidModelError("3MF import requires a valid, watertight, consistently oriented solid mesh")
    return ThreeMFImportResult(mesh, validation, sha256(content).hexdigest())
