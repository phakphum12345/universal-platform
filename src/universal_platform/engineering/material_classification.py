"""Fail-closed exact material classification against closed triangle meshes."""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from fractions import Fraction
from .errors import InvalidModelError
from .geometry import Vec3
from .mesh import TriangleMesh, validate_triangle_mesh
from .mesh_intersection import analyze_mesh_intersections

Point3 = tuple[Fraction, Fraction, Fraction]
_DIRECTIONS: tuple[Point3, ...] = (
    (Fraction(1),Fraction(1,17),Fraction(1,31)),
    (Fraction(1,19),Fraction(1),Fraction(1,37)),
    (Fraction(1,41),Fraction(1,43),Fraction(1)),
    (Fraction(1,23),Fraction(2,29),Fraction(1)),
    (Fraction(2,31),Fraction(1),Fraction(3,47)),
    (Fraction(1),Fraction(3,53),Fraction(2,59)),
    (Fraction(3,61),Fraction(2,67),Fraction(1)),
)
RAY_DIRECTION_COUNT = len(_DIRECTIONS)

class MaterialClassification(str, Enum):
    INSIDE="INSIDE"
    OUTSIDE="OUTSIDE"
    BOUNDARY="BOUNDARY"
    UNKNOWN="UNKNOWN"

@dataclass(frozen=True, slots=True)
class MaterialClassificationResult:
    classification: MaterialClassification
    ray_directions_tested: int
    valid_ray_count: int
    crossing_counts: tuple[int,...]
    reason: str | None = None

def _q(value: float) -> Fraction:
    return Fraction.from_float(float(value))

def _sub(a: Point3,b: Point3)->Point3:
    return tuple(a[i]-b[i] for i in range(3)) # type: ignore[return-value]

def _cross(a: Point3,b: Point3)->Point3:
    return (a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])

def _dot(a: Point3,b: Point3)->Fraction:
    return sum((a[i]*b[i] for i in range(3)),Fraction(0))

def _point_on_triangle(point: Point3, triangle: tuple[Point3,Point3,Point3])->bool:
    a,b,c=triangle
    normal=_cross(_sub(b,a),_sub(c,a))
    if _dot(normal,_sub(point,a))!=0: return False
    drop=max(range(3),key=lambda axis:abs(normal[axis]))
    axes=tuple(axis for axis in range(3) if axis!=drop)
    def orient(p:Point3,q:Point3,r:Point3)->Fraction:
        return ((q[axes[0]]-p[axes[0]])*(r[axes[1]]-p[axes[1]])
               -(q[axes[1]]-p[axes[1]])*(r[axes[0]]-p[axes[0]]))
    area=orient(a,b,c)
    signs=(orient(a,b,point),orient(b,c,point),orient(c,a,point))
    return all(v>=0 for v in signs) if area>0 else all(v<=0 for v in signs)

def _ray_crossings(origin:Point3,direction:Point3,
                   triangles:tuple[tuple[Point3,Point3,Point3],...])->tuple[int,bool]:
    crossings=0
    for a,b,c in triangles:
        edge1,edge2=_sub(b,a),_sub(c,a)
        normal=_cross(edge1,edge2)
        determinant=_dot(edge1,_cross(direction,edge2))
        if determinant==0:
            if _dot(normal,direction)==0 and _dot(normal,_sub(origin,a))==0:
                return crossings,True
            continue
        offset=_sub(origin,a)
        u=_dot(offset,_cross(direction,edge2))/determinant
        qvec=_cross(offset,edge1)
        v=_dot(direction,qvec)/determinant
        distance=_dot(edge2,qvec)/determinant
        if distance>0 and u>=0 and v>=0 and u+v<=1:
            if u==0 or v==0 or u+v==1: return crossings,True
            crossings+=1
    return crossings,False

