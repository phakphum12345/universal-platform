"""Fail-closed recovery orchestration for one runtime component."""
from __future__ import annotations
from dataclasses import dataclass
from ..adapters.base import RepairExecutor, RuntimeAdapter
from ..health.log_analyzer import analyze_logs
from ..resources.models import ResourceState
from ..resources.registry import ResourceRegistry

@dataclass(frozen=True, slots=True)
class RecoveryResult:
    resource_id: str
    state: ResourceState
    repaired: bool
    resumed: bool
    event_count: int
    reason: str

class RecoveryCoordinator:
    """Coordinates sleep, diagnosis, sandboxed repair, validation and resume."""
    def __init__(self, registry: ResourceRegistry) -> None:
        self._registry = registry

    def recover(self, resource_id: str, log_text: str, *, adapter: RuntimeAdapter,
                repair_executor: RepairExecutor, source: str = "application") -> RecoveryResult:
        events = analyze_logs(log_text, source=source)
        if not events:
            raise ValueError("recovery requires at least one error log event")
        record = self._registry.get(resource_id)
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
                return self._quarantine(resource_id, len(events), "repair executor is not sandboxed")
            self._registry.transition(resource_id, ResourceState.REPAIRING)
            if not repair_executor.repair(resource_id, events):
                return self._quarantine(resource_id, len(events), "repair executor reported failure")
            self._registry.transition(resource_id, ResourceState.VALIDATING)
            if not adapter.health_check(resource_id):
                return self._quarantine(resource_id, len(events), "post-repair health check failed")
            self._registry.transition(resource_id, ResourceState.CANARY)
            if not adapter.canary_check(resource_id):
                return self._quarantine(resource_id, len(events), "canary check failed")
            adapter.resume(resource_id)
            self._registry.transition(resource_id, ResourceState.ACTIVE)
            return RecoveryResult(resource_id, ResourceState.ACTIVE, True, True, len(events), "recovery validated")
        except Exception as exc:
            try:
                adapter.rollback(resource_id)
            finally:
                current = self._registry.get(resource_id)
                if current.state is not ResourceState.QUARANTINED:
                    self._registry.transition(resource_id, ResourceState.QUARANTINED)
            return RecoveryResult(resource_id, ResourceState.QUARANTINED, False, False, len(events), f"recovery exception: {type(exc).__name__}")

    def _quarantine(self, resource_id: str, event_count: int, reason: str) -> RecoveryResult:
        self._registry.transition(resource_id, ResourceState.QUARANTINED)
        return RecoveryResult(resource_id, ResourceState.QUARANTINED, False, False, event_count, reason)
