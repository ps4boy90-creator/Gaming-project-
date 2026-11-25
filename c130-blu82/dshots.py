"""Shot definitions and frame renderer for the C-130 / BLU-82 segment.

  python3 dshots.py <shot> <out_dir> [--sim <sim_root>] [--res 1280x720] [--spp N] [--frames a-b | i,j,k]

Shots and their sets:
  card, intro                   studio      the bomb on its platform; the bomb with its dimensions
  approach, release             air         the C-130 with ramp and door open; the load pulled out and the bomb let go
  fall, impact, radius, after   out         the forest from above, from a distance and afterwards
Clocks: air set, t = seconds after the load leaves the ramp; out set, td = seconds after the burst (the fuze
extender touches the ground at td = 0).  Sim frames: 1/60 s each from td = 0.
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
import mshots as ms
from hshots import use_device
from smoke_mat import blast_material
from util import *
import dconst as C, dbomb, dherc, djungle

FPS = C.FPS; SDT = 1.0 / 60.0
D = math.radians
shake = gsh.shake
SET_OF = {"approach": "air", "release": "air", "fall": "out", "impact": "out", "radius": "out", "after": "out"}
SIM_OF = {"impact": "out", "radius": "out"}
N_OF = {"card": 72, "approach": 108, "intro": 96, "release": 144, "fall": 84, "impact": 180, "radius": 108, "after": 108}
T_OPEN = (-8.6, -6.6)                                                 # ramp and door open on the run-in
T_STREAM = (-6.2, -5.2)                                               # the extraction parachute is streamed (in service: 30 seconds before release)
X0B = dbomb.X0; EXT = C.EXT
EDGE = np.array([dherc.X0 - dherc.RAMP[1], 0.0, dherc.FLOOR_Z + dbomb.PLAT[2] + dbomb.CRADLE_H + dbomb.R])       # the bomb's middle as it crosses the edge of the ramp, aircraft frame
LINE_EXT = 18.0; LINE_STAB = 7.0                                      # lines from the load to where each parachute's own lines meet (estimates)

def nose_pitch(t):
    """Angle of the nose below the line of flight (radians, 0 = pointing forward, pi = pointing aft).  The bomb rides
    out nose aft; its parachute swings it round, tail to the wind, and then it follows its own path down."""
    if t <= 0:
        return math.pi
    p, v = C.fall_state(t); pv = math.atan2(-v[2], v[0]); return pv + (math.pi - pv) * (1.0 - smoothstep(0.5, 3.0, t))

def load_rel(t):
    """The bomb's middle and its attitude relative to the aircraft (which stays at the origin of the air set)."""
    if t <= 0:
        run = 0.5 * C.A_EXT * max(t + C.T_EXIT, 0.0) ** 2; return EDGE + np.array([C.HOLD_RUN - run, 0.0, 0.0]), Quaternion((0, 1, 0), math.pi)
    p, v = C.fall_state(t); return EDGE + (p - C.plane_pos(t)), Quaternion((0, 1, 0), nose_pitch(t))

def plat_rel(t):
    """Cradle and platform: under the bomb until it is pulled off them, then falling away on the extraction parachute."""
    if t <= C.T_SEP:
        return load_rel(t)
    p, v = C.plat_state(t); return EDGE + (p - C.plane_pos(t)) + np.array([0.0, 0.0, -0.4]), Quaternion((0, 1, 0), math.pi + 0.9 * (t - C.T_SEP)) @ Quaternion((1, 0, 0), 0.35 * (t - C.T_SEP))

def bomb_site(td):
    """Middle of the bomb and its attitude in site coordinates, falling (td < 0)."""
    t = C.T_FALL + td; p, v = C.fall_state(t); d = v / np.linalg.norm(v); return p - d * (X0B + EXT), Quaternion((0, 1, 0), math.atan2(-v[2], v[0]))

