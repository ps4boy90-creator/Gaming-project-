"""Bake the Mantaflow gas sim of the Hellfire strike on the pickup to an OpenVDB cache.

  python3 qsim.py impact <cache_dir> <resolution> <frames> [noise 0|1]

impact : 9 kg multi-purpose warhead bursting on a pickup - a short white-orange flash, the fuel going up as a rolling
         orange fireball a few metres across, dark smoke, the sand skirt and ejecta, then the wreck burning with black
         smoke (frame 1 = detonation).
Master timeline: 1 frame = 1/120 s (scene fps 24 * time_scale 0.2).
"""
import bpy, sys, math, random, os
HERE = os.path.dirname(os.path.abspath(__file__))
for p in ("grenade-explosion", "mortar-explosion"):
    sys.path.insert(0, os.path.join(HERE, "..", p))
sys.path.insert(0, HERE)
import manta_fix  # noqa: F401
from mathutils import Vector
import msim
from msim import flow, ico, torus, box, collider, jet, DARK
import qconst as C

msim.DOMAINS["q_impact"] = ((36.0, 36.0, 27.0), (1.5, 0.0))
SAND = [(0.52, 0.44, 0.32), (0.46, 0.38, 0.27), (0.58, 0.50, 0.38)]

def build_impact():
    # what is left of the pickup stands in the cloud: chassis and engine bay (the cab and bed are torn open)
    collider(box("E_chassis", (-0.85, -2.6, -0.1), (0.85, 2.6, 0.80))); collider(box("E_engine", (-0.80, 1.2, 0.80), (0.80, 2.55, 1.15)))
    hx, hy, hz = C.HIT
    core = ico("E_core", 0.95, (hx, hy, hz), rough=0.4)
    flow(core, 'BOTH', 1, 2, dens=2.2, temp=2.3, fuel=0.9, color=DARK[0], vn=26.0, vinit=(6.0, 0, 5.0))
    soot = ico("E_soot", 1.35, (hx + 0.2, hy, hz + 0.3), rough=0.45)
    flow(soot, 'SMOKE', 2, 7, dens=3.2, temp=1.0, color=DARK[0], vn=13.0, vinit=(3.0, 0, 9.0))
    fuel = ico("E_fuel", 0.80, (0.25, -0.9, 1.0), rough=0.4)                       # the tank and what was in the bed
    flow(fuel, 'BOTH', 3, 10, dens=1.3, temp=2.1, fuel=1.5, color=DARK[1], vn=10.0, vinit=(2.0, -1.0, 8.0))
    column = ico("E_column", 0.60, (0.1, 0.2, 1.25), rough=0.35, scale=(1.0, 1.9, 0.8))   # the wreck burns
    flow(column, 'BOTH', 9, 400, dens=1.5, temp=1.5, fuel=0.55, color=DARK[0], vn=1.2, vinit=(0.6, 0, 4.0))
    skirt = torus("E_skirt", 2.2, 0.45, (0, 0, 0.32), lobes=0.30)
    flow(skirt, 'SMOKE', 1, 5, dens=1.8, temp=0.25, color=SAND[1], vn=20.0, vinit=(1.0, 0, 2.2))
    sheet = ico("E_sheet", 1.0, (0.5, 0, 0.12), rough=0.25, scale=(6.5, 6.5, 0.07))
    flow(sheet, 'SMOKE', 3, 7, dens=0.75, temp=0.15, color=SAND[2], vn=1.5, vinit=(0, 0, 2.2))
    for i in range(30):                                                           # sand and wreckage thrown up and out
        az = random.uniform(0, math.tau); el = math.radians(random.uniform(12, 80))
        d = (math.cos(az) * math.cos(el), math.sin(az) * math.cos(el), math.sin(el))
        jet("E_j%02d" % i, (1.0 * d[0], 1.3 * d[1], 0.6 + 0.5 * d[2]), d, random.uniform(22, 54), random.uniform(3.2, 6.0), random.randint(14, 34),
            random.uniform(0.26, 0.46), random.choice(SAND + SAND + DARK), dens=1.9)

if __name__ == "__main__":
    kind, cache_dir, res, frames = sys.argv[1], os.path.abspath(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4])
    noise = len(sys.argv) > 5 and sys.argv[5] == "1"
    random.seed(23)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    dom = msim.make_domain("q_" + kind, cache_dir, res, frames, noise)
    d = dom.modifiers["Fluid"].domain_settings
    d.burning_rate = 3.2; d.flame_smoke = 2.6; d.flame_smoke_color = (0.07, 0.065, 0.06)
    build_impact()
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
