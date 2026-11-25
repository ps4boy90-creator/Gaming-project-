"""Bake the Mantaflow gas sim of the Tallboy bursting under the depot's yard to an OpenVDB cache.

  python3 lsim.py out <cache_dir> <resolution> <frames> [noise 0|1]

One frame = 1/60 s, frame 1 = the bomb touching the ground: a spurt of soil where it goes in.  The charge fires on
frame 31 (0.5 s later), about 14 m down: the ground lifts, then a great mass of earth is thrown up and outwards
with the gas of the burst behind it, and a ring of dust is driven out along the ground.  There is little flame to see:
the charge is buried.
2,360 kg of Torpex at this depth: that it throws out a crater about 30 m across is published; the height and speed
of the column of earth are staging (the sources are placed by hand).
"""
import bpy, sys, math, random, os
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
for p in ("grenade-explosion", "mortar-explosion", "howitzer-explosion", "reaper-hellfire"):
    sys.path.insert(0, os.path.join(HERE, "..", p))
sys.path.insert(0, HERE)
import manta_fix  # noqa: F401
import msim
from msim import flow, ico, jet, collider, DARK
from util import new_mesh, new_obj, grid_faces
import lconst as C

SOIL = [(0.34, 0.26, 0.17), (0.27, 0.205, 0.135), (0.40, 0.32, 0.22), (0.22, 0.17, 0.115)]; DUST = [(0.56, 0.50, 0.41), (0.48, 0.42, 0.34)]
OUT_BOX = ((-130.0, 130.0), (-130.0, 130.0), (-0.15, 190.0)); OUT_DT = 1.0 / 60.0; OUT_DET = int(round(C.FUZE_DELAY / OUT_DT)) + 1
RC = C.CRATER_R

def _place(dom, box):
    (x0, x1), (y0, y1), (z0, z1) = box; dom.scale = (x1 - x0, y1 - y0, z1 - z0); dom.location = ((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2)

def build_out():
    f0 = OUT_DET; up = -C.U
    puff = ico("E_puff", 1.8, (0, 0, 1.0), rough=0.4)                                                        # five tons at 330 m/s goes into the ground: a spurt of soil
    flow(puff, 'SMOKE', 1, 5, dens=1.8, temp=0.25, color=SOIL[0], vn=16.0, vinit=tuple(up * 22.0))
    for i in range(18):
        az = random.uniform(0, math.tau); el = math.radians(random.uniform(35, 82)); d = (math.cos(az) * math.cos(el), math.sin(az) * math.cos(el), math.sin(el))
        jet("E_i%02d" % i, (0.6 * d[0], 0.6 * d[1], 0.5), d, random.uniform(20, 50), random.uniform(2.2, 3.6), random.randint(18, 36), random.uniform(0.5, 0.9), random.choice(SOIL), start=random.randint(1, 3), dens=1.6)
    dome = ico("E_dome", 1.0, (0, 0, 2.0), rough=0.3, scale=(RC * 0.8, RC * 0.8, 4.0)); flow(dome, 'SMOKE', f0, f0 + 5, dens=2.6, temp=0.4, color=SOIL[1], vn=20.0, vinit=(0.0, 0.0, 55.0))       # the ground lifting over the burst
    col = ico("E_col", 9.0, (0, 0, 6.0), rough=0.4); flow(col, 'SMOKE', f0 + 2, f0 + 16, dens=2.8, temp=1.0, color=SOIL[1], vn=30.0, vinit=(0.0, 0.0, 120.0))                                     # the column of earth
    fire = ico("E_fire", 6.0, (0, 0, 5.0), rough=0.4); flow(fire, 'BOTH', f0 + 3, f0 + 8, dens=2.0, temp=2.4, fuel=0.7, color=DARK[0], vn=40.0, vinit=(0.0, 0.0, 95.0))                            # the gas of the burst breaking through
    gas = ico("E_gas", 8.0, (0, 0, 7.0), rough=0.4); flow(gas, 'SMOKE', f0 + 6, f0 + 60, dens=2.2, temp=1.8, color=DARK[1], vn=10.0, vinit=(0.0, 0.0, 40.0))
    skirt = msim.torus("E_skirt", RC * 1.0, 3.2, (0, 0, 2.6), lobes=0.3); flow(skirt, 'SMOKE', f0 + 1, f0 + 14, dens=2.4, temp=0.3, color=DUST[0], vn=48.0)                                         # dust driven out along the ground
    for i in range(70):                                                                                     # earth thrown out, each mass trailing soil
        az = random.uniform(0, math.tau); el = math.radians(random.uniform(38, 87)); d = (math.cos(az) * math.cos(el), math.sin(az) * math.cos(el), math.sin(el)); r0 = random.uniform(2.0, RC * 0.7)
        jet("E_j%02d" % i, (r0 * math.cos(az), r0 * math.sin(az), 1.5), d, random.uniform(70, 175), random.uniform(1.0, 2.0), random.randint(50, 110), random.uniform(1.6, 3.2), random.choice(SOIL), start=f0 + random.randint(1, 5), dens=1.9)
    late = ico("E_late", 1.0, (0, 0, 1.0), rough=0.4, scale=(RC * 0.7, RC * 0.7, 3.0)); flow(late, 'SMOKE', f0 + 60, 900, dens=0.9, temp=0.8, color=DUST[1], vn=2.0, vinit=(0.0, 0.0, 5.0))

if __name__ == "__main__":
    kind = sys.argv[1]; cache_dir, res, frames = os.path.abspath(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4])
    noise = len(sys.argv) > 5 and sys.argv[5] == "1"
    random.seed(91)
    msim.TIME_SCALE = 0.4; msim.DT = OUT_DT
    msim.DOMAINS["l_" + kind] = ((1.0, 1.0, 1.0), (0.0, 0.0))
    bpy.ops.wm.read_factory_settings(use_empty=True)
    dom = msim.make_domain("l_" + kind, cache_dir, res, frames, noise); _place(dom, OUT_BOX)
    d = dom.modifiers["Fluid"].domain_settings
    d.burning_rate = 3.0; d.flame_smoke = 2.2; d.flame_smoke_color = (0.13, 0.115, 0.10); d.alpha = -0.05; d.beta = 0.9      # heavy with soil: it falls back
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
