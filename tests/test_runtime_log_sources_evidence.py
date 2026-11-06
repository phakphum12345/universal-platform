from datetime import datetime, timezone
import json

import pytest

from universal_platform.runtime.evidence.recovery_records import JsonlRecoveryEvidenceStore, RecoveryEvidenceRecord
from universal_platform.runtime.health.log_sources import FileLogSource


def test_file_log_source_reads_only_from_configured_root_and_analyzes(tmp_path):
    (tmp_path / "worker.log").write_text("ERROR component_id=worker-9 failed", encoding="utf-8")
    source = FileLogSource(tmp_path)
    events = source.read_events("worker.log")
    assert len(events) == 1
    assert events[0].component_id == "worker-9"
    assert events[0].source == "runtime-file-log"


def test_file_log_source_rejects_traversal_oversize_and_invalid_utf8(tmp_path):
    outside = tmp_path.parent / "outside.log"
    outside.write_text("ERROR outside", encoding="utf-8")
    source = FileLogSource(tmp_path, max_bytes=8)
    with pytest.raises(ValueError, match="relative to"):
        source.read_text("../outside.log")
    (tmp_path / "large.log").write_text("0123456789", encoding="utf-8")
    with pytest.raises(ValueError, match="byte limit"):
        source.read_text("large.log")
    (tmp_path / "bad.log").write_bytes(bytes([0xff]))
    with pytest.raises(ValueError, match="UTF-8"):
        source.read_text("bad.log")


def make_record(record_id="r-1"):
    return RecoveryEvidenceRecord(
        record_id, "worker-9", datetime.now(timezone.utc), ("a" * 64,),
        "ACTIVE", "ACTIVE", True, True, "recovery validated",
    )


def test_recovery_evidence_store_appends_redacted_metadata_only(tmp_path):
    store = JsonlRecoveryEvidenceStore(tmp_path)
    store.append(make_record())
    store.append(make_record("r-2"))
    lines = store.path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    assert json.loads(lines[0])["event_fingerprints"] == ["a" * 64]
    assert "raw traceback" not in lines[0]


def test_recovery_evidence_rejects_naive_time_duplicate_fingerprints_and_invalid_resume():
    with pytest.raises(ValueError, match="timezone-aware"):
        RecoveryEvidenceRecord("r", "worker", datetime.now(), (), "ACTIVE", "ACTIVE", True, True, "ok")
    with pytest.raises(ValueError, match="unique"):
        RecoveryEvidenceRecord("r", "worker", datetime.now(timezone.utc), ("a" * 64, "a" * 64), "ACTIVE", "ACTIVE", True, True, "ok")
    with pytest.raises(ValueError, match="unless repair"):
        RecoveryEvidenceRecord("r", "worker", datetime.now(timezone.utc), (), "ACTIVE", "ACTIVE", False, True, "invalid")


def test_evidence_store_rejects_path_like_filename_and_symlink(tmp_path):
    with pytest.raises(ValueError, match="simple file name"):
        JsonlRecoveryEvidenceStore(tmp_path, filename="../outside.jsonl")
    target = tmp_path / "target.jsonl"
    target.write_text("", encoding="utf-8")
    link = tmp_path / "linked.jsonl"
    try:
        link.symlink_to(target)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks are unavailable on this platform")
    store = JsonlRecoveryEvidenceStore(tmp_path, filename="linked.jsonl")
    with pytest.raises(ValueError, match="symbolic link"):
        store.append(make_record())
