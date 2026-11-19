"""Redacted recovery-outcome records stored in the reusable hash-chain journal."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from .jsonl_journal import JsonlHashChainJournal


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
        if not isinstance(self.event_fingerprints, tuple):
            raise ValueError("event_fingerprints must be an immutable tuple")
        if len(set(self.event_fingerprints)) != len(self.event_fingerprints):
            raise ValueError("event fingerprints must be unique")
        if not isinstance(self.repaired, bool) or not isinstance(self.resumed, bool):
            raise ValueError("repaired and resumed must be booleans")
        if any(
            len(item) != 64 or any(ch not in "0123456789abcdef" for ch in item)
            for item in self.event_fingerprints
        ):
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
    """Append-only recovery outcome store backed by JsonlHashChainJournal.

    Legacy unchained JSONL records remain accepted only as a prefix for
    backward compatibility. New records are hash-chained and verified before
    each append. This store records recovery outcomes, not live worker leases.
    """

    def __init__(
        self,
        root: str,
        *,
        filename: str = "recovery-evidence.jsonl",
        max_record_bytes: int = 65_536,
        max_store_bytes: int = 16_777_216,
    ) -> None:
        self._journal = JsonlHashChainJournal(
            root,
            filename=filename,
            max_record_bytes=max_record_bytes,
            max_store_bytes=max_store_bytes,
            allow_legacy_prefix=True,
        )
        self.root = self._journal.root
        self.path = self._journal.path
        self.lock_path = self._journal.lock_path
        self.max_record_bytes = self._journal.max_record_bytes
        self.max_store_bytes = self._journal.max_store_bytes

    def append(self, record: RecoveryEvidenceRecord) -> None:
        if not isinstance(record, RecoveryEvidenceRecord):
            raise TypeError("record must be a RecoveryEvidenceRecord")
        self._journal.append(record.to_dict())

    def verify(self) -> tuple[int, int, str]:
        """Return (record_count, legacy_prefix_count, chain_head_hash)."""
        return self._journal.verify()


__all__ = ["JsonlHashChainJournal", "JsonlRecoveryEvidenceStore", "RecoveryEvidenceRecord"]
