"""Shot definitions and frame renderer for the 120 mm mortar explosion-comparison segment.

  python3 mshots.py <shot> <out_dir> [--sim <cache_dir>] [--res 1280x720] [--spp N] [--frames a-b | i,j,k]

Shots: card, load, fire (mortar pit) and fall, impact, radius, after (target).  Time base: t = seconds
after the round strikes the firing pin; it lands at T_HIT.  One sim ("master") frame is 1/120 s.
"""
import bpy, sys, os, math, json, time, argparse
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "grenade-explosion")); sys.path.insert(0, os.path.join(HERE, "..", "rpg7-explosion")); sys.path.insert(0, HERE)
import numpy as np
from mathutils import Vector, Quaternion
import manta_fix  # noqa: F401
import env, figure, fx
import shots as gshots
from smoke_mat import blast_material
from util import *
import mconst as C, m120, ruins
from m120 import aim_quat

FPS = C.FPS; DT = C.MASTER_DT; T_HIT = C.T_HIT; T_REL = C.T_RELEASE
D = math.radians
shake = gshots.shake
SIM_OF = {"fire": "launch", "impact": "impact", "radius": "impact"}
SET_OF = {"load": "pit", "fire": "pit", "fall": "target", "impact": "target", "radius": "target", "after": "target"}
M0 = np.array([C.MX, 0.0, 0.0])
EY = np.array([0.0, 1.0, 0.0]); NUP = np.array([-math.sin(C.ELEV), 0.0, math.cos(C.ELEV)])

# ----------------------------------------------------------------------------- the round on its way into the tube
_RK = [(-4.6, np.array([0.74, -0.20, 0.98]), np.array([0.10, 0.25, 0.96])),
       (-3.9, np.array([0.80, -0.17, 1.45]), np.array([0.30, 0.12, 0.95])),
       (-3.3, np.array([0, 0, C.ZB]) + C.BORE * (C.TUBE_LEN + 0.03), C.BORE),
       (-2.3, np.array([0, 0, C.ZB]) + C.BORE * C.HANG, C.BORE)]

def recoil(t):
    return 0.024 * (1 - math.exp(-t / 0.006)) * math.exp(-t / 0.10) if t > 0 else 0.0

def plate_dz(t):
    return -0.014 * (1 - math.exp(-t / 0.012)) + 0.006 * math.exp(-t / 0.08) * math.sin(t * 55) * (t < 0.6) if t > 0 else 0.0

def round_pose(t):
    """World position of the round's tail and its axis (pit set)."""
    if t >= T_REL:
        if t < C.T_EXIT:
            return C.BALL + np.array([0, 0, plate_dz(t)]) + C.BORE * (C.tail_s(t) - recoil(t)), C.BORE
        v = C.launch_vel(t); return C.launch_pos(t), v / np.linalg.norm(v)
    if t <= _RK[0][0]:
        return M0 + _RK[0][1], _RK[0][2] / np.linalg.norm(_RK[0][2])
    for (t0, p0, a0), (t1, p1, a1) in zip(_RK[:-1], _RK[1:]):
        if t <= t1:
            u = smoothstep(0, 1, (t - t0) / (t1 - t0)); a = a0 / np.linalg.norm(a0) * (1 - u) + a1 / np.linalg.norm(a1) * u
            return M0 + p0 * (1 - u) + p1 * u, a / np.linalg.norm(a)
    return M0 + _RK[-1][1], C.BORE

