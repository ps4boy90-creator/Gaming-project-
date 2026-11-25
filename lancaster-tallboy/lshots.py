"""Shot definitions and frame renderer for the Lancaster / Tallboy segment and, with LANC_BOMB=grandslam in the
environment, the Lancaster / Grand Slam segment (the same shots, scaled to the larger bomb and its larger burst).

  python3 lshots.py <shot> <out_dir> [--sim <sim_root>] [--res 1280x720] [--spp N] [--frames a-b | i,j,k]

Shots and their sets:
  card, intro                   studio      the bomb turning; the bomb with its dimensions
  approach, release             air         the Lancaster, its bomb doors opening; the release
  fall, impact, radius, after   out         the depot from above and from the ground
Clocks: air set, t = seconds after release; out set, tp = seconds after the nose touches the ground (the charge
fires at tp = 0.5).  Sim frames: 1/60 s each from tp = 0.
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
from qshots import Plume
from smoke_mat import blast_material
from util import *
import lconst as C, lbomb, llanc, lsite

FPS = C.FPS; SDT = 1.0 / 60.0
D = math.radians
shake = gsh.shake
SET_OF = {"approach": "air", "release": "air", "fall": "out", "impact": "out", "radius": "out", "after": "out"}
SIM_OF = {"impact": "out", "radius": "out"}
N_OF = {"card": 72, "approach": 108, "intro": 96, "release": 132, "fall": 84, "impact": 180, "radius": 108, "after": 108}
JET_Q = Quaternion((0, 1, 0), D(0.0))
T_DOORS = (-8.6, -6.4)                                               # the bomb doors open on the run-up
K = C.K_W; KL = C.K_L; TOP_H = round(100.0 * K, -1)                   # the burst's scale against a Tallboy's; the bomb's length against a Tallboy's; the height marked in the impact shot
L = C.TB_L; T_UNDER = L / C.V_HIT                                    # the tail has gone below the surface this long after the nose touched

def bomb_xform(tp):
    """Middle of the bomb and attitude, site coordinates: falling, then driving into the ground."""
    if tp < 0:
        p, v = C.fall_state(C.TOF + tp); d = v / np.linalg.norm(v); return p - d * L / 2, Quaternion((0, 1, 0), math.atan2(-v[2], v[0]))
    s, _ = C.pen_state(tp); return C.U * (s - L / 2), Quaternion((0, 1, 0), D(C.DIVE))

def rel_xform(t):
    """The released bomb as seen from the aircraft (which stays at the origin of the air set)."""
    p, v = C.fall_state(max(t, 0.0)); rel = p - C.jet_pos(max(t, 0.0)); p0 = np.array(JET_Q @ Vector(llanc.STORE))
    return p0 + rel, (Quaternion((0, 1, 0), math.atan2(-v[2], v[0]) * smoothstep(0.0, 2.5, t)) @ JET_Q if t > 0 else JET_Q)

def air_floor_mat():
    """Sea and coast from 5.5 km up: dark water, a ragged coastline, fields and woods; fading into haze with distance."""
    m, N, L_, P = nodemat("CoastFar"); tc = N.new("ShaderNodeTexCoord")
    def noise(scale, detail=8, rough=0.55, dist=0.0):
        n = N.new("ShaderNodeTexNoise"); n.inputs["Scale"].default_value = scale; n.inputs["Detail"].default_value = detail; n.inputs["Roughness"].default_value = rough
        n.inputs["Distortion"].default_value = dist; L_.new(tc.outputs["Object"], n.inputs["Vector"]); return n
    coast = noise(1 / 9000.0, 10, 0.62, 0.8); sep = N.new("ShaderNodeSeparateXYZ"); L_.new(tc.outputs["Object"], sep.inputs[0])
    gx = N.new("ShaderNodeMapRange"); gx.inputs["From Min"].default_value = -30000.0; gx.inputs["From Max"].default_value = 30000.0; gx.inputs["To Min"].default_value = -0.5; gx.inputs["To Max"].default_value = 0.5; gx.clamp = False; L_.new(sep.outputs["X"], gx.inputs["Value"])
    add = N.new("ShaderNodeMath"); add.operation = 'ADD'; L_.new(coast.outputs["Fac"], add.inputs[0]); L_.new(gx.outputs[0], add.inputs[1])
    land = N.new("ShaderNodeMath"); land.operation = 'GREATER_THAN'; land.inputs[1].default_value = 0.52; L_.new(add.outputs[0], land.inputs[0])
    fields = noise(1 / 700.0, 4, 0.5, 0.2); r1 = N.new("ShaderNodeValToRGB"); e = r1.color_ramp.elements; e[0].position = 0.35; e[0].color = (0.035, 0.060, 0.025, 1); e[1].position = 0.68; e[1].color = (0.150, 0.135, 0.075, 1); L_.new(fields.outputs["Fac"], r1.inputs["Fac"])
    sea = noise(1 / 2500.0, 5, 0.5); r2 = N.new("ShaderNodeValToRGB"); e = r2.color_ramp.elements; e[0].color = (0.010, 0.030, 0.045, 1); e[1].color = (0.020, 0.050, 0.065, 1); L_.new(sea.outputs["Fac"], r2.inputs["Fac"])
    mx = N.new("ShaderNodeMixRGB"); L_.new(land.outputs[0], mx.inputs[0]); L_.new(r2.outputs["Color"], mx.inputs[1]); L_.new(r1.outputs["Color"], mx.inputs[2]); L_.new(mx.outputs[0], P.inputs["Base Color"])
    ro = N.new("ShaderNodeMapRange"); ro.inputs["To Min"].default_value = 0.22; ro.inputs["To Max"].default_value = 0.95; L_.new(land.outputs[0], ro.inputs["Value"]); L_.new(ro.outputs[0], P.inputs["Roughness"])
    cd = N.new("ShaderNodeCameraData"); hz = N.new("ShaderNodeMapRange"); hz.inputs["From Min"].default_value = 5000.0; hz.inputs["From Max"].default_value = 200000.0; hz.inputs["To Max"].default_value = 1.0
    L_.new(cd.outputs["View Distance"], hz.inputs["Value"]); pw = N.new("ShaderNodeMath"); pw.operation = 'POWER'; pw.inputs[1].default_value = 0.62; L_.new(hz.outputs[0], pw.inputs[0])
    em = N.new("ShaderNodeEmission"); em.inputs["Color"].default_value = (0.50, 0.61, 0.78, 1); em.inputs["Strength"].default_value = 0.60
    mixs = N.new("ShaderNodeMixShader"); out = [n for n in N if n.type == 'OUTPUT_MATERIAL'][0]
    L_.new(pw.outputs[0], mixs.inputs["Fac"]); L_.new(P.outputs[0], mixs.inputs[1]); L_.new(em.outputs[0], mixs.inputs[2]); L_.new(mixs.outputs[0], out.inputs["Surface"])
    return m

def build_air(sc, alt):
    col = bpy.data.collections.new("ENV"); sc.collection.children.link(col); env.make_world(sc)
    na = 180; rr = np.concatenate([[0.0], np.geomspace(200.0, 9.0e5, 60)]); a = np.linspace(0, 2 * np.pi, na, endpoint=False)
    A, Rr = np.meshgrid(a, rr, indexing="ij"); V = np.stack([Rr * np.cos(A), Rr * np.sin(A), np.full_like(A, -alt)], -1).reshape(-1, 3)
    return col, new_obj("CoastFloor", new_mesh("coast_floor", V, [grid_faces(na, len(rr), wrap_u=True)]), col, air_floor_mat())

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
            self.fire0 = 26.0; bm_ = blast_material(density=4.5, fire=self.fire0, ambient=0.06); self.dom.data.materials.append(bm_); self.fire_node = bm_.node_tree.nodes[bm_["fire_node"]]
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
            self.env_col, self.floor = build_air(sc, C.H_REL)
            self.car = llanc.Lancaster(col, store=True); self.car.root.rotation_quaternion = JET_Q; self.bomb = lbomb.Bomb(col, "Dropped")
            ld = bpy.data.lights.new("Bounce", 'AREA'); ld.size = 60.0; ld.energy = 2.2e4; ld.color = (0.80, 0.88, 1.0); lo = bpy.data.objects.new("Bounce", ld); col.objects.link(lo)   # light thrown back up by sea and haze: the underside is black paint
            lo.location = (0, 0, -40.0); lo.rotation_euler = (math.pi, 0, 0); ld.use_shadow = False
        else:
            ec = self.env_col = bpy.data.collections.new("ENV"); sc.collection.children.link(ec)
            self.site = lsite.Base(sc, ec)
            self.bomb = lbomb.Bomb(col, "Falling")
            self.l_hit = ms.point_light(col, "BurstFlash", (1.0, 0.60, 0.30), 5.0); self.l_hit.location = (0.0, 0.0, 9.0 * K)
            self.plume = Plume(col); self.plume.ob.location = (0.0, 0.0, -6.0); self.plume.ob.scale = (4.0 * K, 4.0 * K, 3.0 * K); self.plume.fl.hide_render = True; self.plume.glow.hide_render = True
            for mt in self.plume.mats:                                   # dust and thin smoke out of the crater, not an oil fire
                f = mt.node_tree.nodes["Fade"]; f.inputs["To Min"].default_value = 0.05; f.inputs["To Max"].default_value = 0.006
                for nd in mt.node_tree.nodes:
                    if nd.type == 'PRINCIPLED_VOLUME':
                        nd.inputs["Color"].default_value = (0.40, 0.36, 0.30, 1)
        cd = bpy.data.cameras.new("Cam"); self.cam = bpy.data.objects.new("Cam", cd); sc.collection.objects.link(self.cam); sc.camera = self.cam
        cd.clip_start = 0.05; cd.clip_end = 2.0e6; cd.sensor_width = 36; cd.sensor_fit = 'HORIZONTAL'
        self.cam.rotation_mode = 'QUATERNION'
        self.setup_render()
        ng = sc.compositing_node_group; self.haze_mr = [nd for nd in ng.nodes if nd.bl_idname == "ShaderNodeMapRange"][0]; self.haze0 = 0.62
        mix = [nd for nd in ng.nodes if nd.bl_idname == "ShaderNodeMix"][0]                                  # a small blur of the haze amount removes the speckle of a single-sample depth pass
        lk = [l for l in ng.links if l.to_node == mix and l.to_socket.name == "Factor"][0]; src = lk.from_socket; ng.links.remove(lk)
        bl = ng.nodes.new("CompositorNodeBlur"); bl.inputs["Size"].default_value[0] = 6.0; bl.inputs["Size"].default_value[1] = 6.0
        ng.links.new(src, bl.inputs["Image"]); ng.links.new(bl.outputs["Image"], mix.inputs["Factor"])
        for nd in ng.nodes:
            if nd.bl_idname == "ShaderNodeMath" and nd.operation == 'LESS_THAN':
                nd.inputs[1].default_value = 5.0e6
        if kind == "air":
            self.haze_mr.inputs["From Min"].default_value = 3000.0; self.haze_mr.inputs["From Max"].default_value = 90000.0; self.haze0 = 0.22
        else:
            self.haze_mr.inputs["From Min"].default_value = 300.0; self.haze_mr.inputs["From Max"].default_value = 30000.0; self.haze0 = 0.70

    def set_time(self, t, dt_out, opt):
        sc = self.sc; mb = opt.get("motion_blur", True); sc.render.use_motion_blur = mb; k = self.kind
        self.haze_mr.inputs["To Max"].default_value = self.haze0 * opt.get("haze", 1.0)
        if k == "air":
            gone = t >= 0; self.car.store.hide(case=gone, tail=gone); self.bomb.hide(case=not gone, tail=not gone)
            self.car.set(doors=smoothstep(T_DOORS[0], T_DOORS[1], t), links=smoothstep(0.0, 0.12, t)); self.car.spin_props(sc, t, dt_out, mb)
            self.bomb.turn(C.spin_angle(t)); self.key3(self.bomb.root, rel_xform, t, dt_out, mb)
            self.floor.location = (-C.V_REL * t, 0.0, 0.0); return
        tp = t; td = tp - C.FUZE_DELAY
        self.key3(self.bomb.root, bomb_xform, tp, dt_out, mb); self.bomb.turn(C.spin_angle(C.TOF + min(tp, 0.0)))
        self.site.update(tp); under = bool(tp > T_UNDER); self.bomb.hide(case=under, tail=under)
        e = 6.0e6 * math.exp(-(td - 0.07) / 0.08) if 0.07 <= td < 0.8 else 0.0; self.l_hit.data.energy = e; self.l_hit.hide_render = e < 5.0     # the gas breaks through the earth a moment after the burst
        self.plume.update(bool(opt.get("plume", False)), tp); self.plume.fl.hide_render = True; self.plume.glow.hide_render = True
        if self.dom is not None:
            self.dom.hide_render = bool(tp < 0)
            self.fire_node.inputs[1].default_value = self.fire0 * (0.012 + 0.988 * math.exp(-max(td, 0.0) / 0.45))

# ----------------------------------------------------------------------------- shots: in the air
def shot_approach(n=N_OF["approach"]):
    """The Lancaster on its run-up at 18,000 ft, seen from below and to its left: the bulged doors open on the bomb."""
    def frame(st, i):
        t = -9.5 + i / FPS; dt = 1.0 / FPS; st.set_time(t, dt, {}); u = smoothstep(0.0, 1.0, i / (n - 1)); sp = np.array(JET_Q @ Vector(llanc.STORE))
        pos = np.array([lerp(30.0, 15.0, u), lerp(31.0, 15.5, u), lerp(1.5, -8.5, u)]); st.look(pos, sp + np.array([lerp(-3.5, 0.6, u), 0.0, lerp(1.2, 0.2, u)]), lerp(36.0, 42.0, u))
        return t, dt, dict(samples=40, shutter=0.4, anchors={"bomb": tuple(sp + np.array([1.6, 0, -0.3])), "doors": tuple(sp + np.array([-3.0, 0.9, -0.9])), "wing": (-1.5, 9.0, 0.6)}, extra=dict(doors=float(smoothstep(T_DOORS[0], T_DOORS[1], t))))
    return n, frame

def shot_release(n=N_OF["release"]):
    """Under the aircraft: the links let go, the bomb drops clear and begins to turn (half speed from the release)."""
    def frame(st, i):
        t, dt = (-1.5 + i / FPS, 1.0 / FPS) if i < 30 else (-1.5 + 30 / FPS + (i - 30) / 48.0, 1.0 / 48.0)
        st.set_time(t, dt, dict(shutter=0.3)); u = i / (n - 1); home = np.array(JET_Q @ Vector(llanc.STORE)); p, _ = rel_xform(t)
        follow = 0.62 * smoothstep(0.05, 0.9, t) + 0.33 * smoothstep(0.8, 1.7, t); aim = home + follow * (np.array([p[0], home[1], p[2]]) - home)
        pos = home + np.array([lerp(8.5, 7.0, u), lerp(11.0, 9.5, u), lerp(-4.4, -6.8, u)]); st.look(pos, aim + np.array([-0.4, 0, 0]), 30.0)
        return t, dt, dict(samples=44, shutter=0.3, anchors={"bomb": tuple(p), "bay": tuple(home + np.array([-1.0, 0, 0.5]))}, extra=dict(rpm=float(np.interp(max(t, 0.0), C.SPIN[:, 0], C.SPIN[:, 2]) * 60 / (2 * math.pi))))
    return n, frame

# ----------------------------------------------------------------------------- shots: the depot
def shot_fall(n=N_OF["fall"]):
    """Riding down behind the bomb through its last three and a half seconds, on to the depot."""
    t1 = -0.07; t0 = t1 - (n - 1) / FPS
    def cam_at(st, tp, u):
        p, q = bomb_xform(tp); d = np.array(q @ Vector((1, 0, 0))); up = np.array([-1.0, 0, 0]) - d * (-d[0]); up /= np.linalg.norm(up)
        pos = p - d * lerp(16.0, 11.5, u) * KL + up * lerp(3.4, 2.4, u) * KL + np.array([0, 2.0 * KL, 0]); return pos, (Vector(p + d * 22.0) - Vector(pos)).to_track_quat('-Z', 'Y')
    def frame(st, i):
        tp = t0 + i / FPS; dt = 1.0 / FPS; st.set_time(tp, dt, dict(haze=1.0)); u = i / (n - 1); pos, q = cam_at(st, tp, u); st.look(pos, None, 28.0, quat=q)
        st.key3(st.cam, lambda tt: cam_at(st, tt, u), tp, dt, True); p, v = C.fall_state(C.TOF + tp)
        return tp, dt, dict(samples=20, shutter=0.3, anchors={"target": (0, 0, 0), "barracks": (0.0, 111.0, 6.0), "garages": (-6.0, -84.0, 5.0)},
                            extra=dict(alt=float(p[2]), v=float(np.linalg.norm(v)), dive=float(math.degrees(math.atan2(-v[2], v[0])))))
    return n, frame

def _out_clock(i, pre, one):
    """Before the hit and for `one` frames after it, one frame = 1/60 s (2.5x slow); after that two sim frames per frame."""
    if i < pre:
        return 0, -(pre - i) * SDT, SDT
    if i < pre + one:
        sf = i - pre + 1; return sf, (sf - 1) * SDT, SDT
    sf = one + 2 * (i - pre - one + 1); return sf, (sf - 1) * SDT, 2 * SDT

def shot_impact(n=N_OF["impact"]):
    """From a watch tower's height, 220 m off: the bomb goes into the yard; half a second later the yard is thrown into the air."""
    def frame(st, i):
        sf, tp, dt = _out_clock(i, 16, 104); st.set_time(tp, dt, {}); u = i / (n - 1); td = tp - C.FUZE_DELAY
        pos = np.array([(-70.0 + 8.0 * u) * K, (-205.0 - 12.0 * u) * K, 17.0 + 2.0 * u]); tgt = np.array([0.0, 0.0, (10.0 + 40.0 * smoothstep(0.26, 0.9, u)) * K])
        off, rq = shake(td - 0.75, 3.0); st.look(pos + off, tgt, lerp(36.0, 22.0, smoothstep(0.24, 0.6, u))); st.cam.rotation_quaternion = st.cam.rotation_quaternion @ rq
        return tp, dt, dict(samples=16, sim=sf, shutter=0.25, anchors={"hit": (0, 0, 0.5), "top": (0, 0, TOP_H), "lorry": (52.0, 16.0, 2.6), "barracks": (56.0, 96.0, 8.0)})
    return n, frame

