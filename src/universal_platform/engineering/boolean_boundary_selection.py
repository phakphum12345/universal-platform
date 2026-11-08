"""Boolean boundary selection from complete, exactly certified source-face partitions.

This module selects already-arranged fragments. It does not compute
inter-solid intersections or split crossing faces; callers must supply a
complete per-source-face partition, which is independently certified here.
"""
from __future__ import annotations
from dataclasses import dataclass
from fractions import Fraction

from .brep_boolean import BRepBooleanOperation
from .errors import InvalidModelError
from .material_classification import ExactMeshMaterialClassifier, MaterialClassification
from .mesh import TriangleMesh
from .triangle_coverage_oracle import certify_triangle_partition
from .triangle_fragment_arrangement import RationalPoint3, RationalTriangle3, RationalTriangleFragment

@dataclass(frozen=True, slots=True)
class SelectedBoundaryFragment:
    source_solid_index: int
    source_triangle_index: int
    vertices: RationalTriangle3
    reversed_for_result: bool
    other_solid_membership: tuple[bool, ...]

@dataclass(frozen=True, slots=True)
class BooleanBoundarySelection:
    operation: BRepBooleanOperation
    selected_fragments: tuple[SelectedBoundaryFragment, ...]
    discarded_fragment_count: int
    classification_witness_count: int
    coverage_check_count: int


def _q(value: float) -> Fraction:
    return Fraction.from_float(float(value))

def _mesh_triangle(mesh: TriangleMesh, face_index: int) -> RationalTriangle3:
    return tuple(tuple(_q(value) for value in (
        mesh.vertices[index].x,mesh.vertices[index].y,mesh.vertices[index].z))
        for index in mesh.triangles[face_index]) # type: ignore[return-value]

def _sub(a:RationalPoint3,b:RationalPoint3)->RationalPoint3:
    return tuple(a[i]-b[i] for i in range(3)) # type: ignore[return-value]

def _cross(a:RationalPoint3,b:RationalPoint3)->RationalPoint3:
    return (a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])

def _dot(a:RationalPoint3,b:RationalPoint3)->Fraction:
    return sum((a[i]*b[i] for i in range(3)),Fraction(0))

def _signed_volume(mesh:TriangleMesh)->Fraction:
    total=Fraction(0)
    for index in range(len(mesh.triangles)):
        a,b,c=_mesh_triangle(mesh,index)
        total+=_dot(a,_cross(b,c))
    return total/6

def _inside_source_face(point:RationalPoint3,source:RationalTriangle3)->bool:
    a,b,c=source
    ab,ac,ap=_sub(b,a),_sub(c,a),_sub(point,a)
    normal=_cross(ab,ac)
    if _dot(normal,ap)!=0: return False
    d00,d01,d11=_dot(ab,ab),_dot(ab,ac),_dot(ac,ac)
    d20,d21=_dot(ap,ab),_dot(ap,ac)
    denominator=d00*d11-d01*d01
    if denominator==0: return False
    u=(d11*d20-d01*d21)/denominator
    v=(d00*d21-d01*d20)/denominator
    return u>=0 and v>=0 and u+v<=1

def _witnesses(triangle:RationalTriangle3)->tuple[RationalPoint3,...]:
    a,b,c=triangle
    return (
        tuple((a[i]+b[i]+c[i])/3 for i in range(3)),
        tuple((2*a[i]+b[i]+c[i])/4 for i in range(3)),
        tuple((a[i]+2*b[i]+c[i])/4 for i in range(3)),
        tuple((a[i]+b[i]+2*c[i])/4 for i in range(3)),
    ) # type: ignore[return-value]

def _operation_value(values:tuple[bool,...],operation:BRepBooleanOperation)->bool:
    if operation is BRepBooleanOperation.UNION: return any(values)
    if operation is BRepBooleanOperation.INTERSECTION: return all(values)
    if operation is BRepBooleanOperation.DIFFERENCE: return values[0] and not any(values[1:])
    return sum(values)%2==1


