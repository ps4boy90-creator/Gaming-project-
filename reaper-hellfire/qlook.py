"""Model check: renders the Reaper (and a Hellfire close-up) on a plain studio from several directions.

  python3 qlook.py <out_dir> [views...]        views: front side top rear q34 under hell
"""
import bpy, sys, os, math, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "grenade-explosion")); sys.path.insert(0, os.path.join(HERE, "..", "howitzer-explosion")); sys.path.insert(0, HERE)
import numpy as np
from mathutils import Vector
import qmq9, qhell
from qgeo import *

VIEWS = {"front": ((30, 0.0, 0.6), (0, 0, 0.2), 70), "side": ((-0.6, -34, 0.3), (-0.6, 0, 0.1), 80), "top": ((-0.5, 0.01, 40), (-0.5, 0, 0), 50),
         "rear": ((-26, 0.0, 1.2), (0, 0, 0.3), 60), "q34": ((15, -13, 5.5), (-0.2, 0, -0.1), 50), "under": ((7.5, -5.5, -3.2), (0.2, 1.2, -0.3), 40),
         "hell": ((1.9, -1.7, 0.55), (0.8, 0, 0), 60), "tailq": ((-14, -10, 4.0), (-2.5, 0, 0.2), 55)}

def main():
    out = sys.argv[1]; views = sys.argv[2:] or list(VIEWS)
    bpy.ops.wm.read_factory_settings(use_empty=True); sc = bpy.context.scene
    w = bpy.data.worlds.new("Studio"); sc.world = w; w.use_nodes = True
    w.node_tree.nodes["Background"].inputs[0].default_value = (0.78, 0.82, 0.88, 1); w.node_tree.nodes["Background"].inputs[1].default_value = 0.9
    sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", 'SUN')); sc.collection.objects.link(sun); sun.data.energy = 3.0; sun.data.angle = 0.05
    sun.rotation_euler = (math.radians(50), 0, math.radians(35))
    A = qmq9.build(); qmq9.spin_prop(A["prop"], sc, 0.01, 0.0)
    H = qhell.Hellfire(None, "HellfireShow"); H.root.location = (0, -40, 0)
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); sc.collection.objects.link(cam); sc.camera = cam; cam.data.clip_start = 0.05; cam.data.clip_end = 500
    sc.render.engine = 'CYCLES'; c = sc.cycles; c.samples = 24; c.use_denoising = True
    import hshots; hshots.use_device(sc)
    sc.render.resolution_x, sc.render.resolution_y = 1280, 720; sc.view_settings.view_transform = 'AgX'
    sc.render.image_settings.file_format = 'JPEG'; sc.render.image_settings.quality = 88
    os.makedirs(out, exist_ok=True)
    for v in views:
        pos, tgt, lens = VIEWS[v]
        if v == "hell":
            pos = (pos[0], pos[1] - 40, pos[2]); tgt = (tgt[0], -40, tgt[2])
        cam.location = pos; cam.rotation_euler = (Vector(tgt) - Vector(pos)).to_track_quat('-Z', 'Y').to_euler(); cam.data.lens = lens
        sc.render.filepath = os.path.join(out, v + ".jpg"); t = time.time(); bpy.ops.render.render(write_still=True); print("VIEW %s %.1fs" % (v, time.time() - t)); sys.stdout.flush()
    os._exit(0)

if __name__ == "__main__":
    main()
