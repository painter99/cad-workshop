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
    INK_BIAS_V,
    _snap_data,
    build_manifest,
    closed_dash_offset,
    draw_title_block,
    frame_collision_violations,
    narrow_label_violations,
    probe_views,
    project_views,
    small_circle_solid,
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
    assert "omitted" in manifest["sheet"]["centring_marks"]


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


def test_regenerated_manifest_records_frame_clearance_pass():
    """The versioned manifest must carry the mechanical layout gate result."""
    import json
    m = json.loads((REPO / "specs" / "brush_organizer" / "visuals"
                    / "drawing.manifest.json").read_text(encoding="utf-8"))
    assert m["sheet"]["frame_clearance_ok"] is True, (
        "frame collision probe failed — layout must be fixed, not asserted")
    assert "omitted" in m["sheet"]["centring_marks"], (
        "centring marks are optional per ISO 5457 and were removed as a "
        "collision surface — they must not quietly return")


def test_frame_collision_violations_catches_lines_and_patches():
    """The gate covers every drawn element, not only texts (owner found a
    patch/symbol colliding with sheet furniture that the text-only gate
    missed)."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig = plt.figure(figsize=(11.69, 8.27), dpi=150)
    frame_ax = fig.add_axes([0, 0, 1, 1])
    frame_ax.set_xlim(0, 297)
    frame_ax.set_ylim(0, 210)
    ax = fig.add_axes([0.1, 0.1, 0.5, 0.5])
    ax.plot([0, 1], [0.98, 0.98])  # line crossing the top frame area
    ax.add_patch(plt.Rectangle((0.5, 0.97), 0.1, 0.05, fill=False))  # patch
    viol = frame_collision_violations(fig, frame_ax)
    assert len(viol) >= 2, f"gate must catch line+patch collisions, got {viol}"


def test_text_geometry_collisions_catches_and_clears():
    """The text-geometry clearance gate: a text ON a line violates, a text
    2 mm clear of it does not."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    from tools.render_drawing import text_geometry_collisions

    class FakeV:

        def __init__(self, x, y):
            self.X, self.Y = x, y

    class FakeEdge:  # horizontal 10 mm line at y = 0
        length = 10.0

        def __matmul__(self, t):
            return FakeV(-5.0 + 10.0 * t, 0.0)

    fig = plt.figure(figsize=(4, 3), dpi=100)
    ax = fig.add_axes([0.1, 0.1, 0.8, 0.8])
    ax.set_xlim(-10, 10)
    ax.set_ylim(-10, 10)
    fig.canvas.draw()
    ax.text(0, 0, "ON", ha="center", va="center")
    ax.text(0, 5, "CLEAR", ha="center", va="center")
    # a leader whose ARROW touches the line: judged on the text alone
    ax.annotate("LEADER", xy=(0, 0), xytext=(6, 5),
                arrowprops=dict(arrowstyle="->"))
    try:
        violations = text_geometry_collisions(
            fig, {"top": ([FakeEdge()], [])}, {"top": ax})
        assert any("'ON'" in v for v in violations), violations
        assert not any("'CLEAR'" in v or "'LEADER'" in v
                       for v in violations), violations
    finally:
        plt.close(fig)


def test_narrow_label_gate_passes_verified_placement_and_catches_drift():
    """The 12 mm plate-thickness label saga as a gate: the verified
    placement (box centre on the dim line axis + ink bias, beyond the
    arrowhead tail) passes; the detached (3 mm off-axis) and the squeezed
    (inside the arrow zone) placements fail."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig = plt.figure(figsize=(6, 6), dpi=150)
    ax = fig.add_axes([0.1, 0.1, 0.8, 0.8])
    ax.set_xlim(-10, 10)
    ax.set_ylim(-10, 30)
    good = ax.text(INK_BIAS_V, 21, "12", fontsize=10, rotation=90,
                   ha="center", va="bottom")
    off_axis = ax.text(3 + INK_BIAS_V, 21, "12", fontsize=10, rotation=90,
                       ha="center", va="bottom")
    squeezed = ax.text(INK_BIAS_V, 18, "12", fontsize=10, rotation=90,
                       ha="center", va="bottom")
    records = [
        {"ax": ax, "text": good, "kind": "v", "axis": 0.0,
         "line_pos": 12.0, "arrow_far": 17.0},
        {"ax": ax, "text": off_axis, "kind": "v", "axis": 0.0,
         "line_pos": 12.0, "arrow_far": 17.0},
        {"ax": ax, "text": squeezed, "kind": "v", "axis": 0.0,
         "line_pos": 12.0, "arrow_far": 17.0},
    ]
    fig.canvas.draw()
    try:
        violations = narrow_label_violations(fig, records)
        assert len(violations) == 2, violations
        assert "off the dim line axis" in violations[0], violations
        assert "inside the arrow" in violations[1], violations
    finally:
        plt.close(fig)


def test_narrow_label_gate_horizontal_label_centered_above_line():
    """h-kind convention (the keyway 8): the label centred on the span
    midpoint and above the dim line; an off-mid or on-the-line placement
    fails."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig = plt.figure(figsize=(6, 6), dpi=150)
    ax = fig.add_axes([0.1, 0.1, 0.8, 0.8])
    ax.set_xlim(-10, 10)
    ax.set_ylim(-10, 30)
    good = ax.text(0, 2, "8", fontsize=10, ha="center", va="bottom")
    off_mid = ax.text(2, 2, "8", fontsize=10, ha="center", va="bottom")
    on_line = ax.text(0, 0.5, "8", fontsize=10, ha="center", va="bottom")
    records = [
        {"ax": ax, "text": good, "kind": "h", "axis": 0.0,
         "line_pos": 0.0, "arrow_far": None},
        {"ax": ax, "text": off_mid, "kind": "h", "axis": 0.0,
         "line_pos": 0.0, "arrow_far": None},
        {"ax": ax, "text": on_line, "kind": "h", "axis": 0.0,
         "line_pos": 0.0, "arrow_far": None},
    ]
    fig.canvas.draw()
    try:
        violations = narrow_label_violations(fig, records)
        assert len(violations) == 2, violations
        assert "off the dim line midpoint" in violations[0], violations
        assert "too close to the dim line" in violations[1], violations
    finally:
        plt.close(fig)


