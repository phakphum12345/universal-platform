# 2D Convex Profile Boolean Topology Contract

**Status:** Convex polygon Boolean operations v1.0 implementation candidate (PR #61). This is a dependency-free planar geometry increment, not a general CAD kernel.

## 1. Inputs and coordinate model

- Inputs are immutable ProfileLoop records with stable IDs and finite Vec2 coordinates.
- Each input must be a simple convex polygon with non-zero area.
- Clockwise input is normalized to counter-clockwise order.
- Inputs have no implicit units; callers must keep both profiles in the same coordinate frame and unit system.
- Concave loops, circular arcs, splines, holes and non-simple boundaries fail closed.

## 2. Operations

- UNION returns the first profile plus a non-overlapping convex-cell partition of the second profile outside the first.
- INTERSECTION returns the convex intersection cell, or an empty result when the interiors do not overlap.
- DIFFERENCE returns a non-overlapping convex-cell partition of the first profile outside the second.

The output is a set of convex cells, not a dissolved outer boundary. Adjacent cells may share boundaries and are intentionally not merged in v1.0. This decomposition preserves area and supports deterministic downstream topology work without pretending to be a full polygon Boolean boundary solver.

## 3. Numerical and determinism rules

- Half-plane clipping uses floating-point predicates with scale-relative tolerances.
- Output cells are counter-clockwise, cyclically normalized to a stable first vertex, and sorted by bounding box, area and coordinate sequence.
- Result snapshots use schema v1.0 and include operation, source profile IDs, regions, area and region count.
- Snapshot import rejects missing/unknown fields, invalid loops, unsupported operations and area/count tampering.

## 4. Acceptance criteria

1. Overlap, disjoint, touching and containment references produce expected intersection/union/difference areas.
2. Difference and union partitions contain only convex simple cells and preserve expected total area.
3. Clockwise/counter-clockwise equivalent inputs produce identical snapshots.
4. Concave, self-intersecting, duplicate-vertex and underspecified inputs fail closed.
5. Result serialization round-trips deterministically and rejects tampering.
6. No third-party geometry dependency is introduced.

## 5. Explicit limitations and next gates

This v1.0 operation set accepts convex polygon loops only. It does not support concave input, arcs, holes, exact arithmetic, robust arbitrary near-coincident topology, region dissolution, general planar arrangements, 3D Boolean/B-rep operations, mesh Boolean operations, fillets, offsets, feature history, STEP/STL exchange, manufacturing validation or physical safety. Floating-point tolerances can affect very small or nearly coincident features; this must be addressed before claiming general-purpose CAD robustness.

The next CAD gates are general simple-polygon arrangements with holes, topology invariants and adversarial numerical references; then a reviewed CAD-kernel adapter decision, mesh generation/validation, and independent STEP/STL reopen tests.
