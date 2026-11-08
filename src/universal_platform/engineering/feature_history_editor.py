"""Safe immutable editing operations for FeatureHistory DAG documents.

These helpers transform validated source documents without mutating persisted
revisions or executing feature operations. Callers persist the returned
snapshot through CADGeneratorService.save_history with an expected revision.
"""
from __future__ import annotations

from .errors import InvalidModelError
from .feature_history import FeatureHistory, FeatureNode


def add_feature(
    history: FeatureHistory,
    node: FeatureNode,
    *,
    make_output: bool = False,
) -> FeatureHistory:
    """Return a new history with one feature appended."""
    if not isinstance(history, FeatureHistory):
        raise InvalidModelError("add_feature requires a FeatureHistory")
    if not isinstance(node, FeatureNode):
        raise InvalidModelError("add_feature requires a FeatureNode")
    if not isinstance(make_output, bool):
        raise InvalidModelError("make_output must be a boolean")
    if any(existing.feature_id == node.feature_id for existing in history.nodes):
        raise InvalidModelError(f"feature {node.feature_id!r} already exists")
    outputs = history.output_feature_ids + ((node.feature_id,) if make_output else ())
    return FeatureHistory(
        history.history_id, history.nodes + (node,), outputs,
        history.suppressed_feature_ids, history.document_version,
    )


def replace_feature(
    history: FeatureHistory,
    feature_id: str,
    replacement: FeatureNode,
) -> FeatureHistory:
    """Return a new history with an existing node replaced in place.

    A replacement cannot silently rename a feature because dependent nodes
    refer to stable feature IDs. Renaming requires an explicit graph migration.
    """
    if not isinstance(history, FeatureHistory):
        raise InvalidModelError("replace_feature requires a FeatureHistory")
    if not isinstance(feature_id, str) or not feature_id:
        raise InvalidModelError("feature_id must be a non-empty string")
    if not isinstance(replacement, FeatureNode):
        raise InvalidModelError("replacement must be a FeatureNode")
    if replacement.feature_id != feature_id:
        raise InvalidModelError("replacement must preserve the existing feature_id")
    if not any(node.feature_id == feature_id for node in history.nodes):
        raise InvalidModelError(f"feature {feature_id!r} does not exist")
    nodes = tuple(replacement if node.feature_id == feature_id else node for node in history.nodes)
    return FeatureHistory(
        history.history_id, nodes, history.output_feature_ids,
        history.suppressed_feature_ids, history.document_version,
    )


def remove_feature(
    history: FeatureHistory,
    feature_id: str,
    *,
    cascade: bool = False,
) -> FeatureHistory:
    """Return a new history with a feature removed.

    By default, removal is rejected while downstream features depend on the
    target. With cascade=True, all transitive dependents are removed too.
    Output references are removed with their nodes; at least one output must
    remain, as required by FeatureHistory.
    """
    if not isinstance(history, FeatureHistory):
        raise InvalidModelError("remove_feature requires a FeatureHistory")
    if not isinstance(feature_id, str) or not feature_id:
        raise InvalidModelError("feature_id must be a non-empty string")
    if not isinstance(cascade, bool):
        raise InvalidModelError("cascade must be a boolean")

    by_id = {node.feature_id: node for node in history.nodes}
    if feature_id not in by_id:
        raise InvalidModelError(f"feature {feature_id!r} does not exist")

    dependents: dict[str, set[str]] = {key: set() for key in by_id}
    for node in history.nodes:
        for dependency in node.input_feature_ids:
            dependents[dependency].add(node.feature_id)

    removed = {feature_id}
    pending = [feature_id]
    while pending:
        current = pending.pop()
        children = dependents[current] - removed
        if children and not cascade:
            raise InvalidModelError(
                f"feature {feature_id!r} has dependent features; use cascade=True to remove them"
            )
        removed.update(children)
        pending.extend(sorted(children))

    nodes = tuple(node for node in history.nodes if node.feature_id not in removed)
    outputs = tuple(item for item in history.output_feature_ids if item not in removed)
    if not outputs:
        raise InvalidModelError("feature removal would leave the history without an output feature")
    return FeatureHistory(
        history.history_id, nodes, outputs,
        tuple(item for item in history.suppressed_feature_ids if item not in removed),
        history.document_version,
    )


