from datetime import datetime, timezone
import sys
import threading
import time

import pytest

from universal_platform.engineering.contracts import ModuleRequest
from universal_platform.engineering.errors import InvalidModelError
from universal_platform.engineering.module_registry import (
    ModuleManifest,
    ModuleOperation,
    ModuleRegistry,
)
from universal_platform.engineering.module_runtime import ModuleRuntime
from universal_platform.runtime.resources.allocator import ResourceAllocator
from universal_platform.runtime.resources.durable_allocator import DurableResourceAllocator
from universal_platform.runtime.resources.models import ResourceMetric
from universal_platform.runtime.process_identity import ProcessIdentity
from universal_platform.runtime.process_reconciliation import ProcessLiveness, ProcessLivenessEvidence
from universal_platform.runtime.worker_ipc import WorkerIPCClient


def setup_runtime(required=("engineering.calculate",)):
    registry = ModuleRegistry()
    registry.register(ModuleManifest(
        module_id="org.example.calc", version="1.0.0", domain="calculation",
        operations=(ModuleOperation(
            "calculate.sum", input_schema_version="1.0",
            required_permissions=required,
            output_schema={
                "type": "object",
                "x-schema-version": "1.0",
                "required": ["total"],
                "properties": {"total": {"type": "number"}},
                "additionalProperties": False,
            },
        ),),
        permissions=("engineering.calculate", "engineering.read"),
        license_id="Apache-2.0",
    ))
    runtime = ModuleRuntime(registry)
    return registry, runtime


def request(**changes):
    values = {
        "module_id": "org.example.calc", "operation": "calculate.sum",
        "inputs": {"values": [2, 3]}, "permissions": (),
    }
    values.update(changes)
    return ModuleRequest(**values)


def test_runtime_invokes_only_registered_handler_with_host_grant():
    _, runtime = setup_runtime()
    runtime.register_handler("org.example.calc", "calculate.sum",
                             lambda inputs: {"total": sum(inputs["values"])})
    runtime.grant("org.example.calc", frozenset({"engineering.calculate"}))
    result = runtime.invoke(request())
    assert result.status == "COMPLETED"
    assert result.outputs["total"] == 5


def test_request_cannot_self_grant_permissions():
    _, runtime = setup_runtime()
    called = []
    runtime.register_handler("org.example.calc", "calculate.sum",
                             lambda inputs: called.append(True) or {"ok": True})
    result = runtime.invoke(request(permissions=("engineering.calculate",)))
    assert result.status == "REJECTED"
    assert result.error_code == "module.permission_denied"
    assert called == []


def test_missing_grant_and_revoked_grant_fail_closed():
    _, runtime = setup_runtime()
    runtime.register_handler("org.example.calc", "calculate.sum", lambda _: {"total": 1})
    assert runtime.invoke(request()).error_code == "module.permission_denied"
    runtime.grant("org.example.calc", frozenset({"engineering.calculate"}))
    assert runtime.invoke(request()).status == "COMPLETED"
    assert runtime.revoke("org.example.calc") is True
    assert runtime.invoke(request()).error_code == "module.permission_denied"


def test_grant_cannot_exceed_manifest_permissions():
    _, runtime = setup_runtime()
    with pytest.raises(InvalidModelError, match="not declared"):
        runtime.grant("org.example.calc", frozenset({"hardware.write"}))


def test_unregistered_handler_and_unknown_operation_rejected():
    _, runtime = setup_runtime()
    runtime.grant("org.example.calc", frozenset({"engineering.calculate"}))
    assert runtime.invoke(request()).error_code == "module.handler_unavailable"
    result = runtime.invoke(request(operation="calculate.unknown"))
    assert result.status == "REJECTED"
    assert result.error_code == "module.operation_not_found"


def test_schema_mismatch_rejected_before_handler():
    _, runtime = setup_runtime()
    called = []
    runtime.register_handler("org.example.calc", "calculate.sum",
                             lambda _: called.append(True) or {})
    runtime.grant("org.example.calc", frozenset({"engineering.calculate"}))
    result = runtime.invoke(request(schema_version="2.0"))
    assert result.error_code == "module.input_schema_mismatch"
    assert called == []


def test_handler_failure_is_sanitized():
    _, runtime = setup_runtime()
    def fail(_):
        raise RuntimeError("secret token must not leak")
    runtime.register_handler("org.example.calc", "calculate.sum", fail)
    runtime.grant("org.example.calc", frozenset({"engineering.calculate"}))
    result = runtime.invoke(request())
    assert result.status == "ERROR"
    assert result.error_code == "module.handler_failed"
    assert "secret" not in repr(result.to_dict())


def test_duplicate_handler_registration_rejected():
    _, runtime = setup_runtime()
    handler = lambda _: {}
    runtime.register_handler("org.example.calc", "calculate.sum", handler)
    with pytest.raises(InvalidModelError, match="already"):
        runtime.register_handler("org.example.calc", "calculate.sum", handler)


def test_runtime_does_not_accept_non_contract_requests():
    _, runtime = setup_runtime()
    with pytest.raises(InvalidModelError, match="ModuleRequest"):
        runtime.invoke({"module_id": "org.example.calc"})




