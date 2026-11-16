"""Sets for the 155 mm howitzer segment.

build_town(): a war-damaged Middle-Eastern town block round the impact point (origin of that set) -
flat-roofed concrete-block houses of one to three storeys with sand-coloured render, broken walls and
slabs, rubble, burnt-out cars, power poles, palms and a minaret; the house whose street front stands
3 m from the burst loses the middle of that wall and the slabs behind it.

build_gun_position(): a desert gun position with HESCO barriers, an ammunition pallet and charge canisters.
"""
import bpy, math, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
for p in ("grenade-explosion", "rpg7-explosion", "mortar-explosion"):
    sys.path.insert(0, os.path.join(HERE, "..", p))
from util import *
import env, fx, ruins
import wall as wallmod
from wall import q_axis, q_mat, boxes
from ruins import Seg, Debris, _mesh
from rpg7 import lathe, pipe
import h777, hconst as C

ruins.BW, ruins.BH = 0.40, 0.20              # concrete-block module (length, course)
BW, BH = ruins.BW, ruins.BH
STOREY = 3.0
HIT_Y = 3.0                                  # street front of the struck house: 3 m from the burst
BLOCK_COLS = np.array([(0.33, 0.32, 0.30), (0.40, 0.38, 0.35), (0.29, 0.28, 0.27), (0.46, 0.41, 0.33)])
STUCCO = [((0.36, 0.29, 0.20), (0.60, 0.51, 0.38)), ((0.42, 0.37, 0.29), (0.68, 0.62, 0.50)), ((0.33, 0.27, 0.22), (0.55, 0.45, 0.36))]

# (x0, y0, x1, y1, storeys, damage 0..1); the first one is the struck house
HOUSES = [(-6.0, HIT_Y, 5.0, 13.0, 2, 0.30),
          (-20.0, HIT_Y, -8.0, 13.5, 3, 0.55), (7.0, HIT_Y, 17.0, 12.0, 1, 0.35), (19.0, HIT_Y, 31.0, 14.0, 2, 0.15), (-35.0, HIT_Y, -22.5, 13.0, 2, 0.45),
          (-31.0, -17.0, -18.5, -6.0, 2, 0.25), (-16.5, -16.0, -4.5, -6.0, 3, 0.70), (-2.5, -15.0, 9.0, -6.0, 1, 0.20), (11.0, -17.0, 24.0, -6.0, 2, 0.50),
          (26.0, -16.0, 36.0, -6.0, 1, 0.60)]

def _auto_houses(rng):
    out = []
    for row_y0, depth in ((17.0, 11.0), (32.0, 10.0), (46.0, 11.0), (-32.0, 11.0), (-47.0, 11.0), (-61.0, 10.0)):
        x = -58.0 + rng.uniform(0, 4)
        while x < 52:
            w = rng.uniform(8.5, 14.0)
            if rng.random() < 0.88:
                out.append((x, row_y0, x + w, row_y0 + depth * rng.uniform(0.8, 1.0), int(rng.choice([1, 2, 2, 3])), float(rng.choice([0.0, 0.1, 0.25, 0.45, 0.7], p=[0.2, 0.25, 0.25, 0.2, 0.1]))))
            x += w + rng.uniform(1.5, 3.5)
    for x0, x1 in ((-58.0, -38.0), (39.0, 56.0)):                   # ends of the main street
        for y0 in (HIT_Y, -17.0):
            out.append((x0, y0, x1 - rng.uniform(0, 4), y0 + rng.uniform(9, 11), int(rng.choice([1, 2])), float(rng.uniform(0.1, 0.6))))
    return out

