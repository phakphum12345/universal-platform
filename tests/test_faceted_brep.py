import json
from pathlib import Path
from dataclasses import replace

import pytest

from universal_platform.engineering.brep import (
    BRepEdge,
    BRepEdgeUse,
    BRepFace,
    BRepLoop,
    BRepShell,
    BRepSolid,
    BRepVertex,
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


def test_faceted_brep_contract_is_indexed():
    root = Path(__file__).parents[1]
    index = (root / "DOCUMENTATION_INDEX.md").read_text(encoding="utf-8")
    contract = root / "docs" / "design-3d" / "FACETED_BREP_TOPOLOGY_CONTRACT.md"
    assert contract.is_file()
    assert "FACETED_BREP_TOPOLOGY_CONTRACT.md" in index



def hollow_box_brep():
    coordinates = {
        "o0": (0, 0, 0), "o1": (4, 0, 0), "o2": (4, 4, 0), "o3": (0, 4, 0),
        "o4": (0, 0, 1), "o5": (4, 0, 1), "o6": (4, 4, 1), "o7": (0, 4, 1),
        "i0": (1, 1, 0), "i1": (1, 3, 0), "i2": (3, 3, 0), "i3": (3, 1, 0),
        "j0": (1, 1, 1), "j1": (1, 3, 1), "j2": (3, 3, 1), "j3": (3, 1, 1),
    }
    face_specs = (
        ("top", "top.outer", ("o4", "o5", "o6", "o7"),
         (("top.inner", ("j0", "j1", "j2", "j3")),)),
        ("bottom", "bottom.outer", ("o0", "o3", "o2", "o1"),
         (("bottom.inner", ("i0", "i3", "i2", "i1")),)),
        ("front", "front.outer", ("o0", "o1", "o5", "o4"), ()),
        ("right", "right.outer", ("o1", "o2", "o6", "o5"), ()),
        ("back", "back.outer", ("o2", "o3", "o7", "o6"), ()),
        ("left", "left.outer", ("o3", "o0", "o4", "o7"), ()),
        ("hole.left", "hole.left.loop", ("i0", "i1", "j1", "j0"), ()),
        ("hole.back", "hole.back.loop", ("i1", "i2", "j2", "j1"), ()),
        ("hole.right", "hole.right.loop", ("i2", "i3", "j3", "j2"), ()),
        ("hole.front", "hole.front.loop", ("i3", "i0", "j0", "j3"), ()),
    )
    edge_by_pair = {}
    loops = []
    faces = []
    for face_id, outer_id, outer_vertices, inner_specs in face_specs:
        loop_specs = ((outer_id, outer_vertices), *inner_specs)
        for loop_id, vertex_ids in loop_specs:
            uses = []
            for index, start in enumerate(vertex_ids):
                end = vertex_ids[(index + 1) % len(vertex_ids)]
                canonical = tuple(sorted((start, end)))
                edge_id = "edge." + canonical[0] + "." + canonical[1]
                edge_by_pair.setdefault(
                    canonical, BRepEdge(edge_id, canonical[0], canonical[1])
                )
                uses.append(BRepEdgeUse(edge_id, (start, end) == canonical))
            loops.append(BRepLoop(loop_id, tuple(uses)))
        faces.append(BRepFace(face_id, outer_id, tuple(item[0] for item in inner_specs)))
    vertices = tuple(
        BRepVertex(vertex_id, Vec3(*point)) for vertex_id, point in coordinates.items()
    )
    return BRepSolid(
        "solid.hollow-box", "part.frame", "mm", "a" * 64,
        vertices, tuple(edge_by_pair.values()), tuple(loops), tuple(faces),
        BRepShell("shell.hollow-box", tuple(face.face_id for face in faces)),
    )


def test_polygonal_brep_supports_quad_faces_and_a_square_through_hole():
    solid = hollow_box_brep()
    result = validate_brep_solid(solid)

    assert result.valid and result.closed and result.manifold
    assert result.consistently_oriented and result.connected
    assert result.euler_characteristic == 0
    assert result.genus == 1
    assert result.signed_volume == pytest.approx(12.0)
    assert len(solid.vertices) == 16
    assert len(solid.edges) == 24
    assert len(solid.faces) == 10
    restored = BRepSolid.from_dict(solid.to_dict())
    assert restored.to_dict() == solid.to_dict()
    with pytest.raises(InvalidModelError, match="triangular faces without inner loops"):
        triangle_mesh_from_brep(solid)


def test_polygonal_brep_rejects_non_planar_face_and_invalid_inner_loop_reference():
    solid = hollow_box_brep()
    changed_vertices = tuple(
        BRepVertex(item.vertex_id, Vec3(item.position.x, item.position.y, 1.25))
        if item.vertex_id == "o6" else item
        for item in solid.vertices
    )
    with pytest.raises(InvalidModelError, match="not coplanar|invalid"):
        replace(solid, vertices=changed_vertices)

    changed_faces = tuple(
        BRepFace(item.face_id, item.outer_loop_id, ("loop.missing",))
        if item.face_id == "top" else item
        for item in solid.faces
    )
    with pytest.raises(InvalidModelError, match="missing boundary loop"):
        replace(solid, faces=changed_faces)


def test_faceted_brep_v1_triangular_snapshot_remains_importable():
    legacy = brep_from_triangle_mesh(source_mesh()).to_dict()
    legacy["schema_version"] = "1.0"
    legacy["profile"] = "FACETED_TRIANGULAR_PLANAR_SHELL_V1"
    for face in legacy["faces"]:
        face.pop("inner_loop_ids")
    restored = BRepSolid.from_dict(legacy)
    assert restored.SCHEMA_VERSION == "2.0"
    assert all(not face.inner_loop_ids for face in restored.faces)
    assert validate_brep_solid(restored).valid