def make_runtime_with_allocator(capacity=2):
    registry, _ = setup_runtime()
    allocator = ResourceAllocator((ResourceMetric("cpu.cores", capacity, "cores"),))
    runtime = ModuleRuntime(registry, resource_allocator=allocator)
    runtime.register_handler(
        "org.example.calc", "calculate.sum",
        lambda inputs: {"total": sum(inputs["values"])},
    )
    runtime.grant("org.example.calc", frozenset({"engineering.calculate"}))
    return runtime, allocator


def test_runtime_reserves_host_quota_for_invocation_and_releases_after_success():
    runtime, allocator = make_runtime_with_allocator()
    result = runtime.invoke(request(resource_limits={"cpu.cores": 1}))
    assert result.status == "COMPLETED"
    assert result.warnings
    assert "not an OS resource limit" in result.warnings[0]
    assert allocator.active_leases() == ()
    assert allocator.available()[0].value == 2


def test_runtime_rejects_overcommit_before_handler_and_does_not_leak_lease():
    registry, _ = setup_runtime()
    allocator = ResourceAllocator((ResourceMetric("cpu.cores", 0.5, "cores"),))
    runtime = ModuleRuntime(registry, resource_allocator=allocator)
    called = []
    runtime.register_handler(
        "org.example.calc", "calculate.sum",
        lambda inputs: called.append(True) or {"total": 5},
    )
    runtime.grant("org.example.calc", frozenset({"engineering.calculate"}))
    result = runtime.invoke(request(resource_limits={"cpu.cores": 1}))
    assert result.status == "REJECTED"
    assert result.error_code == "module.resource_reservation_failed"
    assert called == []
    assert allocator.active_leases() == ()


def test_runtime_rejects_resource_request_without_host_allocator():
    _, runtime = setup_runtime()
    runtime.register_handler("org.example.calc", "calculate.sum", lambda _: {"ok": True})
    runtime.grant("org.example.calc", frozenset({"engineering.calculate"}))
    result = runtime.invoke(request(resource_limits={"cpu.cores": 1}))
    assert result.status == "REJECTED"
    assert result.error_code == "module.resource_reservation_failed"


def test_runtime_releases_resource_lease_when_handler_fails():
    registry, _ = setup_runtime()
    allocator = ResourceAllocator((ResourceMetric("cpu.cores", 1, "cores"),))
    runtime = ModuleRuntime(registry, resource_allocator=allocator)

    def fail(_):
        raise RuntimeError("private failure detail")

    runtime.register_handler("org.example.calc", "calculate.sum", fail)
    runtime.grant("org.example.calc", frozenset({"engineering.calculate"}))
    result = runtime.invoke(request(resource_limits={"cpu.cores": 1}))
    assert result.status == "ERROR"
    assert result.error_code == "module.handler_failed"
    assert allocator.active_leases() == ()
    assert allocator.available()[0].value == 1


def test_runtime_rejects_unknown_host_resource_metric():
    runtime, allocator = make_runtime_with_allocator()
    result = runtime.invoke(request(resource_limits={"gpu.units": 1}))
    assert result.status == "REJECTED"
    assert result.error_code == "module.resource_reservation_failed"
    assert allocator.active_leases() == ()


from datetime import UTC, datetime, timedelta


def test_runtime_lease_remains_reserved_until_long_handler_returns():
    registry, _ = setup_runtime()
    allocator = ResourceAllocator((ResourceMetric("cpu.cores", 1, "cores"),))
    observed = []

    def long_running_handler(_):
        future = datetime.now(UTC) + timedelta(days=30)
        active = allocator.active_leases(now=future)
        observed.extend(active)
        assert len(active) == 1
        assert active[0].expires_at is None
        assert allocator.available(now=future)[0].value == 0
        return {"total": 1}

    runtime = ModuleRuntime(registry, resource_allocator=allocator)
    runtime.register_handler("org.example.calc", "calculate.sum", long_running_handler)
    runtime.grant("org.example.calc", frozenset({"engineering.calculate"}))
    result = runtime.invoke(request(resource_limits={"cpu.cores": 1}))

    assert result.status == "COMPLETED"
    assert len(observed) == 1
    assert allocator.active_leases() == ()
    assert allocator.available()[0].value == 1



def test_output_schema_rejects_missing_required_field_and_never_completes():
    _, runtime = setup_runtime()
    runtime.register_handler("org.example.calc", "calculate.sum", lambda _: {})
    runtime.grant("org.example.calc", frozenset({"engineering.calculate"}))
    result = runtime.invoke(request())
    assert result.status == "ERROR"
    assert result.error_code == "module.output_validation_failed"


@pytest.mark.parametrize("outputs", [
    {"total": "5"},
    {"total": 5, "unexpected": True},
    {"total": {"value": 5}},
])
def test_output_schema_rejects_wrong_type_and_unknown_fields(outputs):
    _, runtime = setup_runtime()
    runtime.register_handler("org.example.calc", "calculate.sum", lambda _: outputs)
    runtime.grant("org.example.calc", frozenset({"engineering.calculate"}))
    result = runtime.invoke(request())
    assert result.status == "ERROR"
    assert result.error_code == "module.output_validation_failed"


