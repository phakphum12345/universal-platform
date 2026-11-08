"""Conservative, deterministic three-way merge analysis for FeatureHistory DAGs.

This module is pure: it does not persist revisions, mutate stores, execute
geometry, or resolve conflicts by choosing a side.
"""
from __future__ import annotations

from dataclasses import dataclass
import heapq
from itertools import combinations

from .errors import InvalidModelError
from .feature_history import FeatureHistory, FeatureNode


@dataclass(frozen=True, slots=True)
class FeatureHistoryMergeConflict:
    category: str
    feature_id: str | None
    detail: str

    def to_dict(self) -> dict[str, object]:
        return {
            "category": self.category,
            "feature_id": self.feature_id,
            "detail": self.detail,
        }


@dataclass(frozen=True, slots=True)
class FeatureHistoryMergeResult:
    merged_history: FeatureHistory | None
    conflicts: tuple[FeatureHistoryMergeConflict, ...]

    @property
    def successful(self) -> bool:
        return self.merged_history is not None and not self.conflicts

    def to_dict(self) -> dict[str, object]:
        return {
            "successful": self.successful,
            "merged_history": self.merged_history.to_dict() if self.merged_history else None,
            "conflicts": [item.to_dict() for item in self.conflicts],
        }


def _merge_membership(
    base: set[str],
    source: set[str],
    target: set[str],
    *,
    category: str,
    conflicts: list[FeatureHistoryMergeConflict],
) -> set[str]:
    merged: set[str] = set()
    for item in sorted(base | source | target):
        before = item in base
        source_value = item in source
        target_value = item in target
        if source_value == before:
            selected = target_value
        elif target_value == before or source_value == target_value:
            selected = source_value
        else:
            conflicts.append(FeatureHistoryMergeConflict(
                category, item, "both sides changed the same membership value incompatibly"
            ))
            continue
        if selected:
            merged.add(item)
    return merged


def _pair_order(order: tuple[str, ...], left: str, right: str) -> bool | None:
    positions = {item: index for index, item in enumerate(order)}
    if left not in positions or right not in positions:
        return None
    return positions[left] < positions[right]


def _merge_presentation_order(
    base: FeatureHistory,
    source: FeatureHistory,
    target: FeatureHistory,
    nodes: dict[str, FeatureNode],
    conflicts: list[FeatureHistoryMergeConflict],
) -> tuple[str, ...]:
    ids = set(nodes)
    base_ids = set(node.feature_id for node in base.nodes) & ids
    base_order = tuple(node.feature_id for node in base.nodes)
    source_order = tuple(node.feature_id for node in source.nodes)
    target_order = tuple(node.feature_id for node in target.nodes)
    edges: dict[str, set[str]] = {item: set() for item in ids}
    dependency_edges: dict[str, set[str]] = {item: set() for item in ids}
    indegree = {item: 0 for item in ids}

    def add_before(first: str, second: str) -> None:
        if first == second or second in edges[first]:
            return
        edges[first].add(second)
        indegree[second] += 1

    # Dependency constraints are authoritative; stored order is only a
    # presentation hint and older snapshots may not have topological order.
    for node in nodes.values():
        for dependency in node.input_feature_ids:
            if dependency not in nodes:
                conflicts.append(FeatureHistoryMergeConflict(
                    "missing_dependency", node.feature_id,
                    f"merged feature references missing dependency {dependency!r}",
                ))
            else:
                dependency_edges[dependency].add(node.feature_id)
                add_before(dependency, node.feature_id)

    if conflicts:
        return ()

    def has_dependency_path(first: str, second: str) -> bool:
        pending = [first]
        visited = {first}
        while pending:
            current = pending.pop()
            if current == second:
                return True
            for child in dependency_edges[current]:
                if child not in visited:
                    visited.add(child)
                    pending.append(child)
        return False

    for left, right in combinations(sorted(ids), 2):
        base_relation = _pair_order(base_order, left, right)
        source_relation = _pair_order(source_order, left, right)
        target_relation = _pair_order(target_order, left, right)
        if left in base_ids and right in base_ids:
            source_changed = source_relation is not None and source_relation != base_relation
            target_changed = target_relation is not None and target_relation != base_relation
            if source_changed and target_changed and source_relation != target_relation:
                conflicts.append(FeatureHistoryMergeConflict(
                    "presentation_order", None,
                    f"branches reorder base features {left!r} and {right!r} incompatibly",
                ))
                continue
            selected = (
                source_relation if source_changed else
                target_relation if target_changed else
                base_relation
            )
        else:
            if source_relation is not None and target_relation is not None and source_relation != target_relation:
                conflicts.append(FeatureHistoryMergeConflict(
                    "presentation_order", None,
                    f"branches order new/changed features {left!r} and {right!r} incompatibly",
                ))
                continue
            selected = source_relation if source_relation is not None else target_relation
        if selected is True:
            if not has_dependency_path(right, left):
                add_before(left, right)
        elif selected is False:
            if not has_dependency_path(left, right):
                add_before(right, left)

    if conflicts:
        return ()

    source_positions = {item: index for index, item in enumerate(source_order)}
    target_positions = {item: index for index, item in enumerate(target_order)}
    base_positions = {item: index for index, item in enumerate(base_order)}

    def priority(item: str) -> tuple[int, int, int, str]:
        # Prefer target-side placement, then source, then base, then stable ID.
        return (
            target_positions.get(item, 10**9),
            source_positions.get(item, 10**9),
            base_positions.get(item, 10**9),
            item,
        )

    ready = [(priority(item), item) for item, degree in indegree.items() if degree == 0]
    heapq.heapify(ready)
    ordered: list[str] = []
    while ready:
        _key, item = heapq.heappop(ready)
        ordered.append(item)
        for dependent in sorted(edges[item]):
            indegree[dependent] -= 1
            if indegree[dependent] == 0:
                heapq.heappush(ready, (priority(dependent), dependent))
    if len(ordered) != len(ids):
        conflicts.append(FeatureHistoryMergeConflict(
            "presentation_cycle", None,
            "combined presentation and dependency constraints contain a cycle",
        ))
        return ()
    return tuple(ordered)


