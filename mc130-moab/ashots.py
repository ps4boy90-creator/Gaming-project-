"""Shot definitions and frame renderer for the MC-130 / GBU-43/B MOAB segment (adapted from the BLU-82 segment's dshots).

  python3 ashots.py <shot> <out_dir> [--sim <sim_root>] [--res 1280x720] [--spp N] [--frames a-b | i,j,k]

Shots and their sets:
  card, intro                 studio   the bomb on its cradle; the bomb whole and cut open
  approach, release           air      the MC-130 with its ramp open; the load pulled out, the bomb leaving its cradle, the fins opening
  fall, strike, reach, after  out      the valley
Clocks: air set, t = seconds after the load is released; out set, tb = seconds after the burst.
Sim frames: 1/40 s each, frame 1 = the burst.
"""
import bpy, sys, os, math, json, time, argparse
HERE = os.path.dirname(os.path.abspath(__file__))
for p in ("grenade-explosion", "rpg7-explosion", "mortar-explosion", "howitzer-explosion", "reaper-hellfire", "c130-blu82"):
    sys.path.insert(0, os.path.join(HERE, "..", p))
sys.path.insert(0, HERE)
import numpy as np
from mathutils import Vector, Quaternion
import manta_fix  # noqa: F401
import env
import shots as gsh
from hshots import use_device
from qshots import Plume
from qgeo import aim_quat, Shell, box as gbox
from smoke_mat import blast_material
from util import *
import aconst as C, abomb
if C.SITE == "city":
    import acity as asite                                             # the hypothetical drop on an invented ruined city district
else:
    import asite
import dc130, dbomb                                                   # the Hercules and the parachute of the BLU-82 segment

FPS = C.FPS; ODT = 1.0 / 40.0
D = math.radians
shake = gsh.shake
SET_OF = {"approach": "air", "release": "air", "city": "out", "fall": "out", "strike": "out", "reach": "out", "after": "out"}
CITY = C.SITE == "city"
SIM_OF = {"strike": "out", "reach": "out"}
N_OF = {"card": 72, "approach": 96, "intro": 96, "release": 180, "city": 132, "fall": 84, "strike": 220, "reach": 300 if CITY else 204, "after": 108}      # the city version adds a flight over the whole city and a pull-out at the end of "reach"
LINE_L = 19.0                                                        # the extraction line, from the platform to where the parachute's lines meet
PITCH = lambda th: Quaternion((0, 1, 0), th)
GREY = ((0.105, 0.110, 0.118, 1), (0.118, 0.123, 0.130, 1), (0.095, 0.100, 0.108, 1))     # the dark grey of the special-operations Hercules

def bomb_site(t):
    p, v, th = C.bomb_state(t); return p, PITCH(th)

def cradle_site(t):
    tau = t - C.T_EXIT
    if tau < C.T_SEP:
        return bomb_site(t)
    p, v = C.plat_state(t); th = C.bomb_state(C.T_EXIT + C.T_SEP)[2] - 0.50 * (1 - math.exp(-(tau - C.T_SEP) / 1.2))       # relieved of the bomb, it is pulled away tail-first by the parachute
    return p + np.array([0, 0, C.AXIS_H]), PITCH(th)

def extr_site(t):
    """Where the parachute's lines meet, the way it trails, and the point on the platform it pulls on."""
    p, q = cradle_site(t); a = p + np.array(q @ Vector((abomb.PLAT_XC - C.PLAT_L / 2 - 0.05, 0.0, -C.AXIS_H + C.PLAT_H))); tau = t - C.T_EXIT
    d0 = np.array([-1.0, 0.0, -0.04]); v = C.plat_state(t)[1] if tau > 0 else np.array([C.V_AC, 0.0, 0.0]); d1 = -v / np.linalg.norm(v); k = smoothstep(0.0, 0.8, tau); d = d0 * (1 - k) + d1 * k; d /= np.linalg.norm(d)
    return a + d * LINE_L, d, a

RACK = np.array([C.X0 - 23.3, 0.0, 2.45])                            # the parachute's pack hangs here, over the ramp, until it is let go
CLEAR = np.array([C.X0 - 26.2, 0.0, 0.3])

def extr_deploy(t):
    """(stage, where the lines meet in the aircraft's frame or None, how far the canopy has filled): 0 the pack on its rack, 1 the pack swinging out, 2 the line running out, 3 trailing."""
    t0, t1, t2, t3 = C.T_EXTR
    if t < t0:
        return 0, RACK, 0.0
    if t < t1:
        u = (t - t0) / (t1 - t0); p = RACK + (CLEAR - RACK) * u; p[2] -= 0.9 * math.sin(math.pi * u) * (1 - u); return 1, p, 0.0
    if t < t2:
        return 2, None, 0.0
    return 3, None, smoothstep(t2, t3, t) * (1.0 + 0.10 * math.exp(-(t - t3) / 0.25) * math.sin((t - t3) * 14.0) * (t > t3))

