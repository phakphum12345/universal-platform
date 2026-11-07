import json
from math import pi
from pathlib import Path

import pytest

from universal_platform.engineering.errors import InvalidModelError, SolverError
from universal_platform.engineering.nonlinear_solver import NonlinearSolveStatus
from universal_platform.engineering.parametric_sketch import (
    ParametricSketch,
    SketchConstraint,
    SketchConstraintKind as Kind,
    SketchPoint,
    SketchSegment,
    solve_parametric_sketch,
)


def rectangle_sketch():
    return ParametricSketch(
        "sketch.rectangle", "part.xy", "mm",
        (
            SketchPoint("p0", 0.2, 0.3),
            SketchPoint("p1", 4.1, 0.1),
            SketchPoint("p2", 3.9, 3.2),
            SketchPoint("p3", -0.1, 3.1),
        ),
        (
            SketchSegment("e0", "p0", "p1"),
            SketchSegment("e1", "p1", "p2"),
            SketchSegment("e2", "p2", "p3"),
            SketchSegment("e3", "p3", "p0"),
        ),
        (
            SketchConstraint("anchor-x", Kind.FIX_X, ("p0",), 0.0),
            SketchConstraint("anchor-y", Kind.FIX_Y, ("p0",), 0.0),
            SketchConstraint("bottom-horizontal", Kind.HORIZONTAL, ("p0", "p1")),
            SketchConstraint("width", Kind.HORIZONTAL_DISTANCE, ("p0", "p1"), 4.0),
            SketchConstraint("right-vertical", Kind.VERTICAL, ("p1", "p2")),
            SketchConstraint("height", Kind.VERTICAL_DISTANCE, ("p1", "p2"), 3.0),
            SketchConstraint("top-horizontal", Kind.HORIZONTAL, ("p2", "p3")),
            SketchConstraint("left-vertical", Kind.VERTICAL, ("p3", "p0")),
        ),
    )


def test_parametric_sketch_solves_dimensioned_rectangle_from_rough_initial_guess():
    result = solve_parametric_sketch(rectangle_sketch())
    assert result.solver.status is NonlinearSolveStatus.CONVERGED
    assert result.converged
    points = {point.point_id: point for point in result.points}
    assert (points["p0"].x, points["p0"].y) == pytest.approx((0.0, 0.0), abs=1e-7)
    assert (points["p1"].x, points["p1"].y) == pytest.approx((4.0, 0.0), abs=1e-7)
    assert (points["p2"].x, points["p2"].y) == pytest.approx((4.0, 3.0), abs=1e-7)
    assert (points["p3"].x, points["p3"].y) == pytest.approx((0.0, 3.0), abs=1e-7)
    assert result.frame_id == "part.xy" and result.length_unit == "mm"


def test_coincident_constraint_contributes_two_coordinate_equations():
    sketch = ParametricSketch(
        "coincident", "plane", "mm",
        (SketchPoint("a", 0.0, 0.0), SketchPoint("b", 1.0, -2.0)),
        constraints=(
            SketchConstraint("same", Kind.COINCIDENT, ("a", "b")),
            SketchConstraint("fix-x", Kind.FIX_X, ("a",), 0.0),
            SketchConstraint("fix-y", Kind.FIX_Y, ("a",), 0.0),
            SketchConstraint("fix-b-x", Kind.FIX_X, ("b",), 0.0),
            SketchConstraint("fix-b-y", Kind.FIX_Y, ("b",), 0.0),
        ),
    )
    result = solve_parametric_sketch(sketch)
    assert result.converged
    assert result.points[0].x == pytest.approx(result.points[1].x, abs=1e-8)
    assert result.points[0].y == pytest.approx(result.points[1].y, abs=1e-8)


def test_distance_constraint_solves_euclidean_length():
    sketch = ParametricSketch(
        "distance", "plane", "mm",
        (SketchPoint("a", 0.0, 0.0), SketchPoint("b", 2.2, 1.8)),
        constraints=(
            SketchConstraint("anchor-x", Kind.FIX_X, ("a",), 0.0),
            SketchConstraint("anchor-y", Kind.FIX_Y, ("a",), 0.0),
            SketchConstraint("fix-b-y", Kind.FIX_Y, ("b",), 0.0),
            SketchConstraint("length", Kind.DISTANCE, ("a", "b"), 5.0),
        ),
    )
    result = solve_parametric_sketch(sketch)
    assert result.converged
    assert result.points[1].x == pytest.approx(5.0, abs=1e-7)
    assert result.points[1].y == pytest.approx(0.0, abs=1e-7)


