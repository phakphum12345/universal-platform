"""Fail-closed OS process-tree liveness inspection for durable worker recovery."""
from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path

from .process_identity import ProcessIdentity


class ProcessLiveness(str, Enum):
    PRESENT = "PRESENT"
    ABSENT = "ABSENT"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True, slots=True)
class ProcessLivenessEvidence:
    identity: ProcessIdentity
    status: ProcessLiveness
    method: str
    observed_at: datetime
    reason: str | None = None
    details: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.identity, ProcessIdentity):
            raise TypeError("identity must be a ProcessIdentity")
        if not isinstance(self.status, ProcessLiveness):
            raise TypeError("status must be a ProcessLiveness")
        if not isinstance(self.method, str) or not self.method.strip():
            raise TypeError("method must be a non-empty string") if not isinstance(self.method, str) else ValueError("method must be a non-empty string")
        if (
            not isinstance(self.observed_at, datetime)
            or self.observed_at.tzinfo is None
            or self.observed_at.utcoffset() is None
        ):
            raise TypeError("observed_at must be a datetime") if not isinstance(self.observed_at, datetime) else ValueError("observed_at must be timezone-aware")
        if self.reason is not None and not isinstance(self.reason, str):
            raise TypeError("reason must be a string or None")
        if not isinstance(self.details, tuple) or any(not isinstance(item, str) for item in self.details):
            raise TypeError("details must be a tuple of strings")

    def to_dict(self) -> dict[str, object]:
        return {
            "status": self.status.value,
            "method": self.method,
            "observed_at": self.observed_at.astimezone(UTC).isoformat(),
            "reason": self.reason,
            "details": list(self.details),
            "process_identity": self.identity.to_dict(),
        }


def _linux_stat_fields(path: Path) -> tuple[str, int, int, int]:
    text = path.read_text(encoding="ascii")
    closing = text.rfind(")")
    if closing < 0:
        raise ValueError("proc stat record has no closing comm delimiter")
    fields = text[closing + 1 :].split()
    if len(fields) < 20:
        raise ValueError("proc stat record is incomplete")
    try:
        state = fields[0]
        process_group_id = int(fields[2])
        session_id = int(fields[3])
        start_ticks = int(fields[19])
    except (ValueError, IndexError) as error:
        raise ValueError("proc stat identity fields are invalid") from error
    if min(process_group_id, session_id, start_ticks) <= 0:
        raise ValueError("proc stat identity fields must be positive")
    return state, process_group_id, session_id, start_ticks


@dataclass(frozen=True, slots=True)
class WorkerReconciliationResult:
    lease_id: str
    status: ProcessLiveness
    action: str
    reason: str | None = None
    evidence: ProcessLivenessEvidence | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.lease_id, str) or not self.lease_id.strip():
            raise TypeError("lease_id must be a non-empty string") if not isinstance(self.lease_id, str) else ValueError("lease_id must be a non-empty string")
        if not isinstance(self.status, ProcessLiveness):
            raise TypeError("status must be a ProcessLiveness")
        if not isinstance(self.action, str) or self.action not in {
            "retained", "released", "quarantined", "retained_quarantine"
        }:
            raise TypeError("action must be a string") if not isinstance(self.action, str) else ValueError("unsupported worker reconciliation action")
        if self.reason is not None and not isinstance(self.reason, str):
            raise TypeError("reason must be a string or None")
        if self.evidence is not None and not isinstance(self.evidence, ProcessLivenessEvidence):
            raise TypeError("evidence must be ProcessLivenessEvidence or None")

    def to_dict(self) -> dict[str, object]:
        return {
            "lease_id": self.lease_id,
            "status": self.status.value,
            "action": self.action,
            "reason": self.reason,
            "evidence": self.evidence.to_dict() if self.evidence is not None else None,
        }


