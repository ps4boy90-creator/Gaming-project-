"""Model check: renders the bomb, the load and the aircraft on a plain background.
   python3 dlook.py <out_dir> [views...]"""
import bpy, sys, os, math
HERE = os.path.dirname(os.path.abspath(__file__))
for p in ("grenade-explosion", "rpg7-explosion", "mortar-explosion", "howitzer-explosion", "reaper-hellfire"):
    sys.path.insert(0, os.path.join(HERE, "..", p))
sys.path.insert(0, HERE)
from mathutils import Vector, Quaternion
import dconst as C, dbomb
# the aircraft at y = 0; the bomb and its load at y = -200; trees at y = 400
VIEWS = {"side": ((0, -70, 3), (0, 0, 2.5), 60), "top": ((0, 0.01, 85), (0, 0, 0), 60), "front": ((70, 0, 3), (0, 0, 2.5), 85), "q34": ((40, -34, 18), (0, 0, 2), 50), "rear": ((-42, -22, 9), (-6, 0, 2.5), 55),
         "ramp": ((-22, -9, -2.5), (-7, 0, 1.2), 50), "under": ((26, -20, -20), (2, 0, 1), 50),
         "bomb": ((1.6, -209.5, 1.4), (0.3, -200, 0), 50), "load": ((6.5, -207, 2.2), (0.2, -200, -0.3), 50), "cut": ((0.5, -208.5, -3.0), (0.4, -200, -3.0), 50), "chute": ((-4, -222, 2), (-4, -200, 0), 50),
         "trees": ((0, 330, 22), (0, 400, 18), 35), "trees2": ((60, 340, 70), (0, 400, 10), 35)}
def main():
    out = sys.argv[1]; views = sys.argv[2:] or list(VIEWS)
    bpy.ops.wm.read_factory_settings(use_empty=True); sc = bpy.context.scene
    w = bpy.data.worlds.new("Studio"); sc.world = w; w.use_nodes = True
    w.node_tree.nodes["Background"].inputs[0].default_value = (0.78, 0.82, 0.88, 1); w.node_tree.nodes["Background"].inputs[1].default_value = 1.2
    sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", 'SUN')); sc.collection.objects.link(sun); sun.data.energy = 4.0; sun.rotation_euler = (math.radians(50), 0, math.radians(35))
    if any(v in views for v in ("side", "top", "front", "q34", "rear", "ramp", "under")):
        import dc130; A = dc130.C130(name="Herc"); A.set_props(0.3)
    if any(v in views for v in ("bomb", "load", "cut", "chute")):
        b = dbomb.Bomb(name="Show"); b.ob.location = (0, -200, 0); cr = dbomb.Cradle(name="ShowCradle"); cr.ob.location = (0, -200, 0)
        c = dbomb.Bomb(name="ShowCut", cut=True); c.ob.location = (0, -200, -3.0)
        ch = dbomb.Chute(name="Stab", d=C.STAB_D); ch.ob.location = (-C.BLU_L / 2 - 0.34, -200, 0); ch.set(1.0)
    if any(v.startswith("trees") for v in views):
        import djungle; djungle.look_row(sc.collection, (0, 400, 0))
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); sc.collection.objects.link(cam); sc.camera = cam; cam.data.clip_end = 3000
    sc.render.engine = 'CYCLES'; sc.cycles.samples = int(os.environ.get('LOOK_SPP', '24')); sc.cycles.use_denoising = True
    import hshots; hshots.use_device(sc)
    sc.render.resolution_x, sc.render.resolution_y = [int(v) for v in os.environ.get('LOOK_RES', '960x540').split('x')]; sc.view_settings.view_transform = 'AgX'
    sc.render.image_settings.file_format = 'JPEG'; os.makedirs(out, exist_ok=True)
    for v in views:
        pos, tgt, lens = VIEWS[v]; cam.location = pos; cam.rotation_euler = (Vector(tgt) - Vector(pos)).to_track_quat('-Z', 'Y').to_euler(); cam.data.lens = lens
        sc.render.filepath = os.path.join(out, v + ".jpg"); bpy.ops.render.render(write_still=True); print("VIEW", v); sys.stdout.flush()
    os._exit(0)
if __name__ == "__main__":
    main()