def extr_rel(t):
    """The parachute in the aircraft's frame: where its lines meet, the way it trails, the point on the platform."""
    c, d, a = extr_site(t); o = C.ac_pos(t); c = c - o; a = a - o; st, p, op = extr_deploy(t)
    if st <= 1:
        c = p; d = (c - a) / np.linalg.norm(c - a)
    elif st == 2:
        t1, t2 = C.T_EXTR[1], C.T_EXTR[2]; u = (t - t1) / (t2 - t1); u = 1 - (1 - u) ** 2; c = CLEAR + (c - CLEAR) * u; d = d * u + (c - a) / np.linalg.norm(c - a) * (1 - u); d /= np.linalg.norm(d)
    return c, d, a, st, op

def steer(t):
    """A small working of the fins, for the eye: the guidance holding the bomb on its line."""
    return math.radians(5.0) * math.sin(2.3 * t) * math.sin(0.7 * t + 1.0)

# ----------------------------------------------------------------------------- scene
class Stage(gsh.Stage):
    def __init__(self, kind, sim_dir=None):
        self.kind = kind; self.dom = None
        if sim_dir and os.path.exists(os.path.join(sim_dir, "sim.blend")):
            bpy.ops.wm.open_mainfile(filepath=os.path.join(sim_dir, "sim.blend"))
            for o in list(bpy.data.objects):
                if o.name.startswith("E_"):
                    bpy.data.objects.remove(o, do_unlink=True)
            self.dom = bpy.data.objects["BlastDomain"]; self.dom.data.materials.clear()
            self.fire0 = 30.0; bm_ = blast_material(density=2.6, fire=self.fire0, ambient=0.06); self.dom.data.materials.append(bm_); self.fire_node = bm_.node_tree.nodes[bm_["fire_node"]]
            for nd in bm_.node_tree.nodes:                             # keep the dust the colour of the ground it came from
                if nd.type == 'VECT_MATH' and nd.operation == 'POWER':
                    nd.inputs[1].default_value = (0.88, 0.88, 0.88)
            self.dom.hide_render = True
        else:
            bpy.ops.wm.read_factory_settings(use_empty=True)
        sc = self.sc = bpy.context.scene; sc.render.fps = FPS
        col = self.col = bpy.data.collections.new("ACTION"); sc.collection.children.link(col)
        ec = self.env_col = bpy.data.collections.new("ENV"); sc.collection.children.link(ec)
        self.bomb = abomb.Bomb(col, "Bomb")
        if kind == "air":
            self.floor = asite.AirFloor(sc, ec); self.ac = dc130.C130(col)
            hp = bpy.data.materials["HercPaint"]                        # grey all over instead of the Vietnam camouflage
            for nd in hp.node_tree.nodes:
                if nd.type == 'VALTORGB':
                    for e, c in zip(nd.color_ramp.elements, GREY):
                        e.color = c
                if nd.type == 'MIX_RGB' and tuple(round(v, 2) for v in nd.inputs[2].default_value[:3]) == (0.42, 0.44, 0.45):
                    nd.inputs[2].default_value = GREY[0]
            self.cradle = abomb.Cradle(col); self.extr = dbomb.Chute(col, "Extraction", d=C.EXTR_D, lines=0.9, c1=(0.33, 0.37, 0.24, 1), c2=(0.26, 0.30, 0.19, 1))
            S = Shell(); S.add(*gbox((0.5, 0, 0), (1.0, 0.04, 0.04)), color=(0.62, 0.60, 0.50, 1)); self.line = new_obj("ExtractionLine", S.mesh("extr_line"), col, dbomb.cloth_mat()); self.line.rotation_mode = 'QUATERNION'
            S = Shell(); S.add(*gbox((0, 0, 0), (0.70, 0.55, 0.42)), color=(0.30, 0.33, 0.22, 1)); self.pack = new_obj("ExtractionPack", S.mesh("extr_pack"), col, dbomb.cloth_mat())
            ld = bpy.data.lights.new("Bounce", 'AREA'); ld.size = 80.0; ld.energy = 1.2e4; ld.color = (0.95, 0.86, 0.72); lo = bpy.data.objects.new("Bounce", ld); col.objects.link(lo)   # light thrown back up by the dry country
            lo.location = (0, 0, -50.0); lo.rotation_euler = (math.pi, 0, 0); ld.use_shadow = False
        else:
            self.site = asite.Site(sc, ec); self.plumes = []
            for (x, y, s) in ((4.0, -6.0, 0.9), (-52.0, -38.0, 0.55), (38.0, -70.0, 0.5), (-20.0, 66.0, 0.45)):
                pl = Plume(col); pl.ob.location = (x, y, float(asite.ground(x, y))); pl.ob.scale = (s, s, s); pl.fl.hide_render = True; pl.glow.hide_render = True; self.plumes.append(pl)
                for mt in pl.mats:                                  # thin grey smoke
                    f = mt.node_tree.nodes["Fade"]; f.inputs["To Min"].default_value = 0.16; f.inputs["To Max"].default_value = 0.02
                    for nd in mt.node_tree.nodes:
                        if nd.type == 'PRINCIPLED_VOLUME':
                            nd.inputs["Color"].default_value = (0.62, 0.60, 0.57, 1)
        cd = bpy.data.cameras.new("Cam"); self.cam = bpy.data.objects.new("Cam", cd); sc.collection.objects.link(self.cam); sc.camera = self.cam
        cd.clip_start = 0.05; cd.clip_end = 2.0e6; cd.sensor_width = 36; cd.sensor_fit = 'HORIZONTAL'
        self.cam.rotation_mode = 'QUATERNION'
        self.setup_render()
        ng = sc.compositing_node_group; self.haze_mr = [nd for nd in ng.nodes if nd.bl_idname == "ShaderNodeMapRange"][0]
        mix = [nd for nd in ng.nodes if nd.bl_idname == "ShaderNodeMix"][0]
        lk = [l for l in ng.links if l.to_node == mix and l.to_socket.name == "Factor"][0]; src = lk.from_socket; ng.links.remove(lk)               # the depth pass is noisy through smoke: soften the haze amount
        bl = ng.nodes.new("CompositorNodeBlur"); bl.inputs["Size"].default_value[0] = 5.0; bl.inputs["Size"].default_value[1] = 5.0
        ng.links.new(src, bl.inputs["Image"]); ng.links.new(bl.outputs["Image"], mix.inputs["Factor"])
        for nd in ng.nodes:
            if nd.bl_idname == "ShaderNodeMath" and nd.operation == 'LESS_THAN':
                nd.inputs[1].default_value = 5.0e6
        if kind == "air":
            self.haze_mr.inputs["From Min"].default_value = 3000.0; self.haze_mr.inputs["From Max"].default_value = 90000.0; self.haze0 = 0.35
        else:
            self.haze_mr.inputs["From Min"].default_value = 400.0; self.haze_mr.inputs["From Max"].default_value = 30000.0; self.haze0 = 0.75

    def set_time(self, t, dt_out, opt):
        """t: seconds after release in the air set; seconds after the burst otherwise."""
        sc = self.sc; mb = opt.get("motion_blur", True); sc.render.use_motion_blur = mb; k = self.kind
        self.haze_mr.inputs["To Max"].default_value = self.haze0 * opt.get("haze", 1.0)
        if k == "air":
            rel = lambda fn: (lambda tt: (lambda p, q: (p - C.ac_pos(tt), q))(*fn(tt)))
            self.key3(self.bomb.ob, rel(bomb_site), t, dt_out, mb); self.key3(self.cradle.ob, rel(cradle_site), t, dt_out, mb); self.bomb.set_fins(C.fins_open(t), steer(t) * C.fins_open(t))
            self.key3(self.extr.ob, lambda tt: (extr_rel(tt)[0], aim_quat(-extr_rel(tt)[1])), t, dt_out, mb)
            c, d, a, stg, op = extr_rel(t); self.extr.set(op, t * 9.0); self.extr.ob.hide_render = stg < 2; self.pack.hide_render = stg >= 2; self.pack.location = tuple(c)
            v = c - a; ln = float(np.linalg.norm(v)); self.line.location = tuple(a); self.line.rotation_quaternion = aim_quat(v / ln); self.line.scale = (ln, 1, 1); self.line.hide_render = stg == 0
            for j, p in enumerate(self.ac.props):
                loc = tuple(p.location); self.key3(p, lambda tt, j=j, loc=loc: (loc, self.ac.prop_quat(tt, j)), t, dt_out, mb)
            self.floor.set(t); return
        tb = t; tt_ = C.T_BURST + min(tb, 0.0); gone = tb >= 0.0
        self.key3(self.bomb.ob, bomb_site, tt_, dt_out, mb); self.bomb.set_fins(1.0, steer(tt_)); self.bomb.hide(gone)
        self.site.update(tb)
        for pl in self.plumes:
            pl.update(bool(opt.get("plume", False)), tb); pl.fl.hide_render = True; pl.glow.hide_render = True
        if self.dom is not None:
            self.dom.hide_render = (not gone) or bool(opt.get("no_sim", False))
            self.fire_node.inputs[1].default_value = self.fire0 * (0.02 + 0.98 * math.exp(-max(tb, 0.0) / 0.55))

