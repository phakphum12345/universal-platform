from copy import deepcopy
from fractions import Fraction as F

import pytest

from universal_platform.engineering.errors import InvalidModelError
from universal_platform.engineering.rational_faceted_solid import RationalFacetedSolid


def tetrahedron():
    # Lexicographically canonical vertices; the oriented boundary is outward.
    vertices = (
        (F(0), F(0), F(0)),
        (F(0), F(0), F(1, 3)),
        (F(0), F(1), F(0)),
        (F(1), F(0), F(0)),
    )
    triangles = (
        (0, 2, 3),
        (0, 3, 1),
        (0, 1, 2),
        (3, 2, 1),
    )
    return RationalFacetedSolid(
        "tetra", "world", "m", vertices, triangles,
        (("source-a", "a" * 64),),
    )


def test_rational_faceted_solid_preserves_non_binary_rational_volume():
    solid = tetrahedron()
    assert solid.exact_signed_volume == F(1, 18)
    snapshot = solid.to_dict()
    assert snapshot["profile"] == "RATIONAL_FACETED_SOLID_V1"
    assert snapshot["vertices"][1][2] == ["1", "3"]
    restored = RationalFacetedSolid.from_dict(snapshot)
    assert restored == solid
    assert restored.to_dict() == snapshot


def test_rational_snapshot_rejects_noncanonical_rational_pairs():
    snapshot = tetrahedron().to_dict()
    snapshot["vertices"][1][2] = ["2", "6"]
    with pytest.raises(InvalidModelError, match="canonical"):
        RationalFacetedSolid.from_dict(snapshot)


def test_rational_snapshot_rejects_float_coordinates_and_tampering():
    snapshot = tetrahedron().to_dict()
    snapshot["vertices"][1][2] = [0.3333333333333333, "1"]
    with pytest.raises(InvalidModelError, match="canonical decimal integer"):
        RationalFacetedSolid.from_dict(snapshot)
    snapshot = tetrahedron().to_dict()
    snapshot["solid_id"] = "changed"
    with pytest.raises(InvalidModelError, match="digest"):
        RationalFacetedSolid.from_dict(snapshot)


def test_rational_shell_rejects_open_or_inconsistently_oriented_edges():
    solid = tetrahedron()
    with pytest.raises(InvalidModelError, match="exactly two incident faces"):
        RationalFacetedSolid(
            solid.solid_id, solid.frame_id, solid.length_unit,
            solid.vertices, solid.triangles[:-1],
        )
    bad = list(solid.triangles)
    bad[0] = tuple(reversed(bad[0]))
    with pytest.raises(InvalidModelError, match="opposite orientation"):
        RationalFacetedSolid(
            solid.solid_id, solid.frame_id, solid.length_unit,
            solid.vertices, tuple(bad),
        )


def test_rational_shell_rejects_resource_exhaustion_and_noncanonical_vertices():
    solid = tetrahedron()
    with pytest.raises(InvalidModelError, match="pair budget"):
        RationalFacetedSolid(
            solid.solid_id, solid.frame_id, solid.length_unit,
            solid.vertices, solid.triangles, max_pairwise_checks=5,
        )
    with pytest.raises(InvalidModelError, match="lexicographically canonical"):
        RationalFacetedSolid(
            "tetra", "world", "m", tuple(reversed(solid.vertices)),
            solid.triangles,
        )


def test_rational_v1_fails_closed_for_cavity_shells():
    snapshot = tetrahedron().to_dict()
    snapshot["shells"].append({
        "shell_id": "cavity", "role": "CAVITY",
        "triangle_indices": [], "parent_outer_shell_id": "outer",
    })
    with pytest.raises(InvalidModelError, match="cavities are unsupported"):
        RationalFacetedSolid.from_dict(snapshot)
