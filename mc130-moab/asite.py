"""The target: an invented dry mountain valley with walled compounds, trees and tunnel mouths at the foot of one slope.

Nobody is modelled.  The valley runs along X; its floor is about 300 m wide; the burst is over the origin, 58 m from
the foot of the northern slope, where four tunnel mouths are.  What the blast does to each thing follows from the
pressure calculated for its distance (aconst.psi): at 5 psi and more a compound is flattened and trees go down; from
2 to 5 psi roofs are gone and walls are breached, trees are stripped and left leaning; below that things stand.
Those thresholds are general published guidance for blast on ordinary buildings, not measurements of this bomb, and
the ground's own shelter (walls, folds, the slope) is not worked out.

ground(x, y)     the surface
Valley(sc, col)  the valley for views from the ground and the air; update(tb) moves it for tb seconds after the burst
AirFloor(sc, col) the same country seen from the aircraft, 4,900 m up
"""
import bpy, math, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
for p in ("grenade-explosion", "rpg7-explosion", "mortar-explosion", "howitzer-explosion", "reaper-hellfire", "tomahawk-sub"):
    sys.path.insert(0, os.path.join(HERE, "..", p))
sys.path.insert(0, HERE)
from mathutils import Quaternion, Vector
from qgeo import Shell, box as gbox, revolve, ellipsoid, paint_mat, EX, EY, EZ
from util import new_mesh, new_obj, grid_faces, nodemat, smoothstep, fbm, Geo
import env, tland
import aconst as C

env.SUN_ELEV = math.radians(34.0)                                     # a late afternoon (the real strike was after dark)
Y_N = 58.0; Y_S = -250.0                                              # the feet of the northern and southern slopes
MUD = (0.33, 0.255, 0.17, 1); MUD2 = (0.27, 0.21, 0.14, 1); MUD3 = (0.38, 0.30, 0.20, 1); DOOR = (0.05, 0.04, 0.03, 1); STONE = (0.24, 0.21, 0.18, 1); TIMBER = (0.20, 0.13, 0.07, 1); HOLE = (0.006, 0.006, 0.006, 1)
LEAF = (0.070, 0.125, 0.040, 1); LEAF2 = (0.095, 0.150, 0.050, 1); BARK = (0.10, 0.075, 0.05, 1)
sp = lambda u, k: k * np.logaddexp(0.0, u / k)

def _raw(x, y, fine):
    r = np.hypot(x, y); w = np.clip((r - 150.0) / 500.0, 0.0, 1.0); w = w * w * (3 - 2 * w)
    yn = y - 300.0 * w * (fbm(x / 1500.0 + 0.3, x * 0.0 + 0.7, 3, 3) - 0.5)                                    # away from the target the valley wanders
    north = sp(yn - Y_N, 12.0); south = sp(-(yn - Y_S), 16.0); HM = 1350.0
    h = HM * (1 - np.exp(-0.66 * north / HM)) + 0.9 * HM * (1 - np.exp(-0.52 * south / (0.9 * HM))) + 0.012 * x + 0.008 * np.abs(yn + 90.0)
    m = np.clip((north + south - 6.0) / 60.0, 0.0, 1.0)                                                       # on the slopes: shoulders, spurs and ravines
    rib = np.abs(fbm(x / 330.0 + 5.1, y / 1700.0 + 2.2, 11, 3) - 0.5) * 2.0
    h = h + m * (150.0 * (fbm(x / 900.0 + 3.3, y / 900.0 + 1.1, 5, 4) - 0.5) - 26.0 * (1 - np.clip(rib * 3.0, 0, 1)) ** 2)
    m2 = np.clip((north + south - 250.0) / 1800.0, 0.0, 1.0)                                                  # behind the valley's own slopes: ranges and high basins
    h = h + m2 * (1500.0 * (fbm(x / 9000.0 + 7.7, y / 9000.0 + 4.1, 21, 4) - 0.42) + 420.0 * (fbm(x / 2600.0 + 1.9, y / 2600.0 + 8.3, 23, 4) - 0.5))
    h = h - 1.4 * np.exp(-((yn - (-100.0 + 38.0 * np.sin(x / 170.0))) / 9.0) ** 2)                            # a dry stream bed
    if fine:
        near = 1.0 - np.clip((r - 1400.0) / 800.0, 0.0, 1.0)
        h = h + near * (m * 11.0 * (fbm(x / 70.0, y / 70.0, 7, 3) - 0.5) + (0.35 + 0.5 * m) * (fbm(x / 7.0, y / 7.0, 9, 3) - 0.5) + 0.8 * (1 - m) * (fbm(x / 45.0 + 9.0, y / 45.0, 13, 2) - 0.5))
    return h

