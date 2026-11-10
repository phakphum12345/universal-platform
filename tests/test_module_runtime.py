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
    runtime.register_handler("org.example.calc", "calculate.sum", lambda _: {"ok": True})
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
        return {"ok": True}

    runtime = ModuleRuntime(registry, resource_allocator=allocator)
    runtime.register_handler("org.example.calc", "calculate.sum", long_running_handler)
    runtime.grant("org.example.calc", frozenset({"engineering.calculate"}))
    result = runtime.invoke(request(resource_limits={"cpu.cores": 1}))

    assert result.status == "COMPLETED"
    assert len(observed) == 1
    assert allocator.active_leases() == ()
    assert allocator.available()[0].value == 1
