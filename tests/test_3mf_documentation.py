from pathlib import Path


ROOT = Path(__file__).parents[1]


def test_3mf_interchange_contract_is_indexed():
    index = (ROOT / "DOCUMENTATION_INDEX.md").read_text(encoding="utf-8")
    contract = ROOT / "docs" / "engineering" / "3MF_CORE_MESH_INTERCHANGE_CONTRACT.md"
    assert contract.is_file()
    assert "3MF_CORE_MESH_INTERCHANGE_CONTRACT.md" in index


def test_3mf_status_records_exact_evidence_and_step_non_claim():
    contract = (ROOT / "docs" / "engineering" / "3MF_CORE_MESH_INTERCHANGE_CONTRACT.md").read_text(encoding="utf-8")
    roadmap = (ROOT / "ROADMAP.md").read_text(encoding="utf-8")
    status = (ROOT / "docs" / "implementation" / "IMPLEMENTATION_STATUS.md").read_text(encoding="utf-8")
    traceability = (ROOT / "docs" / "traceability" / "REQUIREMENTS_TRACEABILITY_MATRIX.md").read_text(encoding="utf-8")
    for text in (contract, roadmap, status):
        assert "9b415f7c6be0f537feb67cbe86a911dc0ef5f662" in text
        assert "650" in text
    assert "CAD-3MF-MESH-001" in traceability
    assert "STEP import/export remains OPEN" in contract
    assert "DTD/entity" in contract