_H0 = float(_raw(np.array(0.0), np.array(0.0), 1))

def ground(x, y, fine=1):
    return _raw(np.asarray(x, float), np.asarray(y, float), fine) - _H0

def _graded(inner=320.0, step0=2.0, outer=6400.0):
    g = [inner]; step = step0
    while g[-1] < outer:
        step *= 1.07; g.append(g[-1] + step)
    g[-1] = outer; g = np.array(g[1:]); return np.concatenate([-g[::-1], np.arange(-inner, inner + 1e-3, step0), g])

def land_mat():
    m = tland.land_mat("MountainRock")
    for nd in m.node_tree.nodes:
        if nd.type == 'VALTORGB' and abs(nd.color_ramp.elements[0].color[0] - 0.170) < 1e-3:
            nd.color_ramp.elements[0].color = (0.165, 0.130, 0.095, 1); nd.color_ramp.elements[1].color = (0.390, 0.320, 0.230, 1)
    return m

def _terrain(col):
    m = land_mat(); obs = []
    for name, xs, hole in (("Near", _graded(), 0.0), ("Far", np.arange(-84000.0, 84000.0 + 1e-3, 700.0), 6400.0)):
        X, Y = np.meshgrid(xs, xs, indexing="ij"); Z = ground(X, Y, fine=int(name == "Near")); V = np.stack([X, Y, Z], -1).reshape(-1, 3); F = [grid_faces(len(xs), len(xs))]; n = len(xs)
        if hole:
            c = V[F[0]].mean(1); F[0] = F[0][~((np.abs(c[:, 0]) < hole - 1e-3) & (np.abs(c[:, 1]) < hole - 1e-3))]
        else:                                                          # a skirt under the edge hides the gaps where the two sheets meet
            for e in (np.arange(n) * n, (n - 1) * n + np.arange(n), np.arange(n), np.arange(n) * n + n - 1):
                n0 = len(V); top = V[e]; bot = top - np.array([0.0, 0.0, 260.0]); V = np.vstack([V, top, bot]); k = np.arange(len(e) - 1); F.append(np.stack([n0 + k, n0 + k + 1, n0 + len(e) + k + 1, n0 + len(e) + k], 1))
        obs.append(new_obj("Ground" + name, new_mesh("ground_" + name.lower(), V, F), col, m))
    return obs

# ----------------------------------------------------------------------------- compounds
def _rot(a):
    c, s = math.cos(a), math.sin(a); return np.array([[c, -s, 0.0], [s, c, 0.0], [0.0, 0.0, 1.0]])

def _rubble(S, rng, p, q, hmax, wid, colors):
    """A broken wall: a row of low, uneven heaps from p to q."""
    d = q - p; ln = float(np.linalg.norm(d)); n = max(int(ln / 2.4), 1); ex = d / ln; a = math.atan2(ex[1], ex[0])
    for k in range(n):
        c = p + d * ((k + 0.5) / n) + np.array([rng.uniform(-0.5, 0.5), rng.uniform(-0.5, 0.5), 0.0]); h = float(rng.uniform(0.25, hmax))
        S.add(*gbox((c[0], c[1], c[2] + h / 2 - 0.15), (ln / n * rng.uniform(0.8, 1.15), wid * rng.uniform(0.7, 1.3), h), rot=_rot(a + rng.uniform(-0.25, 0.25))), color=colors[int(rng.integers(0, len(colors)))])

