"""Global exact-rational arrangement with conforming facet edge subdivision."""
from __future__ import annotations
from dataclasses import dataclass
from fractions import Fraction
from typing import Iterable
from .errors import InvalidModelError
from .boolean_resource_budget import BooleanResourceLedger
from .triangle_coverage_oracle import certify_triangle_partition
from .triangle_fragment_arrangement import RationalPlane, RationalPoint3, RationalTriangle3, RationalTriangleFragment, arrange_triangles_by_planes

@dataclass(frozen=True, slots=True)
class GlobalArrangementVertex:
    vertex_id:int
    point:RationalPoint3

@dataclass(frozen=True, slots=True)
class GlobalArrangementFace:
    face_id:int
    source_triangle_index:int
    side_signature:tuple[str,...]
    vertex_ids:tuple[int,int,int]

@dataclass(frozen=True, slots=True)
class GlobalArrangementEdge:
    vertex_ids:tuple[int,int]
    incident_face_ids:tuple[int,...]

@dataclass(frozen=True, slots=True)
class SourceCoverageReport:
    source_triangle_index:int
    source_area_squared_scaled:Fraction
    fragment_area_squared_scaled:Fraction
    area_conserved:bool
    fragment_count:int
    oracle_certified:bool
    outside_fragment_indices:tuple[int,...]
    overlapping_fragment_pairs:tuple[tuple[int,int],...]
    duplicate_fragment_pairs:tuple[tuple[int,int],...]

@dataclass(frozen=True, slots=True)
class GlobalTriangleArrangement:
    vertices:tuple[GlobalArrangementVertex,...]
    faces:tuple[GlobalArrangementFace,...]
    edges:tuple[GlobalArrangementEdge,...]
    adjacent_face_pairs:tuple[tuple[int,int],...]
    boundary_edge_ids:tuple[tuple[int,int],...]
    non_manifold_edges:tuple[tuple[int,int],...]
    t_junctions:tuple[tuple[int,int,int],...]
    coverage_reports:tuple[SourceCoverageReport,...]
    fragments:tuple[RationalTriangleFragment,...]

def _sub(a:RationalPoint3,b:RationalPoint3)->RationalPoint3:
    return tuple(a[i]-b[i] for i in range(3)) # type: ignore[return-value]

def _cross(a:RationalPoint3,b:RationalPoint3)->RationalPoint3:
    return (a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])

def _dot(a:RationalPoint3,b:RationalPoint3)->Fraction:
    return sum((a[i]*b[i] for i in range(3)),Fraction(0))

def _validate_source(triangle:object)->None:
    if not isinstance(triangle,tuple) or len(triangle)!=3:
        raise InvalidModelError("each source triangle must contain three exact points")
    for point in triangle:
        if not isinstance(point,tuple) or len(point)!=3 or any(not isinstance(v,Fraction) for v in point):
            raise InvalidModelError("source vertices must use exact Fraction coordinates")
    if len(set(triangle))!=3: raise InvalidModelError("source triangle vertices must be distinct")
    if _cross(_sub(triangle[1],triangle[0]),_sub(triangle[2],triangle[0]))==(0,0,0):
        raise InvalidModelError("source triangle must be non-degenerate")

def _check_bits(triangle:RationalTriangle3,limit:int)->None:
    for point in triangle:
        for value in point:
            if abs(value.numerator).bit_length()>limit or value.denominator.bit_length()>limit:
                raise InvalidModelError("rational coordinate exceeded max_coordinate_bits")

def _area_vector(triangle:RationalTriangle3)->RationalPoint3:
    return _cross(_sub(triangle[1],triangle[0]),_sub(triangle[2],triangle[0]))

