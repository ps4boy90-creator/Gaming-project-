"""Shot definitions and frame renderer for the MQ-9 Reaper / AGM-114 Hellfire explosion-comparison segment.

  python3 qshots.py <shot> <out_dir> [--sim <cache_dir>] [--res 1280x720] [--spp N] [--frames a-b | i,j,k]

Shots: card, cruise, launch (air set) and target, fly, impact, radius, after (target set).
Time base: t = seconds after the motor ignites; the missile strikes at T_HIT.  One sim frame is 1/120 s.
"""
import bpy, sys, os, math, json, time, argparse
HERE = os.path.dirname(os.path.abspath(__file__))
for p in ("grenade-explosion", "rpg7-explosion", "mortar-explosion", "howitzer-explosion"):
    sys.path.insert(0, os.path.join(HERE, "..", p))
sys.path.insert(0, HERE)
import numpy as np
from mathutils import Vector, Quaternion
import manta_fix  # noqa: F401
import env, fx
import shots as gshots
import mshots as ms
from hshots import use_device
from smoke_mat import blast_material
from util import *
import qconst as C, qmq9, qhell, qtruck, qenv
from qgeo import aim_quat, Shell, revolve

FPS = C.FPS; DT = C.MASTER_DT; T_HIT = C.T_HIT
D = math.radians
shake = gshots.shake
SIM_OF = {"impact": "impact", "radius": "impact"}
SET_OF = {"cruise": "air", "launch": "air", "target": "target", "fly": "target", "impact": "target", "radius": "target", "after": "target"}
FIRED = 0                                    # index of the missile that is launched (outer rail, left wing)

class Rings(ms.GroundRings):
    SPEC = [("kill", C.KILL_R, 0.22, (1.0, 0.10, 0.05), 6.0), ("wound", C.WOUND_R, 0.22, (1.0, 0.62, 0.10), 6.0)]

# ----------------------------------------------------------------------------- effects
class Puffs:
    """A cloud built from many overlapping lumpy blobs of thin smoke; each blob keeps its own shape from frame to frame."""
    def __init__(self, nmax, seed):
        rng = np.random.default_rng(seed); U, F, _ = ellipsoid((0, 0, 0), (1, 1, 1), 12, 8); U = np.asarray(U); self.F = np.asarray(F); self.m = len(U)
        w1 = rng.normal(0, 1, (nmax, 3)); w2 = rng.normal(0, 1, (nmax, 3)); ph = rng.uniform(0, 6.283, (nmax, 2))
        lump = 1 + 0.28 * np.sin(np.einsum("mk,nk->nm", U, w1) * 2.2 + ph[:, :1]) + 0.18 * np.sin(np.einsum("mk,nk->nm", U, w2) * 4.0 + ph[:, 1:])
        self.UL = U[None, :, :] * lump[:, :, None]; self.rnd = rng.uniform(-1, 1, (nmax, 3)); self.size = rng.uniform(0.8, 1.25, nmax)
    def mesh(self, name, idx, cen, rad):
        rad = np.asarray(rad, float); rad = rad[:, None] * np.ones(3)[None] if rad.ndim == 1 else rad
        V = cen[:, None, :] + self.UL[idx] * rad[:, None, :]
        F = (self.F[None] + (np.arange(len(idx)) * self.m)[:, None, None]).reshape(-1, self.F.shape[1])
        return new_mesh(name, V.reshape(-1, 3), [F])

