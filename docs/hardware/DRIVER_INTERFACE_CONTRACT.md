# Hardware Driver Interface Contract

**Status:** Metadata-only driver interface and schematic pin binding subset implemented under PR #47.

## 1. Core records

- `DriverInterface`: stable driver ID, module ID, operation ID, protocol, semantic version and declared signals.
- `DriverSignal`: stable signal ID, name and direction from the driver/controller perspective.
- `DriverBinding`: stable binding ID mapping one schematic component pin to one driver signal.
- `DriverBindingModel`: versioned collection of interfaces and bindings.

Supported protocol labels: GPIO, I2C, SPI, UART, CAN, USB, PCIE, PWM, ADC, DAC and GENERIC.

## 2. Validation

`validate_against(schematic, registry=None)` validates component/pin references, driver/signal references, one driver binding per schematic pin, NO_CONNECT restrictions and basic direction compatibility. When a ModuleRegistry is supplied, each driver module/operation declaration must resolve.

Direction is expressed from the controller/driver perspective. For example, a peripheral INPUT pin requires a driver OUTPUT signal. PASSIVE pins permit any declared signal direction. This is a structural contract, not an electrical rule checker.

## 3. Safety boundary

The model does not import/load/execute driver code, open a bus, configure GPIO, send commands, write firmware, control hardware or perform electrical measurements. Declared module/operation references are metadata only.

## 4. Limitations and future work

- Voltage levels, current limits, pull-ups, timing and bus topology are not checked.
- Shared bus topology, interrupts, reset sequencing and power domains need richer constraints.
- No actual driver adapters or firmware interface implementations exist in this contract.
- No hardware-in-the-loop evidence is produced.
