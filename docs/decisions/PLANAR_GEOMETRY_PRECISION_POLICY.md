# Planar Geometry Precision Policy — v1

**Status:** Selected for the dependency-free PlanarRegion v1 input/validation layer. This is not approval to adopt a third-party geometry kernel.

## Policy

- Interpret every finite input coordinate as the exact rational value of its represented IEEE-754 binary64 number, using `Fraction.from_float(float(value))`.
- Use exact rational signs for orientation, segment intersection, signed area and point-in-polygon decisions.
- Do not apply a global epsilon, snap, quantize, weld or silently repair coordinates.
- Do not infer coordinate frame or convert units. Every region carries an explicit frame ID and length unit; Boolean operations must reject mismatched frames/units until an explicit conversion is requested.
- Normalize outer loops counter-clockwise and hole loops clockwise, then rotate each loop to its lexicographically smallest coordinate. Preserve collinear intermediate vertices; reject zero-length/overlapping adjacent edges and all non-adjacent self-contact.
- Store source coordinates as finite binary64 values. Exact rational arithmetic governs topology decisions; future generated intersection coordinates must define a deterministic binary64 conversion and report a conservative conversion/area error bound before Boolean results can be marked complete.
- Bound validation work at 2,048 total boundary edges per region. Exceeding the bound is an invalid request, not a topology PASS.

## Consequences and limitations

- The runtime remains Python standard-library-only and offline; no external dependency or paid service is introduced.
- Rational numerators/denominators may grow with complex inputs. The edge bound limits the initial validation workload; Boolean arrangement work will need its own pair/memory limits and UNKNOWN behavior.
- This policy provides exact predicates for represented input coordinates, not exact physical measurements, manufacturing tolerances, or certified CAD geometry.
- `ProfileLoop` and `ProfileBooleanResult v1.0` remain unchanged and convex-only. The new `PlanarRegion v1.0` model is a separate API.
- This decision does not select a B-rep kernel, provide arcs/splines, or implement region Boolean operations.