# ----------------------------------------------------------------------------- Ghost Man: assistant gunner
MAN_XY = (0.66, -0.50)
FR, FL = (0.17, 0.0, 0.0), (-0.17, 0.0, 0.0)
_E = dict(er=(0.75, -0.25, -0.45), el=(-0.75, -0.15, -0.45), fyr=80, fyl=100)
_H0 = ((0.10, 0.25, 1.30), (-0.10, 0.25, 1.40))
_k = figure._k
MAN_KEYS = [
    _k(-7.0, (0.00, 0.00, 0.955), 88, (0.00, 0.03, 1), 88, *_H0, FR, FL, head=90, **_E),
    _k(-4.6, (0.00, 0.00, 0.955), 88, (0.00, 0.03, 1), 88, *_H0, FR, FL, head=90, **_E),
    _k(-3.9, (0.02, 0.03, 0.965), 84, (0.05, 0.14, 1), 64, *_H0, FR, FL, head=80, **_E),
    _k(-3.3, (0.06, 0.07, 0.990), 80, (0.13, 0.30, 1), 40, *_H0, FR, FL, head=70, fpr=24, fpl=24, **_E),
    _k(-2.3, (0.04, 0.05, 0.955), 80, (0.10, 0.30, 1), 52, *_H0, FR, FL, head=75, **_E),
    _k(T_REL, (0.04, 0.05, 0.955), 80, (0.10, 0.30, 1), 52, *_H0, FR, FL, head=75, **_E),
    _k(T_REL + 0.20, (0.00, 0.00, 0.900), 86, (0.02, 0.28, 1), 70, (0.26, 0.40, 1.22), (-0.02, 0.50, 1.30), FR, FL, head=100,
       er=(0.7, -0.3, -0.5), el=(-0.7, -0.2, -0.5), fyr=80, fyl=100),
    _k(T_REL + 0.48, (-0.10, -0.10, 0.680), 96, (-0.14, 0.52, 1), 104, (0.30, 0.24, 0.84), (-0.30, 0.26, 0.84), FR, FL, head=150,
       er=(0.8, -0.3, 0.0), el=(-0.8, -0.3, 0.0), fyr=80, fyl=100),
    _k(1.60, (-0.10, -0.10, 0.680), 96, (-0.14, 0.52, 1), 104, (0.30, 0.24, 0.84), (-0.30, 0.26, 0.84), FR, FL, head=150,
       er=(0.8, -0.3, 0.0), el=(-0.8, -0.3, 0.0), fyr=80, fyl=100),
    _k(9.00, (-0.10, -0.10, 0.680), 96, (-0.14, 0.52, 1), 104, (0.30, 0.24, 0.84), (-0.30, 0.26, 0.84), FR, FL, head=150,
       er=(0.8, -0.3, 0.0), el=(-0.8, -0.3, 0.0), fyr=80, fyl=100),
]
GRIPS = (("r", m120.GRIP_LO + 0.05, 0.059), ("l", m120.GRIP_HI + 0.02, 0.057))

def man_pose(t, base):
    """Body from the key poses; while the round is held, both hands are solved onto it."""
    p = figure.throw_pose(t, MAN_KEYS)
    w = 1.0 - smoothstep(T_REL, T_REL + 0.14, t)
    if w > 0:
        tail, ax = round_pose(min(t, T_REL))
        side = -EY - ax * np.dot(-EY, ax); side /= np.linalg.norm(side)
        top = np.cross(side, ax); top = top if np.dot(top, NUP) > 0 else -top
        J = figure.solve(p)
        for s, gx, rb in GRIPS:
            off = side if s == "r" else (0.75 * top + 0.25 * side) / np.linalg.norm(0.75 * top + 0.25 * side)
            fc = tail + ax * gx + off * (rb + 0.046) - base
            sh = J["sho_" + s]; d = fc - sh; d /= np.linalg.norm(d) + 1e-9
            tgt = fc - d * 0.052
            p["hand_" + s] = np.asarray(p["hand_" + s]) * (1 - w) + tgt * w
    return p

def point_light(col, name, color, soft=0.3):
    ld = bpy.data.lights.new(name, 'POINT'); ld.shadow_soft_size = soft; ld.color = color; ld.energy = 0.0
    ob = bpy.data.objects.new(name, ld); col.objects.link(ob); return ob

# ----------------------------------------------------------------------------- burst effects (target set)
def dust_volume_mat(name, color):
    """Homogeneous dust volume; its density is set per frame (all strikes are nearly the same age)."""
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree; N = nt.nodes; L = nt.links; N.clear()
    out = N.new("ShaderNodeOutputMaterial"); pv = N.new("ShaderNodeVolumePrincipled")
    pv.inputs["Color"].default_value = (*color, 1); pv.inputs["Anisotropy"].default_value = 0.3; pv.inputs["Density"].default_value = 0.0
    L.new(pv.outputs[0], out.inputs["Volume"])
    return m, pv

