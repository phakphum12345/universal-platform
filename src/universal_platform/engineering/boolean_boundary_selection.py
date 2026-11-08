"""Boolean boundary selection using exact two-sided material witnesses."""
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
    source_solid_index:int
    source_triangle_index:int
    vertices:RationalTriangle3
    reversed_for_result:bool
    other_solid_membership:tuple[bool,...]

@dataclass(frozen=True, slots=True)
class BooleanBoundarySelection:
    operation:BRepBooleanOperation
    selected_fragments:tuple[SelectedBoundaryFragment,...]
    discarded_fragment_count:int
    classification_witness_count:int
    coverage_check_count:int

def _q(value:float)->Fraction:
    return Fraction.from_float(float(value))
def _mesh_triangle(mesh:TriangleMesh,face_index:int)->RationalTriangle3:
    return tuple(tuple(_q(value) for value in (mesh.vertices[i].x,mesh.vertices[i].y,mesh.vertices[i].z))
                 for i in mesh.triangles[face_index]) # type: ignore[return-value]
def _sub(a:RationalPoint3,b:RationalPoint3)->RationalPoint3:
    return tuple(a[i]-b[i] for i in range(3)) # type: ignore[return-value]
def _cross(a:RationalPoint3,b:RationalPoint3)->RationalPoint3:
    return (a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])
def _dot(a:RationalPoint3,b:RationalPoint3)->Fraction:
    return sum((a[i]*b[i] for i in range(3)),Fraction(0))
def _inside_source_face(point:RationalPoint3,source:RationalTriangle3)->bool:
    a,b,c=source
    ab,ac,ap=_sub(b,a),_sub(c,a),_sub(point,a)
    if _dot(_cross(ab,ac),ap)!=0:return False
    d00,d01,d11=_dot(ab,ab),_dot(ab,ac),_dot(ac,ac)
    d20,d21=_dot(ap,ab),_dot(ap,ac)
    denominator=d00*d11-d01*d01
    if denominator==0:return False
    u=(d11*d20-d01*d21)/denominator
    v=(d00*d21-d01*d20)/denominator
    return u>=0 and v>=0 and u+v<=1
def _witnesses(triangle:RationalTriangle3)->tuple[RationalPoint3,...]:
    a,b,c=triangle
    return (tuple((a[i]+b[i]+c[i])/3 for i in range(3)),
            tuple((2*a[i]+b[i]+c[i])/4 for i in range(3)),
            tuple((a[i]+2*b[i]+c[i])/4 for i in range(3)),
            tuple((a[i]+b[i]+2*c[i])/4 for i in range(3))) # type: ignore[return-value]
def _operation_value(values:tuple[bool,...],operation:BRepBooleanOperation)->bool:
    if operation is BRepBooleanOperation.UNION:return any(values)
    if operation is BRepBooleanOperation.INTERSECTION:return all(values)
    if operation is BRepBooleanOperation.DIFFERENCE:return values[0] and not any(values[1:])
    return sum(values)%2==1
def _offset_witness(witness:RationalPoint3,face_normal:RationalPoint3,
                    all_planes:tuple[tuple[RationalPoint3,RationalPoint3],...]
                    )->tuple[RationalPoint3,RationalPoint3]:
    nearest=None
    for normal,plane_point in all_planes:
        signed=_dot(normal,_sub(witness,plane_point))
        if signed==0:
            if _cross(normal,face_normal)!=(0,0,0):
                raise InvalidModelError("fragment witness lies on a non-coplanar arrangement plane")
            continue
        rate=_dot(normal,face_normal)
        if rate!=0:
            distance=abs(signed/rate)
            if nearest is None or distance<nearest:nearest=distance
    epsilon=nearest/2 if nearest is not None else Fraction(1)
    minus=tuple(witness[i]-face_normal[i]*epsilon for i in range(3))
    plus=tuple(witness[i]+face_normal[i]*epsilon for i in range(3))
    return minus,plus # type: ignore[return-value]

