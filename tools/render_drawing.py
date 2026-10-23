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
The annotation plan assumes the spec carries pockets and legs (current parts).
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


def dimension_plan(spec: dict) -> list[dict]:
    """The complete set of dimensions the drawing must carry.

    Single source of truth for WHAT is dimensioned (view + tag + text); the
    draw functions place these by tag, the manifest records them and the
    completeness test checks the plan covers every spec dimension key.
    """
    dims, feats = spec["dimensions"], spec["features"]
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


def load_builder(spec_path: Path):
    """Resolve the part's model builder by convention: models/<part>.build."""
    root = Path(__file__).resolve().parents[1]
    if str(root) not in sys.path:  # CLI run: sys.path[0] is tools/, not root
        sys.path.insert(0, str(root))
    module = importlib.import_module(f"models.{spec_path.parent.name}")
    return module.build


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
            off = closed_dash_offset(e, style.get("linestyle"))
            if off is not None:
                st = dict(style, linestyle=(off, style["linestyle"][1]))
        n = min(max_points, max(2, math.ceil(e.length / step) + 1))
        pts = [(v.X, v.Y) for v in (e @ (i / (n - 1)) for i in range(n))]
        xs, ys = zip(*pts)
        ax.plot(xs, ys, **st)
    return len(edges)


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
    pockets = feats["pockets"]
    leg_h = dims["leg_height"]
    top_z = dims["height"] + leg_h
    vis_top, hid_top = views["top"]
    vis_front, hid_front = views["front"]
    vis_end, hid_end = views["end"]
    probes: dict = {"pockets": {}, "x_fill": {}, "legs": {}, "outline": {}}

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
            "centring_marks": "centring marks: 4 × 10 mm strokes at the side midpoints",
        },
        "line_styles": {
            "visible": "ISO 128-24 type 01.2, continuous wide (0.7 mm)",
            "hidden": "ISO 128-24 type 02.1, dashed narrow (0.35 mm, 12d/3d)",
            "centre_lines": "ISO 128-24 type 04.1, long-dashed dotted narrow",
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
                for p in spec["features"]["pockets"]
            ],
            "schedule_rows": len(spec["features"]["pockets"]) + 1,
            "fill_note": fill_note(spec["features"].get("x_fill")),
        },
    }


# ---------------------------------------------------------------- views


def draw_top(ax, view, spec: dict) -> list[str]:
    """Top view: projected edges + spec-driven labels, note and dimensions."""
    vis, hid = view
    plot_edges(ax, vis, **SOLID)
    plot_edges(ax, hid, **HIDDEN)
    dims, feats = spec["dimensions"], spec["features"]
    pockets = feats["pockets"]
    L, W = dims["length"], dims["width"]
    plan = {e["tag"]: e["text"] for e in dimension_plan(spec) if e["view"] == "top"}
    drawn: list[str] = []
    for p in pockets:
        cx, hx, hy = p["x_position"], *pocket_half_xy(p)
        # ISO 128-24 type 04.1 centre lines: dash-dot cross through the
        # centre, extending ~4 mm beyond the opening
        ax.plot([cx - hx - 4, cx + hx + 4], [0, 0], **CENTERLINE)
        ax.plot([cx, cx], [-hy - 4, hy + 4], **CENTERLINE)
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
    dim_v(ax, -L / 2 - 14, -W / 2, W / 2, plan["width"], ext0=-L / 2, ext1=-L / 2)
    drawn += ["length", "width"]
    ax.set_xlim(-L / 2 - 45, L / 2 + 30)
    ax.set_ylim(-W / 2 - 40, W / 2 + 30)
    ax.set_aspect("equal")
    ax.set_title("TOP VIEW", fontsize=10, loc="left")
    ax.axis("off")
    return drawn


def draw_front(ax, view, spec: dict) -> list[str]:
    """Front view: projected edges (pockets appear as hidden lines)."""
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
          ext0=-L / 2, ext1=-L / 2)
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


