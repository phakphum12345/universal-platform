from hashlib import sha256

from universal_platform.engineering import (
    BRepBooleanOperation,
    CADGeneratorService,
    BoxSolid,
    SQLiteFeatureArtifactCache,
    SQLiteFeatureHistoryStore,
    TriangleMesh,
    tessellate_box,
)
from universal_platform.engineering.geometry import Vec3


def _box(solid_id, size, offset=(0.0, 0.0, 0.0)):
    source=tessellate_box(BoxSolid(solid_id,"world",Vec3(size,size,size)))
    vertices=tuple(Vec3(v.x+offset[0],v.y+offset[1],v.z+offset[2]) for v in source.vertices)
    digest=sha256(f"{solid_id}:{size}:{offset}".encode()).hexdigest()
    return TriangleMesh(solid_id,"world","m","BOX",digest,vertices,source.triangles)


def test_cad_generator_executes_non_coplanar_intersecting_box_union_end_to_end(tmp_path):
    service=CADGeneratorService(
        SQLiteFeatureHistoryStore(tmp_path/"source.sqlite3"),
        SQLiteFeatureArtifactCache(tmp_path/"artifacts.sqlite3"),
    )
    meshes=(_box("a",2.0),_box("b",2.0,(1.0,1.0,1.0)))
    result=service.execute_faceted_boolean(meshes,BRepBooleanOperation.UNION)
    snapshot=result.to_dict()
    assert snapshot["operation"]=="UNION"
    assert snapshot["arrangement"]["source_triangle_count"]==24
    assert snapshot["arrangement"]["unique_plane_count"]==12
    assert snapshot["component_count"]==1
    assert snapshot["total_exact_volume"]=="15"
    assert snapshot["selected_fragment_count"]>0