def _compound(rng, cx, cy, w, d, yaw, state):
    """One walled yard with its houses, in world coordinates.  state: 0 as built, 1 roofs gone and walls breached, 2 flattened."""
    S = Shell(); Rm = _rot(yaw); z0 = float(ground(cx, cy)) - 0.5; hw = float(rng.uniform(2.6, 3.2)); t = 0.55; cols = (MUD, MUD2, MUD3)
    P = lambda u, v, z=0.0: np.array([cx, cy, z0]) + Rm @ np.array([u, v, z])
    corners = [(-w / 2, -d / 2), (w / 2, -d / 2), (w / 2, d / 2), (-w / 2, d / 2)]
    for k in range(4):
        (u0, v0), (u1, v1) = corners[k], corners[(k + 1) % 4]; nseg = 5; ang = yaw + math.atan2(v1 - v0, u1 - u0); gate = int(rng.integers(1, 4)) if k == 0 else -1
        for j in range(nseg):
            a0 = np.array([u0 + (u1 - u0) * j / nseg, v0 + (v1 - v0) * j / nseg]); a1 = np.array([u0 + (u1 - u0) * (j + 1) / nseg, v0 + (v1 - v0) * (j + 1) / nseg]); mid = (a0 + a1) / 2; ln = float(np.linalg.norm(a1 - a0))
            broke = state == 2 or (state == 1 and rng.uniform() < 0.42)
            if j == gate and not broke:                                 # the gate: a gap with a dark leaf
                S.add(*gbox(P(mid[0], mid[1], hw * 0.42 + 0.5), (ln * 0.5, 0.12, hw * 0.84), rot=_rot(ang)), color=DOOR)
                for sgn in (-1, 1):
                    e = mid + (a1 - a0) / ln * sgn * ln * 0.375; S.add(*gbox(P(e[0], e[1], hw / 2 + 0.25), (ln * 0.25 + 0.05, t, hw + 0.5), rot=_rot(ang)), color=MUD)
            elif broke:
                _rubble(S, rng, P(a0[0], a0[1], 0.5), P(a1[0], a1[1], 0.5), 0.9 if state == 2 else 1.5, 1.7, cols)
            else:
                S.add(*gbox(P(mid[0], mid[1], hw / 2 + 0.25), (ln + 0.05, t, hw + 0.5), rot=_rot(ang)), color=cols[(k + j) % 2])
    nh = int(rng.integers(1, 4))
    for h in range(nh):                                                # houses against the walls
        side = (h + int(rng.integers(0, 2))) % 4; hl = float(rng.uniform(8.0, min(15.0, (w if side % 2 == 0 else d) - 6.0))); hd = float(rng.uniform(4.8, 6.4)); hh = float(rng.uniform(3.1, 3.7)); off = float(rng.uniform(-0.2, 0.2)) * ((w if side % 2 == 0 else d) - hl - 4.0)
        u, v, a = {0: (off, -d / 2 + hd / 2 + 0.7, 0.0), 1: (w / 2 - hd / 2 - 0.7, off, math.pi / 2), 2: (off, d / 2 - hd / 2 - 0.7, math.pi), 3: (-w / 2 + hd / 2 + 0.7, off, -math.pi / 2)}[side]; ang = yaw + a; Rh = _rot(a)
        Q = lambda lu, lv, z=0.0: P(*(np.array([u, v, 0.0]) + Rh @ np.array([lu, lv, 0.0]))[:2], z)
        if state == 0:
            S.add(*gbox(Q(0, 0, hh / 2 + 0.25), (hl, hd, hh + 0.5), rot=_rot(ang)), color=MUD3 if h % 2 else MUD); S.add(*gbox(Q(0, 0, hh + 0.55), (hl + 0.5, hd + 0.5, 0.22), rot=_rot(ang)), color=MUD2)     # walls and the flat roof
            for dx in np.linspace(-hl / 2 + 1.6, hl / 2 - 1.6, max(int(hl / 4.0), 2)):                                                                   # door and window openings on the yard side
                S.add(*gbox(Q(dx, hd / 2 + 0.01, 1.45), (1.0, 0.06, 1.9), rot=_rot(ang)), color=DOOR)
        else:
            for (lu, lv, sl, st_) in ((0, -hd / 2, hl, 0.5), (0, hd / 2, hl, 0.5), (-hl / 2, 0, 0.5, hd), (hl / 2, 0, 0.5, hd)):                          # what is left of the walls
                if state == 2:
                    a0 = Q(lu - sl / 2 if sl > 1 else lu, lv - st_ / 2 if st_ > 1 else lv, 0.5); a1 = Q(lu + sl / 2 if sl > 1 else lu, lv + st_ / 2 if st_ > 1 else lv, 0.5); _rubble(S, rng, a0, a1, 1.0, 1.6, cols)
                else:
                    hr = hh * float(rng.uniform(0.35, 0.95)); S.add(*gbox(Q(lu, lv, hr / 2 + 0.25), (sl, st_, hr + 0.5), rot=_rot(ang)), color=MUD3 if h % 2 else MUD)
            for k in range(7 if state == 1 else 10):                    # the roof and what was under it, on the floor
                S.add(*gbox(Q(rng.uniform(-hl / 2, hl / 2), rng.uniform(-hd / 2, hd / 2), 0.5 + rng.uniform(0.1, 0.4)), (rng.uniform(0.8, 2.6), rng.uniform(0.6, 1.8), rng.uniform(0.3, 0.8)), rot=_rot(rng.uniform(0, 3.1))), color=cols[k % 3])
    if state == 2:                                                      # thrown about the yard
        for k in range(26):
            S.add(*gbox(P(rng.uniform(-w / 2, w / 2) * 1.15, rng.uniform(-d / 2, d / 2) * 1.15, 0.5 + rng.uniform(0.0, 0.25)), (rng.uniform(0.5, 2.2), rng.uniform(0.4, 1.4), rng.uniform(0.2, 0.6)), rot=_rot(rng.uniform(0, 3.1))), color=cols[k % 3])
    return S

