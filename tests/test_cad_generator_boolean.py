from fractions import Fraction
from hashlib import sha256

from universal_platform.engineering import (
    BRepBooleanOperation,
    CADGeneratorService,
    RationalTriangleFragment,
    SQLiteFeatureArtifactCache,
    SQLiteFeatureHistoryStore,
    TriangleMesh,
    BoxSolid,
    tessellate_box,
)
from universal_platform.engineering.geometry import Vec3


def _box(solid_id, size, offset=0.0):
    source=tessellate_box(BoxSolid(solid_id,"world",Vec3(size,size,size)))
    vertices=tuple(Vec3(v.x+offset,v.y+offset,v.z+offset) for v in source.vertices)
    digest=sha256(f"{solid_id}:{size}:{offset}".encode()).hexdigest()
    return TriangleMesh(solid_id,"world","m","BOX",digest,vertices,source.triangles)


def _fragments(mesh):
    return tuple(
        RationalTriangleFragment(index,(),tuple(tuple(Fraction.from_float(value) for value in
            (mesh.vertices[i].x,mesh.vertices[i].y,mesh.vertices[i].z)) for i in face))
        for index,face in enumerate(mesh.triangles)
    )


def test_cad_generator_service_executes_prearranged_boolean_pipeline(tmp_path):
    service=CADGeneratorService(
        SQLiteFeatureHistoryStore(tmp_path/"source.sqlite3"),
        SQLiteFeatureArtifactCache(tmp_path/"artifacts.sqlite3"),
    )
    meshes=(_box("outer",4.0),_box("inner",2.0,1.0))
    result=service.execute_prearranged_boolean(
        meshes,tuple(_fragments(mesh) for mesh in meshes),
        BRepBooleanOperation.DIFFERENCE,
    )
    snapshot=result.to_dict()
    assert snapshot["operation"]=="DIFFERENCE"
    assert snapshot["component_count"]==1
    assert snapshot["total_exact_volume"]=="56"
    assert snapshot["components"][0]["cavity_face_counts"]==[12]
    assert "automatic face splitting" in snapshot["limitations"][1]