class FragField:
    """Where fragments strike the ground: short radial dust spurts out to the 75 m bursting radius.  The steel
    itself is far too fast to see; these marks are what a camera would record."""
    def __init__(self, col, seed=4, n=560, rmax=None):
        rng = np.random.default_rng(seed); rmax = rmax or C.BURST_R
        az = rng.uniform(0, 2 * np.pi, n * 2); keep = rng.random(n * 2) < (0.55 + 0.45 * np.abs(np.sin(az))); az = az[keep][:n]; n = len(az)
        self.r = rng.uniform(3.5, rmax + 4.0, n) ** 1.0; self.az = az
        self.t = self.r / rng.uniform(650, 1150, n)
        self.len = rng.uniform(0.6, 1.8, n) * (0.45 + self.r / 55.0); self.wid = rng.uniform(0.22, 0.45, n) * (0.55 + self.r / 80.0)
        self.hgt = rng.uniform(0.22, 0.50, n) * (0.6 + self.r / 120.0); self.n = n
        U, F, _ = ellipsoid((0, 0, 0), (1, 1, 1), 12, 8); U = np.asarray(U); self.F = np.asarray(F)
        w1 = rng.normal(0, 1, (n, 3)); w2 = rng.normal(0, 1, (n, 3)); ph = rng.uniform(0, 6.283, (n, 2))       # lumpy, not egg-shaped
        lump = 1 + 0.30 * np.sin(np.einsum("mk,nk->nm", U, w1) * 2.2 + ph[:, :1]) + 0.20 * np.sin(np.einsum("mk,nk->nm", U, w2) * 4.0 + ph[:, 1:])
        self.UL = U[None, :, :] * lump[:, :, None]; self.U = U
        mat, self.pv = dust_volume_mat("FragDust", (0.66, 0.58, 0.45))
        self.ob = new_obj("FragStrikes", bpy.data.meshes.new("fs"), col, mat)
        self.ob.visible_shadow = False; self.ob.hide_render = True
    def update(self, td, gain=1.0):
        age = td - self.t; on = (age > 0) & (age < 3.5)
        self.ob.hide_render = not on.any()
        if not on.any():
            return
        a = age[on]; g = 1 - np.exp(-a / 0.045)
        er = np.stack([np.cos(self.az[on]), np.sin(self.az[on]), np.zeros(on.sum())], 1); et = np.stack([-er[:, 1], er[:, 0], er[:, 2]], 1)
        ln = self.len[on] * gain; wd = self.wid[on] * gain; hg = self.hgt[on] * gain
        cen = er * (self.r[on] + 0.5 * ln * g)[:, None]; cen[:, 2] = 0.10 + 0.5 * hg * g + 0.25 * a
        UL = self.UL[on]
        V = (cen[:, None, :] + UL[:, :, 0:1] * er[:, None, :] * (0.5 * ln * g + 0.1)[:, None, None]
             + UL[:, :, 1:2] * et[:, None, :] * (wd * (0.4 + 0.6 * g) * (1 + 0.5 * a))[:, None, None]
             + UL[:, :, 2:3] * np.array([0, 0, 1.0])[None, None, :] * (hg * (0.3 + 0.7 * g) * (1 + 0.6 * a))[:, None, None])
        m = len(self.U); F = (self.F[None] + (np.arange(on.sum()) * m)[:, None, None]).reshape(-1, self.F.shape[1])
        me = new_mesh("fs", V.reshape(-1, 3), [F]); me.materials.append(self.ob.data.materials[0])
        self.pv.inputs["Density"].default_value = 0.75 * gain ** 1.25 * math.exp(-max(td - 0.1, 0.0) / (0.75 * gain ** 0.5))
        old = self.ob.data; self.ob.data = me; bpy.data.meshes.remove(old)

class Ejecta:
    """Clods of earth thrown out of the crater and a short shower of glowing sparks."""
    def __init__(self, col, seed=8, scale=1.0):
        rng = np.random.default_rng(seed)
        self.clods = fx.Ballistic(int(800 * scale), rng, (5.0, 27.0 * scale ** 0.5), (14.0, 80.0), (0.8, 2.2), (0.012, 0.050 * scale ** 0.5), origin=(0, 0, 0.15), spread=0.5 * scale)
        self.sparks = fx.Ballistic(220, rng, (50.0, 230.0), (4.0, 80.0), (5.0, 11.0), (0.008, 0.018), origin=(0, 0, 0.3), spread=0.4)
        self.life = rng.uniform(0.08, 0.32, 220)
        self.c_ob = new_obj("Clods", bpy.data.meshes.new("c"), col, simple_mat("ClodMat", (0.090, 0.062, 0.040), rough=0.95))
        self.s_ob = new_obj("Sparks", bpy.data.meshes.new("s"), col, fx.emission_mat("SparkMat", (1.0, 0.52, 0.14), 26.0))
        self.s_ob.visible_shadow = False; self.c_ob.hide_render = True; self.s_ob.hide_render = True
    def update(self, td, shutter):
        self.c_ob.hide_render = td < 0; self.s_ob.hide_render = not (0 <= td < 0.34)
        if td < 0:
            return
        p, v, air = self.clods.state(td)
        me = fx.streak_mesh("c", p, v, self.clods.size, shutter, self.clods.shape); me.materials.append(self.c_ob.data.materials[0])
        old = self.c_ob.data; self.c_ob.data = me; bpy.data.meshes.remove(old)
        if td < 0.34:
            p, v, air = self.sparks.state(td); on = air & (td < self.life)
            if on.any():
                me = fx.streak_mesh("s", p[on], v[on], self.sparks.size[on], shutter, self.sparks.shape[on], min_len=2.0); me.materials.append(self.s_ob.data.materials[0])
                old = self.s_ob.data; self.s_ob.data = me; bpy.data.meshes.remove(old)
            else:
                self.s_ob.hide_render = True

