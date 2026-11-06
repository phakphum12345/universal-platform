from datetime import datetime, timezone

import pytest

from universal_platform.runtime.health.monitor import (
    HealthStatus,
    ResourceHealthMonitor,
    ResourceHealthRule,
    ThresholdComparison,
)
from universal_platform.runtime.resources.models import ResourceMetric, ResourceRecord, ResourceSnapshot, ResourceState
from universal_platform.runtime.resources.registry import ResourceRegistry


def make_registry():
    registry = ResourceRegistry()
    registry.register(ResourceRecord("host-1", "host", "host-adapter"))
    return registry


def record_snapshot(registry, sequence, metrics):
    snapshot = ResourceSnapshot("host-1", sequence, datetime.now(timezone.utc), tuple(metrics))
    registry.record_snapshot(snapshot)
    return snapshot


def test_monitor_marks_active_resource_suspect_when_critical_threshold_triggers():
    registry = make_registry()
    snapshot = record_snapshot(registry, 1, (ResourceMetric("cpu.utilization", 96, "%"),))
    monitor = ResourceHealthMonitor(registry, (
        ResourceHealthRule("cpu.utilization", "%", ThresholdComparison.GTE, 90, "CRITICAL"),
    ))
    result = monitor.evaluate(snapshot)
    assert result.status is HealthStatus.SUSPECT
    assert result.resource_state is ResourceState.SUSPECT
    assert result.findings[0].status == "TRIGGERED"


def test_monitor_reports_unknown_when_required_metric_is_missing_or_wrong_unit():
    registry = make_registry()
    snapshot = record_snapshot(registry, 1, (ResourceMetric("cpu.utilization", 50, "ratio"),))
    monitor = ResourceHealthMonitor(registry, (
        ResourceHealthRule("cpu.utilization", "%", ThresholdComparison.GT, 90),
        ResourceHealthRule("memory.used", "bytes", ThresholdComparison.GT, 1000),
    ))
    result = monitor.evaluate(snapshot)
    assert result.status is HealthStatus.UNKNOWN
    assert result.resource_state is ResourceState.ACTIVE
    assert [finding.status for finding in result.findings] == ["UNKNOWN", "UNKNOWN"]


def test_monitor_does_not_automatically_reactivate_a_suspect_resource():
    registry = make_registry()
    registry.transition("host-1", ResourceState.SUSPECT)
    snapshot = record_snapshot(registry, 1, (ResourceMetric("cpu.utilization", 10, "%"),))
    monitor = ResourceHealthMonitor(registry, (
        ResourceHealthRule("cpu.utilization", "%", ThresholdComparison.GT, 90),
    ))
    result = monitor.evaluate(snapshot)
    assert result.status is HealthStatus.HEALTHY
    assert result.resource_state is ResourceState.SUSPECT


def test_monitor_requires_latest_snapshot_and_rejects_duplicate_rules():
    registry = make_registry()
    first = record_snapshot(registry, 1, (ResourceMetric("cpu.utilization", 10, "%"),))
    second = record_snapshot(registry, 2, (ResourceMetric("cpu.utilization", 10, "%"),))
    monitor = ResourceHealthMonitor(registry, (
        ResourceHealthRule("cpu.utilization", "%", ThresholdComparison.GT, 90),
    ))
    with pytest.raises(ValueError, match="latest"):
        monitor.evaluate(first)
    with pytest.raises(ValueError, match="exact duplicates"):
        ResourceHealthMonitor(registry, (
            ResourceHealthRule("cpu.utilization", "%", ThresholdComparison.GT, 90),
            ResourceHealthRule("cpu.utilization", "%", ThresholdComparison.GT, 90),
        ))
    assert monitor.evaluate(second).status is HealthStatus.HEALTHY


def test_monitor_supports_warning_and_critical_thresholds_for_same_metric():
    registry = make_registry()
    snapshot = record_snapshot(registry, 1, (ResourceMetric("memory.used", 85, "%"),))
    monitor = ResourceHealthMonitor(registry, (
        ResourceHealthRule("memory.used", "%", ThresholdComparison.GTE, 80, "WARNING"),
        ResourceHealthRule("memory.used", "%", ThresholdComparison.GTE, 95, "CRITICAL"),
    ))
    result = monitor.evaluate(snapshot)
    assert result.status is HealthStatus.SUSPECT
    assert [item.status for item in result.findings] == ["TRIGGERED", "PASS"]
