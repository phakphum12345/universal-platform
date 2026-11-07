from copy import deepcopy
from hashlib import sha256
from json import dumps

import pytest

from universal_platform.engineering.errors import InvalidModelError
from universal_platform.engineering.feature_history import (
    FeatureArtifact,
    FeatureHistory,
    FeatureKind,
    FeatureNode,
    regenerate_feature_history,
)
from universal_platform.engineering.mesh import TriangleMesh
from universal_platform.engineering.planar_region_extrusion import PlanarRegionExtrusionResult
from universal_platform.engineering.planar_region_set_boolean import PlanarRegionSetBooleanResult
from universal_platform.engineering.sketch_region import SketchRegionConversionResult
from universal_platform.engineering.parametric_sketch import (
    ParametricSketch,
    SketchConstraint,
    SketchConstraintKind as Kind,
    SketchPoint,
    SketchSegment,
)


def square_sketch(sketch_id, x0):
    coords = ((x0, 0), (x0 + 4, 0), (x0 + 4, 3), (x0, 3))
    ids = ("p0", "p1", "p2", "p3")
    points = tuple(SketchPoint(key, x, y) for key, (x, y) in zip(ids, coords))
    segments = tuple(SketchSegment(f"edge.{i}", ids[i], ids[(i + 1) % 4]) for i in range(4))
    constraints = tuple(
        item
        for key, (x, y) in zip(ids, coords)
        for item in (
            SketchConstraint(f"x.{key}", Kind.FIX_X, (key,), x),
            SketchConstraint(f"y.{key}", Kind.FIX_Y, (key,), y),
        )
    )
    return ParametricSketch(sketch_id, "part.xy", "mm", points, segments, constraints)


def feature_artifacts():
    left = square_sketch("left", 0)
    right = square_sketch("right", 2)
    history = FeatureHistory(
        "history.artifact-roundtrip",
        (
            FeatureNode.create("left.profile", FeatureKind.SKETCH_PROFILE, (), {"sketch": left.to_dict()}),
            FeatureNode.create("right.profile", FeatureKind.SKETCH_PROFILE, (), {"sketch": right.to_dict()}),
            FeatureNode.create(
                "union", FeatureKind.PLANAR_BOOLEAN, ("left.profile", "right.profile"),
                {"operation": "UNION"},
            ),
            FeatureNode.create(
                "extrusion", FeatureKind.EXTRUSION, ("union",),
                {"solid_id": "solid.union", "height": 2.0},
            ),
            FeatureNode.create("mesh", FeatureKind.MESH, ("extrusion",)),
        ),
        ("mesh",),
    )
    result = regenerate_feature_history(history)
    assert result.successful
    return result.artifacts


def test_all_feature_artifact_kinds_round_trip_through_trusted_rehydration():
    artifacts = feature_artifacts()
    assert {item.kind for item in artifacts} == set(FeatureKind)

    restored = tuple(FeatureArtifact.from_dict(item.to_dict()) for item in artifacts)
    assert [item.to_dict() for item in restored] == [item.to_dict() for item in artifacts]
    assert isinstance(restored[0].value, SketchRegionConversionResult)
    assert isinstance(restored[2].value, PlanarRegionSetBooleanResult)
    assert isinstance(restored[3].value, PlanarRegionExtrusionResult)
    assert isinstance(restored[4].value[0], TriangleMesh)
    assert restored[4].value[1].watertight is True


def test_feature_artifact_rehydration_rejects_payload_digest_tampering():
    snapshot = feature_artifacts()[0].to_dict()
    tampered = deepcopy(snapshot)
    tampered["payload"]["source_sketch_id"] = "different.sketch"

    with pytest.raises(InvalidModelError, match="content digest mismatch"):
        FeatureArtifact.from_dict(tampered)


def test_feature_artifact_rehydration_rejects_invalid_mesh_validation_even_with_new_digest():
    snapshot = next(item.to_dict() for item in feature_artifacts() if item.kind is FeatureKind.MESH)
    tampered = deepcopy(snapshot)
    tampered["payload"]["validation"]["watertight"] = False
    encoded = dumps(tampered["payload"], sort_keys=True, separators=(",", ":"), allow_nan=False)
    tampered["content_sha256"] = sha256(encoded.encode("utf-8")).hexdigest()

    with pytest.raises(InvalidModelError, match="validation report mismatch"):
        FeatureArtifact.from_dict(tampered)


def test_feature_artifact_rehydration_rejects_unknown_fields_and_bad_digests():
    snapshot = feature_artifacts()[0].to_dict()
    with pytest.raises(InvalidModelError, match="missing or unknown"):
        FeatureArtifact.from_dict(dict(snapshot, unexpected=True))
    invalid_digest = dict(snapshot, computation_sha256="not-a-digest")
    with pytest.raises(InvalidModelError, match="computation_sha256"):
        FeatureArtifact.from_dict(invalid_digest)
