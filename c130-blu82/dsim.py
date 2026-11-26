"""Bake the two Mantaflow gas sims of the BLU-82 bursting just above the jungle floor to OpenVDB caches.

  python3 dsim.py out <cache_dir> <resolution> <frames> [noise 0|1]     the burst seen from a distance, 1 frame = 1/40 s
  python3 dsim.py sec <cache_dir> <resolution> <frames> [noise 0|1]     the first second, for the section, 1 frame = 1/240 s

Frame 1 = the burst.  A fireball a few metres above the ground, a skirt of dust and shredded wood driven outwards
along the ground, and the hot gas rising afterwards on a stem.  The fireball is sized by the usual rule of thumb for a
charge of this weight (about 62 m across, dconst.FB_D); published accounts describe a mushroom cloud that was taken
for a nuclear one, so the hot gas is made to climb some 250 m in ten seconds.  Speeds and brightness are staging, and the
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
BOX = {"out": ((-190.0, 190.0), (-190.0, 190.0), (-0.3, 380.0)), "sec": ((-125.0, 125.0), (-78.0, 78.0), (-0.3, 125.0))}
DTS = {"out": 1.0 / 40.0, "sec": 1.0 / 240.0}

def thermal(name, r0, r1, z0, rise, tau, start, end, color, dens, temp):
    """A source that climbs: the ball of burnt gas going up, slowing as it cools (z0 + rise * (1 - exp(-t / tau))), growing from
    radius r0 to r1.  The gas it gives off takes its speed, so the cloud rolls up into a head on a stem."""
    e = ico(name, 1.0, (0, 0, z0), sub=2, rough=0.25)
    for fr in range(start, end + 2):
        t = (fr - start) * msim.DT; u = 1 - math.exp(-t / tau); r = r0 + (r1 - r0) * u
        e.location = (0, 0, z0 + rise * u); e.keyframe_insert("location", frame=fr); e.scale = (r, r, 0.75 * r); e.keyframe_insert("scale", frame=fr)
    flow(e, 'SMOKE', start, end, dens=dens, temp=temp, color=color, vn=3.0, vfac=1.0, sub=2)

def build(kind, frames):
    k = DTS["out"] / DTS[kind]; F = lambda fr: max(1, int(round(fr * k))); FB = C.FB_D        # frame numbers below are for the "out" clock; FB: the fireball, about 62 m across
    core = ico("E_core", 0.11 * FB, (0, 0, C.HOB + 4.0), rough=0.3); flow(core, 'BOTH', 1, F(2), dens=1.6, temp=2.8, fuel=1.0, color=PALE[0], vn=140.0)
    fb2 = ico("E_fb2", 0.17 * FB, (0, 0, 10.0), rough=0.35, scale=(1.3, 1.3, 0.85)); flow(fb2, 'BOTH', F(2), F(6), dens=1.8, temp=2.8, fuel=0.95, color=PALE[1], vn=50.0, vinit=(0, 0, 45.0))
    n = 44
    for i in range(n):                                                                   # the skirt along the ground: soil dust and shredded wood
        az = 2 * math.pi * (i + random.uniform(-0.3, 0.3)) / n; el = math.radians(random.uniform(2, 16) if kind == "out" else random.uniform(3, 38)); d = (math.cos(az) * math.cos(el), math.sin(az) * math.cos(el), math.sin(el))        # seen edge-on in the section a low skirt reads as a flat sheet: spread it higher there
        jet("E_s%02d" % i, (8 * d[0], 8 * d[1], 2.0), d, random.uniform(210, 340), random.uniform(2.2, 3.2), F(random.randint(30, 46)), random.uniform(3.5, 5.5), random.choice(SOIL + PALE + LEAF), start=F(random.randint(1, 3)), dens=1.5 if kind == "out" else 1.0, zmin=2.0)
    for i in range(20):                                                                  # stuff thrown higher
        az = random.uniform(0, math.tau); el = math.radians(random.uniform(30, 75)); d = (math.cos(az) * math.cos(el), math.sin(az) * math.cos(el), math.sin(el))
        jet("E_u%02d" % i, (5 * d[0], 5 * d[1], 5.0), d, random.uniform(110, 210), random.uniform(1.8, 2.8), F(random.randint(26, 48)), random.uniform(2.6, 4.0), random.choice(SOIL + LEAF), start=F(random.randint(1, 3)), dens=1.3, zmin=2.0)
    ring = torus("E_ring", 36.0, 5.0, (0, 0, 8.0)); flow(ring, 'SMOKE', F(3), F(12), dens=1.1, temp=0.6, color=LEAF[0], vn=10.0, vinit=(0, 0, 9.0))               # the forest inside the circle, in pieces
    ring2 = torus("E_ring2", 18.0, 6.0, (0, 0, 7.0)); flow(ring2, 'SMOKE', F(2), F(9), dens=1.4, temp=0.9, color=SOIL[1], vn=14.0, vinit=(0, 0, 16.0))
    # the burnt gas, hot and light, climbs: top about C.CLOUD_10S after ten seconds (staging, see dconst)
    thermal("E_head", 15.0, 36.0, 20.0, C.CLOUD_10S - 55.0, 5.5, F(6), frames, DARK[2], 1.1, 2.6)
    thermal("E_neck", 9.0, 15.0, 12.0, 0.55 * (C.CLOUD_10S - 55.0), 5.5, F(8), frames, PALE[1], 0.9, 2.0)
    stem = ico("E_stem", 9.0, (0, 0, 9.0), rough=0.3, scale=(1.2, 1.2, 0.7)); flow(stem, 'SMOKE', F(5), F(240), dens=1.2, temp=3.0, color=PALE[1], vn=3.0, vinit=(0, 0, 42.0))            # dust drawn up after it
    dust = ico("E_dust", 1.0, (0, 0, 3.0), rough=0.25, scale=(44.0, 44.0, 2.6)); flow(dust, 'SMOKE', F(8), F(90), dens=0.45, temp=0.3, color=PALE[0], vn=1.5)   # dust hanging over the clearing

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
    d.beta = 3.2; d.burning_rate = 2.6 if kind == "out" else 1.4; d.flame_smoke = 1.8; d.flame_smoke_color = (0.42, 0.39, 0.35); d.vorticity = 0.35; d.timesteps_max = 8
    build(kind, frames)
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
