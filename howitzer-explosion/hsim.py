"""Bake the two Mantaflow gas sims of the 155 mm howitzer segment to OpenVDB caches.

  python3 hsim.py launch|impact <cache_dir> <resolution> <frames> [noise 0|1]

launch : muzzle flash and smoke - forward jet plus the two side jets thrown out by the muzzle-brake
         baffles - and the dust the blast lifts off the ground in front of and around the gun
impact : point-detonating 155 mm HE in a street 3 m from a house front: short fireball, dark smoke,
         dirt skirt and ejecta, then the pale masonry dust of the house front coming down
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
from msim import flow, ico, torus, box, collider, jet, DIRT, DARK
import hconst as C

msim.DOMAINS["h_launch"] = ((26.0, 20.0, 13.0), (6.5, 0.0)); msim.DOMAINS["h_impact"] = ((46.0, 46.0, 32.0), (0.0, 3.0))
SAND = [(0.52, 0.44, 0.32), (0.46, 0.38, 0.27), (0.58, 0.50, 0.38)]
DUST = [(0.60, 0.56, 0.48), (0.54, 0.50, 0.43), (0.66, 0.61, 0.52)]

def build_launch():
    A = Vector(C.BORE); M = Vector(C.MUZZLE); L = Vector((0, 1, 0))
    flash = ico("E_mflash", 0.42, M + A * 0.9, rough=0.35)
    flow(flash, 'BOTH', 1, 2, dens=1.4, temp=2.2, fuel=1.0, color=(0.42, 0.40, 0.37), vn=16.0, vinit=A * 70)
    smoke = ico("E_msmoke", 0.55, M + A * 1.2, rough=0.4)
    flow(smoke, 'SMOKE', 2, 9, dens=2.6, temp=0.7, color=(0.50, 0.47, 0.42), vn=9.0, vinit=A * 34)
    for k, sgn in enumerate((-1, 1)):                               # the muzzle brake throws two jets out sideways and a little back
        d = (L * sgn * 0.94 - A * 0.34).normalized()
        f = ico("E_side%d" % k, 0.30, M - A * 0.20 + d * 0.5, rough=0.35)
        flow(f, 'BOTH', 1, 2, dens=1.3, temp=2.0, fuel=0.8, color=(0.45, 0.42, 0.38), vn=10.0, vinit=d * 55)
        s = ico("E_sides%d" % k, 0.38, M - A * 0.20 + d * 0.8, rough=0.4)
        flow(s, 'SMOKE', 2, 7, dens=2.2, temp=0.5, color=(0.52, 0.49, 0.44), vn=7.0, vinit=d * 30)
    sheet = ico("E_gsheet", 1.0, (5.5, 0, 0.12), rough=0.25, scale=(7.5, 6.5, 0.07))
    flow(sheet, 'SMOKE', 3, 9, dens=0.9, temp=0.15, color=SAND[2], vn=1.5, vinit=(1.5, 0, 2.6))
    near = ico("E_gnear", 1.0, (0.5, 0, 0.12), rough=0.25, scale=(4.0, 4.0, 0.06))
    flow(near, 'SMOKE', 4, 9, dens=0.45, temp=0.12, color=SAND[0], vn=1.0, vinit=(0, 0, 1.6))
    for i in range(12):
        az = random.uniform(-1.9, 1.9); d = (math.cos(az), math.sin(az), random.uniform(0.05, 0.35))
        jet("E_gj%02d" % i, (5.2 + 2.0 * d[0], 2.0 * d[1], 0.25), d, random.uniform(14, 30), random.uniform(3.5, 6.0), random.randint(14, 30), random.uniform(0.3, 0.5),
            random.choice(SAND), start=3, dens=1.4)

def build_impact():
    Y = 3.0                                                         # street front of the struck house (see htown.HIT_Y)
    collider(box("E_frontL", (-6.1, Y - 0.12, -0.1), (-3.3, Y + 0.13, 6.6))); collider(box("E_frontR", (3.3, Y - 0.12, -0.1), (5.1, Y + 0.13, 6.6)))
    collider(box("E_sideL", (-6.1, Y, -0.1), (-5.85, 13.0, 6.6))); collider(box("E_sideR", (4.85, Y, -0.1), (5.1, 13.0, 6.6))); collider(box("E_back", (-6.1, 12.8, -0.1), (5.1, 13.05, 6.6)))
    collider(box("E_nbL", (-20.0, Y, -0.1), (-8.0, 13.5, 9.0))); collider(box("E_nbR", (7.0, Y, -0.1), (17.0, 12.0, 3.4)))
    collider(box("E_opp1", (-16.5, -16.0, -0.1), (-4.5, -6.0, 8.0))); collider(box("E_opp2", (-2.5, -15.0, -0.1), (9.0, -6.0, 3.4))); collider(box("E_opp3", (11.0, -17.0, -0.1), (22.9, -6.0, 6.4)))
    core = ico("E_core", 1.45, (0, 0, 0.9), rough=0.4)
    flow(core, 'BOTH', 1, 2, dens=2.4, temp=2.3, fuel=0.9, color=DARK[0], vn=30.0, vinit=(4.0, 0, 9.0))
    soot = ico("E_soot", 2.1, (0, 0, 1.3), rough=0.45)
    flow(soot, 'SMOKE', 2, 8, dens=3.6, temp=1.0, color=DARK[0], vn=16.0, vinit=(2.0, 0, 13.0))
    column = ico("E_column", 1.3, (0, 0, 2.0), rough=0.35)
    flow(column, 'SMOKE', 4, 16, dens=2.8, temp=1.4, color=DARK[1], vn=5.0, vinit=(1.0, 0, 11.0))
    skirt = torus("E_skirt", 3.0, 0.65, (0, 0, 0.45), lobes=0.30)
    flow(skirt, 'SMOKE', 1, 5, dens=1.9, temp=0.25, color=SAND[1], vn=24.0, vinit=(0, 0, 2.5))
    sheet = ico("E_sheet", 1.0, (0, -1.0, 0.14), rough=0.25, scale=(11.0, 4.6, 0.07))
    flow(sheet, 'SMOKE', 3, 8, dens=0.8, temp=0.15, color=SAND[2], vn=1.5, vinit=(0, 0, 2.4))
    for i in range(34):
        az = random.uniform(0, math.tau); el = math.radians(random.uniform(14, 82))
        d = (math.cos(az) * math.cos(el), math.sin(az) * math.cos(el), math.sin(el))
        jet("E_j%02d" % i, (0.6 * d[0], 0.6 * d[1], 0.5), d, random.uniform(28, 64), random.uniform(3.0, 5.5), random.randint(16, 40),
            random.uniform(0.40, 0.70), random.choice(SAND + DARK + DARK[:2]), dens=2.0)
    # the house front and the slabs behind it come down: pale masonry dust, first blown inwards, then rolling out
    blown = ico("E_blown", 1.0, (0, Y + 1.0, 2.6), rough=0.35, scale=(3.0, 0.9, 2.6))
    flow(blown, 'SMOKE', 2, 7, dens=2.4, temp=0.2, color=DUST[0], vn=3.0, vinit=(0, 9.0, 2.5))
    for k, (fr0, fr1) in enumerate(((10, 40), (30, 75), (60, 110))):
        fall = ico("E_fall%d" % k, 1.0, (random.uniform(-1, 1), Y + 1.6 + 0.7 * k, 1.2 + 0.6 * k), rough=0.4, scale=(3.4 - 0.4 * k, 1.6, 1.3))
        flow(fall, 'SMOKE', fr0, fr1, dens=1.5 - 0.3 * k, temp=0.12, color=DUST[k], vn=2.5, vinit=(0, -1.5, 1.2))

if __name__ == "__main__":
    kind, cache_dir, res, frames = sys.argv[1], os.path.abspath(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4])
    noise = len(sys.argv) > 5 and sys.argv[5] == "1"
    random.seed(19 if kind == "impact" else 31)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    dom = msim.make_domain("h_" + kind, cache_dir, res, frames, noise)
    d = dom.modifiers["Fluid"].domain_settings
    d.burning_rate = 4.5 if kind == "impact" else 3.4; d.flame_smoke_color = (0.10, 0.095, 0.09) if kind == "impact" else (0.40, 0.38, 0.35)
    (build_impact if kind == "impact" else build_launch)()
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
