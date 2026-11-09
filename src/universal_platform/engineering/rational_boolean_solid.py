"""Exact rational multi-shell Boolean result contract.

Each shell is independently validated by RationalFacetedSolid. This wrapper
preserves component/cavity semantics without binary64 conversion.
"""
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from hashlib import sha256
import json
import re
from typing import Any

from .errors import InvalidModelError
from .rational_faceted_solid import RationalFacetedSolid, RationalPoint3

_ID = re.compile(r"^[a-z0-9]+(?:[._/-][a-z0-9]+)*$")


def _pair(value: Fraction) -> list[str]:
    return [str(value.numerator), str(value.denominator)]


def _parse_pair(value: object, label: str) -> Fraction:
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        raise InvalidModelError(f"{label} must be a rational numerator/denominator pair")
    if any(not isinstance(part, str) or not re.fullmatch(r"(?:0|-?[1-9][0-9]*)", part)
           for part in value):
        raise InvalidModelError(f"{label} must use canonical decimal integer strings")
    numerator, denominator = int(value[0]), int(value[1])
    if denominator <= 0:
        raise InvalidModelError(f"{label} denominator must be positive")
    result = Fraction(numerator, denominator)
    if (result.numerator, result.denominator) != (numerator, denominator):
        raise InvalidModelError(f"{label} must be reduced")
    return result


@dataclass(frozen=True, slots=True)
class RationalBooleanShell:
    shell_id: str
    role: str
    solid: RationalFacetedSolid
    parent_outer_shell_id: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.shell_id, str) or not _ID.fullmatch(self.shell_id):
            raise InvalidModelError("shell_id must be a stable lowercase identifier")
        if self.role not in ("OUTER", "CAVITY"):
            raise InvalidModelError("rational shell role must be OUTER or CAVITY")
        if not isinstance(self.solid, RationalFacetedSolid):
            raise InvalidModelError("rational shell must contain a validated RationalFacetedSolid")
        if self.solid.exact_signed_volume <= 0:
            raise InvalidModelError("rational shell artifact must have positive exact volume")
        if self.role == "OUTER" and self.parent_outer_shell_id is not None:
            raise InvalidModelError("outer shell cannot name a parent outer shell")
        if self.role == "CAVITY" and (
            not isinstance(self.parent_outer_shell_id, str)
            or not _ID.fullmatch(self.parent_outer_shell_id)
        ):
            raise InvalidModelError("cavity shell must name its parent outer shell")


@dataclass(frozen=True, slots=True)
class RationalBooleanComponent:
    component_id: str
    outer_shell: RationalBooleanShell
    cavity_shells: tuple[RationalBooleanShell, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.component_id, str) or not _ID.fullmatch(self.component_id):
            raise InvalidModelError("component_id must be a stable lowercase identifier")
        if self.outer_shell.role != "OUTER":
            raise InvalidModelError("component outer_shell must have OUTER role")
        if not isinstance(self.cavity_shells, tuple):
            raise InvalidModelError("cavity_shells must be an immutable tuple")
        ids = {self.outer_shell.shell_id}
        for cavity in self.cavity_shells:
            if cavity.role != "CAVITY":
                raise InvalidModelError("component cavity_shells must have CAVITY role")
            if cavity.parent_outer_shell_id != self.outer_shell.shell_id:
                raise InvalidModelError("cavity parent does not match component outer shell")
            if cavity.shell_id in ids:
                raise InvalidModelError("shell identifiers must be unique within a component")
            ids.add(cavity.shell_id)
        if self.exact_net_volume <= 0:
            raise InvalidModelError("component exact net volume must be positive")

    @property
    def exact_net_volume(self) -> Fraction:
        return self.outer_shell.solid.exact_signed_volume - sum(
            (item.solid.exact_signed_volume for item in self.cavity_shells), Fraction(0)
        )


