"""Shot definitions and frame renderer for the UH-60 Black Hawk / Mk 77 fire bomb explosion-comparison segment.

  python3 nshots.py <shot> <out_dir> [--sim <cache_dir>] [--res 1280x720] [--spp N] [--frames a-b | i,j,k]

Shots: card, approach, release, fall, impact, radius, after - all in the ruined town of segment 04.
Time base: t = seconds after release; the canister hits at T_HIT.  One sim frame is 1/48 s.
"""
import bpy, sys, os, math, json, time, argparse
HERE = os.path.dirname(os.path.abspath(__file__))
for p in ("grenade-explosion", "rpg7-explosion", "mortar-explosion", "howitzer-explosion", "reaper-hellfire"):
    sys.path.insert(0, os.path.join(HERE, "..", p))
sys.path.insert(0, HERE)
import numpy as np
from mathutils import Vector, Quaternion
import manta_fix  # noqa: F401
import shots as gshots
import mshots as ms
import htown
from hshots import use_device
from qshots import Plume
from smoke_mat import blast_material
from util import *
import nconst as C, nuh60

FPS = C.FPS; T_HIT = C.T_HIT; SDT = C.SIM_DT
D = math.radians
shake = gshots.shake
SIM_OF = {"impact": "impact", "radius": "impact"}
DROP = 1                                      # index of the canister that is released (left outboard pylon)
PITCH = D(4.0)                                # nose-down attitude in forward flight
FIRE_C = np.array([17.0, -1.5, 0.0])          # middle of the burning stretch of street

def heli_xform(t):
    p = C.heli_pos(t) + np.array([0, 0, 0.25 * math.sin(1.1 * t)]); q = Quaternion((0, 1, 0), PITCH) @ Quaternion((1, 0, 0), D(1.0) * math.sin(0.8 * t))
    return p, q

def store_world(t):
    """World position of the canister while it still hangs on its pylon."""
    p, q = heli_xform(t); ay, side = nuh60.PYLONS[DROP]
    return p + np.array(q @ Vector(nuh60.store_centre(ay, side))), q

def bomb_xform(t):
    if t <= 0:
        return store_world(t)
    p0, q0 = store_world(0.0); p, v, ang = C.bomb_state(t)
    return np.array([p[0], p0[1], p[2]]), Quaternion((0, 1, 0), ang) @ q0

def scorch_mesh(col):
    """Burnt ground along the street (shown after the fire has passed)."""
    na, nr = 72, 8; a = np.linspace(0, 2 * np.pi, na, endpoint=False); r = np.linspace(0.02, 1.0, nr); A, R_ = np.meshgrid(a, r, indexing="ij")
    X = FIRE_C[0] + 21.0 * R_ * np.cos(A); Y = FIRE_C[1] + 4.3 * R_ * np.sin(A); V = np.stack([X, Y, np.full_like(X, 0.045)], -1).reshape(-1, 3)
    uv = np.stack([R_, A / (2 * np.pi)], -1).reshape(-1, 2); me = new_mesh("scorch", V, [grid_faces(na, nr, wrap_u=True)], uvs=uv)
    m, N, L, P = nodemat("ScorchMat"); tc = N.new("ShaderNodeTexCoord"); sep = N.new("ShaderNodeSeparateXYZ"); L.new(tc.outputs["UV"], sep.inputs[0])
    n = N.new("ShaderNodeTexNoise"); n.inputs["Scale"].default_value = 0.6; n.inputs["Detail"].default_value = 5; L.new(tc.outputs["Object"], n.inputs["Vector"])
    edge = N.new("ShaderNodeMapRange"); edge.inputs["From Min"].default_value = 1.0; edge.inputs["From Max"].default_value = 0.45; L.new(sep.outputs["X"], edge.inputs["Value"])
    nm = N.new("ShaderNodeMapRange"); nm.inputs["From Min"].default_value = 0.30; nm.inputs["From Max"].default_value = 0.60; L.new(n.outputs["Fac"], nm.inputs["Value"])
    gain = N.new("ShaderNodeValue"); gain.name = "Gain"; mu = N.new("ShaderNodeMath"); mu.operation = 'MULTIPLY'; L.new(edge.outputs[0], mu.inputs[0]); L.new(nm.outputs[0], mu.inputs[1])
    mu2 = N.new("ShaderNodeMath"); mu2.operation = 'MULTIPLY'; L.new(mu.outputs[0], mu2.inputs[0]); L.new(gain.outputs[0], mu2.inputs[1]); L.new(mu2.outputs[0], P.inputs["Alpha"])
    P.inputs["Base Color"].default_value = (0.012, 0.011, 0.010, 1); P.inputs["Roughness"].default_value = 0.9
    ob = new_obj("Scorch", me, col, m); ob.visible_shadow = False
    return ob, gain

