"""Policy-gated dispatch to trusted handlers or host-configured supervised workers.

This is an application-level permission boundary, not an OS sandbox. In-process
handler callables and worker executable specifications are supplied by trusted
host code; requests never load code or choose process configuration. Optional
resource leases reserve host-configured quota and are released only after worker
termination is confirmed; unconfirmed worker exits quarantine the lease.
"""
from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from math import isfinite
from threading import Condition, RLock
from typing import Any, Protocol, runtime_checkable
from uuid import uuid4

from ..runtime.process_reconciliation import ProcessIdentityInspector
from ..runtime.resources.allocator import ResourceLease
from ..runtime.resources.models import ResourceMetric
from ..runtime.worker_ipc import WorkerInvocationHandle, WorkerIPCClient, WorkerIPCError
from ..runtime.worker_protocol import WorkerFrame, WorkerProtocolError
from .contracts import ModuleRequest, ModuleResponse
from .errors import InvalidModelError
from .module_registry import ModuleRegistry

_PROCESS_HOST_INSTANCE_ID = uuid4().hex


class ResourceLeasePort(Protocol):
    """Minimal lease surface consumed by ModuleRuntime."""

    lease_id: str


@runtime_checkable
class ResourceAllocatorPort(Protocol):
    """Host-supplied quota allocator; implementations may be in-memory or durable."""

    def capacity(self) -> tuple[ResourceMetric, ...]: ...
    def allocate(
        self,
        owner_id: str,
        requested: tuple[ResourceMetric, ...],
        *,
        ttl_seconds: float | None = 60.0,
    ) -> ResourceLeasePort: ...
    def quarantine(self, lease_id: str, reason: str) -> bool: ...
    def release(self, lease_id: str) -> bool: ...


ModuleHandler = Callable[[Mapping[str, Any]], Mapping[str, Any]]
RegisteredHandler = ModuleHandler | WorkerIPCClient

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


