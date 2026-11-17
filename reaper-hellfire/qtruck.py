"""The target: an armed pickup (a generic four-door "technical" with a heavy machine gun in the bed), and what the
missile leaves of it.

Target-set frame: the pickup's long axis is Y, front towards +Y, wheels on z = 0, centre at the origin when it stands.
The body carries a 'Wreck' shape key and a second colour set; doors, bonnet, tailgate, two wheels and the gun are
separate rigid pieces that are thrown clear on ballistic paths.  Nobody is modelled in or on the vehicle.
"""
import bpy, math, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from mathutils import Quaternion, Vector
from qgeo import *
from util import smoothstep, nodemat
import qconst as C

PAINT = (0.50, 0.48, 0.43, 1); TRIM = (0.035, 0.035, 0.04, 1); TYRE = (0.022, 0.022, 0.024, 1); HUB = (0.30, 0.30, 0.31, 1); STEEL = (0.07, 0.075, 0.07, 1)
LAMP = (0.75, 0.74, 0.68, 1); RED = (0.35, 0.02, 0.02, 1)
WR = 0.40; WHEELS = {"FL": (-0.80, 1.55), "FR": (0.80, 1.55), "RL": (-0.80, -1.50), "RR": (0.80, -1.50)}

def hexa(lo, hi, top_lo=None, top_hi=None):
    """Box from lo to hi whose top face may be a different rectangle (top_lo/top_hi give its x,y extent)."""
    (x0, y0, z0), (x1, y1, z1) = lo, hi; tx0, ty0 = top_lo or (x0, y0); tx1, ty1 = top_hi or (x1, y1)
    V = np.array([[x0, y0, z0], [tx0, ty0, z1], [x0, y1, z0], [tx0, ty1, z1], [x1, y0, z0], [tx1, ty0, z1], [x1, y1, z0], [tx1, ty1, z1]], float)
    Q = np.array([[0, 1, 3, 2], [4, 6, 7, 5], [0, 4, 5, 1], [2, 3, 7, 6], [0, 2, 6, 4], [1, 5, 7, 3]])
    return V, Q, None

def truck_mat():
    m, N, L, P = nodemat("TruckPaint")
    a = N.new("ShaderNodeAttribute"); a.attribute_name = "col"; b = N.new("ShaderNodeAttribute"); b.attribute_name = "col2"
    burn = N.new("ShaderNodeValue"); burn.name = "Burn"; burn.outputs[0].default_value = 0.0
    mix = N.new("ShaderNodeMixRGB"); L.new(burn.outputs[0], mix.inputs[0]); L.new(a.outputs["Color"], mix.inputs[1]); L.new(b.outputs["Color"], mix.inputs[2])
    tc = N.new("ShaderNodeTexCoord"); n = N.new("ShaderNodeTexNoise"); n.inputs["Scale"].default_value = 2.2; n.inputs["Detail"].default_value = 6; L.new(tc.outputs["Object"], n.inputs["Vector"])
    dust = N.new("ShaderNodeMixRGB"); dust.inputs[2].default_value = (0.36, 0.30, 0.22, 1)                       # road dust, thicker low down
    sep = N.new("ShaderNodeSeparateXYZ"); L.new(tc.outputs["Object"], sep.inputs[0])
    mr = N.new("ShaderNodeMapRange"); mr.inputs["From Min"].default_value = 1.5; mr.inputs["From Max"].default_value = 0.3; mr.inputs["To Min"].default_value = 0.10; mr.inputs["To Max"].default_value = 0.75
    L.new(sep.outputs["Z"], mr.inputs["Value"]); mul = N.new("ShaderNodeMath"); mul.operation = 'MULTIPLY'; L.new(mr.outputs[0], mul.inputs[0]); L.new(n.outputs["Fac"], mul.inputs[1])
    keep = N.new("ShaderNodeMapRange"); keep.inputs["To Min"].default_value = 1.0; keep.inputs["To Max"].default_value = 0.12; L.new(burn.outputs[0], keep.inputs["Value"])    # soot, not dust, once it has burnt
    mul2 = N.new("ShaderNodeMath"); mul2.operation = 'MULTIPLY'; L.new(mul.outputs[0], mul2.inputs[0]); L.new(keep.outputs[0], mul2.inputs[1])
    L.new(mul2.outputs[0], dust.inputs[0]); L.new(mix.outputs[0], dust.inputs[1]); L.new(dust.outputs[0], P.inputs["Base Color"])
    rr = N.new("ShaderNodeMapRange"); rr.inputs["To Min"].default_value = 0.42; rr.inputs["To Max"].default_value = 0.92; L.new(burn.outputs[0], rr.inputs["Value"]); L.new(rr.outputs[0], P.inputs["Roughness"])
    return m, burn