# ----------------------------------------------------------------------------- shots: in the air
def shot_approach(n=N_OF["approach"]):
    """The MC-130 on its run-in, seen from behind and to its left: ramp open, the parachute let out."""
    def frame(st, i):
        t = -7.0 + i / FPS; dt = 1.0 / FPS; st.set_time(t, dt, {}); u = smoothstep(0.0, 1.0, i / (n - 1)); c, d, a, stg, op = extr_rel(t)
        pos = np.array([lerp(-50.0, -40.0, u), lerp(42.0, 31.0, u), lerp(12.0, 6.5, u)]); st.look(pos, np.array([lerp(-10.0, -14.0, u), 0.0, 2.0]), lerp(32.0, 37.0, u))
        return t, dt, dict(samples=40, shutter=0.4, anchors={"ac": (C.X0 - 9.0, 0, 4.2), "ramp": (C.X0 - C.RAMP_S[1], 0, 0.0), "chute": tuple(c + d * (0.9 * C.EXTR_D + 0.8)), "rack": tuple(RACK)}, extra=dict(stage=int(stg), open=float(op)))
    return n, frame

REL_REAL = 72                                                        # frames at full speed, to about the moment the load leaves the ramp; half speed after that

def rel_clock(i):
    return (-1.0 + i / FPS, 1.0 / FPS) if i < REL_REAL else (-1.0 + REL_REAL / FPS + (i - REL_REAL) / 48.0, 1.0 / 48.0)

