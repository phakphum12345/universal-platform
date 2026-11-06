"""Runtime adapter contracts and governed adapter discovery."""
from .base import RuntimeAdapter, RepairExecutor
from .catalog import (
    AdapterCandidate,
    AdapterRegistry,
    AdapterReplacement,
    AdapterReplacementCoordinator,
    RuntimeAdapterRouter,
)

__all__ = [
    "AdapterCandidate",
    "AdapterRegistry",
    "AdapterReplacement",
    "AdapterReplacementCoordinator",
    "RuntimeAdapterRouter",
    "RepairExecutor",
    "RuntimeAdapter",
]
