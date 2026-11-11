from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

import pytest

from universal_platform.runtime.resources.allocator import ResourceAllocator
from universal_platform.runtime.resources.models import ResourceMetric


def make_allocator():
    return ResourceAllocator(
        (
            ResourceMetric("cpu.cores", 4, "cores"),
            ResourceMetric("memory.bytes", 1024, "bytes"),
            ResourceMetric("gpu.units", 1, "devices"),
        ),
        pool_id="test-host",
    )


def test_allocator_reserves_and_releases_capacity():
    allocator = make_allocator()
    lease = allocator.allocate(
        "worker-a",
        (ResourceMetric("cpu.cores", 2, "cores"), ResourceMetric("memory.bytes", 512, "bytes")),
    )
    remaining = {item.name: item.value for item in allocator.available()}
    assert remaining == {"cpu.cores": 2, "gpu.units": 1, "memory.bytes": 512}
    assert allocator.release(lease.lease_id)
    assert not allocator.release(lease.lease_id)
    assert {item.name: item.value for item in allocator.available()}["cpu.cores"] == 4


def test_allocator_rejects_overcommit_unknown_metrics_and_unit_mismatch():
    allocator = make_allocator()
    allocator.allocate("worker-a", (ResourceMetric("cpu.cores", 3, "cores"),))
    with pytest.raises(RuntimeError, match="capacity exceeded"):
        allocator.allocate("worker-b", (ResourceMetric("cpu.cores", 2, "cores"),))
    with pytest.raises(ValueError, match="unknown capacity"):
        allocator.allocate("worker-c", (ResourceMetric("disk.bytes", 1, "bytes"),))
    with pytest.raises(ValueError, match="unit mismatch"):
        allocator.allocate("worker-d", (ResourceMetric("memory.bytes", 1, "kilobytes"),))


def test_expired_lease_is_reclaimed_using_injected_aware_timestamp():
    allocator = make_allocator()
    now = datetime(2026, 11, 7, tzinfo=timezone.utc)
    lease = allocator.allocate(
        "worker-a", (ResourceMetric("cpu.cores", 4, "cores"),),
        ttl_seconds=5, now=now,
    )
    assert allocator.active_leases(now=now + timedelta(seconds=4)) == (lease,)
    assert allocator.active_leases(now=now + timedelta(seconds=5)) == ()
    assert allocator.available(now=now + timedelta(seconds=5))[0].value == 4


def test_allocator_requires_valid_owner_ttl_and_timezone():
    allocator = make_allocator()
    with pytest.raises(ValueError, match="owner_id"):
        allocator.allocate("", (ResourceMetric("cpu.cores", 1, "cores"),))
    with pytest.raises(ValueError, match="ttl_seconds"):
        allocator.allocate("worker", (ResourceMetric("cpu.cores", 1, "cores"),), ttl_seconds=float("nan"))
    with pytest.raises(ValueError, match="timezone-aware"):
        allocator.allocate(
            "worker", (ResourceMetric("cpu.cores", 1, "cores"),),
            now=datetime(2026, 11, 7),
        )


def test_allocator_concurrent_reservations_never_overcommit():
    allocator = ResourceAllocator((ResourceMetric("cpu.cores", 2, "cores"),))
    def reserve(index):
        try:
            allocator.allocate(f"worker-{index}", (ResourceMetric("cpu.cores", 1, "cores"),))
            return True
        except RuntimeError:
            return False
    with ThreadPoolExecutor(max_workers=12) as pool:
        outcomes = list(pool.map(reserve, range(12)))
    assert sum(outcomes) == 2
    assert allocator.available()[0].value == 0


def test_allocator_rejects_empty_or_duplicate_capacity_and_requests():
    with pytest.raises(ValueError, match="at least one"):
        ResourceAllocator(())
    with pytest.raises(ValueError, match="unique"):
        ResourceAllocator((ResourceMetric("cpu", 1, "cores"), ResourceMetric("cpu", 2, "cores")))
    allocator = make_allocator()
    with pytest.raises(ValueError, match="unique"):
        allocator.allocate(
            "worker",
            (ResourceMetric("cpu.cores", 1, "cores"), ResourceMetric("cpu.cores", 1, "cores")),
        )


def test_allocator_supports_explicit_release_only_lease():
    allocator = ResourceAllocator((ResourceMetric("cpu.cores", 1, "cores"),))
    now = datetime(2026, 11, 7, tzinfo=timezone.utc)
    lease = allocator.allocate(
        "runtime-invocation",
        (ResourceMetric("cpu.cores", 1, "cores"),),
        ttl_seconds=None,
        now=now,
    )
    assert lease.expires_at is None
    assert allocator.active_leases(now=now + timedelta(days=30)) == (lease,)
    assert allocator.available(now=now + timedelta(days=30))[0].value == 0
    assert allocator.release(lease.lease_id)
    assert allocator.active_leases(now=now + timedelta(days=30)) == ()
