"""A dependency-free forest of rigid coordinate frames.

Each non-root frame has exactly one parent. The graph resolves a rigid
transform between any two connected frames. It is a coordinate utility, not
an assembly constraint or motion solver.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field

from .errors import InvalidModelError
from .transforms import RigidTransform


@dataclass(slots=True)
class FrameGraph:
    """Store parent-to-child transforms and resolve paths in either direction."""

    _parent_to_child: dict[str, RigidTransform] = field(default_factory=dict)
    _children: dict[str, set[str]] = field(default_factory=dict)
    _frames: set[str] = field(default_factory=set)

    @property
    def frames(self) -> frozenset[str]:
        return frozenset(self._frames)

    @property
    def roots(self) -> frozenset[str]:
        children = set(self._parent_to_child)
        return frozenset(self._frames - children)

    def add_frame(self, frame_id: str) -> None:
        if not isinstance(frame_id, str) or not frame_id.strip():
            raise InvalidModelError("Frame identifier is required")
        if frame_id in self._frames:
            raise InvalidModelError(f"Frame already exists: {frame_id}")
        self._frames.add(frame_id)
        self._children.setdefault(frame_id, set())

    def add_transform(self, transform: RigidTransform) -> None:
        """Add a parent-to-child edge; each child may have only one parent."""
        parent, child = transform.from_frame, transform.to_frame
        if parent == child:
            raise InvalidModelError("A frame cannot be its own parent")
        if child in self._parent_to_child:
            raise InvalidModelError(f"Frame already has a parent: {child}")
        if parent not in self._frames:
            self.add_frame(parent)
        if child not in self._frames:
            self.add_frame(child)
        if self._has_path(child, parent):
            raise InvalidModelError("Adding this transform would create a cycle")
        self._parent_to_child[child] = transform
        self._children.setdefault(parent, set()).add(child)

    def _neighbors(self, frame_id: str):
        for child in self._children.get(frame_id, ()):
            yield child, self._parent_to_child[child]
        parent_transform = self._parent_to_child.get(frame_id)
        if parent_transform is not None:
            yield parent_transform.from_frame, parent_transform.inverse()

    def _has_path(self, start: str, target: str) -> bool:
        if start == target:
            return True
        seen = {start}
        queue = deque([start])
        while queue:
            current = queue.popleft()
            for neighbor, _ in self._neighbors(current):
                if neighbor == target:
                    return True
                if neighbor not in seen:
                    seen.add(neighbor)
                    queue.append(neighbor)
        return False

    def transform_between(self, from_frame: str, to_frame: str) -> RigidTransform:
        """Resolve the mapping from one known frame to another."""
        if from_frame not in self._frames or to_frame not in self._frames:
            missing = from_frame if from_frame not in self._frames else to_frame
            raise InvalidModelError(f"Unknown coordinate frame: {missing}")
        if from_frame == to_frame:
            return RigidTransform.identity(from_frame)
        queue = deque([(from_frame, RigidTransform.identity(from_frame))])
        seen = {from_frame}
        while queue:
            current, accumulated = queue.popleft()
            for neighbor, edge in self._neighbors(current):
                if neighbor in seen:
                    continue
                composed = accumulated.then(edge)
                if neighbor == to_frame:
                    return composed
                seen.add(neighbor)
                queue.append((neighbor, composed))
        raise InvalidModelError(
            f"No coordinate-frame path from {from_frame} to {to_frame}"
        )
