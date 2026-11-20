import json
from concurrent.futures import ThreadPoolExecutor

import pytest

from universal_platform.runtime.evidence.jsonl_journal import JsonlHashChainJournal


def test_jsonl_hash_chain_journal_appends_and_replays_versioned_events(tmp_path):
    journal = JsonlHashChainJournal(tmp_path, filename="worker-leases.jsonl")
    first = journal.append({
        "schema_version": 1,
        "event_type": "LEASE_ACQUIRED",
        "lease_id": "lease-1",
        "pool_id": "local",
    })
    second = journal.append({
        "schema_version": 1,
        "event_type": "LEASE_QUARANTINED",
        "lease_id": "lease-1",
        "reason": "worker termination unknown",
    })

    assert first["sequence"] == 1
    assert second["sequence"] == 2
    assert second["previous_hash"] == first["record_hash"]
    assert len(second["record_hash"]) == 64
    records = journal.read_all()
    assert [record["event_type"] for record in records] == [
        "LEASE_ACQUIRED",
        "LEASE_QUARANTINED",
    ]
    assert journal.verify() == (2, 0, second["record_hash"])


def test_jsonl_hash_chain_journal_rejects_non_json_and_reserved_fields(tmp_path):
    journal = JsonlHashChainJournal(tmp_path)
    with pytest.raises(TypeError, match="mapping"):
        journal.append([("event_type", "LEASE_ACQUIRED")])
    with pytest.raises(ValueError, match="reserved chain fields"):
        journal.append({"event_type": "LEASE_ACQUIRED", "sequence": 1})
    with pytest.raises(ValueError, match="finite JSON-compatible"):
        journal.append({"event_type": "LEASE_ACQUIRED", "value": float("nan")})
    assert journal.verify()[0] == 0


def test_jsonl_hash_chain_journal_disallows_legacy_prefix_by_default(tmp_path):
    path = tmp_path / "events.jsonl"
    path.write_text(json.dumps({"event_type": "legacy"}) + "\n", encoding="utf-8")
    journal = JsonlHashChainJournal(tmp_path)
    with pytest.raises(ValueError, match="legacy journal record"):
        journal.verify()


def test_jsonl_hash_chain_journal_rejects_incomplete_tail_and_tampering(tmp_path):
    journal = JsonlHashChainJournal(tmp_path)
    journal.append({"event_type": "LEASE_ACQUIRED", "lease_id": "lease-1"})
    path = journal.path
    lines = path.read_text(encoding="utf-8").splitlines()
    record = json.loads(lines[0])
    record["lease_id"] = "tampered"
    path.write_text(json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="hash-chain"):
        journal.verify()

    path.write_bytes(b'{"partial":')
    with pytest.raises(ValueError, match="incomplete record"):
        journal.append({"event_type": "LEASE_RELEASED", "lease_id": "lease-1"})


def test_jsonl_hash_chain_journal_serializes_multiple_instances(tmp_path):
    journals = tuple(
        JsonlHashChainJournal(tmp_path, filename="concurrent.jsonl")
        for _ in range(4)
    )

    def append(index):
        journals[index % len(journals)].append({
            "event_type": "LEASE_ACQUIRED",
            "lease_id": f"lease-{index}",
        })

    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(append, range(32)))

    count, legacy_count, head_hash = journals[0].verify()
    assert count == 32
    assert legacy_count == 0
    assert len(head_hash) == 64
    records = journals[1].read_all()
    assert len(records) == 32
    assert [record["sequence"] for record in records] == list(range(1, 33))


def test_jsonl_hash_chain_journal_rejects_symlink(tmp_path):
    target = tmp_path / "target.jsonl"
    target.write_text("", encoding="utf-8")
    link = tmp_path / "events.jsonl"
    try:
        link.symlink_to(target)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks are unavailable on this platform")
    journal = JsonlHashChainJournal(tmp_path)
    with pytest.raises(ValueError, match="symbolic link"):
        journal.append({"event_type": "LEASE_ACQUIRED"})


def test_jsonl_hash_chain_journal_reserves_lock_file_suffix(tmp_path):
    with pytest.raises(ValueError, match="reserved for lock files"):
        JsonlHashChainJournal(tmp_path, filename="events.jsonl.lock")
    with pytest.raises(ValueError, match="reserved for lock files"):
        JsonlHashChainJournal(tmp_path, filename="events.jsonl.LOCK")


@pytest.mark.skipif(__import__("os").name == "nt", reason="Windows uses MoveFileExW WRITE_THROUGH")
def test_new_journal_creation_fsyncs_parent_directory(tmp_path, monkeypatch):
    import os
    import stat

    real_fsync = os.fsync
    synced_directories = []

    def track_fsync(descriptor):
        if stat.S_ISDIR(os.fstat(descriptor).st_mode):
            synced_directories.append(True)
        return real_fsync(descriptor)

    monkeypatch.setattr(os, "fsync", track_fsync)
    JsonlHashChainJournal(tmp_path).append({"event_type": "LEASE_ACQUIRED"})
    assert synced_directories


def test_jsonl_hash_chain_journal_transaction_serializes_check_and_append(tmp_path):
    journal_path = tmp_path
    from universal_platform.runtime.evidence.jsonl_journal import JsonlHashChainJournal
    journals = tuple(JsonlHashChainJournal(journal_path, filename="transaction.jsonl") for _ in range(6))

    def reserve(index):
        appended = journals[index % len(journals)].append_transaction(
            lambda records: (
                ({"event_type": "RESERVED", "reservation_id": str(index)},)
                if sum(record.get("event_type") == "RESERVED" for record in records) < 2
                else ()
            )
        )
        return bool(appended)

    with ThreadPoolExecutor(max_workers=12) as pool:
        outcomes = list(pool.map(reserve, range(12)))

    assert sum(outcomes) == 2
    assert sum(record["event_type"] == "RESERVED" for record in journals[0].read_all()) == 2


def test_jsonl_hash_chain_journal_transaction_callback_failure_appends_nothing(tmp_path):
    from universal_platform.runtime.evidence.jsonl_journal import JsonlHashChainJournal
    journal = JsonlHashChainJournal(tmp_path)
    with pytest.raises(RuntimeError, match="abort"):
        journal.append_transaction(lambda _records: (_ for _ in ()).throw(RuntimeError("abort")))
    assert journal.verify()[0] == 0
