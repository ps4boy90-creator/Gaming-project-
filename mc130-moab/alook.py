"""Model check: renders the bomb (fins out, fins folded on its cradle, cut open) on a plain background.
   python3 alook.py <out_dir> [views...]"""
import bpy, sys, os, math
HERE = os.path.dirname(os.path.abspath(__file__))
for p in ("grenade-explosion", "rpg7-explosion", "mortar-explosion", "howitzer-explosion", "reaper-hellfire", "c130-blu82"):
    sys.path.insert(0, os.path.join(HERE, "..", p))
sys.path.insert(0, HERE)
from mathutils import Vector
import aconst as C
VIEWS = {"side": ((0.0, -17.0, 0.6), (0, 0, 0), 50), "q34": ((9.0, -11.0, 4.5), (0.3, 0, 0), 50), "top": ((0, 0.01, 17.0), (0, 0, 0), 50), "tail": ((-9.5, -6.5, 3.0), (-3.2, 0, 0), 50),
         "cradle": ((8.0, -11.0, 26.0), (0, 0, 22.0 - 0.5), 50), "cradle2": ((-10.0, -8.0, 24.5), (-1.0, 0, 21.6), 50), "cut": ((0.0, -15.0, -6.0), (0, 0, -6.0), 50)}
def main():
    out = sys.argv[1]; views = sys.argv[2:] or list(VIEWS)
    bpy.ops.wm.read_factory_settings(use_empty=True); sc = bpy.context.scene
    w = bpy.data.worlds.new("Studio"); sc.world = w; w.use_nodes = True
    w.node_tree.nodes["Background"].inputs[0].default_value = (0.78, 0.82, 0.88, 1); w.node_tree.nodes["Background"].inputs[1].default_value = 1.2
    sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", 'SUN')); sc.collection.objects.link(sun); sun.data.energy = 4.0; sun.rotation_euler = (math.radians(50), 0, math.radians(35))
    import abomb
    g = abomb.Bomb(name="Show"); f = abomb.Bomb(name="Folded"); f.ob.location = (0, 0, 22.0); f.set_fins(0.0); cr = abomb.Cradle(name="ShowCradle"); cr.ob.location = (0, 0, 22.0)
    c = abomb.Bomb(name="ShowCut", cut=True); c.ob.location = (0, 0, -6.0)
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