def _vol_mat(name, color, noise_scale, lo, hi, rise=0.0, emission=None):
    """Volume material: density (or flame emission) = gain x noise mask; returns material, gain socket, time value node, tex-coord separate node."""
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree; N = nt.nodes; L = nt.links; N.clear()
    out = N.new("ShaderNodeOutputMaterial"); pv = N.new("ShaderNodeVolumePrincipled"); pv.inputs["Color"].default_value = (*color, 1); pv.inputs["Anisotropy"].default_value = 0.3
    tc = N.new("ShaderNodeTexCoord"); tv = N.new("ShaderNodeValue"); up = N.new("ShaderNodeCombineXYZ")
    mt = N.new("ShaderNodeMath"); mt.operation = 'MULTIPLY'; mt.inputs[1].default_value = -rise; L.new(tv.outputs[0], mt.inputs[0]); L.new(mt.outputs[0], up.inputs[2])
    add = N.new("ShaderNodeVectorMath"); add.operation = 'ADD'; L.new(tc.outputs["Object"], add.inputs[0]); L.new(up.outputs[0], add.inputs[1])
    n = N.new("ShaderNodeTexNoise"); n.inputs["Scale"].default_value = noise_scale; n.inputs["Detail"].default_value = 5; n.inputs["Roughness"].default_value = 0.6; L.new(add.outputs[0], n.inputs["Vector"])
    mr = N.new("ShaderNodeMapRange"); mr.inputs["From Min"].default_value = lo; mr.inputs["From Max"].default_value = hi; L.new(n.outputs["Fac"], mr.inputs["Value"])
    fade = N.new("ShaderNodeMapRange"); sep = N.new("ShaderNodeSeparateXYZ"); L.new(tc.outputs["Object"], sep.inputs[0])
    m1 = N.new("ShaderNodeMath"); m1.operation = 'MULTIPLY'; L.new(mr.outputs[0], m1.inputs[0]); L.new(fade.outputs[0], m1.inputs[1])
    if emission:
        pv.inputs["Density"].default_value = 0.15; pv.inputs["Emission Color"].default_value = (*emission, 1); L.new(m1.outputs[0], pv.inputs["Emission Strength"])
    else:
        L.new(m1.outputs[0], pv.inputs["Density"])
    L.new(pv.outputs[0], out.inputs["Volume"])
    return m, fade, tv, sep

class Trail:
    """Motor exhaust.  The smoke stays where it was released while the aircraft flies on, so in the aircraft's frame it
    streams back past the wing.  The Hellfire's motor is a minimum-smoke type: a thin pale wisp, not a thick plume."""
    def __init__(self, col):
        sv = np.arange(0.0, C.s_of(min(C.T_BURN, 1.6)), 0.35); self.taus = np.interp(sv, C.FLY[:, 1], C.FLY[:, 0]); self.P = Puffs(len(self.taus), 41)   # one puff every 0.35 m of flight
        self.base = np.array([C.path_at(s_)[0] - C._P0 for s_ in sv])
        m, self.fade, tv, sep = _vol_mat("TrailSmoke", (0.90, 0.89, 0.87), 1.6, 0.34, 0.62)
        m.node_tree.links.new(sep.outputs["X"], self.fade.inputs["Value"])
        self.ob = new_obj("Trail", bpy.data.meshes.new("trail"), col, m); self.ob.visible_shadow = False; self.ob.hide_render = True
    def update(self, t, rail):
        idx = np.nonzero(self.taus < t - 0.004)[0]; self.ob.hide_render = len(idx) < 2
        if len(idx) < 2:
            return
        ages = t - self.taus[idx]; R = self.P.rnd[idx]
        cen = rail[None] + self.base[idx] - np.array([C.U * t, 0, 0])[None]
        cen[:, 1] += 0.34 * ages ** 0.8 * R[:, 0]; cen[:, 2] += 0.08 * ages + 0.30 * ages ** 0.8 * R[:, 1]
        rad = (0.15 + 0.50 * ages ** 0.60) * self.P.size[idx]
        me = self.P.mesh("trail", idx, cen, rad); me.materials.append(self.ob.data.materials[0])
        old = self.ob.data; self.ob.data = me; bpy.data.meshes.remove(old)
        x_old = float(cen[:, 0].min()); x_new = float(cen[:, 0].max())
        f = self.fade; f.inputs["From Min"].default_value = x_old; f.inputs["From Max"].default_value = x_new; f.inputs["To Min"].default_value = 0.10; f.inputs["To Max"].default_value = 1.3

