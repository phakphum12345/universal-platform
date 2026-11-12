import pytest

from universal_platform.engineering.contracts import ModuleRequest
from universal_platform.engineering.errors import InvalidModelError
from universal_platform.engineering.module_registry import ModuleManifest, ModuleOperation, ModuleRegistry
from universal_platform.engineering.module_runtime import ModuleRuntime


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
    values = dict(
        module_id="org.example.calc", operation="calculate.sum",
        inputs={"values": [2, 3]}, permissions=(),
    )
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


from universal_platform.runtime.resources.allocator import ResourceAllocator
from universal_platform.runtime.resources.models import ResourceMetric


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


from datetime import datetime, timedelta, timezone


def test_runtime_lease_remains_reserved_until_long_handler_returns():
    registry, _ = setup_runtime()
    allocator = ResourceAllocator((ResourceMetric("cpu.cores", 1, "cores"),))
    observed = []

    def long_running_handler(_):
        future = datetime.now(timezone.utc) + timedelta(days=30)
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
