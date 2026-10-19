"""Render headless PNG previews from a model's exported STL.

Usage: python tools/render_preview.py <stl_path> <out_prefix> [views...]
Default views: iso, front, top, side. Output: <out_prefix>_<view>.png in exports/.
"""

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # headless: no display required
import matplotlib.pyplot as plt
import numpy as np
import trimesh
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

VIEWS = {
    "iso": (30, -60),
    "front": (0, -90),
    "top": (90, -90),
    "side": (0, 0),
    "bottom": (-90, -90),
}


def render(mesh: trimesh.Trimesh, elev: float, azim: float, out_path: Path) -> None:
    fig = plt.figure(figsize=(8, 6), dpi=120)
    ax = fig.add_subplot(111, projection="3d")
    tri = mesh.vertices[mesh.faces]
    pc = Poly3DCollection(tri, facecolor="#8fb7d9", edgecolor="#33475b", linewidths=0.1)
    ax.add_collection3d(pc)
    bmin, bmax = mesh.bounds
    c, r = (bmin + bmax) / 2, (bmax - bmin).max() / 2
    ax.set_xlim(c[0] - r, c[0] + r)
    ax.set_ylim(c[1] - r, c[1] + r)
    ax.set_zlim(c[2] - r, c[2] + r)
    ax.set_box_aspect((1, 1, 1))
    ax.view_init(elev=elev, azim=azim)
    ax.set_axis_off()
    fig.tight_layout()
    fig.savefig(out_path, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    stl_path = Path(sys.argv[1])
    out_prefix = Path(sys.argv[2]) if len(sys.argv) > 2 else stl_path.with_suffix("")
    views = sys.argv[3:] or list(VIEWS)
    mesh = trimesh.load(stl_path)
    out_prefix.parent.mkdir(parents=True, exist_ok=True)
    for v in views:
        elev, azim = VIEWS[v]
        out = out_prefix.parent / f"{out_prefix.name}_{v}.png"
        render(mesh, elev, azim, out)
        print(f"rendered {out}")


if __name__ == "__main__":
    main()
