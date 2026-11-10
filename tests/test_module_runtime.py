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