class Plume:
    """The wreck burning some time after the strike: black smoke rising and leaning down-wind, flames in the cab and bed."""
    AX = 0.3; K = 0.022; R0 = 0.70; RK = 0.19; HT = 27.0; N = 90
    def __init__(self, col):
        self.P = Puffs(self.N, 57); self.phase = (np.arange(self.N) + np.random.default_rng(2).uniform(0, 1, self.N)) / self.N
        m, fade, self.time, sep = _vol_mat("PlumeSmoke", (0.030, 0.028, 0.027), 0.55, 0.30, 0.58, rise=2.2)
        m.node_tree.links.new(sep.outputs["Z"], fade.inputs["Value"]); fade.inputs["From Min"].default_value = 1.0; fade.inputs["From Max"].default_value = 26.0; fade.inputs["To Min"].default_value = 2.6; fade.inputs["To Max"].default_value = 0.10
        self.ob = new_obj("Plume", bpy.data.meshes.new("plume"), col, m); self.ob.hide_render = True
        self.FP = Puffs(14, 63); rng = np.random.default_rng(9); self.fpos = np.stack([rng.uniform(-0.55, 0.75, 14), rng.uniform(-2.0, 1.0, 14), rng.uniform(0.75, 1.25, 14)], 1); self.fph = rng.uniform(0, 6.28, 14)
        fm, ffade, self.ftime, fsep = _vol_mat("WreckFlames", (0.05, 0.03, 0.02), 1.7, 0.36, 0.62, rise=5.0, emission=(1.0, 0.36, 0.05))
        fm.node_tree.links.new(fsep.outputs["Z"], ffade.inputs["Value"]); ffade.inputs["From Min"].default_value = 3.3; ffade.inputs["From Max"].default_value = 0.9; ffade.inputs["To Max"].default_value = 38.0
        self.fl = new_obj("Flames", bpy.data.meshes.new("flames"), col, fm); self.fl.hide_render = True; self.fl.visible_shadow = False
        self.glow = ms.point_light(col, "FireGlow", (1.0, 0.45, 0.15), 0.8); self.glow.location = (0.2, -0.3, 1.9)
    def update(self, on, t):
        self.ob.hide_render = not on; self.glow.hide_render = not on; self.fl.hide_render = not on
        if not on:
            return
        s = (self.phase + t * 0.085) % 1.0; z = self.HT * s; idx = np.arange(self.N); R = self.P.rnd
        rad = (self.R0 + self.RK * z ** 1.05) * self.P.size * np.clip(s / 0.04, 0.35, 1.0) * np.clip((1.0 - s) / 0.08, 0.2, 1.0)
        cen = np.stack([self.AX + self.K * z * z + 0.38 * rad * R[:, 0], 0.02 * z + 0.38 * rad * R[:, 1], 1.0 + z + 0.25 * rad * R[:, 2]], 1)
        me = self.P.mesh("plume", idx, cen, rad); me.materials.append(self.ob.data.materials[0]); old = self.ob.data; self.ob.data = me; bpy.data.meshes.remove(old)
        k = 1.0 + 0.30 * np.sin(t * 9.0 + self.fph) + 0.18 * np.sin(t * 23.0 + 2.1 * self.fph)
        frad = np.stack([0.42 * k, 0.42 * k, 0.95 * k], 1) * self.FP.size[:, None]; fcen = self.fpos + np.array([0, 0, 1.0])[None] * (0.55 * k)[:, None]
        me = self.FP.mesh("flames", np.arange(14), fcen, frad); me.materials.append(self.fl.data.materials[0]); old = self.fl.data; self.fl.data = me; bpy.data.meshes.remove(old)
        self.time.outputs[0].default_value = t; self.ftime.outputs[0].default_value = t
        self.glow.data.energy = 520.0 * (1 + 0.18 * math.sin(t * 13.0) + 0.12 * math.sin(t * 29.0))

