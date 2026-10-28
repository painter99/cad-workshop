#!/usr/bin/env python3
"""Generate a dimensioned technical drawing for a part.

Views are TRUE projections of the built model (build123d
``project_to_viewport``, OCCT hidden-line removal): visible edges solid,
hidden edges dashed narrow (ISO 128-24). The model is built from the approved spec, so a feature
cannot go missing from the drawing — the views are not drawn by hand.
Dimensions, pocket labels, the schedule and the title block are generated
from the spec (the intent).

Principle (docs/01): *view geometry from the model, annotations from the
spec.* When a view disagrees with a spec dimension, either the model or the
spec is wrong — the completeness probes make that visible mechanically
(``tests/test_drawing_completeness.py``).

The renderer also writes a manifest (``<out_prefix>.manifest.json``) with
per-view edge counts, objective geometry probes and the annotation plan.

Usage:
    python tools/render_drawing.py specs/<part>/spec.yaml [out_prefix]

Output: <out_prefix>.png, <out_prefix>.svg, <out_prefix>.manifest.json
(default out_prefix: specs/<part>/visuals/drawing).

The model builder is resolved by convention: ``models/<part>.build(spec)``.
The annotation plan dispatches on the part kind: pockets + legs (organizer
kind) or ``features.flange_plate`` (round flange kind: bolt circle, through
bore, keyway — probes and draw functions mirror ``models/hub_flange.py``).
"""
from __future__ import annotations

import importlib
import json
import math
import sys
from datetime import date
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
import yaml
from build123d import GeomType
from matplotlib.patches import Circle, Polygon, Rectangle

TOL = 0.05  # mm — probe tolerance

# ISO 128-24 line groups (two widths, 1:2): wide ≈ 0.7 mm, narrow ≈ 0.35 mm
# on paper (2.0 / 1.0 pt). Dash lengths per ISO 128-20 table 3, in units of
# the line width d: hidden = dashed 12d/3d (type 02.1), centre lines =
# long-dash dot 24d/3d (type 04.1). Dotted lines are NOT used for hidden
# edges (that was the pre-ISO style, corrected 2026-10-23).
SOLID = dict(color="black", lw=2.0)          # 01.2 continuous wide
HIDDEN = dict(color="black", lw=1.0,
              linestyle=(0, (12, 3)))        # 02.1 dashed narrow
CENTERLINE = dict(color="black", lw=1.0,
                  linestyle=(0, (24, 3, 1, 3)))  # 04.1 long-dashed dotted narrow
DIMLINE = dict(color="#1a1a1a", lw=1.0)      # 01.1 continuous narrow

SCALE = 0.5  # 1:2 — ISO 5455 preferred reduction scale, declared in the title block

# ISO 3098 lettering: osifont (GPL-3.0 with font exception — see
# assets/fonts/osifont-LICENSE.txt). Falls back to the matplotlib default if
# the asset is missing; the test suite asserts the asset is present.
FONT_PATH = Path(__file__).resolve().parents[1] / "assets" / "fonts" / "osifont.ttf"
FONT_NAME = "osifont"
if FONT_PATH.exists():
    font_manager.fontManager.addfont(str(FONT_PATH))
    FONT_NAME = font_manager.FontProperties(fname=str(FONT_PATH)).get_name()
matplotlib.rcParams["font.family"] = FONT_NAME
matplotlib.rcParams["axes.unicode_minus"] = False  # osifont lacks U+2212; ASCII hyphen (tick labels are hidden anyway, but tight-bbox extents still resolve them)


def apply_scale(fig, ax, rect, scale: float = SCALE) -> None:
    """Set view limits so geometry renders at exactly `scale` (paper/data).

    ISO 5455: the scale is a preferred ratio, shared by all views and
    declared in the title block. Axes paper size (mm) / scale = data range,
    centred on the midpoints of the content-based limits the draw functions
    set first.
    """
    w_mm = fig.get_figwidth() * 25.4 * rect[2]
    h_mm = fig.get_figheight() * 25.4 * rect[3]
    x0, x1 = ax.get_xlim()
    y0, y1 = ax.get_ylim()
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    ax.set_xlim(cx - w_mm / (2 * scale), cx + w_mm / (2 * scale))
    ax.set_ylim(cy - h_mm / (2 * scale), cy + h_mm / (2 * scale))


def draw_projection_symbol(ax, x0: float, y0: float, s: float) -> None:
    """Third-angle projection symbol (ISO 128-30 B.3, proportions per
    ISO 5456-2 fig. A.2): frustum side view (large end left, small end right)
    + concentric circles = the view from the small end, placed on the right.
    Narrow continuous lines; centre lines omitted (ISO 5456-2 A.2 allows it).
    s = large-end height in axis units."""
    ax.add_patch(Polygon(
        [(x0, y0 + s / 2), (x0 + s, y0 + s / 4), (x0 + s, y0 - s / 4),
         (x0, y0 - s / 2)], fill=False, lw=1.0, edgecolor="black"))
    ax.add_patch(Circle((x0 + 1.75 * s, y0), s / 4, fill=False, lw=1.0,
                        edgecolor="black"))
    ax.add_patch(Circle((x0 + 1.75 * s, y0), s / 2, fill=False, lw=1.0,
                        edgecolor="black"))


# ---------------------------------------------------------------- helpers


def dim_h(ax, x0, x1, y, text, offset=6, ext0=None, ext1=None, color="#1a1a1a"):
    """Horizontal dimension line (ISO 129): arrows, label above the line and
    thin extension lines from the features (ext0/ext1 = feature y) with a
    2 mm gap at the feature and a 4 mm overhang past the dimension line."""
    ax.annotate(
        "", xy=(x0, y), xytext=(x1, y),
        arrowprops=dict(arrowstyle="<|-|>", color=color, shrinkA=0, shrinkB=0,
                        mutation_scale=12, lw=1.0),
    )
    for xf, ef in ((x0, ext0), (x1, ext1)):
        if ef is None:
            continue
        d = 1 if y > ef else -1
        ax.plot([xf, xf], [ef + d * 2, y + d * 4], **DIMLINE)
    ax.text((x0 + x1) / 2, y + offset, text, ha="center", va="bottom",
            fontsize=10, color=color)


def dim_v(ax, x, y0, y1, text, offset=6, ext0=None, ext1=None, color="#1a1a1a"):
    """Vertical dimension line (ISO 129): arrows, label beside the line and
    thin extension lines from the features (ext0/ext1 = feature x)."""
    ax.annotate(
        "", xy=(x, y0), xytext=(x, y1),
        arrowprops=dict(arrowstyle="<|-|>", color=color, shrinkA=0, shrinkB=0,
                        mutation_scale=12, lw=1.0),
    )
    for yf, ef in ((y0, ext0), (y1, ext1)):
        if ef is None:
            continue
        d = 1 if x > ef else -1
        ax.plot([ef + d * 2, x + d * 4], [yf, yf], **DIMLINE)
    ax.text(x + offset, (y0 + y1) / 2, text, ha="left", va="center",
            fontsize=10, rotation=90, color=color)


def leader(ax, xy, xytext, text, color="#1a1a1a"):
    ax.annotate(
        text, xy=xy, xytext=xytext, fontsize=9, color=color,
        arrowprops=dict(arrowstyle="->", color=color, lw=1.0),
        ha="center", va="center",
    )


def pocket_label(spec: dict) -> str:
    if spec["shape"] == "circle":
        return f"Ø{spec['diameter']:g}"
    return f"{spec['along_x']:g}×{spec['along_y']:g}"


def pocket_half_xy(spec: dict) -> tuple[float, float]:
    """Half-extents of the pocket opening along X and Y."""
    if spec["shape"] == "circle":
        r = spec["diameter"] / 2
        return r, r
    return spec["along_x"] / 2, spec["along_y"] / 2


def fill_note(x_fill: dict | None) -> str | None:
    """One-line fill note for the top view, derived from the spec."""
    if not x_fill:
        return None
    style = x_fill.get("style", "web_floor")
    under = x_fill.get("under", "all")
    if style == "web_floor" and under == "all":
        return (f"ALL POCKETS: X-web floor — ribs {x_fill.get('rib_width', 4):g} mm wide,"
                f" block bottom → pocket floor, ends embedded"
                f" {x_fill.get('rib_embed', 2):g} mm into walls")
    return f"FILL: see spec features.x_fill (style: {style}, under: {under})"


def fill_targets(spec: dict) -> list[str]:
    """Pocket ids the spec's x_fill applies to.

    Mirrors the model rule exactly (models/<part>.build): under == "all", or
    "deep_only" with little material left below the pocket floor. The old
    schematic renderer used 'deepest pocket' here — a latent mismatch with
    the model; the gate now has to match the model, not a guess.
    """
    xf = spec["features"].get("x_fill")
    if not xf:
        return []
    leg_h = spec["dimensions"]["leg_height"]
    top_z = spec["dimensions"]["height"] + leg_h
    pockets = spec["features"]["pockets"]
    if xf.get("under", "all") == "deep_only":
        return [p["id"] for p in pockets if (top_z - p["depth"]) - leg_h <= 5]
    return [p["id"] for p in pockets]


# ---------------------------------------------------------------- flange kind
#
# Round flange parts (``features.flange_plate``): plate + hub + through bore
# + keyway + bolt circle. As with the pockets, the probes and the draw
# functions mirror the model (``models/hub_flange.py``): bolt hole positions
# from the same spec formula (start angle + even spacing), feature lines
# identified in the projected views by position and span.


