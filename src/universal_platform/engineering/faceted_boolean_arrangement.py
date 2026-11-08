"""Bounded global arrangement orchestration for multiple faceted mesh inputs."""
from __future__ import annotations
from dataclasses import dataclass
from fractions import Fraction
from math import gcd, lcm
from typing import Sequence

from .errors import InvalidModelError
from .mesh import TriangleMesh, validate_triangle_mesh
from .mesh_intersection import analyze_mesh_intersections
from .triangle_coverage_oracle import (coplanar_contact_is_covered, coplanar_triangle_intersection_geometry, coplanar_triangle_intersection_kind)
from .triangle_fragment_arrangement import RationalPlane, RationalPoint3, RationalTriangle3, RationalTriangleFragment
from .global_triangle_arrangement import GlobalTriangleArrangement, arrange_triangle_mesh_globally

@dataclass(frozen=True, slots=True)
class FacetedBooleanArrangement:
    global_arrangement: GlobalTriangleArrangement
    fragments_by_solid: tuple[tuple[RationalTriangleFragment,...],...]
    source_triangle_count: int
    unique_plane_count: int
    coplanar_pair_checks: int
    coplanar_coverage_checks: int = 0

def _q(value:float)->Fraction:
    return Fraction.from_float(float(value))

def _triangle(mesh:TriangleMesh,face_index:int)->RationalTriangle3:
    face=mesh.triangles[face_index]
    return tuple(tuple(_q(value) for value in (
        mesh.vertices[index].x,mesh.vertices[index].y,mesh.vertices[index].z))
        for index in face) # type: ignore[return-value]

def _sub(a:RationalPoint3,b:RationalPoint3)->RationalPoint3:
    return tuple(a[i]-b[i] for i in range(3)) # type: ignore[return-value]

def _cross(a:RationalPoint3,b:RationalPoint3)->RationalPoint3:
    return (a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])

def _dot(a:RationalPoint3,b:RationalPoint3)->Fraction:
    return sum((a[i]*b[i] for i in range(3)),Fraction(0))

