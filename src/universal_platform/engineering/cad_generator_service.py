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
    FeatureRegenerationResult,
    regenerate_feature_history,
)
from .feature_history_store import (
    FeatureHistoryRevision,
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

    def get_revision(
        self,
        history_id: str,
        *,
        revision: int | None = None,
    ) -> FeatureHistoryRevision:
        return self.history_store.load(history_id, revision=revision)

    def list_revisions(self, history_id: str) -> tuple[int, ...]:
        return self.history_store.list_revisions(history_id)

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
