import sqlite3

import pytest

from universal_platform.engineering.errors import InvalidModelError
from universal_platform.engineering.feature_artifact_store import (
    FeatureArtifactCacheIntegrityError,
    SQLiteFeatureArtifactCache,
)
from universal_platform.engineering.feature_history import (
    FeatureHistory,
    FeatureKind,
    FeatureNode,
    RegenerationStatus,
    regenerate_feature_history,
)
from universal_platform.engineering.parametric_sketch import (
    ParametricSketch,
    SketchConstraint,
    SketchConstraintKind as Kind,
    SketchPoint,
    SketchSegment,
)


def square_sketch(width=4.0):
    coords = ((0.0, 0.0), (width, 0.0), (width, 3.0), (0.0, 3.0))
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
    return ParametricSketch("profile", "part.xy", "mm", points, segments, constraints)


def history(width=4.0):
    sketch = square_sketch(width)
    return FeatureHistory(
        "history.cache-test",
        (
            FeatureNode.create("mesh", FeatureKind.MESH, ("extrusion",)),
            FeatureNode.create(
                "extrusion", FeatureKind.EXTRUSION, ("profile",),
                {"solid_id": "solid.cache-test", "height": 2.0},
            ),
            FeatureNode.create(
                "profile", FeatureKind.SKETCH_PROFILE, (), {"sketch": sketch.to_dict()}
            ),
        ),
        ("mesh",),
    )


def test_artifact_cache_persists_and_reuses_all_features_after_reopen(tmp_path):
    database = tmp_path / "nested" / "artifacts.sqlite3"
    first_cache = SQLiteFeatureArtifactCache(database)
    first = regenerate_feature_history(history(), artifact_cache=first_cache)

    assert first.status is RegenerationStatus.SUCCESS
    assert first.recomputed_feature_ids == ("profile", "extrusion", "mesh")
    assert first.reused_feature_ids == ()
    assert first_cache.count("history.cache-test") == 3

    reopened_cache = SQLiteFeatureArtifactCache(database)
    second = regenerate_feature_history(history(), artifact_cache=reopened_cache)

    assert second.status is RegenerationStatus.SUCCESS
    assert second.reused_feature_ids == ("profile", "extrusion", "mesh")
    assert second.recomputed_feature_ids == ()
    assert [item.content_sha256 for item in first.artifacts] == [
        item.content_sha256 for item in second.artifacts
    ]


def test_artifact_cache_recomputes_only_changed_feature_and_descendants(tmp_path):
    cache = SQLiteFeatureArtifactCache(tmp_path / "artifacts.sqlite3")
    first = regenerate_feature_history(history(4.0), artifact_cache=cache)
    changed = regenerate_feature_history(history(5.0), artifact_cache=cache)

    assert first.successful and changed.successful
    assert changed.reused_feature_ids == ()
    assert changed.recomputed_feature_ids == ("profile", "extrusion", "mesh")
    assert cache.count("history.cache-test") == 6


def test_artifact_cache_save_is_idempotent_for_the_same_computation_key(tmp_path):
    cache = SQLiteFeatureArtifactCache(tmp_path / "artifacts.sqlite3")
    result = regenerate_feature_history(history())
    artifact = result.artifacts[0]

    cache.save("history.cache-test", artifact)
    cache.save("history.cache-test", artifact)

    loaded = cache.load("history.cache-test", artifact.feature_id, artifact.computation_sha256)
    assert loaded is not None
    assert loaded.to_dict() == artifact.to_dict()
    assert cache.count("history.cache-test") == 1


def test_artifact_cache_detects_record_tampering_and_fails_regeneration_closed(tmp_path):
    database = tmp_path / "artifacts.sqlite3"
    cache = SQLiteFeatureArtifactCache(database)
    initial = regenerate_feature_history(history(), artifact_cache=cache)
    first = initial.artifacts[0]

    with sqlite3.connect(database) as connection:
        connection.execute("DROP TRIGGER feature_artifact_cache_no_update")
        connection.execute(
            "UPDATE feature_artifact_cache SET artifact_json = ? "
            "WHERE history_id = ? AND feature_id = ?",
            ("{}", "history.cache-test", "profile"),
        )

    with pytest.raises(FeatureArtifactCacheIntegrityError, match="record digest mismatch"):
        cache.load("history.cache-test", first.feature_id, first.computation_sha256)

    failed = regenerate_feature_history(history(), artifact_cache=cache)
    assert failed.status is RegenerationStatus.FAILED
    assert failed.failed_feature_id == "profile"
    assert failed.artifacts == ()


def test_artifact_cache_rejects_invalid_paths_ids_and_cache_protocol(tmp_path):
    with pytest.raises(ValueError, match="filesystem path"):
        SQLiteFeatureArtifactCache(":memory:")
    with pytest.raises(ValueError, match="positive number"):
        SQLiteFeatureArtifactCache(tmp_path / "bad.db", timeout_seconds=float("nan"))

    cache = SQLiteFeatureArtifactCache(tmp_path / "artifacts.sqlite3")
    with pytest.raises(ValueError, match="stable lowercase identifier"):
        cache.count("../outside")
    with pytest.raises(ValueError, match="stable lowercase identifier"):
        cache.load("history.cache-test", "../outside", "0" * 64)
    with pytest.raises(InvalidModelError, match="callable load and save"):
        regenerate_feature_history(history(), artifact_cache=object())