def build_air(sc, alt):
    """The forest from 6,000 ft: the far canopy's surface out to the horizon."""
    col = bpy.data.collections.new("ENV"); sc.collection.children.link(col); env.make_world(sc)
    na = 200; rr = np.concatenate([[0.0], np.geomspace(60.0, 9.0e5, 110)]); a = np.linspace(0, 2 * np.pi, na, endpoint=False); A, Rr = np.meshgrid(a, rr, indexing="ij"); X, Y = Rr * np.cos(A), Rr * np.sin(A)
    Z = -alt + djungle.CAN_H + djungle.terrain(X, Y) * np.clip((9000.0 - Rr) / 7000.0, 0, 1) + 9.0 * (fbm(X / 16.0, Y / 16.0, 7, 4) - 0.3) * np.clip((6000.0 - Rr) / 5000.0, 0, 1)
    return col, new_obj("CanopyFloor", new_mesh("canopy_floor", np.stack([X, Y, Z], -1).reshape(-1, 3), [grid_faces(na, len(rr), wrap_u=True)]), col, djungle.canopy_mat())

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
            self.fire0 = 60.0; bm_ = blast_material(density=3.2, fire=self.fire0, ambient=0.10); self.dom.data.materials.append(bm_); self.fire_node = bm_.node_tree.nodes[bm_["fire_node"]]
            self.dom.hide_render = True
        else:
            bpy.ops.wm.read_factory_settings(use_empty=True)
        sc = self.sc = bpy.context.scene; sc.render.fps = FPS
        col = self.col = bpy.data.collections.new("ACTION"); sc.collection.children.link(col)
        if kind == "air":
            self.env_col, self.floor = build_air(sc, C.H_REL)
            self.car = dherc.Hercules(col); self.bomb = dbomb.Bomb(col, "Load")
            self.c_ext = dbomb.Chute(col, "chute_ext", C.D_EXT, LINE_EXT, gores=20, rings=5); self.c_stab = dbomb.Chute(col, "chute_stab", C.D_STAB, LINE_STAB, gores=24, rings=7)
        else:
            ec = self.env_col = bpy.data.collections.new("ENV"); sc.collection.children.link(ec)
            self.site = djungle.Jungle(sc, ec)
            self.bomb = dbomb.Bomb(col, "Falling", platform=False); self.c_stab = dbomb.Chute(col, "chute_stab", C.D_STAB, LINE_STAB, gores=24, rings=7)
            self.l_hit = ms.point_light(col, "BurstFlash", (1.0, 0.86, 0.66), 8.0); self.l_hit.location = (0.0, 0.0, 14.0)
        cd = bpy.data.cameras.new("Cam"); self.cam = bpy.data.objects.new("Cam", cd); sc.collection.objects.link(self.cam); sc.camera = self.cam
        cd.clip_start = 0.05; cd.clip_end = 2.0e6; cd.sensor_width = 36; cd.sensor_fit = 'HORIZONTAL'
        self.cam.rotation_mode = 'QUATERNION'
        self.setup_render()
        ng = sc.compositing_node_group; self.haze_mr = [nd for nd in ng.nodes if nd.bl_idname == "ShaderNodeMapRange"][0]
        mix = [nd for nd in ng.nodes if nd.bl_idname == "ShaderNodeMix"][0]                                  # a small blur of the haze amount removes the speckle of a single-sample depth pass
        lk = [l for l in ng.links if l.to_node == mix and l.to_socket.name == "Factor"][0]; src = lk.from_socket; ng.links.remove(lk)
        bl = ng.nodes.new("CompositorNodeBlur"); bl.inputs["Size"].default_value[0] = 6.0; bl.inputs["Size"].default_value[1] = 6.0
        ng.links.new(src, bl.inputs["Image"]); ng.links.new(bl.outputs["Image"], mix.inputs["Factor"])
        for nd in ng.nodes:
            if nd.bl_idname == "ShaderNodeMath" and nd.operation == 'LESS_THAN':
                nd.inputs[1].default_value = 5.0e6
        if kind == "air":
            self.haze_mr.inputs["From Min"].default_value = 1500.0; self.haze_mr.inputs["From Max"].default_value = 60000.0; self.haze0 = 0.55
        else:
            self.haze_mr.inputs["From Min"].default_value = 250.0; self.haze_mr.inputs["From Max"].default_value = 20000.0; self.haze0 = 0.72

    def set_time(self, t, dt_out, opt):
        sc = self.sc; mb = opt.get("motion_blur", True); sc.render.use_motion_blur = mb
        self.haze_mr.inputs["To Max"].default_value = self.haze0 * opt.get("haze", 1.0)
        if self.kind == "air":
            self.car.set(open_=smoothstep(T_OPEN[0], T_OPEN[1], t)); self.car.spin_props(sc, t, dt_out, mb)
            self.key3(self.bomb.root, load_rel, t, dt_out, mb); self.key3(self.bomb.platform, plat_rel, t, dt_out, mb)
            pp, pq = plat_rel(t); aft = np.array(pq @ Vector((1.0, 0, 0))) * (dbomb.PLAT[0] / 2)                 # the platform's rear edge (the load rides nose aft)
            if t <= C.T_SEP:
                dirn = np.array([-1.0, 0.0, -0.06])
            else:
                p, v = C.plat_state(t); dirn = -np.array([v[0], 0.0, v[2]]) / np.linalg.norm(v)
            self.c_ext.place(tuple(pp + aft + np.array([0, 0, -dbomb.R - 0.3])), tuple(dirn), smoothstep(T_STREAM[0], T_STREAM[1], t)); self.c_ext.hide(bool(t < T_STREAM[0]))
            bp, bq = load_rel(t); tail = bp - np.array(bq @ Vector((1.0, 0, 0))) * (X0B + 0.3)
            if t > 0:
                p, v = C.fall_state(t); wind = -np.array([v[0], 0.0, v[2]]) / np.linalg.norm(v)
            else:
                wind = np.array([-1.0, 0.0, 0.0])
            self.c_stab.place(tuple(tail), tuple(wind), smoothstep(C.T_SEP, C.T_CHUTE + 0.5, t)); self.c_stab.hide(bool(t < C.T_SEP * 0.6))
            self.floor.location = (-C.V_REL * t, 0.0, 0.0); return
        td = t
        if td < 0:
            self.key3(self.bomb.root, bomb_site, td, dt_out, mb); bp, bq = bomb_site(td); n = np.array(bq @ Vector((1.0, 0, 0))); self.c_stab.place(tuple(bp - n * (X0B + 0.3)), tuple(-n), 1.0)
        self.bomb.hide(bool(td >= 0)); self.c_stab.hide(bool(td >= 0))
        self.site.update(td)
        e = 3.0e7 * math.exp(-td / 0.10) if 0.0 <= td < 1.2 else 0.0; self.l_hit.data.energy = e; self.l_hit.hide_render = e < 5.0
        if self.dom is not None:
            self.dom.hide_render = bool(td < 0)
            self.fire_node.inputs[1].default_value = self.fire0 * (0.010 + 0.990 * math.exp(-max(td, 0.0) / 0.55))

