"""Tests for the hub_flange part: every spec dimension gets an assertion.

Part kind: round flange (plate + hub + through bore + keyway + bolt circle).
The drawing-completeness section gates the projected views against the spec
(the mechanical equivalent of "every spec feature must appear in the
drawing", docs/06 lesson 9).
"""

import math
from pathlib import Path

import pytest
import trimesh
from build123d import GeomType, Vector, export_step, export_stl, import_step

import models.hub_flange
from models.hub_flange import build, load_spec
from tools.render_drawing import (
    TOL,
    _edges_in,
    _union_bbox,
    build_manifest,
    dimension_plan,
    probe_views,
    project_drawing_views,
)

REPO = Path(__file__).resolve().parents[1]
EXPORTS = REPO / "exports"


@pytest.fixture(scope="module")
def spec():
    return load_spec()


@pytest.fixture(scope="module")
def part(spec):
    return build(spec)


@pytest.fixture(scope="module")
def measured(part, spec):
    """All measured values in one registry; the completeness test uses it.

    Cylinder faces are identified by radius; the bore wall is trimmed by the
    keyway (its radius reads None on a trimmed face — recorded in
    verification.md), so it is identified by its full-height z span.
    Feature positions come from bounding-box centers, never Face.center()
    of a trimmed cylinder (docs/06 lesson).
    """
    dims = spec["dimensions"]
    bb = part.bounding_box()
    cyls = part.faces().filter_by(GeomType.CYLINDER)

    def by_radius(r):
        return [f for f in cyls if f.radius is not None
                and f.radius == pytest.approx(r, abs=0.01)]

    plate = by_radius(dims["flange_diameter"] / 2)[0]
    hub = by_radius(dims["hub_diameter"] / 2)[0]
    hole_faces = by_radius(dims["bolt_hole_diameter"] / 2)
    hole_centers = [
        (round((f.bounding_box().min.X + f.bounding_box().max.X) / 2, 2),
         round((f.bounding_box().min.Y + f.bounding_box().max.Y) / 2, 2))
        for f in hole_faces
    ]
    bore = [
        f for f in cyls if f.radius is None
        and f.bounding_box().size.Z == pytest.approx(dims["height"], abs=0.01)
    ][0]
    bore_bb = bore.bounding_box()
    planes = part.faces().filter_by(GeomType.PLANE)
    key_floor = [
        f for f in planes
        if abs(f.bounding_box().max.Y
               - (dims["bore_diameter"] / 2 + dims["keyway_depth"])) < 0.01
        and f.bounding_box().size.Z == pytest.approx(dims["height"], abs=0.01)
    ][0]
    key_sides = [
        f for f in planes
        if abs(abs((f.bounding_box().min.X + f.bounding_box().max.X) / 2)
               - dims["keyway_width"] / 2) < 0.01
        and f.bounding_box().size.Z == pytest.approx(dims["height"], abs=0.01)
    ]
    key_side_x = [
        (f.bounding_box().min.X + f.bounding_box().max.X) / 2 for f in key_sides
    ]
    hole_r = math.hypot(*hole_centers[0])
    return {
        "length": bb.size.X,
        "width": bb.size.Y,
        "height": bb.size.Z,
        "flange_diameter": 2 * plate.radius,
        "flange_thickness": plate.bounding_box().size.Z,
        "hub_diameter": 2 * hub.radius,
        "hub_length": hub.bounding_box().size.Z,
        "bore_diameter": bore_bb.size.X,
        "keyway_width": abs(key_side_x[0] - key_side_x[1]),
        "keyway_depth": key_floor.bounding_box().max.Y - bore_bb.size.X / 2,
        "pcd_diameter": 2 * hole_r,
        "bolt_hole_diameter": 2 * hole_faces[0].radius,
        "hole_centers": hole_centers,
        "volume": part.volume,
        "is_valid": bool(part.is_valid),
        "_dims": dims,
    }


# ---------------------------------------------------------------- geometry


def test_bounding_box(measured, spec):
    d = spec["dimensions"]
    assert measured["length"] == pytest.approx(d["length"], abs=0.01)
    assert measured["width"] == pytest.approx(d["width"], abs=0.01)
    assert measured["height"] == pytest.approx(d["height"], abs=0.01)


def test_validity(part):
    assert part.is_valid, "solid is not a valid closed BREP body"


def test_single_body(part):
    """Mandatory connectivity test: the part must be ONE connected solid."""
    bodies = part.solids()
    assert len(bodies) == 1, f"part has {len(bodies)} disconnected bodies"


