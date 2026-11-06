from dataclasses import dataclass, field

import pytest

from universal_platform.runtime.adapters.catalog import (
    AdapterCandidate,
    AdapterRegistry,
    AdapterReplacementCoordinator,
)
from universal_platform.runtime.resources.models import ResourceRecord, ResourceState
from universal_platform.runtime.resources.registry import ResourceRegistry


@dataclass
class FakeAdapter:
    adapter_id: str
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


def asleep_registry():
    resources = ResourceRegistry()
    resources.register(ResourceRecord(
        "worker-1", "python-worker", "adapter-old", ("execute-python", "checkpoint")
    ))
    resources.transition("worker-1", ResourceState.QUIESCING)
    resources.transition("worker-1", ResourceState.SLEEP)
    return resources


def test_catalog_selects_highest_priority_policy_compatible_fallback():
    catalog = AdapterRegistry()
    low = FakeAdapter("adapter-low")
    high = FakeAdapter("adapter-high")
    catalog.register(AdapterCandidate(low, "1.8.0", "Apache-2.0", ("runtime-core",), priority=1))
    catalog.register(AdapterCandidate(high, "1.10.0", "MIT", ("runtime-core",), priority=5))
    selected = catalog.select_fallback(
        resource_kind="python-worker",
        required_capabilities=("execute-python", "checkpoint"),
        current_adapter_id="adapter-old",
        minimum_version="1.9.0",
        allowed_licenses=("MIT", "Apache-2.0"),
        dependency_check=lambda deps: deps == ("runtime-core",),
    )
    assert selected.adapter.adapter_id == "adapter-high"


def test_catalog_fails_closed_without_explicit_license_allowlist():
    catalog = AdapterRegistry()
    catalog.register(AdapterCandidate(FakeAdapter("adapter-new"), "1.0", "MIT"))
    with pytest.raises(PermissionError, match="license allow-list"):
        catalog.select_fallback(
            resource_kind="python-worker",
            required_capabilities=("execute-python",),
            current_adapter_id="adapter-old",
            minimum_version="1.0",
            allowed_licenses=(),
            dependency_check=lambda deps: True,
        )


def test_catalog_rejects_incompatible_license_version_capabilities_and_dependencies():
    catalog = AdapterRegistry()
    catalog.register(AdapterCandidate(
        FakeAdapter("too-old"), "0.9", "MIT", ("runtime-core",), priority=99
    ))
    catalog.register(AdapterCandidate(
        FakeAdapter("missing-capability", capabilities=("execute-python",)),
        "2.0", "MIT", ("runtime-core",), priority=90,
    ))
    catalog.register(AdapterCandidate(
        FakeAdapter("unapproved-license"), "2.0", "GPL-3.0", ("runtime-core",), priority=80
    ))
    catalog.register(AdapterCandidate(
        FakeAdapter("missing-dependency"), "2.0", "MIT", ("optional-extra",), priority=70
    ))
    with pytest.raises(LookupError, match="no policy-compatible"):
        catalog.select_fallback(
            resource_kind="python-worker",
            required_capabilities=("execute-python", "checkpoint"),
            current_adapter_id="adapter-old",
            minimum_version="1.0",
            allowed_licenses=("MIT",),
            dependency_check=lambda deps: deps == ("runtime-core",),
        )


def test_replacement_requires_sleep_and_commits_only_after_health_and_canary():
    resources = asleep_registry()
    catalog = AdapterRegistry()
    replacement = FakeAdapter("adapter-new")
    catalog.register(AdapterCandidate(replacement, "1.2.0", "MIT"))
    result = AdapterReplacementCoordinator(resources, catalog).replace_asleep_resource(
        "worker-1",
        minimum_version="1.0",
        allowed_licenses=("MIT",),
        dependency_check=lambda deps: True,
    )
    assert result.previous_adapter_id == "adapter-old"
    assert result.replacement_adapter_id == "adapter-new"
    assert resources.get("worker-1").adapter_id == "adapter-new"
    assert replacement.calls == ["health", "canary"]
    assert resources.get("worker-1").state is ResourceState.SLEEP


@pytest.mark.parametrize("healthy,canary", [(False, True), (True, False)])
def test_failed_candidate_validation_does_not_change_registered_adapter(healthy, canary):
    resources = asleep_registry()
    catalog = AdapterRegistry()
    candidate = FakeAdapter("adapter-bad", healthy=healthy, canary=canary)
    catalog.register(AdapterCandidate(candidate, "1.2.0", "MIT"))
    coordinator = AdapterReplacementCoordinator(resources, catalog)
    with pytest.raises(RuntimeError):
        coordinator.replace_asleep_resource(
            "worker-1",
            minimum_version="1.0",
            allowed_licenses=("MIT",),
            dependency_check=lambda deps: True,
        )
    assert resources.get("worker-1").adapter_id == "adapter-old"
    assert resources.get("worker-1").state is ResourceState.SLEEP


def test_replacement_is_rejected_while_resource_is_active():
    resources = ResourceRegistry()
    resources.register(ResourceRecord("worker-1", "python-worker", "adapter-old", ("execute-python",)))
    catalog = AdapterRegistry()
    catalog.register(AdapterCandidate(FakeAdapter("adapter-new"), "1.2.0", "MIT"))
    coordinator = AdapterReplacementCoordinator(resources, catalog)
    with pytest.raises(RuntimeError, match="asleep"):
        coordinator.replace_asleep_resource(
            "worker-1",
            minimum_version="1.0",
            allowed_licenses=("MIT",),
            dependency_check=lambda deps: True,
        )
    assert resources.get("worker-1").adapter_id == "adapter-old"


def test_adapter_registry_rejects_duplicate_ids_and_non_numeric_versions():
    catalog = AdapterRegistry()
    adapter = FakeAdapter("same")
    catalog.register(AdapterCandidate(adapter, "1.0", "MIT"))
    with pytest.raises(ValueError, match="already registered"):
        catalog.register(AdapterCandidate(adapter, "1.1", "MIT"))
    with pytest.raises(ValueError, match="numeric"):
        AdapterCandidate(FakeAdapter("bad-version"), "v1.0", "MIT")
