# Requirements Traceability Matrix

**Status:** Phase 0 baseline; mappings are documentation coverage, not implementation evidence.

| ID | Requirement | Primary document | State |
|---|---|---|---|
| R-001 | Cross-disciplinary extensibility | UNIVERSAL_REQUIREMENTS; DOMAIN_CATALOGUE | Documented |
| R-002 | Cross-platform support | UNIVERSAL_REQUIREMENTS; PLATFORM_ARCHITECTURE | Documented |
| R-003 | Computing/software/hardware/electronics/communications/science | DOMAIN_CATALOGUE | Documented |
| R-004 | Authorized system understanding | SYSTEM_INTELLIGENCE | Documented |
| R-005 | Adapt existing and create new systems/apps | SYSTEM_INTELLIGENCE; PLATFORM_SELF_EVOLUTION | Documented |
| R-006 | IC/chip/board/sensor/module intelligence | DEVICE_INTELLIGENCE | Documented |
| R-007 | Analysis/simulation only; no physical control initially | DEVICE_INTELLIGENCE; VIRTUAL_LAB_AND_SIMULATION | Explicit |
| R-008 | Cross-domain calculation | UNIVERSAL_CALCULATION_ENGINE | Documented |
| R-009 | Governed capability evolution | PLATFORM_SELF_EVOLUTION | Documented |
| R-010 | Cost-aware/local-first/open reuse | UNIVERSAL_REQUIREMENTS | Documented |
| R-011 | Review requirements before implementation | ROADMAP; UNIVERSAL_REQUIREMENTS | Documented |
| R-012 | No automatic integration of existing projects | PROJECT_INTEGRATION | Explicit |

## Coverage checklist
- [x] Platform vision and broad scope
- [x] Requirements and quality attributes
- [x] Command/task orchestration concept
- [x] System discovery and adaptation
- [x] Calculation and engineering modules
- [x] IC/chip, board, sensor, module analysis
- [x] Virtual lab and simulation
- [x] Existing project integration boundaries
- [x] Governed self-evolution
- [x] Evidence and traceability model
- [ ] Full historical conversation audit: not yet proven exhaustive
- [ ] Resolve ambiguous phrase “ยังเก็บคำสั่งไม่หนดครับ”
- [ ] Owner selects first end-to-end use case
- [ ] Confirm OS/platform priority and minimum hardware
- [ ] Approve final architecture and technology choices

## Status semantics
Documented means the requirement is represented in the specification. It does not mean implemented, tested, or accepted. Use PASS / FAIL / SKIPPED / UNKNOWN for executed evidence. Do not mark Phase 0 fully complete until every open item is resolved or explicitly accepted as open/deferred by the owner.
