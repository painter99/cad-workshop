"""Tests for the brush_organizer part: every spec dimension gets an assertion."""

from pathlib import Path

import pytest
import trimesh
from build123d import GeomType, Vector, export_step, export_stl, import_step

from models.brush_organizer import build, load_spec

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
    """All measured values in one registry; the completeness test uses it."""
    dims = spec["dimensions"]
    bb = part.bounding_box()
    cyl = part.faces().filter_by(GeomType.CYLINDER)
    leg_faces = [f for f in cyl if f.radius * 2 == pytest.approx(dims["leg_diameter"], abs=0.01)]
    leg_height = leg_faces[0].bounding_box().size.Z if leg_faces else None
    # use bounding-box centers: Face.center() of a trimmed cylinder is unreliable
    leg_centers = (
        [
            (round((f.bounding_box().min.X + f.bounding_box().max.X) / 2, 2),
             round((f.bounding_box().min.Y + f.bounding_box().max.Y) / 2, 2))
            for f in leg_faces
        ]
        if leg_faces
        else []
    )
    top_z = bb.size.Z
    top_face = [
        f
        for f in part.faces().filter_by(GeomType.PLANE)
        if f.center().Z == pytest.approx(top_z, abs=0.01)
    ][0]
    openings = [w.bounding_box() for w in top_face.inner_wires()]
    return {
        "length": bb.size.X,
        "width": bb.size.Y,
        "total_height": bb.size.Z,
        "leg_height": leg_height,
        "height": bb.size.Z - leg_height,
        "leg_diameter": 2 * leg_faces[0].radius if leg_faces else None,
        "leg_count": len(leg_faces),
        "leg_centers": leg_centers,
        "openings": openings,  # bounding boxes of the 6 pocket openings
        "volume": part.volume,
        "is_valid": bool(part.is_valid),
        "_dims": dims,
    }


def test_bounding_box(measured, spec):
    d = spec["dimensions"]
    assert measured["length"] == pytest.approx(d["length"], abs=0.01)
    assert measured["width"] == pytest.approx(d["width"], abs=0.01)
    # block height + leg height
    assert measured["total_height"] == pytest.approx(
        d["height"] + d["leg_height"], abs=0.01
    )


def test_validity(part):
    assert part.is_valid, "solid is not a valid closed BREP body"


def test_single_body(part):
    """Regression guard: the first M3 attempt passed validity while being
    5 disconnected bodies (legs detached by the open quarters). The part
    must be ONE connected solid."""
    bodies = part.solids()
    assert len(bodies) == 1, f"part has {len(bodies)} disconnected bodies"


def test_legs(measured, spec):
    assert measured["leg_count"] == spec["features"]["legs"]["count"]
    assert measured["leg_diameter"] == pytest.approx(
        spec["dimensions"]["leg_diameter"], abs=0.01
    )
    # corner positions per spec inset (stability: legs almost flush in corners)
    d = spec["dimensions"]
    inset = spec["features"]["legs"]["inset"]
    lx, ly = d["length"] / 2 - inset, d["width"] / 2 - inset
    want = {
        (round(sx * lx, 2), round(sy * ly, 2)) for sx in (-1, 1) for sy in (-1, 1)
    }
    assert set(measured["leg_centers"]) == want, (
        f"leg positions mismatch:\n got={sorted(measured['leg_centers'])}\n"
        f"want={sorted(want)}"
    )


def test_pocket_openings_on_top_face(part, spec):
    """Top face must show exactly six pocket openings."""
    top_z = spec["dimensions"]["height"] + spec["dimensions"]["leg_height"]
    top_face = [
        f for f in part.faces().filter_by(GeomType.PLANE) if f.center().Z == pytest.approx(top_z)
    ]
    assert len(top_face) == 1
    assert len(top_face[0].inner_wires()) == len(spec["features"]["pockets"])


def test_pocket_openings_positions_and_sizes(measured, spec):
    """Each top-face opening: X position + X-size (diameter or slot width),
    slots also Y-size (length). Read from the opening wire bounding boxes."""
    pockets = spec["features"]["pockets"]
    tol = 0.05
    got = set()
    for bb in measured["openings"]:
        cx = (bb.min.X + bb.max.X) / 2
        got.add((round(cx, 2), round(bb.size.X, 2), round(bb.size.Y, 2)))
    want = set()
    for p in pockets:
        if p["shape"] == "circle":
            want.add((p["x_position"], p["diameter"], p["diameter"]))
        else:
            want.add((p["x_position"], p["along_x"], p["along_y"]))
    assert got == want, f"openings mismatch:\n got={sorted(got)}\nwant={sorted(want)}"


