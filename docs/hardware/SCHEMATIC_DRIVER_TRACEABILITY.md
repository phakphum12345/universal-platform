# Schematic-to-Driver Traceability

**Status:** PROPOSED  
**Requirement:** HWR-005  
**Implementation:** PARTIAL — normalized SchematicModel connectivity graph implemented in PR #46; schematic rendering and schematic-to-driver traceability remain NOT IMPLEMENTED / NOT VERIFIED

## 1. Purpose

Define traceability between physical design intent and software implementation. The platform should answer which driver/configuration represents a component, which schematic pin/net corresponds to an interrupt/reset/bus/power dependency, and what software must be reviewed when a board design changes.

## 2. Traceability chain

Where evidence exists, support:

Board revision → Schematic sheet/component → Pin → Net → Connector/controller → Protocol/resource → OS/firmware configuration → Driver/module → Register/API → Consumer/test.

The chain may be incomplete. Missing links must be visible and must not be guessed.

## 3. Traceability record

Each link includes source and target object IDs; relationship type (implements, connects-to, configures, consumes, depends-on, validates); source/target file paths and revisions; line/sheet/object/symbol references; evidence class and confidence; valid hardware/software version range; and reviewer confirmation when available.

## 4. Queries and reports

Support hardware-to-driver and driver-to-hardware lookup; pin/net-to-register/API trace when justified; board revision impact reports; orphaned hardware objects; driver resources without documented hardware origin; stale links; evidence gaps; and conflicting mappings.

## 5. Revision and change impact

Links are revision-aware. A link valid for one board or kernel version must not silently apply to another. Changed upstream objects mark dependent links for revalidation. Preserve historical links for audit.

## 6. Evidence integrity

Classify links as EXPLICIT, INFERRED, MANUALLY_CONFIRMED, or UNKNOWN. A matching signal name or visual resemblance alone is not proof of an electrical/software relationship.

## 7. Safety boundary

Read-only traceability in the initial phase. No live bus discovery, register access, GPIO operation, firmware changes, or physical control.

## 8. Acceptance criteria

- [ ] Components trace to driver/configuration references when evidence exists.
- [ ] Drivers trace back to hardware components/interfaces.
- [ ] Every relationship includes provenance, revision, and confidence.
- [ ] Incomplete, stale, and conflicting links are visible.
- [ ] Revision changes mark affected links for revalidation.
- [ ] Reports are exportable for review/audit.
- [ ] Unsupported links are never labelled confirmed.

## 9. Traceability and dependencies

Related: SCHEMATIC_INTELLIGENCE.md, HARDWARE_TO_SOFTWARE_MAPPING.md, DRIVER_ARCHITECTURE_INTELLIGENCE.md, HARDWARE_DESIGN_VERIFICATION.md.

HWR-005 — Schematic/driver bidirectional traceability (PROPOSED). Supports HR-002, HR-007 through HR-011, and HR-018.

## 10. Open questions

- Which EDA and source-control object IDs are stable enough for long-lived links?
- Should links be sidecar metadata, generated indexes, or both?
- Which reviewer roles may mark a relationship MANUALLY_CONFIRMED?


## Implemented schematic data subset

PR #46 adds normalized components, symbol IDs, pin identities/numbers/names/electrical types, nets and terminal references with deterministic JSON serialization. This does not yet provide EDA import/export, diagram rendering, electrical rule checking, or driver-interface binding.
