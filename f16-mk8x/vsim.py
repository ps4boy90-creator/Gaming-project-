"""Bake the Mantaflow gas sim of one bomb bursting on a bunker roof to an OpenVDB cache.

  python3 vsim.py mk82|mk83 <cache_dir> <resolution> <frames> [noise 0|1]

Instantaneous fuze on the concrete roof: a short fireball, a dark smoke column, grey concrete dust, and the sand of
the earth bank thrown out as a skirt and in jets.  The Mk 83 is the same burst scaled up by the cube root of its
filling.  Timeline: 1 frame = 1/60 s (scene fps 24 x time scale 0.4); frame 1 = detonation.
"""
import bpy, sys, math, random, os
HERE = os.path.dirname(os.path.abspath(__file__))
for p in ("grenade-explosion", "mortar-explosion"):
    sys.path.insert(0, os.path.join(HERE, "..", p))
sys.path.insert(0, HERE)
import manta_fix  # noqa: F401
import msim
from msim import flow, ico, torus, box, collider, jet, DARK
import vconst as C

msim.TIME_SCALE = 0.4; msim.DT = C.SIM_DT
SCALE = {"mk82": 2.0, "mk83": 2.0 * (202.0 / 87.0) ** (1 / 3)}
SIZE = {"mk82": (70.0, 70.0, 54.0), "mk83": (92.0, 92.0, 70.0)}
SAND = [(0.52, 0.44, 0.32), (0.46, 0.38, 0.27), (0.58, 0.50, 0.38)]; DUST = [(0.56, 0.55, 0.52), (0.48, 0.47, 0.45)]

def build(kind):
    s = SCALE[kind]; v = 1.25 * (s / 2.0) ** 0.5; B = C.BUNK; z0 = B["h"]
    collider(box("E_bunker", (-B["lx"] / 2, -B["ly"] / 2, -0.1), (B["lx"] / 2, B["ly"] / 2, B["h"] - 0.1)))
    core = ico("E_core", 1.15 * s, (0, 0, z0 + 0.5 * s), rough=0.4)
    flow(core, 'BOTH', 1, 2, dens=2.4, temp=2.3, fuel=0.9, color=DARK[0], vn=30.0 * v, vinit=(5.0 * v, 0, 9.0 * v))
    soot = ico("E_soot", 1.7 * s, (0, 0, z0 + 0.8 * s), rough=0.45)
    flow(soot, 'SMOKE', 2, 8, dens=3.4, temp=1.0, color=DARK[0], vn=16.0 * v, vinit=(3.0 * v, 0, 13.0 * v))
    column = ico("E_column", 1.05 * s, (0, 0, z0 + 1.2 * s), rough=0.35)
    flow(column, 'SMOKE', 4, 18, dens=2.8, temp=1.4, color=DARK[1], vn=5.0, vinit=(1.5 * v, 0, 11.0 * v))
    conc = ico("E_concrete", 1.0, (0, 0, z0 * 0.6), rough=0.4, scale=(B["lx"] * 0.42, B["ly"] * 0.42, 1.4))        # pulverised concrete
    flow(conc, 'SMOKE', 2, 9, dens=2.2, temp=0.3, color=DUST[0], vn=6.0 * v, vinit=(1.0, 0, 5.0 * v))
    skirt = torus("E_skirt", 3.4 * s, 0.6 * s, (0, 0, 0.5 * s), lobes=0.30)                                          # the earth bank blown outwards
    flow(skirt, 'SMOKE', 1, 4, dens=1.5, temp=0.30, color=SAND[1], vn=22.0 * v, vinit=(1.0, 0, 3.0 * v))
    sheet = ico("E_sheet", 1.0, (0, 0, 0.12), rough=0.5, scale=(8.0 * s, 8.0 * s, 0.05))
    flow(sheet, 'SMOKE', 3, 5, dens=0.22, temp=0.12, color=SAND[2], vn=1.0, vinit=(0, 0, 1.4))
    for i in range(34):
        az = random.uniform(0, math.tau); el = math.radians(random.uniform(14, 80))
        d = (math.cos(az) * math.cos(el), math.sin(az) * math.cos(el), math.sin(el))
        jet("E_j%02d" % i, (1.6 * s * d[0], 1.4 * s * d[1], 1.0 + z0 * 0.7 * d[2]), d, random.uniform(30, 66) * v, random.uniform(2.6, 4.6), random.randint(16, 40),
            random.uniform(0.36, 0.62) * s * 0.75, random.choice(SAND + DUST + DARK[:2]), dens=1.9)

if __name__ == "__main__":
    kind, cache_dir, res, frames = sys.argv[1], os.path.abspath(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4])
    noise = len(sys.argv) > 5 and sys.argv[5] == "1"
    random.seed(41 if kind == "mk82" else 43)
    msim.DOMAINS["v_" + kind] = (SIZE[kind], (3.0, 0.0))
    bpy.ops.wm.read_factory_settings(use_empty=True)
    dom = msim.make_domain("v_" + kind, cache_dir, res, frames, noise)
    d = dom.modifiers["Fluid"].domain_settings
    d.burning_rate = 3.6; d.flame_smoke = 2.4; d.flame_smoke_color = (0.10, 0.095, 0.09)
    build(kind)
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
