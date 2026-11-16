"""Target set for the 120 mm mortar segment: a cluster of old, roofless masonry ruins around the impact
point (world origin), rubble heaps, fallen timbers, the crater, and the one free-standing wall close
enough (2.7 m) to be knocked partly down by the burst.

Walls are built from brick courses (240 x 80 mm module) so their broken edges step like real masonry; a
shader lays weathered plaster over the brick, and after the detonation adds fragment pock-marks and soot
on the faces that look at the burst.
"""
import bpy, math, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "grenade-explosion")); sys.path.insert(0, os.path.join(HERE, "..", "rpg7-explosion"))
from util import *
import env, fx
import wall as wallmod
from wall import q_axis, q_slerp, q_mat, boxes

BW, BH = 0.24, 0.08
G = 9.81
_SG = np.array([[sx, sy, sz] for sx in (-1, 1) for sy in (-1, 1) for sz in (-1, 1)], float)
_FC = np.array([[0, 1, 3, 2], [4, 6, 7, 5], [0, 4, 5, 1], [2, 3, 7, 6], [0, 2, 6, 4], [1, 5, 7, 3]])

# (name, p0, p1, thickness, [(s_frac, height)...], [(s0, s1, z0, z1) openings])
WALLS = [
    ("A1", (-2.0, 4.5), (7.0, 4.5), 0.30, [(0, 3.3), (0.25, 2.9), (0.45, 3.4), (0.62, 2.4), (0.8, 1.5), (1, 1.9)], [(3.6, 4.6, 0, 2.05), (0.9, 2.0, 0.95, 2.15), (6.2, 7.3, 0.95, 2.15)]),
    ("A2", (-2.0, 4.5), (-2.0, 10.5), 0.30, [(0, 3.3), (0.5, 4.7), (1, 3.0)], [(2.4, 3.5, 1.0, 2.2)]),
    ("A3", (-2.0, 10.5), (7.0, 10.5), 0.30, [(0, 3.0), (0.3, 2.2), (0.6, 2.9), (1, 1.2)], [(1.5, 2.6, 1.0, 2.1), (5.5, 6.6, 1.0, 2.1)]),
    ("A4", (7.0, 4.5), (7.0, 10.5), 0.30, [(0, 1.9), (0.3, 0.9), (0.7, 0.5), (1, 1.2)], []),
    ("A5", (2.6, 4.5), (2.6, 10.5), 0.20, [(0, 2.6), (0.4, 1.2), (0.7, 0.4), (1, 2.0)], [(2.2, 3.1, 0, 2.0)]),
    ("B1", (8.5, -5.0), (8.5, -1.0), 0.30, [(0, 3.9), (0.35, 3.2), (0.7, 1.4), (1, 0.8)], [(1.2, 2.2, 1.0, 2.1)]),
    ("B2", (8.5, -5.0), (13.5, -5.0), 0.30, [(0, 3.9), (0.3, 2.6), (0.7, 1.8), (1, 2.4)], [(2.6, 3.6, 1.0, 2.1)]),
    ("B3", (13.5, -5.0), (13.5, -1.0), 0.30, [(0, 2.4), (1, 1.2)], []),
    ("B4", (8.5, -1.0), (13.5, -1.0), 0.30, [(0, 0.8), (0.5, 0.4), (1, 1.2)], []),
    ("D1", (-11.0, 7.0), (-6.5, 7.0), 0.30, [(0, 2.6), (0.6, 1.4), (1, 2.2)], [(1.6, 2.6, 1.0, 2.0)]),
    ("D2", (-11.0, 7.0), (-11.0, 11.5), 0.30, [(0, 2.6), (1, 1.0)], []),
    ("D3", (-6.5, 7.0), (-6.5, 9.0), 0.30, [(0, 2.2), (1, 0.5)], []),
    ("E1", (16.0, 6.0), (22.0, 6.0), 0.30, [(0, 2.8), (0.5, 1.6), (1, 3.1)], [(2.4, 3.4, 0, 2.0)]),
    ("E2", (22.0, 6.0), (22.0, 11.0), 0.30, [(0, 3.1), (0.6, 1.2), (1, 0.6)], []),
    ("E3", (16.0, 6.0), (16.0, 11.0), 0.30, [(0, 2.8), (1, 1.4)], [(2.0, 3.0, 1.0, 2.1)]),
    ("F1", (-24.0, -6.0), (-18.0, -6.0), 0.30, [(0, 2.4), (0.4, 3.0), (1, 1.0)], [(3.4, 4.4, 1.0, 2.1)]),
    ("F2", (-24.0, -6.0), (-24.0, -11.0), 0.30, [(0, 2.4), (1, 1.3)], []),
]
NEAR = ("C", (-1.8, 2.7), (1.6, 2.7), 0.24, [(0, 1.5), (0.3, 2.0), (0.7, 1.9), (1, 1.3)], [])
RUBBLE = [((6.2, 7.0), 1.5, 150), ((1.0, 9.6), 1.1, 90), ((4.4, 5.2), 0.8, 60), ((11.5, -2.2), 1.4, 130), ((9.3, -0.6), 0.7, 45), ((-8.0, 9.5), 1.2, 90),
          ((7.8, 5.6), 0.8, 50), ((-2.6, 3.9), 0.6, 30), ((19.0, 9.0), 1.3, 80), ((-21.0, -8.5), 1.2, 70), ((1.9, 3.0), 0.45, 22)]

