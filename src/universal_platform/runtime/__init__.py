"""Governed runtime resource management, supervision and recovery primitives."""
from .process_identity import ProcessIdentity, capture_process_identity
from .process_reconciliation import (
    ProcessIdentityInspector,
    ProcessLiveness,
    ProcessLivenessEvidence,
    WorkerReconciliationResult,
)
from .resources import ResourceRegistry
from .resources.models import ResourceRecord, ResourceState
from .supervisor import (
    PythonProcessSupervisor,
    WorkerResult,
    WorkerSpec,
    WorkerTerminationError,
)
from .worker_ipc import WorkerIPCClient, WorkerIPCError

__all__ = [
    "ProcessIdentity",
    "ProcessIdentityInspector",
    "ProcessLiveness",
    "ProcessLivenessEvidence",
    "PythonProcessSupervisor",
    "ResourceRecord",
    "ResourceRegistry",
    "ResourceState",
    "WorkerIPCClient",
    "WorkerIPCError",
    "WorkerReconciliationResult",
    "WorkerResult",
    "WorkerSpec",
    "WorkerTerminationError",
    "capture_process_identity",
]
