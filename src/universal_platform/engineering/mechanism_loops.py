"""Deterministic graph topology and solver bridge for closed mechanisms."""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from enum import Enum
from typing import Callable, Mapping, Sequence

from .errors import InvalidModelError
from .mechanism_model import MechanismModel, validate_mechanism_model
from .nonlinear_solver import (
    NonlinearConstraint, NonlinearSolveResult, NonlinearSolveStatus,
    NonlinearSolverOptions, solve_nonlinear_constraints,
)

LoopResidualFunction = Callable[[Mapping[str, float]], float]


class LoopClosureStatus(str, Enum):
    CONVERGED = "CONVERGED"
    UNDERCONSTRAINED = "UNDERCONSTRAINED"
    SINGULAR = "SINGULAR"
    UNREACHABLE = "UNREACHABLE"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True, slots=True)
class MechanismLoop:
    loop_id: str
    closure_joint_id: str
    joint_ids: tuple[str, ...]
    link_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class LoopTopology:
    model_id: str
    model_revision: str
    components: tuple[tuple[str, ...], ...]
    spanning_tree_joint_ids: tuple[str, ...]
    loop_closing_joint_ids: tuple[str, ...]
    loops: tuple[MechanismLoop, ...]

    @property
    def loop_count(self) -> int:
        return len(self.loops)


@dataclass(frozen=True, slots=True)
class LoopClosureConstraint:
    """Caller-defined scalar equality residual associated with a closing edge."""
    constraint_id: str
    closure_joint_id: str
    residual: LoopResidualFunction
    tolerance: float = 1e-8
    scale: float = 1.0


@dataclass(frozen=True, slots=True)
class LoopClosureResult:
    status: LoopClosureStatus
    topology: LoopTopology
    solver_result: NonlinearSolveResult
    limitations: tuple[str, ...] = (
        "Fundamental graph cycles are topological, not geometric loop equations",
        "Caller-supplied residuals define geometry, coordinates and units",
        "The underlying solver is local damped least squares without global guarantees",
        "SINGULAR and UNREACHABLE are not inferred from a failed local solve",
        "No spatial joint kinematics, collision/contact, dynamics or certification",
    )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": "1.0",
            "status": self.status.value,
            "topology": {
                "model_id": self.topology.model_id,
                "model_revision": self.topology.model_revision,
                "components": [list(item) for item in self.topology.components],
                "spanning_tree_joint_ids": list(self.topology.spanning_tree_joint_ids),
                "loop_closing_joint_ids": list(self.topology.loop_closing_joint_ids),
                "loops": [
                    {
                        "loop_id": item.loop_id,
                        "closure_joint_id": item.closure_joint_id,
                        "joint_ids": list(item.joint_ids),
                        "link_ids": list(item.link_ids),
                    }
                    for item in self.topology.loops
                ],
            },
            "solver_result": self.solver_result.to_dict(),
            "limitations": list(self.limitations),
        }


