"""Validated, immutable request/response envelopes for engineering modules.

These records define data contracts only. They do not execute modules or grant
permissions.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from math import isfinite
from re import compile as compile_regex
from types import MappingProxyType
from typing import Any
from uuid import uuid4

from .errors import InvalidModelError

_IDENTIFIER = compile_regex(r"^[a-z0-9]+(?:[._/-][a-z0-9]+)*$")
_SCHEMA_VERSION = compile_regex(r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$")
_OPERATIONAL_STATUSES = frozenset({
    "ACCEPTED", "REJECTED", "RUNNING", "COMPLETED", "CANCELLED", "ERROR",
})


def _validate_identifier(value: str, label: str) -> None:
    if not isinstance(value, str) or not _IDENTIFIER.fullmatch(value):
        raise InvalidModelError(f"{label} must be a stable lowercase identifier")


def _validate_text_tuple(values: tuple[str, ...], label: str) -> None:
    if not isinstance(values, tuple):
        raise InvalidModelError(f"{label} must be an immutable tuple")
    for value in values:
        if not isinstance(value, str) or not value.strip():
            raise InvalidModelError(f"{label} entries must be non-empty strings")
    if len(values) != len(set(values)):
        raise InvalidModelError(f"{label} must not contain duplicates")


def _freeze_json(value: Any, path: str = "value") -> Any:
    """Validate JSON-compatible data and recursively detach/freeze containers."""
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if not isfinite(value):
            raise InvalidModelError(f"{path} contains a non-finite number")
        return value
    if isinstance(value, Mapping):
        frozen: dict[str, Any] = {}
        for key, item in value.items():
            if not isinstance(key, str) or not key:
                raise InvalidModelError(f"{path} object keys must be non-empty strings")
            frozen[key] = _freeze_json(item, f"{path}.{key}")
        return MappingProxyType(frozen)
    if isinstance(value, (list, tuple)):
        return tuple(_freeze_json(item, f"{path}[{index}]") for index, item in enumerate(value))
    raise InvalidModelError(f"{path} contains a non-JSON value: {type(value).__name__}")


def _freeze_object(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise InvalidModelError(f"{label} must be a JSON object")
    frozen = _freeze_json(value, label)
    return frozen


def _thaw_json(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _thaw_json(value[key]) for key in sorted(value)}
    if isinstance(value, tuple):
        return [_thaw_json(item) for item in value]
    return value


def _freeze_resource_limits(value: Any) -> Mapping[str, float]:
    if not isinstance(value, Mapping):
        raise InvalidModelError("resource_limits must be an object")
    result: dict[str, float] = {}
    for key, amount in value.items():
        _validate_identifier(key, "resource limit key")
        if isinstance(amount, bool) or not isinstance(amount, (int, float)):
            raise InvalidModelError(f"resource limit {key} must be numeric")
        if not isfinite(float(amount)) or amount < 0:
            raise InvalidModelError(f"resource limit {key} must be finite and non-negative")
        result[key] = float(amount)
    return MappingProxyType(result)


@dataclass(frozen=True, slots=True)
class ModuleRequest:
    """Validated immutable request envelope; permissions remain descriptive."""

    module_id: str
    operation: str
    inputs: Mapping[str, Any]
    schema_version: str = "1.0"
    request_id: str = field(default_factory=lambda: str(uuid4()))
    assumptions: tuple[str, ...] = ()
    source_refs: tuple[str, ...] = ()
    resource_limits: Mapping[str, float] = field(default_factory=dict)
    permissions: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _validate_identifier(self.module_id, "module_id")
        _validate_identifier(self.operation, "operation")
        if not isinstance(self.schema_version, str) or not _SCHEMA_VERSION.fullmatch(self.schema_version):
            raise InvalidModelError("schema_version must use MAJOR.MINOR")
        if not isinstance(self.request_id, str) or not self.request_id.strip():
            raise InvalidModelError("request_id must be a non-empty string")
        _validate_text_tuple(self.assumptions, "assumptions")
        _validate_text_tuple(self.source_refs, "source_refs")
        _validate_text_tuple(self.permissions, "permissions")
        for permission in self.permissions:
            _validate_identifier(permission, "permission")
        object.__setattr__(self, "inputs", _freeze_object(self.inputs, "inputs"))
        object.__setattr__(self, "resource_limits", _freeze_resource_limits(self.resource_limits))

    def to_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "module_id": self.module_id,
            "operation": self.operation,
            "schema_version": self.schema_version,
            "inputs": _thaw_json(self.inputs),
            "assumptions": list(self.assumptions),
            "source_refs": list(self.source_refs),
            "resource_limits": {key: self.resource_limits[key] for key in sorted(self.resource_limits)},
            "permissions": list(self.permissions),
        }


@dataclass(frozen=True, slots=True)
class ModuleResponse:
    """Validated immutable operational response, separate from evidence status."""

    request_id: str
    status: str
    outputs: Mapping[str, Any] = field(default_factory=dict)
    warnings: tuple[str, ...] = ()
    assumptions: tuple[str, ...] = ()
    limitations: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()
    error_code: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.request_id, str) or not self.request_id.strip():
            raise InvalidModelError("request_id must be a non-empty string")
        if not isinstance(self.status, str) or self.status not in _OPERATIONAL_STATUSES:
            raise InvalidModelError(f"status must be one of {sorted(_OPERATIONAL_STATUSES)}")
        _validate_text_tuple(self.warnings, "warnings")
        _validate_text_tuple(self.assumptions, "assumptions")
        _validate_text_tuple(self.limitations, "limitations")
        _validate_text_tuple(self.evidence_refs, "evidence_refs")
        if self.status == "ERROR" and not self.error_code:
            raise InvalidModelError("ERROR responses require error_code")
        if self.error_code is not None:
            if self.status not in {"ERROR", "REJECTED"}:
                raise InvalidModelError("error_code is only valid for ERROR or REJECTED responses")
            _validate_identifier(self.error_code, "error_code")
        object.__setattr__(self, "outputs", _freeze_object(self.outputs, "outputs"))

    def to_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "status": self.status,
            "outputs": _thaw_json(self.outputs),
            "warnings": list(self.warnings),
            "assumptions": list(self.assumptions),
            "limitations": list(self.limitations),
            "evidence_refs": list(self.evidence_refs),
            "error_code": self.error_code,
        }
