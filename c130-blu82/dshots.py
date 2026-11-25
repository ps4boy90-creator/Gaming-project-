"""Shot definitions and frame renderer for the C-130 / BLU-82 segment.

  python3 dshots.py <shot> <out_dir> [--sim <sim_root>] [--res 1280x720] [--spp N] [--frames a-b | i,j,k]

Shots and their sets:
  card, intro           studio      the bomb on its cradle; the bomb whole and cut open
  approach, release     air         the C-130 with its ramp open; the load pulled out, the bomb leaving its cradle
  fall, strike, after   out         the jungle from the air
  cutaway               sec         the forest cut along a line through the burst point, seen square on
Clocks: air set, t = seconds after the loadmaster releases the load; out and sec sets, tb = seconds after the burst.
Sim frames: "out" 1/40 s each, "sec" 1/240 s each, frame 1 = the burst.
"""
import bpy, sys, os, math, json, time, argparse
HERE = os.path.dirname(os.path.abspath(__file__))
for p in ("grenade-explosion", "rpg7-explosion", "mortar-explosion", "howitzer-explosion", "reaper-hellfire"):
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
import dconst as C, dbomb, dc130, djungle

FPS = C.FPS; ODT = 1.0 / 40.0; SDT = 1.0 / 240.0
D = math.radians
shake = gsh.shake
SET_OF = {"approach": "air", "release": "air", "fall": "out", "strike": "out", "after": "out", "cutaway": "sec"}
SIM_OF = {"strike": "out", "cutaway": "sec"}
N_OF = {"card": 72, "approach": 96, "intro": 96, "release": 174, "fall": 84, "strike": 220, "cutaway": 252, "after": 108}
LINE_L = 14.0                                                        # the extraction line, from the platform to where the parachute's lines meet
TAIL = C.BLU_L / 2 + 0.34                                            # the stabilising parachute is made fast here, behind the middle of the bomb
PITCH = lambda th: Quaternion((0, 1, 0), th)

def bomb_site(t):
    p, v, th = C.bomb_state(t); return p, PITCH(th)

def cradle_site(t):
    tau = t - C.T_EXIT
    if tau < C.T_SEP:
        return bomb_site(t)
    p, v = C.plat_state(t); th = C.bomb_state(C.T_EXIT + C.T_SEP)[2] - 0.55 * (1 - math.exp(-(tau - C.T_SEP) / 1.2))       # relieved of the bomb, it is pulled tail-first by its parachute
    return p + np.array([0, 0, C.AXIS_H]), PITCH(th)

def extr_site(t):
    """Where the extraction parachute's lines meet, the way it trails, and the point on the platform it pulls on."""
    p, q = cradle_site(t); a = p + np.array(q @ Vector((-C.PLAT_L / 2 - 0.05, 0.0, -C.AXIS_H + C.PLAT_H))); tau = t - C.T_EXIT
    d0 = np.array([-1.0, 0.0, -0.04]); v = C.plat_state(t)[1] if tau > 0 else np.array([C.V_AC, 0.0, 0.0]); d1 = -v / np.linalg.norm(v); k = smoothstep(0.0, 0.8, tau); d = d0 * (1 - k) + d1 * k; d /= np.linalg.norm(d)
    return a + d * LINE_L, d, a

