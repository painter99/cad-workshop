"""Hero visualization for the brush organizer.

Builds simple schematic props (toothpaste tubes, brushes, rollers) around the
real CAD model, exports them as temporary STLs and renders one colored hero
scene with matplotlib. Output: specs/brush_organizer/visuals/hero_scene.png

The props are schematic marketing props, NOT production parts - the CAD model
itself is unchanged by this script.
"""

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import trimesh
from build123d import Align, Box, Cylinder, Pos, Sphere, export_stl
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from models.brush_organizer import load_spec, build  # noqa: E402

TMP = Path("/tmp/cad_viz_props")
TMP.mkdir(exist_ok=True)
OUT_DIR = REPO / "specs" / "brush_organizer" / "visuals"


def tube(x: float):
    """Toothpaste tube standing cap-up in a 35 mm pocket."""
    body = Pos(x, 0, 20 + 55 / 2) * Cylinder(radius=15, height=55)
    shoulder = Pos(x, 0, 75 + 4) * Cylinder(radius=15, height=8)
    neck = Pos(x, 0, 83 + 5) * Cylinder(radius=7, height=10)
    cap = Pos(x, 0, 93 + 6) * Cylinder(radius=9, height=12)
    return body + shoulder + neck + cap


def brush(x: float):
    """Brush standing head-up in a 15x12 slot."""
    handle = Pos(x, 0, 20 + 60 / 2) * Box(11, 9, 60)
    head = Pos(x, 0, 80 + 6) * Box(14, 11, 12)
    return handle, head


def roller(x: float, r: float):
    """Round child-hand-sized roller: cylinder body + spherical knob."""
    body = Pos(x, 8, 15 + 35 / 2) * Cylinder(radius=r, height=35)
    knob = Pos(x, 8, 50) * Sphere(radius=r)
    return body + knob


def main() -> None:
    spec = load_spec()
    organizer = build(spec)
    export_stl(organizer, str(TMP / "organizer.stl"))

    parts = {
        "organizer": (TMP / "organizer.stl", "#9db8cc", "#5f7484"),
        "tube_body_1": (None, "#e8f2ec", "#8aa89a"),
        "tube_body_2": (None, "#e8f2ec", "#8aa89a"),
        "tube_cap_1": (None, "#4c9c7e", "#2f6b54"),
        "tube_cap_2": (None, "#4c9c7e", "#2f6b54"),
        "brush_handle_1": (None, "#d99a55", "#9c6a33"),
        "brush_handle_2": (None, "#b5713d", "#84502a"),
        "bristles_1": (None, "#f2e3c4", "#bfa878"),
        "bristles_2": (None, "#f2e3c4", "#bfa878"),
        "roller_1": (None, "#e08a72", "#a55f4c"),
        "roller_2": (None, "#7fa8c9", "#54788f"),
    }

    # Build props and export each as its own STL.
    t1, t2 = tube(-100), tube(100)
    export_stl(t1, str(TMP / "tube1.stl"))
    export_stl(t2, str(TMP / "tube2.stl"))
    # caps only (top part of the tube) for a second color
    cap1 = Pos(-100, 0, 93 + 6) * Cylinder(radius=9, height=12)
    cap2 = Pos(100, 0, 93 + 6) * Cylinder(radius=9, height=12)
    export_stl(cap1, str(TMP / "cap1.stl"))
    export_stl(cap2, str(TMP / "cap2.stl"))
    h1, b1 = brush(-60)
    h2, b2 = brush(-20)
    export_stl(h1, str(TMP / "handle1.stl"))
    export_stl(h2, str(TMP / "handle2.stl"))
    export_stl(b1, str(TMP / "bristles1.stl"))
    export_stl(b2, str(TMP / "bristles2.stl"))
    r1 = roller(20, 9)     # P4, Ø22 pocket
    r2 = roller(60, 12)    # P5, Ø30 pocket
    export_stl(r1, str(TMP / "roller1.stl"))
    export_stl(r2, str(TMP / "roller2.stl"))

    stl_map = {
        "tube_body_1": TMP / "tube1.stl",
        "tube_body_2": TMP / "tube2.stl",
        "tube_cap_1": TMP / "cap1.stl",
        "tube_cap_2": TMP / "cap2.stl",
        "brush_handle_1": TMP / "handle1.stl",
        "brush_handle_2": TMP / "handle2.stl",
        "bristles_1": TMP / "bristles1.stl",
        "bristles_2": TMP / "bristles2.stl",
        "roller_1": TMP / "roller1.stl",
        "roller_2": TMP / "roller2.stl",
    }
    for name, path in stl_map.items():
        parts[name] = (path, parts[name][1], parts[name][2])

    fig = plt.figure(figsize=(12, 7.5), dpi=130)
    ax = fig.add_subplot(111, projection="3d")

    def add_mesh(path, face, edge):
        mesh = trimesh.load(path)
        tri = mesh.vertices[mesh.faces]
        pc = Poly3DCollection(tri, facecolor=face, edgecolor=edge, linewidths=0.08)
        ax.add_collection3d(pc)

    # Painter's-order workaround for matplotlib: tubes and brushes first,
    # then the organizer (its top face occludes their lower parts so they
    # read as inserted), then the shorter rollers on top of the block face.
    order = [
        "tube_body_1", "tube_body_2", "tube_cap_1", "tube_cap_2",
        "brush_handle_1", "brush_handle_2", "bristles_1", "bristles_2",
        "organizer",
        "roller_1", "roller_2",
    ]
    for name in order:
        path, face, edge = parts[name]
        add_mesh(path, face, edge)
    bmin, bmax = (-125, -27.5, 0), (125, 27.5, 105)
    c = [(a + b) / 2 for a, b in zip(bmin, bmax)]
    r = max(bmax[i] - bmin[i] for i in range(3)) / 2 * 1.05
    ax.set_xlim(c[0] - r, c[0] + r)
    ax.set_ylim(c[1] - r, c[1] + r)
    ax.set_zlim(c[2] - r, c[2] + r)
    ax.set_box_aspect((1, 1, 1))
    ax.view_init(elev=30, azim=-55)
    ax.set_axis_off()
    ax.set_facecolor("#f5f2ec")
    fig.patch.set_facecolor("#f5f2ec")
    fig.tight_layout()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / "hero_scene.png"
    fig.savefig(out, bbox_inches="tight", facecolor="#f5f2ec")
    plt.close(fig)
    print(f"rendered {out}")


if __name__ == "__main__":
    main()