def test_output_schema_version_must_match_operation_declaration():
    with pytest.raises(InvalidModelError, match="x-schema-version"):
        ModuleOperation(
            "calculate.sum", output_schema_version="2.0",
            output_schema={
                "type": "object", "x-schema-version": "1.0",
                "properties": {}, "additionalProperties": False,
            },
        )


def test_output_schema_is_required_before_handler_dispatch():
    registry_without_schema = ModuleRegistry()
    registry_without_schema.register(ModuleManifest(
        module_id="org.example.calc", version="1.0.0", domain="calculation",
        operations=(ModuleOperation("calculate.sum"),),
        permissions=("engineering.calculate",),
        license_id="Apache-2.0",
    ))
    runtime = ModuleRuntime(registry_without_schema)
    called = []
    runtime.register_handler("org.example.calc", "calculate.sum",
                             lambda _: called.append(True) or {"total": 5})
    runtime.grant("org.example.calc", frozenset({"engineering.calculate"}))
    result = runtime.invoke(request())
    assert result.status == "REJECTED"
    assert result.error_code == "module.output_schema_unavailable"
    assert called == []


def test_output_schema_validates_nested_objects_and_array_item_types():
    registry = ModuleRegistry()
    registry.register(ModuleManifest(
        module_id="org.example.calc", version="1.0.0", domain="calculation",
        operations=(ModuleOperation(
            "calculate.sum",
            output_schema={
                "type": "object", "x-schema-version": "1.0",
                "required": ["items"],
                "properties": {
                    "items": {"type": "array", "items": {"type": "integer"}},
                },
                "additionalProperties": False,
            },
        ),),
        permissions=("engineering.calculate",), license_id="Apache-2.0",
    ))
    runtime = ModuleRuntime(registry)
    runtime.register_handler("org.example.calc", "calculate.sum",
                             lambda _: {"items": [1, "2"]})
    runtime.grant("org.example.calc", frozenset({"engineering.calculate"}))
    result = runtime.invoke(request())
    assert result.status == "ERROR"
    assert result.error_code == "module.output_validation_failed"



def test_output_schema_rejects_non_finite_numbers():
    _, runtime = setup_runtime()
    runtime.register_handler(
        "org.example.calc", "calculate.sum",
        lambda _: {"total": float("nan")},
    )
    runtime.grant("org.example.calc", frozenset({"engineering.calculate"}))
    result = runtime.invoke(request())
    assert result.status == "ERROR"
    assert result.error_code == "module.output_validation_failed"


def test_output_schema_fails_closed_on_unsupported_keywords():
    registry = ModuleRegistry()
    registry.register(ModuleManifest(
        module_id="org.example.calc", version="1.0.0", domain="calculation",
        operations=(ModuleOperation(
            "calculate.sum",
            output_schema={
                "type": "object", "x-schema-version": "1.0",
                "required": ["label"],
                "properties": {"label": {"type": "string", "pattern": "^ok$"}},
                "additionalProperties": False,
            },
        ),),
        permissions=("engineering.calculate",), license_id="Apache-2.0",
    ))
    runtime = ModuleRuntime(registry)
    runtime.register_handler("org.example.calc", "calculate.sum",
                             lambda _: {"label": "ok"})
    runtime.grant("org.example.calc", frozenset({"engineering.calculate"}))
    result = runtime.invoke(request())
    assert result.status == "ERROR"
    assert result.error_code == "module.output_validation_failed"


def test_output_schema_is_detached_and_immutable():
    source = {
        "type": "object", "x-schema-version": "1.0",
        "properties": {"total": {"type": "number"}},
        "additionalProperties": False,
    }
    operation = ModuleOperation("calculate.sum", output_schema=source)
    source["properties"]["total"]["type"] = "string"
    assert operation.output_schema["properties"]["total"]["type"] == "number"
    with pytest.raises(TypeError):
        operation.output_schema["properties"]["total"]["type"] = "string"



def test_output_schema_fails_closed_on_malformed_nested_schema_rules():
    registry = ModuleRegistry()
    registry.register(ModuleManifest(
        module_id="org.example.calc", version="1.0.0", domain="calculation",
        operations=(ModuleOperation(
            "calculate.sum",
            output_schema={
                "type": "object", "x-schema-version": "1.0",
                "properties": {"total": "number"},
                "additionalProperties": False,
            },
        ),),
        permissions=("engineering.calculate",), license_id="Apache-2.0",
    ))
    runtime = ModuleRuntime(registry)
    runtime.register_handler("org.example.calc", "calculate.sum",
                             lambda _: {"total": 5})
    runtime.grant("org.example.calc", frozenset({"engineering.calculate"}))
    result = runtime.invoke(request())
    assert result.status == "ERROR"
    assert result.error_code == "module.output_validation_failed"


from threading import Event, Thread


