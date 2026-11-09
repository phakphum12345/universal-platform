from fractions import Fraction as F
from hashlib import sha256
import json

import pytest

from universal_platform.engineering import (
    BRepBooleanOperation,
    CADGeneratorService,
    RationalBooleanSolid,
    SelectedBoundaryFragment,
    BooleanBoundarySelection,
    assemble_rational_boolean_solid,
    BoxSolid,
    TriangleMesh,
    tessellate_box,
    SQLiteFeatureArtifactCache,
    SQLiteFeatureHistoryStore,
)
from universal_platform.engineering.errors import InvalidModelError
from universal_platform.engineering.geometry import Vec3


def _box(solid_id, size, offset=(0.0, 0.0, 0.0)):
    source = tessellate_box(BoxSolid(solid_id, "world", Vec3(size, size, size)))
    vertices = tuple(
        Vec3(v.x + offset[0], v.y + offset[1], v.z + offset[2])
        for v in source.vertices
    )
    digest = sha256(f"{solid_id}:{size}:{offset}".encode()).hexdigest()
    return TriangleMesh(solid_id, "world", "m", "BOX", digest, vertices, source.triangles)


def _tetra_faces(vertices, source_triangle_offset=0, reverse=False):
    faces = ((0, 2, 3), (0, 3, 1), (0, 1, 2), (3, 2, 1))
    fragments = []
    for index, face in enumerate(faces):
        ordered = tuple(reversed(face)) if reverse else face
        fragments.append(SelectedBoundaryFragment(
            0, source_triangle_offset + index,
            tuple(vertices[item] for item in ordered), False, ()
        ))
    return tuple(fragments)


def _tetra(origin=(F(0), F(0), F(0)), scale=F(1)):
    base = ((F(0), F(0), F(0)), (F(0), F(0), F(1)),
            (F(0), F(1), F(0)), (F(1), F(0), F(0)))
    return tuple(
        tuple(origin[axis] + point[axis] * scale for axis in range(3))
        for point in base
    )


def _selection(fragments):
    return BooleanBoundarySelection(BRepBooleanOperation.UNION, tuple(fragments), 0, 0, 0)


def test_rational_boolean_assembly_preserves_non_binary_coordinates_and_round_trips():
    mesh = _box("source", 1.0)
    artifact = assemble_rational_boolean_solid(
        _selection(_tetra_faces(_tetra(scale=F(1, 3)))), (mesh,),
        result_id="rational.tetra"
    )
    assert isinstance(artifact, RationalBooleanSolid)
    assert artifact.exact_net_volume == F(1, 162)
    snapshot = artifact.to_dict()
    assert snapshot["profile"] == "RATIONAL_BOOLEAN_SOLID_V1"
    assert any(["1", "3"] in point for point in
               snapshot["components"][0]["outer_shell"]["solid"]["vertices"])
    restored = RationalBooleanSolid.from_dict(snapshot)
    assert restored == artifact
    assert restored.to_dict() == snapshot


def test_rational_boolean_assembly_supports_disconnected_outer_components():
    mesh = _box("source", 1.0)
    first = _tetra(scale=F(1, 2))
    second = _tetra(origin=(F(4), F(0), F(0)), scale=F(1, 2))
    artifact = assemble_rational_boolean_solid(
        _selection(_tetra_faces(first) + _tetra_faces(second, 4)),
        (mesh,), result_id="rational.disjoint"
    )
    assert len(artifact.components) == 2
    assert artifact.shell_count == 2
    assert artifact.exact_net_volume == F(1, 24)


def test_rational_boolean_assembly_preserves_cavity_role_and_exact_net_volume():
    mesh = _box("source", 1.0)
    outer = _tetra(scale=F(3))
    cavity = _tetra(origin=(F(1, 4), F(1, 4), F(1, 4)), scale=F(1, 4))
    fragments = _tetra_faces(outer) + _tetra_faces(cavity, 4, reverse=True)
    artifact = assemble_rational_boolean_solid(
        _selection(fragments), (mesh,), result_id="rational.cavity"
    )
    component = artifact.components[0]
    assert len(component.cavity_shells) == 1
    assert component.cavity_shells[0].role == "CAVITY"
    assert component.cavity_shells[0].parent_outer_shell_id == component.outer_shell.shell_id
    assert artifact.exact_net_volume == F(27, 6) - F(1, 384)
    assert artifact.to_dict()["resource_counters"]["containment_ray_checks"] > 0


