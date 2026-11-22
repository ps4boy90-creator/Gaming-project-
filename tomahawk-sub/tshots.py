"""Shot definitions and frame renderer for the submarine-launched Tomahawk segment.

  python3 tshots.py <shot> <out_dir> [--sim <cache_dir>] [--res 1280x720] [--spp N] [--frames a-b | i,j,k]

Shots and their sets:
  card                         studio
  depth, hatch, eject          deep    under water with the submarine
  broach, wings, boost         sea     the surface and the air above it
  landfall                     coast   low over the sea towards the shore
  cruise                       land    low over desert hills
  terminal, impact, radius, after   target   the factory
Clocks: sea and deep sets, t = seconds after first motion in the tube; target set, td = seconds after the warhead
fires; one sim frame is 1/60 s.
"""
import bpy, sys, os, math, json, time, argparse
HERE = os.path.dirname(os.path.abspath(__file__))
for p in ("grenade-explosion", "rpg7-explosion", "mortar-explosion", "howitzer-explosion", "reaper-hellfire"):
    sys.path.insert(0, os.path.join(HERE, "..", p))
sys.path.insert(0, HERE)
import numpy as np
from mathutils import Vector, Quaternion
import manta_fix  # noqa: F401
import env, htown, qenv
import shots as gshots
import mshots as ms
from hshots import use_device
from qshots import Plume
from smoke_mat import blast_material
from util import *
import tconst as C, ttlam, tsub, tsea, tland, tfac

FPS = C.FPS; SDT = 1.0 / 60.0
D = math.radians
shake = gshots.shake
SET_OF = {"depth": "deep", "hatch": "deep", "eject": "deep", "broach": "sea", "wings": "sea", "boost": "sea", "landfall": "coast", "cruise": "land",
          "terminal": "target", "impact": "target", "radius": "target", "after": "target"}
SIM_SHOTS = ("impact", "radius")
CRUISE_X0 = 1500.0; COAST_X = 5200.0
N_OF = {"card": 72, "depth": 84, "hatch": 60, "eject": 108, "broach": 144, "wings": 60, "boost": 120, "landfall": 72, "cruise": 144, "terminal": 132, "impact": 132, "radius": 96, "after": 120}

# ----------------------------------------------------------------------------- the missile through the launch
def burn(t):
    return 0.0 if t < C.T_IGN else min(1.0, (t - C.T_IGN) / 0.08) * (1.0 if t < C.T_BURNOUT - 0.4 else max(0.0, (C.T_BURNOUT - t) / 0.4))

def launch_config(t):
    return dict(wings=smoothstep(C.T_WINGS, C.T_WINGS + 0.6, t), fins=smoothstep(C.T_SHROUD, C.T_SHROUD + C.FIN_TIME, t), booster=t < C.T_JETT, shroud=t < C.T_SHROUD,
                plugs=t < C.T_SHROUD, cover=t < C.T_WINGS, burn=burn(t))

def pitch_quat(v):
    """Nose along v (which lies in the X-Z plane); the missile's top stays towards the sky once it is over on its side of the arc."""
    return Quaternion((0, 1, 0), -math.atan2(v[2], v[0]))

def launch_xform(t):
    p, v, _ = C.launch_state(t); return p, pitch_quat(v)

FREE = {"shroudA": (C.T_SHROUD, (0, 0, 7.0), (0.3, 1, 0.1), 5.0), "shroudB": (C.T_SHROUD, (0, 0, -7.0), (0.2, -1, 0.3), -6.0), "plugL": (C.T_SHROUD, (0, 9.0, -2.0), (1, 0.2, 0.4), 9.0),
        "plugR": (C.T_SHROUD, (0, -9.0, -2.0), (1, -0.3, 0.2), -8.0), "cover": (C.T_WINGS, (-3.0, 0, -8.0), (0.2, 1, 0), 7.0), "booster": (C.T_JETT, (-9.0, 0, -1.5), (0.1, 1, 0.05), 0.9)}

