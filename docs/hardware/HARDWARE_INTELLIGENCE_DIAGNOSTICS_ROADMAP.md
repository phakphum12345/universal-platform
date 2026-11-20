# Hardware Intelligence & Diagnostics Roadmap

**Status:** Approved scope baseline; implementation remains incremental and evidence-gated.
**Scope decision:** 2026-11-09. Capability areas 1–10 are the core roadmap; 11–16 are long-term capabilities. This document records scope, not a claim that these capabilities are implemented.

## Safety and evidence boundary

The currently verified hardware implementation is an offline schematic metadata model, SVG schematic rendering, and a conservative static Electrical Rule Check (ERC) v1.0. The ERC evaluates declared pin and net types; it is not an electrical simulator, standards-compliance checker, physical-board inspector, or proof of safety. The driver package currently exposes metadata/interface and binding contracts; it is not evidence of a live hardware driver, sensor acquisition, register access, or device control.

The initial product boundary remains **analysis and simulation only**. No physical power-on, GPIO writes, actuator/motor control, firmware flashing, device programming, machine operation, or remote hardware control is authorized by this roadmap. Simulation, calculated values, datasheet-derived limits, and measured telemetry must be represented as distinct evidence kinds. Missing, stale, conflicting, or unsupported data must remain UNKNOWN/SKIPPED rather than being promoted to PASS.

## Core roadmap — capability areas 1–10

| ID | Capability | Scope | Initial acceptance evidence |
|---|---|---|---|
| HW-01 | Component Intelligence Database | Versioned component identity, aliases, manufacturer, package, pinout, datasheet provenance, operating limits, lifecycle and confidence. | Datasheet-page-linked fields, schema validation, provenance and revision tests. |
| HW-02 | Electrical Measurement & Analysis Engine | Voltage, current, resistance, power, energy, frequency, impedance, margins, tolerances and uncertainty; keep calculated, simulated and measured values distinct. | Dimensional/reference cases, uncertainty tests and source/evidence lineage. |
| HW-03 | Hardware Fault Diagnosis | Diagnose only supported faults from explicit observations and models; distinguish confirmed findings from hypotheses. | Fault-injection fixtures, false-positive/negative accounting, UNKNOWN for insufficient evidence. |
| HW-04 | Driver Runtime & Device Discovery | Permissioned driver lifecycle, device identity/capabilities, transport adapters and safe read-only acquisition. | Fake-device contract tests, adapter conformance, timeout/cancellation and no-write enforcement. |
| HW-05 | Live Hardware Monitoring | Timestamped telemetry, sampling metadata, history, thresholds and alerts, only for explicitly authorized read-only sources. | Replayable telemetry fixtures, clock/units validation, stale-data and disconnect tests. |
| HW-06 | PCB Design & Verification | Schematic/PCB linkage, net connectivity, footprints, routing, clearance, vias, planes and DRC. | Supported-format import/export round trips and independently checked DRC fixtures. |
| HW-07 | Circuit Simulation | DC, AC, transient and digital simulation adapters with explicit model/version/solver provenance. | Reference circuits, convergence/failure cases and simulation-vs-measurement labeling. |
| HW-08 | Thermal & Reliability Analysis | Power dissipation, thermal paths, derating, operating margins and reliability estimates connected to Physics. | Validated reference cases, assumptions, uncertainty and model applicability limits. |
| HW-09 | Hardware Test & Calibration | Test plans, calibration records, sensor calibration, equipment metadata and maintenance history. | Traceable calibration chain, repeatability and uncertainty budgets; no unsupported certification claims. |
| HW-10 | Hardware–Software Integration | Traceable links among component, schematic, PCB, firmware/software interface, driver, telemetry, Physics and CAD. | Cross-module contract tests, version compatibility, provenance and permission enforcement. |

## Long-term roadmap — capability areas 11–16

| ID | Capability | Scope | Entry condition |
|---|---|---|---|
| HW-11 | FPGA & Programmable Logic | HDL workflows, logic synthesis/verification and FPGA/CPLD device profiles. | Validated toolchain, licensing review and reproducible reference designs. |
| HW-12 | Firmware Intelligence | Firmware structure, bootloader, image integrity, update/recovery analysis and compatibility. | Isolated offline analysis, signed provenance and explicit approval for any future write workflow. |
| HW-13 | Hardware Security | Secure boot, device identity, firmware integrity, key lifecycle and vulnerability analysis. | Threat model, security review and non-exportable secret handling policy. |
| HW-14 | Power & Battery Management | Battery models, charging profiles, BMS, power budgets and energy efficiency. | Validated chemistry-specific models and explicit safety limits. |
| HW-15 | Manufacturing & BOM | BOM lifecycle, alternates, sourcing provenance, fabrication/assembly outputs and cost analysis. | Traceable part data, export validation and cost/source freshness. |
| HW-16 | Industrial & Network Hardware | Industrial controllers, field/network interfaces, device interoperability and operational diagnostics. | Protocol threat models, permission boundaries and hardware-in-the-loop test strategy. |

## Shared platform services

These are cross-cutting contracts, not separate competing hardware stacks:

1. **Device Discovery** — identify attached or described devices without assuming permission to communicate.
2. **Device Capability Registry** — declare supported operations, read/write classification, units, limits and evidence.
3. **Telemetry & Event Bus** — transport timestamped, typed observations with source and quality metadata.
4. **Safety & Permission Engine** — default-deny hardware writes; enforce authorization, limits, audit and human approval.
5. **Evidence & Diagnostic History** — immutable provenance for source documents, measurements, calculations, simulations, tests and diagnostic decisions.

## Delivery order and dependency rules

1. Complete component metadata/provenance and the electrical analysis foundation.
2. Extend static ERC only where declared models and datasheet evidence justify each rule.
3. Build fault diagnosis on explicit, testable observations; do not infer unmeasured conditions.
4. Implement read-only driver contracts, discovery and fake-device tests before considering real-device adapters.
5. Add telemetry replay/monitoring and diagnostic history.
6. Add circuit simulation and Physics adapters with reference cases.
7. Add PCB verification, calibration and reliability workflows.
8. Integrate the validated interfaces across CAD, Physics, firmware metadata and platform APIs.
9. Start HW-11–HW-16 only after their entry conditions are met.

## Completion semantics

Each capability must have a requirement ID, owner module, API/schema contract, test fixtures, evidence provenance, limitations and exact-SHA CI. Use PASS / FAIL / SKIPPED / UNKNOWN for evidence; maturity labels such as IMPLEMENTED / PARTIAL / PLANNED describe scope only. A successful static check does not prove electrical safety, and simulated or calculated telemetry is never represented as a physical measurement.

## Existing assets to reuse

- `src/universal_platform/hardware/schematic.py`: normalized schematic metadata model.
- `src/universal_platform/hardware/schematic_layout.py`: schematic SVG layout/rendering.
- `src/universal_platform/hardware/erc.py`: conservative static ERC v1.0.
- `src/universal_platform/hardware/driver.py`: driver interface/binding metadata contracts.
- `schemas/hardware/`: existing schematic, layout, driver-binding and ERC schemas.
- Existing Physics and engineering quantity modules: reuse after auditing their exact validated scope; do not duplicate them.

## Explicit non-goals

This roadmap does not authorize physical control, automatic firmware flashing, autonomous device writes, safety certification, unreviewed external data ingestion, paid service dependencies, or replacement of existing driver-generation work without an inventory proving a gap.
