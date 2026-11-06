"""Validated provenance records and conservative evidence aggregation."""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from math import isfinite
import re
from types import MappingProxyType
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


_SHA256 = re.compile(r"^[0-9a-fA-F]{64}$")


def _optional_text(value: str | None, label: str) -> None:
    if value is not None and (not isinstance(value, str) or not value.strip()):
        raise ValueError(f"{label} must be None or a non-empty string")


def _freeze_json(value: Any, path: str = "metadata") -> Any:
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if not isfinite(value):
            raise ValueError(f"{path} contains a non-finite number")
        return value
    if isinstance(value, Mapping):
        result: dict[str, Any] = {}
        for key, item in value.items():
            if not isinstance(key, str) or not key:
                raise ValueError(f"{path} keys must be non-empty strings")
            result[key] = _freeze_json(item, f"{path}.{key}")
        return MappingProxyType(result)
    if isinstance(value, (list, tuple)):
        return tuple(_freeze_json(item, f"{path}[{index}]") for index, item in enumerate(value))
    raise ValueError(f"{path} contains a non-JSON value: {type(value).__name__}")


def _thaw_json(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _thaw_json(value[key]) for key in sorted(value)}
    if isinstance(value, tuple):
        return [_thaw_json(item) for item in value]
    return value


@dataclass(frozen=True, slots=True)
class SourceRef:
    """A versioned source locator with optional content and license identity."""

    source_id: str
    revision: str | None = None
    locator: str | None = None
    content_sha256: str | None = None
    license_id: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.source_id, str) or not self.source_id.strip():
            raise ValueError("source_id cannot be empty")
        _optional_text(self.revision, "revision")
        _optional_text(self.locator, "locator")
        _optional_text(self.license_id, "license_id")
        if self.content_sha256 is not None and (
            not isinstance(self.content_sha256, str)
            or not _SHA256.fullmatch(self.content_sha256)
        ):
            raise ValueError("content_sha256 must be a 64-character hexadecimal SHA-256")

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_id": self.source_id,
            "revision": self.revision,
            "locator": self.locator,
            "content_sha256": self.content_sha256.lower() if self.content_sha256 else None,
            "license_id": self.license_id,
        }


@dataclass(frozen=True, slots=True)
class EvidenceRecord:
    """An immutable claim/check record; evidence kind is not a verification result."""

    kind: EvidenceKind
    status: EvidenceStatus
    statement: str
    source_refs: tuple[SourceRef, ...] = ()
    method: str | None = None
    limitations: tuple[str, ...] = ()
    record_id: str = field(default_factory=lambda: str(uuid4()))
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.kind, EvidenceKind):
            raise ValueError("kind must be an EvidenceKind")
        if not isinstance(self.status, EvidenceStatus):
            raise ValueError("status must be an EvidenceStatus")
        if not isinstance(self.statement, str) or not self.statement.strip():
            raise ValueError("Evidence statement cannot be empty")
        if self.status is EvidenceStatus.PASS and self.kind is EvidenceKind.UNKNOWN:
            raise ValueError("UNKNOWN evidence cannot have PASS status")
        if not isinstance(self.source_refs, tuple) or any(
            not isinstance(source, SourceRef) for source in self.source_refs
        ):
            raise ValueError("source_refs must be an immutable tuple of SourceRef records")
        source_keys = tuple(
            (source.source_id, source.revision, source.locator) for source in self.source_refs
        )
        if len(source_keys) != len(set(source_keys)):
            raise ValueError("source_refs must not contain duplicate source locators")
        if not isinstance(self.limitations, tuple):
            raise ValueError("limitations must be an immutable tuple")
        if any(not isinstance(item, str) or not item.strip() for item in self.limitations):
            raise ValueError("limitations entries must be non-empty strings")
        if len(self.limitations) != len(set(self.limitations)):
            raise ValueError("limitations must not contain duplicates")
        _optional_text(self.method, "method")
        if not isinstance(self.record_id, str) or not self.record_id.strip():
            raise ValueError("record_id cannot be empty")
        if not isinstance(self.created_at, str) or not self.created_at.strip():
            raise ValueError("created_at cannot be empty")
        try:
            timestamp = datetime.fromisoformat(self.created_at.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError("created_at must be ISO-8601") from exc
        if timestamp.tzinfo is None or timestamp.utcoffset() is None:
            raise ValueError("created_at must include a timezone")
        if not isinstance(self.metadata, Mapping):
            raise ValueError("metadata must be a JSON object")
        object.__setattr__(self, "metadata", _freeze_json(self.metadata))

    def to_dict(self) -> dict[str, Any]:
        return {
            "record_id": self.record_id,
            "kind": self.kind.value,
            "status": self.status.value,
            "statement": self.statement,
            "source_refs": [source.to_dict() for source in self.source_refs],
            "method": self.method,
            "limitations": list(self.limitations),
            "created_at": self.created_at,
            "metadata": _thaw_json(self.metadata),
        }


@dataclass(frozen=True, slots=True)
class EvidenceGateResult:
    """Conservative aggregate; every supplied record is treated as required."""

    status: EvidenceStatus
    record_ids: tuple[str, ...]
    pass_count: int
    fail_count: int
    skipped_count: int
    unknown_count: int
    blockers: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "record_ids": list(self.record_ids),
            "counts": {
                "PASS": self.pass_count,
                "FAIL": self.fail_count,
                "SKIPPED": self.skipped_count,
                "UNKNOWN": self.unknown_count,
            },
            "blockers": list(self.blockers),
        }


def evaluate_evidence_gate(records: tuple[EvidenceRecord, ...]) -> EvidenceGateResult:
    """Aggregate required evidence; missing evidence is UNKNOWN, never PASS."""
    if not isinstance(records, tuple):
        raise ValueError("records must be an immutable tuple")
    if any(not isinstance(record, EvidenceRecord) for record in records):
        raise ValueError("records must contain EvidenceRecord values")
    record_ids = tuple(record.record_id for record in records)
    if len(record_ids) != len(set(record_ids)):
        raise ValueError("evidence record IDs must be unique")
    counts = {status: sum(record.status is status for record in records)
              for status in EvidenceStatus}
    if not records:
        status = EvidenceStatus.UNKNOWN
    elif counts[EvidenceStatus.FAIL]:
        status = EvidenceStatus.FAIL
    elif counts[EvidenceStatus.UNKNOWN]:
        status = EvidenceStatus.UNKNOWN
    elif counts[EvidenceStatus.SKIPPED]:
        status = EvidenceStatus.SKIPPED
    else:
        status = EvidenceStatus.PASS
    blockers = tuple(sorted(
        record.record_id for record in records if record.status is not EvidenceStatus.PASS
    ))
    return EvidenceGateResult(
        status=status,
        record_ids=tuple(sorted(record_ids)),
        pass_count=counts[EvidenceStatus.PASS],
        fail_count=counts[EvidenceStatus.FAIL],
        skipped_count=counts[EvidenceStatus.SKIPPED],
        unknown_count=counts[EvidenceStatus.UNKNOWN],
        blockers=blockers,
    )
