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
| R-016 | FeatureHistory suppression preserves source nodes and immutable revision history | FEATURE_HISTORY_SUPPRESSION_CONTRACT; FEATURE_HISTORY_REGENERATION_CONTRACT; CAD_GENERATOR_HTTP_API_CONTRACT | PASS end-to-end by PRs #163/#165/#166; exact merge SHA `34148fc359076567eaa4b931304f61f536a41779`, 854 Python tests and 5 Chromium E2E tests PASS on PR head and post-merge |
| R-017 | FeatureHistory Undo/Redo restores prior content without rewriting or deleting immutable revisions | FEATURE_HISTORY_UNDO_REDO_CONTRACT; CAD_GENERATOR_HTTP_API_CONTRACT | PASS — end-to-end bounded workflow merged by PRs #168–#171. PR #171 merge SHA `21bee045ea4d06aa07c7130f9123afaa64372638`: workflow-sanity PASS, python-tests PASS (865 tests), Chromium E2E PASS (6 tests) on exact PR head and post-merge SHA. |

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


| CAD-SKETCH-001 | Versioned 2D parametric sketch model with deterministic point/segment/arc references | [Parametric Sketch Constraint Contract](../design-3d/PARAMETRIC_SKETCH_CONSTRAINTS_CONTRACT.md); `parametric-sketch.schema.json` | PARTIAL — PR #90 baseline, PR #125 schema v1.1 ANGLE and PR #126 schema v1.2 circular arcs plus RADIUS/TANGENT are merged. Legacy v1.0/v1.1 reads are retained. Curved region conversion remains OPEN. |
| CAD-SKETCH-CONSTRAINT-001 | Geometric/dimensional equality constraints solved through bounded nonlinear solver | Same contract; `solve_parametric_sketch` | PARTIAL — 14 constraint kinds including signed ANGLE, RADIUS and endpoint TANGENT are merged. The solver remains bounded/local; no uniqueness/global convergence guarantee. Arc-to-arc tangent remains OPEN. |


| CAD-SKETCH-REGION-001 | Convert converged closed sketch loops (straight segments and circular arcs) to canonical planar regions with holes and nested islands | [Parametric Sketch Constraint Contract](../design-3d/PARAMETRIC_SKETCH_CONSTRAINTS_CONTRACT.md); `sketch_to_planar_regions` | IMPLEMENTED — straight loops PR #92; bounded circular-arc tessellation PR #128 merged at `30deb5290e4a84b8ce86848dcac21309d0b1ad95`; exact PR-head and post-merge CI PASS, 801 tests. Curves are polygonal approximations under explicit chord error; curved Boolean/B-rep remain OPEN. |
| CAD-FEATURE-HISTORY-001 | Versioned feature DAG, deterministic regeneration and source-to-output provenance | [Feature History and Regeneration Contract](../design-3d/FEATURE_HISTORY_REGENERATION_CONTRACT.md); `feature-history.schema.json`; `feature-history-revision.schema.json`; `feature_history_store.py`; `feature_artifact_store.py` | PARTIAL — PR #124 merged append-only SQLite source-document revisions with SHA-256 chain and optimistic concurrency; PR #131 merged strict artifact rehydration for all four feature kinds; PR #132 merged optional local SQLite artifact cache with algorithm-version-aware computation signatures and fail-closed integrity checks (post-merge 812 tests). Combined source-revision + artifact-cache reopen workflow, cache retention/backup, suppression and branch/merge editing remain OPEN. |


| CAD-PLANAR-TOPOLOGY-TOUCH-001 | Deterministic planar Boolean output for point-touching components without figure-eight boundaries | [CAD Boolean Point-Contact Topology Contract](../design-3d/CAD_BOOLEAN_POINT_CONTACT_CONTRACT.md) | IMPLEMENTED — PR #95 merged at `2eea0bdc9226c8ec3b3d5458e3902ee01b8314f0`; exact-head and post-merge CI PASS, 639 tests. Ambiguous branching and invalid hole topology remain fail-closed. |


| CAD-3MF-MESH-001 | Bounded 3MF Core import/export for validated watertight triangle meshes with source provenance | [3MF Core Mesh Interchange Contract](../engineering/3MF_CORE_MESH_INTERCHANGE_CONTRACT.md); `export_3mf` / `import_3mf` | IMPLEMENTED — PR #97 merged at `9b415f7c6be0f537feb67cbe86a911dc0ef5f662`; exact-head and post-merge CI PASS, 650 tests. One untransformed mesh object only; full 3MF and STEP remain OPEN. |


