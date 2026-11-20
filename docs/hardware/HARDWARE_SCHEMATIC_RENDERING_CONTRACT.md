# Hardware Schematic Rendering Contract

**Status:** PR #59 implementation candidate. This is a deterministic offline symbol/layout renderer, not an electrical verification engine.

## 1. Separation of concerns

- SchematicModel remains the normalized connectivity graph: components, pins, electrical pin types and nets.
- SchematicLayout is a separate versioned document containing page dimensions in millimetres, symbol definitions, component placements and explicit net routes.
- Symbol definitions map package pin numbers to local pin-anchor coordinates and provide line, polyline, rectangle and circle graphics.
- Component placements use page-space millimetres and counter-clockwise rotation in radians.
- Net routes identify their net and endpoint PinRef values; optional waypoints are page-space millimetres.

## 2. Rendering behavior

- render_schematic_svg is pure Python and returns deterministic SVG text plus a structured report.
- Components, symbols, pins and routes are rendered in stable ID order.
- XML text is escaped; coordinates are formatted deterministically.
- Every schematic component must have exactly one placement and a matching symbol definition.
- Symbol pin numbers must match the component's declared pin numbers.
- Route endpoints must be terminals of the declared net and all route points must remain inside the page.
- A net is reported as rendered only when its route graph connects all declared terminals. Otherwise it is listed in unrouted_net_ids and a warning is returned.

## 3. Acceptance criteria

1. Layout snapshots round-trip deterministically under schema v1.0.
2. Symbol graphics support LINE, POLYLINE, RECTANGLE and CIRCLE with explicit millimetre coordinates.
3. Component rotation transforms symbol graphics and pin anchors consistently.
4. Two-terminal and multi-terminal route graphs are checked for connectivity.
5. Missing placements/symbols/pins, unknown route terminals and page overflow fail closed.
6. Unrouted nets are reported as incomplete; they are never represented as connected.
7. SVG is well-formed and deterministic for reordered equivalent inputs.
8. No external renderer, EDA library, hardware access or network access is required.

## 4. Limitations

- No automatic placement or autorouting.
- No symbol library importer, footprint/BOM synchronization or EDA project export.
- No electrical rule checking, power analysis, SPICE/circuit simulation or component derating.
- No manufacturing, safety, certification or physical validation claim.
- SVG output is a drawing artifact, not an electrical proof.
