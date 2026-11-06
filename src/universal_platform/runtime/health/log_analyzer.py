"""Bounded, dependency-free log parsing and secret redaction."""
from __future__ import annotations
from dataclasses import dataclass
import hashlib
import json
import re

_SECRET_PATTERNS = (
 re.compile(r"(?i)(authorization\s*[:=]\s*bearer\s+)\S+"),
 re.compile(r"(?i)((?:password|passwd|token|secret|api[_-]?key)\s*[:=]\s*)[^\s,;]+"),
)
_ERROR = re.compile(r"(?i)\b(error|critical|fatal|exception|traceback|timed?\s*out|timeout)\b")
_COMPONENT = re.compile(r"(?i)\b(?:component|resource|module)[_-]?id\s*[:=]\s*([a-z0-9_.:/-]+)")

@dataclass(frozen=True, slots=True)
class LogEvent:
    severity: str
    source: str
    component_id: str | None
    message: str
    fingerprint: str

def _redact(value: str) -> str:
    for pattern in _SECRET_PATTERNS:
        value = pattern.sub(r"\1[REDACTED]", value)
    return value

def analyze_logs(log_text: str, *, source: str = "application", max_lines: int = 10_000) -> tuple[LogEvent, ...]:
    """Extract error evidence from supplied text; never reads files or executes content."""
    if not isinstance(log_text, str):
        raise TypeError("log_text must be a string")
    if max_lines < 1:
        raise ValueError("max_lines must be positive")
    events: list[LogEvent] = []
    for raw_line in log_text.splitlines()[:max_lines]:
        line = raw_line.strip()
        if not line:
            continue
        severity, component_id, message = "ERROR", None, line
        try:
            payload = json.loads(line)
        except (json.JSONDecodeError, TypeError):
            payload = None
        if isinstance(payload, dict):
            severity = str(payload.get("level", payload.get("severity", "INFO"))).upper()
            component = payload.get("component_id", payload.get("resource_id"))
            component_id = str(component) if component is not None else None
            message = str(payload.get("message", line))
            if severity not in {"ERROR", "CRITICAL", "FATAL", "EXCEPTION"}:
                continue
        else:
            match = _ERROR.search(line)
            if match is None:
                continue
            severity = "CRITICAL" if match.group(1).upper() in {"CRITICAL", "FATAL"} else "ERROR"
            component_match = _COMPONENT.search(line)
            component_id = component_match.group(1) if component_match else None
        message = _redact(message)[:2_000]
        identity = f"{source}\\0{component_id or ''}\\0{severity}\\0{message}"
        fingerprint = hashlib.sha256(identity.encode("utf-8")).hexdigest()
        events.append(LogEvent(severity, source, component_id, message, fingerprint))
    return tuple(events)
