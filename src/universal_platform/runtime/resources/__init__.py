"""Typed runtime resources, snapshots, allocation and lease primitives."""
from .allocator import ResourceAllocator, ResourceLease
from .collector import (
    LocalSystemResourceProvider,
    ResourceMetricProvider,
    ResourceSnapshotCollector,
)
from .models import ResourceMetric, ResourceRecord, ResourceSnapshot, ResourceState
from .registry import ResourceRegistry

__all__ = [
    "LocalSystemResourceProvider",
    "ResourceAllocator",
    "ResourceLease",
    "ResourceMetric",
    "ResourceMetricProvider",
    "ResourceRecord",
    "ResourceRegistry",
    "ResourceSnapshot",
    "ResourceSnapshotCollector",
    "ResourceState",
]
