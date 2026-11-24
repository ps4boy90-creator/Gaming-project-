"""Shot definitions and frame renderer for the B-1B / BLU-109 segment.

  python3 pshots.py <shot> <out_dir> [--sim <sim_root>] [--res 1280x720] [--spp N] [--frames a-b | i,j,k]

Shots and their sets:
  card, intro          studio      the aircraft; the bomb whole and cut open
  approach, bay        air         the B-1B at release height; the bay opens and one bomb is ejected
  fall, strike, after  out         the mountainside from outside
  cutaway              sec         the same ground cut along the bomb's path
Clocks: air set, t = seconds after release; out and sec sets, tp = seconds after the nose touches the slope (the charge
fires at tp = 0.060).  Sim frames: "out" 1/60 s each from tp = 0, "in" 1/240 s each from the burst.
"""
import bpy, sys, os, math, json, time, argparse
HERE = os.path.dirname(os.path.abspath(__file__))
for p in ("grenade-explosion", "rpg7-explosion", "mortar-explosion", "howitzer-explosion", "reaper-hellfire", "tomahawk-sub"):
    sys.path.insert(0, os.path.join(HERE, "..", p))
sys.path.insert(0, HERE)
import numpy as np
from mathutils import Vector, Quaternion
import manta_fix  # noqa: F401
import env, qenv
import shots as gshots
import mshots as ms
from hshots import use_device
from qshots import Plume
from smoke_mat import blast_material
from util import *
import pconst as C, pb1b, pbomb, psite

FPS = C.FPS; SDT = 1.0 / 60.0; IDT = 1.0 / 240.0
D = math.radians
shake = gshots.shake
SET_OF = {"approach": "air", "bay": "air", "fall": "out", "strike": "out", "after": "out", "cutaway": "sec"}
SIM_OF = {"strike": "out", "cutaway": "in"}
N_OF = {"card": 72, "approach": 96, "bay": 152, "intro": 96, "fall": 84, "strike": 144, "cutaway": 328, "after": 96}
JET_Q = Quaternion((0, 1, 0), D(-2.0))                               # two degrees nose-up in the cruise
T_DOORS = (-2.7, -1.3)                                              # the bay doors open
T_TURN = (0.85, 1.5)                                                # the launcher turns the next bomb to the bottom
XF = psite.XF; ZF = C.Z_FLOOR
T_TORN = float(np.interp(C.BLU_L, [0.0, C.S1], [0.0, C.TP[1]]))        # roughly when the tail kit meets the ground (the nose is 2.4 m in)

def bomb_xform(tp):
    """Centre and attitude of the bomb, site coordinates: falling, then going through the ground."""
    if tp < 0:
        p, v = C.fall_state(C.TOF + tp); return p - C.U * C.BLU_L / 2, Quaternion((0, 1, 0), math.atan2(-v[2], v[0]))
    s, _ = C.pen_state(tp); return C.U * (s - C.BLU_L / 2), Quaternion((0, 1, 0), D(C.DIVE))

def rel_xform(st, t):
    """The released bomb as seen from the aircraft (which stays at the origin of the air set)."""
    p, v = C.fall_state(max(t, 0.0)); rel = p - C.jet_pos(max(t, 0.0)); p0 = np.array(JET_Q @ Vector(st.jet.store_local(0)))
    return p0 + rel, Quaternion((0, 1, 0), math.atan2(-v[2], v[0])) @ JET_Q if t > 0 else JET_Q

