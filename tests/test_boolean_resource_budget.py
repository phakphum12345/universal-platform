from fractions import Fraction
from hashlib import sha256

import pytest

from universal_platform.engineering.boolean_boundary_selection import select_boolean_boundary_fragments
from universal_platform.engineering.boolean_resource_budget import BooleanResourceLedger
from universal_platform.engineering.boolean_shell_assembly import assemble_rational_boolean_solid
from universal_platform.engineering.brep_boolean import BRepBooleanOperation
from universal_platform.engineering.errors import InvalidModelError
from universal_platform.engineering.faceted_boolean_arrangement import arrange_faceted_boolean_meshes
from universal_platform.engineering.geometry import Vec3
from universal_platform.engineering.mesh import TriangleMesh, tessellate_box
from universal_platform.engineering.primitive_geometry import BoxSolid
from universal_platform.engineering.triangle_fragment_arrangement import RationalTriangleFragment


def _box(solid_id, size, offset=(0.0, 0.0, 0.0)):
    source = tessellate_box(BoxSolid(solid_id, "world", Vec3(size, size, size)))
    vertices = tuple(
        Vec3(v.x + offset[0], v.y + offset[1], v.z + offset[2])
        for v in source.vertices
    )
    digest = sha256(f"{solid_id}:{size}:{offset}".encode()).hexdigest()
    return TriangleMesh(
        solid_id, "world", "m", "BOX", digest, vertices, source.triangles,
    )


def _fragments(mesh):
    result = []
    for face_index, face in enumerate(mesh.triangles):
        points = tuple(
            tuple(Fraction.from_float(value) for value in (
                mesh.vertices[index].x,
                mesh.vertices[index].y,
                mesh.vertices[index].z,
            ))
            for index in face
        )
        result.append(RationalTriangleFragment(face_index, (), points))
    return tuple(result)


def test_ledger_charges_cumulatively_and_does_not_commit_failed_charge():
    ledger = BooleanResourceLedger({"coverage_checks": 3})
    ledger.charge("coverage_checks", 2)
    with pytest.raises(InvalidModelError, match="invocation resource budget exceeded"):
        ledger.charge("coverage_checks", 2)
    assert dict(ledger.usage)["coverage_checks"] == 2
    assert ledger.usage == tuple(sorted(ledger.usage))


def test_ledger_rejects_boolean_limits_and_unknown_dimensions():
    with pytest.raises(InvalidModelError, match="positive integer"):
        BooleanResourceLedger({"coverage_checks": True})
    with pytest.raises(InvalidModelError, match="unknown Boolean resource dimension"):
        BooleanResourceLedger({"unmetered_work": 10})


def test_shared_ledger_exhaustion_between_arrangement_and_selection():
    meshes = (_box("a", 2.0), _box("b", 2.0, (1.0, 1.0, 1.0)))

    probe = BooleanResourceLedger()
    arrange_faceted_boolean_meshes(meshes, resource_ledger=probe)
    arrangement_coverage = dict(probe.usage)["coverage_checks"]
    assert arrangement_coverage > 0

    ledger = BooleanResourceLedger({"coverage_checks": arrangement_coverage})
    arrangement = arrange_faceted_boolean_meshes(meshes, resource_ledger=ledger)
    assert dict(ledger.usage)["coverage_checks"] == arrangement_coverage

    # Arrangement consumed the complete invocation allowance. Selection has
    # additional independent-coverage work and must fail before returning a
    # partial BooleanBoundarySelection.
    with pytest.raises(
        InvalidModelError,
        match="invocation resource budget exceeded for coverage_checks",
    ):
        select_boolean_boundary_fragments(
            meshes, arrangement.fragments_by_solid,
            BRepBooleanOperation.UNION, resource_ledger=ledger,
        )
    assert dict(ledger.usage)["coverage_checks"] == arrangement_coverage


def test_rational_shell_assembly_charges_shared_face_budget_before_output():
    meshes = (_box("outer", 4.0), _box("inner", 2.0, (1.0, 1.0, 1.0)))
    fragments = tuple(_fragments(mesh) for mesh in meshes)
    selection = select_boolean_boundary_fragments(
        meshes, fragments, BRepBooleanOperation.DIFFERENCE,
    )
    ledger = BooleanResourceLedger({"faces": 1})
    with pytest.raises(
        InvalidModelError,
        match="invocation resource budget exceeded for faces",
    ):
        assemble_rational_boolean_solid(
            selection, meshes, resource_ledger=ledger,
        )
    assert dict(ledger.usage)["faces"] == 0
