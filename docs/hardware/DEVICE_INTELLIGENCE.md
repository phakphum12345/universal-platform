# Device Intelligence: ICs, Chips, Boards, Sensors, and Modules

**Status:** CONFIRMED initial scope = analysis and simulation only. Physical control is excluded.

## Supported device families
- ICs/chips: MCU, MPU, CPU, GPU, FPGA, memory, logic, analog, mixed-signal, power-management, communication and interface ICs.
- Boards: development boards, SBCs, custom PCBs, carrier boards, power and interface boards.
- Sensors: temperature, pressure, humidity, motion, inertial, optical, acoustic, position, chemical and environmental sensors.
- Modules: radio, GNSS, display, storage, motor-driver, power, connectivity, and application modules.

## Component knowledge model
Part number and aliases; manufacturer; package/footprint; function; block diagram; pinout; electrical characteristics; absolute maximum ratings; recommended operating conditions; supply rails; current and power; logic levels; interfaces/protocols; clock/timing; thermal characteristics; environmental constraints; lifecycle/availability; source document, revision, page, date, and confidence.

## Analysis capabilities
- Identify components from markings, images, BOMs, and documents when evidence permits.
- Parse datasheets and extract tables, diagrams, pin descriptions, timing, and limits.
- Explain architecture, pin functions, interfaces, power sequencing, and operating conditions.
- Analyze schematics, PCB layouts, netlists, footprints, and BOMs.
- Calculate power, current, voltage margins, signal timing, pull-ups, filtering, thermal estimates, and interface budgets.
- Compare alternatives and evaluate component/board/module compatibility.
- Generate reviewable circuit concepts, connection tables, BOM proposals, and simulation inputs.

## Compatibility dimensions
Electrical voltage/current; logic thresholds; interface/protocol; pin mapping; timing/clock; power budget; thermal limits; package/footprint; mechanical fit; firmware/software support; environmental limits; availability and lifecycle. Compatibility outcomes must be PASS / FAIL / CONDITIONAL / UNKNOWN with reasons and sources.

## Input formats
PDF datasheets, images, text tables, CSV/XLSX BOMs, schematic exports, PCB design files, Gerber/drill files, netlists, SPICE models, IBIS models, and vendor specifications where supported. Unsupported formats must be declared.

## Explicit non-goals for initial phase
No physical power-on, GPIO writes, live sensor reads, actuator or motor control, firmware flashing, device programming, machine operation, or remote hardware control. A simulated device is not a real measurement.

## Acceptance criteria
- Every extracted electrical limit cites the datasheet revision/page.
- Pin mappings are validated and uncertainty is visible.
- Compatibility checks show each dimension and its evidence.
- Calculations state assumptions and margins.
- No physical-control interface is exposed in the initial release.
