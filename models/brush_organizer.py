"""Brush organizer: 250x55x35 block on 6 legs, six pockets with X-fill.

Reads all parameters from specs/brush_organizer/spec.yaml.
Entry point: build(spec) -> Part.

X-fill styles (spec: features.x_fill.style):
- "web_floor": the pocket floor IS an X-shaped web (two diagonal ribs);
  the quarter sectors stay open below it, through to the bottom face.
  Only applied to pockets whose remaining floor is thin (see "under").
- "cradle": the pocket has a solid floor at its depth; an X-shaped ridge
  rises from the floor inside the pocket (a semi-open saddle).

x_fill.under: "all" or "deep_only" (deep = remaining floor <= 5 mm).
"""

from pathlib import Path

import yaml
from build123d import Align, Box, Cylinder, Pos, Rot

SPEC_PATH = (
    Path(__file__).resolve().parents[1] / "specs" / "brush_organizer" / "spec.yaml"
)


def load_spec() -> dict:
    return yaml.safe_load(SPEC_PATH.read_text(encoding="utf-8"))


def _pocket_solid(pocket: dict, top_z: float, width_dim: float = None):
    """Cutting tool for one pocket, extruded downward from the top face."""
    depth = pocket["depth"]
    if pocket["shape"] == "circle":
        return Pos(pocket["x_position"], 0, top_z - depth / 2) * Cylinder(
            radius=pocket["diameter"] / 2, height=depth
        )
    if pocket["shape"] == "slot_channel":
        # open channel across the full width (Y), width along X
        y_len = width_dim + 4  # overshoot for a clean cut through both faces
        return Pos(pocket["x_position"], 0, top_z - depth / 2) * Box(
            pocket["width"], y_len, depth
        )
    # rectangular slot: width along X, length along Y
    return Pos(pocket["x_position"], 0, top_z - depth / 2) * Box(
        pocket["width"], pocket["length"], depth
    )


def _pocket_span(pocket: dict) -> float:
    """Rib length needed to span the pocket."""
    if pocket["shape"] == "circle":
        return pocket["diameter"]
    return (pocket["width"] ** 2 + pocket["length"] ** 2) ** 0.5


def _x_ribs(pocket: dict, rib_w: float, rib_t: float, z_center: float):
    """Two diagonal ribs crossing in an X, centered on the pocket axis."""
    rib = Box(_pocket_span(pocket), rib_w, rib_t)
    return [
        Pos(pocket["x_position"], 0, z_center) * Rot(0, 0, 45) * rib,
        Pos(pocket["x_position"], 0, z_center) * Rot(0, 0, -45) * rib,
    ]


def build(spec: dict):
    """Build the organizer from an approved spec dict. Returns a Part."""
    dims = spec["dimensions"]
    length = dims["length"]
    width = dims["width"]
    height = dims["height"]
    leg_h = dims["leg_height"]
    leg_r = dims["leg_diameter"] / 2
    top_z = leg_h + height  # block spans [leg_h, top_z]

    pockets = spec["features"]["pockets"]
    xf = spec["features"]["x_fill"]
    style = xf.get("style", "web_floor")
    under = xf.get("under", "all")
    rib_w = xf["rib_width"]
    web_t = xf["web_thickness"]

    # Block: base sits on top of the legs (Z = leg_h).
    part = Pos(0, 0, leg_h) * Box(
        length, width, height, align=(Align.CENTER, Align.CENTER, Align.MIN)
    )

    # Legs: 4 near corners + 2 under the end pockets (the small circles at
    # the end pockets in the sketch are the legs seen from above).
    inset = spec["features"]["legs"]["inset"]
    lx = length / 2 - inset
    ly = width / 2 - inset
    end_x = pockets[0]["x_position"]
    leg_positions = [
        (-lx, -ly),
        (-lx, ly),
        (lx, -ly),
        (lx, ly),
        (-end_x, 0),
        (end_x, 0),
    ]
    leg = Cylinder(
        radius=leg_r, height=leg_h, align=(Align.CENTER, Align.CENTER, Align.MIN)
    )
    part += [Pos(x, y, 0) * leg for x, y in leg_positions]

    # Pockets cut from the top face.
    part -= [_pocket_solid(p, top_z, width) for p in pockets]

    # X-fill per pocket.
    for p in pockets:
        if p["shape"] == "slot_channel":
            continue  # channels keep a solid floor; X-fill applies to holes
        floor_z = top_z - p["depth"]
        remaining = floor_z - leg_h  # material between pocket floor and block bottom
        is_deep = remaining <= 5
        applies = under == "all" or (under == "deep_only" and is_deep)
        if not applies:
            continue
        if style == "web_floor":
            # open the region below the pocket floor, then close it with the X web
            if p["shape"] == "circle":
                below = Pos(
                    p["x_position"], 0, (leg_h + floor_z) / 2
                ) * Cylinder(radius=p["diameter"] / 2, height=remaining)
            else:
                below = Pos(
                    p["x_position"], 0, (leg_h + floor_z) / 2
                ) * Box(p["width"], p["length"], remaining)
            part -= below
            part += _x_ribs(p, rib_w, web_t, floor_z - web_t / 2)
        else:  # cradle: solid floor, X ridge rising inside the pocket
            part += _x_ribs(p, rib_w, web_t, floor_z + web_t / 2)

    return part
