from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta

import pytest

from universal_platform.runtime.operator_recovery import (
    FORCE_RELEASE_PERMISSION,
    OperatorAuthorizationError,
    OperatorPrincipal,
    OperatorRecoveryService,
)
from universal_platform.runtime.process_identity import ProcessIdentity
from universal_platform.runtime.process_reconciliation import (
    ProcessLiveness,
    ProcessLivenessEvidence,
)
from universal_platform.runtime.resources.durable_allocator import DurableResourceAllocator
from universal_platform.runtime.resources.models import ResourceMetric


def capacity():
    return (ResourceMetric("cpu.cores", 2, "cores"), ResourceMetric("memory.bytes", 1024, "bytes"))


def worker_identity(*, pid=1234, worker_id="worker-1", host_instance_id="host-1"):
    return ProcessIdentity(
        platform="linux",
        pid=pid,
        creation_token=str(pid * 10),
        host_boot_id="boot-token",
        worker_id=worker_id,
        host_instance_id=host_instance_id,
        process_group_id=pid,
        session_id=pid,
    )


class StaticAuthorizer:
    def __init__(self, *, denied=False, authenticated_at=None):
        self.denied = denied
        self.authenticated_at = authenticated_at or datetime.now(UTC)
        self.calls = []

    def authenticate_and_authorize(self, context, *, permission):
        self.calls.append((context, permission))
        if self.denied:
            raise OperatorAuthorizationError("operator is not authorized")
        assert permission == FORCE_RELEASE_PERMISSION
        return OperatorPrincipal(
            subject="operator:alice",
            authentication_method="test-host-sso",
            authenticated_at=self.authenticated_at,
            authorization_reference="authz-decision-123",
        )


class StaticInspector:
    def __init__(self, status, *, observed_at=None, mismatch=False, error=None):
        self.status = status
        self.observed_at = observed_at or datetime.now(UTC)
        self.mismatch = mismatch
        self.error = error
        self.calls = 0

    def inspect(self, identity):
        self.calls += 1
        if self.error:
            raise self.error
        if self.mismatch:
            identity = worker_identity(pid=identity.pid + 1)
        return ProcessLivenessEvidence(
            identity=identity,
            status=self.status,
            method="test.exact-process-tree-inspection",
            observed_at=self.observed_at,
            reason="test evidence",
        )


def quarantined_worker(tmp_path, *, pool_id="operator-recovery"):
    allocator = DurableResourceAllocator(tmp_path, capacity(), pool_id=pool_id)
    lease = allocator.allocate_worker(
        "runtime",
        (ResourceMetric("cpu.cores", 1, "cores"),),
        host_instance_id="host-1",
        worker_id="worker-1",
    )
    identity = worker_identity()
    lease = allocator.bind_process_identity(lease.lease_id, identity)
    allocator.quarantine(lease.lease_id, "worker termination could not be confirmed")
    return allocator, lease, identity


def service_for(allocator, inspector, authorizer):
    return OperatorRecoveryService(
        allocator,
        inspector,
        authorizer,
        max_evidence_age=timedelta(seconds=10),
        max_authentication_age=timedelta(minutes=2),
    )


def test_operator_recovery_requires_host_authorization_before_inspection(tmp_path):
    allocator, lease, _identity = quarantined_worker(tmp_path)
    inspector = StaticInspector(ProcessLiveness.ABSENT)
    authorizer = StaticAuthorizer(denied=True)
    service = service_for(allocator, inspector, authorizer)

    with pytest.raises(OperatorAuthorizationError, match="not authorized"):
        service.recover(lease.lease_id, "operator verified cleanup", {"session": "opaque"})

    assert inspector.calls == 0
    assert allocator.quarantined_leases()[0][0].lease_id == lease.lease_id


@pytest.mark.parametrize("status", [ProcessLiveness.PRESENT, ProcessLiveness.UNKNOWN])
def test_present_or_unknown_evidence_never_releases_quarantine(tmp_path, status):
    allocator, lease, _identity = quarantined_worker(tmp_path, pool_id=f"status-{status.value}")
    service = service_for(
        allocator,
        StaticInspector(status),
        StaticAuthorizer(),
    )

    result = service.recover(lease.lease_id, "operator reviewed process", object())

    assert result.status is status
    assert result.action == "retained_quarantine"
    assert result.audit_reference is None
    assert allocator.active_leases() == (lease,)


def test_stale_or_future_liveness_evidence_is_reported_unknown_and_retained(tmp_path):
    allocator, lease, _identity = quarantined_worker(tmp_path, pool_id="stale-evidence")
    old = datetime.now(UTC) - timedelta(minutes=1)
    service = service_for(
        allocator,
        StaticInspector(ProcessLiveness.ABSENT, observed_at=old),
        StaticAuthorizer(),
    )

    result = service.recover(lease.lease_id, "stale evidence must not release", object())

    assert result.status is ProcessLiveness.UNKNOWN
    assert result.action == "retained_quarantine"
    assert "stale" in result.reason
    assert allocator.active_leases() == (lease,)


