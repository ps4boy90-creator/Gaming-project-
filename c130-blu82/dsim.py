"""Bake the two Mantaflow gas sims of the BLU-82 bursting just above the jungle floor to OpenVDB caches.

  python3 dsim.py out <cache_dir> <resolution> <frames> [noise 0|1]     the burst seen from a distance, 1 frame = 1/40 s
  python3 dsim.py sec <cache_dir> <resolution> <frames> [noise 0|1]     the first second, for the section, 1 frame = 1/240 s

Frame 1 = the burst.  A fireball a few metres above the ground, a skirt of dust and shredded wood driven outwards
along the ground, and the hot gas rising afterwards on a stem.  The sizes follow photographs of BLU-82 bursts on open
ranges (a fireball some tens of metres across, then a pale, wide cloud); speeds and brightness are staging, and the
trees are not in the simulation (they are moved separately, see djungle).
"""
import bpy, sys, math, random, os
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
for p in ("grenade-explosion", "mortar-explosion", "howitzer-explosion", "reaper-hellfire"):
    sys.path.insert(0, os.path.join(HERE, "..", p))
sys.path.insert(0, HERE)
import manta_fix  # noqa: F401
import msim
from msim import flow, ico, jet, torus, DARK
import dconst as C

SOIL = [(0.42, 0.30, 0.20), (0.50, 0.38, 0.27), (0.36, 0.27, 0.18)]; PALE = [(0.62, 0.58, 0.52), (0.55, 0.50, 0.44), (0.66, 0.63, 0.58)]; LEAF = [(0.20, 0.19, 0.13), (0.25, 0.22, 0.16)]
BOX = {"out": ((-140.0, 140.0), (-140.0, 140.0), (-0.3, 200.0)), "sec": ((-115.0, 115.0), (-70.0, 70.0), (-0.3, 105.0))}
DTS = {"out": 1.0 / 40.0, "sec": 1.0 / 240.0}

def build(kind):
    k = DTS["out"] / DTS[kind]; F = lambda fr: max(1, int(round(fr * k)))                 # frame numbers below are for the "out" clock
    core = ico("E_core", 7.0, (0, 0, C.HOB + 3.0), rough=0.3); flow(core, 'BOTH', 1, F(2), dens=1.6, temp=2.6, fuel=1.0, color=PALE[0], vn=150.0)
    fb2 = ico("E_fb2", 11.0, (0, 0, 9.0), rough=0.35, scale=(1.3, 1.3, 0.8)); flow(fb2, 'BOTH', F(2), F(5), dens=1.8, temp=2.6, fuel=0.9, color=PALE[1], vn=60.0, vinit=(0, 0, 40.0))
    n = 34
    for i in range(n):                                                                   # the skirt along the ground: soil dust and shredded wood
        az = 2 * math.pi * (i + random.uniform(-0.3, 0.3)) / n; el = math.radians(random.uniform(2, 16) if kind == "out" else random.uniform(3, 38)); d = (math.cos(az) * math.cos(el), math.sin(az) * math.cos(el), math.sin(el))        # seen edge-on in the section a low skirt reads as a flat sheet: spread it higher there
        jet("E_s%02d" % i, (6 * d[0], 6 * d[1], 2.0), d, random.uniform(170, 300), random.uniform(3.2, 4.6), F(random.randint(26, 40)), random.uniform(3.0, 4.6), random.choice(SOIL + PALE + LEAF), start=F(random.randint(1, 3)), dens=1.5 if kind == "out" else 1.0, zmin=2.0)
    for i in range(16):                                                                  # stuff thrown higher
        az = random.uniform(0, math.tau); el = math.radians(random.uniform(30, 75)); d = (math.cos(az) * math.cos(el), math.sin(az) * math.cos(el), math.sin(el))
        jet("E_u%02d" % i, (4 * d[0], 4 * d[1], 4.0), d, random.uniform(90, 170), random.uniform(2.0, 3.2), F(random.randint(24, 44)), random.uniform(2.2, 3.4), random.choice(SOIL + LEAF), start=F(random.randint(1, 3)), dens=1.3, zmin=2.0)
    ring = torus("E_ring", 30.0, 4.5, (0, 0, 7.0)); flow(ring, 'SMOKE', F(3), F(11), dens=1.1, temp=0.6, color=LEAF[0], vn=10.0, vinit=(0, 0, 9.0))               # the forest inside the circle, in pieces
    ring2 = torus("E_ring2", 15.0, 5.0, (0, 0, 6.0)); flow(ring2, 'SMOKE', F(2), F(8), dens=1.4, temp=0.8, color=SOIL[1], vn=14.0, vinit=(0, 0, 14.0))
    stem = ico("E_stem", 9.0, (0, 0, 8.0), rough=0.3, scale=(1.2, 1.2, 0.7)); flow(stem, 'SMOKE', F(4), F(110), dens=1.5, temp=3.0, color=DARK[2], vn=4.0, vinit=(0, 0, 48.0))
    dust = ico("E_dust", 1.0, (0, 0, 3.0), rough=0.25, scale=(34.0, 34.0, 2.6)); flow(dust, 'SMOKE', F(8), F(120), dens=0.7, temp=0.35, color=PALE[0], vn=1.5)   # dust hanging over the clearing

if __name__ == "__main__":
    kind = sys.argv[1]; cache_dir, res, frames = os.path.abspath(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4])
    noise = len(sys.argv) > 5 and sys.argv[5] == "1"
    random.seed(41)
    msim.DT = DTS[kind]; msim.TIME_SCALE = msim.DT * 24.0
    msim.DOMAINS["d_" + kind] = ((1.0, 1.0, 1.0), (0.0, 0.0))
    bpy.ops.wm.read_factory_settings(use_empty=True)
    dom = msim.make_domain("d_" + kind, cache_dir, res, frames, noise)
    (x0, x1), (y0, y1), (z0, z1) = BOX[kind]; dom.scale = (x1 - x0, y1 - y0, z1 - z0); dom.location = ((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2)
    d = dom.modifiers["Fluid"].domain_settings
    d.beta = 2.4; d.burning_rate = 2.6 if kind == "out" else 1.4; d.flame_smoke = 1.8; d.flame_smoke_color = (0.42, 0.39, 0.35); d.vorticity = 0.35; d.timesteps_max = 8
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
