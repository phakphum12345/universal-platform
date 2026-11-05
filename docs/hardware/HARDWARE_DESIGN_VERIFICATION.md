# Hardware Design Verification

**Status:** PROPOSED  
**Requirement:** HWR-006  
**Implementation:** NOT IMPLEMENTED / NOT VERIFIED

## 1. Purpose

Specify evidence-driven checks for schematic, component, electrical, and driver consistency before physical construction or operation. Deterministic rule violations must be distinguished from heuristic warnings and questions requiring engineering judgment.

## 2. Verification domains

### 2.1 Schematic and connectivity
- Unconnected or unexpectedly connected pins.
- Duplicate/inconsistent component references.
- Unresolved symbols, footprints, and net labels.
- Conflicting net names or ambiguous connectivity.
- Connector pinout mismatch against supplied specifications.

### 2.2 Electrical constraints
- Voltage-domain incompatibility and logic-level mismatch.
- Input/output direction conflicts.
- Pull-up/pull-down and open-drain requirements.
- Current, power, and thermal budget inconsistencies when data exists.
- Missing level shifting/protection where documented limits require it.

### 2.3 Interface and timing
- I2C address collisions and SPI chip-select conflicts.
- UART signal mapping and voltage assumptions.
- Bus speed/timing constraints.
- Interrupt polarity/trigger mismatch.
- Clock frequency/tolerance and reset sequencing constraints.

### 2.4 Power and resource dependencies
- Power-rail sequencing and dependency constraints.
- Regulator capacity/load estimates.
- Decoupling/reference-design checks when rules and data are supplied.
- Shared GPIO/peripheral, DMA, interrupt, clock, reset, and pin-multiplexing conflicts.

### 2.5 Driver/software consistency
- Driver match IDs versus component identity.
- Register offsets, widths, masks, and reset values versus supplied datasheets.
- Device Tree/ACPI/configuration versus schematic connectivity.
- Missing interrupt, clock, reset, regulator, or bus declarations.
- Unsupported hardware revision or OS/kernel version.
- Stale mappings after schematic/BOM changes.

## 3. Rule model

Each rule defines stable ID/version, domain/applicability, required inputs and authoritative sources, deterministic or heuristic classification, severity (BLOCKER/ERROR/WARNING/INFO), affected objects, evidence/confidence, suggested remediation, and limitations.

If inputs are insufficient, return NOT_APPLICABLE, UNKNOWN, or SKIPPED as appropriate. Missing data must never become PASS.

## 4. Result model

Use PASS, FAIL, SKIPPED, UNKNOWN, and NOT_APPLICABLE. Record rule version, input revision, source SHA where relevant, tool version, execution time, and evidence. PASS means only that the stated rule ran and its defined condition was satisfied.

## 5. Calculation and simulation

Estimates identify formulas, units, tolerances, assumptions, and source values. Simulations identify model fidelity, tool/version, configuration, and limitations. Neither calculations nor simulations alone prove physical behavior.

Initial phase permits offline calculations and simulations only. No circuit energization, live equipment connection, or hardware operation.

## 6. Acceptance criteria

- [ ] Rules are versioned and applicability is explicit.
- [ ] Findings point to affected design/configuration/driver objects.
- [ ] Deterministic failures are distinct from heuristic warnings.
- [ ] Missing inputs yield UNKNOWN, SKIPPED, or NOT_APPLICABLE, never unsupported PASS.
- [ ] Electrical findings cite specifications and operating conditions.
- [ ] Calculations/simulations preserve assumptions, units, model versions, and limitations.
- [ ] Results are reproducible from recorded inputs and tool versions.
- [ ] No physical energization or device operation occurs.

## 7. Traceability and dependencies

Related: SCHEMATIC_INTELLIGENCE.md, HARDWARE_TO_SOFTWARE_MAPPING.md, DRIVER_ARCHITECTURE_INTELLIGENCE.md, DRIVER_REFACTORING_ENGINE.md, SCHEMATIC_DRIVER_TRACEABILITY.md.

HWR-006 — Offline hardware and driver design verification (PROPOSED). Supports HR-010 through HR-014 and HR-018.

## 8. Open questions

- Which electrical standards and reference-design libraries are in scope?
- Which checks must be deterministic in the first milestone?
- Which thresholds/tolerances are configurable per project?
- How can reviewers approve or waive findings while preserving audit history?
