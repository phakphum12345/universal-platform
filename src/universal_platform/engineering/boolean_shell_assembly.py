"""Exact topology checks and conservative B-rep shell assembly for Boolean boundaries."""
from __future__ import annotations
from dataclasses import dataclass
from fractions import Fraction
from hashlib import sha256
import json

from .brep import BRepSolid, brep_from_triangle_mesh, validate_brep_solid
from .brep_multishell import BRepMultiShellSolid, validate_brep_multishell_solid
from .boolean_boundary_selection import BooleanBoundarySelection
from .errors import InvalidModelError
from .boolean_resource_budget import BooleanResourceLedger
from .geometry import Vec3
from .material_classification import ExactMeshMaterialClassifier, MaterialClassification
from .mesh import TriangleMesh, validate_triangle_mesh
from .mesh_intersection import analyze_mesh_intersections
from .triangle_fragment_arrangement import RationalPoint3, RationalTriangle3

@dataclass(frozen=True, slots=True)
class AssembledBooleanComponent:
    solid: BRepMultiShellSolid
    exact_net_volume: Fraction
    outer_face_count: int
    cavity_face_counts: tuple[int,...]

@dataclass(frozen=True, slots=True)
class BooleanShellAssemblyResult:
    components: tuple[AssembledBooleanComponent,...]
    total_exact_volume: Fraction
    selected_face_count: int
    connected_shell_count: int
    discarded_cavity_count: int


def _sub(a:RationalPoint3,b:RationalPoint3)->RationalPoint3:
    return tuple(a[i]-b[i] for i in range(3)) # type: ignore[return-value]

def _cross(a:RationalPoint3,b:RationalPoint3)->RationalPoint3:
    return (a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])

def _dot(a:RationalPoint3,b:RationalPoint3)->Fraction:
    return sum((a[i]*b[i] for i in range(3)),Fraction(0))

def _signed_volume(faces:tuple[RationalTriangle3,...])->Fraction:
    total=Fraction(0)
    for a,b,c in faces: total+=_dot(a,_cross(b,c))
    return total/6

def _edge_uses(faces:tuple[RationalTriangle3,...]):
    uses={}
    for face_index,face in enumerate(faces):
        if len(set(face))!=3: raise InvalidModelError("shell contains a degenerate triangle")
        for a,b in ((face[0],face[1]),(face[1],face[2]),(face[2],face[0])):
            key=tuple(sorted((a,b)))
            uses.setdefault(key,[]).append((face_index,a,b))
    return uses

def _components(faces:tuple[RationalTriangle3,...],uses):
    adjacency={i:set() for i in range(len(faces))}
    for edge,attached in uses.items():
        if len(attached)!=2:
            raise InvalidModelError(
                f"shell assembly requires exactly two uses per edge; got {len(attached)} for {edge}; "
                f"incident faces={[(item[0], faces[item[0]]) for item in attached]}"
            )
        first,second=attached
        if first[1]!=second[2] or first[2]!=second[1]:
            raise InvalidModelError("shell edge uses must have opposite directions")
        adjacency[first[0]].add(second[0]); adjacency[second[0]].add(first[0])
    remaining=set(adjacency); result=[]
    while remaining:
        seed=min(remaining); remaining.remove(seed); found={seed}; pending=[seed]
        while pending:
            current=pending.pop()
            for neighbor in adjacency[current]:
                if neighbor in remaining:
                    remaining.remove(neighbor); found.add(neighbor); pending.append(neighbor)
        result.append(tuple(sorted(found)))
    return tuple(result)

def _mesh_from_faces(faces:tuple[RationalTriangle3,...],template:TriangleMesh,solid_id:str)->TriangleMesh:
    points=sorted({point for face in faces for point in face})
    indices={point:index for index,point in enumerate(points)}
    vertices=[]
    for point in points:
        converted=[]
        for value in point:
            as_float=float(value)
            if Fraction.from_float(as_float)!=value:
                raise InvalidModelError(f"exact shell coordinate {value} at {point} is not losslessly representable as binary64")
            converted.append(as_float)
        vertices.append(Vec3(*converted))
    triangles=tuple(tuple(indices[point] for point in face) for face in faces)
    payload={"solid_id":solid_id,"vertices":[[str(v) for v in point] for point in points],
             "triangles":[list(face) for face in triangles]}
    digest=sha256(json.dumps(payload,sort_keys=True,separators=(",",":")).encode()).hexdigest()
    mesh=TriangleMesh(solid_id,template.frame_id,template.length_unit,"BREP_BOOLEAN",
                      digest,tuple(vertices),triangles)
    validation=validate_triangle_mesh(mesh)
    if not (validation.valid and validation.watertight and validation.consistently_oriented):
        raise InvalidModelError("assembled shell failed watertight/orientation validation: "+"; ".join(validation.issues))
    intersections=analyze_mesh_intersections(mesh)
    if intersections.status!="NO_INTERSECTIONS_FOUND":
        raise InvalidModelError("assembled shell self-intersection status is "+intersections.status)
    return mesh

