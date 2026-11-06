"""Offline hardware driver interface and schematic pin binding contracts.

These records validate metadata and connectivity only. They do not load driver
code, configure buses, write firmware or actuate hardware.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum
import re
from typing import Any, ClassVar

from universal_platform.engineering.errors import InvalidModelError
from universal_platform.engineering.module_registry import ModuleRegistry
from .schematic import PinElectricalType, SchematicModel

_IDENTIFIER = re.compile(r"^[a-z0-9]+(?:[._/-][a-z0-9]+)*$")
_SEMVER = re.compile(r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$")


def _id(value: str, label: str) -> None:
    if not isinstance(value, str) or not _IDENTIFIER.fullmatch(value):
        raise InvalidModelError(f"{label} must be a stable lowercase identifier")


class DriverProtocol(str, Enum):
    GPIO = "GPIO"
    I2C = "I2C"
    SPI = "SPI"
    UART = "UART"
    CAN = "CAN"
    USB = "USB"
    PCIE = "PCIE"
    PWM = "PWM"
    ADC = "ADC"
    DAC = "DAC"
    GENERIC = "GENERIC"


class DriverSignalDirection(str, Enum):
    INPUT = "INPUT"
    OUTPUT = "OUTPUT"
    BIDIRECTIONAL = "BIDIRECTIONAL"
    POWER_IN = "POWER_IN"
    POWER_OUT = "POWER_OUT"
    OPEN_DRAIN = "OPEN_DRAIN"
    OPEN_COLLECTOR = "OPEN_COLLECTOR"


@dataclass(frozen=True, slots=True)
class DriverSignal:
    signal_id: str
    name: str
    direction: DriverSignalDirection

    def __post_init__(self) -> None:
        _id(self.signal_id, "signal_id")
        if not isinstance(self.name, str) or not self.name.strip():
            raise InvalidModelError("driver signal name is required")
        if not isinstance(self.direction, DriverSignalDirection):
            raise InvalidModelError("direction must be a DriverSignalDirection")

    def to_dict(self) -> dict[str, str]:
        return {"signal_id": self.signal_id, "name": self.name, "direction": self.direction.value}


@dataclass(frozen=True, slots=True)
class DriverInterface:
    driver_id: str
    module_id: str
    operation_id: str
    protocol: DriverProtocol
    version: str
    signals: tuple[DriverSignal, ...]

    def __post_init__(self) -> None:
        _id(self.driver_id, "driver_id")
        _id(self.module_id, "module_id")
        _id(self.operation_id, "operation_id")
        if not isinstance(self.protocol, DriverProtocol):
            raise InvalidModelError("protocol must be a DriverProtocol")
        if not isinstance(self.version, str) or not _SEMVER.fullmatch(self.version):
            raise InvalidModelError("driver version must use MAJOR.MINOR.PATCH")
        if not isinstance(self.signals, tuple) or not self.signals:
            raise InvalidModelError("driver signals must be a non-empty immutable tuple")
        if any(not isinstance(signal, DriverSignal) for signal in self.signals):
            raise InvalidModelError("signals must contain DriverSignal records")
        ids = tuple(signal.signal_id for signal in self.signals)
        if len(ids) != len(set(ids)):
            raise InvalidModelError("driver signal IDs must be unique")

    def to_dict(self) -> dict[str, Any]:
        return {
            "driver_id": self.driver_id,
            "module_id": self.module_id,
            "operation_id": self.operation_id,
            "protocol": self.protocol.value,
            "version": self.version,
            "signals": [signal.to_dict() for signal in sorted(self.signals, key=lambda item: item.signal_id)],
        }


@dataclass(frozen=True, slots=True)
class DriverBinding:
    binding_id: str
    component_id: str
    pin_id: str
    driver_id: str
    signal_id: str

    def __post_init__(self) -> None:
        for value, label in (
            (self.binding_id, "binding_id"),
            (self.component_id, "component_id"),
            (self.pin_id, "pin_id"),
            (self.driver_id, "driver_id"),
            (self.signal_id, "signal_id"),
        ):
            _id(value, label)

    def to_dict(self) -> dict[str, str]:
        return {
            "binding_id": self.binding_id,
            "component_id": self.component_id,
            "pin_id": self.pin_id,
            "driver_id": self.driver_id,
            "signal_id": self.signal_id,
        }


_COMPATIBLE_DIRECTIONS = {
    PinElectricalType.PASSIVE: frozenset(DriverSignalDirection),
    PinElectricalType.INPUT: frozenset({DriverSignalDirection.OUTPUT, DriverSignalDirection.BIDIRECTIONAL}),
    PinElectricalType.OUTPUT: frozenset({DriverSignalDirection.INPUT, DriverSignalDirection.BIDIRECTIONAL}),
    PinElectricalType.BIDIRECTIONAL: frozenset({DriverSignalDirection.BIDIRECTIONAL}),
    PinElectricalType.POWER_IN: frozenset({DriverSignalDirection.POWER_OUT}),
    PinElectricalType.POWER_OUT: frozenset({DriverSignalDirection.POWER_IN}),
    PinElectricalType.OPEN_DRAIN: frozenset({DriverSignalDirection.OPEN_DRAIN, DriverSignalDirection.BIDIRECTIONAL}),
    PinElectricalType.OPEN_COLLECTOR: frozenset({DriverSignalDirection.OPEN_COLLECTOR, DriverSignalDirection.BIDIRECTIONAL}),
    PinElectricalType.NO_CONNECT: frozenset(),
}


@dataclass(frozen=True, slots=True)
class DriverBindingModel:
    interfaces: tuple[DriverInterface, ...]
    bindings: tuple[DriverBinding, ...]

    SCHEMA_VERSION: ClassVar[str] = "1.0"

    def __post_init__(self) -> None:
        if not isinstance(self.interfaces, tuple) or any(not isinstance(item, DriverInterface) for item in self.interfaces):
            raise InvalidModelError("interfaces must be an immutable tuple of DriverInterface records")
        if not isinstance(self.bindings, tuple) or any(not isinstance(item, DriverBinding) for item in self.bindings):
            raise InvalidModelError("bindings must be an immutable tuple of DriverBinding records")
        driver_ids = tuple(item.driver_id for item in self.interfaces)
        binding_ids = tuple(item.binding_id for item in self.bindings)
        if len(driver_ids) != len(set(driver_ids)):
            raise InvalidModelError("driver IDs must be unique")
        if len(binding_ids) != len(set(binding_ids)):
            raise InvalidModelError("binding IDs must be unique")

    def validate_against(
        self,
        schematic: SchematicModel,
        registry: ModuleRegistry | None = None,
    ) -> None:
        if not isinstance(schematic, SchematicModel):
            raise InvalidModelError("schematic must be a SchematicModel")
        if registry is not None and not isinstance(registry, ModuleRegistry):
            raise InvalidModelError("registry must be a ModuleRegistry")
        drivers = {item.driver_id: item for item in self.interfaces}
        pins = {
            (component.component_id, pin.pin_id): pin
            for component in schematic.components
            for pin in component.pins
        }
        used_pins: set[tuple[str, str]] = set()
        for interface in self.interfaces:
            if registry is not None:
                registry.resolve_operation(interface.module_id, interface.operation_id)
        for binding in self.bindings:
            key = (binding.component_id, binding.pin_id)
            pin = pins.get(key)
            if pin is None:
                raise InvalidModelError(f"binding references an unknown schematic pin: {key}")
            if key in used_pins:
                raise InvalidModelError(f"schematic pin has multiple driver bindings: {key}")
            if pin.electrical_type is PinElectricalType.NO_CONNECT:
                raise InvalidModelError("NO_CONNECT pins cannot have driver bindings")
            interface = drivers.get(binding.driver_id)
            if interface is None:
                raise InvalidModelError(f"binding references an unknown driver: {binding.driver_id}")
            signals = {signal.signal_id: signal for signal in interface.signals}
            signal = signals.get(binding.signal_id)
            if signal is None:
                raise InvalidModelError(f"binding references an unknown driver signal: {binding.signal_id}")
            if signal.direction not in _COMPATIBLE_DIRECTIONS[pin.electrical_type]:
                raise InvalidModelError(
                    f"driver signal direction {signal.direction.value} is incompatible with "
                    f"schematic pin type {pin.electrical_type.value}"
                )
            used_pins.add(key)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.SCHEMA_VERSION,
            "interfaces": [item.to_dict() for item in sorted(self.interfaces, key=lambda item: item.driver_id)],
            "bindings": [item.to_dict() for item in sorted(self.bindings, key=lambda item: item.binding_id)],
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "DriverBindingModel":
        if not isinstance(value, Mapping) or set(value) != {"schema_version", "interfaces", "bindings"}:
            raise InvalidModelError("DriverBindingModel snapshot has missing or unknown fields")
        if value["schema_version"] != cls.SCHEMA_VERSION:
            raise InvalidModelError("Unsupported DriverBindingModel schema_version")
        raw_interfaces, raw_bindings = value["interfaces"], value["bindings"]
        if not isinstance(raw_interfaces, (list, tuple)) or not isinstance(raw_bindings, (list, tuple)):
            raise InvalidModelError("interfaces and bindings must be arrays")
        interfaces: list[DriverInterface] = []
        for raw in raw_interfaces:
            keys = {"driver_id", "module_id", "operation_id", "protocol", "version", "signals"}
            if not isinstance(raw, Mapping) or set(raw) != keys:
                raise InvalidModelError("DriverInterface snapshot has missing or unknown fields")
            if not isinstance(raw["signals"], (list, tuple)):
                raise InvalidModelError("driver signals must be an array")
            signals: list[DriverSignal] = []
            for signal in raw["signals"]:
                if not isinstance(signal, Mapping) or set(signal) != {"signal_id", "name", "direction"}:
                    raise InvalidModelError("DriverSignal snapshot has missing or unknown fields")
                try:
                    direction = DriverSignalDirection(signal["direction"])
                except (ValueError, TypeError) as exc:
                    raise InvalidModelError("Unsupported driver signal direction") from exc
                signals.append(DriverSignal(signal["signal_id"], signal["name"], direction))
            try:
                protocol = DriverProtocol(raw["protocol"])
            except (ValueError, TypeError) as exc:
                raise InvalidModelError("Unsupported driver protocol") from exc
            interfaces.append(DriverInterface(
                raw["driver_id"], raw["module_id"], raw["operation_id"],
                protocol, raw["version"], tuple(signals),
            ))
        bindings: list[DriverBinding] = []
        for raw in raw_bindings:
            if not isinstance(raw, Mapping) or set(raw) != {
                "binding_id", "component_id", "pin_id", "driver_id", "signal_id"
            }:
                raise InvalidModelError("DriverBinding snapshot has missing or unknown fields")
            bindings.append(DriverBinding(
                raw["binding_id"], raw["component_id"], raw["pin_id"],
                raw["driver_id"], raw["signal_id"],
            ))
        return cls(tuple(interfaces), tuple(bindings))