def test_snap_data_lands_on_pixel_grid():
    """_snap_data must return coordinates that matplotlib maps back to whole
    render pixels — half-pixel positions are what rendered the title block's
    right frame edge 1 px thin while its neighbours rendered 2 px."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig = plt.figure(figsize=(11.69, 8.27), dpi=150)
    ax = fig.add_axes([0.70, 0.47, 0.25, 0.40])
    ax.set_xlim(-2, 93)
    ax.set_ylim(-64, 10)
    for value, axis in [(0.0, "x"), (40.0, "x"), (66.0, "x"), (92.0, "x"),
                        (-46.0, "y"), (-54.0, "y"), (-62.0, "y")]:
        snapped = _snap_data(ax, value, axis)
        xy = (snapped, 0.0) if axis == "x" else (0.0, snapped)
        px = ax.transData.transform(xy)[0 if axis == "x" else 1]
        assert px == pytest.approx(round(px), abs=1e-6), (
            f"{axis}={value} snapped to {snapped}, lands on px {px}")


def test_title_block_grid_lines_render_equal_width():
    """Pixel probe on a rendered title block: every vertical and horizontal
    grid line must render the same pixel width. The owner caught the right
    frame edge at a half-pixel data position rendering 1 px while its
    neighbours rendered 2 px — _snap_data pins the grid to the pixel grid."""
    import io
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np
    from PIL import Image

    fig = plt.figure(figsize=(11.69, 8.27), dpi=150)
    ax = fig.add_axes([0.70, 0.47, 0.25, 0.40])
    ax.axis("off")
    ax.set_xlim(-2, 93)
    ax.set_ylim(-64, 10)
    draw_title_block(ax, "brush_organizer",
                     REPO / "specs" / "brush_organizer" / "spec.yaml", 0.0, -46)
    buf = io.BytesIO()
    fig.savefig(buf, format="png")  # no tight bbox → deterministic pixel grid
    gray = np.asarray(Image.open(buf).convert("L")).astype(float) / 255.0
    dark = gray < 0.5

    # the info axes region in pixels (axes rect [0.70, 0.47, 0.25, 0.40])
    y0px = int((1 - 0.87) * gray.shape[0])
    y1px = int((1 - 0.47) * gray.shape[0])
    x0px = int(0.70 * gray.shape[1])
    x1px = min(gray.shape[1], x0px + 445)  # right frame edge sits at the axes edge
    region = dark[y0px:y1px, x0px:x1px]

    # horizontal lines: rows where nearly the whole title-block width is dark
    hrows = np.where(region.sum(axis=1) > 0.8 * region.shape[1])[0]
    hgroups = np.split(hrows, np.where(np.diff(hrows) > 1)[0] + 1)
    assert len(hgroups) == 3, (
        f"expected 3 horizontal title-block lines, got {len(hgroups)}")
    hw = [len(g) for g in hgroups]
    assert len(set(hw)) == 1, f"horizontal line widths differ: {hw}"

    # vertical lines in the first row band (between top and middle lines)
    band = region[hgroups[0][-1] + 1:hgroups[1][0], :]
    vcols = np.where(band.sum(axis=0) > 0.9 * band.shape[0])[0]
    vgroups = np.split(vcols, np.where(np.diff(vcols) > 1)[0] + 1)
    assert len(vgroups) == 4, (
        f"expected 4 vertical title-block lines, got {len(vgroups)}")
    vw = [len(g) for g in vgroups]
    assert len(set(vw)) == 1, f"vertical line widths differ: {vw}"