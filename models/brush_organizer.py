"""Brush organizer: 250x55x35 block on 4 corner legs, six pockets with X-fill.

Reads all parameters from specs/brush_organizer/spec.yaml.
Entry point: build(spec) -> Part.

X-fill styles (spec: features.x_fill.style):
- "web_floor": the pocket floor IS an X of two diagonal ribs spanning the
  FULL height from the block bottom face to the pocket floor (the crosses
  sit at the lowest point of the block); the quarter sectors stay open
  through to the bottom face. Each rib end extends rib_embed mm into the
  wall for a solid union. Applied per x_fill.under ("all" / "deep_only").
- "cradle": the pocket has a solid floor at its depth; an X-shaped ridge
  rises from the floor inside the pocket (a semi-open saddle).
"""

from pathlib import Path

import yaml
from build123d import Align, Box, Cylinder, Pos, Rot

SPEC_PATH = (
    Path(__file__).resolve().parents[1] / "specs" / "brush_organizer" / "spec.yaml"
)


def load_spec() -> dict:
    return yaml.safe_load(SPEC_PATH.read_text(encoding="utf-8"))


def _pocket_solid(pocket: dict, top_z: float):
    """Cutting tool for one pocket, extruded downward from the top face."""
    depth = pocket["depth"]
    if pocket["shape"] == "circle":
        return Pos(pocket["x_position"], 0, top_z - depth / 2) * Cylinder(
            radius=pocket["diameter"] / 2, height=depth
        )
    # rectangular slot: along_x along the block (X), along_y across it (Y)
    return Pos(pocket["x_position"], 0, top_z - depth / 2) * Box(
        pocket["along_x"], pocket["along_y"], depth
    )


def _pocket_span(pocket: dict) -> float:
    """Rib length needed to span the pocket."""
    if pocket["shape"] == "circle":
        return pocket["diameter"]
    return (pocket["along_x"] ** 2 + pocket["along_y"] ** 2) ** 0.5


def _x_ribs(pocket: dict, rib_w: float, rib_t: float, z_center: float,
            rib_len: float = None):
    """Two diagonal ribs crossing in an X, centered on the pocket axis."""
    length = rib_len if rib_len is not None else _pocket_span(pocket)
    rib = Box(length, rib_w, rib_t)
    return [
        Pos(pocket["x_position"], 0, z_center) * Rot(0, 0, 45) * rib,
        Pos(pocket["x_position"], 0, z_center) * Rot(0, 0, -45) * rib,
    ]


def _leg_positions(spec: dict, pockets: list) -> list:
    """Leg centers: 4 near the corners. The historical 6-leg layout added
    two mid-length legs under the end pockets; kept only for spec count == 6."""
    dims = spec["dimensions"]
    inset = spec["features"]["legs"]["inset"]
    lx = dims["length"] / 2 - inset
    ly = dims["width"] / 2 - inset
    positions = [(-lx, -ly), (-lx, ly), (lx, -ly), (lx, ly)]
    if spec["features"]["legs"]["count"] == 6:
        end_x = pockets[0]["x_position"]
        positions += [(-end_x, 0), (end_x, 0)]
    return positions


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
    rib_embed = xf.get("rib_embed", 2)

    # Block: base sits on top of the legs (Z = leg_h).
    part = Pos(0, 0, leg_h) * Box(
        length, width, height, align=(Align.CENTER, Align.CENTER, Align.MIN)
    )

    # Legs: per spec count (4 = corners only).
    leg = Cylinder(
        radius=leg_r, height=leg_h, align=(Align.CENTER, Align.CENTER, Align.MIN)
    )
    part += [Pos(x, y, 0) * leg for x, y in _leg_positions(spec, pockets)]

    # Pockets cut from the top face.
    part -= [_pocket_solid(p, top_z) for p in pockets]

    # X-fill per pocket.
    for p in pockets:
        floor_z = top_z - p["depth"]
        remaining = floor_z - leg_h  # material between pocket floor and block bottom
        is_deep = remaining <= 5
        applies = under == "all" or (under == "deep_only" and is_deep)
        if not applies:
            continue
        if style == "web_floor":
            # open the region below the pocket floor, then fill it with X ribs
            # spanning the FULL height (block bottom -> pocket floor), so the
            # crosses sit at the lowest point of the block (Pavel's correction)
            if p["shape"] == "circle":
                below = Pos(
                    p["x_position"], 0, (leg_h + floor_z) / 2
                ) * Cylinder(radius=p["diameter"] / 2, height=remaining)
            else:
                below = Pos(
                    p["x_position"], 0, (leg_h + floor_z) / 2
                ) * Box(p["along_x"], p["along_y"], remaining)
            part -= below
            part += _x_ribs(
                p, rib_w, remaining, (leg_h + floor_z) / 2,
                rib_len=_pocket_span(p) + 2 * rib_embed,
            )
        else:  # cradle: solid floor, X ridge rising inside the pocket
            part += _x_ribs(p, rib_w, web_t, floor_z + web_t / 2)

    return part