def test_revoke_denies_new_invocations_and_waits_for_inflight_handler():
    _, runtime = setup_runtime()
    entered = Event()
    release = Event()
    invocation_done = Event()
    revoke_done = Event()
    responses = []
    revoke_results = []

    def handler(_):
        entered.set()
        assert release.wait(3)
        return {"total": 7}

    runtime.register_handler("org.example.calc", "calculate.sum", handler)
    runtime.grant("org.example.calc", frozenset({"engineering.calculate"}))
    invocation = Thread(target=lambda: (responses.append(runtime.invoke(request())), invocation_done.set()))
    invocation.start()
    assert entered.wait(3)

    revoker = Thread(target=lambda: (revoke_results.append(runtime.revoke("org.example.calc")), revoke_done.set()))
    revoker.start()
    with runtime._condition:
        assert runtime._condition.wait_for(lambda: "org.example.calc" in runtime._revoking, timeout=3)

    rejected = runtime.invoke(request())
    assert rejected.status == "REJECTED"
    assert rejected.error_code == "module.permission_denied"
    assert not revoke_done.is_set()
    assert not invocation_done.is_set()

    release.set()
    invocation.join(3)
    revoker.join(3)
    assert not invocation.is_alive()
    assert not revoker.is_alive()
    assert invocation_done.is_set()
    assert revoke_done.is_set()
    assert responses[0].status == "COMPLETED"
    assert revoke_results == [True]
    assert runtime.invoke(request()).error_code == "module.permission_denied"


def test_revoke_drains_resource_lease_before_returning():
    registry, _ = setup_runtime()
    allocator = ResourceAllocator((ResourceMetric("cpu.cores", 1, "cores"),))
    entered = Event()
    release = Event()
    runtime = ModuleRuntime(registry, resource_allocator=allocator)

    def handler(_):
        entered.set()
        assert release.wait(3)
        return {"total": 9}

    runtime.register_handler("org.example.calc", "calculate.sum", handler)
    runtime.grant("org.example.calc", frozenset({"engineering.calculate"}))
    invocation = Thread(target=lambda: runtime.invoke(request(resource_limits={"cpu.cores": 1})))
    invocation.start()
    assert entered.wait(3)

    result = []
    revoker = Thread(target=lambda: result.append(runtime.revoke("org.example.calc")))
    revoker.start()
    with runtime._condition:
        assert runtime._condition.wait_for(lambda: "org.example.calc" in runtime._revoking, timeout=3)
    assert len(allocator.active_leases()) == 1
    assert revoker.is_alive()

    release.set()
    invocation.join(3)
    revoker.join(3)
    assert not invocation.is_alive()
    assert not revoker.is_alive()
    assert result == [True]
    assert allocator.active_leases() == ()
    assert allocator.available()[0].value == 1


def test_revoke_is_idempotent_and_grant_cannot_race_with_drain():
    _, runtime = setup_runtime()
    entered = Event()
    release = Event()

    def handler(_):
        entered.set()
        assert release.wait(3)
        return {"total": 3}

    runtime.register_handler("org.example.calc", "calculate.sum", handler)
    runtime.grant("org.example.calc", frozenset({"engineering.calculate"}))
    invocation = Thread(target=lambda: runtime.invoke(request()))
    invocation.start()
    assert entered.wait(3)

    first_result = []
    first = Thread(target=lambda: first_result.append(runtime.revoke("org.example.calc")))
    first.start()
    with runtime._condition:
        assert runtime._condition.wait_for(lambda: "org.example.calc" in runtime._revoking, timeout=3)
    with pytest.raises(InvalidModelError, match="being revoked"):
        runtime.grant("org.example.calc", frozenset({"engineering.calculate"}))

    release.set()
    invocation.join(3)
    first.join(3)
    assert not invocation.is_alive()
    assert not first.is_alive()
    assert first_result == [True]
    assert runtime.revoke("org.example.calc") is False
    runtime.grant("org.example.calc", frozenset({"engineering.calculate"}))
    assert runtime.invoke(request()).status == "COMPLETED"


def test_failed_invocation_still_unblocks_revoke():
    _, runtime = setup_runtime()
    entered = Event()
    release = Event()

    def failing_handler(_):
        entered.set()
        assert release.wait(3)
        raise RuntimeError("private handler detail")

    runtime.register_handler("org.example.calc", "calculate.sum", failing_handler)
    runtime.grant("org.example.calc", frozenset({"engineering.calculate"}))
    responses = []
    invocation = Thread(target=lambda: responses.append(runtime.invoke(request())))
    invocation.start()
    assert entered.wait(3)

    revoke_results = []
    revoker = Thread(target=lambda: revoke_results.append(runtime.revoke("org.example.calc")))
    revoker.start()
    with runtime._condition:
        assert runtime._condition.wait_for(lambda: "org.example.calc" in runtime._revoking, timeout=3)
    release.set()
    invocation.join(3)
    revoker.join(3)
    assert not invocation.is_alive()
    assert not revoker.is_alive()
    assert responses[0].error_code == "module.handler_failed"
    assert revoke_results == [True]


_INPUT_SCHEMA = {
    "type": "object",
    "x-schema-version": "1.0",
    "required": ["value"],
    "properties": {"value": {"type": "integer", "minimum": 0}},
    "additionalProperties": False,
}
_OUTPUT_SCHEMA = {
    "type": "object",
    "x-schema-version": "1.0",
    "required": ["result"],
    "properties": {"result": {"type": "integer", "minimum": 0}},
    "additionalProperties": False,
}