def select_boolean_boundary_fragments(
    meshes:tuple[TriangleMesh,...],
    fragments_by_solid:tuple[tuple[RationalTriangleFragment,...],...],
    operation:BRepBooleanOperation,
    *,
    max_coverage_checks:int=1_000_000,
    max_classification_checks:int=250_000,
    max_ray_checks_per_mesh:int=1_000_000,
)->BooleanBoundarySelection:
    """Select oriented result boundaries using exact witnesses and set semantics.

    Every source triangle must be partitioned exactly by its supplied fragments.
    For each fragment, four strict-interior witnesses must agree against every
    other solid. Any BOUNDARY/UNKNOWN or disagreement aborts the entire call.
    """
    if not isinstance(meshes,tuple) or not 2<=len(meshes)<=16:
        raise InvalidModelError("Boolean boundary selection requires 2..16 immutable input meshes")
    if not isinstance(fragments_by_solid,tuple) or len(fragments_by_solid)!=len(meshes):
        raise InvalidModelError("fragments_by_solid must align with input meshes")
    if not isinstance(operation,BRepBooleanOperation):
        raise InvalidModelError("operation must be a BRepBooleanOperation")
    for name,value in (("max_coverage_checks",max_coverage_checks),
                       ("max_classification_checks",max_classification_checks),
                       ("max_ray_checks_per_mesh",max_ray_checks_per_mesh)):
        if isinstance(value,bool) or not isinstance(value,int) or value<1:
            raise InvalidModelError(f"{name} must be a positive integer")
    if len({(mesh.frame_id,mesh.length_unit) for mesh in meshes})!=1:
        raise InvalidModelError("Boolean inputs must share frame and length unit")
    if any(not isinstance(mesh,TriangleMesh) for mesh in meshes):
        raise InvalidModelError("Boolean inputs must be TriangleMesh values")
    total_fragments=sum(len(items) for items in fragments_by_solid)
    required_classifications=total_fragments*(len(meshes)-1)*4
    if required_classifications>max_classification_checks:
        raise InvalidModelError("Boolean classification exceeded max_classification_checks")

    classifiers=tuple(ExactMeshMaterialClassifier(mesh,max_ray_checks=max_ray_checks_per_mesh)
                      for mesh in meshes)
    for classifier in classifiers:
        if classifier.reason:
            raise InvalidModelError("Boolean material classifier unavailable: "+classifier.reason)
    for mesh in meshes:
        if _signed_volume(mesh)<=0:
            raise InvalidModelError("Boolean input mesh must have positive outward signed volume")

    coverage_used=0
    for solid_index,(mesh,fragments) in enumerate(zip(meshes,fragments_by_solid)):
        if any(not isinstance(fragment,RationalTriangleFragment) for fragment in fragments):
            raise InvalidModelError("all fragments must be RationalTriangleFragment values")
        by_source:dict[int,list[RationalTriangle3]]={}
        for fragment in fragments:
            source_index=fragment.source_triangle_index
            if source_index>=len(mesh.triangles):
                raise InvalidModelError("fragment references an out-of-range source triangle")
            source=_mesh_triangle(mesh,source_index)
            normal=_cross(_sub(source[1],source[0]),_sub(source[2],source[0]))
            fragment_normal=_cross(_sub(fragment.vertices[1],fragment.vertices[0]),
                                   _sub(fragment.vertices[2],fragment.vertices[0]))
            if _dot(normal,fragment_normal)<=0:
                raise InvalidModelError("fragment winding must preserve source outward orientation")
            if any(not _inside_source_face(point,source) for point in fragment.vertices):
                raise InvalidModelError("fragment vertex lies outside its source triangle")
            by_source.setdefault(source_index,[]).append(fragment.vertices)
        if set(by_source)!=set(range(len(mesh.triangles))):
            raise InvalidModelError("fragments must cover every source mesh triangle")
        for source_index in range(len(mesh.triangles)):
            remaining=max_coverage_checks-coverage_used
            oracle=certify_triangle_partition(_mesh_triangle(mesh,source_index),
                         tuple(by_source[source_index]),max_pairwise_checks=remaining)
            coverage_used+=oracle.pairwise_checks
            if not oracle.certified:
                raise InvalidModelError(f"fragment coverage failed for solid {solid_index}, face {source_index}")

    selected=[]
    discarded=0
    for solid_index,fragments in enumerate(fragments_by_solid):
        for fragment in fragments:
            memberships=[]
            for other_index,classifier in enumerate(classifiers):
                if other_index==solid_index: continue
                witness_states=tuple(classifier.classify_rational(point).classification
                                     for point in _witnesses(fragment.vertices))
                if any(state in (MaterialClassification.BOUNDARY,MaterialClassification.UNKNOWN)
                       for state in witness_states):
                    raise InvalidModelError("Boolean fragment classification is BOUNDARY or UNKNOWN")
                if len(set(witness_states))!=1:
                    raise InvalidModelError("Boolean fragment witnesses disagree; arrangement may be incomplete")
                memberships.append(witness_states[0] is MaterialClassification.INSIDE)
            outside_values=tuple(memberships[:solid_index])+(False,)+tuple(memberships[solid_index:])
            inside_values=tuple(memberships[:solid_index])+(True,)+tuple(memberships[solid_index:])
            outside_result=_operation_value(outside_values,operation)
            inside_result=_operation_value(inside_values,operation)
            if outside_result==inside_result:
                discarded+=1
                continue
            reverse=outside_result and not inside_result
            vertices=fragment.vertices
            if reverse:
                vertices=(vertices[0],vertices[2],vertices[1])
            selected.append(SelectedBoundaryFragment(
                solid_index,fragment.source_triangle_index,vertices,reverse,tuple(memberships)))
    return BooleanBoundarySelection(operation,tuple(selected),discarded,
                                    required_classifications,coverage_used)