def test_mismatched_identity_and_inspector_errors_fail_closed(tmp_path):
    allocator, lease, _identity = quarantined_worker(tmp_path, pool_id="mismatched-evidence")
    mismatch = service_for(
        allocator,
        StaticInspector(ProcessLiveness.ABSENT, mismatch=True),
        StaticAuthorizer(),
    )
    result = mismatch.recover(lease.lease_id, "review identity", object())
    assert result.status is ProcessLiveness.UNKNOWN
    assert result.action == "retained_quarantine"

    failing = service_for(
        allocator,
        StaticInspector(ProcessLiveness.ABSENT, error=OSError("procfs unavailable")),
        StaticAuthorizer(),
    )
    failed = failing.recover(lease.lease_id, "inspection failed", object())
    assert failed.status is ProcessLiveness.UNKNOWN
    assert failed.action == "retained_quarantine"
    assert allocator.active_leases() == (lease,)


def test_successful_force_release_persists_operator_and_evidence_audit_reference(tmp_path):
    allocator, lease, identity = quarantined_worker(tmp_path, pool_id="success")
    service = service_for(
        allocator,
        StaticInspector(ProcessLiveness.ABSENT),
        StaticAuthorizer(),
    )

    result = service.recover(lease.lease_id, "confirmed orphaned process tree", {"session": "opaque"})

    assert result.status is ProcessLiveness.ABSENT
    assert result.action == "released"
    assert result.audit_reference
    assert allocator.active_leases() == ()
    assert allocator.quarantined_leases() == ()
    event = next(
        record for record in allocator._journal.read_all()
        if record["event_type"] == "LEASE_FORCE_RELEASED"
    )
    assert event["record_hash"] == result.audit_reference
    assert event["operator"]["subject"] == "operator:alice"
    assert event["operator"]["authentication_method"] == "test-host-sso"
    assert event["operator"]["authorization_reference"] == "authz-decision-123"
    assert event["permission"] == FORCE_RELEASE_PERMISSION
    assert event["reason"] == "confirmed orphaned process tree"
    assert event["evidence"]["process_identity"] == identity.to_dict()

    restarted = DurableResourceAllocator(tmp_path, capacity(), pool_id="success")
    assert restarted.active_leases() == ()
    assert restarted.verify()[0] >= 5


def test_stale_operator_authentication_is_rejected_before_inspection(tmp_path):
    allocator, lease, _identity = quarantined_worker(tmp_path, pool_id="stale-auth")
    stale = StaticAuthorizer(authenticated_at=datetime.now(UTC) - timedelta(hours=1))
    inspector = StaticInspector(ProcessLiveness.ABSENT)
    service = service_for(allocator, inspector, stale)

    with pytest.raises(OperatorAuthorizationError, match="stale"):
        service.recover(lease.lease_id, "re-authentication required", object())

    assert inspector.calls == 0
    assert allocator.active_leases() == (lease,)


def test_audit_append_failure_keeps_quarantine_and_capacity_charged(tmp_path, monkeypatch):
    allocator, lease, _identity = quarantined_worker(tmp_path, pool_id="audit-write-failure")
    service = service_for(
        allocator,
        StaticInspector(ProcessLiveness.ABSENT),
        StaticAuthorizer(),
    )

    def fail_append(_callback):
        raise OSError("simulated durable journal failure")

    monkeypatch.setattr(allocator._journal, "append_transaction", fail_append)
    with pytest.raises(OSError, match="simulated"):
        service.recover(lease.lease_id, "audit write failure injection", object())
    monkeypatch.undo()

    assert allocator.quarantined_leases()[0][0] == lease
    assert allocator.active_leases() == (lease,)


def test_concurrent_operator_recovery_appends_at_most_one_force_release(tmp_path):
    allocator, lease, _identity = quarantined_worker(tmp_path, pool_id="concurrent-recovery")
    inspector = StaticInspector(ProcessLiveness.ABSENT)
    service = service_for(allocator, inspector, StaticAuthorizer())

    def recover(_index):
        return service.recover(lease.lease_id, "concurrent operator recovery", object())

    with ThreadPoolExecutor(max_workers=8) as pool:
        outcomes = list(pool.map(recover, range(8)))

    assert sum(item.action == "released" for item in outcomes) == 1
    assert sum(item.action == "already_resolved" for item in outcomes) == 7
    events = [
        record for record in allocator._journal.read_all()
        if record["event_type"] == "LEASE_FORCE_RELEASED"
    ]
    assert len(events) == 1