def stab_site(t):
    p, v, th = C.bomb_state(t); tail = p + np.array(PITCH(th) @ Vector((-TAIL, 0, 0))); d = v / np.linalg.norm(v); return tail, aim_quat(d)

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
            self.fire0 = 30.0 if kind == "out" else 15.0; bm_ = blast_material(density=4.2 if kind == "out" else 2.6, fire=self.fire0, ambient=0.06); self.dom.data.materials.append(bm_); self.fire_node = bm_.node_tree.nodes[bm_["fire_node"]]; self.dens_node = bm_.node_tree.nodes[bm_["density_node"]]; self.dens0 = self.dens_node.inputs[1].default_value
            for nd in bm_.node_tree.nodes:                             # keep the dust's own browns: less of the lift towards pale grey that suits desert dust
                if nd.type == 'VECT_MATH' and nd.operation == 'POWER':
                    nd.inputs[1].default_value = (0.80, 0.80, 0.80)
            self.dom.hide_render = True
        else:
            bpy.ops.wm.read_factory_settings(use_empty=True)
        sc = self.sc = bpy.context.scene; sc.render.fps = FPS
        col = self.col = bpy.data.collections.new("ACTION"); sc.collection.children.link(col)
        ec = self.env_col = bpy.data.collections.new("ENV"); sc.collection.children.link(ec)
        self.bomb = dbomb.Bomb(col, "Bomb"); self.stab = dbomb.Chute(col, "Stab", d=C.STAB_D)
        if kind == "air":
            self.floor = djungle.AirFloor(sc, ec); self.ac = dc130.C130(col)
            self.cradle = dbomb.Cradle(col); self.extr = dbomb.Chute(col, "Extraction", d=C.EXTR_D, lines=0.9, c1=(0.33, 0.37, 0.24, 1), c2=(0.26, 0.30, 0.19, 1))
            S = Shell(); S.add(*gbox((0.5, 0, 0), (1.0, 0.035, 0.035)), color=(0.62, 0.60, 0.50, 1)); self.line = new_obj("ExtractionLine", S.mesh("extr_line"), col, dbomb.cloth_mat()); self.line.rotation_mode = 'QUATERNION'
            ld = bpy.data.lights.new("Bounce", 'AREA'); ld.size = 80.0; ld.energy = 1.0e4; ld.color = (0.80, 0.95, 0.75); lo = bpy.data.objects.new("Bounce", ld); col.objects.link(lo)   # light thrown back up by the forest
            lo.location = (0, 0, -50.0); lo.rotation_euler = (math.pi, 0, 0); ld.use_shadow = False
        else:
            self.site = djungle.Jungle(sc, ec, kind)
            if kind == "out":
                self.plumes = []
                for (x, y, s) in ((6.0, -4.0, 0.8), (-17.0, 9.0, 0.6), (14.0, 18.0, 0.5)):
                    pl = Plume(col); pl.ob.location = (x, y, 0.0); pl.ob.scale = (s, s, s); pl.fl.hide_render = True; pl.glow.hide_render = True; self.plumes.append(pl)
                    for mt in pl.mats:                                  # thin grey smoke from smouldering wood
                        f = mt.node_tree.nodes["Fade"]; f.inputs["To Min"].default_value = 0.16; f.inputs["To Max"].default_value = 0.02
                        for nd in mt.node_tree.nodes:
                            if nd.type == 'PRINCIPLED_VOLUME':
                                nd.inputs["Color"].default_value = (0.78, 0.77, 0.75, 1)
        cd = bpy.data.cameras.new("Cam"); self.cam = bpy.data.objects.new("Cam", cd); sc.collection.objects.link(self.cam); sc.camera = self.cam
        cd.clip_start = 0.05; cd.clip_end = 2.0e6; cd.sensor_width = 36; cd.sensor_fit = 'HORIZONTAL'
        self.cam.rotation_mode = 'QUATERNION'
        self.setup_render()
        ng = sc.compositing_node_group; self.haze_mr = [nd for nd in ng.nodes if nd.bl_idname == "ShaderNodeMapRange"][0]
        mix = [nd for nd in ng.nodes if nd.bl_idname == "ShaderNodeMix"][0]; mix.inputs["B"].default_value = (0.66, 0.74, 0.82, 1.0)                 # damp tropical air
        lk = [l for l in ng.links if l.to_node == mix and l.to_socket.name == "Factor"][0]; src = lk.from_socket; ng.links.remove(lk)               # the depth pass is noisy through smoke and leaves: soften the haze amount
        bl = ng.nodes.new("CompositorNodeBlur"); bl.inputs["Size"].default_value[0] = 5.0; bl.inputs["Size"].default_value[1] = 5.0
        ng.links.new(src, bl.inputs["Image"]); ng.links.new(bl.outputs["Image"], mix.inputs["Factor"])
        for nd in ng.nodes:
            if nd.bl_idname == "ShaderNodeMath" and nd.operation == 'LESS_THAN':
                nd.inputs[1].default_value = 5.0e6
        if kind == "air":
            self.haze_mr.inputs["From Min"].default_value = 1500.0; self.haze_mr.inputs["From Max"].default_value = 70000.0; self.haze0 = 0.80
        else:
            self.haze_mr.inputs["From Min"].default_value = 350.0; self.haze_mr.inputs["From Max"].default_value = 12000.0; self.haze0 = 0.97

    def set_time(self, t, dt_out, opt):
        """t: seconds after release in the air set; seconds after the burst otherwise."""
        sc = self.sc; mb = opt.get("motion_blur", True); sc.render.use_motion_blur = mb; k = self.kind
        self.haze_mr.inputs["To Max"].default_value = self.haze0 * opt.get("haze", 1.0)
        if k == "air":
            rel = lambda fn: (lambda tt: (lambda p, q: (p - C.ac_pos(tt), q))(*fn(tt)))
            self.key3(self.bomb.ob, rel(bomb_site), t, dt_out, mb); self.key3(self.cradle.ob, rel(cradle_site), t, dt_out, mb)
            self.key3(self.extr.ob, rel(lambda tt: (extr_site(tt)[0], aim_quat(-extr_site(tt)[1]))), t, dt_out, mb); self.extr.set(1.0, t * 9.0)
            c, d, a = extr_site(t); self.line.location = tuple(a - C.ac_pos(t)); self.line.rotation_quaternion = aim_quat(d); self.line.scale = (LINE_L, 1, 1)
            on = t - C.T_EXIT > C.T_SEP; self.stab.ob.hide_render = not on
            self.key3(self.stab.ob, rel(stab_site), t, dt_out, mb); self.stab.set(C.stab_open(t) if on else 0.0, t * 11.0)
            for j, p in enumerate(self.ac.props):
                loc = tuple(p.location); self.key3(p, lambda tt, j=j, loc=loc: (loc, self.ac.prop_quat(tt, j)), t, dt_out, mb)
            self.floor.ob.location = (-C.V_AC * t, 0.0, 0.0); return
        tb = t; tt_ = C.T_BURST + min(tb, 0.0); gone = tb >= 0.0
        self.key3(self.bomb.ob, bomb_site, tt_, dt_out, mb); self.key3(self.stab.ob, stab_site, tt_, dt_out, mb); self.stab.set(1.0, tt_ * 11.0)
        self.bomb.hide(gone); self.stab.ob.hide_render = gone
        self.site.update(tb)
        if k == "out":
            for pl in self.plumes:
                pl.update(bool(opt.get("plume", False)), tb); pl.fl.hide_render = True; pl.glow.hide_render = True
        if self.dom is not None:
            self.dom.hide_render = (not gone) or bool(opt.get("no_sim", False))
            self.fire_node.inputs[1].default_value = self.fire0 * (0.02 + 0.98 * math.exp(-max(tb, 0.0) / (0.55 if k == "out" else 0.20)))
            if k == "sec":                                           # in the section the dust is thinned as it spreads, so that the trees behind it can be seen
                self.dens_node.inputs[1].default_value = self.dens0 * (0.035 + 0.965 * math.exp(-max(tb, 0.0) / 0.11))