def free_xform(name, t):
    """A part that has been thrown off: it keeps the missile's speed for a moment, is pushed away, slows in the air and falls."""
    t0, kick, axis, spin = FREE[name]; p0, v0, _ = C.launch_state(t0); q0 = pitch_quat(v0); tau = max(t - t0, 0.0); k = 0.9 if name != "booster" else 0.25
    v = v0 + np.array(q0 @ Vector(kick)); p = p0 + v * (1 - math.exp(-k * tau)) / k + np.array([0, 0, -0.5 * C.G * tau * tau * (0.6 if name != "booster" else 0.9)])
    return p, Quaternion(Vector(axis).normalized(), spin * tau) @ q0

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
            self.fire0 = 36.0; bm_ = blast_material(density=7.5, fire=self.fire0, ambient=0.06); self.dom.data.materials.append(bm_); self.fire_node = bm_.node_tree.nodes[bm_["fire_node"]]
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
        self.tlam = ttlam.Tomahawk(col)
        if kind == "deep":
            self.env_col, self.wave = tsea.build_underwater(sc); self.sub = tsub.Submarine(col); self.fx = tsea.Launch(col, True)
        elif kind == "sea":
            self.env_col, self.sea, self.wave = tsea.build_sea(sc); self.fx = tsea.Launch(col, False)
        elif kind == "coast":
            self.env_col, self.sea, self.wave = tsea.build_sea(sc); tland.build_coast(sc, COAST_X)
        elif kind == "land":
            self.env_col = tland.build_land(sc, CRUISE_X0, CRUISE_X0 + C.V_CRUISE * N_OF["cruise"] / FPS)
        else:
            rng = np.random.default_rng(11); np.random.seed(11); ec = self.env_col = bpy.data.collections.new("ENV"); sc.collection.children.link(ec)
            env.make_world(sc); self.ground = env.build_ground(ec); htown.sandy(self.ground); env.build_stones(ec, rng, -200.0); htown.desert_hills(ec, rng, 2.4)
            self.blast_node = self.ground.data.materials[0].node_tree.nodes["Blast"]
            na = 120; rr = np.geomspace(2500.0, 9.0e5, 40); a = np.linspace(0, 2 * np.pi, na, endpoint=False); A, Rr = np.meshgrid(a, rr, indexing="ij")           # the same plain out to the horizon, for the view from the dive
            new_obj("GroundHuge", new_mesh("ground_huge", np.stack([Rr * np.cos(A), Rr * np.sin(A), np.full_like(A, -0.03)], -1).reshape(-1, 3), [grid_faces(na, len(rr), wrap_u=True)]), ec, self.ground.data.materials[0])
            for nm in ("GroundFar", "GroundHuge"):                         # one texture space for both, so the sand's pattern runs on unbroken across the join
                me_ = bpy.data.objects[nm].data; me_.use_auto_texspace = False; me_.texspace_location = (0.0, 0.0, -0.03); me_.texspace_size = (2600.0, 2600.0, 1.0)
            self.fac = tfac.Factory(col)
            self.frags = ms.FragField(col, n=300, rmax=C.R_BLAST); self.ejecta = ms.Ejecta(col, scale=1.6 * C.K)
            self.l_hit = ms.point_light(col, "HitFlash", (1.0, 0.58, 0.26), 1.5); self.l_hit.location = (0.0, -1.0, C.BURST_Z + 3.0)
            self.plume = Plume(col)
            for o in (self.plume.ob, self.plume.fl):
                o.location = (1.0, 0.5, -0.5)
            self.plume.ob.scale = (0.95, 0.95, 1.0); self.plume.glow.location = (1.0, 0.5, 1.5)
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
        if kind in ("sea", "coast", "land"):
            self.haze_mr.inputs["From Min"].default_value = 400.0; self.haze_mr.inputs["From Max"].default_value = 60000.0; self.haze0 = 0.80
            for nd in ng.nodes:
                if nd.bl_idname == "ShaderNodeMath" and nd.operation == 'LESS_THAN':
                    nd.inputs[1].default_value = 5.0e6
        if kind == "deep":
            self.haze0 = 0.0; sc.cycles.volume_bounces = 1

    def place(self, fn, t, dt, cfg):
        """Missile at fn(t) -> (position, quaternion), in the given configuration."""
        self.tlam.hide(False); self.tlam.config(**cfg); self.key3(self.tlam.root, fn, t, dt, self.sc.render.use_motion_blur)

    def set_time(self, t, dt_out, opt):
        sc = self.sc; mb = opt.get("motion_blur", True); sc.render.use_motion_blur = mb; k = self.kind
        self.haze_mr.inputs["To Max"].default_value = self.haze0 * opt.get("haze", 1.0)
        if k in ("deep", "sea"):
            self.wave.outputs[0].default_value = t
            self.place(launch_xform, t, dt_out, launch_config(t))
            for name, ob in self.tlam.free.items():
                t0 = FREE[name][0]; ob.hide_render = not (t0 <= t < t0 + 7.0)
                if not ob.hide_render:
                    self.key3(ob, lambda tt, name=name: free_xform(name, tt), t, dt_out, mb)
            self.fx.update(t)
            if k == "deep":
                self.tlam.glow.data.energy *= 0.02                          # water swallows the light of the flame within metres
                self.key3(self.sub.root, lambda tt: (np.array([C.sub_bow_x(tt), -C.HATCH_Y, C.SUB_AXIS_Z]), Quaternion()), t, dt_out, mb)
                self.sub.set(door=smoothstep(-5.2, -3.6, t), prop_angle=-2.2 * t)
                if t < 0:
                    self.tlam.hide(True)                                    # inside its capsule until it moves
            return
        if k == "coast":
            self.wave.outputs[0].default_value = t
            self.place(lambda tt: (np.array([C.V_CRUISE * tt, 0.0, 30.0 + 1.2 * math.sin(0.8 * tt)]), Quaternion((0, 1, 0), D(-1.5))), t, dt_out, {}); return
        if k == "land":
            self.place(lambda tt: (lambda p, v: (p, pitch_quat(v) @ Quaternion((0, 1, 0), D(-2.0))))(*tland.cruise_state(tt, CRUISE_X0)), t, dt_out, {}); return
        # ---- target set: t is td here
        td = t; hit = td >= 0
        self.place(lambda tt: (lambda p, v: (p, pitch_quat(v)))(*C.term_state(tt)), td, dt_out, {})
        if td > C.T_ROOF * 0.4:
            self.tlam.hide(True)                                        # it has gone through the roof
        self.fac.update(td); self.blast_node.outputs[0].default_value = 0.0
        self.frags.update(td if opt.get("frags", False) else -1.0, opt.get("frag_gain", 1.0)); self.ejecta.update(td if td < 7 else -1.0, 0.5 * dt_out)
        self.l_hit.data.energy = 1.1e6 * C.K ** 2 * math.exp(-td / 0.03) if 0 <= td < 0.3 else 0.0; self.l_hit.hide_render = self.l_hit.data.energy < 5.0
        self.plume.update(bool(opt.get("plume", False)), td); self.plume.fl.hide_render = not opt.get("flames", False); self.plume.glow.hide_render = not opt.get("flames", False)
        if self.dom is not None:
            self.dom.hide_render = not hit
            self.fire_node.inputs[1].default_value = self.fire0 * (0.10 + 0.90 * math.exp(-max(td, 0.0) / 0.24))

