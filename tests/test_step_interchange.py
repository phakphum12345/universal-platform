from dataclasses import replace
import re

import pytest

from universal_platform.engineering.errors import InvalidModelError
from universal_platform.engineering.geometry import Vec3
from universal_platform.engineering.mesh import TriangleMesh, tessellate_box, validate_triangle_mesh
from universal_platform.engineering.primitive_geometry import BoxSolid
from universal_platform.engineering.step import export_step, import_step


def make_mesh(unit="mm"):
    return tessellate_box(BoxSolid("solid.fixture", "part.frame", Vec3(12, 8, 4), unit))


def test_step_ap214_faceted_brep_export_import_round_trip():
    mesh = make_mesh()
    first = export_step(mesh)
    second = export_step(mesh)
    assert first.content == second.content
    assert first.content_sha256 == second.content_sha256
    assert b"FACETED_BREP_SHAPE_REPRESENTATION" in first.content
    assert b"FACETED_BREP" in first.content
    assert b"CLOSED_SHELL" in first.content
    assert b"POLY_LOOP" in first.content
    restored = import_step(first.content)
    assert restored.validation.valid
    assert restored.validation.watertight
    assert restored.validation.consistently_oriented
    assert restored.mesh.solid_id == mesh.solid_id
    assert restored.mesh.frame_id == mesh.frame_id
    assert restored.mesh.length_unit == mesh.length_unit
    assert restored.mesh.source_kind == "IMPORTED_STEP"
    assert restored.mesh.source_geometry_sha256 == mesh.source_geometry_sha256
    assert restored.mesh.vertices == mesh.vertices
    assert restored.mesh.triangles == mesh.triangles


@pytest.mark.parametrize("unit", ["m", "mm", "cm"])
def test_step_round_trip_preserves_supported_si_length_units(unit):
    mesh = make_mesh(unit)
    restored = import_step(export_step(mesh).content)
    assert restored.mesh.length_unit == unit
    assert restored.mesh.vertices == mesh.vertices


def test_step_export_rejects_open_or_disconnected_shell_and_unsupported_units():
    mesh = make_mesh()
    with pytest.raises(InvalidModelError, match="watertight"):
        export_step(replace(mesh, triangles=mesh.triangles[:-1]))
    first = make_mesh()
    second = tessellate_box(BoxSolid("other", "part.frame", Vec3(1, 1, 1), "mm"))
    disconnected = TriangleMesh(
        "disconnected", "part.frame", "mm", "BOX", first.source_geometry_sha256,
        first.vertices + second.vertices,
        first.triangles + tuple(tuple(i + len(first.vertices) for i in face) for face in second.triangles),
        None,
    )
    with pytest.raises(InvalidModelError, match="connected closed shell"):
        export_step(disconnected)
    with pytest.raises(InvalidModelError, match="m, mm and cm"):
        export_step(make_mesh("in"))


def test_step_import_rejects_invalid_part21_envelope_and_schema():
    content = export_step(make_mesh()).content
    with pytest.raises(InvalidModelError, match="envelope"):
        import_step(content.replace(b"END-ISO-10303-21;", b"END-STEP;"))
    with pytest.raises(InvalidModelError, match="AP214/AP242"):
        import_step(content.replace(b"AUTOMOTIVE_DESIGN", b"UNKNOWN_SCHEMA"))


def test_step_import_rejects_unsupported_entity_and_invalid_poly_loop_reference():
    content = export_step(make_mesh()).content
    with pytest.raises(InvalidModelError, match="unsupported entity"):
        import_step(content.replace(b"ENDSEC;\nEND-ISO", b"#999999=SPHERE('',#1,1.0);\nENDSEC;\nEND-ISO"))
    loop_match = re.search(rb"(POLY_LOOP\('',\(#[0-9]+,#[0-9]+,)#[0-9]+(\)\))", content)
    assert loop_match
    damaged = (
        content[:loop_match.start()] + loop_match.group(1) + b"#999999" + loop_match.group(2)
        + content[loop_match.end():]
    )
    with pytest.raises(InvalidModelError, match="missing Cartesian point"):
        import_step(damaged)


def test_step_import_rejects_wrong_plane_orientation_and_unit_prefix():
    content = export_step(make_mesh()).content
    damaged = content.replace(b"FACE_SURFACE('',(#", b"FACE_SURFACE('',(#", 1)
    # The first FACE_SURFACE same_sense flag is the final .T. before the next entity.
    face_start = damaged.index(b"FACE_SURFACE")
    face_end = damaged.index(b";", face_start)
    face = damaged[face_start:face_end]
    damaged = damaged[:face_start] + face.replace(b".T.", b".F.", 1) + damaged[face_end:]
    with pytest.raises(InvalidModelError, match="same_sense"):
        import_step(damaged)
    unsupported = content.replace(b"SI_UNIT(.MILLI.,.METRE.)", b"SI_UNIT(.MICRO.,.METRE.)")
    with pytest.raises(InvalidModelError, match="unsupported or missing SI"):
        import_step(unsupported)


def test_step_import_rejects_representation_with_wrong_geometric_context():
    content = export_step(make_mesh()).content
    unit_match = re.search(rb"#([0-9]+)=\(LENGTH_UNIT", content)
    representation_match = re.search(
        rb"(FACETED_BREP_SHAPE_REPRESENTATION\('Universal Platform', \(#[0-9]+\), )#[0-9]+(\))",
        content,
    )
    assert unit_match and representation_match
    damaged = (
        content[:representation_match.start()]
        + representation_match.group(1) + b"#" + unit_match.group(1) + representation_match.group(2)
        + content[representation_match.end():]
    )
    with pytest.raises(InvalidModelError, match="geometric context"):
        import_step(damaged)


def test_step_import_rejects_context_assigning_a_different_length_unit():
    content = export_step(make_mesh()).content
    context_match = re.search(
        rb"(#([0-9]+)=\(GEOMETRIC_REPRESENTATION_CONTEXT\(3\) "
        rb"GLOBAL_UNIT_ASSIGNED_CONTEXT\(\(#)([0-9]+)(\)\) REPRESENTATION_CONTEXT)",
        content,
    )
    brep_match = re.search(rb"#([0-9]+)=FACETED_BREP\(", content)
    assert context_match and brep_match
    damaged = (
        content[:context_match.start()]
        + context_match.group(1) + brep_match.group(1) + context_match.group(4)
        + content[context_match.end():]
    )
    with pytest.raises(InvalidModelError, match="assign the declared SI length unit"):
        import_step(damaged)


def test_step_import_preserves_source_digest_and_result_validation_summary():
    mesh = make_mesh("cm")
    artifact = export_step(mesh)
    result = import_step(artifact.content)
    assert artifact.to_dict()["format"] == "ISO10303-21_AP214_FACETED_BREP"
    assert result.to_dict()["file_sha256"] == artifact.content_sha256
    assert result.to_dict()["validation"]["valid"] is True


def test_imported_step_mesh_snapshot_round_trips():
    mesh = import_step(export_step(make_mesh()).content).mesh
    snapshot = mesh.to_dict()
    restored = TriangleMesh.from_dict(snapshot)
    assert restored.to_dict() == snapshot
    assert validate_triangle_mesh(restored).valid