class GroundRings:
    """Radius rings drawn on the ground (emissive, inside the scene so smoke and trees can hide them)."""
    SPEC = [("burst", C.BURST_R, 0.55, (1.0, 0.10, 0.05), 6.0), ("m67", C.M67_R, 0.32, (1.0, 0.62, 0.10), 6.0)]
    def __init__(self, col):
        self.obs = {}
        for name, r, w, c, s in self.SPEC:
            ob = new_obj("Ring_" + name, bpy.data.meshes.new("ring"), col, fx.emission_mat("RingMat_" + name, c, s))
            ob.visible_shadow = False; ob.visible_diffuse = False; ob.visible_glossy = False; ob.hide_render = True; self.obs[name] = ob
        self.fill = new_obj("Ring_fill", bpy.data.meshes.new("fill"), col, fx.emission_mat("RingFill", (1.0, 0.08, 0.03), 1.4, alpha=0.03))
        self.fill.visible_shadow = False; self.fill.visible_diffuse = False; self.fill.visible_glossy = False; self.fill.hide_render = True
    def update(self, radii):
        """radii: name -> current radius (0 hides it); 'fill' -> radius of the tinted disc."""
        for name, r_full, w, c, s in self.SPEC:
            r = radii.get(name, 0.0); ob = self.obs[name]; ob.hide_render = r <= 0.5
            if r > 0.5:
                a = np.linspace(0, 2 * np.pi, 361); ca, sa = np.cos(a), np.sin(a); ww = w * (0.6 + 0.4 * r / r_full)
                V = np.empty((722, 3)); V[0::2] = np.stack([(r - ww / 2) * ca, (r - ww / 2) * sa, np.full(361, 0.30)], 1)
                V[1::2] = np.stack([(r + ww / 2) * ca, (r + ww / 2) * sa, np.full(361, 0.30)], 1)
                me = new_mesh("ring", V, [grid_faces(361, 2)], smooth=False); me.materials.append(ob.data.materials[0])
                old = ob.data; ob.data = me; bpy.data.meshes.remove(old)
        rf = radii.get("fill", 0.0); self.fill.hide_render = rf <= 0.5
        if rf > 0.5:
            A, R_ = np.meshgrid(np.linspace(0, 2 * np.pi, 96, endpoint=False), np.linspace(0.02, 1.0, 6) * rf, indexing="ij")
            V = np.stack([R_ * np.cos(A), R_ * np.sin(A), np.full_like(A, 0.28)], -1).reshape(-1, 3)
            me = new_mesh("fill", V, [grid_faces(96, 6, wrap_u=True)]); me.materials.append(self.fill.data.materials[0])
            old = self.fill.data; self.fill.data = me; bpy.data.meshes.remove(old)

