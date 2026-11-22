"""Model check: renders the Tomahawk (stowed, boosting, cruising) and the submarine on a plain background.
   python3 tlook.py <out_dir> [views...]"""
import bpy, sys, os, math
HERE = os.path.dirname(os.path.abspath(__file__))
for p in ("grenade-explosion", "rpg7-explosion", "mortar-explosion", "howitzer-explosion", "reaper-hellfire"):
    sys.path.insert(0, os.path.join(HERE, "..", p))
sys.path.insert(0, HERE)
from mathutils import Vector
import ttlam, tsub
import tconst as C
# missiles stand at y = 0 (cruise), z offsets; the submarine at y = 400
VIEWS = {"m_side": ((0, -9.5, 0.6), (0, 0, 0.0), 50), "m_q": ((6.5, -5.5, 2.6), (0.2, 0, -0.2), 50), "m_under": ((2.0, -3.5, -5.5), (-0.6, 0, 0), 50), "m_rear": ((-7.0, -4.0, 1.8), (-1.0, 0, 0), 50),
         "m_states": ((0, -16.0, -5.0), (-0.3, 0, -5.0), 50), "s_side": ((-55, 250, 4), (-55, 400, 0), 50), "s_q": ((45, 330, 28), (-30, 400, 0), 50), "s_bow": ((6, 388, 9), (-13, 400, 4), 35),
         "s_stern": ((-135, 372, 10), (-100, 400, 0), 50), "s_top": ((-55, 400.01, 150), (-55, 400, 0), 50)}
def main():
    out = sys.argv[1]; views = sys.argv[2:] or list(VIEWS)
    bpy.ops.wm.read_factory_settings(use_empty=True); sc = bpy.context.scene
    w = bpy.data.worlds.new("Studio"); sc.world = w; w.use_nodes = True
    w.node_tree.nodes["Background"].inputs[0].default_value = (0.78, 0.82, 0.88, 1); w.node_tree.nodes["Background"].inputs[1].default_value = 1.2
    sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", 'SUN')); sc.collection.objects.link(sun); sun.data.energy = 4.0; sun.rotation_euler = (math.radians(50), 0, math.radians(35))
    T = ttlam.Tomahawk(name="Cruise"); T.config()
    for k, (kw, z) in enumerate(((dict(wings=0.0, fins=0.0, booster=True, shroud=True, plugs=True, cover=True), -3.4), (dict(wings=0.0, fins=1.0, booster=True, cover=True, burn=1.0), -5.0), (dict(wings=0.55, fins=1.0, booster=True, burn=1.0), -6.6))):
        m = ttlam.Tomahawk(name="State%d" % k); m.config(**kw); m.root.location = (0, 0, z)
    S = tsub.Submarine(); S.root.location = (0, 400, 0); S.set(door=1.0)
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); sc.collection.objects.link(cam); sc.camera = cam; cam.data.clip_end = 2000
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
