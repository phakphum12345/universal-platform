from fractions import Fraction
from hashlib import sha256

import pytest

from universal_platform.engineering.brep_boolean import BRepBooleanOperation
from universal_platform.engineering.errors import InvalidModelError
from universal_platform.engineering.boolean_boundary_selection import select_boolean_boundary_fragments
from universal_platform.engineering.geometry import Vec3
from universal_platform.engineering.mesh import TriangleMesh, tessellate_box
from universal_platform.engineering.primitive_geometry import BoxSolid
from universal_platform.engineering.triangle_fragment_arrangement import RationalTriangleFragment


def _box(solid_id, size, offset=0.0):
    source = tessellate_box(BoxSolid(solid_id, "world", Vec3(size, size, size)))
    vertices = tuple(Vec3(v.x+offset, v.y+offset, v.z+offset) for v in source.vertices)
    digest = sha256(f"{solid_id}:{size}:{offset}".encode()).hexdigest()
    return TriangleMesh(solid_id, "world", "m", "BOX", digest, vertices, source.triangles)


def _fragments(mesh):
    result = []
    for face_index, face in enumerate(mesh.triangles):
        points = tuple(tuple(Fraction.from_float(value) for value in (
            mesh.vertices[i].x, mesh.vertices[i].y, mesh.vertices[i].z)) for i in face)
        result.append(RationalTriangleFragment(face_index, (), points))
    return tuple(result)


def _inputs():
    outer, inner = _box("outer", 4.0), _box("inner", 2.0, 1.0)
    return (outer, inner), (_fragments(outer), _fragments(inner))


def test_union_keeps_outer_boundary_and_discards_nested_inner_boundary():
    meshes, fragments = _inputs()
    result = select_boolean_boundary_fragments(meshes, fragments, BRepBooleanOperation.UNION)
    assert len(result.selected_fragments) == 12
    assert {item.source_solid_index for item in result.selected_fragments} == {0}
    assert result.discarded_fragment_count == 12
    assert result.ray_triangle_check_count > 0


def test_intersection_keeps_inner_boundary():
    meshes, fragments = _inputs()
    result = select_boolean_boundary_fragments(meshes, fragments, BRepBooleanOperation.INTERSECTION)
    assert len(result.selected_fragments) == 12
    assert {item.source_solid_index for item in result.selected_fragments} == {1}
    assert not any(item.reversed_for_result for item in result.selected_fragments)


def test_difference_reverses_subtractor_boundary():
    meshes, fragments = _inputs()
    result = select_boolean_boundary_fragments(meshes, fragments, BRepBooleanOperation.DIFFERENCE)
    assert len(result.selected_fragments) == 24
    assert sum(item.reversed_for_result for item in result.selected_fragments) == 12
    assert {item.source_solid_index for item in result.selected_fragments} == {0, 1}


def test_selection_rejects_incomplete_source_face_partition():
    meshes, fragments = _inputs()
    broken = (fragments[0][:-1], fragments[1])
    try:
        select_boolean_boundary_fragments(meshes, broken, BRepBooleanOperation.UNION)
    except Exception as exc:
        assert "cover every source mesh triangle" in str(exc) or "coverage failed" in str(exc)
    else:
        raise AssertionError("incomplete face partition must fail closed")


def test_selection_fails_closed_at_aggregate_ray_triangle_budget():
    meshes, fragments = _inputs()
    with pytest.raises(InvalidModelError, match="max_total_ray_checks"):
        select_boolean_boundary_fragments(
            meshes, fragments, BRepBooleanOperation.UNION,
            max_total_ray_checks=1,
        )



def test_selection_fails_closed_at_aggregate_rational_budget():
    meshes, fragments = _inputs()
    with pytest.raises(InvalidModelError, match="aggregate rational bit budget"):
        select_boolean_boundary_fragments(
            meshes, fragments, BRepBooleanOperation.UNION,
            max_aggregate_rational_bits=1,
        )
