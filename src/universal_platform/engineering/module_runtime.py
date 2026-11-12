"""Policy-gated in-process execution for explicitly registered trusted handlers.

This is an application-level permission boundary, not an OS sandbox. Handler
callables are supplied by trusted application code; this module never imports
or downloads code based on a request. Optional resource leases reserve host-
configured quota for one invocation and are always released afterward.
"""
from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from math import isfinite
from threading import Condition, RLock
from typing import Any

from .contracts import ModuleRequest, ModuleResponse
from .errors import InvalidModelError
from .module_registry import ModuleRegistry
from ..runtime.resources.allocator import ResourceAllocator, ResourceLease
from ..runtime.resources.models import ResourceMetric

ModuleHandler = Callable[[Mapping[str, Any]], Mapping[str, Any]]

_SCHEMA_ANNOTATIONS = frozenset({
    "$schema", "$id", "title", "description", "default", "examples",
    "x-schema-version",
})
_SCHEMA_KEYWORDS = frozenset({
    "type", "required", "properties", "additionalProperties", "items",
    "minItems", "maxItems", "minProperties", "maxProperties",
    "minLength", "maxLength", "minimum", "maximum", "enum", "const",
})


def _output_schema_error(value: Any, schema: Mapping[str, Any], path: str = "outputs",
                         depth: int = 0, budget: list[int] | None = None) -> str | None:
    """Validate the deliberately supported, fail-closed JSON Schema subset."""
    if budget is None:
        budget = [10000]
    budget[0] -= 1
    if budget[0] < 0 or depth > 64:
        return f"{path} exceeds output validation limits"
    unsupported = set(schema) - _SCHEMA_KEYWORDS - _SCHEMA_ANNOTATIONS
    if unsupported:
        return f"{path} schema uses unsupported keywords"
    expected = schema.get("type")
    valid = {
        "object": lambda item: isinstance(item, Mapping),
        "array": lambda item: isinstance(item, (list, tuple)),
        "string": lambda item: isinstance(item, str),
        "boolean": lambda item: isinstance(item, bool),
        "integer": lambda item: isinstance(item, int) and not isinstance(item, bool),
        "number": lambda item: isinstance(item, (int, float)) and not isinstance(item, bool),
        "null": lambda item: item is None,
    }
    if not isinstance(expected, str) or expected not in valid:
        return f"{path} schema has an unsupported or missing type"
    if not valid[expected](value):
        return f"{path} must be {expected}"
    if "const" in schema and value != schema["const"]:
        return f"{path} does not match const"
    if "enum" in schema:
        if not isinstance(schema["enum"], tuple):
            return f"{path} schema has an invalid enum rule"
        if value not in schema["enum"]:
            return f"{path} is not an allowed value"
    if expected == "object":
        required = schema.get("required", ())
        properties = schema.get("properties", {})
        if not isinstance(properties, Mapping) or not isinstance(required, tuple):
            return f"{path} schema has invalid object rules"
        if any(key not in value for key in required):
            return f"{path} is missing required properties"
        if len(value) < schema.get("minProperties", 0) or len(value) > schema.get("maxProperties", float("inf")):
            return f"{path} property count is outside bounds"
        additional = schema.get("additionalProperties", True)
        if not isinstance(additional, (bool, Mapping)):
            return f"{path} schema has an invalid additionalProperties rule"
        if any(not isinstance(child, Mapping) for child in properties.values()):
            return f"{path} schema has an invalid property schema"
        for key, item in value.items():
            child_schema = properties.get(key)
            if child_schema is None:
                if additional is False:
                    return f"{path}.{key} is not allowed"
                if isinstance(additional, Mapping):
                    child_schema = additional
            if isinstance(child_schema, Mapping):
                error = _output_schema_error(item, child_schema, f"{path}.{key}", depth + 1, budget)
                if error:
                    return error
    elif expected == "array":
        if len(value) < schema.get("minItems", 0) or len(value) > schema.get("maxItems", float("inf")):
            return f"{path} item count is outside bounds"
        item_schema = schema.get("items")
        if item_schema is not None:
            if not isinstance(item_schema, Mapping):
                return f"{path} schema has invalid items rule"
            for index, item in enumerate(value):
                error = _output_schema_error(item, item_schema, f"{path}[{index}]", depth + 1, budget)
                if error:
                    return error
    elif expected == "string":
        if len(value) < schema.get("minLength", 0) or len(value) > schema.get("maxLength", float("inf")):
            return f"{path} length is outside bounds"
    elif expected in {"integer", "number"}:
        if isinstance(value, float) and not isfinite(value):
            return f"{path} must be finite"
        if "minimum" in schema and value < schema["minimum"]:
            return f"{path} is below minimum"
        if "maximum" in schema and value > schema["maximum"]:
            return f"{path} is above maximum"
    return None