class Stage(gshots.Stage):
    def __init__(self, sim_dir=None):
        self.dom = None
        if sim_dir and os.path.exists(os.path.join(sim_dir, "sim.blend")):
            bpy.ops.wm.open_mainfile(filepath=os.path.join(sim_dir, "sim.blend"))
            for o in list(bpy.data.objects):
                if o.name.startswith("E_"):
                    bpy.data.objects.remove(o, do_unlink=True)
            self.dom = bpy.data.objects["BlastDomain"]; self.dom.data.materials.clear()
            bm_ = blast_material(density=7.0, fire=5.5, ambient=0.03); self.dom.data.materials.append(bm_); self.fire_node = bm_.node_tree.nodes[bm_["fire_node"]]
            for nd in bm_.node_tree.nodes:
                if nd.type == 'VECT_MATH' and nd.operation == 'POWER':
                    nd.inputs[1].default_value = (0.85, 0.85, 0.85)                    # keep the smoke black
                if nd.type == 'VALTORGB':
                    for el, c in zip(sorted(nd.color_ramp.elements, key=lambda e: e.position), [(0, 0, 0), (0.55, 0.05, 0.0), (1.0, 0.24, 0.02), (1.0, 0.52, 0.07), (1.0, 0.80, 0.32)]):
                        el.color = (*c, 1)
            self.dom.hide_render = True
        else:
            bpy.ops.wm.read_factory_settings(use_empty=True)
        sc = self.sc = bpy.context.scene; sc.render.fps = FPS
        self.env_col, self.ground = htown.build_town(sc)
        self.ground.data.materials[0].node_tree.nodes["Blast"].outputs[0].default_value = 0.0
        col = self.col = bpy.data.collections.new("ACTION"); sc.collection.children.link(col)
        self.town = htown.Town(col); self.town.update(-1.0)
        self.ac = nuh60.build(col); self.ac["bombs"][DROP].ob.hide_render = True
        self.bomb = nuh60.Mk77(col, "Mk77_dropped")
        self.scorch, self.scorch_gain = scorch_mesh(col)
        self.glow = ms.point_light(col, "FireGlow", (1.0, 0.50, 0.18), 2.5); self.glow.location = (12.0, -1.5, 3.5)
        self.plumes = []
        for x, y in ((9.0, -1.0), (24.0, -2.0)):
            p = Plume(col)
            for o in (p.ob, p.fl):
                o.location = (x, y, -0.75)
            p.glow.location = (x, y, 1.5); self.plumes.append(p)
        cd = bpy.data.cameras.new("Cam"); self.cam = bpy.data.objects.new("Cam", cd); sc.collection.objects.link(self.cam); sc.camera = self.cam
        cd.clip_start = 0.05; cd.clip_end = 8000; cd.sensor_width = 36; cd.sensor_fit = 'HORIZONTAL'
        self.cam.rotation_mode = 'QUATERNION'
        self.setup_render()
        self.haze_mr = [nd for nd in sc.compositing_node_group.nodes if nd.bl_idname == "ShaderNodeMapRange"][0]

    def set_time(self, t, dt_out, opt):
        sc = self.sc; mb = opt.get("motion_blur", True); sc.render.use_motion_blur = mb; sh = opt.get("shutter", 0.5)
        self.haze_mr.inputs["To Max"].default_value = 0.62 * opt.get("haze", 1.0)
        root = self.ac["root"]
        def hstate(tt):
            p, q = heli_xform(tt); return p, q
        self.key3(root, hstate, t, dt_out, mb)
        nuh60.spin(self.ac["main"], sc, t, dt_out if mb else 0.0, C.MAIN_RPS, sh); nuh60.spin(self.ac["tail"], sc, t, dt_out if mb else 0.0, C.TAIL_RPS, sh)
        td = t - T_HIT; hit = td >= 0
        self.bomb.ob.hide_render = hit
        if not hit:
            self.key3(self.bomb.ob, bomb_xform, t, dt_out, mb)            # keyed before release too: it rides with the helicopter
        self.scorch_gain.outputs[0].default_value = 0.92 * smoothstep(0.3, 2.5, td)
        on = hit and opt.get("glow", True) and td < 20
        self.glow.hide_render = not on
        if on:
            self.glow.location = (min(4.0 + 30.0 * td, 16.0), -1.5, 3.5); self.glow.data.energy = 55000.0 * smoothstep(0.0, 0.5, td) * (1 + 0.15 * math.sin(td * 17.0) + 0.1 * math.sin(td * 41.0))
        for k, p in enumerate(self.plumes):
            p.update(bool(opt.get("plume", False)), t + 3.3 * k)
        if self.dom is not None:
            self.dom.hide_render = not hit
            self.fire_node.inputs[1].default_value = lerp(5.5, 13.0, smoothstep(0.4, 1.6, td))      # the first fireball is the brightest; later flames show through smoke

