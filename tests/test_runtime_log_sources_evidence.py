from datetime import datetime, timezone
import json

import pytest

from universal_platform.runtime.evidence.recovery_records import JsonlRecoveryEvidenceStore, RecoveryEvidenceRecord
from universal_platform.runtime.health.log_sources import FileLogSource
from universal_platform.runtime.recovery.coordinator import RecoveryCoordinator
from universal_platform.runtime.resources.models import ResourceRecord, ResourceState
from universal_platform.runtime.resources.registry import ResourceRegistry


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


class RecoveryAdapter:
    adapter_id = "python-worker-v1"
    resource_kind = "python-worker"
    capabilities = ("execute-python",)
    def __init__(self): self.calls = []
    def quiesce(self, resource_id): self.calls.append("quiesce")
    def health_check(self, resource_id): self.calls.append("health"); return True
    def canary_check(self, resource_id): self.calls.append("canary"); return True
    def resume(self, resource_id): self.calls.append("resume")
    def rollback(self, resource_id): self.calls.append("rollback")

class SandboxedRepair:
    sandboxed = True
    def repair(self, resource_id, events): return True

def make_recovery_registry():
    registry = ResourceRegistry()
    registry.register(ResourceRecord("worker-9", "python-worker", "python-worker-v1", ("execute-python",)))
    return registry

def test_recovery_coordinator_reads_file_log_and_persists_before_and_after_resume(tmp_path):
    (tmp_path / "worker.log").write_text("ERROR component_id=worker-9 simulated failure", encoding="utf-8")
    evidence_root = tmp_path / "evidence"
    evidence_root.mkdir()
    source = FileLogSource(tmp_path)
    store = JsonlRecoveryEvidenceStore(evidence_root)
    adapter = RecoveryAdapter()
    coordinator = RecoveryCoordinator(make_recovery_registry(), evidence_store=store)
    result = coordinator.recover_from_source("worker-9", "worker.log", log_source=source, adapter=adapter, repair_executor=SandboxedRepair())
    records = [json.loads(line) for line in store.path.read_text(encoding="utf-8").splitlines()]
    assert result.state is ResourceState.ACTIVE and result.evidence_recorded
    assert adapter.calls == ["quiesce", "health", "canary", "resume"]
    assert len(records) == 2
    assert records[0]["final_state"] == "CANARY" and records[0]["resumed"] is False
    assert records[1]["final_state"] == "ACTIVE" and records[1]["resumed"] is True
    assert records[1]["event_fingerprints"]


def test_recovery_quarantines_before_resume_when_evidence_cannot_be_written(tmp_path):
    (tmp_path / "worker.log").write_text("ERROR component_id=worker-9 failure", encoding="utf-8")
    class BrokenStore:
        def append(self, record): raise OSError("evidence unavailable")
    adapter = RecoveryAdapter()
    coordinator = RecoveryCoordinator(make_recovery_registry(), evidence_store=BrokenStore())
    result = coordinator.recover_from_source("worker-9", "worker.log", log_source=FileLogSource(tmp_path), adapter=adapter, repair_executor=SandboxedRepair())
    assert result.state is ResourceState.QUARANTINED and not result.resumed
    assert "resume" not in adapter.calls and "rollback" in adapter.calls


def test_evidence_store_hash_chain_detects_tampering(tmp_path):
    store = JsonlRecoveryEvidenceStore(tmp_path)
    store.append(make_record("chain-1"))
    store.append(make_record("chain-2"))
    count, legacy_count, head_hash = store.verify()
    assert count == 2 and legacy_count == 0 and len(head_hash) == 64
    lines = store.path.read_text(encoding="utf-8").splitlines()
    first = json.loads(lines[0])
    first["reason"] = "tampered"
    lines[0] = json.dumps(first, sort_keys=True, separators=(",", ":"))
    store.path.write_text("\\n".join(lines) + "\\n", encoding="utf-8")
    with pytest.raises(ValueError, match="hash-chain"):
        store.verify()
    with pytest.raises(ValueError, match="hash-chain"):
        store.append(make_record("chain-3"))


def test_evidence_store_serializes_multiple_store_instances(tmp_path):
    from concurrent.futures import ThreadPoolExecutor

    stores = (JsonlRecoveryEvidenceStore(tmp_path), JsonlRecoveryEvidenceStore(tmp_path))
    def append(index):
        stores[index % 2].append(make_record(f"parallel-{index}"))
    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(append, range(32)))
    count, legacy_count, head_hash = stores[0].verify()
    assert count == 32 and legacy_count == 0 and len(head_hash) == 64
    assert len(stores[0].path.read_text(encoding="utf-8").splitlines()) == 32


def test_evidence_store_accepts_legacy_prefix_and_chains_new_records(tmp_path):
    legacy = make_record("legacy").to_dict()
    path = tmp_path / "recovery-evidence.jsonl"
    path.write_text(json.dumps(legacy, sort_keys=True, separators=(",", ":")) + "\\n", encoding="utf-8")
    store = JsonlRecoveryEvidenceStore(tmp_path)
    assert store.verify()[0:2] == (1, 1)
    store.append(make_record("new-after-legacy"))
    count, legacy_count, head_hash = store.verify()
    assert count == 2 and legacy_count == 1 and len(head_hash) == 64


def test_evidence_store_enforces_total_store_size(tmp_path):
    store = JsonlRecoveryEvidenceStore(tmp_path, max_record_bytes=512, max_store_bytes=512)
    store.append(make_record("size-1"))
    with pytest.raises(ValueError, match="store reached"):
        store.append(make_record("size-2"))
