"""Governed runtime resource management, supervision and recovery primitives."""
from .resources.registry import ResourceRegistry
from .resources.models import ResourceRecord, ResourceState
from .supervisor import PythonProcessSupervisor, WorkerResult, WorkerSpec, WorkerTerminationError
from .worker_ipc import WorkerIPCClient, WorkerIPCError
from .worker_protocol import WorkerFrame, WorkerProtocolError

__all__ = [
    "PythonProcessSupervisor",
    "ResourceRecord",
    "ResourceRegistry",
    "ResourceState",
    "WorkerFrame",
    "WorkerIPCClient",
    "WorkerIPCError",
    "WorkerProtocolError",
    "WorkerResult",
    "WorkerSpec",
    "WorkerTerminationError",
]
