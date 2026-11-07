from universal_platform.engineering.feature_history import (
    FeatureHistory,
    FeatureKind,
    FeatureNode,
    RegenerationStatus,
    regenerate_feature_history,
)
from universal_platform.engineering.parametric_sketch import (
    ParametricSketch,
    SketchArc,
    SketchConstraint,
    SketchConstraintKind as Kind,
    SketchPoint,
)


def circle_sketch():
    points = (
        SketchPoint("center", 0, 0),
        SketchPoint("east", 1, 0),
        SketchPoint("north", 0, 1),
        SketchPoint("west", -1, 0),
        SketchPoint("south", 0, -1),
    )
    arcs = (
        SketchArc("arc.east-north", "center", "east", "north"),
        SketchArc("arc.north-west", "center", "north", "west"),
        SketchArc("arc.west-south", "center", "west", "south"),
        SketchArc("arc.south-east", "center", "south", "east"),
    )
    constraints = []
    for point in points:
        constraints.extend((
            SketchConstraint(f"fix-x.{point.point_id}", Kind.FIX_X, (point.point_id,), point.x),
            SketchConstraint(f"fix-y.{point.point_id}", Kind.FIX_Y, (point.point_id,), point.y),
        ))
    for arc in arcs:
        constraints.append(SketchConstraint(
            f"radius.{arc.arc_id}", Kind.RADIUS, (), 1.0, arc_ids=(arc.arc_id,)
        ))
    return ParametricSketch(
        "curved.profile", "part.xy", "mm", points,
        constraints=tuple(constraints), arcs=arcs,
    )


def curved_profile_history():
    sketch = circle_sketch()
    return FeatureHistory(
        "history.curved-profile",
        (
            FeatureNode.create("mesh.final", FeatureKind.MESH, ("extrude.final",)),
            FeatureNode.create(
                "extrude.final", FeatureKind.EXTRUSION, ("sketch.profile",),
                {"solid_id": "solid.curved-profile", "height": 2.0},
            ),
            FeatureNode.create(
                "sketch.profile", FeatureKind.SKETCH_PROFILE, (),
                {"sketch": sketch.to_dict()},
            ),
        ),
        ("mesh.final",),
    )


def test_curved_sketch_profile_regenerates_through_extrusion_to_watertight_mesh():
    history = curved_profile_history()
    result = regenerate_feature_history(history)

    assert result.status is RegenerationStatus.SUCCESS
    assert result.execution_order == ("sketch.profile", "extrude.final", "mesh.final")
    assert len(result.artifacts) == 3

    profile = result.artifacts[0].to_dict()["payload"]["regions"][0]
    assert len(profile["outer_boundary"]) > 4
    assert profile["frame_id"] == "part.xy"
    assert profile["length_unit"] == "mm"

    extrusion = result.artifacts[1].to_dict()["payload"]["solid"]
    assert len(extrusion["profile"]) == len(profile["outer_boundary"])
    assert extrusion["height"] == 2.0

    mesh = result.artifacts[2].to_dict()["payload"]
    assert mesh["validation"]["valid"] is True
    assert mesh["validation"]["watertight"] is True
    assert mesh["validation"]["consistently_oriented"] is True


def test_curved_profile_pipeline_is_deterministic_across_full_regeneration():
    first = regenerate_feature_history(curved_profile_history())
    second = regenerate_feature_history(curved_profile_history())

    assert first.successful and second.successful
    assert [item.content_sha256 for item in first.artifacts] == [
        item.content_sha256 for item in second.artifacts
    ]
