"""Bake the two Mantaflow gas sims of the GBU-28 bursting in the buried chamber to OpenVDB caches.

  python3 gsim.py out <cache_dir> <resolution> <frames> [noise 0|1]     seen from the surface
  python3 gsim.py in  <cache_dir> <resolution> <frames> [noise 0|1]     the section through the bunker

out   one frame = 1/60 s, frame 1 = the bomb touching the ground; the charge fires on frame 5 (0.060 s later), 20 m
      down.  A spurt of soil at the hole; then, with nothing to see of the burst itself, smoke driven up the two air
      shafts, out of the entrance and back up the hole.
in    one frame = 1/240 s, frame 1 = the charge firing.  A thin slab of space on the plane of the section in which the
      chambers, corridors, stair, air shafts and the bomb's hole are hollows in a solid block: the fire fills the
      target chamber and is driven along the corridors into the next chamber, up the stair and up the shafts.
286 kg of explosive in a closed chamber: where the gas goes is right; how fast and how bright is staging (the sources
are placed by hand along its way).
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
from util import new_mesh, new_obj
import gconst as C, gsite

SOIL = [(0.50, 0.41, 0.29), (0.43, 0.35, 0.25), (0.57, 0.49, 0.37)]; DUST = [(0.60, 0.58, 0.54), (0.50, 0.48, 0.45), (0.55, 0.50, 0.44)]
A0, A1 = C.ROOM_A; B0, B1 = C.ROOM_B; ZF = C.Z_FLOOR; ZC = C.Z_CEIL; CH = C.COR_H; CW = C.COR_W; S0 = C.STAIR_X[0]; VENTS = gsite.VENTS; VR = gsite.VR; HUT = gsite.HUT; ST_H = gsite.ST_H
OUT_BOX = ((-52.0, 34.0), (-16.0, 16.0), (-0.15, 30.0)); IN_BOX = ((-42.0, 32.0), (-3.3, 0.3), (-23.4, 9.0))
OUT_DT = 1.0 / 60.0; IN_DT = 1.0 / 240.0; OUT_DET = 5

def _place(dom, box):
    (x0, x1), (y0, y1), (z0, z1) = box; dom.scale = (x1 - x0, y1 - y0, z1 - z0); dom.location = ((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2)

def build_out():
    f0 = OUT_DET; up = -C.U
    puff = ico("E_puff", 1.1, (0, 0, 0.7), rough=0.4)                                                        # 2 t at 440 m/s goes in: soil thrown up round the hole
    flow(puff, 'SMOKE', 1, 4, dens=1.8, temp=0.25, color=SOIL[0], vn=14.0, vinit=tuple(up * 16.0))
    for i in range(22):
        az = random.uniform(0, math.tau); el = math.radians(random.uniform(35, 82)); d = (math.cos(az) * math.cos(el), math.sin(az) * math.cos(el), math.sin(el))
        jet("E_i%02d" % i, (0.5 * d[0], 0.5 * d[1], 0.4), d, random.uniform(16, 42), random.uniform(2.4, 4.0), random.randint(18, 40), random.uniform(0.34, 0.6), random.choice(SOIL), start=random.randint(1, 3), dens=1.8)
    hole = ico("E_hole", 0.6, (0, 0, 0.5), rough=0.3)                                                        # later: smoke back up the bomb's own hole
    flow(hole, 'SMOKE', f0 + 14, f0 + 150, dens=1.4, temp=1.8, color=DARK[1], vn=2.0, vinit=tuple(up * 14.0))
    for k, xv in enumerate(VENTS):                                                                          # the air shafts: a hard jet, then steady smoke
        t0 = f0 + (5 if k == 0 else 9)
        v1 = ico("E_vent%da" % k, 0.5, (xv, 0, 1.6), rough=0.2); flow(v1, 'BOTH', t0, t0 + 4, dens=2.2, temp=2.0, fuel=0.5, color=DARK[0], vn=2.0, vinit=(0.0, 0.0, 70.0))
        v2 = ico("E_vent%db" % k, 0.55, (xv, 0, 1.7), rough=0.2); flow(v2, 'SMOKE', t0 + 3, t0 + 60, dens=2.4, temp=1.8, color=DARK[0], vn=2.0, vinit=(0.0, 0.0, 34.0))
        v3 = ico("E_vent%dc" % k, 0.5, (xv, 0, 1.6), rough=0.2); flow(v3, 'SMOKE', t0 + 60, 400, dens=1.0, temp=2.2, color=DARK[1], vn=1.0, vinit=(0.0, 0.0, 13.0))
    t0 = f0 + 10; mx = HUT[0] - 1.0                                                                          # the entrance: flame, then smoke, out of the doorway
    m1 = ico("E_mouth", 0.95, (mx, 0.0, 1.2), rough=0.3); flow(m1, 'BOTH', t0, t0 + 5, dens=2.4, temp=2.2, fuel=0.8, color=DARK[0], vn=8.0, vinit=(-60.0, 0.0, 6.0))
    m2 = ico("E_mouth2", 1.0, (mx - 0.3, 0.0, 1.3), rough=0.35); flow(m2, 'SMOKE', t0 + 4, t0 + 60, dens=2.6, temp=1.0, color=DARK[0], vn=4.0, vinit=(-24.0, 0.0, 4.0))
    m3 = ico("E_mouth3", 0.9, (mx, 0.0, 1.5), rough=0.35); flow(m3, 'SMOKE', t0 + 60, 400, dens=1.0, temp=2.0, color=DARK[1], vn=1.0, vinit=(-4.0, 0.0, 5.0))
    hut = msim.box("E_hut", (HUT[0], -(CW / 2 + 0.5), 0.0), (HUT[1], CW / 2 + 0.5, 3.0)); collider(hut)

def _cut(ob, cutter):
    m = ob.modifiers.new("b", 'BOOLEAN'); m.operation = 'DIFFERENCE'; m.object = cutter; m.solver = 'EXACT'

def build_in():
    U = C.U; (x0, x1), (y0, y1), (z0, z1) = IN_BOX; yf = y1 + 1.0
    solid = msim.box("E_solid", (x0 - 1.5, y0 - 0.4, z0 - 1.0), (x1 + 1.5, y1 + 0.4, 0.0))               # everything below the surface; above it is open air
    cut = [msim.box("E_ra", (A0, -3.2, ZF), (A1, yf, ZC)), msim.box("E_rb", (B0, -3.2, ZF), (B1, yf, ZC)), msim.box("E_c1", (S0 - 0.3, -CW, ZF), (A0 + 0.05, yf, ZF + CH)), msim.box("E_c2", (A1 - 0.05, -CW, ZF), (B0 + 0.05, yf, ZF + CH))]
    for k, xv in enumerate(VENTS):
        cut.append(msim.box("E_v%d" % k, (xv - VR, -2 * VR, ((ZF + CH) if k == 0 else ZC) - 0.05), (xv + VR, yf, 0.5)))
    L_ = (S0 - HUT[0]) * math.sqrt(2.0); st = msim.box("E_st", (0, 0, 0), (1, 1, 1)); hh = ST_H / math.sqrt(2.0); st.scale = (L_ + 1.0, CW + yf, hh)           # the stair, a box laid on the 45 degree slope
    mid = np.array([(S0 + HUT[0]) / 2, (-CW + yf) / 2, ZF + (S0 - HUT[0]) / 2 + ST_H / 2]); st.location = tuple(mid); st.rotation_euler = (0, math.radians(45.0), 0); cut.append(st)
    sa, sb = -1.0, C.layer_at("floor")[3] + 0.3; ch = msim.box("E_chan", (0, 0, 0), (1, 1, 1)); ch.scale = (sb - sa, 0.5 + yf, 0.9); ch.location = tuple(U * (sa + sb) / 2 + np.array([0.0, (-0.5 + yf) / 2, 0.0])); ch.rotation_euler = (0, math.radians(C.DIVE), 0); cut.append(ch)
    for c in cut:
        _cut(solid, c)
    bpy.context.view_layer.update(); dg = bpy.context.evaluated_depsgraph_get(); me = bpy.data.meshes.new_from_object(solid.evaluated_get(dg))
    collider(new_obj("E_collider", me))
    for o in [solid] + cut:
        bpy.data.objects.remove(o, do_unlink=True)
    B = C.BURST; yb = -0.9; zm = ZF + 1.3
    core = ico("E_core", 0.9, (B[0], yb, B[2]), rough=0.35); flow(core, 'BOTH', 1, 4, dens=2.2, temp=2.4, fuel=1.0, color=DARK[0], vn=80.0)
    for k, (dx, v) in enumerate(((-3.5, (-75.0, 0, 5.0)), (3.5, (75.0, 0, 5.0)), (0.0, (0.0, 0, 50.0)))):                                      # the fireball spreading along the chamber
        fb = ico("E_fb%d" % k, 1.0, (B[0] + dx, yb - 0.3, zm + 0.6), rough=0.4); flow(fb, 'BOTH', 2, 10, dens=2.0, temp=2.2, fuel=0.85, color=DARK[0], vn=30.0, vinit=v)
    soot = ico("E_soot", 1.0, ((A0 + A1) / 2, -1.4, ZF + 2.0), rough=0.4, scale=(6.0, 1.2, 1.6)); flow(soot, 'SMOKE', 6, 44, dens=2.8, temp=1.0, color=DARK[0], vn=8.0)
    dust = ico("E_dust", 1.0, ((A0 + A1) / 2, -1.6, ZF + 2.0), rough=0.3, scale=(6.4, 1.3, 1.7)); flow(dust, 'SMOKE', 40, 200, dens=1.8, temp=0.4, color=DUST[0], vn=3.0)
    def push(name, p, v, t0, hot=10, smoke=120, r=0.8):
        """A source on the gas's way: flame for a few frames from t0, then smoke."""
        a = ico("E_%sa" % name, r, p, rough=0.3); flow(a, 'BOTH', t0, t0 + hot, dens=2.2, temp=2.2, fuel=0.75, color=DARK[0], vn=5.0, vinit=v)
        b = ico("E_%sb" % name, r, p, rough=0.3); flow(b, 'SMOKE', t0 + hot - 2, t0 + smoke, dens=2.4, temp=1.0, color=DARK[0], vn=3.0, vinit=tuple(0.3 * np.array(v)))
    yc = -0.6; zc_ = ZF + CH / 2
    push("cb1", (A1 + 0.5, yc, zc_), (95.0, 0, 0), 4); push("cb2", (A1 + 4.5, yc, zc_), (85.0, 0, 0), 9); push("rb1", (B0 + 0.8, yc - 0.3, zc_ + 0.3), (70.0, 0, 8.0), 14, hot=12, smoke=200, r=1.0)
    push("rb2", (B0 + 6.0, yc - 0.6, ZF + 2.0), (40.0, 0, 6.0), 26, hot=10, smoke=220, r=1.2)
    push("cs1", (A0 - 0.5, yc, zc_), (-95.0, 0, 0), 4); push("cs2", (A0 - 5.0, yc, zc_), (-85.0, 0, 0), 10)
    n_st = 4
    for k in range(n_st):                                                                                                                      # up the stair
        u = (k + 0.5) / n_st; xs_ = S0 - u * (S0 - HUT[0]); push("st%d" % k, (xs_, yc, ZF + (S0 - xs_) + ST_H / 2), (-55.0, 0, 55.0), 16 + 9 * k, hot=8, smoke=150)
    push("v0", (VENTS[0], -0.2, ZF + CH + 1.5), (0, 0, 80.0), 9, hot=8, smoke=160, r=0.4); push("v0b", (VENTS[0], -0.2, -8.0), (0, 0, 70.0), 20, hot=5, smoke=170, r=0.4)
    push("v1", (VENTS[1], -0.2, ZC + 1.5), (0, 0, 80.0), 30, hot=6, smoke=200, r=0.4); push("v1b", (VENTS[1], -0.2, -8.0), (0, 0, 70.0), 42, hot=4, smoke=210, r=0.4)
    hp = U * (C.layer_at("roof")[3] - 0.6); push("ho", (hp[0], -0.05, hp[2]), tuple(-U * 85.0), 3, hot=8, smoke=130, r=0.42)                        # and back up the bomb's hole
    hp = U * 8.0; push("ho2", (hp[0], -0.05, hp[2]), tuple(-U * 70.0), 16, hot=3, smoke=150, r=0.42)
    late = ico("E_late", 1.0, (B[0], -1.5, ZF + 1.2), rough=0.4, scale=(5.0, 1.2, 1.0)); flow(late, 'SMOKE', 200, 600, dens=1.2, temp=0.6, color=DARK[1], vn=1.0)

if __name__ == "__main__":
    kind = sys.argv[1]; cache_dir, res, frames = os.path.abspath(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4])
    noise = len(sys.argv) > 5 and sys.argv[5] == "1"
    random.seed(81 if kind == "out" else 83)
    msim.TIME_SCALE = 0.4 if kind == "out" else 0.1; msim.DT = OUT_DT if kind == "out" else IN_DT
    msim.DOMAINS["g_" + kind] = ((1.0, 1.0, 1.0), (0.0, 0.0))
    bpy.ops.wm.read_factory_settings(use_empty=True)
    dom = msim.make_domain("g_" + kind, cache_dir, res, frames, noise); _place(dom, OUT_BOX if kind == "out" else IN_BOX)
    d = dom.modifiers["Fluid"].domain_settings
    d.burning_rate = 3.4; d.flame_smoke = 2.2; d.flame_smoke_color = (0.10, 0.095, 0.09)
    if kind == "in":
        d.use_collision_border_bottom = False; d.use_collision_border_front = True; d.use_collision_border_back = True; d.vorticity = 0.3; d.burning_rate = 1.6; d.timesteps_max = 8; d.cfl_condition = 3.0
        build_in()
    else:
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