# ----------------------------------------------------------------------------- shots: under water
def _hatch(t):
    return np.array([C.sub_bow_x(t) - C.HATCH_X, 0.0, C.HATCH_Z])

def shot_depth(n=N_OF["depth"]):
    """The submarine at launch depth, seen from off its port bow: it slides past under the bright surface."""
    def frame(st, i):
        t = -9.5 + i / FPS; dt = 1.0 / FPS; st.set_time(t, dt, {}); u = i / (n - 1); h = _hatch(-7.75)
        pos = h + np.array([34.0 - 6.0 * u, 46.0 - 4.0 * u, -11.0 + 2.5 * u]); st.look(pos, h + np.array([-30.0 + 4.0 * u, 0.0, -4.0]), 30.0)
        return t, dt, dict(samples=40, shutter=0.4, anchors={"sail": tuple(h + np.array([C.HATCH_X - 31.0, -C.HATCH_Y, 8.0])), "tubes": tuple(_hatch(t))})
    return n, frame

def shot_hatch(n=N_OF["hatch"]):
    """Close over the bow: the twelve launch-tube hatches, and one of them swinging open."""
    def frame(st, i):
        t = -5.6 + i / FPS; dt = 1.0 / FPS; st.set_time(t, dt, {}); u = i / (n - 1); h = _hatch(t)
        pos = h + np.array([8.5 - 1.5 * u, 6.0 + 1.0 * u, 4.6 - 0.6 * u]); st.look(pos, h + np.array([-0.6, -0.2, 0.2]), 32.0)
        st.key3(st.cam, lambda tt: (_hatch(tt) + np.array([8.5 - 1.5 * u, 6.0 + 1.0 * u, 4.6 - 0.6 * u]), st.cam.rotation_quaternion.copy()), t, dt, True)
        return t, dt, dict(samples=40, shutter=0.4, anchors={"hatch": tuple(h)})
    return n, frame