def _flange_hole_positions(spec: dict) -> list[tuple[float, float]]:
    """Bolt hole centres: the model's rule (models/hub_flange) mirrored.

    Hole #1 at start_angle_deg (90 = +Y), then every 360/count degrees. The
    model's own positions are pinned to the spec by tests/test_hub_flange.py,
    so a drift between this mirror and the model surfaces as a gate failure.
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


def _vertical_lines(edges, want_x: float, z0: float, z1: float) -> list:
    """Projected vertical line edges at |x| ≈ want_x spanning [z0, z1].

    Front/end views map the model's vertical axis (Z) to the viewport Y, so a
    vertical edge is a constant-viewport-x line; |x| keeps the end view's
    unresolved ±Y sign irrelevant.
    """
    out = []
    for e in edges:
        b = e.bounding_box()
        if (b.max.X - b.min.X <= TOL
                and abs(abs((b.min.X + b.max.X) / 2) - want_x) <= TOL
                and b.min.Y >= z0 - TOL and b.max.Y <= z1 + TOL):
            out.append(e)
    return out


def _dim_h_narrow(ax, x0, x1, y, text, ext0=None, ext1=None,
                  stub: float = 5, offset: float = 2) -> None:
    """Horizontal dimension too narrow for two inside arrowheads (ISO 129).

    Arrowheads (~3.4 mm at 1:2) would overlap on dims under ~7 mm, so the
    arrows sit OUTSIDE on short stubs, pointing inward at the extension
    lines; the dim line spans the feature and the label sits above it.
    """
    ax.plot([x0, x1], [y, y], **DIMLINE)
    ax.annotate("", xy=(x0, y), xytext=(x0 - stub, y),
                arrowprops=dict(arrowstyle="->", color="#1a1a1a", lw=1.0,
                                shrinkA=0, shrinkB=0, mutation_scale=12))
    ax.annotate("", xy=(x1, y), xytext=(x1 + stub, y),
                arrowprops=dict(arrowstyle="->", color="#1a1a1a", lw=1.0,
                                shrinkA=0, shrinkB=0, mutation_scale=12))
    for xf, ef in ((x0, ext0), (x1, ext1)):
        if ef is None:
            continue
        d = 1 if y > ef else -1
        ax.plot([xf, xf], [ef + d * 2, y + d * 4], **DIMLINE)
    ax.text((x0 + x1) / 2, y + offset, text, ha="center", va="bottom",
            fontsize=10, color="#1a1a1a")


def _dim_v_narrow(ax, x, y0, y1, text, ext0=None, ext1=None,
                  stub: float = 5) -> None:
    """Vertical dimension too narrow for two inside arrowheads (ISO 129).

    Mirror of _dim_h_narrow: at 1:2 the arrowheads would overlap on spans
    under ~7 mm, so they sit OUTSIDE on short stubs past the extension
    lines, pointing inward (ISO 129-1:2018 5.3). The label stays IN LINE
    with the dimension — on the dim line axis, above the upper extension
    line and its outside arrowhead, like the horizontal narrow label sits
    above its line; a label parked sideways off the axis read as detached
    from the dimension (owner 2026-10-28).
    """
    ax.plot([x, x], [y0, y1], **DIMLINE)
    ax.annotate("", xy=(x, y0), xytext=(x, y0 - stub),
                arrowprops=dict(arrowstyle="->", color="#1a1a1a", lw=1.0,
                                shrinkA=0, shrinkB=0, mutation_scale=12))
    ax.annotate("", xy=(x, y1), xytext=(x, y1 + stub),
                arrowprops=dict(arrowstyle="->", color="#1a1a1a", lw=1.0,
                                shrinkA=0, shrinkB=0, mutation_scale=12))
    for yf, ef in ((y0, ext0), (y1, ext1)):
        if ef is None:
            continue
        d = 1 if x > ef else -1
        ax.plot([ef + d * 2, x + d * 4], [yf, yf], **DIMLINE)
    # a rotated digit label sits on the baseline, so its ink hangs ~0.6 mm
    # left of the (exactly axis-centred) text box; +1.2 model mm recentres
    # the INK on the dim line axis (measured on the render, owner review
    # 2026-10-28: "nesedi presne na ose")
    ax.text(x + 1.2, y1 + stub + 4, text, ha="center", va="bottom",
            fontsize=10, rotation=90, color="#1a1a1a")


def _flange_dimension_plan(spec: dict) -> list[dict]:
    """Dimension plan for the flange kind (round part: bolt circle + bore)."""
    dims = spec["dimensions"]
    n = spec["features"]["bolt_holes"]["count"]
    return [
        {"view": "top", "tag": "flange_diameter",
         "text": f"Ø{dims['flange_diameter']:g}"},
        {"view": "top", "tag": "hub_diameter",
         "text": f"Ø{dims['hub_diameter']:g}"},
        {"view": "top", "tag": "pcd_diameter",
         "text": f"Ø{dims['pcd_diameter']:g}"},
        {"view": "top", "tag": "bolt_hole_diameter",
         "text": (f"{n}X Ø{dims['bolt_hole_diameter']:g} EQ. SP. "
                  f"ON Ø{dims['pcd_diameter']:g} PCD")},
        {"view": "front", "tag": "flange_thickness",
         "text": f"{dims['flange_thickness']:g}"},
        {"view": "front", "tag": "hub_length",
         "text": f"{dims['hub_length']:g}"},
        {"view": "front", "tag": "height", "text": f"{dims['height']:g}"},
        {"view": "front", "tag": "bore_diameter",
         "text": f"Ø{dims['bore_diameter']:g}"},
        {"view": "front", "tag": "keyway_width",
         "text": f"{dims['keyway_width']:g}"},
        # DIN 6885 presents the keyway depth as d + t2: in the end view the
        # bore silhouette on the keyway side is cut away by the slot (the
        # slot-mouth line sits 0.66 mm from the wall line — illegible at
        # 1:2), so the depth is dimensioned across, from the opposite bore
        # wall to the keyway floor.
        {"view": "end", "tag": "keyway_depth",
         "text": f"{dims['bore_diameter'] + dims['keyway_depth']:g}"},
    ]


def _probe_flange(views: dict, spec: dict) -> dict:
    """Probes for the flange kind: bolt circle, bore, keyway, hub silhouette.

    Same contract as the pocket probes: read the projected edges (not the
    matplotlib output), so the manifest and the gate cannot drift.
    """
    dims = spec["dimensions"]
    vis_top, hid_top = views["top"]
    vis_front, hid_front = views["front"]
    vis_end, hid_end = views["end"]
    total = dims["height"]
    flange_t = dims["flange_thickness"]
    bore_r = dims["bore_diameter"] / 2
    hub_r = dims["hub_diameter"] / 2
    hole_r = dims["bolt_hole_diameter"] / 2
    key = spec["features"]["bore"]["keyway"]
    key_w, key_d = key["width"], key["depth"]

    bolt_holes = {}
    for i, (cx, cy) in enumerate(_flange_hole_positions(spec), start=1):
        opening = _edges_in(vis_top, cx - hole_r - TOL, cx + hole_r + TOL,
                            cy - hole_r - TOL, cy + hole_r + TOL)
        bb = _union_bbox(opening)
        bolt_holes[f"hole_{i}"] = {
            "top_opening_edges": len(opening),
            "position_size_ok": bool(
                opening and bb
                and abs((bb[0] + bb[1]) / 2 - cx) <= TOL
                and abs((bb[2] + bb[3]) / 2 - cy) <= TOL
                and abs((bb[1] - bb[0]) - 2 * hole_r) <= TOL
                and abs((bb[3] - bb[2]) - 2 * hole_r) <= TOL
            ),
        }

    bore_lines = _vertical_lines(hid_front, bore_r, 0, total)
    bb = _union_bbox(bore_lines) if bore_lines else None
    bore = {
        "front_hidden_profile_edges": len(bore_lines),
        "front_profile_position_ok": bool(
            bb and abs((bb[0] + bb[1]) / 2) <= TOL
            and abs((bb[1] - bb[0]) - 2 * bore_r) <= TOL),
    }

    key_front = _vertical_lines(hid_front, key_w / 2, 0, total)
    key_floor = (_vertical_lines(vis_end, bore_r + key_d, 0, total)
                 + _vertical_lines(hid_end, bore_r + key_d, 0, total))
    fb = _union_bbox(key_floor) if key_floor else None
    keyway = {
        "front_hidden_lines": len(key_front),
        "end_floor_lines": len(key_floor),
        "end_floor_position_ok": bool(
            fb and abs(abs((fb[0] + fb[1]) / 2) - (bore_r + key_d)) <= TOL),
    }

    hub_lines = _vertical_lines(vis_front, hub_r, flange_t, total)
    return {
        "bolt_holes": bolt_holes,
        "bore": bore,
        "keyway": keyway,
        "hub": {"front_silhouette_edges": len(hub_lines)},
    }


def _draw_top_flange(ax, view, spec: dict) -> list[str]:
    """Top view for the flange kind: centre lines, PCD and hole callouts."""
    vis, hid = view
    dims = spec["dimensions"]
    plot_edges(ax, vis, **SOLID)
    plot_edges(ax, hid, **HIDDEN)
    r_f = dims["flange_diameter"] / 2
    r_hub = dims["hub_diameter"] / 2
    r_pcd = dims["pcd_diameter"] / 2
    plan = {e["tag"]: e["text"] for e in dimension_plan(spec)
            if e["view"] == "top"}
    # centre cross through the origin, 3 mm past the outline (ISO 128-24
    # type 04.1, the pocket centre-line convention)
    ax.plot([-r_f - 3, r_f + 3], [0, 0], **CENTERLINE)
    ax.plot([0, 0], [-r_f - 3, r_f + 3], **CENTERLINE)
    # bolt PCD as a dash-dot centre-line circle (ISO 129 bolt-circle convention)
    ax.add_patch(Circle((0, 0), r_pcd, fill=False, lw=1.0, edgecolor="black",
                        linestyle=(0, (24, 3, 1, 3))))
    holes = _flange_hole_positions(spec)
    for cx, cy in holes:
        ax.plot([cx - 3, cx + 3], [cy, cy], **CENTERLINE)
        ax.plot([cx, cx], [cy - 3, cy + 3], **CENTERLINE)
    leader(ax, (r_f * math.cos(math.radians(200)),
                r_f * math.sin(math.radians(200))),
           (-r_f - 24, -r_f * 0.45), plan["flange_diameter"])
    leader(ax, (r_hub * math.cos(math.radians(30)),
                r_hub * math.sin(math.radians(30))),
           (r_hub + 13, r_hub * 0.3), plan["hub_diameter"])
    leader(ax, (r_pcd * math.cos(math.radians(340)),
                r_pcd * math.sin(math.radians(340))),
           (r_pcd + 22, -r_pcd * 0.5), plan["pcd_diameter"])
    # bolt note with a leader to the hole nearest the note (hole #4, 270°);
    # fontsize 8 — the note is long, the standard 9 would crowd the view
    nx, ny = -r_f - 20, -r_f - 14
    hx, hy = holes[3]
    hr = dims["bolt_hole_diameter"] / 2
    dx, dy = hx - nx, hy - ny
    L = math.hypot(dx, dy)
    ax.annotate(plan["bolt_hole_diameter"],
                xy=(hx - hr * dx / L, hy - hr * dy / L), xytext=(nx, ny),
                fontsize=8, color="#1a1a1a", ha="center", va="center",
                arrowprops=dict(arrowstyle="->", color="#1a1a1a", lw=1.0))
    ax.set_xlim(-r_f - 50, r_f + 10)
    ax.set_ylim(-r_f - 18, r_f + 5)
    ax.set_aspect("equal")
    ax.set_title("TOP VIEW", fontsize=10, loc="left")
    ax.axis("off")
    return ["flange_diameter", "hub_diameter", "pcd_diameter",
            "bolt_hole_diameter"]


def _draw_front_flange(ax, view, spec: dict) -> list[str]:
    """Front view for the flange kind: silhouette + stack dimensions."""
    vis, hid = view
    plot_edges(ax, vis, **SOLID)
    plot_edges(ax, hid, **HIDDEN)
    dims = spec["dimensions"]
    r_f = dims["flange_diameter"] / 2
    flange_t = dims["flange_thickness"]
    r_hub = dims["hub_diameter"] / 2
    r_bore = dims["bore_diameter"] / 2
    key_w = dims["keyway_width"]
    total = dims["height"]
    plan = {e["tag"]: e["text"] for e in dimension_plan(spec)
            if e["view"] == "front"}
    _dim_v_narrow(ax, -r_f - 14, 0, flange_t, plan["flange_thickness"],
                  ext0=-r_f, ext1=-r_f)
    dim_v(ax, r_hub + 14, flange_t, total, plan["hub_length"],
          ext0=r_hub, ext1=r_hub)
    dim_v(ax, r_f + 14, 0, total, plan["height"], ext0=r_f, ext1=r_f)
    dim_h(ax, -r_bore, r_bore, -18, plan["bore_diameter"], ext0=0, ext1=0)
    _dim_h_narrow(ax, -key_w / 2, key_w / 2, total + 8, plan["keyway_width"],
                  ext0=total, ext1=total)
    ax.set_xlim(-r_f - 25, r_f + 30)
    ax.set_ylim(-24, total + 20)
    ax.set_aspect("equal")
    ax.set_title("FRONT VIEW", fontsize=10, loc="left")
    ax.axis("off")
    return ["flange_thickness", "hub_length", "height", "bore_diameter",
            "keyway_width"]


def _draw_end_flange(ax, view, spec: dict) -> list[str]:
    """End view for the flange kind: keyway depth per DIN 6885 (d + t2).

    The bare depth (3.3 mm) is not drawable here: the bore silhouette on the
    keyway side is cut away by the slot and the slot-mouth line sits 0.66 mm
    from the wall line — illegible at 1:2. The depth is therefore dimensioned
    across, from the opposite bore wall (drawn) to the keyway floor (drawn),
    with outside arrows (ISO 129 narrow-dimension style). The keyway side
    sign is a projection convention (the end view maps ±Y to ∓x): read from
    the projected keyway floor line, mirroring the probe.
    """
    vis, hid = view
    plot_edges(ax, vis, **SOLID)
    plot_edges(ax, hid, **HIDDEN)
    dims = spec["dimensions"]
    r_f = dims["flange_diameter"] / 2
    r_bore = dims["bore_diameter"] / 2
    key_d = dims["keyway_depth"]
    total = dims["height"]
    plan = {e["tag"]: e["text"] for e in dimension_plan(spec)
            if e["view"] == "end"}
    floor = (_vertical_lines(vis, r_bore + key_d, 0, total)
             + _vertical_lines(hid, r_bore + key_d, 0, total))
    sign = 1
    if floor:
        b = floor[0].bounding_box()
        sign = 1 if (b.min.X + b.max.X) / 2 >= 0 else -1
    # d + t2 across the part (DIN 6885): from the bore wall on the side
    # OPPOSITE the keyway (its silhouette line is drawn) to the keyway floor
    _dim_h_narrow(ax, -sign * r_bore, sign * (r_bore + key_d), -14,
                  plan["keyway_depth"], ext0=0, ext1=0)
    ax.set_xlim(-r_f - 6, r_f + 6)
    ax.set_ylim(-20, total + 6)
    ax.set_aspect("equal")
    ax.set_title("END VIEW", fontsize=10, loc="left")
    ax.axis("off")
    return ["keyway_depth"]


def dimension_plan(spec: dict) -> list[dict]:
    """The complete set of dimensions the drawing must carry.

    Single source of truth for WHAT is dimensioned (view + tag + text); the
    draw functions place these by tag, the manifest records them and the
    completeness test checks the plan covers every spec dimension key.
    """
    dims, feats = spec["dimensions"], spec["features"]
    if "flange_plate" in feats:
        return _flange_dimension_plan(spec)
    xs = sorted({p["x_position"] for p in feats["pockets"]})
    plan: list[dict] = []
    if len(xs) > 1:
        plan.append({"view": "top", "tag": "pitch", "text": f"{xs[1] - xs[0]:g}"})
    plan += [
        {"view": "top", "tag": "length", "text": f"{dims['length']:g}"},
        {"view": "top", "tag": "width", "text": f"{dims['width']:g}"},
        {"view": "front", "tag": "height", "text": f"{dims['height']:g}"},
        {"view": "front", "tag": "length", "text": f"{dims['length']:g}"},
        {"view": "end", "tag": "total_height",
         "text": f"{dims['leg_height'] + dims['height']:g}"},
        {"view": "end", "tag": "width", "text": f"{dims['width']:g}"},
    ]
    if "legs" in feats:
        plan += [
            {"view": "front", "tag": "leg_height", "text": f"{dims['leg_height']:g}"},
            {"view": "front", "tag": "leg_diameter",
             "text": f"Ø{dims['leg_diameter']:g}"},
            {"view": "front", "tag": "leg_inset",
             "text": f"{feats['legs']['inset']:g}"},
        ]
    return plan


# ---------------------------------------------------------------- projection


def load_model_module(spec_path: Path):
    """Resolve the part's model module by convention: models/<part>."""
    root = Path(__file__).resolve().parents[1]
    if str(root) not in sys.path:  # CLI run: sys.path[0] is tools/, not root
        sys.path.insert(0, str(root))
    return importlib.import_module(f"models.{spec_path.parent.name}")