def _reverse_faces(faces:tuple[RationalTriangle3,...])->tuple[RationalTriangle3,...]:
    return tuple((a,c,b) for a,b,c in faces)

def _inside_all_vertices(cavity_faces:tuple[RationalTriangle3,...],outer_mesh:TriangleMesh)->bool:
    classifier=ExactMeshMaterialClassifier(outer_mesh)
    if classifier.reason: raise InvalidModelError("outer shell classifier unavailable: "+classifier.reason)
    for point in {p for face in cavity_faces for p in face}:
        state=classifier.classify_rational(point).classification
        if state is not MaterialClassification.INSIDE: return False
    return True


def assemble_boolean_shells(
    selection:BooleanBoundarySelection,
    input_meshes:tuple[TriangleMesh,...],
    *,
    result_id_prefix:str="boolean.result",
    max_faces:int=100_000,
    max_vertices:int=100_000,
    max_coordinate_bits:int=4096,
    resource_ledger:BooleanResourceLedger|None=None,
)->BooleanShellAssemblyResult:
    """Assemble selected oriented facets into validated outer/cavity components.

    Distinct rational points are never tolerance-welded. Because the public
    B-rep stores binary64 coordinates, non-binary-rational intersection points
    are rejected rather than rounded. Every output shell must be closed,
    consistently oriented, self-intersection-free and independently B-rep
    validated. Nested material islands and ambiguous cavity ownership fail closed.
    """
    ledger=resource_ledger or BooleanResourceLedger()
    if not isinstance(ledger,BooleanResourceLedger):
        raise InvalidModelError("resource_ledger must be a BooleanResourceLedger")
    if not isinstance(selection,BooleanBoundarySelection):
        raise InvalidModelError("assemble_boolean_shells requires a BooleanBoundarySelection")
    if not isinstance(input_meshes,tuple) or not input_meshes:
        raise InvalidModelError("input_meshes must be a non-empty immutable tuple")
    if not isinstance(result_id_prefix,str) or not result_id_prefix or any(ch not in "abcdefghijklmnopqrstuvwxyz0123456789.-/" for ch in result_id_prefix):
        raise InvalidModelError("result_id_prefix must be a lowercase stable identifier")
    for name,value in (("max_faces",max_faces),("max_vertices",max_vertices),("max_coordinate_bits",max_coordinate_bits)):
        if isinstance(value,bool) or not isinstance(value,int) or value<1:
            raise InvalidModelError(f"{name} must be a positive integer")
    selected=selection.selected_fragments
    if not selected: 
        return BooleanShellAssemblyResult((),Fraction(0),0,0,0)
    if len(selected)>max_faces:
        raise InvalidModelError("shell assembly exceeded max_faces")
    ledger.charge("faces",len(selected))
    for item in selected:
        if item.source_solid_index>=len(input_meshes):
            raise InvalidModelError("selected fragment references an unknown input solid")
    faces=tuple(item.vertices for item in selected)
    all_points={point for face in faces for point in face}
    if len(all_points)>max_vertices:
        raise InvalidModelError("shell assembly exceeded max_vertices")
    ledger.charge("vertices",len(all_points))
    for point in all_points:
        for value in point:
            if abs(value.numerator).bit_length()>max_coordinate_bits or value.denominator.bit_length()>max_coordinate_bits:
                raise InvalidModelError("shell coordinate exceeded max_coordinate_bits")
    aggregate_bits=sum(abs(value.numerator).bit_length()+value.denominator.bit_length()
                       for point in all_points for value in point)
    ledger.charge("aggregate_rational_bits",aggregate_bits)
    uses=_edge_uses(faces)
    groups=_components(faces,uses)
    shells=[]
    for group_index,face_indices in enumerate(groups):
        shell_faces=tuple(faces[i] for i in face_indices)
        volume=_signed_volume(shell_faces)
        if volume==0: raise InvalidModelError("assembled shell has zero exact signed volume")
        was_cavity=volume<0
        normalized=_reverse_faces(shell_faces) if was_cavity else shell_faces
        mesh=_mesh_from_faces(normalized,input_meshes[0],f"{result_id_prefix}.shell.{group_index:03d}")
        brep=brep_from_triangle_mesh(mesh)
        validation=validate_brep_solid(brep)
        if not validation.valid:
            raise InvalidModelError("assembled B-rep shell failed validation: "+"; ".join(validation.issues))
        shells.append((was_cavity,normalized,mesh,brep,abs(volume),len(shell_faces)))

    outers=[item for item in shells if not item[0]]
    cavities=[item for item in shells if item[0]]
    if not outers and cavities:
        raise InvalidModelError("Boolean result contains cavity shells but no outer material shell")
    cavity_owners={index:[] for index in range(len(outers))}
    for cavity in cavities:
        owners=[index for index,outer in enumerate(outers) if _inside_all_vertices(cavity[1],outer[2])]
        if len(owners)!=1:
            raise InvalidModelError("cavity shell must be strictly contained by exactly one outer shell")
        cavity_owners[owners[0]].append(cavity)

    # Separate positive shells must not be nested; nested material islands need
    # a richer parent/child shell profile than the current multi-shell contract.
    outer_classifiers=[ExactMeshMaterialClassifier(item[2]) for item in outers]
    for i,outer in enumerate(outers):
        for j,other in enumerate(outers):
            if i==j: continue
            point=next(iter(outer[1]))[0]
            state=outer_classifiers[j].classify_rational(point).classification
            if state is not MaterialClassification.OUTSIDE:
                raise InvalidModelError("nested or ambiguous positive shells are unsupported")

    components=[]
    for index,outer in enumerate(outers):
        cavity_items=tuple(cavity_owners[index])
        cavity_breps=tuple(item[3] for item in cavity_items)
        solid=BRepMultiShellSolid(f"{result_id_prefix}.{index:03d}",outer[3],cavity_breps)
        validation=validate_brep_multishell_solid(solid)
        if not validation.valid:
            raise InvalidModelError("assembled multi-shell solid failed validation: "+"; ".join(validation.issues))
        net_volume=outer[4]-sum((item[4] for item in cavity_items),Fraction(0))
        if net_volume<=0:
            raise InvalidModelError("assembled material component has non-positive exact net volume")
        components.append(AssembledBooleanComponent(solid,net_volume,outer[5],
                            tuple(item[5] for item in cavity_items)))
    total=sum((item.exact_net_volume for item in components),Fraction(0))
    if total<=0:
        raise InvalidModelError("assembled Boolean result must have positive exact net volume")
    return BooleanShellAssemblyResult(tuple(components),total,len(selected),len(groups),len(cavities))