# ----------------------------------------------------------------------------- scene
class Stage(gshots.Stage):
    def __init__(self, which, sim_dir=None, kind=None):
        self.which = which; self.dom = None; self.T0 = {"launch": 0.0, "impact": T_HIT}.get(kind, 0.0)
        if sim_dir and os.path.exists(os.path.join(sim_dir, "sim.blend")):
            bpy.ops.wm.open_mainfile(filepath=os.path.join(sim_dir, "sim.blend"))
            for o in list(bpy.data.objects):
                if o.name.startswith("E_"):
                    bpy.data.objects.remove(o, do_unlink=True)
            self.dom = bpy.data.objects["BlastDomain"]; self.dom.data.materials.clear()
            self.fire0 = 8.0 if kind == "launch" else 15.0
            bm_ = blast_material(density=5.0, fire=self.fire0, ambient=0.17) if kind == "launch" else blast_material(density=9.0, fire=self.fire0, ambient=0.05)
            self.dom.data.materials.append(bm_); self.fire_node = bm_.node_tree.nodes[bm_["fire_node"]]
            if kind == "impact":
                for nd in bm_.node_tree.nodes:                      # keep the HE smoke dark: less lift of the sooty sim colours
                    if nd.type == 'VECT_MATH' and nd.operation == 'POWER':
                        nd.inputs[1].default_value = (0.72, 0.72, 0.72)
                for nd in bm_.node_tree.nodes:
                    if nd.type == 'VALTORGB':
                        for el, c in zip(sorted(nd.color_ramp.elements, key=lambda e: e.position),
                                         [(0, 0, 0), (0.55, 0.05, 0.0), (0.95, 0.22, 0.02), (1.0, 0.42, 0.07), (1.0, 0.62, 0.22)]):
                            el.color = (*c, 1)
            self.dom.hide_render = True
        else:
            bpy.ops.wm.read_factory_settings(use_empty=True)
        sc = self.sc = bpy.context.scene; sc.render.fps = FPS
        col_name = "ACTION"
        if which == "pit":
            self.env_col, self.ground = env.build(sc, C.PIT_X)
            self.ground.data.materials[0].node_tree.nodes["Blast"].outputs[0].default_value = 0.0
            col = self.col = bpy.data.collections.new(col_name); sc.collection.children.link(col)
            gz = float(env.ground_h(C.MX, 0.0))
            self.mortar, self.cannon, self.plate, self.bipod = m120.build_mortar(col); self.mortar.location = (C.MX, 0, 0)
            self.round = m120.Round(col)
            self.ghost = figure.ghost_material()
            self.man = figure.Figure(col, "GhostMan", self.ghost)
            self.man_base = np.array([C.MX + MAN_XY[0], MAN_XY[1], float(env.ground_h(C.MX + MAN_XY[0], MAN_XY[1]))])
            self.man.ob.location = self.man_base
            self.l_muzzle = point_light(col, "MuzzleFlash", (1.0, 0.70, 0.42), 0.25); self.l_muzzle.location = C.MUZZLE + C.BORE * 0.55
        else:
            self.env_col, self.ground = ruins.build_env(sc)
            self.blast_node = self.ground.data.materials[0].node_tree.nodes["Blast"]
            col = self.col = bpy.data.collections.new(col_name); sc.collection.children.link(col)
            self.ruins = ruins.Ruins(col)
            self.round = m120.Round(col, increments=0)
            self.frags = FragField(col); self.ejecta = Ejecta(col); self.rings = GroundRings(col)
            self.l_hit = point_light(col, "HitFlash", (1.0, 0.56, 0.24), 0.8); self.l_hit.location = (0, 0, 1.4)
        cd = bpy.data.cameras.new("Cam"); self.cam = bpy.data.objects.new("Cam", cd); sc.collection.objects.link(self.cam); sc.camera = self.cam
        cd.clip_start = 0.02; cd.clip_end = 6000; cd.sensor_width = 36; cd.sensor_fit = 'HORIZONTAL'
        self.cam.rotation_mode = 'QUATERNION'
        self._pose_t = None
        self.setup_render()

    def set_time(self, t, dt_out, opt):
        sc = self.sc; mb = opt.get("motion_blur", True); sc.render.use_motion_blur = mb
        if self.which == "pit":
            tp = min(t, 1.5)
            if self._pose_t is None or abs(tp - self._pose_t) > 1e-9:
                self.man.set_pose(man_pose(tp, self.man_base)); self._pose_t = tp
            def rstate(tt):
                tail, ax = round_pose(tt)
                return tail, aim_quat(ax)
            self.round.set_visible(t < C.T_EXIT + 0.6)
            self.key3(self.round.root, rstate, t, dt_out, mb and t > T_REL)
            self.cannon.location = np.array([0, 0, C.ZB + plate_dz(t)]) - (C.BORE * recoil(t))
            self.plate.location = (0, 0, plate_dz(t))
            self.l_muzzle.data.energy = 3200.0 * opt.get("flash", 1.0) * math.exp(-t / 0.012) if 0 <= t < 0.12 else 0.0
            self.l_muzzle.hide_render = self.l_muzzle.data.energy < 5.0
        else:
            td = t - T_HIT; hit = td >= 0
            self.round.set_visible(not hit)
            if not hit:
                def fstate(tt):
                    d = tt - T_HIT; v = C.fall_vel(d); v = v / np.linalg.norm(v)
                    return C.fall_pos(d) - v * C.ROUND_LEN, aim_quat(v, 2 * math.pi * 2.0 * d)
                self.key3(self.round.root, fstate, t, dt_out, mb and opt.get("round_blur", True))
            self.ruins.update(td)
            self.blast_node.outputs[0].default_value = 0.8 if hit else 0.0
            self.ground.data.shape_keys.key_blocks["Crater120"].value = 1.0 if hit else 0.0
            self.frags.update(td if opt.get("frags", True) else -1.0, opt.get("frag_gain", 1.0)); self.ejecta.update(td, 0.5 * dt_out)
            self.rings.update(opt.get("rings", {}))
            self.l_hit.data.energy = 70000.0 * opt.get("flash", 1.0) * math.exp(-td / 0.016) if 0 <= td < 0.25 else 0.0
            self.l_hit.hide_render = self.l_hit.data.energy < 5.0
        if self.dom is not None:
            self.dom.hide_render = t < self.T0
            self.fire_node.inputs[1].default_value = self.fire0 * (0.06 + 0.94 * math.exp(-max(t - self.T0, 0.0) / 0.045))

