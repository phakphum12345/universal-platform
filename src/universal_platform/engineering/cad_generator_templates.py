"""Validated template builders for bounded CAD Generator authoring workflows."""
from __future__ import annotations

from math import isclose, isfinite
import re
from typing import Sequence

from .errors import InvalidModelError
from .feature_history import FeatureHistory, FeatureKind, FeatureNode
from .parametric_sketch import (
    ParametricSketch,
    SketchConstraint,
    SketchConstraintKind,
    SketchPoint,
    SketchSegment,
)

_HISTORY_ID = re.compile(r"^[a-z0-9]+(?:[._/-][a-z0-9]+)*$")
_MAX_POLYGON_POINTS = 64


def build_polygon_extrusion_history(
    history_id: str,
    points: Sequence[Sequence[float]],
    *,
    height: float,
    length_unit: str = "mm",
) -> FeatureHistory:
    """Build a strict fixed-coordinate sketch → extrusion → mesh FeatureHistory.

    This creates a closed straight-edge polygon profile. It does not infer
    constraints, repair self-intersections, or claim a global CAD-kernel solve;
    geometry validation remains part of the normal regeneration pipeline.
    """
    if not isinstance(history_id, str) or not _HISTORY_ID.fullmatch(history_id):
        raise InvalidModelError("history_id must be a stable lowercase identifier")
    if isinstance(height, bool) or not isinstance(height, (int, float)):
        raise InvalidModelError("extrusion height must be numeric")
    if not isfinite(float(height)) or height <= 0:
        raise InvalidModelError("extrusion height must be finite and positive")
    if not isinstance(length_unit, str) or not length_unit.strip():
        raise InvalidModelError("length_unit must be a non-empty length unit")
    if not isinstance(points, (list, tuple)) or not 3 <= len(points) <= _MAX_POLYGON_POINTS:
        raise InvalidModelError(f"polygon requires 3 to {_MAX_POLYGON_POINTS} points")

    coordinates: list[tuple[float, float]] = []
    for index, pair in enumerate(points):
        if not isinstance(pair, (list, tuple)) or len(pair) != 2:
            raise InvalidModelError(f"polygon point {index} must contain exactly x and y")
        x, y = pair
        if any(isinstance(value, bool) or not isinstance(value, (int, float)) for value in (x, y)):
            raise InvalidModelError(f"polygon point {index} coordinates must be numeric")
        x, y = float(x), float(y)
        if not isfinite(x) or not isfinite(y):
            raise InvalidModelError(f"polygon point {index} coordinates must be finite")
        coordinates.append((x, y))

    for index, coordinate in enumerate(coordinates):
        following = coordinates[(index + 1) % len(coordinates)]
        if isclose(coordinate[0], following[0], rel_tol=0.0, abs_tol=1e-12) and isclose(
            coordinate[1], following[1], rel_tol=0.0, abs_tol=1e-12
        ):
            raise InvalidModelError("polygon contains duplicate adjacent vertices or a repeated closing point")
    unique = set(coordinates)
    if len(unique) != len(coordinates):
        raise InvalidModelError("polygon vertices must be unique")
    twice_area = sum(
        coordinates[index][0] * coordinates[(index + 1) % len(coordinates)][1]
        - coordinates[(index + 1) % len(coordinates)][0] * coordinates[index][1]
        for index in range(len(coordinates))
    )
    if not isfinite(twice_area) or abs(twice_area) <= 1e-12:
        raise InvalidModelError("polygon signed area must be non-zero")

    point_ids = tuple(f"p{index}" for index in range(len(coordinates)))
    sketch_points = tuple(
        SketchPoint(point_id, x, y)
        for point_id, (x, y) in zip(point_ids, coordinates)
    )
    segments = tuple(
        SketchSegment(f"edge.{index}", point_ids[index], point_ids[(index + 1) % len(point_ids)])
        for index in range(len(point_ids))
    )
    constraints = tuple(
        constraint
        for point_id, (x, y) in zip(point_ids, coordinates)
        for constraint in (
            SketchConstraint(
                f"fix-x.{point_id}", SketchConstraintKind.FIX_X, (point_id,), x
            ),
            SketchConstraint(
                f"fix-y.{point_id}", SketchConstraintKind.FIX_Y, (point_id,), y
            ),
        )
    )
    sketch = ParametricSketch(
        "sketch.profile", "part.xy", length_unit,
        sketch_points, segments, constraints, (),
    )
    return FeatureHistory(
        history_id,
        (
            FeatureNode.create(
                "profile", FeatureKind.SKETCH_PROFILE, (),
                {"sketch": sketch.to_dict()},
            ),
            FeatureNode.create(
                "extrusion", FeatureKind.EXTRUSION, ("profile",),
                {"solid_id": "solid.generated", "height": float(height)},
            ),
            FeatureNode.create("mesh", FeatureKind.MESH, ("extrusion",)),
        ),
        ("mesh",),
    )


__all__ = ["build_polygon_extrusion_history"]
