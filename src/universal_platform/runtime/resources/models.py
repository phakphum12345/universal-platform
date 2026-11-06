"""Immutable resource identity and lifecycle models."""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum

class ResourceState(str, Enum):
    ACTIVE = "ACTIVE"
    SUSPECT = "SUSPECT"
    QUIESCING = "QUIESCING"
    SLEEP = "SLEEP"
    DIAGNOSING = "DIAGNOSING"
    REPAIRING = "REPAIRING"
    VALIDATING = "VALIDATING"
    CANARY = "CANARY"
    QUARANTINED = "QUARANTINED"

@dataclass(frozen=True, slots=True)
class ResourceRecord:
    resource_id: str
    resource_kind: str
    adapter_id: str
    required_capabilities: tuple[str, ...] = ()
    state: ResourceState = ResourceState.ACTIVE
    generation: int = 0

    def __post_init__(self) -> None:
        for name in ("resource_id", "resource_kind", "adapter_id"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be a non-empty string")
        if len(set(self.required_capabilities)) != len(self.required_capabilities):
            raise ValueError("required_capabilities must be unique")
        if any(not item.strip() for item in self.required_capabilities):
            raise ValueError("required_capabilities must not contain empty values")
        if self.generation < 0:
            raise ValueError("generation must be non-negative")

    def with_state(self, state: ResourceState) -> "ResourceRecord":
        return ResourceRecord(self.resource_id, self.resource_kind, self.adapter_id,
                              self.required_capabilities, state, self.generation + 1)

    def with_adapter(self, adapter_id: str) -> "ResourceRecord":
        if not adapter_id.strip():
            raise ValueError("adapter_id must be a non-empty string")
        return ResourceRecord(self.resource_id, self.resource_kind, adapter_id,
                              self.required_capabilities, self.state, self.generation + 1)