# ----------------------------------------------------------------------------- shots: mortar pit
def shot_load(n=96):
    """Real time: Ghost Man lifts the round to the muzzle, lowers its tail into the tube and holds it - "hanging"."""
    t0 = -4.78
    def frame(st, i):
        t = t0 + i / FPS; dt = 1.0 / FPS
        st.set_time(t, dt, {})
        u = i / (n - 1)
        pos = M0 + np.array([2.12 - 0.20 * u, 2.30 - 0.15 * u, 1.22 + 0.10 * u])
        tgt = M0 + np.array([0.66, -0.12, 1.02 + 0.12 * smoothstep(0.1, 0.8, u)])
        st.look(pos, tgt, 17.5, fstop=4.0, focus=float(np.linalg.norm(C.MUZZLE - pos)))
        return t, dt, dict(samples=10, shutter=0.4, anchors={"muzzle": C.MUZZLE})
    return n, frame

def shot_fire(n=96, lead=18):
    """Release in real time, then the shot in slow motion: flash, smoke jet up the bore, dust off the ground."""
    def frame(st, i):
        if i < lead:
            sf = 0; t = -(lead - i) / FPS * 0.9 - 0.002; dt = 0.9 / FPS
        elif i < lead + 60:
            sf = i - lead + 1; t = (sf - 1) * DT; dt = DT
        else:
            sf = 60 + 2 * (i - lead - 60 + 1); t = (sf - 1) * DT; dt = 2 * DT
        st.set_time(t, dt, {})
        u = i / (n - 1)
        pos = M0 + np.array([1.42, 2.50, 0.72 + 0.05 * u])
        tgt = M0 + np.array([0.60, 0.0, 1.22 + 0.80 * smoothstep(lead / n, 1.0, u)])
        off, rq = shake(t - 0.003, 1.3)
        q = st.look(pos + off, tgt, 16.5, fstop=4.0, focus=float(np.linalg.norm(C.MUZZLE - pos)))
        st.cam.rotation_quaternion = q @ rq
        return t, dt, dict(samples=8, sim=sf, shutter=0.3, anchors={"muzzle": C.MUZZLE})
    return n, frame

# ----------------------------------------------------------------------------- shots: target
def shot_fall(n=72):
    """Real time, last three seconds of flight: the camera rides down behind the round towards the ruins."""
    td0, td1 = -3.02, -0.035
    def cam_at(t):
        d = t - T_HIT; v = C.fall_vel(d); v = v / np.linalg.norm(v); nose = C.fall_pos(d)
        up = np.array([0, 0, 1.0]) - v * v[2]; up /= np.linalg.norm(up)
        u = (d - td0) / (td1 - td0)
        pos = nose - v * lerp(2.3, 1.9, u) + up * lerp(0.62, 0.50, u) + np.array([0, -0.30, 0])
        aim = nose + v * lerp(0.9, 0.3, u) + up * 0.12
        return pos, (Vector(aim) - Vector(pos)).to_track_quat('-Z', 'Y')
    def frame(st, i):
        td = lerp(td0, td1, i / (n - 1)); t = T_HIT + td; dt = (td1 - td0) / (n - 1)
        st.set_time(t, dt, {})
        pos, q = cam_at(t)
        st.look(pos, None, 24.0, quat=q)
        st.key3(st.cam, cam_at, t, dt, True)
        return t, dt, dict(samples=10, shutter=0.35, anchors={"target": (0, 0, 0)})
    return n, frame

def _slow(i, pre, one, k=2):
    """Slow-motion schedule round the burst: `pre` lead frames, `one` frames at 1 sim frame each, then k per frame."""
    if i < pre:
        return 0, T_HIT - (pre - i) * DT, DT
    if i < pre + one:
        sf = i - pre + 1; return sf, T_HIT + (sf - 1) * DT, DT
    sf = one + k * (i - pre - one + 1); return sf, T_HIT + (sf - 1) * DT, k * DT

def shot_impact(n=120):
    def frame(st, i):
        sf, t, dt = _slow(i, 10, 62, 2)
        st.set_time(t, dt, {})
        u = i / (n - 1)
        pos = np.array([-8.5 - 1.5 * u, -20.5 - 2.5 * u, 1.75 + 0.25 * u])
        tgt = np.array([1.0, 1.5, 2.0 + 3.6 * smoothstep(0.15, 1.0, u)])
        off, rq = shake(t - T_HIT - 0.05, 2.0)
        q = st.look(pos + off, tgt, 24.0)
        st.cam.rotation_quaternion = q @ rq
        return t, dt, dict(samples=8, sim=sf, shutter=0.25, anchors={"hit": (0, 0, 0.5)})
    return n, frame

