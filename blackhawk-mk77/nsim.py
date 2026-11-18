"""Bake the Mantaflow fire of the Mk 77 strike to an OpenVDB cache.

  python3 nsim.py impact <cache_dir> <resolution> <frames> [noise 0|1]

The canister bursts in the street and its fuel gel is thrown forward along the line of flight, burning as it goes:
a rolling orange fireball that runs down the street between the house fronts, then pools of fire and black smoke
(frame 1 = impact).  Timeline: 1 frame = 1/48 s (scene fps 24 x time scale 0.5).
"""
import bpy, sys, math, random, os
HERE = os.path.dirname(os.path.abspath(__file__))
for p in ("grenade-explosion", "rpg7-explosion", "mortar-explosion", "howitzer-explosion"):
    sys.path.insert(0, os.path.join(HERE, "..", p))
sys.path.insert(0, HERE)
import manta_fix  # noqa: F401
import msim, htown
from msim import flow, ico, box, collider, DARK
import nconst as C

SIZE = (62.0, 32.0, 36.0); CEN = (19.0, -1.5)
msim.DOMAINS["n_impact"] = (SIZE, CEN)
FRONT = 46.0 * C.SIM_DT                      # how far the burning fuel runs along the street per sim frame

def build(frames):
    for i, (x0, y0, x1, y1, st, dmg) in enumerate(htown.HOUSES):
        if x1 > CEN[0] - SIZE[0] / 2 and x0 < CEN[0] + SIZE[0] / 2:
            collider(box("E_house%d" % i, (x0, y0, -0.1), (x1, y1, st * htown.STOREY)))
    burst = ico("E_burst", 1.3, (0.6, 0.0, 0.8), rough=0.4)
    flow(burst, 'BOTH', 1, 3, dens=1.1, temp=2.2, fuel=1.6, color=DARK[0], vn=10.0, vinit=(20.0, 0, 7.0))
    for k in range(16):                                               # the fuel thrown forward, alight
        x = 2.0 + 2.05 * k; f = 1 + int(x / FRONT)
        e = ico("E_run%02d" % k, 1.0, (x, random.uniform(-2.4, 0.9), 0.7), rough=0.35, scale=(1.5, 2.3, 0.6))
        flow(e, 'BOTH', f, f + 6, dens=0.9, temp=2.0, fuel=1.7, color=DARK[0], vn=5.0, vinit=(16.0 * (1 - 0.5 * k / 16), random.uniform(-2, 2), 5.5))
    for k in range(11):                                               # what stays on the ground keeps burning
        x = 1.5 + 3.1 * k; f = 3 + int(x / FRONT)
        e = ico("E_pool%02d" % k, 1.0, (x, random.uniform(-2.8, 0.9), 0.22), rough=0.3, scale=(1.7, 2.3, 0.2))
        flow(e, 'BOTH', f, frames, dens=0.75, temp=1.3, fuel=0.5, color=DARK[0], vn=0.5, vinit=(0.6, 0, 2.6))
    for k, (x, yw, sy) in enumerate(((6.0, 2.75, -1), (15.0, 2.75, -1), (25.0, 2.75, -1), (9.0, -5.75, 1), (19.0, -5.75, 1), (29.0, -5.75, 1))):   # gel splashed up the house fronts
        f = 4 + int(x / FRONT); e = ico("E_wall%d" % k, 1.0, (x, yw + 0.35 * sy, 1.5), rough=0.3, scale=(1.7, 0.30, 1.3))
        flow(e, 'BOTH', f, frames, dens=0.6, temp=1.4, fuel=0.45, color=DARK[0], vn=0.6, vinit=(0.5, 1.0 * sy, 3.0))

if __name__ == "__main__":
    kind, cache_dir, res, frames = sys.argv[1], os.path.abspath(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4])
    noise = len(sys.argv) > 5 and sys.argv[5] == "1"
    random.seed(37)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    dom = msim.make_domain("n_" + kind, cache_dir, res, frames, noise)
    d = dom.modifiers["Fluid"].domain_settings
    d.time_scale = 0.5; d.burning_rate = 1.0; d.flame_smoke = 3.0; d.flame_smoke_color = (0.045, 0.042, 0.040); d.flame_vorticity = 0.75; d.flame_ignition = 1.2; d.flame_max_temp = 2.6; d.vorticity = 0.55; d.beta = 2.3
    build(frames)
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