def assemble_rational_boolean_solid(
    selection: BooleanBoundarySelection,
    input_meshes: tuple[TriangleMesh, ...],
    *,
    result_id: str = "boolean.result",
    max_faces: int = 100_000,
    max_vertices: int = 100_000,
    max_coordinate_bits: int = 4096,
    max_inter_shell_pair_checks: int = 5_000_000,
    max_containment_ray_checks: int = 5_000_000,
    max_aggregate_rational_bits: int = 64_000_000,
):
    """Assemble exact rational outer/cavity shells without binary64 conversion."""
    from .rational_faceted_solid import RationalFacetedSolid, _axes_overlap
    from .rational_boolean_solid import (
        RationalBooleanComponent, RationalBooleanShell, RationalBooleanSolid,
    )
    from .material_classification import (
        MaterialClassification, classify_rational_point_against_triangles,
    )

    ledger = resource_ledger or BooleanResourceLedger()
    if not isinstance(ledger, BooleanResourceLedger):
        raise InvalidModelError("resource_ledger must be a BooleanResourceLedger")
    if not isinstance(selection, BooleanBoundarySelection):
        raise InvalidModelError("selection must be a BooleanBoundarySelection")
    if not isinstance(input_meshes, tuple) or not input_meshes:
        raise InvalidModelError("input_meshes must be a non-empty immutable tuple")
    if not isinstance(result_id, str) or not result_id or any(
        ch not in "abcdefghijklmnopqrstuvwxyz0123456789.-/" for ch in result_id
    ):
        raise InvalidModelError("result_id must be a lowercase stable identifier")
    for name, value in (
        ("max_faces", max_faces), ("max_vertices", max_vertices),
        ("max_coordinate_bits", max_coordinate_bits),
        ("max_inter_shell_pair_checks", max_inter_shell_pair_checks),
        ("max_containment_ray_checks", max_containment_ray_checks),
        ("max_aggregate_rational_bits", max_aggregate_rational_bits),
    ):
        if isinstance(value, bool) or not isinstance(value, int) or value < 1:
            raise InvalidModelError(f"{name} must be a positive integer")
    if max_faces > 200_000 or max_vertices > 100_000 or max_coordinate_bits > 16_384:
        raise InvalidModelError("rational shell resource limit exceeds its supported hard ceiling")
    if (max_inter_shell_pair_checks > 5_000_000 or max_containment_ray_checks > 5_000_000
            or max_aggregate_rational_bits > 64_000_000):
        raise InvalidModelError("rational shell aggregate resource limit exceeds its hard ceiling")

    fragments = selection.selected_fragments
    if not fragments:
        raise InvalidModelError("empty Boolean results do not produce a solid artifact")
    if len(fragments) > max_faces:
        raise InvalidModelError("rational shell assembly exceeded max_faces")
    if any(item.source_solid_index >= len(input_meshes) for item in fragments):
        raise InvalidModelError("selected fragment references an unknown input solid")

    faces = tuple(item.vertices for item in fragments)
    points = {point for face in faces for point in face}
    if len(points) > max_vertices:
        raise InvalidModelError("rational shell assembly exceeded max_vertices")
    aggregate_bits = 0
    for point in points:
        if len(point) != 3 or any(not isinstance(value, Fraction) for value in point):
            raise InvalidModelError("selected shell coordinates must be exact Fraction values")
        for value in point:
            if (abs(value.numerator).bit_length() > max_coordinate_bits
                    or value.denominator.bit_length() > max_coordinate_bits):
                raise InvalidModelError("shell coordinate exceeded max_coordinate_bits")
            aggregate_bits += abs(value.numerator).bit_length() + value.denominator.bit_length()
            if aggregate_bits > max_aggregate_rational_bits:
                raise InvalidModelError("aggregate rational shell bit budget exceeded")

    ledger.charge("aggregate_rational_bits", aggregate_bits)
    uses = _edge_uses(faces)
    groups = _components(faces, uses)
    shell_records = []
    for group_index, face_indices in enumerate(groups):
        shell_faces = tuple(faces[index] for index in face_indices)
        signed_volume = _signed_volume(shell_faces)
        if signed_volume == 0:
            raise InvalidModelError("rational Boolean shell has zero exact signed volume")
        role = "CAVITY" if signed_volume < 0 else "OUTER"
        normalized = _reverse_faces(shell_faces) if signed_volume < 0 else shell_faces
        vertices = tuple(sorted({point for face in normalized for point in face}))
        vertex_index = {point: index for index, point in enumerate(vertices)}
        triangles = tuple(sorted(
            tuple(vertex_index[point] for point in face) for face in normalized
        ))
        provenance = tuple(sorted({
            (input_meshes[fragments[index].source_solid_index].solid_id,
             input_meshes[fragments[index].source_solid_index].source_geometry_sha256)
            for index in face_indices
        }))
        solid = RationalFacetedSolid(
            f"{result_id}.shell.{group_index:04d}",
            input_meshes[0].frame_id,
            input_meshes[0].length_unit,
            vertices,
            triangles,
            provenance,
            max_coordinate_bits=max_coordinate_bits,
        )
        shell_triangles = tuple(
            tuple(solid.vertices[item] for item in face) for face in solid.triangles
        )
        shell_records.append({
            "group_index": group_index,
            "role": role,
            "solid": solid,
            "triangles": shell_triangles,
            "volume": abs(signed_volume),
        })

    # Charge all inter-shell triangle pairs before performing any pairwise work.
    pair_checks = sum(
        len(first["triangles"]) * len(second["triangles"])
        for first_index, first in enumerate(shell_records)
        for second in shell_records[first_index + 1:]
    )
    if pair_checks > max_inter_shell_pair_checks:
        raise InvalidModelError("inter-shell exact intersection pair budget exceeded")
    for first_index, first in enumerate(shell_records):
        for second in shell_records[first_index + 1:]:
            for first_triangle in first["triangles"]:
                for second_triangle in second["triangles"]:
                    if _axes_overlap(first_triangle, second_triangle, touching_is_overlap=True):
                        raise InvalidModelError(
                            "rational Boolean shells intersect or touch; unsupported shell contact"
                        )

    outers = [item for item in shell_records if item["role"] == "OUTER"]
    cavities = [item for item in shell_records if item["role"] == "CAVITY"]
    if not outers:
        raise InvalidModelError("rational Boolean result contains cavities but no outer shell")

    # Bound all exact point-in-shell work before running any ray predicate.
    containment_ray_checks = 0
    for outer_index, outer in enumerate(outers):
        for other_index, other in enumerate(outers):
            if outer_index != other_index:
                containment_ray_checks += len(other["triangles"]) * 7
    for cavity in cavities:
        for outer in outers:
            containment_ray_checks += len(outer["triangles"]) * 7
    for cavity_index, cavity in enumerate(cavities):
        for other in cavities[cavity_index + 1:]:
            containment_ray_checks += (
                len(other["triangles"]) + len(cavity["triangles"])
            ) * 7
    if containment_ray_checks > max_containment_ray_checks:
        raise InvalidModelError("exact shell containment ray budget exceeded")

    # Positive material components must be disjoint, not nested.
    outer_triangles = [item["triangles"] for item in outers]
    for index, outer in enumerate(outers):
        representative = outer["solid"].vertices[0]
        for other_index, other in enumerate(outers):
            if index == other_index:
                continue
            witness = classify_rational_point_against_triangles(
                representative, outer_triangles[other_index]
            )
            if witness.classification is not MaterialClassification.OUTSIDE:
                raise InvalidModelError("nested or ambiguous positive rational shells are unsupported")

    cavity_owners: dict[int, list[dict[str, object]]] = {
        index: [] for index in range(len(outers))
    }
    for cavity in cavities:
        representative = cavity["solid"].vertices[0]
        owners = []
        for outer_index, outer in enumerate(outers):
            witness = classify_rational_point_against_triangles(
                representative, outer_triangles[outer_index]
            )
            if witness.classification is MaterialClassification.INSIDE:
                owners.append(outer_index)
            elif witness.classification is not MaterialClassification.OUTSIDE:
                raise InvalidModelError("cavity containment is boundary or UNKNOWN")
        if len(owners) != 1:
            raise InvalidModelError("each rational cavity must be strictly inside exactly one outer shell")
        cavity_owners[owners[0]].append(cavity)

    # Nested cavities are not a valid single-level material subtraction model.
    for index, cavity in enumerate(cavities):
        representative = cavity["solid"].vertices[0]
        for other in cavities[index + 1:]:
            first_state = classify_rational_point_against_triangles(
                representative, other["triangles"]
            ).classification
            second_state = classify_rational_point_against_triangles(
                other["solid"].vertices[0], cavity["triangles"]
            ).classification
            if first_state is not MaterialClassification.OUTSIDE or second_state is not MaterialClassification.OUTSIDE:
                raise InvalidModelError("nested or ambiguous rational cavity shells are unsupported")

    components = []
    for outer_index, outer in enumerate(outers):
        outer_shell = RationalBooleanShell(
            f"outer.{outer['group_index']:04d}", "OUTER", outer["solid"], None
        )
        cavity_shells = tuple(
            RationalBooleanShell(
                f"cavity.{item['group_index']:04d}", "CAVITY", item["solid"],
                outer_shell.shell_id,
            )
            for item in cavity_owners[outer_index]
        )
        components.append(RationalBooleanComponent(
            f"component.{outer_index:04d}", outer_shell, cavity_shells
        ))

    provenance = tuple(sorted({
        (input_meshes[item.source_solid_index].solid_id,
         input_meshes[item.source_solid_index].source_geometry_sha256)
        for item in fragments
    }))
    return RationalBooleanSolid(
        result_id, input_meshes[0].frame_id, input_meshes[0].length_unit,
        tuple(components), provenance, pair_checks, aggregate_bits,
        containment_ray_checks,
    )
