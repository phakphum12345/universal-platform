"""Validated assembly occurrence and joint contracts.

This module records nominal joint degrees of freedom. It does not solve
assembly mobility, loop closure, motion, collision, or physical feasibility.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from math import isclose, isfinite, sqrt

from .geometry import Vec3


class JointType(str, Enum):
    FIXED = "FIXED"
    REVOLUTE = "REVOLUTE"
    PRISMATIC = "PRISMATIC"
    CYLINDRICAL = "CYLINDRICAL"
    SPHERICAL = "SPHERICAL"
    PLANAR = "PLANAR"


_DOF = {
    JointType.FIXED: 0,
    JointType.REVOLUTE: 1,
    JointType.PRISMATIC: 1,
    JointType.CYLINDRICAL: 2,
    JointType.SPHERICAL: 3,
    JointType.PLANAR: 3,
}
_AXIS_JOINTS = frozenset({
    JointType.REVOLUTE,
    JointType.PRISMATIC,
    JointType.CYLINDRICAL,
})


@dataclass(frozen=True, slots=True)
class PartOccurrence:
    occurrence_id: str
    part_id: str
    revision: str


@dataclass(frozen=True, slots=True)
class Joint:
    joint_id: str
    parent_occurrence: str
    child_occurrence: str
    joint_type: JointType
    axis: Vec3 | None = None
    lower_limit: float | None = None
    upper_limit: float | None = None

    @property
    def degrees_of_freedom(self) -> int:
        try:
            return _DOF[self.joint_type]
        except KeyError as exc:
            raise ValueError(f"Unsupported joint type: {self.joint_type!r}") from exc


@dataclass(frozen=True, slots=True)
class Assembly:
    assembly_id: str
    occurrences: tuple[PartOccurrence, ...]
    joints: tuple[Joint, ...]

    def validate(self) -> tuple[str, ...]:
        errors: list[str] = []
        if not self.assembly_id.strip():
            errors.append("Assembly identifier is required")

        occurrence_ids = [item.occurrence_id for item in self.occurrences]
        if any(not value.strip() for value in occurrence_ids):
            errors.append("Occurrence identifiers must be non-empty")
        if len(occurrence_ids) != len(set(occurrence_ids)):
            errors.append("Duplicate occurrence_id")

        for occurrence in self.occurrences:
            if not occurrence.part_id.strip():
                errors.append(f"Occurrence {occurrence.occurrence_id!r} has an empty part_id")
            if not occurrence.revision.strip():
                errors.append(f"Occurrence {occurrence.occurrence_id!r} has an empty revision")

        joint_ids = [item.joint_id for item in self.joints]
        if any(not value.strip() for value in joint_ids):
            errors.append("Joint identifiers must be non-empty")
        if len(joint_ids) != len(set(joint_ids)):
            errors.append("Duplicate joint_id")

        known = set(occurrence_ids)
        for joint in self.joints:
            if not isinstance(joint.joint_type, JointType):
                errors.append(f"Joint {joint.joint_id!r} has an unsupported joint type")
                continue
            if not joint.parent_occurrence.strip() or not joint.child_occurrence.strip():
                errors.append(f"Joint {joint.joint_id!r} must name parent and child occurrences")
            if joint.parent_occurrence not in known or joint.child_occurrence not in known:
                errors.append(f"Joint {joint.joint_id} references an unknown occurrence")
            if joint.parent_occurrence == joint.child_occurrence:
                errors.append(f"Joint {joint.joint_id} connects an occurrence to itself")

            for label, value in (("lower", joint.lower_limit), ("upper", joint.upper_limit)):
                if value is not None and not isfinite(value):
                    errors.append(f"Joint {joint.joint_id} has a non-finite {label} limit")
            if (joint.lower_limit is not None and joint.upper_limit is not None
                    and isfinite(joint.lower_limit) and isfinite(joint.upper_limit)
                    and joint.lower_limit > joint.upper_limit):
                errors.append(f"Joint {joint.joint_id} has inverted limits")

            if joint.joint_type in _AXIS_JOINTS and joint.axis is None:
                errors.append(f"Joint {joint.joint_id} requires an axis")
            if joint.axis is not None:
                magnitude = sqrt(joint.axis.x ** 2 + joint.axis.y ** 2 + joint.axis.z ** 2)
                if magnitude <= 1e-12:
                    errors.append(f"Joint {joint.joint_id} axis must be non-zero")
                elif not isclose(magnitude, 1.0, rel_tol=0.0, abs_tol=1e-9):
                    errors.append(f"Joint {joint.joint_id} axis must be normalized to unit length")
        return tuple(errors)

    @property
    def nominal_joint_dof(self) -> int:
        return sum(joint.degrees_of_freedom for joint in self.joints)