def wall_material():
    m, N, L, P = nodemat("RuinWall")
    at = N.new("ShaderNodeAttribute"); at.attribute_name = "col"; sep = N.new("ShaderNodeSeparateColor"); L.new(at.outputs["Color"], sep.inputs[0])
    geo = N.new("ShaderNodeNewGeometry"); spos = N.new("ShaderNodeSeparateXYZ"); L.new(geo.outputs["Position"], spos.inputs[0])
    vec = N.new("ShaderNodeCombineXYZ"); L.new(sep.outputs["Green"], vec.inputs[0]); L.new(spos.outputs["Z"], vec.inputs[1])
    def mth(op, a, b=None, c=None):
        n = N.new("ShaderNodeMath"); n.operation = op
        for k, v in enumerate((a, b, c)):
            if v is None:
                continue
            if isinstance(v, (int, float)):
                n.inputs[k].default_value = v
            else:
                L.new(v, n.inputs[k])
        return n.outputs[0]
    def noise(scale, detail=5, vecsrc=None, rough=0.55):
        n = N.new("ShaderNodeTexNoise"); n.inputs["Scale"].default_value = scale; n.inputs["Detail"].default_value = detail; n.inputs["Roughness"].default_value = rough
        L.new(vecsrc or geo.outputs["Position"], n.inputs["Vector"]); return n.outputs["Fac"]
    def mix(fac, a, b, blend='MIX'):
        n = N.new("ShaderNodeMix"); n.data_type = 'RGBA'; n.blend_type = blend
        for sock, v in (("Factor", fac), ("A", a), ("B", b)):
            if isinstance(v, (int, float)):
                n.inputs[sock].default_value = v
            elif isinstance(v, tuple):
                n.inputs[sock].default_value = (*v, 1)
            else:
                L.new(v, n.inputs[sock])
        return n.outputs["Result"]
    def ramp(v, lo, hi):
        n = N.new("ShaderNodeMapRange"); n.interpolation_type = 'SMOOTHSTEP'; n.inputs["From Min"].default_value = lo; n.inputs["From Max"].default_value = hi
        L.new(v, n.inputs["Value"]); return n.outputs["Result"]
    br = N.new("ShaderNodeTexBrick"); br.offset = 0.5; br.inputs["Scale"].default_value = 1.0
    br.inputs["Color1"].default_value = (0.25, 0.095, 0.058, 1); br.inputs["Color2"].default_value = (0.36, 0.165, 0.10, 1); br.inputs["Mortar"].default_value = (0.36, 0.33, 0.29, 1)
    br.inputs["Mortar Size"].default_value = 0.011; br.inputs["Mortar Smooth"].default_value = 0.25; br.inputs["Brick Width"].default_value = BW; br.inputs["Row Height"].default_value = BH
    L.new(vec.outputs[0], br.inputs["Vector"])
    n_big = noise(0.45, 5); n_mid = noise(2.6, 5); n_fine = noise(34, 4)
    brick = mix(1.0, br.outputs["Color"], mix(ramp(n_mid, 0.3, 0.7), (0.55, 0.52, 0.50), (1.15, 1.12, 1.08)), 'MULTIPLY')
    plaster = mix(1.0, mix(ramp(noise(1.1, 6), 0.30, 0.70), (0.20, 0.175, 0.135), (0.43, 0.39, 0.32)), mix(ramp(n_fine, 0.3, 0.75), (0.80, 0.80, 0.80), (1.10, 1.10, 1.10)), 'MULTIPLY')
    pm = ramp(mth('ADD', mth('ADD', mth('MULTIPLY', sep.outputs["Red"], 0.70), mth('MULTIPLY', mth('SUBTRACT', n_big, 0.5), 1.25)),
                  mth('MULTIPLY', mth('SUBTRACT', n_mid, 0.5), 0.55)), 0.36, 0.43)
    base = mix(pm, brick, plaster)
    # --- blast marks: pale fragment pocks + soot on faces looking at the burst (Blast value 0 -> 1)
    blast = N.new("ShaderNodeValue"); blast.name = blast.label = "Blast"; blast.outputs[0].default_value = 0.0
    tob = N.new("ShaderNodeVectorMath"); tob.operation = 'SUBTRACT'; tob.inputs[0].default_value = (0, 0, 0.6); L.new(geo.outputs["Position"], tob.inputs[1])
    dist = N.new("ShaderNodeVectorMath"); dist.operation = 'LENGTH'; L.new(tob.outputs[0], dist.inputs[0])
    nrm = N.new("ShaderNodeVectorMath"); nrm.operation = 'NORMALIZE'; L.new(tob.outputs[0], nrm.inputs[0])
    dot = N.new("ShaderNodeVectorMath"); dot.operation = 'DOT_PRODUCT'; L.new(nrm.outputs[0], dot.inputs[0]); L.new(geo.outputs["True Normal"], dot.inputs[1])
    facing = ramp(dot.outputs["Value"], 0.02, 0.30)
    near = N.new("ShaderNodeMapRange"); near.inputs["From Min"].default_value = 2.0; near.inputs["From Max"].default_value = 26.0
    near.inputs["To Min"].default_value = 1.0; near.inputs["To Max"].default_value = 0.0; L.new(dist.outputs["Value"], near.inputs["Value"])
    w = mth('MULTIPLY', mth('MULTIPLY', mth('POWER', near.outputs["Result"], 1.6), facing), blast.outputs[0])
    vor = N.new("ShaderNodeTexVoronoi"); vor.inputs["Scale"].default_value = 9.0; L.new(geo.outputs["Position"], vor.inputs["Vector"])
    spot = mth('LESS_THAN', vor.outputs["Distance"], mth('MULTIPLY', w, 0.20))
    base = mix(mth('MULTIPLY', spot, 0.9), base, mix(ramp(n_fine, 0.3, 0.7), (0.50, 0.36, 0.27), (0.62, 0.55, 0.46)))
    sootn = N.new("ShaderNodeMapRange"); sootn.inputs["From Min"].default_value = 2.2; sootn.inputs["From Max"].default_value = 6.5
    sootn.inputs["To Min"].default_value = 0.85; sootn.inputs["To Max"].default_value = 0.0; L.new(dist.outputs["Value"], sootn.inputs["Value"])
    soot = mth('MULTIPLY', mth('MULTIPLY', mth('MULTIPLY', sootn.outputs["Result"], facing), blast.outputs[0]), mth('ADD', mth('MULTIPLY', n_mid, 0.8), 0.45))
    base = mix(soot, base, (0.022, 0.020, 0.018))
    L.new(base, P.inputs["Base Color"]); P.inputs["Roughness"].default_value = 0.92; P.inputs["Specular IOR Level"].default_value = 0.2
    b1 = N.new("ShaderNodeBump"); b1.inputs["Strength"].default_value = 0.6; b1.inputs["Distance"].default_value = 0.012; b1.invert = True
    L.new(mth('MULTIPLY', br.outputs["Fac"], mth('SUBTRACT', 1.0, pm)), b1.inputs["Height"])
    b2 = N.new("ShaderNodeBump"); b2.inputs["Strength"].default_value = 0.5; b2.inputs["Distance"].default_value = 0.006
    L.new(n_fine, b2.inputs["Height"]); L.new(b1.outputs["Normal"], b2.inputs["Normal"])
    b3 = N.new("ShaderNodeBump"); b3.inputs["Strength"].default_value = 0.8; b3.inputs["Distance"].default_value = 0.010
    L.new(pm, b3.inputs["Height"]); L.new(b2.outputs["Normal"], b3.inputs["Normal"])
    b4 = N.new("ShaderNodeBump"); b4.inputs["Strength"].default_value = 1.0; b4.inputs["Distance"].default_value = 0.015; b4.invert = True
    L.new(spot, b4.inputs["Height"]); L.new(b3.outputs["Normal"], b4.inputs["Normal"])
    L.new(b4.outputs["Normal"], P.inputs["Normal"])
    return m