def draw_title_block(ax, part: str, spec_path: Path, x0: float, y0: float):
    """Simplified ISO 7200 title block: framed grid with labelled fields
    (TITLE, DWG NO, SCALE, DATE, SOURCE) and the third-angle projection
    symbol (ISO 128-30 B.3) in the last cell. DWG NO is a placeholder —
    the spec carries no drawing number."""
    cols, rows = [40, 26, 26], [8, 8]
    w, h = sum(cols), sum(rows)
    ax.add_patch(Rectangle((x0, y0 - h), w, h, fill=False, lw=1.0,
                           edgecolor="black"))
    xa = x0
    for c in cols[:-1]:
        xa += c
        ax.plot([xa, xa], [y0 - h, y0], **DIMLINE)
    ya = y0
    for r in rows[:-1]:
        ya -= r
        ax.plot([x0, x0 + w], [ya, ya], **DIMLINE)
    fields = [  # (col, row, label, value) — label above value
        (0, 0, "TITLE", part.upper().replace("_", " ")),
        (1, 0, "DWG NO", "BO-001"),
        (2, 0, "SCALE", "1:2"),
        (0, 1, "DATE", date.today().isoformat()),
        (1, 1, "SOURCE", spec_path.name),
    ]
    for col, row, label, value in fields:
        cx = x0 + 2 + sum(cols[:col])
        top = y0 - sum(rows[:row])
        ax.text(cx, top - 1.5, label, fontsize=6,
                color="#555555", va="top")
        ax.text(cx, top - 5, value, fontsize=9,
                fontweight="bold", va="top")
    # third-angle symbol instead of text in the last cell
    draw_projection_symbol(ax, x0 + cols[0] + cols[1] + 12, y0 - rows[0] - 4, 6)


# ---------------------------------------------------------------- sheet


def draw_sheet_frame(fig) -> None:
    """ISO 5457 sheet furniture: frame with a 10 mm margin and centring
    marks (10 mm strokes at the midpoints of the four sides).

    Convention note: the full ISO 5457 text is not in the repo — the 10 mm
    margin and inner centring marks are declared as conventions in the
    manifest, same as the line styles.
    """
    ax = fig.add_axes([0, 0, 1, 1])
    ax.axis("off")
    ax.set_xlim(0, 297)
    ax.set_ylim(0, 210)
    ax.add_patch(Rectangle((10, 10), 277, 190, fill=False, lw=1.0,
                           edgecolor="black"))
    cx, cy = 297 / 2, 210 / 2
    ax.plot([cx, cx], [10, 20], **DIMLINE)
    ax.plot([cx, cx], [190, 200], **DIMLINE)
    ax.plot([10, 20], [cy, cy], **DIMLINE)
    ax.plot([277, 287], [cy, cy], **DIMLINE)


# ---------------------------------------------------------------- main


def main() -> None:
    spec_path = Path(sys.argv[1])
    out_prefix = (Path(sys.argv[2]) if len(sys.argv) > 2
                  else spec_path.parent / "visuals" / "drawing")
    spec = yaml.safe_load(spec_path.read_text(encoding="utf-8"))
    part = load_builder(spec_path)(spec)
    dims = spec["dimensions"]

    views = project_views(part, dims)
    probes = probe_views(views, spec)

    fig = plt.figure(figsize=(11.69, 8.27), dpi=150)  # A4 landscape
    draw_sheet_frame(fig)
    fig.suptitle(
        f"{spec['part']} — dimensioned drawing "
        "(views: projected from model, dimensions: from spec)",
        fontsize=12, fontweight="bold", y=0.935,
    )
    ax_top = fig.add_axes([0.05, 0.55, 0.60, 0.38])
    ax_front = fig.add_axes([0.05, 0.12, 0.60, 0.32])
    ax_end = fig.add_axes([0.70, 0.12, 0.22, 0.32])
    ax_info = fig.add_axes([0.70, 0.50, 0.25, 0.43])

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
    apply_scale(fig, ax_top, (0.05, 0.55, 0.60, 0.38))
    apply_scale(fig, ax_front, (0.05, 0.12, 0.60, 0.32))
    apply_scale(fig, ax_end, (0.70, 0.12, 0.22, 0.32))

    ax_info.axis("off")
    ax_info.set_xlim(-2, 92)
    ax_info.set_ylim(-64, 4)  # title block: 2 rows x 8 from y=-46 -> bottom -62
    draw_schedule(ax_info, spec["features"]["pockets"], 0.0, 0.0)
    draw_title_block(ax_info, spec["part"], spec_path, 0.0, -46)

    manifest = build_manifest(views, probes, spec, spec_path)
    manifest["annotations"]["drawn_tags"] = drawn

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