class ProcessIdentityInspector:
    """Inspect exact worker identity without ever degrading to PID-only matching."""

    def __init__(self, *, proc_root: str | os.PathLike[str] = "/proc") -> None:
        self._proc_root = Path(proc_root)

    @staticmethod
    def _evidence(
        identity: ProcessIdentity,
        status: ProcessLiveness,
        method: str,
        *,
        reason: str | None = None,
        details: tuple[str, ...] = (),
    ) -> ProcessLivenessEvidence:
        return ProcessLivenessEvidence(
            identity=identity,
            status=status,
            method=method,
            observed_at=datetime.now(UTC),
            reason=reason,
            details=details,
        )

    def inspect(self, identity: ProcessIdentity) -> ProcessLivenessEvidence:
        if not isinstance(identity, ProcessIdentity):
            raise TypeError("identity must be a ProcessIdentity")
        if identity.platform == "linux":
            if sys.platform != "linux":
                return self._evidence(
                    identity,
                    ProcessLiveness.UNKNOWN,
                    "linux.procfs",
                    reason="Linux process identity cannot be inspected on this platform",
                )
            return self._inspect_linux(identity)
        if identity.platform == "windows":
            if os.name != "nt":
                return self._evidence(
                    identity,
                    ProcessLiveness.UNKNOWN,
                    "windows.job-object",
                    reason="Windows Job Object identity cannot be inspected on this platform",
                )
            return self._inspect_windows(identity)
        return self._evidence(
            identity,
            ProcessLiveness.UNKNOWN,
            "unsupported",
            reason="process identity platform is unsupported",
        )

    def _inspect_linux(self, identity: ProcessIdentity) -> ProcessLivenessEvidence:
        method = "linux.procfs.boot-id-starttime-pgrp-session"
        if identity.process_group_id != identity.pid or identity.session_id != identity.pid:
            return self._evidence(
                identity, ProcessLiveness.UNKNOWN, method,
                reason="worker identity is not its process-group and session leader; safe group attribution is unavailable",
            )
        boot_path = self._proc_root / "sys/kernel/random/boot_id"
        try:
            current_boot_id = boot_path.read_text(encoding="ascii").strip()
        except FileNotFoundError:
            return self._evidence(
                identity, ProcessLiveness.UNKNOWN, method,
                reason="host boot identity is unavailable",
            )
        except OSError as error:
            return self._evidence(
                identity, ProcessLiveness.UNKNOWN, method,
                reason=f"host boot identity cannot be read ({error.__class__.__name__})",
            )
        if not current_boot_id:
            return self._evidence(
                identity, ProcessLiveness.UNKNOWN, method,
                reason="host boot identity is empty",
            )
        if current_boot_id != identity.host_boot_id:
            return self._evidence(
                identity, ProcessLiveness.ABSENT, method,
                reason="host boot ID changed since worker creation",
                details=("previous-boot-processes-cannot-survive",),
            )

        try:
            expected_start = int(identity.creation_token)
        except ValueError:
            return self._evidence(
                identity, ProcessLiveness.UNKNOWN, method,
                reason="stored Linux creation token is not a start-time integer",
            )

        unknown_entries = 0
        leader_pid_reused = False
        group_member_seen = False
        try:
            entries = tuple(self._proc_root.iterdir())
        except OSError as error:
            return self._evidence(
                identity, ProcessLiveness.UNKNOWN, method,
                reason=f"procfs cannot be enumerated ({error.__class__.__name__})",
            )

        for entry in entries:
            if not entry.name.isdecimal():
                continue
            try:
                pid = int(entry.name)
                state, process_group_id, session_id, start_ticks = _linux_stat_fields(
                    entry / "stat"
                )
            except FileNotFoundError:
                # A process exited between directory enumeration and stat read.
                continue
            except (PermissionError, OSError, ValueError):
                unknown_entries += 1
                continue
            if state in {"Z", "X"}:
                continue
            if pid == identity.pid:
                if start_ticks == expected_start:
                    return self._evidence(
                        identity, ProcessLiveness.PRESENT, method,
                        details=("leader-pid-and-starttime-match",),
                    )
                # The PID was reused. Do not mistake the new leader or any
                # newly-created group with the same numeric IDs for this worker.
                leader_pid_reused = True
                continue
            if (
                process_group_id == identity.process_group_id
                and session_id == identity.session_id
            ):
                group_member_seen = True

        if leader_pid_reused and group_member_seen:
            return self._evidence(
                identity, ProcessLiveness.UNKNOWN, method,
                reason="leader PID was reused while matching group IDs remain; refusing ambiguous attribution",
            )
        if group_member_seen:
            return self._evidence(
                identity, ProcessLiveness.PRESENT, method,
                details=("original-process-group-has-live-member",),
            )
        if unknown_entries:
            return self._evidence(
                identity, ProcessLiveness.UNKNOWN, method,
                reason="one or more procfs process records could not be inspected",
                details=(f"uninspectable-process-records:{unknown_entries}",),
            )
        return self._evidence(
            identity, ProcessLiveness.ABSENT, method,
            reason="no matching live leader or original process-group member exists",
            details=("leader-starttime-and-process-group-checked",),
        )

    def _inspect_windows(self, identity: ProcessIdentity) -> ProcessLivenessEvidence:
        method = "windows.named-job-object-active-processes"
        if not identity.job_object_id:
            return self._evidence(
                identity, ProcessLiveness.UNKNOWN, method,
                reason="Windows process identity has no Job Object name",
            )
        try:
            from .windows_job import query_named_job_active_processes

            active_processes = query_named_job_active_processes(identity.job_object_id)
        except (OSError, ValueError) as error:
            return self._evidence(
                identity, ProcessLiveness.UNKNOWN, method,
                reason=f"named Job Object cannot be inspected ({error.__class__.__name__})",
            )
        if active_processes is None:
            return self._evidence(
                identity, ProcessLiveness.ABSENT, method,
                reason="named kill-on-close Job Object no longer exists",
            )
        if active_processes > 0:
            return self._evidence(
                identity, ProcessLiveness.PRESENT, method,
                details=(f"active-job-processes:{active_processes}",),
            )
        return self._evidence(
            identity, ProcessLiveness.ABSENT, method,
            reason="named Job Object has no active processes",
            details=("active-job-processes:0",),
        )


__all__ = [
    "ProcessIdentityInspector",
    "ProcessLiveness",
    "ProcessLivenessEvidence",
    "WorkerReconciliationResult",
]