# ----------------------------------------------------------------------------- one wall as brick courses
class Seg:
    def __init__(self, spec, seed):
        self.name, p0, p1, self.th, hpts, self.openings = spec
        self.p0 = np.array(p0, float); d = np.array(p1, float) - self.p0; self.L = float(np.linalg.norm(d)); self.d = d / self.L
        self.nrm = np.array([-self.d[1], self.d[0]])
        self.nc = int(math.ceil(self.L / (BW / 2))); hs = np.array(hpts, float)
        s = (np.arange(self.nc) + 0.5) * BW / 2
        top = np.interp(s / self.L, hs[:, 0], hs[:, 1]) + 0.55 * (fbm(s * 0.9 + seed * 7.1, s * 0 + seed, seed, 3) - 0.5) + 0.30 * (fbm(s * 5.0, s * 0 + 3.0, seed + 5, 2) - 0.5)
        top = np.maximum(top, 0.16)
        self.nr = int(math.ceil((top.max() + 0.1) / BH)); z = (np.arange(self.nr) + 0.5) * BH
        m = z[:, None] < top[None, :]
        for (s0, s1, z0, z1) in self.openings:
            m &= ~((s[None, :] > s0) & (s[None, :] < s1) & (z[:, None] > z0) & (z[:, None] < z1))
        self.s, self.z, self.top = s, z, top
        self.mask = m
        dz = top[None, :] - z[:, None]
        pl = np.clip(dz / 0.75, 0, 1) * np.clip((z[:, None] - 0.05) / 0.45, 0.25, 1)
        for (s0, s1, z0, z1) in self.openings:                 # plaster is gone round the openings as well
            dd = np.maximum(np.maximum(s0 - s[None, :], s[None, :] - s1), np.maximum(z0 - z[:, None], z[:, None] - z1))
            pl *= np.clip(dd / 0.35, 0.0, 1.0)
        self.pl = pl

    def runs(self, mask):
        """Brick-aligned runs of every course: arrays (s_lo, s_hi, z_centre, plaster)."""
        out = []
        for j in range(self.nr):
            row = mask[j]
            if not row.any():
                continue
            e = np.diff(np.r_[0, row.astype(np.int8), 0]); a = np.where(e == 1)[0]; b = np.where(e == -1)[0]
            for i0, i1 in zip(a, b):
                if (i0 + j) % 2 == 1 and i0 > 0:
                    i0 += 1
                if (i1 + j) % 2 == 1 and i1 < self.nc:
                    i1 -= 1
                if i1 <= i0:
                    continue
                k = i0                                           # split long runs so plaster can vary along them
                while k < i1:
                    k2 = min(k + 4, i1); out.append((k * BW / 2, k2 * BW / 2, self.z[j], float(self.pl[j, k:k2].mean()))); k = k2
        return np.array(out).reshape(-1, 4)

    def mesh_data(self, mask, wid):
        r = self.runs(mask)
        if len(r) == 0:
            return np.zeros((0, 3)), np.zeros((0, 4), int), np.zeros((0, 4))
        cen = np.stack([(r[:, 0] + r[:, 1]) / 2, np.zeros(len(r)), r[:, 2]], 1); half = np.stack([(r[:, 1] - r[:, 0]) / 2, np.full(len(r), self.th / 2), np.full(len(r), BH / 2)], 1)
        loc = cen[:, None, :] + _SG[None] * half[:, None, :]                                  # wall-local: x along, y across, z up
        u = loc[..., 0] + wid * 3.7
        W = self.p0[None, None, :] + loc[..., 0:1] * self.d[None, None, :] + loc[..., 1:2] * self.nrm[None, None, :]
        V = np.concatenate([W, loc[..., 2:3] - 0.10], -1).reshape(-1, 3)
        F = (_FC[None] + (np.arange(len(r)) * 8)[:, None, None]).reshape(-1, 4)
        Cc = np.stack([np.repeat(r[:, 3], 8), u.ravel(), np.full(len(r) * 8, (wid * 0.37) % 1.0), np.ones(len(r) * 8)], 1)
        return V, F, Cc

    def world(self, s, z, off=0.0):
        p = self.p0 + self.d * s + self.nrm * off
        return np.array([p[0], p[1], z - 0.10])