@dataclass(frozen=True, slots=True)
class RationalBooleanSolid:
    result_id: str
    frame_id: str
    length_unit: str
    components: tuple[RationalBooleanComponent, ...]
    source_provenance: tuple[tuple[str, str], ...] = ()

    PROFILE = "RATIONAL_BOOLEAN_SOLID_V1"

    def __post_init__(self) -> None:
        if not isinstance(self.result_id, str) or not _ID.fullmatch(self.result_id):
            raise InvalidModelError("result_id must be a stable lowercase identifier")
        if not isinstance(self.frame_id, str) or not self.frame_id.strip():
            raise InvalidModelError("frame_id is required")
        if not isinstance(self.length_unit, str) or not self.length_unit.strip():
            raise InvalidModelError("length_unit is required")
        if not isinstance(self.components, tuple) or not self.components:
            raise InvalidModelError("rational Boolean result requires at least one component")
        component_ids = [item.component_id for item in self.components]
        if len(set(component_ids)) != len(component_ids):
            raise InvalidModelError("component identifiers must be unique")
        for component in self.components:
            shells = (component.outer_shell,) + component.cavity_shells
            for shell in shells:
                if shell.solid.frame_id != self.frame_id or shell.solid.length_unit != self.length_unit:
                    raise InvalidModelError("all rational shells must share the result frame and unit")
        if not isinstance(self.source_provenance, tuple):
            raise InvalidModelError("source_provenance must be an immutable tuple")
        for source_id, digest in self.source_provenance:
            if (not isinstance(source_id, str) or not _ID.fullmatch(source_id)
                    or not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest)):
                raise InvalidModelError("source provenance must contain stable IDs and SHA-256 digests")

    @property
    def exact_net_volume(self) -> Fraction:
        return sum((item.exact_net_volume for item in self.components), Fraction(0))

    @property
    def shell_count(self) -> int:
        return sum(1 + len(item.cavity_shells) for item in self.components)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema_version": "1.0",
            "profile": self.PROFILE,
            "result_id": self.result_id,
            "frame_id": self.frame_id,
            "length_unit": self.length_unit,
            "components": [
                {
                    "component_id": component.component_id,
                    "outer_shell": {
                        "shell_id": component.outer_shell.shell_id,
                        "role": "OUTER",
                        "parent_outer_shell_id": None,
                        "solid": component.outer_shell.solid.to_dict(),
                    },
                    "cavity_shells": [
                        {
                            "shell_id": shell.shell_id,
                            "role": "CAVITY",
                            "parent_outer_shell_id": shell.parent_outer_shell_id,
                            "solid": shell.solid.to_dict(),
                        }
                        for shell in component.cavity_shells
                    ],
                    "exact_net_volume": _pair(component.exact_net_volume),
                }
                for component in self.components
            ],
            "source_provenance": [
                {"source_id": source_id, "source_sha256": digest}
                for source_id, digest in self.source_provenance
            ],
            "resource_counters": {
                "component_count": len(self.components),
                "shell_count": self.shell_count,
                "vertex_count": sum(
                    len(shell.solid.vertices)
                    for component in self.components
                    for shell in ((component.outer_shell,) + component.cavity_shells)
                ),
                "triangle_count": sum(
                    len(shell.solid.triangles)
                    for component in self.components
                    for shell in ((component.outer_shell,) + component.cavity_shells)
                ),
            },
            "exact_net_volume": _pair(self.exact_net_volume),
        }

    def to_dict(self) -> dict[str, Any]:
        payload = self._payload()
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        return {**payload, "result_sha256": sha256(canonical).hexdigest()}

    @classmethod
    def from_dict(cls, value: object) -> "RationalBooleanSolid":
        if not isinstance(value, dict) or value.get("schema_version") != "1.0" or value.get("profile") != cls.PROFILE:
            raise InvalidModelError("unsupported rational Boolean result schema/profile")
        expected_fields = {
            "schema_version", "profile", "result_id", "frame_id", "length_unit",
            "components", "source_provenance", "resource_counters", "exact_net_volume",
            "result_sha256",
        }
        if set(value) != expected_fields:
            raise InvalidModelError("rational Boolean result has missing or unknown fields")
        digest = value.get("result_sha256")
        payload = {key: item for key, item in value.items() if key != "result_sha256"}
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        if not isinstance(digest, str) or sha256(canonical).hexdigest() != digest:
            raise InvalidModelError("rational Boolean result digest mismatch")
        raw_components = value.get("components")
        if not isinstance(raw_components, list) or not raw_components:
            raise InvalidModelError("rational Boolean components must be a non-empty array")
        components = []
        for raw in raw_components:
            if not isinstance(raw, dict) or set(raw) != {
                "component_id", "outer_shell", "cavity_shells", "exact_net_volume"
            }:
                raise InvalidModelError("invalid rational Boolean component record")
            def parse_shell(item: object, expected_role: str) -> RationalBooleanShell:
                if not isinstance(item, dict) or set(item) != {
                    "shell_id", "role", "parent_outer_shell_id", "solid"
                } or item.get("role") != expected_role:
                    raise InvalidModelError("invalid rational Boolean shell record")
                return RationalBooleanShell(
                    item["shell_id"], item["role"],
                    RationalFacetedSolid.from_dict(item["solid"]),
                    item["parent_outer_shell_id"],
                )
            outer = parse_shell(raw["outer_shell"], "OUTER")
            cavities_raw = raw["cavity_shells"]
            if not isinstance(cavities_raw, list):
                raise InvalidModelError("cavity_shells must be an array")
            cavities = tuple(parse_shell(item, "CAVITY") for item in cavities_raw)
            component = RationalBooleanComponent(raw["component_id"], outer, cavities)
            if component.exact_net_volume != _parse_pair(raw["exact_net_volume"], "component volume"):
                raise InvalidModelError("component exact net volume mismatch")
            components.append(component)
        provenance_raw = value.get("source_provenance")
        if not isinstance(provenance_raw, list):
            raise InvalidModelError("source_provenance must be an array")
        provenance = tuple((item["source_id"], item["source_sha256"]) for item in provenance_raw)
        result = cls(value["result_id"], value["frame_id"], value["length_unit"],
                     tuple(components), provenance)
        if result.exact_net_volume != _parse_pair(value["exact_net_volume"], "result volume"):
            raise InvalidModelError("result exact net volume mismatch")
        if result._payload() != payload:
            raise InvalidModelError("rational Boolean result counters or canonical payload mismatch")
        return result