def _circle(r):
    return [(r * math.cos(a), r * math.sin(a), 0.3) for a in np.linspace(0, 2 * np.pi, 97)]

def shot_radius(n=N_OF["radius"]):
    """From the air: the burst and its circles (the crater, buildings destroyed, 5 psi), with a smaller bomb's 5 psi circle for
    comparison (a Mk 84's in the Tallboy film, a Tallboy's in the Grand Slam film)."""
    def frame(st, i):
        sf = 27 + int(1.55 * i); tp = (sf - 1) * SDT; dt = 1.55 * SDT; st.set_time(tp, dt, dict(haze=0.5)); u = i / (n - 1)
        pos = np.array([-50.0 + 5 * u, -205.0, 232.0 + 5 * u]) * K; st.look(pos, np.array([3.0, -22.0, 6.0]) * K, 30.0)
        at = lambda r, a: (r * math.cos(D(a)), r * math.sin(D(a)), 0.3)
        an = {"crater": at(C.CRATER_R, -62), "struct": at(C.R_STRUCT, -32), "blast": at(C.R_BLAST, -142), "cmp": at(C.R_CMP, 96)}
        paths = {"crater": _circle(C.CRATER_R), "struct": _circle(C.R_STRUCT), "blast": _circle(C.R_BLAST), "cmp": _circle(C.R_CMP)}
        return tp, dt, dict(samples=12, sim=sf, shutter=0.25, anchors=an, paths=paths)
    return n, frame

