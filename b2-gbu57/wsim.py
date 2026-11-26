"""Bake the two Mantaflow gas sims of the GBU-57 bursting in the buried hall to OpenVDB caches.

  python3 wsim.py out <cache_dir> <resolution> <frames> [noise 0|1]     the mountainside from outside
  python3 wsim.py in  <cache_dir> <resolution> <frames> [noise 0|1]     the section through the bunker

out   one frame = 1/60 s, frame 1 = the bomb touching the slope; the charge fires on frame 5.  A spurt of earth at the
      hole; gas back up the hole; dust forced out of the cover as the roof lifts; flame and smoke out of the tunnel
      and the ventilation shafts.
in    one frame = 1/240 s, frame 1 = the charge firing.  A slab of space on the plane of the section in which the hall,
      the tunnel and the bomb's hole are hollows in a solid block.
Adapted from the BLU-109 segment's psim for a bunker three times the size and ten times the charge.  Where the gas
goes follows the geometry; how fast and how bright is staging.
"""
import bpy, sys, math, random, os
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
for p in ("grenade-explosion", "mortar-explosion", "howitzer-explosion", "reaper-hellfire", "tomahawk-sub"):
    sys.path.insert(0, os.path.join(HERE, "..", p))
sys.path.insert(0, HERE)
import manta_fix  # noqa: F401
import msim
from msim import flow, ico, jet, collider, DARK
from util import new_mesh, new_obj, grid_faces
import wconst as C, wsite as psite

FILL = [(0.50, 0.41, 0.29), (0.43, 0.35, 0.25), (0.57, 0.49, 0.37)]; DUST = [(0.60, 0.58, 0.54), (0.50, 0.48, 0.45), (0.55, 0.50, 0.44)]
XF = psite.XF; ZF = C.Z_FLOOR; TW = C.TUN_W / 2
NRM = np.array([-math.sin(math.radians(C.SLOPE)), 0.0, math.cos(math.radians(C.SLOPE))])       # out of the slope
OUT_BOX = ((-150.0, 102.0), (-87.0, 87.0), (-39.0, 111.0)); IN_BOX = ((-66.0, 40.0), (-9.4, 0.8), (-27.0, 26.0)); HX = psite.HX; X0, X1 = C.ROOM_X
OUT_DT = 1.0 / 60.0; IN_DT = 1.0 / 240.0; OUT_DET = 5

def _block(name, xs, ys, zb):
    """The ground as a closed solid: its surface on top, a flat bottom, upright sides."""
    X, Y = np.meshgrid(xs, ys, indexing="ij"); nx, ny = len(xs), len(ys); top = np.stack([X, Y, psite.ground(X, Y)], -1).reshape(-1, 3); bot = top.copy(); bot[:, 2] = zb; n = nx * ny
    F = [grid_faces(nx, ny), grid_faces(nx, ny, offset=n, flip=True)]; idx = lambda i, j: i * ny + j
    ring = [idx(i, 0) for i in range(nx)] + [idx(nx - 1, j) for j in range(1, ny)] + [idx(i, ny - 1) for i in range(nx - 2, -1, -1)] + [idx(0, j) for j in range(ny - 2, 0, -1)]
    r = np.array(ring); r1 = np.roll(r, -1); F.append(np.stack([r, r + n, r1 + n, r1], 1))
    ob = new_obj(name, new_mesh(name, np.vstack([top, bot]), F, smooth=False)); return ob