def test_plate(measured, spec):
    d = spec["dimensions"]
    assert measured["flange_diameter"] == pytest.approx(
        d["flange_diameter"], abs=0.01)
    assert measured["flange_thickness"] == pytest.approx(
        d["flange_thickness"], abs=0.01)


def test_hub_on_top(measured, spec):
    """The hub is concentric, sits on +Z above the plate, and the stack adds
    up: flange_thickness + hub_length == height."""
    d = spec["dimensions"]
    assert measured["hub_diameter"] == pytest.approx(d["hub_diameter"], abs=0.01)
    assert measured["hub_length"] == pytest.approx(d["hub_length"], abs=0.01)
    assert measured["flange_thickness"] + measured["hub_length"] == pytest.approx(
        measured["height"], abs=0.01)


def test_bore_through_all(part, spec):
    """The Ø25 bore is void along the whole axis; material right beside it."""
    d = spec["dimensions"]
    for z in (1.0, d["flange_thickness"] + 0.5, d["height"] - 1.0):
        assert not part.is_inside(Vector(0, 0, z)), f"bore not void at z={z}"
    # wall material: in the plate ring and in the hub wall
    assert part.is_inside(Vector(0, 20, 6)), "no plate ring material"
    assert part.is_inside(Vector(0, 20, d["flange_thickness"] + 5)), (
        "no hub wall material")


def test_keyway(part, spec):
    """The keyway slot: void inside, material beside and beyond it."""
    d = spec["dimensions"]
    y_in = d["bore_diameter"] / 2 + d["keyway_depth"] / 2  # 14.15
    for z in (1.0, d["height"] / 2, d["height"] - 1.0):
        assert not part.is_inside(Vector(0, y_in, z)), f"keyway not void at z={z}"
    for x in (-3.0, 3.0):  # inside the 8 mm width
        assert not part.is_inside(Vector(x, y_in, d["height"] / 2)), (
            "keyway narrower than the spec width")
    for x in (-5.0, 5.0):  # outside the 8 mm width
        assert part.is_inside(Vector(x, y_in, d["height"] / 2)), (
            "material missing beside the keyway")
    assert part.is_inside(Vector(0, y_in + 3, d["height"] / 2)), (
        "no material beyond the keyway floor")


def test_bolt_holes(part, measured, spec):
    """Six Ø11 holes through the plate, equally spaced on the Ø90 PCD,
    hole #1 at 12 o'clock (start angle 90°)."""
    d = spec["dimensions"]
    holes = spec["features"]["bolt_holes"]
    assert len(measured["hole_centers"]) == holes["count"]
    r_pcd = holes["pcd_diameter"] / 2
    start = math.radians(holes["start_angle_deg"])
    want = {
        (round(r_pcd * math.cos(start + 2 * math.pi * i / holes["count"]), 2),
         round(r_pcd * math.sin(start + 2 * math.pi * i / holes["count"]), 2))
        for i in range(holes["count"])
    }
    assert set(measured["hole_centers"]) == want, (
        f"bolt hole positions mismatch:\n got={sorted(measured['hole_centers'])}\n"
        f"want={sorted(want)}")
    for x, y in want:
        assert not part.is_inside(Vector(x, y, d["flange_thickness"] / 2)), (
            f"bolt hole at ({x}, {y}) not void")
    # material between holes, on the PCD, at mid-angle
    for i in range(holes["count"]):
        a = start + (2 * math.pi * (i + 0.5) / holes["count"])
        x, y = r_pcd * math.cos(a), r_pcd * math.sin(a)
        assert part.is_inside(Vector(x, y, d["flange_thickness"] / 2)), (
            f"no material between bolt holes at ({x:.2f}, {y:.2f})")


def test_volume_analytic(part, spec):
    """BREP volume vs. the analytic value (plate + hub - holes - keyway).

    The naive keyway term (width x depth) understates the cut by ~0.035 %
    (the cut box's corners reach into the bore circle where the circle dips
    below the keyway mouth) — covered by the rel=0.001 tolerance.
    """
    d = spec["dimensions"]
    holes = spec["features"]["bolt_holes"]
    analytic = (
        math.pi * ((d["flange_diameter"] / 2) ** 2 - (d["bore_diameter"] / 2) ** 2)
        * d["flange_thickness"]
        + math.pi * ((d["hub_diameter"] / 2) ** 2 - (d["bore_diameter"] / 2) ** 2)
        * d["hub_length"]
        - holes["count"] * math.pi * (d["bolt_hole_diameter"] / 2) ** 2
        * d["flange_thickness"]
        - d["keyway_width"] * d["keyway_depth"] * d["height"]
    )
    assert part.volume == pytest.approx(analytic, rel=0.001)


