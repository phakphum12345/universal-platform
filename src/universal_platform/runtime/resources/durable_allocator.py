"""Journal-backed resource reservations with cross-process admission serialization."""
from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone
import hashlib
import json
from math import isfinite
from pathlib import Path
from typing import Iterable
from uuid import uuid4

from ..evidence.jsonl_journal import JsonlHashChainJournal
from ..process_identity import ProcessIdentity
from ..process_reconciliation import (
    ProcessLiveness,
    ProcessLivenessEvidence,
    WorkerReconciliationResult,
)
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
    process_identity: ProcessIdentity | None = None

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
        if self.process_identity is not None:
            if self.lease_kind != "supervised_worker":
                raise ValueError("process identity is only valid for supervised worker leases")
            if not isinstance(self.process_identity, ProcessIdentity):
                raise ValueError("process_identity must be a ProcessIdentity")
            if (
                self.process_identity.host_instance_id != self.host_instance_id
                or self.process_identity.worker_id != self.worker_id
            ):
                raise ValueError("process identity does not match the supervised worker lease")
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
        records = self._journal.read_all()
        self._validate_pool(records)
        state, _quarantined = self._replay(records)
        self._startup_reconciliation_required = any(
            lease.lease_kind == "supervised_worker" for lease in state.values()
        )

    @property
    def startup_reconciliation_required(self) -> bool:
        return self._startup_reconciliation_required

    @property
    def is_ready(self) -> bool:
        return not self._startup_reconciliation_required

    def _ensure_ready(self) -> None:
        if self._startup_reconciliation_required:
            raise RuntimeError(
                "durable worker lease startup reconciliation is required before new admissions"
            )

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
        self._ensure_ready()
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
        if not amounts and lease_kind != "supervised_worker":
            raise ValueError("ordinary leases require at least one resource amount")
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

    def bind_process_identity(
        self,
        lease_id: str,
        identity: ProcessIdentity,
    ) -> DurableResourceLease:
        """Durably bind an OS identity to its matching, non-expiring worker lease.

        Repeating the exact same binding is idempotent. A different identity,
        mismatched worker/host, unknown lease, ordinary lease, or quarantined
        lease is rejected without changing the journal.
        """
        if not isinstance(lease_id, str) or not lease_id.strip():
            raise ValueError("lease_id must be a non-empty string")
        if not isinstance(identity, ProcessIdentity):
            raise ValueError("identity must be a ProcessIdentity")
        result: dict[str, DurableResourceLease] = {}

        def bind(records):
            self._validate_pool(records)
            state, quarantined = self._replay(records)
            lease = state.get(lease_id)
            if lease is None:
                raise ValueError("cannot bind process identity to an unknown lease")
            if lease.lease_kind != "supervised_worker":
                raise ValueError("process identity requires a supervised worker lease")
            if lease_id in quarantined:
                raise RuntimeError("cannot bind process identity to a quarantined lease")
            if (
                identity.host_instance_id != lease.host_instance_id
                or identity.worker_id != lease.worker_id
            ):
                raise ValueError("process identity does not match the lease host and worker")
            if lease.process_identity is not None:
                if lease.process_identity != identity:
                    raise RuntimeError("lease is already bound to a different process identity")
                result["lease"] = lease
                return ()
            bound = replace(lease, process_identity=identity)
            result["lease"] = bound
            return (self._event("LEASE_PROCESS_BOUND", {
                "lease_id": lease_id,
                "process_identity": identity.to_dict(),
            }),)

        self._journal.append_transaction(bind)
        return result["lease"]

    def reconcile_startup(
        self,
        inspector,
        *,
        current_host_instance_id: str,
    ) -> tuple[WorkerReconciliationResult, ...]:
        """Reconcile non-terminal worker leases before admitting new work.

        ABSENT identities receive a durable recovered-release event. PRESENT
        identities from this same host instance remain charged. PRESENT workers
        from another host and all UNKNOWN identities are quarantined. Existing
        quarantine is never cleared by startup reconciliation.
        """
        if not callable(getattr(inspector, "inspect", None)):
            raise ValueError("inspector must provide a callable inspect(identity) method")
        if (
            not isinstance(current_host_instance_id, str)
            or not current_host_instance_id.strip()
            or "\\x00" in current_host_instance_id
        ):
            raise ValueError("current_host_instance_id must be a non-empty NUL-free string")
        outcomes: list[WorkerReconciliationResult] = []

        def reconcile(records):
            self._validate_pool(records)
            state, quarantined = self._replay(records)
            events = []
            for lease_id, lease in sorted(state.items()):
                if lease.lease_kind != "supervised_worker":
                    continue
                evidence: ProcessLivenessEvidence | None = None
                if lease.process_identity is None:
                    status = ProcessLiveness.UNKNOWN
                    reason = "worker lease has no recorded OS process identity"
                else:
                    try:
                        candidate = inspector.inspect(lease.process_identity)
                        if (
                            isinstance(candidate, ProcessLivenessEvidence)
                            and candidate.identity == lease.process_identity
                        ):
                            evidence = candidate
                            status = candidate.status
                            reason = candidate.reason
                        else:
                            status = ProcessLiveness.UNKNOWN
                            reason = "process inspector returned invalid or mismatched evidence"
                    except Exception as error:
                        status = ProcessLiveness.UNKNOWN
                        reason = f"process liveness inspection failed ({error.__class__.__name__})"

                if lease_id in quarantined:
                    outcomes.append(WorkerReconciliationResult(
                        lease_id, status, "retained_quarantine", reason, evidence
                    ))
                    continue
                if status is ProcessLiveness.ABSENT and evidence is not None:
                    events.append(self._event("LEASE_RECOVERED_RELEASED", {
                        "lease_id": lease_id,
                        "evidence": evidence.to_dict(),
                    }))
                    outcomes.append(WorkerReconciliationResult(
                        lease_id, status, "released", reason, evidence
                    ))
                elif status is ProcessLiveness.PRESENT and lease.host_instance_id == current_host_instance_id:
                    outcomes.append(WorkerReconciliationResult(
                        lease_id, status, "retained", reason, evidence
                    ))
                else:
                    quarantine_reason = (
                        "startup reconciliation: worker is PRESENT but belongs to another host instance; "
                        "automatic adoption is disabled"
                        if status is ProcessLiveness.PRESENT
                        else f"startup reconciliation: {reason or 'process liveness is UNKNOWN'}"
                    )
                    events.append(self._event("LEASE_QUARANTINED", {
                        "lease_id": lease_id,
                        "reason": quarantine_reason,
                    }))
                    outcomes.append(WorkerReconciliationResult(
                        lease_id, status, "quarantined", quarantine_reason, evidence
                    ))
            return tuple(events)

        self._journal.append_transaction(reconcile)
        self._startup_reconciliation_required = False
        return tuple(outcomes)

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
        self._ensure_ready()
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
            "process_identity": (
                lease.process_identity.to_dict() if lease.process_identity is not None else None
            ),
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
            elif event_type == "LEASE_PROCESS_BOUND":
                if not isinstance(lease_id, str) or lease_id not in state:
                    raise ValueError("durable journal binds an unknown lease identity")
                lease = state[lease_id]
                if lease.lease_kind != "supervised_worker" or lease.process_identity is not None:
                    raise ValueError("durable journal contains an invalid process identity binding")
                if lease_id in quarantined:
                    raise ValueError("durable journal binds a quarantined worker lease")
                try:
                    identity = ProcessIdentity(**record["process_identity"])
                    state[lease_id] = replace(lease, process_identity=identity)
                except (KeyError, TypeError, ValueError) as exc:
                    raise ValueError("durable journal process identity binding is invalid") from exc
            elif event_type == "LEASE_QUARANTINED":
                if not isinstance(lease_id, str) or lease_id not in state:
                    raise ValueError("durable journal quarantines an unknown lease")
                reason = record.get("reason")
                if not isinstance(reason, str) or not reason.strip():
                    raise ValueError("durable journal quarantine reason is invalid")
                quarantined[lease_id] = reason
            elif event_type in {"LEASE_RELEASED", "LEASE_RECOVERED_RELEASED"}:
                if not isinstance(lease_id, str) or lease_id not in state:
                    raise ValueError("durable journal releases an unknown lease")
                if lease_id in quarantined:
                    raise ValueError("durable journal releases a quarantined lease without operator audit")
                if event_type == "LEASE_RECOVERED_RELEASED":
                    lease = state[lease_id]
                    evidence = record.get("evidence")
                    if (
                        lease.lease_kind != "supervised_worker"
                        or lease.process_identity is None
                        or not isinstance(evidence, dict)
                        or evidence.get("status") != ProcessLiveness.ABSENT.value
                        or evidence.get("process_identity") != lease.process_identity.to_dict()
                        or not isinstance(evidence.get("method"), str)
                        or not evidence.get("method")
                        or not isinstance(evidence.get("observed_at"), str)
                    ):
                        raise ValueError("durable journal recovered-release evidence is invalid")
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
                process_identity=(
                    ProcessIdentity(**record["process_identity"])
                    if record.get("process_identity") is not None else None
                ),
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
        if event["event_type"] in {"LEASE_RELEASED", "LEASE_RECOVERED_RELEASED"}:
            state.pop(event["lease_id"], None)
            quarantined.pop(event["lease_id"], None)


__all__ = ["DurableResourceAllocator", "DurableResourceLease"]