def _place_compounds(rng):
    out = []
    for gx in np.arange(-700.0, 700.1, 62.0):
        for gy in np.arange(Y_S + 34.0, Y_N - 24.0, 58.0):
            x = float(gx + rng.uniform(-14, 14)); y = float(gy + rng.uniform(-11, 11)); r = math.hypot(x, y); w = float(rng.uniform(24.0, 36.0)); d = float(rng.uniform(22.0, 32.0))
            keep = rng.uniform() < (0.62 if r < 260.0 else 0.30)
            if not keep or r < 32.0 or abs(y - (-100.0 + 38.0 * math.sin(x / 170.0))) < 26.0 or y > Y_N - 22.0:
                continue
            out.append((x, y, w, d, float(rng.uniform(-0.25, 0.25))))
    return out

# ----------------------------------------------------------------------------- trees and tunnel mouths
def _tree_mesh(k, bare):
    name = "tree%d_%s" % (k, "bare" if bare else "full"); me = bpy.data.meshes.get(name)
    if me:
        return me
    rng = np.random.default_rng(300 + k); S = Shell(); h = (6.0, 8.5, 11.5)[k]; th = h * 0.42
    S.add(*revolve([(0.0, 0.26), (th, 0.17), (h * 0.80, 0.05)], 8, axis=EZ), color=BARK)
    for j in range(5):
        a = j * 1.3 + rng.uniform(0, 0.6); z = th + rng.uniform(-0.2, 0.3) * h; ln = h * rng.uniform(0.18, 0.30); d = np.array([math.cos(a) * 0.8, math.sin(a) * 0.8, 0.6]); d /= np.linalg.norm(d); c = np.array([0, 0, z]) + d * ln / 2
        ey = np.cross(EZ, d); ey /= np.linalg.norm(ey); ez = np.cross(d, ey); S.add(*gbox(c, (ln, 0.10, 0.10), rot=np.stack([d, ey, ez], 1)), color=BARK)
    if not bare:
        for j in range(4):
            a = j * 1.7 + rng.uniform(0, 0.8); rr = h * 0.13 * (j > 0); S.add(*ellipsoid((rr * math.cos(a), rr * math.sin(a), h * (0.66 + 0.08 * (j % 2)) + (0.12 * h if j == 0 else 0.0)), (h * rng.uniform(0.19, 0.25), h * rng.uniform(0.19, 0.25), h * rng.uniform(0.20, 0.27)), 10, 7), color=LEAF if j % 2 else LEAF2)
    return S.mesh(name, sharp=math.radians(50))

CAVES = ((-86.0, 0), (-21.0, 1), (46.0, 2), (118.0, 3))               # x of each tunnel mouth; they stand at the foot of the northern slope

def cave_pos(xc):
    ys = np.linspace(Y_N - 6.0, Y_N + 60.0, 265); zs = ground(np.full_like(ys, xc), ys); zf = float(ground(xc, Y_N - 20.0)); k = int(np.argmax(zs > zf + 4.5)); return np.array([xc, float(ys[k]), float(zs[k])])