def shot_release(n=N_OF["release"]):
    """From behind and below the tail: the load runs out along the floor and off the ramp; the bomb leaves its cradle and its fins swing out."""
    def frame(st, i):
        t, dt = rel_clock(i); st.set_time(t, dt, {}); u = i / (n - 1); o = C.ac_pos(t); pb = C.bomb_state(t)[0] - o; q = PITCH(C.bomb_state(t)[2]); pc = cradle_site(t)[0] - o; c, d, a, stg, op = extr_rel(t)
        ramp = np.array([C.X0 - C.RAMP_S[1] + 3.0, 0.0, 1.0]); f = smoothstep(-0.2, 1.6, t - C.T_EXIT); aim = ramp + f * (pb - ramp) + np.array([-3.0 * f, 0, 0])
        pos = np.array([lerp(-40.0, -47.0, u), lerp(15.0, 22.0, u), lerp(1.2, -13.0, smoothstep(0.25, 1.0, u))]); st.look(pos, aim, lerp(32.0, 27.0, f))
        return t, dt, dict(samples=44, shutter=0.35, anchors={"bomb": tuple(pb), "nose": tuple(pb + np.array(q @ Vector((C.GBU_L / 2, 0, 0)))), "fins": tuple(pb + np.array(q @ Vector((C.GBU_L / 2 - abomb.S_HINGE, 0, 0.9)))), "plat": tuple(pc + np.array([0, 0, -C.AXIS_H])), "chute": tuple(c + d * (0.9 * C.EXTR_D + 0.8)), "ramp": (C.X0 - C.RAMP_S[1], 0, 0.0)},
                            extra=dict(tau=float(t - C.T_EXIT), fins=float(C.fins_open(t)), sep=float(t - C.T_EXIT > C.T_SEP)))
    return n, frame

# ----------------------------------------------------------------------------- shots: the valley
STRIKE = (24, 96)                                                    # frames before the burst, then frames at one sim frame each; three sim frames per frame after that

def shot_fall(n=N_OF["fall"]):
    """Riding down behind the bomb through its last three and a half seconds: its fins working, the valley coming up."""
    t1 = -STRIKE[0] * ODT; t0 = t1 - (n - 1) / FPS
    def cam_at(tb, u):
        p, q = bomb_site(C.T_BURST + tb); d = np.array(q @ Vector((1, 0, 0))); up = np.array([0, 0, 1.0]) - d * d[2]; up /= np.linalg.norm(up)
        pos = p - d * lerp(19.0, 13.0, u) + up * lerp(6.5, 4.4, u) + np.array([0, -5.0, 0]); return pos, (Vector(p + d * 30.0) - Vector(pos)).to_track_quat('-Z', 'Y')
    def frame(st, i):
        tb = t0 + i / FPS; dt = 1.0 / FPS; st.set_time(tb, dt, dict(haze=1.0)); u = i / (n - 1); pos, q = cam_at(tb, u); st.look(pos, None, 27.0, quat=q)
        st.key3(st.cam, lambda tt: cam_at(tt, u), tb, dt, True); p, v, th = C.bomb_state(C.T_BURST + tb)
        return tb, dt, dict(samples=20, shutter=0.3, anchors={"bomb": tuple(p), "gz": (0, 0, 0), "cave": tuple(asite.target(1))}, extra=dict(alt=float(p[2] - C.Z_BURST), v=float(np.linalg.norm(v)), dive=float(math.degrees(math.atan2(-v[2], v[0])))))
    return n, frame

