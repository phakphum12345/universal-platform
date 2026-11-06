"""Threshold-based resource health assessment with fail-visible unknowns."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from math import isfinite

from ..resources.models import ResourceSnapshot, ResourceState
from ..resources.registry import ResourceRegistry


class ThresholdComparison(str, Enum):
    GT = "GT"
    GTE = "GTE"
    LT = "LT"
    LTE = "LTE"


class HealthStatus(str, Enum):
    HEALTHY = "HEALTHY"
    SUSPECT = "SUSPECT"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True, slots=True)
class ResourceHealthRule:
    metric_name: str
    unit: str
    comparison: ThresholdComparison
    threshold: float
    severity: str = "WARNING"

    def __post_init__(self) -> None:
        if not self.metric_name.strip() or not self.unit.strip():
            raise ValueError("metric_name and unit must be non-empty")
        if not isinstance(self.comparison, ThresholdComparison):
            raise ValueError("comparison must be a ThresholdComparison")
        if isinstance(self.threshold, bool) or not isinstance(self.threshold, (int, float)) or not isfinite(self.threshold):
            raise ValueError("threshold must be finite")
        if not isinstance(self.severity, str) or self.severity not in {"WARNING", "CRITICAL"}:
            raise ValueError("severity must be WARNING or CRITICAL")


@dataclass(frozen=True, slots=True)
class HealthFinding:
    metric_name: str
    observed_value: float | None
    unit: str
    status: str
    severity: str
    reason: str


@dataclass(frozen=True, slots=True)
class ResourceHealthAssessment:
    resource_id: str
    snapshot_sequence: int
    status: HealthStatus
    findings: tuple[HealthFinding, ...]
    resource_state: ResourceState


class ResourceHealthMonitor:
    """Evaluates registered metric thresholds and moves ACTIVE resources to SUSPECT."""

    def __init__(self, registry: ResourceRegistry, rules: tuple[ResourceHealthRule, ...]) -> None:
        if not isinstance(rules, tuple) or not rules:
            raise ValueError("rules must be a non-empty immutable tuple")
        if any(not isinstance(rule, ResourceHealthRule) for rule in rules):
            raise ValueError("rules must contain ResourceHealthRule records")
        keys = [(rule.metric_name, rule.unit, rule.comparison, rule.threshold, rule.severity) for rule in rules]
        if len(keys) != len(set(keys)):
            raise ValueError("health rules must not contain exact duplicates")
        self._registry = registry
        self._rules = rules

    def evaluate(self, snapshot: ResourceSnapshot) -> ResourceHealthAssessment:
        record = self._registry.get(snapshot.resource_id)
        latest = self._registry.latest_resource_snapshot(snapshot.resource_id)
        if latest.sequence != snapshot.sequence:
            raise ValueError("health monitor requires the latest recorded resource snapshot")
        metrics = {metric.name: metric for metric in snapshot.metrics}
        findings: list[HealthFinding] = []
        triggered = False
        unknown = False
        for rule in self._rules:
            metric = metrics.get(rule.metric_name)
            if metric is None:
                unknown = True
                findings.append(HealthFinding(
                    rule.metric_name, None, rule.unit, "UNKNOWN", rule.severity,
                    "metric was not reported by the provider",
                ))
                continue
            if metric.unit != rule.unit:
                unknown = True
                findings.append(HealthFinding(
                    rule.metric_name, metric.value, metric.unit, "UNKNOWN", rule.severity,
                    f"expected unit {rule.unit}",
                ))
                continue
            value = metric.value
            exceeded = {
                ThresholdComparison.GT: value > rule.threshold,
                ThresholdComparison.GTE: value >= rule.threshold,
                ThresholdComparison.LT: value < rule.threshold,
                ThresholdComparison.LTE: value <= rule.threshold,
            }[rule.comparison]
            if exceeded:
                triggered = True
                findings.append(HealthFinding(
                    rule.metric_name, value, metric.unit, "TRIGGERED", rule.severity,
                    f"observed value crossed {rule.comparison.value} threshold {rule.threshold}",
                ))
            else:
                findings.append(HealthFinding(
                    rule.metric_name, value, metric.unit, "PASS", rule.severity,
                    "metric is within the configured threshold",
                ))
        status = HealthStatus.SUSPECT if triggered else HealthStatus.UNKNOWN if unknown else HealthStatus.HEALTHY
        if triggered and record.state is ResourceState.ACTIVE:
            record = self._registry.transition(
                snapshot.resource_id, ResourceState.SUSPECT, expected=ResourceState.ACTIVE
            )
        return ResourceHealthAssessment(
            snapshot.resource_id, snapshot.sequence, status, tuple(findings), record.state
        )
