from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import struct

import pytest

from universal_platform.engineering import (
    BoxSolid,
    CylinderSolid,
    ExtrudedProfileSolid,
    Vec2,
    export_binary_stl,
    tessellate_box,
    tessellate_cylinder,
    tessellate_extruded_profile,
    validate_binary_stl_artifact,
)
from universal_platform.engineering.errors import InvalidModelError
from universal_platform.engineering.geometry import Vec3
from universal_platform.engineering.mesh import TriangleMesh
from universal_platform.engineering.stl_interchange import (
    MAX_STL_FACETS,
    STLInterchangeManifest,
)


def _independent_binary_stl_reader(payload: bytes):
    """Test-only parser; deliberately does not call production STL helpers."""
    assert len(payload) >= 84
    header = payload[:80]
    facet_count = struct.unpack_from("<I", payload, 80)[0]
    assert len(payload) == 84 + 50 * facet_count
    facets = []
    for index in range(facet_count):
        offset = 84 + index * 50
        record = struct.unpack_from("<12fH", payload, offset)
        normal = record[:3]
        vertices = (record[3:6], record[6:9], record[9:12])
        attribute = record[12]
        facets.append((normal, vertices, attribute))
    return header, facets


def _assert_reopened_facets_match(mesh: TriangleMesh, payload: bytes):
    header, facets = _independent_binary_stl_reader(payload)
    assert header.startswith(b"UNIVERSAL_PLATFORM_BINARY_STL_V1")
    assert not header.startswith(b"solid")
    assert len(facets) == len(mesh.triangles)
    for source_face, (normal, vertices, attribute) in zip(mesh.triangles, facets):
        assert attribute == 0
        source_vertices = [mesh.vertices[index] for index in source_face]
        for source, reopened in zip(source_vertices, vertices):
            expected = tuple(
                struct.unpack("<f", struct.pack("<f", value))[0]
                for value in (source.x, source.y, source.z)
            )
            assert reopened == expected
        ax, ay, az = vertices[0]
        bx, by, bz = vertices[1]
        cx, cy, cz = vertices[2]
        ab = (bx-ax, by-ay, bz-az)
        ac = (cx-ax, cy-ay, cz-az)
        cross = (
            ab[1]*ac[2]-ab[2]*ac[1],
            ab[2]*ac[0]-ab[0]*ac[2],
            ab[0]*ac[1]-ab[1]*ac[0],
        )
        magnitude = sum(value*value for value in cross) ** 0.5
        expected_normal = tuple(value/magnitude for value in cross)
        assert sum(normal[i]*expected_normal[i] for i in range(3)) == pytest.approx(1.0, abs=1e-5)


def test_binary_stl_box_export_is_deterministic_and_independently_reopens():
    mesh = tessellate_box(BoxSolid("box.stl", "assembly.frame", Vec3(2, 3, 4), "mm"))
    artifact = export_binary_stl(mesh)

    assert len(artifact.payload) == 84 + 50 * 12
    assert artifact.manifest.facet_count == 12
    assert artifact.manifest.stl_byte_length == len(artifact.payload)
    assert artifact.manifest.frame_id == "assembly.frame"
    assert artifact.manifest.length_unit == "mm"
    assert artifact.manifest.source_geometry_sha256 == mesh.source_geometry_sha256
    assert artifact.manifest.max_coordinate_rounding_error == 0.0
    assert artifact.manifest.stl_sha256 == sha256(artifact.payload).hexdigest()
    assert export_binary_stl(mesh) == artifact
    assert artifact.manifest.to_dict() == export_binary_stl(mesh).manifest.to_dict()
    _assert_reopened_facets_match(mesh, artifact.payload)
    assert validate_binary_stl_artifact(
        artifact.payload, artifact.manifest.to_dict(),
        expected_frame_id="assembly.frame", expected_length_unit="mm",
    ) == artifact.manifest


def test_binary_stl_supports_cylinder_straight_hole_and_arc_meshes():
    cylinder = tessellate_cylinder(CylinderSolid("cylinder.stl", "world", 2.0, 3.0, "cm"), 0.1)
    outer = (Vec2(0, 0), Vec2(8, 0), Vec2(8, 8), Vec2(0, 8))
    hole = (Vec2(2, 2), Vec2(2, 4), Vec2(4, 4), Vec2(4, 2))
    straight_hole = ExtrudedProfileSolid("profile.hole.stl", "world", outer, 2.0, "m", (hole,))
    arc_hole = ExtrudedProfileSolid(
        "profile.arc-hole.stl", "world",
        (Vec2(0, 0), Vec2(12, 0), Vec2(12, 12), Vec2(0, 12)), 2.0, "mm",
        ((Vec2(3, 3), Vec2(3, 7), Vec2(7, 7), Vec2(7, 3)),),
        hole_arc_sweeps_rad=((2.0, 0.0, 0.0, 0.0),),
        hole_segment_ids=(("hole.arc", "hole.top", "hole.right", "hole.bottom"),),
    )
    meshes = (
        cylinder,
        tessellate_extruded_profile(straight_hole),
        tessellate_extruded_profile(arc_hole, chordal_tolerance=0.02),
    )
    for mesh in meshes:
        artifact = export_binary_stl(mesh)
        _assert_reopened_facets_match(mesh, artifact.payload)
        assert artifact.manifest.facet_count == len(mesh.triangles)
        assert validate_binary_stl_artifact(
            artifact.payload, artifact.manifest,
            expected_frame_id=mesh.frame_id, expected_length_unit=mesh.length_unit,
        ) == artifact.manifest


