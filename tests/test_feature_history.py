import json

import pytest

from universal_platform.engineering.errors import InvalidModelError
from universal_platform.engineering.feature_history import (
    FeatureHistory, FeatureKind, FeatureNode, RegenerationStatus,
    regenerate_feature_history,
)
from universal_platform.engineering.parametric_sketch import (
    ParametricSketch, SketchConstraint, SketchConstraintKind as Kind,
    SketchPoint, SketchSegment,
)


def square_sketch(sketch_id="plate", width=10.0, height=8.0, x0=0.0):
    coords = ((x0, 0.0), (x0 + width, 0.0), (x0 + width, height), (x0, height))
    ids = ("p0", "p1", "p2", "p3")
    points = tuple(SketchPoint(point_id, x, y) for point_id, (x, y) in zip(ids, coords))
    segments = tuple(SketchSegment(f"e{i}", ids[i], ids[(i + 1) % 4]) for i in range(4))
    constraints = tuple(
        constraint
        for point_id, (x, y) in zip(ids, coords)
        for constraint in (
            SketchConstraint(f"fx.{point_id}", Kind.FIX_X, (point_id,), x),
            SketchConstraint(f"fy.{point_id}", Kind.FIX_Y, (point_id,), y),
        )
    )
    return ParametricSketch(sketch_id, "part.xy", "mm", points, segments, constraints)


def feature_history_for_square(width=10.0, height=8.0):
    sketch = square_sketch(width=width, height=height)
    return FeatureHistory(
        "history.plate",
        (
            FeatureNode.create("mesh.final", FeatureKind.MESH, ("extrude.final",)),
            FeatureNode.create("extrude.final", FeatureKind.EXTRUSION, ("sketch.profile",),
                               {"solid_id": "solid.plate", "height": 3.0}),
            FeatureNode.create("sketch.profile", FeatureKind.SKETCH_PROFILE, (),
                               {"sketch": sketch.to_dict()}),
        ),
        ("mesh.final",),
    )


def test_feature_history_regenerates_sketch_extrusion_and_watertight_mesh():
    history = feature_history_for_square()
    result = regenerate_feature_history(history)
    assert result.status is RegenerationStatus.SUCCESS
    assert result.successful
    assert result.execution_order == ("sketch.profile", "extrude.final", "mesh.final")
    assert len(result.artifacts) == 3
    mesh_artifact = result.artifacts[-1]
    mesh_payload = mesh_artifact.to_dict()["payload"]
    assert mesh_payload["validation"]["valid"] is True
    assert mesh_payload["validation"]["watertight"] is True
    assert mesh_payload["validation"]["consistently_oriented"] is True
    assert len(mesh_artifact.content_sha256) == 64


def test_feature_history_multi_region_boolean_then_extrusion_and_mesh():
    left = square_sketch("left", 4.0, 3.0, 0.0)
    right = square_sketch("right", 4.0, 3.0, 3.0)
    history = FeatureHistory(
        "history.union",
        (
            FeatureNode.create("left.profile", FeatureKind.SKETCH_PROFILE, (), {"sketch": left.to_dict()}),
            FeatureNode.create("right.profile", FeatureKind.SKETCH_PROFILE, (), {"sketch": right.to_dict()}),
            FeatureNode.create("union", FeatureKind.PLANAR_BOOLEAN,
                               ("left.profile", "right.profile"), {"operation": "UNION"}),
            FeatureNode.create("extrusion", FeatureKind.EXTRUSION, ("union",),
                               {"solid_id": "solid.union", "height": 5.0}),
            FeatureNode.create("mesh", FeatureKind.MESH, ("extrusion",)),
        ),
        ("mesh",),
    )
    result = regenerate_feature_history(history)
    assert result.successful
    boolean_payload = result.artifacts[2].to_dict()["payload"]
    assert boolean_payload["regions"][0]["region_id"]
    assert result.artifacts[-1].to_dict()["payload"]["validation"]["watertight"] is True


def test_feature_history_is_deterministic_and_parameter_changes_invalidate_downstream_digest():
    first = regenerate_feature_history(feature_history_for_square(10.0, 8.0))
    repeated = regenerate_feature_history(feature_history_for_square(10.0, 8.0))
    changed = regenerate_feature_history(feature_history_for_square(12.0, 8.0))
    assert first.successful and repeated.successful and changed.successful
    assert [a.content_sha256 for a in first.artifacts] == [a.content_sha256 for a in repeated.artifacts]
    assert [a.content_sha256 for a in first.artifacts] != [a.content_sha256 for a in changed.artifacts]


def test_feature_history_snapshot_round_trip_is_strict_and_deterministic():
    history = feature_history_for_square()
    snapshot = history.to_dict()
    restored = FeatureHistory.from_dict(json.loads(json.dumps(snapshot)))
    assert restored.to_dict() == snapshot
    with pytest.raises(InvalidModelError, match="missing or unknown"):
        FeatureHistory.from_dict(dict(snapshot, unexpected=True))


def test_feature_history_rejects_missing_dependencies_duplicate_ids_and_cycles():
    with pytest.raises(InvalidModelError, match="missing dependency"):
        FeatureHistory("bad", (
            FeatureNode.create("node", FeatureKind.MESH, ("missing",)),
        ), ("node",))
    with pytest.raises(InvalidModelError, match="cycle"):
        FeatureHistory("bad", (
            FeatureNode.create("a", FeatureKind.MESH, ("b",)),
            FeatureNode.create("b", FeatureKind.MESH, ("a",)),
        ), ("a",))
    with pytest.raises(InvalidModelError, match="unique"):
        FeatureHistory("bad", (
            FeatureNode.create("same", FeatureKind.MESH, ()),
            FeatureNode.create("same", FeatureKind.MESH, ()),
        ), ("same",))


def test_feature_history_fails_closed_and_discards_partial_artifacts():
    history = FeatureHistory(
        "history.invalid",
        (
            FeatureNode.create("profile", FeatureKind.SKETCH_PROFILE, (),
                               {"sketch": square_sketch().to_dict()}),
            FeatureNode.create("bad-extrusion", FeatureKind.EXTRUSION, ("profile",),
                               {"solid_id": "solid.bad", "height": -1.0}),
            FeatureNode.create("mesh", FeatureKind.MESH, ("bad-extrusion",)),
        ),
        ("mesh",),
    )
    result = regenerate_feature_history(history)
    assert result.status is RegenerationStatus.FAILED
    assert result.failed_feature_id == "bad-extrusion"
    assert result.artifacts == ()
    assert result.error


def test_feature_nodes_reject_invalid_json_nonfinite_parameters_and_unknown_feature_kinds():
    with pytest.raises(InvalidModelError, match="valid JSON"):
        FeatureNode("bad", FeatureKind.MESH, (), "{")
    with pytest.raises(InvalidModelError, match="finite JSON"):
        FeatureNode.create("bad", FeatureKind.MESH, (), {"bad": float("nan")})
    snapshot = feature_history_for_square().to_dict()
    snapshot["nodes"][0]["kind"] = "RUN_SHELL"
    with pytest.raises(InvalidModelError, match="unsupported feature kind"):
        FeatureHistory.from_dict(snapshot)


def test_parametric_sketch_strict_snapshot_import_rejects_unknown_fields():
    sketch = square_sketch()
    restored = ParametricSketch.from_dict(sketch.to_dict())
    assert restored.to_dict() == sketch.to_dict()
    with pytest.raises(InvalidModelError, match="missing or unknown"):
        ParametricSketch.from_dict(dict(sketch.to_dict(), extra=True))
