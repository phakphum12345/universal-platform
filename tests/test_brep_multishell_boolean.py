import hashlib
import json
from math import cos, pi, sin

import pytest

from universal_platform.engineering import (
    BRepBooleanOperation,
    BRepMultiShellBooleanResult,
    BRepMultiShellSolid,
    boolean_axis_aligned_multishell_solids,
    validate_brep_multishell_solid,
)
from universal_platform.engineering.brep import brep_from_triangle_mesh
from universal_platform.engineering.errors import InvalidModelError
from universal_platform.engineering.geometry import Vec3
from universal_platform.engineering.mesh import TriangleMesh, tessellate_box, validate_triangle_mesh
from universal_platform.engineering.primitive_geometry import BoxSolid


def box_brep(solid_id, minimum, maximum, *, frame="part.frame", unit="mm"):
    dimensions = Vec3(
        maximum[0] - minimum[0],
        maximum[1] - minimum[1],
        maximum[2] - minimum[2],
    )
    source = BoxSolid(solid_id, frame, dimensions, unit)
    mesh = tessellate_box(source)
    vertices = tuple(
        Vec3(v.x + minimum[0], v.y + minimum[1], v.z + minimum[2])
        for v in mesh.vertices
    )
    digest = hashlib.sha256(json.dumps(
        {"solid_id": solid_id, "minimum": minimum, "maximum": maximum, "unit": unit},
        sort_keys=True, separators=(",", ":"),
    ).encode()).hexdigest()
    translated = TriangleMesh(
        solid_id, frame, unit, "BOX", digest, vertices, mesh.triangles
    )
    return brep_from_triangle_mesh(translated)




def rotated_box_brep(solid_id, *, center=(5.0, 5.0, 5.0), angle=pi / 4):
    source = tessellate_box(BoxSolid(solid_id, "part.frame", Vec3(2, 2, 2), "mm"))
    c, s = cos(angle), sin(angle)
    vertices = tuple(
        Vec3(
            center[0] + (point.x - 1.0) * c - (point.y - 1.0) * s,
            center[1] + (point.x - 1.0) * s + (point.y - 1.0) * c,
            center[2] + point.z - 1.0,
        )
        for point in source.vertices
    )
    digest = hashlib.sha256(f"{solid_id}:{center}:{angle}".encode()).hexdigest()
    rotated = TriangleMesh(
        solid_id, "part.frame", "mm", "BOX", digest, vertices, source.triangles
    )
    return brep_from_triangle_mesh(rotated)


def multishell_box(solid_id, minimum, maximum, *, cavities=(), frame="part.frame", unit="mm"):
    outer = box_brep(f"{solid_id}.outer", minimum, maximum, frame=frame, unit=unit)
    cavity_solids = tuple(
        box_brep(f"{solid_id}.cavity.{index}", cavity_min, cavity_max, frame=frame, unit=unit)
        for index, (cavity_min, cavity_max) in enumerate(cavities)
    )
    return BRepMultiShellSolid(solid_id, outer, cavity_solids)


def net_volume(result):
    return sum(validate_brep_multishell_solid(item).net_signed_volume for item in result.components)


def test_multishell_boolean_difference_emits_one_outer_shell_and_one_cavity():
    outer = multishell_box("outer", (0, 0, 0), (10, 10, 10))
    cutter = multishell_box("cutter", (2, 2, 2), (4, 4, 4))
    result = boolean_axis_aligned_multishell_solids(
        (outer, cutter), BRepBooleanOperation.DIFFERENCE
    )

    assert len(result.components) == 1
    component = result.components[0]
    validation = validate_brep_multishell_solid(component)
    mesh_validation = validate_triangle_mesh(component.to_mesh())
    assert validation.valid
    assert validation.shell_count == 2
    assert validation.cavity_count == 1
    assert validation.net_signed_volume == pytest.approx(992.0)
    assert mesh_validation.valid and mesh_validation.watertight
    assert mesh_validation.consistently_oriented
    assert mesh_validation.signed_volume == pytest.approx(992.0)


def test_multishell_boolean_difference_emits_multiple_disjoint_cavities():
    outer = multishell_box("outer", (0, 0, 0), (10, 10, 10))
    small = multishell_box("small", (1, 1, 1), (2, 2, 2))
    large = multishell_box("large", (7, 7, 7), (9, 9, 9))
    result = boolean_axis_aligned_multishell_solids(
        (outer, small, large), BRepBooleanOperation.DIFFERENCE
    )
    assert len(result.components) == 1
    assert result.components[0].cavity_shells and len(result.components[0].cavity_shells) == 2
    assert net_volume(result) == pytest.approx(991.0)


