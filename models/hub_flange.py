"""Hub flange, 6-bolt: Ø120x12 plate, Ø50x18 hub, Ø25 through bore, 8 mm keyway.

Reads all parameters from specs/hub_flange/spec.yaml.
Entry point: build(spec) -> Part.

Layout (owner-approved 2026-10-28): the plate spans Z 0..flange_thickness,
the hub sits on +Z (top) spanning flange_thickness..height. The bore and the
keyway go through the whole part; bolt holes go through the plate only.
"""

import math
from pathlib import Path

import yaml
from build123d import Align, Box, Cylinder, Pos, Rot

SPEC_PATH = (
    Path(__file__).resolve().parents[1] / "specs" / "hub_flange" / "spec.yaml"
)


def load_spec() -> dict:
    return yaml.safe_load(SPEC_PATH.read_text(encoding="utf-8"))


def _bolt_hole_positions(spec: dict) -> list[tuple[float, float]]:
    """Bolt hole centers: `count` holes equally spaced on the PCD.

    Hole #1 sits at start_angle_deg (90 = +Y, 12 o'clock) per the source
    drawing, then every 360/count degrees.
    """
    holes = spec["features"]["bolt_holes"]
    r = holes["pcd_diameter"] / 2
    n = holes["count"]
    start = math.radians(holes.get("start_angle_deg", 90))
    return [
        (r * math.cos(start + 2 * math.pi * i / n),
         r * math.sin(start + 2 * math.pi * i / n))
        for i in range(n)
    ]


def build(spec: dict):
    """Build the hub flange from an approved spec dict. Returns a Part."""
    dims = spec["dimensions"]
    feats = spec["features"]
    flange_r = dims["flange_diameter"] / 2
    flange_t = dims["flange_thickness"]
    hub_r = dims["hub_diameter"] / 2
    bore_r = dims["bore_diameter"] / 2
    total = dims["height"]
    hole_r = dims["bolt_hole_diameter"] / 2

    # Plate: Z 0..flange_t; hub on +Z: flange_t..total (2D profiles -> 3D
    # cylinders, booleans last; no fillets/chamfers per the approved spec).
    part = Cylinder(
        radius=flange_r, height=flange_t,
        align=(Align.CENTER, Align.CENTER, Align.MIN),
    )
    part += Pos(0, 0, flange_t) * Cylinder(
        radius=hub_r, height=total - flange_t,
        align=(Align.CENTER, Align.CENTER, Align.MIN),
    )

    # Bore through-all (plate + hub).
    part -= Cylinder(
        radius=bore_r, height=total,
        align=(Align.CENTER, Align.CENTER, Align.MIN),
    )

    # Keyway: rectangular slot cut radially into the bore wall, through-all.
    # The cut box reaches 2 mm into the bore void for a clean boolean.
    key = feats["bore"]["keyway"]
    cut_depth = key["depth"] + 2
    slot = Pos(0, bore_r + key["depth"], 0) * Box(
        key["width"], cut_depth, total,
        align=(Align.CENTER, Align.MAX, Align.MIN),
    )
    angle = key.get("angle_deg", 90)
    if angle != 90:
        slot = Rot(0, 0, angle - 90) * slot
    part -= slot

    # Bolt holes through the plate (one vectorized boolean).
    part -= [
        Pos(x, y, 0) * Cylinder(
            radius=hole_r, height=flange_t,
            align=(Align.CENTER, Align.CENTER, Align.MIN),
        )
        for x, y in _bolt_hole_positions(spec)
    ]

    return part