def _wall_specs(h, k, rng):
    x0, y0, x1, y1, fl, dmg = h; H = fl * STOREY + 0.6; specs = []
    for w, (p0, p1) in enumerate((((x0, y0), (x1, y0)), ((x1, y0), (x1, y1)), ((x1, y1), (x0, y1)), ((x0, y1), (x0, y0)))):
        L_ = math.hypot(p1[0] - p0[0], p1[1] - p0[1]); pts = [(0.0, H), (1.0, H)]
        for _ in range(int(round(dmg * 3 + rng.uniform(-0.4, 0.6)))):
            f = rng.uniform(0.05, 0.95); wd = rng.uniform(0.10, 0.28); dp = H * dmg * rng.uniform(0.5, 1.25)
            pts += [(max(f - wd, 0.0), H), (f, max(H - dp, 0.5)), (min(f + wd, 1.0), H)]
        pts = sorted(pts); hp = [pts[0]]
        for q in pts[1:]:
            if q[0] > hp[-1][0] + 1e-3:
                hp.append(q)
        ops = []; s = 1.3 + rng.uniform(0, 0.8); door = rng.uniform(0.3, 0.7) * L_ if w in (0, 2) else -1
        while s + 1.1 < L_ - 0.9:
            for f in range(fl):
                if f == 0 and abs(s + 0.55 - door) < 1.6:
                    ops.append((s, s + 1.0, 0.0, 2.15))
                elif rng.random() < 0.85:
                    ops.append((s, s + 1.1, f * STOREY + 1.0, f * STOREY + 2.2))
            s += rng.uniform(2.6, 3.4)
        specs.append(("H%02d_%d" % (k, w), p0, p1, 0.25, hp, ops))
    return specs

def _slab_boxes(h, rng, seed, hole=None):
    """Floor / roof slabs as rows of 1 m cells; parts are missing where the house is damaged (or inside `hole`)."""
    x0, y0, x1, y1, fl, dmg = h; cen = []; half = []
    nx = int(math.ceil((x1 - x0) / 1.0)); ny = int(math.ceil((y1 - y0) / 1.0))
    xs = x0 + (np.arange(nx) + 0.5) * (x1 - x0) / nx; ys = y0 + (np.arange(ny) + 0.5) * (y1 - y0) / ny
    X, Y = np.meshgrid(xs, ys, indexing="ij")
    for f in range(fl):
        z = (f + 1) * STOREY - 0.10
        keep = fbm(X * 0.22 + seed * 3.1, Y * 0.22 + f * 5.0, seed, 3) > dmg * (0.78 + 0.12 * f)
        if hole is not None:
            keep &= ~hole(X, Y, z)
        for j in range(ny):
            row = keep[:, j]; e = np.diff(np.r_[0, row.astype(np.int8), 0])
            for i0, i1 in zip(np.where(e == 1)[0], np.where(e == -1)[0]):
                cen.append([(xs[i0] + xs[i1 - 1]) / 2, ys[j], z]); half.append([(i1 - i0) * (x1 - x0) / nx / 2 - 0.12, (y1 - y0) / ny / 2 + 0.01, 0.09])
    return np.array(cen).reshape(-1, 3), np.array(half).reshape(-1, 3)

def concrete_material(name="TownConcrete"):
    m, N, L, P = nodemat(name); tc = N.new("ShaderNodeNewGeometry")
    n = N.new("ShaderNodeTexNoise"); n.inputs["Scale"].default_value = 1.4; n.inputs["Detail"].default_value = 6; L.new(tc.outputs["Position"], n.inputs["Vector"])
    ramp = N.new("ShaderNodeValToRGB"); e = ramp.color_ramp.elements; e[0].position = 0.3; e[0].color = (0.20, 0.19, 0.17, 1); e[1].position = 0.72; e[1].color = (0.46, 0.43, 0.38, 1)
    L.new(n.outputs["Fac"], ramp.inputs["Fac"]); L.new(ramp.outputs["Color"], P.inputs["Base Color"]); P.inputs["Roughness"].default_value = 0.92
    f = N.new("ShaderNodeTexNoise"); f.inputs["Scale"].default_value = 30; L.new(tc.outputs["Position"], f.inputs["Vector"])
    b = N.new("ShaderNodeBump"); b.inputs["Strength"].default_value = 0.5; b.inputs["Distance"].default_value = 0.01; L.new(f.outputs["Fac"], b.inputs["Height"]); L.new(b.outputs["Normal"], P.inputs["Normal"])
    return m