def project_views(part, dims: dict) -> dict[str, tuple[list, list]]:
    """Third-angle projections: top (from +Z), front (from −Y), end (from +X).

    Returns ``{name: (visible_edges, hidden_edges)}``. Projected edges lie in
    the viewport plane (Z = 0) with viewport X/Y on the model axes the
    dimension code uses: top → (X, Y); front → (X, Z); end → (∓Y, Z).
    """
    d = max(dims["length"], dims["width"], dims["height"]) * 3 + 100
    cameras = {
        "top": ((0, 0, d), (0, 1, 0)),
        "front": ((0, -d, 0), (0, 0, 1)),
        "end": ((d, 0, 0), (0, 0, 1)),
    }
    return {
        name: part.project_to_viewport(origin, up, look_at=(0, 0, 0))
        for name, (origin, up) in cameras.items()
    }


def small_circle_solid(length_mm: float, linestyle) -> bool:
    """Hidden circles too small for a legible dash pattern are drawn solid.

    A closed circle with a circumference under 3 dash periods cannot carry
    the 12d/3d pattern legibly (the seam dominates — the 'C' artifact on the
    Ø5 legs); practice (ASME Y14.2) substitutes a continuous narrow line.
    Declared as a convention in the manifest.
    """
    if not isinstance(linestyle, tuple) or len(linestyle) != 2 or not linestyle[1]:
        return False
    return length_mm * SCALE * 72 / 25.4 < 3 * sum(linestyle[1])


