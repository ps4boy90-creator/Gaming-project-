"""Bake the two Mantaflow gas sims of the BLU-109 bursting in the bunker to OpenVDB caches.

  python3 psim.py out <cache_dir> <resolution> <frames> [noise 0|1]     seen from outside
  python3 psim.py in  <cache_dir> <resolution> <frames> [noise 0|1]     the section through the bunker

out   one frame = 1/60 s, frame 1 = the bomb touching the slope; the charge fires on frame 5 (0.060 s later).  Dust at
      the entry hole, then gas driven back up the hole, flame and smoke out of the tunnel mouth, and dust forced up
      through the cover as it lifts.  The mountainside is a solid obstacle.
in    one frame = 1/240 s, frame 1 = the charge firing.  A thin slab of space on the plane of the section: the room, the
      tunnel and the hole the bomb made are hollows in a solid block, so the fire fills the room and is driven down
      the tunnel and back up the hole.  The slab reaches 0.3 m in front of the section so that the gas is seen in front
      of the cut ground.
About 243 kg of explosive in a closed room of 180 cubic metres: where the gas goes is right; how fast and how bright is
staging.
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
import pconst as C, psite

FILL = [(0.50, 0.41, 0.29), (0.43, 0.35, 0.25), (0.57, 0.49, 0.37)]; DUST = [(0.60, 0.58, 0.54), (0.50, 0.48, 0.45), (0.55, 0.50, 0.44)]
XF = psite.XF; ZF = C.Z_FLOOR; TW = C.TUN_W / 2
NRM = np.array([-math.sin(math.radians(C.SLOPE)), 0.0, math.cos(math.radians(C.SLOPE))])       # out of the slope
OUT_BOX = ((-50.0, 34.0), (-29.0, 29.0), (-13.0, 37.0)); IN_BOX = ((-22.0, 12.0), (-3.3, 0.3), (-9.4, 10.6))
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
    collider(_block("E_ground", np.arange(-56.0, 40.01, 1.0), np.arange(-34.0, 34.01, 1.0), -18.0))
    puff = ico("E_puff", 0.9, NRM * 0.7, rough=0.4)                                                       # the bomb goes in: a spurt of dust from the hole
    flow(puff, 'SMOKE', 1, 3, dens=1.6, temp=0.25, color=FILL[0], vn=9.0, vinit=tuple(NRM * 9.0 + up * 12.0))
    vent = ico("E_vent", 0.75, NRM * 0.8, rough=0.3)                                                      # the charge fires: gas back up the hole
    flow(vent, 'BOTH', f0, f0 + 4, dens=2.2, temp=2.0, fuel=0.55, color=DARK[0], vn=6.0, vinit=tuple(up * 85.0))
    vent2 = ico("E_vent2", 0.8, NRM * 0.9, rough=0.3)
    flow(vent2, 'SMOKE', f0 + 4, f0 + 36, dens=2.2, temp=0.9, color=DARK[1], vn=3.0, vinit=tuple(up * 26.0))
    for k, (ex, ey) in enumerate(((3.6, 0.0), (1.2, 1.6), (6.4, -1.4))):                                    # the cover lifts and breaks: dust out of the ground over the room
        heave = ico("E_heave%d" % k, 1.0, (ex, ey, float(psite.ground(ex, ey)) + 0.5), rough=0.4, scale=(4.6 if k == 0 else 2.6, 3.2 if k == 0 else 2.0, 0.35))
        heave.rotation_euler = (0, -math.radians(C.SLOPE), 0)
        flow(heave, 'SMOKE', f0 + 3 + 2 * k, f0 + 44, dens=1.3 if k == 0 else 1.0, temp=0.35, color=FILL[k % 3], vn=3.5, vinit=tuple(NRM * (7.0 - k)))
    for i in range(34):
        ex = random.uniform(-2.0, 9.0); ey = random.uniform(-3.4, 3.4); d = NRM + np.array([random.uniform(-0.45, 0.45), random.uniform(-0.5, 0.5), random.uniform(-0.1, 0.4)])
        jet("E_j%02d" % i, (ex, ey, float(psite.ground(ex, ey)) + 0.5), tuple(d), random.uniform(14, 42), random.uniform(2.2, 4.0), random.randint(18, 44), random.uniform(0.34, 0.62),
            random.choice(FILL + FILL + DUST + DARK[1:]), start=f0 + random.randint(2, 26), dens=1.8, zmin=-30.0)
    mouth = ico("E_mouth", 1.0, (XF - 1.3, 0.0, ZF + 1.25), rough=0.3, scale=(1.0, 0.95, 1.05))            # flame and smoke out of the tunnel
    flow(mouth, 'BOTH', f0, f0 + 5, dens=2.4, temp=2.2, fuel=0.8, color=DARK[0], vn=8.0, vinit=(-78.0, 0.0, 4.0))
    mouth2 = ico("E_mouth2", 1.05, (XF - 1.6, 0.0, ZF + 1.3), rough=0.35)
    flow(mouth2, 'SMOKE', f0 + 4, f0 + 50, dens=2.6, temp=1.0, color=DARK[0], vn=4.0, vinit=(-27.0, 0.0, 3.0))
    mouth3 = ico("E_mouth3", 0.9, (XF - 1.2, 0.0, ZF + 1.5), rough=0.35)
    flow(mouth3, 'SMOKE', f0 + 50, 400, dens=1.0, temp=1.1, color=DARK[1], vn=1.0, vinit=(-4.0, 0.0, 2.5))
    for k, (vx, vy) in enumerate(((1.0, 2.0), (6.5, -2.0))):                                               # the two ventilation pipes
        pipe = ico("E_pipe%d" % k, 0.45, (vx, vy, float(psite.ground(vx, vy)) + 1.7), rough=0.2)
        flow(pipe, 'SMOKE', f0, f0 + 16, dens=2.0, temp=1.0, color=DARK[1], vn=2.0, vinit=(0.0, 0.0, 34.0))
    for i in range(10):                                                                                    # stones and dust thrown out of the hole
        d = up + np.array([random.uniform(-0.35, 0.35), random.uniform(-0.4, 0.4), random.uniform(-0.2, 0.3)])
        jet("E_h%02d" % i, tuple(NRM * 0.9), tuple(d), random.uniform(30, 70), random.uniform(2.0, 3.4), random.randint(20, 40), random.uniform(0.3, 0.5), random.choice(FILL + DARK[:2]), start=f0 + random.randint(0, 5), dens=1.8, zmin=-30.0)

def _cut(ob, cutter):
    m = ob.modifiers.new("b", 'BOOLEAN'); m.operation = 'DIFFERENCE'; m.object = cutter; m.solver = 'EXACT'

def _box(name, lo, hi):
    return msim.box(name, lo, hi)

def build_in():
    U = C.U; (x0, x1), (y0, y1), (z0, z1) = IN_BOX; X0, X1 = C.ROOM_X
    solid = _box("E_solid", (x0 - 1.5, y0 - 0.4, z0 - 1.0), (x1 + 1.5, y1 + 0.4, z1 + 1.5))
    xs = np.arange(x0 - 3.0, x1 + 3.01, 0.25); g = psite.ground(xs, np.zeros_like(xs)); n = len(xs)                                    # the open air above the ground line
    V = np.array([[x, y, z] for y in (y0 - 1.0, y1 + 1.0) for (x, z) in list(zip(xs, g)) + list(zip(xs[::-1], np.full(n, z1 + 3.0)))]); m = 2 * n; k = np.arange(m); k1 = (k + 1) % m
    air = new_obj("E_air", new_mesh("air", V, [np.stack([k, k1, k1 + m, k + m], 1), np.array([list(k[::-1])]), np.array([list(k + m)])], smooth=False))
    room = _box("E_room", (X0, -C.ROOM_Y, ZF), (X1, y1 + 1.0, C.Z_CEIL)); tun = _box("E_tun", (XF - 0.3, -TW, ZF), (X0 + 0.05, y1 + 1.0, ZF + C.TUN_H))
    sa, sb = -1.2, C.S_END + 0.25; chan = _box("E_chan", (0, 0, 0), (1, 1, 1)); chan.scale = (sb - sa, 0.5 + y1 + 1.0, 0.72); chan.location = tuple(U * (sa + sb) / 2 + np.array([0.0, (-0.5 + y1 + 1.0) / 2, 0.0]))
    chan.rotation_euler = (0, math.radians(C.DIVE), 0)
    for c in (air, room, tun, chan):
        _cut(solid, c)
    bpy.context.view_layer.update(); dg = bpy.context.evaluated_depsgraph_get(); me = bpy.data.meshes.new_from_object(solid.evaluated_get(dg))
    col = new_obj("E_collider", me); collider(col)
    for o in (solid, air, room, tun, chan):
        bpy.data.objects.remove(o, do_unlink=True)
    B = C.BURST; yb = -0.9
    core = ico("E_core", 0.8, (B[0], yb, B[2] + 0.5), rough=0.35)
    flow(core, 'BOTH', 1, 4, dens=2.2, temp=2.4, fuel=1.0, color=DARK[0], vn=70.0)
    for k, (dx, dz, v) in enumerate(((-2.6, 0.9, (-60.0, 0, 6.0)), (2.6, 0.9, (60.0, 0, 6.0)), (0.0, 1.9, (0.0, 0, 55.0)))):                 # the fireball spreading along the room
        fb = ico("E_fb%d" % k, 0.9, (B[0] + dx, yb - 0.3, B[2] + dz), rough=0.4)
        flow(fb, 'BOTH', 2, 9, dens=2.0, temp=2.2, fuel=0.85, color=DARK[0], vn=30.0, vinit=v)
    soot = ico("E_soot", 1.0, ((X0 + X1) / 2, -1.4, ZF + 1.5), rough=0.4, scale=(4.2, 1.2, 1.2))
    flow(soot, 'SMOKE', 6, 40, dens=2.6, temp=1.0, color=DARK[0], vn=8.0)
    dust = ico("E_dust", 1.0, ((X0 + X1) / 2, -1.6, ZF + 1.5), rough=0.3, scale=(4.6, 1.3, 1.3))
    flow(dust, 'SMOKE', 30, 150, dens=1.6, temp=0.4, color=DUST[0], vn=3.0)
    door = ico("E_door", 0.85, (X0 - 0.4, -0.45, ZF + 1.2), rough=0.3, scale=(1.0, 0.6, 1.1))                                              # driven down the tunnel
    flow(door, 'BOTH', 3, 16, dens=2.2, temp=2.2, fuel=0.8, color=DARK[0], vn=6.0, vinit=(-95.0, 0.0, 0.0))
    door2 = ico("E_door2", 0.85, (X0 - 0.6, -0.45, ZF + 1.2), rough=0.3, scale=(1.0, 0.6, 1.1))
    flow(door2, 'SMOKE', 14, 130, dens=2.4, temp=1.0, color=DARK[0], vn=3.0, vinit=(-30.0, 0.0, 0.5))
    hp = U * (C.S2 - 0.5); hole = ico("E_hole", 0.42, (hp[0], -0.05, hp[2]), rough=0.2)                                                    # and back up the hole the bomb made
    flow(hole, 'BOTH', 3, 12, dens=2.2, temp=2.2, fuel=0.7, color=DARK[0], vn=3.0, vinit=tuple(-U * 95.0))
    hole2 = ico("E_hole2", 0.42, (hp[0], -0.05, hp[2]), rough=0.2)
    flow(hole2, 'SMOKE', 12, 110, dens=2.4, temp=1.0, color=DARK[1], vn=2.0, vinit=tuple(-U * 30.0))
    late = ico("E_late", 1.0, (B[0], -1.5, ZF + 1.0), rough=0.4, scale=(3.4, 1.2, 0.9))                                                    # what keeps burning and smoking in the wreck
    flow(late, 'SMOKE', 150, 600, dens=1.2, temp=0.6, color=DARK[1], vn=1.0)

if __name__ == "__main__":
    kind = sys.argv[1]; cache_dir, res, frames = os.path.abspath(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4])
    noise = len(sys.argv) > 5 and sys.argv[5] == "1"
    random.seed(71 if kind == "out" else 73)
    msim.TIME_SCALE = 0.4 if kind == "out" else 0.1; msim.DT = OUT_DT if kind == "out" else IN_DT
    msim.DOMAINS["p_" + kind] = ((1.0, 1.0, 1.0), (0.0, 0.0))
    bpy.ops.wm.read_factory_settings(use_empty=True)
    dom = msim.make_domain("p_" + kind, cache_dir, res, frames, noise); _place(dom, OUT_BOX if kind == "out" else IN_BOX)
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
