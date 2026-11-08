"""Global exact-rational topology assembly for per-triangle arrangements.

Global coordinate identity, edge subdivision, and independent per-source
coverage certification use exact Fraction arithmetic. This remains an
arrangement/topology primitive, not a solid classifier or Boolean shell builder.
"""
from __future__ import annotations
from dataclasses import dataclass
from fractions import Fraction
from typing import Iterable
from .errors import InvalidModelError
from .triangle_coverage_oracle import certify_triangle_partition
from .triangle_fragment_arrangement import RationalPlane, RationalPoint3, RationalTriangle3, RationalTriangleFragment, arrange_triangles_by_planes

@dataclass(frozen=True, slots=True)
class GlobalArrangementVertex:
    vertex_id: int
    point: RationalPoint3

@dataclass(frozen=True, slots=True)
class GlobalArrangementFace:
    face_id: int
    source_triangle_index: int
    side_signature: tuple[str, ...]
    vertex_ids: tuple[int, int, int]

@dataclass(frozen=True, slots=True)
class GlobalArrangementEdge:
    vertex_ids: tuple[int, int]
    incident_face_ids: tuple[int, ...]

@dataclass(frozen=True, slots=True)
class SourceCoverageReport:
    source_triangle_index: int
    source_area_squared_scaled: Fraction
    fragment_area_squared_scaled: Fraction
    area_conserved: bool
    fragment_count: int
    oracle_certified: bool
    outside_fragment_indices: tuple[int, ...]
    overlapping_fragment_pairs: tuple[tuple[int, int], ...]
    duplicate_fragment_pairs: tuple[tuple[int, int], ...]

@dataclass(frozen=True, slots=True)
class GlobalTriangleArrangement:
    vertices: tuple[GlobalArrangementVertex, ...]
    faces: tuple[GlobalArrangementFace, ...]
    edges: tuple[GlobalArrangementEdge, ...]
    adjacent_face_pairs: tuple[tuple[int, int], ...]
    boundary_edge_ids: tuple[tuple[int, int], ...]
    non_manifold_edges: tuple[tuple[int, int], ...]
    t_junctions: tuple[tuple[int, int, int], ...]
    coverage_reports: tuple[SourceCoverageReport, ...]
    fragments: tuple[RationalTriangleFragment, ...]

def _sub(a: RationalPoint3, b: RationalPoint3) -> RationalPoint3:
    return tuple(a[i] - b[i] for i in range(3))  # type: ignore[return-value]

def _cross(a: RationalPoint3, b: RationalPoint3) -> RationalPoint3:
    return (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])

def _dot(a: RationalPoint3, b: RationalPoint3) -> Fraction:
    return sum((a[i]*b[i] for i in range(3)), Fraction(0))

def _validate_source(triangle: object) -> None:
    if not isinstance(triangle, tuple) or len(triangle) != 3:
        raise InvalidModelError("each source triangle must contain three exact points")
    for point in triangle:
        if not isinstance(point, tuple) or len(point) != 3 or any(not isinstance(v, Fraction) for v in point):
            raise InvalidModelError("source vertices must use exact Fraction coordinates")
    if len(set(triangle)) != 3:
        raise InvalidModelError("source triangle vertices must be distinct")
    if _cross(_sub(triangle[1], triangle[0]), _sub(triangle[2], triangle[0])) == (0,0,0):
        raise InvalidModelError("source triangle must be non-degenerate")

def _check_bits(triangle: RationalTriangle3, limit: int) -> None:
    for point in triangle:
        for value in point:
            if abs(value.numerator).bit_length() > limit or value.denominator.bit_length() > limit:
                raise InvalidModelError("rational coordinate exceeded max_coordinate_bits")

def _area_vector(triangle: RationalTriangle3) -> RationalPoint3:
    return _cross(_sub(triangle[1], triangle[0]), _sub(triangle[2], triangle[0]))

