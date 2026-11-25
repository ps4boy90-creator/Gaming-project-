"""Bake the Mantaflow gas sim of the BLU-82 bursting three feet above the forest floor to an OpenVDB cache.

  python3 dsim.py out <cache_dir> <resolution> <frames> [noise 0|1]

One frame = 1/60 s, frame 1 = the burst.  There is no crater to throw earth from: a white-hot fireball about 50 m
across, a ring of dust, leaves and torn wood driven out along the ground through the trees, then a pale grey cloud
(the aluminium in the slurry burns to white smoke) that rises on its stem above the canopy.
That the cloud is pale and mushrooms is from the photographs in the 1970 report; its size and speed are staging (the
sources are placed by hand).
"""
import bpy, sys, math, random, os
HERE = os.path.dirname(os.path.abspath(__file__))
for p in ("grenade-explosion", "mortar-explosion", "howitzer-explosion", "reaper-hellfire"):
    sys.path.insert(0, os.path.join(HERE, "..", p))
sys.path.insert(0, HERE)
import manta_fix  # noqa: F401
import msim
from msim import flow, ico, jet, DARK
import dconst as C

PALE = [(0.74, 0.73, 0.70), (0.66, 0.65, 0.62), (0.80, 0.79, 0.76)]; DUST = [(0.40, 0.31, 0.21), (0.33, 0.26, 0.18)]; LEAFY = [(0.16, 0.17, 0.10), (0.22, 0.20, 0.13)]
OUT_BOX = ((-150.0, 150.0), (-150.0, 150.0), (-0.15, 230.0)); OUT_DT = 1.0 / 60.0
RF = C.R_FIRE

def _place(dom, box):
    (x0, x1), (y0, y1), (z0, z1) = box; dom.scale = (x1 - x0, y1 - y0, z1 - z0); dom.location = ((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2)

def build_out():
    z0 = C.HOB
    core = ico("E_core", RF * 0.42, (0, 0, z0 + 3.0), rough=0.35); flow(core, 'BOTH', 1, 3, dens=1.6, temp=2.8, fuel=1.0, color=PALE[2], vn=75.0, vinit=(0.0, 0.0, 20.0))                 # the fireball
    ball = ico("E_ball", RF * 0.70, (0, 0, z0 + 7.0), rough=0.4); flow(ball, 'BOTH', 2, 7, dens=2.0, temp=2.6, fuel=0.6, color=PALE[0], vn=34.0, vinit=(0.0, 0.0, 40.0))
    skirt = msim.torus("E_skirt", RF * 0.9, 4.5, (0, 0, 4.5), lobes=0.25); flow(skirt, 'SMOKE', 1, 12, dens=2.4, temp=0.25, color=DUST[0], vn=62.0)                                           # driven out along the ground through the trees
    skirt2 = msim.torus("E_skirt2", RF * 1.5, 5.0, (0, 0, 6.0), lobes=0.35); flow(skirt2, 'SMOKE', 6, 26, dens=1.8, temp=0.3, color=LEAFY[0], vn=34.0)
    col = ico("E_col", RF * 0.50, (0, 0, 12.0), rough=0.4); flow(col, 'SMOKE', 5, 130, dens=2.4, temp=5.0, color=PALE[1], vn=12.0, vinit=(0.0, 0.0, 85.0))                                    # the stem
    for i in range(46):                                                                                     # torn wood, leaves and dust thrown out low and fast
        az = random.uniform(0, math.tau); el = math.radians(random.uniform(6, 55)); d = (math.cos(az) * math.cos(el), math.sin(az) * math.cos(el), math.sin(el)); r0 = random.uniform(4.0, RF * 0.8)
        jet("E_j%02d" % i, (r0 * math.cos(az), r0 * math.sin(az), 2.0 + 4.0 * d[2]), d, random.uniform(60, 150), random.uniform(1.0, 2.2), random.randint(28, 70), random.uniform(1.6, 3.4), random.choice(DUST + LEAFY + PALE[:1]), start=random.randint(1, 4), dens=1.7)
    late = ico("E_late", 1.0, (0, 0, 2.0), rough=0.4, scale=(RF * 0.9, RF * 0.9, 3.0)); flow(late, 'SMOKE', 60, 900, dens=0.8, temp=1.0, color=PALE[1], vn=2.0, vinit=(0.0, 0.0, 6.0))

if __name__ == "__main__":
    kind = sys.argv[1]; cache_dir, res, frames = os.path.abspath(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4])
    noise = len(sys.argv) > 5 and sys.argv[5] == "1"
    random.seed(57)
    msim.TIME_SCALE = 0.4; msim.DT = OUT_DT
    msim.DOMAINS["d_" + kind] = ((1.0, 1.0, 1.0), (0.0, 0.0))
    bpy.ops.wm.read_factory_settings(use_empty=True)
    dom = msim.make_domain("d_" + kind, cache_dir, res, frames, noise); _place(dom, OUT_BOX)
    d = dom.modifiers["Fluid"].domain_settings
    d.burning_rate = 2.6; d.flame_smoke = 1.6; d.flame_smoke_color = (0.70, 0.69, 0.66); d.alpha = 1.0; d.beta = 4.0          # hot and buoyant: it rises
    build_out()
    os.makedirs(cache_dir, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(cache_dir, "sim.blend"))
    bpy.context.view_layer.objects.active = dom
    import time; t0 = time.time()
    with bpy.context.temp_override(object=dom, active_object=dom, selected_objects=[dom]):
        bpy.ops.fluid.bake_all()
    print("BAKE DONE %.1fs" % (time.time() - t0))
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(cache_dir, "sim.blend"))
    open(os.path.join(cache_dir, "DONE"), "w").write("ok")
    sys.stdout.flush(); os._exit(0)
