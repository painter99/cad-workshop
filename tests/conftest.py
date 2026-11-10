"""Pytest path setup: allow `from models... import ...` imports."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def assert_stl_export_boundary(mesh, expected_xyz, tol=0.2, expected_bodies=1):
    """Export-boundary check: the final STL envelope and connectivity.

    The envelope is compared against the spec-derived dimensions AXIS BY AXIS
    (X, Y, Z order preserved — a transposed export of unequal axes fails) with
    an absolute
    tolerance: triangulated cylinders undershoot the true bound (measured
    worst case 0.037 mm on a Ø120 flange, build123d 0.13.0 default STL
    quality); real export-scale mistakes (mm/inch = 25.4x) fail by orders of
    magnitude. `body_count` catches disconnected closed components that are
    still watertight (verified: it counts an open fragment too, it does not
    silently discard it). Caveat: it counts connected components — two solids
    touching at a single shared vertex may count as one, so this is a
    connectivity regression check, not a proof of robust part connection.
    """
    actual = [float(e) for e in mesh.extents]
    expected = [float(e) for e in expected_xyz]
    assert len(actual) == 3 and len(expected) == 3, (
        f"expected exactly 3 spec-derived dimensions, got mesh {len(actual)} "
        f"/ spec {len(expected)}"
    )
    for axis, (a, e) in enumerate(zip(actual, expected)):
        assert a == pytest.approx(e, abs=tol), (
            f"STL envelope axis {axis}: {actual} does not match the "
            f"spec-derived dimensions {expected} (abs tolerance {tol} mm)"
        )
    assert mesh.body_count == expected_bodies, (
        f"exported STL has {mesh.body_count} disconnected bodies "
        f"(expected {expected_bodies})"
    )