def shot_eject(n=N_OF["eject"]):
    """Slow motion: gas throws the missile out of its tube, the booster lights under water, and it climbs to the surface."""
    t0, t1 = -0.22, C.T_CLEAR + 0.12
    def frame(st, i):
        dt = (t1 - t0) / (n - 1); t = t0 + i * dt; st.set_time(t, dt, dict(shutter=0.25)); u = i / (n - 1); h = _hatch(0.3)
        p = C.launch_state(max(t, 0.0))[0]; zt = min(p[2], -1.5)
        pos = h + np.array([13.0, 11.0 + 2.0 * u, 2.2 + 1.5 * u]); st.look(pos, np.array([h[0], 0.0, lerp(h[2] + 1.0, 0.5 * (h[2] + zt) + 2.0, smoothstep(0.05, 0.9, u))]), 24.0)
        return t, dt, dict(samples=48, shutter=0.25, anchors={"tlam": tuple(p)})
    return n, frame

# ----------------------------------------------------------------------------- shots: the surface and the boost
def shot_broach(n=N_OF["broach"], slow=60):
    """From a boat's height: the missile bursts out of the sea (half speed), throws off its shrouds, and climbs away on the booster."""
    ta = C.T_BROACH - 0.55
    def clock(i):
        return (ta + i / 48.0, 1.0 / 48.0) if i < slow else (ta + slow / 48.0 + (i - slow) / FPS, 1.0 / FPS)
    def frame(st, i):
        t, dt = clock(i); st.set_time(t, dt, dict(shutter=0.3)); u = i / (n - 1); p = C.launch_state(t)[0]
        zt = max(p[2], 0.0); aim = np.array([p[0] * 0.8, 0.0, 2.0 + 0.62 * zt]); pos = np.array([46.0 + 14.0 * u, 58.0 + 20.0 * u, 2.6 + 1.0 * u])
        st.look(pos, aim, lerp(34.0, 24.0, smoothstep(0.2, 1.0, u)))
        return t, dt, dict(samples=36, shutter=0.3, anchors={"tlam": tuple(p)}, extra=dict(alt=float(p[2]), v=float(C.launch_state(t)[2])))
    return n, frame

def _chase(t, back, side, up):
    p, v, _ = C.launch_state(t); d = v / np.linalg.norm(v); return p - d * back + np.array([0.0, side, up])

def shot_wings(n=N_OF["wings"]):
    """Flying alongside as the speed check passes: the inlet cover drops away and the wings swing out of their slots."""
    t0 = C.T_WINGS - 1.0
    def cam_at(st, t, u):
        p = C.launch_state(t)[0]; pos = _chase(t, lerp(5.0, 2.0, u), lerp(9.5, 8.5, u), lerp(1.0, 2.6, u)); return pos, (Vector(p + np.array([0.6, 0, 0])) - Vector(pos)).to_track_quat('-Z', 'Y')
    def frame(st, i):
        t = t0 + i / FPS; dt = 1.0 / FPS; st.set_time(t, dt, dict(shutter=0.3)); u = i / (n - 1); pos, q = cam_at(st, t, u); st.look(pos, None, 34.0, quat=q)
        st.key3(st.cam, lambda tt: cam_at(st, tt, u), t, dt, True); p, v, s = C.launch_state(t)
        return t, dt, dict(samples=32, shutter=0.3, anchors={"tlam": tuple(p)}, extra=dict(alt=float(p[2]), v=float(s)))
    return n, frame

def shot_boost(n=N_OF["boost"]):
    """The end of the boost: the rocket motor burns out and is dropped, and the turbofan takes over."""
    t0 = C.T_BURNOUT - 1.4
    def cam_at(st, t, u):
        p = C.launch_state(t)[0]; pos = _chase(t, lerp(-7.0, 9.0, u), lerp(15.0, 12.0, u), lerp(2.5, 3.5, u)); return pos, (Vector(p + np.array([-1.5 - 3.0 * u, 0, -0.5 * u])) - Vector(pos)).to_track_quat('-Z', 'Y')
    def frame(st, i):
        t = t0 + i / FPS; dt = 1.0 / FPS; st.set_time(t, dt, dict(shutter=0.3)); u = i / (n - 1); pos, q = cam_at(st, t, u); st.look(pos, None, 34.0, quat=q)
        st.key3(st.cam, lambda tt: cam_at(st, tt, u), t, dt, True); p, v, s = C.launch_state(t)
        return t, dt, dict(samples=32, shutter=0.3, anchors={"tlam": tuple(p), "booster": tuple(free_xform("booster", t)[0])}, extra=dict(alt=float(p[2]), v=float(s)))
    return n, frame

