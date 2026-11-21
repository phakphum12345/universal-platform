import json
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta

import pytest

from universal_platform.runtime.process_identity import ProcessIdentity
from universal_platform.runtime.process_reconciliation import ProcessLiveness, ProcessLivenessEvidence
from universal_platform.runtime.resources.durable_allocator import DurableResourceAllocator
from universal_platform.runtime.resources.models import ResourceMetric


def capacity():
    return (ResourceMetric("cpu.cores", 2, "cores"), ResourceMetric("memory.bytes", 1024, "bytes"))


def test_durable_allocator_persists_leases_across_instances_and_rejects_overcommit(tmp_path):
    first = DurableResourceAllocator(tmp_path, capacity(), pool_id="shared-host")
    lease = first.allocate("worker-a", (ResourceMetric("cpu.cores", 2, "cores"),), ttl_seconds=None)
    second = DurableResourceAllocator(tmp_path, capacity(), pool_id="shared-host")

    assert second.active_leases() == (lease,)
    assert {metric.name: metric.value for metric in second.available()}["cpu.cores"] == 0
    with pytest.raises(RuntimeError, match="capacity exceeded"):
        second.allocate("worker-b", (ResourceMetric("cpu.cores", 1, "cores"),), ttl_seconds=None)


def test_durable_allocator_serializes_concurrent_instances_without_overcommit(tmp_path):
    allocators = tuple(DurableResourceAllocator(tmp_path, capacity(), pool_id="race") for _ in range(6))

    def reserve(index):
        try:
            allocators[index % len(allocators)].allocate(
                f"worker-{index}", (ResourceMetric("cpu.cores", 1, "cores"),), ttl_seconds=None
            )
            return True
        except RuntimeError:
            return False

    with ThreadPoolExecutor(max_workers=12) as pool:
        results = list(pool.map(reserve, range(12)))

    assert sum(results) == 2
    assert len(allocators[0].active_leases()) == 2
    assert allocators[0].available()[0].value == 0


def test_durable_allocator_pins_capacity_configuration(tmp_path):
    DurableResourceAllocator(tmp_path, capacity(), pool_id="pinned")
    changed = (ResourceMetric("cpu.cores", 3, "cores"), ResourceMetric("memory.bytes", 1024, "bytes"))
    with pytest.raises(ValueError, match="capacity configuration mismatch"):
        DurableResourceAllocator(tmp_path, changed, pool_id="pinned")


def test_durable_quarantine_survives_restart_and_never_expires(tmp_path):
    now = datetime(2026, 11, 20, tzinfo=UTC)
    first = DurableResourceAllocator(tmp_path, capacity(), pool_id="quarantine")
    lease = first.allocate(
        "worker-a", (ResourceMetric("cpu.cores", 1, "cores"),),
        ttl_seconds=1, now=now,
    )
    assert first.quarantine(lease.lease_id, "termination could not be confirmed")

    restarted = DurableResourceAllocator(tmp_path, capacity(), pool_id="quarantine")
    assert restarted.active_leases(now=now + timedelta(days=30)) == (lease,)
    assert restarted.quarantined_leases() == ((lease, "termination could not be confirmed"),)
    with pytest.raises(RuntimeError, match="audited operator recovery"):
        restarted.release(lease.lease_id)


def test_supervised_worker_lease_is_non_expiring_and_requires_host_identity(tmp_path):
    allocator = DurableResourceAllocator(tmp_path, capacity(), pool_id="worker")
    with pytest.raises(ValueError, match="ttl_seconds=None"):
        allocator.allocate(
            "runtime", (ResourceMetric("cpu.cores", 1, "cores"),),
            lease_kind="supervised_worker", host_instance_id="host-1", worker_id="worker-1",
        )
    with pytest.raises(ValueError, match="host_instance_id and worker_id"):
        allocator.allocate(
            "runtime", (ResourceMetric("cpu.cores", 1, "cores"),),
            ttl_seconds=None, lease_kind="supervised_worker",
        )
    lease = allocator.allocate(
        "runtime", (ResourceMetric("cpu.cores", 1, "cores"),),
        ttl_seconds=None, lease_kind="supervised_worker",
        host_instance_id="host-1", worker_id="worker-1",
    )
    restarted = DurableResourceAllocator(tmp_path, capacity(), pool_id="worker")
    assert restarted.active_leases(now=lease.acquired_at + timedelta(days=90)) == (lease,)