# ----------------------------------------------------------------------------- scene
class Stage(gshots.Stage):
    def __init__(self, kind, sim_dir=None):
        self.kind = kind; self.dom = None
        if sim_dir and os.path.exists(os.path.join(sim_dir, "sim.blend")):
            bpy.ops.wm.open_mainfile(filepath=os.path.join(sim_dir, "sim.blend"))
            for o in list(bpy.data.objects):
                if o.name.startswith("E_"):
                    bpy.data.objects.remove(o, do_unlink=True)
            self.dom = bpy.data.objects["BlastDomain"]; self.dom.data.materials.clear()
            self.fire0 = 34.0 if kind == "out" else 26.0; bm_ = blast_material(density=7.5 if kind == "out" else 11.0, fire=self.fire0, ambient=0.06); self.dom.data.materials.append(bm_); self.fire_node = bm_.node_tree.nodes[bm_["fire_node"]]
            for nd in bm_.node_tree.nodes:
                if nd.type == 'VECT_MATH' and nd.operation == 'POWER':
                    nd.inputs[1].default_value = (0.72, 0.72, 0.72)
                if nd.type == 'VALTORGB':
                    for el, c in zip(sorted(nd.color_ramp.elements, key=lambda e: e.position), [(0, 0, 0), (0.55, 0.05, 0.0), (0.95, 0.22, 0.02), (1.0, 0.42, 0.07), (1.0, 0.62, 0.22)]):
                        el.color = (*c, 1)
            self.dom.hide_render = True
        else:
            bpy.ops.wm.read_factory_settings(use_empty=True)
        sc = self.sc = bpy.context.scene; sc.render.fps = FPS
        col = self.col = bpy.data.collections.new("ACTION"); sc.collection.children.link(col)
        if kind == "air":
            self.env_col, self.floor = qenv.build_air(sc, C.H_REL)
            self.jet = pb1b.B1B(col); self.jet.root.rotation_quaternion = JET_Q; self.bomb = pbomb.Bomb(col, "Dropped")
            bc = self.jet.bay_c; self.bay_lamps = []
            for dx in (-1.7, 1.7):                                      # a little light in the bay, or it is a black hole under the aircraft
                lo = ms.point_light(col, "BayLamp", (1.0, 0.97, 0.92), 0.4); lo.parent = self.jet.root; lo.location = (bc[0] + dx, 0.0, bc[2] - 0.75); lo.data.energy = 0.0; self.bay_lamps.append(lo)
            ld = bpy.data.lights.new("Bounce", 'AREA'); ld.size = 60.0; ld.energy = 1.4e4; ld.color = (0.95, 0.85, 0.72); lo = bpy.data.objects.new("Bounce", ld); col.objects.link(lo)   # light thrown back up by the desert
            lo.location = (0, 0, -40.0); lo.rotation_euler = (math.pi, 0, 0); ld.use_shadow = False
        else:
            ec = self.env_col = bpy.data.collections.new("ENV"); sc.collection.children.link(ec); env.make_world(sc)
            self.site = psite.Outside(ec) if kind == "out" else psite.Section(ec); self.bomb = pbomb.Bomb(col, "Falling")
            self.bare = pbomb.Bomb(col, "Warhead", part="warhead"); self.kit = pbomb.Bomb(col, "TornKit", part="kit")           # the tail kit and strakes do not follow the warhead into the ground
            if kind == "out":
                self.l_hit = ms.point_light(col, "MouthFlash", (1.0, 0.58, 0.26), 1.2); self.l_hit.location = (XF - 3.0, 0.0, ZF + 1.6)
                self.plumes = []
                for (loc, s) in (((3.6, 0.0, float(psite.ground(3.6, 0.0)) - 2.6), 1.25), ((XF - 0.6, 0.0, ZF - 0.2), 0.62)):
                    pl = Plume(col); pl.ob.location = loc; pl.ob.scale = (s, s, s); pl.fl.hide_render = True; pl.glow.hide_render = True; self.plumes.append(pl)
                    for mt in pl.mats:                                  # dust and smoke from a wrecked room, not an oil fire: thinner, and brown-grey over the hollow
                        f = mt.node_tree.nodes["Fade"]; f.inputs["To Min"].default_value = 0.22 if s > 1 else 0.55; f.inputs["To Max"].default_value = 0.05 if s > 1 else 0.09
                        for nd in mt.node_tree.nodes:
                            if nd.type == 'PRINCIPLED_VOLUME':
                                nd.inputs["Color"].default_value = (0.50, 0.44, 0.37, 1) if s > 1 else (0.10, 0.095, 0.09, 1)
        cd = bpy.data.cameras.new("Cam"); self.cam = bpy.data.objects.new("Cam", cd); sc.collection.objects.link(self.cam); sc.camera = self.cam
        cd.clip_start = 0.05; cd.clip_end = 2.0e6; cd.sensor_width = 36; cd.sensor_fit = 'HORIZONTAL'
        self.cam.rotation_mode = 'QUATERNION'
        self.setup_render()
        ng = sc.compositing_node_group; self.haze_mr = [nd for nd in ng.nodes if nd.bl_idname == "ShaderNodeMapRange"][0]; self.haze0 = 0.62
        # The depth pass comes from single samples, so through smoke it flickers between the smoke and what lies behind; a small blur of the haze amount removes the speckle.
        mix = [nd for nd in ng.nodes if nd.bl_idname == "ShaderNodeMix"][0]
        lk = [l for l in ng.links if l.to_node == mix and l.to_socket.name == "Factor"][0]; src = lk.from_socket; ng.links.remove(lk)
        bl = ng.nodes.new("CompositorNodeBlur"); bl.inputs["Size"].default_value[0] = 6.0; bl.inputs["Size"].default_value[1] = 6.0
        ng.links.new(src, bl.inputs["Image"]); ng.links.new(bl.outputs["Image"], mix.inputs["Factor"])
        for nd in ng.nodes:
            if nd.bl_idname == "ShaderNodeMath" and nd.operation == 'LESS_THAN':
                nd.inputs[1].default_value = 5.0e6
        if kind == "air":                                               # the desert is kilometres away: most of its haze is in its own material
            self.haze_mr.inputs["From Min"].default_value = 3000.0; self.haze_mr.inputs["From Max"].default_value = 90000.0; self.haze0 = 0.22
        else:
            self.haze_mr.inputs["From Min"].default_value = 250.0; self.haze_mr.inputs["From Max"].default_value = 30000.0; self.haze0 = 0.70

    def set_time(self, t, dt_out, opt):
        sc = self.sc; mb = opt.get("motion_blur", True); sc.render.use_motion_blur = mb; k = self.kind
        self.haze_mr.inputs["To Max"].default_value = self.haze0 * opt.get("haze", 1.0)
        if k == "air":
            open_ = smoothstep(T_DOORS[0], T_DOORS[1], t); self.jet.set(C.SWEEP_AFT, open_, -math.pi / 4 * smoothstep(T_TURN[0], T_TURN[1], t), gone=(0,) if t >= 0 else ())
            for lo in self.bay_lamps:
                lo.data.energy = 55.0 * open_; lo.hide_render = open_ < 0.02
            self.bomb.ob.hide_render = t < 0
            self.key3(self.bomb.ob, lambda tt: rel_xform(self, tt), t, dt_out, mb)
            self.floor.location = (-C.V_REL * t, 0.0, 0.0); return
        tp = t; td = tp - C.FUZE_DELAY
        self.key3(self.bomb.ob, bomb_xform, tp, dt_out, mb); self.key3(self.bare.ob, bomb_xform, tp, dt_out, mb)
        self.site.update(tp)
        s_now = C.pen_state(tp)[0]; torn = s_now >= C.BLU_L                # the tail kit has reached the surface
        kq = 1.0 - 0.68 * smoothstep(0.0, 0.004, tp - T_TORN); self.kit.ob.hide_render = not torn or td >= 0
        self.kit.ob.location = tuple(C.U * (C.BLU_L / 2 * kq)); self.kit.ob.rotation_quaternion = Quaternion((0, 1, 0), D(C.DIVE)); self.kit.ob.scale = (kq, 1.5 - 0.5 * kq, 1.5 - 0.5 * kq)
        if k == "out":
            self.bomb.ob.hide_render = torn; self.bare.ob.hide_render = True  # the warhead is under ground from then on
            self.l_hit.data.energy = 2.2e5 * math.exp(-td / 0.05) if 0 <= td < 0.4 else 0.0; self.l_hit.hide_render = self.l_hit.data.energy < 5.0
            for pl in self.plumes:
                pl.update(bool(opt.get("plume", False)), tp); pl.fl.hide_render = True; pl.glow.hide_render = True
        else:
            self.bomb.ob.hide_render = torn; self.bare.ob.hide_render = not torn or td > 0.002   # the warhead alone goes on, until it bursts
        if self.dom is not None:
            self.dom.hide_render = tp < 0 if k == "out" else td < 0
            lo, tau = (0.012, 0.22) if k == "out" else (0.10, 0.45)         # outside, the dust must not go on glowing once the flame at the tunnel mouth is out
            self.fire_node.inputs[1].default_value = self.fire0 * (lo + (1 - lo) * math.exp(-max(td, 0.0) / tau))

