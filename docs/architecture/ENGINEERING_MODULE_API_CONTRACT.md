# Engineering Module API Contract

**Status:** PROPOSED invocation contract; metadata registry subset implemented in PR #39

## 1. Purpose

Define the stable boundary between UEIC, domain modules, CAD/design tools, solvers, simulation adapters and evidence services.

## 2. Required operations

- describe_module
- validate_inputs
- estimate_resources
- prepare_model
- solve_or_simulate
- validate_outputs
- explain_result
- emit_evidence
- cancel_operation

The actual transport and serialization format remain OPEN until a vertical slice is tested.

## 3. Request envelope

The implemented Python ModuleRequest (PR #41) validates stable module/operation IDs, MAJOR.MINOR schema versions, a non-empty request ID, immutable assumptions/source references/permissions, finite non-negative resource limits, and recursively JSON-compatible input data. Resource-limit keys are stable identifiers; callers should use unit-bearing names where applicable (for example, memory_bytes or time_seconds). The envelope does not yet include task identity, typed input-unit maps, coordinate-frame maps, constraints, requested precision or cancellation context.

## 4. Response envelope

The implemented Python ModuleResponse (PR #41) validates request identity, operational status, JSON-compatible outputs, immutable warnings/assumptions/limitations/evidence references and machine-readable error codes. Operational status is ACCEPTED / REJECTED / RUNNING / COMPLETED / CANCELLED / ERROR; it is not an engineering evidence status. Model/solver versions, units, uncertainty, source lineage and execution metadata remain future extensions.

## 5. Status semantics

Use PASS / FAIL / SKIPPED / UNKNOWN for evidence checks. Operational responses may use ACCEPTED / REJECTED / RUNNING / COMPLETED / CANCELLED / ERROR. Never equate COMPLETED with engineering PASS.

## 6. Security and authority

Modules receive least privilege. A calculation module cannot acquire hardware-control permissions. External network, file modification, procurement, fabrication and deployment are separate permission scopes.

## 7. Compatibility

Contracts are versioned. Breaking changes require a new major schema version, migration notes and compatibility tests. Unknown fields must not silently change safety-critical meaning.

## 8. Acceptance criteria

- [ ] Module operations and schemas are versioned.
- [ ] Permissions are operation-specific.
- [ ] Errors and cancellation are explicit.
- [ ] Result lineage is preserved.
- [ ] Completion and verification are separate.


## Implemented metadata registry subset (PR #39)

The implementation adds immutable `ModuleManifest` and `ModuleOperation` records plus an in-memory `ModuleRegistry`. It validates stable IDs, semantic module versions, MAJOR.MINOR operation schema versions, explicit license/maturity, operation permission subsets and a restricted execution classification. Dependency ordering is deterministic and fails closed for missing dependencies or cycles. Snapshots are JSON-compatible and sorted.

This is a metadata registry only. It does not load or invoke code, enforce permissions, isolate processes, or provide a runtime plugin system.


### PR #39 evidence

- Final PR head: `4c07fb980afa19a36f3696d5ceed7eb35105fcc3`; run #311 (`42167103639`): 308 tests passed.
- Merge commit: `cd552e5fa96fa21ab21a437b0103b3a195542dbc`.
- Post-merge run #312 (`42167199845`) on the exact merge SHA: 308 tests passed.


## Validated request/response envelope implementation (PR #41)

ModuleRequest and ModuleResponse are immutable data-contract records. Nested JSON objects and arrays are detached and frozen on construction; `to_dict()` returns deterministic JSON-compatible snapshots. Non-finite numbers, unsupported Python objects, malformed identifiers/schema versions, invalid resource limits, duplicate tuple metadata and invalid status/error-code combinations fail closed.

The envelopes themselves do not load modules, execute operations, enforce permissions, or grant authority. Runtime invocation is implemented separately by host-grant-gated ModuleRuntime dispatch (PR #235) and supervised WorkerIPC dispatch (PR #254). These are trusted host-controlled execution paths, not arbitrary plugin loading or a general OS sandbox; durable lease recovery and security acceptance are tracked separately under WP-09G.


## Evidence and provenance contract

The evidence model is implemented in `provenance.py`. SourceRef validates optional SHA-256 content hashes and preserves revision, locator and license. EvidenceRecord validates evidence kind/status, non-empty statements, unique source locators, timezone-aware ISO-8601 timestamps and JSON-safe immutable metadata. Its `to_dict()` method returns a deterministic JSON-compatible snapshot.

`evaluate_evidence_gate()` treats every supplied record as required. FAIL takes precedence over UNKNOWN, which takes precedence over SKIPPED; PASS is returned only when at least one record exists and every record is PASS. An empty set is UNKNOWN. This aggregate does not infer physical validity or certification.


## Coordinate-frame interchange (PR #43)

RigidTransform and FrameGraph use versioned v1.0 JSON-compatible snapshots. Transform records identify source/destination frames, a proper 3×3 rotation and translation with an explicit length unit. FrameGraph snapshots sort frame IDs and edges deterministically and reject duplicate IDs, undeclared edge endpoints, multiple parents, cycles and mixed length units. This forest is a coordinate utility, not an assembly constraint solver. Mixed-unit graphs require explicit conversion and are not supported implicitly.


## Frame-bound spatial values (PR #45)

FramedPoint3 and FramedVector3 bind Vec3 values to a stable frame ID and explicit length unit. Their v1.0 JSON snapshots distinguish POINT from VECTOR. Conversion uses FrameGraph and requires matching length units. Points apply rotation and translation; displacement vectors apply rotation only. These types represent spatial coordinates/displacements, not arbitrary force or velocity vectors.


## CAD-neutral primitive geometry (PR #48)

The engineering package exports BoxSolid, CylinderSolid, FramedBounds3 and PrimitiveGeometryModel. The model uses FrameGraph to transform bounds and Quantity to report SI volume/surface area. It is a primitive analytic layer, not a CAD kernel.


## Profile extrusion (PR #49)

The primitive geometry layer also exports Vec2 and ExtrudedProfileSolid. PR #49 introduced straight-edged extrusion, PR #52 added polygonal through-hole loops, and PR #58 added bounded circular-arc edges and curved through-holes with analytic area/perimeter/volume/surface-area calculations. Curved topology validation uses deterministic arc tessellation; this is not an exact B-rep or general 3D Boolean kernel.


## CAD Generator application service (PR #136)

A transport-neutral in-process `CADGeneratorService` now provides the CAD-specific application boundary over versioned FeatureHistory documents, the local SQLite revision store, the validated FeatureArtifact cache and the allow-listed regeneration engine. The service supports typed and strict snapshot writes, explicit revision reads, regeneration and a provenance-bearing response envelope. It is exported from `universal_platform.engineering`.

The service remains transport-neutral and does not itself grant network authority. PR #138 adds the authenticated loopback-only HTTP transport; PR #140 adds the same-origin local FeatureHistory workbench; PR #142 adds a bounded straight-polygon sketch authoring workflow. Any additional listener or remote access must define authentication, authorization, request-size/time limits, audit evidence, cancellation, structured errors and a separately reviewed network boundary.


## CAD Generator local HTTP transport (PR #138)

The revision-aware `CADGeneratorService` is now exposed through an explicit-start, same-origin local HTTP adapter. The API provides authenticated health, immutable FeatureHistory save, revision list/read and exact-revision regeneration. It binds only to IPv4 loopback (`127.0.0.1`) and uses port 0 by default for OS-selected dynamic allocation. The request boundary validates bearer authorization, loopback peer/Host/Origin, strict JSON, body limits, socket timeout and allowed methods. Request lifecycle metadata is appended to a local SQLite SHA-256 audit chain without storing credentials or model bodies.

This is a local development interface, not a remote service or production authentication system. No CORS permission, public/LAN bind, TLS endpoint, rate limiting, browser session management or remote access is included. See [CAD Generator Loopback HTTP API Contract](../design-3d/CAD_GENERATOR_HTTP_API_CONTRACT.md). A same-origin local authoring UI remains a separate OPEN requirement.


## Local FeatureHistory workbench (PR #140)

The local HTTP server serves packaged same-origin HTML/CSS/JS for a FeatureHistory JSON/revision workbench. The page supports bearer-token connection, source JSON editing/paste, immutable revision append, revision list/load and exact-revision regeneration. Static files are restricted to the validated loopback origin and protected by a restrictive CSP; API requests still require the bearer token. The token is not persisted by the UI.

This interface includes a bounded SVG polygon sketch workflow added by PR #142, but it is not a full parametric CAD editor or general 3D viewport. Arc authoring, dimensional/automatic constraint editing, general 3D modelling and full assembly authoring remain separate requirements. See the local UI section in the [CAD Generator Loopback HTTP API Contract](../design-3d/CAD_GENERATOR_HTTP_API_CONTRACT.md).


## Bounded visual polygon sketch workflow (PR #142)

The local FeatureHistory workbench now offers a bounded SVG canvas for straight-edge polygons. The authenticated polygon template endpoint builds a fixed-coordinate ParametricSketch v1.2 and a Sketch → Extrusion → Mesh history. The user reviews the returned JSON, saves an immutable source revision and explicitly requests regeneration. Geometry and watertight mesh validation are returned as artifacts and evidence; the drawing canvas alone does not certify the shape.

The editor is deliberately limited to 3–64 vertices within X 0–26 mm and Y 0–15 mm. It does not implement arcs, holes, dimensional/automatic constraints, drag solving or a 3D viewport. See [CAD Generator Loopback HTTP API Contract](../design-3d/CAD_GENERATOR_HTTP_API_CONTRACT.md).


## ModuleRuntime output contract enforcement (WP-09A)

A runtime-enabled ModuleOperation must declare an immutable output schema. The schema root carries `x-schema-version`, which must equal the operation's `output_schema_version`. The runtime rejects missing or mismatched schema metadata before dispatch and validates the returned object against the supported JSON Schema subset before emitting `COMPLETED`. Structural failures produce a sanitized `ERROR` response. JSON compatibility/finiteness checks remain independently enforced by ModuleResponse.

The current validator is deliberately not a complete JSON Schema implementation. Unsupported keywords fail closed. Implemented schema rules include object/array/string/boolean/integer/number/null types, required fields, properties, additionalProperties, array items, enum/const and basic size/numeric bounds. Full standards conformance and input structural validation remain separate work.