def arrange_triangle_mesh_globally(
    triangles: Iterable[RationalTriangle3], planes: Iterable[RationalPlane], *,
    max_fragments: int = 16384, max_coordinate_bits: int = 4096,
    max_edges: int = 65536, max_topology_checks: int = 1_000_000,
    max_coverage_checks: int = 1_000_000,
) -> GlobalTriangleArrangement:
    """Arrange facets; independently certify exact coverage and edge incidence.

    Coverage certification requires containment, zero pairwise interior
    overlap, and exact source-area conservation. All work budgets fail closed.
    """
    for name, value in (("max_fragments",max_fragments),("max_coordinate_bits",max_coordinate_bits),
                        ("max_edges",max_edges),("max_topology_checks",max_topology_checks),
                        ("max_coverage_checks",max_coverage_checks)):
        if isinstance(value,bool) or not isinstance(value,int) or value < 1:
            raise InvalidModelError(f"{name} must be a positive integer")
    source_items, plane_items = tuple(triangles), tuple(planes)
    if not source_items:
        raise InvalidModelError("at least one source triangle is required")
    if len(source_items) > max_fragments:
        raise InvalidModelError("source triangle count exceeded max_fragments")
    if any(not isinstance(p,RationalPlane) for p in plane_items):
        raise InvalidModelError("planes must contain only RationalPlane values")
    if len({p.plane_index for p in plane_items}) != len(plane_items):
        raise InvalidModelError("plane indices must be unique")
    for tri in source_items:
        _validate_source(tri)
        _check_bits(tri,max_coordinate_bits)
    for plane in plane_items:
        _check_bits(plane.vertices,max_coordinate_bits)

    fragments: list[RationalTriangleFragment] = []
    coverage: list[SourceCoverageReport] = []
    coverage_used = 0
    for source_index, source in enumerate(source_items):
        remaining = max_fragments-len(fragments)
        if remaining < 1:
            raise InvalidModelError("global arrangement exceeded max_fragments")
        local = arrange_triangles_by_planes((source,),plane_items,max_fragments=remaining,
                                            max_coordinate_bits=max_coordinate_bits)
        normal = _area_vector(source)
        expected = _dot(normal,normal)
        actual = sum((_dot(_area_vector(f.vertices),normal) for f in local),Fraction(0))
        if actual != expected:
            raise InvalidModelError(f"global coverage area mismatch for source triangle {source_index}")
        oracle = certify_triangle_partition(source,tuple(f.vertices for f in local),
                    max_pairwise_checks=max_coverage_checks-coverage_used)
        coverage_used += oracle.pairwise_checks
        if not oracle.certified:
            raise InvalidModelError(f"independent exact coverage oracle rejected source triangle {source_index}")
        coverage.append(SourceCoverageReport(source_index,expected,actual,actual==expected,len(local),
                         oracle.certified,oracle.outside_fragment_indices,
                         oracle.overlapping_fragment_pairs,oracle.duplicate_fragment_pairs))
        fragments.extend(RationalTriangleFragment(source_index,f.side_signature,f.vertices) for f in local)
        if len(fragments)>max_fragments:
            raise InvalidModelError("global arrangement exceeded max_fragments")

    all_points=sorted({point for fragment in fragments for point in fragment.vertices})
    point_ids={point:index for index,point in enumerate(all_points)}
    vertices=tuple(GlobalArrangementVertex(index,point) for index,point in enumerate(all_points))
    faces=[]
    face_edges=[]
    raw_edges=set()
    for face_id,fragment in enumerate(fragments):
        ids=tuple(point_ids[point] for point in fragment.vertices)
        faces.append(GlobalArrangementFace(face_id,fragment.source_triangle_index,fragment.side_signature,ids))
        face_edges.append((face_id,ids))
        for first,second in ((ids[0],ids[1]),(ids[1],ids[2]),(ids[2],ids[0])):
            raw_edges.add((first,second) if first<second else (second,first))
    if len(vertices)*len(raw_edges)>max_topology_checks:
        raise InvalidModelError("global topology scan exceeded max_topology_checks")

    t_junctions=[]
    edge_faces={}
    for face_id,ids in face_edges:
        for start_id,end_id in ((ids[0],ids[1]),(ids[1],ids[2]),(ids[2],ids[0])):
            first_id,second_id=(start_id,end_id) if start_id<end_id else (end_id,start_id)
            first,second=vertices[first_id].point,vertices[second_id].point
            direction=_sub(second,first)
            length_squared=_dot(direction,direction)
            interior=[]
            for candidate in vertices:
                if candidate.vertex_id in (first_id,second_id): continue
                offset=_sub(candidate.point,first)
                if _cross(direction,offset)==(0,0,0):
                    projection=_dot(offset,direction)
                    if 0<projection<length_squared: interior.append((projection,candidate.vertex_id))
            if interior:
                t_junctions.extend((first_id,second_id,candidate_id) for _,candidate_id in interior)
            ordered=[first_id]+[candidate_id for _,candidate_id in sorted(interior)]+[second_id]
            for sub_start,sub_end in zip(ordered,ordered[1:]):
                edge=(sub_start,sub_end) if sub_start<sub_end else (sub_end,sub_start)
                edge_faces.setdefault(edge,set()).add(face_id)
                if len(edge_faces)>max_edges:
                    raise InvalidModelError("global arrangement exceeded max_edges")
    edges=tuple(GlobalArrangementEdge(edge,tuple(sorted(incident))) for edge,incident in sorted(edge_faces.items()))
    adjacent=sorted({(first,second) for edge in edges for i,first in enumerate(edge.incident_face_ids)
                     for second in edge.incident_face_ids[i+1:]})
    boundary=tuple(edge.vertex_ids for edge in edges if len(edge.incident_face_ids)==1)
    non_manifold=tuple(edge.vertex_ids for edge in edges if len(edge.incident_face_ids)>2)
    return GlobalTriangleArrangement(vertices,tuple(faces),edges,tuple(adjacent),boundary,non_manifold,
              tuple(sorted(set(t_junctions))),tuple(coverage),tuple(fragments))
