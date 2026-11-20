import json

import pytest

from universal_platform.engineering.errors import InvalidModelError
from universal_platform.engineering.module_registry import (
    ModuleManifest,
    ModuleOperation,
    ModuleRegistry,
)


def manifest(module_id="org.physics.mechanics", **overrides):
    values = {
        "module_id": module_id,
        "version": "1.2.3",
        "domain": "mechanics",
        "operations": (
            ModuleOperation(
                "calculate.stress",
                required_permissions=("engineering.calculate",),
            ),
        ),
        "permissions": ("engineering.calculate",),
        "license_id": "Apache-2.0",
        "maturity": "EXPERIMENTAL",
    }
    values.update(overrides)
    return ModuleManifest(**values)


def test_manifest_accepts_explicit_version_license_and_operation_contract():
    item = manifest()
    assert item.module_id == "org.physics.mechanics"
    assert item.operations[0].input_schema_version == "1.0"
    assert item.operations[0].execution_kind == "CALCULATION"


@pytest.mark.parametrize(
    "changes",
    [
        {"module_id": ""},
        {"module_id": "Org.Physics"},
        {"version": "1.2"},
        {"domain": " "},
        {"operations": ()},
        {"license_id": ""},
        {"maturity": "SELF_CERTIFIED"},
        {"dependencies": ("bad id",)},
        {"dependencies": ("org.physics.mechanics",)},
        {"permissions": ()},
        {"operations": [ModuleOperation("calculate")]},
        {"dependencies": ["org.domain.base"]},
        {"permissions": ["engineering.calculate"]},
    ],
)
def test_manifest_rejects_invalid_metadata(changes):
    with pytest.raises(InvalidModelError):
        manifest(**changes)


def test_operation_rejects_unsupported_execution_kind_and_bad_schema_version():
    with pytest.raises(InvalidModelError):
        ModuleOperation("run", execution_kind="PHYSICAL_CONTROL")
    with pytest.raises(InvalidModelError):
        ModuleOperation("run", input_schema_version="v1")
    with pytest.raises(InvalidModelError):
        ModuleOperation("run", input_schema_version=None)
    with pytest.raises(InvalidModelError):
        ModuleOperation("run", execution_kind=[])
    with pytest.raises(InvalidModelError):
        ModuleOperation("run", required_permissions=["engineering.calculate"])


def test_manifest_rejects_duplicate_operations_and_undeclared_permissions():
    operation = ModuleOperation("calculate")
    with pytest.raises(InvalidModelError, match="duplicates"):
        manifest(operations=(operation, operation))
    with pytest.raises(InvalidModelError, match="undeclared"):
        manifest(operations=(ModuleOperation(
            "calculate", required_permissions=("hardware.write",)
        ),))


def test_registry_rejects_duplicate_ids_and_unknown_lookups():
    registry = ModuleRegistry()
    item = manifest()
    registry.register(item)
    with pytest.raises(InvalidModelError, match="duplicate"):
        registry.register(item)
    with pytest.raises(InvalidModelError, match="unknown module"):
        registry.get("org.missing.module")
    with pytest.raises(InvalidModelError, match="stable lowercase identifier"):
        registry.get([])
    with pytest.raises(InvalidModelError, match="unknown operation"):
        registry.resolve_operation(item.module_id, "missing")


def test_registry_resolves_declared_operation_without_invoking_code():
    registry = ModuleRegistry()
    item = manifest()
    registry.register(item)
    assert registry.resolve_operation(
        item.module_id, "calculate.stress"
    ) == item.operations[0]


def test_dependency_order_is_deterministic_and_dependencies_come_first():
    registry = ModuleRegistry()
    registry.register(manifest("org.domain.z", dependencies=("org.domain.a",)))
    registry.register(manifest("org.domain.b"))
    registry.register(manifest("org.domain.a"))
    assert registry.dependency_order() == (
        "org.domain.a", "org.domain.b", "org.domain.z"
    )


def test_dependency_order_fails_closed_for_missing_dependency():
    registry = ModuleRegistry()
    registry.register(manifest("org.domain.a", dependencies=("org.domain.missing",)))
    with pytest.raises(InvalidModelError, match="missing module dependencies"):
        registry.dependency_order()


def test_dependency_order_fails_closed_for_cycles():
    registry = ModuleRegistry()
    registry.register(manifest("org.domain.a", dependencies=("org.domain.b",)))
    registry.register(manifest("org.domain.b", dependencies=("org.domain.a",)))
    with pytest.raises(InvalidModelError, match="cycle"):
        registry.dependency_order()


def test_snapshot_is_json_compatible_and_insertion_order_independent():
    first = ModuleRegistry()
    second = ModuleRegistry()
    a, b = manifest("org.domain.a"), manifest("org.domain.b")
    first.register(a)
    first.register(b)
    second.register(b)
    second.register(a)
    assert first.snapshot() == second.snapshot()
    assert json.loads(json.dumps(first.snapshot())) == first.snapshot()
    assert [item["module_id"] for item in first.snapshot()["modules"]] == [
        "org.domain.a", "org.domain.b"
    ]


def test_manifest_rejects_mutable_operation_permission_and_dependency_collections():
    with pytest.raises(InvalidModelError, match="immutable tuple"):
        manifest(operations=[ModuleOperation("calculate")])
    with pytest.raises(InvalidModelError, match="immutable tuple"):
        manifest(permissions=["engineering.calculate"])
    with pytest.raises(InvalidModelError, match="immutable tuple"):
        manifest(dependencies=["org.domain.base"])
