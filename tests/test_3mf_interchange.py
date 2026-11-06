from dataclasses import replace
from io import BytesIO
from zipfile import ZIP_DEFLATED, ZipFile

import pytest

from universal_platform.engineering.errors import InvalidModelError
from universal_platform.engineering.geometry import Vec3
from universal_platform.engineering.mesh import TriangleMesh, tessellate_box, validate_triangle_mesh
from universal_platform.engineering.primitive_geometry import BoxSolid
from universal_platform.engineering.three_mf import export_3mf, import_3mf


def box_mesh(unit="mm"):
    solid = BoxSolid("solid.fixture", "part.frame", Vec3(10, 8, 4), unit)
    return tessellate_box(solid)


def package_parts(content):
    with ZipFile(BytesIO(content), "r") as archive:
        return {name: archive.read(name) for name in archive.namelist()}


def rebuild_package(parts):
    output = BytesIO()
    with ZipFile(output, "w", ZIP_DEFLATED) as archive:
        for name, value in parts.items():
            archive.writestr(name, value)
    return output.getvalue()


def test_3mf_export_is_deterministic_and_round_trips_watertight_mesh():
    mesh = box_mesh()
    first = export_3mf(mesh)
    second = export_3mf(mesh)
    assert first.content == second.content
    assert first.content_sha256 == second.content_sha256
    restored = import_3mf(first.content)
    assert restored.validation.valid
    assert restored.validation.watertight
    assert restored.validation.consistently_oriented
    assert restored.mesh.solid_id == mesh.solid_id
    assert restored.mesh.frame_id == mesh.frame_id
    assert restored.mesh.length_unit == mesh.length_unit
    assert restored.mesh.source_kind == "IMPORTED_3MF"
    assert restored.mesh.source_geometry_sha256 == mesh.source_geometry_sha256
    assert restored.mesh.vertices == mesh.vertices
    assert restored.mesh.triangles == mesh.triangles


def test_3mf_supports_explicit_registered_unit_mapping_for_inches():
    mesh = box_mesh("in")
    restored = import_3mf(export_3mf(mesh).content)
    assert restored.mesh.length_unit == "in"
    assert restored.mesh.vertices == mesh.vertices


def test_3mf_export_rejects_non_watertight_mesh_and_unsupported_units():
    mesh = box_mesh()
    open_mesh = replace(mesh, triangles=mesh.triangles[:-1])
    with pytest.raises(InvalidModelError, match="watertight"):
        export_3mf(open_mesh)
    unsupported = tessellate_box(BoxSolid("solid.km", "part.frame", Vec3(1, 1, 1), "km"))
    with pytest.raises(InvalidModelError, match="does not support"):
        export_3mf(unsupported)


def test_3mf_import_rejects_extra_parts_and_unsafe_package_structure():
    parts = package_parts(export_3mf(box_mesh()).content)
    parts["../outside.txt"] = b"bad"
    with pytest.raises(InvalidModelError, match="missing or unsupported parts"):
        import_3mf(rebuild_package(parts))


def test_3mf_import_rejects_dtd_entity_declarations():
    parts = package_parts(export_3mf(box_mesh()).content)
    model = parts["3D/3dmodel.model"]
    parts["3D/3dmodel.model"] = b'<!DOCTYPE model [<!ENTITY x "boom">]>' + model
    with pytest.raises(InvalidModelError, match="DTD or entity"):
        import_3mf(rebuild_package(parts))


def test_3mf_import_rejects_out_of_range_triangle_indices_and_nonfinite_vertices():
    parts = package_parts(export_3mf(box_mesh()).content)
    model = parts["3D/3dmodel.model"]
    parts["3D/3dmodel.model"] = model.replace(b'v1="0"', b'v1="999"', 1)
    with pytest.raises(InvalidModelError, match="outside the vertex"):
        import_3mf(rebuild_package(parts))
    parts = package_parts(export_3mf(box_mesh()).content)
    parts["3D/3dmodel.model"] = parts["3D/3dmodel.model"].replace(b'x="0"', b'x="NaN"', 1)
    with pytest.raises(InvalidModelError, match="finite"):
        import_3mf(rebuild_package(parts))


def test_3mf_import_rejects_invalid_relationship_and_unsupported_unit():
    parts = package_parts(export_3mf(box_mesh()).content)
    parts["_rels/.rels"] = parts["_rels/.rels"].replace(b"/3D/3dmodel.model", b"/3D/missing.model")
    with pytest.raises(InvalidModelError, match="primary 3D model"):
        import_3mf(rebuild_package(parts))
    parts = package_parts(export_3mf(box_mesh()).content)
    parts["3D/3dmodel.model"] = parts["3D/3dmodel.model"].replace(b'unit="millimeter"', b'unit="micron"')
    with pytest.raises(InvalidModelError, match="not supported"):
        import_3mf(rebuild_package(parts))


def test_3mf_artifact_and_import_result_expose_package_hash_and_validation():
    mesh = box_mesh()
    artifact = export_3mf(mesh)
    result = import_3mf(artifact.content)
    assert artifact.to_dict()["format"] == "3MF_CORE"
    assert result.to_dict()["format"] == "3MF_CORE"
    assert result.to_dict()["package_sha256"] == artifact.content_sha256
    assert result.to_dict()["validation"]["valid"] is True


def test_imported_mesh_snapshot_round_trips_with_new_source_kind():
    restored = import_3mf(export_3mf(box_mesh()).content).mesh
    snapshot = restored.to_dict()
    decoded = TriangleMesh.from_dict(snapshot)
    assert decoded.to_dict() == snapshot
    assert validate_triangle_mesh(decoded).valid
