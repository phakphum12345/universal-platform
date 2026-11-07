import pytest

from universal_platform.engineering import (
    FeatureKind,
    build_polygon_extrusion_history,
    regenerate_feature_history,
)
from universal_platform.engineering.errors import InvalidModelError


SQUARE = ((0.0, 0.0), (12.0, 0.0), (12.0, 8.0), (0.0, 8.0))


def test_polygon_template_builds_fixed_sketch_extrusion_and_watertight_mesh():
    history = build_polygon_extrusion_history(
        "history.visual-profile", SQUARE, height=4.0, length_unit="mm"
    )
    assert history.history_id == "history.visual-profile"
    assert history.output_feature_ids == ("mesh",)
    assert tuple(node.kind for node in history.nodes) == (
        FeatureKind.SKETCH_PROFILE, FeatureKind.EXTRUSION, FeatureKind.MESH
    )
    sketch = history.nodes[0].parameters["sketch"]
    assert sketch["schema_version"] == "1.2"
    assert len(sketch["points"]) == 4
    assert len(sketch["segments"]) == 4
    assert len(sketch["constraints"]) == 8
    assert sketch["arcs"] == []

    result = regenerate_feature_history(history)
    assert result.successful
    mesh = result.artifacts[-1].to_dict()["payload"]
    assert mesh["validation"]["valid"] is True
    assert mesh["validation"]["watertight"] is True
    assert mesh["validation"]["consistently_oriented"] is True


@pytest.mark.parametrize(
    "points",
    [
        ((0.0, 0.0), (1.0, 0.0)),
        ((0.0, 0.0), (1.0, 0.0), (0.0, 0.0)),
        ((0.0, 0.0), (2.0, 2.0), (0.0, 2.0), (2.0, 0.0)),
        ((0.0, 0.0), (1.0, 0.0), (1.0, 0.0), (0.0, 1.0)),
    ],
)
def test_polygon_template_rejects_insufficient_duplicate_or_zero_area_points(points):
    with pytest.raises(InvalidModelError):
        build_polygon_extrusion_history("history.invalid", points, height=2.0)


def test_polygon_template_rejects_invalid_height_units_ids_and_point_values():
    with pytest.raises(InvalidModelError, match="height"):
        build_polygon_extrusion_history("history.invalid", SQUARE, height=0.0)
    with pytest.raises(InvalidModelError, match="history_id"):
        build_polygon_extrusion_history("History.Invalid", SQUARE, height=2.0)
    with pytest.raises(InvalidModelError, match="coordinates must be finite"):
        build_polygon_extrusion_history(
            "history.invalid", ((0.0, 0.0), (1.0, 0.0), (0.0, float("inf"))), height=2.0
        )
    with pytest.raises(InvalidModelError, match="length_unit"):
        build_polygon_extrusion_history(
            "history.invalid", SQUARE, height=2.0, length_unit="kg"
        )


def test_polygon_template_enforces_maximum_vertex_count():
    points = tuple(
        (float(index), float(index % 3))
        for index in range(65)
    )
    with pytest.raises(InvalidModelError, match="3 to 64"):
        build_polygon_extrusion_history("history.too-many", points, height=2.0)
