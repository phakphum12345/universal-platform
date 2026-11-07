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


| CAD-PLANAR-BOOLEAN-001 | Pairwise and set Boolean operations over validated PlanarRegion inputs, with multiple components, holes and bounded point-contact handling | CAD_GENERAL_PLANAR_TOPOLOGY_CONTRACT; CAD_BOOLEAN_POINT_CONTACT_CONTRACT; PlanarRegionBooleanResult schemas | IMPLEMENTED — PR #84 merge SHA `1b75e2dab5b64d2d089e410bba02187d28772193`; PRs #84/#87/#95 merged with exact-head and post-merge CI PASS (580/600/639 tests respectively). Point-only contacts are represented as separate components. Ambiguous branching, coincident outgoing directions, unbalanced incidence and invalid hole topology remain fail-closed; this is not a general 3D Boolean kernel. |


| CAD-PLANAR-SET-001 | Set Boolean operations over two or more PlanarRegion inputs | PlanarRegion Set Boolean contract / result schema | IMPLEMENTED — PR #87 merged at `316e0d6c3166470bc839d3c880a38720bd854577`; PR/push and post-merge CI PASS, 600 tests. |
| CAD-PLANAR-EXTRUSION-001 | Convert validated PlanarRegion with holes into an analytic extruded solid and validated mesh | PlanarRegion Extrusion Result schema; CAD-neutral Primitive Geometry Contract | IMPLEMENTED — PR #88 merged at `bd9379617f1bc88772137a6e9886e33cb0bed3cb`; PR/push and post-merge CI PASS, 607 tests. |


| CAD-SKETCH-001 | Versioned 2D parametric sketch model with deterministic point/segment references | [Parametric Sketch Constraint Contract](../design-3d/PARAMETRIC_SKETCH_CONSTRAINTS_CONTRACT.md); `parametric-sketch.schema.json` | IMPLEMENTED — PR #90 merged at `e2d631b49910e3d7f05fea6337742fd87385fb81`; exact PR-head and post-merge CI PASS, 618 tests. Bounded points/straight segments only. |
| CAD-SKETCH-CONSTRAINT-001 | Initial geometric/dimensional equality constraints solved through bounded nonlinear solver | Same contract; `solve_parametric_sketch` | IMPLEMENTED — eight constraint kinds; exact PR-head and post-merge CI PASS, 618 tests. No uniqueness/global convergence guarantee; unsupported constraint families remain OPEN. |


| CAD-SKETCH-REGION-001 | Convert converged closed straight-line sketch loops to canonical planar regions with holes and nested islands | [Parametric Sketch Constraint Contract](../design-3d/PARAMETRIC_SKETCH_CONSTRAINTS_CONTRACT.md); `sketch_to_planar_regions` | IMPLEMENTED — PR #92 merged at `ecc5b7acebdfd48ccf07e64c53f169caf268193a`; exact-head and post-merge CI PASS, 627 tests. Curves and touching/branching topology remain unsupported. |
| CAD-FEATURE-HISTORY-001 | Versioned feature DAG, deterministic regeneration and source-to-output provenance | [Feature History and Regeneration Contract](../design-3d/FEATURE_HISTORY_REGENERATION_CONTRACT.md); `feature-history.schema.json` | IMPLEMENTED — PR #93 baseline plus incremental in-memory regeneration in this feature PR. Cache signatures bind canonical parameters, input artifact digests and sketch solver options; unchanged nodes reuse prior artifacts and changed branches invalidate descendants. Durable persistence/cache, suppression and branch history remain OPEN. |


| CAD-PLANAR-TOPOLOGY-TOUCH-001 | Deterministic planar Boolean output for point-touching components without figure-eight boundaries | [CAD Boolean Point-Contact Topology Contract](../design-3d/CAD_BOOLEAN_POINT_CONTACT_CONTRACT.md) | IMPLEMENTED — PR #95 merged at `2eea0bdc9226c8ec3b3d5458e3902ee01b8314f0`; exact-head and post-merge CI PASS, 639 tests. Ambiguous branching and invalid hole topology remain fail-closed. |


| CAD-3MF-MESH-001 | Bounded 3MF Core import/export for validated watertight triangle meshes with source provenance | [3MF Core Mesh Interchange Contract](../engineering/3MF_CORE_MESH_INTERCHANGE_CONTRACT.md); `export_3mf` / `import_3mf` | IMPLEMENTED — PR #97 merged at `9b415f7c6be0f537feb67cbe86a911dc0ef5f662`; exact-head and post-merge CI PASS, 650 tests. One untransformed mesh object only; full 3MF and STEP remain OPEN. |


## Current sub-requirement status — post-PR #113 (2026-11-07)