# ----------------------------------------------------------------------------- scene
class Stage(gshots.Stage):
    def __init__(self, which, sim_dir=None, kind=None):
        self.which = which; self.dom = None; self.T0 = T_HIT
        if sim_dir and os.path.exists(os.path.join(sim_dir, "sim.blend")):
            bpy.ops.wm.open_mainfile(filepath=os.path.join(sim_dir, "sim.blend"))
            for o in list(bpy.data.objects):
                if o.name.startswith("E_"):
                    bpy.data.objects.remove(o, do_unlink=True)
            self.dom = bpy.data.objects["BlastDomain"]; self.dom.data.materials.clear()
            self.fire0 = 34.0; bm_ = blast_material(density=7.5, fire=self.fire0, ambient=0.06)
            self.dom.data.materials.append(bm_); self.fire_node = bm_.node_tree.nodes[bm_["fire_node"]]
            for nd in bm_.node_tree.nodes:
                if nd.type == 'VECT_MATH' and nd.operation == 'POWER':
                    nd.inputs[1].default_value = (0.70, 0.70, 0.70)
                if nd.type == 'VALTORGB':
                    for el, c in zip(sorted(nd.color_ramp.elements, key=lambda e: e.position),
                                     [(0, 0, 0), (0.55, 0.05, 0.0), (0.95, 0.22, 0.02), (1.0, 0.42, 0.07), (1.0, 0.62, 0.22)]):
                        el.color = (*c, 1)
            self.dom.hide_render = True
        else:
            bpy.ops.wm.read_factory_settings(use_empty=True)
        sc = self.sc = bpy.context.scene; sc.render.fps = FPS
        if which == "air":
            self.env_col, self.floor = qenv.build_air(sc)
            col = self.col = bpy.data.collections.new("ACTION"); sc.collection.children.link(col)
            self.ac = qmq9.build(col); self.shot = self.ac["missiles"][FIRED]; self.rail = self.ac["rails"][FIRED].copy(); self.shot.add_motor(col)
            self.trail = Trail(col); self.trail.ob.parent = self.ac["root"]
        else:
            self.env_col, self.ground = qenv.build_target(sc)
            self.blast_node = self.ground.data.materials[0].node_tree.nodes["Blast"]
            col = self.col = bpy.data.collections.new("ACTION"); sc.collection.children.link(col)
            self.truck = qtruck.Truck(col); self.shot = qhell.Hellfire(col, "Hellfire")
            self.frags = ms.FragField(col, n=150, rmax=C.WOUND_R); self.ejecta = ms.Ejecta(col, scale=0.85); self.rings = Rings(col)
            self.ejecta.c_ob.location = (0.2, 0, 0.5); self.ejecta.s_ob.location = (0, 0, 1.0)
            self.l_hit = ms.point_light(col, "HitFlash", (1.0, 0.60, 0.28), 0.9); self.l_hit.location = (C.HIT[0] - 0.3, 0.0, C.HIT[2] + 0.5)
            self.plume = Plume(col)
        cd = bpy.data.cameras.new("Cam"); self.cam = bpy.data.objects.new("Cam", cd); sc.collection.objects.link(self.cam); sc.camera = self.cam
        cd.clip_start = 0.05; cd.clip_end = 2.0e6 if which == "air" else 8000; cd.sensor_width = 36; cd.sensor_fit = 'HORIZONTAL'
        self.cam.rotation_mode = 'QUATERNION'
        self.setup_render()
        self.haze_mr = [nd for nd in sc.compositing_node_group.nodes if nd.bl_idname == "ShaderNodeMapRange"][0]; self.haze0 = 0.62
        if which == "air":                                          # the desert is kilometres away: most of its haze is in its own material
            self.haze_mr.inputs["From Min"].default_value = 3000.0; self.haze_mr.inputs["From Max"].default_value = 90000.0; self.haze0 = 0.22
            for nd in sc.compositing_node_group.nodes:
                if nd.bl_idname == "ShaderNodeMath" and nd.operation == 'LESS_THAN':
                    nd.inputs[1].default_value = 5.0e6

    def set_time(self, t, dt_out, opt):
        sc = self.sc; mb = opt.get("motion_blur", True); sc.render.use_motion_blur = mb
        self.haze_mr.inputs["To Max"].default_value = self.haze0 * opt.get("haze", 1.0)
        if self.which == "air":
            A = self.ac; root = A["root"]
            root.location = (0, 0, 0.06 * math.sin(0.9 * t + 0.4)); root.rotation_quaternion = Quaternion((1, 0, 0), D(0.7) * math.sin(0.7 * t)) @ Quaternion((0, 1, 0), D(-2.0))
            qmq9.spin_prop(A["prop"], sc, t, dt_out if mb else 0.0, shutter=opt.get("shutter", 0.5))
            self.floor.location = (-C.U * t, 0, 0)
            tgt = np.array([C.RANGE - C.U * t, 0.0, -C.ALT]); tgt = tgt - qmq9.TURRET; A["turret"].rotation_quaternion = aim_quat(tgt / np.linalg.norm(tgt))
            def mstate(tt):
                r, d = C.missile_rel(tt); return self.rail + r, aim_quat(d)
            self.key3(self.shot.root, mstate, t, dt_out, mb and t > 0)
            burn = smoothstep(0.0, 0.025, t) * (1 - smoothstep(C.T_BURN - 0.1, C.T_BURN, t)) if t > 0 else 0.0
            self.shot.set_burn(burn * (1 + 0.10 * math.sin(t * 400.0)), 1.0 + 0.25 * math.sin(t * 270.0))
            self.trail.update(t if opt.get("trail", True) else -1.0, self.rail)
        else:
            td = t - T_HIT; hit = td >= 0
            self.shot.set_visible((not hit) and t > 0 and opt.get("missile", True))
            if not hit:
                def fstate(tt):
                    p, d, v = C.missile_state(min(max(tt, 0.0), T_HIT)); return p - d * C.M_LEN, aim_quat(d)
                self.key3(self.shot.root, fstate, t, dt_out, mb)
            self.truck.update(t)
            self.blast_node.outputs[0].default_value = 0.8 if hit else 0.0
            self.ground.data.shape_keys.key_blocks["Crater155"].value = 0.8 if hit else 0.0
            self.frags.update(td if opt.get("frags", True) else -1.0, opt.get("frag_gain", 1.0)); self.ejecta.update(td if td < 6 else -1.0, 0.5 * dt_out)
            self.rings.update(opt.get("rings", {}))
            self.l_hit.data.energy = 150000.0 * opt.get("flash", 1.0) * math.exp(-td / 0.020) if 0 <= td < 0.25 else 0.0
            self.l_hit.hide_render = self.l_hit.data.energy < 5.0
            self.plume.update(bool(opt.get("plume", False)), t)
        if self.dom is not None:
            self.dom.hide_render = t < self.T0
            self.fire_node.inputs[1].default_value = self.fire0 * (0.22 + 0.78 * math.exp(-max(t - self.T0, 0.0) / 0.06))

