"""Model check: renders the B-2 (bays shut and open) and the bomb on a plain background.
   python3 wlook.py <out_dir> [views...]"""
import bpy, sys, os, math
HERE = os.path.dirname(os.path.abspath(__file__))
for p in ("grenade-explosion", "rpg7-explosion", "mortar-explosion", "howitzer-explosion", "reaper-hellfire"):
    sys.path.insert(0, os.path.join(HERE, "..", p))
sys.path.insert(0, HERE)
from mathutils import Vector
import wconst as C
# the aircraft with its bays shut at y = 0, with them open at y = 300; the bombs at y = -200
VIEWS = {"top": ((0, 0.01, 95), (0, 0, 0), 55), "under": ((0, 0.01, -95), (0, 0, 0), 55), "front": ((80, 0, 4), (0, 0, 1), 85), "side": ((0, -90, 3), (0, 0, 1), 60), "q34": ((44, -40, 22), (0, 0, 0), 50), "rear": ((-52, -30, 14), (0, 0, 1), 55),
         "bay": ((12, 287, -12), (-1, 300, -0.5), 50), "bay2": ((-16, 290, -9), (-1, 300, -1.0), 50),
         "bomb": ((1.5, -214.0, 2.0), (-0.3, -200, 0), 50), "tail": ((-9.0, -205.0, 2.5), (-3.0, -200, 0), 50), "cut": ((-0.2, -213.0, -2.4), (-0.2, -200, -2.4), 50)}
def main():
    out = sys.argv[1]; views = sys.argv[2:] or list(VIEWS)
    bpy.ops.wm.read_factory_settings(use_empty=True); sc = bpy.context.scene
    w = bpy.data.worlds.new("Studio"); sc.world = w; w.use_nodes = True
    w.node_tree.nodes["Background"].inputs[0].default_value = (0.78, 0.82, 0.88, 1); w.node_tree.nodes["Background"].inputs[1].default_value = 1.2
    sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", 'SUN')); sc.collection.objects.link(sun); sun.data.energy = 4.0; sun.rotation_euler = (math.radians(50), 0, math.radians(35))
    if any(v in views for v in ("top", "under", "front", "side", "q34", "rear", "bay", "bay2")):
        import wb2; A = wb2.B2(name="Shut"); A.set(0.0); B = wb2.B2(name="Open"); B.root.location = (0, 300, 0); B.set(1.0, gone=(0,))
    if any(v in views for v in ("bomb", "tail", "cut")):
        import wbomb; g = wbomb.Bomb(name="Show"); g.ob.location = (0, -200, 0); c = wbomb.Bomb(name="ShowCut", cut=True); c.ob.location = (0, -200, -2.4)
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