def _validate_module_output(outputs: Any, operation: Any) -> str | None:
    schema = operation.output_schema
    if schema is None:
        return "operation has no registered output schema"
    if schema.get("x-schema-version") != operation.output_schema_version:
        return "output schema version does not match operation declaration"
    return _output_schema_error(outputs, schema)


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
        self._active_invocations: dict[str, int] = {}
        self._revoking: set[str] = set()
        self._lock = RLock()
        self._condition = Condition(self._lock)

    def grant(self, module_id: str, permissions: frozenset[str]) -> None:
        manifest = self._registry.get(module_id)
        if not isinstance(permissions, frozenset):
            raise InvalidModelError("permissions must be an immutable frozenset")
        declared = set(manifest.permissions)
        if not permissions.issubset(declared):
            raise InvalidModelError("grant contains permissions not declared by module")
        with self._condition:
            if module_id in self._revoking:
                raise InvalidModelError("module grant is being revoked")
            self._grants[module_id] = permissions

    def revoke(self, module_id: str) -> bool:
        """Block new invocations, then wait for admitted work to drain."""
        self._registry.get(module_id)
        with self._condition:
            if module_id in self._revoking:
                while module_id in self._revoking:
                    self._condition.wait()
                return False
            if self._grants.pop(module_id, None) is None:
                return False
            self._revoking.add(module_id)
            self._condition.notify_all()
            try:
                while self._active_invocations.get(module_id, 0):
                    self._condition.wait()
            finally:
                self._revoking.discard(module_id)
                self._condition.notify_all()
            return True

    def _finish_invocation(self, module_id: str) -> None:
        with self._condition:
            active = self._active_invocations.get(module_id, 0)
            if active <= 1:
                self._active_invocations.pop(module_id, None)
            else:
                self._active_invocations[module_id] = active - 1
            self._condition.notify_all()

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
        return allocator.allocate(request.request_id, tuple(requested), ttl_seconds=None)

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
        if operation.output_schema is None:
            return ModuleResponse(
                request_id=request.request_id, status="REJECTED",
                error_code="module.output_schema_unavailable",
            )
        if operation.output_schema.get("x-schema-version") != operation.output_schema_version:
            return ModuleResponse(
                request_id=request.request_id, status="REJECTED",
                error_code="module.output_schema_mismatch",
            )

        key = (request.module_id, request.operation)
        required = frozenset(operation.required_permissions)
        # Admission and active-count increment share revoke's condition lock.
        with self._condition:
            granted = self._grants.get(request.module_id, frozenset())
            handler = self._handlers.get(key)
            if request.module_id in self._revoking or not required.issubset(granted):
                return ModuleResponse(
                    request_id=request.request_id, status="REJECTED",
                    error_code="module.permission_denied",
                )
            if handler is None:
                return ModuleResponse(
                    request_id=request.request_id, status="REJECTED",
                    error_code="module.handler_unavailable",
                )
            self._active_invocations[request.module_id] = (
                self._active_invocations.get(request.module_id, 0) + 1
            )

        lease: ResourceLease | None = None
        try:
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
                try:
                    outputs = handler(request.inputs)
                except Exception:
                    return ModuleResponse(
                        request_id=request.request_id, status="ERROR",
                        error_code="module.handler_failed", warnings=warnings,
                    )
                try:
                    validation_error = _validate_module_output(outputs, operation)
                except Exception:
                    validation_error = "output schema validation failed"
                if validation_error is not None:
                    return ModuleResponse(
                        request_id=request.request_id, status="ERROR",
                        error_code="module.output_validation_failed", warnings=warnings,
                    )
                try:
                    return ModuleResponse(
                        request_id=request.request_id, status="COMPLETED",
                        outputs=outputs, warnings=warnings,
                    )
                except InvalidModelError:
                    return ModuleResponse(
                        request_id=request.request_id, status="ERROR",
                        error_code="module.output_validation_failed", warnings=warnings,
                    )
            finally:
                if lease is not None:
                    self._resource_allocator.release(lease.lease_id)
        finally:
            # Drain includes reservation failures, handler completion and lease release.
            self._finish_invocation(request.module_id)