class ExactMeshMaterialClassifier:
    """Prepared classifier; validates a mesh once and reuses exact triangles."""
    def __init__(self,mesh:TriangleMesh,*,max_ray_checks:int=1_000_000,
                 max_aggregate_rational_bits:int=64_000_000)->None:
        if not isinstance(mesh,TriangleMesh):
            raise InvalidModelError("classifier requires a TriangleMesh")
        if isinstance(max_ray_checks,bool) or not isinstance(max_ray_checks,int) or max_ray_checks<1:
            raise InvalidModelError("max_ray_checks must be a positive integer")
        if (isinstance(max_aggregate_rational_bits,bool)
                or not isinstance(max_aggregate_rational_bits,int)
                or not 1<=max_aggregate_rational_bits<=64_000_000):
            raise InvalidModelError("max_aggregate_rational_bits must be within the supported hard limit")
        self.mesh=mesh
        self.max_ray_checks=max_ray_checks
        self.reason=None
        # Do not allocate exact triangle tuples until the ray-work preflight
        # has established that this mesh is eligible for classification.
        if len(mesh.triangles)*len(_DIRECTIONS)>max_ray_checks:
            self.triangles=()
            self.reason="ray-triangle resource budget exceeded"
            return
        triangles=[]
        aggregate_bits=0
        for face in mesh.triangles:
            exact=[]
            for index in face:
                vertex=mesh.vertices[index]
                point=(_q(vertex.x),_q(vertex.y),_q(vertex.z))
                aggregate_bits+=sum(
                    abs(value.numerator).bit_length()+value.denominator.bit_length()
                    for value in point
                )
                if aggregate_bits>max_aggregate_rational_bits:
                    self.triangles=()
                    self.reason="aggregate rational bit budget exceeded"
                    return
                exact.append(point)
            triangles.append(tuple(exact))
        self.triangles=tuple(triangles)
        topology=validate_triangle_mesh(mesh)
        if not (topology.valid and topology.watertight and topology.consistently_oriented):
            self.reason="mesh is not a valid oriented watertight shell"
        elif analyze_mesh_intersections(mesh).status!="NO_INTERSECTIONS_FOUND":
            self.reason="mesh self-intersection status is not NO_INTERSECTIONS_FOUND"

    def classify_rational(self,point:Point3)->MaterialClassificationResult:
        if (not isinstance(point,tuple) or len(point)!=3
                or any(not isinstance(value,Fraction) for value in point)):
            raise InvalidModelError("classification point must be a 3D tuple of exact Fractions")
        if self.reason:
            return MaterialClassificationResult(MaterialClassification.UNKNOWN,0,0,(),self.reason)
        if any(_point_on_triangle(point,triangle) for triangle in self.triangles):
            return MaterialClassificationResult(MaterialClassification.BOUNDARY,0,0,())
        counts=[]
        for direction in _DIRECTIONS:
            count,ambiguous=_ray_crossings(point,direction,self.triangles)
            if not ambiguous: counts.append(count)
        if len(counts)<2 or len({count%2 for count in counts})!=1:
            return MaterialClassificationResult(MaterialClassification.UNKNOWN,len(_DIRECTIONS),
                len(counts),tuple(counts),"insufficient or inconsistent non-degenerate exact ray witnesses")
        result=MaterialClassification.INSIDE if counts[0]%2 else MaterialClassification.OUTSIDE
        return MaterialClassificationResult(result,len(_DIRECTIONS),len(counts),tuple(counts))

def classify_point_against_mesh(point:Vec3,mesh:TriangleMesh,*,
                                max_ray_checks:int=1_000_000)->MaterialClassificationResult:
    """Classify binary64 point coordinates as exact represented rationals."""
    if not isinstance(point,Vec3):
        raise InvalidModelError("classification requires a Vec3 point")
    classifier=ExactMeshMaterialClassifier(mesh,max_ray_checks=max_ray_checks)
    return classifier.classify_rational((_q(point.x),_q(point.y),_q(point.z)))