# ----------------------------------------------------------------------------- shots: in the air
def shot_approach(n=N_OF["approach"]):
    """The C-130 on its run-in, seen from behind and to its left: ramp open, the extraction parachute already out."""
    def frame(st, i):
        t = -7.0 + i / FPS; dt = 1.0 / FPS; st.set_time(t, dt, {}); u = smoothstep(0.0, 1.0, i / (n - 1)); c, d, a = extr_site(t); o = C.ac_pos(t)
        pos = np.array([lerp(-46.0, -36.0, u), lerp(40.0, 29.0, u), lerp(12.0, 6.5, u)]); st.look(pos, np.array([lerp(-9.0, -12.0, u), 0.0, 2.0]), lerp(34.0, 40.0, u))
        return t, dt, dict(samples=40, shutter=0.4, anchors={"ac": (C.X0 - 9.0, 0, 4.2), "ramp": (C.X0 - C.RAMP_S[1], 0, 0.0), "chute": tuple(c - o + d * (0.9 * C.EXTR_D + 0.8)), "tank": (C.X0 - 12.0, dc130.TANK_Y, 1.6)})
    return n, frame

REL_REAL = 78                                                        # frames at full speed, to the moment the load leaves the ramp; half speed after that

def rel_clock(i):
    return (-1.0 + i / FPS, 1.0 / FPS) if i < REL_REAL else (-1.0 + REL_REAL / FPS + (i - REL_REAL) / 48.0, 1.0 / 48.0)

