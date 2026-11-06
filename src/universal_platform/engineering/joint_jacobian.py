"""Numerical Jacobians for automatically generated joint pose constraints.

The matrix differentiates the generated residuals with respect to generalized
coordinates and body-pose tangent variables. Derivatives are finite-difference
estimates, not symbolic or exact analytic derivatives.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Mapping

from .errors import InvalidModelError
from .geometry import Vec3
from .joint_constraints import GeneratedJointConstraintSet, _matmul, _rotation_about_axis
from .mechanism_model import CoordinateKind
from .nonlinear_solver import JacobianMethod
from .transforms import RigidTransform


@dataclass(frozen=True, slots=True)
class JointConstraintVariable:
    variable_id: str
    variable_kind: str
    owner_id: str
    component: str
    unit: str
    scale: float

    def to_dict(self) -> dict[str, object]:
        return {
            "variable_id": self.variable_id,
            "variable_kind": self.variable_kind,
            "owner_id": self.owner_id,
            "component": self.component,
            "unit": self.unit,
            "scale": self.scale,
        }


@dataclass(frozen=True, slots=True)
class JointConstraintJacobianColumn:
    variable: JointConstraintVariable
    step: float
    method: str

    def to_dict(self) -> dict[str, object]:
        return {
            "variable": self.variable.to_dict(),
            "step": self.step,
            "method": self.method,
        }


@dataclass(frozen=True, slots=True)
class JointConstraintJacobian:
    schema_version: str
    model_id: str
    model_revision: str
    method: str
    finite_difference_step: float
    row_ids: tuple[str, ...]
    row_units: tuple[str, ...]
    columns: tuple[JointConstraintJacobianColumn, ...]
    values: tuple[tuple[float, ...], ...]
    base_residual_values: tuple[float, ...]

    @property
    def shape(self) -> tuple[int, int]:
        return len(self.row_ids), len(self.columns)

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "model_id": self.model_id,
            "model_revision": self.model_revision,
            "method": self.method,
            "finite_difference_step": self.finite_difference_step,
            "shape": list(self.shape),
            "row_ids": list(self.row_ids),
            "row_units": list(self.row_units),
            "columns": [item.to_dict() for item in self.columns],
            "values": [list(row) for row in self.values],
            "base_residual_values": list(self.base_residual_values),
            "entry_unit_convention": "row residual unit divided by column variable unit",
            "limitations": [
                "Finite-difference approximation; derivative accuracy depends on step size",
                "Body orientation columns use world-frame left perturbations at fixed body origins",
                "No symbolic differentiation, exact analytic Jacobian or physical validation",
            ],
        }


def _variable_catalog(
    constraint_set: GeneratedJointConstraintSet,
) -> tuple[JointConstraintVariable, ...]:
    model = constraint_set.model
    variables = []
    for coordinate in sorted(model.generalized_coordinates, key=lambda item: item.coordinate_id):
        variables.append(JointConstraintVariable(
            f"coordinate/{coordinate.coordinate_id}",
            "GENERALIZED_COORDINATE",
            coordinate.coordinate_id,
            coordinate.coordinate_kind.value.lower(),
            coordinate.unit,
            float(coordinate.scale),
        ))
    for link in sorted(model.links, key=lambda item: item.link_id):
        for component in ("translation_x", "translation_y", "translation_z"):
            variables.append(JointConstraintVariable(
                f"link/{link.link_id}/pose/{component}",
                "BODY_POSE_TRANSLATION",
                link.link_id,
                component,
                "m",
                1.0,
            ))
        for component in ("rotation_x", "rotation_y", "rotation_z"):
            variables.append(JointConstraintVariable(
                f"link/{link.link_id}/pose/{component}",
                "BODY_POSE_ROTATION",
                link.link_id,
                component,
                "rad",
                1.0,
            ))
    return tuple(variables)


def _perturb_state(
    variable: JointConstraintVariable,
    amount: float,
    body_poses: Mapping[str, RigidTransform],
    coordinate_values: Mapping[str, float],
) -> tuple[dict[str, RigidTransform], dict[str, float]]:
    poses = dict(body_poses)
    coordinates = dict(coordinate_values)
    if variable.variable_kind == "GENERALIZED_COORDINATE":
        coordinates[variable.owner_id] += amount
        return poses, coordinates

    pose = poses[variable.owner_id]
    if variable.variable_kind == "BODY_POSE_TRANSLATION":
        values = [pose.translation.x, pose.translation.y, pose.translation.z]
        index = ("translation_x", "translation_y", "translation_z").index(variable.component)
        values[index] += amount
        translation = Vec3(*values)
        poses[variable.owner_id] = RigidTransform(
            pose.from_frame, pose.to_frame, pose.rotation, translation
        )
    else:
        index = ("rotation_x", "rotation_y", "rotation_z").index(variable.component)
        axis = tuple(1.0 if i == index else 0.0 for i in range(3))
        delta = _rotation_about_axis(axis, amount)
        rotation = _matmul(delta, pose.rotation)
        poses[variable.owner_id] = RigidTransform(
            pose.from_frame, pose.to_frame, rotation, pose.translation
        )
    return poses, coordinates


def _available_steps(
    variable: JointConstraintVariable,
    value: float,
    proposed: float,
    constraint_set: GeneratedJointConstraintSet,
) -> tuple[float, float]:
    if variable.variable_kind != "GENERALIZED_COORDINATE":
        return proposed, proposed
    coordinate = next(
        item for item in constraint_set.model.generalized_coordinates
        if item.coordinate_id == variable.owner_id
    )
    plus_room = float("inf") if coordinate.upper_limit is None else coordinate.upper_limit - value
    minus_room = float("inf") if coordinate.lower_limit is None else value - coordinate.lower_limit
    return max(0.0, min(proposed, plus_room)), max(0.0, min(proposed, minus_room))


def build_joint_constraint_jacobian(
    constraint_set: GeneratedJointConstraintSet,
    body_poses: Mapping[str, RigidTransform],
    coordinate_values: Mapping[str, float],
    *,
    method: JacobianMethod = JacobianMethod.CENTRAL_FINITE_DIFFERENCE,
    finite_difference_step: float = 1e-6,
) -> JointConstraintJacobian:
    """Build a deterministic finite-difference Jacobian for all generated rows.

    Columns are ordered by stable coordinate ID, then link ID and body-pose
    component (world translations followed by world-frame rotation tangents).
    At coordinate limits, the method falls back to a feasible one-sided
    difference; fixed-at-both-limits variables are reported as BOUND_LOCKED.
    """
    if not isinstance(constraint_set, GeneratedJointConstraintSet):
        raise InvalidModelError("constraint_set must be a GeneratedJointConstraintSet")
    if not isinstance(method, JacobianMethod) or method is JacobianMethod.ANALYTIC:
        raise InvalidModelError(
            "Joint constraint Jacobian supports forward or central finite differences only"
        )
    if (isinstance(finite_difference_step, bool)
            or not isinstance(finite_difference_step, (int, float))
            or not isfinite(finite_difference_step) or finite_difference_step <= 0):
        raise InvalidModelError("finite_difference_step must be finite and positive")

    base = constraint_set.evaluate(body_poses, coordinate_values)
    row_ids = tuple(item.constraint_id for item in base.residuals)
    row_units = tuple(item.unit for item in base.residuals)
    base_values = tuple(item.value for item in base.residuals)
    variables = _variable_catalog(constraint_set)
    matrix = [[0.0 for _ in variables] for _ in row_ids]
    columns = []

    for column_index, variable in enumerate(variables):
        value = (
            coordinate_values[variable.owner_id]
            if variable.variable_kind == "GENERALIZED_COORDINATE"
            else 0.0
        )
        proposed = float(finite_difference_step) * max(
            abs(float(value)), variable.scale, 1e-12
        )
        plus_step, minus_step = _available_steps(
            variable, float(value), proposed, constraint_set
        )

        if method is JacobianMethod.CENTRAL_FINITE_DIFFERENCE and plus_step > 0 and minus_step > 0:
            step = min(plus_step, minus_step)
            plus_poses, plus_coordinates = _perturb_state(
                variable, step, body_poses, coordinate_values
            )
            minus_poses, minus_coordinates = _perturb_state(
                variable, -step, body_poses, coordinate_values
            )
            plus_values = tuple(
                item.value for item in constraint_set.evaluate(plus_poses, plus_coordinates).residuals
            )
            minus_values = tuple(
                item.value for item in constraint_set.evaluate(minus_poses, minus_coordinates).residuals
            )
            for row in range(len(row_ids)):
                matrix[row][column_index] = (
                    plus_values[row] - minus_values[row]
                ) / (2.0 * step)
            used_method = "CENTRAL_FINITE_DIFFERENCE"
        elif plus_step > 0:
            step = plus_step
            plus_poses, plus_coordinates = _perturb_state(
                variable, step, body_poses, coordinate_values
            )
            plus_values = tuple(
                item.value for item in constraint_set.evaluate(plus_poses, plus_coordinates).residuals
            )
            for row in range(len(row_ids)):
                matrix[row][column_index] = (
                    plus_values[row] - base_values[row]
                ) / step
            used_method = "FORWARD_FINITE_DIFFERENCE"
        elif minus_step > 0:
            step = minus_step
            minus_poses, minus_coordinates = _perturb_state(
                variable, -step, body_poses, coordinate_values
            )
            minus_values = tuple(
                item.value for item in constraint_set.evaluate(minus_poses, minus_coordinates).residuals
            )
            for row in range(len(row_ids)):
                matrix[row][column_index] = (
                    base_values[row] - minus_values[row]
                ) / step
            used_method = "BACKWARD_FINITE_DIFFERENCE"
        else:
            step = 0.0
            used_method = "BOUND_LOCKED"

        columns.append(JointConstraintJacobianColumn(variable, step, used_method))

    if not all(isfinite(value) for row in matrix for value in row):
        raise InvalidModelError("Generated joint constraint Jacobian contains non-finite entries")
    return JointConstraintJacobian(
        "1.0",
        constraint_set.model.model_id,
        constraint_set.model.revision,
        method.value,
        float(finite_difference_step),
        row_ids,
        row_units,
        tuple(columns),
        tuple(tuple(row) for row in matrix),
        base_values,
    )