def test_durable_release_is_persisted_and_idempotent(tmp_path):
    allocator = DurableResourceAllocator(tmp_path, capacity(), pool_id="release")
    lease = allocator.allocate("worker", (ResourceMetric("cpu.cores", 1, "cores"),), ttl_seconds=None)
    assert allocator.release(lease.lease_id)
    assert not allocator.release(lease.lease_id)
    restarted = DurableResourceAllocator(tmp_path, capacity(), pool_id="release")
    assert restarted.active_leases() == ()
    assert restarted.available()[0].value == 2


def test_expired_ordinary_lease_is_released_as_a_durable_event(tmp_path):
    now = datetime(2026, 11, 20, tzinfo=UTC)
    allocator = DurableResourceAllocator(tmp_path, capacity(), pool_id="expiry")
    allocator.allocate(
        "worker", (ResourceMetric("cpu.cores", 1, "cores"),), ttl_seconds=5, now=now,
    )
    assert allocator.active_leases(now=now + timedelta(seconds=5)) == ()
    restarted = DurableResourceAllocator(tmp_path, capacity(), pool_id="expiry")
    assert restarted.active_leases(now=now) == ()
    events = [json.loads(line) for line in next(tmp_path.glob("worker-leases-*.jsonl")).read_text().splitlines()]
    assert any(event.get("event_type") == "LEASE_RELEASED" and event.get("reason") == "ttl_expired" for event in events)


def test_durable_allocator_fails_closed_on_corrupt_journal(tmp_path):
    allocator = DurableResourceAllocator(tmp_path, capacity(), pool_id="corrupt")
    allocator.allocate("worker", (ResourceMetric("cpu.cores", 1, "cores"),), ttl_seconds=None)
    path = next(tmp_path.glob("worker-leases-*.jsonl"))
    records = path.read_text(encoding="utf-8").splitlines()
    damaged = json.loads(records[0])
    damaged["capacity_fingerprint"] = "0" * 64
    records[0] = json.dumps(damaged, sort_keys=True, separators=(",", ":"))
    path.write_text("\n".join(records) + "\n", encoding="utf-8")

    with pytest.raises(ValueError, match="hash-chain"):
        DurableResourceAllocator(tmp_path, capacity(), pool_id="corrupt")


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


def test_process_identity_binding_is_durable_and_idempotent(tmp_path):
    allocator = DurableResourceAllocator(tmp_path, capacity(), pool_id="identity-bound")
    lease = allocator.allocate_worker(
        "runtime",
        (ResourceMetric("cpu.cores", 1, "cores"),),
        host_instance_id="host-1",
        worker_id="worker-1",
    )
    identity = worker_identity()

    bound = allocator.bind_process_identity(lease.lease_id, identity)
    assert bound.process_identity == identity
    assert allocator.bind_process_identity(lease.lease_id, identity) == bound

    restarted = DurableResourceAllocator(tmp_path, capacity(), pool_id="identity-bound")
    recovered = restarted.active_leases()
    assert len(recovered) == 1
    assert recovered[0].process_identity == identity
    assert restarted.verify()[0] >= 3


def test_process_identity_binding_rejects_mismatched_host_or_worker(tmp_path):
    allocator = DurableResourceAllocator(tmp_path, capacity(), pool_id="identity-mismatch")
    lease = allocator.allocate_worker(
        "runtime",
        (ResourceMetric("cpu.cores", 1, "cores"),),
        host_instance_id="host-1",
        worker_id="worker-1",
    )
    with pytest.raises(ValueError, match="does not match"):
        allocator.bind_process_identity(
            lease.lease_id,
            worker_identity(worker_id="worker-other"),
        )
    with pytest.raises(ValueError, match="does not match"):
        allocator.bind_process_identity(
            lease.lease_id,
            worker_identity(host_instance_id="host-other"),
        )
    assert allocator.active_leases()[0].process_identity is None


def test_process_identity_binding_rejects_ordinary_or_unknown_leases(tmp_path):
    allocator = DurableResourceAllocator(tmp_path, capacity(), pool_id="identity-kind")
    ordinary = allocator.allocate(
        "runtime",
        (ResourceMetric("cpu.cores", 1, "cores"),),
        ttl_seconds=None,
    )
    with pytest.raises(ValueError, match="supervised worker"):
        allocator.bind_process_identity(ordinary.lease_id, worker_identity())
    with pytest.raises(ValueError, match="unknown lease"):
        allocator.bind_process_identity("missing-lease", worker_identity())


