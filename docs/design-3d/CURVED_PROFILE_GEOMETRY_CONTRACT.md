# Curved Profile Geometry Contract

**Status:** PR #58 implementation candidate. Acceptance is limited to circular-arc profile edges in analytic extrusion; no B-rep or Boolean kernel is implied.

## 1. Representation

- A profile is an ordered immutable loop of Vec2 vertices.
- Each edge runs from vertex i to vertex i+1; arc_sweeps_rad[i] == 0 denotes a line, otherwise the signed value is a circular-arc sweep in radians.
- Arc center and radius are deterministically derived from the chord endpoints and signed sweep.
- Curved edges require stable per-edge IDs. Hole loops use matching sweep and ID arrays.
- Existing straight-only ExtrudedProfileSolid snapshots remain schema v1.0. Curved profiles use schema v1.1; v1.0 readers must reject the new fields rather than silently discard them.

## 2. Geometry and topology

- Area is evaluated analytically with Green's theorem for lines and circular arcs.
- Perimeter is the exact sum of line lengths and circular-arc lengths.
- Local profile bounds include analytic circular-arc extrema.
- Volume and surface area remain exact for the ideal extruded profile, including curved inner walls.
- Topology validation uses deterministic 1-degree arc tessellation before applying existing loop intersection and containment checks. This is a bounded validation guard, not exact curve/curve intersection or a B-rep proof.
- Arc sweeps must be finite, non-zero for curved edges, and have magnitude strictly below 2*pi. Full circles are represented by multiple connected arcs.

## 3. Acceptance criteria

1. A quarter-circle sector matches independent analytic area, perimeter, volume and surface-area references.
2. A circular through-hole matches independent analytic net area, perimeter, volume and inner-wall surface-area references.
3. Arc extrema are included in local and transformed conservative bounds.
4. Missing/duplicate segment IDs, mismatched sweep counts, invalid sweeps, open loops, self-intersections and invalid holes fail closed.
5. Straight-only v1.0 snapshots round-trip unchanged; curved geometry emits v1.1 snapshots.
6. Existing Box/Cylinder, polygon extrusion, through-hole, transform and mechanism regression tests remain passing.
7. No claim of B-rep, exact Boolean operations, meshing, STEP/STL interchange, physical validation or manufacturing readiness.

## 4. Known limitations

- Only circular arcs are supported; splines and rational curves are not.
- Curved-loop topology guards are tessellation-based with a fixed angular step.
- Boolean union/subtract/intersect, general B-rep, feature history, meshing, STEP/STL export and manufacturing validation remain separate roadmap work.