def shot_after(n=N_OF["after"]):
    """Half a minute later, circling low: the crater, the wrecked buildings round it, a lorry for scale."""
    def cam_at(st, t, u):
        a = D(lerp(232.0, 285.0, u)); r = lerp(120.0, 98.0, u) * K; pos = np.array([r * math.cos(a), r * math.sin(a), lerp(46.0, 36.0, u) * K]); return pos, (Vector((2.0, 4.0, -2.0)) - Vector(pos)).to_track_quat('-Z', 'Y')
    def frame(st, i):
        tp = 30.0 + i / FPS; dt = 1.0 / FPS; st.set_time(tp, dt, dict(plume=True, haze=0.8)); u = smoothstep(0.0, 1.0, i / (n - 1)); pos, q = cam_at(st, tp, u); st.look(pos, None, 30.0, quat=q)
        st.key3(st.cam, lambda tt: cam_at(st, tt, u), tp, dt, True); a0 = D(20.0)
        lp = next((tuple(ob.location) for ob, pc, q0, d in st.site.lorries if abs(pc.p0[0] - 52.0) < 0.1 and abs(pc.p0[1] - 16.0) < 0.1), (52.0, 16.0, 0.0))     # where that lorry came to rest
        return tp, dt, dict(samples=32, shutter=0.35, anchors={"a": (C.CRATER_R * math.cos(a0), C.CRATER_R * math.sin(a0), 1.6), "b": (-C.CRATER_R * math.cos(a0), -C.CRATER_R * math.sin(a0), 1.6), "mid": (0, 0, -C.CRATER_D), "lorry": (lp[0], lp[1], lp[2] + 1.6), "wreck": (-42.0, 36.0, 1.5)})
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
    """The bomb turning slowly on a studio backdrop (left half of the frame; the panel is added in post)."""
    sc, cam = _studio(1.0); sc.cycles.samples = spp or 40
    pivot = bpy.data.objects.new("Pivot", None); sc.collection.objects.link(pivot); pivot.location = (0.2, 0, 2.2)
    B = lbomb.Bomb(name="Card"); B.root.parent = pivot; B.root.rotation_quaternion = Quaternion((1, 0, 0), D(-10)) @ Quaternion((0, 1, 0), D(-5))
    cam.data.lens = 85; cam.location = (0.0, -29.0 * KL, 2.7); cam.rotation_euler = (math.radians(88.9), 0, 0); cam.data.shift_x = 0.25
    sc.render.resolution_x, sc.render.resolution_y = res; sc.render.use_border = True; sc.render.use_crop_to_border = True
    sc.render.border_min_x = 0.0; sc.render.border_max_x = 0.50; sc.render.border_min_y = 0.0; sc.render.border_max_y = 1.0
    os.makedirs(out_dir, exist_ok=True)
    for i in (frames if frames is not None else range(n)):
        u = i / n
        if os.path.exists(os.path.join(out_dir, "f%04d.png" % i)):
            continue
        pivot.rotation_euler = (0, 0, math.radians(-128) + math.radians(18) * math.sin(2 * math.pi * u)); B.turn(2 * math.pi * u * 0.25)
        sc.render.filepath = os.path.join(out_dir, "f%04d.png" % i); t = time.time(); bpy.ops.render.render(write_still=True)
        print("FRAME card %d %.1fs" % (i, time.time() - t)); sys.stdout.flush()

