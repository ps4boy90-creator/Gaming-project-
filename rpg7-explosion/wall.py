"""Free-standing brick wall (two stretcher-bond wythes, real brick and joint sizes) and its breach.

Every brick is its own box with its bed / head / collar mortar attached, so the wall can be
shown intact, then swapped for the breached wall (bricks inside the hole removed, edge bricks
snapped in half, the ring around it shaken loose and sooted) while the removed bricks fly as
tumbling debris on ballistic paths with one bounce, plus a spray of small chips."""
import bpy, math, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, "..", "grenade-explosion"))
from util import *
import env, fx
from rconst import WALL_T, WALL_W, WALL_H, ZI

BL, BW, BH, J = 0.215, 0.1025, 0.065, 0.010
G = 9.81
_SG = np.array([[sx, sy, sz] for sx in (-1, 1) for sy in (-1, 1) for sz in (-1, 1)], float)
_FC = np.array([[0, 1, 3, 2], [4, 6, 7, 5], [0, 4, 5, 1], [2, 3, 7, 6], [0, 2, 6, 4], [1, 5, 7, 3]])

# ---- small quaternion kit (w, x, y, z), vectorised
def q_axis(axis, ang):
    axis = axis / (np.linalg.norm(axis, axis=1, keepdims=True) + 1e-12)
    return np.concatenate([np.cos(ang / 2)[:, None], axis * np.sin(ang / 2)[:, None]], 1)
def q_mul(a, b):
    w1, x1, y1, z1 = a.T; w2, x2, y2, z2 = b.T
    return np.stack([w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2, w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2,
                     w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2, w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2], 1)
def q_slerp(a, b, u):
    d = np.sum(a * b, 1); b = np.where(d[:, None] < 0, -b, b); d = np.abs(d).clip(0, 1)
    th = np.arccos(d); s = np.sin(th); u = u[:, None]
    near = (s < 1e-5)[:, None]
    wa = np.where(near, 1 - u, np.sin((1 - u) * th[:, None]) / (s[:, None] + 1e-12))
    wb = np.where(near, u, np.sin(u * th[:, None]) / (s[:, None] + 1e-12))
    q = wa * a + wb * b
    return q / np.linalg.norm(q, axis=1, keepdims=True)
def q_mat(q):
    w, x, y, z = q.T
    return np.stack([np.stack([1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)], 1),
                     np.stack([2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)], 1),
                     np.stack([2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)], 1)], 1)

def boxes(cen, half, col, R=None):
    """n oriented boxes -> (verts, quads, per-vertex colour)."""
    n = len(cen)
    loc = _SG[None] * half[:, None, :]
    if R is not None:
        loc = np.einsum("nij,nkj->nki", R, loc)
    V = (cen[:, None, :] + loc).reshape(-1, 3)
    F = (_FC[None] + (np.arange(n) * 8)[:, None, None]).reshape(-1, 4)
    C = np.repeat(np.concatenate([col, np.ones((n, 1))], 1), 8, axis=0)
    return V, F, C

def brick_material():
    m, N, L, P = nodemat("BrickMat")
    a = N.new("ShaderNodeAttribute"); a.attribute_name = "col"
    tc = N.new("ShaderNodeTexCoord")
    n1 = N.new("ShaderNodeTexNoise"); n1.inputs["Scale"].default_value = 38; n1.inputs["Detail"].default_value = 5
    L.new(tc.outputs["Generated"], n1.inputs["Vector"])
    n2 = N.new("ShaderNodeTexNoise"); n2.inputs["Scale"].default_value = 260; n2.inputs["Detail"].default_value = 3
    L.new(tc.outputs["Object"], n1.inputs["Vector"]); L.new(tc.outputs["Object"], n2.inputs["Vector"])
    mr = N.new("ShaderNodeMapRange"); mr.inputs["To Min"].default_value = 0.72; mr.inputs["To Max"].default_value = 1.18
    L.new(n1.outputs["Fac"], mr.inputs["Value"])
    mul = N.new("ShaderNodeVectorMath"); mul.operation = 'SCALE'; L.new(a.outputs["Color"], mul.inputs[0]); L.new(mr.outputs["Result"], mul.inputs["Scale"])
    L.new(mul.outputs[0], P.inputs["Base Color"]); P.inputs["Roughness"].default_value = 0.9; P.inputs["Specular IOR Level"].default_value = 0.25
    b = N.new("ShaderNodeBump"); b.inputs["Strength"].default_value = 0.5; b.inputs["Distance"].default_value = 0.0025
    L.new(n2.outputs["Fac"], b.inputs["Height"]); L.new(b.outputs["Normal"], P.inputs["Normal"])
    return m