def analyze_loop_topology(model: MechanismModel) -> LoopTopology:
    """Build a deterministic spanning forest and fundamental cycle basis."""
    validation = validate_mechanism_model(model)
    if not validation.valid:
        raise InvalidModelError(
            "Cannot analyze invalid mechanism model: " + "; ".join(validation.errors)
        )

    parent = {link.link_id: link.link_id for link in model.links}
    rank = {link.link_id: 0 for link in model.links}

    def find(item: str) -> str:
        while parent[item] != item:
            parent[item] = parent[parent[item]]
            item = parent[item]
        return item

    def union(left: str, right: str) -> bool:
        root_left, root_right = find(left), find(right)
        if root_left == root_right:
            return False
        if rank[root_left] < rank[root_right]:
            root_left, root_right = root_right, root_left
        parent[root_right] = root_left
        if rank[root_left] == rank[root_right]:
            rank[root_left] += 1
        return True

    adjacency: dict[str, list[tuple[str, str]]] = {key: [] for key in parent}
    tree_edges: list[str] = []
    closure_edges: list[str] = []
    loops: list[MechanismLoop] = []

    for joint in sorted(model.joints, key=lambda item: item.joint_id):
        left, right = joint.parent_link_id, joint.child_link_id
        if union(left, right):
            tree_edges.append(joint.joint_id)
            adjacency[left].append((right, joint.joint_id))
            adjacency[right].append((left, joint.joint_id))
            continue

        queue = deque([left])
        previous: dict[str, tuple[str, str] | None] = {left: None}
        while queue and right not in previous:
            current = queue.popleft()
            for neighbor, edge_id in sorted(adjacency[current]):
                if neighbor not in previous:
                    previous[neighbor] = (current, edge_id)
                    queue.append(neighbor)
        if right not in previous:
            raise InvalidModelError(
                f"Internal topology error: no forest path for joint {joint.joint_id!r}"
            )

        reverse_nodes = [right]
        reverse_edges: list[str] = []
        current = right
        while current != left:
            step = previous[current]
            assert step is not None
            predecessor, edge_id = step
            reverse_edges.append(edge_id)
            reverse_nodes.append(predecessor)
            current = predecessor
        path_nodes = tuple(reversed(reverse_nodes))
        path_edges = tuple(reversed(reverse_edges))
        closure_edges.append(joint.joint_id)
        loops.append(MechanismLoop(
            f"loop/{joint.joint_id}", joint.joint_id,
            path_edges + (joint.joint_id,), path_nodes + (left,),
        ))

    component_map: dict[str, list[str]] = {}
    for link_id in sorted(parent):
        component_map.setdefault(find(link_id), []).append(link_id)
    components = tuple(sorted(
        (tuple(items) for items in component_map.values()), key=lambda items: items
    ))
    return LoopTopology(
        model.model_id, model.revision, components, tuple(tree_edges),
        tuple(closure_edges), tuple(loops),
    )


def solve_mechanism_loops(
    model: MechanismModel,
    variable_names: Sequence[str],
    initial_values: Mapping[str, float],
    constraints: Sequence[LoopClosureConstraint],
    *,
    options: NonlinearSolverOptions | None = None,
) -> LoopClosureResult:
    """Solve explicit caller-provided equality residuals for every graph loop.

    Joint schema records lack complete placements and parameterizations, so
    this bridge intentionally does not synthesize geometric equations.
    """
    topology = analyze_loop_topology(model)
    if not topology.loops:
        raise InvalidModelError("Mechanism model contains no closed graph loops")
    equations = tuple(constraints)
    if not equations:
        raise InvalidModelError("At least one explicit loop-closure constraint is required")
    if any(not isinstance(item, LoopClosureConstraint) for item in equations):
        raise InvalidModelError("All constraints must be LoopClosureConstraint records")
    ids = [item.constraint_id for item in equations]
    if any(not isinstance(value, str) or not value.strip() for value in ids):
        raise InvalidModelError("Constraint identifiers must be non-empty strings")
    if len(ids) != len(set(ids)):
        raise InvalidModelError("Constraint identifiers must be unique")

    closure_ids = set(topology.loop_closing_joint_ids)
    covered = {item.closure_joint_id for item in equations}
    unknown, missing = covered - closure_ids, closure_ids - covered
    if unknown:
        raise InvalidModelError(
            "Constraints reference joints that are not loop-closing edges: "
            + ", ".join(sorted(unknown))
        )
    if missing:
        raise InvalidModelError(
            "Missing explicit residuals for loop-closing joints: "
            + ", ".join(sorted(missing))
        )

    solver_constraints = []
    for item in equations:
        if not callable(item.residual):
            raise InvalidModelError(
                f"Constraint {item.constraint_id!r} residual must be callable"
            )
        solver_constraints.append(NonlinearConstraint(
            item.constraint_id, item.residual, item.tolerance, item.scale
        ))

    solved = solve_nonlinear_constraints(
        tuple(variable_names), initial_values, tuple(solver_constraints),
        options=options,
    )
    if solved.status is NonlinearSolveStatus.CONVERGED:
        status = LoopClosureStatus.CONVERGED
    elif (
        solved.jacobian_rank is not None
        and solved.jacobian_rank.system_shape == "UNDERDETERMINED"
        and solved.jacobian_rank.estimated_rank is not None
        and solved.jacobian_rank.estimated_rank < solved.jacobian_rank.column_count
    ):
        status = LoopClosureStatus.UNDERCONSTRAINED
    else:
        status = LoopClosureStatus.UNKNOWN
    return LoopClosureResult(status, topology, solved)
