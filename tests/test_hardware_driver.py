import json
import pytest

from universal_platform.engineering.errors import InvalidModelError
from universal_platform.engineering.module_registry import ModuleManifest, ModuleOperation, ModuleRegistry
from universal_platform.hardware.schematic import Component, Net, Pin, PinElectricalType, PinRef, SchematicModel
from universal_platform.hardware.driver import (
    DriverBinding, DriverBindingModel, DriverInterface, DriverProtocol,
    DriverSignal, DriverSignalDirection,
)


def fixture_models():
    component = Component("component.u1", "U1", "mcu.header", (
        Pin("u1.rx", "1", "RX", PinElectricalType.INPUT),
        Pin("u1.tx", "2", "TX", PinElectricalType.OUTPUT),
        Pin("u1.vcc", "3", "VCC", PinElectricalType.POWER_IN),
        Pin("u1.nc", "4", "NC", PinElectricalType.NO_CONNECT),
    ))
    schematic = SchematicModel((component,), ())
    driver = DriverInterface(
        "driver.uart0", "org.driver.uart", "configure", DriverProtocol.UART, "1.0.0",
        (
            DriverSignal("signal.tx", "TX", DriverSignalDirection.OUTPUT),
            DriverSignal("signal.rx", "RX", DriverSignalDirection.INPUT),
            DriverSignal("signal.vcc", "VCC", DriverSignalDirection.POWER_OUT),
        ),
    )
    bindings = DriverBindingModel((driver,), (
        DriverBinding("binding.rx", "component.u1", "u1.rx", "driver.uart0", "signal.tx"),
        DriverBinding("binding.tx", "component.u1", "u1.tx", "driver.uart0", "signal.rx"),
        DriverBinding("binding.vcc", "component.u1", "u1.vcc", "driver.uart0", "signal.vcc"),
    ))
    return schematic, driver, bindings


def registry():
    value = ModuleRegistry()
    value.register(ModuleManifest(
        "org.driver.uart", "1.0.0", "hardware.driver",
        (ModuleOperation("configure"),),
    ))
    return value


def test_driver_binding_v1_round_trip_and_validation_against_schematic():
    schematic, _, model = fixture_models()
    restored = DriverBindingModel.from_dict(json.loads(json.dumps(model.to_dict())))
    assert restored.to_dict() == model.to_dict()
    restored.validate_against(schematic, registry())


def test_driver_binding_requires_known_driver_and_signal():
    schematic, driver, model = fixture_models()
    unknown_driver = DriverBinding("binding.x", "component.u1", "u1.rx", "driver.missing", "signal.tx")
    with pytest.raises(InvalidModelError, match="unknown driver"):
        DriverBindingModel((driver,), (unknown_driver,)).validate_against(schematic)
    unknown_signal = DriverBinding("binding.x", "component.u1", "u1.rx", "driver.uart0", "signal.missing")
    with pytest.raises(InvalidModelError, match="unknown driver signal"):
        DriverBindingModel((driver,), (unknown_signal,)).validate_against(schematic)


def test_driver_binding_rejects_unknown_pins_multiple_bindings_and_no_connect():
    schematic, driver, model = fixture_models()
    dangling = DriverBinding("binding.dangling", "component.u1", "u1.missing", "driver.uart0", "signal.tx")
    with pytest.raises(InvalidModelError, match="unknown schematic pin"):
        DriverBindingModel((driver,), (dangling,)).validate_against(schematic)
    repeated = model.bindings + (
        DriverBinding("binding.duplicate", "component.u1", "u1.rx", "driver.uart0", "signal.tx"),
    )
    with pytest.raises(InvalidModelError, match="multiple driver bindings"):
        DriverBindingModel((driver,), repeated).validate_against(schematic)
    no_connect = DriverBinding("binding.nc", "component.u1", "u1.nc", "driver.uart0", "signal.tx")
    with pytest.raises(InvalidModelError, match="NO_CONNECT"):
        DriverBindingModel((driver,), (no_connect,)).validate_against(schematic)


def test_driver_binding_checks_pin_and_signal_direction_compatibility():
    schematic, driver, model = fixture_models()
    wrong = DriverBinding("binding.wrong", "component.u1", "u1.rx", "driver.uart0", "signal.rx")
    with pytest.raises(InvalidModelError, match="incompatible"):
        DriverBindingModel((driver,), (wrong,)).validate_against(schematic)


def test_driver_binding_checks_module_operation_when_registry_is_supplied():
    schematic, driver, model = fixture_models()
    model.validate_against(schematic, registry())
    with pytest.raises(InvalidModelError, match="unknown module"):
        DriverBindingModel(
            (DriverInterface("driver.bad", "org.missing", "configure", DriverProtocol.GPIO, "1.0.0",
                             (DriverSignal("gpio.1", "GPIO1", DriverSignalDirection.OUTPUT),)),),
            (),
        ).validate_against(schematic, registry())


def test_driver_binding_snapshot_rejects_unknown_version_and_fields():
    _, _, model = fixture_models()
    data = model.to_dict()
    with pytest.raises(InvalidModelError, match="schema_version"):
        DriverBindingModel.from_dict(dict(data, schema_version="2.0"))
    with pytest.raises(InvalidModelError, match="missing or unknown"):
        DriverBindingModel.from_dict(dict(data, extra=True))


def test_driver_interface_rejects_duplicate_signals_and_bad_versions():
    signal = DriverSignal("signal.tx", "TX", DriverSignalDirection.OUTPUT)
    with pytest.raises(InvalidModelError, match="unique"):
        DriverInterface("driver.uart", "org.driver.uart", "configure", DriverProtocol.UART,
                        "1.0.0", (signal, signal))
    with pytest.raises(InvalidModelError, match="MAJOR.MINOR.PATCH"):
        DriverInterface("driver.uart", "org.driver.uart", "configure", DriverProtocol.UART,
                        "v1", (signal,))