# ----------------------------------------------------------------------------- shots: in the air
def shot_approach(n=N_OF["approach"]):
    """The C-130 on its run-in 6,000 ft above the forest: ramp and door open, the extraction parachute streamed behind."""
    def frame(st, i):
        t = -9.0 + i / FPS; dt = 1.0 / FPS; st.set_time(t, dt, {}); u = smoothstep(0.0, 1.0, i / (n - 1))
        pos = np.array([lerp(34.0, -36.0, u), lerp(31.0, 27.0, u), lerp(4.0, -7.0, u)]); st.look(pos, np.array([lerp(3.0, -11.0, u), 0.0, lerp(0.8, -0.8, u)]), lerp(34.0, 40.0, u))
        return t, dt, dict(samples=40, shutter=0.4, anchors={"ramp": tuple(EDGE + np.array([1.5, 0, -1.3])), "chute": tuple(EDGE + np.array([-LINE_EXT - 3.0, 0, -2.5])), "load": tuple(EDGE + np.array([C.HOLD_RUN, 0, 0])), "wing": (dherc.X0 - 12.0, 9.0, 2.3)},
                           extra=dict(open=float(smoothstep(T_OPEN[0], T_OPEN[1], t)), stream=float(smoothstep(T_STREAM[0], T_STREAM[1], t))))
    return n, frame

def shot_release(n=N_OF["release"]):
    """Behind and below the tail, real time: the load runs down the rollers and off the ramp, the bomb is pulled off its
    cradle and swings nose down under its own parachute."""
    def frame(st, i):
        t = -3.1 + i / FPS; dt = 1.0 / FPS; st.set_time(t, dt, dict(shutter=0.3)); u = i / (n - 1); bp, bq = load_rel(t)
        follow = smoothstep(0.1, 2.2, t); p_, v_ = C.fall_state(max(t, 0.0)); wd = -np.array([v_[0], 0.0, v_[2]]) / np.linalg.norm(v_); mid = bp + wd * 8.0 * smoothstep(0.9, 2.6, t)        # later, half-way between the bomb and its parachute
        aim = EDGE + np.array([1.0, 0, -0.6]) + follow * 0.9 * (np.array([mid[0], 0.0, mid[2]]) - EDGE)
        pos = EDGE + np.array([lerp(-26.0, -34.0, u), lerp(17.0, 20.0, u), lerp(-5.0, -11.0, u)]) + follow * 0.35 * (np.array([bp[0], 0.0, bp[2]]) - EDGE); st.look(pos, aim, lerp(34.0, 24.0, smoothstep(0.55, 1.0, u)))
        pp, pq = plat_rel(t)
        return t, dt, dict(samples=44, shutter=0.3, anchors={"bomb": tuple(bp), "plat": tuple(pp), "ramp": tuple(EDGE + np.array([0.5, 0, -1.3]))}, extra=dict(pitch=float(math.degrees(nose_pitch(t)))))
    return n, frame

