"""Governed runtime resource management, supervision and recovery primitives."""
from .resources.registry import ResourceRegistry
from .resources.models import ResourceRecord, ResourceState
from .supervisor import PythonProcessSupervisor, WorkerResult, WorkerSpec, WorkerTerminationError
from .worker_ipc import WorkerIPCClient, WorkerIPCError

__all__ = [
    "PythonProcessSupervisor",
    "ResourceRecord",
    "ResourceRegistry",
    "ResourceState",
    "WorkerResult",
    "WorkerTerminationError",
    "WorkerIPCClient",
    "WorkerIPCError",
    "WorkerSpec",
]
