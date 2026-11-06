from pathlib import Path


ROOT = Path(__file__).parents[1]


def test_planar_boolean_audit_and_contract_are_indexed():
    index = (ROOT / "DOCUMENTATION_INDEX.md").read_text(encoding="utf-8")
    audit = ROOT / "docs" / "audit" / "REPOSITORY_AUDIT_2026-11-06_POST_PR84.md"
    contract = ROOT / "docs" / "design-3d" / "CAD_GENERAL_PLANAR_TOPOLOGY_CONTRACT.md"
    schema = ROOT / "schemas" / "geometry" / "planar-region-boolean-result.schema.json"
    assert audit.is_file()
    assert contract.is_file()
    assert schema.is_file()
    assert "REPOSITORY_AUDIT_2026-11-06_POST_PR84.md" in index
    assert "planar-region-boolean-result.schema.json" in index


def test_planar_boolean_implementation_status_is_consistent_across_ledgers():
    audit = (ROOT / "docs" / "audit" / "REPOSITORY_AUDIT_2026-11-06_POST_PR84.md").read_text(encoding="utf-8")
    roadmap = (ROOT / "ROADMAP.md").read_text(encoding="utf-8")
    status = (ROOT / "docs" / "implementation" / "IMPLEMENTATION_STATUS.md").read_text(encoding="utf-8")
    traceability = (ROOT / "docs" / "traceability" / "REQUIREMENTS_TRACEABILITY_MATRIX.md").read_text(encoding="utf-8")
    for text in (audit, roadmap, status, traceability):
        assert "1b75e2dab5b64d2d089e410bba02187d28772193" in text
        assert "580" in text
    assert "CAD-PLANAR-BOOLEAN-001" in traceability


def test_planar_boolean_documentation_does_not_claim_full_cad_completion():
    audit = (ROOT / "docs" / "audit" / "REPOSITORY_AUDIT_2026-11-06_POST_PR84.md").read_text(encoding="utf-8")
    contract = (ROOT / "docs" / "design-3d" / "CAD_GENERAL_PLANAR_TOPOLOGY_CONTRACT.md").read_text(encoding="utf-8")
    assert "not implemented" in audit.lower()
    assert "remains open" in contract.lower()