# ----------------------------------------------------------------------------- shots: the forest
def shot_fall(n=N_OF["fall"]):
    """Beside the bomb through its last three and a half seconds: nose down under the parachute, the canopy coming up."""
    t1 = -0.50; t0 = t1 - (n - 1) / FPS
    def cam_at(st, td, u):
        p, q = bomb_site(td); d = np.array(q @ Vector((1, 0, 0))); side = np.array([0.0, 1.0, 0.0]); fw = np.cross(side, d)
        pos = p - d * lerp(19.0, 15.0, u) + side * lerp(11.0, 8.5, u) + fw * 5.0; return pos, (Vector(p + d * 9.0 - side * 1.0) - Vector(pos)).to_track_quat('-Z', 'Y')
    def frame(st, i):
        td = t0 + i / FPS; dt = 1.0 / FPS; st.set_time(td, dt, dict(haze=1.0)); u = i / (n - 1); pos, q = cam_at(st, td, u); st.look(pos, None, 26.0, quat=q)
        st.key3(st.cam, lambda tt: cam_at(st, tt, u), td, dt, True); p, v = C.fall_state(C.T_FALL + td); bp, bq = bomb_site(td)
        return td, dt, dict(samples=20, shutter=0.3, anchors={"target": (0, 0, 0), "bomb": tuple(bp), "probe": tuple(p)}, extra=dict(alt=float(p[2]), v=float(np.linalg.norm(v))))
    return n, frame

def _out_clock(i, pre, one):
    """Before the burst and for `one` frames after it, one frame = 1/60 s (2.5x slow); after that three sim frames per frame."""
    if i < pre:
        return 0, -(pre - i) * SDT, SDT
    if i < pre + one:
        sf = i - pre + 1; return sf, (sf - 1) * SDT, SDT
    sf = one + 3 * (i - pre - one + 1); return sf, (sf - 1) * SDT, 3 * SDT

def shot_impact(n=N_OF["impact"]):
    """From above the canopy 400 m off: the bomb comes down into the trees and bursts; the forest round it goes down."""
    def frame(st, i):
        sf, td, dt = _out_clock(i, 20, 100); st.set_time(td, dt, {}); u = i / (n - 1)
        pos = np.array([-330.0 + 10.0 * u, -235.0 - 10.0 * u, 74.0 + 4.0 * u]); tgt = np.array([0.0, 0.0, 30.0 + 62.0 * smoothstep(0.25, 0.95, u)])
        off, rq = shake(td - 1.15, 3.0); st.look(pos + off, tgt, lerp(46.0, 24.0, smoothstep(0.2, 0.7, u))); st.cam.rotation_quaternion = st.cam.rotation_quaternion @ rq
        return td, dt, dict(samples=16, sim=sf, shutter=0.25, anchors={"hit": (0, 0, 1.0), "top": (0, 0, 100.0), "edge": (C.R_CLEAR, 0.0, 12.0)})
    return n, frame

def _circle(r, c=(0.0, 0.0), z=0.5):
    return [(c[0] + r * math.cos(a), c[1] + r * math.sin(a), z + float(djungle.terrain(c[0] + r * math.cos(a), c[1] + r * math.sin(a)))) for a in np.linspace(0, 2 * np.pi, 97)]