INTRO_X = 0.0; INTRO_Z = 2.25

def render_intro(out_dir, res, spp, frames, n=N_OF["intro"]):
    """The bomb alone, side on, with a lorry of the target beside it for scale."""
    from bpy_extras.object_utils import world_to_camera_view
    sc, cam = _studio(1.0, world=0.24, backdrop=(0.105, 0.11, 0.12)); sc.cycles.samples = spp or 48
    bpy.data.objects["Backdrop"].location = (0, 0, -3.4)
    g = lbomb.Bomb(name="Whole"); g.root.location = (INTRO_X, 0, INTRO_Z)
    lo = bpy.data.objects.new("Lorry", lsite._lorry_mesh()); sc.collection.objects.link(lo); lo.data.materials.append(bpy.data.materials.get("BombPaint")); lo.location = (-0.2, 2.6, -0.62)
    sc.render.resolution_x, sc.render.resolution_y = res; os.makedirs(out_dir, exist_ok=True)
    R = C.TB_D / 2; zt = INTRO_Z; x0 = INTRO_X; X = lambda s: x0 + L / 2 - s
    pts = {"nose": (X(0), 0, zt), "tail": (X(L), 0, zt), "top": (X(1.6 * KL), 0, zt + R), "bot": (X(1.6 * KL), 0, zt - R), "case": (X(1.9 * KL), -R, zt + 0.1), "fins": (X(L - 0.8 * KL), -0.3, zt - 0.36 * KL), "joint": (X(C.CASE_L + 0.9 * KL), -0.3, zt + 0.1), "band": (X(1.04 * KL), -0.38, zt + 0.2), "lorry": (-1.4, 2.6, 2.0)}
    meta_path = os.path.join(out_dir, "meta.json"); meta = json.load(open(meta_path)) if os.path.exists(meta_path) else {}
    for i in (frames if frames is not None else range(n)):
        u = smoothstep(0.0, 1.0, i / (n - 1)); cam.data.lens = 50; cam.location = (lerp(0.30, -0.20, u), -12.6 * KL, 2.05); cam.rotation_euler = (math.radians(90.0), 0, 0)
        g.turn(0.5 * u)
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
    tl = dict(TOF=C.TOF, THROW=C.THROW, V_REL=C.V_REL, V_HIT=C.V_HIT, MACH_HIT=C.MACH_HIT, DIVE=C.DIVE, H_REL=C.H_REL, FUZE=C.FUZE_DELAY, RPM=C.RPM_HIT, D_PATH=C.D_PATH, T_STOP=C.T_STOP, DEPTH=C.DEPTH_BURST,
              CRATER_R=C.CRATER_R, R_STRUCT=C.R_STRUCT, R_BLAST=C.R_BLAST, R_MK84=C.R_MK84, R_CMP=C.R_CMP, R_TALLBOY=C.R_TALLBOY, BOMB=C.BOMB, NAME=C.NAME, TOP=TOP_H, CRATER_PUB_D=C.CRATER_PUB_D, T_DOORS=list(T_DOORS), T_UNDER=T_UNDER, fps=FPS)
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