def _cave(rng, p, shut):
    """A stone-faced mouth let into the slope (as built), or the fall of rock where it was."""
    if shut:
        g = Geo()
        for k in range(46):
            s = float(rng.uniform(0.5, 1.9)); env.rock_geo(g, rng, (p[0] + rng.normal(0, 2.6), p[1] - 1.2 + rng.normal(0, 2.2) - 0.5 * abs(rng.normal(0, 2.0)), p[2] - 1.0 + abs(rng.normal(0, 1.6))), s, 2, [(0.20, 0.17, 0.14, 1), (0.27, 0.23, 0.19, 1), (0.15, 0.13, 0.11, 1)][k % 3])
        return g.mesh("cave_shut_%d" % int(p[0]))
    S = Shell(); x, y, z = p
    S.add(*gbox((x, y + 1.6, z + 1.0), (5.2, 5.2, 5.4)), color=STONE)                                                    # stone facing, built into the slope
    S.add(*gbox((x, y - 1.02, z + 0.75), (2.3, 0.06, 2.9)), color=HOLE)                                                    # the way in
    for sx in (-1.3, 1.3):
        S.add(*gbox((x + sx, y - 1.12, z + 0.75), (0.28, 0.26, 3.1)), color=TIMBER)
    S.add(*gbox((x, y - 1.12, z + 2.35), (3.3, 0.30, 0.30)), color=TIMBER)
    return S.mesh("cave_open_%d" % int(p[0]), sharp=math.radians(40))

def _alpha_mat(name):
    m, N, L, P = nodemat(name); a = N.new("ShaderNodeAttribute"); a.attribute_name = "col"; L.new(a.outputs["Color"], P.inputs["Base Color"]); L.new(a.outputs["Alpha"], P.inputs["Alpha"]); P.inputs["Roughness"].default_value = 0.95
    try:
        m.surface_render_method = 'BLENDED'
    except Exception:
        pass
    return m