# ----------------------------------------------------------------------------- shots: air set
def shot_cruise(n=96):
    """The Reaper at 20,000 ft over the desert: the camera drifts from ahead of the left wing round to the beam."""
    def frame(st, i):
        t = -9.0 + i / FPS; dt = 1.0 / FPS; u = i / (n - 1)
        st.set_time(t, dt, dict(trail=False))
        a = D(lerp(38.0, 78.0, smoothstep(0.0, 1.0, u))); r = lerp(19.0, 15.5, u)
        pos = np.array([r * math.cos(a), r * math.sin(a), lerp(4.2, 1.6, u)])
        st.look(pos, np.array([-0.6, 0.0, -0.2]), 32.0)
        return t, dt, dict(samples=40, shutter=0.5, anchors={"nose": (4.7, 0, 0), "turret": tuple(qmq9.TURRET), "missile": tuple(st.rail + np.array([0.8, 0, 0]))})
    return n, frame

def shot_launch(n=116, lead=26, one=54):
    """Under the left wing: the motor lights, the missile runs off the rail and pulls away; then slow motion."""
    def frame(st, i):
        if i < lead:
            sf = 0; t = -(lead - i) / FPS - 0.002; dt = 1.0 / FPS
        elif i < lead + one:
            sf = i - lead + 1; t = (sf - 1) * DT; dt = DT
        else:
            sf = one + 2 * (i - lead - one + 1); t = (sf - 1) * DT; dt = 2 * DT
        st.set_time(t, dt, dict(shutter=0.35))
        u = i / (n - 1)
        r, d = C.missile_rel(max(t, 0.0)); mpos = st.rail + r + d * 0.8
        pos = np.array([5.4 + 0.5 * u, 6.6, -1.75 - 0.25 * u])
        k = smoothstep(0.0, 0.5, max(t, 0.0)) if t > 0 else 0.0
        tgt = lerp(st.rail + np.array([0.9, 0.0, 0.05]), mpos, 0.90 * smoothstep(0.02, 0.22, max(t, 0.0)))
        off, rq = shake(t - 0.005, 0.9)
        q = st.look(pos + off, tgt, lerp(30.0, 24.0, k))
        st.cam.rotation_quaternion = q @ rq
        return t, dt, dict(samples=14, sim=0, shutter=0.35, anchors={"missile": tuple(mpos)}, extra=dict(rel=float(np.linalg.norm(r)), v=float(C.v_of(max(t, 0.0)))))
    return n, frame

