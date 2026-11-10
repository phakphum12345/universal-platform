"""Policy-gated in-process execution for explicitly registered trusted handlers.

This is an application-level permission boundary, not an OS sandbox. Handler
callables are supplied by trusted application code; this module never imports
or downloads code based on a request. Optional resource leases reserve host-
configured quota for one invocation and are always released afterward.
"""
from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from threading import RLock
from typing import Any

from .contracts import ModuleRequest, ModuleResponse
from .errors import InvalidModelError
from .module_registry import ModuleRegistry
from ..runtime.resources.allocator import ResourceAllocator, ResourceLease
from ..runtime.resources.models import ResourceMetric

ModuleHandler = Callable[[Mapping[str, Any]], Mapping[str, Any]]


@dataclass(frozen=True, slots=True)
class ModuleGrant:
    """Trusted host-side permission grant for one module identity."""

    module_id: str
    permissions: frozenset[str]

    def __post_init__(self) -> None:
        if not isinstance(self.module_id, str) or not self.module_id.strip():
            raise InvalidModelError("module grant requires a module_id")
        if not isinstance(self.permissions, frozenset):
            raise InvalidModelError("module grant permissions must be a frozenset")
        if any(not isinstance(item, str) or not item.strip() for item in self.permissions):
            raise InvalidModelError("module grant permissions must be non-empty strings")


class ModuleRuntime:
    """Dispatch registered handlers after host-side permission and quota checks.

    Request.permissions is descriptive and is never treated as an authority
    grant. Resource limits are reservation requests against a host-configured
    in-memory quota pool; they do not limit actual CPU, memory, I/O or runtime.
    """

    def __init__(
        self,
        registry: ModuleRegistry,
        *,
        resource_allocator: ResourceAllocator | None = None,
    ) -> None:
        if not isinstance(registry, ModuleRegistry):
            raise InvalidModelError("registry must be a ModuleRegistry")
        if resource_allocator is not None and not isinstance(resource_allocator, ResourceAllocator):
            raise InvalidModelError("resource_allocator must be a ResourceAllocator")
        self._registry = registry
        self._resource_allocator = resource_allocator
        self._handlers: dict[tuple[str, str], ModuleHandler] = {}
        self._grants: dict[str, frozenset[str]] = {}
        self._lock = RLock()

    def grant(self, module_id: str, permissions: frozenset[str]) -> None:
        manifest = self._registry.get(module_id)
        if not isinstance(permissions, frozenset):
            raise InvalidModelError("permissions must be an immutable frozenset")
        declared = set(manifest.permissions)
        if not permissions.issubset(declared):
            raise InvalidModelError("grant contains permissions not declared by module")
        with self._lock:
            self._grants[module_id] = permissions

    def revoke(self, module_id: str) -> bool:
        self._registry.get(module_id)
        with self._lock:
            return self._grants.pop(module_id, None) is not None

    def register_handler(self, module_id: str, operation_id: str, handler: ModuleHandler) -> None:
        operation = self._registry.resolve_operation(module_id, operation_id)
        if not callable(handler):
            raise InvalidModelError("handler must be callable")
        key = (module_id, operation.operation_id)
        with self._lock:
            if key in self._handlers:
                raise InvalidModelError("handler already registered")
            self._handlers[key] = handler

    def _reserve_resources(self, request: ModuleRequest) -> ResourceLease | None:
        if not request.resource_limits:
            return None
        allocator = self._resource_allocator
        if allocator is None:
            raise RuntimeError("resource allocator is not configured")
        capacities = {item.name: item for item in allocator.capacity()}
        requested: list[ResourceMetric] = []
        for name, amount in sorted(request.resource_limits.items()):
            capacity = capacities.get(name)
            if capacity is None:
                raise ValueError(f"resource metric is not host-configured: {name}")
            requested.append(ResourceMetric(name, amount, capacity.unit))
        return allocator.allocate(request.request_id, tuple(requested))

    def invoke(self, request: ModuleRequest) -> ModuleResponse:
        if not isinstance(request, ModuleRequest):
            raise InvalidModelError("request must be a validated ModuleRequest")
        try:
            operation = self._registry.resolve_operation(request.module_id, request.operation)
        except InvalidModelError:
            return ModuleResponse(
                request_id=request.request_id, status="REJECTED",
                error_code="module.operation_not_found",
            )

        if request.schema_version != operation.input_schema_version:
            return ModuleResponse(
                request_id=request.request_id, status="REJECTED",
                error_code="module.input_schema_mismatch",
            )

        key = (request.module_id, request.operation)
        with self._lock:
            granted = self._grants.get(request.module_id, frozenset())
            handler = self._handlers.get(key)

        required = frozenset(operation.required_permissions)
        if not required.issubset(granted):
            return ModuleResponse(
                request_id=request.request_id, status="REJECTED",
                error_code="module.permission_denied",
            )
        if handler is None:
            return ModuleResponse(
                request_id=request.request_id, status="REJECTED",
                error_code="module.handler_unavailable",
            )

        try:
            lease = self._reserve_resources(request)
        except (ValueError, RuntimeError, OverflowError):
            return ModuleResponse(
                request_id=request.request_id, status="REJECTED",
                error_code="module.resource_reservation_failed",
            )

        warnings = (
            ("Host quota reservation acquired for this invocation; it is not an OS resource limit.",)
            if lease is not None else ()
        )
        try:
            outputs = handler(request.inputs)
            return ModuleResponse(
                request_id=request.request_id, status="COMPLETED",
                outputs=outputs, warnings=warnings,
            )
        except Exception:
            # Do not expose exception text, traceback, or secrets to the caller.
            return ModuleResponse(
                request_id=request.request_id, status="ERROR",
                error_code="module.handler_failed", warnings=warnings,
            )
        finally:
            if lease is not None:
                self._resource_allocator.release(lease.lease_id)
