import pytest

from universal_platform.engineering import (
    CADGeneratorRun,
    CADGeneratorService,
    FeatureArtifactCacheIntegrityError,
    SQLiteFeatureArtifactCache,
)
from universal_platform.engineering.errors import InvalidModelError
from universal_platform.engineering.feature_history import (
    FeatureHistory,
    FeatureKind,
    FeatureNode,
)
from universal_platform.engineering.feature_history_store import (
    FeatureHistoryNavigationUnavailable,
    FeatureHistoryRevisionConflict,
    SQLiteFeatureHistoryStore,
)
from universal_platform.engineering.parametric_sketch import (
    ParametricSketch,
    SketchConstraint,
    SketchConstraintKind as Kind,
    SketchPoint,
    SketchSegment,
)


def make_history(width=4.0):
    coordinates = ((0.0, 0.0), (width, 0.0), (width, 3.0), (0.0, 3.0))
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
        "history.cad-service",
        (
            FeatureNode.create("mesh", FeatureKind.MESH, ("extrusion",)),
            FeatureNode.create(
                "extrusion", FeatureKind.EXTRUSION, ("profile",),
                {"solid_id": "solid.service", "height": 2.0},
            ),
            FeatureNode.create(
                "profile", FeatureKind.SKETCH_PROFILE, (), {"sketch": sketch.to_dict()}
            ),
        ),
        ("mesh",),
    )


def make_service(tmp_path):
    return CADGeneratorService(
        SQLiteFeatureHistoryStore(tmp_path / "source.sqlite3"),
        SQLiteFeatureArtifactCache(tmp_path / "artifacts.sqlite3"),
    )


def test_cad_generator_service_saves_snapshot_regenerates_and_returns_provenance(tmp_path):
    service = make_service(tmp_path)
    saved = service.save_snapshot(make_history().to_dict(), expected_revision=0)

    assert saved.history_id == "history.cad-service"
    assert saved.revision == 1
    assert service.list_revisions(saved.history_id) == (1,)

    run = service.regenerate(saved.history_id, revision=1)
    assert isinstance(run, CADGeneratorRun)
    assert run.successful
    assert run.source_revision.content_sha256 == saved.content_sha256
    assert run.regeneration.recomputed_feature_ids == ("profile", "extrusion", "mesh")
    assert run.regeneration.reused_feature_ids == ()

    payload = run.to_dict()
    assert payload["source_revision"]["revision"] == 1
    assert payload["regeneration"]["status"] == "SUCCESS"
    assert payload["regeneration"]["artifacts"][-1]["payload"]["validation"]["watertight"] is True


def test_cad_generator_service_reuses_cache_and_supports_immutable_revision_selection(tmp_path):
    service = make_service(tmp_path)
    first = service.save_history(make_history(4.0), expected_revision=0)
    first_run = service.regenerate(first.history_id, revision=first.revision)
    second = service.save_history(make_history(5.0), expected_revision=first.revision)

    assert second.revision == 2
    assert service.list_revisions(first.history_id) == (1, 2)

    restored_first = service.regenerate(first.history_id, revision=1)
    restored_second = service.regenerate(first.history_id, revision=2)

    assert restored_first.successful and restored_second.successful
    assert restored_first.regeneration.reused_feature_ids == ("profile", "extrusion", "mesh")
    assert restored_first.regeneration.recomputed_feature_ids == ()
    assert restored_second.regeneration.recomputed_feature_ids == ("profile", "extrusion", "mesh")
    assert restored_first.regeneration.artifacts[-1].content_sha256 == first_run.regeneration.artifacts[-1].content_sha256


def test_cad_generator_service_surfaces_revision_conflicts_and_rejects_invalid_snapshots(tmp_path):
    service = make_service(tmp_path)
    service.save_history(make_history(), expected_revision=0)

    with pytest.raises(FeatureHistoryRevisionConflict):
        service.save_history(make_history(5.0), expected_revision=0)
    with pytest.raises(InvalidModelError):
        service.save_snapshot({"history_id": "bad", "unknown": True}, expected_revision=1)


def test_cad_generator_service_requires_explicit_local_store_dependencies(tmp_path):
    with pytest.raises(InvalidModelError, match="SQLiteFeatureHistoryStore"):
        CADGeneratorService(object(), SQLiteFeatureArtifactCache(tmp_path / "cache.sqlite3"))
    with pytest.raises(InvalidModelError, match="SQLiteFeatureArtifactCache"):
        CADGeneratorService(SQLiteFeatureHistoryStore(tmp_path / "source.sqlite3"), object())

    assert FeatureArtifactCacheIntegrityError.__name__ == "FeatureArtifactCacheIntegrityError"


def test_cad_generator_service_edits_and_appends_revision_without_mutating_prior_snapshot(tmp_path):
    service = make_service(tmp_path)
    first = service.save_history(make_history(), expected_revision=0)

    replacement = FeatureNode.create(
        "extrusion", FeatureKind.EXTRUSION, ("profile",),
        {"solid_id": "solid.service", "height": 3.0},
    )
    second = service.edit_history(
        first.history_id,
        expected_revision=first.revision,
        operation="replace",
        feature_id="extrusion",
        feature=replacement,
    )

    assert second.revision == 2
    assert second.parent_sha256 == first.content_sha256
    assert first.history.nodes[1].parameters["height"] == 2.0
    assert second.history.nodes[1].parameters["height"] == 3.0
    assert service.get_revision(first.history_id, revision=1).history.nodes[1].parameters["height"] == 2.0
    regenerated = service.regenerate(first.history_id, revision=2)
    assert regenerated.successful
    assert regenerated.regeneration.artifacts[-1].to_dict()["payload"]["validation"]["watertight"] is True


