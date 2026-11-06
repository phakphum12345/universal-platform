# 3D Model Validation and Design Verification

**Status:** PROPOSED

## 1. Validation layers

1. File integrity and parser compatibility.
2. Geometry validity: watertightness where required, normals, self-intersections, duplicate faces and degeneracy.
3. Parametric integrity: constraints, references, feature dependencies and rebuild status.
4. Assembly integrity: mates, joints, missing parts, collisions and clearances.
5. Engineering consistency: units, material, loads, boundary conditions and physical properties.
6. Manufacturing readiness: tolerances, process limits, drawings and BOM consistency.
7. Evidence and review: source versions, checks, reviewer and unresolved risks.

## 2. Result semantics

PASS: the defined check executed and met its criterion. FAIL: executed and did not meet it. SKIPPED: not run, with reason. UNKNOWN: evidence or capability insufficient. CONDITIONAL: result depends on an explicit unresolved assumption; do not treat as PASS.

## 3. Validation record

Model identifier/revision; input files and hashes; CAD tool/kernel version; check name/version; parameters; output; evidence references; timestamp; operator; warnings; and reviewer decision.

## 4. Acceptance criteria

- [ ] Each check has a defined criterion.
- [ ] Failed and skipped checks remain visible.
- [ ] Model changes invalidate affected downstream evidence.
- [ ] Geometry validation is not confused with structural safety.
- [ ] Exports are checked independently.
- [ ] No overall PASS is issued while critical checks are UNKNOWN or FAIL.


## Current mesh-validation evidence and gaps

- `validate_triangle_mesh` currently checks indexed face validity, degeneracy, edge incidence, winding, signed volume and surface area.
- Binary STL export is implemented with a metadata sidecar; independent test-only parsing verifies facets, quantized bounds and signed volume.
- PR #76 merged the mesh topology-analysis contract; PR #77 adds a candidate implementation for component, vertex-link and duplicate/coincident-coordinate diagnostics, pending exact-SHA CI.
- Triangle-triangle self-intersection detection, arbitrary mesh repair, external CAD application reopen, manufacturing checks and physical validation remain UNKNOWN or NOT IMPLEMENTED. No overall model-validity PASS may be inferred from structural mesh validation alone.