def sandy(ground, crater_r=None):
    """Shift the range dirt towards pale desert sand; optionally add the shell crater and widen the scorch."""
    nt = ground.data.materials[0].node_tree
    for nd in nt.nodes:
        if nd.type == 'VALTORGB' and abs(nd.color_ramp.elements[0].color[0] - 0.160) < 1e-3:
            nd.color_ramp.elements[0].color = (0.250, 0.200, 0.140, 1); nd.color_ramp.elements[1].color = (0.470, 0.390, 0.280, 1)
        if crater_r and nd.type == 'MAP_RANGE' and abs(nd.inputs["From Min"].default_value - 0.30) < 1e-6 and abs(nd.inputs["From Max"].default_value - 0.78) < 1e-6:
            nd.inputs["To Min"].default_value = 3.5; nd.inputs["To Max"].default_value = 13.0
    me = ground.data; n = len(me.vertices); V = np.empty(n * 3, np.float32); me.vertices.foreach_get("co", V); V = V.reshape(-1, 3)
    edge = np.minimum.reduce([V[:, 0] + 52, 30 - V[:, 0], V[:, 1] + 24, 32 - V[:, 1]]); k = np.clip(edge / 4.0, 0, 1); k = k * k * (3 - 2 * k)
    for kb in ground.data.shape_keys.key_blocks:
        co = np.empty(n * 3, np.float32); kb.data.foreach_get("co", co); co = co.reshape(-1, 3); co[:, 2] = -0.035 + (co[:, 2] + 0.035) * k; kb.data.foreach_set("co", co.ravel())
    V[:, 2] = -0.035 + (V[:, 2] + 0.035) * k; me.vertices.foreach_set("co", V.ravel()); me.update()
    if crater_r:
        sk = ground.shape_key_add(name="Crater155")
        r = np.hypot(V[:, 0], V[:, 1]); ang = np.arctan2(V[:, 1], V[:, 0]); rough = 1 + 0.18 * np.sin(ang * 5 + 0.5) + 0.10 * np.sin(ang * 11 + 2.0)
        dz = -0.78 * np.exp(-(r / (crater_r * 0.70 * rough)) ** 2) + 0.16 * np.exp(-((r - crater_r * 1.22 * rough) / 0.50) ** 2)
        co = V.copy(); co[:, 2] += dz; sk.data.foreach_set("co", co.astype(np.float32).ravel()); sk.value = 0.0

def desert_hills(col, rng):
    ob = env.build_hills(col, rng)
    for nd in ob.data.materials[0].node_tree.nodes:
        if nd.type == 'VALTORGB':
            nd.color_ramp.elements[0].color = (0.20, 0.155, 0.105, 1); nd.color_ramp.elements[1].color = (0.42, 0.34, 0.24, 1)

def palm(g, rng, x, y, h):
    lean = rng.normal(0, 0.12, 2); n = 9; zz = np.linspace(0, h, n)
    path = np.stack([x + lean[0] * (zz / h) ** 2 * h, y + lean[1] * (zz / h) ** 2 * h, zz], 1)
    v, f, t = tube(path, np.linspace(0.21, 0.12, n), 10); g.add(v, f, color=(0.22, 0.16, 0.10, 1)); g.add(v, t, color=(0.22, 0.16, 0.10, 1))
    top = path[-1]
    for k in range(15):
        a = 2 * np.pi * k / 15 + rng.uniform(-0.2, 0.2); L_ = rng.uniform(2.2, 3.1); up = rng.uniform(0.2, 0.9)
        m = 8; u = np.linspace(0, 1, m); d = np.array([math.cos(a), math.sin(a), 0])
        c = top[None] + d[None] * (u * L_)[:, None] + np.array([0, 0, 1.0])[None] * (up * u * L_ * 0.7 - 1.25 * (u * L_) ** 2 / L_)[:, None]
        s = np.array([-math.sin(a), math.cos(a), 0]); w = 0.34 * np.sin(np.pi * np.clip(u * 0.92 + 0.06, 0, 1)) + 0.02
        V = np.empty((m * 2, 3)); V[0::2] = c - s[None] * w[:, None] + [0, 0, -0.10]; V[1::2] = c + s[None] * w[:, None] + [0, 0, -0.10]
        g.add(V, grid_faces(m, 2), color=(*(np.array([0.10, 0.17, 0.05]) * rng.uniform(0.7, 1.2)), 1))