def test_sketch_snapshot_is_deterministic_and_records_solver_limitations():
    result = solve_parametric_sketch(rectangle_sketch())
    snapshot = result.to_dict()
    assert json.loads(json.dumps(snapshot, sort_keys=True))["schema_version"] == "1.0"
    assert result.to_dict() == snapshot
    assert snapshot["converged"] is True
    assert any("uniqueness" in item for item in snapshot["limitations"])
    assert set(snapshot) == {
        "schema_version", "sketch_id", "frame_id", "length_unit",
        "points", "solver", "converged", "limitations",
    }


def test_sketch_schema_is_strict_and_matches_serialized_top_level_contract():
    schema = json.loads((Path(__file__).parents[1] / "schemas" / "geometry" /
                         "parametric-sketch.schema.json").read_text(encoding="utf-8"))
    snapshot = rectangle_sketch().to_dict()
    assert set(snapshot) == set(schema["required"])
    assert schema["additionalProperties"] is False
    assert schema["properties"]["schema_version"]["enum"] == ["1.0", "1.1"]


def test_sketch_rejects_duplicate_ids_and_dangling_segment_or_constraint_references():
    with pytest.raises(InvalidModelError, match="point identifiers must be unique"):
        ParametricSketch("bad", "plane", "mm",
                         (SketchPoint("p", 0, 0), SketchPoint("p", 1, 1)))
    with pytest.raises(InvalidModelError, match="unknown point"):
        ParametricSketch("bad", "plane", "mm", (SketchPoint("p", 0, 0),),
                         (SketchSegment("edge", "p", "missing"),))
    with pytest.raises(InvalidModelError, match="unknown point"):
        ParametricSketch("bad", "plane", "mm", (SketchPoint("p", 0, 0),),
                         constraints=(SketchConstraint("c", Kind.FIX_X, ("missing",), 0),))


def test_sketch_rejects_invalid_constraint_arity_values_and_tolerances():
    with pytest.raises(InvalidModelError, match="requires 2"):
        SketchConstraint("bad", Kind.HORIZONTAL, ("p",))
    with pytest.raises(InvalidModelError, match="required only"):
        SketchConstraint("bad", Kind.HORIZONTAL, ("a", "b"), 2.0)
    with pytest.raises(InvalidModelError, match="non-negative"):
        SketchConstraint("bad", Kind.DISTANCE, ("a", "b"), -1.0)
    with pytest.raises(InvalidModelError, match="finite and positive"):
        SketchConstraint("bad", Kind.FIX_X, ("a",), 0.0, 0.0)


def test_sketch_requires_constraints_and_rejects_wrong_input_type():
    empty = ParametricSketch("empty", "plane", "mm", (SketchPoint("p", 0, 0),))
    with pytest.raises(SolverError, match="at least one supported constraint"):
        solve_parametric_sketch(empty)
    with pytest.raises(InvalidModelError, match="requires a ParametricSketch"):
        solve_parametric_sketch(object())


def test_sketch_segment_endpoints_must_be_distinct_and_references_must_exist():
    with pytest.raises(InvalidModelError, match="must be distinct"):
        SketchSegment("bad", "p", "p")



@pytest.mark.parametrize(
    "kind,coordinates",
    [
        (Kind.PARALLEL, ((0.0, 0.0), (2.0, 0.0), (0.0, 1.0), (3.0, 1.0))),
        (Kind.PERPENDICULAR, ((0.0, 0.0), (2.0, 0.0), (1.0, 1.0), (1.0, 4.0))),
        (Kind.EQUAL_LENGTH, ((0.0, 0.0), (2.0, 0.0), (0.0, 1.0), (0.0, 3.0))),
    ],
)
def test_relational_segment_constraints_accept_valid_geometry(kind, coordinates):
    points = tuple(SketchPoint(f"p{i}", x, y) for i, (x, y) in enumerate(coordinates))
    constraints = [SketchConstraint("relation", kind, ("p0", "p1", "p2", "p3"))]
    for i, (x, y) in enumerate(coordinates):
        constraints.extend((
            SketchConstraint(f"fix-x-{i}", Kind.FIX_X, (f"p{i}",), x),
            SketchConstraint(f"fix-y-{i}", Kind.FIX_Y, (f"p{i}",), y),
        ))
    sketch = ParametricSketch("relations", "plane", "mm", points, constraints=tuple(constraints))
    result = solve_parametric_sketch(sketch)
    assert result.converged