# ----------------------------------------------------------------------------- shots
def shot_approach(n=96):
    """Air to air: the Black Hawk running in low towards the ruins, four fire bombs under its stub wings."""
    def frame(st, i):
        t = -5.2 + i / FPS; dt = 1.0 / FPS; u = i / (n - 1)
        st.set_time(t, dt, dict(haze=0.6, shutter=0.35))
        a = D(lerp(28.0, 66.0, smoothstep(0, 1, u))); r = lerp(21.0, 17.0, u); off = np.array([r * math.cos(a), r * math.sin(a), lerp(0.4, 2.6, u)])      # on the sunlit (left) side
        def cam_at(tt):
            hp = heli_xform(tt)[0]; pos = hp + off; return pos, (Vector(hp + np.array([-1.5, 0.0, 2.0])) - Vector(pos)).to_track_quat('-Z', 'Y')
        hp = heli_xform(t)[0]; pos, q = cam_at(t); st.look(pos, None, 34.0, quat=q); st.key3(st.cam, cam_at, t, dt, True)
        an = {"store": tuple(store_world(t)[0]), "rotor": tuple(hp + np.array([0, 0, 3.8]))}
        return t, dt, dict(samples=24, shutter=0.35, anchors=an)
    return n, frame

def shot_release(n=112, lead=20):
    """Close beside the left stub wing, on the sunlit side: the rack lets go and the canister drops away and starts to
    tumble (real time, then 4x slow).  The camera rides with the helicopter and sinks with the canister, on a short
    exposure, so that both stay sharp."""
    def frame(st, i):
        if i < lead:
            t = -(lead - i) / FPS - 0.002; dt = 1.0 / FPS
        else:
            dt = 1.0 / 96.0; t = (i - lead) * dt
        st.set_time(t, dt, dict(haze=0.30, shutter=0.18))
        bp, bq = bomb_xform(t); u = i / (n - 1); fallen = float(max(store_world(t)[0][2] - bp[2], 0.0))
        off = np.array([4.5 - 0.5 * u, 6.3, 0.60 - 0.55 * fallen]); k = smoothstep(0.02, 0.30, max(t, 0.0))
        def cam_at(tt):
            pos = heli_xform(tt)[0] + off; tgt = lerp(store_world(tt)[0] + np.array([0.0, -0.35, 0.15]), bomb_xform(tt)[0], k)
            return pos, (Vector(tgt) - Vector(pos)).to_track_quat('-Z', 'Y')
        pos, q = cam_at(t); st.look(pos, None, lerp(46.0, 40.0, u), quat=q); st.key3(st.cam, cam_at, t, dt, True)
        return t, dt, dict(samples=40, shutter=0.18, anchors={"bomb": tuple(bp)}, extra=dict(drop=fallen))
    return n, frame

