"""Brush organizer: 250x55x35 block on 6 legs, six pockets with X-webs.

Reads all parameters from specs/brush_organizer/spec.yaml.
Entry point: build(spec) -> Part.

Construction order follows docs/05-modeling-rules.md:
base solid -> pockets cut from the top -> under-floor openings -> X ribs.
"""

from pathlib import Path

import yaml
from build123d import Align, Box, Cylinder, Pos, Rot

SPEC_PATH = (
    Path(__file__).resolve().parents[1] / "specs" / "brush_organizer" / "spec.yaml"
)


def load_spec() -> dict:
    return yaml.safe_load(SPEC_PATH.read_text(encoding="utf-8"))


def _pocket_solid(pocket: dict, height: float, top_z: float):
    """Cutting tool for one pocket, extruded downward from the top face."""
    depth = pocket["depth"]
    if pocket["shape"] == "circle":
        return Pos(pocket["x_position"], 0, top_z - depth / 2) * Cylinder(
            radius=pocket["diameter"] / 2, height=depth
        )
    # rectangular slot: width along X, length along Y
    return Pos(pocket["x_position"], 0, top_z - depth / 2) * Box(
        pocket["width"], pocket["length"], depth
    )


def build(spec: dict):
    """Build the organizer from an approved spec dict. Returns a Part."""
    dims = spec["dimensions"]
    length = dims["length"]
    width = dims["width"]
    height = dims["height"]
    leg_h = dims["leg_height"]
    leg_r = dims["leg_diameter"] / 2
    top_z = leg_h + height  # block spans [leg_h, top_z]

    # Block: base sits on top of the legs (Z = leg_h).
    part = Pos(0, 0, leg_h) * Box(
        length, width, height, align=(Align.CENTER, Align.CENTER, Align.MIN)
    )

    # Legs: 4 near corners + 2 at mid-length, inset from the edges.
    inset = spec["features"]["legs"]["inset"]
    lx = length / 2 - inset
    ly = width / 2 - inset
    leg_positions = [
        (-lx, -ly),
        (-lx, ly),
        (lx, -ly),
        (lx, ly),
        (0, -ly),
        (0, ly),
    ]
    leg = Cylinder(radius=leg_r, height=leg_h, align=(Align.CENTER, Align.CENTER, Align.MIN))
    part += [Pos(x, y, 0) * leg for x, y in leg_positions]

    # Pockets cut from the top face.
    pockets = spec["features"]["pockets"]
    part -= [_pocket_solid(p, height, top_z) for p in pockets]

    # X-webs: under every pocket, open quarters through to the bottom face.
    xf = spec["features"]["x_fill"]
    rib_w = xf["rib_width"]
    web_t = xf["web_thickness"]
    for p in pockets:
        floor_z = top_z - p["depth"]  # top of the web
        if p["shape"] == "circle":
            r = p["diameter"] / 2
            span = 2 * r
            below = Pos(p["x_position"], 0, (leg_h + floor_z) / 2) * Cylinder(
                radius=r, height=floor_z - leg_h
            )
            rib = Box(span, rib_w, web_t)
        else:
            w, l = p["width"], p["length"]
            span = (w**2 + l**2) ** 0.5  # diagonal span of the rectangle
            below = Pos(p["x_position"], 0, (leg_h + floor_z) / 2) * Box(
                w, l, floor_z - leg_h
            )
            rib = Box(span, rib_w, web_t)
        # open the region below the pocket floor, then add the X ribs back
        part -= below
        rib_top = floor_z
        rib_z = rib_top - web_t / 2
        part += [
            Pos(p["x_position"], 0, rib_z) * Rot(0, 0, 45) * rib,
            Pos(p["x_position"], 0, rib_z) * Rot(0, 0, -45) * rib,
        ]

    return part
