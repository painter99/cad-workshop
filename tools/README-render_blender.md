# Blender headless renderer for presentation images of verified STL exports.

Runs inside a standalone Blender (4.x LTS recommended) that is downloaded
separately — it is deliberately NOT a pip dependency of this repository.
No display or GPU is required (Cycles CPU rendering).

## Usage

```bash
# one-time: get a standalone Blender (no system install needed)
#   https://www.blender.org/download/lts/  (linux-x64 tarball works headless)
blender --background --python tools/render_blender.py -- \
    <stl_path> <outdir> <views> [samples] [scale]
```

- `views`: comma-separated list from `iso, top, front, side`
- `samples`: Cycles samples (default 64; 64 is plenty for matte parts)
- `scale`: optional uniform model scale (default 1.0)

Example:

```bash
blender --background --python tools/render_blender.py -- \
    exports/brush_organizer.stl specs/brush_organizer/visuals iso,top,front,side
```

## What it does

1. Imports the STL, scales it, and places it bottom-on-ground centered on the origin.
2. Applies a matte PLA-like material (light gray, roughness 0.38), a ground
   plane, a sun + area fill light and a neutral studio world.
3. Renders each requested view with Cycles (CPU, denoised) at 1600x1200.

## Camera conventions (match tools/render_preview.py)

- `front` looks from -Y, `side` from +X, azimuth 0 = +X axis.
- Views are computed with a deterministic look-at quaternion — no Track-To
  constraints. Gotcha learned the hard way: a top-down camera degenerates
  with Track-To and needs an explicit `rotation_euler = (0, 0, 0)`, otherwise
  the render comes out rolled/mirrored.
- When a render "looks wrong", verify the model against the spec by measured
  probes (e.g. ray casts in Blender) instead of judging by eye — in the case
  that produced this rule the model was right and the camera was wrong.

## Notes

- Renders land as `<outdir>/blender_<view>.png` (presentation images in
  `specs/<part>/visuals/` are renamed without the prefix after review).
- ~60-90 s per frame on a laptop CPU at 64 samples.
