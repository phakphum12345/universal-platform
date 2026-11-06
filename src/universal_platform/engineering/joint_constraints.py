"""Geometry-aware automatic joint-constraint generation.

The generator evaluates normalized joint placements and explicit generalized
coordinates against caller-supplied rigid body poses. It is an offline
kinematic consistency layer, not a dynamics or physical-feasibility solver.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import acos, cos, isfinite, sin, sqrt
from typing import Mapping

from .errors import InvalidModelError
from .geometry import Vec3
from .mechanism_model import (
    CoordinateKind,
    JointKind,
    MechanismModel,
    validate_mechanism_model,
)
from .transforms import Matrix3, RigidTransform


_IDENTITY: Matrix3 = (
    (1.0, 0.0, 0.0),
    (0.0, 1.0, 0.0),
    (0.0, 0.0, 1.0),
)


def _matmul(left: Matrix3, right: Matrix3) -> Matrix3:
    return tuple(
        tuple(sum(left[row][k] * right[k][column] for k in range(3))
              for column in range(3))
        for row in range(3)
    )  # type: ignore[return-value]


def _transpose(matrix: Matrix3) -> Matrix3:
    return tuple(
        tuple(matrix[column][row] for column in range(3))
        for row in range(3)
    )  # type: ignore[return-value]


def _rotation_about_axis(axis: tuple[float, float, float], angle: float) -> Matrix3:
    x, y, z = axis
    c, s, one_minus_c = cos(angle), sin(angle), 1.0 - cos(angle)
    return (
        (c + x*x*one_minus_c, x*y*one_minus_c - z*s, x*z*one_minus_c + y*s),
        (y*x*one_minus_c + z*s, c + y*y*one_minus_c, y*z*one_minus_c - x*s),
        (z*x*one_minus_c - y*s, z*y*one_minus_c + x*s, c + z*z*one_minus_c),
    )


def _rotation_error(
    actual: Matrix3, expected: Matrix3
) -> tuple[float, float, float]:
    """Return the logarithmic rotation error of expected.T @ actual in radians."""
    relative = _matmul(_transpose(expected), actual)
    cosine = max(-1.0, min(1.0, (relative[0][0] + relative[1][1] + relative[2][2] - 1.0) / 2.0))
    angle = acos(cosine)
    skew = (
        relative[2][1] - relative[1][2],
        relative[0][2] - relative[2][0],
        relative[1][0] - relative[0][1],
    )
    if angle < 1e-8:
        return tuple(0.5 * value for value in skew)  # type: ignore[return-value]
    if 3.141592653589793 - angle < 1e-6:
        diagonal = (
            max(0.0, (relative[0][0] + 1.0) / 2.0),
            max(0.0, (relative[1][1] + 1.0) / 2.0),
            max(0.0, (relative[2][2] + 1.0) / 2.0),
        )
        index = max(range(3), key=lambda item: diagonal[item])
        axis = [0.0, 0.0, 0.0]
        axis[index] = sqrt(diagonal[index])
        if axis[index] <= 1e-12:
            axis = [1.0, 0.0, 0.0]
        elif index == 0:
            axis[1] = (relative[0][1] + relative[1][0]) / (4.0 * axis[0])
            axis[2] = (relative[0][2] + relative[2][0]) / (4.0 * axis[0])
        elif index == 1:
            axis[0] = (relative[0][1] + relative[1][0]) / (4.0 * axis[1])
            axis[2] = (relative[1][2] + relative[2][1]) / (4.0 * axis[1])
        else:
            axis[0] = (relative[0][2] + relative[2][0]) / (4.0 * axis[2])
            axis[1] = (relative[1][2] + relative[2][1]) / (4.0 * axis[2])
        magnitude = sqrt(sum(value * value for value in axis))
        return tuple(angle * value / magnitude for value in axis)  # type: ignore[return-value]
    factor = angle / (2.0 * sin(angle))
    return tuple(factor * value for value in skew)  # type: ignore[return-value]


def _expected_joint_transform(
    model: MechanismModel,
    joint_id: str,
    coordinate_values: Mapping[str, float],
) -> RigidTransform:
    joint = next(item for item in model.joints if item.joint_id == joint_id)
    parameterization = next(
        (item for item in model.joint_parameterizations if item.joint_id == joint_id),
        None,
    )
    coordinates = {item.coordinate_id: item for item in model.generalized_coordinates}
    values = () if parameterization is None else tuple(
        (coordinates[key], coordinate_values[key]) for key in parameterization.coordinate_ids
    )
    rotation = _IDENTITY
    translation = Vec3(0.0, 0.0, 0.0)

    if joint.joint_kind is JointKind.FIXED:
        pass
    elif joint.joint_kind is JointKind.REVOLUTE:
        coordinate, value = values[0]
        rotation = _rotation_about_axis(coordinate.axis, value)
    elif joint.joint_kind is JointKind.PRISMATIC:
        coordinate, value = values[0]
        translation = Vec3(*(component * value for component in coordinate.axis))
    elif joint.joint_kind is JointKind.CYLINDRICAL:
        angular, angle = values[0]
        linear, distance = values[1]
        rotation = _rotation_about_axis(angular.axis, angle)
        translation = Vec3(*(component * distance for component in linear.axis))
    elif joint.joint_kind is JointKind.HELICAL:
        coordinate, angle = values[0]
        rotation = _rotation_about_axis(coordinate.axis, angle)
        distance = parameterization.pitch_m_per_rad * angle
        translation = Vec3(*(component * distance for component in coordinate.axis))
    elif joint.joint_kind is JointKind.SPHERICAL:
        convention = parameterization.coordinate_convention
        rotations = [
            _rotation_about_axis(coordinate.axis, value)
            for coordinate, value in values
        ]
        if convention.startswith("EULER_EXTRINSIC"):
            for item in rotations:
                rotation = _matmul(item, rotation)
        else:
            for item in rotations:
                rotation = _matmul(rotation, item)
    elif joint.joint_kind is JointKind.PLANAR:
        first, second, angular = values
        translation = Vec3(*(
            first[0].axis[index] * first[1] + second[0].axis[index] * second[1]
            for index in range(3)
        ))
        rotation = _rotation_about_axis(angular[0].axis, angular[1])
    elif joint.joint_kind is JointKind.UNIVERSAL:
        first, second = values
        first_rotation = _rotation_about_axis(first[0].axis, first[1])
        second_rotation = _rotation_about_axis(second[0].axis, second[1])
        # Axes are declared in the joint frame: apply the fixed-axis sequence.
        rotation = _matmul(second_rotation, first_rotation)
    return RigidTransform(joint.frame_id, joint.frame_id, rotation, translation)


@dataclass(frozen=True, slots=True)
class JointConstraintDefinition:
    constraint_id: str
    joint_id: str
    component: str
    unit: str
    tolerance: float

    def to_dict(self) -> dict[str, object]:
        return {
            "constraint_id": self.constraint_id,
            "joint_id": self.joint_id,
            "component": self.component,
            "unit": self.unit,
            "tolerance": self.tolerance,
        }


@dataclass(frozen=True, slots=True)
class JointConstraintResidual:
    constraint_id: str
    joint_id: str
    component: str
    unit: str
    value: float
    tolerance: float
    passed: bool

    def to_dict(self) -> dict[str, object]:
        return {
            "constraint_id": self.constraint_id,
            "joint_id": self.joint_id,
            "component": self.component,
            "unit": self.unit,
            "value": self.value,
            "tolerance": self.tolerance,
            "status": "PASS" if self.passed else "FAIL",
        }


@dataclass(frozen=True, slots=True)
class JointConstraintEvaluation:
    schema_version: str
    model_id: str
    model_revision: str
    residuals: tuple[JointConstraintResidual, ...]

    @property
    def all_satisfied(self) -> bool:
        return all(item.passed for item in self.residuals)

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "model_id": self.model_id,
            "model_revision": self.model_revision,
            "all_satisfied": self.all_satisfied,
            "residuals": [item.to_dict() for item in self.residuals],
        }


@dataclass(frozen=True, slots=True)
class GeneratedJointConstraintSet:
    """Deterministic six-component pose-consistency constraints for each joint."""

    schema_version: str
    model: MechanismModel
    definitions: tuple[JointConstraintDefinition, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "model_id": self.model.model_id,
            "model_revision": self.model.revision,
            "definitions": [item.to_dict() for item in self.definitions],
        }

    def evaluate(
        self,
        body_poses: Mapping[str, RigidTransform],
        coordinate_values: Mapping[str, float],
    ) -> JointConstraintEvaluation:
        """Evaluate joint residuals from body-to-world poses and coordinate values."""
        links = {item.link_id: item for item in self.model.links}
        if set(body_poses) != set(links):
            missing = sorted(set(links) - set(body_poses))
            extra = sorted(set(body_poses) - set(links))
            raise InvalidModelError(
                f"body_poses must cover exactly the model links; missing={missing}, extra={extra}"
            )
        world_frames = set()
        for link_id, link in links.items():
            pose = body_poses[link_id]
            if not isinstance(pose, RigidTransform) or pose.from_frame != link.frame_id:
                raise InvalidModelError(
                    f"Body pose for link {link_id!r} must map from frame {link.frame_id!r}"
                )
            world_frames.add(pose.to_frame)
        if len(world_frames) != 1:
            raise InvalidModelError("All body poses must target the same world frame")

        expected_coordinate_ids = {
            item.coordinate_id for item in self.model.generalized_coordinates
        }
        if set(coordinate_values) != expected_coordinate_ids:
            missing = sorted(expected_coordinate_ids - set(coordinate_values))
            extra = sorted(set(coordinate_values) - expected_coordinate_ids)
            raise InvalidModelError(
                f"coordinate_values must cover exactly the model coordinates; "
                f"missing={missing}, extra={extra}"
            )
        coordinate_by_id = {
            item.coordinate_id: item for item in self.model.generalized_coordinates
        }
        for coordinate_id, value in coordinate_values.items():
            if (isinstance(value, bool) or not isinstance(value, (int, float))
                    or not isfinite(value)):
                raise InvalidModelError(
                    f"Coordinate {coordinate_id!r} value must be finite numeric"
                )
            coordinate = coordinate_by_id[coordinate_id]
            if coordinate.lower_limit is not None and value < coordinate.lower_limit:
                raise InvalidModelError(
                    f"Coordinate {coordinate_id!r} value is below its lower limit"
                )
            if coordinate.upper_limit is not None and value > coordinate.upper_limit:
                raise InvalidModelError(
                    f"Coordinate {coordinate_id!r} value is above its upper limit"
                )

        placements = {item.joint_id: item for item in self.model.joint_placements}
        residuals = []
        for joint in sorted(self.model.joints, key=lambda item: item.joint_id):
            placement = placements[joint.joint_id]
            parent = links[joint.parent_link_id]
            child = links[joint.child_link_id]
            parent_joint_to_world = placement.parent_to_joint.inverse().then(
                body_poses[parent.link_id]
            )
            child_joint_to_world = placement.joint_to_child.then(
                body_poses[child.link_id]
            )
            actual = child_joint_to_world.then(parent_joint_to_world.inverse())
            expected = _expected_joint_transform(
                self.model, joint.joint_id, coordinate_values
            )
            delta_translation = (
                actual.translation.x - expected.translation.x,
                actual.translation.y - expected.translation.y,
                actual.translation.z - expected.translation.z,
            )
            delta_rotation = _rotation_error(actual.rotation, expected.rotation)
            values = (*delta_translation, *delta_rotation)
            for definition, value in zip(
                (item for item in self.definitions if item.joint_id == joint.joint_id),
                values,
            ):
                residuals.append(JointConstraintResidual(
                    definition.constraint_id, joint.joint_id, definition.component,
                    definition.unit, value, definition.tolerance,
                    abs(value) <= definition.tolerance,
                ))
        return JointConstraintEvaluation(
            "1.0", self.model.model_id, self.model.revision, tuple(residuals)
        )


def generate_joint_constraints(
    model: MechanismModel,
    *,
    translation_tolerance_m: float = 1e-8,
    rotation_tolerance_rad: float = 1e-8,
) -> GeneratedJointConstraintSet:
    """Generate deterministic pose-consistency residual definitions for all joints.

    Every joint must have explicit parent/joint/child placements. Every
    non-fixed joint must have a complete v1.2 generalized-coordinate mapping.
    """
    for name, value in (
        ("translation_tolerance_m", translation_tolerance_m),
        ("rotation_tolerance_rad", rotation_tolerance_rad),
    ):
        if (isinstance(value, bool) or not isinstance(value, (int, float))
                or not isfinite(value) or value <= 0):
            raise InvalidModelError(f"{name} must be finite and positive")
    validation = validate_mechanism_model(model)
    if not validation.valid:
        raise InvalidModelError(
            "Cannot generate joint constraints for invalid model: "
            + "; ".join(validation.errors)
        )
    if not model.joints:
        raise InvalidModelError("Joint constraint generation requires at least one joint")
    placed = {item.joint_id for item in model.joint_placements}
    missing_placements = sorted(
        item.joint_id for item in model.joints if item.joint_id not in placed
    )
    if missing_placements:
        raise InvalidModelError(
            f"Joint constraint generation requires placements for every joint: {missing_placements}"
        )
    if validation.joints_without_parameterization:
        raise InvalidModelError(
            "Joint constraint generation requires explicit parameterization for "
            f"non-fixed joints: {list(validation.joints_without_parameterization)}"
        )

    definitions = []
    for joint in sorted(model.joints, key=lambda item: item.joint_id):
        for component in ("translation_x", "translation_y", "translation_z"):
            definitions.append(JointConstraintDefinition(
                f"joint/{joint.joint_id}/closure/{component}", joint.joint_id,
                component, "m", float(translation_tolerance_m),
            ))
        for component in ("rotation_x", "rotation_y", "rotation_z"):
            definitions.append(JointConstraintDefinition(
                f"joint/{joint.joint_id}/closure/{component}", joint.joint_id,
                component, "rad", float(rotation_tolerance_rad),
            ))
    return GeneratedJointConstraintSet("1.0", model, tuple(definitions))
