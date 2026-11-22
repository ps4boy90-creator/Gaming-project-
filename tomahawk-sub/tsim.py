"""Bake the Mantaflow gas sim of the Tomahawk's warhead bursting inside the factory hall to an OpenVDB cache.

  python3 tsim.py <cache_dir> <resolution> <frames> [noise 0|1]

About 120 kg of PBXN-107 fires two metres above the floor after going through the sheet roof: a short fireball that
vents through the roof and the long walls, dark smoke, pale dust from the block walls, and the sand of the yard thrown
out as a skirt.  Sized from the Mk 82 burst of segment 07 by the cube root of the filling.
Timeline: 1 frame = 1/60 s (scene fps 24 x time scale 0.4); frame 1 = detonation.
"""
import bpy, sys, math, random, os
HERE = os.path.dirname(os.path.abspath(__file__))
for p in ("grenade-explosion", "mortar-explosion"):
    sys.path.insert(0, os.path.join(HERE, "..", p))
sys.path.insert(0, HERE)
import manta_fix  # noqa: F401
import msim
from msim import flow, ico, torus, jet, DARK
import tconst as C

SIM_DT = 1.0 / 60.0
msim.TIME_SCALE = 0.4; msim.DT = SIM_DT
S_ = 2.0 * C.K
SAND = [(0.52, 0.44, 0.32), (0.46, 0.38, 0.27), (0.58, 0.50, 0.38)]; DUST = [(0.60, 0.58, 0.54), (0.50, 0.48, 0.45), (0.55, 0.47, 0.40)]

def build():
    s = S_; v = 1.25 * (s / 2.0) ** 0.5; F = C.FAC; z0 = C.BURST_Z
    core = ico("E_core", 1.2 * s, (0, 0, z0 + 0.4 * s), rough=0.4)
    flow(core, 'BOTH', 1, 2, dens=2.4, temp=2.3, fuel=0.9, color=DARK[0], vn=30.0 * v, vinit=(3.0 * v, 0, 10.0 * v))
    soot = ico("E_soot", 1.7 * s, (0, 0, z0 + 0.9 * s), rough=0.45)
    flow(soot, 'SMOKE', 2, 8, dens=3.2, temp=1.0, color=DARK[0], vn=16.0 * v, vinit=(2.0 * v, 0, 14.0 * v))
    column = ico("E_column", 1.1 * s, (0, 0, z0 + 2.2 * s), rough=0.35)                                             # up through the roof
    flow(column, 'SMOKE', 4, 20, dens=2.8, temp=1.5, color=DARK[1], vn=5.0, vinit=(1.5 * v, 0, 12.0 * v))
    hall = ico("E_hall", 1.0, (0, 0, F["h"] * 0.5), rough=0.35, scale=(F["lx"] * 0.46, F["ly"] * 0.46, F["h"] * 0.45))   # the hall's own dust, pushed out sideways
    flow(hall, 'SMOKE', 2, 10, dens=2.3, temp=0.35, color=DUST[0], vn=12.0 * v, vinit=(0.5, 0, 4.0 * v))
    for sg in (1, -1):                                                                                               # venting through the long walls
        side = ico("E_side%d" % sg, 1.0, (0, sg * F["ly"] * 0.5, F["h"] * 0.45), rough=0.4, scale=(F["lx"] * 0.36, 1.2, F["h"] * 0.38))
        flow(side, 'SMOKE', 1, 5, dens=2.0, temp=0.5, color=DUST[1], vn=6.0, vinit=(0, sg * 34.0 * v, 5.0 * v))
    skirt = torus("E_skirt", 3.6 * s, 0.6 * s, (0, 0, 0.5 * s), lobes=0.30)
    flow(skirt, 'SMOKE', 2, 5, dens=1.4, temp=0.30, color=SAND[1], vn=22.0 * v, vinit=(1.0, 0, 3.0 * v))
    sheet = ico("E_sheet", 1.0, (0, 0, 0.12), rough=0.5, scale=(9.0 * s, 8.0 * s, 0.05))
    flow(sheet, 'SMOKE', 3, 6, dens=0.22, temp=0.12, color=SAND[2], vn=1.0, vinit=(0, 0, 1.4))
    for i in range(40):
        az = random.uniform(0, math.tau); el = math.radians(random.uniform(12, 80))
        d = (math.cos(az) * math.cos(el), math.sin(az) * math.cos(el), math.sin(el))
        jet("E_j%02d" % i, (2.2 * s * d[0], 1.6 * s * d[1], 1.0 + 3.0 * d[2]), d, random.uniform(30, 68) * v, random.uniform(2.6, 4.6), random.randint(16, 40),
            random.uniform(0.36, 0.62) * s * 0.75, random.choice(SAND + DUST + DUST + DARK[:2]), dens=1.9)

if __name__ == "__main__":
    cache_dir, res, frames = os.path.abspath(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3])
    noise = len(sys.argv) > 4 and sys.argv[4] == "1"
    random.seed(53)
    msim.DOMAINS["t_hit"] = ((84.0, 84.0, 62.0), (3.0, 0.0))
    bpy.ops.wm.read_factory_settings(use_empty=True)
    dom = msim.make_domain("t_hit", cache_dir, res, frames, noise)
    d = dom.modifiers["Fluid"].domain_settings
    d.burning_rate = 3.6; d.flame_smoke = 2.4; d.flame_smoke_color = (0.10, 0.095, 0.09)
    build()
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