def suppress_feature(
    history: FeatureHistory,
    feature_id: str,
    *,
    cascade: bool = False,
) -> FeatureHistory:
    """Return a new v1.1 history with a feature and optionally its dependents suppressed."""
    if not isinstance(history, FeatureHistory):
        raise InvalidModelError("suppress_feature requires a FeatureHistory")
    if not isinstance(feature_id, str) or not feature_id:
        raise InvalidModelError("feature_id must be a non-empty string")
    if not isinstance(cascade, bool):
        raise InvalidModelError("cascade must be a boolean")
    by_id = {node.feature_id: node for node in history.nodes}
    if feature_id not in by_id:
        raise InvalidModelError(f"feature {feature_id!r} does not exist")
    suppressed = set(history.suppressed_feature_ids)
    if feature_id in suppressed:
        return history

    dependents: dict[str, set[str]] = {key: set() for key in by_id}
    for node in history.nodes:
        for dependency in node.input_feature_ids:
            dependents[dependency].add(node.feature_id)

    affected = {feature_id}
    pending = [feature_id]
    while pending:
        current = pending.pop()
        children = dependents[current] - affected
        affected.update(children)
        pending.extend(sorted(children))
    active_dependents = affected - suppressed - {feature_id}
    if active_dependents and not cascade:
        raise InvalidModelError(
            f"feature {feature_id!r} has active dependents; use cascade=True to suppress them"
        )
    suppressed.update(affected if cascade else {feature_id})
    return FeatureHistory(
        history.history_id, history.nodes, history.output_feature_ids,
        tuple(sorted(suppressed)), FeatureHistory.CURRENT_SCHEMA_VERSION,
    )


def unsuppress_feature(history: FeatureHistory, feature_id: str) -> FeatureHistory:
    """Return a new v1.1 history with one feature unsuppressed."""
    if not isinstance(history, FeatureHistory):
        raise InvalidModelError("unsuppress_feature requires a FeatureHistory")
    if not isinstance(feature_id, str) or not feature_id:
        raise InvalidModelError("feature_id must be a non-empty string")
    by_id = {node.feature_id: node for node in history.nodes}
    if feature_id not in by_id:
        raise InvalidModelError(f"feature {feature_id!r} does not exist")
    suppressed = set(history.suppressed_feature_ids)
    if feature_id not in suppressed:
        return history
    node = by_id[feature_id]
    if any(dependency in suppressed for dependency in node.input_feature_ids):
        raise InvalidModelError(
            f"feature {feature_id!r} cannot be unsuppressed while a dependency is suppressed"
        )
    suppressed.remove(feature_id)
    return FeatureHistory(
        history.history_id, history.nodes, history.output_feature_ids,
        tuple(sorted(suppressed)), FeatureHistory.CURRENT_SCHEMA_VERSION,
    )


def reorder_features(
    history: FeatureHistory,
    ordered_feature_ids: tuple[str, ...],
) -> FeatureHistory:
    """Return a new history with a validated topological presentation order.

    Reordering changes only the immutable source node sequence used for display.
    Feature execution order remains the deterministic dependency-derived order
    returned by FeatureHistory.topological_order(). Every dependency must still
    appear before its dependent in the requested presentation sequence.
    """
    if not isinstance(history, FeatureHistory):
        raise InvalidModelError("reorder_features requires a FeatureHistory")
    if not isinstance(ordered_feature_ids, tuple) or any(
        not isinstance(item, str) or not item for item in ordered_feature_ids
    ):
        raise InvalidModelError("ordered_feature_ids must be an immutable tuple of feature IDs")
    by_id = {node.feature_id: node for node in history.nodes}
    if len(ordered_feature_ids) != len(by_id) or set(ordered_feature_ids) != set(by_id):
        raise InvalidModelError("ordered_feature_ids must contain every feature ID exactly once")
    positions = {feature_id: index for index, feature_id in enumerate(ordered_feature_ids)}
    for node in history.nodes:
        if any(positions[dependency] >= positions[node.feature_id] for dependency in node.input_feature_ids):
            raise InvalidModelError("ordered_feature_ids must place every dependency before its dependent")
    nodes = tuple(by_id[feature_id] for feature_id in ordered_feature_ids)
    return FeatureHistory(
        history.history_id, nodes, history.output_feature_ids,
        history.suppressed_feature_ids, history.document_version,
    )


__all__ = ["add_feature", "replace_feature", "remove_feature", "reorder_features", "suppress_feature", "unsuppress_feature"]
