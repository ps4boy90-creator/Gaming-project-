"""Bake the Mantaflow gas sim of the MOAB bursting just above the valley floor to an OpenVDB cache.

  python3 asim.py out <cache_dir> <resolution> <frames> [noise 0|1]     1 frame = 1/40 s, frame 1 = the burst

A fireball about 70 m across (the usual rule of thumb for a charge of this weight, aconst.FB_D), a skirt of dust
driven outwards along the ground by a ring of thrown sources (wide flat sources were tried for the dust that the front
raises, and came out as hard-edged plates), and the hot gas rising afterwards into a head on a stem: the released film of the
2017 strike shows a cloud of that kind climbing out of the valley.  The valley's ground is in the simulation as a
solid, so the dust runs along the floor and up the slopes.  Sizes of the cloud, speeds and brightness are staging;
the buildings and trees are not in the simulation (they are moved separately, see asite).
"""
import bpy, sys, math, random, os
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
for p in ("grenade-explosion", "mortar-explosion", "howitzer-explosion", "reaper-hellfire", "tomahawk-sub"):
    sys.path.insert(0, os.path.join(HERE, "..", p))
sys.path.insert(0, HERE)
import manta_fix  # noqa: F401
import msim
from msim import flow, ico, jet, torus, collider, DARK
from util import new_mesh, new_obj, grid_faces
import aconst as C
if C.SITE == "city":
    import acity as asite
else:
    import asite

SOIL = [(0.33, 0.265, 0.185), (0.39, 0.315, 0.225), (0.28, 0.225, 0.16)]; PALE = [(0.46, 0.41, 0.34), (0.41, 0.365, 0.30), (0.50, 0.45, 0.38)]      # the valley's own earth, a little darker than it lies in the sun
BOX = ((-250.0, 250.0), (-290.0, 230.0), (-8.0, 400.0)); DT = 1.0 / 40.0

def _block(name, xs, ys, zb):
    """The ground as a closed solid: its surface on top, a flat bottom, upright sides."""
    X, Y = np.meshgrid(xs, ys, indexing="ij"); nx, ny = len(xs), len(ys); top = np.stack([X, Y, asite.ground(X, Y)], -1).reshape(-1, 3); bot = top.copy(); bot[:, 2] = zb; n = nx * ny
    F = [grid_faces(nx, ny), grid_faces(nx, ny, offset=n, flip=True)]; idx = lambda i, j: i * ny + j
    ring = [idx(i, 0) for i in range(nx)] + [idx(nx - 1, j) for j in range(1, ny)] + [idx(i, ny - 1) for i in range(nx - 2, -1, -1)] + [idx(0, j) for j in range(ny - 2, 0, -1)]
    r = np.array(ring); r1 = np.roll(r, -1); F.append(np.stack([r, r + n, r1 + n, r1], 1))
    return new_obj(name, new_mesh(name, np.vstack([top, bot]), F, smooth=False))

def thermal(name, r0, r1, z0, rise, tau, start, end, color, dens, temp):
    """A source that climbs: the ball of burnt gas going up, slowing as it cools, growing from radius r0 to r1."""
    e = ico(name, 1.0, (0, 0, z0), sub=2, rough=0.25)
    for fr in range(start, end + 2):
        t = (fr - start) * msim.DT; u = 1 - math.exp(-t / tau); r = r0 + (r1 - r0) * u
        e.location = (0, 0, z0 + rise * u); e.keyframe_insert("location", frame=fr); e.scale = (r, r, 0.75 * r); e.keyframe_insert("scale", frame=fr)
    flow(e, 'SMOKE', start, end, dens=dens, temp=temp, color=color, vn=3.0, vfac=1.0, sub=2)

