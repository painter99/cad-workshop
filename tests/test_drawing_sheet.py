"""Sheet-level drawing conventions: ISO 3098 font asset, ISO 5457 frame
and dash-phase alignment for closed circular edges.

These gate the *presentation* layer the same way the completeness gate
gates the geometry: the font asset and its license must ship with the
repo, the manifest must declare the conventions, and the dash-phase
helper must be deterministic.
"""

from pathlib import Path

import pytest

from models.brush_organizer import build, load_spec
from tools.render_drawing import (
    FONT_NAME,
    FONT_PATH,
    build_manifest,
    closed_dash_offset,
    probe_views,
    project_views,
    small_circle_solid,
    text_clearance_violations,
)

REPO = Path(__file__).resolve().parents[1]


class FakeEdge:
    """closed_dash_offset only reads edge.length."""

    def __init__(self, length: float):
        self.length = length


@pytest.fixture(scope="module")
def spec():
    return load_spec()


@pytest.fixture(scope="module")
def manifest(spec):
    part = build(spec)
    views = project_views(part, spec["dimensions"])
    probes = probe_views(views, spec)
    return build_manifest(
        views, probes, spec, REPO / "specs" / "brush_organizer" / "spec.yaml"
    )


def test_font_asset_and_license_present():
    """The ISO 3098 font ships with the repo, with its license attached."""
    assert FONT_PATH.exists(), "osifont asset missing from assets/fonts/"
    lic = FONT_PATH.parent / "osifont-LICENSE.txt"
    assert lic.exists(), "osifont license file missing"
    text = lic.read_text(encoding="utf-8")
    assert "GNU General Public License" in text
    assert "font exception" in text.lower()


def test_font_registered_as_osifont():
    assert FONT_NAME == "osifont", "renderer did not register the osifont face"


def test_manifest_declares_font_and_sheet(manifest):
    """The manifest documents the typography and sheet conventions."""
    assert manifest["font"]["name"] == "osifont"
    assert "ISO 3098" in manifest["font"]["standard"]
    assert "font exception" in manifest["font"]["license"]
    assert "A4 landscape" in manifest["sheet"]["size"]
    assert "10 mm" in manifest["sheet"]["frame"]
    assert "centring" in manifest["sheet"]["centring_marks"]


def test_closed_dash_offset_deterministic():
    """Ø35 pocket circle: seam must land at the gap midpoint, exactly."""
    circumference = 109.956  # mm, measured on the real model (π × 35)
    off = closed_dash_offset(FakeEdge(circumference), (0, (12, 3)))
    period = 15.0
    seam = (circumference * 0.5 * 72 / 25.4) % period
    expected = (13.5 - seam) % period
    assert off == pytest.approx(expected, abs=1e-9)
    assert 0 <= off < period


def test_closed_dash_offset_rejects_solid_and_malformed():
    assert closed_dash_offset(FakeEdge(10.0), None) is None
    assert closed_dash_offset(FakeEdge(10.0), (0, ())) is None
    assert closed_dash_offset(FakeEdge(10.0), (0, (12, 3, 1))) is None


def test_closed_dash_offset_shifts_phase_by_half_period_for_half_period_circumference():
    """A circle rendering exactly 7.5 pt (half the 15 pt period, mid-dash)
    gets offset 6.0: seam lands at 13.5 pt = the gap midpoint."""
    length_pts = 7.5 / (0.5 * 72 / 25.4)  # mm that render as 7.5 pt
    off = closed_dash_offset(FakeEdge(length_pts), (0, (12, 3)))
    assert off == pytest.approx(6.0, abs=1e-9)


def test_small_hidden_circles_solid_rule():
    """Ø5 legs (15.708 mm → 22.3 pt < 45 pt) go solid; Ø35 stays dashed."""
    assert small_circle_solid(15.708, (0, (12, 3))) is True
    assert small_circle_solid(109.956, (0, (12, 3))) is False
    assert small_circle_solid(15.708, None) is False


def test_regenerated_manifest_records_text_clearance_pass():
    """The versioned manifest must carry the mechanical layout gate result."""
    import json
    m = json.loads((REPO / "specs" / "brush_organizer" / "visuals"
                    / "drawing.manifest.json").read_text(encoding="utf-8"))
    assert m["sheet"]["text_clearance_ok"] is True, (
        "text/frame clearance probe failed — layout must be fixed, not asserted")