# ----------------------------------------------------------------------------- shots: target set
def shot_target(n=84):
    """What the sensor ball sees from 7 km: the pickup comes up the track and stops.  Shown as the infra-red picture in post."""
    t0 = C.T_STOP - 3.0
    def frame(st, i):
        t = t0 + i / FPS; dt = 1.0 / FPS
        st.set_time(t, dt, dict(missile=False, motion_blur=False, haze=0.2))
        ac = C.aircraft_pos(t); dv = ac / np.linalg.norm(ac)
        y = C.truck_y(t); y_s = C.truck_y(t - 0.25) * 0.85 + y * 0.15                 # the operator's cursor lags the vehicle a little
        tgt = np.array([0.0, y_s + 0.4, 1.0]) + 0.20 * np.array([math.sin(t * 2.1), math.sin(t * 1.7 + 1.0), 0.0])
        pos = tgt + dv * 620.0
        st.look(pos, tgt, 560.0, roll=D(1.2) * math.sin(t * 0.6))
        return t, dt, dict(samples=16, anchors={"truck": (0.0, y, 1.0)}, extra=dict(slant=float(np.linalg.norm(ac)), tti=float(T_HIT - t), speed=float((C.truck_y(t + 0.05) - C.truck_y(t - 0.05)) / 0.1)))
    return n, frame

def shot_fly(n=72):
    """Real time, the last three seconds: the camera rides down behind the missile onto the pickup."""
    td0, td1 = -3.02, -0.035
    def cam_at(t):
        p, d, v = C.missile_state(t); up = np.array([0, 0, 1.0]) - d * d[2]; up /= np.linalg.norm(up)
        u = (t - T_HIT - td0) / (td1 - td0)
        pos = p - d * (C.M_LEN + lerp(1.7, 1.4, u)) + up * lerp(0.42, 0.36, u) + np.array([0, -0.26, 0])
        aim = p + d * lerp(0.8, 0.0, u) + up * 0.10
        return pos, (Vector(aim) - Vector(pos)).to_track_quat('-Z', 'Y')
    def frame(st, i):
        td = lerp(td0, td1, i / (n - 1)); t = T_HIT + td; dt = (td1 - td0) / (n - 1)
        st.set_time(t, dt, dict(haze=0.55))
        pos, q = cam_at(t)
        st.look(pos, None, 24.0, quat=q)
        st.key3(st.cam, cam_at, t, dt, True)
        return t, dt, dict(samples=12, shutter=0.3, anchors={"target": tuple(C.HIT)})
    return n, frame

def _slow(i, pre, one, k=2):
    if i < pre:
        return 0, T_HIT - (pre - i) * DT, DT
    if i < pre + one:
        sf = i - pre + 1; return sf, T_HIT + (sf - 1) * DT, DT
    sf = one + k * (i - pre - one + 1); return sf, T_HIT + (sf - 1) * DT, k * DT

def shot_impact(n=124):
    """Beside the track: the missile comes down onto the pickup; the burst, the fuel fire, the parts thrown clear."""
    def frame(st, i):
        sf, t, dt = _slow(i, 10, 54, 2)
        st.set_time(t, dt, dict(frags=False))
        u = i / (n - 1)
        pos = np.array([6.2 + 0.8 * u, -14.5 - 2.5 * u, 1.65 + 0.6 * u])
        tgt = np.array([0.6, 0.0, 1.7 + 2.4 * smoothstep(0.12, 1.0, u)])
        off, rq = shake(t - T_HIT - 0.045, 1.8)
        q = st.look(pos + off, tgt, 26.0)
        st.cam.rotation_quaternion = q @ rq
        return t, dt, dict(samples=12, sim=sf, shutter=0.25, anchors={"hit": tuple(C.HIT)})
    return n, frame

