# Hardware-to-Software Mapping

**Status:** PROPOSED  
**Requirement:** HWR-002  
**Implementation:** NOT IMPLEMENTED / NOT VERIFIED

## 1. Purpose

Specify how physical components and electrical interfaces map to firmware, operating-system, kernel, driver, HAL, and application software. The purpose is to reveal dependencies and compatibility constraints before changing driver or system architecture. A mapping is an evidence-backed relationship, not an assumption that a driver exists or is correct.

## 2. Mapping layers

Support applicable relationships across:
1. Physical component: IC/chip, board, sensor, module, connector, external device.
2. Electrical interface: pins, nets, voltage domains, reset, clock, interrupt, power, signal direction.
3. Transport/protocol: GPIO, I2C, SPI, UART, USB, PCIe, CAN, Ethernet, SDIO, or documented alternatives.
4. Hardware controller: SoC peripheral, bus controller, bridge, DMA engine, interrupt controller, clock/reset controller, regulator.
5. Software abstraction: bus framework, subsystem, HAL, firmware service, kernel framework, userspace API.
6. Implementation: driver source, configuration, Device Tree, ACPI, firmware manifest, build target, application consumer.

Do not force every device into one universal driver pattern.

## 3. Mapping record

Each relationship should include hardware identity/revision; component and pin/net IDs; documented electrical characteristics; interface/protocol; bus address or chip-select only when supplied; controller/platform; OS/kernel/firmware versions; driver/module/source symbols; configuration source; dependent subsystem/consumer; evidence, confidence, and unresolved assumptions.

Classify relationships as EXPLICIT, INFERRED, MANUALLY_CONFIRMED, or UNKNOWN.

## 4. Required analysis

- Map component pins to schematic nets and board connectors.
- Map nets/pins to controller peripherals and software interfaces when documented.
- Identify bus topology, addressing, chip-select, interrupt, reset, clock, and power dependencies.
- Trace device identity through enumeration, driver binding, and application exposure.
- Detect missing links, conflicting definitions, duplicate ownership, and unsupported combinations.
- Compare mappings across hardware revisions and software versions.

## 5. Platform-specific coverage

Potential targets include Linux (kernel drivers, Device Tree, ACPI, Kconfig, subsystem frameworks), Windows (PnP IDs, INF metadata, KMDF/UMDF, ACPI), embedded firmware/RTOS (BSP, HAL, peripheral drivers, interrupt vectors), and other documented platforms. These are candidate domains, not a claim of complete support.

## 6. Outputs

Produce a hardware/software mapping table, component-to-driver dependency graph, pin/net-to-interface trace, OS/version compatibility matrix, unresolved evidence-gap list, and impact report for proposed changes.

## 7. Safety boundary

Initial capability is read-only and offline. No live bus probing, privileged hardware enumeration, register access, GPIO operation, firmware flashing, or device control.

## 8. Acceptance criteria

- [ ] Components trace to documented pins/nets and software mappings where evidence exists.
- [ ] Drivers link to source, configuration, target OS/kernel/firmware, and hardware revision when known.
- [ ] Missing/conflicting relationships are surfaced, not guessed.
- [ ] Version and platform constraints are explicit.
- [ ] Every mapping carries provenance and confidence.
- [ ] Change impact lists affected layers.
- [ ] No physical hardware operation occurs.

## 9. Traceability and dependencies

Related: SCHEMATIC_INTELLIGENCE.md, DRIVER_ARCHITECTURE_INTELLIGENCE.md, SCHEMATIC_DRIVER_TRACEABILITY.md, DEVICE_INTELLIGENCE.md.

HWR-002 — Hardware-to-software mapping (PROPOSED). Supports HR-002 through HR-005 and HR-007 through HR-011.

## 10. Open questions

- Which OS/RTOS targets belong in the first support matrix?
- Which metadata sources are authoritative per target?
- What evidence is required to confirm a mapping?