def setup_worker_runtime(tmp_path, worker_script, *, supervisor=None, input_schema=_INPUT_SCHEMA):
    registry = ModuleRegistry()
    registry.register(ModuleManifest(
        module_id="org.example.worker",
        version="1.0.0",
        domain="calculation",
        operations=(ModuleOperation(
            "calculate.double",
            input_schema_version="1.0",
            output_schema_version="1.0",
            required_permissions=("engineering.calculate",),
            input_schema=input_schema,
            output_schema=_OUTPUT_SCHEMA,
        ),),
        permissions=("engineering.calculate",),
        license_id="Apache-2.0",
    ))
    allocator = ResourceAllocator((ResourceMetric("cpu.cores", 2, "cores"),))
    if supervisor is None:
        supervisor = PythonProcessSupervisor(
            working_root=tmp_path,
            allowed_executables=(sys.executable,),
            max_output_bytes=4096,
        )
    client = WorkerIPCClient(
        supervisor,
        WorkerSpec(
            "worker-template",
            sys.executable,
            ("-c", worker_script),
            working_directory=".",
            timeout_seconds=3,
        ),
    )
    runtime = ModuleRuntime(registry, resource_allocator=allocator)
    runtime.register_worker_handler("org.example.worker", "calculate.double", client)
    return runtime, allocator, supervisor


def worker_request(**changes):
    values = {
        "module_id": "org.example.worker",
        "operation": "calculate.double",
        "inputs": {"value": 3},
        "permissions": ("engineering.calculate",),
        "resource_limits": {"cpu.cores": 1},
        "request_id": "worker-request-1",
    }
    values.update(changes)
    return ModuleRequest(**values)


def test_worker_handler_uses_host_grant_schema_and_supervised_process(tmp_path):
    script = (
        "import sys; "
        "from universal_platform.runtime.worker_protocol import read_frame, write_frame, WorkerFrame; "
        "request = read_frame(sys.stdin.buffer); "
        "assert 'permissions' not in request.payload; "
        "value = request.payload['inputs']['value']; "
        "write_frame(sys.stdout.buffer, WorkerFrame('RESPONSE', request.request_id, "
        "{'outputs': {'result': value * 2}}))"
    )
    runtime, allocator, supervisor = setup_worker_runtime(tmp_path, script)
    runtime.grant("org.example.worker", frozenset({"engineering.calculate"}))
    result = runtime.invoke(worker_request())
    assert result.status == "COMPLETED"
    assert result.outputs["result"] == 6
    assert any("not an OS resource limit" in warning for warning in result.warnings)
    assert allocator.active_leases() == ()
    assert allocator.available()[0].value == 2
    assert supervisor.active_worker_ids == ()


def test_worker_handler_rejects_invalid_input_before_process_start(tmp_path):
    script = "raise SystemExit('must not execute')"
    runtime, allocator, supervisor = setup_worker_runtime(tmp_path, script)
    runtime.grant("org.example.worker", frozenset({"engineering.calculate"}))
    result = runtime.invoke(worker_request(inputs={"value": "3"}))
    assert result.status == "REJECTED"
    assert result.error_code == "module.input_validation_failed"
    assert supervisor.active_worker_ids == ()
    assert allocator.active_leases() == ()


def test_module_input_schema_version_must_match_operation_declaration():
    with pytest.raises(InvalidModelError, match="input_schema x-schema-version"):
        ModuleOperation(
            "calculate.double",
            input_schema_version="2.0",
            input_schema={
                "type": "object",
                "x-schema-version": "1.0",
                "properties": {},
                "additionalProperties": False,
            },
        )


def test_worker_handler_requires_input_schema_at_registration(tmp_path):
    script = "pass"
    registry = ModuleRegistry()
    registry.register(ModuleManifest(
        module_id="org.example.worker", version="1.0.0", domain="calculation",
        operations=(ModuleOperation("calculate.double", output_schema=_OUTPUT_SCHEMA),),
        permissions=("engineering.calculate",), license_id="Apache-2.0",
    ))
    supervisor = PythonProcessSupervisor(
        working_root=tmp_path, allowed_executables=(sys.executable,)
    )
    client = WorkerIPCClient(supervisor, WorkerSpec("template", sys.executable, ("-c", script)))
    runtime = ModuleRuntime(registry)
    with pytest.raises(InvalidModelError, match="input schema"):
        runtime.register_worker_handler("org.example.worker", "calculate.double", client)


def test_worker_handler_cannot_self_grant_from_request_permissions(tmp_path):
    script = "raise SystemExit('must not execute')"
    runtime, allocator, supervisor = setup_worker_runtime(tmp_path, script)
    result = runtime.invoke(worker_request())
    assert result.status == "REJECTED"
    assert result.error_code == "module.permission_denied"
    assert supervisor.active_worker_ids == ()
    assert allocator.active_leases() == ()


def test_worker_handler_output_is_validated_by_host_schema(tmp_path):
    script = (
        "import sys; "
        "from universal_platform.runtime.worker_protocol import read_frame, write_frame, WorkerFrame; "
        "request = read_frame(sys.stdin.buffer); "
        "write_frame(sys.stdout.buffer, WorkerFrame('RESPONSE', request.request_id, "
        "{'outputs': {'result': 'not-an-integer'}}))"
    )
    runtime, allocator, supervisor = setup_worker_runtime(tmp_path, script)
    runtime.grant("org.example.worker", frozenset({"engineering.calculate"}))
    result = runtime.invoke(worker_request())
    assert result.status == "ERROR"
    assert result.error_code == "module.output_validation_failed"
    assert allocator.active_leases() == ()
    assert supervisor.active_worker_ids == ()