def test_cad_generator_service_edit_requires_current_revision_and_valid_operation(tmp_path):
    service = make_service(tmp_path)
    saved = service.save_history(make_history(), expected_revision=0)
    feature = FeatureNode.create("extra.mesh", FeatureKind.MESH, ("extrusion",))
    service.save_history(make_history(5.0), expected_revision=saved.revision)

    with pytest.raises(FeatureHistoryRevisionConflict):
        service.edit_history(
            saved.history_id,
            expected_revision=1,
            operation="add",
            feature=feature,
        )
    with pytest.raises(InvalidModelError, match="operation must be"):
        service.edit_history(
            saved.history_id,
            expected_revision=2,
            operation="execute",
        )
    with pytest.raises(InvalidModelError, match="does not accept"):
        service.edit_history(
            saved.history_id,
            expected_revision=2,
            operation="add",
            feature=feature,
            cascade=True,
        )



def make_history_with_alternate_output():
    original = make_history()
    profile = next(node for node in original.nodes if node.feature_id == "profile")
    alternate = (
        FeatureNode.create(
            "profile.alt", FeatureKind.SKETCH_PROFILE, (),
            {"sketch": profile.parameters["sketch"]},
        ),
        FeatureNode.create(
            "extrusion.alt", FeatureKind.EXTRUSION, ("profile.alt",),
            {"solid_id": "solid.alt", "height": 1.5},
        ),
        FeatureNode.create("mesh.alt", FeatureKind.MESH, ("extrusion.alt",)),
    )
    return FeatureHistory(
        original.history_id, original.nodes + alternate, ("mesh", "mesh.alt")
    )


def test_cad_generator_service_suppresses_and_restores_revisioned_features(tmp_path):
    service = make_service(tmp_path)
    first = service.save_history(make_history_with_alternate_output(), expected_revision=0)

    suppressed = service.edit_history(
        first.history_id,
        expected_revision=1,
        operation="suppress",
        feature_id="extrusion",
        cascade=True,
    )
    assert suppressed.revision == 2
    assert suppressed.history.document_version == "1.1"
    assert suppressed.history.suppressed_feature_ids == ("extrusion", "mesh")

    run = service.regenerate(first.history_id, revision=2)
    assert run.successful
    assert run.regeneration.suppressed_feature_ids == ("extrusion", "mesh")
    assert set(run.regeneration.execution_order) == {"profile", "profile.alt", "extrusion.alt", "mesh.alt"}

    restored_parent = service.edit_history(
        first.history_id,
        expected_revision=2,
        operation="unsuppress",
        feature_id="extrusion",
    )
    assert restored_parent.revision == 3
    assert restored_parent.history.suppressed_feature_ids == ("mesh",)

    restored_output = service.edit_history(
        first.history_id,
        expected_revision=3,
        operation="unsuppress",
        feature_id="mesh",
    )
    assert restored_output.revision == 4
    assert restored_output.history.suppressed_feature_ids == ()

    with pytest.raises(FeatureHistoryRevisionConflict):
        service.edit_history(
            first.history_id,
            expected_revision=3,
            operation="unsuppress",
            feature_id="mesh",
        )


def test_cad_generator_service_rejects_invalid_suppression_operation_fields(tmp_path):
    service = make_service(tmp_path)
    first = service.save_history(make_history_with_alternate_output(), expected_revision=0)

    with pytest.raises(InvalidModelError, match="unsuppress requires"):
        service.edit_history(
            first.history_id,
            expected_revision=1,
            operation="unsuppress",
            feature_id="mesh",
            cascade=True,
        )



def test_cad_generator_service_exposes_persistent_undo_redo_state(tmp_path):
    service = make_service(tmp_path)
    service.save_history(make_history(width=4.0), expected_revision=0)
    service.save_history(make_history(width=5.0), expected_revision=1)

    state = service.get_navigation_state("history.cad-service")
    assert state.current_revision == 2
    assert state.can_undo is True
    assert state.can_redo is False
    assert state.undo_depth == 1

    undone = service.undo_history("history.service", expected_revision=2)
    assert undone.revision == 3
    assert undone.operation == "undo"
    assert undone.target_revision == 1
    state = service.get_navigation_state("history.service")
    assert state.current_revision == 3
    assert state.can_undo is False
    assert state.can_redo is True

    redone = service.redo_history("history.service", expected_revision=3)
    assert redone.revision == 4
    assert redone.operation == "redo"
    assert redone.target_revision == 2
    state = service.get_navigation_state("history.service")
    assert state.current_revision == 4
    assert state.can_undo is True
    assert state.can_redo is False


def test_cad_generator_service_navigation_rejects_stale_head_and_empty_stack(tmp_path):
    service = make_service(tmp_path)
    service.save_history(make_history(), expected_revision=0)
    with pytest.raises(FeatureHistoryNavigationUnavailable) as error:
        service.undo_history("history.service", expected_revision=1)
    assert error.value.code == "NO_UNDO"
    with pytest.raises(FeatureHistoryNavigationUnavailable) as error:
        service.redo_history("history.service", expected_revision=1)
    assert error.value.code == "NO_REDO"
