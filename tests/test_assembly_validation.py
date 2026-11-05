import pytest

from universal_platform.engineering.assembly import Assembly, Joint, JointType, PartOccurrence
from universal_platform.engineering.geometry import Vec3


def make_assembly(joints=(), occurrences=None, assembly_id="assembly"):
    if occurrences is None:
        occurrences = (
            PartOccurrence("base", "part-base", "r1"),
            PartOccurrence("arm", "part-arm", "r1"),
        )
    return Assembly(assembly_id, tuple(occurrences), tuple(joints))


def make_revolute(**overrides):
    values = {
        "joint_id": "joint-1",
        "parent_occurrence": "base",
        "child_occurrence": "arm",
        "joint_type": JointType.REVOLUTE,
        "axis": Vec3(0.0, 0.0, 1.0),
        "lower_limit": -1.0,
        "upper_limit": 1.0,
    }
    values.update(overrides)
    return Joint(**values)


def test_valid_revolute_joint_contract_and_nominal_dof():
    assembly = make_assembly([make_revolute()])
    assert assembly.validate() == ()
    assert assembly.nominal_joint_dof == 1


def test_rejects_empty_assembly_and_occurrence_metadata():
    assembly = make_assembly(
        occurrences=[PartOccurrence("", "", "")],
        assembly_id=" ",
    )
    errors = assembly.validate()
    assert "Assembly identifier is required" in errors
    assert "Occurrence identifiers must be non-empty" in errors
    assert any("empty part_id" in error for error in errors)
    assert any("empty revision" in error for error in errors)


def test_rejects_duplicate_occurrence_ids():
    assembly = make_assembly(occurrences=[
        PartOccurrence("same", "part-a", "r1"),
        PartOccurrence("same", "part-b", "r1"),
    ])
    assert "Duplicate occurrence_id" in assembly.validate()


def test_rejects_duplicate_joint_ids():
    assembly = make_assembly([make_revolute(), make_revolute()])
    assert "Duplicate joint_id" in assembly.validate()


def test_rejects_unknown_occurrence_and_self_joint():
    unknown = make_revolute(child_occurrence="missing")
    self_joint = make_revolute(joint_id="self", child_occurrence="base")
    errors = make_assembly([unknown, self_joint]).validate()
    assert any("unknown occurrence" in error for error in errors)
    assert any("connects an occurrence to itself" in error for error in errors)


def test_axis_joint_requires_axis():
    errors = make_assembly([make_revolute(axis=None)]).validate()
    assert "Joint joint-1 requires an axis" in errors


def test_axis_joint_rejects_zero_or_non_unit_axis():
    zero = make_revolute(axis=Vec3(0.0, 0.0, 0.0))
    non_unit = make_revolute(joint_id="non-unit", axis=Vec3(0.0, 0.0, 2.0))
    errors = make_assembly([zero, non_unit]).validate()
    assert any("axis must be non-zero" in error for error in errors)
    assert any("axis must be normalized" in error for error in errors)


@pytest.mark.parametrize("field", ["lower_limit", "upper_limit"])
def test_joint_rejects_non_finite_limits(field):
    errors = make_assembly([make_revolute(**{field: float("inf")})]).validate()
    assert any("non-finite" in error for error in errors)


def test_joint_rejects_inverted_limits():
    errors = make_assembly([make_revolute(lower_limit=2.0, upper_limit=1.0)]).validate()
    assert "Joint joint-1 has inverted limits" in errors


def test_joint_accepts_one_sided_finite_limit():
    assert make_assembly([make_revolute(upper_limit=None)]).validate() == ()


def test_rejects_unknown_joint_type_without_crashing_validation():
    errors = make_assembly([make_revolute(joint_type="UNKNOWN")]).validate()
    assert any("unsupported joint type" in error for error in errors)
