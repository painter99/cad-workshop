"""Tests for the test_block part: every spec dimension gets an assertion."""

import math
from pathlib import Path

import pytest
import trimesh
import yaml
from build123d import GeomType, import_step

from models.test_block import build, load_spec

REPO = Path(__file__).resolve().parents[1]
EXPORTS = REPO / "exports"
TOL = None  # set from spec in fixture


@pytest.fixture(scope="module")
def spec():
    return load_spec()


@pytest.fixture(scope="module")
def part(spec):
    return build(spec)


@pytest.fixture(scope="module")
def measured(part, spec):
    """All measured values in one registry; the completeness test uses it."""
    tol = spec["tolerance"]
    dims = spec["dimensions"]
    bb = part.bounding_box()
    cyl_faces = part.faces().filter_by(GeomType.CYLINDER)
    hole_centers_x = sorted(
        f.center().X for f in cyl_faces
    )
    return {
        "length": bb.size.X,
        "width": bb.size.Y,
        "thickness": bb.size.Z,
        "hole_diameter": sum(f.radius for f in cyl_faces) / len(cyl_faces) * 2,
        "hole_spacing": hole_centers_x[-1] - hole_centers_x[0],
        "through_holes": len(cyl_faces),
        "volume": part.volume,
        "is_valid": bool(part.is_valid),
        "_tol": tol,
        "_dims": dims,
    }


def test_bounding_box_dimensions(measured, spec):
    tol = spec["tolerance"]
    d = spec["dimensions"]
    assert measured["length"] == pytest.approx(d["length"], abs=tol)
    assert measured["width"] == pytest.approx(d["width"], abs=tol)
    assert measured["thickness"] == pytest.approx(d["thickness"], abs=tol)


def test_validity(part):
    assert part.is_valid, "solid is not a valid closed BREP body"


def test_volume_matches_analytic(measured, spec):
    d = spec["dimensions"]
    expected = (
        d["length"] * d["width"] * d["thickness"]
        - spec["features"]["through_holes"]
        * math.pi
        * (d["hole_diameter"] / 2) ** 2
        * d["thickness"]
    )
    assert measured["volume"] == pytest.approx(expected, rel=0.001)


def test_hole_count_and_diameter(measured, spec):
    assert measured["through_holes"] == spec["features"]["through_holes"]
    assert measured["hole_diameter"] == pytest.approx(
        spec["dimensions"]["hole_diameter"], abs=spec["tolerance"]
    )


def test_hole_spacing(measured, spec):
    assert measured["hole_spacing"] == pytest.approx(
        spec["dimensions"]["hole_spacing"], abs=spec["tolerance"]
    )


def test_stl_export_roundtrip_and_printability(part, spec):
    """Export STL, re-import, verify watertight + volume (printability proxy)."""
    EXPORTS.mkdir(exist_ok=True)
    stl_path = EXPORTS / "test_block.stl"
    from build123d import export_stl

    export_stl(part, str(stl_path))
    mesh = trimesh.load(stl_path)
    assert mesh.is_watertight, "exported STL is not watertight -> not printable"
    assert mesh.volume == pytest.approx(part.volume, rel=0.02)


def test_step_export_roundtrip(part, spec):
    """Export STEP, re-import, verify volume survives the round-trip."""
    EXPORTS.mkdir(exist_ok=True)
    step_path = EXPORTS / "test_block.step"
    from build123d import export_step

    export_step(part, str(step_path))
    reimported = import_step(str(step_path))
    assert reimported.volume == pytest.approx(part.volume, rel=0.001)


def test_spec_completeness(measured, spec):
    """Every dimension in the spec must have a measured counterpart."""
    untested = [k for k in spec["dimensions"] if k not in measured]
    assert not untested, f"spec dimensions without any test: {untested}"