# ----------------------------------------------------------------------------- shots: in the air
def shot_approach(n=N_OF["approach"]):
    """The B-1B at release height, wings swept right back, seen from ahead and to its left; the camera drifts aft along it."""
    def frame(st, i):
        t = -9.0 + i / FPS; dt = 1.0 / FPS; st.set_time(t, dt, {}); u = smoothstep(0.0, 1.0, i / (n - 1))
        pos = np.array([lerp(60.0, 34.0, u), lerp(44.0, 56.0, u), lerp(15.0, 9.0, u)]); st.look(pos, (lerp(2.0, -3.0, u), 0.0, 0.5), 42.0)
        return t, dt, dict(samples=40, shutter=0.4, anchors={"jet": (0, 0, 2.0), "nose": (22, 0, 0), "wing": (-6.0, 9.0, 0.3), "nacelle": (-4.0, 4.0, -1.4)})
    return n, frame

def shot_bay(n=N_OF["bay"]):
    """Under the aircraft: the forward bay opens on the rotary launcher, one bomb is ejected and falls away, the launcher turns."""
    def frame(st, i):
        t, dt = (-3.0 + i / FPS, 1.0 / FPS) if i < 65 else (-3.0 + 65 / FPS + (i - 65) / 48.0, 1.0 / 48.0)                    # real time while the doors open, half speed for the release
        st.set_time(t, dt, dict(shutter=0.3)); u = i / (n - 1); bc = np.array(JET_Q @ Vector(st.jet.bay_c))
        p, _ = rel_xform(st, t); follow = smoothstep(0.05, 0.7, t) * (1 - smoothstep(0.8, 1.3, t)); home = bc + np.array([0.2, 0.0, -1.2])
        aim = home + follow * 0.5 * (np.array([p[0], 0.0, max(p[2], bc[2] - 6.0)]) - home)
        pos = bc + np.array([lerp(7.5, 5.5, u), lerp(5.2, 4.4, u), lerp(-9.5, -8.6, u)]); st.look(pos, aim, 27.0)
        return t, dt, dict(samples=48, shutter=0.3, anchors={"bay": tuple(bc + np.array([0, 0, -1.2])), "bomb": tuple(p), "door": tuple(bc + np.array([0.0, 1.9, -1.9]))}, extra=dict(doors=float(smoothstep(T_DOORS[0], T_DOORS[1], t))))
    return n, frame