def shot_radius(n=96, one=26):
    """From the air: the fragment strikes race outwards and the 75 m bursting radius is drawn on the ground."""
    def frame(st, i):
        if i < one:
            sf = i + 1; dt = DT
        else:
            sf = one + 2 * (i - one + 1); dt = 2 * DT
        td = (sf - 1) * DT; t = T_HIT + td
        r_front = min(C.BURST_R, 900.0 * max(td - 0.004, 0.0))
        rings = {"burst": r_front, "m67": min(C.M67_R, r_front) if td > 0.35 else 0.0, "fill": C.BURST_R if r_front >= C.BURST_R else 0.0}
        st.set_time(t, dt, dict(rings=rings, frag_gain=2.3))
        u = i / (n - 1)
        pos = np.array([-62.0 + 10 * u, -98.0 + 6 * u, 88.0 + 6 * u])
        st.look(pos, np.array([0.0, 6.0, 0.0]), 24.0)
        an = {"centre": (0, 0, 0.3), "edge": (C.BURST_R * math.cos(D(-52)), C.BURST_R * math.sin(D(-52)), 0.3),
              "m67": (C.M67_R * math.cos(D(-52)), C.M67_R * math.sin(D(-52)), 0.3), "front": (r_front * math.cos(D(-52)), r_front * math.sin(D(-52)), 0.3)}
        return t, dt, dict(samples=10, sim=sf, shutter=0.25, anchors=an, extra=dict(r_front=float(r_front)))
    return n, frame

def shot_after(n=84):
    """Aftermath: the crater and the knocked-down wall, then up and back over the ruins."""
    A = np.array([-2.6, -3.4, 1.05]); B = np.array([-6.5, -7.5, 2.4]); E = np.array([-11.0, -15.0, 8.5])
    def frame(st, i):
        t = T_HIT + 14.0; dt = 1.0 / FPS
        st.set_time(t, dt, dict(motion_blur=False, frags=False))
        u = smoothstep(0.10, 1.0, i / (n - 1))
        pos = (1 - u) ** 2 * A + 2 * u * (1 - u) * B + u * u * E
        tgt = lerp(np.array([0.1, 0.9, 0.2]), np.array([1.5, 3.5, 1.0]), smoothstep(0.2, 1.0, u))
        st.look(pos, tgt, 26.0)
        an = {"crater": (0, 0, 0.0), "wall": (0.0, 2.7, 0.9)}
        return t, dt, dict(samples=12, anchors=an)
    return n, frame

SHOTS = {"load": shot_load, "fire": shot_fire, "fall": shot_fall, "impact": shot_impact, "radius": shot_radius, "after": shot_after}

# ----------------------------------------------------------------------------- title card (studio)
def render_card(out_dir, res, spp, frames, n=72):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    pivot = bpy.data.objects.new("Pivot", None); sc.collection.objects.link(pivot)
    root, cannon, plate, bipod = m120.build_mortar(); root.parent = pivot; root.location = (-0.42, 0, 0)
    R = m120.Round(); R.root.parent = pivot; R.root.location = (-0.12, -0.72, 0.0); R.root.rotation_quaternion = aim_quat((0.0, 0.0, 1.0))
    prof = [(-10.0, 0.0), (3.4, 0.0)] + [(3.4 + 1.8 * math.sin(a), 1.8 * (1 - math.cos(a))) for a in np.linspace(0, math.pi / 2, 12)[1:]] + [(5.2, 11.0)]
    V = np.array([[x, y, z] for (y, z) in prof for x in (-14.0, 14.0)])
    new_obj("Backdrop", new_mesh("bd", V, [grid_faces(len(prof), 2)]), None, simple_mat("BackdropMat", (0.64, 0.61, 0.56), rough=0.85))
    w = bpy.data.worlds.new("Studio"); sc.world = w; w.use_nodes = True
    w.node_tree.nodes["Background"].inputs[0].default_value = (0.75, 0.78, 0.82, 1); w.node_tree.nodes["Background"].inputs[1].default_value = 0.30
    def area(loc, size, power, color=(1, 1, 1)):
        L_ = bpy.data.lights.new("a", 'AREA'); L_.size = size; L_.energy = power; L_.color = color
        o = bpy.data.objects.new("a", L_); sc.collection.objects.link(o); o.location = loc
        o.rotation_euler = (Vector((0, 0, 0.8)) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    area((3.6, -4.2, 4.6), 3.6, 900, (1.0, 0.96, 0.9)); area((-4.6, -2.6, 1.6), 4.0, 300, (0.8, 0.9, 1.0)); area((-1.4, 3.6, 3.6), 3.0, 950)
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); sc.collection.objects.link(cam); sc.camera = cam
    cam.data.lens = 85; cam.data.clip_start = 0.05; cam.data.sensor_width = 36
    cam.location = (0.0, -10.6, 1.10); cam.rotation_euler = (math.radians(88.3), 0, 0)
    cam.data.shift_x = 0.25
    sc.render.engine = 'CYCLES'; c = sc.cycles; c.samples = spp or 20; c.use_denoising = True; c.denoising_quality = 'HIGH'; c.max_bounces = 6
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.use_border = True; sc.render.use_crop_to_border = True
    sc.render.border_min_x = 0.0; sc.render.border_max_x = 0.50; sc.render.border_min_y = 0.0; sc.render.border_max_y = 1.0
    sc.view_settings.view_transform = 'AgX'; sc.view_settings.look = 'AgX - Medium High Contrast'
    sc.render.image_settings.file_format = 'PNG'; sc.render.use_persistent_data = True
    os.makedirs(out_dir, exist_ok=True)
    for i in (frames if frames is not None else range(n)):
        u = i / n
        pivot.rotation_euler = (0, 0, math.radians(112) + math.radians(24) * math.sin(2 * math.pi * u))
        sc.render.filepath = os.path.join(out_dir, "f%04d.png" % i)
        t = time.time(); bpy.ops.render.render(write_still=True)
        print("FRAME card %d %.1fs" % (i, time.time() - t)); sys.stdout.flush()