def test_process_identity_binding_cannot_be_replaced_or_added_after_quarantine(tmp_path):
    allocator = DurableResourceAllocator(tmp_path, capacity(), pool_id="identity-immutable")
    lease = allocator.allocate_worker(
        "runtime",
        (ResourceMetric("cpu.cores", 1, "cores"),),
        host_instance_id="host-1",
        worker_id="worker-1",
    )
    first = worker_identity(pid=1234)
    allocator.bind_process_identity(lease.lease_id, first)
    with pytest.raises(RuntimeError, match="different process identity"):
        allocator.bind_process_identity(lease.lease_id, worker_identity(pid=5678))

    other = allocator.allocate_worker(
        "runtime",
        (ResourceMetric("cpu.cores", 1, "cores"),),
        host_instance_id="host-1",
        worker_id="worker-2",
    )
    allocator.quarantine(other.lease_id, "identity capture incomplete")
    with pytest.raises(RuntimeError, match="quarantined"):
        allocator.bind_process_identity(
            other.lease_id,
            worker_identity(worker_id="worker-2"),
        )


def test_identity_only_worker_lease_allows_empty_resource_metrics_but_ordinary_lease_does_not(tmp_path):
    allocator = DurableResourceAllocator(
        tmp_path,
        capacity(),
        pool_id="identity-only-worker",
    )
    lease = allocator.allocate_worker(
        "runtime",
        (),
        host_instance_id="host-identity-only",
        worker_id="worker-identity-only",
    )
    assert lease.allocations == ()
    assert allocator.active_leases() == (lease,)
    with pytest.raises(ValueError, match="ordinary leases require"):
        allocator.allocate("ordinary-runtime", (), ttl_seconds=None)


class StaticProcessInspector:
    def __init__(self, status, *, reason=None, mismatch=False):
        self.status = status
        self.reason = reason
        self.mismatch = mismatch

    def inspect(self, identity):
        if self.mismatch:
            identity = worker_identity(pid=identity.pid + 1, worker_id=identity.worker_id,
                                       host_instance_id=identity.host_instance_id)
        return ProcessLivenessEvidence(
            identity=identity,
            status=self.status,
            method="test.static-inspector",
            observed_at=datetime.now(UTC),
            reason=self.reason,
        )


def test_startup_reconciliation_requires_proof_before_new_admissions_and_recovers_absent_worker(tmp_path):
    original = DurableResourceAllocator(tmp_path, capacity(), pool_id="startup-absent")
    lease = original.allocate_worker(
        "runtime",
        (ResourceMetric("cpu.cores", 1, "cores"),),
        host_instance_id="host-old",
        worker_id="worker-old",
    )
    identity = worker_identity(worker_id="worker-old", host_instance_id="host-old")
    original.bind_process_identity(lease.lease_id, identity)

    restarted = DurableResourceAllocator(tmp_path, capacity(), pool_id="startup-absent")
    assert restarted.startup_reconciliation_required
    with pytest.raises(RuntimeError, match="startup reconciliation"):
        restarted.allocate("new-runtime", (ResourceMetric("cpu.cores", 1, "cores"),))
    with pytest.raises(RuntimeError, match="startup reconciliation"):
        restarted.release(lease.lease_id)

    outcomes = restarted.reconcile_startup(
        StaticProcessInspector(ProcessLiveness.ABSENT, reason="worker process tree is gone"),
        current_host_instance_id="host-new",
    )
    assert len(outcomes) == 1
    assert outcomes[0].status is ProcessLiveness.ABSENT
    assert outcomes[0].action == "released"
    assert not restarted.startup_reconciliation_required
    assert restarted.active_leases() == ()
    assert restarted.available()[0].value == 2
    recovered = next(
        event for event in restarted._journal.read_all()
        if event["event_type"] == "LEASE_RECOVERED_RELEASED"
    )
    assert recovered["evidence"]["status"] == "ABSENT"
    assert recovered["evidence"]["process_identity"] == identity.to_dict()
    replayed = DurableResourceAllocator(tmp_path, capacity(), pool_id="startup-absent")
    assert not replayed.startup_reconciliation_required
    assert replayed.active_leases() == ()
    restarted.allocate("new-runtime", (ResourceMetric("cpu.cores", 1, "cores"),))


def test_startup_reconciliation_quarantines_unknown_worker_without_identity(tmp_path):
    original = DurableResourceAllocator(tmp_path, capacity(), pool_id="startup-missing-identity")
    lease = original.allocate_worker(
        "runtime",
        (ResourceMetric("cpu.cores", 2, "cores"),),
        host_instance_id="host-old",
        worker_id="worker-no-identity",
    )
    restarted = DurableResourceAllocator(tmp_path, capacity(), pool_id="startup-missing-identity")
    outcome = restarted.reconcile_startup(
        StaticProcessInspector(ProcessLiveness.ABSENT),
        current_host_instance_id="host-new",
    )[0]

    assert outcome.status is ProcessLiveness.UNKNOWN
    assert outcome.action == "quarantined"
    assert "no recorded OS process identity" in (outcome.reason or "")
    assert restarted.active_leases() == (lease,)
    assert restarted.available()[0].value == 0
    assert len(restarted.quarantined_leases()) == 1


