import json

import pytest

from universal_platform.engineering.errors import InvalidModelError
from universal_platform.hardware.erc import ERCSeverity, ERCStatus, check_electrical_rules
from universal_platform.hardware.schematic import (
    Component, Net, Pin, PinElectricalType, PinRef, SchematicModel,
)


def pin(component, pin_id, number, kind=PinElectricalType.PASSIVE, name=None):
    return Pin(pin_id, number, name or pin_id, kind)


def component(component_id, ref, *pins):
    return Component(component_id, ref, "symbol.generic", tuple(pins))


def ref(component_id, pin_id):
    return PinRef(component_id, pin_id)


def test_clean_two_pin_signal_net_passes_and_result_is_deterministic():
    left = component("component.u1", "U1", pin("u1", "u1.out", "1", PinElectricalType.OUTPUT))
    right = component("component.u2", "U2", pin("u2", "u2.in", "1", PinElectricalType.INPUT))
    model = SchematicModel((left, right), (Net("net.signal", (ref("component.u1", "u1.out"),
                                                                  ref("component.u2", "u2.in")), "SIGNAL"),))
    result = check_electrical_rules(model)
    assert result.status is ERCStatus.PASS
    assert result.findings == ()
    assert result.summary["finding_count"] == 0
    assert check_electrical_rules(model).to_dict() == result.to_dict()
    assert len(result.input_sha256) == 64


def test_unconnected_pins_are_warnings_but_explicit_no_connect_is_exempt():
    u1 = component("component.u1", "U1",
        pin("u1", "u1.1", "1", PinElectricalType.INPUT),
        pin("u1", "u1.2", "2", PinElectricalType.NO_CONNECT))
    result = check_electrical_rules(SchematicModel((u1,), ()))
    assert result.status is ERCStatus.FAIL
    assert len(result.findings) == 1
    finding = result.findings[0]
    assert finding.rule_id == "ERC-PIN-001"
    assert finding.severity is ERCSeverity.WARNING
    assert finding.object_refs == ("component:component.u1/pin:u1.1",)


def test_multiple_push_pull_outputs_on_one_net_are_an_error():
    a = component("component.u1", "U1", pin("u1", "u1.out", "1", PinElectricalType.OUTPUT))
    b = component("component.u2", "U2", pin("u2", "u2.out", "1", PinElectricalType.OUTPUT))
    net = Net("net.bus", (ref("component.u1", "u1.out"), ref("component.u2", "u2.out")))
    result = check_electrical_rules(SchematicModel((a, b), (net,)))
    finding = next(item for item in result.findings if item.rule_id == "ERC-NET-001")
    assert finding.severity is ERCSeverity.ERROR
    assert result.status is ERCStatus.FAIL


def test_multiple_power_sources_and_power_input_without_source_are_reported():
    source_a = component("component.reg1", "U1", pin("reg1", "reg1.out", "1", PinElectricalType.POWER_OUT))
    source_b = component("component.reg2", "U2", pin("reg2", "reg2.out", "1", PinElectricalType.POWER_OUT))
    load = component("component.load", "J1", pin("load", "load.vcc", "1", PinElectricalType.POWER_IN))
    parallel = Net("net.rail", (ref("component.reg1", "reg1.out"), ref("component.reg2", "reg2.out"),
                                ref("component.load", "load.vcc")), "VCC")
    result = check_electrical_rules(SchematicModel((source_a, source_b, load), (parallel,)))
    assert "ERC-NET-002" in {item.rule_id for item in result.findings}
    assert "ERC-NET-003" not in {item.rule_id for item in result.findings}

    no_source = check_electrical_rules(SchematicModel((load,), ()))
    # The isolated pin is reported as unconnected; no power-source rule can be
    # evaluated until a net exists, so missing connectivity is not a false PASS.
    assert "ERC-PIN-001" in {item.rule_id for item in no_source.findings}


def test_power_input_mixed_with_signal_driver_is_an_error():
    supply_pin = component("component.j1", "J1", pin("j1", "j1.vcc", "1", PinElectricalType.POWER_IN))
    gpio = component("component.u1", "U1", pin("u1", "u1.out", "2", PinElectricalType.OUTPUT))
    net = Net("net.bad", (ref("component.j1", "j1.vcc"), ref("component.u1", "u1.out")))
    result = check_electrical_rules(SchematicModel((supply_pin, gpio), (net,)))
    assert "ERC-NET-004" in {item.rule_id for item in result.findings}


def test_open_drain_without_declared_power_source_is_warning():
    device = component("component.u1", "U1", pin("u1", "u1.sda", "1", PinElectricalType.OPEN_DRAIN))
    connector = component("component.j1", "J1", pin("j1", "j1.sda", "1", PinElectricalType.PASSIVE))
    net = Net("net.sda", (ref("component.u1", "u1.sda"), ref("component.j1", "j1.sda")), "SDA")
    result = check_electrical_rules(SchematicModel((device, connector), (net,)))
    finding = next(item for item in result.findings if item.rule_id == "ERC-NET-005")
    assert finding.severity is ERCSeverity.WARNING
    assert "passive pull-up is not inferred" in finding.recommendation


def test_non_schematic_input_fails_closed():
    with pytest.raises(InvalidModelError, match="SchematicModel"):
        check_electrical_rules({"components": [], "nets": []})


def test_finding_ids_and_order_are_stable_for_equivalent_input_order():
    a = component("component.u1", "U1",
        pin("u1", "u1.a", "1", PinElectricalType.OUTPUT),
        pin("u1", "u1.b", "2", PinElectricalType.OUTPUT))
    b = component("component.u2", "U2", pin("u2", "u2.a", "1", PinElectricalType.OUTPUT))
    nets = (Net("net.a", (ref("component.u1", "u1.a"), ref("component.u2", "u2.a"))),
            Net("net.b", (ref("component.u1", "u1.b"), ref("component.u2", "u2.a"))))
    # The source model correctly rejects a pin assigned to two nets. Use separate pins.
    b = component("component.u2", "U2",
        pin("u2", "u2.a", "1", PinElectricalType.OUTPUT),
        pin("u2", "u2.b", "2", PinElectricalType.OUTPUT))
    nets = (Net("net.a", (ref("component.u1", "u1.a"), ref("component.u2", "u2.a"))),
            Net("net.b", (ref("component.u1", "u1.b"), ref("component.u2", "u2.b"))))
    first = check_electrical_rules(SchematicModel((a, b), nets))
    second = check_electrical_rules(SchematicModel((b, a), tuple(reversed(nets))))
    assert json.dumps(first.to_dict(), sort_keys=True) == json.dumps(second.to_dict(), sort_keys=True)