def _mesh(name, parts, mat):
    V = np.concatenate([p[0] for p in parts]); n = np.cumsum([0] + [len(p[0]) for p in parts])
    F = np.concatenate([p[1] + n[i] for i, p in enumerate(parts)]); Cc = np.concatenate([p[2] for p in parts])
    me = new_mesh(name, V, [F], smooth=False, attrs={"col": Cc}); me.shade_flat(); me.materials.append(mat)
    return me

class Debris:
    """Rigid pieces: ballistic flight, one bounce, short slide, then lying flat (same scheme as the RPG wall)."""
    def __init__(self, P):
        self.p0 = P[:, 0:3]; self.hs = P[:, 3:6]; self.v0 = P[:, 6:9]; self.td = P[:, 9]; self.om = P[:, 10]
        self.ax = P[:, 11:14]; self.yaw = P[:, 14]; self.col = P[:, 15:18]
        zr = self.hs[:, 2] + 0.002; vz = self.v0[:, 2]
        self.t1 = (vz + np.sqrt(vz * vz + 2 * G * np.maximum(self.p0[:, 2] - zr, 0))) / G
        self.p1 = self.p0 + self.v0 * self.t1[:, None]; self.p1[:, 2] = zr
        vz1 = vz - G * self.t1
        self.v1 = np.stack([self.v0[:, 0] * 0.40, self.v0[:, 1] * 0.40, -vz1 * 0.20], 1)
        self.t2 = 2 * self.v1[:, 2] / G
        self.p2 = self.p1 + self.v1 * self.t2[:, None]; self.p2[:, 2] = zr
        self.q1 = q_axis(self.ax, self.om * self.t1); self.qr = q_axis(np.tile([0.0, 0, 1.0], (len(P), 1)), self.yaw)
    def state(self, td):
        t = np.maximum(td - self.td, 0.0)
        a1 = t < self.t1; a2 = (~a1) & (t < self.t1 + self.t2)
        p = self.p0 + self.v0 * t[:, None]; p[:, 2] -= 0.5 * G * t * t
        u = t - self.t1
        pb = self.p1 + self.v1 * u[:, None]; pb[:, 2] -= 0.5 * G * u * u
        ur = np.maximum(t - self.t1 - self.t2, 0.0)
        pr = self.p2 + (self.v1 * 0.4) * (0.08 * (1 - np.exp(-ur / 0.08)))[:, None]; pr[:, 2] = self.p2[:, 2]
        p = np.where(a1[:, None], p, np.where(a2[:, None], pb, pr))
        q = q_axis(self.ax, self.om * np.minimum(t, self.t1))
        s = np.clip(u / np.maximum(self.t2, 1e-3), 0, 1); s = s * s * (3 - 2 * s)
        q = np.where(a1[:, None], q, q_slerp(self.q1, self.qr, s))
        return p, q_mat(q)