def shot_radius(n=N_OF["radius"]):
    """From the air: the burst and its circles (the ground cleared, the foliage burnt off, 5 psi), and a helicopter's rotor for scale."""
    def frame(st, i):
        sf = 1 + int(1.7 * i); td = (sf - 1) * SDT; dt = 1.7 * SDT; st.set_time(td, dt, dict(haze=0.5)); u = i / (n - 1)
        pos = np.array([-55.0 + 5 * u, -225.0, 250.0 + 6 * u]); st.look(pos, np.array([3.0, -22.0, 8.0]), 30.0)
        at = lambda r, a: (r * math.cos(D(a)), r * math.sin(D(a)), 0.5 + float(djungle.terrain(r * math.cos(D(a)), r * math.sin(D(a)))))
        an = {"clear": at(C.R_CLEAR, -58), "strip": at(C.R_STRIP, -30), "blast": at(C.R_BLAST, 52), "rotor": at(C.ROTOR / 2 + 12.0, 150)}
        paths = {"clear": _circle(C.R_CLEAR), "strip": _circle(C.R_STRIP), "blast": _circle(C.R_BLAST), "rotor": _circle(C.ROTOR / 2, (-12.0 * math.cos(D(30)), 12.0 * math.sin(D(30))))}
        return td, dt, dict(samples=12, sim=sf, shutter=0.25, anchors=an, paths=paths)
    return n, frame

def shot_after(n=N_OF["after"]):
    """A minute later, circling low: bare ground, stumps, trunks thrown outwards, the forest standing round it."""
    def cam_at(st, t, u):
        a = D(lerp(228.0, 290.0, u)); r = lerp(150.0, 120.0, u); pos = np.array([r * math.cos(a), r * math.sin(a), lerp(120.0, 96.0, u)]); return pos, (Vector((0.0, 4.0, 0.0)) - Vector(pos)).to_track_quat('-Z', 'Y')
    def frame(st, i):
        td = 60.0 + i / FPS; dt = 1.0 / FPS; st.set_time(td, dt, dict(haze=0.8)); u = smoothstep(0.0, 1.0, i / (n - 1)); pos, q = cam_at(st, td, u); st.look(pos, None, 30.0, quat=q)
        st.key3(st.cam, lambda tt: cam_at(st, tt, u), td, dt, True); a0 = D(15.0)
        return td, dt, dict(samples=32, shutter=0.35, anchors={"a": (C.R_CLEAR * math.cos(a0), C.R_CLEAR * math.sin(a0), 1.5), "b": (-C.R_CLEAR * math.cos(a0), -C.R_CLEAR * math.sin(a0), 1.5), "mid": (0, 0, 0.5), "rim": (0.0, C.R_STRIP * 0.85, 18.0)},
                            paths={"rotor": _circle(C.ROTOR / 2, (-10.0, 6.0), 0.8)})
    return n, frame

SHOTS = {"approach": shot_approach, "release": shot_release, "fall": shot_fall, "impact": shot_impact, "radius": shot_radius, "after": shot_after}

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
    area((6.0, -8.0, 9.0), 7.0, 2600, (1.0, 0.96, 0.9)); area((-8.0, -5.0, 3.5), 8.0, 900, (0.8, 0.9, 1.0)); area((-2.5, 7.0, 7.0), 6.0, 2200)
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); sc.collection.objects.link(cam); sc.camera = cam; cam.data.clip_start = 0.05; cam.data.clip_end = 6000; cam.data.sensor_width = 36
    sc.render.engine = 'CYCLES'; c = sc.cycles; c.use_denoising = True; c.denoising_quality = 'HIGH'; c.max_bounces = 6
    use_device(sc); sc.view_settings.view_transform = 'AgX'; sc.view_settings.look = 'AgX - Medium High Contrast'
    sc.render.image_settings.file_format = 'PNG'; sc.render.use_persistent_data = True
    return sc, cam

def render_card(out_dir, res, spp, frames, n=N_OF["card"]):
    """The bomb on its cradle and platform, turning slowly (left half of the frame; the panel is added in post)."""
    sc, cam = _studio(1.0); sc.cycles.samples = spp or 40
    pivot = bpy.data.objects.new("Pivot", None); sc.collection.objects.link(pivot); zc = dbomb.R + dbomb.CRADLE_H + dbomb.PLAT[2]; pivot.location = (0.0, 0, zc)
    B = dbomb.Bomb(name="Card"); B.root.parent = pivot; B.platform.parent = pivot
    cam.data.lens = 85; cam.location = (0.0, -27.0, 3.3); cam.rotation_euler = (math.radians(86.5), 0, 0); cam.data.shift_x = 0.25
    sc.render.resolution_x, sc.render.resolution_y = res; sc.render.use_border = True; sc.render.use_crop_to_border = True
    sc.render.border_min_x = 0.0; sc.render.border_max_x = 0.50; sc.render.border_min_y = 0.0; sc.render.border_max_y = 1.0
    os.makedirs(out_dir, exist_ok=True)
    for i in (frames if frames is not None else range(n)):
        u = i / n
        if os.path.exists(os.path.join(out_dir, "f%04d.png" % i)):
            continue
        pivot.rotation_euler = (0, 0, math.radians(-62) + math.radians(20) * math.sin(2 * math.pi * u))
        sc.render.filepath = os.path.join(out_dir, "f%04d.png" % i); t = time.time(); bpy.ops.render.render(write_still=True)
        print("FRAME card %d %.1fs" % (i, time.time() - t)); sys.stdout.flush()

