from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

import pytest

from universal_platform.runtime.resources.collector import (
    LocalSystemResourceProvider,
    ResourceSnapshotCollector,
)
from universal_platform.runtime.resources.models import ResourceMetric, ResourceRecord
from universal_platform.runtime.resources.registry import ResourceRegistry


class FakeProvider:
    def __init__(self, metrics=None):
        self.metrics = metrics or (ResourceMetric("cpu.load", 1.5, "load"),)
        self.calls = 0

    def collect(self, resource_id):
        self.calls += 1
        return self.metrics


def make_registry():
    registry = ResourceRegistry()
    registry.register(ResourceRecord("host-1", "host", "local-host"))
    return registry


def test_collector_records_unit_bearing_monotonic_snapshots():
    registry = make_registry()
    provider = FakeProvider()
    collector = ResourceSnapshotCollector(
        registry,
        clock=lambda: datetime(2026, 11, 7, tzinfo=timezone.utc),
    )
    collector.register_provider("host-1", provider)
    first = collector.collect("host-1")
    second = collector.collect("host-1")
    assert first.sequence == 1 and second.sequence == 2
    assert registry.latest_resource_snapshot("host-1") == second
    assert provider.calls == 2


def test_collector_rejects_duplicate_or_unknown_provider_registration():
    collector = ResourceSnapshotCollector(make_registry())
    collector.register_provider("host-1", FakeProvider())
    with pytest.raises(ValueError, match="already registered"):
        collector.register_provider("host-1", FakeProvider())
    with pytest.raises(KeyError, match="unknown resource"):
        collector.register_provider("missing", FakeProvider())


def test_collector_rejects_missing_provider_and_invalid_snapshot_without_advancing_sequence():
    registry = make_registry()
    collector = ResourceSnapshotCollector(registry, clock=lambda: datetime(2026, 11, 7))
    with pytest.raises(KeyError, match="no resource provider"):
        collector.collect("host-1")
    collector.register_provider("host-1", FakeProvider())
    with pytest.raises(ValueError, match="timezone-aware"):
        collector.collect("host-1")


def test_collector_serializes_concurrent_sequences():
    registry = make_registry()
    collector = ResourceSnapshotCollector(registry)
    collector.register_provider("host-1", FakeProvider())
    with ThreadPoolExecutor(max_workers=8) as pool:
        snapshots = list(pool.map(lambda _: collector.collect("host-1"), range(24)))
    assert sorted(item.sequence for item in snapshots) == list(range(1, 25))
    assert registry.latest_resource_snapshot("host-1").sequence == 24


def test_local_provider_reports_real_disk_and_linux_network_counters(tmp_path):
    network = tmp_path / "net-dev"
    network.write_text(
        "Inter-| Receive | Transmit\n"
        " face |bytes packets errs drop fifo frame compressed multicast|bytes packets errs drop fifo colls carrier compressed\n"
        " eth0: 100 1 0 0 0 0 0 0 250 2 0 0 0 0 0 0\n",
        encoding="ascii",
    )
    provider = LocalSystemResourceProvider(disk_path=tmp_path, network_stats_path=network)
    metrics = {item.name: item for item in provider.collect("host-1")}
    assert metrics["disk.total"].value >= metrics["disk.used"].value
    assert metrics["disk.free"].value >= 0
    assert metrics["network.received"].value == 100
    assert metrics["network.transmitted"].value == 250
    if __import__("os").cpu_count() is not None:
        assert metrics["cpu.logical_cores"].value == __import__("os").cpu_count()


def test_local_provider_omits_unavailable_network_counters_and_gpu_instead_of_guessing(tmp_path):
    provider = LocalSystemResourceProvider(disk_path=tmp_path, network_stats_path=tmp_path / "missing")
    names = {item.name for item in provider.collect("host-1")}
    assert "disk.free" in names
    assert "gpu.utilization" not in names
    assert "network.received" not in names