def build(frames):
    FB = C.FB_D; g = lambda x, y: float(asite.ground(x, y))
    (x0, x1), (y0, y1), (z0, z1) = BOX; collider(_block("E_ground", np.arange(x0 - 12.0, x1 + 12.1, 4.0), np.arange(y0 - 12.0, y1 + 12.1, 4.0), z0 - 30.0))
    core = ico("E_core", 0.11 * FB, (0, 0, C.HOB + 5.0), rough=0.06); flow(core, 'BOTH', 1, 2, dens=1.6, temp=2.8, fuel=1.0, color=PALE[0], vn=70.0)
    push = torus("E_push", 15.0, 5.5, (0, 0, 6.0), lobes=0.04); push.scale = (1.0, 1.0, 0.7); flow(push, 'SMOKE', 1, 4, dens=0.8, temp=0.6, color=SOIL[1], vn=120.0)      # the first rush outwards along the ground, even all round
    fb2 = ico("E_fb2", 0.17 * FB, (0, 0, 12.0), rough=0.12, scale=(1.3, 1.3, 0.85)); flow(fb2, 'BOTH', 2, 6, dens=1.8, temp=2.8, fuel=0.95, color=PALE[1], vn=55.0, vinit=(0, 0, 48.0))
    n = 96
    for i in range(n):                                                                   # the skirt along the ground: dust
        az = 2 * math.pi * (i + random.uniform(-0.3, 0.3)) / n; el = math.radians(random.uniform(2, 14)); d = (math.cos(az) * math.cos(el), math.sin(az) * math.cos(el), math.sin(el) + 0.45 * max(math.sin(az), 0.0))     # towards the northern slope it has to climb
        jet("E_s%02d" % i, (9 * d[0], 9 * d[1], 2.5), d, random.uniform(270, 350), random.uniform(2.2, 2.8), random.randint(34, 48), random.uniform(4.0, 5.6), random.choice(SOIL + PALE), start=random.randint(1, 3), dens=1.0, zmin=2.0)
    for i in range(22):                                                                  # earth thrown higher
        az = random.uniform(0, math.tau); el = math.radians(random.uniform(30, 75)); d = (math.cos(az) * math.cos(el), math.sin(az) * math.cos(el), math.sin(el))
        jet("E_u%02d" % i, (6 * d[0], 6 * d[1], 6.0), d, random.uniform(120, 230), random.uniform(1.8, 2.8), random.randint(26, 48), random.uniform(2.8, 4.4), random.choice(SOIL), start=random.randint(1, 3), dens=1.3, zmin=2.0)
    ring2 = torus("E_ring2", 22.0, 7.0, (0, 0, 8.0), lobes=0.08); flow(ring2, 'SMOKE', 2, 9, dens=1.4, temp=0.9, color=SOIL[1], vn=14.0, vinit=(0, 0, 16.0))
    thermal("E_head", 17.0, 42.0, 22.0, C.CLOUD_10S - 62.0, 5.5, 6, frames, DARK[2], 1.1, 2.6)                    # the burnt gas, hot and light, climbs
    thermal("E_neck", 10.0, 17.0, 13.0, 0.55 * (C.CLOUD_10S - 62.0), 5.5, 8, frames, PALE[1], 0.9, 2.0)
    stem = ico("E_stem", 10.0, (0, 0, 10.0), rough=0.3, scale=(1.2, 1.2, 0.7)); flow(stem, 'SMOKE', 5, 240, dens=1.2, temp=3.0, color=PALE[1], vn=3.0, vinit=(0, 0, 44.0))

if __name__ == "__main__":
    kind = sys.argv[1]; cache_dir, res, frames = os.path.abspath(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4])
    noise = len(sys.argv) > 5 and sys.argv[5] == "1"
    random.seed(47)
    msim.DT = DT; msim.TIME_SCALE = msim.DT * 24.0
    msim.DOMAINS["a_out"] = ((1.0, 1.0, 1.0), (0.0, 0.0))
    bpy.ops.wm.read_factory_settings(use_empty=True)
    dom = msim.make_domain("a_out", cache_dir, res, frames, noise)
    (x0, x1), (y0, y1), (z0, z1) = BOX; dom.scale = (x1 - x0, y1 - y0, z1 - z0); dom.location = ((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2)
    d = dom.modifiers["Fluid"].domain_settings
    d.beta = 3.2; d.burning_rate = 2.6; d.flame_smoke = 1.8; d.flame_smoke_color = (0.42, 0.39, 0.35); d.vorticity = 0.35; d.timesteps_max = 8; d.use_collision_border_bottom = False
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