def shot_radius(n=96, one=30):
    """From the air: the burst and the fragments reaching out; the published kill and wounding radii drawn on the sand."""
    def frame(st, i):
        if i < one:
            sf = i + 1; dt = DT
        else:
            sf = one + 2 * (i - one + 1); dt = 2 * DT
        td = (sf - 1) * DT; t = T_HIT + td
        r_front = min(C.WOUND_R, 420.0 * max(td - 0.003, 0.0))
        rings = {"kill": min(C.KILL_R, r_front), "wound": r_front if r_front > C.KILL_R else 0.0}
        st.set_time(t, dt, dict(frag_gain=1.5, rings={}))
        u = i / (n - 1)
        pos = np.array([-17.0 + 3 * u, -37.0 + 2 * u, 33.0 + 3 * u])
        st.look(pos, np.array([0.0, 2.5, 0.0]), 24.0)
        a_ = D(-35)
        an = {"centre": (0, 0, 0.3), "kill": (C.KILL_R * math.cos(a_), C.KILL_R * math.sin(a_), 0.2), "wound": (C.WOUND_R * math.cos(D(-150)), C.WOUND_R * math.sin(D(-150)), 0.2)}
        return t, dt, dict(samples=10, sim=sf, shutter=0.25, anchors=an, extra=dict(r_front=float(r_front)), circles=rings)
    return n, frame

def shot_after(n=84):
    """Half a minute later: the wreck burning under its smoke; the camera lifts up and back."""
    A = np.array([6.0, -9.0, 1.5]); B = np.array([9.0, -13.0, 3.5]); E = np.array([13.0, -22.0, 9.5])
    def frame(st, i):
        t = T_HIT + 30.0 + i / FPS; dt = 1.0 / FPS
        st.set_time(t, dt, dict(motion_blur=False, frags=False, plume=True, haze=0.12))
        u = smoothstep(0.05, 1.0, i / (n - 1))
        pos = (1 - u) ** 2 * A + 2 * u * (1 - u) * B + u * u * E
        tgt = lerp(np.array([0.3, 0.0, 1.2]), np.array([1.5, 0.5, 4.5]), smoothstep(0.2, 1.0, u))
        st.look(pos, tgt, 26.0)
        return t, dt, dict(samples=24, anchors={"wreck": (0.3, 0.0, 1.0), "door": tuple(st.truck.pieces["doorR"].at(30.0)[0])})
    return n, frame

SHOTS = {"cruise": shot_cruise, "launch": shot_launch, "target": shot_target, "fly": shot_fly, "impact": shot_impact, "radius": shot_radius, "after": shot_after}