# ----------------------------------------------------------------------------- shots: the mountainside from outside
def shot_fall(n=N_OF["fall"]):
    """Riding down behind the bomb through its last three and a half seconds: the mountainside coming up."""
    t1 = -0.08; t0 = t1 - (n - 1) / FPS
    def cam_at(st, tp, u):
        p, q = bomb_xform(tp); d = np.array(q @ Vector((1, 0, 0))); up = np.array([0, 0, 1.0]) - d * d[2]; up /= np.linalg.norm(up)
        pos = p - d * lerp(10.5, 7.0, u) + up * lerp(2.6, 1.5, u) + np.array([0, 1.5, 0]); return pos, (Vector(p + d * 14.0) - Vector(pos)).to_track_quat('-Z', 'Y')
    def frame(st, i):
        tp = t0 + i / FPS; dt = 1.0 / FPS; st.set_time(tp, dt, dict(haze=1.0)); u = i / (n - 1); pos, q = cam_at(st, tp, u); st.look(pos, None, 28.0, quat=q)
        st.key3(st.cam, lambda tt: cam_at(st, tt, u), tp, dt, True); p, v = C.fall_state(C.TOF + tp)
        return tp, dt, dict(samples=20, shutter=0.3, anchors={"target": (0, 0, 0)}, extra=dict(alt=float(p[2]), v=float(np.linalg.norm(v)), dive=float(math.degrees(math.atan2(-v[2], v[0])))))
    return n, frame

