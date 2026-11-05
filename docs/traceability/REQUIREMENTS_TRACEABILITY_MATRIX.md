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
| R-008 | Cross-domain calculation | UNIVERSAL_CALCULATION_ENGINE; UEIC | Documented |
| R-009 | Governed capability evolution | PLATFORM_SELF_EVOLUTION | Documented |
| R-010 | Cost-aware/local-first/open reuse | UNIVERSAL_REQUIREMENTS | Documented |
| R-011 | Review requirements before implementation | ROADMAP; UNIVERSAL_REQUIREMENTS | Documented |
| R-012 | No automatic integration of existing projects | PROJECT_INTEGRATION | Explicit |
| R-013 | Shared multidisciplinary engineering core | UNIVERSAL_ENGINEERING_INTELLIGENCE_CORE | Specification added |
| R-014 | 3D design, tools, machines, mechanisms, structures and products | 3D_DESIGN_INTELLIGENCE; 3D_TOOL_GENERATION_ENGINE | Specification added |
| R-015 | Reuse existing Driver Generation; no duplicate | DRIVER_ARCHITECTURE_INTELLIGENCE; DRIVER_REFACTORING_ENGINE | Inventory required |

## Engineering and 3D sub-requirements

See [Engineering Requirements Traceability](ENGINEERING_REQUIREMENTS_TRACEABILITY.md) for UEIC-001..UEIC-006, CAD-001..CAD-007, API-001, DATA-001 and SAFE-001 with proposed acceptance evidence.

## Coverage checklist
- [x] Platform vision and broad scope
- [x] Requirements and quality attributes
- [x] Command/task orchestration concept
- [x] System discovery and adaptation
- [x] Calculation and multidisciplinary engineering
- [x] IC/chip, board, sensor, module analysis
- [x] Virtual lab and simulation
- [x] Existing project integration boundaries
- [x] Governed self-evolution
- [x] Engineering/3D specification and traceability documents added
- [ ] Full historical conversation audit: not yet proven exhaustive
- [ ] Resolve ambiguous phrase “ยังเก็บคำสั่งไม่หนดครับ”
- [ ] Owner selects first end-to-end use case
- [ ] Confirm OS/platform priority and minimum hardware
- [ ] Approve final architecture, technology choices and vertical-slice criteria
- [ ] Inventory existing Driver Generation and verify reuse boundary

## Status semantics
Documented means the requirement is represented in the specification. It does not mean implemented, tested, or accepted. Use PASS / FAIL / SKIPPED / UNKNOWN for executed evidence. Do not mark Phase 0 fully complete until every open item is resolved or explicitly accepted as open/deferred by the owner.
