from fractions import Fraction
from hashlib import sha256

from universal_platform.engineering.brep_boolean import BRepBooleanOperation
from universal_platform.engineering.boolean_boundary_selection import (
    BooleanBoundarySelection, select_boolean_boundary_fragments,
)
from universal_platform.engineering.boolean_shell_assembly import assemble_boolean_shells
from universal_platform.engineering.geometry import Vec3
from universal_platform.engineering.mesh import TriangleMesh, tessellate_box
from universal_platform.engineering.primitive_geometry import BoxSolid
from universal_platform.engineering.triangle_fragment_arrangement import RationalTriangleFragment


def _box(solid_id, size, offset=0.0):
    source=tessellate_box(BoxSolid(solid_id,"world",Vec3(size,size,size)))
    vertices=tuple(Vec3(v.x+offset,v.y+offset,v.z+offset) for v in source.vertices)
    digest=sha256(f"{solid_id}:{size}:{offset}".encode()).hexdigest()
    return TriangleMesh(solid_id,"world","m","BOX",digest,vertices,source.triangles)


def _fragments(mesh):
    result=[]
    for index,face in enumerate(mesh.triangles):
        points=tuple(tuple(Fraction.from_float(value) for value in
            (mesh.vertices[i].x,mesh.vertices[i].y,mesh.vertices[i].z)) for i in face)
        result.append(RationalTriangleFragment(index,(),points))
    return tuple(result)


def _difference_selection():
    meshes=(_box("outer",4.0),_box("inner",2.0,1.0))
    fragments=tuple(_fragments(mesh) for mesh in meshes)
    selection=select_boolean_boundary_fragments(meshes,fragments,BRepBooleanOperation.DIFFERENCE)
    return meshes,selection


def test_shell_assembly_builds_valid_outer_and_cavity_component():
    meshes,selection=_difference_selection()
    result=assemble_boolean_shells(selection,meshes)
    assert len(result.components)==1
    component=result.components[0]
    assert len(component.solid.cavity_shells)==1
    assert component.exact_net_volume==Fraction(56)
    assert component.outer_face_count==12
    assert component.cavity_face_counts==(12,)
    assert result.connected_shell_count==2
    assert result.total_exact_volume==Fraction(56)


def test_shell_assembly_rejects_resource_exhaustion():
    meshes,selection=_difference_selection()
    try:
        assemble_boolean_shells(selection,meshes,max_faces=1)
    except Exception as exc:
        assert "max_faces" in str(exc)
    else:
        raise AssertionError("face budget must fail closed")


def test_shell_assembly_returns_empty_for_empty_boolean_result():
    meshes=(_box("outer",4.0),_box("inner",2.0,1.0))
    empty=BooleanBoundarySelection(BRepBooleanOperation.INTERSECTION,(),0,0,0)
    result=assemble_boolean_shells(empty,meshes)
    assert result.components==()
    assert result.total_exact_volume==0