# ----------------------------------------------------------------------------- shots: the way in
def shot_landfall(n=N_OF["landfall"]):
    """Thirty metres over the sea at 880 km/h, the coast coming up ahead."""
    x0 = COAST_X - 3300.0
    def cam_at(st, t, u):
        p = np.array([C.V_CRUISE * t, 0.0, 30.0 + 1.2 * math.sin(0.8 * t)]); pos = p + np.array([lerp(-13.0, -9.0, u), lerp(5.0, 7.5, u), lerp(3.2, 2.0, u)]); return pos, (Vector(p + np.array([14.0, -1.0, 0.5])) - Vector(pos)).to_track_quat('-Z', 'Y')
    def frame(st, i):
        t = x0 / C.V_CRUISE + i / FPS; dt = 1.0 / FPS; st.set_time(t, dt, dict(shutter=0.35)); u = i / (n - 1); pos, q = cam_at(st, t, u); st.look(pos, None, 30.0, quat=q)
        st.key3(st.cam, lambda tt: cam_at(st, tt, u), t, dt, True)
        return t, dt, dict(samples=28, shutter=0.35, anchors={"tlam": (C.V_CRUISE * t, 0.0, 30.0)}, extra=dict(coast=float(COAST_X - C.V_CRUISE * t)))
    return n, frame

def shot_cruise(n=N_OF["cruise"]):
    """Over the desert hills: the missile follows the ground about forty metres up, the camera swinging from behind it round to its side."""
    def cam_at(st, t, u):
        p, v = tland.cruise_state(t, CRUISE_X0); a = D(lerp(158.0, 96.0, smoothstep(0.0, 1.0, u))); r = lerp(15.0, 11.5, u)
        pos = p + np.array([r * math.cos(a), r * math.sin(a), lerp(4.5, 1.2, u)]); pos[2] = max(pos[2], float(tland.height(pos[0], pos[1])) + 6.0)
        return pos, (Vector(p + np.array([lerp(10.0, 1.5, u), 0, 0])) - Vector(pos)).to_track_quat('-Z', 'Y')
    def frame(st, i):
        t = i / FPS; dt = 1.0 / FPS; st.set_time(t, dt, dict(shutter=0.35)); u = i / (n - 1); pos, q = cam_at(st, t, u); st.look(pos, None, 30.0, quat=q)
        st.key3(st.cam, lambda tt: cam_at(st, tt, u), t, dt, True); p, v = tland.cruise_state(t, CRUISE_X0)
        return t, dt, dict(samples=24, shutter=0.35, anchors={"tlam": tuple(p)}, extra=dict(agl=float(p[2] - tland.height(p[0], 0.0)), v=float(np.linalg.norm(v))))
    return n, frame

# ----------------------------------------------------------------------------- shots: the factory
def shot_terminal(n=N_OF["terminal"]):
    """Riding down behind the missile through its last five and a half seconds: over the top of the pop-up and down on to the hall."""
    t1 = -0.05; t0 = t1 - (n - 1) / FPS
    def cam_at(st, t, u):
        p, v = C.term_state(t); d = v / np.linalg.norm(v); up = np.array([0, 0, 1.0]) - d * d[2]; up /= np.linalg.norm(up)
        pos = p - d * lerp(11.0, 7.5, u) + up * lerp(2.6, 1.5, u) + np.array([0, -1.6, 0]); return pos, (Vector(p + d * 14.0) - Vector(pos)).to_track_quat('-Z', 'Y')
    def frame(st, i):
        st.haze_mr.inputs["From Min"].default_value = 300.0; st.haze_mr.inputs["From Max"].default_value = 40000.0        # seen from high up: thin haze out to the horizon
        bpy.data.objects["Hills"].hide_render = True                    # the ring of low hills is drawn for views from the ground; from above it reads as blotches
        t = t0 + i / FPS; dt = 1.0 / FPS; st.set_time(t, dt, dict(haze=1.1)); u = i / (n - 1); pos, q = cam_at(st, t, u); st.look(pos, None, 28.0, quat=q)
        st.key3(st.cam, lambda tt: cam_at(st, tt, u), t, dt, True); p, v = C.term_state(t)
        return t, dt, dict(samples=18, shutter=0.3, anchors={"target": (0, 0, C.FAC["h"])}, extra=dict(alt=float(p[2]), dive=float(-math.degrees(math.atan2(v[2], v[0])))))
    return n, frame

