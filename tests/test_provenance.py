import json

import pytest

from universal_platform.engineering.provenance import (
    EvidenceKind,
    EvidenceRecord,
    EvidenceStatus,
    SourceRef,
    evaluate_evidence_gate,
)


def record(status=EvidenceStatus.PASS, kind=EvidenceKind.SIMULATION, **changes):
    values = {
        "kind": kind,
        "status": status,
        "statement": "validated reference result",
        "record_id": "evidence-1",
        "created_at": "2026-11-06T05:00:00+00:00",
    }
    values.update(changes)
    return EvidenceRecord(**values)


def test_source_ref_validates_and_serializes_sha256():
    source = SourceRef(
        "datasheet:component-a",
        revision="rev-2",
        locator="page:4/table:2",
        content_sha256="A" * 64,
        license_id="CC-BY-4.0",
    )
    assert source.to_dict()["content_sha256"] == "a" * 64
    assert json.loads(json.dumps(source.to_dict()))["revision"] == "rev-2"


@pytest.mark.parametrize(
    "changes",
    [
        {"source_id": ""},
        {"revision": ""},
        {"locator": " "},
        {"license_id": ""},
        {"content_sha256": "not-a-sha"},
        {"content_sha256": "a" * 63},
    ],
)
def test_source_ref_rejects_invalid_metadata(changes):
    values = {"source_id": "source-1"}
    values.update(changes)
    with pytest.raises(ValueError):
        SourceRef(**values)


def test_evidence_record_rejects_unknown_pass_and_invalid_status_types():
    with pytest.raises(ValueError, match="UNKNOWN evidence"):
        record(kind=EvidenceKind.UNKNOWN)
    with pytest.raises(ValueError, match="EvidenceStatus"):
        record(status="PASS")


def test_evidence_record_requires_timezone_and_valid_timestamp():
    with pytest.raises(ValueError, match="timezone"):
        record(created_at="2026-11-06T05:00:00")
    with pytest.raises(ValueError, match="ISO-8601"):
        record(created_at="not-a-date")


def test_evidence_record_validates_sources_and_immutable_limitations():
    with pytest.raises(ValueError, match="immutable tuple"):
        record(source_refs=[SourceRef("s1")])
    with pytest.raises(ValueError, match="duplicates"):
        record(limitations=("one", "one"))
    with pytest.raises(ValueError, match="duplicate source"):
        record(source_refs=(SourceRef("s1"), SourceRef("s1")))


def test_evidence_metadata_is_detached_frozen_and_json_compatible():
    source = {"solver": {"iterations": [2, 3]}}
    evidence = record(metadata=source)
    source["solver"]["iterations"].append(4)
    assert evidence.to_dict()["metadata"]["solver"]["iterations"] == [2, 3]
    with pytest.raises(TypeError):
        evidence.metadata["solver"]["new"] = "value"
    with pytest.raises(TypeError):
        evidence.metadata["solver"]["iterations"][0] = 99
    assert json.loads(json.dumps(evidence.to_dict()))["status"] == "PASS"


def test_evidence_record_rejects_non_json_and_non_finite_metadata():
    with pytest.raises(ValueError, match="non-finite"):
        record(metadata={"value": float("nan")})
    with pytest.raises(ValueError, match="non-JSON"):
        record(metadata={"value": object()})


def test_evidence_gate_passes_only_when_every_required_record_passes():
    result = evaluate_evidence_gate((
        record(record_id="evidence-b"),
        record(record_id="evidence-a"),
    ))
    assert result.status is EvidenceStatus.PASS
    assert result.record_ids == ("evidence-a", "evidence-b")
    assert result.blockers == ()
    assert result.to_dict()["counts"]["PASS"] == 2


@pytest.mark.parametrize(
    "statuses,expected",
    [
        ((EvidenceStatus.PASS, EvidenceStatus.FAIL), EvidenceStatus.FAIL),
        ((EvidenceStatus.PASS, EvidenceStatus.UNKNOWN), EvidenceStatus.UNKNOWN),
        ((EvidenceStatus.PASS, EvidenceStatus.SKIPPED), EvidenceStatus.SKIPPED),
        ((EvidenceStatus.FAIL, EvidenceStatus.UNKNOWN), EvidenceStatus.FAIL),
    ],
)
def test_evidence_gate_never_promotes_non_pass_evidence(statuses, expected):
    records = tuple(
        record(status=status, record_id=f"evidence-{index}")
        for index, status in enumerate(statuses)
    )
    assert evaluate_evidence_gate(records).status is expected


def test_evidence_gate_empty_or_duplicate_record_ids_do_not_pass():
    assert evaluate_evidence_gate(()).status is EvidenceStatus.UNKNOWN
    with pytest.raises(ValueError, match="unique"):
        evaluate_evidence_gate((
            record(record_id="same"),
            record(record_id="same"),
        ))


def test_evidence_gate_requires_immutable_record_tuple():
    with pytest.raises(ValueError, match="immutable tuple"):
        evaluate_evidence_gate([record()])