def _wheel():
    S = Shell(); w = 0.135
    V, Q, T = revolve([(-w, 0.30), (-w, 0.375), (-w * 0.6, WR), (w * 0.6, WR), (w, 0.375), (w, 0.30)], 24, axis=EX, side=EY); S.add(V, Q, T, TYRE)
    V, Q, T = revolve([(-w * 0.9, 0.0), (-w * 0.9, 0.245), (-w * 0.5, 0.26), (w * 0.5, 0.26), (w * 0.9, 0.245), (w * 0.9, 0.0)], 16, axis=EX, side=EY); S.add(V, Q, T, HUB)
    return S.mesh("truck_wheel")

def _body():
    S = Shell()
    V, Q, T = hexa((-0.90, -2.65, 0.48), (0.90, 2.65, 1.00)); S.add(V, Q, T, PAINT)                                 # lower body
    V, Q, T = hexa((-0.88, -0.78, 1.00), (0.88, 1.12, 1.28)); S.add(V, Q, T, PAINT)                                 # cab, waist up to the window line
    V, Q, T = hexa((-0.86, -0.72, 1.28), (0.86, 1.08, 1.80), (-0.73, -0.60), (0.73, 0.52)); S.add(V, Q, T, PAINT)   # greenhouse
    V, Q, T = hexa((-0.90, -2.58, 1.00), (-0.82, -0.82, 1.42)); S.add(V, Q, T, PAINT)                               # bed sides and front wall
    V, Q, T = hexa((0.82, -2.58, 1.00), (0.90, -0.82, 1.42)); S.add(V, Q, T, PAINT)
    V, Q, T = hexa((-0.90, -0.86, 1.00), (0.90, -0.78, 1.42)); S.add(V, Q, T, PAINT)
    for y in (2.70, -2.70):
        V, Q, T = hexa((-0.92, y - 0.07, 0.50), (0.92, y + 0.07, 0.72)); S.add(V, Q, T, TRIM)                       # bumpers
    V, Q, T = hexa((-0.60, 2.645, 0.80), (0.60, 2.665, 1.00)); S.add(V, Q, T, TRIM)                                 # grille
    for x in (-0.74, 0.74):
        V, Q, T = hexa((x - 0.14, 2.645, 0.84), (x + 0.14, 2.665, 0.99)); S.add(V, Q, T, LAMP)
        V, Q, T = hexa((x - 0.10, -2.665, 0.80), (x + 0.10, -2.645, 0.98)); S.add(V, Q, T, RED)
        V, Q, T = hexa((x * 1.19 - 0.09, 0.90, 1.26), (x * 1.19 + 0.09, 0.96, 1.40)); S.add(V, Q, T, TRIM)          # mirrors
        for y in (1.55, -1.50):                                                                                      # wheel-arch shadow
            V, Q, T = hexa((x * 1.215 - 0.012, y - 0.50, 0.46), (x * 1.215 + 0.012, y + 0.50, 0.86)); S.add(V, Q, T, TRIM)
    V, Q, T = hexa((-0.84, -2.55, 0.40), (0.84, 2.55, 0.50)); S.add(V, Q, T, TRIM)                                  # chassis rails
    return S