def test_worker_timeout_releases_lease_after_supervisor_cleanup(tmp_path):
    script = "import time; time.sleep(30)"
    registry = ModuleRegistry()
    registry.register(ModuleManifest(
        module_id="org.example.worker", version="1.0.0", domain="calculation",
        operations=(ModuleOperation(
            "calculate.double", required_permissions=("engineering.calculate",),
            input_schema=_INPUT_SCHEMA, output_schema=_OUTPUT_SCHEMA,
        ),),
        permissions=("engineering.calculate",), license_id="Apache-2.0",
    ))
    allocator = ResourceAllocator((ResourceMetric("cpu.cores", 1, "cores"),))
    supervisor = PythonProcessSupervisor(
        working_root=tmp_path, allowed_executables=(sys.executable,), max_output_bytes=4096
    )
    client = WorkerIPCClient(
        supervisor,
        WorkerSpec("template", sys.executable, ("-c", script), timeout_seconds=0.1,
                   terminate_grace_seconds=0.1),
    )
    runtime = ModuleRuntime(registry, resource_allocator=allocator)
    runtime.register_worker_handler("org.example.worker", "calculate.double", client)
    runtime.grant("org.example.worker", frozenset({"engineering.calculate"}))
    result = runtime.invoke(worker_request())
    assert result.status == "ERROR"
    assert result.error_code == "module.worker_timeout"
    assert allocator.active_leases() == ()
    assert supervisor.active_worker_ids == ()


def test_worker_cancel_is_host_controlled_and_releases_confirmed_lease(tmp_path):
    script = "import time; time.sleep(30)"
    runtime, allocator, supervisor = setup_worker_runtime(tmp_path, script)
    runtime.grant("org.example.worker", frozenset({"engineering.calculate"}))
    results = []
    thread = threading.Thread(target=lambda: results.append(runtime.invoke(worker_request())))
    thread.start()
    deadline = time.monotonic() + 3
    while not supervisor.active_worker_ids and time.monotonic() < deadline:
        time.sleep(0.01)
    assert supervisor.active_worker_ids
    assert runtime.cancel("worker-request-1")
    thread.join(timeout=3)
    assert not thread.is_alive()
    assert results[0].status == "CANCELLED"
    assert allocator.active_leases() == ()
    assert supervisor.active_worker_ids == ()


def test_worker_termination_unconfirmed_quarantines_resource_lease(tmp_path):
    class UnconfirmedSupervisor:
        def run(self, spec):
            raise WorkerTerminationError(spec.worker_id)

        def cancel(self, request_id, *, grace_seconds=1.0):
            return False

    runtime, allocator, _ = setup_worker_runtime(
        tmp_path, "pass", supervisor=UnconfirmedSupervisor()
    )
    runtime.grant("org.example.worker", frozenset({"engineering.calculate"}))
    result = runtime.invoke(worker_request())
    assert result.status == "ERROR"
    assert result.error_code == "module.worker_termination_unconfirmed"
    quarantined = allocator.quarantined_leases()
    assert len(quarantined) == 1
    lease, reason = quarantined[0]
    assert "termination was not confirmed" in reason
    assert allocator.active_leases() == (lease,)
    assert allocator.available()[0].value == 1
    with pytest.raises(RuntimeError, match="force release"):
        allocator.release(lease.lease_id)
    assert allocator.release(lease.lease_id, force=True)


def test_worker_request_id_is_validated_for_ipc_contract(tmp_path):
    script = "raise SystemExit('must not execute')"
    runtime, allocator, supervisor = setup_worker_runtime(tmp_path, script)
    runtime.grant("org.example.worker", frozenset({"engineering.calculate"}))
    result = runtime.invoke(worker_request(request_id="x" * 129))
    assert result.status == "REJECTED"
    assert result.error_code == "module.worker_request_invalid"
    assert supervisor.active_worker_ids == ()
    assert allocator.active_leases() == ()


def test_worker_handler_requires_explicit_host_permission(tmp_path):
    registry = ModuleRegistry()
    registry.register(ModuleManifest(
        module_id="org.example.worker", version="1.0.0", domain="calculation",
        operations=(ModuleOperation(
            "calculate.double", input_schema=_INPUT_SCHEMA, output_schema=_OUTPUT_SCHEMA,
        ),),
        license_id="Apache-2.0",
    ))
    supervisor = PythonProcessSupervisor(
        working_root=tmp_path, allowed_executables=(sys.executable,)
    )
    client = WorkerIPCClient(supervisor, WorkerSpec("template", sys.executable, ("-c", "pass")))
    runtime = ModuleRuntime(registry)
    with pytest.raises(InvalidModelError, match="at least one host permission"):
        runtime.register_worker_handler("org.example.worker", "calculate.double", client)


