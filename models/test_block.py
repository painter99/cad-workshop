"""Test block: verification plate with two through holes.

Reads all parameters from specs/test_block/spec.yaml. No magic numbers.
Entry point for tests and preview rendering: build(spec) -> Part.
"""

from pathlib import Path

import yaml
from build123d import Align, Box, Cylinder, Pos

SPEC_PATH = Path(__file__).resolve().parents[1] / "specs" / "test_block" / "spec.yaml"


def load_spec() -> dict:
    return yaml.safe_load(SPEC_PATH.read_text(encoding="utf-8"))


def build(spec: dict):
    """Build the part from an approved spec dict. Returns a build123d Part."""
    dims = spec["dimensions"]
    length = dims["length"]
    width = dims["width"]
    thickness = dims["thickness"]
    hole_d = dims["hole_diameter"]
    hole_spacing = dims["hole_spacing"]
    n_holes = spec["features"]["through_holes"]

    # Plate: centered in X/Y, base on Z=0 (Align.MIN) so the bbox is predictable.
    plate = Box(length, width, thickness, align=(Align.CENTER, Align.CENTER, Align.MIN))

    # Through holes: centered on the plate mid-thickness, spaced along X.
    hole = Cylinder(radius=hole_d / 2, height=thickness * 3)
    offsets = [
        (-hole_spacing / 2 + i * hole_spacing / (n_holes - 1), 0, thickness / 2)
        for i in range(n_holes)
    ]
    holes = [Pos(x, y, z) * hole for x, y, z in offsets]

    return plate - holes
