import pytest

from universal_platform.engineering.errors import InvalidModelError
from universal_platform.engineering.parametric_sketch import (
    ParametricSketch, SketchConstraint, SketchConstraintKind as Kind,
    SketchPoint, SketchSegment, solve_parametric_sketch,
)
from universal_platform.engineering.sketch_region import sketch_to_planar_regions


def make_sketch(loop_coords, sketch_id="profile", *, frame="part.xy", unit="mm"):
    points = []
    segments = []
    constraints = []
    for loop_index, coords in enumerate(loop_coords):
        ids = [f"p{loop_index}.{index}" for index in range(len(coords))]
        for point_id, (x, y) in zip(ids, coords):
            points.append(SketchPoint(point_id, x, y))
            constraints.extend((
                SketchConstraint(f"fix-x.{point_id}", Kind.FIX_X, (point_id,), x),
                SketchConstraint(f"fix-y.{point_id}", Kind.FIX_Y, (point_id,), y),
            ))
        for index, point_id in enumerate(ids):
            segments.append(SketchSegment(
                f"edge.{loop_index}.{index}", point_id, ids[(index + 1) % len(ids)]
            ))
    return ParametricSketch(sketch_id, frame, unit, tuple(points), tuple(segments), tuple(constraints))


def solve(sketch):
    return solve_parametric_sketch(sketch)


def test_closed_sketch_loop_converts_to_canonical_planar_region():
    sketch = make_sketch([[(0, 0), (8, 0), (8, 6), (0, 6)]])
    result = sketch_to_planar_regions(sketch, solve(sketch))
    assert len(result.regions) == 1
    region = result.regions[0]
    assert region.area == 48.0
    assert region.frame_id == sketch.frame_id
    assert region.length_unit == sketch.length_unit
    assert region.outer_boundary[0].x == 0.0
    assert region.outer_boundary[0].y == 0.0
    assert len(result.source_sketch_sha256) == 64


def test_disconnected_closed_loops_produce_deterministically_ordered_regions():
    sketch = make_sketch([
        [(10, 0), (12, 0), (12, 2), (10, 2)],
        [(0, 0), (3, 0), (3, 3), (0, 3)],
    ])
    first = sketch_to_planar_regions(sketch, solve(sketch))
    second = sketch_to_planar_regions(sketch, solve(sketch))
    assert [item.to_dict() for item in first.regions] == [item.to_dict() for item in second.regions]
    assert sorted(item.area for item in first.regions) == [4.0, 9.0]
    assert first.source_sketch_sha256 == second.source_sketch_sha256


def test_nested_loops_become_outer_with_hole_and_separate_island():
    sketch = make_sketch([
        [(0, 0), (10, 0), (10, 10), (0, 10)],
        [(2, 2), (8, 2), (8, 8), (2, 8)],
        [(4, 4), (6, 4), (6, 6), (4, 6)],
    ])
    result = sketch_to_planar_regions(sketch, solve(sketch))
    assert len(result.regions) == 2
    assert sorted(region.area for region in result.regions) == [4.0, 64.0]
    assert sorted(len(region.holes) for region in result.regions) == [0, 1]


def test_open_or_branching_sketch_topology_fails_closed():
    open_sketch = ParametricSketch(
        "open", "plane", "mm",
        (SketchPoint("a", 0, 0), SketchPoint("b", 1, 0), SketchPoint("c", 1, 1)),
        (SketchSegment("ab", "a", "b"), SketchSegment("bc", "b", "c")),
        (SketchConstraint("fix-a-x", Kind.FIX_X, ("a",), 0),
         SketchConstraint("fix-a-y", Kind.FIX_Y, ("a",), 0)),
    )
    with pytest.raises(InvalidModelError, match="degree 2"):
        sketch_to_planar_regions(open_sketch, solve(open_sketch))


def test_self_intersecting_or_touching_loops_fail_closed():
    bowtie = make_sketch([[(0, 0), (2, 2), (0, 2), (2, 0)]], "bowtie")
    with pytest.raises(InvalidModelError):
        sketch_to_planar_regions(bowtie, solve(bowtie))
    touching = make_sketch([
        [(0, 0), (2, 0), (2, 2), (0, 2)],
        [(2, 2), (4, 2), (4, 4), (2, 4)],
    ], "touching")
    with pytest.raises(InvalidModelError, match="touch or cross"):
        sketch_to_planar_regions(touching, solve(touching))


def test_duplicate_undirected_segments_and_solved_result_mismatch_are_rejected():
    sketch = make_sketch([[(0, 0), (2, 0), (2, 2), (0, 2)]])
    duplicate = ParametricSketch(
        sketch.sketch_id, sketch.frame_id, sketch.length_unit, sketch.points,
        sketch.segments + (SketchSegment("duplicate", "p0.1", "p0.0"),),
        sketch.constraints,
    )
    with pytest.raises(InvalidModelError, match="duplicate undirected"):
        sketch_to_planar_regions(duplicate, solve(duplicate))
    other = make_sketch([[(0, 0), (2, 0), (2, 2), (0, 2)]], "other")
    with pytest.raises(InvalidModelError, match="identity, frame and unit"):
        sketch_to_planar_regions(sketch, solve(other))


def test_unconverged_sketch_cannot_be_converted_to_manufacturable_region():
    sketch = make_sketch([[(0, 0), (2, 0), (2, 2), (0, 2)]])
    from universal_platform.engineering.parametric_sketch import ParametricSketchSolveResult
    from universal_platform.engineering.nonlinear_solver import (
        NonlinearConstraintResidual, NonlinearSolveResult, NonlinearSolveStatus,
    )
    invalid_solver = NonlinearSolveResult(
        NonlinearSolveStatus.NOT_CONVERGED, (), 
        (NonlinearConstraintResidual("bad", 1.0, 1e-8, "FAIL"),),
        1, 0.5, "inconsistent",
    )
    invalid = ParametricSketchSolveResult(
        sketch.sketch_id, sketch.frame_id, sketch.length_unit, sketch.points, invalid_solver
    )
    with pytest.raises(InvalidModelError, match="did not converge"):
        sketch_to_planar_regions(sketch, invalid)