def closed_dash_offset(edge, linestyle) -> float | None:
    """Phase shift putting the seam of a closed circular edge mid-gap.

    Dash patterns start at the path start; on a closed curve the seam gets
    the leftover segment (circumference mod period) in an arbitrary phase,
    which read as the 'C' artifact on small hidden circles (legs Ø5, top
    view). Shifting by (gap midpoint − seam position) centres the seam in a
    gap, symmetric on both sides. Lengths: data mm × scale × 72/25.4 = pt.
    """
    if not isinstance(linestyle, tuple) or len(linestyle) != 2:
        return None
    _offset, seq = linestyle
    if not seq or len(seq) % 2 or sum(seq) <= 0:
        return None
    period = float(sum(seq))
    gap_mid = sum(seq[:-1]) + seq[-1] / 2
    seam = (edge.length * SCALE * 72 / 25.4) % period
    return (gap_mid - seam) % period


def plot_edges(ax, edges, step: float = 1.0, max_points: int = 96, **style) -> int:
    """Sample and plot projected edges; returns the number of edges drawn."""
    for e in edges:
        st = style
        if e.geom_type == GeomType.CIRCLE and e.is_closed:
            ls = style.get("linestyle")
            if small_circle_solid(e.length, ls):
                st = {k: v for k, v in style.items() if k != "linestyle"}
            else:
                off = closed_dash_offset(e, ls)
                if off is not None:
                    st = dict(style, linestyle=(off, ls[1]))
        n = min(max_points, max(2, math.ceil(e.length / step) + 1))
        pts = [(v.X, v.Y) for v in (e @ (i / (n - 1)) for i in range(n))]
        xs, ys = zip(*pts)
        ax.plot(xs, ys, **st)
    return len(edges)


def plot_polylines(ax, polys, **style) -> int:
    """Plot pre-sampled polylines (trimmed edges) with the same style."""
    for xs, ys in polys:
        ax.plot(xs, ys, **style)
    return len(polys)


def _outline_trim_split(edges, pockets, lw_pt: float, scale: float,
                        step: float = 1.0, max_points: int = 96):
    """Split edges into (plot-as-is edges, trimmed polylines).

    A web arm ending ON a pocket outline draws its butt-cap corner up to
    ``hw/tan(theta)`` past the outline (the ink artifact the owner flagged
    2026-10-24: "X zebra presahuji ven z obdelniku"). Such an end is pulled
    back along the arm so the cap corners stay under the outline's own line
    width — no ink outside the opening, no visible gap at 1:2. Edges lying
    wholly ON an outline (the outline itself, junction segments) are
    returned unchanged.
    """
    hw = lw_pt * 25.4 / 72 / 2 / scale  # half line width in data mm

    def rel(p, x, y):
        return _cavity_plan_rel(x, y, p)

    normal, trimmed_polys = [], []
    for e in edges:
        n = min(max_points, max(2, math.ceil(e.length / step) + 1))
        pts = [(v.X, v.Y) for v in (e @ (i / (n - 1)) for i in range(n))]
        pk = next((p for p in pockets
                   if any(rel(p, x, y) != "OUT" for x, y in pts)), None)
        if pk is None:
            normal.append(e)
            continue
        rels = [rel(pk, x, y) for x, y in pts]
        if all(r == "ON" for r in rels):
            normal.append(e)  # outline / junction segment — never trimmed
            continue
        trimmed = list(pts)
        changed = False
        for idx, nb in ((0, 1), (-1, -2)):
            if rels[idx] == "ON" and rels[nb] == "IN":
                (x0, y0), (x1, y1) = pts[idx], pts[nb]
                dx, dy = x1 - x0, y1 - y0
                L = math.hypot(dx, dy)
                if L < 1e-9:
                    continue
                if pk["shape"] == "circle":
                    tx, ty = -y0, x0 - pk["x_position"]  # tangent to the arc
                else:
                    px_, py_ = x0 - pk["x_position"], y0
                    hx_, hy_ = pocket_half_xy(pk)
                    tx, ty = ((0.0, 1.0) if abs(abs(px_) - hx_)
                              >= abs(abs(py_) - hy_) else (1.0, 0.0))
                tl = math.hypot(tx, ty) or 1.0
                tx, ty = tx / tl, ty / tl
                ux, uy = dx / L, dy / L
                sin_t = abs(ux * ty - uy * tx)
                cos_t = abs(ux * tx + uy * ty)
                if sin_t < 1e-6:
                    continue
                pull = min(hw * cos_t / sin_t, L * 0.45)
                trimmed[idx] = (x0 + ux * pull, y0 + uy * pull)
                changed = True
        if changed:
            trimmed_polys.append(([p[0] for p in trimmed],
                                  [p[1] for p in trimmed]))
        else:
            normal.append(e)
    return normal, trimmed_polys


# ---------------------------------------------------------------- rib-edge suppression
#
# The fused model keeps the webs' embedded parts (rib ends 2 mm inside the
# walls) and every web touching a wall creates junction edges on the wall
# surface. Projected, these are the artifacts the owner rejected on
# 2026-10-23/24: bar ends overrunning the pocket outlines (top view),
# "crowns" of ticks and connector arcs at the walls (front/end views) and
# web-web crossing seams. None of them is a transition of functional
# surfaces — the material behind a pocket outline is homogeneous, and
# ISO 128 draws no edges inside homogeneous material. Of all web-related
# edges the drawing therefore keeps the void-facing floor/bottom chords
# (the pocket floor line and the X seen through the opening) and drops the
# rest PER VIEW: a suppressed edge is a drop candidate only where its
# projection lies strictly inside its pocket's outline, or wholly in the
# walls (embedded rib ends); where it lies ON the outline it survives,
# because there it IS the pocket silhouette — the slot walls run unbroken
# to the block bottom behind the embedded rib ends, and the projection has
# no other edge to draw that segment from (owner finding 2026-10-24). The
# model itself is NOT modified.


def _cavity_plan_rel(x: float, y: float, pocket: dict, eps: float = 0.02) -> str:
    """IN / ON / OUT of one pocket cavity's plan cross-section."""
    hx, hy = pocket_half_xy(pocket)
    px, py = x - pocket["x_position"], y
    if pocket["shape"] == "circle":
        d = math.hypot(px, py)
        return "ON" if abs(d - hx) <= eps else ("IN" if d < hx - eps else "OUT")
    m = max(abs(px) - hx, abs(py) - hy)
    return "ON" if abs(m) <= eps else ("IN" if m < -eps else "OUT")


def _inside_cavity_view(pt: tuple[float, float], view: str, pocket: dict,
                        leg_h: float, top_z: float, eps: float = 0.05) -> bool:
    """Strictly inside the pocket's outline as seen in `view`.

    top: the cavity's plan cross-section; front: (x, z); end: (±y, z) — the
    end view's sign is irrelevant, the test is symmetric in y. A sample ON
    the outline is NOT inside: an edge running along the outline (a wall
    junction continuing the pocket silhouette below the X-web floor down to
    the block bottom) survives there, while edges strictly inside (crowns,
    crossing seams) or wholly in the walls (embedded rib ends) are droppable.
    """
    hx, hy = pocket_half_xy(pocket)
    if view == "top":
        return _cavity_plan_rel(pt[0], pt[1], pocket) == "IN"
    if view == "front":
        x, z = pt
        return (abs(x - pocket["x_position"]) < hx - eps
                and leg_h + eps < z < top_z - eps)
    y, z = pt
    return abs(y) < hy - eps and leg_h + eps < z < top_z - eps


def _drop_candidate(edge, polys, view: str, pocket: dict, leg_h: float,
                    top_z: float, n: int = 33) -> bool:
    """Per-view drop decision for one suppressed 3D edge.

    True when the edge's `view` projection (polys) has a sample strictly
    inside the pocket's outline, or the edge lies wholly in the walls: every
    PLAN sample (the edge's own 3D X/Y, not the projection) OUT of the
    cavity — embedded rib ends are false in every view. Shared by the
    renderer and the gate so the two cannot drift.
    """
    if any(_inside_cavity_view(q, view, pocket, leg_h, top_z)
           for poly in polys for q in poly):
        return True
    pts = [edge @ (i / (n - 1)) for i in range(n)]
    return all(_cavity_plan_rel(p.X, p.Y, pocket) == "OUT" for p in pts)


def _web_solids(spec: dict, builder_module) -> list:
    """The X-web solids exactly as the model builds them (its own helpers)."""
    if "pockets" not in spec["features"]:
        return []
    dims = spec["dimensions"]
    leg_h = dims["leg_height"]
    top_z = leg_h + dims["height"]
    targets = set(fill_targets(spec))
    webs = []
    for p in spec["features"]["pockets"]:
        if p["id"] not in targets:
            continue
        floor_z = top_z - p["depth"]
        remaining = floor_z - leg_h
        webs += [(p["id"], w) for w in builder_module._x_ribs(
            p, spec["features"]["x_fill"]["rib_width"], remaining,
            (leg_h + floor_z) / 2,
            rib_len=builder_module._pocket_span(p)
            + 2 * spec["features"]["x_fill"].get("rib_embed", 2))]
    return webs