## Current sub-requirement status — post-PR #113 (2026-11-07)

| ID | Requirement | Evidence | Current state |
|---|---|---|---|
| CAD-BOOL-POINT-001 | Exact point-contact Boolean components | PR #95; point-contact contract | PARTIAL — point-only contacts supported; ambiguous branching/coincident incidence fails closed |
| CAD-SKETCH-001 | Parametric 2D sketch constraints | PR #90/#125; `parametric_sketch.py`; nonlinear solver | PARTIAL — 14 point/line/relational/arc constraint kinds including ANGLE, RADIUS and endpoint TANGENT are merged. Curved-loop region conversion and global uniqueness remain OPEN |
| CAD-FEATURE-001 | Feature DAG and deterministic regeneration | PR #93/#123; `feature_history.py`; `feature_history_store.py` | PARTIAL — allow-listed sketch/Boolean/extrusion/mesh pipeline, incremental in-memory reuse, and SQLite source-document revisions on an unmerged branch; durable artifact cache, suppression and branch history remain OPEN |
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


## Curved sketch region traceability — post-PR #128

| ID | Requirement | Evidence | Current state |
|---|---|---|---|
| CAD-SKETCH-REGION-001 | Convert converged closed line/arc sketch loops to canonical PlanarRegion records with holes and nested islands | PR #92; PR #128; `sketch_region.py`; `tests/test_sketch_region_curves.py` | IMPLEMENTED — PR #128 merge SHA `30deb5290e4a84b8ce86848dcac21309d0b1ad95`; exact-head and post-merge CI PASS, 801 tests. Circular arcs use deterministic chord-error-bounded polygon tessellation; this is not exact curved topology. |
| CAD-SKETCH-CURVE-002 | Preserve explicit curve approximation tolerance and fail-closed boundary topology | PR #128; `sketch_to_planar_regions(chord_error=...)` | IMPLEMENTED — default chord error 0.01 in sketch units; total tessellated boundary bounded by 2,048 edges; frame/unit identity, source sketch digest, loop closure and PlanarRegion topology validation retained. |
| CAD-CURVED-BOOLEAN-001 | Boolean operations over analytic curved boundaries | Future curved planar Boolean contract and kernel evaluation | OPEN — PR #128 creates polygonal approximations only; no exact curved Boolean or curved B-rep is claimed. |

Latest integration SHA: `30deb5290e4a84b8ce86848dcac21309d0b1ad95`. Main remains `96e75010716226037893155b9fd4b13410fb0d6f`; no promotion performed. Post-merge workflow #42374839944 passed both required jobs with 801 tests.


## Durable FeatureArtifact cache traceability — post-PR #132

| ID | Requirement | Evidence | Current state |
|---|---|---|---|
| CAD-FEATURE-ARTIFACT-REHYDRATE-001 | Reconstruct persisted feature artifacts only after schema, digest and geometry validation | PR #131; `FeatureArtifact.from_dict`; `SketchRegionConversionResult.from_dict` | IMPLEMENTED — all four allow-listed feature kinds have strict rehydration; mesh validation is recomputed and compared; tampering/unknown fields fail closed. |
| CAD-FEATURE-ARTIFACT-CACHE-001 | Reuse deterministic feature outputs across process restarts | PR #132; `SQLiteFeatureArtifactCache`; `regenerate_feature_history(artifact_cache=...)` | IMPLEMENTED — local SQLite cache keyed by history/feature/computation digest; exact algorithm versions participate in computation signatures; reopen and cache-reuse tests pass. |
| CAD-FEATURE-DURABLE-E2E-001 | Load a durable FeatureHistory revision and regenerate using a reopened artifact cache in a fresh process | PR #124, #132, #134; `tests/test_feature_history_durable_e2e.py` | IMPLEMENTED — PR #134 runs a child Python interpreter, reopens both SQLite stores, loads the exact source revision, reuses profile/extrusion/mesh with zero recomputation, preserves all artifact digests and confirms a watertight consistently oriented mesh; exact-head and post-merge CI PASS, 813 tests. |

Latest integration SHA: `f2cac75f7d4594ccb3a1ff70e56faa4ebe32f523`; main remains `96e75010716226037893155b9fd4b13410fb0d6f`. Post-merge workflow #42375907153 passed both required jobs with 812 tests.


## Durable FeatureHistory + cache fresh-process acceptance — post-PR #134

