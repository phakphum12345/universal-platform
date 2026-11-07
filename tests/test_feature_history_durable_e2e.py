import json
import subprocess
import sys

from universal_platform.engineering.feature_artifact_store import SQLiteFeatureArtifactCache
from universal_platform.engineering.feature_history import (
    FeatureHistory,
    FeatureKind,
    FeatureNode,
    regenerate_feature_history,
)
from universal_platform.engineering.feature_history_store import SQLiteFeatureHistoryStore
from universal_platform.engineering.parametric_sketch import (
    ParametricSketch,
    SketchConstraint,
    SketchConstraintKind as Kind,
    SketchPoint,
    SketchSegment,
)


def source_history():
    coordinates = ((0.0, 0.0), (4.0, 0.0), (4.0, 3.0), (0.0, 3.0))
    ids = ("p0", "p1", "p2", "p3")
    points = tuple(SketchPoint(key, x, y) for key, (x, y) in zip(ids, coordinates))
    segments = tuple(SketchSegment(f"edge.{i}", ids[i], ids[(i + 1) % 4]) for i in range(4))
    constraints = tuple(
        constraint
        for key, (x, y) in zip(ids, coordinates)
        for constraint in (
            SketchConstraint(f"x.{key}", Kind.FIX_X, (key,), x),
            SketchConstraint(f"y.{key}", Kind.FIX_Y, (key,), y),
        )
    )
    sketch = ParametricSketch("profile", "part.xy", "mm", points, segments, constraints)
    return FeatureHistory(
        "history.durable-e2e",
        (
            FeatureNode.create("mesh", FeatureKind.MESH, ("extrusion",)),
            FeatureNode.create(
                "extrusion", FeatureKind.EXTRUSION, ("profile",),
                {"solid_id": "solid.durable-e2e", "height": 2.0},
            ),
            FeatureNode.create(
                "profile", FeatureKind.SKETCH_PROFILE, (), {"sketch": sketch.to_dict()}
            ),
        ),
        ("mesh",),
    )


def test_durable_source_revision_and_artifact_cache_reopen_in_fresh_process(tmp_path):
    source_path = tmp_path / "source" / "feature-history.sqlite3"
    cache_path = tmp_path / "cache" / "feature-artifacts.sqlite3"
    source_store = SQLiteFeatureHistoryStore(source_path)
    cache = SQLiteFeatureArtifactCache(cache_path)

    saved = source_store.save(source_history(), expected_revision=0)
    loaded = SQLiteFeatureHistoryStore(source_path).load(
        saved.history_id, revision=saved.revision
    )
    first = regenerate_feature_history(loaded.history, artifact_cache=cache)

    assert first.successful
    assert first.recomputed_feature_ids == ("profile", "extrusion", "mesh")
    assert cache.count(saved.history_id) == 3

    script = r"""
import json
import sys
from universal_platform.engineering.feature_artifact_store import SQLiteFeatureArtifactCache
from universal_platform.engineering.feature_history import regenerate_feature_history
from universal_platform.engineering.feature_history_store import SQLiteFeatureHistoryStore

source_path, cache_path, history_id = sys.argv[1:4]
revision = SQLiteFeatureHistoryStore(source_path).load(history_id, revision=1)
cache = SQLiteFeatureArtifactCache(cache_path)
result = regenerate_feature_history(revision.history, artifact_cache=cache)
if not result.successful:
    raise SystemExit(result.error or "regeneration failed")
mesh = result.artifacts[-1].to_dict()["payload"]
print(json.dumps({
    "history_id": result.history_id,
    "reused": list(result.reused_feature_ids),
    "recomputed": list(result.recomputed_feature_ids),
    "digests": [item.content_sha256 for item in result.artifacts],
    "watertight": mesh["validation"]["watertight"],
    "consistently_oriented": mesh["validation"]["consistently_oriented"],
}))
"""
    completed = subprocess.run(
        [sys.executable, "-c", script, str(source_path), str(cache_path), saved.history_id],
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )
    restored = json.loads(completed.stdout)

    assert restored["history_id"] == saved.history_id
    assert restored["reused"] == ["profile", "extrusion", "mesh"]
    assert restored["recomputed"] == []
    assert restored["digests"] == [item.content_sha256 for item in first.artifacts]
    assert restored["watertight"] is True
    assert restored["consistently_oriented"] is True