def _out_clock(i, pre, one):
    """Before the hit and for `one` frames after it, one frame = 1/60 s (2.5x slow); after that two sim frames per frame."""
    if i < pre:
        return 0, -(pre - i) * SDT, SDT
    if i < pre + one:
        sf = i - pre + 1; return sf, (sf - 1) * SDT, SDT
    sf = one + 2 * (i - pre - one + 1); return sf, (sf - 1) * SDT, 2 * SDT

def shot_strike(n=N_OF["strike"]):
    """From across the slope: the bomb goes in, and a sixteenth of a second later the mountain answers."""
    def frame(st, i):
        sf, tp, dt = _out_clock(i, 20, 76); st.set_time(tp, dt, {}); u = i / (n - 1); td = tp - C.FUZE_DELAY
        pos = np.array([-22.0 + 3.0 * u, 78.0 + 4.0 * u, 0.0]); pos[2] = max(float(psite.ground(pos[0], pos[1])) + 4.0, 0.5) + 1.5 * u; tgt = np.array([-3.5, 0.0, -1.0 + 4.0 * smoothstep(0.2, 1.0, u)])
        off, rq = shake(td - 0.15, 2.2); q = st.look(pos + off, tgt, 40.0); st.cam.rotation_quaternion = st.cam.rotation_quaternion @ rq
        return tp, dt, dict(samples=16, sim=sf, shutter=0.25, anchors={"hit": (0, 0, 0), "mouth": (XF, 0, ZF + C.TUN_H + 1.6), "cover": (3.6, 0.0, float(psite.ground(3.6, 0.0)) + 0.6)})
    return n, frame

def shot_after(n=N_OF["after"]):
    """Twenty seconds later: the hollow where the cover fell in, the doors on the apron, smoke from the tunnel and the ground."""
    def cam_at(st, t, u):
        a = D(lerp(118.0, 76.0, u)); r = lerp(58.0, 50.0, u); pos = np.array([-3.0 + r * math.cos(a), r * math.sin(a), lerp(13.0, 19.0, u)]); return pos, (Vector((-2.0, 0.0, -1.0)) - Vector(pos)).to_track_quat('-Z', 'Y')
    def frame(st, i):
        tp = 20.0 + i / FPS; dt = 1.0 / FPS; st.set_time(tp, dt, dict(plume=True, haze=0.8)); u = smoothstep(0.0, 1.0, i / (n - 1)); pos, q = cam_at(st, tp, u); st.look(pos, None, 34.0, quat=q)
        st.key3(st.cam, lambda tt: cam_at(st, tt, u), tp, dt, True)
        return tp, dt, dict(samples=32, shutter=0.35, anchors={"hollow": (3.6, 0.0, float(psite.ground(3.6, 0.0))), "mouth": (XF, 0, ZF + C.TUN_H + 1.0)})
    return n, frame

# ----------------------------------------------------------------------------- shot: the section
CUT_PRE = 16; CUT_PEN = 120; CUT_ONE = 96; CUT_MS = 0.0005

