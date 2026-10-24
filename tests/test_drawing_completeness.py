"""Drawing completeness gate: projected views and annotations vs. the spec.

The renderer projects the views from the built model and takes its
annotations from the spec. These tests re-build the part, re-project the
views and re-derive the probes, then gate everything against the spec —
the mechanical equivalent of the manual "every spec feature must appear in
the drawing" check (docs/06 lesson 9) that yesterday's drawing failed.
"""

import math
from pathlib import Path

import pytest
from build123d import GeomType

import models.brush_organizer
from models.brush_organizer import build, load_spec
from tools.render_drawing import (
    _analytic_2d,
    _drop_candidate,
    _inside_cavity_view,
    _matches_suppressed,
    build_manifest,
    classify_rib_edges,
    dimension_plan,
    fill_note,
    fill_targets,
    pocket_half_xy,
    probe_views,
    project_drawing_views,
)

REPO = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def spec():
    return load_spec()


@pytest.fixture(scope="module")
def gate(spec):
    part = build(spec)
    views, report = project_drawing_views(part, spec, models.brush_organizer)
    return views, probe_views(views, spec), report


@pytest.fixture(scope="module")
def rib_split(spec):
    part = build(spec)
    keep, supp, others, _stats = classify_rib_edges(part, spec, models.brush_organizer)
    return supp, [e for e, _ in keep] + others


def test_view_outlines_match_spec(gate):
    """Each view spans exactly the spec envelope — no scaling/offset drift."""
    _, probes, _ = gate
    for name, pr in probes["outline"].items():
        assert pr["span_x_ok"], f"{name}: X span does not match the spec"
        assert pr["span_y_ok"], f"{name}: Y span does not match the spec"


def test_every_pocket_visible_in_top_view(gate, spec):
    """Every pocket opening is projected in the top view at the spec
    position and size (the check lesson 9 was about)."""
    _, probes, _ = gate
    for p in spec["features"]["pockets"]:
        pr = probes["pockets"][p["id"]]
        assert pr["top_opening_edges"] >= 1, f"{p['id']}: opening not drawn"
        assert pr["top_opening_position_size_ok"], (
            f"{p['id']}: opening position/size does not match the spec"
        )


def test_every_pocket_has_hidden_profile_in_front_view(gate, spec):
    """Internal features must appear as hidden lines in the front view."""
    _, probes, _ = gate
    for p in spec["features"]["pockets"]:
        n = probes["pockets"][p["id"]]["front_hidden_profile_edges"]
        assert n >= 1, f"{p['id']}: no hidden profile in the front view"


def test_x_fill_ribs_projected_where_spec_requires(gate, spec):
    """Rib edges appear exactly in the pockets the spec's x_fill covers."""
    _, probes, _ = gate
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
    _, probes, _ = gate
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


def test_manifest_shape_and_annotations(gate, spec):
    """Manifest records the plan, pocket labels and probes consistently."""
    views, probes, _ = gate
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


# ---------- false rib-edge suppression (owner findings 2026-10-23/24) ----------


def test_false_rib_edges_fully_suppressed(gate, rib_split, spec):
    """Every surviving projected edge that still matches a suppressed false
    web edge must be 2D-covered by a real edge as well (coincident under
    projection) — the drawing contains no false-edge-only geometry. The
    per-view drop rule is mirrored exactly: a suppressed edge is a drop
    candidate only strictly inside its pocket's outline (or wholly in the
    walls); on the outline it is a silhouette survivor and joins the shield."""
    views, _, _ = gate
    supp3d, real3d = rib_split
    pockets = {p["id"]: p for p in spec["features"]["pockets"]}
    leg_h = spec["dimensions"]["leg_height"]
    top_z = leg_h + spec["dimensions"]["height"]
    for view, (vis, hid) in views.items():
        supp_polys, survivor_polys = [], []
        for e, pid in supp3d:
            polys = _analytic_2d(e, view)
            if _drop_candidate(e, polys, view, pockets[pid], leg_h, top_z):
                supp_polys += polys
            else:
                survivor_polys += polys
        real_polys = [poly for e in real3d for poly in _analytic_2d(e, view)]
        real_polys += survivor_polys
        for lst in (vis, hid):
            for e in lst:
                if _matches_suppressed(e, supp_polys):
                    assert _matches_suppressed(e, real_polys), (
                        f"{view}: projected edge matches only a false rib edge")


def test_floor_lines_survive_in_front_and_end(gate, spec):
    """Over-suppression guard: every X-fill pocket keeps its floor line.

    The floor line is drawn by the webs' void-facing top chords; they end at
    the wall crossings, so the drawn span is somewhat shorter than the
    pocket width (the wall arcs behind the outline are suppressed)."""
    views, _, _ = gate
    leg_h = spec["dimensions"]["leg_height"]
    top_z = leg_h + spec["dimensions"]["height"]
    for p in spec["features"]["pockets"]:
        floor_z = top_z - p["depth"]
        hx, hy = pocket_half_xy(p)
        for view, half in (("front", hx), ("end", hy)):
            pieces = []
            for e in views[view][1]:
                b = e.bounding_box()
                if abs(b.min.Y - floor_z) > 0.05 or abs(b.max.Y - floor_z) > 0.05:
                    continue
                pieces.append((b.min.X, b.max.X))
            pieces.sort()
            cov_lo, cov_hi = math.inf, -math.inf
            for lo, hi in pieces:
                cov_lo, cov_hi = min(cov_lo, lo), max(cov_hi, hi)
            assert cov_hi - cov_lo >= 1.1 * half, (
                f"{p['id']}: floor line incomplete in the {view} view "
                f"(span {cov_hi - cov_lo:.2f}, want >= {1.1 * half:.2f})")


def test_pocket_silhouettes_span_full_depth(gate, spec):
    """The pocket outline must span the full void: from the block bottom
    (leg_h) to the top face — every pocket is a through-void with an X-web
    floor, so its silhouette may not stop at the floor line (owner finding
    2026-10-24: the slot silhouettes must be drawn down to the block
    bottom)."""
    views, _, _ = gate
    leg_h = spec["dimensions"]["leg_height"]
    top_z = leg_h + spec["dimensions"]["height"]
    for p in spec["features"]["pockets"]:
        hx, hy = pocket_half_xy(p)
        for view in ("front", "end"):
            segs = []
            for e in views[view][1]:
                b = e.bounding_box()
                if b.max.X - b.min.X > 0.05:
                    continue
                if view == "front":
                    if not any(abs(b.min.X - (p["x_position"] + s * hx)) < 0.05
                               for s in (-1, 1)):
                        continue
                elif abs(abs(b.min.X) - hy) > 0.05:
                    continue
                segs.append((b.min.Y, b.max.Y))
            segs.sort()
            cov = leg_h
            for lo, hi in segs:
                if lo > cov + 0.05:
                    break
                cov = max(cov, hi)
            assert cov >= top_z - 0.05, (
                f"{p['id']}: silhouette incomplete in the {view} view "
                f"(covers up to {cov:.2f} of {top_z:.2f})")