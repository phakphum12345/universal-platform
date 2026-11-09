from fractions import Fraction as F
from hashlib import sha256

import pytest

from universal_platform.engineering import (
    BRepBooleanOperation,
    CADGeneratorService,
    RationalFacetedSolid,
    SelectedBoundaryFragment,
    BooleanBoundarySelection,
    assemble_rational_boolean_solid,
    BoxSolid,
    Vec3,
    TriangleMesh,
    tessellate_box,
    SQLiteFeatureArtifactCache,
    SQLiteFeatureHistoryStore,
)
from universal_platform.engineering.errors import InvalidModelError


def _box(solid_id, size, offset=(0.0, 0.0, 0.0)):
    source = tessellate_box(BoxSolid(solid_id, "world", Vec3(size, size, size)))
    vertices = tuple(
        Vec3(v.x + offset[0], v.y + offset[1], v.z + offset[2])
        for v in source.vertices
    )
    digest = sha256(f"{solid_id}:{size}:{offset}".encode()).hexdigest()
    return TriangleMesh(
        solid_id, "world", "m", "BOX", digest, vertices, source.triangles
    )


def _rational_tetra_selection():
    vertices = (
        (F(0), F(0), F(0)),
        (F(0), F(0), F(1, 3)),
        (F(0), F(1), F(0)),
        (F(1), F(0), F(0)),
    )
    faces = (
        (0, 2, 3),
        (0, 3, 1),
        (0, 1, 2),
        (3, 2, 1),
    )
    fragments = tuple(
        SelectedBoundaryFragment(
            0, index, tuple(vertices[item] for item in face), False, ()
        )
        for index, face in enumerate(faces)
    )
    selection = BooleanBoundarySelection(
        BRepBooleanOperation.UNION, fragments, 0, 0, 0
    )
    return selection


def test_rational_boolean_assembly_preserves_non_binary_coordinates():
    mesh = _box("source", 1.0)
    artifact = assemble_rational_boolean_solid(
        _rational_tetra_selection(), (mesh,), result_id="rational.tetra"
    )
    assert isinstance(artifact, RationalFacetedSolid)
    assert artifact.exact_signed_volume == F(1, 18)
    snapshot = artifact.to_dict()
    assert ["1", "3"] in [point[2] for point in snapshot["vertices"]]
    restored = RationalFacetedSolid.from_dict(snapshot)
    assert restored == artifact
    assert restored.to_dict() == snapshot


def test_rational_boolean_assembly_rejects_multiple_disconnected_shells():
    mesh = _box("source", 1.0)
    first = _rational_tetra_selection().selected_fragments
    shifted = tuple(
        SelectedBoundaryFragment(
            item.source_solid_index,
            item.source_triangle_index + len(first),
            tuple((point[0] + 3, point[1], point[2]) for point in item.vertices),
            item.reversed_for_result,
            item.other_solid_membership,
        )
        for item in first
    )
    selection = BooleanBoundarySelection(
        BRepBooleanOperation.UNION, first + shifted, 0, 0, 0
    )
    with pytest.raises(InvalidModelError, match="exactly one connected shell"):
        assemble_rational_boolean_solid(selection, (mesh,))


def test_cad_generator_exposes_serializable_exact_rational_boolean_path(tmp_path):
    service = CADGeneratorService(
        SQLiteFeatureHistoryStore(tmp_path / "source.sqlite3"),
        SQLiteFeatureArtifactCache(tmp_path / "artifacts.sqlite3"),
    )
    meshes = (
        _box("a", 2.0),
        _box("b", 2.0, (1.0, 1.0, 1.0)),
    )
    artifact = service.execute_rational_faceted_boolean(
        meshes, BRepBooleanOperation.UNION, result_id="generator.union"
    )
    snapshot = artifact.to_dict()
    assert snapshot["profile"] == "RATIONAL_FACETED_SOLID_V1"
    assert RationalFacetedSolid.from_dict(snapshot) == artifact
    assert artifact.exact_signed_volume == F(15)
