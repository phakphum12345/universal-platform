from datetime import datetime, timezone
from dataclasses import dataclass, field
import pytest
from universal_platform.runtime.health.log_analyzer import analyze_logs
from universal_platform.runtime.recovery.coordinator import RecoveryCoordinator
from universal_platform.runtime.resources.models import ResourceMetric, ResourceRecord, ResourceSnapshot, ResourceState
from universal_platform.runtime.resources.registry import ResourceRegistry

@dataclass
class FakeAdapter:
    adapter_id: str = "python-worker-v1"
    resource_kind: str = "python-worker"
    capabilities: tuple[str, ...] = ("execute-python", "checkpoint")
    healthy: bool = True
    canary: bool = True
    calls: list[str] = field(default_factory=list)
    def quiesce(self, resource_id): self.calls.append("quiesce")
    def health_check(self, resource_id): self.calls.append("health"); return self.healthy
    def canary_check(self, resource_id): self.calls.append("canary"); return self.canary
    def resume(self, resource_id): self.calls.append("resume")
    def rollback(self, resource_id): self.calls.append("rollback")

@dataclass
class FakeRepair:
    sandboxed: bool = True
    succeeds: bool = True
    seen_events: tuple = ()
    def repair(self, resource_id, events):
        self.seen_events = tuple(events)
        return self.succeeds

def make_registry():
    registry = ResourceRegistry()
    registry.register(ResourceRecord("worker-1", "python-worker", "python-worker-v1", ("execute-python",)))
    return registry

def test_log_analyzer_extracts_error_and_redacts_secrets():
    events = analyze_logs("ERROR component_id=worker-1 password=hunter2 failed")
    assert len(events) == 1
    assert events[0].component_id == "worker-1"
    assert "hunter2" not in events[0].message
    assert "[REDACTED]" in events[0].message

def test_log_analyzer_reads_json_structured_error_only():
    events = analyze_logs('{"level":"INFO","message":"ok"}\n{"level":"ERROR","component_id":"worker-1","message":"broken"}')
    assert len(events) == 1 and events[0].component_id == "worker-1"

def test_recovery_sleeps_repairs_validates_canary_and_resumes():
    registry, adapter, repair = make_registry(), FakeAdapter(), FakeRepair()
    result = RecoveryCoordinator(registry).recover("worker-1", "ERROR component_id=worker-1 worker crashed", adapter=adapter, repair_executor=repair)
    assert result.state is ResourceState.ACTIVE and result.repaired and result.resumed
    assert adapter.calls == ["quiesce", "health", "canary", "resume"]
    assert registry.get("worker-1").generation == 7

def test_unsandboxed_repair_quarantines_without_running_repair():
    registry, adapter, repair = make_registry(), FakeAdapter(), FakeRepair(sandboxed=False)
    result = RecoveryCoordinator(registry).recover("worker-1", "ERROR component_id=worker-1 failed", adapter=adapter, repair_executor=repair)
    assert result.state is ResourceState.QUARANTINED and repair.seen_events == ()
    assert "resume" not in adapter.calls

def test_failed_health_check_rolls_back_and_quarantines():
    registry, adapter = make_registry(), FakeAdapter(healthy=False)
    result = RecoveryCoordinator(registry).recover("worker-1", "ERROR component_id=worker-1 failed", adapter=adapter, repair_executor=FakeRepair())
    assert result.state is ResourceState.QUARANTINED and "rollback" in adapter.calls
    assert "resume" not in adapter.calls

def test_recovery_rejects_logs_for_other_component():
    with pytest.raises(ValueError, match="different component"):
        RecoveryCoordinator(make_registry()).recover("worker-1", "ERROR component_id=worker-2 failed", adapter=FakeAdapter(), repair_executor=FakeRepair())

def test_registry_replacement_requires_sleep_and_compatible_capabilities():
    registry = make_registry()
    registry.transition("worker-1", ResourceState.QUIESCING)
    with pytest.raises(RuntimeError, match="asleep"):
        registry.replace_adapter("worker-1", adapter_id="python-worker-v2", adapter_kind="python-worker", adapter_capabilities=("execute-python",))
    registry.transition("worker-1", ResourceState.SLEEP)
    with pytest.raises(ValueError, match="lacks required"):
        registry.replace_adapter("worker-1", adapter_id="limited", adapter_kind="python-worker", adapter_capabilities=())
    updated = registry.replace_adapter("worker-1", adapter_id="python-worker-v2", adapter_kind="python-worker", adapter_capabilities=("execute-python", "checkpoint"))
    assert updated.adapter_id == "python-worker-v2"

def test_registry_rejects_stale_state_and_invalid_transition():
    registry = make_registry()
    with pytest.raises(RuntimeError, match="stale"):
        registry.transition("worker-1", ResourceState.SLEEP, expected=ResourceState.SUSPECT)
    with pytest.raises(ValueError, match="invalid resource transition"):
        registry.transition("worker-1", ResourceState.ACTIVE)


def test_resource_registry_stores_unit_bearing_monotonic_snapshots():
    registry = make_registry()
    first = ResourceSnapshot(
        "worker-1", 1, datetime.now(timezone.utc),
        (ResourceMetric("cpu.utilization", 31.5, "%"), ResourceMetric("memory.used", 2048, "bytes")),
    )
    registry.record_snapshot(first)
    assert registry.latest_resource_snapshot("worker-1").to_dict()["metrics"][0]["name"] == "cpu.utilization"
    with pytest.raises(ValueError, match="monotonically"):
        registry.record_snapshot(first)
    second = ResourceSnapshot("worker-1", 2, datetime.now(timezone.utc), (ResourceMetric("disk.free", 4096, "bytes"),))
    registry.record_snapshot(second)
    assert registry.latest_resource_snapshot("worker-1").sequence == 2


def test_resource_metrics_reject_invalid_values_and_duplicate_names():
    with pytest.raises(ValueError, match="finite and non-negative"):
        ResourceMetric("memory.used", float("nan"), "bytes")
    with pytest.raises(ValueError, match="unique"):
        ResourceSnapshot(
            "worker-1", 1, datetime.now(timezone.utc),
            (ResourceMetric("cpu", 1, "%"), ResourceMetric("cpu", 2, "%")),
        )
