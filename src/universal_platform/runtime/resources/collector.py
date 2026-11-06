"""Adapter-driven resource sampling and immutable snapshot publication."""
from __future__ import annotations

from datetime import datetime, timezone
import os
from pathlib import Path
import shutil
from threading import RLock
from typing import Callable, Iterable, Protocol

from .models import ResourceMetric, ResourceSnapshot
from .registry import ResourceRegistry


class ResourceMetricProvider(Protocol):
    def collect(self, resource_id: str) -> Iterable[ResourceMetric]:
        """Return current measurements with explicit units."""


class ResourceSnapshotCollector:
    """Collects measurements from registered providers and records monotonic snapshots."""

    def __init__(
        self,
        registry: ResourceRegistry,
        *,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._registry = registry
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._providers: dict[str, ResourceMetricProvider] = {}
        self._sequences: dict[str, int] = {}
        self._lock = RLock()

    def register_provider(self, resource_id: str, provider: ResourceMetricProvider) -> None:
        self._registry.get(resource_id)
        if not callable(getattr(provider, "collect", None)):
            raise TypeError("provider must implement collect(resource_id)")
        with self._lock:
            if resource_id in self._providers:
                raise ValueError(f"resource provider already registered: {resource_id}")
            self._providers[resource_id] = provider

    def collect(self, resource_id: str) -> ResourceSnapshot:
        self._registry.get(resource_id)
        with self._lock:
            try:
                provider = self._providers[resource_id]
            except KeyError as exc:
                raise KeyError(f"no resource provider registered: {resource_id}") from exc
            metrics = tuple(provider.collect(resource_id))
            captured = self._clock()
            sequence = self._sequences.get(resource_id, 0) + 1
            snapshot = ResourceSnapshot(resource_id, sequence, captured, metrics)
            self._registry.record_snapshot(snapshot)
            self._sequences[resource_id] = sequence
            return snapshot

    def collect_all(self) -> tuple[ResourceSnapshot, ...]:
        with self._lock:
            resource_ids = tuple(sorted(self._providers))
        return tuple(self.collect(resource_id) for resource_id in resource_ids)


class LocalSystemResourceProvider:
    """Dependency-free host metrics where the current OS exposes them.

    Reports logical CPU count, POSIX memory totals when sysconf supports them,
    configured-path disk usage, and Linux /proc/net/dev byte counters. GPU and
    CPU utilization are intentionally omitted rather than guessed.
    """

    def __init__(
        self,
        *,
        disk_path: str | os.PathLike[str] = ".",
        network_stats_path: str | os.PathLike[str] = "/proc/net/dev",
    ) -> None:
        self._disk_path = Path(disk_path).resolve(strict=True)
        self._network_stats_path = Path(network_stats_path)

    def collect(self, resource_id: str) -> tuple[ResourceMetric, ...]:
        metrics: list[ResourceMetric] = []
        cpu_count = os.cpu_count()
        if cpu_count is not None:
            metrics.append(ResourceMetric("cpu.logical_cores", cpu_count, "cores"))
        metrics.extend(self._memory_metrics())
        disk = shutil.disk_usage(self._disk_path)
        metrics.extend((
            ResourceMetric("disk.total", disk.total, "bytes"),
            ResourceMetric("disk.used", disk.used, "bytes"),
            ResourceMetric("disk.free", disk.free, "bytes"),
        ))
        metrics.extend(self._network_metrics())
        return tuple(metrics)

    @staticmethod
    def _memory_metrics() -> tuple[ResourceMetric, ...]:
        if os.name == "nt" or not hasattr(os, "sysconf"):
            return ()
        try:
            page_size = int(os.sysconf("SC_PAGE_SIZE"))
            total_pages = int(os.sysconf("SC_PHYS_PAGES"))
            available_pages = int(os.sysconf("SC_AVPHYS_PAGES"))
        except (OSError, ValueError, TypeError, AttributeError):
            return ()
        if page_size <= 0 or total_pages < 0 or available_pages < 0:
            return ()
        total = page_size * total_pages
        available = min(total, page_size * available_pages)
        return (
            ResourceMetric("memory.total", total, "bytes"),
            ResourceMetric("memory.available", available, "bytes"),
        )

    def _network_metrics(self) -> tuple[ResourceMetric, ...]:
        if not self._network_stats_path.is_file():
            return ()
        try:
            content = self._network_stats_path.read_text(encoding="ascii")
        except (OSError, UnicodeError):
            return ()
        if len(content) > 1_000_000:
            return ()
        received = 0
        transmitted = 0
        found = False
        for line in content.splitlines()[2:]:
            if ":" not in line:
                continue
            _, values = line.split(":", 1)
            columns = values.split()
            if len(columns) < 9:
                continue
            try:
                received += int(columns[0])
                transmitted += int(columns[8])
                found = True
            except ValueError:
                continue
        if not found:
            return ()
        return (
            ResourceMetric("network.received", received, "bytes"),
            ResourceMetric("network.transmitted", transmitted, "bytes"),
        )