| ID | Requirement | Evidence | Current state |
|---|---|---|---|
| CAD-BOOL-POINT-001 | Exact point-contact Boolean components | PR #95; point-contact contract | PARTIAL — point-only contacts supported; ambiguous branching/coincident incidence fails closed |
| CAD-SKETCH-001 | Parametric 2D sketch constraints | PR #90; `parametric_sketch.py`; nonlinear solver | PARTIAL — eight point/line constraint kinds; no arcs/splines, angle/tangent families or global uniqueness guarantee |
| CAD-FEATURE-001 | Feature DAG and deterministic regeneration | PR #93; `feature_history.py` | PARTIAL — allow-listed sketch/Boolean/extrusion/mesh pipeline; no persistence/incremental recompute/suppression |
| CAD-BREP-001 | General B-rep and 3D Boolean kernel | Future geometry kernel work | OPEN — STEP faceted mesh interchange is not B-rep modeling |
| CAD-XCHG-001 | STEP and 3MF interchange | PR #97 and #99 | PARTIAL — bounded 3MF Core single object and STEP AP214 faceted triangle shell; no general AP242/assemblies |
| CAD-GEN-001 | End-to-end CAD generator UI/API/persistence | CAD design and feature pipeline contracts | OPEN — core library exists; integrated authoring UI/API and durable documents not verified |
| HW-EDA-001 | EDA interchange and library model | Hardware schematic/driver contracts | PARTIAL — connectivity/SVG/static ERC only; native EDA interchange and library semantics open |
| HW-BOM-001 | Datasheet constraints, BOM/footprint reconciliation and circuit simulation | Hardware design verification requirements | OPEN — not implemented as a validated end-to-end flow |
| PHY-REG-001 | Central multi-method physics registry | PR #110; `engineering/physics.py` | PARTIAL — registry and three analytical built-ins |
| PHY-VALID-001 | Domain validation, numerical/simulation methods and uncertainty | Physics first-principles contract | OPEN — no complete cross-domain reference/convergence/uncertainty suite |
| RT-001 | Typed central resource registry and lifecycle | PR #107; `runtime/resources/registry.py` | PARTIAL — process-local |
| RT-002 | Resource metrics and snapshot collection | PR #107; `runtime/resources/collector.py` | PARTIAL — provider/platform dependent; GPU/CPU utilization not claimed |
| RT-003 | Quotas and leases | PR #107; `runtime/resources/allocator.py` | PARTIAL — in-memory logical quota, no OS enforcement/distributed leases |
| RT-004 | Bounded logs and recovery evidence | PR #107 and #113 | PARTIAL — bounded files, local JSONL, local lock and unkeyed hash chain |
| RT-005 | Recovery lifecycle and trusted process supervision | PR #107; `runtime/recovery`, `runtime/supervisor.py` | PARTIAL — trusted allow-listed workers only; no sandbox |
| RT-006 | Adapter discovery and routing | PR #107 and #113; `runtime/adapters/catalog.py` | PARTIAL — in-process routing; no distributed route control |
| RT-007 | Threshold resource health monitoring | PR #113; `runtime/health/monitor.py` | PARTIAL — caller-defined thresholds; UNKNOWN for missing/wrong units; no auto-repair |
| RT-008 | Secure module runtime and platform API/CLI/UI | Future integration work | OPEN — OS sandbox, durable governance and full product integration not implemented |

Latest integration SHA `50b5ff50e52e9f9f83d1b33030875b53ee7702e2`; post-merge workflow #42279521637 passed 732 tests. Integration is 253 ahead / 0 behind main; main remains unchanged. Acceptance requires source, schemas, tests, exact-SHA CI and explicit limits for every requirement; documentation alone is not PASS.


## B-rep topology and bounded 3D Boolean — PR #117/#118

| ID | Requirement | Primary specification / implementation | Current state |
|---|---|---|---|
| CAD-BREP-TOPOLOGY-001 | Versioned closed faceted B-rep shell with mesh bridge and exact topology validation | `docs/design-3d/FACETED_BREP_TOPOLOGY_CONTRACT.md`; `schemas/geometry/faceted-brep-solid.schema.json`; `src/universal_platform/engineering/brep.py`; `tests/test_brep.py` | IMPLEMENTED — PR #117 merged at `2dbddba4899246c1c75a169224154b9d8ec21402`; exact-head and post-merge CI PASS, 742 tests. Single connected shell of triangular planar faces only; n-gons, inner loops, multiple shells and shell healing remain OPEN. |
| CAD-BREP-BOOLEAN-AXIS-001 | Deterministic 3D Boolean operations for bounded axis-aligned box B-reps | `docs/design-3d/AXIS_ALIGNED_BREP_BOOLEAN_CONTRACT.md`; `schemas/geometry/brep-boolean-result.schema.json`; `src/universal_platform/engineering/brep_boolean.py`; `tests/test_brep_boolean.py` | IMPLEMENTED — PR #118 merged at `0b7e9b4a649a8b3dcf4512cd5172640979115ed4`; exact-head and post-merge CI PASS, 755 tests. Limited to 2–16 axis-aligned box shells and 32,768 grid cells; arbitrary faceted solids, rotated/curved geometry and enclosed cavities remain OPEN. |
