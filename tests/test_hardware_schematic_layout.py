import json
import xml.etree.ElementTree as ET

import pytest

from universal_platform.engineering.errors import InvalidModelError
from universal_platform.hardware.schematic import Component, Net, Pin, PinRef, SchematicModel
from universal_platform.hardware.schematic_layout import (
    ComponentPlacement, NetRoute, SchematicLayout, SchematicPoint,
    SymbolDefinition, SymbolGraphic, SymbolGraphicKind, SymbolPin,
    render_schematic_svg,
)


def sample_schematic():
    resistor = Component(
        "component.r1", "R1", "symbol.resistor.2",
        (Pin("r1.pin.1", "1", "A"), Pin("r1.pin.2", "2", "B")),
        "10k & 1%",
    )
    connector = Component(
        "component.j1", "J1", "symbol.connector.2",
        (Pin("j1.pin.1", "1", "GND"), Pin("j1.pin.2", "2", "VCC")),
    )
    nets = (
        Net("net.gnd", (PinRef("component.r1", "r1.pin.1"), PinRef("component.j1", "j1.pin.1")), "GND"),
        Net("net.vcc", (PinRef("component.r1", "r1.pin.2"), PinRef("component.j1", "j1.pin.2")), "VCC"),
    )
    return SchematicModel((resistor, connector), nets)


def sample_layout():
    resistor = SymbolDefinition(
        "symbol.resistor.2", 20, 8,
        (SymbolPin("1", SchematicPoint(-15, 0)), SymbolPin("2", SchematicPoint(15, 0))),
        (SymbolGraphic("body", SymbolGraphicKind.POLYLINE, (
            SchematicPoint(-8, 0), SchematicPoint(-5, -2), SchematicPoint(-2, 2),
            SchematicPoint(1, -2), SchematicPoint(4, 2), SchematicPoint(7, 0),
        )),),
    )
    connector = SymbolDefinition(
        "symbol.connector.2", 10, 8,
        (SymbolPin("1", SchematicPoint(-10, -2)), SymbolPin("2", SchematicPoint(-10, 2))),
        (SymbolGraphic("body", SymbolGraphicKind.RECTANGLE, (SchematicPoint(-5, -3), SchematicPoint(5, 3))),),
    )
    routes = (
        NetRoute("route.gnd", "net.gnd", PinRef("component.r1", "r1.pin.1"), PinRef("component.j1", "j1.pin.1"),
                 (SchematicPoint(80, 38), SchematicPoint(120, 38))),
        NetRoute("route.vcc", "net.vcc", PinRef("component.r1", "r1.pin.2"), PinRef("component.j1", "j1.pin.2"),
                 (SchematicPoint(80, 42), SchematicPoint(120, 42))),
    )
    return SchematicLayout(
        "layout.board-1", 200, 100, (resistor, connector),
        (ComponentPlacement("component.r1", 40, 40), ComponentPlacement("component.j1", 160, 40)),
        routes,
    )


def test_layout_round_trip_and_svg_render_are_deterministic_and_well_formed():
    schematic, layout = sample_schematic(), sample_layout()
    snapshot = json.loads(json.dumps(layout.to_dict()))
    restored = SchematicLayout.from_dict(snapshot)
    assert restored.to_dict() == snapshot
    result = render_schematic_svg(schematic, restored)
    reordered = SchematicLayout(
        layout.layout_id, layout.page_width_mm, layout.page_height_mm,
        tuple(reversed(layout.symbols)), tuple(reversed(layout.component_placements)), tuple(reversed(layout.net_routes)),
    )
    assert render_schematic_svg(schematic, reordered).svg == result.svg
    root = ET.fromstring(result.svg)
    assert root.tag.endswith("svg")
    assert result.rendered_component_ids == ("component.j1", "component.r1")
    assert result.rendered_net_ids == ("net.gnd", "net.vcc")
    assert result.unrouted_net_ids == ()
    assert "R1" in result.svg and "J1" in result.svg
    assert "GND" in result.svg and "VCC" in result.svg
    assert "10k &amp; 1%" in result.svg
    assert 'data-pin-id="r1.pin.1"' in result.svg


def test_unrouted_net_is_reported_not_claimed_as_rendered():
    schematic, layout = sample_schematic(), sample_layout()
    incomplete = SchematicLayout(
        layout.layout_id, layout.page_width_mm, layout.page_height_mm,
        layout.symbols, layout.component_placements, (layout.net_routes[0],),
    )
    result = render_schematic_svg(schematic, incomplete)
    assert result.rendered_net_ids == ("net.gnd",)
    assert result.unrouted_net_ids == ("net.vcc",)
    assert result.warnings == ("net net.vcc has no complete route",)


def test_missing_component_placement_symbol_or_pin_fails_closed():
    schematic, layout = sample_schematic(), sample_layout()
    missing_placement = SchematicLayout(layout.layout_id, 200, 100, layout.symbols, layout.component_placements[:1], layout.net_routes)
    with pytest.raises(InvalidModelError, match="cover every schematic component"):
        render_schematic_svg(schematic, missing_placement)
    missing_symbol = SchematicLayout(layout.layout_id, 200, 100, layout.symbols[:1], layout.component_placements, layout.net_routes)
    with pytest.raises(InvalidModelError, match="missing symbol definition"):
        render_schematic_svg(schematic, missing_symbol)
    wrong_pins = SymbolDefinition("symbol.resistor.2", 20, 8, (SymbolPin("1", SchematicPoint(-15, 0)),),
                                  layout.symbols[1].graphics)
    wrong_symbols = (wrong_pins, layout.symbols[1])
    wrong_layout = SchematicLayout(layout.layout_id, 200, 100, wrong_symbols, layout.component_placements, layout.net_routes)
    with pytest.raises(InvalidModelError, match="pin numbers do not match"):
        render_schematic_svg(schematic, wrong_layout)


def test_net_route_must_connect_terminals_of_the_declared_net():
    schematic, layout = sample_schematic(), sample_layout()
    invalid = NetRoute("route.bad", "net.gnd", PinRef("component.r1", "r1.pin.1"), PinRef("component.j1", "j1.pin.2"))
    bad_layout = SchematicLayout(layout.layout_id, 200, 100, layout.symbols, layout.component_placements, (invalid,))
    with pytest.raises(InvalidModelError, match="terminals of net"):
        render_schematic_svg(schematic, bad_layout)


def test_page_bounds_and_layout_snapshot_are_strict():
    schematic, layout = sample_schematic(), sample_layout()
    outside = SchematicLayout(layout.layout_id, 100, 60, layout.symbols, layout.component_placements, layout.net_routes)
    with pytest.raises(InvalidModelError, match="outside the schematic page"):
        render_schematic_svg(schematic, outside)
    data = layout.to_dict()
    with pytest.raises(InvalidModelError, match="missing or unknown"):
        SchematicLayout.from_dict(dict(data, unexpected=True))