def test_module_runtime_cancel_rejects_invalid_request_ids():
    registry = ModuleRegistry()
    registry.register(ModuleManifest(
        module_id="org.example.empty", version="1.0.0", domain="calculation",
        operations=(ModuleOperation("calculate.noop", output_schema=_OUTPUT_SCHEMA),),
        license_id="Apache-2.0",
    ))
    runtime = ModuleRuntime(registry)
    assert not runtime.cancel("")
    assert not runtime.cancel("bad\x00id")
    assert not runtime.cancel("x" * 129)


def test_worker_termination_quarantine_failure_still_retains_lease(tmp_path, monkeypatch):
    class UnconfirmedSupervisor:
        def run(self, spec):
            raise WorkerTerminationError(spec.worker_id)

        def cancel(self, worker_id, *, grace_seconds=1.0):
            return False

    runtime, allocator, _ = setup_worker_runtime(
        tmp_path, "pass", supervisor=UnconfirmedSupervisor()
    )
    runtime.grant("org.example.worker", frozenset({"engineering.calculate"}))

    def fail_quarantine(lease_id, reason):
        raise RuntimeError("quarantine store unavailable")

    monkeypatch.setattr(allocator, "quarantine", fail_quarantine)
    result = runtime.invoke(worker_request())
    assert result.status == "ERROR"
    assert result.error_code == "module.worker_termination_unconfirmed"
    assert any("quarantine metadata could not be recorded" in warning for warning in result.warnings)
    assert len(allocator.active_leases()) == 1
    assert allocator.available()[0].value == 1
    assert allocator.quarantined_leases() == ()


def _durable_worker_runtime(tmp_path, worker_script, *, extra_arguments=()):
    registry = ModuleRegistry()
    registry.register(ModuleManifest(
        module_id="org.example.worker",
        version="1.0.0",
        domain="calculation",
        operations=(ModuleOperation(
            "calculate.double",
            input_schema_version="1.0",
            output_schema_version="1.0",
            required_permissions=("engineering.calculate",),
            input_schema=_INPUT_SCHEMA,
            output_schema=_OUTPUT_SCHEMA,
        ),),
        permissions=("engineering.calculate",),
        license_id="Apache-2.0",
    ))
    journal_root = tmp_path / "durable-worker-leases"
    journal_root.mkdir(exist_ok=True)
    allocator = DurableResourceAllocator(
        journal_root,
        (ResourceMetric("cpu.cores", 2, "cores"),),
        pool_id="module-runtime-process-identity",
    )
    supervisor = PythonProcessSupervisor(
        working_root=tmp_path,
        allowed_executables=(sys.executable,),
        max_output_bytes=4096,
    )
    client = WorkerIPCClient(
        supervisor,
        WorkerSpec(
            "worker-template",
            sys.executable,
            ("-c", worker_script, str(journal_root), *extra_arguments),
            working_directory=".",
            timeout_seconds=3,
        ),
    )
    runtime = ModuleRuntime(registry, resource_allocator=allocator)
    runtime.register_worker_handler("org.example.worker", "calculate.double", client)
    runtime.grant("org.example.worker", frozenset({"engineering.calculate"}))
    return runtime, allocator, supervisor, journal_root


def test_durable_worker_identity_is_fsynced_before_payload_execution(tmp_path):
    script = (
        "import json,os,sys; from pathlib import Path; "
        "from universal_platform.runtime.worker_protocol import read_frame,write_frame,WorkerFrame; "
        "root=Path(sys.argv[1]); "
        "journal=next(root.glob('worker-leases-*.jsonl')); "
        "events=[json.loads(line) for line in journal.read_text(encoding='utf-8').splitlines()]; "
        "acquired=next(item for item in events if item.get('event_type')=='LEASE_ACQUIRED'); "
        "bound=next(item for item in events if item.get('event_type')=='LEASE_PROCESS_BOUND'); "
        "identity=bound['process_identity']; "
        "assert identity['pid']==os.getpid(); "
        "assert identity['worker_id']==acquired['worker_id']; "
        "assert identity['host_instance_id']==acquired['host_instance_id']; "
        "request=read_frame(sys.stdin.buffer); "
        "write_frame(sys.stdout.buffer,WorkerFrame('RESPONSE',request.request_id,"
        "{'outputs':{'result':request.payload['inputs']['value']*2}}))"
    )
    runtime, allocator, supervisor, _journal_root = _durable_worker_runtime(tmp_path, script)

    result = runtime.invoke(worker_request(resource_limits={}))

    assert result.status == "COMPLETED"
    assert result.outputs["result"] == 6
    assert any("not an OS resource limit" in warning for warning in result.warnings)
    assert allocator.active_leases() == ()
    assert allocator.available()[0].value == 2
    assert supervisor.active_worker_ids == ()

    events = allocator._journal.read_all()
    event_types = [event["event_type"] for event in events]
    assert event_types.index("LEASE_ACQUIRED") < event_types.index("LEASE_PROCESS_BOUND")
    assert event_types.index("LEASE_PROCESS_BOUND") < event_types.index("LEASE_RELEASED")
    binding = next(event for event in events if event["event_type"] == "LEASE_PROCESS_BOUND")
    assert binding["process_identity"]["pid"] > 0