def _line_key(e):
    a, b = e @ 0, e @ 1
    pa = (round(a.X, 4), round(a.Y, 4), round(a.Z, 4))
    pb = (round(b.X, 4), round(b.Y, 4), round(b.Z, 4))
    return (pa, pb) if pa <= pb else (pb, pa)


def _seam_edges(part) -> list:
    """Seam edges (a cylindrical face meeting itself) are modeling artifacts,
    not part edges — they must never serve as the "real edge" that shields a
    false web edge from suppression, and per the owner's 2026-10-24 decision
    they are suppressed from the drawing. A cylinder's only straight edges are
    its seams, so seams are keyed geometrically from the cylindrical faces."""
    faces_by_key, edges_by_key = {}, {}
    for f in part.faces():
        for fe in f.edges():
            if fe.geom_type != GeomType.LINE:
                continue
            k = _line_key(fe)
            faces_by_key.setdefault(k, set()).add(id(f))
            edges_by_key.setdefault(k, fe)
    # a true seam belongs to exactly ONE face (the cylinder meeting itself);
    # a wall junction line is shared by the cylinder and the rib plane — two
    # distinct faces — and must NOT be treated as a seam
    return [edges_by_key[k] for k, fs in faces_by_key.items() if len(fs) == 1]


def classify_rib_edges(part, spec: dict, builder_module, n_samples: int = 9):
    """Split the part's edges into (keep, suppress) web classes.

    Web-related = every sampled point lies on/in a web solid, rebuilt from
    the spec with the model's own helpers so the classification cannot drift
    from the model. Kept: horizontal edges on the webs' top/bottom faces with
    a point strictly inside the pocket cavity and none outside it — the
    void-facing floor and bottom chords — and the wall junctions (edges lying
    on the pocket wall: real concave edges, strict ISO 128 draws them dashed;
    owner request 2026-10-24). Suppressed: embedded rib ends and web-web
    crossing seams — edges of homogeneous material. Non-web edges (outlines,
    silhouettes, rims, legs) stay. The
    per-view drop decision (strictly inside the pocket outline vs. on it)
    happens later, in ``suppress_false_rib_edges``.
    """
    if "pockets" not in spec["features"]:
        edges = list(part.edges())
        seam_keys = {_line_key(e) for e in _seam_edges(part)}
        seam_ids = {id(e) for e in edges
                    if e.geom_type == GeomType.LINE and _line_key(e) in seam_keys}
        stats = {"web_keep": 0, "web_suppress": 0, "seam_edges": len(seam_ids)}
        return [], [], [e for e in edges if id(e) not in seam_ids], stats
    from OCP.BRepClass3d import BRepClass3d_SolidClassifier
    from OCP.gp import gp_Pnt
    from OCP.TopAbs import TopAbs_State
    on_in = (TopAbs_State.TopAbs_ON, TopAbs_State.TopAbs_IN)
    dims = spec["dimensions"]
    leg_h = dims["leg_height"]
    top_z = leg_h + dims["height"]
    pockets = {p["id"]: p for p in spec["features"]["pockets"]}
    webs = _web_solids(spec, builder_module)
    web_bbs = [(pid, w.bounding_box()) for pid, w in webs]
    seam_keys = {_line_key(e) for e in _seam_edges(part)}
    edges = list(part.edges())
    seam_ids = {id(e) for e in edges
                if e.geom_type == GeomType.LINE and _line_key(e) in seam_keys}
    keep, suppress, others = [], [], []
    for e in edges:
        bb = e.bounding_box()
        pts = [e @ (i / (n_samples - 1)) for i in range(n_samples)]
        hit = None
        for (pid, w), (_, wb) in zip(webs, web_bbs):
            if (bb.max.X < wb.min.X - 0.5 or bb.min.X > wb.max.X + 0.5
                    or bb.max.Y < wb.min.Y - 0.5 or bb.min.Y > wb.max.Y + 0.5
                    or bb.max.Z < wb.min.Z - 0.5 or bb.min.Z > wb.max.Z + 0.5):
                continue
            if all(BRepClass3d_SolidClassifier(
                    w.wrapped, gp_Pnt(pt.X, pt.Y, pt.Z), 1e-7).State() in on_in
                    for pt in pts):
                hit = pid
                break
        if hit is None:
            if id(e) not in seam_ids:
                others.append(e)
            continue
        p = pockets[hit]
        rels = [_cavity_plan_rel(pt.X, pt.Y, p) for pt in pts]
        zs = [pt.Z for pt in pts]
        floor_z = top_z - p["depth"]
        horizontal = max(zs) - min(zs) <= 1e-6
        at_face = any(abs(z - leg_h) <= 1e-6 or abs(z - floor_z) <= 1e-6 for z in zs)
        void_facing = "OUT" not in rels and "IN" in rels
        junction = all(r == "ON" for r in rels)
        (keep if ((horizontal and at_face and void_facing) or junction)
         else suppress).append((e, hit))
    stats = {"web_keep": len(keep), "web_suppress": len(suppress),
             "seam_edges": len(seam_ids)}
    return keep, suppress, others, stats


def _analytic_2d(edge, view: str, n: int = 33) -> list[list[tuple[float, float]]]:
    """Orthographic 2D projection of a 3D edge in the view's coordinate frame.

    Mirrors project_to_viewport's mapping the dimension code relies on:
    top -> (X, Y), front -> (X, Z), end -> (±Y, Z). The end view's sign is
    not resolvable from this symmetric part, so both variants are returned
    and a match against either counts.
    """
    pts = [edge @ (i / (n - 1)) for i in range(n)]
    if view == "top":
        return [[(p.X, p.Y) for p in pts]]
    if view == "front":
        return [[(p.X, p.Z) for p in pts]]
    return [[(p.Y, p.Z) for p in pts], [(-p.Y, p.Z) for p in pts]]


def _point_near_polyline(q, poly, eps: float) -> bool:
    best = math.inf
    for (ax_, ay_), (bx, by) in zip(poly, poly[1:]):
        dx, dy = bx - ax_, by - ay_
        l2 = dx * dx + dy * dy
        t = 0.0 if l2 == 0 else max(0.0, min(1.0, ((q[0] - ax_) * dx
                                                   + (q[1] - ay_) * dy) / l2))
        best = min(best, math.hypot(q[0] - (ax_ + t * dx), q[1] - (ay_ + t * dy)))
        if best < eps:
            return True
    return False


def _matches_suppressed(proj_edge, polys, eps: float = 0.05, n: int = 15) -> bool:
    """True when every sample of the projected edge lies on some polyline."""
    pp = [(v.X, v.Y) for v in (proj_edge @ (i / (n - 1)) for i in range(n))]
    return any(all(_point_near_polyline(q, poly, eps) for q in pp) for poly in polys)


def suppress_false_rib_edges(views, part, spec: dict, builder_module):
    """Filter projected views: drop edges whose 3D source is a false web edge
    or a cylinder seam.

    The true model's projection is filtered, not re-projected from a modified
    copy — HLR visibility stays exactly as the model dictates; only edges of
    homogeneous material disappear. A projected edge is dropped when every
    sample lies on the analytic orthographic projection of a suppressed 3D
    edge (bbox prefilter + point-to-polyline match).
    """
    keep3d, supp3d, others3d, stats = classify_rib_edges(part, spec, builder_module)
    seam3d = _seam_edges(part)
    pockets = {p["id"]: p for p in spec["features"].get("pockets", [])}
    leg_h = spec["dimensions"].get("leg_height", 0)
    top_z = leg_h + spec["dimensions"]["height"]
    real3d = [e for e, _ in keep3d] + others3d
    filtered, per_view = {}, {}
    for view, (vis, hid) in views.items():
        supp_polys, survivor_polys = [], []
        for e, pid in supp3d:
            polys = _analytic_2d(e, view)
            if _drop_candidate(e, polys, view, pockets[pid], leg_h, top_z):
                supp_polys += polys
            else:
                survivor_polys += polys
        # cylinder seam edges are projection artifacts (owner 2026-10-24):
        # dropped in the end view, where they show as a stray line on the
        # pocket axis; in the front view they coincide with the wall
        # silhouette, so dropping them there could eat the silhouette itself
        if view == "end":
            for e in seam3d:
                supp_polys += _analytic_2d(e, view)
        other_polys = [poly for e in real3d for poly in _analytic_2d(e, view)]
        other_polys += survivor_polys

        def _boxes(polys):
            out = []
            for poly in polys:
                xs = [q[0] for q in poly]
                ys = [q[1] for q in poly]
                out.append((min(xs), max(xs), min(ys), max(ys)))
            return out

        supp_boxes, other_boxes = _boxes(supp_polys), _boxes(other_polys)

        def dropped(e, _sp=supp_polys, _sb=supp_boxes,
                    _op=other_polys, _ob=other_boxes):
            b = e.bounding_box()
            hit = False
            for polys, boxes in ((_sp, _sb),):
                for poly, (x0, x1, y0, y1) in zip(polys, boxes):
                    if (b.max.X < x0 - 0.2 or b.min.X > x1 + 0.2
                            or b.max.Y < y0 - 0.2 or b.min.Y > y1 + 0.2):
                        continue
                    if _matches_suppressed(e, [poly]):
                        hit = True
                        break
            if not hit:
                return False
            # a false edge coinciding in 2D with a real edge (e.g. a wall
            # junction under the pocket silhouette) cannot be told apart
            # after projection — it is invisible there, so it stays
            for poly, (x0, x1, y0, y1) in zip(_op, _ob):
                if (b.max.X < x0 - 0.2 or b.min.X > x1 + 0.2
                        or b.max.Y < y0 - 0.2 or b.min.Y > y1 + 0.2):
                    continue
                if _matches_suppressed(e, [poly]):
                    return False
            return True

        nv = [e for e in vis if not dropped(e)]
        nh = [e for e in hid if not dropped(e)]
        per_view[view] = {"dropped_visible": len(vis) - len(nv),
                          "dropped_hidden": len(hid) - len(nh)}
        filtered[view] = (nv, nh)
    return filtered, {"web_edges": stats, "per_view": per_view}