def merge_feature_histories(
    base: FeatureHistory,
    source: FeatureHistory,
    target: FeatureHistory,
) -> FeatureHistoryMergeResult:
    """Analyze a three-way merge; never persists or mutates any input.

    Histories may have different history IDs. The result adopts target's ID.
    Node values are merged by stable feature ID; output/suppression membership
    is merged independently; presentation order is merged conservatively.
    """
    if not all(isinstance(item, FeatureHistory) for item in (base, source, target)):
        raise InvalidModelError("base, source and target must be FeatureHistory values")
    if source.history_id == target.history_id:
        raise InvalidModelError("source and target must have different history IDs")

    base_nodes = {node.feature_id: node for node in base.nodes}
    source_nodes = {node.feature_id: node for node in source.nodes}
    target_nodes = {node.feature_id: node for node in target.nodes}
    conflicts: list[FeatureHistoryMergeConflict] = []
    merged_nodes: dict[str, FeatureNode] = {}
    missing = object()

    for feature_id in sorted(set(base_nodes) | set(source_nodes) | set(target_nodes)):
        before = base_nodes.get(feature_id, missing)
        source_value = source_nodes.get(feature_id, missing)
        target_value = target_nodes.get(feature_id, missing)
        if source_value == before:
            selected = target_value
        elif target_value == before or source_value == target_value:
            selected = source_value
        else:
            conflicts.append(FeatureHistoryMergeConflict(
                "node_content", feature_id,
                "both branches changed this feature differently (including delete-versus-edit)",
            ))
            continue
        if selected is not missing:
            merged_nodes[feature_id] = selected

    merged_outputs = _merge_membership(
        set(base.output_feature_ids), set(source.output_feature_ids),
        set(target.output_feature_ids), category="output_membership", conflicts=conflicts,
    )
    merged_suppressed = _merge_membership(
        set(base.suppressed_feature_ids), set(source.suppressed_feature_ids),
        set(target.suppressed_feature_ids), category="suppression_membership", conflicts=conflicts,
    )

    if conflicts:
        return FeatureHistoryMergeResult(None, tuple(sorted(
            conflicts, key=lambda item: (item.category, item.feature_id or "", item.detail)
        )))

    ordered_ids = _merge_presentation_order(base, source, target, merged_nodes, conflicts)
    if conflicts:
        return FeatureHistoryMergeResult(None, tuple(sorted(
            conflicts, key=lambda item: (item.category, item.feature_id or "", item.detail)
        )))

    output_ids = tuple(item for item in ordered_ids if item in merged_outputs)
    document_version = (
        "1.1" if merged_suppressed or any(
            item.document_version == "1.1" for item in (base, source, target)
        ) else "1.0"
    )
    try:
        merged = FeatureHistory(
            target.history_id,
            tuple(merged_nodes[item] for item in ordered_ids),
            output_ids,
            tuple(sorted(merged_suppressed)),
            document_version,
        )
    except InvalidModelError as exc:
        return FeatureHistoryMergeResult(None, (
            FeatureHistoryMergeConflict("model_validation", None, str(exc)),
        ))
    return FeatureHistoryMergeResult(merged, ())


__all__ = [
    "FeatureHistoryMergeConflict",
    "FeatureHistoryMergeResult",
    "merge_feature_histories",
]
