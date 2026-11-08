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
            solid.vertices, solid.triangles[:-1] + (solid.triangles[0],),
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



def test_rational_parser_rejects_oversized_decimal_strings_before_int_conversion():
    from universal_platform.engineering.rational_faceted_solid import _parse_integer_string

    with pytest.raises(InvalidModelError, match="before integer conversion"):
        _parse_integer_string("9" * 4, "numerator", 8)
    with pytest.raises(InvalidModelError, match="before integer conversion"):
        _parse_integer_string("-" + "9" * 4, "numerator", 8)
    with pytest.raises(InvalidModelError, match="before integer conversion"):
        _parse_integer_string("9" * 4, "denominator", 8)


def test_rational_parser_accepts_bit_limit_boundary_and_rejects_next_value():
    from universal_platform.engineering.rational_faceted_solid import _parse_integer_string

    assert _parse_integer_string("255", "integer", 8) == 255
    with pytest.raises(InvalidModelError, match="max_coordinate_bits"):
        _parse_integer_string("256", "integer", 8)


def test_from_dict_validates_resource_limits_before_parsing_geometry(monkeypatch):
    import universal_platform.engineering.rational_faceted_solid as rational_module

    snapshot = tetrahedron().to_dict()

    def unexpected_parse(*args, **kwargs):
        raise AssertionError("geometry parser must not run before resource preflight")

    monkeypatch.setattr(rational_module, "_parse_rational", unexpected_parse)
    with pytest.raises(InvalidModelError, match="max_coordinate_bits"):
        RationalFacetedSolid.from_dict(snapshot, max_coordinate_bits=0)
    with pytest.raises(InvalidModelError, match="max_pairwise_checks"):
        RationalFacetedSolid.from_dict(snapshot, max_pairwise_checks=True)
    with pytest.raises(InvalidModelError, match="hard ceiling"):
        RationalFacetedSolid.from_dict(snapshot, max_pairwise_checks=5_000_001)


def test_from_dict_enforces_aggregate_rational_budget_incrementally(monkeypatch):
    import universal_platform.engineering.rational_faceted_solid as rational_module

    snapshot = tetrahedron().to_dict()
    monkeypatch.setattr(rational_module, "_MAX_AGGREGATE_RATIONAL_BITS", 8)
    with pytest.raises(InvalidModelError, match="aggregate rational bit budget"):
        RationalFacetedSolid.from_dict(snapshot)


def test_rational_solid_enforces_metadata_and_provenance_limits(monkeypatch):
    import universal_platform.engineering.rational_faceted_solid as rational_module

    solid = tetrahedron()
    with pytest.raises(InvalidModelError, match="solid_id exceeds"):
        RationalFacetedSolid(
            "a" * (rational_module._MAX_SOLID_ID_CHARS + 1), solid.frame_id,
            solid.length_unit, solid.vertices, solid.triangles,
        )
    with pytest.raises(InvalidModelError, match="source provenance record count"):
        RationalFacetedSolid(
            solid.solid_id, solid.frame_id, solid.length_unit,
            solid.vertices, solid.triangles,
            tuple((f"source-{index}", f"{index:064x}") for index in range(4097)),
        )
    snapshot = solid.to_dict()
    snapshot["source_provenance"][0]["source_id"] = "a" * (
        rational_module._MAX_SOURCE_ID_CHARS + 1
    )
    with pytest.raises(InvalidModelError, match="bounded stable IDs"):
        RationalFacetedSolid.from_dict(snapshot)


def test_from_dict_rejects_geometry_counts_before_parsing_coordinates(monkeypatch):
    import universal_platform.engineering.rational_faceted_solid as rational_module

    snapshot = tetrahedron().to_dict()
    snapshot["vertices"] = []
    snapshot["triangles"] = []

    def unexpected_parse(*args, **kwargs):
        raise AssertionError("geometry parser must not run for out-of-range counts")

    monkeypatch.setattr(rational_module, "_parse_rational", unexpected_parse)
    with pytest.raises(InvalidModelError, match="geometry count"):
        RationalFacetedSolid.from_dict(snapshot)



def test_rational_solid_bounds_all_metadata_fields_before_identifier_parsing():
    import universal_platform.engineering.rational_faceted_solid as rational_module

    solid = tetrahedron()
    with pytest.raises(InvalidModelError, match="frame_id exceeds"):
        RationalFacetedSolid(
            solid.solid_id, "a" * (rational_module._MAX_FRAME_ID_CHARS + 1),
            solid.length_unit, solid.vertices, solid.triangles,
        )
    with pytest.raises(InvalidModelError, match="length_unit exceeds"):
        RationalFacetedSolid(
            solid.solid_id, solid.frame_id,
            "a" * (rational_module._MAX_LENGTH_UNIT_CHARS + 1),
            solid.vertices, solid.triangles,
        )
    snapshot = solid.to_dict()
    snapshot["frame_id"] = "a" * (rational_module._MAX_FRAME_ID_CHARS + 1)
    with pytest.raises(InvalidModelError, match="frame_id is missing or exceeds"):
        RationalFacetedSolid.from_dict(snapshot)


def test_rational_solid_enforces_aggregate_metadata_character_budget(monkeypatch):
    import universal_platform.engineering.rational_faceted_solid as rational_module

    solid = tetrahedron()
    monkeypatch.setattr(rational_module, "_MAX_METADATA_CHARS", 32)
    with pytest.raises(InvalidModelError, match="aggregate metadata character budget"):
        RationalFacetedSolid(
            solid.solid_id, solid.frame_id, solid.length_unit,
            solid.vertices, solid.triangles, solid.source_provenance,
        )