def test_startup_reconciliation_retains_same_host_present_worker(tmp_path):
    original = DurableResourceAllocator(tmp_path, capacity(), pool_id="startup-present-same-host")
    lease = original.allocate_worker(
        "runtime",
        (ResourceMetric("cpu.cores", 1, "cores"),),
        host_instance_id="host-current",
        worker_id="worker-current",
    )
    original.bind_process_identity(
        lease.lease_id,
        worker_identity(worker_id="worker-current", host_instance_id="host-current"),
    )
    restarted = DurableResourceAllocator(tmp_path, capacity(), pool_id="startup-present-same-host")
    outcome = restarted.reconcile_startup(
        StaticProcessInspector(ProcessLiveness.PRESENT),
        current_host_instance_id="host-current",
    )[0]
    assert outcome.status is ProcessLiveness.PRESENT
    assert outcome.action == "retained"
    assert restarted.active_leases()[0].lease_id == lease.lease_id
    assert restarted.quarantined_leases() == ()


def test_startup_reconciliation_quarantines_present_worker_from_previous_host(tmp_path):
    original = DurableResourceAllocator(tmp_path, capacity(), pool_id="startup-present-other-host")
    lease = original.allocate_worker(
        "runtime",
        (ResourceMetric("cpu.cores", 1, "cores"),),
        host_instance_id="host-old",
        worker_id="worker-old",
    )
    original.bind_process_identity(
        lease.lease_id,
        worker_identity(worker_id="worker-old", host_instance_id="host-old"),
    )
    restarted = DurableResourceAllocator(tmp_path, capacity(), pool_id="startup-present-other-host")
    outcome = restarted.reconcile_startup(
        StaticProcessInspector(ProcessLiveness.PRESENT),
        current_host_instance_id="host-new",
    )[0]
    assert outcome.status is ProcessLiveness.PRESENT
    assert outcome.action == "quarantined"
    assert "automatic adoption is disabled" in (outcome.reason or "")
    assert len(restarted.quarantined_leases()) == 1
    assert restarted.active_leases()[0].lease_id == lease.lease_id


def test_startup_reconciliation_never_clears_existing_quarantine(tmp_path):
    original = DurableResourceAllocator(tmp_path, capacity(), pool_id="startup-preserve-quarantine")
    lease = original.allocate_worker(
        "runtime",
        (ResourceMetric("cpu.cores", 1, "cores"),),
        host_instance_id="host-old",
        worker_id="worker-old",
    )
    original.bind_process_identity(
        lease.lease_id,
        worker_identity(worker_id="worker-old", host_instance_id="host-old"),
    )
    original.quarantine(lease.lease_id, "previous cleanup could not be confirmed")
    restarted = DurableResourceAllocator(tmp_path, capacity(), pool_id="startup-preserve-quarantine")
    outcome = restarted.reconcile_startup(
        StaticProcessInspector(ProcessLiveness.ABSENT),
        current_host_instance_id="host-new",
    )[0]
    assert outcome.status is ProcessLiveness.ABSENT
    assert outcome.action == "retained_quarantine"
    assert restarted.active_leases()[0].lease_id == lease.lease_id
    assert len(restarted.quarantined_leases()) == 1


def test_startup_reconciliation_rejects_mismatched_inspector_evidence_as_unknown(tmp_path):
    original = DurableResourceAllocator(tmp_path, capacity(), pool_id="startup-mismatched-evidence")
    lease = original.allocate_worker(
        "runtime",
        (ResourceMetric("cpu.cores", 1, "cores"),),
        host_instance_id="host-old",
        worker_id="worker-old",
    )
    original.bind_process_identity(
        lease.lease_id,
        worker_identity(worker_id="worker-old", host_instance_id="host-old"),
    )
    restarted = DurableResourceAllocator(tmp_path, capacity(), pool_id="startup-mismatched-evidence")
    outcome = restarted.reconcile_startup(
        StaticProcessInspector(ProcessLiveness.ABSENT, mismatch=True),
        current_host_instance_id="host-new",
    )[0]
    assert outcome.status is ProcessLiveness.UNKNOWN
    assert outcome.action == "quarantined"
    assert len(restarted.quarantined_leases()) == 1