def project_drawing_views(part, spec: dict, builder_module):
    """Raw projection + false-rib-edge suppression = the views as drawn."""
    views = project_views(part, spec["dimensions"])
    return suppress_false_rib_edges(views, part, spec, builder_module)


# ---------------------------------------------------------------- probes


def _union_bbox(edges):
    boxes = [e.bounding_box() for e in edges]
    if not boxes:
        return None
    return (
        min(b.min.X for b in boxes), max(b.max.X for b in boxes),
        min(b.min.Y for b in boxes), max(b.max.Y for b in boxes),
    )


def _edges_in(edges, x0, x1, y0, y1) -> list:
    return [
        e for e in edges
        if (b := e.bounding_box()).min.X >= x0 and b.max.X <= x1
        and b.min.Y >= y0 and b.max.Y <= y1
    ]


def _diag_line_count(edges, cx, hx, hy, angles=(45.0,)) -> int:
    """Visible diagonal (rib) lines crossing the pocket centre in a view."""
    n = 0
    for e in edges:
        if e.geom_type != GeomType.LINE:
            continue
        a, b = e @ 0, e @ 1
        mx, my = (a.X + b.X) / 2, (a.Y + b.Y) / 2
        if abs(mx - cx) <= hx and abs(my) <= hy:
            ang = math.degrees(math.atan2(abs(b.Y - a.Y), abs(b.X - a.X)))
            if any(abs(ang - t) < 6 for t in angles):
                n += 1
    return n


def _leg_edges(vis, leg_axis: float, leg_h: float) -> int:
    n = 0
    for e in vis:
        b = e.bounding_box()
        if (b.min.Y >= -TOL and b.max.Y <= leg_h + TOL
                and abs(abs((b.min.X + b.max.X) / 2) - leg_axis) < 2):
            n += 1
    return n


def probe_views(views: dict, spec: dict) -> dict:
    """Objective geometry probes of the projected views against the spec.

    Reads the projected edges (not the matplotlib output), so the same probes
    annotate the manifest and gate the drawing in the test suite.
    """
    dims, feats = spec["dimensions"], spec["features"]
    pockets = feats.get("pockets", [])
    leg_h = dims.get("leg_height", 0)
    top_z = dims["height"] + leg_h
    vis_top, hid_top = views["top"]
    vis_front, hid_front = views["front"]
    vis_end, hid_end = views["end"]
    probes: dict = {"pockets": {}, "x_fill": {}, "legs": {}, "outline": {}}
    if "flange_plate" in feats:
        probes["flange"] = _probe_flange(views, spec)

    for p in pockets:
        hx, hy = pocket_half_xy(p)
        cx = p["x_position"]
        opening = _edges_in(vis_top, cx - hx - TOL, cx + hx + TOL,
                            -hy - TOL, hy + TOL)
        bb = _union_bbox(opening)
        ok = bool(
            opening and bb
            and abs((bb[0] + bb[1]) / 2 - cx) <= TOL
            and abs((bb[1] - bb[0]) - 2 * hx) <= TOL
            and abs((bb[3] - bb[2]) - 2 * hy) <= TOL
        )
        profile = _edges_in(hid_front, cx - hx - TOL, cx + hx + TOL,
                            top_z - p["depth"] - TOL, top_z + TOL)
        probes["pockets"][p["id"]] = {
            "top_opening_edges": len(opening),
            "top_opening_position_size_ok": ok,
            "front_hidden_profile_edges": len(profile),
        }

    targets = set(fill_targets(spec))
    for p in pockets:
        hx, hy = pocket_half_xy(p)
        probes["x_fill"][p["id"]] = {
            "expected": p["id"] in targets,
            "diag_edges_in_top": _diag_line_count(vis_top, p["x_position"], hx, hy),
        }

    if "legs" in feats:
        probes["legs"] = {
            "front_visible_edges": _leg_edges(
                vis_front, dims["length"] / 2 - feats["legs"]["inset"], leg_h),
            "end_visible_edges": _leg_edges(
                vis_end, dims["width"] / 2 - feats["legs"]["inset"], leg_h),
        }

    for name, vis, want in (
        ("top", vis_top, (dims["length"], dims["width"])),
        ("front", vis_front, (dims["length"], top_z)),
        ("end", vis_end, (dims["width"], top_z)),
    ):
        bb = _union_bbox(vis)
        probes["outline"][name] = {
            "span_x_ok": bool(bb) and abs((bb[1] - bb[0]) - want[0]) <= TOL,
            "span_y_ok": bool(bb) and abs((bb[3] - bb[2]) - want[1]) <= TOL,
        }
    return probes


def build_manifest(views: dict, probes: dict, spec: dict,
                   spec_path: Path) -> dict:
    """Manifest of the drawing: view edge counts, probes, annotation plan."""
    return {
        "part": spec["part"],
        "spec": spec_path.name,
        "generator": "tools/render_drawing.py",
        "principle": ("views: projected from the model (build123d "
                      "project_to_viewport, OCCT HLR); annotations: from the spec"),
        "scale": "1:2 (ISO 5455)",
        "font": {
            "name": FONT_NAME,
            "standard": "ISO 3098 lettering (osifont)",
            "license": "GPL-3.0 with font exception (assets/fonts/osifont-LICENSE.txt)",
        },
        "sheet": {
            "size": "A4 landscape, 297×210 mm (ISO 5457)",
            "frame": "10 mm margin (convention — full ISO 5457 text not in repo)",
            "centring_marks": "omitted — optional per ISO 5457; a generated PDF is not a preprinted trimmed sheet",
            "small_circles": (
                "hidden circles with circumference < 3 dash periods drawn "
                "solid narrow (legibility convention)"),
            "frame_clearance": "every drawn element ≥2 mm inside the frame (mechanical gate)",
            "text_clearance": (
                "dimension/label texts ≥2 mm from the projected geometry "
                "(mechanical gate; leader arrows excluded — they point at "
                "geometry by design)"),
        },
        "line_styles": {
            "visible": "ISO 128-24 type 01.2, continuous wide (0.7 mm)",
            "hidden": "ISO 128-24 type 02.1, dashed narrow (0.35 mm, 12d/3d)",
            "centre_lines": ("ISO 128-24 type 04.1, long-dashed dotted narrow; "
                             "pocket centre lines extend 3 mm beyond the "
                             "opening (owner delegation 2026-10-24: the more "
                             "professional per ISO form)"),
            "dimensions": "ISO 128-24 type 01.1, continuous narrow",
        },
        "views": {
            name: {"visible_edges": len(v[0]), "hidden_edges": len(v[1])}
            for name, v in views.items()
        },
        "probes": probes,
        "annotations": {
            "dimensions": dimension_plan(spec),
            "pocket_labels": [
                {"id": p["id"], "text": pocket_label(p)}
                for p in spec["features"].get("pockets", [])
            ],
            "schedule_rows": (len(spec["features"].get("pockets", [])) + 1
                              if spec["features"].get("pockets") else 0),
            "fill_note": fill_note(spec["features"].get("x_fill")),
        },
    }


# ---------------------------------------------------------------- views


