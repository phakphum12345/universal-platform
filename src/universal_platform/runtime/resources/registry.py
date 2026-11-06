"""Thread-safe registry with guarded lifecycle transitions."""
from __future__ import annotations
from threading import RLock
from .models import ResourceRecord, ResourceState

_ALLOWED = {
 ResourceState.ACTIVE: {ResourceState.SUSPECT, ResourceState.QUIESCING},
 ResourceState.SUSPECT: {ResourceState.QUIESCING, ResourceState.QUARANTINED},
 ResourceState.QUIESCING: {ResourceState.SLEEP, ResourceState.QUARANTINED},
 ResourceState.SLEEP: {ResourceState.DIAGNOSING, ResourceState.QUARANTINED},
 ResourceState.DIAGNOSING: {ResourceState.REPAIRING, ResourceState.QUARANTINED},
 ResourceState.REPAIRING: {ResourceState.VALIDATING, ResourceState.QUARANTINED},
 ResourceState.VALIDATING: {ResourceState.CANARY, ResourceState.QUARANTINED},
 ResourceState.CANARY: {ResourceState.ACTIVE, ResourceState.QUARANTINED},
 ResourceState.QUARANTINED: set(),
}

class ResourceRegistry:
    """Central typed registry; updates are atomic within this process."""
    def __init__(self) -> None:
        self._records: dict[str, ResourceRecord] = {}
        self._lock = RLock()

    def register(self, record: ResourceRecord) -> None:
        with self._lock:
            if record.resource_id in self._records:
                raise ValueError(f"resource already registered: {record.resource_id}")
            self._records[record.resource_id] = record

    def get(self, resource_id: str) -> ResourceRecord:
        with self._lock:
            try:
                return self._records[resource_id]
            except KeyError as exc:
                raise KeyError(f"unknown resource: {resource_id}") from exc

    def snapshot(self) -> tuple[ResourceRecord, ...]:
        with self._lock:
            return tuple(self._records[key] for key in sorted(self._records))

    def transition(self, resource_id: str, target: ResourceState, *, expected: ResourceState | None = None) -> ResourceRecord:
        with self._lock:
            current = self.get(resource_id)
            if expected is not None and current.state is not expected:
                raise RuntimeError(f"stale resource state: expected {expected.value}, found {current.state.value}")
            if target not in _ALLOWED[current.state]:
                raise ValueError(f"invalid resource transition: {current.state.value} -> {target.value}")
            updated = current.with_state(target)
            self._records[resource_id] = updated
            return updated

    def replace_adapter(self, resource_id: str, *, adapter_id: str, adapter_kind: str,
                        adapter_capabilities: tuple[str, ...]) -> ResourceRecord:
        with self._lock:
            current = self.get(resource_id)
            if current.state is not ResourceState.SLEEP:
                raise RuntimeError("adapter replacement requires the resource to be asleep")
            if adapter_kind != current.resource_kind:
                raise ValueError("replacement adapter kind is incompatible")
            if not set(current.required_capabilities).issubset(adapter_capabilities):
                raise ValueError("replacement adapter lacks required capabilities")
            updated = current.with_adapter(adapter_id)
            self._records[resource_id] = updated
            return updated
