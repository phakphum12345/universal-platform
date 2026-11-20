"""Governed runtime resource management, supervision and recovery primitives."""
from .resources.registry import ResourceRegistry
from .resources.models import ResourceRecord, ResourceState
from .process_identity import ProcessIdentity, capture_process_identity
from .process_reconciliation import ProcessIdentityInspector, ProcessLiveness, ProcessLivenessEvidence
from .supervisor import PythonProcessSupervisor, WorkerResult, WorkerSpec, WorkerTerminationError
from .worker_ipc import WorkerIPCClient, WorkerIPCError

__all__ = [
    "PythonProcessSupervisor",
    "ProcessIdentity",
    "ProcessIdentityInspector",
    "ProcessLiveness",
    "ProcessLivenessEvidence",
    "ResourceRecord",
    "ResourceRegistry",
    "ResourceState",
    "WorkerResult",
    "WorkerTerminationError",
    "WorkerIPCClient",
    "WorkerIPCError",
    "WorkerSpec",
    "capture_process_identity",
]
