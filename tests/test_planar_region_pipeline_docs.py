from pathlib import Path


ROOT = Path(__file__).parents[1]


def test_post_pr88_audit_is_indexed_and_references_existing_schemas():
    index = (ROOT / "DOCUMENTATION_INDEX.md").read_text(encoding="utf-8")
    audit = ROOT / "docs" / "audit" / "REPOSITORY_AUDIT_2026-11-06_POST_PR88.md"
    set_schema = ROOT / "schemas" / "geometry" / "planar-region-set-boolean-result.schema.json"
    extrusion_schema = ROOT / "schemas" / "geometry" / "planar-region-extrusion-result.schema.json"
    assert audit.is_file() and set_schema.is_file() and extrusion_schema.is_file()
    assert "REPOSITORY_AUDIT_2026-11-06_POST_PR88.md" in index
    assert "planar-region-set-boolean-result.schema.json" in index
    assert "planar-region-extrusion-result.schema.json" in index


def test_current_status_records_boolean_to_mesh_vertical_slice_and_open_gates():
    audit = (ROOT / "docs" / "audit" / "REPOSITORY_AUDIT_2026-11-06_POST_PR88.md").read_text(encoding="utf-8")
    roadmap = (ROOT / "ROADMAP.md").read_text(encoding="utf-8")
    status = (ROOT / "docs" / "implementation" / "IMPLEMENTATION_STATUS.md").read_text(encoding="utf-8")
    traceability = (ROOT / "docs" / "traceability" / "REQUIREMENTS_TRACEABILITY_MATRIX.md").read_text(encoding="utf-8")
    for text in (audit, roadmap, status):
        assert "bd9379617f1bc88772137a6e9886e33cb0bed3cb" in text
        assert "607" in text
    assert "CAD-PLANAR-EXTRUSION-001" in traceability
    assert "B-rep" in audit
    assert "feature history" in audit.lower()
