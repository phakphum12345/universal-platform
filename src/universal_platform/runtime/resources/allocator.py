"""Thread-safe quota allocator with expiring, explicit resource leases."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from math import isfinite
from threading import RLock
from typing import Iterable
from uuid import uuid4

from .models import ResourceMetric


@dataclass(frozen=True, slots=True)
class ResourceLease:
    lease_id: str
    owner_id: str
    allocations: tuple[ResourceMetric, ...]
    acquired_at: datetime
    expires_at: datetime

    def __post_init__(self) -> None:
        if not self.lease_id.strip() or not self.owner_id.strip():
            raise ValueError("lease_id and owner_id must be non-empty")
        for value in (self.acquired_at, self.expires_at):
            if value.tzinfo is None or value.utcoffset() is None:
                raise ValueError("lease timestamps must be timezone-aware")
        if self.expires_at <= self.acquired_at:
            raise ValueError("lease expiry must follow acquisition")
        names = [item.name for item in self.allocations]
        if len(names) != len(set(names)):
            raise ValueError("lease allocation metric names must be unique")


class ResourceAllocator:
    """In-memory quota pool; reservations are atomic within this process."""

    def __init__(self, capacity: Iterable[ResourceMetric], *, pool_id: str = "local") -> None:
        if not pool_id.strip():
            raise ValueError("pool_id must be non-empty")
        items = tuple(capacity)
        if not items:
            raise ValueError("at least one capacity metric is required")
        if len({item.name for item in items}) != len(items):
            raise ValueError("capacity metric names must be unique")
        self.pool_id = pool_id
        self._capacity = {item.name: item for item in items}
        self._leases: dict[str, ResourceLease] = {}
        self._lock = RLock()

    def capacity(self) -> tuple[ResourceMetric, ...]:
        return tuple(self._capacity[key] for key in sorted(self._capacity))

    def allocate(
        self,
        owner_id: str,
        requested: Iterable[ResourceMetric],
        *,
        ttl_seconds: float = 60.0,
        now: datetime | None = None,
    ) -> ResourceLease:
        if not owner_id.strip():
            raise ValueError("owner_id must be non-empty")
        if isinstance(ttl_seconds, bool) or not isinstance(ttl_seconds, (int, float)) or not isfinite(ttl_seconds) or ttl_seconds <= 0:
            raise ValueError("ttl_seconds must be finite and positive")
        captured = now or datetime.now(timezone.utc)
        if captured.tzinfo is None or captured.utcoffset() is None:
            raise ValueError("now must be timezone-aware")
        amounts = tuple(requested)
        if not amounts:
            raise ValueError("at least one resource amount is required")
        if len({item.name for item in amounts}) != len(amounts):
            raise ValueError("requested metric names must be unique")
        with self._lock:
            self._expire(captured)
            used = {name: 0.0 for name in self._capacity}
            for lease in self._leases.values():
                for item in lease.allocations:
                    used[item.name] += item.value
            for item in amounts:
                available = self._capacity.get(item.name)
                if available is None:
                    raise ValueError(f"unknown capacity metric: {item.name}")
                if item.unit != available.unit:
                    raise ValueError(f"unit mismatch for capacity metric: {item.name}")
                if used[item.name] + item.value > available.value:
                    raise RuntimeError(f"resource capacity exceeded: {item.name}")
            lease = ResourceLease(
                lease_id=uuid4().hex,
                owner_id=owner_id,
                allocations=amounts,
                acquired_at=captured,
                expires_at=captured + timedelta(seconds=float(ttl_seconds)),
            )
            self._leases[lease.lease_id] = lease
            return lease

    def release(self, lease_id: str) -> bool:
        with self._lock:
            return self._leases.pop(lease_id, None) is not None

    def active_leases(self, *, now: datetime | None = None) -> tuple[ResourceLease, ...]:
        captured = now or datetime.now(timezone.utc)
        if captured.tzinfo is None or captured.utcoffset() is None:
            raise ValueError("now must be timezone-aware")
        with self._lock:
            self._expire(captured)
            return tuple(self._leases[key] for key in sorted(self._leases))

    def available(self, *, now: datetime | None = None) -> tuple[ResourceMetric, ...]:
        captured = now or datetime.now(timezone.utc)
        if captured.tzinfo is None or captured.utcoffset() is None:
            raise ValueError("now must be timezone-aware")
        with self._lock:
            self._expire(captured)
            used = {name: 0.0 for name in self._capacity}
            for lease in self._leases.values():
                for item in lease.allocations:
                    used[item.name] += item.value
            return tuple(
                ResourceMetric(name, max(0.0, item.value - used[name]), item.unit)
                for name, item in sorted(self._capacity.items())
            )

    def _expire(self, now: datetime) -> None:
        expired = [key for key, lease in self._leases.items() if lease.expires_at <= now]
        for key in expired:
            del self._leases[key]
