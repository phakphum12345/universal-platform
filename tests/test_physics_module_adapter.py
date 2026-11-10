import pytest

from universal_platform.engineering.contracts import ModuleRequest
from universal_platform.engineering.module_runtime import ModuleRuntime
from universal_platform.engineering.physics_module_adapter import (
    MODULE_ID,
    SOLVE_OPERATION,
    SOLVE_PERMISSION,
    create_builtin_physics_module_bridge,
)


def request(values, **extra):
    inputs = {
        "solver_id": "builtin.ohms-law",
        "problem_id": "test-ohms",
        "validity_range": "ideal lumped DC circuit",
        "values": values,
    }
    inputs.update(extra)
    return ModuleRequest(
        module_id=MODULE_ID,
        operation=SOLVE_OPERATION,
        inputs=inputs,
        permissions=(SOLVE_PERMISSION,),
    )


def test_physics_bridge_requires_host_grant_and_ignores_request_self_grant():
    bridge = create_builtin_physics_module_bridge()
    result = bridge.invoke(request({
        "voltage": {"value": 12, "unit": "V"},
        "resistance": {"value": 6, "unit": "ohm"},
    }))
    assert result.status == "REJECTED"
    assert result.error_code == "module.permission_denied"

    bridge.grant()
    result = bridge.invoke(request({
        "voltage": {"value": 12, "unit": "V"},
        "resistance": {"value": 6, "unit": "ohm"},
    }))
    assert result.status == "COMPLETED"
    assert result.outputs["outputs"]["current"]["si_value"] == pytest.approx(2)
    assert result.outputs["outputs"]["power"]["si_value"] == pytest.approx(24)
    assert result.outputs["evidence"]["status"] == "PASS"
    assert result.outputs["evidence"]["limitations"]


def test_physics_bridge_supports_axial_stress_and_preserves_evidence():
    bridge = create_builtin_physics_module_bridge()
    bridge.grant()
    result = bridge.invoke(ModuleRequest(
        module_id=MODULE_ID,
        operation=SOLVE_OPERATION,
        inputs={
            "solver_id": "builtin.axial-stress",
            "problem_id": "test-stress",
            "validity_range": "elementary axial loading",
            "values": {
                "force": {"value": 1000, "unit": "N"},
                "area": {"value": 0.01, "unit": "m2"},
            },
            "assumptions": ["uniform axial stress"],
            "boundary_conditions": ["uniaxial force"],
        },
    ))
    assert result.status == "COMPLETED"
    assert result.outputs["outputs"]["stress"]["si_value"] == pytest.approx(100000)
    metadata = result.outputs["evidence"]["metadata"]
    assert metadata["assumptions"] == ("uniform axial stress",)
    assert metadata["boundary_conditions"] == ("uniaxial force",)


def test_physics_bridge_supports_linear_thermal_expansion():
    bridge = create_builtin_physics_module_bridge()
    bridge.grant()
    result = bridge.invoke(ModuleRequest(
        module_id=MODULE_ID,
        operation=SOLVE_OPERATION,
        inputs={
            "solver_id": "builtin.linear-thermal-expansion",
            "problem_id": "test-expansion",
            "validity_range": "constant coefficient and uniform temperature",
            "values": {
                "length": {"value": 2, "unit": "m"},
                "coefficient_per_kelvin": 12e-6,
                "temperature_change_kelvin": 50,
            },
        },
    ))
    assert result.status == "COMPLETED"
    assert result.outputs["outputs"]["delta_length"]["si_value"] == pytest.approx(0.0012)


@pytest.mark.parametrize("values", [
    {"voltage": {"value": 12, "unit": "V"}, "resistance": {"value": 6, "unit": "kohm"}},
    {"voltage": {"value": 12, "unit": "V"}, "resistance": {"value": True, "unit": "ohm"}},
    {"voltage": {"value": 12, "unit": "V"}},
])
def test_physics_bridge_rejects_invalid_or_noncanonical_inputs(values):
    bridge = create_builtin_physics_module_bridge()
    bridge.grant()
    result = bridge.invoke(request(values))
    assert result.status == "ERROR"
    assert result.error_code == "module.handler_failed"


def test_physics_bridge_license_policy_fails_closed():
    bridge = create_builtin_physics_module_bridge(allowed_licenses=("MIT",))
    bridge.grant()
    result = bridge.invoke(request({
        "voltage": {"value": 12, "unit": "V"},
        "resistance": {"value": 6, "unit": "ohm"},
    }))
    assert result.status == "ERROR"
    assert result.error_code == "module.handler_failed"


def test_physics_bridge_revocation_blocks_later_invocations():
    bridge = create_builtin_physics_module_bridge()
    bridge.grant()
    assert bridge.revoke() is True
    result = bridge.invoke(request({
        "voltage": {"value": 12, "unit": "V"},
        "resistance": {"value": 6, "unit": "ohm"},
    }))
    assert result.error_code == "module.permission_denied"


def test_physics_bridge_is_a_real_module_runtime_integration():
    bridge = create_builtin_physics_module_bridge()
    assert isinstance(bridge.runtime, ModuleRuntime)
    manifest = bridge.runtime._registry.get(MODULE_ID)
    operation = manifest.operations[0]
    assert operation.required_permissions == (SOLVE_PERMISSION,)
    assert operation.output_schema_version == "1.0"


def test_physics_bridge_rejects_unknown_top_level_fields():
    bridge = create_builtin_physics_module_bridge()
    bridge.grant()
    result = bridge.invoke(request({
        "voltage": {"value": 12, "unit": "V"},
        "resistance": {"value": 6, "unit": "ohm"},
    }, unexpected_authority=True))
    assert result.status == "ERROR"
    assert result.error_code == "module.handler_failed"


def test_physics_bridge_rejects_numeric_overflow_without_leaking_exception():
    bridge = create_builtin_physics_module_bridge()
    bridge.grant()
    result = bridge.invoke(request({
        "voltage": {"value": 10 ** 10000, "unit": "V"},
        "resistance": {"value": 6, "unit": "ohm"},
    }))
    assert result.status == "ERROR"
    assert result.error_code == "module.handler_failed"