def test_even_pocket_spacing_and_end_wall(spec):
    """Six pocket centers use one even pitch, centered on the block;
    outer circle walls keep enough material to the end faces."""
    pockets = spec["features"]["pockets"]
    xs = [p["x_position"] for p in pockets]
    pitches = [b - a for a, b in zip(xs, xs[1:])]
    assert len(pockets) == 6
    assert xs == sorted(xs)
    assert len(set(pitches)) == 1, f"pocket pitch is not uniform: {pitches}"
    assert (xs[0] + xs[-1]) == pytest.approx(0, abs=0.01), "layout is not centered"
    length = spec["dimensions"]["length"]
    end_margins = []
    for p in (pockets[0], pockets[-1]):
        half_span_x = p["diameter"] / 2 if p["shape"] == "circle" else p["along_x"] / 2
        end_margins.append(length / 2 - abs(p["x_position"]) - half_span_x)
    assert min(end_margins) >= 7.5 - 0.01, f"end wall too thin: {end_margins}"


def test_pocket_depths(part, spec):
    """Void at mid-depth of each pocket, wall material right beside it."""
    top_z = spec["dimensions"]["height"] + spec["dimensions"]["leg_height"]
    for p in spec["features"]["pockets"]:
        x, mid_z = p["x_position"], top_z - p["depth"] / 2
        assert not part.is_inside(
            Vector(x, 0, mid_z)
        ), f"{p['id']}: material found inside pocket at mid-depth"
        if p["shape"] == "circle":
            wall_x = x + p["diameter"] / 2 + 2
        else:
            wall_x = x + p["along_x"] / 2 + 2
        assert part.is_inside(
            Vector(wall_x, 0, mid_z)
        ), f"{p['id']}: no wall beside pocket at mid-depth (pocket too shallow?)"


def test_x_webs_reach_block_bottom(part, spec):
    """Pavel's correction: the X ribs sit at the LOWEST point of the block -
    they span the full height from the block bottom to the pocket floor, in
    every pocket (incl. the shallow 35 mm ones); quarter sectors stay open."""
    dims = spec["dimensions"]
    leg_h = dims["leg_height"]
    top_z = dims["height"] + leg_h
    for p in spec["features"]["pockets"]:
        x = p["x_position"]
        floor_z = top_z - p["depth"]
        if p["shape"] == "circle":
            r = p["diameter"] / 2
            t = r / 2              # probe on the +45 rib centerline, mid-radius
            q = r * 0.8            # quarter-sector probe on the pocket X axis
        else:
            t = min(p["along_x"], p["along_y"]) / 2 * 0.7
            q = p["along_x"] / 2 * 0.8
        mid_z = (leg_h + floor_z) / 2
        pid = p["id"]
        assert part.is_inside(Vector(x + t, t, leg_h + 1)), (
            f"{pid}: X rib does not reach the block bottom"
        )
        assert part.is_inside(Vector(x + t, t, floor_z - 0.5)), (
            f"{pid}: X rib does not reach the pocket floor"
        )
        assert not part.is_inside(Vector(x + q, 0, mid_z)), (
            f"{pid}: quarter sector is not open"
        )


def test_stl_export_roundtrip_and_printability(part):
    EXPORTS.mkdir(exist_ok=True)
    stl_path = EXPORTS / "brush_organizer.stl"
    export_stl(part, str(stl_path))
    mesh = trimesh.load(stl_path)
    assert mesh.is_watertight, "exported STL is not watertight -> not printable"
    assert mesh.volume == pytest.approx(part.volume, rel=0.02)


def test_step_export_roundtrip(part):
    EXPORTS.mkdir(exist_ok=True)
    step_path = EXPORTS / "brush_organizer.step"
    export_step(part, str(step_path))
    reimported = import_step(str(step_path))
    assert reimported.volume == pytest.approx(part.volume, rel=0.001)


def test_spec_completeness(measured, spec):
    untested = [k for k in spec["dimensions"] if k not in measured]
    assert not untested, f"spec dimensions without any test: {untested}"
