import hashlib
import json

import pytest

from universal_platform.engineering.brep import brep_from_triangle_mesh, validate_brep_solid
from universal_platform.engineering.brep_boolean import (
    BRepBooleanOperation,
    BRepBooleanResult,
    boolean_axis_aligned_brep_solids,
)
from universal_platform.engineering.errors import InvalidModelError
from universal_platform.engineering.geometry import Vec3
from universal_platform.engineering.mesh import TriangleMesh, tessellate_box, validate_triangle_mesh
from universal_platform.engineering.primitive_geometry import BoxSolid


def box_brep(solid_id, minimum, maximum, frame="part.frame", unit="mm"):
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


def total_volume(result):
    return sum(validate_brep_solid(item).signed_volume for item in result.components)


def test_axis_aligned_brep_boolean_union_intersection_difference_and_xor():
    left = box_brep("left", (0, 0, 0), (4, 4, 4))
    right = box_brep("right", (2, 0, 0), (6, 4, 4))
    expected = {
        BRepBooleanOperation.UNION: (96.0, 1),
        BRepBooleanOperation.INTERSECTION: (32.0, 1),
        BRepBooleanOperation.DIFFERENCE: (32.0, 1),
        BRepBooleanOperation.SYMMETRIC_DIFFERENCE: (64.0, 2),
    }
    for operation, (volume, count) in expected.items():
        result = boolean_axis_aligned_brep_solids((left, right), operation)
        assert len(result.components) == count
        assert total_volume(result) == pytest.approx(volume)
        for component in result.components:
            validation = validate_brep_solid(component)
            assert validation.valid and validation.closed and validation.manifold
            assert validation.consistently_oriented and validation.connected


def test_axis_aligned_brep_boolean_preserves_a_through_tunnel_as_genus_one_shell():
    plate = box_brep("plate", (0, 0, 0), (4, 4, 4))
    cutter = box_brep("tunnel", (1, 1, -1), (3, 3, 5))
    result = boolean_axis_aligned_brep_solids((plate, cutter), BRepBooleanOperation.DIFFERENCE)
    assert len(result.components) == 1
    validation = validate_brep_solid(result.components[0])
    assert validation.valid
    assert validation.genus == 1
    assert validation.signed_volume == pytest.approx(48.0)


def test_axis_aligned_brep_boolean_keeps_edge_only_contacts_as_separate_components():
    first = box_brep("first", (0, 0, 0), (1, 1, 1))
    second = box_brep("second", (1, 1, 0), (2, 2, 1))
    result = boolean_axis_aligned_brep_solids((first, second), BRepBooleanOperation.UNION)
    assert len(result.components) == 2
    assert total_volume(result) == pytest.approx(2.0)


def test_axis_aligned_brep_boolean_supports_empty_results_and_deterministic_snapshots():
    first = box_brep("first", (0, 0, 0), (1, 1, 1))
    remote = box_brep("remote", (3, 3, 3), (4, 4, 4))
    empty = boolean_axis_aligned_brep_solids((first, remote), BRepBooleanOperation.INTERSECTION)
    assert empty.components == ()
    assert empty.grid_cell_count > 0
    restored = BRepBooleanResult.from_dict(json.loads(json.dumps(empty.to_dict())))
    assert restored.to_dict() == empty.to_dict()
    union_a = boolean_axis_aligned_brep_solids((first, remote), BRepBooleanOperation.UNION)
    union_b = boolean_axis_aligned_brep_solids((remote, first), BRepBooleanOperation.UNION)
    assert union_a.result_sha256 == union_b.result_sha256


def test_axis_aligned_brep_boolean_rejects_frame_unit_and_non_box_inputs():
    first = box_brep("first", (0, 0, 0), (1, 1, 1))
    other_frame = box_brep("other", (0, 0, 0), (1, 1, 1), frame="world")
    other_unit = box_brep("other-unit", (0, 0, 0), (1, 1, 1), unit="cm")
    with pytest.raises(InvalidModelError, match="same frame and length unit"):
        boolean_axis_aligned_brep_solids((first, other_frame), BRepBooleanOperation.UNION)
    with pytest.raises(InvalidModelError, match="same frame and length unit"):
        boolean_axis_aligned_brep_solids((first, other_unit), BRepBooleanOperation.UNION)

    cylinder = tessellate_box(BoxSolid("other-box", "part.frame", Vec3(2, 2, 2), "mm"))
    non_box = brep_from_triangle_mesh(cylinder)
    # The converted mesh is still a box; alter one vertex to make a valid non-axis-aligned shell.
    moved = tuple(
        Vec3(v.x + (0.125 if i == 0 else 0.0), v.y, v.z)
        for i, v in enumerate(non_box.vertices)
    )
    distorted_mesh = TriangleMesh(
        "distorted", "part.frame", "mm", "BOX",
        hashlib.sha256(b"distorted-box").hexdigest(), moved,
        tuple(tuple(index for index in face) for face in cylinder.triangles),
    )
    distorted = brep_from_triangle_mesh(distorted_mesh)
    with pytest.raises(InvalidModelError, match="axis-aligned box"):
        boolean_axis_aligned_brep_solids((first, distorted), BRepBooleanOperation.UNION)


def test_axis_aligned_brep_boolean_enforces_input_and_grid_limits_and_strict_result_schema():
    first = box_brep("first", (0, 0, 0), (1, 1, 1))
    with pytest.raises(InvalidModelError, match="2..16"):
        boolean_axis_aligned_brep_solids((first,), BRepBooleanOperation.UNION)
    many = tuple(box_brep(f"box-{i}", (0, 0, 0), (1, 1, 1)) for i in range(17))
    with pytest.raises(InvalidModelError, match="2..16"):
        boolean_axis_aligned_brep_solids(many, BRepBooleanOperation.UNION)

    result = boolean_axis_aligned_brep_solids(
        (first, box_brep("second", (0.5, 0, 0), (1.5, 1, 1))),
        BRepBooleanOperation.UNION,
    )
    schema = json.loads((__import__("pathlib").Path(__file__).parents[1] / "schemas" / "geometry" /
                         "brep-boolean-result.schema.json").read_text(encoding="utf-8"))
    assert set(result.to_dict()) == set(schema["required"])
    with pytest.raises(InvalidModelError, match="missing or unknown"):
        BRepBooleanResult.from_dict(dict(result.to_dict(), unexpected=True))
    tampered = dict(result.to_dict())
    tampered["result_sha256"] = "0" * 64
    with pytest.raises(InvalidModelError, match="digest"):
        BRepBooleanResult.from_dict(tampered)


def test_axis_aligned_brep_boolean_public_api_is_exported():
    from universal_platform.engineering import BRepBooleanOperation as PublicOperation
    from universal_platform.engineering import boolean_axis_aligned_brep_solids as public_boolean
    assert PublicOperation is BRepBooleanOperation
    assert public_boolean is boolean_axis_aligned_brep_solids