def test_relational_segment_constraints_require_four_distinct_points_and_no_zero_length_segments():
    with pytest.raises(InvalidModelError, match="requires 4"):
        SketchConstraint("parallel", Kind.PARALLEL, ("a", "b"))
    with pytest.raises(InvalidModelError, match="cannot repeat a point"):
        SketchConstraint("parallel", Kind.PARALLEL, ("a", "b", "a", "d"))
    sketch = ParametricSketch(
        "degenerate-relations", "plane", "mm",
        (SketchPoint("a", 0, 0), SketchPoint("b", 0, 0),
         SketchPoint("c", 0, 1), SketchPoint("d", 1, 1)),
        constraints=(SketchConstraint("parallel", Kind.PARALLEL, ("a", "b", "c", "d")),),
    )
    with pytest.raises(InvalidModelError, match="non-degenerate"):
        solve_parametric_sketch(sketch)


@pytest.mark.parametrize(("target", "expected_y"), [(pi / 4, 5.0), (-pi / 4, -1.0)])
def test_angle_constraint_solves_signed_directed_angle_between_named_segments(target, expected_y):
    sketch = ParametricSketch(
        "angle.sketch", "part.xy", "mm",
        (
            SketchPoint("a", 0.0, 0.0),
            SketchPoint("b", 2.0, 0.0),
            SketchPoint("c", 0.0, 2.0),
            SketchPoint("d", 3.0, 4.0),
        ),
        (
            SketchSegment("base", "a", "b"),
            SketchSegment("arm", "c", "d"),
        ),
        (
            SketchConstraint("a-x", Kind.FIX_X, ("a",), 0.0),
            SketchConstraint("a-y", Kind.FIX_Y, ("a",), 0.0),
            SketchConstraint("b-x", Kind.FIX_X, ("b",), 2.0),
            SketchConstraint("b-y", Kind.FIX_Y, ("b",), 0.0),
            SketchConstraint("c-x", Kind.FIX_X, ("c",), 0.0),
            SketchConstraint("c-y", Kind.FIX_Y, ("c",), 2.0),
            SketchConstraint("d-x", Kind.FIX_X, ("d",), 3.0),
            SketchConstraint("directed-angle", Kind.ANGLE, (), target,
                             segment_ids=("base", "arm")),
        ),
    )

    result = solve_parametric_sketch(sketch)
    points = {point.point_id: point for point in result.points}

    assert result.converged
    assert points["d"].y == pytest.approx(expected_y, abs=1e-7)
    assert sketch.to_dict()["schema_version"] == "1.1"
    angle_snapshot = next(item for item in sketch.to_dict()["constraints"]
                          if item["constraint_id"] == "directed-angle")
    assert angle_snapshot["segment_ids"] == ["base", "arm"]


def test_angle_constraint_rejects_missing_or_repeated_segment_references():
    with pytest.raises(InvalidModelError, match="requires 2 distinct segment"):
        SketchConstraint("bad", Kind.ANGLE, (), pi / 2, segment_ids=("one",))
    with pytest.raises(InvalidModelError, match="requires 2 distinct segment"):
        SketchConstraint("bad", Kind.ANGLE, (), pi / 2, segment_ids=("one", "one"))

    with pytest.raises(InvalidModelError, match="unknown segment"):
        ParametricSketch(
            "bad.angle", "plane", "mm",
            (SketchPoint("a", 0, 0), SketchPoint("b", 1, 0)),
            (SketchSegment("known", "a", "b"),),
            (SketchConstraint("angle", Kind.ANGLE, (), pi / 2,
                              segment_ids=("known", "missing")),),
        )


def test_angle_constraint_rejects_degenerate_segments_and_out_of_range_angles():
    with pytest.raises(InvalidModelError, match="within"):
        SketchConstraint("bad-angle", Kind.ANGLE, (), 4 * pi,
                         segment_ids=("first", "second"))
    sketch = ParametricSketch(
        "degenerate.angle", "plane", "mm",
        (SketchPoint("a", 0, 0), SketchPoint("b", 0, 0),
         SketchPoint("c", 0, 1), SketchPoint("d", 1, 1)),
        (SketchSegment("first", "a", "b"), SketchSegment("second", "c", "d")),
        (SketchConstraint("angle", Kind.ANGLE, (), pi / 2,
                          segment_ids=("first", "second")),),
    )
    with pytest.raises(InvalidModelError, match="non-degenerate"):
        solve_parametric_sketch(sketch)


def test_parametric_sketch_v1_0_snapshot_remains_readable_after_v1_1_extension():
    original = rectangle_sketch()
    legacy = original.to_dict()
    legacy["schema_version"] = "1.0"

    restored = ParametricSketch.from_dict(legacy)

    assert restored == original
    assert restored.to_dict()["schema_version"] == "1.1"
