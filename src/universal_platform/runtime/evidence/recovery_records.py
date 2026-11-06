"""Redacted, append-only JSONL evidence for recovery outcomes."""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
import json
import os
from pathlib import Path
import stat
from threading import Lock
from contextlib import contextmanager

@dataclass(frozen=True, slots=True)
class RecoveryEvidenceRecord:
    record_id: str
    resource_id: str
    captured_at: datetime
    event_fingerprints: tuple[str, ...]
    initial_state: str
    final_state: str
    repaired: bool
    resumed: bool
    reason: str

    def __post_init__(self) -> None:
        for name in ("record_id", "resource_id", "initial_state", "final_state", "reason"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be non-empty")
        if self.captured_at.tzinfo is None or self.captured_at.utcoffset() is None:
            raise ValueError("captured_at must be timezone-aware")
        if len(set(self.event_fingerprints)) != len(self.event_fingerprints):
            raise ValueError("event fingerprints must be unique")
        if any(len(item) != 64 or any(ch not in "0123456789abcdef" for ch in item) for item in self.event_fingerprints):
            raise ValueError("event fingerprints must be lowercase SHA-256 values")
        if self.resumed and not self.repaired:
            raise ValueError("a resource cannot be resumed unless repair was validated")

    def to_dict(self) -> dict[str, object]:
        return {
            "record_id": self.record_id,
            "resource_id": self.resource_id,
            "captured_at": self.captured_at.isoformat(),
            "event_fingerprints": list(self.event_fingerprints),
            "initial_state": self.initial_state,
            "final_state": self.final_state,
            "repaired": self.repaired,
            "resumed": self.resumed,
            "reason": self.reason,
        }

class JsonlRecoveryEvidenceStore:
    """Cross-process append-only JSONL store with a SHA-256 hash chain.

    Legacy unchained JSONL records are accepted only as a prefix and become
    the unverified chain anchor. All new records are chained and tampering in
    the chained suffix is detected by verify() and before every append.
    """

    _ZERO_HASH = "0" * 64

    def __init__(
        self,
        root: str | Path,
        *,
        filename: str = "recovery-evidence.jsonl",
        max_record_bytes: int = 65_536,
        max_store_bytes: int = 16_777_216,
    ) -> None:
        self.root = Path(root).resolve(strict=True)
        if not self.root.is_dir():
            raise ValueError("evidence root must be a directory")
        if not filename or Path(filename).name != filename or filename in {".", ".."}:
            raise ValueError("evidence filename must be a simple file name")
        if max_record_bytes < 256:
            raise ValueError("max_record_bytes must be at least 256")
        if max_store_bytes < max_record_bytes:
            raise ValueError("max_store_bytes must be at least max_record_bytes")
        self.path = self.root / filename
        self.lock_path = self.root / f"{filename}.lock"
        self.max_record_bytes = max_record_bytes
        self.max_store_bytes = max_store_bytes
        self._lock = Lock()

    def append(self, record: RecoveryEvidenceRecord) -> None:
        import hashlib

        with self._lock, self._cross_process_lock():
            descriptor = self._open_evidence_file()
            try:
                current = self._read_all(descriptor)
                sequence, previous_hash, legacy_count = self._verify_bytes(current)
                envelope = record.to_dict()
                envelope["sequence"] = sequence + 1
                envelope["previous_hash"] = previous_hash
                canonical = json.dumps(
                    envelope, sort_keys=True, separators=(",", ":"), ensure_ascii=False
                ).encode("utf-8")
                envelope["record_hash"] = hashlib.sha256(canonical).hexdigest()
                payload = (
                    json.dumps(envelope, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
                    + "\n"
                ).encode("utf-8")
                if len(payload) > self.max_record_bytes:
                    raise ValueError("recovery evidence record exceeds the configured byte limit")
                if len(current) + len(payload) > self.max_store_bytes:
                    raise ValueError("recovery evidence store reached its configured byte limit")
                os.lseek(descriptor, 0, os.SEEK_END)
                view = memoryview(payload)
                while view:
                    written = os.write(descriptor, view)
                    if written <= 0:
                        raise OSError("incomplete evidence append")
                    view = view[written:]
                os.fsync(descriptor)
            finally:
                os.close(descriptor)

    def verify(self) -> tuple[int, int, str]:
        """Return (record_count, legacy_prefix_count, chain_head_hash); raise on tampering."""
        with self._lock, self._cross_process_lock():
            descriptor = self._open_evidence_file()
            try:
                data = self._read_all(descriptor)
                sequence, head_hash, legacy_count = self._verify_bytes(data)
                return sequence, legacy_count, head_hash
            finally:
                os.close(descriptor)

    def _open_evidence_file(self) -> int:
        if self.path.is_symlink():
            raise ValueError("evidence file must not be a symbolic link")
        flags = os.O_RDWR | os.O_APPEND | os.O_CREAT
        flags |= getattr(os, "O_NOFOLLOW", 0)
        descriptor = os.open(self.path, flags, 0o600)
        if not stat.S_ISREG(os.fstat(descriptor).st_mode):
            os.close(descriptor)
            raise ValueError("evidence target must be a regular file")
        return descriptor

    def _read_all(self, descriptor: int) -> bytes:
        size = os.fstat(descriptor).st_size
        if size > self.max_store_bytes:
            raise ValueError("recovery evidence store exceeds the configured byte limit")
        os.lseek(descriptor, 0, os.SEEK_SET)
        chunks: list[bytes] = []
        remaining = size
        while remaining:
            chunk = os.read(descriptor, min(remaining, 65_536))
            if not chunk:
                raise OSError("could not read complete recovery evidence store")
            chunks.append(chunk)
            remaining -= len(chunk)
        return b"".join(chunks)

    def _verify_bytes(self, data: bytes) -> tuple[int, str, int]:
        import hashlib

        if data and not data.endswith(b"\n"):
            raise ValueError("recovery evidence store ends with an incomplete record")
        sequence = 0
        previous_hash = self._ZERO_HASH
        legacy_count = 0
        chain_started = False
        for raw in data.splitlines():
            try:
                envelope = json.loads(raw.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise ValueError("recovery evidence store contains invalid JSON") from exc
            if not isinstance(envelope, dict):
                raise ValueError("recovery evidence record must be a JSON object")
            chain_fields = {"sequence", "previous_hash", "record_hash"}
            present = chain_fields.intersection(envelope)
            if not present:
                if chain_started:
                    raise ValueError("legacy evidence record cannot follow a chained record")
                legacy_count += 1
                sequence += 1
                previous_hash = hashlib.sha256(raw).hexdigest()
                continue
            if present != chain_fields:
                raise ValueError("recovery evidence chain metadata is incomplete")
            chain_started = True
            claimed_hash = envelope.pop("record_hash")
            claimed_sequence = envelope.get("sequence")
            claimed_previous = envelope.get("previous_hash")
            if claimed_sequence != sequence + 1 or claimed_previous != previous_hash:
                raise ValueError("recovery evidence chain sequence or previous hash mismatch")
            canonical = json.dumps(
                envelope, sort_keys=True, separators=(",", ":"), ensure_ascii=False
            ).encode("utf-8")
            actual_hash = hashlib.sha256(canonical).hexdigest()
            if not isinstance(claimed_hash, str) or claimed_hash != actual_hash:
                raise ValueError("recovery evidence hash-chain verification failed")
            sequence = claimed_sequence
            previous_hash = actual_hash
        return sequence, previous_hash, legacy_count

    @contextmanager
    def _cross_process_lock(self):
        if self.lock_path.is_symlink():
            raise ValueError("evidence lock file must not be a symbolic link")
        flags = os.O_RDWR | os.O_CREAT
        flags |= getattr(os, "O_NOFOLLOW", 0)
        descriptor = os.open(self.lock_path, flags, 0o600)
        try:
            if not stat.S_ISREG(os.fstat(descriptor).st_mode):
                raise ValueError("evidence lock target must be a regular file")
            if os.fstat(descriptor).st_size == 0:
                os.write(descriptor, b"0")
                os.fsync(descriptor)
            os.lseek(descriptor, 0, os.SEEK_SET)
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(descriptor, msvcrt.LK_LOCK, 1)
            else:
                import fcntl
                fcntl.flock(descriptor, fcntl.LOCK_EX)
            try:
                yield
            finally:
                os.lseek(descriptor, 0, os.SEEK_SET)
                if os.name == "nt":
                    import msvcrt
                    msvcrt.locking(descriptor, msvcrt.LK_UNLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(descriptor, fcntl.LOCK_UN)
        finally:
            os.close(descriptor)
