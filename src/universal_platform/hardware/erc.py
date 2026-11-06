"""Deterministic, offline electrical rule checks for normalized schematics.

This is a conservative static ERC ruleset. It is not an electrical simulator,
standards-compliance checker, or proof of physical safety.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import hashlib
import json

from universal_platform.engineering.errors import InvalidModelError
from .schematic import PinElectricalType, SchematicModel


class ERCStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    SKIPPED = "SKIPPED"
    UNKNOWN = "UNKNOWN"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class ERCSeverity(str, Enum):
    BLOCKER = "BLOCKER"
    ERROR = "ERROR"
    WARNING = "WARNING"
    INFO = "INFO"


@dataclass(frozen=True, slots=True)
class ERCFinding:
    finding_id: str
    rule_id: str
    rule_version: str
    severity: ERCSeverity
    status: ERCStatus
    object_refs: tuple[str, ...]
    message: str
    recommendation: str
    evidence: tuple[str, ...]

    def __post_init__(self) -> None:
        for label, value in (("finding_id", self.finding_id), ("rule_id", self.rule_id),
                             ("rule_version", self.rule_version), ("message", self.message),
                             ("recommendation", self.recommendation)):
            if not isinstance(value, str) or not value.strip():
                raise InvalidModelError(f"{label} must be a non-empty string")
        if not isinstance(self.severity, ERCSeverity) or not isinstance(self.status, ERCStatus):
            raise InvalidModelError("finding severity and status must use ERC enums")
        if self.status is not ERCStatus.FAIL:
            raise InvalidModelError("an ERC finding must describe a failed rule")
        if not isinstance(self.object_refs, tuple) or not isinstance(self.evidence, tuple):
            raise InvalidModelError("finding references and evidence must be immutable tuples")
        if any(not isinstance(item, str) or not item for item in self.object_refs + self.evidence):
            raise InvalidModelError("finding references and evidence must be non-empty strings")

    def to_dict(self) -> dict[str, object]:
        return {
            "finding_id": self.finding_id,
            "rule_id": self.rule_id,
            "rule_version": self.rule_version,
            "severity": self.severity.value,
            "status": self.status.value,
            "object_refs": list(self.object_refs),
            "message": self.message,
            "recommendation": self.recommendation,
            "evidence": list(self.evidence),
        }


@dataclass(frozen=True, slots=True)
class ElectricalRuleCheckResult:
    schema_version: str
    ruleset_version: str
    input_sha256: str
    status: ERCStatus
    evaluated_rule_ids: tuple[str, ...]
    skipped_rule_ids: tuple[str, ...]
    findings: tuple[ERCFinding, ...]

    SCHEMA_VERSION = "1.0"
    RULESET_VERSION = "1.0"

    def __post_init__(self) -> None:
        if self.schema_version != self.SCHEMA_VERSION or self.ruleset_version != self.RULESET_VERSION:
            raise InvalidModelError("unsupported ERC result or ruleset version")
        if len(self.input_sha256) != 64 or any(c not in "0123456789abcdef" for c in self.input_sha256):
            raise InvalidModelError("input_sha256 must be a lowercase SHA-256 digest")
        if not isinstance(self.status, ERCStatus):
            raise InvalidModelError("ERC status must use ERCStatus")
        if not all(isinstance(items, tuple) for items in (self.evaluated_rule_ids, self.skipped_rule_ids, self.findings)):
            raise InvalidModelError("ERC result collections must be immutable tuples")
        if any(not isinstance(item, ERCFinding) for item in self.findings):
            raise InvalidModelError("findings must contain ERCFinding records")
        expected = ERCStatus.FAIL if self.findings else ERCStatus.PASS
        if self.status is not expected:
            raise InvalidModelError("ERC status must be FAIL when findings exist and PASS otherwise")

    @property
    def summary(self) -> dict[str, int]:
        return {
            "finding_count": len(self.findings),
            "blocker_count": sum(f.severity is ERCSeverity.BLOCKER for f in self.findings),
            "error_count": sum(f.severity is ERCSeverity.ERROR for f in self.findings),
            "warning_count": sum(f.severity is ERCSeverity.WARNING for f in self.findings),
            "info_count": sum(f.severity is ERCSeverity.INFO for f in self.findings),
        }

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "ruleset_version": self.ruleset_version,
            "input_sha256": self.input_sha256,
            "status": self.status.value,
            "evaluated_rule_ids": list(self.evaluated_rule_ids),
            "skipped_rule_ids": list(self.skipped_rule_ids),
            "summary": self.summary,
            "findings": [finding.to_dict() for finding in self.findings],
            "limitations": [
                "Static pin-type checks only; no voltage, current, timing, or thermal model is inferred.",
                "No external standards, datasheets, net classes, power-domain metadata, or waivers are applied.",
                "A PASS means only that this versioned ruleset found no modeled violations.",
                "No physical board inspection, simulation, certification, or safety approval is implied.",
            ],
        }


_RULES = (
    "ERC-PIN-001",
    "ERC-NET-001",
    "ERC-NET-002",
    "ERC-NET-003",
    "ERC-NET-004",
    "ERC-NET-005",
)
_RULE_VERSION = "1.0"


def _pin_ref(component_id: str, pin_id: str) -> str:
    return f"component:{component_id}/pin:{pin_id}"


def _finding(rule_id: str, severity: ERCSeverity, refs: tuple[str, ...],
             message: str, recommendation: str, evidence: tuple[str, ...]) -> ERCFinding:
    identity = "|".join((rule_id, *refs))
    suffix = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:16]
    return ERCFinding(
        f"{rule_id.lower()}:{suffix}", rule_id, _RULE_VERSION, severity, ERCStatus.FAIL,
        tuple(sorted(refs)), message, recommendation, tuple(sorted(evidence)),
    )


def check_electrical_rules(schematic: SchematicModel) -> ElectricalRuleCheckResult:
    """Run the deterministic static ERC v1.0 ruleset on a validated schematic."""
    if not isinstance(schematic, SchematicModel):
        raise InvalidModelError("schematic must be a validated SchematicModel")

    model_snapshot = json.dumps(schematic.to_dict(), sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    input_digest = hashlib.sha256(model_snapshot.encode("utf-8")).hexdigest()
    pins = {
        (component.component_id, pin.pin_id): pin
        for component in schematic.components for pin in component.pins
    }
    components = {component.component_id: component for component in schematic.components}
    connected = {
        (terminal.component_id, terminal.pin_id)
        for net in schematic.nets for terminal in net.terminals
    }
    findings: list[ERCFinding] = []

    # ERC-PIN-001: unconnected declared pins, excluding explicit NO_CONNECT pins.
    for component in schematic.components:
        for pin in component.pins:
            key = (component.component_id, pin.pin_id)
            if key not in connected and pin.electrical_type is not PinElectricalType.NO_CONNECT:
                ref = _pin_ref(*key)
                findings.append(_finding(
                    "ERC-PIN-001", ERCSeverity.WARNING, (ref,),
                    f"Pin {component.reference_designator}.{pin.number} ({pin.name}) is unconnected.",
                    "Connect the pin or explicitly mark it NO_CONNECT when the design intent permits.",
                    (f"electrical_type={pin.electrical_type.value}", "pin is absent from every declared net"),
                ))

    for net in schematic.nets:
        refs = tuple(_pin_ref(t.component_id, t.pin_id) for t in net.terminals)
        terminal_pins = [pins[(t.component_id, t.pin_id)] for t in net.terminals]
        types = [pin.electrical_type for pin in terminal_pins]
        net_label = net.name or net.net_id
        outputs = [i for i, kind in enumerate(types) if kind is PinElectricalType.OUTPUT]
        power_outputs = [i for i, kind in enumerate(types) if kind is PinElectricalType.POWER_OUT]
        power_inputs = [i for i, kind in enumerate(types) if kind is PinElectricalType.POWER_IN]
        open_drains = [i for i, kind in enumerate(types)
                       if kind in (PinElectricalType.OPEN_DRAIN, PinElectricalType.OPEN_COLLECTOR)]

        # ERC-NET-001: multiple push-pull outputs on one net.
        if len(outputs) > 1:
            selected = tuple(refs[i] for i in outputs)
            findings.append(_finding(
                "ERC-NET-001", ERCSeverity.ERROR, selected,
                f"Net {net_label} joins multiple push-pull OUTPUT pins.",
                "Review the topology; use a supported wired-logic interface or separate the conflicting drivers.",
                tuple(f"{components[t.component_id].reference_designator}.{pins[(t.component_id, t.pin_id)].number}=OUTPUT"
                      for t in net.terminals if pins[(t.component_id, t.pin_id)].electrical_type is PinElectricalType.OUTPUT),
            ))

        # ERC-NET-002: multiple declared power sources on one rail.
        if len(power_outputs) > 1:
            selected = tuple(refs[i] for i in power_outputs)
            findings.append(_finding(
                "ERC-NET-002", ERCSeverity.ERROR, selected,
                f"Net {net_label} joins multiple POWER_OUT pins.",
                "Verify whether the sources are explicitly designed for parallel operation; otherwise isolate the rails.",
                tuple(f"{components[t.component_id].reference_designator}.{pins[(t.component_id, t.pin_id)].number}=POWER_OUT"
                      for t in net.terminals if pins[(t.component_id, t.pin_id)].electrical_type is PinElectricalType.POWER_OUT),
            ))

        # ERC-NET-003: power input without a declared source.
        if power_inputs and not power_outputs:
            selected = tuple(refs[i] for i in power_inputs)
            findings.append(_finding(
                "ERC-NET-003", ERCSeverity.WARNING, selected,
                f"Net {net_label} has POWER_IN pins but no declared POWER_OUT pin.",
                "Add or document the upstream power source. Passive pull-ups and off-sheet sources are not inferred.",
                tuple(f"{components[t.component_id].reference_designator}.{pins[(t.component_id, t.pin_id)].number}=POWER_IN"
                      for t in net.terminals if pins[(t.component_id, t.pin_id)].electrical_type is PinElectricalType.POWER_IN),
            ))

        # ERC-NET-004: power input mixed with a signal driver.
        signal_drivers = [i for i, kind in enumerate(types)
                          if kind in (PinElectricalType.OUTPUT, PinElectricalType.OPEN_DRAIN,
                                      PinElectricalType.OPEN_COLLECTOR, PinElectricalType.BIDIRECTIONAL)]
        if power_inputs and signal_drivers:
            selected = tuple(refs[i] for i in power_inputs + signal_drivers)
            findings.append(_finding(
                "ERC-NET-004", ERCSeverity.ERROR, selected,
                f"Net {net_label} mixes POWER_IN pins with signal-driver pin types.",
                "Check pin classification and net assignment against the component datasheets.",
                tuple(f"{components[t.component_id].reference_designator}.{pins[(t.component_id, t.pin_id)].number}={pins[(t.component_id, t.pin_id)].electrical_type.value}"
                      for t in net.terminals if pins[(t.component_id, t.pin_id)].electrical_type in
                      (PinElectricalType.POWER_IN, PinElectricalType.OUTPUT, PinElectricalType.OPEN_DRAIN,
                       PinElectricalType.OPEN_COLLECTOR, PinElectricalType.BIDIRECTIONAL)),
            ))

        # ERC-NET-005: open-drain/collector nets lack an explicitly declared power source.
        if open_drains and not power_outputs:
            selected = tuple(refs[i] for i in open_drains)
            findings.append(_finding(
                "ERC-NET-005", ERCSeverity.WARNING, selected,
                f"Net {net_label} has open-drain/open-collector pins but no declared POWER_OUT pin.",
                "Verify the pull-up path and voltage domain from the design documentation; a passive pull-up is not inferred.",
                tuple(f"{components[t.component_id].reference_designator}.{pins[(t.component_id, t.pin_id)].number}={types[i].value}"
                      for i, t in enumerate(net.terminals) if i in open_drains),
            ))

    findings.sort(key=lambda item: (item.rule_id, item.finding_id))
    return ElectricalRuleCheckResult(
        ElectricalRuleCheckResult.SCHEMA_VERSION,
        ElectricalRuleCheckResult.RULESET_VERSION,
        input_digest,
        ERCStatus.FAIL if findings else ERCStatus.PASS,
        _RULES,
        (),
        tuple(findings),
    )