def arrange_triangle_mesh_globally(
    triangles:Iterable[RationalTriangle3],planes:Iterable[RationalPlane],*,
    max_fragments:int=16384,max_coordinate_bits:int=4096,max_edges:int=65536,
    max_topology_checks:int=1_000_000,max_coverage_checks:int=1_000_000,
    max_aggregate_rational_bits:int=64_000_000,
    resource_ledger:BooleanResourceLedger|None=None,
)->GlobalTriangleArrangement:
    """Arrange source triangles and retriangulate every global edge T-junction.

    Every exact global vertex strictly inside a fragment edge is inserted into
    that edge's boundary chain. A rational face centroid fans the resulting
    boundary polygon into conforming triangles. The returned fragments are
    these conforming faces, not the pre-subdivision triangles.
    """
    for name,value in (("max_fragments",max_fragments),("max_coordinate_bits",max_coordinate_bits),
                       ("max_edges",max_edges),("max_topology_checks",max_topology_checks),
                       ("max_coverage_checks",max_coverage_checks),
                       ("max_aggregate_rational_bits",max_aggregate_rational_bits)):
        if isinstance(value,bool) or not isinstance(value,int) or value<1:
            raise InvalidModelError(f"{name} must be a positive integer")
    if max_aggregate_rational_bits>64_000_000:
        raise InvalidModelError("max_aggregate_rational_bits exceeds its supported hard ceiling")
    ledger=resource_ledger or BooleanResourceLedger()
    if not isinstance(ledger,BooleanResourceLedger):
        raise InvalidModelError("resource_ledger must be a BooleanResourceLedger")
    source_items,plane_items=tuple(triangles),tuple(planes)
    if not source_items: raise InvalidModelError("at least one source triangle is required")
    if len(source_items)>max_fragments: raise InvalidModelError("source triangle count exceeded max_fragments")
    if any(not isinstance(p,RationalPlane) for p in plane_items):
        raise InvalidModelError("planes must contain only RationalPlane values")
    if len({p.plane_index for p in plane_items})!=len(plane_items):
        raise InvalidModelError("plane indices must be unique")
    aggregate_input_bits=0
    for tri in source_items:
        _validate_source(tri); _check_bits(tri,max_coordinate_bits)
        aggregate_input_bits += sum(
            abs(value.numerator).bit_length()+value.denominator.bit_length()
            for point in tri for value in point
        )
        if aggregate_input_bits>max_aggregate_rational_bits:
            raise InvalidModelError("global arrangement aggregate rational bit budget exceeded")
    for plane in plane_items:
        _check_bits(plane.vertices,max_coordinate_bits)
        aggregate_input_bits += sum(
            abs(value.numerator).bit_length()+value.denominator.bit_length()
            for point in plane.vertices for value in point
        )
        if aggregate_input_bits>max_aggregate_rational_bits:
            raise InvalidModelError("global arrangement aggregate rational bit budget exceeded")

    ledger.charge("aggregate_rational_bits", aggregate_input_bits)
    raw_fragments=[]
    expected_by_source={}
    actual_by_source={}
    for source_index,source in enumerate(source_items):
        remaining=min(max_fragments-len(raw_fragments),ledger.remaining("fragments"))
        if remaining<1: raise InvalidModelError("global arrangement exceeded the invocation fragment budget")
        local=arrange_triangles_by_planes((source,),plane_items,max_fragments=remaining,
                                          max_coordinate_bits=max_coordinate_bits)
        normal=_area_vector(source)
        expected=_dot(normal,normal)
        actual=sum((_dot(_area_vector(f.vertices),normal) for f in local),Fraction(0))
        if actual!=expected:
            raise InvalidModelError(f"global coverage area mismatch for source triangle {source_index}")
        expected_by_source[source_index]=expected
        actual_by_source[source_index]=actual
        ledger.charge("fragments", len(local))
        raw_fragments.extend(RationalTriangleFragment(source_index,f.side_signature,f.vertices) for f in local)
        if len(raw_fragments)>max_fragments: raise InvalidModelError("global arrangement exceeded max_fragments")

    global_points=sorted({point for fragment in raw_fragments for point in fragment.vertices})
    point_ids={point:index for index,point in enumerate(global_points)}
    if 3*len(raw_fragments)>ledger.remaining("edges"):
        raise InvalidModelError("global arrangement exceeded the invocation edge budget")
    raw_edges=set()
    for fragment in raw_fragments:
        ids=tuple(point_ids[p] for p in fragment.vertices)
        for first,second in ((ids[0],ids[1]),(ids[1],ids[2]),(ids[2],ids[0])):
            raw_edges.add((first,second) if first<second else (second,first))
    ledger.charge("edges", len(raw_edges))
    # The T-junction pass visits every registered global vertex for each
    # of the three edges of every raw fragment. Unique edge count is smaller
    # than (or equal to) this work for shared-edge meshes, so charging only
    # len(global_points) * len(raw_edges) under-counts the actual scan.
    topology_checks = len(global_points) * 3 * len(raw_fragments)
    if topology_checks > max_topology_checks:
        raise InvalidModelError("global topology scan exceeded max_topology_checks")
    ledger.charge("topology_checks", topology_checks)

    t_junctions=set()
    conforming=[]
    for fragment in raw_fragments:
        a,b,c=fragment.vertices
        boundary_ids=[]
        for start,end in ((a,b),(b,c),(c,a)):
            direction=_sub(end,start)
            length_squared=_dot(direction,direction)
            start_id,end_id=point_ids[start],point_ids[end]
            interior=[]
            for candidate in global_points:
                candidate_id=point_ids[candidate]
                if candidate_id in (start_id,end_id): continue
                offset=_sub(candidate,start)
                if _cross(direction,offset)==(0,0,0):
                    projection=_dot(offset,direction)
                    if 0<projection<length_squared:
                        interior.append((projection,candidate_id))
            if interior:
                low,high=(start_id,end_id) if start_id<end_id else (end_id,start_id)
                t_junctions.update((low,high,candidate_id) for _,candidate_id in interior)
            ordered=[start_id]+[candidate_id for _,candidate_id in sorted(interior)]+[end_id]
            boundary_ids.extend(ordered[:-1])
        if len(boundary_ids)==3:
            ledger.charge("fragments", 1)
            conforming.append(fragment)
            continue
        # Ear-clip the convex boundary polygon. This inserts no synthetic
        # interior coordinates, preserving exact source/intersection points
        # and avoiding artificial 1/3 coordinates in binary64 B-rep workflows.
        polygon=[global_points[index] for index in boundary_ids]
        source_normal=_area_vector(fragment.vertices)
        while len(polygon)>3:
            ears=[]
            for index in range(len(polygon)):
                previous=polygon[index-1]
                current=polygon[index]
                following=polygon[(index+1)%len(polygon)]
                orientation=_dot(_cross(_sub(current,previous),_sub(following,current)),source_normal)
                if orientation>0:
                    diagonal=_sub(following,previous)
                    diagonal_length=_dot(diagonal,diagonal)
                    diagonal_blocked=False
                    for candidate_index,candidate in enumerate(polygon):
                        if candidate_index in (index,(index-1)%len(polygon),(index+1)%len(polygon)):
                            continue
                        offset=_sub(candidate,previous)
                        if _cross(diagonal,offset)==(0,0,0):
                            projection=_dot(offset,diagonal)
                            if 0<projection<diagonal_length:
                                diagonal_blocked=True
                                break
                    if diagonal_blocked:
                        continue
                    key=(current,min(previous,following),max(previous,following))
                    ears.append((key,index,previous,current,following))
            if not ears:
                raise InvalidModelError("global conforming polygon could not be triangulated exactly")
            _,index,previous,current,following=min(ears,key=lambda item:item[0])
            ledger.charge("fragments", 1)
            conforming.append(RationalTriangleFragment(
                fragment.source_triangle_index,fragment.side_signature,
                (previous,current,following)))
            polygon.pop(index)
            if len(conforming)>max_fragments:
                raise InvalidModelError("global conforming triangulation exceeded max_fragments")
        final_triangle=(polygon[0],polygon[1],polygon[2])
        if _dot(_area_vector(final_triangle),source_normal)<=0:
            raise InvalidModelError("global conforming triangulation changed source winding")
        ledger.charge("fragments", 1)
        conforming.append(RationalTriangleFragment(
            fragment.source_triangle_index,fragment.side_signature,final_triangle))
        if len(conforming)>max_fragments:
            raise InvalidModelError("global conforming triangulation exceeded max_fragments")

    final_by_source={index:[] for index in range(len(source_items))}
    for fragment in conforming: final_by_source[fragment.source_triangle_index].append(fragment.vertices)
    coverage=[]
    checks_used=0
    coverage_bits_used=0
    for source_index,source in enumerate(source_items):
        source_fragments=tuple(final_by_source[source_index])
        partition_bits=sum(
            abs(value.numerator).bit_length()+value.denominator.bit_length()
            for triangle in (source,*source_fragments)
            for point in triangle for value in point
        )
        remaining_bits=min(max_aggregate_rational_bits-coverage_bits_used,
                           ledger.remaining("aggregate_rational_bits"))
        if partition_bits>remaining_bits:
            raise InvalidModelError("global coverage aggregate rational bit budget exceeded")
        stage_remaining_checks=max_coverage_checks-checks_used
        if stage_remaining_checks<1:
            raise InvalidModelError("global coverage pair-check budget exhausted")
        invocation_remaining_checks=ledger.remaining("coverage_checks")
        if invocation_remaining_checks<1:
            raise InvalidModelError(
                "Boolean invocation resource budget exceeded for coverage_checks"
            )
        remaining_checks=min(stage_remaining_checks,invocation_remaining_checks)
        ledger.charge("aggregate_rational_bits", partition_bits)
        oracle=certify_triangle_partition(
            source,source_fragments,
            max_pairwise_checks=remaining_checks,
            max_aggregate_rational_bits=remaining_bits,
        )
        checks_used+=oracle.pairwise_checks
        coverage_bits_used+=partition_bits
        ledger.charge("coverage_checks", oracle.pairwise_checks)
        if not oracle.certified:
            raise InvalidModelError(f"conforming exact coverage oracle rejected source triangle {source_index}")
        coverage.append(SourceCoverageReport(source_index,expected_by_source[source_index],
            actual_by_source[source_index],True,len(final_by_source[source_index]),oracle.certified,
            oracle.outside_fragment_indices,oracle.overlapping_fragment_pairs,oracle.duplicate_fragment_pairs))

    final_points=sorted({point for fragment in conforming for point in fragment.vertices})
    final_ids={point:index for index,point in enumerate(final_points)}
    vertices=tuple(GlobalArrangementVertex(index,point) for index,point in enumerate(final_points))
    if 3*len(conforming)>ledger.remaining("edges"):
        raise InvalidModelError("global arrangement exceeded the invocation edge budget")
    faces=[]
    edge_faces={}
    for face_id,fragment in enumerate(conforming):
        ids=tuple(final_ids[p] for p in fragment.vertices)
        faces.append(GlobalArrangementFace(face_id,fragment.source_triangle_index,fragment.side_signature,ids))
        for first,second in ((ids[0],ids[1]),(ids[1],ids[2]),(ids[2],ids[0])):
            edge=(first,second) if first<second else (second,first)
            edge_faces.setdefault(edge,set()).add(face_id)
            if len(edge_faces)>max_edges: raise InvalidModelError("global arrangement exceeded max_edges")
    if len(vertices)*len(edge_faces)>max_topology_checks:
        raise InvalidModelError("global topology scan exceeded max_topology_checks")
    ledger.charge("edges", len(edge_faces))
    ledger.charge("topology_checks", len(vertices)*len(edge_faces))
    # Fail closed if centroid insertion introduced any new T-junction that
    # was not present in the original global point set.
    for first_id,second_id in edge_faces:
        first_point,second_point=final_points[first_id],final_points[second_id]
        direction=_sub(second_point,first_point)
        length_squared=_dot(direction,direction)
        for candidate in final_points:
            if candidate in (first_point,second_point):
                continue
            offset=_sub(candidate,first_point)
            if _cross(direction,offset)==(0,0,0):
                projection=_dot(offset,direction)
                if 0<projection<length_squared:
                    raise InvalidModelError("global conforming triangulation left an unresolved T-junction")
    edges=tuple(GlobalArrangementEdge(edge,tuple(sorted(incident))) for edge,incident in sorted(edge_faces.items()))
    adjacent=sorted({(first,second) for edge in edges for i,first in enumerate(edge.incident_face_ids)
                     for second in edge.incident_face_ids[i+1:]})
    boundary=tuple(edge.vertex_ids for edge in edges if len(edge.incident_face_ids)==1)
    non_manifold=tuple(edge.vertex_ids for edge in edges if len(edge.incident_face_ids)>2)
    # Diagnostics are expressed in the final returned vertex-ID space;
    # face-centroid insertion changes deterministic vertex numbering.
    final_t_junctions=tuple(sorted({
        (final_ids[global_points[first]],final_ids[global_points[second]],
         final_ids[global_points[candidate]])
        for first,second,candidate in t_junctions
    }))
    return GlobalTriangleArrangement(vertices,tuple(faces),edges,tuple(adjacent),boundary,non_manifold,
        final_t_junctions,tuple(coverage),tuple(conforming))