def strike_clock(i):
    pre, one = STRIKE
    if i < pre:
        return 0, -(pre - i) * ODT, ODT
    if i < pre + one:
        sf = i - pre + 1; return sf, (sf - 1) * ODT, ODT
    sf = one + 3 * (i - pre - one + 1); return sf, (sf - 1) * ODT, 3 * ODT

CAM_STRIKE = np.array([-250.0, -610.0, 0.0])

def shot_strike(n=N_OF["strike"]):
    """From the southern slope, some 650 m off: the bomb comes down and bursts just above the valley floor; the cloud climbs."""
    z0 = float(asite.ground(CAM_STRIKE[0], CAM_STRIKE[1])) + asite.CAM_H; dist = float(np.linalg.norm(CAM_STRIKE[:2]))
    def frame(st, i):
        sf, tb, dt = strike_clock(i); st.set_time(tb, dt, {}); u = i / (n - 1)
        pos = CAM_STRIKE + np.array([14.0 * u, -8.0 * u, z0 + 8.0 * u]); w = smoothstep(0.12, 1.0, u); tgt = np.array([0.0, 0.0, 34.0 + 120.0 * w])      # the view widens and tilts up with the cloud
        off, rq = shake(tb - float(C.t_front(dist)), 0.5); st.look(pos + off, tgt, lerp(24.0, 17.0, w)); st.cam.rotation_quaternion = st.cam.rotation_quaternion @ rq
        p = C.bomb_state(C.T_BURST + min(tb, 0.0))[0]
        return tb, dt, dict(samples=16, sim=sf, shutter=0.25, anchors={"gz": (0, 0, 0), "bomb": tuple(p), "top": (0, 0, 60.0), "cave": tuple(asite.target(2))}, extra=dict(front=float(C.r_front(tb))))
    return n, frame

REACH = (20, 116)                                                    # frames before the burst, then frames at one sim frame each; two sim frames per frame after that
RINGS = (("r10", C.R_10), ("r5", C.R_5), ("r2", C.R_2), ("r1", C.R_1)); NRING = 48

def reach_clock(i):
    pre, one = REACH
    if i < pre:
        return 0, -(pre - i) * ODT, ODT
    j = i - pre
    sf = j + 1 if j < one else one + 1 + 2 * (j - one); return sf, (sf - 1) * ODT, ODT if j < one else 2 * ODT

def _ring(r, z=0.6):
    a = np.linspace(0, 2 * np.pi, NRING, endpoint=False); x = r * np.cos(a); y = r * np.sin(a); return np.stack([x, y, asite.ground(x, y) + z], 1)

def shot_reach(n=N_OF["reach"]):
    """The same burst again from high above the valley: how far the blast reaches, with the calculated pressures drawn on the ground in post."""
    rings = {k: _ring(r) for k, r in RINGS}
    def frame(st, i):
        w = smoothstep(196.0, 282.0, i) if CITY else 0.0                # the city version ends by climbing until the whole city is in the picture
        sf, tb, dt = reach_clock(i); st.set_time(tb, dt, dict(haze=0.5 * (1 - 0.92 * w))); u = smoothstep(0.0, 1.0, min(i, 203) / 203.0)
        pos = np.array([-40.0 + 30.0 * u, -430.0, 640.0 + 40.0 * u]); tgt = np.array([0.0, -40.0, 0.0])
        if w > 0:
            k = w * w * (3 - 2 * w); pos = pos * (1 - k) + np.array([900.0, -1700.0, 8200.0]) * k; tgt = tgt * (1 - k) + np.array([900.0, 300.0, 0.0]) * k
        st.look(pos, tgt, 27.0)
        an = {"gz": (0, 0, 0.5)}; rf = C.r_front(tb)
        for k, P in rings.items():
            an.update({"%s_%02d" % (k, j): tuple(P[j]) for j in range(NRING)})
        if 0.0 < rf < 900.0:
            an.update({"f_%02d" % j: tuple(q) for j, q in enumerate(_ring(rf, 1.0))})
        return tb, dt, dict(samples=20, sim=sf, shutter=0.25, anchors=an, extra=dict(front=float(rf), tb=float(tb), wide=float(w)))
    return n, frame

