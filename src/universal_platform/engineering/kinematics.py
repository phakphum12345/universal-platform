"""Deterministic forward kinematics for rooted tree assemblies.

Only fixed, revolute and prismatic joints are evaluated. This module does
not solve closed loops, constraints, dynamics, collisions or flexible bodies.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import cos, isfinite, sin, sqrt
from typing import Mapping

from .assembly import Assembly, Joint, JointType
from .errors import InvalidModelError
from .geometry import Vec3
from .transforms import Matrix3, RigidTransform


@dataclass(frozen=True, slots=True)
class JointPlacement:
    """Static parent-to-joint and joint-to-child placement transforms.

    The two transforms share a joint-local frame. Joint.axis is declared in
    the parent occurrence frame and is rotated into the joint frame here.
    """

    joint_id: str
    parent_to_joint: RigidTransform
    joint_to_child: RigidTransform


def _axis_rotation(axis: Vec3, angle: float) -> Matrix3:
    magnitude = sqrt(axis.x * axis.x + axis.y * axis.y + axis.z * axis.z)
    if not isfinite(magnitude) or magnitude <= 1e-12:
        raise InvalidModelError("Kinematic joint axis must be finite and non-zero")
    x, y, z = axis.x / magnitude, axis.y / magnitude, axis.z / magnitude
    c, s, one_minus_c = cos(angle), sin(angle), 1.0 - cos(angle)
    return (
        (c + x*x*one_minus_c, x*y*one_minus_c - z*s, x*z*one_minus_c + y*s),
        (y*x*one_minus_c + z*s, c + y*y*one_minus_c, y*z*one_minus_c - x*s),
        (z*x*one_minus_c - y*s, z*y*one_minus_c + x*s, c + z*z*one_minus_c),
    )


def solve_tree_forward_kinematics(
    assembly: Assembly,
    root_occurrence: str,
    placements: Mapping[str, JointPlacement],
    joint_coordinates: Mapping[str, float] | None = None,
) -> dict[str, RigidTransform]:
    """Return root-to-occurrence poses for a connected rooted joint tree.

    Revolute coordinates are radians; prismatic coordinates use the model
    length unit. The returned transform maps root-occurrence coordinates
    into each occurrence frame.
    """
    errors = assembly.validate()
    if errors:
        raise InvalidModelError("Invalid assembly: " + "; ".join(errors))
    occurrence_ids = {item.occurrence_id for item in assembly.occurrences}
    if root_occurrence not in occurrence_ids:
        raise InvalidModelError(f"Unknown root occurrence: {root_occurrence}")

    joint_by_id = {joint.joint_id: joint for joint in assembly.joints}
    if set(placements) != set(joint_by_id):
        missing = sorted(set(joint_by_id) - set(placements))
        extra = sorted(set(placements) - set(joint_by_id))
        raise InvalidModelError(f"Joint placement mismatch; missing={missing}, extra={extra}")
    coordinates = dict(joint_coordinates or {})
    unknown_coordinates = set(coordinates) - set(joint_by_id)
    if unknown_coordinates:
        raise InvalidModelError(f"Unknown joint coordinates: {sorted(unknown_coordinates)}")

    children: dict[str, list[Joint]] = {item: [] for item in occurrence_ids}
    child_parent: dict[str, str] = {}
    for joint in assembly.joints:
        if joint.child_occurrence in child_parent:
            raise InvalidModelError(
                f"Occurrence {joint.child_occurrence} has multiple parent joints"
            )
        child_parent[joint.child_occurrence] = joint.parent_occurrence
        children[joint.parent_occurrence].append(joint)

    if root_occurrence in child_parent:
        raise InvalidModelError("Root occurrence cannot have a parent joint")
    for occurrence_id in occurrence_ids - {root_occurrence}:
        if occurrence_id not in child_parent:
            raise InvalidModelError(f"Occurrence is disconnected from root: {occurrence_id}")

    poses = {root_occurrence: RigidTransform.identity(root_occurrence)}
    pending = [root_occurrence]
    while pending:
        parent_id = pending.pop(0)
        parent_pose = poses[parent_id]
        for joint in children[parent_id]:
            placement = placements[joint.joint_id]
            parent_to_joint = placement.parent_to_joint
            joint_to_child = placement.joint_to_child
            if parent_to_joint.from_frame != joint.parent_occurrence:
                raise InvalidModelError(
                    f"Joint {joint.joint_id} parent placement frame mismatch"
                )
            if parent_to_joint.to_frame != joint_to_child.from_frame:
                raise InvalidModelError(
                    f"Joint {joint.joint_id} placement joint-frame mismatch"
                )
            if joint_to_child.to_frame != joint.child_occurrence:
                raise InvalidModelError(
                    f"Joint {joint.joint_id} child placement frame mismatch"
                )

            coordinate = coordinates.get(joint.joint_id, 0.0)
            if not isfinite(coordinate):
                raise InvalidModelError(f"Joint {joint.joint_id} coordinate must be finite")
            if joint.lower_limit is not None and coordinate < joint.lower_limit:
                raise InvalidModelError(f"Joint {joint.joint_id} coordinate is below its lower limit")
            if joint.upper_limit is not None and coordinate > joint.upper_limit:
                raise InvalidModelError(f"Joint {joint.joint_id} coordinate is above its upper limit")

            joint_frame = parent_to_joint.to_frame
            if joint.joint_type is JointType.FIXED:
                if coordinate != 0.0:
                    raise InvalidModelError(f"Fixed joint {joint.joint_id} cannot move")
                motion = RigidTransform.identity(joint_frame)
            elif joint.joint_type in (JointType.REVOLUTE, JointType.PRISMATIC):
                if joint.axis is None:
                    raise InvalidModelError(f"Joint {joint.joint_id} requires an axis")
                axis_in_joint = parent_to_joint.apply_vector(joint.axis)
                if joint.joint_type is JointType.REVOLUTE:
                    motion = RigidTransform(
                        joint_frame, joint_frame, _axis_rotation(axis_in_joint, coordinate)
                    )
                else:
                    magnitude = sqrt(
                        axis_in_joint.x ** 2 + axis_in_joint.y ** 2 + axis_in_joint.z ** 2
                    )
                    if magnitude <= 1e-12 or not isfinite(magnitude):
                        raise InvalidModelError(f"Joint {joint.joint_id} has invalid axis")
                    delta = Vec3(
                        axis_in_joint.x / magnitude * coordinate,
                        axis_in_joint.y / magnitude * coordinate,
                        axis_in_joint.z / magnitude * coordinate,
                    )
                    motion = RigidTransform(
                        joint_frame, joint_frame, translation=delta
                    )
            else:
                raise InvalidModelError(
                    f"Joint type {joint.joint_type.value} is not supported by tree kinematics"
                )

            parent_to_child = parent_to_joint.then(motion).then(joint_to_child)
            poses[joint.child_occurrence] = parent_pose.then(parent_to_child)
            pending.append(joint.child_occurrence)

    if set(poses) != occurrence_ids:
        raise InvalidModelError("Assembly contains a cycle or unreachable occurrence")
    return poses
