import json
import math

import pytest

from universal_platform.engineering.contracts import ModuleRequest, ModuleResponse
from universal_platform.engineering.errors import InvalidModelError


def test_request_defaults_and_json_round_trip_are_deterministic():
    request = ModuleRequest(
        module_id="org.physics.mechanics",
        operation="calculate.stress",
        inputs={"force": {"value": 1000, "unit": "N"}, "dimensions": [1, 2, 3]},
        assumptions=("linear elastic",),
        source_refs=("datasheet:rev-1",),
        resource_limits={"memory_bytes": 1024, "time_seconds": 2},
        permissions=("engineering.calculate",),
    )
    snapshot = request.to_dict()
    assert snapshot["schema_version"] == "1.0"
    assert snapshot["request_id"] == request.request_id
    assert json.loads(json.dumps(snapshot)) == snapshot
    assert snapshot["inputs"]["dimensions"] == [1, 2, 3]


@pytest.mark.parametrize(
    "changes",
    [
        {"module_id": "Bad.Module"},
        {"operation": ""},
        {"schema_version": "v1"},
        {"schema_version": None},
        {"request_id": ""},
        {"assumptions": ["mutable"]},
        {"source_refs": ("same", "same")},
        {"permissions": ("Bad.Permission",)},
        {"permissions": ["engineering.calculate"]},
        {"resource_limits": {"memory_bytes": -1}},
        {"resource_limits": {"memory_bytes": math.inf}},
        {"resource_limits": {"memory_bytes": True}},
        {"resource_limits": {"Bad Key": 1}},
        {"inputs": []},
        {"inputs": {"bad": object()}},
        {"inputs": {"bad": math.nan}},
        {"inputs": {1: "non-string key"}},
    ],
)
def test_request_rejects_invalid_contract_values(changes):
    values = {
        "module_id": "org.physics.mechanics",
        "operation": "calculate.stress",
        "inputs": {},
    }
    values.update(changes)
    with pytest.raises(InvalidModelError):
        ModuleRequest(**values)


def test_request_detaches_and_freezes_nested_payload_and_limits():
    source = {"nested": {"values": [1, 2]}}
    limits = {"memory_bytes": 128}
    request = ModuleRequest("org.example.module", "inspect", source, resource_limits=limits)
    source["nested"]["values"].append(3)
    limits["memory_bytes"] = 999
    assert request.to_dict()["inputs"]["nested"]["values"] == [1, 2]
    assert request.resource_limits["memory_bytes"] == 128.0
    with pytest.raises(TypeError):
        request.inputs["new"] = "value"
    with pytest.raises(TypeError):
        request.inputs["nested"]["new"] = "value"


def test_response_accepts_operational_status_and_keeps_completion_distinct():
    response = ModuleResponse(
        request_id="request-1",
        status="COMPLETED",
        outputs={"result": 42},
        warnings=("illustrative input",),
        limitations=("not physical validation",),
        evidence_refs=("evidence:case-1",),
    )
    assert response.to_dict()["status"] == "COMPLETED"
    assert "PASS" not in response.to_dict()["status"]
    assert json.loads(json.dumps(response.to_dict()))["outputs"]["result"] == 42


@pytest.mark.parametrize(
    "values",
    [
        {"request_id": "", "status": "COMPLETED"},
        {"request_id": "r1", "status": "PASS"},
        {"request_id": "r1", "status": "ERROR"},
        {"request_id": "r1", "status": "COMPLETED", "error_code": "unexpected"},
        {"request_id": "r1", "status": "REJECTED", "error_code": "Bad.Code"},
        {"request_id": "r1", "status": "COMPLETED", "warnings": ["mutable"]},
        {"request_id": "r1", "status": "COMPLETED", "evidence_refs": ("e1", "e1")},
        {"request_id": "r1", "status": "COMPLETED", "outputs": {"bad": math.inf}},
        {"request_id": "r1", "status": "COMPLETED", "outputs": {"bad": object()}},
    ],
)
def test_response_rejects_invalid_contract_values(values):
    with pytest.raises(InvalidModelError):
        ModuleResponse(**values)


def test_response_error_requires_machine_readable_error_code():
    response = ModuleResponse("request-1", "ERROR", error_code="solver.non_converged")
    assert response.to_dict()["error_code"] == "solver.non_converged"
