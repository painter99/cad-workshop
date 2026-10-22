#!/usr/bin/env python3
"""Generate a dimensioned technical drawing from a part spec.

Reads ``specs/<part>/spec.yaml`` and renders a third-angle projection
(top / front / end views) with dimension lines and a pocket schedule,
using matplotlib only (headless, no CAD viewer). X-web fill
(spec ``features.x_fill``) is drawn in the top view and annotated; rib
bars are clipped to the pocket openings analytically, not by renderer
clip paths.

Usage:
    python tools/render_drawing.py specs/brush_organizer/spec.yaml \
        [out_prefix]

Output: <out_prefix>_drawing.png (and .svg)

The drawing is generated from the spec, never from the model — it shows
the *intent* (approved dimensions), while the previews in drafts/ show the
*measured result*. Differences between the two are what review is for.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import yaml
from matplotlib.patches import Circle, Polygon, Rectangle

MM = 1.0  # data units are millimeters

# ---------------------------------------------------------------- helpers


def dim_h(ax, x0, x1, y, text, offset=6, color="#1a1a1a"):
    """Horizontal dimension line with arrows, extension ticks and label."""
    ax.annotate(
        "", xy=(x0, y), xytext=(x1, y),
        arrowprops=dict(arrowstyle="<|-|>", color=color, shrinkA=0, shrinkB=0,
                        mutation_scale=10),
    )
    ax.text((x0 + x1) / 2, y + offset, text, ha="center", va="bottom",
            fontsize=7, color=color)


def dim_v(ax, x, y0, y1, text, offset=6, color="#1a1a1a"):
    """Vertical dimension line with arrows and label."""
    ax.annotate(
        "", xy=(x, y0), xytext=(x, y1),
        arrowprops=dict(arrowstyle="<|-|>", color=color, shrinkA=0, shrinkB=0,
                        mutation_scale=10),
    )
    ax.text(x + offset, (y0 + y1) / 2, text, ha="left", va="center",
            fontsize=7, rotation=90, color=color)


def leader(ax, xy, xytext, text, color="#1a1a1a"):
    ax.annotate(
        text, xy=xy, xytext=xytext, fontsize=6.5, color=color,
        arrowprops=dict(arrowstyle="->", color=color, lw=0.6),
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


def _rib_bar(cx: float, cy: float, half_len: float, width: float,
             angle_deg: float) -> list[tuple[float, float]]:
    """Corners of one rib bar: a rectangle centered on (cx, cy), rotated."""
    a = math.radians(angle_deg)
    ux, uy = math.cos(a), math.sin(a)
    vx, vy = -uy, ux
    hl, hw = half_len, width / 2
    return [
        (cx + hl * ux + hw * vx, cy + hl * uy + hw * vy),
        (cx - hl * ux + hw * vx, cy - hl * uy + hw * vy),
        (cx - hl * ux - hw * vx, cy - hl * uy - hw * vy),
        (cx + hl * ux - hw * vx, cy + hl * uy - hw * vy),
    ]


def _clip_poly_rect(points: list[tuple[float, float]],
                    hx: float, hy: float) -> list[tuple[float, float]]:
    """Clip a polygon against the rect (-hx..hx, -hy..hy), Sutherland–Hodgman.

    Analytic and renderer-independent: matplotlib 3.11 silently drops
    ``set_clip_path`` with a Rectangle patch (verified: the clip ends up
    None), so rib bars must be clipped by geometry, not by the renderer.
    """
    def isect_x(p, q, x):
        t = (x - p[0]) / (q[0] - p[0])
        return (x, p[1] + t * (q[1] - p[1]))

    def isect_y(p, q, y):
        t = (y - p[1]) / (q[1] - p[1])
        return (p[0] + t * (q[0] - p[0]), y)

    pts = points
    for inside, isect in (
        (lambda v: v[0] >= -hx, lambda p, q: isect_x(p, q, -hx)),
        (lambda v: v[0] <= hx, lambda p, q: isect_x(p, q, hx)),
        (lambda v: v[1] >= -hy, lambda p, q: isect_y(p, q, -hy)),
        (lambda v: v[1] <= hy, lambda p, q: isect_y(p, q, hy)),
    ):
        out = []
        n = len(pts)
        for i in range(n):
            cur, prev = pts[i], pts[i - 1]
            c_in, p_in = inside(cur), inside(prev)
            if c_in:
                if not p_in:
                    out.append(isect(prev, cur))
                out.append(cur)
            elif p_in:
                out.append(isect(prev, cur))
        pts = out
        if not pts:
            return []
    return pts


def draw_x_fill(ax, pockets: list[dict], x_fill: dict | None) -> None:
    """X-web fill in the top view: two diagonal rib bars (±45°, rib_width
    wide) per pocket. Bars are clipped to the pocket opening analytically;
    the wall embed is hidden inside the wall and is not drawn."""
    if not x_fill or x_fill.get("style", "web_floor") != "web_floor":
        return
    rib_w = x_fill.get("rib_width", 4)
    if x_fill.get("under", "all") == "deep_only":
        deepest = max(p["depth"] for p in pockets)
        targets = [p for p in pockets if p["depth"] == deepest]
    else:
        targets = pockets
    for p in targets:
        cx = p["x_position"]
        if p["shape"] == "circle":
            r = p["diameter"] / 2
            # end-cap chord fully inside the circular wall (the sliver
            # between chord and arc is < 0.2 mm, below drawing precision)
            half = math.sqrt(max(r * r - (rib_w / 2) ** 2, 0.0))
            bars = [_rib_bar(cx, 0, half, rib_w, a) for a in (45, -45)]
        else:
            hx, hy = pocket_half_xy(p)
            half = min(hx, hy) / math.cos(math.pi / 4)
            bars = []
            for a in (45, -45):
                quad = _rib_bar(cx, 0, half, rib_w, a)
                quad = _clip_poly_rect([(x - cx, y) for x, y in quad], hx, hy)
                bars.append([(x + cx, y) for x, y in quad])
        for quad in bars:
            if len(quad) >= 3:
                ax.add_patch(Polygon(quad, fill=False, lw=0.7,
                                     edgecolor="black"))


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


# ---------------------------------------------------------------- views


def draw_top(ax, dims: dict, pockets: list[dict],
             x_fill: dict | None = None) -> None:
    L, W = dims["length"], dims["width"]
    ax.add_patch(Rectangle((-L / 2, -W / 2), L, W, fill=False, lw=1.4,
                           edgecolor="black"))
    for p in pockets:
        cx, cy = p["x_position"], 0
        hx, hy = pocket_half_xy(p)
        if p["shape"] == "circle":
            ax.add_patch(Circle((cx, cy), p["diameter"] / 2, fill=False,
                                lw=0.9, edgecolor="black"))
            ax.plot([cx], [cy], marker="+", color="black", ms=5, mew=0.7)
        else:
            ax.add_patch(Rectangle((cx - hx, cy - hy), 2 * hx, 2 * hy,
                                   fill=False, lw=0.9, edgecolor="black"))
            ax.plot([cx], [cy], marker="+", color="black", ms=5, mew=0.7)
        leader(ax, (cx + hx * 0.7, cy + hy * 0.7),
               (cx, W / 2 + 14), pocket_label(p))
    draw_x_fill(ax, pockets, x_fill)
    note = fill_note(x_fill)
    if note:
        ax.text(-L / 2 - 43, W / 2 + 26, note, fontsize=5.5,
                family="monospace", color="#333333", va="top")
    # X positions of pocket centers
    xs = sorted({p["x_position"] for p in pockets})
    y_dim = -W / 2 - 12
    for a, b in zip(xs, xs[1:]):
        dim_h(ax, a, b, y_dim, f"{b - a:g}", offset=2)
    dim_h(ax, -L / 2, L / 2, y_dim - 12, f"{L:g}", offset=2)
    dim_v(ax, -L / 2 - 14, -W / 2, W / 2, f"{W:g}")
    ax.set_xlim(-L / 2 - 45, L / 2 + 30)
    ax.set_ylim(-W / 2 - 40, W / 2 + 30)
    ax.set_aspect("equal")
    ax.set_title("TOP VIEW", fontsize=8, loc="left")
    ax.axis("off")


def draw_front(ax, dims: dict, legs: dict) -> None:
    L, H = dims["length"], dims["height"]
    lh, ld, inset = legs["height"], dims["leg_diameter"], legs["inset"]
    y0 = 0  # bottom of legs
    ax.add_patch(Rectangle((-L / 2, lh), L, H, fill=False, lw=1.4,
                           edgecolor="black"))
    # legs (side silhouette): two visible cylinders at the corners
    for cx in (-L / 2 + inset, L / 2 - inset):
        ax.add_patch(Rectangle((cx - ld / 2, y0), ld, lh, fill=False, lw=0.9,
                               edgecolor="black"))
    dim_v(ax, -L / 2 - 14, lh, lh + H, f"{H:g}")
    leader(ax, (-L / 2 + inset + ld / 2 + 4, lh / 2),
           (-L / 2 + inset + 30, lh / 2 - 6), f"{lh:g}")
    leader(ax, (-L / 2 + inset, lh), (-L / 2 + inset - 2, -8), f"{inset:g}")
    dim_h(ax, -L / 2, L / 2, -24, f"{L:g}", offset=2)
    ax.set_xlim(-L / 2 - 45, L / 2 + 30)
    ax.set_ylim(-40, lh + H + 12)
    ax.set_aspect("equal")
    ax.set_title("FRONT VIEW", fontsize=8, loc="left")
    ax.axis("off")


def draw_end(ax, dims: dict, legs: dict) -> None:
    W, H = dims["width"], dims["height"]
    lh, ld, inset = legs["height"], dims["leg_diameter"], legs["inset"]
    ax.add_patch(Rectangle((-W / 2, lh), W, H, fill=False, lw=1.4,
                           edgecolor="black"))
    for cx in (-W / 2 + inset, W / 2 - inset):
        ax.add_patch(Rectangle((cx - ld / 2, 0), ld, lh, fill=False, lw=0.9,
                               edgecolor="black"))
    dim_v(ax, W / 2 + 14, 0, lh + H, f"{lh + H:g}")
    dim_h(ax, -W / 2, W / 2, lh + H + 8, f"{W:g}", offset=2)
    ax.set_xlim(-W / 2 - 30, W / 2 + 30)
    ax.set_ylim(-12, lh + H + 22)
    ax.set_aspect("equal")
    ax.set_title("END VIEW", fontsize=8, loc="left")
    ax.axis("off")


def draw_schedule(ax, pockets: list[dict], x0: float, y0: float) -> None:
    """Pocket schedule table (right side of the sheet)."""
    rows = [["ID", "SHAPE", "SIZE", "DEPTH", "X"]]
    for p in pockets:
        size = (f"Ø{p['diameter']:g}" if p["shape"] == "circle"
                else f"{p['along_x']:g}×{p['along_y']:g}")
        rows.append([p["id"], p["shape"], size, f"{p['depth']:g}",
                     f"{p['x_position']:+g}"])
    cell_w, cell_h = 16, 6
    for r, row in enumerate(rows):
        for c, val in enumerate(row):
            ax.text(x0 + c * cell_w, y0 - r * cell_h, val,
                    fontsize=6.5, family="monospace",
                    fontweight="bold" if r == 0 else "normal", va="top")
    ax.text(x0, y0 + cell_h * 1.2, "POCKET SCHEDULE", fontsize=7,
            fontweight="bold")


def draw_title_block(ax, part: str, spec_path: Path, x0: float, y0: float):
    lines = [
        f"PART: {part}",
        "UNITS: mm   PROJECTION: third angle",
        f"SOURCE: {spec_path.name} (authoritative)",
        "DRAWING: generated from spec, not measured",
    ]
    for i, line in enumerate(lines):
        ax.text(x0, y0 - i * 6, line, fontsize=6.5, family="monospace")


# ---------------------------------------------------------------- main


def main() -> None:
    spec_path = Path(sys.argv[1])
    out_prefix = Path(sys.argv[2]) if len(sys.argv) > 2 else spec_path.with_suffix("")
    spec = yaml.safe_load(spec_path.read_text())
    part = spec["part"]
    dims = spec["dimensions"]
    feats = spec["features"]
    pockets = feats["pockets"]
    legs = feats["legs"]

    fig = plt.figure(figsize=(11.69, 8.27), dpi=150)  # A4 landscape
    fig.suptitle(f"{part} — dimensioned drawing (from spec)",
                 fontsize=10, fontweight="bold")

    # top view occupies the upper-left area, front below, end right of front
    ax_top = fig.add_axes([0.05, 0.55, 0.60, 0.38])
    ax_front = fig.add_axes([0.05, 0.12, 0.60, 0.32])
    ax_end = fig.add_axes([0.70, 0.12, 0.22, 0.32])
    ax_info = fig.add_axes([0.70, 0.50, 0.25, 0.43])

    draw_top(ax_top, dims, pockets, feats.get("x_fill"))
    draw_front(ax_front, dims, legs)
    draw_end(ax_end, dims, legs)

    ax_info.axis("off")
    ax_info.set_xlim(-2, 92)
    ax_info.set_ylim(-58, 4)
    draw_schedule(ax_info, pockets, 0.0, 0.0)
    draw_title_block(ax_info, part, spec_path, 0.0, -46)

    out_prefix.parent.mkdir(parents=True, exist_ok=True)
    for ext in ("png", "svg"):
        out = out_prefix.with_name(f"{out_prefix.name}.{ext}")
        fig.savefig(out, bbox_inches="tight")
        print(f"rendered {out}")


if __name__ == "__main__":
    main()