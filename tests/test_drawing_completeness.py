"""Drawing completeness gate: projected views and annotations vs. the spec.

The renderer projects the views from the built model and takes its
annotations from the spec. These tests re-build the part, re-project the
views and re-derive the probes, then gate everything against the spec —
the mechanical equivalent of the manual "every spec feature must appear in
the drawing" check (docs/06 lesson 9) that yesterday's drawing failed.
"""

from pathlib import Path

import pytest

from models.brush_organizer import build, load_spec
from tools.render_drawing import (
    build_manifest,
    dimension_plan,
    fill_note,
    fill_targets,
    probe_views,
    project_views,
)

REPO = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def spec():
    return load_spec()


@pytest.fixture(scope="module")
def gate(spec):
    part = build(spec)
    views = project_views(part, spec["dimensions"])
    return views, probe_views(views, spec)


def test_view_outlines_match_spec(gate):
    """Each view spans exactly the spec envelope — no scaling/offset drift."""
    _, probes = gate
    for name, pr in probes["outline"].items():
        assert pr["span_x_ok"], f"{name}: X span does not match the spec"
        assert pr["span_y_ok"], f"{name}: Y span does not match the spec"


def test_every_pocket_visible_in_top_view(gate, spec):
    """Every pocket opening is projected in the top view at the spec
    position and size (the check lesson 9 was about)."""
    _, probes = gate
    for p in spec["features"]["pockets"]:
        pr = probes["pockets"][p["id"]]
        assert pr["top_opening_edges"] >= 1, f"{p['id']}: opening not drawn"
        assert pr["top_opening_position_size_ok"], (
            f"{p['id']}: opening position/size does not match the spec"
        )


def test_every_pocket_has_hidden_profile_in_front_view(gate, spec):
    """Internal features must appear as hidden lines in the front view."""
    _, probes = gate
    for p in spec["features"]["pockets"]:
        n = probes["pockets"][p["id"]]["front_hidden_profile_edges"]
        assert n >= 1, f"{p['id']}: no hidden profile in the front view"


def test_x_fill_ribs_projected_where_spec_requires(gate, spec):
    """Rib edges appear exactly in the pockets the spec's x_fill covers."""
    _, probes = gate
    targets = set(fill_targets(spec))
    for p in spec["features"]["pockets"]:
        pr = probes["x_fill"][p["id"]]
        assert pr["expected"] == (p["id"] in targets), (
            f"{p['id']}: fill_targets disagrees with the spec rule"
        )
        if pr["expected"]:
            assert pr["diag_edges_in_top"] >= 2, (
                f"{p['id']}: X ribs not projected in the top view"
            )


def test_legs_projected_in_front_and_end(gate, spec):
    _, probes = gate
    assert probes["legs"]["front_visible_edges"] >= 2, "legs missing in front"
    assert probes["legs"]["end_visible_edges"] >= 2, "legs missing in end"


def test_dimension_plan_covers_spec_dimensions(spec):
    """Every spec dimension key must be dimensioned somewhere on the sheet."""
    tags = {e["tag"] for e in dimension_plan(spec)}
    missing = set(spec["dimensions"]) - tags
    assert not missing, f"spec dimensions without a drawing dimension: {missing}"


def test_fill_note_present_iff_spec_has_x_fill(spec):
    note = fill_note(spec["features"].get("x_fill"))
    assert ("x_fill" in spec["features"]) == (note is not None)


def test_manifest_shape_and_annotations(spec):
    """Manifest records the plan, pocket labels and probes consistently."""
    part = build(spec)
    views = project_views(part, spec["dimensions"])
    probes = probe_views(views, spec)
    manifest = build_manifest(
        views, probes, spec, REPO / "specs" / "brush_organizer" / "spec.yaml"
    )
    assert manifest["part"] == spec["part"]
    assert manifest["annotations"]["dimensions"] == dimension_plan(spec)
    labels = manifest["annotations"]["pocket_labels"]
    assert [l["id"] for l in labels] == [p["id"] for p in spec["features"]["pockets"]]
    assert manifest["annotations"]["schedule_rows"] == len(labels) + 1
    assert set(manifest["views"]) == {"top", "front", "end"}
    assert manifest["probes"] == probes