# ----------------------------------------------------------------------------- driver
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("shot"); ap.add_argument("out")
    ap.add_argument("--sim", default=None); ap.add_argument("--res", default="1280x720")
    ap.add_argument("--spp", type=int, default=0); ap.add_argument("--frames", default="")
    a = ap.parse_args(sys.argv[1:])
    res = tuple(int(x) for x in a.res.split("x"))
    if a.shot == "card":
        render_card(a.out, res, a.spp, gshots.parse_frames(a.frames, 72) if a.frames else None)
        sys.stdout.flush(); os._exit(0)
    n, frame = SHOTS[a.shot]()
    frames = gshots.parse_frames(a.frames, n)
    st = Stage(SET_OF[a.shot], a.sim, SIM_OF.get(a.shot))
    sc = st.sc; sc.render.resolution_x, sc.render.resolution_y = res
    os.makedirs(a.out, exist_ok=True)
    tl = dict(T_HIT=T_HIT, T_REL=T_REL, T_EXIT=C.T_EXIT, V0=C.V0, RANGE=C.RANGE, APEX=C.APEX, TOF=C.TOF, ELEV_DEG=math.degrees(C.ELEV), BURST_R=C.BURST_R, M67_R=C.M67_R, fps=FPS)
    if st.which == "target":
        tl["gap"] = st.ruins.gap
    json.dump(tl, open(os.path.join(os.path.dirname(os.path.abspath(a.out)), "timeline_%s.json" % st.which), "w"))
    meta_path = os.path.join(a.out, "meta.json")
    meta = json.load(open(meta_path)) if os.path.exists(meta_path) else {}
    from bpy_extras.object_utils import world_to_camera_view
    for i in frames:
        fp = os.path.join(a.out, "f%04d.png" % i)
        if os.path.exists(fp):
            continue
        t0 = time.time()
        sc.frame_set(0)
        t, dt, info = frame(st, i)
        sf = info.get("sim", 0)
        if sc.frame_current != sf:
            sc.frame_set(sf)
            t, dt, info = frame(st, i)
        sc.cycles.samples = a.spp or info.get("samples", 12)
        sc.render.motion_blur_shutter = info.get("shutter", 0.5)
        bpy.context.view_layer.update()
        an = {}
        for k, p in info.get("anchors", {}).items():
            v = world_to_camera_view(sc, st.cam, Vector(p)); an[k] = [float(v.x), float(1 - v.y), float(v.z)]
        td = t - T_HIT
        m = dict(t=float(t), td=float(td), sim=int(sf), anchors=an)
        if st.which == "target" and td < 0:
            m["alt"] = float(C.fall_pos(td)[2]); m["v"] = float(np.linalg.norm(C.fall_vel(td)))
        m.update(info.get("extra", {}))
        meta[str(i)] = m
        sc.render.filepath = fp
        bpy.ops.render.render(write_still=True)
        print("FRAME %s %d t=%.4f sim=%d %.1fs" % (a.shot, i, t, sf, time.time() - t0)); sys.stdout.flush()
        json.dump(meta, open(meta_path, "w"))
    sys.stdout.flush(); os._exit(0)

if __name__ == "__main__":
    main()