def shot_after(n=N_OF["after"]):
    """A minute later, circling: what stands and what does not."""
    def cam_at(tb, u):
        a = D(lerp(232.0, 282.0, u)); r = lerp(330.0, 300.0, u); pos = np.array([r * math.cos(a), r * math.sin(a) - 30.0, lerp(215.0, 190.0, u)]); return pos, (Vector((0.0, -22.0, -6.0)) - Vector(pos)).to_track_quat('-Z', 'Y')
    ring5 = _ring(C.R_5); ring2 = _ring(C.R_2)
    def frame(st, i):
        tb = 60.0 + i / FPS; dt = 1.0 / FPS; st.set_time(tb, dt, dict(plume=os.environ.get("NO_PLUMES") != "1", haze=0.6, no_sim=True)); u = smoothstep(0.0, 1.0, i / (n - 1)); pos, q = cam_at(tb, u); st.look(pos, None, 28.0, quat=q)
        st.key3(st.cam, lambda tt: cam_at(tt, u), tb, dt, True)
        an = {"gz": (0, 0, 0.3), "cave": tuple(asite.target(1))}; an.update({"r5_%02d" % j: tuple(ring5[j]) for j in range(NRING)}); an.update({"r2_%02d" % j: tuple(ring2[j]) for j in range(NRING)})
        cs = st.site.comps; flat = min((c for c in cs if c["state"] == 2), key=lambda c: abs(c["r"] - 85.0), default=None); city = C.SITE == "city"; hurt = min((c for c in cs if c["state"] == 1 and c.get("lvl", 1) == (2 if city else 1) and c["y"] < (-10.0 if city else -60.0)), key=lambda c: abs(c["r"] - (105.0 if city else 170.0)), default=None); ok = min((c for c in cs if c["state"] == 0 and c["y"] < -60.0), key=lambda c: c["r"], default=None)
        for nm, c in (("flat", flat), ("hurt", hurt), ("ok", ok)):
            if c is not None:
                an[nm] = (c["x"], c["y"], c["z"] + 3.0)
        return tb, dt, dict(samples=32, shutter=0.35, anchors=an)
    return n, frame

def shot_city(n=N_OF["city"]):
    """Before the strike: a flight over the whole city, from the river and the works towards the district the bomb will fall on."""
    def cam_at(u):
        pos = np.array([lerp(4300.0, 2300.0, u), lerp(3600.0, 2500.0, u), lerp(1500.0, 1150.0, u)]); tgt = np.array([lerp(1700.0, 500.0, u), lerp(500.0, 100.0, u), 0.0]); return pos, (Vector(tgt) - Vector(pos)).to_track_quat('-Z', 'Y')
    def frame(st, i):
        tb = -40.0 + i / FPS; dt = 1.0 / FPS; st.set_time(tb, dt, dict(haze=0.45)); u = smoothstep(0.0, 1.0, i / (n - 1)); pos, q = cam_at(u); st.look(pos, None, 24.0, quat=q)
        st.key3(st.cam, lambda tt: cam_at(smoothstep(0.0, 1.0, (i + (tt - tb) * FPS) / (n - 1))), tb, dt, True)
        an = {"gz": (0.0, 0.0, 20.0)}; an.update({k: tuple(v) for k, v in asite.LABELS.items()})
        return tb, dt, dict(samples=32, shutter=0.3, anchors=an, extra=dict(**{k: int(v) for k, v in st.site.count.items()}))
    return n, frame

SHOTS = {"approach": shot_approach, "release": shot_release, "city": shot_city, "fall": shot_fall, "strike": shot_strike, "reach": shot_reach, "after": shot_after}

# ----------------------------------------------------------------------------- studio shots
def _studio(scale, world=0.30, backdrop=(0.64, 0.61, 0.56)):
    bpy.ops.wm.read_factory_settings(use_empty=True); sc = bpy.context.scene; k = scale
    prof = [(-160.0, 0.0), (16.0, 0.0)] + [(16.0 + 5.0 * math.sin(a), 5.0 * (1 - math.cos(a))) for a in np.linspace(0, math.pi / 2, 12)[1:]] + [(21.0, 80.0)]
    V = np.array([[x, y, z] for (y, z) in prof for x in (-120.0, 120.0)]) * k
    new_obj("Backdrop", new_mesh("bd", V, [grid_faces(len(prof), 2)]), None, simple_mat("BackdropMat", backdrop, rough=0.85))
    w = bpy.data.worlds.new("Studio"); sc.world = w; w.use_nodes = True
    w.node_tree.nodes["Background"].inputs[0].default_value = (0.75, 0.78, 0.82, 1); w.node_tree.nodes["Background"].inputs[1].default_value = world
    def area(loc, size, power, color=(1, 1, 1)):
        L_ = bpy.data.lights.new("a", 'AREA'); L_.size = size * k; L_.energy = power * k * k; L_.color = color
        o = bpy.data.objects.new("a", L_); sc.collection.objects.link(o); o.location = Vector(loc) * k; o.rotation_euler = (Vector((0, 0, 2.0)) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    area((6.0, -8.0, 9.0), 7.0, 2200, (1.0, 0.96, 0.9)); area((-8.0, -5.0, 3.5), 8.0, 700, (0.8, 0.9, 1.0)); area((-2.5, 7.0, 7.0), 6.0, 2000)
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); sc.collection.objects.link(cam); sc.camera = cam; cam.data.clip_start = 0.05; cam.data.clip_end = 6000; cam.data.sensor_width = 36
    sc.render.engine = 'CYCLES'; c = sc.cycles; c.use_denoising = True; c.denoising_quality = 'HIGH'; c.max_bounces = 6
    use_device(sc); sc.view_settings.view_transform = 'AgX'; sc.view_settings.look = 'AgX - Medium High Contrast'
    sc.render.image_settings.file_format = 'PNG'; sc.render.use_persistent_data = True
    return sc, cam

