"""Protocols for runtime adapters and isolated repair executors."""
from __future__ import annotations
from typing import Protocol, Sequence
from ..health.log_analyzer import LogEvent

class RuntimeAdapter(Protocol):
    adapter_id: str
    resource_kind: str
    capabilities: tuple[str, ...]
    def quiesce(self, resource_id: str) -> None: ...
    def health_check(self, resource_id: str) -> bool: ...
    def canary_check(self, resource_id: str) -> bool: ...
    def resume(self, resource_id: str) -> None: ...
    def rollback(self, resource_id: str) -> None: ...

class RepairExecutor(Protocol):
    sandboxed: bool
    def repair(self, resource_id: str, events: Sequence[LogEvent]) -> bool:
        """Repair in an isolated workspace; never execute log text."""
