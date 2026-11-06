"""Deterministic, policy-gated runtime adapter discovery and replacement."""
from __future__ import annotations

from dataclasses import dataclass
from threading import RLock
from typing import Callable, Iterable

from .base import RuntimeAdapter
from ..resources.models import ResourceState
from ..resources.registry import ResourceRegistry


def _version_key(value: str) -> tuple[int, ...]:
    parts = value.split(".")
    if not parts or any(not part.isdigit() for part in parts):
        raise ValueError("versions must use numeric dot-separated components")
    return tuple(int(part) for part in parts)


@dataclass(frozen=True, slots=True)
class AdapterCandidate:
    adapter: RuntimeAdapter
    version: str
    license_id: str
    dependencies: tuple[str, ...] = ()
    priority: int = 0

    def __post_init__(self) -> None:
        if not self.adapter.adapter_id.strip() or not self.adapter.resource_kind.strip():
            raise ValueError("adapter identity and resource kind must be non-empty")
        if len(set(self.adapter.capabilities)) != len(self.adapter.capabilities):
            raise ValueError("adapter capabilities must be unique")
        if any(not item.strip() for item in self.adapter.capabilities):
            raise ValueError("adapter capabilities must be non-empty")
        _version_key(self.version)
        if not self.license_id.strip():
            raise ValueError("license_id must be non-empty")
        if len(set(self.dependencies)) != len(self.dependencies):
            raise ValueError("dependencies must be unique")
        if any(not item.strip() for item in self.dependencies):
            raise ValueError("dependencies must be non-empty")
        if isinstance(self.priority, bool) or not isinstance(self.priority, int):
            raise ValueError("priority must be an integer")


class AdapterRegistry:
    """Thread-safe catalog of already-installed adapters; never installs code."""

    def __init__(self) -> None:
        self._candidates: dict[str, AdapterCandidate] = {}
        self._lock = RLock()

    def register(self, candidate: AdapterCandidate) -> None:
        with self._lock:
            adapter_id = candidate.adapter.adapter_id
            if adapter_id in self._candidates:
                raise ValueError(f"adapter already registered: {adapter_id}")
            self._candidates[adapter_id] = candidate

    def get(self, adapter_id: str) -> AdapterCandidate:
        with self._lock:
            try:
                return self._candidates[adapter_id]
            except KeyError as exc:
                raise KeyError(f"unknown adapter: {adapter_id}") from exc

    def snapshot(self) -> tuple[AdapterCandidate, ...]:
        with self._lock:
            return tuple(self._candidates[key] for key in sorted(self._candidates))

    def select_fallback(
        self,
        *,
        resource_kind: str,
        required_capabilities: Iterable[str],
        current_adapter_id: str,
        minimum_version: str,
        allowed_licenses: Iterable[str],
        dependency_check: Callable[[tuple[str, ...]], bool],
    ) -> AdapterCandidate:
        required = frozenset(required_capabilities)
        allowed = frozenset(allowed_licenses)
        minimum = _version_key(minimum_version)
        if not allowed:
            raise PermissionError("an explicit non-empty license allow-list is required")
        if not callable(dependency_check):
            raise TypeError("dependency_check must be callable")
        with self._lock:
            candidates = tuple(self._candidates.values())
        eligible: list[tuple[tuple[int, ...], AdapterCandidate]] = []
        for candidate in candidates:
            adapter = candidate.adapter
            if adapter.adapter_id == current_adapter_id or adapter.resource_kind != resource_kind:
                continue
            if not required.issubset(adapter.capabilities) or candidate.license_id not in allowed:
                continue
            version = _version_key(candidate.version)
            width = max(len(version), len(minimum))
            if version + (0,) * (width - len(version)) < minimum + (0,) * (width - len(minimum)):
                continue
            if not dependency_check(candidate.dependencies):
                continue
            eligible.append((version, candidate))
        if not eligible:
            raise LookupError("no policy-compatible fallback adapter is available")
        eligible.sort(
            key=lambda item: (
                item[1].priority,
                item[0],
                item[1].adapter.adapter_id,
            ),
            reverse=True,
        )
        return eligible[0][1]


@dataclass(frozen=True, slots=True)
class AdapterReplacement:
    resource_id: str
    previous_adapter_id: str
    replacement_adapter_id: str
    version: str
    license_id: str


class AdapterReplacementCoordinator:
    """Stages and validates a fallback while its resource is asleep."""

    def __init__(self, resources: ResourceRegistry, adapters: AdapterRegistry) -> None:
        self._resources = resources
        self._adapters = adapters

    def replace_asleep_resource(
        self,
        resource_id: str,
        *,
        minimum_version: str,
        allowed_licenses: Iterable[str],
        dependency_check: Callable[[tuple[str, ...]], bool],
    ) -> AdapterReplacement:
        resource = self._resources.get(resource_id)
        if resource.state is not ResourceState.SLEEP:
            raise RuntimeError("adapter replacement requires the resource to be asleep")
        candidate = self._adapters.select_fallback(
            resource_kind=resource.resource_kind,
            required_capabilities=resource.required_capabilities,
            current_adapter_id=resource.adapter_id,
            minimum_version=minimum_version,
            allowed_licenses=allowed_licenses,
            dependency_check=dependency_check,
        )
        adapter = candidate.adapter
        if not adapter.health_check(resource_id):
            raise RuntimeError("replacement adapter health check failed")
        if not adapter.canary_check(resource_id):
            raise RuntimeError("replacement adapter canary check failed")
        self._resources.replace_adapter(
            resource_id,
            adapter_id=adapter.adapter_id,
            adapter_kind=adapter.resource_kind,
            adapter_capabilities=adapter.capabilities,
        )
        return AdapterReplacement(
            resource_id=resource_id,
            previous_adapter_id=resource.adapter_id,
            replacement_adapter_id=adapter.adapter_id,
            version=candidate.version,
            license_id=candidate.license_id,
        )