def test_stl_export_roundtrip_and_printability(part):
    EXPORTS.mkdir(exist_ok=True)
    stl_path = EXPORTS / "hub_flange.stl"
    export_stl(part, str(stl_path))
    mesh = trimesh.load(stl_path)
    assert mesh.is_watertight, "exported STL is not watertight -> not printable"
    assert mesh.volume == pytest.approx(part.volume, rel=0.02)


def test_step_export_roundtrip(part):
    EXPORTS.mkdir(exist_ok=True)
    step_path = EXPORTS / "hub_flange.step"
    export_step(part, str(step_path))
    reimported = import_step(str(step_path))
    assert reimported.volume == pytest.approx(part.volume, rel=0.001)


def test_spec_completeness(measured, spec):
    untested = [k for k in spec["dimensions"] if k not in measured]
    assert not untested, f"spec dimensions without any test: {untested}"


# ------------------------------------------------- drawing completeness gate


@pytest.fixture(scope="module")
def gate(part, spec):
    views, report = project_drawing_views(part, spec, models.hub_flange)
    return views, probe_views(views, spec), report


def test_view_outlines_match_spec(gate):
    """Each view spans exactly the spec envelope — no scaling/offset drift."""
    _, probes, _ = gate
    for name, pr in probes["outline"].items():
        assert pr["span_x_ok"], f"{name}: X span does not match the spec"
        assert pr["span_y_ok"], f"{name}: Y span does not match the spec"


def test_every_bolt_hole_visible_in_top_view(gate, spec):
    """Every bolt hole opening is projected in the top view at the spec
    position and size."""
    _, probes, _ = gate
    for key, pr in probes["flange"]["bolt_holes"].items():
        assert pr["top_opening_edges"] >= 1, f"{key}: opening not drawn"
        assert pr["position_size_ok"], (
            f"{key}: opening position/size does not match the spec")


def test_bore_hidden_profile_in_front_view(gate, spec):
    """The through bore must appear as hidden lines in the front view."""
    _, probes, _ = gate
    pr = probes["flange"]["bore"]
    assert pr["front_hidden_profile_edges"] >= 2, "bore profile missing in front"
    assert pr["front_profile_position_ok"], "bore profile at the wrong x"


def test_keyway_in_front_and_end_views(gate, spec):
    """The keyway side walls appear in the front view (full height) and the
    keyway floor appears in the end view at bore_r + depth."""
    _, probes, _ = gate
    pr = probes["flange"]["keyway"]
    assert pr["front_hidden_lines"] >= 2, "keyway walls missing in front"
    assert pr["end_floor_lines"] >= 1, "keyway floor missing in end"
    assert pr["end_floor_position_ok"], "keyway floor at the wrong position"


def test_hub_silhouette_in_front_view(gate, spec):
    """The hub outline (Ø50 x 18) is visible in the front view."""
    _, probes, _ = gate
    assert probes["flange"]["hub"]["front_silhouette_edges"] >= 2, (
        "hub silhouette missing in front")


def test_dimension_plan_covers_spec_dimensions(spec):
    """Every spec dimension key must be dimensioned somewhere on the sheet.

    Round-part rule: the envelope keys `length`/`width` are covered by the
    Ø flange_diameter dimension — the equivalence is asserted here, so the
    rule cannot silently mask a wrong spec.
    """
    tags = {e["tag"] for e in dimension_plan(spec)}
    covered = tags | {"length", "width"}
    missing = set(spec["dimensions"]) - covered
    assert not missing, f"spec dimensions without a drawing dimension: {missing}"
    d = spec["dimensions"]
    assert d["length"] == d["width"] == d["flange_diameter"], (
        "the length/width coverage rule assumes a round part")


def test_manifest_shape_and_annotations(gate, spec):
    """Manifest records the plan and probes consistently (no pocket table for
    a part without pockets)."""
    views, probes, _ = gate
    manifest = build_manifest(
        views, probes, spec, REPO / "specs" / "hub_flange" / "spec.yaml")
    assert manifest["part"] == spec["part"]
    assert manifest["annotations"]["dimensions"] == dimension_plan(spec)
    assert manifest["annotations"]["pocket_labels"] == []
    assert manifest["annotations"]["schedule_rows"] == 0
    assert set(manifest["views"]) == {"top", "front", "end"}
    assert manifest["probes"] == probes