# ----------------------------------------------------------------------------- title card (studio)
def render_card(out_dir, res, spp, frames, n=72):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    pivot = bpy.data.objects.new("Pivot", None); sc.collection.objects.link(pivot)
    A = qmq9.build(); A["root"].parent = pivot; A["root"].location = (0.6, 0, 4.4); A["root"].rotation_quaternion = Quaternion((1, 0, 0), D(-9)) @ Quaternion((0, 1, 0), D(-4))
    A["turret"].rotation_quaternion = aim_quat((0.75, -0.25, -0.6))
    prof = [(-160.0, 0.0), (16.0, 0.0)] + [(16.0 + 5.0 * math.sin(a), 5.0 * (1 - math.cos(a))) for a in np.linspace(0, math.pi / 2, 12)[1:]] + [(21.0, 80.0)]
    V = np.array([[x, y, z] for (y, z) in prof for x in (-120.0, 120.0)])
    new_obj("Backdrop", new_mesh("bd", V, [grid_faces(len(prof), 2)]), None, simple_mat("BackdropMat", (0.64, 0.61, 0.56), rough=0.85))
    w = bpy.data.worlds.new("Studio"); sc.world = w; w.use_nodes = True
    w.node_tree.nodes["Background"].inputs[0].default_value = (0.75, 0.78, 0.82, 1); w.node_tree.nodes["Background"].inputs[1].default_value = 0.30
    def area(loc, size, power, color=(1, 1, 1)):
        L_ = bpy.data.lights.new("a", 'AREA'); L_.size = size; L_.energy = power; L_.color = color
        o = bpy.data.objects.new("a", L_); sc.collection.objects.link(o); o.location = loc
        o.rotation_euler = (Vector((0, 0, 3.5)) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    area((14.0, -18.0, 20.0), 16.0, 6500, (1.0, 0.96, 0.9)); area((-20.0, -12.0, 7.0), 18.0, 2100, (0.8, 0.9, 1.0)); area((-6.0, 16.0, 16.0), 14.0, 6500)
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); sc.collection.objects.link(cam); sc.camera = cam
    cam.data.lens = 85; cam.data.clip_start = 0.05; cam.data.clip_end = 600; cam.data.sensor_width = 36
    cam.location = (0.0, -93.0, 5.2); cam.rotation_euler = (math.radians(89.3), 0, 0)
    cam.data.shift_x = 0.25
    sc.render.engine = 'CYCLES'; c = sc.cycles; c.samples = spp or 24; c.use_denoising = True; c.denoising_quality = 'HIGH'; c.max_bounces = 6
    use_device(sc)
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.use_border = True; sc.render.use_crop_to_border = True
    sc.render.border_min_x = 0.0; sc.render.border_max_x = 0.50; sc.render.border_min_y = 0.0; sc.render.border_max_y = 1.0
    sc.view_settings.view_transform = 'AgX'; sc.view_settings.look = 'AgX - Medium High Contrast'
    sc.render.image_settings.file_format = 'PNG'; sc.render.use_persistent_data = True
    os.makedirs(out_dir, exist_ok=True)
    for i in (frames if frames is not None else range(n)):
        u = i / n
        if os.path.exists(os.path.join(out_dir, "f%04d.png" % i)):
            continue
        pivot.rotation_euler = (0, 0, math.radians(-128) + math.radians(18) * math.sin(2 * math.pi * u))
        qmq9.spin_prop(A["prop"], sc, i / 24.0 * 0.02, 0.0)
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
    st = Stage(SET_OF[a.shot], a.sim if a.shot in SIM_OF else None, SIM_OF.get(a.shot))
    sc = st.sc; sc.render.resolution_x, sc.render.resolution_y = res
    use_device(sc)
    os.makedirs(a.out, exist_ok=True)
    tl = dict(T_HIT=T_HIT, T_BURN=C.T_BURN, V_MAX=C.V_MAX, V_HIT=C.V_HIT, ALT=C.ALT, RANGE=C.RANGE, SLANT=C.SLANT, U=C.U, DIVE_DEG=math.degrees(C.DIVE),
              KILL_R=C.KILL_R, WOUND_R=C.WOUND_R, T_STOP=C.T_STOP, fps=FPS)
    json.dump(tl, open(os.path.join(os.path.dirname(os.path.abspath(a.out)), "timeline.json"), "w"))
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
        if st.which == "target" and 0 < t < T_HIT:
            p, d, v = C.missile_state(t); m["alt"] = float(p[2]); m["v"] = float(v); m["dist"] = float(np.linalg.norm(p - C.HIT))
        m.update(info.get("extra", {}))
        for name, r in info.get("circles", {}).items():
            pts = []
            for a_ in np.linspace(0, 2 * math.pi, 121):
                v = world_to_camera_view(sc, st.cam, Vector((r * math.cos(a_), r * math.sin(a_), 0.1))); pts.append([float(v.x), float(1 - v.y)])
            m["circle_" + name] = pts if r > 0.5 else []
        meta[str(i)] = m
        sc.render.filepath = fp
        bpy.ops.render.render(write_still=True)
        print("FRAME %s %d t=%.4f sim=%d %.1fs" % (a.shot, i, t, sf, time.time() - t0)); sys.stdout.flush()
        json.dump(meta, open(meta_path, "w"))
    sys.stdout.flush(); os._exit(0)

if __name__ == "__main__":
    main()
