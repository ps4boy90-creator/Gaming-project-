"""Model check: renders the Black Hawk and a Mk 77 on a plain background from several directions.   python3 nlook.py <out_dir> [views...]"""
import bpy, sys, os, math, time
HERE = os.path.dirname(os.path.abspath(__file__))
for p in ("grenade-explosion", "rpg7-explosion", "mortar-explosion", "howitzer-explosion", "reaper-hellfire"):
    sys.path.insert(0, os.path.join(HERE, "..", p))
sys.path.insert(0, HERE)
from mathutils import Vector
import nuh60
VIEWS = {"side": ((-3.5, -30, 2.2), (-3.5, 0, 2.2), 60), "front": ((30, 0.0, 2.2), (0, 0, 2.2), 85), "top": ((-3.0, 0.01, 40), (-3.0, 0, 0), 55), "q34": ((14, -13, 6.5), (-2.0, 0, 1.8), 45),
         "rearq": ((-17, 9, 5.0), (-4.0, 0, 2.0), 50), "store": ((3.6, -6.2, 1.2), (0.0, -2.5, 1.7), 45), "bomb": ((1.6, -42.6, 0.5), (0, -40, 0), 50)}
def main():
    out = sys.argv[1]; views = sys.argv[2:] or list(VIEWS)
    bpy.ops.wm.read_factory_settings(use_empty=True); sc = bpy.context.scene
    w = bpy.data.worlds.new("Studio"); sc.world = w; w.use_nodes = True
    w.node_tree.nodes["Background"].inputs[0].default_value = (0.78, 0.82, 0.88, 1); w.node_tree.nodes["Background"].inputs[1].default_value = 1.2
    sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", 'SUN')); sc.collection.objects.link(sun); sun.data.energy = 4.0; sun.rotation_euler = (math.radians(50), 0, math.radians(35))
    A = nuh60.build(); nuh60.spin(A["main"], sc, 0.02, 0.0, 4.3); nuh60.spin(A["tail"], sc, 0.01, 0.0, 20.0)
    b = nuh60.Mk77(sc.collection, "Show"); b.ob.location = (0, -40, 0)
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); sc.collection.objects.link(cam); sc.camera = cam; cam.data.clip_end = 500
    sc.render.engine = 'CYCLES'; sc.cycles.samples = 24; sc.cycles.use_denoising = True
    import hshots; hshots.use_device(sc)
    sc.render.resolution_x, sc.render.resolution_y = 960, 540; sc.view_settings.view_transform = 'AgX'
    sc.render.image_settings.file_format = 'JPEG'; os.makedirs(out, exist_ok=True)
    for v in views:
        pos, tgt, lens = VIEWS[v]; cam.location = pos; cam.rotation_euler = (Vector(tgt) - Vector(pos)).to_track_quat('-Z', 'Y').to_euler(); cam.data.lens = lens
        sc.render.filepath = os.path.join(out, v + ".jpg"); bpy.ops.render.render(write_still=True); print("VIEW", v); sys.stdout.flush()
    os._exit(0)
if __name__ == "__main__":
    main()
