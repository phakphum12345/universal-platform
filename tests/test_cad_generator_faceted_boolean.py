from hashlib import sha256

import pytest

from universal_platform.engineering import (
    BRepBooleanOperation,
    CADGeneratorService,
    BoxSolid,
    ExtrudedProfileSolid,
    Vec2,
    SQLiteFeatureArtifactCache,
    SQLiteFeatureHistoryStore,
    TriangleMesh,
    tessellate_box,
    tessellate_extruded_profile,
)
from universal_platform.engineering.geometry import Vec3
from universal_platform.engineering.errors import InvalidModelError


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


def test_cad_generator_executes_coplanar_overlap_union_end_to_end(tmp_path):
    service=CADGeneratorService(
        SQLiteFeatureHistoryStore(tmp_path/"source.sqlite3"),
        SQLiteFeatureArtifactCache(tmp_path/"artifacts.sqlite3"),
    )
    meshes=(_box("a",2.0),_box("b",2.0,(1.0,0.0,0.0)))
    result=service.execute_faceted_boolean(meshes,BRepBooleanOperation.UNION)
    snapshot=result.to_dict()
    assert snapshot["component_count"]==1
    assert snapshot["total_exact_volume"]=="12"
    assert snapshot["arrangement"]["coplanar_pair_checks"]>0


def _concave_l_prism():
    profile = (
        Vec2(0.0, 0.0), Vec2(4.0, 0.0), Vec2(4.0, 2.0),
        Vec2(2.0, 2.0), Vec2(2.0, 4.0), Vec2(0.0, 4.0),
    )
    return tessellate_extruded_profile(
        ExtrudedProfileSolid("l-prism", "world", profile, 4.0, "m")
    )


def test_cad_generator_concave_prism_boolean_is_exact_or_fails_closed(tmp_path):
    service = CADGeneratorService(
        SQLiteFeatureHistoryStore(tmp_path / "source.sqlite3"),
        SQLiteFeatureArtifactCache(tmp_path / "artifacts.sqlite3"),
    )
    meshes = (_concave_l_prism(), _box("contained-box", 1.0, (0.5, 0.5, 1.5)))
    expected_volumes = {
        BRepBooleanOperation.UNION: "48",
        BRepBooleanOperation.INTERSECTION: "1",
        BRepBooleanOperation.DIFFERENCE: "47",
        BRepBooleanOperation.SYMMETRIC_DIFFERENCE: "47",
    }
    for operation, expected_volume in expected_volumes.items():
        try:
            result = service.execute_faceted_boolean(meshes, operation)
        except InvalidModelError as exc:
            assert "not losslessly representable as binary64" in str(exc)
        else:
            assert result.to_dict()["total_exact_volume"] == expected_volume