| ID | Requirement | Evidence | Current state |
|---|---|---|---|
| CAD-FEATURE-DURABLE-E2E-001 | Load a durable source revision and reuse persisted computed artifacts in a separate process | PR #124/#132/#134; `tests/test_feature_history_durable_e2e.py` | IMPLEMENTED — subprocess reopens both SQLite databases, loads revision 1, reuses all three feature artifacts with zero recomputation, verifies identical SHA-256 outputs and watertight/orientation checks. Exact-head and post-merge CI pass, 813 tests. |
| CAD-GEN-SERVICE-001 | Provide a revision-aware CAD generator application service over versioned FeatureHistory and regeneration | PR #136; `CADGeneratorService`; `CADGeneratorRun`; `CAD_GENERATOR_SERVICE_CONTRACT.md` | IMPLEMENTED — strict snapshot/typed save, revision selection, local artifact-cache regeneration and provenance response; public exports and service tests; exact-head and post-merge CI PASS, 817 tests. No transport/network listener is included. |
| CAD-GEN-HTTP-API-001 | Provide a governed HTTP/CLI transport for the CAD generator service | Future transport contract and integration tests | OPEN — authentication, authorization, request limits, audit, cancellation, structured errors and loopback-only binding must be designed and tested before any listener is enabled. |

Latest integration SHA: `e4a1add528e4fd77c88df96d428ff629e2f4b655`; main remains `96e75010716226037893155b9fd4b13410fb0d6f`. Post-merge workflow #42376427587 passed both required jobs with 813 tests.


## CAD Generator service traceability — post-PR #136

| ID | Requirement | Evidence | Current state |
|---|---|---|---|
| CAD-GEN-SERVICE-001 | Revision-aware application service for durable CAD history and regeneration | PR #136; `cad_generator_service.py`; public exports; service contract | IMPLEMENTED — strict snapshot save, optimistic revision writes, exact revision reads, local cache-backed regeneration and provenance-bearing response. Exact-head and post-merge CI PASS, 817 tests. |
| CAD-GEN-HTTP-API-001 | Governed local HTTP transport for revisioned CAD generator requests | PR #138; `cad_generator_http_api.py`; `CAD_GENERATOR_HTTP_API_CONTRACT.md`; `tests/test_cad_generator_http_api.py` | IMPLEMENTED — explicit-start IPv4 loopback-only server, bearer auth, strict JSON/body/time bounds, immutable revision save/read/list/regenerate, SQLite append-only audit hash chain. Exact-head and post-merge CI PASS, 822 tests. Remote access, TLS, rate limiting and browser session controls remain OPEN. |

Latest integration SHA: `ab0006c1ead3e6848f90e30c804d38a3029218f3`; main remains `96e75010716226037893155b9fd4b13410fb0d6f`. Post-merge workflow #42376951014 passed both required jobs with 817 tests.


## CAD Generator HTTP API traceability — post-PR #138

| ID | Requirement | Evidence | Current state |
|---|---|---|---|
| CAD-GEN-HTTP-API-001 | Governed local transport for versioned CAD Generator operations | PR #138; `cad_generator_http_api.py`; `CAD_GENERATOR_HTTP_API_CONTRACT.md`; HTTP integration tests | IMPLEMENTED — loopback-only explicit-start HTTP server; bearer token; Host/Origin/peer validation; strict JSON; bounded request size/time; revision save/read/list/regenerate; append-only SQLite audit chain. Exact-head and post-merge CI PASS, 822 tests. |
| CAD-GEN-WORKBENCH-001 | Local FeatureHistory revision workbench integrated with the API | PR #140; packaged HTML/CSS/JS; HTTP static-asset integration tests | IMPLEMENTED — token-in-memory local UI supports strict JSON editing/paste, immutable revision save, list/load and exact-revision regeneration. Exact-head and post-merge CI PASS, 823 tests. |
| CAD-VISUAL-SKETCH-001 | Interactive visual 2D sketch editor with validated geometry and constraints | Future browser interaction and geometry acceptance tests | OPEN — current UI is a JSON/revision workbench; no graphical point/segment/arc editor or CAD viewport is claimed. |

Latest integration SHA: `674b6a52c725b6e3f4b4e083b602aab3a138104e`; main remains `96e75010716226037893155b9fd4b13410fb0d6f`. Post-merge workflow #42380918862 passed both required jobs with 822 tests.


## CAD Generator UI traceability — post-PR #140