def render_card(out_dir, res, spp, frames, n=N_OF["card"]):
    """The bomb on its cradle and platform, fins folded, turning slowly on a studio backdrop (left half of the frame; the panel is added in post)."""
    k = 1.5; sc, cam = _studio(k); sc.cycles.samples = spp or 40
    pivot = bpy.data.objects.new("Pivot", None); sc.collection.objects.link(pivot); pivot.location = (0.0, 0, C.AXIS_H)
    B = abomb.Bomb(name="Card"); B.ob.parent = pivot; B.ob.location = (-0.45, 0, 0); B.set_fins(0.0); cr = abomb.Cradle(name="CardCradle"); cr.ob.parent = pivot; cr.ob.location = B.ob.location
    cam.data.lens = 85; cam.location = (0.0, -27.0 * k, 2.3 * k); cam.rotation_euler = (math.radians(87.6), 0, 0); cam.data.shift_x = 0.25
    sc.render.resolution_x, sc.render.resolution_y = res; sc.render.use_border = True; sc.render.use_crop_to_border = True
    sc.render.border_min_x = 0.0; sc.render.border_max_x = 0.50; sc.render.border_min_y = 0.0; sc.render.border_max_y = 1.0
    os.makedirs(out_dir, exist_ok=True)
    for i in (frames if frames is not None else range(n)):
        u = i / n
        if os.path.exists(os.path.join(out_dir, "f%04d.png" % i)):
            continue
        pivot.rotation_euler = (0, 0, math.radians(-150) + math.radians(13) * math.sin(2 * math.pi * u))
        sc.render.filepath = os.path.join(out_dir, "f%04d.png" % i); t = time.time(); bpy.ops.render.render(write_still=True)
        print("FRAME card %d %.1fs" % (i, time.time() - t)); sys.stdout.flush()

INTRO_X = 0.0; INTRO_Z = (5.5, 2.2)

def render_intro(out_dir, res, spp, frames, n=N_OF["intro"]):
    """The bomb as it falls, fins out (above), and cut open along its length (below)."""
    from bpy_extras.object_utils import world_to_camera_view
    sc, cam = _studio(1.0, world=0.24, backdrop=(0.105, 0.11, 0.12)); sc.cycles.samples = spp or 48
    bpy.data.objects["Backdrop"].location = (0, 0, -7.0)
    g = abomb.Bomb(name="Whole"); g.ob.location = (INTRO_X, 0, INTRO_Z[0]); c = abomb.Bomb(name="Cut", cut=True); c.ob.location = (INTRO_X, 0, INTRO_Z[1])
    sc.render.resolution_x, sc.render.resolution_y = res; os.makedirs(out_dir, exist_ok=True)
    L = C.GBU_L; R = C.GBU_D / 2; zt, zb = INTRO_Z; x0 = INTRO_X; X = lambda s: x0 + L / 2 - s; hf = (abomb.R_HINGE + 0.6 * abomb.FIN_L) * 0.707
    pts = {"nose": (X(0.0), 0, zt), "tail": (X(L), 0, zt), "top": (x0, 0, zt + R), "bot": (x0, 0, zt - R), "probe": (X(0.12), 0, zt), "wing": (X(5.6), -R - 0.3, zt), "fin": (X(abomb.S_HINGE), -hf, zt + hf), "box": (X(L - 0.4), -abomb.R_BOX, zt - 0.1),
           "cwall": (X(3.0), 0, zb + R - 0.012), "cfill": (X(4.2), 0, zb - 0.12), "cfuze": (X(C.PROBE_L + 0.38), 0, zb), "cbox": (X(L - 0.42), 0, zb), "cn": (X(0.0), 0, zb), "ct": (X(L), 0, zb), "cbot": (x0, 0, zb - R)}
    meta_path = os.path.join(out_dir, "meta.json"); meta = json.load(open(meta_path)) if os.path.exists(meta_path) else {}
    for i in (frames if frames is not None else range(n)):
        u = smoothstep(0.0, 1.0, i / (n - 1)); cam.data.lens = 60; cam.location = (lerp(0.45, -0.35, u), -34.0, 3.2); cam.rotation_euler = (math.radians(90.0), 0, 0)
        bpy.context.view_layer.update(); proj = lambda p: (lambda v: [float(v.x), float(1 - v.y), float(v.z)])(world_to_camera_view(sc, cam, Vector(p)))
        meta[str(i)] = dict(t=i / FPS, anchors={kk: proj(p) for kk, p in pts.items()}); json.dump(meta, open(meta_path, "w"))
        if os.path.exists(os.path.join(out_dir, "f%04d.png" % i)):
            continue
        sc.render.filepath = os.path.join(out_dir, "f%04d.png" % i); t = time.time(); bpy.ops.render.render(write_still=True)
        print("FRAME intro %d %.1fs" % (i, time.time() - t)); sys.stdout.flush()

