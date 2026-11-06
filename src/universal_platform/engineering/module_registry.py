"""Validated, deterministic metadata registry for offline engineering modules.

The registry stores declarations only. It never imports, loads, invokes, or grants
permissions to module code.
"""
from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any

from .errors import InvalidModelError

_IDENTIFIER = re.compile(r"^[a-z0-9]+(?:[._/-][a-z0-9]+)*$")
_SEMVER = re.compile(r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)(?:-[0-9A-Za-z.-]+)?$")
_SCHEMA_VERSION = re.compile(r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$")
_EXECUTION_KINDS = frozenset({"ANALYSIS", "CALCULATION", "SIMULATION", "EXTERNAL_READ"})
_MATURITY = frozenset({
    "CONCEPT", "EXPERIMENTAL", "VALIDATED", "PRODUCTION_CANDIDATE",
    "STABLE", "DEPRECATED",
})


def _require_identifier(value: str, label: str) -> None:
    if not isinstance(value, str) or not _IDENTIFIER.fullmatch(value):
        raise InvalidModelError(f"{label} must be a non-empty stable lowercase identifier")


def _require_unique(values: tuple[str, ...], label: str) -> None:
    if not isinstance(values, tuple):
        raise InvalidModelError(f"{label} must be an immutable tuple")
    for value in values:
        if not isinstance(value, str) or not value.strip():
            raise InvalidModelError(f"{label} entries must be non-empty strings")
    if len(values) != len(set(values)):
        raise InvalidModelError(f"{label} must not contain duplicates")


@dataclass(frozen=True, slots=True)
class ModuleOperation:
    """A declared operation; this record is not an executable callback."""

    operation_id: str
    input_schema_version: str = "1.0"
    output_schema_version: str = "1.0"
    required_permissions: tuple[str, ...] = ()
    execution_kind: str = "CALCULATION"

    def __post_init__(self) -> None:
        _require_identifier(self.operation_id, "operation_id")
        if not isinstance(self.input_schema_version, str) or not _SCHEMA_VERSION.fullmatch(self.input_schema_version):
            raise InvalidModelError("input_schema_version must use MAJOR.MINOR")
        if not isinstance(self.output_schema_version, str) or not _SCHEMA_VERSION.fullmatch(self.output_schema_version):
            raise InvalidModelError("output_schema_version must use MAJOR.MINOR")
        _require_unique(self.required_permissions, "required_permissions")
        if not isinstance(self.execution_kind, str) or self.execution_kind not in _EXECUTION_KINDS:
            raise InvalidModelError(
                "execution_kind must be ANALYSIS, CALCULATION, SIMULATION, or EXTERNAL_READ"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "operation_id": self.operation_id,
            "input_schema_version": self.input_schema_version,
            "output_schema_version": self.output_schema_version,
            "required_permissions": sorted(self.required_permissions),
            "execution_kind": self.execution_kind,
        }


@dataclass(frozen=True, slots=True)
class ModuleManifest:
    """Immutable, versioned declaration for one specialist module."""

    module_id: str
    version: str
    domain: str
    operations: tuple[ModuleOperation, ...]
    dependencies: tuple[str, ...] = ()
    permissions: tuple[str, ...] = ()
    license_id: str = "NOASSERTION"
    maturity: str = "EXPERIMENTAL"

    def __post_init__(self) -> None:
        _require_identifier(self.module_id, "module_id")
        if not isinstance(self.version, str) or not _SEMVER.fullmatch(self.version):
            raise InvalidModelError("version must be a semantic version (MAJOR.MINOR.PATCH)")
        if not isinstance(self.domain, str) or not self.domain.strip():
            raise InvalidModelError("domain must be a non-empty string")
        if not isinstance(self.operations, tuple):
            raise InvalidModelError("operations must be an immutable tuple")
        if not self.operations:
            raise InvalidModelError("a module must declare at least one operation")
        if any(not isinstance(item, ModuleOperation) for item in self.operations):
            raise InvalidModelError("operations must contain ModuleOperation records")
        operation_ids = tuple(item.operation_id for item in self.operations)
        _require_unique(operation_ids, "operation IDs")
        _require_unique(self.dependencies, "dependencies")
        _require_unique(self.permissions, "permissions")
        if self.module_id in self.dependencies:
            raise InvalidModelError("a module cannot depend on itself")
        for dependency in self.dependencies:
            _require_identifier(dependency, "dependency module_id")
        if not isinstance(self.license_id, str) or not self.license_id.strip():
            raise InvalidModelError("license_id must be explicit; use NOASSERTION when unknown")
        if not isinstance(self.maturity, str) or self.maturity not in _MATURITY:
            raise InvalidModelError(f"maturity must be one of {sorted(_MATURITY)}")
        declared = set(self.permissions)
        for operation in self.operations:
            undeclared = set(operation.required_permissions) - declared
            if undeclared:
                raise InvalidModelError(
                    f"operation {operation.operation_id} requires undeclared permissions: "
                    f"{sorted(undeclared)}"
                )

    def to_dict(self) -> dict[str, Any]:
        return {
            "module_id": self.module_id,
            "version": self.version,
            "domain": self.domain,
            "dependencies": sorted(self.dependencies),
            "permissions": sorted(self.permissions),
            "license_id": self.license_id,
            "maturity": self.maturity,
            "operations": [
                operation.to_dict()
                for operation in sorted(self.operations, key=lambda item: item.operation_id)
            ],
        }


class ModuleRegistry:
    """In-memory metadata registry with deterministic dependency ordering.

    Registration has no code-loading side effects. Callers must separately
    implement and govern any future adapter execution boundary.
    """

    SCHEMA_VERSION = "1.0"

    def __init__(self) -> None:
        self._modules: dict[str, ModuleManifest] = {}

    def register(self, manifest: ModuleManifest) -> None:
        if not isinstance(manifest, ModuleManifest):
            raise InvalidModelError("only validated ModuleManifest records can be registered")
        if manifest.module_id in self._modules:
            raise InvalidModelError(f"duplicate module_id: {manifest.module_id}")
        self._modules[manifest.module_id] = manifest

    def get(self, module_id: str) -> ModuleManifest:
        _require_identifier(module_id, "module_id")
        try:
            return self._modules[module_id]
        except KeyError as exc:
            raise InvalidModelError(f"unknown module_id: {module_id}") from exc

    def list_modules(self) -> tuple[ModuleManifest, ...]:
        return tuple(self._modules[key] for key in sorted(self._modules))

    def resolve_operation(self, module_id: str, operation_id: str) -> ModuleOperation:
        _require_identifier(operation_id, "operation_id")
        manifest = self.get(module_id)
        for operation in manifest.operations:
            if operation.operation_id == operation_id:
                return operation
        raise InvalidModelError(
            f"unknown operation {operation_id!r} for module {module_id!r}"
        )

    def dependency_order(self) -> tuple[str, ...]:
        """Return dependencies before dependants, or fail on missing/cyclic edges."""
        missing = sorted({
            dependency
            for manifest in self._modules.values()
            for dependency in manifest.dependencies
            if dependency not in self._modules
        })
        if missing:
            raise InvalidModelError(f"missing module dependencies: {missing}")

        remaining = {
            module_id: set(manifest.dependencies)
            for module_id, manifest in self._modules.items()
        }
        ordered: list[str] = []
        while remaining:
            ready = sorted(
                module_id for module_id, dependencies in remaining.items()
                if not dependencies
            )
            if not ready:
                raise InvalidModelError(
                    f"module dependency cycle detected among: {sorted(remaining)}"
                )
            for module_id in ready:
                ordered.append(module_id)
                del remaining[module_id]
            for dependencies in remaining.values():
                dependencies.difference_update(ready)
        return tuple(ordered)

    def snapshot(self) -> dict[str, Any]:
        """Return a deterministic JSON-compatible registry snapshot."""
        return {
            "schema_version": self.SCHEMA_VERSION,
            "modules": [manifest.to_dict() for manifest in self.list_modules()],
        }
