"""Versioned module request/response envelopes."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

@dataclass(frozen=True, slots=True)
class ModuleRequest:
    module_id: str
    operation: str
    inputs: dict[str, Any]
    schema_version: str = "1.0"
    request_id: str = field(default_factory=lambda: str(uuid4()))
    assumptions: tuple[str, ...] = ()
    source_refs: tuple[str, ...] = ()
    resource_limits: dict[str, float] = field(default_factory=dict)
    permissions: tuple[str, ...] = ()

@dataclass(frozen=True, slots=True)
class ModuleResponse:
    request_id: str
    status: str
    outputs: dict[str, Any] = field(default_factory=dict)
    warnings: tuple[str, ...] = ()
    assumptions: tuple[str, ...] = ()
    limitations: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()
    error_code: str | None = None