BRICK_COLS = np.array([(0.30, 0.105, 0.060), (0.43, 0.185, 0.105), (0.36, 0.15, 0.085), (0.40, 0.36, 0.30)])

class Ruins:
    def __init__(self, col, seed=7):
        rng = self.rng = np.random.default_rng(seed)
        self.mat = wall_material(); self.blast_node = self.mat.node_tree.nodes["Blast"]
        self.bmat = wallmod.brick_material()
        segs = [Seg(w, 11 + 3 * i) for i, w in enumerate(WALLS)]
        self.static = new_obj("Ruins", _mesh("ruins", [s.mesh_data(s.mask, i) for i, s in enumerate(segs)], self.mat), col)
        # --- the wall next to the burst: intact and breached versions + the bricks that leave it
        c = self.near = Seg(NEAR, 5)
        self.near_intact = new_obj("NearWall", _mesh("near", [c.mesh_data(c.mask, 31)], self.mat), col)
        sb = float(np.dot(np.array([0.0, 0.0]) - c.p0, c.d))                                   # point of the wall closest to the burst
        ang = np.arctan2(c.z[:, None] - 0.75, c.s[None, :] - sb)
        rad = 1.20 * (1 + 0.22 * np.sin(ang * 3 + 0.6) + 0.14 * np.sin(ang * 7 + 2.0))
        rho = np.hypot(c.s[None, :] - sb, (c.z[:, None] - 0.75) * 0.85)
        gone = c.mask & (rho < rad)
        cols_open = gone.any(0); top_gone = np.where(cols_open, np.argmax(np.where(gone, np.arange(c.nr)[:, None], -1), 0), -1)
        faller = c.mask & ~gone & cols_open[None, :] & (np.arange(c.nr)[:, None] > top_gone[None, :])
        keep = c.mask & ~gone & ~faller
        self.near_breached = new_obj("NearWallBreached", _mesh("nearb", [c.mesh_data(keep, 31)], self.mat), col)
        self.gap = dict(width=float(cols_open.sum() * BW / 2), s_center=sb)
        P = []
        away = c.nrm if np.dot(c.nrm, c.p0) > 0 else -c.nrm                                    # unit vector pointing away from the burst
        for kind, m in (("blast", gone), ("fall", faller)):
            jj, ii = np.where(m)
            for j, i in zip(jj, ii):
                if (i + j) % 2 == 1:
                    continue                                                                    # one piece per whole brick
                if kind == "blast" and rng.random() < 0.35:
                    continue                                                                    # shattered: dust and chips only
                k = int(rng.choice([1, 1, 2])); f = rng.uniform(0.7, 0.97, 3)
                for q in range(k):
                    hs = np.array([BW / 2 / k * f[0], c.th / 2 * f[1] * (0.5 if rng.random() < 0.5 else 1.0), BH / 2 * f[2]])
                    p = c.world(c.s[i] + (q - (k - 1) / 2) * BW / k, c.z[j])
                    r_ = max(float(rho[j, i]), 0.3)
                    if kind == "blast":
                        sp = rng.uniform(5, 15) / (0.6 + r_)
                        v = np.array([away[0] * sp + rng.normal(0, 1.2), away[1] * sp + rng.normal(0, 0.6), rng.uniform(0.5, 4.5) + 1.5 * (c.z[j] > 0.9)])
                        v[0] += (c.s[i] - sb) * rng.uniform(0.5, 2.5); td = 0.012; om = rng.uniform(4, 20)
                    else:
                        v = np.array([away[0] * rng.uniform(0.3, 2.2) + rng.normal(0, 0.5), away[1] * rng.uniform(0.3, 2.2), rng.uniform(-0.2, 1.2)])
                        td = rng.uniform(0.05, 0.30); om = rng.uniform(1, 6)
                    P.append(np.concatenate([p, hs, v, [td, om], rng.normal(0, 1, 3), [rng.uniform(0, 6.283)], BRICK_COLS[rng.integers(0, 3)] * rng.uniform(0.6, 1.1)]))
        self.debris = Debris(np.array(P)); self.debris_ob = new_obj("NearDebris", bpy.data.meshes.new("d"), col, self.bmat)
        self.near_breached.hide_render = True; self.debris_ob.hide_render = True
        # --- old rubble heaps, mounds and fallen timbers (static)
        cen, half, colr, Rm = [], [], [], []
        mg = Geo()
        for (cx, cy), rad_, n in RUBBLE:
            rr = np.abs(rng.normal(0, rad_ * 0.55, n)); aa = rng.uniform(0, 6.283, n)
            h0 = 0.27 * rad_ * np.exp(-(rr / (0.7 * rad_)) ** 2)
            for k in range(n):
                whole = rng.random() < 0.55
                hs = np.array([BW / 2, 0.055, BH / 2 - 0.004]) * (rng.uniform(0.75, 1.0, 3) if whole else rng.uniform(0.3, 0.75, 3))
                cen.append([cx + rr[k] * math.cos(aa[k]), cy + rr[k] * math.sin(aa[k]), h0[k] * rng.uniform(0.75, 1.05) + hs[2] * 0.6])
                half.append(hs); colr.append(BRICK_COLS[rng.integers(0, 4)] * rng.uniform(0.55, 1.05))
                Rm.append(q_mat(q_axis(rng.normal(0, 1, (1, 3)) * [1, 1, 0.3], rng.uniform(-0.5, 0.5, 1)))[0] @ q_mat(q_axis(np.array([[0, 0, 1.0]]), rng.uniform(0, 6.283, 1)))[0])
            na, nr = 28, 9; A, Rr = np.meshgrid(np.linspace(0, 2 * np.pi, na, endpoint=False), np.linspace(0.02, 1.0, nr), indexing="ij")
            R2 = Rr * rad_ * 1.25 * (1 + 0.25 * (fbm(np.cos(A) * 2 + cx, np.sin(A) * 2 + cy, 5, 3) - 0.5))
            Z = 0.26 * rad_ * np.exp(-(Rr / 0.62) ** 2) * (0.8 + 0.5 * fbm(R2 * np.cos(A) * 2.5 + cx, R2 * np.sin(A) * 2.5 + cy, 9, 3)) - 0.06
            Vm = np.stack([cx + R2 * np.cos(A), cy + R2 * np.sin(A), Z], -1).reshape(-1, 3)
            mg.add(Vm, grid_faces(na, nr, wrap_u=True), color=(0.17, 0.125, 0.085, 1))
        V, F, Cc = boxes(np.array(cen), np.array(half), np.array(colr), np.array(Rm))
        me = new_mesh("rubble", V, [F], smooth=False, attrs={"col": Cc}); me.shade_flat(); me.materials.append(self.bmat)
        self.rubble = new_obj("Rubble", me, col)
        self.mounds = new_obj("RubbleMounds", mg.mesh("mounds"), col, env.mat_vcol("RubbleDirt", rough=0.95, bump_scale=0.02))
        tg = Geo()
        for (c0, c1, sec) in (((0.2, 5.2, 2.7), (5.6, 8.9, 0.15), 0.15), ((3.4, 9.8, 2.2), (6.0, 6.2, 0.12), 0.13), ((-1.6, 7.0, 0.10), (1.9, 9.7, 0.14), 0.14),
                              ((9.2, -4.4, 3.0), (12.6, -1.8, 0.14), 0.15), ((10.2, -4.6, 0.12), (13.0, -3.1, 0.50), 0.12), ((-10.4, 7.6, 1.9), (-7.4, 10.4, 0.12), 0.14),
                              ((17.0, 7.0, 0.12), (21.2, 9.8, 0.9), 0.14)):
            c0 = np.array(c0); c1 = np.array(c1); d = c1 - c0; Ln = np.linalg.norm(d); d /= Ln
            a = np.cross(d, [0, 0, 1.0]); a /= np.linalg.norm(a); b = np.cross(d, a)
            env.box_geo(tg, (Ln, sec, sec * 1.25), center=(c0 + c1) / 2, rot=np.stack([d, a, b], 1), color=(*(np.array([0.62, 0.56, 0.50]) * rng.uniform(0.55, 0.9)), 1), grain_axis=0)
        self.timbers = new_obj("Timbers", tg.mesh("timbers", smooth=False), col, env.mat_wood("RuinWood", base=(0.20, 0.16, 0.12), dark=(0.06, 0.05, 0.04)))

    def update(self, td):
        hit = td >= 0
        self.blast_node.outputs[0].default_value = 1.0 if hit else 0.0
        self.near_intact.hide_render = hit; self.near_breached.hide_render = not hit; self.debris_ob.hide_render = not hit
        if hit:
            p, R = self.debris.state(td)
            V, F, Cc = boxes(p, self.debris.hs, self.debris.col, R)
            me = new_mesh("debris", V, [F], smooth=False, attrs={"col": Cc}); me.shade_flat(); me.materials.append(self.bmat)
            old = self.debris_ob.data; self.debris_ob.data = me; bpy.data.meshes.remove(old)