def shot_release(n=N_OF["release"]):
    """From behind and below the tail: the load runs out along the floor and off the ramp; the bomb leaves its cradle and its own parachute fills."""
    def frame(st, i):
        t, dt = rel_clock(i); st.set_time(t, dt, {}); u = i / (n - 1); o = C.ac_pos(t); pb = C.bomb_state(t)[0] - o; pc = cradle_site(t)[0] - o; c, d, a = extr_site(t); sp, sq = stab_site(t)
        ramp = np.array([C.X0 - C.RAMP_S[1] + 2.0, 0.0, 1.0]); f = smoothstep(-0.2, 1.4, t - C.T_EXIT); aim = ramp + f * (pb - ramp) + np.array([-2.0 * f, 0, 0])
        pos = np.array([lerp(-36.0, -41.0, u), lerp(13.0, 19.0, u), lerp(1.2, -11.0, smoothstep(0.25, 1.0, u))]); st.look(pos, aim, lerp(34.0, 30.0, f))
        return t, dt, dict(samples=44, shutter=0.35, anchors={"bomb": tuple(pb), "plat": tuple(pc + np.array([0, 0, -C.AXIS_H])), "chute": tuple(c - o + d * (0.9 * C.EXTR_D + 0.8)), "stab": tuple(sp - o - np.array(sq @ Vector((1.25 * C.STAB_D, 0, 0)))), "ramp": (C.X0 - C.RAMP_S[1], 0, 0.0)},
                            extra=dict(tau=float(t - C.T_EXIT), open=float(C.stab_open(t)), sep=float(t - C.T_EXIT > C.T_SEP)))
    return n, frame

# ----------------------------------------------------------------------------- shots: the jungle from the air
def shot_fall(n=N_OF["fall"]):
    """Beside the bomb through its last three and a half seconds: nearly upright under its parachute, the canopy coming up."""
    t1 = -0.05; t0 = t1 - (n - 1) / FPS
    def cam_at(tb, u):
        p, q = bomb_site(C.T_BURST + tb); pos = p + np.array([lerp(-10.0, -5.0, u), lerp(30.0, 22.0, u), lerp(17.0, 12.0, u)]); return pos, (Vector(p + np.array([0.6, 0, -2.5])) - Vector(pos)).to_track_quat('-Z', 'Y')
    def frame(st, i):
        tb = t0 + i / FPS; dt = 1.0 / FPS; st.set_time(tb, dt, dict(haze=0.7)); u = i / (n - 1); pos, q = cam_at(tb, u); st.look(pos, None, 26.0, quat=q)
        st.key3(st.cam, lambda tt: cam_at(tt, u), tb, dt, True); p, v, th = C.bomb_state(C.T_BURST + tb); sp, sq = stab_site(C.T_BURST + tb)
        return tb, dt, dict(samples=20, shutter=0.3, anchors={"bomb": tuple(p), "tip": tuple(p + np.array(PITCH(th) @ Vector((C.BLU_L / 2 + C.EXT_L, 0, 0)))), "stab": tuple(sp - np.array(sq @ Vector((1.25 * C.STAB_D, 0, 0))))},
                            extra=dict(alt=float(p[2] - C.HOB), v=float(np.linalg.norm(v)), dive=float(math.degrees(math.atan2(-v[2], v[0])))))
    return n, frame

STRIKE = (24, 96)                                                    # frames before the burst, then frames at one sim frame each; two sim frames per frame after that

def strike_clock(i):
    pre, one = STRIKE
    if i < pre:
        return 0, -(pre - i) * ODT, ODT
    if i < pre + one:
        sf = i - pre + 1; return sf, (sf - 1) * ODT, ODT
    sf = one + 2 * (i - pre - one + 1); return sf, (sf - 1) * ODT, 2 * ODT

def shot_strike(n=N_OF["strike"]):
    """From the air, 300 m off: the bomb goes into the canopy and bursts just above the ground."""
    def frame(st, i):
        sf, tb, dt = strike_clock(i); st.set_time(tb, dt, {}); u = i / (n - 1)
        pos = np.array([-250.0 + 14.0 * u, -165.0 - 8.0 * u, 92.0 + 6.0 * u]); tgt = np.array([0.0, 0.0, 26.0 + 34.0 * smoothstep(0.15, 1.0, u)])
        off, rq = shake(tb - float(C.t_front(300.0)), 1.6); st.look(pos + off, tgt, 30.0); st.cam.rotation_quaternion = st.cam.rotation_quaternion @ rq
        p = C.bomb_state(C.T_BURST + min(tb, 0.0))[0]
        return tb, dt, dict(samples=16, sim=sf, shutter=0.25, anchors={"gz": (0, 0, 0), "bomb": tuple(p), "top": (0, 0, 45.0), "edge": (0.0, -C.R_LZ, 30.0), "edge2": (0.0, C.R_LZ, 30.0)})
    return n, frame

