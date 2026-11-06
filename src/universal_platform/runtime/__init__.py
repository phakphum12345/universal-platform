"""Governed runtime resource management and recovery primitives."""
from .resources.registry import ResourceRegistry
from .resources.models import ResourceRecord, ResourceState
__all__ = ["ResourceRecord", "ResourceRegistry", "ResourceState"]