# ----------------------------------------------------------------------------- environment for the target set
CRATER_R = 0.75          # radius of the bowl; rim crest a little outside

def build_env(sc, seed=11):
    """Same range terrain, sky, grass, trees and hills as the other segments, without the pit and props."""
    rng = np.random.default_rng(seed); np.random.seed(seed)
    col = bpy.data.collections.new("ENV"); sc.collection.children.link(col)
    env.make_world(sc)
    ground = env.build_ground(col)
    env.build_grass(col, rng, -200.0); env.build_stones(col, rng, -200.0); env.build_trees(col, rng, -200.0); env.build_hills(col, rng)
    # blend the detailed patch into the far plain so no seam shows from the air
    me = ground.data; n = len(me.vertices); V = np.empty(n * 3, np.float32); me.vertices.foreach_get("co", V); V = V.reshape(-1, 3)
    edge = np.minimum.reduce([V[:, 0] + 52, 30 - V[:, 0], V[:, 1] + 24, 32 - V[:, 1]])
    k = np.clip(edge / 4.0, 0, 1); k = k * k * (3 - 2 * k)
    for kb in ground.data.shape_keys.key_blocks:
        co = np.empty(n * 3, np.float32); kb.data.foreach_get("co", co); co = co.reshape(-1, 3)
        co[:, 2] = -0.035 + (co[:, 2] + 0.035) * k; kb.data.foreach_set("co", co.ravel())
    V[:, 2] = -0.035 + (V[:, 2] + 0.035) * k; me.vertices.foreach_set("co", V.ravel()); me.update()
    # crater of a 120 mm point-detonating burst: shallow bowl, raised lip, rays of thrown soil
    sk = ground.shape_key_add(name="Crater120")
    r = np.hypot(V[:, 0], V[:, 1]); ang = np.arctan2(V[:, 1], V[:, 0])
    rough = 1 + 0.20 * np.sin(ang * 5 + 0.5) + 0.12 * np.sin(ang * 11 + 2.0)
    dz = -0.34 * np.exp(-(r / (CRATER_R * 0.72 * rough)) ** 2) + 0.085 * np.exp(-((r - CRATER_R * 1.25 * rough) / 0.33) ** 2)
    co = V.copy(); co[:, 2] += dz
    sk.data.foreach_set("co", co.astype(np.float32).ravel()); sk.value = 0.0
    nt = ground.data.materials[0].node_tree                       # scorch / thrown-soil reach scaled up from the grenade's
    for nd in nt.nodes:
        if nd.type == 'MAP_RANGE' and abs(nd.inputs["From Min"].default_value - 0.30) < 1e-6 and abs(nd.inputs["From Max"].default_value - 0.78) < 1e-6:
            nd.inputs["To Min"].default_value = 2.2; nd.inputs["To Max"].default_value = 8.5
    return col, ground
