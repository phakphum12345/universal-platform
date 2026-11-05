# 3D Design Intelligence

**Owner-approved scope:** CONFIRMED  
**Detailed capability design:** PROPOSED  
**Implementation:** NOT IMPLEMENTED / NOT VERIFIED

## 1. Purpose

Specify a 3D design capability for parts, products, enclosures, equipment, machines, mechanisms, structures and assemblies. It consumes requirements and engineering models from UEIC and returns editable, traceable design artifacts.

## 2. Design modes

- Create from natural-language requirements and structured parameters.
- Create from sketches, dimensions, reference images and 2D drawings.
- Import and inspect existing supported CAD models.
- Modify a copy of an existing model while preserving source provenance.
- Generate parametric variants and compare trade-offs.
- Derive geometry from IC/chip, board, sensor, module, connector and component constraints.
- Create static objects and assemblies with moving mechanisms.

## 3. Core capabilities

Parametric sketches; constraints; feature history; solids and surfaces; assemblies; coordinate frames; datum geometry; reference planes; materials; appearance separated from physical properties; configurations; metadata; drawing views; dimensions; annotations; and revision comparison.

## 4. Engineering integration

Use UEIC for units, physics, material data, load cases, thermal constraints, electrical clearance, fluid constraints, tolerance analysis and verification. Geometry alone is not proof of strength, safety or manufacturability.

## 5. Data and interoperability

Prefer open and documented formats. Candidate interchange formats include STEP for solid/assembly exchange, STL and 3MF for additive manufacturing meshes, OBJ for mesh exchange, and DXF/SVG for suitable 2D geometry. Actual format support must be tested; do not promise lossless parametric feature history across neutral formats.

## 6. Outputs

Native editable project where supported; neutral exports; drawings; dimension tables; material assignments; BOM; assembly structure; mass/property report; constraints; assumptions; and validation/evidence manifest.

## 7. Acceptance criteria

- [ ] Requirements map to parameters and geometry features.
- [ ] Units, coordinate frames and model revision are explicit.
- [ ] Source models are not overwritten.
- [ ] Assemblies preserve component identities and relationships.
- [ ] Exports are reopened and validated by supported tools.
- [ ] Unverified properties are clearly marked.
- [ ] Model artifacts are reproducible from recorded inputs where feasible.

## 8. Open decisions

First CAD kernel/tool; first native file format; parametric feature scope; supported import/export matrix; 2D drawing workflow; target platforms; performance limits.
