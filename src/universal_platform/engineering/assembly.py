"""Assembly graph and joint-degree-of-freedom bookkeeping."""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from .errors import InvalidModelError
from .geometry import Vec3

class JointType(str, Enum):
    FIXED = "FIXED"
    REVOLUTE = "REVOLUTE"
    PRISMATIC = "PRISMATIC"
    CYLINDRICAL = "CYLINDRICAL"
    SPHERICAL = "SPHERICAL"
    PLANAR = "PLANAR"

_DOF = {JointType.FIXED: 0, JointType.REVOLUTE: 1, JointType.PRISMATIC: 1,
        JointType.CYLINDRICAL: 2, JointType.SPHERICAL: 3, JointType.PLANAR: 3}

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
        return _DOF[self.joint_type]

@dataclass(frozen=True, slots=True)
class Assembly:
    assembly_id: str
    occurrences: tuple[PartOccurrence, ...]
    joints: tuple[Joint, ...]

    def validate(self) -> tuple[str, ...]:
        errors = []
        ids = [p.occurrence_id for p in self.occurrences]
        if len(ids) != len(set(ids)):
            errors.append("Duplicate occurrence_id")
        known = set(ids)
        for joint in self.joints:
            if joint.parent_occurrence not in known or joint.child_occurrence not in known:
                errors.append(f"Joint {joint.joint_id} references an unknown occurrence")
            if joint.parent_occurrence == joint.child_occurrence:
                errors.append(f"Joint {joint.joint_id} connects an occurrence to itself")
            if joint.lower_limit is not None and joint.upper_limit is not None and joint.lower_limit > joint.upper_limit:
                errors.append(f"Joint {joint.joint_id} has inverted limits")
            if joint.joint_type in (JointType.REVOLUTE, JointType.PRISMATIC, JointType.CYLINDRICAL) and joint.axis is None:
                errors.append(f"Joint {joint.joint_id} requires an axis")
        return tuple(errors)

    @property
    def nominal_joint_dof(self) -> int:
        return sum(j.degrees_of_freedom for j in self.joints)