def shot_fall(n=64):
    """Real time: the camera follows the tumbling canister down onto the street."""
    t0, t1 = 0.95, T_HIT - 0.04
    def cam_at(t):
        p, v, ang = C.bomb_state(t); p = np.array([p[0], 0.0, p[2]]); d = v / np.linalg.norm(v); up = np.array([0, 0, 1.0]) - d * d[2]; up /= np.linalg.norm(up)
        u = (t - t0) / (t1 - t0); pos = p - d * lerp(7.5, 5.5, u) + up * lerp(1.9, 1.5, u) + np.array([0, -1.2, 0])
        return pos, (Vector(p + d * 4.0) - Vector(pos)).to_track_quat('-Z', 'Y')
    def frame(st, i):
        t = lerp(t0, t1, i / (n - 1)); dt = (t1 - t0) / (n - 1)
        st.set_time(t, dt, dict(haze=0.6, shutter=0.3))
        pos, q = cam_at(t); st.look(pos, None, 26.0, quat=q); st.key3(st.cam, cam_at, t, dt, True)
        p, v, ang = C.bomb_state(t)
        return t, dt, dict(samples=14, shutter=0.3, anchors={"target": (0, 0, 0)}, extra=dict(alt=float(p[2]), v=float(np.linalg.norm(v))))
    return n, frame

def _sim(i, pre, one):
    """Output frame -> (sim frame, t, dt): `pre` frames before the hit, then `one` frames 2x slow, then real time."""
    if i < pre:
        return 0, T_HIT - (pre - i) * SDT, SDT
    if i < pre + one:
        sf = i - pre + 1; return sf, T_HIT + (sf - 1) * SDT, SDT
    sf = one + 2 * (i - pre - one + 1); return sf, T_HIT + (sf - 1) * SDT, 2 * SDT

def shot_impact(n=150):
    """At the far end of the street: the canister bursts and the fire rolls down the street towards the camera."""
    def frame(st, i):
        sf, t, dt = _sim(i, 10, 70)
        st.set_time(t, dt, dict(shutter=0.3))
        u = i / (n - 1)
        pos = np.array([47.0 + 20.0 * smoothstep(0.25, 1.0, u), -2.6 - 1.5 * u, 1.7 + 5.0 * smoothstep(0.25, 1.0, u)]); tgt = np.array([14.0, -1.2, 3.2 + 5.0 * smoothstep(0.1, 1.0, u)])
        off, rq = shake(t - T_HIT - 0.55, 0.9)
        q = st.look(pos + off, tgt, 26.0); st.cam.rotation_quaternion = q @ rq
        return t, dt, dict(samples=14, sim=sf, shutter=0.3, anchors={"hit": (0, 0, 0.5)})
    return n, frame

def _ellipse(cx, cy, a, b):
    th = np.linspace(0, 2 * np.pi, 121); return [(cx + a * math.cos(x), cy + b * math.sin(x), 0.15) for x in th]

def shot_radius(n=96):
    """From the air, real time: the fire's footprint in the street, and the published footprint of a jet-delivered Mk 77."""
    def frame(st, i):
        sf = 1 + 2 * i; t = T_HIT + (sf - 1) * SDT; dt = 2 * SDT; u = i / (n - 1)
        st.set_time(t, dt, dict(shutter=0.3, haze=0.5))
        pos = np.array([-14.0 + 4 * u, -52.0, 50.0 + 3 * u]); st.look(pos, np.array([19.0, -1.0, 0.0]), 24.0)
        front = min(C.SMEAR_L, 46.0 * (t - T_HIT))
        an = {"sim": (FIRE_C[0] + C.SMEAR_L / 2, FIRE_C[1], 0.2), "pub": (C.FOOT_L - 10.0, FIRE_C[1] - C.FOOT_W / 2, 0.2), "hit": (0, 0, 0.3)}
        return t, dt, dict(samples=12, sim=sf, shutter=0.3, anchors=an, extra=dict(front=float(front)),
                           paths={"sim": _ellipse(FIRE_C[0], FIRE_C[1], C.SMEAR_L / 2, C.SMEAR_W / 2), "pub": _ellipse(C.FOOT_L / 2 - 10.0, FIRE_C[1], C.FOOT_L / 2, C.FOOT_W / 2)})
    return n, frame