def shot_after(n=N_OF["after"]):
    """A minute later, circling: the clearing."""
    def cam_at(tb, u):
        a = D(lerp(205.0, 252.0, u)); r = lerp(150.0, 132.0, u); pos = np.array([r * math.cos(a), r * math.sin(a), lerp(118.0, 100.0, u)]); return pos, (Vector((0.0, 0.0, -4.0)) - Vector(pos)).to_track_quat('-Z', 'Y')
    def frame(st, i):
        tb = 60.0 + i / FPS; dt = 1.0 / FPS; st.set_time(tb, dt, dict(plume=True, haze=0.6, no_sim=True)); u = smoothstep(0.0, 1.0, i / (n - 1)); pos, q = cam_at(tb, u); st.look(pos, None, 28.0, quat=q)
        st.key3(st.cam, lambda tt: cam_at(tt, u), tb, dt, True)
        an = {"c": (0, 0, 0.3)}; an.update({"r%02d" % k: (C.R_LZ * math.cos(k * math.pi / 24), C.R_LZ * math.sin(k * math.pi / 24), 0.5) for k in range(48)})
        return tb, dt, dict(samples=32, shutter=0.35, anchors=an)
    return n, frame

# ----------------------------------------------------------------------------- shot: the section
CUT = (48, 150)                                                      # frames before the burst (1/240 s each), then frames at one sim frame each; two per frame after that
VIEW_A = (0.5, 15.0, 62.0); VIEW_B = (0.0, 27.0, 168.0)              # centre x, centre z and width of the view: the last metres, then the whole clearing

def cut_clock(i):
    pre, one = CUT
    if i < pre:
        return 0, -(pre - i) * SDT, SDT
    j = i - pre
    sf = j + 1 if j < one else one + 1 + 2 * (j - one); return sf, (sf - 1) * SDT, SDT if j < one else 2 * SDT

def shot_cutaway(n=N_OF["cutaway"]):
    """The forest cut along a line through the burst point, the camera square on: the fuze touches, the burst, the trees going down."""
    def frame(st, i):
        sf, tb, dt = cut_clock(i); st.set_time(tb, dt, dict(haze=0.5))
        u = smoothstep(0.0, 1.0, (i - CUT[0] + 2) / 40.0); cx, cz, w = [lerp(a, b, u) for a, b in zip(VIEW_A, VIEW_B)]; dist = w * 38.0 / 36.0
        pos = np.array([cx, dist, cz]); st.look(pos, pos + np.array([0.0, -dist, 0.0]), 38.0)        # a steady camera: this is a drawing
        p, v, th = C.bomb_state(C.T_BURST + min(tb, 0.0)); tip = p + np.array(PITCH(th) @ Vector((C.BLU_L / 2 + C.EXT_L, 0, 0)))
        return tb, dt, dict(samples=36 if sf == 0 else 26, sim=sf, shutter=0.3, anchors={"o": (0, 0, 0), "ex": (1, 0, 0), "ez": (0, 0, 1), "bomb": tuple(p), "tip": tuple(tip)}, extra=dict(tb=float(tb), tipz=float(max(tip[2], 0.0)), v=float(np.linalg.norm(v))))
    return n, frame

SHOTS = {"approach": shot_approach, "release": shot_release, "fall": shot_fall, "strike": shot_strike, "after": shot_after, "cutaway": shot_cutaway}

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
    """The bomb on its cradle and platform, turning slowly on a studio backdrop (left half of the frame; the panel is added in post)."""
    sc, cam = _studio(1.0); sc.cycles.samples = spp or 40
    pivot = bpy.data.objects.new("Pivot", None); sc.collection.objects.link(pivot); pivot.location = (0.0, 0, C.AXIS_H)
    B = dbomb.Bomb(name="Card"); B.ob.parent = pivot; B.ob.location = (-C.EXT_L / 2 + 0.15, 0, 0); cr = dbomb.Cradle(name="CardCradle"); cr.ob.parent = pivot; cr.ob.location = B.ob.location
    cam.data.lens = 85; cam.location = (0.0, -27.0, 3.2); cam.rotation_euler = (math.radians(85.6), 0, 0); cam.data.shift_x = 0.25
    sc.render.resolution_x, sc.render.resolution_y = res; sc.render.use_border = True; sc.render.use_crop_to_border = True
    sc.render.border_min_x = 0.0; sc.render.border_max_x = 0.50; sc.render.border_min_y = 0.0; sc.render.border_max_y = 1.0
    os.makedirs(out_dir, exist_ok=True)
    for i in (frames if frames is not None else range(n)):
        u = i / n
        if os.path.exists(os.path.join(out_dir, "f%04d.png" % i)):
            continue
        pivot.rotation_euler = (0, 0, math.radians(-148) + math.radians(14) * math.sin(2 * math.pi * u))
        sc.render.filepath = os.path.join(out_dir, "f%04d.png" % i); t = time.time(); bpy.ops.render.render(write_still=True)
        print("FRAME card %d %.1fs" % (i, time.time() - t)); sys.stdout.flush()

