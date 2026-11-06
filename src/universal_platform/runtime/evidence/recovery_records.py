"""Redacted, append-only JSONL evidence for recovery outcomes."""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
import json
import os
from pathlib import Path
import stat
from threading import Lock

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
    """Append-only JSONL store; raw log messages are deliberately not persisted."""
    def __init__(self, root: str | Path, *, filename: str = "recovery-evidence.jsonl", max_record_bytes: int = 65_536) -> None:
        self.root = Path(root).resolve(strict=True)
        if not self.root.is_dir():
            raise ValueError("evidence root must be a directory")
        if not filename or Path(filename).name != filename or filename in {".", ".."}:
            raise ValueError("evidence filename must be a simple file name")
        if max_record_bytes < 256:
            raise ValueError("max_record_bytes must be at least 256")
        self.path = self.root / filename
        self.max_record_bytes = max_record_bytes
        self._lock = Lock()

    def append(self, record: RecoveryEvidenceRecord) -> None:
        payload = (json.dumps(record.to_dict(), sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode("utf-8")
        if len(payload) > self.max_record_bytes:
            raise ValueError("recovery evidence record exceeds the configured byte limit")
        with self._lock:
            if self.path.is_symlink():
                raise ValueError("evidence file must not be a symbolic link")
            flags = os.O_WRONLY | os.O_APPEND | os.O_CREAT
            flags |= getattr(os, "O_NOFOLLOW", 0)
            descriptor = os.open(self.path, flags, 0o600)
            try:
                if not stat.S_ISREG(os.fstat(descriptor).st_mode):
                    raise ValueError("evidence target must be a regular file")
                written = os.write(descriptor, payload)
                if written != len(payload):
                    raise OSError("incomplete evidence append")
                os.fsync(descriptor)
            finally:
                os.close(descriptor)
