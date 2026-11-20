"""Model check: renders the F-16 and the three bombs on a plain background from several directions.   python3 vlook.py <out_dir> [views...]"""
import bpy, sys, os, math
HERE = os.path.dirname(os.path.abspath(__file__))
for p in ("grenade-explosion", "rpg7-explosion", "mortar-explosion", "howitzer-explosion", "reaper-hellfire"):
    sys.path.insert(0, os.path.join(HERE, "..", p))
sys.path.insert(0, HERE)
from mathutils import Vector
import vf16
VIEWS = {"side": ((0, -34, 0.6), (0, 0, 0.6), 75), "front": ((32, 0.0, 0.4), (0, 0, 0.4), 105), "top": ((-0.2, 0.01, 40), (-0.2, 0, 0), 80), "under": ((-0.2, 0.01, -40), (-0.2, 0, 0), 80),
         "q34": ((15, -12, 7.0), (0.5, 0, 0.2), 55), "low": ((11, 9, -4.0), (0.5, 0, -0.2), 50), "rearq": ((-16, 9, 4.5), (-2.0, 0, 0.6), 60), "bombs": ((2.6, -45.5, 0.9), (0, -40, 0.05), 60), "nose": ((13.5, -6.5, 2.2), (3.2, 0, 0.3), 70), "belly": ((6, -9, -7.0), (-0.5, 0, -0.3), 50)}
def main():
    out = sys.argv[1]; views = sys.argv[2:] or list(VIEWS)
    bpy.ops.wm.read_factory_settings(use_empty=True); sc = bpy.context.scene
    w = bpy.data.worlds.new("Studio"); sc.world = w; w.use_nodes = True
    w.node_tree.nodes["Background"].inputs[0].default_value = (0.78, 0.82, 0.88, 1); w.node_tree.nodes["Background"].inputs[1].default_value = 1.2
    sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", 'SUN')); sc.collection.objects.link(sun); sun.data.energy = 4.0; sun.rotation_euler = (math.radians(50), 0, math.radians(35))
    A = vf16.build()
    for k, z in (("mk82", 0.75), ("mk83", 0.15), ("mk84", -0.55)):
        b = vf16.Bomb(sc.collection, vf16.BOMBS[k], "Show_" + k); b.ob.location = (0, -40, z)
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