def _sim(i, pre, one):
    if i < pre:
        return 0, -(pre - i) * SDT, SDT
    if i < pre + one:
        sf = i - pre + 1; return sf, (sf - 1) * SDT, SDT
    sf = one + 2 * (i - pre - one + 1); return sf, (sf - 1) * SDT, 2 * SDT

def shot_impact(n=N_OF["impact"]):
    """From outside the yard: the missile goes through the roof and the warhead fires inside (2.5x slow, then 1.25x)."""
    def frame(st, i):
        sf, t, dt = _sim(i, 14, 74); st.set_time(t, dt, {}); u = i / (n - 1)
        pos = np.array([30.0 + 3.0 * u, -66.0 - 6.0 * u, 2.4 + 1.6 * u]); tgt = np.array([1.0, 0.0, 6.0 + 9.0 * smoothstep(0.12, 1.0, u)])
        off, rq = shake(t - 0.19, 2.6); q = st.look(pos + off, tgt, 27.0); st.cam.rotation_quaternion = q @ rq
        return t, dt, dict(samples=14, sim=sf, shutter=0.25, anchors={"hit": (0, 0, C.FAC["h"] + C.FAC["ridge"])})
    return n, frame

def _circle(r):
    return [(r * math.cos(a), r * math.sin(a), 0.2) for a in np.linspace(0, 2 * np.pi, 97)]

def shot_radius(n=N_OF["radius"]):
    """From the air, with the radii the overlay draws on the ground (the same camera as the bombs of segment 07)."""
    def frame(st, i):
        sf = 1 + int(1.55 * i); t = (sf - 1) * SDT; dt = 1.55 * SDT
        st.set_time(t, dt, dict(frags=True, frag_gain=1.6, haze=0.5)); u = i / (n - 1)
        pos = np.array([-27.0 + 3 * u, -112.0, 126.0 + 3 * u]); st.look(pos, np.array([2.0, -14.0, 4.0]), 30.0)
        at = lambda r, a: (r * math.cos(D(a)), r * math.sin(D(a)), 0.2)
        return t, dt, dict(samples=12, sim=sf, shutter=0.25, anchors={"struct": at(C.R_STRUCT, -38), "blast": at(C.R_BLAST, -142)}, paths={"struct": _circle(C.R_STRUCT), "blast": _circle(C.R_BLAST)})
    return n, frame

def shot_after(n=N_OF["after"]):
    """Half a minute later: a slow move round what is left of the hall."""
    def cam_at(st, t, u):
        a = D(lerp(-118.0, -62.0, u)); r = lerp(64.0, 56.0, u); pos = np.array([r * math.cos(a), r * math.sin(a), lerp(11.0, 17.0, u)]); return pos, (Vector((0.0, 0.0, 5.0)) - Vector(pos)).to_track_quat('-Z', 'Y')
    def frame(st, i):
        t = 30.0 + i / FPS; dt = 1.0 / FPS; st.set_time(t, dt, dict(plume=True, flames=True, haze=0.3)); u = smoothstep(0.0, 1.0, i / (n - 1)); pos, q = cam_at(st, t, u); st.look(pos, None, 28.0, quat=q)
        st.key3(st.cam, lambda tt: cam_at(st, tt, u), t, dt, True)
        return t, dt, dict(samples=32, shutter=0.35, anchors={"hall": (0, 0, 3.0)})
    return n, frame

SHOTS = {"depth": shot_depth, "hatch": shot_hatch, "eject": shot_eject, "broach": shot_broach, "wings": shot_wings, "boost": shot_boost, "landfall": shot_landfall, "cruise": shot_cruise,
         "terminal": shot_terminal, "impact": shot_impact, "radius": shot_radius, "after": shot_after}