def test_rational_boolean_assembly_rejects_intersecting_or_touching_shells():
    mesh = _box("source", 1.0)
    first = _tetra(scale=F(1))
    touching = _tetra(origin=(F(1), F(0), F(0)), scale=F(1))
    with pytest.raises(InvalidModelError, match="intersect or touch"):
        assemble_rational_boolean_solid(
            _selection(_tetra_faces(first) + _tetra_faces(touching, 4)),
            (mesh,), result_id="rational.touching"
        )


def test_rational_boolean_assembly_rejects_bad_cavity_parentage():
    mesh = _box("source", 1.0)
    outer = _tetra(scale=F(1))
    outside_cavity = _tetra(origin=(F(5), F(0), F(0)), scale=F(1, 4))
    with pytest.raises(InvalidModelError, match="strictly inside exactly one outer"):
        assemble_rational_boolean_solid(
            _selection(_tetra_faces(outer) + _tetra_faces(outside_cavity, 4, reverse=True)),
            (mesh,), result_id="rational.bad-cavity"
        )


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
    assert snapshot["profile"] == "RATIONAL_BOOLEAN_SOLID_V1"
    assert RationalBooleanSolid.from_dict(snapshot) == artifact
    assert artifact.exact_net_volume == F(15)



def test_rational_boolean_shell_containment_budget_is_preflighted():
    mesh = _box("source", 1.0)
    outer = _tetra(scale=F(3))
    cavity = _tetra(origin=(F(1, 4), F(1, 4), F(1, 4)), scale=F(1, 4))
    with pytest.raises(InvalidModelError, match="containment ray budget"):
        assemble_rational_boolean_solid(
            _selection(_tetra_faces(outer) + _tetra_faces(cavity, 4, reverse=True)),
            (mesh,), result_id="rational.cavity-budget",
            max_containment_ray_checks=1,
        )



def test_rational_boolean_deserialization_rejects_rehashed_invalid_cavity_parent():
    mesh = _box("source", 1.0)
    outer = _tetra(scale=F(3))
    cavity = _tetra(origin=(F(1, 4), F(1, 4), F(1, 4)), scale=F(1, 4))
    artifact = assemble_rational_boolean_solid(
        _selection(_tetra_faces(outer) + _tetra_faces(cavity, 4, reverse=True)),
        (mesh,), result_id="rational.cavity-tamper"
    )
    snapshot = artifact.to_dict()
    cavity_solid = snapshot["components"][0]["cavity_shells"][0]["solid"]
    for vertex in cavity_solid["vertices"]:
        shifted_x = F(int(vertex[0][0]), int(vertex[0][1])) + 5
        vertex[0] = [str(shifted_x.numerator), str(shifted_x.denominator)]
    # Keep the serialized aggregate-bit counter consistent with the deliberately
    # translated (but otherwise valid) child shell so validation reaches containment.
    all_shells = []
    for component_record in snapshot["components"]:
        all_shells.append(component_record["outer_shell"]["solid"])
        all_shells.extend(item["solid"] for item in component_record["cavity_shells"])
    snapshot["resource_counters"]["aggregate_rational_bits"] = sum(
        abs(int(numerator)).bit_length() + int(denominator).bit_length()
        for shell_record in all_shells
        for vertex in shell_record["vertices"]
        for numerator, denominator in vertex
    )
    child_payload = {
        key: value for key, value in cavity_solid.items() if key != "result_sha256"
    }
    cavity_solid["result_sha256"] = sha256(
        json.dumps(child_payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    payload = {key: value for key, value in snapshot.items() if key != "result_sha256"}
    snapshot["result_sha256"] = sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    with pytest.raises(InvalidModelError, match="cavity parentage does not match exact containment"):
        RationalBooleanSolid.from_dict(snapshot)
