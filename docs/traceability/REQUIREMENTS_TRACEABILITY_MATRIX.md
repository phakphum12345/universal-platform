# Requirements Traceability Matrix

**Status:** Documentation baseline plus initial engineering-core evidence, updated 2026-11-06. Documentation coverage is not implementation evidence.

| ID | Requirement | Primary document | Current state |
|---|---|---|---|
| R-001 | Cross-disciplinary extensibility | UNIVERSAL_REQUIREMENTS; DOMAIN_CATALOGUE | Documented; broad module ecosystem proposed |
| R-002 | Cross-platform support | UNIVERSAL_REQUIREMENTS; PLATFORM_ARCHITECTURE | Requirement documented; platform matrix OPEN |
| R-003 | Computing/software/hardware/electronics/communications/science | DOMAIN_CATALOGUE | Documented |
| R-004 | Authorized system understanding | SYSTEM_INTELLIGENCE | Specified; implementation not verified |
| R-005 | Adapt existing and create new systems/apps | SYSTEM_INTELLIGENCE; PLATFORM_SELF_EVOLUTION | Specified; governed implementation not verified |
| R-006 | IC/chip/board/sensor/module intelligence | DEVICE_INTELLIGENCE | Specified; runtime implementation not verified |
| R-007 | Analysis/simulation only; no physical control initially | DEVICE_INTELLIGENCE; VIRTUAL_LAB_AND_SIMULATION | Explicit boundary |
| R-008 | Cross-domain calculation | UNIVERSAL_CALCULATION_ENGINE; UEIC | Initial mechanics/electrical/thermal subset implemented; broader scope proposed |
| R-009 | Governed capability evolution | PLATFORM_SELF_EVOLUTION | Specified; implementation not verified |
| R-010 | Cost-aware/local-first/open reuse | UNIVERSAL_REQUIREMENTS | Documented; numeric resource budget OPEN |
| R-011 | Review requirements before implementation | ROADMAP; UNIVERSAL_REQUIREMENTS | Documented; ongoing gates apply |
| R-012 | No automatic integration of existing projects | PROJECT_INTEGRATION | Explicit boundary |
| R-013 | Shared multidisciplinary engineering core | UNIVERSAL_ENGINEERING_INTELLIGENCE_CORE | Initial foundation implemented; full UEIC orchestration proposed |
| R-014 | 3D design, tools, machines, mechanisms, structures and products | 3D_DESIGN_INTELLIGENCE; 3D_TOOL_GENERATION_ENGINE | Specification; only analytic primitives, nominal joint contracts and narrow tree/planar kinematics slices implemented |
| R-015 | Reuse existing Driver Generation; no duplicate | DRIVER_ARCHITECTURE_INTELLIGENCE; DRIVER_REFACTORING_ENGINE | EFI/OpenCore candidate partially inspected; generic source UNKNOWN |

## Engineering and 3D sub-requirements

See [Engineering Requirements Traceability](ENGINEERING_REQUIREMENTS_TRACEABILITY.md) for UEIC-001..UEIC-006, CAD-001..CAD-007, API-001, DATA-001 and SAFE-001 with acceptance evidence. CAD-003A and CAD-003B track the initial planar 2R inverse-kinematics and 4R loop-closure slices separately; neither closes general CAD-003.

## Audit and planning artifacts

- [x] Repository capability inventory created.
- [x] Engineering master file plan created.
- [x] Phase plan updated with merged engineering-core baseline.
- [x] Reference-case, failure-mode, geometry interchange, motion reference, hazard, test strategy, resource budget and release/rollback documents added.
- [ ] Complete external source tree/content/runtime/license/security audit.
- [ ] Locate canonical generic Driver Generation source or obtain owner decision to keep it UNKNOWN.
- [ ] Complete technology comparison and select first CAD/solver stack.
- [ ] Owner approves first vertical slice and acceptance tolerances.

## Coverage checklist

- [x] Platform vision and broad scope.
- [x] Requirements and quality attributes.
- [x] Command/task orchestration concept.
- [x] System discovery and adaptation concept.
- [x] Calculation and multidisciplinary engineering specification.
- [x] IC/chip, board, sensor and module analysis specification.
- [x] Virtual lab and simulation specification.
- [x] Existing project integration boundaries.
- [x] Governed self-evolution.
- [x] Engineering/3D specification and traceability documents.
- [ ] Full historical conversation audit; not proven exhaustive.
- [ ] Resolve ambiguous phrase “ยังเก็บคำสั่งไม่หนดครับ”.
- [ ] Owner selects first end-to-end use case.
- [ ] Confirm OS/platform priority and minimum hardware.
- [ ] Approve architecture, technology choices and vertical-slice criteria.
- [ ] Complete full candidate-source test/license/security audit.

## Status semantics

Documented means represented in specifications. Implemented means source exists. PASS requires executed evidence tied to an exact SHA and reproducible procedure. SKIPPED and UNKNOWN are never PASS. No overall requirement is complete solely because it appears in a document.


| CAD-PROFILE-002 | Through-hole loops in profile extrusion | CAD_NEUTRAL_PRIMITIVE_GEOMETRY | IMPLEMENTED — PR #52 merged at `1d1628175dafca3f5d4d3d6b5cf01e241ec75afa`; exact-head and post-merge CI PASS, 425 tests each. |


| MECH-SPATIAL-JOINT-001 | Spatial joint family reference validation | SPATIAL_JOINT_REFERENCE_VALIDATION_CONTRACT | IMPLEMENTED — PR #54 merged at `22bbf1714224095cfd652d6887130d26facef087`; exact-head and post-merge CI PASS, 452 tests each. 2D PLANAR mobility formulation remains deferred. |