INTRO_X = -0.15; INTRO_Z = (2.95, 0.95)

def render_intro(out_dir, res, spp, frames, n=N_OF["intro"]):
    """The bomb as it falls (above) and cut open along its length (below)."""
    from bpy_extras.object_utils import world_to_camera_view
    sc, cam = _studio(1.0, world=0.24, backdrop=(0.105, 0.11, 0.12)); sc.cycles.samples = spp or 48
    bpy.data.objects["Backdrop"].location = (0, 0, -3.4)
    g = dbomb.Bomb(name="Whole"); g.ob.location = (INTRO_X, 0, INTRO_Z[0]); c = dbomb.Bomb(name="Cut", cut=True); c.ob.location = (INTRO_X, 0, INTRO_Z[1])
    sc.render.resolution_x, sc.render.resolution_y = res; os.makedirs(out_dir, exist_ok=True)
    L = C.BLU_L; R = C.BLU_D / 2; zt, zb = INTRO_Z; x0 = INTRO_X; E = C.EXT_L
    pts = {"nose": (x0 + L / 2, 0, zt), "tail": (x0 - L / 2, 0, zt), "top": (x0, 0, zt + R), "bot": (x0, 0, zt - R), "tip": (x0 + L / 2 + E, 0, zt), "ext": (x0 + L / 2 + E * 0.55, 0, zt + 0.05), "fuze": (x0 + L / 2 + E - 0.12, 0, zt - 0.06), "pack": (x0 - L / 2 - 0.2, -0.3, zt + 0.1), "body": (x0 - 0.5, -R, zt),
           "cwall": (x0 + 0.3, 0, zb + R - 0.01), "cfill": (x0 - 0.4, 0, zb - 0.1), "cboost": (x0 + L / 2 - 0.36, 0, zb), "cfuze": (x0 + L / 2 + E - 0.12, 0, zb), "cbot": (x0, 0, zb - R)}
    meta_path = os.path.join(out_dir, "meta.json"); meta = json.load(open(meta_path)) if os.path.exists(meta_path) else {}
    for i in (frames if frames is not None else range(n)):
        u = smoothstep(0.0, 1.0, i / (n - 1)); cam.data.lens = 50; cam.location = (lerp(0.85, 0.35, u), -16.5, 2.0); cam.rotation_euler = (math.radians(90.0), 0, 0)
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
    tl = dict(T_EXIT=C.T_EXIT, V_EXIT=C.V_EXIT, T_SEP=C.T_SEP, T_STAB=list(C.T_STAB), TAU_HIT=C.TAU_HIT, T_BURST=C.T_BURST, THROW=C.THROW, V_AC=C.V_AC, V_HIT=C.V_HIT, DIVE=C.DIVE, H_REL=C.H_REL, HOB=C.HOB, STAB_D=C.STAB_D,
              R_LZ=C.R_LZ, R_BARE=C.R_BARE, R_LEAN=C.R_LEAN, STRIKE=list(STRIKE), CUT=list(CUT), REL_REAL=REL_REAL, ODT=ODT, SDT=SDT, FRONT=[[r, float(C.t_front(r))] for r in range(0, 301, 5)], fps=FPS)
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
        proj = lambda p: (lambda v: [float(v.x), float(1 - v.y), float(v.z)])(world_to_camera_view(sc, st.cam, Vector(p)))
        m = dict(t=float(t), td=float(t), sim=int(sf), anchors={k: proj(p) for k, p in info.get("anchors", {}).items()})
        m.update(info.get("extra", {}))
        meta[str(i)] = m
        sc.render.filepath = fp
        bpy.ops.render.render(write_still=True)
        print("FRAME %s %d t=%.4f sim=%d %.1fs" % (a.shot, i, t, sf, time.time() - t0)); sys.stdout.flush()
        json.dump(meta, open(meta_path, "w"))
    sys.stdout.flush(); os._exit(0)

if __name__ == "__main__":
    main()