def _validate_module_input(inputs: Any, operation: Any) -> str | None:
    schema = operation.input_schema
    if schema is None:
        return "operation has no registered input schema"
    if schema.get("x-schema-version") != operation.input_schema_version:
        return "input schema version does not match operation declaration"
    return _output_schema_error(inputs, schema, path="inputs")


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
    grant. Worker process configuration is host-owned. Resource limits are
    reservation requests against a host-configured in-memory quota pool; they
    do not limit actual CPU, memory, I/O or runtime. A lease is retained in
    quarantine if the supervisor cannot confirm worker process-tree exit.
    """

    def __init__(
        self,
        registry: ModuleRegistry,
        *,
        resource_allocator: ResourceAllocatorPort | None = None,
        host_instance_id: str | None = None,
        process_identity_inspector: ProcessIdentityInspector | None = None,
    ) -> None:
        if not isinstance(registry, ModuleRegistry):
            raise InvalidModelError("registry must be a ModuleRegistry")
        if resource_allocator is not None and not isinstance(resource_allocator, ResourceAllocatorPort):
            raise InvalidModelError("resource_allocator must implement the resource allocator contract")
        if host_instance_id is not None and (
            not isinstance(host_instance_id, str) or not host_instance_id.strip() or "\\x00" in host_instance_id
        ):
            raise InvalidModelError("host_instance_id must be a non-empty NUL-free string")
        if process_identity_inspector is not None and not callable(
            getattr(process_identity_inspector, "inspect", None)
        ):
            raise InvalidModelError("process_identity_inspector must provide inspect(identity)")
        self._registry = registry
        self._resource_allocator = resource_allocator
        self._host_instance_id = host_instance_id or _PROCESS_HOST_INSTANCE_ID
        self._process_identity_inspector = process_identity_inspector or ProcessIdentityInspector()
        reconcile_startup = getattr(resource_allocator, "reconcile_startup", None)
        if (
            callable(reconcile_startup)
            and getattr(resource_allocator, "startup_reconciliation_required", False)
        ):
            reconcile_startup(
                self._process_identity_inspector,
                current_host_instance_id=self._host_instance_id,
            )
        self._handlers: dict[tuple[str, str], RegisteredHandler] = {}
        self._worker_invocations: dict[str, tuple[WorkerIPCClient, WorkerInvocationHandle]] = {}
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

    def register_worker_handler(
        self,
        module_id: str,
        operation_id: str,
        client: WorkerIPCClient,
    ) -> None:
        """Register a host-configured supervised worker for one declared operation."""
        operation = self._registry.resolve_operation(module_id, operation_id)
        if not isinstance(client, WorkerIPCClient):
            raise InvalidModelError("client must be a WorkerIPCClient")
        if operation.input_schema is None:
            raise InvalidModelError("worker handler requires a declared input schema")
        if operation.output_schema is None:
            raise InvalidModelError("worker handler requires a declared output schema")
        if not operation.required_permissions:
            raise InvalidModelError(
                "worker handler operation must declare at least one host permission"
            )
        key = (module_id, operation.operation_id)
        with self._lock:
            if key in self._handlers:
                raise InvalidModelError("handler already registered")
            self._handlers[key] = client

    def cancel(self, request_id: str) -> bool:
        """Cancel an admitted supervised worker invocation by request_id."""
        if (
            not isinstance(request_id, str)
            or not request_id.strip()
            or len(request_id) > 128
            or "\x00" in request_id
        ):
            return False
        with self._lock:
            invocation = self._worker_invocations.get(request_id)
        if invocation is None:
            return False
        client, handle = invocation
        try:
            return client.cancel(handle)
        except Exception:  # noqa: BLE001
            # Cancellation is a boolean control API; lease safety is enforced
            # independently by the invocation's termination result.
            return False

    def _reserve_resources(
        self,
        request: ModuleRequest,
        *,
        worker_handle: WorkerInvocationHandle | None = None,
    ) -> ResourceLeasePort | None:
        allocator = self._resource_allocator
        if not request.resource_limits:
            if worker_handle is None or allocator is None:
                return None
            allocate_worker = getattr(allocator, "allocate_worker", None)
            bind_process_identity = getattr(allocator, "bind_process_identity", None)
            if callable(allocate_worker) and callable(bind_process_identity):
                return allocate_worker(
                    request.request_id,
                    (),
                    host_instance_id=self._host_instance_id,
                    worker_id=worker_handle.worker_id,
                )
            return None
        if allocator is None:
            raise RuntimeError("resource allocator is not configured")
        capacities = {item.name: item for item in allocator.capacity()}
        requested: list[ResourceMetric] = []
        for name, amount in sorted(request.resource_limits.items()):
            capacity = capacities.get(name)
            if capacity is None:
                raise ValueError(f"resource metric is not host-configured: {name}")
            requested.append(ResourceMetric(name, amount, capacity.unit))
        if worker_handle is not None:
            allocate_worker = getattr(allocator, "allocate_worker", None)
            bind_process_identity = getattr(allocator, "bind_process_identity", None)
            if callable(allocate_worker) and callable(bind_process_identity):
                return allocate_worker(
                    request.request_id,
                    tuple(requested),
                    host_instance_id=self._host_instance_id,
                    worker_id=worker_handle.worker_id,
                )
            return allocator.allocate(request.request_id, tuple(requested), ttl_seconds=None)
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
        worker_handle: WorkerInvocationHandle | None = None
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
            if isinstance(handler, WorkerIPCClient):
                if request.request_id in self._worker_invocations:
                    return ModuleResponse(
                        request_id=request.request_id, status="REJECTED",
                        error_code="module.request_id_already_active",
                    )
                try:
                    input_validation_error = _validate_module_input(request.inputs, operation)
                except Exception:  # noqa: BLE001
                    input_validation_error = "input schema validation failed"
                if input_validation_error is not None:
                    return ModuleResponse(
                        request_id=request.request_id, status="REJECTED",
                        error_code="module.input_validation_failed",
                    )
                try:
                    worker_handle = handler.reserve(request.request_id)
                except WorkerIPCError as error:
                    return ModuleResponse(
                        request_id=request.request_id, status="REJECTED",
                        error_code=(
                            "module.worker_request_invalid"
                            if error.code == "worker.request_invalid"
                            else "module.request_id_already_active"
                        ),
                    )
                self._worker_invocations[request.request_id] = (handler, worker_handle)
            self._active_invocations[request.module_id] = (
                self._active_invocations.get(request.module_id, 0) + 1
            )

        lease: ResourceLease | None = None
        lease_quarantined = False
        try:
            try:
                if isinstance(handler, WorkerIPCClient):
                    lease = self._reserve_resources(
                        request,
                        worker_handle=worker_handle,
                    )
                else:
                    lease = self._reserve_resources(request)
            except (ValueError, RuntimeError, OverflowError):
                return ModuleResponse(
                    request_id=request.request_id, status="REJECTED",
                    error_code="module.resource_reservation_failed",
                )

            identity_binder = getattr(self._resource_allocator, "bind_process_identity", None)
            supports_durable_worker_identity = (
                callable(getattr(self._resource_allocator, "allocate_worker", None))
                and callable(identity_binder)
            )
            warnings = (
                (
                    "Durable worker identity lease acquired; it is not an OS resource limit.",
                    "The supervised worker identity is persisted before its payload is allowed to execute.",
                )
                if lease is not None
                and supports_durable_worker_identity
                and worker_handle is not None
                and not getattr(lease, "allocations", ())
                else (
                    "Host quota and durable worker identity reservation acquired; it is not an OS resource limit.",
                    "The supervised worker identity is persisted before its payload is allowed to execute.",
                )
                if lease is not None and supports_durable_worker_identity and worker_handle is not None
                else ("Host quota reservation acquired for this invocation; it is not an OS resource limit.",)
                if lease is not None else ()
            )
            try:
                if isinstance(handler, WorkerIPCClient):
                    try:
                        request_payload = {
                            "module_id": request.module_id,
                            "operation": request.operation,
                            "schema_version": request.schema_version,
                            "inputs": request.to_dict()["inputs"],
                            "assumptions": list(request.assumptions),
                            "source_refs": list(request.source_refs),
                            "resource_limits": {
                                name: request.resource_limits[name]
                                for name in sorted(request.resource_limits)
                            },
                        }
                        if lease is not None and supports_durable_worker_identity:
                            response_frame = handler.request(
                                WorkerFrame("REQUEST", request.request_id, request_payload),
                                handle=worker_handle,
                                host_instance_id=self._host_instance_id,
                                on_process_started=lambda identity: identity_binder(
                                    lease.lease_id,
                                    identity,
                                ),
                            )
                        else:
                            response_frame = handler.request(
                                WorkerFrame("REQUEST", request.request_id, request_payload),
                                handle=worker_handle,
                            )
                        if set(response_frame.payload) != {"outputs"}:
                            raise WorkerIPCError(
                                "worker.response_contract_invalid",
                                "worker response payload must contain only outputs",
                            )
                        outputs = response_frame.payload["outputs"]
                        if not isinstance(outputs, Mapping):
                            raise WorkerIPCError(
                                "worker.response_contract_invalid",
                                "worker outputs must be a JSON object",
                            )
                    except WorkerProtocolError:
                        return ModuleResponse(
                            request_id=request.request_id, status="REJECTED",
                            error_code="module.worker_request_invalid", warnings=warnings,
                        )
                    except WorkerIPCError as error:
                        if not error.termination_confirmed and lease is not None:
                            # Retain the lease even if writing quarantine metadata
                            # itself fails; ttl_seconds=None prevents silent expiry.
                            lease_quarantined = True
                            try:
                                quarantine_recorded = self._resource_allocator.quarantine(
                                    lease.lease_id,
                                    "worker process-tree termination was not confirmed",
                                )
                            except Exception:  # noqa: BLE001
                                quarantine_recorded = False
                            warnings = warnings + ((
                                "Resource lease quarantined because worker termination was not confirmed; operator inspection is required."
                                if quarantine_recorded else
                                "Resource lease remains allocated because worker termination was not confirmed, but quarantine metadata could not be recorded; manual operator inspection is required."
                            ),)
                        if error.code == "worker.cancelled":
                            return ModuleResponse(
                                request_id=request.request_id, status="CANCELLED",
                                warnings=warnings,
                            )
                        mapped = (
                            "module.worker_termination_unconfirmed"
                            if error.code == "worker.termination_unconfirmed"
                            else "module.worker_timeout"
                            if error.code == "worker.timeout"
                            else "module.worker_request_invalid"
                            if error.code == "worker.request_invalid"
                            else "module.worker_identity_handoff_failed"
                            if error.code.startswith("worker.identity_handoff_")
                            else "module.worker_response_invalid"
                            if error.code.startswith("worker.response_")
                            else "module.worker_failed"
                        )
                        return ModuleResponse(
                            request_id=request.request_id, status="ERROR",
                            error_code=mapped, warnings=warnings,
                        )
                else:
                    try:
                        outputs = handler(request.inputs)
                    except Exception:  # noqa: BLE001
                        return ModuleResponse(
                            request_id=request.request_id, status="ERROR",
                            error_code="module.handler_failed", warnings=warnings,
                        )
                try:
                    validation_error = _validate_module_output(outputs, operation)
                except Exception:  # noqa: BLE001
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
                if lease is not None and not lease_quarantined:
                    self._resource_allocator.release(lease.lease_id)
        finally:
            with self._lock:
                if isinstance(handler, WorkerIPCClient):
                    invocation = self._worker_invocations.pop(request.request_id, None)
                    if invocation is not None:
                        handler.release(invocation[1])
            # Drain includes reservation failures, handler completion and lease release/quarantine.
            self._finish_invocation(request.module_id)
