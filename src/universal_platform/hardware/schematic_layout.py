"""Deterministic offline schematic layout and SVG rendering.

This module renders supplied symbol geometry and layout metadata. It does not
perform electrical rule checking, circuit simulation, EDA import/export or
hardware communication.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum
from html import escape
from math import cos, isfinite, sin
import re
from typing import Any, ClassVar

from universal_platform.engineering.errors import InvalidModelError
from .schematic import PinRef, SchematicModel

_IDENTIFIER = re.compile(r"^[a-z0-9]+(?:[._/-][a-z0-9]+)*$")


def _id(value: str, label: str) -> None:
    if not isinstance(value, str) or not _IDENTIFIER.fullmatch(value):
        raise InvalidModelError(f"{label} must be a stable lowercase identifier")


def _number(value: float, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value):
        raise InvalidModelError(f"{label} must be a finite number")
    return float(value)


def _fmt(value: float) -> str:
    rounded = 0.0 if abs(value) < 0.0000005 else value
    return f"{rounded:.6f}".rstrip("0").rstrip(".") or "0"


@dataclass(frozen=True, slots=True)
class SchematicPoint:
    x_mm: float
    y_mm: float

    def __post_init__(self) -> None:
        object.__setattr__(self, "x_mm", _number(self.x_mm, "x_mm"))
        object.__setattr__(self, "y_mm", _number(self.y_mm, "y_mm"))

    def to_dict(self) -> dict[str, float]:
        return {"x_mm": self.x_mm, "y_mm": self.y_mm}


@dataclass(frozen=True, slots=True)
class SymbolPin:
    number: str
    local_position: SchematicPoint

    def __post_init__(self) -> None:
        if not isinstance(self.number, str) or not self.number.strip():
            raise InvalidModelError("symbol pin number must be non-empty text")
        if not isinstance(self.local_position, SchematicPoint):
            raise InvalidModelError("symbol pin local_position must be a SchematicPoint")

    def to_dict(self) -> dict[str, Any]:
        return {"number": self.number, "local_position": self.local_position.to_dict()}


class SymbolGraphicKind(str, Enum):
    LINE = "LINE"
    POLYLINE = "POLYLINE"
    RECTANGLE = "RECTANGLE"
    CIRCLE = "CIRCLE"


@dataclass(frozen=True, slots=True)
class SymbolGraphic:
    graphic_id: str
    kind: SymbolGraphicKind
    points: tuple[SchematicPoint, ...]
    radius_mm: float | None = None

    def __post_init__(self) -> None:
        _id(self.graphic_id, "graphic_id")
        if not isinstance(self.kind, SymbolGraphicKind):
            raise InvalidModelError("symbol graphic kind must be a SymbolGraphicKind")
        if not isinstance(self.points, tuple) or any(not isinstance(p, SchematicPoint) for p in self.points):
            raise InvalidModelError("symbol graphic points must be an immutable tuple of SchematicPoint records")
        expected = {
            SymbolGraphicKind.LINE: (2, 2),
            SymbolGraphicKind.POLYLINE: (2, None),
            SymbolGraphicKind.RECTANGLE: (2, 2),
            SymbolGraphicKind.CIRCLE: (1, 1),
        }[self.kind]
        if len(self.points) < expected[0] or (expected[1] is not None and len(self.points) > expected[1]):
            raise InvalidModelError(f"{self.kind.value} symbol graphic has an invalid point count")
        if self.kind is SymbolGraphicKind.CIRCLE:
            radius = _number(self.radius_mm, "symbol circle radius")
            if radius <= 0:
                raise InvalidModelError("symbol circle radius must be positive")
            object.__setattr__(self, "radius_mm", radius)
        elif self.radius_mm is not None:
            raise InvalidModelError("radius_mm is only valid for CIRCLE symbol graphics")
        if self.kind is SymbolGraphicKind.RECTANGLE:
            a, b = self.points
            if a.x_mm == b.x_mm or a.y_mm == b.y_mm:
                raise InvalidModelError("symbol rectangle must have positive width and height")

    def to_dict(self) -> dict[str, Any]:
        return {
            "graphic_id": self.graphic_id,
            "kind": self.kind.value,
            "points": [p.to_dict() for p in self.points],
            **({"radius_mm": self.radius_mm} if self.radius_mm is not None else {}),
        }


@dataclass(frozen=True, slots=True)
class SymbolDefinition:
    symbol_id: str
    width_mm: float
    height_mm: float
    pins: tuple[SymbolPin, ...]
    graphics: tuple[SymbolGraphic, ...]

    def __post_init__(self) -> None:
        _id(self.symbol_id, "symbol_id")
        width = _number(self.width_mm, "symbol width_mm")
        height = _number(self.height_mm, "symbol height_mm")
        if width <= 0 or height <= 0:
            raise InvalidModelError("symbol width and height must be positive")
        object.__setattr__(self, "width_mm", width)
        object.__setattr__(self, "height_mm", height)
        if not isinstance(self.pins, tuple) or not self.pins or any(not isinstance(p, SymbolPin) for p in self.pins):
            raise InvalidModelError("symbol pins must be a non-empty immutable tuple")
        if not isinstance(self.graphics, tuple) or any(not isinstance(g, SymbolGraphic) for g in self.graphics):
            raise InvalidModelError("symbol graphics must be an immutable tuple")
        numbers = tuple(pin.number for pin in self.pins)
        ids = tuple(graphic.graphic_id for graphic in self.graphics)
        if len(numbers) != len(set(numbers)):
            raise InvalidModelError("symbol pin numbers must be unique")
        if len(ids) != len(set(ids)):
            raise InvalidModelError("symbol graphic IDs must be unique")
        object.__setattr__(self, "pins", tuple(sorted(self.pins, key=lambda p: p.number)))
        object.__setattr__(self, "graphics", tuple(sorted(self.graphics, key=lambda g: g.graphic_id)))

    def to_dict(self) -> dict[str, Any]:
        return {
            "symbol_id": self.symbol_id,
            "width_mm": self.width_mm,
            "height_mm": self.height_mm,
            "pins": [p.to_dict() for p in self.pins],
            "graphics": [g.to_dict() for g in self.graphics],
        }


@dataclass(frozen=True, slots=True)
class ComponentPlacement:
    component_id: str
    x_mm: float
    y_mm: float
    rotation_rad: float = 0.0

    def __post_init__(self) -> None:
        _id(self.component_id, "component_id")
        for field in ("x_mm", "y_mm", "rotation_rad"):
            object.__setattr__(self, field, _number(getattr(self, field), field))

    def to_dict(self) -> dict[str, Any]:
        return {"component_id": self.component_id, "x_mm": self.x_mm, "y_mm": self.y_mm, "rotation_rad": self.rotation_rad}


@dataclass(frozen=True, slots=True)
class NetRoute:
    route_id: str
    net_id: str
    start_pin: PinRef
    end_pin: PinRef
    waypoints: tuple[SchematicPoint, ...] = ()

    def __post_init__(self) -> None:
        _id(self.route_id, "route_id")
        _id(self.net_id, "net_id")
        if not isinstance(self.start_pin, PinRef) or not isinstance(self.end_pin, PinRef):
            raise InvalidModelError("net route endpoints must be PinRef records")
        if self.start_pin == self.end_pin:
            raise InvalidModelError("net route endpoints must be different pins")
        if not isinstance(self.waypoints, tuple) or any(not isinstance(p, SchematicPoint) for p in self.waypoints):
            raise InvalidModelError("net route waypoints must be an immutable tuple of SchematicPoint records")

    def to_dict(self) -> dict[str, Any]:
        return {
            "route_id": self.route_id,
            "net_id": self.net_id,
            "start_pin": self.start_pin.to_dict(),
            "end_pin": self.end_pin.to_dict(),
            "waypoints": [p.to_dict() for p in self.waypoints],
        }


@dataclass(frozen=True, slots=True)
class SchematicLayout:
    layout_id: str
    page_width_mm: float
    page_height_mm: float
    symbols: tuple[SymbolDefinition, ...]
    component_placements: tuple[ComponentPlacement, ...]
    net_routes: tuple[NetRoute, ...]

    SCHEMA_VERSION: ClassVar[str] = "1.0"

    def __post_init__(self) -> None:
        _id(self.layout_id, "layout_id")
        width = _number(self.page_width_mm, "page_width_mm")
        height = _number(self.page_height_mm, "page_height_mm")
        if width <= 0 or height <= 0:
            raise InvalidModelError("schematic page dimensions must be positive")
        object.__setattr__(self, "page_width_mm", width)
        object.__setattr__(self, "page_height_mm", height)
        for name, values, kind in (
            ("symbols", self.symbols, SymbolDefinition),
            ("component_placements", self.component_placements, ComponentPlacement),
            ("net_routes", self.net_routes, NetRoute),
        ):
            if not isinstance(values, tuple) or any(not isinstance(item, kind) for item in values):
                raise InvalidModelError(f"{name} must be an immutable tuple of {kind.__name__} records")
        for name, ids in (
            ("symbol IDs", tuple(item.symbol_id for item in self.symbols)),
            ("component placement IDs", tuple(item.component_id for item in self.component_placements)),
            ("route IDs", tuple(item.route_id for item in self.net_routes)),
        ):
            if len(ids) != len(set(ids)):
                raise InvalidModelError(f"{name} must be unique")
        object.__setattr__(self, "symbols", tuple(sorted(self.symbols, key=lambda item: item.symbol_id)))
        object.__setattr__(self, "component_placements", tuple(sorted(self.component_placements, key=lambda item: item.component_id)))
        object.__setattr__(self, "net_routes", tuple(sorted(self.net_routes, key=lambda item: item.route_id)))

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.SCHEMA_VERSION,
            "layout_id": self.layout_id,
            "page_width_mm": self.page_width_mm,
            "page_height_mm": self.page_height_mm,
            "symbols": [item.to_dict() for item in self.symbols],
            "component_placements": [item.to_dict() for item in self.component_placements],
            "net_routes": [item.to_dict() for item in self.net_routes],
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "SchematicLayout":
        required = {"schema_version", "layout_id", "page_width_mm", "page_height_mm", "symbols", "component_placements", "net_routes"}
        if not isinstance(value, Mapping) or set(value) != required:
            raise InvalidModelError("SchematicLayout snapshot has missing or unknown fields")
        if value["schema_version"] != cls.SCHEMA_VERSION:
            raise InvalidModelError("Unsupported SchematicLayout schema_version")
        if not all(isinstance(value[key], (list, tuple)) for key in ("symbols", "component_placements", "net_routes")):
            raise InvalidModelError("schematic layout collections must be arrays")
        symbols = []
        for raw in value["symbols"]:
            if not isinstance(raw, Mapping) or set(raw) != {"symbol_id", "width_mm", "height_mm", "pins", "graphics"}:
                raise InvalidModelError("SymbolDefinition snapshot has missing or unknown fields")
            if not isinstance(raw["pins"], (list, tuple)) or not isinstance(raw["graphics"], (list, tuple)):
                raise InvalidModelError("symbol pins and graphics must be arrays")
            pins = []
            for pin in raw["pins"]:
                if not isinstance(pin, Mapping) or set(pin) != {"number", "local_position"}:
                    raise InvalidModelError("SymbolPin snapshot has missing or unknown fields")
                pins.append(SymbolPin(pin["number"], _point_from_dict(pin["local_position"])))
            graphics = []
            for graphic in raw["graphics"]:
                if not isinstance(graphic, Mapping) or set(graphic) - {"graphic_id", "kind", "points", "radius_mm"} or not {"graphic_id", "kind", "points"}.issubset(graphic):
                    raise InvalidModelError("SymbolGraphic snapshot has missing or unknown fields")
                if not isinstance(graphic["points"], (list, tuple)):
                    raise InvalidModelError("symbol graphic points must be an array")
                try:
                    kind = SymbolGraphicKind(graphic["kind"])
                except (ValueError, TypeError) as exc:
                    raise InvalidModelError("Unsupported SymbolGraphic kind") from exc
                graphics.append(SymbolGraphic(
                    graphic["graphic_id"], kind,
                    tuple(_point_from_dict(point) for point in graphic["points"]),
                    graphic.get("radius_mm"),
                ))
            symbols.append(SymbolDefinition(raw["symbol_id"], raw["width_mm"], raw["height_mm"], tuple(pins), tuple(graphics)))
        placements = []
        for raw in value["component_placements"]:
            if not isinstance(raw, Mapping) or set(raw) != {"component_id", "x_mm", "y_mm", "rotation_rad"}:
                raise InvalidModelError("ComponentPlacement snapshot has missing or unknown fields")
            placements.append(ComponentPlacement(raw["component_id"], raw["x_mm"], raw["y_mm"], raw["rotation_rad"]))
        routes = []
        for raw in value["net_routes"]:
            if not isinstance(raw, Mapping) or set(raw) != {"route_id", "net_id", "start_pin", "end_pin", "waypoints"}:
                raise InvalidModelError("NetRoute snapshot has missing or unknown fields")
            if not isinstance(raw["waypoints"], (list, tuple)):
                raise InvalidModelError("net route waypoints must be an array")
            routes.append(NetRoute(
                raw["route_id"], raw["net_id"], _pin_ref_from_dict(raw["start_pin"]),
                _pin_ref_from_dict(raw["end_pin"]), tuple(_point_from_dict(point) for point in raw["waypoints"]),
            ))
        return cls(value["layout_id"], value["page_width_mm"], value["page_height_mm"], tuple(symbols), tuple(placements), tuple(routes))


def _point_from_dict(value: Any) -> SchematicPoint:
    if not isinstance(value, Mapping) or set(value) != {"x_mm", "y_mm"}:
        raise InvalidModelError("SchematicPoint snapshot has missing or unknown fields")
    return SchematicPoint(value["x_mm"], value["y_mm"])


def _pin_ref_from_dict(value: Any) -> PinRef:
    if not isinstance(value, Mapping) or set(value) != {"component_id", "pin_id"}:
        raise InvalidModelError("PinRef snapshot has missing or unknown fields")
    return PinRef(value["component_id"], value["pin_id"])


def _transform_point(point: SchematicPoint, placement: ComponentPlacement) -> SchematicPoint:
    c, s = cos(placement.rotation_rad), sin(placement.rotation_rad)
    return SchematicPoint(
        placement.x_mm + c * point.x_mm - s * point.y_mm,
        placement.y_mm + s * point.x_mm + c * point.y_mm,
    )


def _inside_page(point: SchematicPoint, width: float, height: float) -> bool:
    eps = 1e-9
    return -eps <= point.x_mm <= width + eps and -eps <= point.y_mm <= height + eps


@dataclass(frozen=True, slots=True)
class SchematicRenderResult:
    svg: str
    rendered_component_ids: tuple[str, ...]
    rendered_net_ids: tuple[str, ...]
    unrouted_net_ids: tuple[str, ...]
    warnings: tuple[str, ...]


def render_schematic_svg(schematic: SchematicModel, layout: SchematicLayout) -> SchematicRenderResult:
    """Render a deterministic SVG and explicitly report nets without complete routes."""
    if not isinstance(schematic, SchematicModel) or not isinstance(layout, SchematicLayout):
        raise InvalidModelError("render requires SchematicModel and SchematicLayout records")
    components = {item.component_id: item for item in schematic.components}
    placements = {item.component_id: item for item in layout.component_placements}
    symbols = {item.symbol_id: item for item in layout.symbols}
    if set(placements) != set(components):
        raise InvalidModelError("component placements must cover every schematic component exactly once")
    nets = {item.net_id: item for item in schematic.nets}
    pin_records = {
        (component.component_id, pin.pin_id): (component, pin)
        for component in schematic.components for pin in component.pins
    }
    pin_positions: dict[tuple[str, str], SchematicPoint] = {}
    component_symbols: dict[str, SymbolDefinition] = {}
    for component_id, component in sorted(components.items()):
        placement = placements[component_id]
        symbol = symbols.get(component.symbol_id)
        if symbol is None:
            raise InvalidModelError(f"layout is missing symbol definition: {component.symbol_id}")
        symbol_pins = {pin.number: pin for pin in symbol.pins}
        component_numbers = {pin.number for pin in component.pins}
        if set(symbol_pins) != component_numbers:
            raise InvalidModelError(f"symbol pin numbers do not match component {component.reference_designator}")
        component_symbols[component_id] = symbol
        corners = (
            SchematicPoint(-symbol.width_mm / 2, -symbol.height_mm / 2),
            SchematicPoint(symbol.width_mm / 2, -symbol.height_mm / 2),
            SchematicPoint(symbol.width_mm / 2, symbol.height_mm / 2),
            SchematicPoint(-symbol.width_mm / 2, symbol.height_mm / 2),
        )
        if not all(_inside_page(_transform_point(point, placement), layout.page_width_mm, layout.page_height_mm) for point in corners):
            raise InvalidModelError(f"component {component.reference_designator} lies outside the schematic page")
        for pin in component.pins:
            position = _transform_point(symbol_pins[pin.number].local_position, placement)
            if not _inside_page(position, layout.page_width_mm, layout.page_height_mm):
                raise InvalidModelError(f"pin {component.reference_designator}.{pin.number} lies outside the schematic page")
            pin_positions[(component_id, pin.pin_id)] = position

    route_paths: list[tuple[NetRoute, tuple[SchematicPoint, ...]]] = []
    route_graphs: dict[str, dict[tuple[str, str], set[tuple[str, str]]]] = {net_id: {} for net_id in nets}
    for route in layout.net_routes:
        net = nets.get(route.net_id)
        if net is None:
            raise InvalidModelError(f"net route references unknown net: {route.net_id}")
        terminals = {(terminal.component_id, terminal.pin_id) for terminal in net.terminals}
        start_key = (route.start_pin.component_id, route.start_pin.pin_id)
        end_key = (route.end_pin.component_id, route.end_pin.pin_id)
        if start_key not in terminals or end_key not in terminals:
            raise InvalidModelError(f"net route endpoints must be terminals of net {route.net_id}")
        if start_key not in pin_positions or end_key not in pin_positions:
            raise InvalidModelError("net route references an unknown placed pin")
        points = (pin_positions[start_key], *route.waypoints, pin_positions[end_key])
        if not all(_inside_page(point, layout.page_width_mm, layout.page_height_mm) for point in points):
            raise InvalidModelError(f"net route {route.route_id} leaves the schematic page")
        route_paths.append((route, points))
        route_graphs[route.net_id].setdefault(start_key, set()).add(end_key)
        route_graphs[route.net_id].setdefault(end_key, set()).add(start_key)

    rendered_nets: list[str] = []
    unrouted_nets: list[str] = []
    for net_id, net in sorted(nets.items()):
        terminals = {(terminal.component_id, terminal.pin_id) for terminal in net.terminals}
        graph = route_graphs[net_id]
        if not graph:
            unrouted_nets.append(net_id)
            continue
        visited = set()
        stack = [next(iter(terminals))]
        while stack:
            current = stack.pop()
            if current in visited:
                continue
            visited.add(current)
            stack.extend(graph.get(current, ()))
        if visited >= terminals:
            rendered_nets.append(net_id)
        else:
            unrouted_nets.append(net_id)

    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{_fmt(layout.page_width_mm)}mm" height="{_fmt(layout.page_height_mm)}mm" viewBox="0 0 {_fmt(layout.page_width_mm)} {_fmt(layout.page_height_mm)}">',
        f'<title>{escape(layout.layout_id)}</title>',
        '<rect x="0" y="0" width="100%" height="100%" fill="#ffffff"/>',
    ]
    for route, points in sorted(route_paths, key=lambda item: item[0].route_id):
        coords = " ".join(f"{_fmt(point.x_mm)},{_fmt(point.y_mm)}" for point in points)
        lines.append(f'<polyline id="route-{escape(route.route_id)}" data-net-id="{escape(route.net_id)}" points="{coords}" fill="none" stroke="#222222" stroke-width="0.6" stroke-linejoin="round" stroke-linecap="round"/>')
    for net_id in rendered_nets:
        route = next(route for route, _ in sorted(route_paths, key=lambda item: item[0].route_id) if route.net_id == net_id)
        points = next(points for candidate, points in route_paths if candidate.route_id == route.route_id)
        midpoint = points[len(points) // 2]
        net = nets[net_id]
        label = net.name or net.net_id
        lines.append(f'<text data-net-label="{escape(net_id)}" x="{_fmt(midpoint.x_mm)}" y="{_fmt(midpoint.y_mm - 1.5)}" font-size="2.8" fill="#333333">{escape(label)}</text>')
    for component_id, component in sorted(components.items()):
        placement = placements[component_id]
        symbol = component_symbols[component_id]
        for graphic in symbol.graphics:
            points = tuple(_transform_point(point, placement) for point in graphic.points)
            common = f'id="symbol-{escape(component_id)}-{escape(graphic.graphic_id)}" data-component-id="{escape(component_id)}" fill="none" stroke="#111111" stroke-width="0.7"'
            if graphic.kind is SymbolGraphicKind.LINE:
                a, b = points
                lines.append(f'<line {common} x1="{_fmt(a.x_mm)}" y1="{_fmt(a.y_mm)}" x2="{_fmt(b.x_mm)}" y2="{_fmt(b.y_mm)}"/>')
            elif graphic.kind is SymbolGraphicKind.POLYLINE:
                coords = " ".join(f"{_fmt(point.x_mm)},{_fmt(point.y_mm)}" for point in points)
                lines.append(f'<polyline {common} points="{coords}"/>')
            elif graphic.kind is SymbolGraphicKind.RECTANGLE:
                a, b = graphic.points
                local = (
                    SchematicPoint(a.x_mm, a.y_mm), SchematicPoint(b.x_mm, a.y_mm),
                    SchematicPoint(b.x_mm, b.y_mm), SchematicPoint(a.x_mm, b.y_mm),
                )
                world = tuple(_transform_point(point, placement) for point in local)
                coords = " ".join(f"{_fmt(point.x_mm)},{_fmt(point.y_mm)}" for point in world)
                lines.append(f'<polygon {common} points="{coords}"/>')
            else:
                center = points[0]
                lines.append(f'<circle {common} cx="{_fmt(center.x_mm)}" cy="{_fmt(center.y_mm)}" r="{_fmt(graphic.radius_mm or 0.0)}"/>')
        ref_y = placement.y_mm - symbol.height_mm / 2.0 - 3.0
        value_y = placement.y_mm + symbol.height_mm / 2.0 + 3.0
        lines.append(f'<text data-component-ref="{escape(component_id)}" x="{_fmt(placement.x_mm)}" y="{_fmt(ref_y)}" text-anchor="middle" font-size="3.2" fill="#111111">{escape(component.reference_designator)}</text>')
        if component.value is not None:
            lines.append(f'<text data-component-value="{escape(component_id)}" x="{_fmt(placement.x_mm)}" y="{_fmt(value_y)}" text-anchor="middle" font-size="2.6" fill="#333333">{escape(component.value)}</text>')
        symbol_pins = {pin.number: pin for pin in symbol.pins}
        for pin in component.pins:
            position = pin_positions[(component_id, pin.pin_id)]
            local = symbol_pins[pin.number].local_position
            anchor = "start" if local.x_mm >= 0 else "end"
            label_x = position.x_mm + (2.0 if anchor == "start" else -2.0)
            lines.append(f'<circle data-pin-id="{escape(pin.pin_id)}" data-component-id="{escape(component_id)}" cx="{_fmt(position.x_mm)}" cy="{_fmt(position.y_mm)}" r="0.7" fill="#ffffff" stroke="#111111" stroke-width="0.5"/>')
            lines.append(f'<text x="{_fmt(label_x)}" y="{_fmt(position.y_mm - 1.0)}" text-anchor="{anchor}" font-size="2.2" fill="#444444">{escape(pin.number)} {escape(pin.name)}</text>')
    lines.append("</svg>")
    warnings = tuple(f"net {net_id} has no complete route" for net_id in unrouted_nets)
    return SchematicRenderResult(
        "\n".join(lines),
        tuple(sorted(components)),
        tuple(rendered_nets),
        tuple(unrouted_nets),
        warnings,
    )
