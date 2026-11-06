import json
import pytest
from universal_platform.engineering.errors import InvalidModelError
from universal_platform.hardware.schematic import Component, Net, Pin, PinElectricalType, PinRef, SchematicModel

def sample():
    r=Component("component.r1","R1","resistor.through-hole",
        (Pin("r1.pin.1","1","A"),Pin("r1.pin.2","2","B")),"10k","RES-10K-TH")
    j=Component("component.j1","J1","connector.2pin",
        (Pin("j1.pin.1","1","GND"),Pin("j1.pin.2","2","VCC",PinElectricalType.POWER_IN)))
    nets=(Net("net.gnd",(PinRef("component.r1","r1.pin.1"),PinRef("component.j1","j1.pin.1")),"GND"),
          Net("net.vcc",(PinRef("component.r1","r1.pin.2"),PinRef("component.j1","j1.pin.2")),"VCC"))
    return SchematicModel((r,j),nets)

def test_round_trip_and_deterministic_serialization():
    model=sample(); data=json.loads(json.dumps(model.to_dict()))
    assert SchematicModel.from_dict(data)==model
    reordered=SchematicModel(tuple(reversed(model.components)),tuple(reversed(model.nets)))
    assert reordered.to_dict()==model.to_dict()
    assert reordered==model

def test_duplicate_component_ids_and_reference_designators_rejected():
    a=Component("component.a","R1","resistor",(Pin("a.1","1","A"),))
    with pytest.raises(InvalidModelError,match="component IDs"):
        SchematicModel((a,Component("component.a","R2","resistor",(Pin("b.1","1","A"),))),())
    with pytest.raises(InvalidModelError,match="reference designators"):
        SchematicModel((a,Component("component.b","R1","resistor",(Pin("c.1","1","A"),))),())

def test_duplicate_pin_ids_numbers_and_invalid_reference_rejected():
    with pytest.raises(InvalidModelError,match="pin IDs"):
        Component("component.r1","R1","resistor",(Pin("same","1","A"),Pin("same","2","B")))
    with pytest.raises(InvalidModelError,match="pin numbers"):
        Component("component.r1","R1","resistor",(Pin("p1","1","A"),Pin("p2","1","B")))
    with pytest.raises(InvalidModelError,match="reference_designator"):
        Component("component.r1","resistor-1","resistor",(Pin("p1","1","A"),))

def test_dangling_and_no_connect_terminals_rejected():
    c=Component("component.u1","U1","ic",(Pin("u1.pin.1","1","NC",PinElectricalType.NO_CONNECT),
        Pin("u1.pin.2","2","IO",PinElectricalType.BIDIRECTIONAL)))
    dangling=Net("net.a",(PinRef("component.u1","u1.pin.2"),PinRef("component.missing","missing.pin")))
    with pytest.raises(InvalidModelError,match="unknown component/pin"): SchematicModel((c,),(dangling,))
    nc=Net("net.b",(PinRef("component.u1","u1.pin.1"),PinRef("component.u1","u1.pin.2")))
    with pytest.raises(InvalidModelError,match="NO_CONNECT"): SchematicModel((c,),(nc,))

def test_pin_cannot_belong_to_multiple_nets_and_net_needs_two_terminals():
    c=Component("component.u1","U1","ic",(Pin("p1","1","A"),Pin("p2","2","B"),Pin("p3","3","C")))
    shared=PinRef("component.u1","p1")
    with pytest.raises(InvalidModelError,match="more than one net"):
        SchematicModel((c,),(Net("net.a",(shared,PinRef("component.u1","p2"))),
                              Net("net.b",(shared,PinRef("component.u1","p3")))))
    with pytest.raises(InvalidModelError,match="at least two"): Net("net.single",(shared,))

def test_duplicate_terminals_and_net_names_rejected():
    p=PinRef("component.a","pin.1")
    with pytest.raises(InvalidModelError,match="duplicate terminals"): Net("net.a",(p,p))
    model=sample()
    dup=Net("net.other",(PinRef("component.r1","r1.pin.1"),PinRef("component.j1","j1.pin.1")),"GND")
    with pytest.raises(InvalidModelError,match="unique names"): SchematicModel(model.components,model.nets+(dup,))

def test_snapshot_rejects_unknown_schema_and_fields():
    data=sample().to_dict()
    with pytest.raises(InvalidModelError,match="schema_version"): SchematicModel.from_dict(dict(data,schema_version="2.0"))
    with pytest.raises(InvalidModelError,match="missing or unknown"): SchematicModel.from_dict(dict(data,extra=True))
