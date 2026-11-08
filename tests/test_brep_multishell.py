import hashlib
import json
from pathlib import Path

import pytest

from universal_platform.engineering import (
    BRepMultiShellSolid,
    BRepSolid,
    BRepMultiShellValidationResult,
    validate_brep_multishell_solid,
)
from universal_platform.engineering.brep import brep_from_triangle_mesh, triangle_mesh_from_brep
from universal_platform.engineering.errors import InvalidModelError
from universal_platform.engineering.geometry import Vec3
from universal_platform.engineering.mesh import TriangleMesh, tessellate_box, validate_triangle_mesh
from universal_platform.engineering.primitive_geometry import BoxSolid


def box_brep(solid_id, minimum, maximum, *, frame="part.frame", unit="mm"):
    dimensions = Vec3(
        maximum[0] - minimum[0],
        maximum[1] - minimum[1],
        maximum[2] - minimum[2],
    )
    source = BoxSolid(solid_id, frame, dimensions, unit)
    mesh = tessellate_box(source)
    vertices = tuple(
        Vec3(v.x + minimum[0], v.y + minimum[1], v.z + minimum[2])
        for v in mesh.vertices
    )
    digest = hashlib.sha256(json.dumps(
        {"solid_id": solid_id, "minimum": minimum, "maximum": maximum, "unit": unit},
        sort_keys=True, separators=(",", ":"),
    ).encode()).hexdigest()
    translated = TriangleMesh(
        solid_id, frame, unit, "BOX", digest, vertices, mesh.triangles
    )
    return brep_from_triangle_mesh(translated)


def test_multi_shell_box_with_one_cavity_has_subtractive_volume_and_watertight_mesh():
    outer = box_brep("outer", (0, 0, 0), (10, 10, 10))
    cavity = box_brep("cavity", (2, 2, 2), (4, 4, 4))
    solid = BRepMultiShellSolid("part.with-cavity", outer, (cavity,))

    result = validate_brep_multishell_solid(solid)
    mesh = solid.to_mesh()
    mesh_result = validate_triangle_mesh(mesh)

    assert result.valid
    assert result.shell_count == 2
    assert result.cavity_count == 1
    assert result.intersection_status == "NO_INTERSECTIONS_FOUND"
    assert result.net_signed_volume == pytest.approx(992.0)
    assert mesh_result.valid and mesh_result.watertight and mesh_result.consistently_oriented
    assert mesh_result.signed_volume == pytest.approx(992.0)
    assert mesh.source_kind == "IMPORTED_BREP"


def test_multi_shell_supports_multiple_disjoint_cavities_deterministically():
    outer = box_brep("outer", (0, 0, 0), (10, 10, 10))
    first = box_brep("cavity-a", (1, 1, 1), (2, 2, 2))
    second = box_brep("cavity-b", (7, 7, 7), (9, 9, 9))
    solid = BRepMultiShellSolid("part.two-cavities", outer, (first, second))

    mesh_a = solid.to_mesh()
    mesh_b = BRepMultiShellSolid("part.two-cavities", outer, (first, second)).to_mesh()
    assert validate_brep_multishell_solid(solid).valid
    assert validate_triangle_mesh(mesh_a).signed_volume == pytest.approx(993.0)
    assert mesh_a.triangles == mesh_b.triangles
    assert mesh_a.vertices == mesh_b.vertices


def test_multi_shell_rejects_cavity_outside_outer_shell():
    outer = box_brep("outer", (0, 0, 0), (10, 10, 10))
    outside = box_brep("outside", (11, 11, 11), (12, 12, 12))
    with pytest.raises(InvalidModelError, match="outside or on"):
        BRepMultiShellSolid("part.invalid", outer, (outside,))


def test_multi_shell_rejects_intersecting_or_nested_cavity_shells():
    outer = box_brep("outer", (0, 0, 0), (10, 10, 10))
    first = box_brep("cavity-a", (1, 1, 1), (5, 5, 5))
    overlap = box_brep("cavity-b", (4, 4, 4), (7, 7, 7))
    with pytest.raises(InvalidModelError, match="boundaries are not proven disjoint"):
        BRepMultiShellSolid("part.overlap", outer, (first, overlap))

    nested = box_brep("cavity-nested", (2, 2, 2), (3, 3, 3))
    with pytest.raises(InvalidModelError, match="non-nested"):
        BRepMultiShellSolid("part.nested", outer, (first, nested))


def test_multi_shell_rejects_frame_and_unit_mismatch():
    outer = box_brep("outer", (0, 0, 0), (10, 10, 10))
    wrong_frame = box_brep("wrong-frame", (2, 2, 2), (4, 4, 4), frame="world")
    with pytest.raises(InvalidModelError, match="same frame and length unit"):
        BRepMultiShellSolid("part.bad-frame", outer, (wrong_frame,))

    wrong_unit = box_brep("wrong-unit", (2, 2, 2), (4, 4, 4), unit="cm")
    with pytest.raises(InvalidModelError, match="same frame and length unit"):
        BRepMultiShellSolid("part.bad-unit", outer, (wrong_unit,))


def test_multi_shell_snapshot_round_trip_digest_and_strict_schema():
    outer = box_brep("outer", (0, 0, 0), (10, 10, 10))
    cavity = box_brep("cavity", (2, 2, 2), (4, 4, 4))
    solid = BRepMultiShellSolid("part.with-cavity", outer, (cavity,))
    snapshot = json.loads(json.dumps(solid.to_dict()))
    restored = BRepMultiShellSolid.from_dict(snapshot)
    assert restored.to_dict() == snapshot
    assert restored.source_geometry_sha256 == solid.source_geometry_sha256

    schema = json.loads((Path(__file__).parents[1] / "schemas" / "geometry" /
                         "faceted-brep-multishell-solid.schema.json").read_text(encoding="utf-8"))
    assert set(snapshot) == set(schema["required"])
    assert schema["additionalProperties"] is False
    assert schema["properties"]["profile"]["const"] == BRepMultiShellSolid.PROFILE

    tampered = dict(snapshot)
    tampered["source_geometry_sha256"] = "0" * 64
    with pytest.raises(InvalidModelError, match="digest"):
        BRepMultiShellSolid.from_dict(tampered)
    with pytest.raises(InvalidModelError, match="missing or unknown"):
        BRepMultiShellSolid.from_dict(dict(snapshot, unexpected=True))


def test_multi_shell_accepts_single_shell_compatibility_without_cavities():
    outer = box_brep("outer", (0, 0, 0), (2, 2, 2))
    solid = BRepMultiShellSolid("part.solid", outer)
    assert solid.to_mesh().triangles == triangle_mesh_from_brep(outer).triangles
    assert validate_brep_multishell_solid(solid).net_signed_volume == pytest.approx(8.0)


def test_multi_shell_contract_is_indexed_and_public_api_is_exported():
    from universal_platform.engineering import BRepMultiShellSolid as PublicModel
    root = Path(__file__).parents[1]
    index = (root / "DOCUMENTATION_INDEX.md").read_text(encoding="utf-8")
    contract = root / "docs" / "design-3d" / "FACETED_BREP_MULTISHELL_SOLID_CONTRACT.md"
    assert PublicModel is BRepMultiShellSolid
    assert contract.is_file()
    assert "FACETED_BREP_MULTISHELL_SOLID_CONTRACT.md" in index
