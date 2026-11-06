"""Geometry-aware evaluation of closed mechanism configurations.

This module evaluates a supplied configuration against generated joint
pose-consistency residuals and deterministic fundamental-cycle topology.
It does not search for a configuration or establish physical feasibility.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Mapping

from .errors import InvalidModelError
from .joint_constraints import (
    JointConstraintEvaluation,
    JointConstraintResidual,
    generate_joint_constraints,
)
from .mechanism_loops import LoopTopology, analyze_loop_topology
from .mechanism_model import MechanismModel
from .transforms import RigidTransform


class GeometricLoopClosureStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"


@dataclass(frozen=True, slots=True)
class GeometricLoopResidualGroup:
    loop_id: str
    closure_joint_id: str
    joint_ids: tuple[str, ...]
    link_ids: tuple[str, ...]
    residuals: tuple[JointConstraintResidual, ...]

    @property
    def all_satisfied(self) -> bool:
        return bool(self.residuals) and all(item.passed for item in self.residuals)

    def to_dict(self) -> dict[str, object]:
        return {
            "loop_id": self.loop_id,
            "closure_joint_id": self.closure_joint_id,
            "joint_ids": list(self.joint_ids),
            "link_ids": list(self.link_ids),
            "all_satisfied": self.all_satisfied,
            "residuals": [item.to_dict() for item in self.residuals],
        }


@dataclass(frozen=True, slots=True)
class GeometricLoopClosureResult:
    schema_version: str
    model_id: str
    model_revision: str
    status: GeometricLoopClosureStatus
    topology: LoopTopology
    joint_evaluation: JointConstraintEvaluation
    loops: tuple[GeometricLoopResidualGroup, ...]
    limitations: tuple[str, ...] = (
        "Evaluates only caller-supplied body poses and generalized-coordinate values",
        "PASS means represented joint pose residuals meet declared tolerances; it is not physical validation",
        "No configuration search, nonlinear solve, branch discovery or global reachability analysis",
        "No collision/contact, dynamics, forces, stability, manufacturing validation or certification",
    )

    @property
    def all_joint_constraints_satisfied(self) -> bool:
        return self.joint_evaluation.all_satisfied

    @property
    def all_loop_closures_satisfied(self) -> bool:
        return bool(self.loops) and all(item.all_satisfied for item in self.loops)

    @property
    def all_satisfied(self) -> bool:
        return (
            self.status is GeometricLoopClosureStatus.PASS
            and self.all_joint_constraints_satisfied
            and self.all_loop_closures_satisfied
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "model_id": self.model_id,
            "model_revision": self.model_revision,
            "status": self.status.value,
            "all_satisfied": self.all_satisfied,
            "all_joint_constraints_satisfied": self.all_joint_constraints_satisfied,
            "all_loop_closures_satisfied": self.all_loop_closures_satisfied,
            "topology": {
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
            "joint_evaluation": self.joint_evaluation.to_dict(),
            "loops": [item.to_dict() for item in self.loops],
            "limitations": list(self.limitations),
        }


def evaluate_geometric_loop_closure(
    model: MechanismModel,
    body_poses: Mapping[str, RigidTransform],
    coordinate_values: Mapping[str, float],
    *,
    translation_tolerance_m: float = 1e-8,
    rotation_tolerance_rad: float = 1e-8,
) -> GeometricLoopClosureResult:
    """Evaluate every fundamental loop using explicit geometric joint residuals.

    All joint residuals are evaluated and retained. Per-loop groups select the
    residuals belonging to each deterministic loop-closing joint. The overall
    result is PASS only when every joint residual and every loop group passes.
    """
    topology = analyze_loop_topology(model)
    if not topology.loops:
        raise InvalidModelError("Geometric loop closure requires at least one graph loop")

    generated = generate_joint_constraints(
        model,
        translation_tolerance_m=translation_tolerance_m,
        rotation_tolerance_rad=rotation_tolerance_rad,
    )
    evaluation = generated.evaluate(body_poses, coordinate_values)
    by_joint: dict[str, list[JointConstraintResidual]] = {}
    for residual in evaluation.residuals:
        by_joint.setdefault(residual.joint_id, []).append(residual)

    groups = []
    for loop in topology.loops:
        residuals = tuple(by_joint.get(loop.closure_joint_id, ()))
        if len(residuals) != 6:
            raise InvalidModelError(
                f"Loop-closing joint {loop.closure_joint_id!r} must have six geometric residuals"
            )
        groups.append(GeometricLoopResidualGroup(
            loop.loop_id, loop.closure_joint_id, loop.joint_ids, loop.link_ids, residuals
        ))

    status = (
        GeometricLoopClosureStatus.PASS
        if evaluation.all_satisfied and all(item.all_satisfied for item in groups)
        else GeometricLoopClosureStatus.FAIL
    )
    return GeometricLoopClosureResult(
        "1.0", model.model_id, model.revision, status, topology, evaluation, tuple(groups)
    )
