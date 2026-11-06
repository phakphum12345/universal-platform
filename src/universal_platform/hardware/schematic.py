"""Offline normalized hardware schematic/netlist data model."""
from __future__ import annotations
from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum
import re
from typing import Any, ClassVar
from universal_platform.engineering.errors import InvalidModelError

_IDENTIFIER = re.compile(r"^[a-z0-9]+(?:[._/-][a-z0-9]+)*$")
_REFERENCE = re.compile(r"^[A-Z]{1,4}[0-9]+$")

def _identifier(value: str, label: str) -> None:
    if not isinstance(value, str) or not _IDENTIFIER.fullmatch(value):
        raise InvalidModelError(f"{label} must be a stable lowercase identifier")

def _optional_text(value: str | None, label: str) -> None:
    if value is not None and (not isinstance(value, str) or not value.strip()):
        raise InvalidModelError(f"{label} must be None or a non-empty string")

class PinElectricalType(str, Enum):
    PASSIVE="PASSIVE"
    INPUT="INPUT"
    OUTPUT="OUTPUT"
    BIDIRECTIONAL="BIDIRECTIONAL"
    POWER_IN="POWER_IN"
    POWER_OUT="POWER_OUT"
    OPEN_DRAIN="OPEN_DRAIN"
    OPEN_COLLECTOR="OPEN_COLLECTOR"
    NO_CONNECT="NO_CONNECT"

@dataclass(frozen=True, slots=True)
class Pin:
    pin_id: str
    number: str
    name: str
    electrical_type: PinElectricalType = PinElectricalType.PASSIVE
    def __post_init__(self):
        _identifier(self.pin_id, "pin_id")
        if not isinstance(self.number, str) or not self.number.strip():
            raise InvalidModelError("pin number must be a non-empty string")
        if not isinstance(self.name, str) or not self.name.strip():
            raise InvalidModelError("pin name must be a non-empty string")
        if not isinstance(self.electrical_type, PinElectricalType):
            raise InvalidModelError("electrical_type must be a PinElectricalType")
    def to_dict(self):
        return {"pin_id":self.pin_id,"number":self.number,"name":self.name,"electrical_type":self.electrical_type.value}

@dataclass(frozen=True, slots=True)
class Component:
    component_id: str
    reference_designator: str
    symbol_id: str
    pins: tuple[Pin,...]
    value: str|None = None
    manufacturer_part: str|None = None
    def __post_init__(self):
        _identifier(self.component_id,"component_id")
        _identifier(self.symbol_id,"symbol_id")
        if not isinstance(self.reference_designator,str) or not _REFERENCE.fullmatch(self.reference_designator):
            raise InvalidModelError("reference_designator must match a form such as R1, U2 or J10")
        if not isinstance(self.pins,tuple) or not self.pins:
            raise InvalidModelError("component pins must be a non-empty immutable tuple")
        if any(not isinstance(p,Pin) for p in self.pins):
            raise InvalidModelError("component pins must contain Pin records")
        ids=tuple(p.pin_id for p in self.pins); nums=tuple(p.number for p in self.pins)
        if len(ids)!=len(set(ids)): raise InvalidModelError("pin IDs must be unique within a component")
        if len(nums)!=len(set(nums)): raise InvalidModelError("pin numbers must be unique within a component")
        _optional_text(self.value,"component value"); _optional_text(self.manufacturer_part,"manufacturer_part")
    def to_dict(self):
        return {"component_id":self.component_id,"reference_designator":self.reference_designator,
                "symbol_id":self.symbol_id,"pins":[p.to_dict() for p in sorted(self.pins,key=lambda p:p.pin_id)],
                "value":self.value,"manufacturer_part":self.manufacturer_part}

@dataclass(frozen=True, slots=True)
class PinRef:
    component_id: str
    pin_id: str
    def __post_init__(self):
        _identifier(self.component_id,"component_id"); _identifier(self.pin_id,"pin_id")
    def to_dict(self): return {"component_id":self.component_id,"pin_id":self.pin_id}

@dataclass(frozen=True, slots=True)
class Net:
    net_id: str
    terminals: tuple[PinRef,...]
    name: str|None = None
    def __post_init__(self):
        _identifier(self.net_id,"net_id"); _optional_text(self.name,"net name")
        if not isinstance(self.terminals,tuple) or len(self.terminals)<2:
            raise InvalidModelError("a net requires at least two immutable PinRef terminals")
        if any(not isinstance(t,PinRef) for t in self.terminals):
            raise InvalidModelError("net terminals must contain PinRef records")
        keys=tuple((t.component_id,t.pin_id) for t in self.terminals)
        if len(keys)!=len(set(keys)): raise InvalidModelError("a net cannot contain duplicate terminals")
    def to_dict(self):
        return {"net_id":self.net_id,"name":self.name,
                "terminals":[t.to_dict() for t in sorted(self.terminals,key=lambda t:(t.component_id,t.pin_id))]}