def car_wreck(g, c, yaw, tone):
    R = rot_z(yaw); c = np.asarray(c, float); col = (*(np.array([0.16, 0.10, 0.07]) * tone), 1)
    for size, off in (((4.1, 1.65, 0.50), (0, 0, 0.52)), ((2.0, 1.50, 0.44), (-0.25, 0, 0.99)), ((0.9, 1.55, 0.10), (1.55, 0, 0.80))):
        env.box_geo(g, size, center=c + R @ np.array(off), rot=R, color=col)
    for sx in (-1.25, 1.30):
        for sy in (-0.80, 0.80):
            p = c + R @ np.array([sx, sy, 0.28]); v, f, t = tube(np.array([p - R @ [0, 0.09, 0], p + R @ [0, 0.09, 0]]), np.array([0.28, 0.28]), 14)
            g.add(v, f, color=(0.03, 0.03, 0.03, 1)); g.add(v, t, color=(0.03, 0.03, 0.03, 1))

class Town:
    def __init__(self, col, seed=21):
        rng = self.rng = np.random.default_rng(seed)
        houses = HOUSES + _auto_houses(rng); self.houses = houses
        mats = [ruins.wall_material("TownWall%d" % i, c1=(0.30, 0.29, 0.27), c2=(0.40, 0.38, 0.34), mortar=(0.47, 0.45, 0.41), plo=lo, phi=hi, reach=55.0, soot_r=11.0,
                                    origin=(0, 0, 1.0)) for i, (lo, hi) in enumerate(STUCCO)]
        self.blast_nodes = [m.node_tree.nodes["Blast"] for m in mats]
        self.bmat = wallmod.brick_material(); conc = concrete_material()
        parts = [[], [], []]; sc_, sh_ = [], []; wid = 0
        hit = houses[0]
        def hole(X, Y, z):                                        # slab area of the struck house brought down behind the breach
            return (np.hypot(X - 0.0, (Y - HIT_Y) * 0.8) < 4.2 - 0.25 * (z - STOREY))
        for k, h in enumerate(houses):
            specs = _wall_specs(h, k, rng)
            for w, sp in enumerate(specs):
                wid += 1
                if k == 0 and w == 0:
                    self.front_spec = sp; self.front_wid = wid; continue
                s = Seg(sp, 13 + 3 * wid, rough=0.10 + 0.9 * h[5]); s.clean_openings = True; parts[k % 3].append(s.mesh_data(s.mask, wid))
            c, hf = _slab_boxes(h, rng, 5 + k, hole if k == 0 else None); sc_.append(c); sh_.append(hf)
        self.walls = [new_obj("TownWalls%d" % i, _mesh("tw%d" % i, parts[i], mats[i]), col) for i in range(3)]
        sc_ = np.concatenate(sc_); sh_ = np.concatenate(sh_)
        V, F, Cc = boxes(sc_, sh_, np.tile([0.5, 0.5, 0.5], (len(sc_), 1)))
        me = new_mesh("slabs", V, [F], smooth=False); me.shade_flat(); me.materials.append(conc); self.slabs = new_obj("TownSlabs", me, col)
        # --- the struck street front: intact / breached + everything that leaves it; and the slab cells that come down
        c = self.front = Seg(self.front_spec, 13 + 3 * self.front_wid, rough=0.10 + 0.9 * hit[5]); c.clean_openings = True
        self.front_intact = new_obj("FrontWall", _mesh("front", [c.mesh_data(c.mask, self.front_wid)], mats[0]), col)
        sb = float(np.dot(np.array([0.0, HIT_Y]) - c.p0, c.d)); zc = 1.3
        ang = np.arctan2(c.z[:, None] - zc, c.s[None, :] - sb)
        rad = 3.3 * (1 + 0.20 * np.sin(ang * 3 + 0.6) + 0.12 * np.sin(ang * 7 + 2.0))
        rho = np.hypot(c.s[None, :] - sb, (c.z[:, None] - zc) * 0.85)
        gone = c.mask & (rho < rad); cols_open = gone.any(0)
        top_gone = np.where(cols_open, np.argmax(np.where(gone, np.arange(c.nr)[:, None], -1), 0), -1)
        faller = c.mask & ~gone & cols_open[None, :] & (np.arange(c.nr)[:, None] > top_gone[None, :])
        keep = c.mask & ~gone & ~faller
        self.front_breached = new_obj("FrontWallBreached", _mesh("frontb", [c.mesh_data(keep, self.front_wid)], mats[0]), col)
        self.gap = dict(width=float(cols_open.sum() * BW / 2), height=float(hit[4] * STOREY + 0.6))
        P = []; away = np.array([0.0, 1.0])
        for kind, m in (("blast", gone), ("fall", faller)):
            jj, ii = np.where(m)
            for j, i in zip(jj, ii):
                if (i + j) % 2 == 1 or (kind == "blast" and rng.random() < 0.40):
                    continue
                f = rng.uniform(0.7, 0.97, 3); hs = np.array([BW / 2 * f[0], 0.11 * f[1], BH / 2 * f[2]]) * (1.0 if rng.random() < 0.6 else 0.6)
                p = c.world(c.s[i], c.z[j]); r_ = max(float(rho[j, i]), 0.4)
                if kind == "blast":
                    sp = rng.uniform(7, 24) / (0.5 + 0.45 * r_)
                    v = np.array([(c.s[i] - sb) * rng.uniform(0.3, 2.0) + rng.normal(0, 1.5), away[1] * sp, rng.uniform(0.5, 6.0)]); td = 0.010; om = rng.uniform(4, 22)
                else:
                    v = np.array([rng.normal(0, 0.8), rng.uniform(-1.5, 2.5), rng.uniform(-0.3, 1.0)]); td = rng.uniform(0.08, 0.55) + 0.05 * (c.z[j] - zc); om = rng.uniform(1, 6)
                P.append(np.concatenate([p, hs, v, [td, om], rng.normal(0, 1, 3), [rng.uniform(0, 6.283)], BLOCK_COLS[rng.integers(0, 4)] * rng.uniform(0.7, 1.1)]))
        for f in range(hit[4]):                                    # slab pieces
            z = (f + 1) * STOREY - 0.10
            for x in np.arange(-4.0, 4.01, 1.0):
                for y in np.arange(HIT_Y + 0.6, HIT_Y + 5.0, 1.0):
                    if math.hypot(x, (y - HIT_Y) * 0.8) < 4.2 - 0.25 * (z - STOREY) and rng.random() < 0.8:
                        hs = np.array([rng.uniform(0.3, 0.52), rng.uniform(0.3, 0.52), 0.085])
                        v = np.array([rng.normal(0, 0.6), rng.uniform(0.3, 2.5), rng.uniform(0.0, 2.5 - 1.5 * f)])
                        P.append(np.concatenate([[x, y, z], hs, v, [rng.uniform(0.03, 0.35) + 0.12 * f, rng.uniform(0.5, 3.0)], rng.normal(0, 1, 3), [rng.uniform(0, 6.283)],
                                                 np.array([0.36, 0.34, 0.31]) * rng.uniform(0.8, 1.1)]))
        self.debris = Debris(np.array(P)); self.debris_ob = new_obj("FrontDebris", bpy.data.meshes.new("d"), col, self.bmat)
        self.front_breached.hide_render = True; self.debris_ob.hide_render = True
        # --- old rubble along the streets and inside the worst houses
        cen, half, colr, Rm = [], [], [], []; mg = Geo()
        spots = [((rng.uniform(-45, 40), rng.choice([HIT_Y - 0.9, -5.1]) + rng.normal(0, 0.3)), rng.uniform(0.7, 1.6)) for _ in range(16)]
        spots = [s for s in spots if math.hypot(*s[0]) > 5.0]
        for h in houses:
            if h[5] >= 0.45:
                spots.append((((h[0] + h[2]) / 2 + rng.normal(0, 2), (h[1] + h[3]) / 2 + rng.normal(0, 2)), rng.uniform(1.5, 2.6)))
        for (cx, cy), rad_ in spots:
            n = int(70 * rad_); rr = np.abs(rng.normal(0, rad_ * 0.55, n)); aa = rng.uniform(0, 6.283, n); h0 = 0.30 * rad_ * np.exp(-(rr / (0.7 * rad_)) ** 2)
            for q in range(n):
                hs = np.array([BW / 2, 0.10, BH / 2]) * rng.uniform(0.35, 1.0, 3)
                cen.append([cx + rr[q] * math.cos(aa[q]), cy + rr[q] * math.sin(aa[q]), h0[q] * rng.uniform(0.75, 1.05) + hs[2] * 0.6]); half.append(hs)
                colr.append(BLOCK_COLS[rng.integers(0, 4)] * rng.uniform(0.6, 1.1))
                Rm.append(q_mat(q_axis(rng.normal(0, 1, (1, 3)) * [1, 1, 0.3], rng.uniform(-0.5, 0.5, 1)))[0] @ q_mat(q_axis(np.array([[0, 0, 1.0]]), rng.uniform(0, 6.283, 1)))[0])
            na, nr = 24, 8; A, Rr = np.meshgrid(np.linspace(0, 2 * np.pi, na, endpoint=False), np.linspace(0.02, 1.0, nr), indexing="ij")
            R2 = Rr * rad_ * 1.25; Z = 0.28 * rad_ * np.exp(-(Rr / 0.62) ** 2) * (0.8 + 0.5 * fbm(R2 * np.cos(A) * 2.5 + cx, R2 * np.sin(A) * 2.5 + cy, 9, 3)) - 0.06
            mg.add(np.stack([cx + R2 * np.cos(A), cy + R2 * np.sin(A), Z], -1).reshape(-1, 3), grid_faces(na, nr, wrap_u=True), color=(0.30, 0.25, 0.18, 1))
        V, F, Cc = boxes(np.array(cen), np.array(half), np.array(colr), np.array(Rm))
        me = new_mesh("rubble", V, [F], smooth=False, attrs={"col": Cc}); me.shade_flat(); me.materials.append(self.bmat); self.rubble = new_obj("TownRubble", me, col)
        new_obj("TownMounds", mg.mesh("mounds"), col, env.mat_vcol("TownDirt", rough=0.95, bump_scale=0.02))
        # --- street furniture: wrecks, barriers, drums, power poles with sagging wires, roof tanks
        pg = Geo()
        car_wreck(pg, (-11.5, -3.6, 0), 0.25, 1.0); car_wreck(pg, (15.0, 1.0, 0), -2.9, 0.7); car_wreck(pg, (-30.0, -1.5, 0), 1.4, 1.2)
        for k, x in enumerate((6.5, 8.6, 10.7)):
            env.box_geo(pg, (2.0, 0.55, 0.85), center=(x, -1.2 + 0.25 * k, 0.42), rot=rot_z(0.12 * k), color=(0.42, 0.40, 0.36, 1))
        poles = [(-38, HIT_Y - 0.6), (-19, HIT_Y - 0.6), (6.0, HIT_Y - 0.6), (24, HIT_Y - 0.6), (-28, -5.4), (0, -5.4), (22, -5.4)]
        for (x, y) in poles:
            tilt = rot_y(rng.normal(0, 0.05)) @ rot_x(rng.normal(0, 0.05)); top = np.array([x, y, 0]) + tilt @ np.array([0, 0, 8.2])
            v, f, t = tube(np.array([[x, y, -0.2], top]), np.array([0.13, 0.09]), 10); pg.add(v, f, color=(0.22, 0.19, 0.16, 1)); pg.add(v, t, color=(0.22, 0.19, 0.16, 1))
            env.box_geo(pg, (0.10, 1.6, 0.10), center=top - [0, 0, 0.5], color=(0.2, 0.17, 0.14, 1))
        wg = Geo()
        for (a, b) in ((0, 1), (1, 2), (2, 3), (4, 5), (5, 6), (1, 5), (2, 5)):
            for off in (-0.6, 0.6):
                p0 = np.array([poles[a][0], poles[a][1] + off, 7.7]); p1 = np.array([poles[b][0], poles[b][1] + off, 7.7]); u = np.linspace(0, 1, 12)
                path = p0[None] * (1 - u)[:, None] + p1[None] * u[:, None]; path[:, 2] -= rng.uniform(0.6, 1.6) * np.sin(np.pi * u)
                v, f, t = tube(path, np.full(12, 0.012), 5); wg.add(v, f)
        tg = Geo()
        for k, h in enumerate(houses):
            if h[5] <= 0.3 and rng.random() < 0.8:
                x = rng.uniform(h[0] + 1.5, h[2] - 1.5); y = rng.uniform(h[1] + 1.5, h[3] - 1.5); z = h[4] * STOREY
                v, f, t = tube(np.array([[x, y, z], [x, y, z + 1.15]]), np.array([0.55, 0.55]), 16); tg.add(v, f, color=(0.05, 0.05, 0.06, 1)); tg.add(v, t, color=(0.05, 0.05, 0.06, 1))
        for (x, y) in ((-3.5, -4.9), (-2.9, -5.2), (12.5, 2.2)):
            env.drum_geo(tg, rng, (x, y, 0.0), (0.10, 0.07, 0.05))
        # --- minaret (lathe about Z) and palms
        mn = Geo(); tmp = Geo()
        lathe(tmp, [(0, 1.55), (15.5, 1.30), (15.5, 2.0), (15.9, 2.0), (16.6, 1.25), (20.5, 1.10), (20.6, 1.45), (21.0, 1.45), (21.2, 1.0), (22.4, 0.85), (23.6, 0.45), (24.6, 0.05)], 20)
        Vm = np.concatenate(tmp.v)[:, [1, 2, 0]] + np.array([29.0, 24.0, 0.0])
        for kk, fl_ in tmp.f.items():
            mn.add(Vm, np.concatenate(fl_), color=(0.55, 0.48, 0.38, 1))
        gp = Geo()
        for (x, y, hh) in ((-13.5, -4.6, 7.5), (20.5, -4.8, 8.5), (33.0, 1.6, 7.0), (-24.0, 15.2, 8.0), (10.0, 14.5, 7.2), (-41.0, -4.0, 8.2), (2.0, -18.5, 7.8), (38.0, 15.5, 8.4)):
            palm(gp, rng, x, y, hh)
        new_obj("TownProps", pg.mesh("props", smooth=False), col, env.mat_vcol("TownPropMat", rough=0.8))
        new_obj("TownWires", wg.mesh("wires"), col, simple_mat("WireMat", (0.02, 0.02, 0.02), rough=0.6))
        new_obj("TownTanks", tg.mesh("tanks"), col, env.mat_vcol("TownTankMat", rough=0.5))
        new_obj("Minaret", mn.mesh("minaret"), col, env.mat_vcol("MinaretMat", rough=0.9, bump_scale=6.0))
        new_obj("Palms", gp.mesh("palms"), col, env.mat_vcol("PalmMat", rough=0.7, translucent=0.2))
        # --- the rest of the town, as plain blocks out to the hills
        cen, half, colr = [], [], []
        for gx in np.arange(-300, 301, 15.0):
            for gy in np.arange(-300, 301, 14.0):
                x = gx + rng.uniform(-2, 2); y = gy + rng.uniform(-2, 2); d = math.hypot(x, y)
                if (abs(x) < 68 and abs(y) < 74) or rng.random() > 0.80 * math.exp(-(d / 260.0) ** 2) or abs(gy % 56 - 28) < 5:
                    continue
                hx, hy = rng.uniform(3.8, 6.2, 2); hz = rng.choice([1.6, 3.1, 3.1, 4.6]); cen.append([x, y, hz]); half.append([hx, hy, hz])
                colr.append(np.array(STUCCO[rng.integers(0, 3)][1]) * rng.uniform(0.40, 0.62))
                if rng.random() < 0.5:                                # a lower wing or a roof room
                    cen.append([x + hx * 0.4, y - hy * 0.3, hz * 2 + 1.2]); half.append([hx * 0.45, hy * 0.5, 1.2]); colr.append(colr[-1] * 0.9)
        V, F, Cc = boxes(np.array(cen), np.array(half), np.array(colr))
        me = new_mesh("far", V, [F], smooth=False, attrs={"col": Cc}); me.shade_flat()
        new_obj("TownFar", me, col, env.mat_vcol("TownFarMat", rough=0.9, bump_scale=0.6))

    def update(self, td):
        hit = td >= 0
        for b in self.blast_nodes:
            b.outputs[0].default_value = 1.0 if hit else 0.0
        self.front_intact.hide_render = hit; self.front_breached.hide_render = not hit; self.debris_ob.hide_render = not hit
        if hit:
            p, R = self.debris.state(td)
            V, F, Cc = boxes(p, self.debris.hs, self.debris.col, R)
            me = new_mesh("debris", V, [F], smooth=False, attrs={"col": Cc}); me.shade_flat(); me.materials.append(self.bmat)
            old = self.debris_ob.data; self.debris_ob.data = me; bpy.data.meshes.remove(old)

