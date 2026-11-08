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
    assert result.unique_plane_count>12
    assert all(report.oracle_certified for report in result.global_arrangement.coverage_reports)


def test_multi_mesh_arrangement_rejects_coplanar_edge_only_contact():
    meshes=(_box("a",2.0),_box("b",2.0,(2.0,2.0,0.0)))
    with pytest.raises(InvalidModelError,match="coplanar point/edge contact"):
        arrange_faceted_boolean_meshes(meshes)


def test_multi_mesh_arrangement_fails_closed_at_source_triangle_budget():
    meshes=(_box("a",2.0),_box("b",2.0,(1.0,1.0,1.0)))
    with pytest.raises(InvalidModelError,match="max_source_triangles"):
        arrange_faceted_boolean_meshes(meshes,max_source_triangles=10)
