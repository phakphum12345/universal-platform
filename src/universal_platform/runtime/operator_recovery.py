"""Authenticated, evidence-bound recovery for quarantined worker leases.

Authentication and authorization are deliberately delegated to a trusted host
adapter. This module does not implement passwords, tokens, sessions, or an
identity provider and must not be wired to a mock authorizer in production.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Protocol
from uuid import uuid4

from .process_reconciliation import (
    ProcessIdentityInspector,
    ProcessLiveness,
    ProcessLivenessEvidence,
)
from .resources.durable_allocator import DurableResourceAllocator

FORCE_RELEASE_PERMISSION = "runtime.worker.force_release"


class OperatorAuthorizationError(PermissionError):
    """The host identity adapter did not authenticate and authorize the operator."""


@dataclass(frozen=True, slots=True)
class OperatorPrincipal:
    """Identity assertion returned by the trusted host authorization adapter."""

    subject: str
    authentication_method: str
    authenticated_at: datetime
    authorization_reference: str

    def __post_init__(self) -> None:
        for name, value in (
            ("subject", self.subject),
            ("authentication_method", self.authentication_method),
            ("authorization_reference", self.authorization_reference),
        ):
            if not isinstance(value, str) or not value.strip() or "\\x00" in value:
                raise ValueError(f"{name} must be a non-empty NUL-free string")
        if (
            not isinstance(self.authenticated_at, datetime)
            or self.authenticated_at.tzinfo is None
            or self.authenticated_at.utcoffset() is None
        ):
            raise ValueError("authenticated_at must be timezone-aware")


class OperatorAuthorizationPort(Protocol):
    """Host-provided authentication + authorization boundary.

    Implementations must verify a real operator credential/session and enforce
    the requested permission. Returning a principal is an authorization grant;
    callers must not construct one from untrusted request fields.
    """

    def authenticate_and_authorize(
        self,
        context: object,
        *,
        permission: str,
    ) -> OperatorPrincipal: ...


@dataclass(frozen=True, slots=True)
class OperatorRecoveryResult:
    lease_id: str
    status: ProcessLiveness
    action: str
    reason: str
    evidence: ProcessLivenessEvidence | None = None
    audit_reference: str | None = None


class OperatorRecoveryService:
    """Release a quarantined lease only after authorization and fresh ABSENT proof."""

    def __init__(
        self,
        allocator: DurableResourceAllocator,
        inspector: ProcessIdentityInspector,
        authorizer: OperatorAuthorizationPort,
        *,
        max_evidence_age: timedelta = timedelta(seconds=30),
        max_authentication_age: timedelta = timedelta(minutes=5),
        allowed_clock_skew: timedelta = timedelta(seconds=2),
    ) -> None:
        if not isinstance(allocator, DurableResourceAllocator):
            raise TypeError("allocator must be a DurableResourceAllocator")
        if not callable(getattr(inspector, "inspect", None)):
            raise TypeError("inspector must provide inspect(identity)")
        if not callable(getattr(authorizer, "authenticate_and_authorize", None)):
            raise TypeError("authorizer must provide authenticate_and_authorize(context, permission=...)")
        for name, value in (
            ("max_evidence_age", max_evidence_age),
            ("max_authentication_age", max_authentication_age),
        ):
            if not isinstance(value, timedelta) or value <= timedelta(0):
                raise ValueError(f"{name} must be a positive timedelta")
        if not isinstance(allowed_clock_skew, timedelta) or allowed_clock_skew < timedelta(0):
            raise ValueError("allowed_clock_skew must be a non-negative timedelta")
        self._allocator = allocator
        self._inspector = inspector
        self._authorizer = authorizer
        self._max_evidence_age = max_evidence_age
        self._max_authentication_age = max_authentication_age
        self._allowed_clock_skew = allowed_clock_skew

    def recover(
        self,
        lease_id: str,
        reason: str,
        operator_context: object,
        *,
        now: datetime | None = None,
    ) -> OperatorRecoveryResult:
        if not isinstance(lease_id, str) or not lease_id.strip():
            raise ValueError("lease_id must be a non-empty string")
        if not isinstance(reason, str) or not reason.strip() or len(reason) > 2000 or "\\x00" in reason:
            raise ValueError("reason must be non-empty, NUL-free and at most 2000 characters")
        captured = now or datetime.now(UTC)
        if not isinstance(captured, datetime) or captured.tzinfo is None or captured.utcoffset() is None:
            raise ValueError("now must be timezone-aware")

        principal = self._authorizer.authenticate_and_authorize(
            operator_context,
            permission=FORCE_RELEASE_PERMISSION,
        )
        if not isinstance(principal, OperatorPrincipal):
            raise OperatorAuthorizationError(
                "host authorization adapter returned no trusted OperatorPrincipal"
            )
        authenticated_at = principal.authenticated_at.astimezone(UTC)
        current = captured.astimezone(UTC)
        if authenticated_at > current + self._allowed_clock_skew:
            raise OperatorAuthorizationError("operator authentication timestamp is in the future")
        if current - authenticated_at > self._max_authentication_age:
            raise OperatorAuthorizationError("operator authentication is stale; re-authentication is required")

        quarantined = {
            lease.lease_id: (lease, quarantine_reason)
            for lease, quarantine_reason in self._allocator.quarantined_leases()
        }
        selected = quarantined.get(lease_id)
        if selected is None:
            return OperatorRecoveryResult(
                lease_id, ProcessLiveness.UNKNOWN, "not_found",
                "lease is not currently quarantined",
            )
        lease, _quarantine_reason = selected
        if lease.lease_kind != "supervised_worker" or lease.process_identity is None:
            return OperatorRecoveryResult(
                lease_id, ProcessLiveness.UNKNOWN, "retained_quarantine",
                "lease has no bound supervised-worker process identity",
            )

        try:
            evidence = self._inspector.inspect(lease.process_identity)
        except Exception as error:  # noqa: BLE001 - inspection failure must fail closed
            return OperatorRecoveryResult(
                lease_id, ProcessLiveness.UNKNOWN, "retained_quarantine",
                f"process liveness inspection failed ({error.__class__.__name__})",
            )
        if not isinstance(evidence, ProcessLivenessEvidence) or evidence.identity != lease.process_identity:
            return OperatorRecoveryResult(
                lease_id, ProcessLiveness.UNKNOWN, "retained_quarantine",
                "process inspector returned invalid or mismatched identity evidence",
            )
        observed_at = evidence.observed_at.astimezone(UTC)
        age = current - observed_at
        if observed_at > current + self._allowed_clock_skew or age > self._max_evidence_age:
            return OperatorRecoveryResult(
                lease_id, ProcessLiveness.UNKNOWN, "retained_quarantine",
                "process liveness evidence is stale or from the future",
                evidence,
            )
        if evidence.status is not ProcessLiveness.ABSENT:
            return OperatorRecoveryResult(
                lease_id, evidence.status, "retained_quarantine",
                evidence.reason or f"process liveness is {evidence.status.value}; capacity remains reserved",
                evidence,
            )

        audit_reference = self._allocator._force_release_quarantined(
            lease_id,
            operator_subject=principal.subject,
            authentication_method=principal.authentication_method,
            authenticated_at=principal.authenticated_at,
            authorization_reference=principal.authorization_reference,
            permission=FORCE_RELEASE_PERMISSION,
            reason=reason.strip(),
            evidence=evidence,
            audit_event_id=uuid4().hex,
        )
        if audit_reference is None:
            return OperatorRecoveryResult(
                lease_id, ProcessLiveness.ABSENT, "already_resolved",
                "lease was resolved by another recovery action",
                evidence,
            )
        return OperatorRecoveryResult(
            lease_id, ProcessLiveness.ABSENT, "released",
            "quarantined worker lease was force-released with a durable operator audit event",
            evidence,
            audit_reference,
        )


__all__ = [
    "FORCE_RELEASE_PERMISSION",
    "OperatorAuthorizationError",
    "OperatorAuthorizationPort",
    "OperatorPrincipal",
    "OperatorRecoveryResult",
    "OperatorRecoveryService",
]
