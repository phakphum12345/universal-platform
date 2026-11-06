"""Fail-closed recovery orchestration with optional log and evidence adapters."""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol
from uuid import uuid4
from ..adapters.base import RepairExecutor, RuntimeAdapter
from ..evidence.recovery_records import RecoveryEvidenceRecord
from ..health.log_analyzer import LogEvent, analyze_logs
from ..resources.models import ResourceState
from ..resources.registry import ResourceRegistry

class LogSource(Protocol):
    source_id: str
    def read_text(self, relative_path: str) -> str: ...

class RecoveryEvidenceSink(Protocol):
    def append(self, record: RecoveryEvidenceRecord) -> None: ...

@dataclass(frozen=True, slots=True)
class RecoveryResult:
    resource_id: str
    state: ResourceState
    repaired: bool
    resumed: bool
    event_count: int
    reason: str
    evidence_recorded: bool = False

class RecoveryCoordinator:
    """Coordinates sleep, diagnosis, sandboxed repair, validation and resume."""
    def __init__(self, registry: ResourceRegistry, *, evidence_store: RecoveryEvidenceSink | None = None) -> None:
        self._registry = registry
        self._evidence_store = evidence_store

    def recover_from_source(self, resource_id: str, relative_path: str, *, log_source: LogSource,
                            adapter: RuntimeAdapter, repair_executor: RepairExecutor) -> RecoveryResult:
        """Read a bounded configured log source and run the same guarded recovery flow."""
        return self.recover(
            resource_id, log_source.read_text(relative_path), adapter=adapter,
            repair_executor=repair_executor, source=log_source.source_id,
        )

    def recover(self, resource_id: str, log_text: str, *, adapter: RuntimeAdapter,
                repair_executor: RepairExecutor, source: str = "application") -> RecoveryResult:
        events = analyze_logs(log_text, source=source)
        if not events:
            raise ValueError("recovery requires at least one error log event")
        record = self._registry.get(resource_id)
        initial_state = record.state
        if record.adapter_id != adapter.adapter_id or record.resource_kind != adapter.resource_kind:
            raise ValueError("runtime adapter does not match the registered resource")
        if not set(record.required_capabilities).issubset(adapter.capabilities):
            raise ValueError("runtime adapter does not satisfy registered capabilities")
        if any(event.component_id not in (None, resource_id) for event in events):
            raise ValueError("log evidence contains events for a different component")
        if record.state not in (ResourceState.ACTIVE, ResourceState.SUSPECT):
            raise RuntimeError("resource is not eligible for recovery from its current state")
        self._registry.transition(resource_id, ResourceState.QUIESCING)
        try:
            adapter.quiesce(resource_id)
            self._registry.transition(resource_id, ResourceState.SLEEP)
            self._registry.transition(resource_id, ResourceState.DIAGNOSING)
            if not repair_executor.sandboxed:
                return self._quarantine(resource_id, events, initial_state, "repair executor is not sandboxed")
            self._registry.transition(resource_id, ResourceState.REPAIRING)
            if not repair_executor.repair(resource_id, events):
                return self._rollback_and_quarantine(resource_id, events, initial_state, "repair executor reported failure", adapter)
            self._registry.transition(resource_id, ResourceState.VALIDATING)
            if not adapter.health_check(resource_id):
                return self._rollback_and_quarantine(resource_id, events, initial_state, "post-repair health check failed", adapter)
            self._registry.transition(resource_id, ResourceState.CANARY)
            if not adapter.canary_check(resource_id):
                return self._rollback_and_quarantine(resource_id, events, initial_state, "canary check failed", adapter)
            if self._evidence_store is not None:
                pending = RecoveryResult(resource_id, ResourceState.CANARY, True, False, len(events), "validation passed; resume pending")
                pending = self._persist_result(pending, events, initial_state)
                if not pending.evidence_recorded:
                    return self._rollback_and_quarantine(resource_id, events, initial_state, "pre-resume evidence unavailable", adapter)
            adapter.resume(resource_id)
            self._registry.transition(resource_id, ResourceState.ACTIVE)
            result = RecoveryResult(resource_id, ResourceState.ACTIVE, True, True, len(events), "recovery validated")
            return self._persist_result(result, events, initial_state, adapter)
        except Exception as exc:
            return self._rollback_and_quarantine(resource_id, events, initial_state, f"recovery exception: {type(exc).__name__}", adapter)

    def _persist_result(self, result: RecoveryResult, events: tuple[LogEvent, ...],
                        initial_state: ResourceState, adapter: RuntimeAdapter | None = None) -> RecoveryResult:
        if self._evidence_store is None:
            return result
        record = RecoveryEvidenceRecord(
            record_id=uuid4().hex,
            resource_id=result.resource_id,
            captured_at=datetime.now(timezone.utc),
            event_fingerprints=tuple(event.fingerprint for event in events),
            initial_state=initial_state.value,
            final_state=result.state.value,
            repaired=result.repaired,
            resumed=result.resumed,
            reason=result.reason,
        )
        try:
            self._evidence_store.append(record)
            return RecoveryResult(result.resource_id, result.state, result.repaired, result.resumed,
                                  result.event_count, result.reason, True)
        except Exception as exc:
            reason = f"evidence persistence failed: {type(exc).__name__}"
            if result.resumed:
                try:
                    if adapter is not None:
                        adapter.rollback(result.resource_id)
                except Exception:
                    reason += "; rollback failed"
                current = self._registry.get(result.resource_id)
                if current.state is not ResourceState.QUARANTINED:
                    self._registry.transition(result.resource_id, ResourceState.QUARANTINED)
                return RecoveryResult(result.resource_id, ResourceState.QUARANTINED, False, False,
                                      result.event_count, reason, False)
            return RecoveryResult(result.resource_id, result.state, result.repaired, result.resumed,
                                  result.event_count, f"{result.reason}; {reason}", False)

    def _quarantine(self, resource_id: str, events: tuple[LogEvent, ...], initial_state: ResourceState,
                    reason: str) -> RecoveryResult:
        self._registry.transition(resource_id, ResourceState.QUARANTINED)
        result = RecoveryResult(resource_id, ResourceState.QUARANTINED, False, False, len(events), reason)
        return self._persist_result(result, events, initial_state)

    def _rollback_and_quarantine(self, resource_id: str, events: tuple[LogEvent, ...],
                                 initial_state: ResourceState, reason: str,
                                 adapter: RuntimeAdapter) -> RecoveryResult:
        try:
            adapter.rollback(resource_id)
        except Exception:
            reason += "; rollback failed"
        current = self._registry.get(resource_id)
        if current.state is not ResourceState.QUARANTINED:
            self._registry.transition(resource_id, ResourceState.QUARANTINED)
        result = RecoveryResult(resource_id, ResourceState.QUARANTINED, False, False, len(events), reason)
        return self._persist_result(result, events, initial_state)
