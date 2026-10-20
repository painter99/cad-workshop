# Blender headless renderer for presentation images of verified STL exports.
#
# Runs inside a standalone Blender (4.x LTS recommended) that is downloaded
# separately — it is deliberately NOT a pip dependency of this repository.
# No display or GPU is required (Cycles CPU rendering).
#
# See README-render_blender.md next to this file for usage, camera conventions
# and the top-view camera gotcha.
#
# Usage:
#
#     blender --background --python tools/render_blender.py -- \
#         <stl_path> <outdir> <views> [samples] [scale]
#
# views: comma-separated list from `iso, top, front, side`.

import math
import os
import sys

import bpy
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:]
stl_path = argv[0]
outdir = argv[1]
views = argv[2].split(",")
samples = int(argv[3]) if len(argv) > 3 else 64
scale = float(argv[4]) if len(argv) > 4 else 1.0

os.makedirs(outdir, exist_ok=True)

bpy.ops.wm.read_factory_settings(use_empty=True)

# --- import model -----------------------------------------------------------
bpy.ops.wm.stl_import(filepath=stl_path)
obj = bpy.context.selected_objects[0]
obj.scale = (scale, scale, scale)
bpy.context.view_layer.update()

# shift so the model bottom sits on z=0, centered on origin
bb = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
mins = Vector((min(v.x for v in bb), min(v.y for v in bb), min(v.z for v in bb)))
maxs = Vector((max(v.x for v in bb), max(v.y for v in bb), max(v.z for v in bb)))
size = maxs - mins
center = (mins + maxs) / 2
obj.location = obj.location - center + Vector((0, 0, size.z / 2))
bpy.context.view_layer.update()

# --- material: matte PLA-like plastic ---------------------------------------
mat = bpy.data.materials.new("pla")
mat.use_nodes = True
bsdf = mat.node_tree.nodes["Principled BSDF"]
bsdf.inputs["Base Color"].default_value = (0.72, 0.72, 0.73, 1.0)
bsdf.inputs["Roughness"].default_value = 0.38
obj.data.materials.append(mat)

# --- ground plane -----------------------------------------------------------
bpy.ops.mesh.primitive_plane_add(size=size.length * 8, location=(0, 0, 0))
plane = bpy.context.active_object
pmat = bpy.data.materials.new("ground")
pmat.use_nodes = True
pbsdf = pmat.node_tree.nodes["Principled BSDF"]
pbsdf.inputs["Base Color"].default_value = (0.85, 0.85, 0.85, 1.0)
pbsdf.inputs["Roughness"].default_value = 0.9
plane.data.materials.append(pmat)

# --- lights & world ---------------------------------------------------------
world = bpy.data.worlds.new("world")
world.use_nodes = True
world.node_tree.nodes["Background"].inputs[0].default_value = (0.9, 0.92, 0.95, 1.0)
world.node_tree.nodes["Background"].inputs[1].default_value = 0.6
bpy.context.scene.world = world

sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", 'SUN'))
sun.data.energy = 4.5
sun.data.angle = math.radians(5)
sun.rotation_euler = (math.radians(50), 0, math.radians(35))
bpy.context.collection.objects.link(sun)

area = bpy.data.objects.new("fill", bpy.data.lights.new("fill", 'AREA'))
area.data.energy = 200 * size.length
area.data.size = size.length
area.location = (-size.x, -size.y, size.z * 2)
area.rotation_euler = (math.radians(45), 0, math.radians(-45))
bpy.context.collection.objects.link(area)

# --- camera rig -------------------------------------------------------------
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
cam.data.lens = 60
bpy.context.collection.objects.link(cam)
bpy.context.scene.camera = cam

# orbit radius: fit model into the horizontal FOV of a 60 mm lens with margin
_half_fov = math.atan(18.0 / 60.0)    # sensor 36 mm wide / 2, lens 60 mm
_half_fov_v = math.atan(12.0 / 60.0)  # sensor 24 mm high / 2
radius = (max(size.x, size.y) / 2) / math.tan(_half_fov) * 1.25 + size.z

VIEW_ANGLES = {
    "iso":   (40, 45),    # elevation, azimuth (degrees; azimuth 0 = +X axis)
    "top":   (90, 0),
    "front": (8, -90),    # from -Y, matching render_preview.py convention
    "side":  (8, 0),      # from +X
}

# --- render settings --------------------------------------------------------
scene = bpy.context.scene
scene.render.engine = 'CYCLES'
scene.cycles.device = 'CPU'
scene.cycles.samples = samples
scene.cycles.use_denoising = True
scene.render.resolution_x = 1600
scene.render.resolution_y = 1200
scene.render.image_settings.file_format = 'PNG'

for name in views:
    elev, azim = VIEW_ANGLES[name]
    e, a = math.radians(elev), math.radians(azim)
    r = radius
    if name == "top":
        # fit the long axis horizontally: use the vertical FOV for the short axis
        r = max((size.x / 2) / math.tan(_half_fov),
                (size.y / 2) / math.tan(_half_fov_v)) * 1.15
    cam.location = (
        r * math.cos(e) * math.cos(a),
        r * math.cos(e) * math.sin(a),
        r * math.sin(e) + size.z / 2,
    )
    # deterministic look-at (no constraint roll ambiguity)
    if name == "top":
        cam.rotation_euler = (0, 0, 0)  # straight down, X right, Y up
    else:
        look = (Vector((0, 0, size.z / 2)) - cam.location).normalized()
        cam.rotation_euler = look.to_track_quat('-Z', 'Y').to_euler()
    scene.render.filepath = os.path.join(outdir, f"blender_{name}.png")
    bpy.ops.render.render(write_still=True)
    print(f"RENDER_OK {name}")

print("ALL_DONE")