def test_durable_identity_persistence_failure_never_executes_worker_payload(tmp_path, monkeypatch):
    marker = tmp_path / "worker-payload-must-not-run.txt"
    script = (
        "from pathlib import Path; import sys; "
        "Path(sys.argv[2]).write_text('ran', encoding='utf-8')"
    )
    runtime, allocator, supervisor, _journal_root = _durable_worker_runtime(
        tmp_path,
        script,
        extra_arguments=(str(marker),),
    )

    def fail_binding(_lease_id, _identity):
        raise OSError("injected durable identity persistence failure")

    monkeypatch.setattr(allocator, "bind_process_identity", fail_binding)
    result = runtime.invoke(worker_request(resource_limits={}))

    assert result.status == "ERROR"
    assert result.error_code == "module.worker_identity_handoff_failed"
    assert not marker.exists()
    assert allocator.active_leases() == ()
    assert supervisor.active_worker_ids == ()


def test_unconfirmed_identity_handoff_quarantines_durable_worker_lease(tmp_path):
    class UnconfirmedIdentitySupervisor:
        def run(self, _spec):
            raise AssertionError("identity-gated execution must use run_with_identity")

        def run_with_identity(self, spec, *, host_instance_id, on_process_started):
            raise WorkerTerminationError(spec.worker_id)

        def cancel(self, _worker_id, *, grace_seconds=1.0):
            return False

    registry = ModuleRegistry()
    registry.register(ModuleManifest(
        module_id="org.example.worker",
        version="1.0.0",
        domain="calculation",
        operations=(ModuleOperation(
            "calculate.double",
            input_schema_version="1.0",
            output_schema_version="1.0",
            required_permissions=("engineering.calculate",),
            input_schema=_INPUT_SCHEMA,
            output_schema=_OUTPUT_SCHEMA,
        ),),
        permissions=("engineering.calculate",),
        license_id="Apache-2.0",
    ))
    journal_root = tmp_path / "unconfirmed-worker-leases"
    journal_root.mkdir()
    allocator = DurableResourceAllocator(
        journal_root,
        (ResourceMetric("cpu.cores", 1, "cores"),),
        pool_id="unconfirmed-worker",
    )
    client = WorkerIPCClient(
        UnconfirmedIdentitySupervisor(),
        WorkerSpec("worker-template", sys.executable, ("-c", "pass")),
    )
    runtime = ModuleRuntime(registry, resource_allocator=allocator)
    runtime.register_worker_handler("org.example.worker", "calculate.double", client)
    runtime.grant("org.example.worker", frozenset({"engineering.calculate"}))

    result = runtime.invoke(worker_request(resource_limits={}))

    assert result.status == "ERROR"
    assert result.error_code == "module.worker_termination_unconfirmed"
    active = allocator.active_leases()
    assert len(active) == 1
    assert active[0].process_identity is None
    quarantined = allocator.quarantined_leases()
    assert len(quarantined) == 1
    assert quarantined[0][0].lease_id == active[0].lease_id


def test_module_runtime_reconciles_existing_worker_leases_before_startup(tmp_path):
    allocator = DurableResourceAllocator(
        tmp_path,
        (ResourceMetric("cpu.cores", 2, "cores"),),
        pool_id="module-runtime-startup-reconciliation",
    )
    lease = allocator.allocate_worker(
        "previous-runtime",
        (ResourceMetric("cpu.cores", 1, "cores"),),
        host_instance_id="host-before-restart",
        worker_id="worker-before-restart",
    )
    identity = ProcessIdentity(
        platform="linux",
        pid=43210,
        creation_token="12345",
        host_boot_id="previous-boot",
        worker_id="worker-before-restart",
        host_instance_id="host-before-restart",
        process_group_id=43210,
        session_id=43210,
    )
    allocator.bind_process_identity(lease.lease_id, identity)

    restarted_allocator = DurableResourceAllocator(
        tmp_path,
        (ResourceMetric("cpu.cores", 2, "cores"),),
        pool_id="module-runtime-startup-reconciliation",
    )
    assert restarted_allocator.startup_reconciliation_required

    class AbsentInspector:
        def inspect(self, observed_identity):
            return ProcessLivenessEvidence(
                identity=observed_identity,
                status=ProcessLiveness.ABSENT,
                method="test.startup-inspector",
                observed_at=datetime.now(timezone.utc),
                reason="test proves previous worker process tree is absent",
            )

    runtime = ModuleRuntime(
        ModuleRegistry(),
        resource_allocator=restarted_allocator,
        host_instance_id="host-after-restart",
        process_identity_inspector=AbsentInspector(),
    )

    assert runtime._host_instance_id == "host-after-restart"
    assert not restarted_allocator.startup_reconciliation_required
    assert restarted_allocator.active_leases() == ()
    assert restarted_allocator.available()[0].value == 2
    assert any(
        event["event_type"] == "LEASE_RECOVERED_RELEASED"
        for event in restarted_allocator._journal.read_all()
    )


def test_module_runtime_instances_share_process_scoped_host_identity():
    first = ModuleRuntime(ModuleRegistry())
    second = ModuleRuntime(ModuleRegistry())
    explicit = ModuleRuntime(ModuleRegistry(), host_instance_id="explicit-host-instance")
    assert first._host_instance_id == second._host_instance_id
    assert explicit._host_instance_id == "explicit-host-instance"