def shot_after(n=84):
    """Forty seconds later: the street burnt black, fire still burning in places, smoke standing over the ruins."""
    A = np.array([42.0, -3.2, 1.8]); B = np.array([50.0, -6.0, 5.0]); E = np.array([60.0, -14.0, 17.0])
    def frame(st, i):
        t = T_HIT + 40.0 + i / FPS; dt = 1.0 / FPS
        st.set_time(t, dt, dict(motion_blur=False, plume=True, glow=False, haze=0.25))
        u = smoothstep(0.05, 1.0, i / (n - 1)); pos = (1 - u) ** 2 * A + 2 * u * (1 - u) * B + u * u * E
        st.look(pos, lerp(np.array([16.0, -1.5, 2.5]), np.array([16.0, -1.0, 6.0]), u), 26.0)
        return t, dt, dict(samples=20, anchors={"street": (16.0, -1.5, 0.2), "front": (15.0, 3.0, 3.0)})
    return n, frame

SHOTS = {"approach": shot_approach, "release": shot_release, "fall": shot_fall, "impact": shot_impact, "radius": shot_radius, "after": shot_after}

# ----------------------------------------------------------------------------- title card (studio)
def render_card(out_dir, res, spp, frames, n=72):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    pivot = bpy.data.objects.new("Pivot", None); sc.collection.objects.link(pivot)
    A = nuh60.build(); A["root"].parent = pivot; A["root"].location = (2.0, 0, 0)
    prof = [(-160.0, 0.0), (16.0, 0.0)] + [(16.0 + 5.0 * math.sin(a), 5.0 * (1 - math.cos(a))) for a in np.linspace(0, math.pi / 2, 12)[1:]] + [(21.0, 80.0)]
    V = np.array([[x, y, z] for (y, z) in prof for x in (-120.0, 120.0)])
    new_obj("Backdrop", new_mesh("bd", V, [grid_faces(len(prof), 2)]), None, simple_mat("BackdropMat", (0.64, 0.61, 0.56), rough=0.85))
    w = bpy.data.worlds.new("Studio"); sc.world = w; w.use_nodes = True
    w.node_tree.nodes["Background"].inputs[0].default_value = (0.75, 0.78, 0.82, 1); w.node_tree.nodes["Background"].inputs[1].default_value = 0.30
    def area(loc, size, power, color=(1, 1, 1)):
        L_ = bpy.data.lights.new("a", 'AREA'); L_.size = size; L_.energy = power; L_.color = color
        o = bpy.data.objects.new("a", L_); sc.collection.objects.link(o); o.location = loc
        o.rotation_euler = (Vector((0, 0, 2.0)) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    area((12.0, -15.0, 16.0), 14.0, 9000, (1.0, 0.96, 0.9)); area((-17.0, -10.0, 6.0), 16.0, 3000, (0.8, 0.9, 1.0)); area((-5.0, 14.0, 14.0), 12.0, 9000)
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); sc.collection.objects.link(cam); sc.camera = cam
    cam.data.lens = 85; cam.data.clip_start = 0.05; cam.data.clip_end = 600; cam.data.sensor_width = 36
    cam.location = (0.0, -64.0, 5.2); cam.rotation_euler = (math.radians(87.9), 0, 0); cam.data.shift_x = 0.25
    sc.render.engine = 'CYCLES'; c = sc.cycles; c.samples = spp or 28; c.use_denoising = True; c.denoising_quality = 'HIGH'; c.max_bounces = 6
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
        pivot.rotation_euler = (0, 0, math.radians(-132) + math.radians(18) * math.sin(2 * math.pi * u))
        nuh60.spin(A["main"], sc, 0.02 + i * 0.004, 0.0, C.MAIN_RPS); nuh60.spin(A["tail"], sc, 0.01, 0.0, C.TAIL_RPS)
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
    st = Stage(a.sim if a.shot in SIM_OF else None)
    sc = st.sc; sc.render.resolution_x, sc.render.resolution_y = res
    use_device(sc)
    os.makedirs(a.out, exist_ok=True)
    tl = dict(T_HIT=T_HIT, ALT=C.ALT, V_HELI=C.V_HELI, FWD=C.FWD, V_HIT=C.V_HIT, FALL_DEG=math.degrees(C.FALL_ANGLE), FOOT_L=C.FOOT_L, FOOT_W=C.FOOT_W, SMEAR_L=C.SMEAR_L, SMEAR_W=C.SMEAR_W, fps=FPS)
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
        m = dict(t=float(t), td=float(t - T_HIT), sim=int(sf), anchors={k: proj(p) for k, p in info.get("anchors", {}).items()})
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
