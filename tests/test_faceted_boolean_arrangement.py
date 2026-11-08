from hashlib import sha256

import pytest

from universal_platform.engineering.errors import InvalidModelError
from universal_platform.engineering.faceted_boolean_arrangement import arrange_faceted_boolean_meshes
from universal_platform.engineering.geometry import Vec3
from universal_platform.engineering.mesh import TriangleMesh, tessellate_box
from universal_platform.engineering.primitive_geometry import BoxSolid


def _box(solid_id, size, offset=(0.0, 0.0, 0.0)):
    source=tessellate_box(BoxSolid(solid_id,"world",Vec3(size,size,size)))
    vertices=tuple(Vec3(v.x+offset[0],v.y+offset[1],v.z+offset[2]) for v in source.vertices)
    digest=sha256(f"{solid_id}:{size}:{offset}".encode()).hexdigest()
    return TriangleMesh(solid_id,"world","m","BOX",digest,vertices,source.triangles)


def test_multi_mesh_arrangement_splits_intersecting_non_coplanar_boxes():
    meshes=(_box("a",2.0),_box("b",2.0,(1.0,1.0,1.0)))
    result=arrange_faceted_boolean_meshes(meshes)
    assert result.source_triangle_count==24
    assert result.unique_plane_count==12
    assert result.coplanar_pair_checks==0
    assert all(report.oracle_certified for report in result.global_arrangement.coverage_reports)
    assert all(len(fragments)>len(mesh.triangles)
               for fragments,mesh in zip(result.fragments_by_solid,meshes))
    assert all(fragment.source_triangle_index < len(meshes[index].triangles)
               for index,items in enumerate(result.fragments_by_solid) for fragment in items)


def test_multi_mesh_arrangement_allows_coplanar_but_disjoint_faces():
    meshes=(_box("a",2.0),_box("b",2.0,(3.0,0.0,0.0)))
    result=arrange_faceted_boolean_meshes(meshes)
    assert result.coplanar_pair_checks>0
    assert len(result.fragments_by_solid)==2


def test_multi_mesh_arrangement_splits_coplanar_area_overlap():
    meshes=(_box("a",2.0),_box("b",2.0,(0.5,0.0,0.0)))
    result=arrange_faceted_boolean_meshes(meshes)
    assert result.coplanar_pair_checks>0
    assert result.unique_plane_count>=12
    assert all(report.oracle_certified for report in result.global_arrangement.coverage_reports)


def test_multi_mesh_arrangement_rejects_coplanar_edge_only_contact():
    meshes=(_box("a",2.0),_box("b",2.0,(2.0,2.0,0.0)))
    with pytest.raises(InvalidModelError,match="coplanar point/edge contact"):
        arrange_faceted_boolean_meshes(meshes)


def test_multi_mesh_arrangement_fails_closed_at_source_triangle_budget():
    meshes=(_box("a",2.0),_box("b",2.0,(1.0,1.0,1.0)))
    with pytest.raises(InvalidModelError,match="max_source_triangles"):
        arrange_faceted_boolean_meshes(meshes,max_source_triangles=10)

def _combine_meshes(solid_id, meshes):
    vertices = []
    triangles = []
    for mesh in meshes:
        offset = len(vertices)
        vertices.extend(mesh.vertices)
        triangles.extend(tuple(index + offset for index in face)
                         for face in mesh.triangles)
    digest = sha256(solid_id.encode()).hexdigest()
    return TriangleMesh(
        solid_id, "world", "m", "BOX", digest,
        tuple(vertices), tuple(triangles),
    )


def _mixed_coplanar_contact_meshes():
    # Component pair A2/B2 touches only along an edge on planes x=12 and y=2.
    # Separate component pairs A3/B3 and A4/B4 overlap with positive area on
    # those same planes.
    first = _combine_meshes("first", (
        _box("a2", 2.0, (10.0, 0.0, 0.0)),
        _box("a3", 2.0, (12.0, 10.0, 5.0)),
        _box("a4", 2.0, (20.0, 0.0, 10.0)),
    ))
    second = _combine_meshes("second", (
        _box("b2", 2.0, (12.0, 2.0, 0.0)),
        _box("b3", 2.0, (12.0, 11.0, 5.0)),
        _box("b4", 2.0, (21.0, 0.0, 11.0)),
    ))
    return first, second


def test_coplanar_contact_is_not_hidden_by_unrelated_overlap_on_same_planes():
    with pytest.raises(InvalidModelError, match="coplanar point/edge contact"):
        arrange_faceted_boolean_meshes(_mixed_coplanar_contact_meshes())


def test_coplanar_contact_coverage_fails_closed_at_aggregate_budget():
    with pytest.raises(InvalidModelError, match="max_coplanar_coverage_checks"):
        arrange_faceted_boolean_meshes(
            _mixed_coplanar_contact_meshes(), max_coplanar_coverage_checks=1
        )


def test_source_triangle_budget_is_checked_before_mesh_topology_analysis():
    valid = _box("oversized", 2.0)
    malformed = TriangleMesh(
        "oversized", "world", "m", "BOX", valid.source_geometry_sha256,
        valid.vertices, valid.triangles + valid.triangles,
    )
    with pytest.raises(InvalidModelError, match="max_source_triangles"):
        arrange_faceted_boolean_meshes(
            (malformed, _box("other", 1.0)), max_source_triangles=20
        )