def cut_clock(i):
    """(sim frame, tp, seconds per frame): half a millisecond per frame until the fuze fires, then 1/240 s, then 1/80 s."""
    if i < CUT_PRE + CUT_PEN:
        return 0, (i - CUT_PRE) * CUT_MS, CUT_MS
    j = i - CUT_PRE - CUT_PEN
    sf = j + 1 if j < CUT_ONE else CUT_ONE + 1 + 3 * (j - CUT_ONE); return sf, C.FUZE_DELAY + (sf - 1) * IDT, IDT if j < CUT_ONE else 3 * IDT

def shot_cutaway(n=N_OF["cutaway"]):
    """The ground cut along the bomb's path, the camera square on to the cut: through the cover, the roof, the room and into the floor; then the burst."""
    def frame(st, i):
        sf, tp, dt = cut_clock(i); st.set_time(tp, dt, dict(haze=0.6)); td = tp - C.FUZE_DELAY
        pos = np.array([-0.6, 30.0, -3.2]); off, rq = shake(td - 0.004, 0.9); st.look(pos + off, pos + np.array([0.0, -30.0, 0.0]), 38.0); st.cam.rotation_quaternion = st.cam.rotation_quaternion @ rq
        s, v = C.pen_state(tp)
        return tp, dt, dict(samples=40 if sf == 0 else 28, sim=sf, shutter=0.3, anchors={"o": (0, 0, 0), "ex": (1, 0, 0), "ez": (0, 0, 1)}, extra=dict(s=float(max(s, 0.0)), v=float(v), tp=float(tp)))
    return n, frame

SHOTS = {"approach": shot_approach, "bay": shot_bay, "fall": shot_fall, "strike": shot_strike, "after": shot_after, "cutaway": shot_cutaway}

# ----------------------------------------------------------------------------- studio shots: the aircraft, the bomb
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
    """The aircraft turning slowly on a studio backdrop while its wings swing from 15 to 67.5 degrees (left half of the frame; the panel is added in post)."""
    k = 8.0; sc, cam = _studio(k); sc.cycles.samples = spp or 40
    pivot = bpy.data.objects.new("Pivot", None); sc.collection.objects.link(pivot); pivot.location = (0.2 * k, 0, 2.2 * k)
    J = pb1b.B1B(stores=False); J.root.parent = pivot; J.root.rotation_quaternion = Quaternion((1, 0, 0), D(-34)) @ Quaternion((0, 1, 0), D(-3))
    cam.data.lens = 85; cam.location = (0.0, -27.0 * k, 2.6 * k); cam.rotation_euler = (math.radians(88.9), 0, 0); cam.data.shift_x = 0.25
    sc.render.resolution_x, sc.render.resolution_y = res; sc.render.use_border = True; sc.render.use_crop_to_border = True
    sc.render.border_min_x = 0.0; sc.render.border_max_x = 0.50; sc.render.border_min_y = 0.0; sc.render.border_max_y = 1.0
    os.makedirs(out_dir, exist_ok=True)
    for i in (frames if frames is not None else range(n)):
        u = i / n
        if os.path.exists(os.path.join(out_dir, "f%04d.png" % i)):
            continue
        pivot.rotation_euler = (0, 0, math.radians(-128) + math.radians(14) * math.sin(2 * math.pi * u))
        J.set(lerp(C.SWEEP_FWD, C.SWEEP_AFT, smoothstep(0.12, 0.80, 0.5 - 0.5 * math.cos(2 * math.pi * u))), 0.0, 0.0)
        sc.render.filepath = os.path.join(out_dir, "f%04d.png" % i); t = time.time(); bpy.ops.render.render(write_still=True)
        print("FRAME card %d %.1fs" % (i, time.time() - t)); sys.stdout.flush()

INTRO_X = 0.65; INTRO_Z = (2.75, 1.60)

