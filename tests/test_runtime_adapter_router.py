from dataclasses import dataclass

import pytest

from universal_platform.runtime.adapters.catalog import (
    AdapterCandidate,
    AdapterRegistry,
    AdapterReplacementCoordinator,
    RuntimeAdapterRouter,
)
from universal_platform.runtime.resources.models import ResourceRecord, ResourceState
from universal_platform.runtime.resources.registry import ResourceRegistry


@dataclass
class Adapter:
    adapter_id: str
    resource_kind: str = "python-worker"
    capabilities: tuple[str, ...] = ("execute-python",)
    healthy: bool = True
    canary: bool = True

    def quiesce(self, resource_id): pass
    def health_check(self, resource_id): return self.healthy
    def canary_check(self, resource_id): return self.canary
    def resume(self, resource_id): pass
    def rollback(self, resource_id): pass


def setup():
    resources = ResourceRegistry()
    resources.register(ResourceRecord("worker-1", "python-worker", "old", ("execute-python",)))
    resources.transition("worker-1", ResourceState.QUIESCING)
    resources.transition("worker-1", ResourceState.SLEEP)
    old = Adapter("old")
    router = RuntimeAdapterRouter(resources)
    router.bind_current("worker-1", old)
    catalog = AdapterRegistry()
    new = Adapter("new")
    catalog.register(AdapterCandidate(new, "1.2.0", "MIT"))
    coordinator = AdapterReplacementCoordinator(resources, catalog, router=router)
    return resources, router, coordinator, old, new


def test_replacement_atomically_updates_registry_and_runtime_route():
    resources, router, coordinator, old, new = setup()
    result = coordinator.replace_asleep_resource(
        "worker-1", minimum_version="1.0", allowed_licenses=("MIT",),
        dependency_check=lambda dependencies: True,
    )
    assert result.previous_adapter_id == "old"
    assert result.replacement_adapter_id == "new"
    assert router.get_current("worker-1") is new
    assert resources.get("worker-1").adapter_id == "new"
    assert resources.get("worker-1").state is ResourceState.SLEEP


def test_route_replacement_requires_existing_matching_route():
    resources = ResourceRegistry()
    resources.register(ResourceRecord("worker-1", "python-worker", "old"))
    resources.transition("worker-1", ResourceState.QUIESCING)
    resources.transition("worker-1", ResourceState.SLEEP)
    router = RuntimeAdapterRouter(resources)
    with pytest.raises(KeyError, match="no runtime adapter route"):
        router.replace_asleep("worker-1", Adapter("new"))
    assert resources.get("worker-1").adapter_id == "old"


def test_route_binding_validates_adapter_identity_and_capabilities():
    resources = ResourceRegistry()
    resources.register(ResourceRecord("worker-1", "python-worker", "old", ("execute-python", "checkpoint")))
    router = RuntimeAdapterRouter(resources)
    with pytest.raises(ValueError, match="identity"):
        router.bind_current("worker-1", Adapter("different"))
    with pytest.raises(ValueError, match="capabilities"):
        router.bind_current("worker-1", Adapter("old", capabilities=("execute-python",)))


def test_failed_candidate_validation_preserves_existing_runtime_route():
    resources, router, coordinator, old, new = setup()
    new.healthy = False
    with pytest.raises(RuntimeError, match="health check"):
        coordinator.replace_asleep_resource(
            "worker-1", minimum_version="1.0", allowed_licenses=("MIT",),
            dependency_check=lambda dependencies: True,
        )
    assert router.get_current("worker-1") is old
    assert resources.get("worker-1").adapter_id == "old"


def test_router_rejects_stale_route_and_non_sleeping_replacement():
    resources, router, coordinator, old, new = setup()
    resources.transition("worker-1", ResourceState.DIAGNOSING)
    with pytest.raises(RuntimeError, match="SLEEP"):
        router.replace_asleep("worker-1", new)
    assert router.get_current("worker-1") is old


def test_coordinator_requires_router_to_share_resource_registry():
    resources, _, _, _, _ = setup()
    other = ResourceRegistry()
    with pytest.raises(ValueError, match="share"):
        AdapterReplacementCoordinator(resources, AdapterRegistry(), router=RuntimeAdapterRouter(other))
