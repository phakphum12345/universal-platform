from dataclasses import dataclass

import pytest

from universal_platform.runtime.adapters.catalog import (
    AdapterCandidate,
    AdapterRegistry,
    AdapterReplacementCoordinator,
    RuntimeAdapterRouter,
)
from universal_platform.runtime.evidence.recovery_records import JsonlRecoveryEvidenceStore
from universal_platform.runtime.health.log_sources import FileLogSource
from universal_platform.runtime.recovery.coordinator import (
    AdapterFallbackPolicy,
    RecoveryCoordinator,
)
from universal_platform.runtime.resources.models import ResourceRecord, ResourceState
from universal_platform.runtime.resources.registry import ResourceRegistry


@dataclass
class Adapter:
    adapter_id: str
    healthy: bool = True
    resource_kind: str = "python-worker"
    capabilities: tuple[str, ...] = ("execute-python",)
    calls: list[str] | None = None

    def __post_init__(self):
        if self.calls is None:
            self.calls = []

    def quiesce(self, resource_id): self.calls.append("quiesce")
    def health_check(self, resource_id): self.calls.append("health"); return self.healthy
    def canary_check(self, resource_id): self.calls.append("canary"); return self.healthy
    def resume(self, resource_id): self.calls.append("resume")
    def rollback(self, resource_id): self.calls.append("rollback")


class Repair:
    sandboxed = True
    def __init__(self): self.called = False
    def repair(self, resource_id, events):
        self.called = True
        assert events
        return True


def make_stack(old_healthy=False, new_healthy=True, evidence_root=None):
    resources = ResourceRegistry()
    resources.register(ResourceRecord(
        "worker-1", "python-worker", "adapter-old", ("execute-python",)
    ))
    old = Adapter("adapter-old", healthy=old_healthy)
    new = Adapter("adapter-new", healthy=new_healthy)
    router = RuntimeAdapterRouter(resources)
    router.bind_current("worker-1", old)
    catalog = AdapterRegistry()
    catalog.register(AdapterCandidate(new, "2.1.0", "MIT"))
    replacement = AdapterReplacementCoordinator(resources, catalog, router=router)
    evidence = JsonlRecoveryEvidenceStore(evidence_root) if evidence_root else None
    coordinator = RecoveryCoordinator(
        resources,
        evidence_store=evidence,
        adapter_replacement=replacement,
        adapter_router=router,
    )
    policy = AdapterFallbackPolicy(
        "2.0.0", ("MIT",), lambda dependencies: not dependencies
    )
    return resources, old, new, router, coordinator, policy, evidence


def test_recovery_automatically_replaces_unhealthy_adapter_while_asleep_and_resumes_new_route(tmp_path):
    (tmp_path / "worker.log").write_text(
        "ERROR component_id=worker-1 adapter process failed", encoding="utf-8"
    )
    evidence_root = tmp_path / "evidence"
    evidence_root.mkdir()
    resources, old, new, router, coordinator, policy, evidence = make_stack(evidence_root=evidence_root)
    repair = Repair()
    result = coordinator.recover_from_source(
        "worker-1", "worker.log", log_source=FileLogSource(tmp_path),
        adapter=old, repair_executor=repair, fallback_policy=policy,
    )
    assert result.state is ResourceState.ACTIVE and result.resumed and result.evidence_recorded
    assert "fallback adapter adapter-new" in result.reason
    assert repair.called
    assert router.get_current("worker-1") is new
    assert resources.get("worker-1").adapter_id == "adapter-new"
    assert old.calls == ["quiesce", "health"]
    assert new.calls == ["health", "canary", "health", "canary", "resume"]
    count, legacy_count, head_hash = evidence.verify()
    assert count == 2 and legacy_count == 0 and len(head_hash) == 64


def test_unhealthy_adapter_without_fallback_policy_is_quarantined_without_repair(tmp_path):
    (tmp_path / "worker.log").write_text("ERROR component_id=worker-1 failed", encoding="utf-8")
    resources = ResourceRegistry()
    resources.register(ResourceRecord("worker-1", "python-worker", "adapter-old", ("execute-python",)))
    old = Adapter("adapter-old", healthy=False)
    router = RuntimeAdapterRouter(resources)
    router.bind_current("worker-1", old)
    repair = Repair()
    result = RecoveryCoordinator(resources).recover_from_source(
        "worker-1", "worker.log", log_source=FileLogSource(tmp_path),
        adapter=old, repair_executor=repair,
    )
    assert result.state is ResourceState.QUARANTINED and not result.resumed
    assert not repair.called
    assert "rollback" in old.calls and "resume" not in old.calls
    assert router.get_current("worker-1") is old


def test_failed_fallback_candidate_keeps_old_route_and_quarantines(tmp_path):
    (tmp_path / "worker.log").write_text("ERROR component_id=worker-1 failed", encoding="utf-8")
    resources, old, new, router, coordinator, policy, _ = make_stack(new_healthy=False)
    repair = Repair()
    result = coordinator.recover_from_source(
        "worker-1", "worker.log", log_source=FileLogSource(tmp_path),
        adapter=old, repair_executor=repair, fallback_policy=policy,
    )
    assert result.state is ResourceState.QUARANTINED and not result.resumed
    assert not repair.called
    assert router.get_current("worker-1") is old
    assert resources.get("worker-1").adapter_id == "adapter-old"
    assert "rollback" in old.calls


def test_fallback_policy_requires_explicit_license_and_dependency_gate():
    with pytest.raises(ValueError, match="allowed_licenses"):
        AdapterFallbackPolicy("1.0.0", (), lambda dependencies: True)
    with pytest.raises(ValueError, match="dependency_check"):
        AdapterFallbackPolicy("1.0.0", ("MIT",), None)


def test_recovery_fallback_configuration_must_share_router_and_registry():
    resources = ResourceRegistry()
    other = ResourceRegistry()
    router = RuntimeAdapterRouter(other)
    catalog = AdapterRegistry()
    replacement = AdapterReplacementCoordinator(other, catalog, router=router)
    with pytest.raises(ValueError, match="share"):
        RecoveryCoordinator(resources, adapter_replacement=replacement, adapter_router=router)