| ID | Requirement | Evidence | Current state |
|---|---|---|---|
| CAD-GEN-WORKBENCH-001 | Local FeatureHistory revision workbench | PR #140; static assets; same-origin HTTP integration tests | IMPLEMENTED — JSON snapshot editing/paste, optimistic revision save, revision list/load and exact revision regeneration. Token memory-only; CSP/no CORS. Exact-head and post-merge CI PASS, 823 tests. |
| CAD-VISUAL-SKETCH-001 | Interactive visual 2D sketch authoring | PR #142; SVG canvas; polygon template endpoint; `tests/test_cad_generator_templates.py`; HTTP integration tests | PARTIAL — bounded straight-edge polygon editor with click/numeric input, undo/clear, fixed X/Y constraints and validated Sketch → Extrusion → Mesh generation. Exact-head and post-merge CI PASS, 832 tests. Arcs, holes, automatic/dimensional constraints, drag solver and general sketch topology remain OPEN. |
| CAD-VISUAL-VIEWPORT-001 | Source-linked 3D mesh viewport and validation display | Future mesh renderer and browser integration tests | OPEN — the UI returns mesh artifacts/provenance as JSON but does not yet render a 3D viewport. |

Latest integration SHA: `f3abe346a259f2f3f3ed767889dba32be6a284b9`; main remains `96e75010716226037893155b9fd4b13410fb0d6f`. Post-merge workflow #42381936401 passed both required jobs with 823 tests.


## Visual polygon sketch traceability — post-PR #142

| ID | Requirement | Evidence | Current state |
|---|---|---|---|
| CAD-VISUAL-SKETCH-001 | Interactive visual 2D sketch authoring | PR #142; SVG canvas; polygon template builder; template API integration tests | PARTIAL — bounded straight-edge polygon editor with click/numeric input, undo/clear, fixed coordinate constraints and Sketch → Extrusion → Mesh FeatureHistory generation. Exact-head and post-merge CI PASS, 832 tests. |
| CAD-VISUAL-VIEWPORT-001 | Source-linked 3D mesh viewport and validation display | PR #144; renderMeshPreview; exact MESH artifact vertices/triangles, source revision, content/computation digests and backend validation flags | PARTIAL — static isometric SVG preview is rendered from the exact returned MESH artifact, with bounded 10,000-vertex/5,000-triangle rendering and validation warnings. Orbit/pan/zoom, selection, sectioning, B-rep editing and assembly view remain OPEN. |

Latest integration SHA: `da5b34182396c485760aa1940ab2623d52d89cbc`; main remains `96e75010716226037893155b9fd4b13410fb0d6f`. Post-merge workflow #42383384086 passed both required jobs; test-count detail was not captured.


## CAD mesh preview evidence — PR #144

| ID | Requirement | Evidence | Current state |
|---|---|---|---|
| CAD-MESH-PREVIEW-001 | Display generated mesh with source/artifact provenance and backend validation | PR #144; exact MESH FeatureArtifact; static SVG renderer; API/UI wiring assertions; exact-head run #42383293137; post-merge run #42383384086 | IMPLEMENTED — static isometric preview only, capped at 10,000 vertices and 5,000 triangles. It displays source revision, mesh counts, content/computation digests and backend validation flags/issues. It is not a certification or general CAD viewport. |
| CAD-VIEWPORT-INTERACTION-001 | Interactive orbit/pan/zoom mesh viewport | Future bounded interaction and browser regression tests | OPEN — static projection only; no interactive camera controls. |

Latest integration SHA: da5b34182396c485760aa1940ab2623d52d89cbc; main remains 96e75010716226037893155b9fd4b13410fb0d6f. Post-merge workflow #42383384086 passed both required jobs.


## B-rep polygonal mesh triangulation — PR #182

| ID | Requirement | Primary specification / implementation | Current state |
|---|---|---|---|
| CAD-BREP-MESH-TRIANGULATION-001 | Convert validated single-shell planar polygonal B-rep faces, including one or more inner loops, into a deterministic watertight triangle mesh without adding geometric vertices | [Faceted B-rep Polygonal Mesh Triangulation Contract](../design-3d/FACETED_BREP_MESH_TRIANGULATION_CONTRACT.md); `src/universal_platform/engineering/brep.py`; `mesh._triangulate_profile_region`; `tests/test_faceted_brep.py` | IMPLEMENTED — PR #182 merged at `9c84d4d94030c0e3084d7a288064491d8160a71f` (exact PR head `c4c1a5c642096f2c030982c567fe308cb2df07e4`). Exact PR-head workflow #42459969975: workflow-sanity PASS, Python 894 PASS; post-merge workflow #42460044330: workflow-sanity PASS, Python 894 PASS. Chromium E2E SKIPPED/not triggered (no UI change). Multiple shells and general 3D Boolean remain OPEN. |