def draw_top(ax, view, spec: dict) -> list[str]:
    """Top view: projected edges + spec-driven labels, note and dimensions."""
    if "flange_plate" in spec["features"]:
        return _draw_top_flange(ax, view, spec)
    vis, hid = view
    dims, feats = spec["dimensions"], spec["features"]
    pockets = feats["pockets"]
    L, W = dims["length"], dims["width"]
    vis_n, vis_t = _outline_trim_split(vis, pockets, SOLID["lw"], SCALE)
    hid_n, hid_t = _outline_trim_split(hid, pockets, HIDDEN["lw"], SCALE)
    plot_edges(ax, vis_n, **SOLID)
    plot_edges(ax, hid_n, **HIDDEN)
    plot_polylines(ax, vis_t, **SOLID)
    plot_polylines(ax, hid_t, **HIDDEN)
    plan = {e["tag"]: e["text"] for e in dimension_plan(spec) if e["view"] == "top"}
    drawn: list[str] = []
    for p in pockets:
        cx, hx, hy = p["x_position"], *pocket_half_xy(p)
        # ISO 128-24 type 04.1 centre lines: dash-dot cross through the
        # pocket centre, extending 3 mm beyond the opening (owner delegation
        # 2026-10-24: the more professional per ISO form — the classic
        # convention draws centre lines slightly past the outline; 3 mm keeps
        # neighbouring centre lines clear of each other at the 40 mm pitch).
        ax.plot([cx - hx - 3, cx + hx + 3], [0, 0], **CENTERLINE)
        ax.plot([cx, cx], [-hy - 3, hy + 3], **CENTERLINE)
        leader(ax, (cx + hx * 0.7, hy * 0.7), (cx, W / 2 + 14), pocket_label(p))
    note = fill_note(feats.get("x_fill"))
    if note:
        ax.text(-L / 2 - 43, W / 2 + 26, note, fontsize=8,
                color="#333333", va="top")
    xs = sorted({p["x_position"] for p in pockets})
    y_dim = -W / 2 - 12
    if "pitch" in plan:
        for a, b in zip(xs, xs[1:]):
            dim_h(ax, a, b, y_dim, plan["pitch"], offset=2, ext0=0, ext1=0)
        drawn.append("pitch")
    dim_h(ax, -L / 2, L / 2, y_dim - 12, plan["length"], offset=2,
          ext0=-W / 2, ext1=-W / 2)
    dim_v(ax, -L / 2 - 14, -W / 2, W / 2, plan["width"],
          offset=2, ext0=-L / 2, ext1=-L / 2)
    drawn += ["length", "width"]
    ax.set_xlim(-L / 2 - 45, L / 2 + 30)
    ax.set_ylim(-W / 2 - 40, W / 2 + 30)
    ax.set_aspect("equal")
    ax.set_title("TOP VIEW", fontsize=10, loc="left")
    ax.axis("off")
    return drawn


def draw_front(ax, view, spec: dict) -> list[str]:
    """Front view: projected edges (pockets appear as hidden lines)."""
    if "flange_plate" in spec["features"]:
        return _draw_front_flange(ax, view, spec)
    vis, hid = view
    plot_edges(ax, vis, **SOLID)
    plot_edges(ax, hid, **HIDDEN)
    dims, feats = spec["dimensions"], spec["features"]
    legs = feats["legs"]
    L, H = dims["length"], dims["height"]
    lh, ld, inset = dims["leg_height"], dims["leg_diameter"], legs["inset"]
    plan = {e["tag"]: e["text"] for e in dimension_plan(spec)
            if e["view"] == "front"}
    leg_x = -L / 2 + inset  # left leg centre
    dim_v(ax, -L / 2 - 14, lh, lh + H, plan["height"],
          offset=2, ext0=-L / 2, ext1=-L / 2)
    leader(ax, (leg_x + ld / 2 + 4, lh / 2), (leg_x + 30, lh / 2 - 6),
           plan["leg_height"])
    leader(ax, (leg_x, lh), (leg_x - 2, -8), plan["leg_inset"])
    leader(ax, (leg_x - ld / 2, lh / 2), (leg_x - 34, lh / 2 + 8),
           plan["leg_diameter"])
    dim_h(ax, -L / 2, L / 2, -24, plan["length"], offset=2, ext0=0, ext1=0)
    ax.set_xlim(-L / 2 - 45, L / 2 + 30)
    ax.set_ylim(-40, lh + H + 12)
    ax.set_aspect("equal")
    ax.set_title("FRONT VIEW", fontsize=10, loc="left")
    ax.axis("off")
    return ["height", "leg_height", "leg_inset", "leg_diameter", "length"]


def draw_end(ax, view, spec: dict) -> list[str]:
    """End view: projected edges + spec-driven dimensions."""
    if "flange_plate" in spec["features"]:
        return _draw_end_flange(ax, view, spec)
    vis, hid = view
    plot_edges(ax, vis, **SOLID)
    plot_edges(ax, hid, **HIDDEN)
    dims = spec["dimensions"]
    W, H = dims["width"], dims["height"]
    lh = dims["leg_height"]
    plan = {e["tag"]: e["text"] for e in dimension_plan(spec) if e["view"] == "end"}
    dim_v(ax, W / 2 + 14, 0, lh + H, plan["total_height"],
          ext0=W / 2, ext1=W / 2)
    dim_h(ax, -W / 2, W / 2, lh + H + 8, plan["width"], offset=2,
          ext0=lh + H, ext1=lh + H)
    ax.set_xlim(-W / 2 - 30, W / 2 + 30)
    ax.set_ylim(-12, lh + H + 22)
    ax.set_aspect("equal")
    ax.set_title("END VIEW", fontsize=10, loc="left")
    ax.axis("off")
    return ["total_height", "width"]


def draw_schedule(ax, pockets: list[dict], x0: float, y0: float) -> None:
    """Pocket schedule table (right side of the sheet)."""
    rows = [["ID", "SHAPE", "SIZE", "DEPTH", "X"]]
    for p in pockets:
        size = (f"Ø{p['diameter']:g}" if p["shape"] == "circle"
                else f"{p['along_x']:g}×{p['along_y']:g}")
        rows.append([p["id"], p["shape"], size, f"{p['depth']:g}",
                     f"{p['x_position']:+g}"])
    cell_w, cell_h = 17, 6
    for r, row in enumerate(rows):
        for c, val in enumerate(row):
            ax.text(x0 + c * cell_w, y0 - r * cell_h, val,
                    fontsize=9,
                    fontweight="bold" if r == 0 else "normal", va="top")
    ax.text(x0, y0 + cell_h * 1.2, "POCKET SCHEDULE", fontsize=10,
            fontweight="bold")


def _snap_data(ax, value: float, axis: str) -> float:
    """Snap an ax data coordinate so it lands on the render pixel grid.

    A line half a pixel off renders antialiased (one fully dark core px +
    two half-intensity edges) and reads as a thinner line than its neighbour
    on a whole-pixel position — the owner caught exactly that on the title
    block's last vertical. Snapping makes equal-width lines render equally.
    """
    fig = ax.figure
    pos = ax.get_position()
    if axis == "x":
        lo, hi = ax.get_xlim()
        span = fig.get_figwidth() * 25.4
        off, size = pos.x0, pos.width
    else:
        lo, hi = ax.get_ylim()
        span = fig.get_figheight() * 25.4
        off, size = pos.y0, pos.height
    paper = (off + (value - lo) / (hi - lo) * size) * span
    px = round(paper * fig.dpi / 25.4)
    frac = (px * 25.4 / fig.dpi / span - off) / size
    return frac * (hi - lo) + lo


def draw_title_block(ax, part: str, spec_path: Path, x0: float, y0: float):
    """Simplified ISO 7200 title block: framed grid with labelled fields
    (TITLE, DWG NO, SCALE, DATE, SOURCE) and the third-angle projection
    symbol (ISO 128-30 B.3) in the last cell. DWG NO is a placeholder —
    the spec carries no drawing number. All grid lines are pixel-snapped
    so equal widths render equally."""
    cols, rows = [40, 26, 26], [8, 8]
    w, h = sum(cols), sum(rows)
    xs = [_snap_data(ax, x0 + sum(cols[:i]), "x") for i in range(len(cols) + 1)]
    ys = [_snap_data(ax, y0 - sum(rows[:i]), "y") for i in range(len(rows) + 1)]
    ax.add_patch(Rectangle((xs[0], ys[-1]), xs[-1] - xs[0], ys[0] - ys[-1],
                           fill=False, lw=1.0, edgecolor="black"))
    for xa in xs[1:-1]:
        ax.plot([xa, xa], [ys[-1], ys[0]], **DIMLINE)
    for ya in ys[1:-1]:
        ax.plot([xs[0], xs[-1]], [ya, ya], **DIMLINE)
    fields = [  # (col, row, label, value) — label above value
        (0, 0, "TITLE", part.upper().replace("_", " ")),
        (1, 0, "DWG NO", "BO-001"),
        (2, 0, "SCALE", "1:2"),
        (0, 1, "DATE", date.today().isoformat()),
        (1, 1, "SOURCE", spec_path.name),
    ]
    for col, row, label, value in fields:
        cx = xs[col] + 2
        top = ys[row]
        ax.text(cx, top - 1.5, label, fontsize=6,
                color="#555555", va="top")
        ax.text(cx, top - 5, value, fontsize=9,
                fontweight="bold", va="top")
    # third-angle symbol instead of text in the last cell
    draw_projection_symbol(ax, xs[2] + 12, ys[1] - 4, 6)


# ---------------------------------------------------------------- sheet


def draw_sheet_frame(fig):
    """ISO 5457 sheet furniture: frame with a 10 mm margin.

    Centring marks are OMITTED: they are optional per ISO 5457 (the sheet is
    a generated PDF, not a preprinted trimmed sheet) and their collision
    surface cost the owner two review rounds. Declared in the manifest.
    """
    ax = fig.add_axes([0, 0, 1, 1])
    ax.axis("off")
    ax.set_xlim(0, 297)
    ax.set_ylim(0, 210)
    ax.add_patch(Rectangle((10, 10), 277, 190, fill=False, lw=1.0,
                           edgecolor="black"))
    return ax