def _glass():
    S = Shell(); e = 0.008
    for sx in (-1, 1):                                                                                               # side windows (two a side)
        for y0, y1, t0, t1 in ((0.22, 0.98, 0.22, 0.47), (-0.62, 0.14, -0.52, 0.14)):
            xb = sx * (0.86 + e); xt = sx * (0.74 + e)
            S.add(*plate([(xb, y0, 1.31), (xb, y1, 1.31), (xt, t1, 1.75), (xt, t0, 1.75)], (sx, 0, 0.25), 0.01), color=(0.02, 0.03, 0.04, 1))
    S.add(*plate([(-0.80, 1.08 + e, 1.31), (0.80, 1.08 + e, 1.31), (0.68, 0.56 + e, 1.76), (-0.68, 0.56 + e, 1.76)], (0, 1, 1.0), 0.01), color=(0.02, 0.03, 0.04, 1))     # windscreen
    S.add(*plate([(-0.78, -0.72 - e, 1.33), (0.78, -0.72 - e, 1.33), (0.68, -0.62 - e, 1.74), (-0.68, -0.62 - e, 1.74)], (0, -1, 0.2), 0.01), color=(0.02, 0.03, 0.04, 1))  # rear window
    return S

def _gun():
    """12.7 mm class heavy machine gun on a pedestal in the bed, muzzle towards the front."""
    S = Shell(); p = np.array([0.0, -1.55, 1.00])
    S.add(*revolve([(0.0, 0.07), (0.05, 0.045), (0.80, 0.04)], 12, axis=EZ, origin=p, side=EX), color=STEEL)
    S.add(*hexa((-0.22, -1.77, 1.00), (0.22, -1.33, 1.03)), color=STEEL)
    a = math.radians(9); d = np.array([0, math.cos(a), math.sin(a)]); o = p + np.array([0, 0, 0.90])
    R = np.array([[1, 0, 0], [0, math.cos(a), -math.sin(a)], [0, math.sin(a), math.cos(a)]])
    S.add(*box(o + d * 0.05, (0.11, 0.80, 0.13), rot=R), color=STEEL)
    S.add(*revolve([(0.45, 0.030), (0.80, 0.030), (0.80, 0.019), (1.48, 0.019), (1.48, 0.030), (1.60, 0.030)], 10, axis=d, origin=o, side=EX), color=STEEL)
    S.add(*box(o + d * 0.10 + np.array([-0.17, 0, -0.02]), (0.20, 0.30, 0.16), rot=R), color=(0.10, 0.12, 0.07, 1))       # ammunition box
    for sx in (-1, 1):
        S.add(*revolve([(-0.36, 0.014), (-0.56, 0.014)], 8, axis=d, origin=o + np.array([sx * 0.06, 0, 0]), side=EX), color=STEEL)   # spade grips
    return S

class Piece:
    """A rigid part that is thrown clear at the hit: ballistic flight with drag, tumbling, then lying where it lands."""
    def __init__(self, ob, pivot, v0, spin_axis, spin, z_rest, rest_q, drag=0.35):
        self.ob = ob; self.p0 = np.array(pivot, float); self.v0 = np.array(v0, float); self.ax = Vector(spin_axis).normalized(); self.spin = spin
        self.zr = z_rest; self.rq = Quaternion(rest_q); self.k = drag; ob.rotation_mode = 'QUATERNION'
        t = 0.0; self.tl = 9.0
        while t < 9.0:                                              # landing time
            if self._z(t) <= z_rest and t > 0.05:
                self.tl = t; break
            t += 0.004
    def _z(self, t):
        return self.p0[2] + self.v0[2] * t - 0.5 * C.G * t * t
    def at(self, td):
        if td <= 0:
            return self.p0, Quaternion()
        t = min(td, self.tl); k = self.k
        p = self.p0 + np.array([self.v0[0] * (1 - math.exp(-k * t)) / k, self.v0[1] * (1 - math.exp(-k * t)) / k, 0.0]); p[2] = max(self._z(t), self.zr)
        q = Quaternion(self.ax, self.spin * t)
        if td > self.tl:
            u = smoothstep(0.0, 0.12, td - self.tl); q = q.slerp(self.rq, u)
            sl = 0.25 * (1 - math.exp(-(td - self.tl) / 0.25)); h = np.array([self.v0[0], self.v0[1], 0.0]); p = p + h / (np.linalg.norm(h) + 1e-6) * sl
        return p, q