def _plane_key(triangle:RationalTriangle3)->tuple[int,int,int,int]:
    a,b,c=triangle
    normal=_cross(_sub(b,a),_sub(c,a))
    coefficients=(*normal,_dot(normal,a))
    common=lcm(*(value.denominator for value in coefficients))
    integers=[int(value*common) for value in coefficients]
    divisor=0
    for value in integers: divisor=gcd(divisor,abs(value))
    if divisor==0: raise InvalidModelError("cannot derive a plane from a degenerate triangle")
    integers=[value//divisor for value in integers]
    first=next(value for value in integers if value)
    if first<0: integers=[-value for value in integers]
    return tuple(integers) # type: ignore[return-value]

def _signed_volume(triangles:Sequence[RationalTriangle3])->Fraction:
    return sum((_dot(a,_cross(b,c)) for a,b,c in triangles),Fraction(0))/6

def arrange_faceted_boolean_meshes(
    meshes:tuple[TriangleMesh,...],
    *,
    max_source_triangles:int=2048,
    max_unique_planes:int=2048,
    max_fragments:int=32768,
    max_coordinate_bits:int=4096,
    max_edges:int=131072,
    max_topology_checks:int=10_000_000,
    max_coverage_checks:int=10_000_000,
    max_coplanar_checks:int=1_000_000,
    max_coplanar_coverage_checks:int=1_000_000,
)->FacetedBooleanArrangement:
    """Create a conservative all-source-plane arrangement for 2..16 meshes.

    Every unique supporting plane from every source triangle is applied to
    every source facet. This intentionally over-splits but ensures that a
    non-coplanar source face cannot cross another input facet's supporting
    plane inside a returned fragment. Exact global T-junctions are then
    converted to conforming triangles. Positive-area coplanar overlaps add exact edge-line cutters; point/edge-only contact is rejected.
    """
    if not isinstance(meshes,tuple) or not 2<=len(meshes)<=16:
        raise InvalidModelError("faceted Boolean arrangement requires 2..16 immutable TriangleMesh inputs")
    for name,value in (("max_source_triangles",max_source_triangles),("max_unique_planes",max_unique_planes),
                       ("max_fragments",max_fragments),("max_coordinate_bits",max_coordinate_bits),
                       ("max_edges",max_edges),("max_topology_checks",max_topology_checks),
                       ("max_coverage_checks",max_coverage_checks),("max_coplanar_checks",max_coplanar_checks),
                       ("max_coplanar_coverage_checks",max_coplanar_coverage_checks)):
        if isinstance(value,bool) or not isinstance(value,int) or value<1:
            raise InvalidModelError(f"{name} must be a positive integer")
    if any(not isinstance(mesh,TriangleMesh) for mesh in meshes):
        raise InvalidModelError("all Boolean inputs must be TriangleMesh values")
    # Reject oversized inputs before topology validation and self-intersection
    # analysis, both of which may scan every source face or face pair.
    source_triangle_total = sum(len(mesh.triangles) for mesh in meshes)
    if source_triangle_total > max_source_triangles:
        raise InvalidModelError("faceted arrangement exceeded max_source_triangles")
    if len({(mesh.frame_id,mesh.length_unit) for mesh in meshes})!=1:
        raise InvalidModelError("Boolean inputs must share frame and length unit")

    source_triangles=[]
    source_offsets=[0]
    per_mesh_triangles=[]
    plane_by_key={}
    for mesh in meshes:
        topology=validate_triangle_mesh(mesh)
        if not (topology.valid and topology.watertight and topology.consistently_oriented):
            raise InvalidModelError("Boolean input mesh is not a valid oriented watertight shell")
        if analyze_mesh_intersections(mesh).status!="NO_INTERSECTIONS_FOUND":
            raise InvalidModelError("Boolean input mesh is self-intersecting or indeterminate")
        triangles=tuple(_triangle(mesh,index) for index in range(len(mesh.triangles)))
        if _signed_volume(triangles)<=0:
            raise InvalidModelError("Boolean input mesh must have positive outward signed volume")
        per_mesh_triangles.append(triangles)
        source_triangles.extend(triangles)
        source_offsets.append(len(source_triangles))
        if len(source_triangles)>max_source_triangles:
            raise InvalidModelError("faceted arrangement exceeded max_source_triangles")
        for triangle in triangles:
            key=_plane_key(triangle)
            if key not in plane_by_key:
                plane_by_key[key]=RationalPlane(len(plane_by_key),triangle)
                if len(plane_by_key)>max_unique_planes:
                    raise InvalidModelError("faceted arrangement exceeded max_unique_planes")

    coplanar_checks=0
    active_coplanar_planes=set()
    area_polygons_by_plane={}
    contact_polygons_by_plane={}
    for first_index in range(len(meshes)):
        for second_index in range(first_index+1,len(meshes)):
            first_by_plane={}
            for triangle in per_mesh_triangles[first_index]:
                first_by_plane.setdefault(_plane_key(triangle),[]).append(triangle)
            second_by_plane={}
            for triangle in per_mesh_triangles[second_index]:
                second_by_plane.setdefault(_plane_key(triangle),[]).append(triangle)
            for key in first_by_plane.keys() & second_by_plane.keys():
                for first in first_by_plane[key]:
                    for second in second_by_plane[key]:
                        coplanar_checks+=1
                        if coplanar_checks>max_coplanar_checks:
                            raise InvalidModelError("coplanar pair scan exceeded max_coplanar_checks")
                        relation=coplanar_triangle_intersection_kind(first,second)
                        if relation=="AREA_OVERLAP":
                            geometry=coplanar_triangle_intersection_geometry(first,second)
                            if geometry is None:
                                raise InvalidModelError("coplanar overlap lost its supporting plane")
                            _, polygon=geometry
                            active_coplanar_planes.add(key)
                            area_polygons_by_plane.setdefault(key,[]).append(polygon)
                        elif relation=="CONTACT":
                            geometry=coplanar_triangle_intersection_geometry(first,second)
                            if geometry is None:
                                raise InvalidModelError("coplanar contact lost its supporting plane")
                            _, polygon=geometry
                            contact_polygons_by_plane.setdefault(key,[]).append(polygon)
                        elif relation!="DISJOINT":
                            raise InvalidModelError("unexpected coplanar relation: "+relation)
    coplanar_coverage_checks = 0
    unsupported_contacts = False
    for key, contacts in contact_polygons_by_plane.items():
        overlap_polygons = area_polygons_by_plane.get(key, ())
        for contact in contacts:
            # The helper may inspect every overlap polygon. Charge the
            # worst-case work before calling it and fail closed on overflow.
            coplanar_coverage_checks += max(1, len(overlap_polygons))
            if coplanar_coverage_checks > max_coplanar_coverage_checks:
                raise InvalidModelError(
                    "coplanar contact coverage exceeded max_coplanar_coverage_checks"
                )
            if not coplanar_contact_is_covered(contact, overlap_polygons):
                unsupported_contacts = True
    if unsupported_contacts:
        raise InvalidModelError("coplanar point/edge contact is unsupported")
    # Build a complete planar line arrangement on each active coplanar plane:
    # include every source triangle edge on that plane, not only edges from
    # the individual overlapping triangle pairs.
    for key in sorted(active_coplanar_planes):
        for triangles in per_mesh_triangles:
            for triangle in triangles:
                if _plane_key(triangle)!=key:
                    continue
                normal=_cross(_sub(triangle[1],triangle[0]),_sub(triangle[2],triangle[0]))
                for edge_start,edge_end in ((triangle[0],triangle[1]),
                                            (triangle[1],triangle[2]),
                                            (triangle[2],triangle[0])):
                    off_plane=tuple(edge_start[axis]+normal[axis] for axis in range(3))
                    cutter=(edge_start,edge_end,off_plane)
                    cutter_key=_plane_key(cutter)
                    if cutter_key not in plane_by_key:
                        plane_by_key[cutter_key]=RationalPlane(len(plane_by_key),cutter)
                        if len(plane_by_key)>max_unique_planes:
                            raise InvalidModelError("coplanar cutters exceeded max_unique_planes")

    arrangement=arrange_triangle_mesh_globally(
        tuple(source_triangles),tuple(plane_by_key.values()),
        max_fragments=max_fragments,max_coordinate_bits=max_coordinate_bits,
        max_edges=max_edges,max_topology_checks=max_topology_checks,
        max_coverage_checks=max_coverage_checks,
    )
    grouped=[[] for _ in meshes]
    for fragment in arrangement.fragments:
        source_index=fragment.source_triangle_index
        owner=next(index for index in range(len(meshes))
                   if source_offsets[index]<=source_index<source_offsets[index+1])
        local_index=source_index-source_offsets[owner]
        grouped[owner].append(RationalTriangleFragment(
            local_index,fragment.side_signature,fragment.vertices))
    if any(len(items)==0 for items in grouped):
        raise InvalidModelError("global arrangement omitted an input mesh")
    return FacetedBooleanArrangement(
        arrangement,tuple(tuple(items) for items in grouped),
        len(source_triangles),len(plane_by_key),coplanar_checks,coplanar_coverage_checks,
    )