def frame_collision_violations(fig, frame_ax) -> list[str]:
    """Nothing may touch the ISO 5457 frame (10/287 × 10/200, 2 mm clearance).

    Mechanical layout gate over EVERY drawn element — texts, lines, patches
    and annotation arrows (the frame axes itself excluded) — converted to
    paper mm and checked against the frame lines minus a 2 mm clearance.
    Catches the 'element running into the frame' defect class (texts, the
    projection symbol, anything) that geometry probes cannot see.
    """
    from matplotlib.lines import Line2D
    from matplotlib.patches import Patch
    from matplotlib.spines import Spine
    from matplotlib.text import Text
    renderer = fig.canvas.get_renderer()
    px_mm = 25.4 / fig.dpi
    # Axes/figure background patches are not content — excluded.
    background = {fig.patch} | {ax.patch for ax in fig.axes}
    # Tick labels of axis-off axes are never drawn (only their extents are
    # resolved during the tight-bbox pass) — excluded from the gate.
    skip = set()
    for ax in fig.axes:
        if ax is frame_ax or not ax.axison:
            for axis in (ax.xaxis, ax.yaxis):
                for tick in axis.get_major_ticks() + axis.get_minor_ticks():
                    skip.update((tick.label1, tick.label2,
                                 tick.tick1line, tick.tick2line, tick.gridline))
    violations = []
    for obj in fig.findobj(match=lambda o: isinstance(o, (Text, Line2D, Patch))
                           and not isinstance(o, Spine)):
        if (getattr(obj, "axes", None) is frame_ax or obj in skip
                or obj in background or not obj.get_visible()):
            continue
        if isinstance(obj, Text) and not (obj.get_text() or "").strip():
            continue
        try:
            bb = obj.get_window_extent(renderer=renderer)
        except Exception:
            continue
        if bb.width <= 0 and bb.height <= 0:
            continue
        x0, x1 = bb.x0 * px_mm, bb.x1 * px_mm
        y0, y1 = bb.y0 * px_mm, bb.y1 * px_mm
        if x0 < 12 or x1 > 285 or y0 < 12 or y1 > 198:
            label = obj.get_text()[:40] if isinstance(obj, Text) else type(obj).__name__
            violations.append(
                f"{type(obj).__name__} '{label}' bbox mm "
                f"({x0:.1f},{y0:.1f})..({x1:.1f},{y1:.1f}) breaks frame clearance")
    return violations


def text_geometry_collisions(fig, views: dict, view_axes: dict,
                             clearance: float = 2.0) -> list[str]:
    """Dimension/label texts must keep clearance from the projected geometry.

    Samples every projected edge of each view (≈1 mm step) and probes every
    data-transformed Text of the view's axes (bbox corners, edge midpoints,
    centre, transformed back to data coordinates) against the sample cloud;
    a closer approach than `clearance` mm is a violation. Catches the
    'dimension number overlaps the part outline' defect class (owner
    2026-10-28: Ø25, 28.3; the gate then caught Ø90 as well) that the frame
    gate cannot see — that one checks the sheet frame only. Leader ARROWS
    legitimately touch the geometry and are not Texts; the axes title and
    any text not placed in data coordinates are excluded.
    """
    from matplotlib.text import Annotation, Text
    violations = []
    for name, ax in view_axes.items():
        vis, hid = views[name]
        pts = []
        for e in list(vis) + list(hid):
            n = min(96, max(2, math.ceil(e.length / 1.0) + 1))
            pts += [(v.X, v.Y) for v in (e @ (i / (n - 1)) for i in range(n))]
        if not pts:
            continue
        inv = ax.transData.inverted()
        renderer = fig.canvas.get_renderer()
        for obj in ax.texts:
            if (not isinstance(obj, Text)
                    or not (obj.get_text() or "").strip()
                    or not obj.get_visible()
                    or not obj.get_transform().contains_branch(ax.transData)):
                continue
            # an Annotation's window extent unions its arrow patch — the
            # arrow legitimately touches the geometry it points at, so the
            # clearance is judged on the text alone
            bb = (Text.get_window_extent(obj, renderer=renderer)
                  if isinstance(obj, Annotation)
                  else obj.get_window_extent(renderer=renderer))
            probes = [
                (bb.x0, bb.y0), (bb.x0, bb.y1), (bb.x1, bb.y0), (bb.x1, bb.y1),
                ((bb.x0 + bb.x1) / 2, (bb.y0 + bb.y1) / 2),
                ((bb.x0 + bb.x1) / 2, bb.y0), ((bb.x0 + bb.x1) / 2, bb.y1),
                (bb.x0, (bb.y0 + bb.y1) / 2), (bb.x1, (bb.y0 + bb.y1) / 2),
            ]
            for px, py in probes:
                dx, dy = inv.transform((px, py))
                d = min(math.hypot(dx - qx, dy - qy) for qx, qy in pts)
                if d < clearance:
                    violations.append(
                        f"{name}: text '{obj.get_text()[:24]}' approaches "
                        f"geometry to {d:.2f} mm (< {clearance:g})")
                    break
    return violations


# ---------------------------------------------------------------- main


def main() -> None:
    spec_path = Path(sys.argv[1])
    out_prefix = (Path(sys.argv[2]) if len(sys.argv) > 2
                  else spec_path.parent / "visuals" / "drawing")
    spec = yaml.safe_load(spec_path.read_text(encoding="utf-8"))
    module = load_model_module(spec_path)
    part = module.build(spec)
    dims = spec["dimensions"]

    views, suppression = project_drawing_views(part, spec, module)
    probes = probe_views(views, spec)

    fig = plt.figure(figsize=(11.69, 8.27), dpi=150)  # A4 landscape
    frame_ax = draw_sheet_frame(fig)
    fig.suptitle(
        f"{spec['part']} — dimensioned drawing "
        "(views: projected from model, dimensions: from spec)",
        fontsize=12, fontweight="bold", y=0.92,
    )
    ax_top = fig.add_axes([0.05, 0.52, 0.60, 0.35])
    ax_front = fig.add_axes([0.05, 0.12, 0.60, 0.32])
    ax_end = fig.add_axes([0.70, 0.12, 0.22, 0.32])
    ax_info = fig.add_axes([0.70, 0.47, 0.25, 0.40])

    drawn = {
        "top": draw_top(ax_top, views["top"], spec),
        "front": draw_front(ax_front, views["front"], spec),
        "end": draw_end(ax_end, views["end"], spec),
    }
    # the draw functions must realise the full dimension plan — fail loud
    for view, tags in drawn.items():
        want = {e["tag"] for e in dimension_plan(spec) if e["view"] == view}
        if set(tags) != want:
            raise RuntimeError(
                f"dimension plan drift in {view}: drawn={sorted(tags)} "
                f"plan={sorted(want)}")

    # ISO 5455: every view at the declared 1:2 scale — data range from the
    # axes paper size, centred on the content midpoints the draw functions set
    apply_scale(fig, ax_top, (0.05, 0.52, 0.60, 0.35))
    apply_scale(fig, ax_front, (0.05, 0.12, 0.60, 0.32))
    apply_scale(fig, ax_end, (0.70, 0.12, 0.22, 0.32))

    ax_info.axis("off")
    ax_info.set_xlim(-2, 93)  # 93: right frame edge must NOT sit on the axes
    # edge — matplotlib clips at the axes and would shave half the line width
    ax_info.set_ylim(-64, 10)  # schedule title (y=7.2) stays inside the axes
    if "pockets" in spec["features"]:
        draw_schedule(ax_info, spec["features"]["pockets"], 0.0, 0.0)
    draw_title_block(ax_info, spec["part"], spec_path, 0.0, -46)

    manifest = build_manifest(views, probes, spec, spec_path)
    manifest["annotations"]["drawn_tags"] = drawn
    manifest["rib_edge_suppression"] = {
        "rule": ("web-related edges of homogeneous material are dropped per "
                 "view: embedded rib ends (wholly in the walls) and web-web "
                 "crossing seams; cylinder seam edges are dropped in the end "
                 "view (owner 2026-10-24). Wall junctions — edges lying on "
                 "the pocket wall — are real concave edges and are kept "
                 "(drawn dashed, strict ISO, owner 2026-10-24). Void-facing "
                 "floor/bottom chords are kept in every view"),
        **suppression,
    }

    violations = frame_collision_violations(fig, frame_ax)
    for v in violations:
        print(f"PROBE FAILED: {v}", file=sys.stderr)
    manifest["sheet"]["frame_clearance_ok"] = not violations

    text_violations = text_geometry_collisions(
        fig, views, {"top": ax_top, "front": ax_front, "end": ax_end})
    for v in text_violations:
        print(f"PROBE FAILED: {v}", file=sys.stderr)
    manifest["sheet"]["text_collision_ok"] = not text_violations

    failed = [
        f"{pid}: opening" for pid, pr in probes["pockets"].items()
        if not pr["top_opening_position_size_ok"]
    ] + [
        f"{pid}: ribs" for pid, pr in probes["x_fill"].items()
        if pr["expected"] and pr["diag_edges_in_top"] < 2
    ] + [
        f"outline:{name}" for name, pr in probes["outline"].items()
        if not (pr["span_x_ok"] and pr["span_y_ok"])
    ]
    for warning in failed:
        print(f"PROBE FAILED: {warning}", file=sys.stderr)

    out_prefix.parent.mkdir(parents=True, exist_ok=True)
    for ext in ("png", "svg"):
        out = out_prefix.with_name(f"{out_prefix.name}.{ext}")
        fig.savefig(out, bbox_inches="tight")
        print(f"rendered {out}")
    manifest_out = out_prefix.with_name(f"{out_prefix.name}.manifest.json")
    manifest_out.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8")
    print(f"rendered {manifest_out}")


if __name__ == "__main__":
    main()