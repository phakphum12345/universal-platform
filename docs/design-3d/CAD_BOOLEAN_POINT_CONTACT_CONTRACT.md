# Planar Boolean Point-Contact Topology Contract

**Status:** Bounded point-contact component handling implemented by PR #95.  
**Merge SHA:** `2eea0bdc9226c8ec3b3d5458e3902ee01b8314f0`.  
**Exact PR-head CI:** run #42264798640 — both required jobs PASS, 639 tests.  
**Post-merge CI:** run #42264923364 — both required jobs PASS, 639 tests.

## 1. Topology semantics

A point contact between otherwise disjoint material components has zero shared area and must not be converted into a self-touching figure-eight region. The result is a set of separate canonical PlanarRegion components that may share a coordinate at a contact vertex.

Shared-edge boundaries continue to dissolve when the Boolean operation yields one connected material region. Empty-area edge/point contacts do not create zero-area output regions.

## 2. Deterministic boundary pairing

The arrangement emits directed boundary edges with result material on the left. At each vertex:
1. Collect incoming and outgoing selected boundary half-edges.
2. Require balanced incoming/outgoing incidence.
3. Sort outgoing direction vectors counter-clockwise using exact rational half-plane and cross-product comparisons.
4. For each incoming edge, use its reverse direction as the reference ray.
5. Pair it with the outgoing edge immediately clockwise from that reference ray.
6. Require a one-to-one pairing; coincident directions, unbalanced incidence or ambiguous mappings fail closed.

The stitcher then traverses each directed edge exactly once and rejects repeated-vertex or degenerate cycles. It does not snap coordinates, introduce epsilon topology repairs or round predicates.

## 3. Output validity

- Every emitted cycle must be non-degenerate and simple.
- Each output region is validated by PlanarRegion v1.0, including outer/hole winding and strict hole containment.
- Distinct point-touching components remain distinct PlanarRegion records.
- Ambiguous branching, invalid hole contact and unsupported topology remain fail-closed.
- The existing 256-edge input bound and frame/unit compatibility requirements remain unchanged.

## 3A. Region-set result semantics

The set-level Boolean result metadata states that unambiguous point-only contacts remain separate output components. Ambiguous branching, coincident outgoing directions, unbalanced incidence and invalid hole topology remain fail-closed. The serialized `limitations` field and its strict round-trip validator must use the same versioned wording as the executable behavior; this metadata is descriptive and does not weaken topology validation.

## 4. Acceptance evidence

- Two unit squares touching at one point: UNION returns two separate area-1 regions.
- Four triangular sectors touching only at one point: UNION returns four separate area-2 regions.
- Edge-adjacent rectangles continue to dissolve their shared edge into one region.
- Existing exact-predicate, holes, multiple components, permutation, area and serialization regression corpus remains passing.
- Exact PR-head and post-merge Python suite: 639 passed.