def _place(dom, box):
    (x0, x1), (y0, y1), (z0, z1) = box; dom.scale = (x1 - x0, y1 - y0, z1 - z0); dom.location = ((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2)

def build_out():
    U = C.U; f0 = OUT_DET; up = -U
    collider(_block("E_ground", np.arange(-168.0, 120.01, 3.0), np.arange(-102.0, 102.01, 3.0), -54.0))
    puff = ico("E_puff", 2.2, NRM * 2.0, rough=0.4)                                                       # the bomb goes in: a spurt of dust from the hole
    flow(puff, 'SMOKE', 1, 4, dens=1.6, temp=0.25, color=FILL[0], vn=14.0, vinit=tuple(NRM * 14.0 + up * 20.0))
    vent = ico("E_vent", 1.6, NRM * 2.0, rough=0.3)                                                      # the charge fires: gas back up the hole
    flow(vent, 'BOTH', f0, f0 + 6, dens=2.2, temp=2.0, fuel=0.6, color=DARK[0], vn=6.0, vinit=tuple(up * 110.0))
    vent2 = ico("E_vent2", 1.7, NRM * 2.2, rough=0.3)
    flow(vent2, 'SMOKE', f0 + 6, f0 + 70, dens=2.2, temp=0.9, color=DARK[1], vn=3.0, vinit=tuple(up * 34.0))
    for k, (ex, ey) in enumerate(((HX, 0.0), (HX - 8.0, 5.0), (HX + 8.0, -4.5))):                                    # the cover lifts and breaks: dust out of the ground over the room
        heave = ico("E_heave%d" % k, 1.0, (ex, ey, float(psite.ground(ex, ey)) + 1.5), rough=0.4, scale=(14.0 if k == 0 else 8.0, 9.0 if k == 0 else 6.0, 0.9))
        heave.rotation_euler = (0, -math.radians(C.SLOPE), 0)
        flow(heave, 'SMOKE', f0 + 4 + 3 * k, f0 + 70, dens=1.3 if k == 0 else 1.0, temp=0.35, color=FILL[k % 3], vn=4.5, vinit=tuple(NRM * (9.0 - k)))
    for i in range(40):
        ex = random.uniform(X0 - 1.0, X1 + 1.0); ey = random.uniform(-9.0, 9.0); d = NRM + np.array([random.uniform(-0.45, 0.45), random.uniform(-0.5, 0.5), random.uniform(-0.1, 0.4)])
        jet("E_j%02d" % i, (ex, ey, float(psite.ground(ex, ey)) + 1.5), tuple(d), random.uniform(20, 60), random.uniform(1.6, 3.0), random.randint(30, 70), random.uniform(1.0, 1.9),
            random.choice(FILL + FILL + DUST + DARK[1:]), start=f0 + random.randint(3, 40), dens=1.8, zmin=-90.0)
    mouth = ico("E_mouth", 2.8, (XF - 3.5, 0.0, ZF + 3.0), rough=0.3, scale=(1.0, 0.95, 1.05))            # flame and smoke out of the tunnel
    flow(mouth, 'BOTH', f0 + 6, f0 + 14, dens=2.4, temp=2.2, fuel=0.8, color=DARK[0], vn=8.0, vinit=(-95.0, 0.0, 6.0))
    mouth2 = ico("E_mouth2", 3.0, (XF - 4.5, 0.0, ZF + 3.2), rough=0.35)
    flow(mouth2, 'SMOKE', f0 + 12, f0 + 80, dens=2.6, temp=1.0, color=DARK[0], vn=4.0, vinit=(-34.0, 0.0, 4.0))
    mouth3 = ico("E_mouth3", 2.6, (XF - 3.5, 0.0, ZF + 3.6), rough=0.35)
    flow(mouth3, 'SMOKE', f0 + 80, 400, dens=1.0, temp=1.1, color=DARK[1], vn=1.0, vinit=(-6.0, 0.0, 3.5))
    for k, (vx, vy) in enumerate(psite.VENTS):                                               # the two ventilation pipes
        pipe = ico("E_pipe%d" % k, 1.2, (vx, vy, float(psite.ground(vx, vy)) + 4.6), rough=0.2)
        flow(pipe, 'SMOKE', f0 + 2, f0 + 40, dens=2.0, temp=1.0, color=DARK[1], vn=2.0, vinit=(0.0, 0.0, 45.0))
    for i in range(10):                                                                                    # stones and dust thrown out of the hole
        d = up + np.array([random.uniform(-0.35, 0.35), random.uniform(-0.4, 0.4), random.uniform(-0.2, 0.3)])
        jet("E_h%02d" % i, tuple(NRM * 2.2), tuple(d), random.uniform(40, 90), random.uniform(1.6, 2.8), random.randint(30, 60), random.uniform(0.8, 1.3), random.choice(FILL + DARK[:2]), start=f0 + random.randint(0, 6), dens=1.8, zmin=-90.0)

def _cut(ob, cutter):
    m = ob.modifiers.new("b", 'BOOLEAN'); m.operation = 'DIFFERENCE'; m.object = cutter; m.solver = 'EXACT'

def _box(name, lo, hi):
    return msim.box(name, lo, hi)

def build_in():
    U = C.U; (x0, x1), (y0, y1), (z0, z1) = IN_BOX
    solid = _box("E_solid", (x0 - 1.5, y0 - 0.4, z0 - 1.0), (x1 + 1.5, y1 + 0.4, z1 + 1.5))
    xs = np.arange(x0 - 3.0, x1 + 3.01, 0.5); g = psite.ground(xs, np.zeros_like(xs)); n = len(xs)                                    # the open air above the ground line
    V = np.array([[x, y, z] for y in (y0 - 1.0, y1 + 1.0) for (x, z) in list(zip(xs, g)) + list(zip(xs[::-1], np.full(n, z1 + 3.0)))]); m = 2 * n; k = np.arange(m); k1 = (k + 1) % m
    air = new_obj("E_air", new_mesh("air", V, [np.stack([k, k1, k1 + m, k + m], 1), np.array([list(k[::-1])]), np.array([list(k + m)])], smooth=False))
    room = _box("E_room", (X0, -C.ROOM_Y, ZF), (X1, y1 + 1.0, C.Z_CEIL)); tun = _box("E_tun", (XF - 0.3, -TW, ZF), (X0 + 0.05, y1 + 1.0, ZF + C.TUN_H))
    sa, sb = -2.5, C.S2 + 0.6; chan = _box("E_chan", (0, 0, 0), (1, 1, 1)); chan.scale = (sb - sa, 0.9 + y1 + 1.0, 1.5); chan.location = tuple(U * (sa + sb) / 2 + np.array([0.0, (-0.9 + y1 + 1.0) / 2, 0.0]))        # the hole the bomb made, from the surface to the hall
    chan.rotation_euler = (0, math.radians(C.DIVE), 0)
    for c in (air, room, tun, chan):
        _cut(solid, c)
    bpy.context.view_layer.update(); dg = bpy.context.evaluated_depsgraph_get(); me = bpy.data.meshes.new_from_object(solid.evaluated_get(dg))
    col = new_obj("E_collider", me); collider(col)
    for o in (solid, air, room, tun, chan):
        bpy.data.objects.remove(o, do_unlink=True)
    B = C.BURST; yb = -2.6
    core = ico("E_core", 2.2, (B[0], yb, B[2]), rough=0.35)
    flow(core, 'BOTH', 1, 5, dens=2.2, temp=2.4, fuel=1.0, color=DARK[0], vn=95.0)
    for k, (dx, dz, v) in enumerate(((-8.0, 0.4, (-90.0, 0, 6.0)), (8.0, 0.4, (90.0, 0, 6.0)), (0.0, 2.2, (0.0, 0, 60.0)), (-15.0, -0.5, (-70.0, 0, 0.0)), (15.0, -0.5, (70.0, 0, 0.0)))):      # the fireball spreading along the hall
        fb = ico("E_fb%d" % k, 2.4, (min(max(B[0] + dx, X0 + 2.6), X1 - 2.6), yb - 0.8, min(max(B[2] + dz, ZF + 2.6), C.Z_CEIL - 2.6)), rough=0.4)
        flow(fb, 'BOTH', 2 + 3 * (k > 2), 14 + 6 * (k > 2), dens=2.0, temp=2.2, fuel=0.85, color=DARK[0], vn=30.0, vinit=v)
    soot = ico("E_soot", 1.0, (HX, -3.8, ZF + 3.5), rough=0.4, scale=(13.0, 3.2, 3.0))
    flow(soot, 'SMOKE', 10, 70, dens=2.6, temp=1.0, color=DARK[0], vn=8.0)
    dust = ico("E_dust", 1.0, (HX, -4.2, ZF + 3.5), rough=0.3, scale=(14.0, 3.4, 3.2))
    flow(dust, 'SMOKE', 60, 260, dens=1.6, temp=0.4, color=DUST[0], vn=3.0)
    door = ico("E_door", 2.2, (X0 - 1.2, -1.4, ZF + 3.0), rough=0.3, scale=(1.0, 0.6, 1.1))                                                # driven down the tunnel
    flow(door, 'BOTH', 8, 30, dens=2.2, temp=2.2, fuel=0.8, color=DARK[0], vn=6.0, vinit=(-110.0, 0.0, 0.0))
    door2 = ico("E_door2", 2.2, (X0 - 1.8, -1.4, ZF + 3.0), rough=0.3, scale=(1.0, 0.6, 1.1))
    flow(door2, 'SMOKE', 26, 240, dens=2.4, temp=1.0, color=DARK[0], vn=3.0, vinit=(-36.0, 0.0, 0.8))
    mid = ico("E_mid", 2.2, ((XF + X0) / 2, -1.4, ZF + 3.0), rough=0.3, scale=(1.0, 0.6, 1.1))                                              # the flame keeps going along the tunnel
    flow(mid, 'BOTH', 22, 40, dens=2.2, temp=2.2, fuel=0.7, color=DARK[0], vn=4.0, vinit=(-100.0, 0.0, 0.0))
    hp = U * (C.S2 - 1.6); hole = ico("E_hole", 0.62, (hp[0], -0.12, hp[2]), rough=0.2)                                                    # and back up the hole the bomb made
    flow(hole, 'BOTH', 4, 18, dens=2.2, temp=2.2, fuel=0.7, color=DARK[0], vn=3.0, vinit=tuple(-U * 110.0))
    hole2 = ico("E_hole2", 0.62, (hp[0], -0.12, hp[2]), rough=0.2)
    flow(hole2, 'SMOKE', 18, 200, dens=2.4, temp=1.0, color=DARK[1], vn=2.0, vinit=tuple(-U * 36.0))
    late = ico("E_late", 1.0, (B[0], -4.0, ZF + 2.5), rough=0.4, scale=(10.0, 3.0, 2.4))                                                   # what keeps burning and smoking in the wreck
    flow(late, 'SMOKE', 260, 600, dens=1.2, temp=0.6, color=DARK[1], vn=1.0)

if __name__ == "__main__":
    kind = sys.argv[1]; cache_dir, res, frames = os.path.abspath(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4])
    noise = len(sys.argv) > 5 and sys.argv[5] == "1"
    random.seed(71 if kind == "out" else 73)
    msim.TIME_SCALE = 0.4 if kind == "out" else 0.1; msim.DT = OUT_DT if kind == "out" else IN_DT
    msim.DOMAINS["w_" + kind] = ((1.0, 1.0, 1.0), (0.0, 0.0))
    bpy.ops.wm.read_factory_settings(use_empty=True)
    dom = msim.make_domain("w_" + kind, cache_dir, res, frames, noise); _place(dom, OUT_BOX if kind == "out" else IN_BOX)
    d = dom.modifiers["Fluid"].domain_settings
    d.burning_rate = 3.4; d.flame_smoke = 2.2; d.flame_smoke_color = (0.10, 0.095, 0.09); d.use_collision_border_bottom = False
    if kind == "in":
        d.use_collision_border_front = True; d.use_collision_border_back = True; d.vorticity = 0.3; d.burning_rate = 1.6; d.timesteps_max = 8; d.cfl_condition = 3.0
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
