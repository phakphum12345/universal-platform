from pathlib import Path


ROOT = Path(__file__).parents[1]


def test_feature_history_contract_and_schema_are_indexed():
    index = (ROOT / "DOCUMENTATION_INDEX.md").read_text(encoding="utf-8")
    contract = ROOT / "docs" / "design-3d" / "FEATURE_HISTORY_REGENERATION_CONTRACT.md"
    schema = ROOT / "schemas" / "geometry" / "feature-history.schema.json"
    assert contract.is_file() and schema.is_file()
    assert "FEATURE_HISTORY_REGENERATION_CONTRACT.md" in index
    assert "feature-history.schema.json" in index


def test_feature_history_status_records_merge_evidence_and_non_claims():
    contract = (ROOT / "docs" / "design-3d" / "FEATURE_HISTORY_REGENERATION_CONTRACT.md").read_text(encoding="utf-8")
    roadmap = (ROOT / "ROADMAP.md").read_text(encoding="utf-8")
    status = (ROOT / "docs" / "implementation" / "IMPLEMENTATION_STATUS.md").read_text(encoding="utf-8")
    traceability = (ROOT / "docs" / "traceability" / "REQUIREMENTS_TRACEABILITY_MATRIX.md").read_text(encoding="utf-8")
    for text in (contract, roadmap, status):
        assert "0983de4c8839070e2a27cd7b8e704f975d176abf" in text
        assert "636" in text
    assert "CAD-FEATURE-HISTORY-001" in traceability
    assert "does not invoke user Python" in contract
    assert "incremental recomputation" in contract.lower()



def test_feature_history_suppression_contract_is_indexed_and_keeps_implementation_boundary():
    index = (ROOT / "DOCUMENTATION_INDEX.md").read_text(encoding="utf-8")
    contract = (
        ROOT / "docs" / "design-3d" / "FEATURE_HISTORY_SUPPRESSION_CONTRACT.md"
    ).read_text(encoding="utf-8")
    assert "FEATURE_HISTORY_SUPPRESSION_CONTRACT.md" in index
    assert "v1.0 → v1.1" in contract
    assert "old immutable revisions" in contract.lower()
    assert "PR #163 merged the first backend slice" in contract
    assert "workbench" in contract.lower()



def test_feature_history_undo_redo_contract_is_indexed_and_design_only():
    index = (ROOT / "DOCUMENTATION_INDEX.md").read_text(encoding="utf-8")
    contract = (
        ROOT / "docs" / "design-3d" / "FEATURE_HISTORY_UNDO_REDO_CONTRACT.md"
    ).read_text(encoding="utf-8")
    matrix = (
        ROOT / "docs" / "traceability" / "REQUIREMENTS_TRACEABILITY_MATRIX.md"
    ).read_text(encoding="utf-8")
    assert "FEATURE_HISTORY_UNDO_REDO_CONTRACT.md" in index
    assert "DESIGN CONTRACT — not implemented" in contract
    assert "Undo and Redo never delete revisions" in contract
    assert "CAD-EDIT-008" in (ROOT / "ROADMAP.md").read_text(encoding="utf-8")
    assert "| R-017 |" in matrix