class Chips(fx.Ballistic):
    """Small brick chips: most blown out of the back of the hole, the rest splashed back off the front face."""
    def __init__(self, n, rng, r_hole):
        back = rng.random(n) < 0.68
        cone = np.radians(np.where(back, rng.uniform(0, 40, n), rng.uniform(20, 78, n)))
        az = rng.uniform(0, 2 * np.pi, n)
        sp = np.where(back, rng.uniform(8, 60, n), rng.uniform(4, 26, n)) * rng.uniform(0.35, 1.0, n) ** 0.7
        d = np.stack([np.where(back, 1.0, -1.0) * np.cos(cone), np.sin(cone) * np.cos(az), np.sin(cone) * np.sin(az)], 1)
        self.v0 = d * sp[:, None]; self.v0[:, 2] += rng.uniform(0, 3, n)
        rr = r_hole * np.sqrt(rng.random(n)); a2 = rng.uniform(0, 2 * np.pi, n)
        self.p0 = np.stack([np.where(back, WALL_T + 0.03, -0.03), rr * np.cos(a2), ZI + rr * np.sin(a2)], 1)
        self.k = rng.uniform(1.5, 5.0, n); self.size = rng.uniform(0.006, 0.026, n) * rng.uniform(0.5, 1.0, n)
        self.n = n; self.shape = rng.uniform(0.6, 1.0, (n, 2))
        ts = np.linspace(0, 6, 1500); z = self._pos(ts[None, :])[..., 2]; below = z < 0.0
        idx = np.where(below.any(1), below.argmax(1), len(ts) - 1)
        self.t_hit = ts[idx]; self.p_hit = self._pos(self.t_hit[:, None])[:, 0, :]; self.p_hit[:, 2] = 0.0