# ----------------------------------------------------------------------------- driver
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("shot"); ap.add_argument("out")
    ap.add_argument("--sim", default=None); ap.add_argument("--res", default="1280x720")
    ap.add_argument("--spp", type=int, default=0); ap.add_argument("--frames", default="")
    a = ap.parse_args(sys.argv[1:])
    res = tuple(int(x) for x in a.res.split("x"))
    if a.shot in ("card", "intro"):
        (render_card if a.shot == "card" else render_intro)(a.out, res, a.spp, gsh.parse_frames(a.frames, N_OF[a.shot]) if a.frames else None)
        sys.stdout.flush(); os._exit(0)
    n, frame = SHOTS[a.shot]()
    frames = gsh.parse_frames(a.frames, n)
    st = Stage(SET_OF[a.shot], os.path.join(a.sim, SIM_OF[a.shot]) if (a.sim and a.shot in SIM_OF) else None)
    sc = st.sc; sc.render.resolution_x, sc.render.resolution_y = res
    use_device(sc)
    sc.render.use_persistent_data = os.environ.get("PERSIST", "0") == "1"   # off: with data kept between frames the ground now and then rendered black for the rest of a run
    if os.environ.get("VOL_STEP"):                                  # coarser volume steps for a quick draft on a CPU
        sc.cycles.volume_step_rate = float(os.environ["VOL_STEP"]); sc.cycles.volume_max_steps = 96
    os.makedirs(a.out, exist_ok=True)
    tl = dict(SITE=C.SITE, T_EXIT=C.T_EXIT, V_EXIT=C.V_EXIT, T_SEP=C.T_SEP, T_FINS=list(C.T_FINS), TAU_HIT=C.TAU_HIT, T_BURST=C.T_BURST, THROW=C.THROW, V_AC=C.V_AC, V_HIT=C.V_HIT, DIVE=C.DIVE, H_REL=C.H_REL, ELEV=C.ELEV, HOB=C.HOB, MACH=C.V_HIT / C.C0,
              R_10=C.R_10, R_5=C.R_5, R_2=C.R_2, R_1=C.R_1, PSI_MILE=C.PSI_MILE, FB_D=C.FB_D, STRIKE=list(STRIKE), REACH=list(REACH), REL_REAL=REL_REAL, ODT=ODT, NRING=NRING, CAM_DIST=float(np.linalg.norm(CAM_STRIKE[:2])),
              N_FLAT=sum(1 for c in st.site.comps if c["state"] == 2) if hasattr(st, "site") else -1, PSI={str(r): float(C.psi(r)) for r in (50, 100, 150, 200, 300, 500, 1000)}, FRONT=[[r, float(C.t_front(r))] for r in range(0, 1201, 10)], fps=FPS)
    json.dump(tl, open(os.path.join(os.path.dirname(os.path.abspath(a.out)), "timeline.json"), "w"))
    meta_path = os.path.join(a.out, "meta.json")
    meta = json.load(open(meta_path)) if os.path.exists(meta_path) else {}
    from bpy_extras.object_utils import world_to_camera_view
    for i in frames:
        fp = os.path.join(a.out, "f%04d.png" % i); have = os.path.exists(fp)
        if have and str(i) in meta:
            continue
        t0 = time.time()                                             # a frame that exists without its entry in meta.json gets the entry rebuilt, not a new render
        sc.frame_set(0)
        t, dt, info = frame(st, i)
        sf = info.get("sim", 0)
        if sc.frame_current != sf:
            sc.frame_set(sf)
            t, dt, info = frame(st, i)
        sc.cycles.samples = a.spp or info.get("samples", 12)
        sc.render.motion_blur_shutter = info.get("shutter", 0.5)
        bpy.context.view_layer.update()
        proj = lambda p: (lambda v: [float(v.x), float(1 - v.y), float(v.z)])(world_to_camera_view(sc, st.cam, Vector(p)))
        m = dict(t=float(t), td=float(t), sim=int(sf), anchors={k: proj(p) for k, p in info.get("anchors", {}).items()})
        m.update(info.get("extra", {}))
        meta[str(i)] = m
        if not have:
            sc.render.filepath = fp
            bpy.ops.render.render(write_still=True)
        print("%s %s %d t=%.4f sim=%d %.1fs" % ("META" if have else "FRAME", a.shot, i, t, sf, time.time() - t0)); sys.stdout.flush()
        json.dump(meta, open(meta_path, "w"))
    sys.stdout.flush(); os._exit(0)

if __name__ == "__main__":
    main()