| CAD-BREP-MULTISHELL-001 | Represent one polygonal outer shell with disjoint, strictly-contained cavity shells and deterministic subtractive mesh orientation | [Faceted B-rep Multi-Shell Solid Contract](../design-3d/FACETED_BREP_MULTISHELL_SOLID_CONTRACT.md); `schemas/geometry/faceted-brep-multishell-solid.schema.json`; `src/universal_platform/engineering/brep_multishell.py`; `tests/test_brep_multishell.py` | IMPLEMENTED — PR #184 merged at `db7ce54efe3d9334b87b3902a14b089b6ce67ebd` (exact PR head `850e521cd3499ede4e8a00a5cb1698cee32347d0`). PR workflow #42461224579: 902 PASS; push workflow #42461220462: 902 PASS; post-merge workflow #42461294867: 902 PASS. Browser E2E not triggered (no UI change), not counted as PASS. Nested cavity islands, general 3D Boolean and multi-shell STEP/AP242 remain OPEN. |

| CAD-BREP-MULTISHELL-REFERENCE-001 | Validate multi-shell cavity composition for non-axis-aligned and concave polygonal shells | [Faceted B-rep Multi-Shell Solid Contract](../design-3d/FACETED_BREP_MULTISHELL_SOLID_CONTRACT.md); `tests/test_brep_multishell.py` | IMPLEMENTED — PR #186 merged at `7b02337fb6bfe678ba950135c913b910c6e5fd40` (exact PR head `4d8f253078ccfc202e275db9494c25d7f0174227`). PR workflow #42461621856: 904 PASS; post-merge workflow #42461678728: 904 PASS. Separate push-event run for PR head UNKNOWN/not returned. Covers rotated 45-degree box cavity and concave L-prism cavity. |
| CAD-BREP-MULTISHELL-FAILCLOSED-001 | Reject cavity/outer boundary contact and fail closed when complete shell-intersection classification is UNKNOWN | [Faceted B-rep Multi-Shell Solid Contract](../design-3d/FACETED_BREP_MULTISHELL_SOLID_CONTRACT.md); `tests/test_brep_multishell.py` | IMPLEMENTED — PR #188 merged at `3e51a20339ddf5d9a4bcecbe94ef8160eb9fae2f` (exact PR head `de8403ce210a4d283d4163401338cf0370c811de`). PR workflow #42461990534: 906 PASS; post-merge workflow #42462067390: 906 PASS. Separate push-event run for PR head UNKNOWN/not returned. Touching boundary and injected UNKNOWN intersection status are rejected. |
| CAD-BREP-MULTISHELL-AUDIT-001 | Keep multi-shell implementation status, traceability and repository audit synchronized with exact-SHA evidence | [Post-PR #189 Repository Audit](../audit/REPOSITORY_AUDIT_2026-11-08_POST_PR189.md); [Multi-Shell Solid Contract](../design-3d/FACETED_BREP_MULTISHELL_SOLID_CONTRACT.md) | IMPLEMENTED — PR #189 merged at `050d18d863653103fb62d6d39426c8c255a8f99c`. Exact PR-head push #42462189154 and PR #42462199774 each passed 906 tests; post-merge workflow #42462267653 passed 906 tests. |
| CAD-BREP-BOOLEAN-MULTISHELL-001 | Execute exact-grid Boolean operations on axis-aligned multi-shell box inputs and emit cavity-aware result solids | [Axis-Aligned Multi-Shell B-rep Boolean Contract](../design-3d/AXIS_ALIGNED_MULTISHELL_BREP_BOOLEAN_CONTRACT.md); `schemas/geometry/brep-multishell-boolean-result.schema.json`; `src/universal_platform/engineering/brep_boolean.py`; `tests/test_brep_multishell_boolean.py` | IMPLEMENTED — PR #191 merged at `20e03675ec1000bd2bbcfaf251df4790305f2c0c` (exact PR head `9e069f85e840147d541491a7b424bfd7eef8de1c`). Push workflow #42462848667: 914 PASS; PR workflow #42462853863: 914 PASS; post-merge workflow #42462960964: 914 PASS. Limited to axis-aligned box outer/cavity components, 2–16 inputs and 32,768 grid cells; not general 3D Boolean. |

## Current CAD Boolean traceability snapshot — post-PR #212

| Requirement | Current implementation evidence | Status | Explicit remaining boundary |
|---|---|---|---|
| Exact global topology | PRs #200–#202; `global_triangle_arrangement.py` | PASS for bounded global identity, adjacency, T-junction detection and edge subdivision | Does not certify arbitrary global arrangement completeness or heal degenerate input |
| Independent exact fragment coverage | PRs #203 and #212; `triangle_coverage_oracle.py` | PASS for exact coplanar per-source partitions | No global proof for every multi-solid topology; exact 3D coplanarity is required |
| Material classification | PR #204; `material_classification.py` | PASS for bounded closed-mesh point classification | Nested material islands and broader shell semantics remain open |
| Boolean boundary selection | PRs #205 and #211; `boolean_boundary_selection.py` | PASS for supported arrangement cells and two-sided witness agreement | Unsupported/ambiguous degeneracies fail closed |
| Shell assembly | PR #206; `boolean_shell_assembly.py` | PASS for bounded connected outer/cavity shell output | Binary64 output rejects non-lossless rational coordinates; nested positive islands unsupported |
| Automatic multi-mesh arrangement and generator execution | PRs #207, #210, #211; `faceted_boolean_arrangement.py`, `CADGeneratorService.execute_faceted_boolean` | PASS for tested non-coplanar UNION volume 15 and coplanar-overlap UNION volume 12 | Not unrestricted arbitrary faceted Boolean; no general HTTP/browser Boolean endpoint |
| Rational input budgets | PR #213 merge `d1289efdb71a1172beb88665baf09b4620f0cdc5`; exact head `093db080ebbb2a04431bd6254c889ceb53d8afed` | PASS for exact-head Python/workflow-sanity | Post-merge workflow #42485255693 workflow-sanity/Python tests PASS |

**Overall CAD-BREP-BOOLEAN-001:** PARTIAL / INCOMPLETE. The bounded test cases pass; unsupported contact/tangency/branching, broader adversarial geometry and rational-coordinate B-rep output remain open.

**Pinned evidence snapshot:** integration `7fd78fa40886694bd46cfb6a61f60c3f716033f2`; main `96e75010716226037893155b9fd4b13410fb0d6f` unchanged.


| Coplanar contact isolation | PR #215 merge `1ce59cab30ccfa18d8a8d72022706ffd9d9cec0b`; exact head `171583c852994aba3f61f712d48deabd0aab7cca` | PASS for exact-head Python/workflow-sanity | Post-merge workflow-sanity and Python tests PASS on exact merge SHA `1ce59cab30ccfa18d8a8d72022706ffd9d9cec0b`. Isolated contacts on active planes are rejected unless fully covered by overlap closure. |


## CAD exact-output requirement — 2026-11-08

| ID | Requirement | Primary document | Current state |
|---|---|---|---|
| CAD-BREP-RATIONAL-OUTPUT-001 | Preserve exact rational intersection coordinates in a versioned faceted-solid output without rounding or tolerance welding; emit legacy binary64 output only when every coordinate round-trips losslessly | [Exact Rational Faceted Output Contract](../design-3d/EXACT_RATIONAL_FACETED_OUTPUT_CONTRACT.md) | DESIGN ONLY — no rational output model is implemented. Current shell assembly correctly rejects non-binary-rational coordinates. |

### Current bounded Boolean evidence — post-PR #219

- PR #218 merge SHA `f2bbaf2f4868412020051c58762e2337af3a1a25`: exact-head workflow-sanity, Python tests and Chromium E2E PASS; post-merge workflow-sanity, Python tests and Chromium E2E PASS.
- PR #219 merge SHA `7a0d2a21d05709ccfead7f95e57349310c878a58`: exact-head workflow-sanity/Python PASS; post-merge workflow-sanity/Python PASS. The topology budget now charges all three edges per raw fragment against every global vertex.
- PR #217 exact head `921de7c2013183abd770acde714adc3b7680738b` passed workflow-sanity and Python tests and merged at `972f5d5787cb0f70c3f3200dd942f6b8329f08bf`; post-merge workflow-sanity PASS and Python tests IN_PROGRESS at this documentation snapshot.
- Main remains `96e75010716226037893155b9fd4b13410fb0d6f` and unchanged.

**Current CAD verdict:** PASS for the bounded named cases and implemented fail-closed gates; PARTIAL / INCOMPLETE for arbitrary faceted Boolean. The rational-output profile is a required follow-on.