def select_boolean_boundary_fragments(
    meshes:tuple[TriangleMesh,...],fragments_by_solid:tuple[tuple[RationalTriangleFragment,...],...],
    operation:BRepBooleanOperation,*,max_coverage_checks:int=1_000_000,
    max_classification_checks:int=250_000,max_ray_checks_per_mesh:int=1_000_000,
)->BooleanBoundarySelection:
    """Select boundaries by exact Boolean membership on both sides of each face."""
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
    if any(not isinstance(mesh,TriangleMesh) for mesh in meshes):
        raise InvalidModelError("Boolean inputs must be TriangleMesh values")
    if len({(mesh.frame_id,mesh.length_unit) for mesh in meshes})!=1:
        raise InvalidModelError("Boolean inputs must share frame and length unit")
    total_fragments=sum(len(items) for items in fragments_by_solid)
    required_classifications=total_fragments*len(meshes)*4*2
    if required_classifications>max_classification_checks:
        raise InvalidModelError("Boolean classification exceeded max_classification_checks")
    classifiers=tuple(ExactMeshMaterialClassifier(mesh,max_ray_checks=max_ray_checks_per_mesh)
                      for mesh in meshes)
    for classifier in classifiers:
        if classifier.reason:raise InvalidModelError("Boolean material classifier unavailable: "+classifier.reason)
    all_planes=[]
    for mesh in meshes:
        for index in range(len(mesh.triangles)):
            triangle=_mesh_triangle(mesh,index)
            all_planes.append((_cross(_sub(triangle[1],triangle[0]),_sub(triangle[2],triangle[0])),triangle[0]))
    plane_tuple=tuple(all_planes)
    coverage_used=0
    for solid_index,(mesh,fragments) in enumerate(zip(meshes,fragments_by_solid)):
        if any(not isinstance(fragment,RationalTriangleFragment) for fragment in fragments):
            raise InvalidModelError("all fragments must be RationalTriangleFragment values")
        by_source={}
        for fragment in fragments:
            source_index=fragment.source_triangle_index
            if source_index>=len(mesh.triangles):raise InvalidModelError("fragment references an out-of-range source triangle")
            source=_mesh_triangle(mesh,source_index)
            normal=_cross(_sub(source[1],source[0]),_sub(source[2],source[0]))
            fragment_normal=_cross(_sub(fragment.vertices[1],fragment.vertices[0]),_sub(fragment.vertices[2],fragment.vertices[0]))
            if _dot(normal,fragment_normal)<=0:raise InvalidModelError("fragment winding must preserve source outward orientation")
            if any(not _inside_source_face(point,source) for point in fragment.vertices):
                raise InvalidModelError("fragment vertex lies outside its source triangle")
            by_source.setdefault(source_index,[]).append(fragment.vertices)
        if set(by_source)!=set(range(len(mesh.triangles))):
            raise InvalidModelError("fragments must cover every source mesh triangle")
        for source_index in range(len(mesh.triangles)):
            oracle=certify_triangle_partition(_mesh_triangle(mesh,source_index),tuple(by_source[source_index]),
                max_pairwise_checks=max_coverage_checks-coverage_used)
            coverage_used+=oracle.pairwise_checks
            if not oracle.certified:raise InvalidModelError(f"fragment coverage failed for solid {solid_index}, face {source_index}")
    selected=[];discarded=0
    for solid_index,fragments in enumerate(fragments_by_solid):
        for fragment in fragments:
            face_normal=_cross(_sub(fragment.vertices[1],fragment.vertices[0]),_sub(fragment.vertices[2],fragment.vertices[0]))
            witness_pairs=[]
            for witness in _witnesses(fragment.vertices):
                minus_point,plus_point=_offset_witness(witness,face_normal,plane_tuple)
                minus_states=tuple(classifier.classify_rational(minus_point).classification for classifier in classifiers)
                plus_states=tuple(classifier.classify_rational(plus_point).classification for classifier in classifiers)
                if any(state not in (MaterialClassification.INSIDE,MaterialClassification.OUTSIDE)
                       for state in (*minus_states,*plus_states)):
                    raise InvalidModelError("Boolean side witness classification is BOUNDARY or UNKNOWN")
                witness_pairs.append((tuple(s is MaterialClassification.INSIDE for s in minus_states),
                                      tuple(s is MaterialClassification.INSIDE for s in plus_states)))
            if len(set(witness_pairs))!=1:
                raise InvalidModelError("Boolean fragment side witnesses disagree; arrangement may be incomplete")
            minus_membership,plus_membership=witness_pairs[0]
            minus_result=_operation_value(minus_membership,operation)
            plus_result=_operation_value(plus_membership,operation)
            if minus_result==plus_result:
                discarded+=1;continue
            reverse=plus_result and not minus_result
            vertices=fragment.vertices
            if reverse:vertices=(vertices[0],vertices[2],vertices[1])
            other=tuple(value for index,value in enumerate(minus_membership) if index!=solid_index)
            selected.append(SelectedBoundaryFragment(solid_index,fragment.source_triangle_index,vertices,reverse,other))
    # Deduplicate coincident patches only when their final orientations agree.
    by_geometry={};deduplicated=[]
    for item in selected:
        geometry=tuple(sorted(item.vertices))
        oriented=min((item.vertices[0],item.vertices[1],item.vertices[2]),
                     (item.vertices[1],item.vertices[2],item.vertices[0]),
                     (item.vertices[2],item.vertices[0],item.vertices[1]))
        previous=by_geometry.get(geometry)
        if previous is None:
            by_geometry[geometry]=(oriented,item);deduplicated.append(item)
        elif previous[0]!=oriented:
            raise InvalidModelError("coincident Boolean boundary fragments have conflicting orientations")
        elif item.source_solid_index<previous[1].source_solid_index:
            deduplicated.remove(previous[1]);by_geometry[geometry]=(oriented,item);deduplicated.append(item)
        else:discarded+=1
    return BooleanBoundarySelection(operation,tuple(deduplicated),discarded,required_classifications,coverage_used)
