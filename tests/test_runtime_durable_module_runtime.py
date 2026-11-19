import sys

import pytest

from universal_platform.engineering.contracts import ModuleRequest
from universal_platform.engineering.errors import InvalidModelError
from universal_platform.engineering.module_registry import ModuleManifest, ModuleOperation, ModuleRegistry
from universal_platform.engineering.module_runtime import ModuleRuntime
from universal_platform.runtime.resources.durable_allocator import DurableResourceAllocator
from universal_platform.runtime.resources.models import ResourceMetric
from universal_platform.runtime.supervisor import WorkerSpec, WorkerTerminationError
from universal_platform.runtime.worker_ipc import WorkerIPCClient


def build_runtime(root, *, capacity=2):
    registry = ModuleRegistry()
    registry.register(ModuleManifest(
        module_id="org.example.durable",
        version="1.0.0",
        domain="runtime",
        operations=(ModuleOperation(
            "resource.reserve",
            input_schema_version="1.0",
            required_permissions=("resource.reserve",),
            output_schema={
                "type": "object",
                "x-schema-version": "1.0",
                "required": ["total"],
                "properties": {"total": {"type": "number"}},
                "additionalProperties": False,
            },
        ),),
        permissions=("resource.reserve",),
        license_id="Apache-2.0",
    ))
    allocator = DurableResourceAllocator(
        root,
        (ResourceMetric("cpu.cores", capacity, "cores"),),
        pool_id="module-runtime",
    )
    runtime = ModuleRuntime(registry, resource_allocator=allocator)
    runtime.grant("org.example.durable", frozenset({"resource.reserve"}))
    return runtime, allocator


def make_request(*, cpu_cores=1):
    return ModuleRequest(
        module_id="org.example.durable",
        operation="resource.reserve",
        inputs={"value": 7},
        permissions=(),
        resource_limits={"cpu.cores": cpu_cores},
    )


def test_module_runtime_uses_durable_allocator_and_releases_after_success(tmp_path):
    runtime, allocator = build_runtime(tmp_path)
    observed = []

    def handler(inputs):
        observed.extend(allocator.active_leases())
        return {"total": inputs["value"]}

    runtime.register_handler("org.example.durable", "resource.reserve", handler)
    result = runtime.invoke(make_request())

    assert result.status == "COMPLETED"
    assert result.outputs["total"] == 7
    assert len(observed) == 1
    assert observed[0].owner_id == result.request_id
    assert allocator.active_leases() == ()
    assert allocator.available()[0].value == 2

    restarted = DurableResourceAllocator(
        tmp_path,
        (ResourceMetric("cpu.cores", 2, "cores"),),
        pool_id="module-runtime",
    )
    assert restarted.active_leases() == ()
    assert restarted.available()[0].value == 2


def test_module_runtime_rejects_durable_allocator_overcommit_before_handler(tmp_path):
    runtime, allocator = build_runtime(tmp_path, capacity=0.5)
    called = []
    runtime.register_handler(
        "org.example.durable",
        "resource.reserve",
        lambda inputs: called.append(True) or {"total": inputs["value"]},
    )

    result = runtime.invoke(make_request(cpu_cores=1))

    assert result.status == "REJECTED"
    assert result.error_code == "module.resource_reservation_failed"
    assert called == []
    assert allocator.active_leases() == ()
    assert allocator.available()[0].value == 0.5


def test_module_runtime_releases_durable_lease_when_handler_fails(tmp_path):
    runtime, allocator = build_runtime(tmp_path)

    def fail(_inputs):
        raise RuntimeError("private handler detail")

    runtime.register_handler("org.example.durable", "resource.reserve", fail)
    result = runtime.invoke(make_request())

    assert result.status == "ERROR"
    assert result.error_code == "module.handler_failed"
    assert allocator.active_leases() == ()
    assert allocator.available()[0].value == 2


def test_module_runtime_requires_allocator_contract():
    registry = ModuleRegistry()
    with pytest.raises(InvalidModelError, match="resource allocator contract"):
        ModuleRuntime(registry, resource_allocator=object())

def test_worker_runtime_persists_quarantine_in_durable_allocator(tmp_path):
    class UnconfirmedSupervisor:
        def run(self, spec):
            raise WorkerTerminationError(spec.worker_id)

        def cancel(self, request_id, *, grace_seconds=1.0):
            return False

    registry = ModuleRegistry()
    registry.register(ModuleManifest(
        module_id="org.example.worker",
        version="1.0.0",
        domain="runtime",
        operations=(ModuleOperation(
            "calculate.double",
            input_schema_version="1.0",
            required_permissions=("engineering.calculate",),
            input_schema={
                "type": "object",
                "x-schema-version": "1.0",
                "required": ["value"],
                "properties": {"value": {"type": "integer"}},
                "additionalProperties": False,
            },
            output_schema={
                "type": "object",
                "x-schema-version": "1.0",
                "required": ["result"],
                "properties": {"result": {"type": "integer"}},
                "additionalProperties": False,
            },
        ),),
        permissions=("engineering.calculate",),
        license_id="Apache-2.0",
    ))
    capacity = (ResourceMetric("cpu.cores", 2, "cores"),)
    allocator = DurableResourceAllocator(tmp_path, capacity, pool_id="worker-runtime")
    supervisor = UnconfirmedSupervisor()
    client = WorkerIPCClient(
        supervisor,
        WorkerSpec("worker-template", sys.executable, ("-c", "pass")),
    )
    runtime = ModuleRuntime(registry, resource_allocator=allocator)
    runtime.register_worker_handler("org.example.worker", "calculate.double", client)
    runtime.grant("org.example.worker", frozenset({"engineering.calculate"}))

    request = ModuleRequest(
        module_id="org.example.worker",
        operation="calculate.double",
        inputs={"value": 3},
        permissions=(),
        resource_limits={"cpu.cores": 1},
        request_id="durable-worker-request",
    )
    result = runtime.invoke(request)

    assert result.status == "ERROR"
    assert result.error_code == "module.worker_termination_unconfirmed"
    quarantined = allocator.quarantined_leases()
    assert len(quarantined) == 1
    lease, reason = quarantined[0]
    assert lease.owner_id == request.request_id
    assert "termination was not confirmed" in reason
    assert allocator.active_leases() == (lease,)
    assert allocator.available()[0].value == 1

    restarted = DurableResourceAllocator(tmp_path, capacity, pool_id="worker-runtime")
    restored = restarted.quarantined_leases()
    assert len(restored) == 1
    assert restored[0][0].lease_id == lease.lease_id
    assert restarted.active_leases() == (lease,)
    assert restarted.available()[0].value == 1
