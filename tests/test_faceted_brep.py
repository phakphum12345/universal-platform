import json
from pathlib import Path

import pytest

from universal_platform.engineering.brep import (
    BRepSolid,
    brep_from_triangle_mesh,
    triangle_mesh_from_brep,
    validate_brep_solid,
)
from universal_platform.engineering.errors import InvalidModelError
from universal_platform.engineering.geometry import Vec3
from universal_platform.engineering.mesh import tessellate_box, validate_triangle_mesh
from universal_platform.engineering.primitive_geometry import BoxSolid


def source_mesh():
    return tessellate_box(BoxSolid("solid.fixture", "part.frame", Vec3(12, 8, 4), "mm"))


def test_box_triangle_mesh_converts_to_closed_faceted_brep_and_back():
    mesh = source_mesh()
    solid = brep_from_triangle_mesh(mesh)
    result = validate_brep_solid(solid)
    assert result.valid and result.closed and result.manifold
    assert result.consistently_oriented and result.connected
    assert result.euler_characteristic == 2
    assert result.genus == 0
    assert result.signed_volume > 0
    restored = triangle_mesh_from_brep(solid)
    assert restored.source_kind == "IMPORTED_BREP"
    assert restored.source_geometry_sha256 == mesh.source_geometry_sha256
    assert restored.solid_id == mesh.solid_id
    assert restored.frame_id == mesh.frame_id
    assert restored.length_unit == mesh.length_unit
    assert restored.vertices == mesh.vertices
    assert restored.triangles == mesh.triangles
    assert validate_triangle_mesh(restored).watertight


def test_faceted_brep_snapshot_round_trip_and_schema_contract():
    solid = brep_from_triangle_mesh(source_mesh())
    snapshot = json.loads(json.dumps(solid.to_dict()))
    restored = BRepSolid.from_dict(snapshot)
    assert restored.to_dict() == snapshot
    schema = json.loads((Path(__file__).parents[1] / "schemas" / "geometry" /
                         "faceted-brep-solid.schema.json").read_text(encoding="utf-8"))
    assert set(snapshot) == set(schema["required"])
    assert schema["additionalProperties"] is False
    assert schema["properties"]["profile"]["const"] == BRepSolid.PROFILE


def test_faceted_brep_rejects_open_shell_and_wrong_edge_orientation():
    solid = brep_from_triangle_mesh(source_mesh())
    snapshot = solid.to_dict()
    snapshot["faces"] = snapshot["faces"][:-1]
    snapshot["shell"]["face_ids"] = snapshot["shell"]["face_ids"][:-1]
    with pytest.raises(InvalidModelError, match="exactly two faces|every face"):
        BRepSolid.from_dict(snapshot)

    snapshot = solid.to_dict()
    snapshot["loops"][0]["edge_uses"][0]["forward"] = not snapshot["loops"][0]["edge_uses"][0]["forward"]
    with pytest.raises(InvalidModelError, match="closed connected edge cycle|opposite directions"):
        BRepSolid.from_dict(snapshot)


def test_faceted_brep_rejects_unknown_references_and_unknown_snapshot_fields():
    snapshot = brep_from_triangle_mesh(source_mesh()).to_dict()
    changed = json.loads(json.dumps(snapshot))
    changed["loops"][0]["edge_uses"][0]["edge_id"] = "edge.missing"
    with pytest.raises(InvalidModelError, match="missing edge"):
        BRepSolid.from_dict(changed)
    with pytest.raises(InvalidModelError, match="missing or unknown"):
        BRepSolid.from_dict(dict(snapshot, unexpected=True))


def test_faceted_brep_conversion_requires_valid_watertight_oriented_mesh():
    mesh = source_mesh()
    broken = type(mesh)(
        mesh.solid_id, mesh.frame_id, mesh.length_unit, mesh.source_kind,
        mesh.source_geometry_sha256, mesh.vertices, mesh.triangles[:-1],
    )
    with pytest.raises(InvalidModelError, match="valid, watertight"):
        brep_from_triangle_mesh(broken)


def test_faceted_brep_public_api_is_exported():
    from universal_platform.engineering import BRepSolid as PublicBRepSolid
    from universal_platform.engineering import brep_from_triangle_mesh as public_convert
    assert PublicBRepSolid is BRepSolid
    assert public_convert is brep_from_triangle_mesh