class Truck:
    def __init__(self, col, seed=5):
        rng = np.random.default_rng(seed)
        self.root = bpy.data.objects.new("Truck", None); col.objects.link(self.root)
        mat, self.burn = truck_mat()
        S = _body(); me = S.mesh("truck_body"); self._wreck_attrs(me, rng)
        self.body = new_obj("Truck_Body", me, col, mat); self.body.parent = self.root
        self.body.shape_key_add(name="Basis"); sk = self.body.shape_key_add(name="Wreck"); sk.data.foreach_set("co", self._wreck_co(me, rng).astype(np.float32).ravel()); sk.value = 0.0; self.sk = sk
        self.glass = new_obj("Truck_Glass", _glass().mesh("truck_glass"), col, glass_mat("TruckGlass", (0.015, 0.02, 0.025), 0.04)); self.glass.parent = self.root
        wm = _wheel(); self.wheels = {}
        for k, (x, y) in WHEELS.items():
            w = bpy.data.objects.new("Truck_Wheel" + k, wm); col.objects.link(w); w.rotation_mode = 'QUATERNION'; self.wheels[k] = w
        wm.materials.append(paint_mat("WheelPaint", rough=0.75))
        self.pieces = {}
        def piece(name, shell, pivot, v0, axis, spin, zr, rq, mat_=mat):
            V = np.concatenate(shell.v) - np.asarray(pivot)[None]; shell.v = [V]; me_ = shell.mesh("truck_" + name)
            c2 = np.concatenate(shell.c) * np.array([0.22, 0.20, 0.19, 1.0], np.float32); at = me_.attributes.new("col2", 'FLOAT_COLOR', 'POINT'); at.data.foreach_set("color", c2.ravel())
            ob = new_obj("Truck_" + name, me_, col, mat_); self.pieces[name] = Piece(ob, pivot, v0, axis, spin, zr, rq)
        piece("hood", Shell().add(*hexa((-0.87, 1.14, 1.00), (0.87, 2.63, 1.17), (-0.85, 1.14), (0.83, 2.60)), color=PAINT), (0, 1.9, 1.08), (2.5, 9.0, 13.0), (1, 0.2, 0), 7.0, 0.06, (0.99, 0.05, 0.08, 0.1))
        piece("tailgate", Shell().add(*hexa((-0.90, -2.66, 1.00), (0.90, -2.59, 1.42)), color=PAINT), (0, -2.62, 1.21), (3.0, -15.0, 6.0), (1, 0, 0.3), -9.0, 0.05, (0.70, 0.70, 0.0, 0.1))
        piece("doorR", Shell().add(*hexa((0.885, 0.20, 0.55), (0.915, 1.08, 1.29)), color=PAINT), (0.90, 0.64, 0.92), (16.0, 3.0, 7.5), (0.2, 1, 0.1), 11.0, 0.04, (0.70, 0.0, 0.70, 0.15))
        piece("doorL", Shell().add(*hexa((-0.915, -0.66, 0.55), (-0.885, 0.18, 1.29)), color=PAINT), (-0.90, -0.24, 0.92), (-9.0, -2.0, 5.0), (0.1, 1, 0.3), -8.0, 0.04, (0.70, 0.0, -0.70, 0.1))
        piece("gun", _gun(), (0.0, -1.55, 1.45), (7.0, -5.0, 14.0), (0.4, 1, 0.2), 6.0, 0.10, (0.6, 0.3, 0.7, 0.2), paint_mat("GunPaint", rough=0.45, metal=0.6))
        self._wheel_piece = {"RR": Piece(self.wheels["RR"], (0.80, -1.50, WR), (13.0, -6.0, 9.0), (0.2, 1, 0.4), 14.0, 0.14, (0.70, 0.0, 0.70, 0.0), drag=0.25),
                             "FL": Piece(self.wheels["FL"], (-0.80, 1.55, WR), (-7.0, 6.0, 5.0), (0.3, 1, 0.1), -10.0, 0.14, (0.70, 0.0, 0.70, 0.0), drag=0.25)}

    def _dist(self, V):
        return np.linalg.norm(V - C.HIT[None], axis=1), np.hypot(V[:, 0] - C.HIT[0], V[:, 1] - C.HIT[1])

    def _wreck_co(self, me, rng):
        n = len(me.vertices); V = np.empty(n * 3, np.float32); me.vertices.foreach_get("co", V); V = V.reshape(-1, 3).astype(np.float64); W = V.copy()
        d, dxy = self._dist(V)
        up = V[:, 2] > 0.95
        W[:, 2] = np.where(up, 0.95 + (V[:, 2] - 0.95) * (1 - 0.58 * np.exp(-(dxy / 1.3) ** 2)), V[:, 2])               # cab and bed walls driven down
        rad = np.stack([V[:, 0] - C.HIT[0], V[:, 1] - C.HIT[1]], 1); rn = rad / (np.linalg.norm(rad, axis=1, keepdims=True) + 0.15)
        push = 0.42 * np.exp(-(d / 1.7) ** 2) * (V[:, 2] > 0.6)
        W[:, 0] += rn[:, 0] * push + 0.12 * np.exp(-(d / 2.2) ** 2); W[:, 1] += rn[:, 1] * push * 0.7                     # torn outwards, shoved down-range
        ph = rng.uniform(0, 6.28, 6); amp = 0.11 * (0.25 + np.exp(-(d / 2.4) ** 2))
        W[:, 0] += amp * np.sin(V[:, 1] * 3.1 + V[:, 2] * 4.0 + ph[0]) * np.sin(V[:, 1] * 1.3 + ph[1])
        W[:, 1] += amp * np.sin(V[:, 0] * 3.7 + V[:, 2] * 2.9 + ph[2]) * 0.6
        W[:, 2] += amp * np.sin(V[:, 0] * 2.9 + V[:, 1] * 2.3 + ph[3]) * (V[:, 2] > 0.7)
        W[:, 2] -= 0.13 * (V[:, 2] > 0.3) + 0.10 * np.clip(-V[:, 1] / 2.6, 0, 1) * (V[:, 2] > 0.3)                         # down on its rims, rear lower
        return W

    def _wreck_attrs(self, me, rng):
        n = len(me.vertices); V = np.empty(n * 3, np.float32); me.vertices.foreach_get("co", V); V = V.reshape(-1, 3)
        col = np.empty(n * 4, np.float32); me.attributes["col"].data.foreach_get("color", col); col = col.reshape(-1, 4)
        d, dxy = self._dist(V.astype(np.float64)); w = np.clip(np.exp(-(d / 2.6) ** 2) * 1.3, 0, 1)[:, None]
        char = np.array([0.018, 0.016, 0.015, 1.0], np.float32)[None]; rust = col * np.array([0.16, 0.12, 0.10, 1.0], np.float32)[None]
        c2 = rust * (1 - w) + char * w; c2[:, 3] = 1.0
        at = me.attributes.new("col2", 'FLOAT_COLOR', 'POINT'); at.data.foreach_set("color", c2.ravel())

    def update(self, t):
        td = t - C.T_HIT; y = C.truck_y(t) if td < 0 else 0.0
        k = smoothstep(0.0, 0.035, td); shove = 0.38 * (1 - math.exp(-max(td, 0) / 0.12)); hop = 0.10 * math.exp(-max(td, 0) / 0.18) * math.sin(min(max(td, 0) / 0.18, 1.0) * math.pi) if td > 0 else 0.0
        self.root.location = (shove, y, hop); self.root.rotation_euler = (0, 0.035 * k, -0.05 * k)
        self.sk.value = k; self.burn.outputs[0].default_value = smoothstep(0.0, 0.10, td)
        self.glass.hide_render = td >= 0
        roll = Quaternion((1, 0, 0), -y / WR)
        for name, w in self.wheels.items():
            x0, y0 = WHEELS[name]
            if td >= 0 and name in self._wheel_piece:
                p, q = self._wheel_piece[name].at(td); w.location = p; w.rotation_quaternion = q
            else:
                w.location = (x0 + shove, y0 + y, WR - 0.10 * k + hop); w.rotation_quaternion = (Quaternion((0, 1, 0), 0.20 * k * (1 if x0 > 0 else -1)) @ roll)
        for name, pc in self.pieces.items():
            p, q = pc.at(td); pc.ob.location = (p[0], p[1] + y, p[2]); pc.ob.rotation_quaternion = q
