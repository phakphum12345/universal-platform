from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import json

import pytest

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
    now = datetime(2026, 11, 20, tzinfo=timezone.utc)
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
    now = datetime(2026, 11, 20, tzinfo=timezone.utc)
    allocator = DurableResourceAllocator(tmp_path, capacity(), pool_id="expiry")
    lease = allocator.allocate(
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