def test_multishell_boolean_intersection_preserves_existing_cavity():
    hollow = multishell_box(
        "hollow", (0, 0, 0), (10, 10, 10),
        cavities=(((2, 2, 2), (4, 4, 4)),),
    )
    clip = multishell_box("clip", (1, 1, 1), (9, 9, 9))
    result = boolean_axis_aligned_multishell_solids(
        (hollow, clip), BRepBooleanOperation.INTERSECTION
    )
    assert len(result.components) == 1
    assert len(result.components[0].cavity_shells) == 1
    assert net_volume(result) == pytest.approx(504.0)


def test_multishell_boolean_union_keeps_disconnected_material_regions_and_is_deterministic():
    first = multishell_box("first", (0, 0, 0), (1, 1, 1))
    second = multishell_box("second", (3, 3, 3), (4, 4, 4))
    a = boolean_axis_aligned_multishell_solids((first, second), BRepBooleanOperation.UNION)
    b = boolean_axis_aligned_multishell_solids((second, first), BRepBooleanOperation.UNION)
    assert len(a.components) == 2
    assert net_volume(a) == pytest.approx(2.0)
    assert a.result_sha256 == b.result_sha256
    assert [item.to_dict() for item in a.components] == [item.to_dict() for item in b.components]


def test_multishell_boolean_empty_intersection_and_snapshot_round_trip():
    first = multishell_box("first", (0, 0, 0), (1, 1, 1))
    remote = multishell_box("remote", (3, 3, 3), (4, 4, 4))
    empty = boolean_axis_aligned_multishell_solids(
        (first, remote), BRepBooleanOperation.INTERSECTION
    )
    assert empty.components == ()
    assert empty.grid_cell_count > 0
    restored = BRepMultiShellBooleanResult.from_dict(json.loads(json.dumps(empty.to_dict())))
    assert restored.to_dict() == empty.to_dict()

    nonempty = boolean_axis_aligned_multishell_solids(
        (first, remote), BRepBooleanOperation.UNION
    )
    restored_nonempty = BRepMultiShellBooleanResult.from_dict(
        json.loads(json.dumps(nonempty.to_dict()))
    )
    assert restored_nonempty.to_dict() == nonempty.to_dict()
    tampered = dict(nonempty.to_dict())
    tampered["result_sha256"] = "0" * 64
    with pytest.raises(InvalidModelError, match="digest"):
        BRepMultiShellBooleanResult.from_dict(tampered)
    with pytest.raises(InvalidModelError, match="missing or unknown"):
        BRepMultiShellBooleanResult.from_dict(dict(nonempty.to_dict(), unexpected=True))


def test_multishell_boolean_rejects_non_box_cavity_components_and_frame_unit_mismatch():
    outer = multishell_box("outer", (0, 0, 0), (10, 10, 10))
    wrong_frame = multishell_box("wrong-frame", (0, 0, 0), (1, 1, 1), frame="world")
    wrong_unit = multishell_box("wrong-unit", (0, 0, 0), (1, 1, 1), unit="cm")
    with pytest.raises(InvalidModelError, match="same frame and length unit"):
        boolean_axis_aligned_multishell_solids((outer, wrong_frame), BRepBooleanOperation.UNION)
    with pytest.raises(InvalidModelError, match="same frame and length unit"):
        boolean_axis_aligned_multishell_solids((outer, wrong_unit), BRepBooleanOperation.UNION)

    rotated_cavity = rotated_box_brep("rotated-cavity")
    bad = BRepMultiShellSolid("bad-input", outer.outer_shell, (rotated_cavity,))
    with pytest.raises(InvalidModelError, match="axis-aligned box"):
        boolean_axis_aligned_multishell_solids((bad, first), BRepBooleanOperation.UNION)


def test_multishell_boolean_enforces_input_limit_and_public_schema_contract():
    first = multishell_box("first", (0, 0, 0), (1, 1, 1))
    with pytest.raises(InvalidModelError, match="2..16"):
        boolean_axis_aligned_multishell_solids((first,), BRepBooleanOperation.UNION)
    many = tuple(multishell_box(f"box-{i}", (0, 0, 0), (1, 1, 1)) for i in range(17))
    with pytest.raises(InvalidModelError, match="2..16"):
        boolean_axis_aligned_multishell_solids(many, BRepBooleanOperation.UNION)

    result = boolean_axis_aligned_multishell_solids(
        (first, multishell_box("second", (2, 0, 0), (3, 1, 1))),
        BRepBooleanOperation.UNION,
    )
    schema = json.loads((__import__("pathlib").Path(__file__).parents[1] / "schemas" / "geometry" /
                         "brep-multishell-boolean-result.schema.json").read_text(encoding="utf-8"))
    assert set(result.to_dict()) == set(schema["required"])
    from universal_platform.engineering import (
        BRepMultiShellBooleanResult as PublicResult,
        boolean_axis_aligned_multishell_solids as public_boolean,
    )
    assert PublicResult is BRepMultiShellBooleanResult
    assert public_boolean is boolean_axis_aligned_multishell_solids