# ----------------------------------------------------------------------------- title card (studio)
def render_card(out_dir, res, spp, frames, n=N_OF["card"]):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    prof = [(-160.0, 0.0), (16.0, 0.0)] + [(16.0 + 5.0 * math.sin(a), 5.0 * (1 - math.cos(a))) for a in np.linspace(0, math.pi / 2, 12)[1:]] + [(21.0, 80.0)]
    V = np.array([[x, y, z] for (y, z) in prof for x in (-120.0, 120.0)])
    new_obj("Backdrop", new_mesh("bd", V, [grid_faces(len(prof), 2)]), None, simple_mat("BackdropMat", (0.64, 0.61, 0.56), rough=0.85))
    w = bpy.data.worlds.new("Studio"); sc.world = w; w.use_nodes = True
    w.node_tree.nodes["Background"].inputs[0].default_value = (0.75, 0.78, 0.82, 1); w.node_tree.nodes["Background"].inputs[1].default_value = 0.30
    def area(loc, size, power, color=(1, 1, 1)):
        L_ = bpy.data.lights.new("a", 'AREA'); L_.size = size; L_.energy = power; L_.color = color
        o = bpy.data.objects.new("a", L_); sc.collection.objects.link(o); o.location = loc; o.rotation_euler = (Vector((0, 0, 2.0)) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    area((6.0, -8.0, 9.0), 7.0, 2200, (1.0, 0.96, 0.9)); area((-8.0, -5.0, 3.5), 8.0, 700, (0.8, 0.9, 1.0)); area((-2.5, 7.0, 7.0), 6.0, 2000)
    pivot = bpy.data.objects.new("Pivot", None); sc.collection.objects.link(pivot); pivot.location = (0.2, 0, 2.1)
    T = ttlam.Tomahawk(); T.config(); T.root.parent = pivot; T.root.rotation_quaternion = Quaternion((1, 0, 0), D(-12)) @ Quaternion((0, 1, 0), D(-4))
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); sc.collection.objects.link(cam); sc.camera = cam
    cam.data.lens = 85; cam.data.clip_start = 0.05; cam.data.clip_end = 600; cam.data.sensor_width = 36
    cam.location = (0.0, -27.0, 2.6); cam.rotation_euler = (math.radians(88.9), 0, 0); cam.data.shift_x = 0.25
    sc.render.engine = 'CYCLES'; c = sc.cycles; c.samples = spp or 32; c.use_denoising = True; c.denoising_quality = 'HIGH'; c.max_bounces = 6
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
        render_card(a.out, res, a.spp, gshots.parse_frames(a.frames, N_OF["card"]) if a.frames else None)
        sys.stdout.flush(); os._exit(0)
    n, frame = SHOTS[a.shot]()
    frames = gshots.parse_frames(a.frames, n)
    st = Stage(SET_OF[a.shot], a.sim if (a.sim and a.shot in SIM_SHOTS) else None)
    sc = st.sc; sc.render.resolution_x, sc.render.resolution_y = res
    use_device(sc)
    os.makedirs(a.out, exist_ok=True)
    tl = dict(T_IGN=C.T_IGN, T_BROACH=C.T_BROACH, T_CLEAR=C.T_CLEAR, T_SHROUD=C.T_SHROUD, T_WINGS=C.T_WINGS, T_BURNOUT=C.T_BURNOUT, T_JETT=C.T_JETT, T_ENGINE=C.T_ENGINE, APEX=C.APEX, V_BURNOUT=C.V_BURNOUT,
              V_CRUISE=C.V_CRUISE, R_STRUCT=C.R_STRUCT, R_BLAST=C.R_BLAST, K=C.K, DIVE=C.DIVE, ROUTE_KM=C.ROUTE_KM, FLIGHT_MIN=C.FLIGHT_MIN, HATCH_Z=C.HATCH_Z, T_ROOF=C.T_ROOF, fps=FPS)
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
        for name, pts in info.get("paths", {}).items():
            m["path_" + name] = [proj(p)[:2] for p in pts]
        meta[str(i)] = m
        sc.render.filepath = fp
        bpy.ops.render.render(write_still=True)
        print("FRAME %s %d t=%.4f sim=%d %.1fs" % (a.shot, i, t, sf, time.time() - t0)); sys.stdout.flush()
        json.dump(meta, open(meta_path, "w"))
    sys.stdout.flush(); os._exit(0)

if __name__ == "__main__":
    main()
