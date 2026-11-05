"""Evidence and provenance contracts shared by engineering modules."""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

class EvidenceKind(str, Enum):
    FACT = "FACT"
    INFERENCE = "INFERENCE"
    ASSUMPTION = "ASSUMPTION"
    HYPOTHESIS = "HYPOTHESIS"
    ESTIMATE = "ESTIMATE"
    SIMULATION = "SIMULATION"
    MEASUREMENT = "MEASUREMENT"
    UNKNOWN = "UNKNOWN"

class EvidenceStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    SKIPPED = "SKIPPED"
    UNKNOWN = "UNKNOWN"

@dataclass(frozen=True, slots=True)
class SourceRef:
    source_id: str
    revision: str | None = None
    locator: str | None = None
    content_sha256: str | None = None
    license_id: str | None = None

@dataclass(frozen=True, slots=True)
class EvidenceRecord:
    kind: EvidenceKind
    status: EvidenceStatus
    statement: str
    source_refs: tuple[SourceRef, ...] = ()
    method: str | None = None
    limitations: tuple[str, ...] = ()
    record_id: str = field(default_factory=lambda: str(uuid4()))
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.statement.strip():
            raise ValueError("Evidence statement cannot be empty")
        if self.status is EvidenceStatus.PASS and self.kind is EvidenceKind.UNKNOWN:
            raise ValueError("UNKNOWN evidence cannot have PASS status")
