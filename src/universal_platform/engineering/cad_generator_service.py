"""In-process CAD generator application service over durable local stores.

This layer exposes a stable, transport-neutral boundary. It does not start an
HTTP listener, access the network, execute user code, or control devices.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from .errors import InvalidModelError
from .feature_artifact_store import SQLiteFeatureArtifactCache
from .feature_history import (
    FeatureHistory,
    FeatureNode,
    FeatureRegenerationResult,
    regenerate_feature_history,
)
from .feature_history_editor import (
    add_feature, remove_feature, reorder_features, replace_feature, suppress_feature, unsuppress_feature,
)
from .feature_history_store import (
    FeatureHistoryBranch,
    FeatureHistoryNavigationState,
    FeatureHistoryRevision,
    FeatureHistoryRevisionConflict,
    SQLiteFeatureHistoryStore,
)
from .nonlinear_solver import NonlinearSolverOptions


@dataclass(frozen=True, slots=True)
class CADGeneratorRun:
    """Regeneration result bound to the exact durable source revision."""

    source_revision: FeatureHistoryRevision
    regeneration: FeatureRegenerationResult

    @property
    def successful(self) -> bool:
        return self.regeneration.successful

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": "1.0",
            "history_id": self.source_revision.history_id,
            "source_revision": {
                "revision": self.source_revision.revision,
                "parent_sha256": self.source_revision.parent_sha256,
                "content_sha256": self.source_revision.content_sha256,
                "created_at": self.source_revision.created_at,
            },
            "regeneration": self.regeneration.to_dict(),
            "limitations": [
                "Transport-neutral in-process service; no HTTP listener or network exposure",
                "Local SQLite source and artifact stores; no distributed transaction or replication",
                "Only built-in allow-listed FeatureHistory operations execute",
                "No user code, plugin, shell, firmware, physical-device or deployment actions",
            ],
        }


class CADGeneratorService:
    """Revision-aware CAD regeneration service using local SQLite stores.

    The service accepts typed FeatureHistory records or their strict JSON
    snapshots, persists immutable revisions, and regenerates a selected
    revision using exact computation-signature cache keys.
    """

    def __init__(
        self,
        history_store: SQLiteFeatureHistoryStore,
        artifact_cache: SQLiteFeatureArtifactCache,
    ):
        if not isinstance(history_store, SQLiteFeatureHistoryStore):
            raise InvalidModelError("history_store must be a SQLiteFeatureHistoryStore")
        if not isinstance(artifact_cache, SQLiteFeatureArtifactCache):
            raise InvalidModelError("artifact_cache must be a SQLiteFeatureArtifactCache")
        self.history_store = history_store
        self.artifact_cache = artifact_cache

    def save_history(
        self,
        history: FeatureHistory,
        *,
        expected_revision: int,
    ) -> FeatureHistoryRevision:
        if not isinstance(history, FeatureHistory):
            raise InvalidModelError("save_history requires a FeatureHistory")
        return self.history_store.save(history, expected_revision=expected_revision)

    def save_snapshot(
        self,
        snapshot: Mapping[str, object],
        *,
        expected_revision: int,
    ) -> FeatureHistoryRevision:
        """Strictly parse and persist a JSON-compatible FeatureHistory snapshot."""
        if not isinstance(snapshot, Mapping):
            raise InvalidModelError("FeatureHistory snapshot must be an object")
        history = FeatureHistory.from_dict(snapshot)
        return self.save_history(history, expected_revision=expected_revision)

    def edit_history(
        self,
        history_id: str,
        *,
        expected_revision: int,
        operation: str,
        feature: FeatureNode | None = None,
        feature_id: str | None = None,
        cascade: bool = False,
        make_output: bool = False,
        ordered_feature_ids: tuple[str, ...] | None = None,
    ) -> FeatureHistoryRevision:
        """Apply one validated graph edit and append a new immutable revision.

        The latest source revision must equal expected_revision before editing.
        SQLite compare-and-swap on save closes the race between this read and
        the append, so concurrent writers cannot silently overwrite each other.
        """
        if isinstance(expected_revision, bool) or not isinstance(expected_revision, int) or expected_revision < 1:
            raise InvalidModelError("expected_revision must be a positive integer for an edit")
        if not isinstance(operation, str) or operation not in {"add", "replace", "remove", "reorder", "suppress", "unsuppress"}:
            raise InvalidModelError("operation must be add, replace, remove, reorder, suppress or unsuppress")
        if not isinstance(cascade, bool) or not isinstance(make_output, bool):
            raise InvalidModelError("cascade and make_output must be booleans")
        if ordered_feature_ids is not None and not isinstance(ordered_feature_ids, tuple):
            raise InvalidModelError("ordered_feature_ids must be an immutable tuple")
        if operation != "reorder" and ordered_feature_ids is not None:
            raise InvalidModelError("ordered_feature_ids is only accepted for reorder")

        current = self.history_store.load(history_id)
        if current.revision != expected_revision:
            raise FeatureHistoryRevisionConflict(
                history_id, expected_revision, current.revision
            )

        if operation == "add":
            if not isinstance(feature, FeatureNode) or feature_id is not None or cascade:
                raise InvalidModelError("add requires feature and does not accept feature_id or cascade")
            updated = add_feature(current.history, feature, make_output=make_output)
        elif operation == "replace":
            if not isinstance(feature, FeatureNode) or not isinstance(feature_id, str):
                raise InvalidModelError("replace requires feature and feature_id")
            if cascade or make_output:
                raise InvalidModelError("replace does not accept cascade or make_output")
            updated = replace_feature(current.history, feature_id, feature)
        elif operation == "remove":
            if feature is not None or not isinstance(feature_id, str) or make_output:
                raise InvalidModelError("remove requires feature_id and does not accept feature or make_output")
            updated = remove_feature(current.history, feature_id, cascade=cascade)
        elif operation == "reorder":
            if feature is not None or feature_id is not None or cascade or make_output or not isinstance(ordered_feature_ids, tuple):
                raise InvalidModelError("reorder requires ordered_feature_ids and does not accept feature, feature_id, cascade or make_output")
            updated = reorder_features(current.history, ordered_feature_ids)
        elif operation == "suppress":
            if feature is not None or not isinstance(feature_id, str) or make_output:
                raise InvalidModelError("suppress requires feature_id and does not accept feature or make_output")
            updated = suppress_feature(current.history, feature_id, cascade=cascade)
        else:
            if feature is not None or not isinstance(feature_id, str) or cascade or make_output:
                raise InvalidModelError("unsuppress requires feature_id and does not accept cascade, feature or make_output")
            updated = unsuppress_feature(current.history, feature_id)

        return self.history_store.save(updated, expected_revision=expected_revision)

    def fork_history(
        self,
        history_id: str,
        *,
        branch_history_id: str,
        branch_name: str,
        revision: int | None = None,
    ) -> FeatureHistoryBranch:
        """Create an isolated branch from an immutable root-history revision."""
        return self.history_store.create_branch(
            history_id, branch_history_id, branch_name, fork_revision=revision
        )

    def merge_history_branch(
        self,
        source_branch_history_id: str,
        target_history_id: str,
        *,
        expected_source_revision: int,
        expected_target_revision: int,
    ) -> FeatureHistoryRevision:
        """Append a verified three-way branch merge to the target history."""
        return self.history_store.merge_branch(
            source_branch_history_id,
            target_history_id,
            expected_source_revision=expected_source_revision,
            expected_target_revision=expected_target_revision,
        )

    def get_revision(
        self,
        history_id: str,
        *,
        revision: int | None = None,
    ) -> FeatureHistoryRevision:
        return self.history_store.load(history_id, revision=revision)

    def list_revisions(self, history_id: str) -> tuple[int, ...]:
        return self.history_store.list_revisions(history_id)

    def get_navigation_state(self, history_id: str) -> FeatureHistoryNavigationState:
        """Return persistent Undo/Redo availability for the current source head."""
        return self.history_store.get_navigation_state(history_id)

    def undo_history(
        self, history_id: str, *, expected_revision: int
    ) -> FeatureHistoryRevision:
        """Append a new immutable revision restoring the next Undo target."""
        return self.history_store.undo(history_id, expected_revision=expected_revision)

    def redo_history(
        self, history_id: str, *, expected_revision: int
    ) -> FeatureHistoryRevision:
        """Append a new immutable revision restoring the next Redo target."""
        return self.history_store.redo(history_id, expected_revision=expected_revision)

    def regenerate(
        self,
        history_id: str,
        *,
        revision: int | None = None,
        solver_options: NonlinearSolverOptions | None = None,
    ) -> CADGeneratorRun:
        """Regenerate the requested immutable revision and return provenance."""
        source = self.history_store.load(history_id, revision=revision)
        result = regenerate_feature_history(
            source.history,
            solver_options=solver_options,
            artifact_cache=self.artifact_cache,
        )
        return CADGeneratorRun(source, result)