def test_stl_manifest_is_strict_and_round_trips():
    artifact = export_binary_stl(tessellate_box(BoxSolid("box.manifest", "world", Vec3(1, 1, 1))))
    snapshot = artifact.manifest.to_dict()
    assert STLInterchangeManifest.from_dict(snapshot) == artifact.manifest
    assert STLInterchangeManifest.from_dict(snapshot).to_dict() == snapshot

    malformed = deepcopy(snapshot)
    malformed["unknown"] = True
    with pytest.raises(InvalidModelError):
        STLInterchangeManifest.from_dict(malformed)
    malformed = deepcopy(snapshot)
    malformed["length_unit"] = "kg"
    with pytest.raises(InvalidModelError):
        STLInterchangeManifest.from_dict(malformed)
    malformed = deepcopy(snapshot)
    malformed["stl_byte_length"] += 1
    with pytest.raises(InvalidModelError):
        STLInterchangeManifest.from_dict(malformed)

    malformed = deepcopy(snapshot)
    malformed["source_kind"] = ["BOX"]
    with pytest.raises(InvalidModelError):
        STLInterchangeManifest.from_dict(malformed)
    malformed = deepcopy(snapshot)
    malformed["max_coordinate_rounding_error"] = -1.0
    with pytest.raises(InvalidModelError):
        STLInterchangeManifest.from_dict(malformed)


def test_stl_manifest_schema_matches_exported_shape():
    artifact = export_binary_stl(tessellate_box(BoxSolid("box.schema.stl", "world", Vec3(1, 1, 1))))
    schema = json.loads(
        (Path(__file__).parents[1] / "schemas" / "geometry" / "stl-interchange-manifest.schema.json").read_text()
    )
    snapshot = artifact.manifest.to_dict()
    assert schema["properties"]["schema_version"]["const"] == snapshot["schema_version"]
    assert schema["properties"]["format"]["const"] == "BINARY_STL"
    assert set(snapshot) == set(schema["required"])
    assert schema["additionalProperties"] is False


def test_stl_payload_and_context_tampering_are_rejected():
    artifact = export_binary_stl(tessellate_box(BoxSolid("box.tamper.stl", "world", Vec3(1, 1, 1))))
    with pytest.raises(InvalidModelError):
        validate_binary_stl_artifact(
            artifact.payload, artifact.manifest,
            expected_frame_id="other.frame", expected_length_unit="m",
        )
    with pytest.raises(InvalidModelError):
        validate_binary_stl_artifact(
            artifact.payload, artifact.manifest,
            expected_frame_id="world", expected_length_unit="mm",
        )
    with pytest.raises(InvalidModelError):
        validate_binary_stl_artifact(
            artifact.payload[:-1], artifact.manifest,
            expected_frame_id="world", expected_length_unit="m",
        )
    with pytest.raises(InvalidModelError):
        validate_binary_stl_artifact(
            artifact.payload + b"\x00", artifact.manifest,
            expected_frame_id="world", expected_length_unit="m",
        )

    changed = bytearray(artifact.payload)
    changed[-1] = 1
    changed_bytes = bytes(changed)
    changed_manifest = deepcopy(artifact.manifest.to_dict())
    changed_manifest["stl_sha256"] = sha256(changed_bytes).hexdigest()
    with pytest.raises(InvalidModelError, match="attribute"):
        validate_binary_stl_artifact(
            changed_bytes, changed_manifest,
            expected_frame_id="world", expected_length_unit="m",
        )


def test_stl_export_rejects_invalid_mesh_quantization_and_resource_excess():
    mesh = tessellate_box(BoxSolid("box.limit", "world", Vec3(1, 1, 1)))
    with pytest.raises(InvalidModelError):
        export_binary_stl(mesh, max_facets=4-1)
    with pytest.raises(InvalidModelError):
        export_binary_stl(mesh, max_facets=True)
    with pytest.raises(InvalidModelError):
        export_binary_stl(mesh, max_facets=4)

    open_mesh = TriangleMesh(
        mesh.solid_id, mesh.frame_id, mesh.length_unit, mesh.source_kind,
        mesh.source_geometry_sha256, mesh.vertices, mesh.triangles[:-1],
    )
    with pytest.raises(InvalidModelError, match="valid"):
        export_binary_stl(open_mesh)

    huge = tessellate_box(BoxSolid("box.huge.stl", "world", Vec3(1e39, 1e39, 1e39)))
    with pytest.raises(InvalidModelError, match="binary32"):
        export_binary_stl(huge)

    tiny = tessellate_box(BoxSolid("box.tiny.stl", "world", Vec3(1e-50, 1e-50, 1e-50)))
    with pytest.raises(InvalidModelError, match="quantization"):
        export_binary_stl(tiny)