class Wall:
    R_HOLE = (0.27, 0.40)            # front (entry) / rear (exit) breach radius before the ragged edge
    def __init__(self, col, seed=3):
        rng = self.rng = np.random.default_rng(seed)
        self.col = col; self.mat = brick_material()
        pal = np.array([(0.40, 0.155, 0.095), (0.46, 0.19, 0.115), (0.33, 0.125, 0.085), (0.50, 0.235, 0.145), (0.29, 0.135, 0.105)])
        B = []                         # bricks: wythe, y_lo, y_hi, z_centre
        y0 = -WALL_W / 2
        for w in (0, 1):
            for k in range(int(round(WALL_H / (BH + J)))):
                s = y0 + ((k + w) % 2) * (BL + J) / 2 - (BL + J)
                for i in range(int(WALL_W / (BL + J)) + 2):
                    lo = max(s + i * (BL + J), y0); hi = min(s + i * (BL + J) + BL, y0 + WALL_W)
                    if hi - lo > 0.04:
                        B.append((w, lo, hi, BH / 2 + k * (BH + J)))
        B = np.array(B); n = len(B)
        self.w = B[:, 0].astype(int); self.lo = B[:, 1].copy(); self.hi = B[:, 2].copy(); self.zc = B[:, 3]
        self.xc = np.where(self.w == 0, BW / 2, WALL_T - BW / 2)
        self.bcol = pal[rng.integers(0, len(pal), n)] * rng.uniform(0.82, 1.12, (n, 1))
        self.mcol = np.array([0.62, 0.60, 0.55])[None] * rng.uniform(0.85, 1.08, (n, 1))
        self._breach()
        self.intact = self._wall_obj("WallIntact", np.ones(n, bool), self.lo, self.hi, None, None, np.ones(n))
        keep = ~self.gone
        self.breached = self._wall_obj("WallBreached", keep, self.lo2, self.hi2, self.shift, self.tilt, self.soot)
        self.breached.hide_render = True
        self.debris = new_obj("BrickDebris", bpy.data.meshes.new("debris"), col, self.mat); self.debris.hide_render = True
        self.chips = Chips(650, rng, 0.9 * self.R_HOLE[1])
        self.chip_mat = simple_mat("BrickChip", (0.30, 0.125, 0.08), rough=0.95)
        self.chip_ob = new_obj("BrickChips", bpy.data.meshes.new("chips"), col, self.chip_mat); self.chip_ob.hide_render = True

    # ------------------------------------------------------------------ breach layout
    def _breach(self):
        rng = self.rng; n = len(self.w)
        yc = (self.lo + self.hi) / 2; dy = yc; dz = self.zc - ZI
        a = np.arctan2(dz, dy); rho = np.hypot(dy, dz)
        r = np.array(self.R_HOLE)[self.w] * (1 + 0.16 * np.sin(3 * a + 1.0) + 0.10 * np.sin(7 * a + 0.4))
        gone = rho < r
        faller = (~gone) & (np.abs(dy) < 0.45 * r) & (dz > 0) & (dz < r + 0.17) & (rng.random(n) < 0.75)
        half = (~gone) & (~faller) & (rho < r + 0.12) & (rng.random(n) < 0.6) & (self.hi - self.lo > 0.15)
        self.lo2 = self.lo.copy(); self.hi2 = self.hi.copy(); mid = yc
        self.lo2[half & (dy > 0)] = mid[half & (dy > 0)]; self.hi2[half & (dy <= 0)] = mid[half & (dy <= 0)]
        fall = np.clip(1 - (rho - r) / 0.45, 0, 1) * (~gone)
        self.shift = np.stack([0.014 * fall ** 2 + rng.normal(0, 0.004, n) * fall, rng.normal(0, 0.003, n) * fall, rng.normal(0, 0.002, n) * fall], 1)
        self.tilt = q_axis(rng.normal(0, 1, (n, 3)), rng.normal(0, math.radians(1.6), n) * fall)
        ss = lambda lo, hi, x: (lambda u: u * u * (3 - 2 * u))(np.clip((x - lo) / (hi - lo), 0, 1))
        self.soot = np.where(self.w == 0, 1.0, 0.55 + 0.45 * ss(r, r + 0.30, rho))     # front face is sooted per vertex (soot_at)
        self.gone = gone | faller
        # ---- debris pieces
        P = []
        def piece(i, ylo, yhi, kind):
            L_ = yhi - ylo
            k = int(rng.choice([1, 2, 2, 3, 3])) if (kind != "fall" and L_ > 0.12) else 1
            cuts = np.linspace(ylo, yhi, k + 1)
            for j in range(k):
                rr = float(rho[i] / r[i])
                if kind == "blast" and rng.random() < 0.55 * (1 - rr) + 0.12:
                    continue                                    # pulverised: only dust and chips remain
                f = rng.uniform(0.72, 0.97, 3)
                hs = np.array([BW / 2 * f[0], (cuts[j + 1] - cuts[j]) / 2 * f[1], BH / 2 * f[2]])
                c = np.array([self.xc[i], (cuts[j] + cuts[j + 1]) / 2, self.zc[i]])
                ca, sa = math.cos(a[i]), math.sin(a[i]); ff = 1 - 0.65 * min(rr, 1.0)
                if kind == "fall":
                    v = np.array([rng.uniform(-0.4, 1.6), rng.uniform(-0.5, 0.5), rng.uniform(-0.3, 0.3)]); td = rng.uniform(0.03, 0.16); om = rng.uniform(1, 6)
                elif self.w[i] == 1 or rr < 0.6:
                    rad = rng.uniform(0, 7) * rr
                    v = np.array([rng.uniform(6, 22) * ff + 2, rad * ca, rad * sa + rng.uniform(0, 3)]); td = 0.0; om = rng.uniform(5, 26)
                    if self.w[i] == 0:
                        v[0] *= 0.6
                else:
                    rad = rng.uniform(1, 6)
                    v = np.array([-rng.uniform(2, 10), rad * ca, rad * sa + rng.uniform(0, 2.5)]); td = 0.0; om = rng.uniform(4, 20)
                P.append(np.concatenate([c, hs, v, [td, om], rng.normal(0, 1, 3), [rng.uniform(0, 6.283)], self.bcol[i] * self.soot_piece(rr, self.w[i], rng)]))
        for i in np.where(gone)[0]:
            piece(i, self.lo[i], self.hi[i], "blast")
        for i in np.where(faller)[0]:
            piece(i, self.lo[i], self.hi[i], "fall")
        for i in np.where(half)[0]:
            if dy[i] > 0:
                piece(i, self.lo[i], mid[i], "blast")
            else:
                piece(i, mid[i], self.hi[i], "blast")
        P = np.array(P)
        self.p0 = P[:, 0:3]; self.hs = P[:, 3:6]; self.v0 = P[:, 6:9]; self.td = P[:, 9]; self.om = P[:, 10]
        self.ax = P[:, 11:14]; self.yaw = P[:, 14]; self.pcol = P[:, 15:18]
        zr = self.hs[:, 2] + 0.002
        vz = self.v0[:, 2]
        self.t1 = (vz + np.sqrt(vz * vz + 2 * G * np.maximum(self.p0[:, 2] - zr, 0))) / G
        self.p1 = self.p0 + self.v0 * self.t1[:, None]; self.p1[:, 2] = zr
        vz1 = vz - G * self.t1
        self.v1 = np.stack([self.v0[:, 0] * 0.42, self.v0[:, 1] * 0.42, -vz1 * 0.22], 1)
        self.t2 = 2 * self.v1[:, 2] / G
        self.p2 = self.p1 + self.v1 * self.t2[:, None]; self.p2[:, 2] = zr
        self.q1 = q_axis(self.ax, self.om * self.t1)
        self.qr = q_axis(np.tile([0.0, 0, 1.0], (len(P), 1)), self.yaw)
        gy = (self.lo[self.gone] + self.hi[self.gone]) / 2; rear = self.w[self.gone] == 1
        self.hole = dict(width=float(self.hi[self.gone][rear].max() - self.lo[self.gone][rear].min()),
                         height=float(self.zc[self.gone][rear].max() - self.zc[self.gone][rear].min() + BH),
                         bricks=int(self.gone.sum()), pieces=int(len(P)))
        self.reach = float(np.percentile((self.p2 + self.v1 * 0.4 * 0.08)[:, 0], 97))

    def soot_at(self, y, z):
        """Scorch factor on the struck face: black at the breach edge, fading out in a ragged star."""
        a = np.arctan2(z - ZI, y); rho = np.hypot(y, z - ZI)
        r = self.R_HOLE[0] * (1 + 0.16 * np.sin(3 * a + 1.0) + 0.10 * np.sin(7 * a + 0.4))
        reach = 0.95 + 0.35 * np.sin(5 * a + 0.7) + 0.2 * np.sin(11 * a + 2.0) + 0.25 * (fbm(y * 9, z * 9, 5, 3) - 0.5)
        u = np.clip((rho - r) / reach, 0, 1); u = u * u * (3 - 2 * u)
        return 0.07 + 0.93 * u ** 1.15

    @staticmethod
    def soot_piece(rr, w, rng):
        return rng.uniform(0.25, 0.6) if (w == 0 and rr < 1.0) else rng.uniform(0.7, 1.0)

    # ------------------------------------------------------------------ meshes
    def _wall_obj(self, name, keep, lo, hi, shift, tilt, soot):
        idx = np.where(keep)[0]; n = len(idx)
        L_ = (hi - lo)[idx]; yc = ((lo + hi) / 2)[idx]; xc = self.xc[idx]; zc = self.zc[idx]; w = self.w[idx]
        cen = [np.stack([xc, yc, zc], 1)]; hal = [np.stack([np.full(n, BW / 2), L_ / 2, np.full(n, BH / 2)], 1)]
        colr = [self.bcol[idx] * soot[idx, None]]
        mc = self.mcol[idx] * soot[idx, None]
        cen.append(np.stack([xc, yc + J / 2, zc - BH / 2 - J / 2], 1)); hal.append(np.stack([np.full(n, BW / 2 - 0.004), L_ / 2 + J / 2, np.full(n, J / 2)], 1)); colr.append(mc)
        cen.append(np.stack([xc, yc + L_ / 2 + J / 2, zc], 1)); hal.append(np.stack([np.full(n, BW / 2 - 0.004), np.full(n, J / 2), np.full(n, BH / 2)], 1)); colr.append(mc)
        f = w == 0
        cen.append(np.stack([np.full(f.sum(), BW + J / 2), yc[f], zc[f]], 1)); hal.append(np.stack([np.full(f.sum(), J / 2), L_[f] / 2 + J / 2, np.full(f.sum(), BH / 2 + J / 2)], 1)); colr.append(mc[f])
        R = None
        if shift is not None:
            sh = shift[idx]; qm = q_mat(tilt[idx])
            cen[0] = cen[0] + sh; cen[1] = cen[1] + sh; cen[2] = cen[2] + sh; cen[3] = cen[3] + sh[f]
            R = np.concatenate([qm, qm, qm, qm[f]])
        V, F, C = boxes(np.concatenate(cen), np.concatenate(hal), np.concatenate(colr), R)
        if shift is not None:                       # scorch on the struck face, shaded per vertex so it grades across bricks
            m = V[:, 0] < BW + J + 0.02
            C[m, :3] *= self.soot_at(V[m, 1], V[m, 2])[:, None]
        me = new_mesh(name, V, [F], smooth=False, attrs={"col": C}); me.shade_flat()
        return new_obj(name, me, self.col, self.mat)

    def debris_state(self, td):
        """Centres and rotation matrices of every debris piece td seconds after the hit."""
        t = np.maximum(td - self.td, 0.0)
        a1 = t < self.t1; a2 = (~a1) & (t < self.t1 + self.t2)
        p = self.p0 + self.v0 * t[:, None]; p[:, 2] -= 0.5 * G * t * t
        u = t - self.t1
        pb = self.p1 + self.v1 * u[:, None]; pb[:, 2] -= 0.5 * G * u * u
        ur = np.maximum(t - self.t1 - self.t2, 0.0)
        pr = self.p2 + (self.v1 * 0.4) * (0.08 * (1 - np.exp(-ur / 0.08)))[:, None]; pr[:, 2] = self.p2[:, 2]
        p = np.where(a1[:, None], p, np.where(a2[:, None], pb, pr))
        p[~a1, 2] += np.asarray(env.ground_h(p[~a1, 0], p[~a1, 1]))
        q = q_axis(self.ax, self.om * np.minimum(t, self.t1))
        s = np.clip(u / np.maximum(self.t2, 1e-3), 0, 1); s = s * s * (3 - 2 * s)
        q = np.where(a1[:, None], q, q_slerp(self.q1, self.qr, s))
        return p, q_mat(q)

    def update(self, td, shutter=0.0):
        hit = td >= 0
        self.intact.hide_render = hit; self.breached.hide_render = not hit
        self.debris.hide_render = not hit; self.chip_ob.hide_render = not hit
        if not hit:
            return
        p, R = self.debris_state(td)
        V, F, C = boxes(p, self.hs, self.pcol, R)
        me = new_mesh("debris", V, [F], smooth=False, attrs={"col": C}); me.shade_flat(); me.materials.append(self.mat)
        old = self.debris.data; self.debris.data = me; bpy.data.meshes.remove(old)
        cp, cv, air = self.chips.state(td)
        me = fx.streak_mesh("chips", cp, cv, self.chips.size, shutter, self.chips.shape); me.materials.append(self.chip_mat)
        old = self.chip_ob.data; self.chip_ob.data = me; bpy.data.meshes.remove(old)