def render_intro(out_dir, res, spp, frames, n=N_OF["intro"]):
    """The bomb as it is dropped (above) and the warhead alone, cut open along its length (below)."""
    from bpy_extras.object_utils import world_to_camera_view
    sc, cam = _studio(1.0, world=0.24, backdrop=(0.105, 0.11, 0.12)); sc.cycles.samples = spp or 48          # dark, so that the labels read
    bpy.data.objects["Backdrop"].location = (0, 0, -3.4)                                                                                           # the floor out of sight: only the dark wall is behind the bombs
    g = pbomb.Bomb(name="Whole"); g.ob.location = (INTRO_X, 0, INTRO_Z[0]); g.ob.rotation_quaternion = Quaternion((1, 0, 0), D(45))            # fins in an X, as it hangs
    c = pbomb.Bomb(name="Cut", cut=True); c.ob.location = (INTRO_X, 0, INTRO_Z[1])
    sc.render.resolution_x, sc.render.resolution_y = res; os.makedirs(out_dir, exist_ok=True)
    L = C.BLU_L; R = C.BLU_D / 2; zt, zb = INTRO_Z; x0 = INTRO_X
    pts = {"nose": (x0 + L / 2, 0, zt), "tail": (x0 + L / 2 - C.GBU_L, 0, zt), "top": (x0, 0, zt + R), "bot": (x0, 0, zt - R), "kit": (x0 - L / 2 - 0.75, 0, zt + 0.17), "strake": (x0 + 0.30, -0.17, zt - 0.17),
           "cnose": (x0 + L / 2 - 0.20, -R, zb), "ccase": (x0 + 0.3, -0.0, zb + R - C.CASE / 2), "cfill": (x0 - 0.1, 0, zb), "cfuze": (x0 - L / 2 + 0.17, 0, zb), "cn": (x0 + L / 2, 0, zb), "ct": (x0 - L / 2, 0, zb), "cbot": (x0, 0, zb - R)}
    meta_path = os.path.join(out_dir, "meta.json"); meta = json.load(open(meta_path)) if os.path.exists(meta_path) else {}
    for i in (frames if frames is not None else range(n)):
        u = smoothstep(0.0, 1.0, i / (n - 1)); cam.data.lens = 60; cam.location = (lerp(0.55, -0.10, u), -9.6, 2.12); cam.rotation_euler = (math.radians(90.0), 0, 0)
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
        (render_card if a.shot == "card" else render_intro)(a.out, res, a.spp, gshots.parse_frames(a.frames, N_OF[a.shot]) if a.frames else None)
        sys.stdout.flush(); os._exit(0)
    n, frame = SHOTS[a.shot]()
    frames = gshots.parse_frames(a.frames, n)
    st = Stage(SET_OF[a.shot], os.path.join(a.sim, SIM_OF[a.shot]) if (a.sim and a.shot in SIM_OF) else None)
    sc = st.sc; sc.render.resolution_x, sc.render.resolution_y = res
    use_device(sc)
    os.makedirs(a.out, exist_ok=True)
    tl = dict(TOF=C.TOF, THROW=C.THROW, V_REL=C.V_REL, V_HIT=C.V_HIT, DIVE=C.DIVE, H_REL=C.H_REL, FUZE=C.FUZE_DELAY, TP=list(C.TP), S=[0.0, C.S1, C.S2, C.S3, C.S4, C.S_END], VS=[C.V_HIT, C.V1, C.V2, C.V2, C.V3, 0.0],
              U=[float(x) for x in C.U], S_BURST=C.S_BURST, DEPTH=C.DEPTH_BURST, Z=[C.Z_ROOF_TOP, C.Z_CEIL, C.Z_FLOOR], ROOM_X=list(C.ROOM_X), XF=XF, PX=C.PORTAL_X, TABLE=C.TABLE,
              CUT=[CUT_PRE, CUT_PEN, CUT_ONE, CUT_MS], fps=FPS)
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
