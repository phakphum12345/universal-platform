"""Immutable resource identity, measurements and lifecycle models."""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from math import isfinite

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

@dataclass(frozen=True, slots=True)
class ResourceMetric:
    """A unit-bearing, non-negative resource measurement."""
    name: str
    value: float
    unit: str

    def __post_init__(self) -> None:
        if not self.name.strip() or not self.unit.strip():
            raise ValueError("metric name and unit must be non-empty")
        if isinstance(self.value, bool) or not isinstance(self.value, (int, float)):
            raise ValueError("metric value must be numeric")
        if not isfinite(float(self.value)) or self.value < 0:
            raise ValueError("metric value must be finite and non-negative")

    def to_dict(self) -> dict[str, object]:
        return {"name": self.name, "value": self.value, "unit": self.unit}

@dataclass(frozen=True, slots=True)
class ResourceSnapshot:
    """Immutable, timestamped measurements for one registered resource."""
    resource_id: str
    sequence: int
    captured_at: datetime
    metrics: tuple[ResourceMetric, ...]

    def __post_init__(self) -> None:
        if not self.resource_id.strip():
            raise ValueError("resource_id must be a non-empty string")
        if self.sequence < 1:
            raise ValueError("snapshot sequence must be positive")
        if self.captured_at.tzinfo is None or self.captured_at.utcoffset() is None:
            raise ValueError("captured_at must be timezone-aware")
        names = [metric.name for metric in self.metrics]
        if len(names) != len(set(names)):
            raise ValueError("snapshot metric names must be unique")

    def to_dict(self) -> dict[str, object]:
        return {
            "resource_id": self.resource_id,
            "sequence": self.sequence,
            "captured_at": self.captured_at.isoformat(),
            "metrics": [metric.to_dict() for metric in sorted(self.metrics, key=lambda item: item.name)],
        }
