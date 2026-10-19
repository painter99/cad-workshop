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


def test_x_web_under_deep_pocket(part, spec):
    """Under a deep pocket: open below the web, ribs on the diagonals, open quarters."""
    p4 = next(p for p in spec["features"]["pockets"] if p["id"] == "P4")
    x = p4["x_position"]
    floor_z = (
        spec["dimensions"]["height"] + spec["dimensions"]["leg_height"] - p4["depth"]
    )
    web_mid = floor_z - spec["features"]["x_fill"]["web_thickness"] / 2
    below_web = floor_z - spec["features"]["x_fill"]["web_thickness"] - 1
    r = p4["diameter"] / 2
    d = r / (2 ** 0.5)  # point on the diagonal rib
    assert not part.is_inside(Vector(x, 0, below_web)), "region below web is not open"
    assert part.is_inside(Vector(x + d, d, web_mid)), "X rib missing on +45 diagonal"
    assert part.is_inside(Vector(x - d, -d, web_mid)), "X rib missing on -45 diagonal"
    assert not part.is_inside(Vector(x, r * 0.8, web_mid)), "quarter sector is not open"


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