INTRO_Z = 2.3

def render_intro(out_dir, res, spp, frames, n=N_OF["intro"]):
    """The bomb alone, side on, with its fuze extender; a jeep behind it for scale."""
    from bpy_extras.object_utils import world_to_camera_view
    sc, cam = _studio(1.0, world=0.24, backdrop=(0.105, 0.11, 0.12)); sc.cycles.samples = spp or 48
    bpy.data.objects["Backdrop"].location = (0, 0, -3.4)
    g = dbomb.Bomb(name="Whole", platform=False); g.root.location = (-0.2, 0, INTRO_Z)
    jp = bpy.data.objects.new("Jeep", dbomb.jeep_mesh()); sc.collection.objects.link(jp); jp.data.materials.append(bpy.data.materials.get("BombPaint")); jp.location = (-0.4, 2.4, -0.45)
    sc.render.resolution_x, sc.render.resolution_y = res; os.makedirs(out_dir, exist_ok=True)
    R = dbomb.R; zt = INTRO_Z; X = lambda x: -0.2 + x
    pts = {"nose": (X(X0B), 0, zt), "tail": (X(-X0B), 0, zt), "tip": (X(X0B + EXT), 0, zt), "top": (X(0.0), 0, zt + R), "bot": (X(0.0), 0, zt - R), "case": (X(-0.6), -R, zt - 0.25), "band": (X(X0B - dbomb.CL * 0.24), -0.2, zt + 0.22),
           "ext": (X(X0B + EXT * 0.55), -0.05, zt), "pack": (X(-X0B - 0.2), -0.2, zt + 0.1), "jeep": (-1.6, 2.4, 1.25)}
    meta_path = os.path.join(out_dir, "meta.json"); meta = json.load(open(meta_path)) if os.path.exists(meta_path) else {}
    for i in (frames if frames is not None else range(n)):
        u = smoothstep(0.0, 1.0, i / (n - 1)); cam.data.lens = 50; cam.location = (lerp(0.55, 0.05, u), -13.6, 2.05); cam.rotation_euler = (math.radians(90.0), 0, 0)
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
    sc.render.use_persistent_data = os.environ.get("PERSIST", "0") == "1"
    if os.environ.get("VOL_STEP"):                                  # coarser volume steps for a quick draft on a CPU
        sc.cycles.volume_step_rate = float(os.environ["VOL_STEP"]); sc.cycles.volume_max_steps = 96
    os.makedirs(a.out, exist_ok=True)
    tl = dict(BOMB="blu82", NAME="BLU-82/B", TOF=C.TOF, T_FALL=C.T_FALL, T_EXIT=C.T_EXIT, V_OUT=C.V_OUT, THROW=C.THROW, V_REL=C.V_REL, V_HIT=C.V_HIT, DIVE=C.DIVE, H_REL=C.H_REL, FUZE=0.0, HOB=C.HOB, EXT=C.EXT,
              R_CLEAR=C.R_CLEAR, R_DOWN=C.R_DOWN, R_STRIP=C.R_STRIP, R_BLAST=C.R_BLAST, R_FIRE=C.R_FIRE, ROTOR=C.ROTOR, T_SEP=C.T_SEP, T_CHUTE=C.T_CHUTE, T_OPEN=list(T_OPEN), T_STREAM=list(T_STREAM), fps=FPS)
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
        if "paths" in info:
            m["paths"] = {k: [proj(p)[:2] for p in pts] for k, pts in info["paths"].items()}
        meta[str(i)] = m
        sc.render.filepath = fp
        bpy.ops.render.render(write_still=True)
        print("FRAME %s %d t=%.4f sim=%d %.1fs" % (a.shot, i, t, sf, time.time() - t0)); sys.stdout.flush()
        json.dump(meta, open(meta_path, "w"))
    sys.stdout.flush(); os._exit(0)

if __name__ == "__main__":
    main()