@dataclass(frozen=True, slots=True)
class SchematicModel:
    components: tuple[Component,...]
    nets: tuple[Net,...]
    SCHEMA_VERSION: ClassVar[str]="1.0"
    def __post_init__(self):
        if not isinstance(self.components,tuple) or any(not isinstance(c,Component) for c in self.components):
            raise InvalidModelError("components must be an immutable tuple of Component records")
        if not isinstance(self.nets,tuple) or any(not isinstance(n,Net) for n in self.nets):
            raise InvalidModelError("nets must be an immutable tuple of Net records")
        cids=tuple(c.component_id for c in self.components); refs=tuple(c.reference_designator for c in self.components)
        nids=tuple(n.net_id for n in self.nets); names=tuple(n.name for n in self.nets if n.name is not None)
        if len(cids)!=len(set(cids)): raise InvalidModelError("component IDs must be unique")
        if len(refs)!=len(set(refs)): raise InvalidModelError("reference designators must be unique")
        if len(nids)!=len(set(nids)): raise InvalidModelError("net IDs must be unique")
        if len(names)!=len(set(names)): raise InvalidModelError("named nets must have unique names")
        pins={(c.component_id,p.pin_id):p for c in self.components for p in c.pins}
        connected=set()
        for net in self.nets:
            for terminal in net.terminals:
                key=(terminal.component_id,terminal.pin_id); pin=pins.get(key)
                if pin is None: raise InvalidModelError(f"net {net.net_id} references an unknown component/pin: {key}")
                if pin.electrical_type is PinElectricalType.NO_CONNECT:
                    raise InvalidModelError("NO_CONNECT pins cannot be assigned to a net")
                if key in connected: raise InvalidModelError(f"pin is assigned to more than one net: {key}")
                connected.add(key)
    def to_dict(self):
        return {"schema_version":self.SCHEMA_VERSION,
                "components":[c.to_dict() for c in sorted(self.components,key=lambda c:c.component_id)],
                "nets":[n.to_dict() for n in sorted(self.nets,key=lambda n:n.net_id)]}
    @classmethod
    def from_dict(cls,value:Mapping[str,Any]):
        if not isinstance(value,Mapping) or set(value)!={"schema_version","components","nets"}:
            raise InvalidModelError("SchematicModel snapshot has missing or unknown fields")
        if value["schema_version"]!=cls.SCHEMA_VERSION:
            raise InvalidModelError("Unsupported SchematicModel schema_version")
        raw_components,raw_nets=value["components"],value["nets"]
        if not isinstance(raw_components,(list,tuple)) or not isinstance(raw_nets,(list,tuple)):
            raise InvalidModelError("components and nets must be arrays")
        components=[]
        for raw in raw_components:
            keys={"component_id","reference_designator","symbol_id","pins","value","manufacturer_part"}
            if not isinstance(raw,Mapping) or set(raw)!=keys: raise InvalidModelError("Component snapshot has missing or unknown fields")
            if not isinstance(raw["pins"],(list,tuple)): raise InvalidModelError("component pins must be an array")
            pins=[]
            for p in raw["pins"]:
                if not isinstance(p,Mapping) or set(p)!={"pin_id","number","name","electrical_type"}:
                    raise InvalidModelError("Pin snapshot has missing or unknown fields")
                try: et=PinElectricalType(p["electrical_type"])
                except (ValueError,TypeError) as exc: raise InvalidModelError("Unsupported pin electrical_type") from exc
                pins.append(Pin(p["pin_id"],p["number"],p["name"],et))
            components.append(Component(raw["component_id"],raw["reference_designator"],raw["symbol_id"],
                                        tuple(pins),raw["value"],raw["manufacturer_part"]))
        nets=[]
        for raw in raw_nets:
            if not isinstance(raw,Mapping) or set(raw)!={"net_id","name","terminals"}:
                raise InvalidModelError("Net snapshot has missing or unknown fields")
            if not isinstance(raw["terminals"],(list,tuple)): raise InvalidModelError("net terminals must be an array")
            terminals=[]
            for tr in raw["terminals"]:
                if not isinstance(tr,Mapping) or set(tr)!={"component_id","pin_id"}:
                    raise InvalidModelError("PinRef snapshot has missing or unknown fields")
                terminals.append(PinRef(tr["component_id"],tr["pin_id"]))
            nets.append(Net(raw["net_id"],tuple(terminals),raw["name"]))
        return cls(tuple(components),tuple(nets))
