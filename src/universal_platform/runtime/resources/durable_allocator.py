"""Journal-backed resource reservations with cross-process admission serialization."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import json
from math import isfinite
from pathlib import Path
from typing import Iterable
from uuid import uuid4

from ..evidence.jsonl_journal import JsonlHashChainJournal
from .models import ResourceMetric


@dataclass(frozen=True, slots=True)
class DurableResourceLease:
    lease_id: str
    owner_id: str
    allocations: tuple[ResourceMetric, ...]
    acquired_at: datetime
    expires_at: datetime | None
    lease_kind: str = "ordinary"
    host_instance_id: str | None = None
    worker_id: str | None = None

    def __post_init__(self) -> None:
        if not self.lease_id.strip() or not self.owner_id.strip():
            raise ValueError("lease_id and owner_id must be non-empty")
        if self.acquired_at.tzinfo is None or self.acquired_at.utcoffset() is None:
            raise ValueError("lease timestamps must be timezone-aware")
        if self.expires_at is not None:
            if self.expires_at.tzinfo is None or self.expires_at.utcoffset() is None:
                raise ValueError("lease timestamps must be timezone-aware")
            if self.expires_at <= self.acquired_at:
                raise ValueError("lease expiry must follow acquisition")
        if self.lease_kind not in {"ordinary", "supervised_worker"}:
            raise ValueError("unsupported lease_kind")
        if self.lease_kind == "supervised_worker":
            if self.expires_at is not None:
                raise ValueError("supervised worker leases must not expire by TTL")
            if not self.host_instance_id or not self.worker_id:
                raise ValueError("supervised worker leases require host_instance_id and worker_id")
        names = [item.name for item in self.allocations]
        if len(names) != len(set(names)):
            raise ValueError("lease allocation metric names must be unique")


class DurableResourceAllocator:
    """Durable quota pool; all admissions replay and append under one shared lock.

    The journal's hash chain protects against accidental corruption. It is not
    an authenticated trust anchor against a privileged actor who can rewrite
    the journal and recompute the chain.
    """

    _SCHEMA_VERSION = 1

    def __init__(
        self,
        root: str | Path,
        capacity: Iterable[ResourceMetric],
        *,
        pool_id: str = "local",
        max_record_bytes: int = 65_536,
        max_store_bytes: int = 16_777_216,
    ) -> None:
        if not isinstance(pool_id, str) or not pool_id.strip():
            raise ValueError("pool_id must be non-empty")
        items = tuple(capacity)
        if not items:
            raise ValueError("at least one capacity metric is required")
        if len({item.name for item in items}) != len(items):
            raise ValueError("capacity metric names must be unique")
        self.pool_id = pool_id
        self._capacity = {item.name: item for item in items}
        canonical = [item.to_dict() for item in sorted(items, key=lambda metric: metric.name)]
        self._capacity_fingerprint = hashlib.sha256(
            json.dumps(canonical, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
        ).hexdigest()
        filename = f"worker-leases-{hashlib.sha256(pool_id.encode('utf-8')).hexdigest()[:20]}.jsonl"
        self._journal = JsonlHashChainJournal(
            root,
            filename=filename,
            max_record_bytes=max_record_bytes,
            max_store_bytes=max_store_bytes,
        )

        def initialize(records):
            if not records:
                return (self._event("POOL_INITIALIZED", {
                    "capacity": canonical,
                    "capacity_fingerprint": self._capacity_fingerprint,
                }),)
            self._validate_pool(records)
            return ()

        self._journal.append_transaction(initialize)

    def allocate(
        self,
        owner_id: str,
        requested: Iterable[ResourceMetric],
        *,
        ttl_seconds: float | None = 60.0,
        now: datetime | None = None,
        lease_kind: str = "ordinary",
        host_instance_id: str | None = None,
        worker_id: str | None = None,
    ) -> DurableResourceLease:
        if not isinstance(owner_id, str) or not owner_id.strip():
            raise ValueError("owner_id must be non-empty")
        if ttl_seconds is not None and (
            isinstance(ttl_seconds, bool)
            or not isinstance(ttl_seconds, (int, float))
            or not isfinite(ttl_seconds)
            or ttl_seconds <= 0
        ):
            raise ValueError("ttl_seconds must be finite and positive, or None")
        if lease_kind not in {"ordinary", "supervised_worker"}:
            raise ValueError("unsupported lease_kind")
        if lease_kind == "supervised_worker":
            if ttl_seconds is not None:
                raise ValueError("supervised worker leases must use ttl_seconds=None")
            if not host_instance_id or not worker_id:
                raise ValueError("supervised worker leases require host_instance_id and worker_id")
        elif host_instance_id is not None or worker_id is not None:
            raise ValueError("worker identity fields are only valid for supervised worker leases")
        captured = now or datetime.now(timezone.utc)
        if captured.tzinfo is None or captured.utcoffset() is None:
            raise ValueError("now must be timezone-aware")
        amounts = tuple(requested)
        if not amounts:
            raise ValueError("at least one resource amount is required")
        if len({item.name for item in amounts}) != len(amounts):
            raise ValueError("requested metric names must be unique")
        for item in amounts:
            available = self._capacity.get(item.name)
            if available is None:
                raise ValueError(f"unknown capacity metric: {item.name}")
            if item.unit != available.unit:
                raise ValueError(f"unit mismatch for capacity metric: {item.name}")

        lease_id = uuid4().hex
        lease = DurableResourceLease(
            lease_id=lease_id,
            owner_id=owner_id,
            allocations=amounts,
            acquired_at=captured,
            expires_at=(captured + timedelta(seconds=float(ttl_seconds)) if ttl_seconds is not None else None),
            lease_kind=lease_kind,
            host_instance_id=host_instance_id,
            worker_id=worker_id,
        )
        result: dict[str, object] = {}

        def reserve(records):
            self._validate_pool(records)
            state, quarantined = self._replay(records)
            events = self._expiry_events(state, quarantined, captured)
            for event in events:
                self._apply_event(state, quarantined, event)
            used = {name: 0.0 for name in self._capacity}
            for active in state.values():
                for metric in active.allocations:
                    used[metric.name] += metric.value
            for metric in amounts:
                if used[metric.name] + metric.value > self._capacity[metric.name].value:
                    raise RuntimeError(f"resource capacity exceeded: {metric.name}")
            events.append(self._event("LEASE_ACQUIRED", self._lease_payload(lease)))
            result["lease"] = lease
            return tuple(events)

        self._journal.append_transaction(reserve)
        return result["lease"]  # type: ignore[return-value]

    def allocate_worker(
        self,
        owner_id: str,
        requested: Iterable[ResourceMetric],
        *,
        host_instance_id: str,
        worker_id: str,
        now: datetime | None = None,
    ) -> DurableResourceLease:
        """Persist a non-expiring supervised-worker lease with its reserved identity."""
        return self.allocate(
            owner_id,
            requested,
            ttl_seconds=None,
            now=now,
            lease_kind="supervised_worker",
            host_instance_id=host_instance_id,
            worker_id=worker_id,
        )

    def quarantine(self, lease_id: str, reason: str) -> bool:
        if not isinstance(reason, str) or not reason.strip():
            raise ValueError("quarantine reason must be a non-empty string")
        result = {"changed": False}

        def update(records):
            self._validate_pool(records)
            state, quarantined = self._replay(records)
            if lease_id not in state:
                return ()
            if lease_id in quarantined:
                if quarantined[lease_id] != reason.strip():
                    raise RuntimeError("lease is already quarantined with a different reason")
                return ()
            result["changed"] = True
            return (self._event("LEASE_QUARANTINED", {
                "lease_id": lease_id,
                "reason": reason.strip(),
            }),)

        self._journal.append_transaction(update)
        return bool(result["changed"])

    def release(self, lease_id: str) -> bool:
        result = {"changed": False}

        def update(records):
            self._validate_pool(records)
            state, quarantined = self._replay(records)
            if lease_id not in state:
                return ()
            if lease_id in quarantined:
                raise RuntimeError("quarantined lease requires audited operator recovery")
            result["changed"] = True
            return (self._event("LEASE_RELEASED", {
                "lease_id": lease_id,
                "reason": "confirmed_release",
            }),)

        self._journal.append_transaction(update)
        return bool(result["changed"])

    def active_leases(self, *, now: datetime | None = None) -> tuple[DurableResourceLease, ...]:
        captured = now or datetime.now(timezone.utc)
        if captured.tzinfo is None or captured.utcoffset() is None:
            raise ValueError("now must be timezone-aware")
        result: dict[str, tuple[DurableResourceLease, ...]] = {}

        def expire(records):
            self._validate_pool(records)
            state, quarantined = self._replay(records)
            events = self._expiry_events(state, quarantined, captured)
            for event in events:
                self._apply_event(state, quarantined, event)
            result["leases"] = tuple(state[key] for key in sorted(state))
            return tuple(events)

        self._journal.append_transaction(expire)
        return result["leases"]

    def quarantined_leases(self) -> tuple[tuple[DurableResourceLease, str], ...]:
        records = self._journal.read_all()
        self._validate_pool(records)
        state, quarantined = self._replay(records)
        return tuple((state[key], quarantined[key]) for key in sorted(quarantined) if key in state)

    def capacity(self) -> tuple[ResourceMetric, ...]:
        """Return the immutable host-configured pool capacity."""
        return tuple(self._capacity[key] for key in sorted(self._capacity))

    def available(self, *, now: datetime | None = None) -> tuple[ResourceMetric, ...]:
        leases = self.active_leases(now=now)
        used = {name: 0.0 for name in self._capacity}
        for lease in leases:
            for metric in lease.allocations:
                used[metric.name] += metric.value
        return tuple(
            ResourceMetric(name, max(0.0, metric.value - used[name]), metric.unit)
            for name, metric in sorted(self._capacity.items())
        )

    def verify(self) -> tuple[int, int, str]:
        records = self._journal.read_all()
        self._validate_pool(records)
        self._replay(records)
        return self._journal.verify()

    def _event(self, event_type: str, payload: dict[str, object]) -> dict[str, object]:
        return {
            "schema_version": self._SCHEMA_VERSION,
            "pool_id": self.pool_id,
            "event_id": uuid4().hex,
            "event_type": event_type,
            "occurred_at": datetime.now(timezone.utc).isoformat(),
            **payload,
        }

    @staticmethod
    def _lease_payload(lease: DurableResourceLease) -> dict[str, object]:
        return {
            "lease_id": lease.lease_id,
            "owner_id": lease.owner_id,
            "allocations": [item.to_dict() for item in lease.allocations],
            "acquired_at": lease.acquired_at.isoformat(),
            "expires_at": lease.expires_at.isoformat() if lease.expires_at else None,
            "lease_kind": lease.lease_kind,
            "host_instance_id": lease.host_instance_id,
            "worker_id": lease.worker_id,
        }

    def _validate_pool(self, records) -> None:
        if not records:
            raise ValueError("durable resource pool has no initialization event")
        first = records[0]
        if first.get("event_type") != "POOL_INITIALIZED":
            raise ValueError("durable resource pool must begin with POOL_INITIALIZED")
        if first.get("schema_version") != self._SCHEMA_VERSION or first.get("pool_id") != self.pool_id:
            raise ValueError("durable resource pool identity or schema mismatch")
        if first.get("capacity_fingerprint") != self._capacity_fingerprint:
            raise ValueError("durable resource pool capacity configuration mismatch")
        for record in records:
            if record.get("schema_version") != self._SCHEMA_VERSION or record.get("pool_id") != self.pool_id:
                raise ValueError("durable resource journal contains an incompatible event")

    def _replay(self, records):
        state: dict[str, DurableResourceLease] = {}
        quarantined: dict[str, str] = {}
        for record in records[1:]:
            event_type = record.get("event_type")
            lease_id = record.get("lease_id")
            if event_type == "LEASE_ACQUIRED":
                lease = self._lease_from_payload(record)
                if lease.lease_id in state:
                    raise ValueError("durable journal repeats an active lease ID")
                state[lease.lease_id] = lease
            elif event_type == "LEASE_QUARANTINED":
                if not isinstance(lease_id, str) or lease_id not in state:
                    raise ValueError("durable journal quarantines an unknown lease")
                reason = record.get("reason")
                if not isinstance(reason, str) or not reason.strip():
                    raise ValueError("durable journal quarantine reason is invalid")
                quarantined[lease_id] = reason
            elif event_type == "LEASE_RELEASED":
                if not isinstance(lease_id, str) or lease_id not in state:
                    raise ValueError("durable journal releases an unknown lease")
                if lease_id in quarantined:
                    raise ValueError("durable journal releases a quarantined lease without operator audit")
                del state[lease_id]
            else:
                raise ValueError(f"unsupported durable lease event: {event_type}")
        return state, quarantined

    @staticmethod
    def _lease_from_payload(record) -> DurableResourceLease:
        try:
            allocations = tuple(
                ResourceMetric(item["name"], item["value"], item["unit"])
                for item in record["allocations"]
            )
            acquired_at = datetime.fromisoformat(record["acquired_at"])
            expires_at = datetime.fromisoformat(record["expires_at"]) if record.get("expires_at") else None
            return DurableResourceLease(
                lease_id=record["lease_id"],
                owner_id=record["owner_id"],
                allocations=allocations,
                acquired_at=acquired_at,
                expires_at=expires_at,
                lease_kind=record.get("lease_kind", "ordinary"),
                host_instance_id=record.get("host_instance_id"),
                worker_id=record.get("worker_id"),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("durable lease acquisition event is invalid") from exc

    def _expiry_events(self, state, quarantined, now: datetime):
        return [
            self._event("LEASE_RELEASED", {
                "lease_id": lease_id,
                "reason": "ttl_expired",
            })
            for lease_id, lease in sorted(state.items())
            if lease_id not in quarantined
            and lease.lease_kind == "ordinary"
            and lease.expires_at is not None
            and lease.expires_at <= now
        ]

    @staticmethod
    def _apply_event(state, quarantined, event):
        if event["event_type"] == "LEASE_RELEASED":
            state.pop(event["lease_id"], None)
            quarantined.pop(event["lease_id"], None)


__all__ = ["DurableResourceAllocator", "DurableResourceLease"]
