"""Model check: renders the B-1B (swept and spread, bay shut and open) and the bomb on a plain background.
   python3 plook.py <out_dir> [views...]"""
import bpy, sys, os, math
HERE = os.path.dirname(os.path.abspath(__file__))
for p in ("grenade-explosion", "rpg7-explosion", "mortar-explosion", "howitzer-explosion", "reaper-hellfire"):
    sys.path.insert(0, os.path.join(HERE, "..", p))
sys.path.insert(0, HERE)
from mathutils import Vector
import pb1b, pbomb
import pconst as C
# swept aircraft at y = 0; spread aircraft with its bay open at y = 300; bombs at y = -200
VIEWS = {"side": ((0, -95, 2), (0, 0, 1.5), 60), "top": ((0, 0.01, 110), (0, 0, 0), 60), "front": ((90, 0, 2), (0, 0, 1), 85), "q34": ((48, -38, 20), (0, 0, 0), 50), "rear": ((-52, -30, 14), (-6, 0, 1), 55),
         "under": ((30, -22, -26), (2, 0, -1), 50), "top2": ((0, 300.01, 110), (0, 300, 0), 60), "bay": ((16, 294, -9), (7.8, 300, -1.0), 50), "bay2": ((7.8, 293, -6.5), (7.8, 300, -1.2), 40),
         "dbg": ((8, -30, 6), (2, 0, 1.5), 60), "dbg2": ((2, 0.01, 30), (2, 0, 0), 60), "bomb": ((0.6, -206.5, 0.5), (-0.6, -200, 0), 50), "cut": ((0.4, -204.6, -1.25), (0, -200, -1.6), 50)}
def main():
    out = sys.argv[1]; views = sys.argv[2:] or list(VIEWS)
    bpy.ops.wm.read_factory_settings(use_empty=True); sc = bpy.context.scene
    w = bpy.data.worlds.new("Studio"); sc.world = w; w.use_nodes = True
    w.node_tree.nodes["Background"].inputs[0].default_value = (0.78, 0.82, 0.88, 1); w.node_tree.nodes["Background"].inputs[1].default_value = 1.2
    sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", 'SUN')); sc.collection.objects.link(sun); sun.data.energy = 4.0; sun.rotation_euler = (math.radians(50), 0, math.radians(35))
    A = pb1b.B1B(name="Swept", stores=False)
    B = pb1b.B1B(name="Spread"); B.root.location = (0, 300, 0); B.set(C.SWEEP_FWD, 1.0, 0.0, gone=(0,))
    g = pbomb.Bomb(name="Show"); g.ob.location = (0, -200, 0); c = pbomb.Bomb(name="ShowCut", cut=True); c.ob.location = (0, -200, -1.6)
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
