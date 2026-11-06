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


| MECH-SPATIAL-JOINT-001 | Spatial joint family reference validation | SPATIAL_JOINT_REFERENCE_VALIDATION_CONTRACT | IMPLEMENTED — PR #54 merged at `22bbf1714224095cfd652d6887130d26facef087`; exact-head and post-merge CI PASS, 452 tests each. Explicit 2D PLANAR mobility is implemented separately by PR #56. |


| MECH-PLANAR-MOBILITY-001 | Explicit plane-frame geometric mobility | PLANAR_PLANE_FRAME_MOBILITY_CONTRACT | IMPLEMENTED — PR #56; PR #56 merged at `8335515b31a89efc4cacb70cf9c2e3aeb4ae16d4`. Exact PR head `8b76f89687c4685c66fee5f8bc9cd045bd589abe`; run #459 (`42197011073`) passed `workflow-sanity` and `python-tests` with 462 tests. Exact post-merge run #461 (`42197156442`) on the merge SHA passed both jobs with 462 tests. |


| CAD-PLANAR-BOOLEAN-001 | Pairwise Boolean operations over validated PlanarRegion inputs, with multiple output components and holes | CAD_GENERAL_PLANAR_TOPOLOGY_CONTRACT; PlanarRegionBooleanResult schema | IMPLEMENTED — PR #84 merged at `1b75e2dab5b64d2d089e410bba02187d28772193`; exact PR-head and post-merge CI PASS, 580 tests each. Pairwise only; 256 total input-edge limit; point-touching/branching output fails closed; region-set aggregation and B-rep remain PLANNED. |


| CAD-PLANAR-SET-001 | Set Boolean operations over two or more PlanarRegion inputs | PlanarRegion Set Boolean contract / result schema | IMPLEMENTED — PR #87 merged at `316e0d6c3166470bc839d3c880a38720bd854577`; PR/push and post-merge CI PASS, 600 tests. |
| CAD-PLANAR-EXTRUSION-001 | Convert validated PlanarRegion with holes into an analytic extruded solid and validated mesh | PlanarRegion Extrusion Result schema; CAD-neutral Primitive Geometry Contract | IMPLEMENTED — PR #88 merged at `bd9379617f1bc88772137a6e9886e33cb0bed3cb`; PR/push and post-merge CI PASS, 607 tests. |


| CAD-SKETCH-001 | Versioned 2D parametric sketch model with deterministic point/segment references | [Parametric Sketch Constraint Contract](../design-3d/PARAMETRIC_SKETCH_CONSTRAINTS_CONTRACT.md); `parametric-sketch.schema.json` | IMPLEMENTED — PR #90 merged at `e2d631b49910e3d7f05fea6337742fd87385fb81`; exact PR-head and post-merge CI PASS, 618 tests. Bounded points/straight segments only. |
| CAD-SKETCH-CONSTRAINT-001 | Initial geometric/dimensional equality constraints solved through bounded nonlinear solver | Same contract; `solve_parametric_sketch` | IMPLEMENTED — eight constraint kinds; exact PR-head and post-merge CI PASS, 618 tests. No uniqueness/global convergence guarantee; unsupported constraint families remain OPEN. |