class Valley:
    def __init__(self, sc, col):
        rng = np.random.default_rng(13); self.col = col; env.make_world(sc); self.ground = _terrain(col)[0]
        pm = bpy.data.materials.get("MudPaint") or paint_mat("MudPaint", rough=0.92, bump=0.5); tm = bpy.data.materials.get("TreePaint") or paint_mat("TreePaint", rough=0.85, bump=0.3)
        # ---- compounds: as built, and as the blast leaves them
        self.comps = []
        for i, (x, y, w, d, yaw) in enumerate(_place_compounds(rng)):
            r = math.hypot(x, y); p = float(C.psi(r)); state = 2 if p >= 5.0 else (1 if p >= 2.0 else 0); seed = int(rng.integers(0, 1 << 30))
            a = new_obj("Comp%02d" % i, _compound(np.random.default_rng(seed), x, y, w, d, yaw, 0).mesh("comp%02d" % i, sharp=math.radians(35)), col, pm)
            b = new_obj("Comp%02d_after" % i, _compound(np.random.default_rng(seed), x, y, w, d, yaw, state).mesh("comp%02d_after" % i, sharp=math.radians(35)), col, pm) if state else None
            self.comps.append(dict(a=a, b=b, r=r, t=float(C.t_front(r)), state=state, x=x, y=y, z=float(ground(x, y))))
        # ---- trees
        self.trees = []; spots = []
        for k in range(150):                                            # along the stream bed and over the floor
            x = float(rng.uniform(-760, 760)); y = float(-100.0 + 38.0 * math.sin(x / 170.0) + rng.normal(0, 13.0)) if k % 2 else float(rng.uniform(Y_S + 12.0, Y_N - 8.0)); spots.append((x, y))
        for c in self.comps:                                            # and by the compounds
            for k in range(int(rng.integers(1, 4))):
                a = rng.uniform(0, 6.283); spots.append((c["x"] + 22.0 * math.cos(a), c["y"] + 20.0 * math.sin(a)))
        for i, (x, y) in enumerate(spots):
            r = math.hypot(x, y)
            if r < 20.0 or any(abs(x - c["x"]) < 19.0 and abs(y - c["y"]) < 17.0 for c in self.comps):
                continue
            k = int(rng.integers(0, 3)); ob = new_obj("Tree%03d" % i, _tree_mesh(k, False), col, tm); ob.rotation_mode = 'QUATERNION'; ob.location = (x, y, float(ground(x, y)) - 0.15); s = float(rng.uniform(0.8, 1.2)); ob.scale = (s, s, s)
            _tree_mesh(k, True).materials.append(tm) if not _tree_mesh(k, True).materials else None
            self.trees.append(dict(ob=ob, k=k, r=r, d=np.array([x, y]) / r, t=float(C.t_front(r)), p=float(C.psi(r)), yaw=float(rng.uniform(0, 6.283)), j=float(rng.uniform(0, 1)), bare=False))
        # ---- tunnel mouths
        self.caves = []
        for xc, i in CAVES:
            p = cave_pos(xc); r = float(np.linalg.norm(p)); a = new_obj("Cave%d" % i, _cave(rng, p, False), col, pm); shut = float(C.psi(r)) >= 5.0
            b = new_obj("Cave%d_shut" % i, _cave(rng, p, True), col, env.mat_vcol("RockMat", rough=0.9, bump_scale=6)) if shut else None
            self.caves.append(dict(a=a, b=b, r=r, t=float(C.t_front(r)), p=p))
        # ---- the ground under the fireball, burnt
        R1 = 0.75 * C.FB_D; a_ = np.linspace(0, 2 * np.pi, 72, endpoint=False); rr = np.linspace(0.0, R1, 16)[1:]; V = [[0.0, 0.0, 0.08]]; A = [[0.045, 0.040, 0.036, 0.92]]
        for q in rr:
            for t in a_:
                x = q * math.cos(t); y = q * math.sin(t); V.append([x, y, float(ground(x, y)) + 0.08]); A.append([0.045, 0.040, 0.036, 0.92 * float(1 - smoothstep(0.45 * R1, R1, q * (1 + 0.25 * (fbm(x / 9.0, y / 9.0, 3, 3) - 0.5))))])
        n = len(a_); F3 = [[0, 1 + k, 1 + (k + 1) % n] for k in range(n)]; F4 = [[1 + j * n + k, 1 + (j + 1) * n + k, 1 + (j + 1) * n + (k + 1) % n, 1 + j * n + (k + 1) % n] for j in range(len(rr) - 1) for k in range(n)]
        self.scorch = new_obj("Scorch", new_mesh("scorch", np.array(V), [np.array(F3), np.array(F4)], attrs={"col": np.array(A, np.float32)}), col, _alpha_mat("ScorchMat")); self.scorch.visible_shadow = False
        self.update(-1.0)

    def update(self, tb):
        """tb: seconds after the burst."""
        self.scorch.hide_render = tb < 0.2
        for c in self.comps:
            tau = tb - c["t"]
            if c["b"] is None:
                continue
            fall = 0.55 if c["state"] == 2 else 0.35; u = smoothstep(0.0, fall, tau); c["a"].hide_render = u >= 1.0; c["b"].hide_render = u < 1.0
            c["a"].scale = (1.0, 1.0, 1.0 - (0.82 if c["state"] == 2 else 0.30) * u); c["a"].location = (0.0, 0.0, (c["z"] - 0.5) * (0.82 if c["state"] == 2 else 0.30) * u)       # going down, about its own base
        for t in self.trees:
            tau = tb - t["t"]; p = t["p"]; ang = 0.0
            if tau > 0:
                if p >= 5.0:
                    ang = math.radians(84.0 + 5.0 * t["j"]) * smoothstep(0.0, 0.42 + 0.2 * t["j"], tau)
                elif p >= 2.0:
                    ang = math.radians(4.0 + 20.0 * t["j"] * (p - 2.0) / 3.0) * smoothstep(0.0, 0.3, tau) + math.radians(7.0) * math.exp(-tau / 0.7) * math.sin(9.0 * tau)
                else:
                    ang = math.radians(min(4.0 * p, 5.0)) * math.exp(-tau / 0.9) * math.sin(8.0 * tau)
            bare = tau > 0.10 and p >= 2.6
            if bare != t["bare"]:
                t["ob"].data = _tree_mesh(t["k"], bare); t["bare"] = bare
            d = t["d"]; t["ob"].rotation_quaternion = Quaternion((-d[1], d[0], 0.0), ang) @ Quaternion((0, 0, 1), t["yaw"])
        for c in self.caves:
            if c["b"] is not None:
                done = tb - c["t"] > 0.5; c["a"].hide_render = done; c["b"].hide_render = not done

class AirFloor:
    """The same country from the aircraft: ob is moved so that the valley slides past underneath."""
    def __init__(self, sc, col):
        env.make_world(sc)
        xs = np.concatenate([-np.geomspace(500000.0, 9300.0, 40), np.arange(-9000.0, 9000.1, 30.0), np.geomspace(9300.0, 500000.0, 40)]); X, Y = np.meshgrid(xs, xs, indexing="ij")
        self.ob = new_obj("Country", new_mesh("country", np.stack([X, Y, ground(X, Y, fine=0)], -1).reshape(-1, 3), [grid_faces(len(xs), len(xs))]), col, land_mat())
    def set(self, t):
        p = C.ac_pos(t); self.ob.location = (-float(p[0]), 0.0, -float(p[2]))