CRATER_R = 1.45

def build_town(sc, seed=11):
    rng = np.random.default_rng(seed); np.random.seed(seed)
    col = bpy.data.collections.new("ENV"); sc.collection.children.link(col)
    env.make_world(sc); ground = env.build_ground(col); sandy(ground, CRATER_R); env.build_stones(col, rng, -200.0); desert_hills(col, rng)
    return col, ground

def build_gun_position(sc, seed=11):
    """Flat sandy position: HESCO barriers on two sides, a pallet of projectiles, charge canisters, a few sandbags."""
    rng = np.random.default_rng(seed); np.random.seed(seed)
    col = bpy.data.collections.new("ENV"); sc.collection.children.link(col)
    env.make_world(sc); ground = env.build_ground(col); sandy(ground); env.build_stones(col, rng, -200.0); desert_hills(col, rng)
    hg = Geo()
    def hesco(x, y, yaw, tall=1):
        for lv in range(tall):
            env.box_geo(hg, (1.06, 1.06, 1.37), center=(x, y, 0.685 + 1.37 * lv), rot=rot_z(yaw + rng.normal(0, 0.03)), color=(*(np.array([0.50, 0.43, 0.31]) * rng.uniform(0.85, 1.08)), 1))
            env.box_geo(hg, (0.98, 0.98, 0.10), center=(x, y, 1.40 + 1.37 * lv), rot=rot_z(yaw), color=(0.40, 0.33, 0.23, 1))
    for k in range(22):
        hesco(-11.0 + 1.1 * k, 8.5, 0.0, 2 if k % 7 else 1)
    for k in range(13):
        hesco(-11.5, 8.0 - 1.1 * k, math.pi / 2, 2)
    new_obj("Hesco", hg.mesh("hesco", smooth=False), col, env.mat_vcol("HescoMat", rough=0.95, bump_scale=14.0))
    wood = env.mat_wood(); pg = Geo()
    for (px, py) in ((-4.6, -3.9), (-6.3, -4.1)):
        for k in range(3):
            env.box_geo(pg, (1.15, 0.10, 0.10), center=(px, py - 0.45 + 0.45 * k, 0.05), color=(0.75, 0.70, 0.62, 1), grain_axis=0)
        for k in range(6):
            env.box_geo(pg, (0.10, 1.05, 0.025), center=(px - 0.5 + 0.2 * k, py, 0.113), color=(0.8, 0.74, 0.66, 1), grain_axis=1)
    new_obj("Pallets", pg.mesh("pallets", smooth=False), col, wood)
    shells = []
    for (px, py), n in (((-4.6, -3.9), 8), ((-6.3, -4.1), 6)):
        for k in range(n):
            s = h777.Shell(col, "Stock%02d" % len(shells), plug=True); s.root.location = (px - 0.36 + 0.24 * (k % 4), py - 0.14 + 0.28 * (k // 4), 0.126)
            s.root.rotation_quaternion = h777.aim_quat((0.0, 0.0, 1.0), rng.uniform(0, 6.28)); shells.append(s)
    cg = Geo()
    for k in range(7):                                             # propellant canisters, stacked
        row, i = (0, k) if k < 4 else (1, k - 4)
        c = np.array([-7.6, -1.6 - 0.21 * i - 0.105 * row, 0.105 + 0.182 * row]); v, f, t = tube(np.array([c + [-0.45, 0, 0], c + [0.45, 0, 0]]), np.array([0.10, 0.10]), 16)
        cg.add(v, f, color=(0.085, 0.10, 0.055, 1)); cg.add(v, t, color=(0.085, 0.10, 0.055, 1))
    new_obj("Canisters", cg.mesh("canisters"), col, env.mat_vcol("CanisterMat", rough=0.5))
    sg = Geo()
    for k in range(9):
        env.sandbag_geo(sg, rng, (-8.6 + 0.62 * (k % 5) + 0.3 * (k // 5), -6.2, 0.07 + 0.145 * (k // 5)), 0.0)
    new_obj("Sandbags", sg.mesh("sandbags"), col, env.mat_burlap())
    return col, ground
