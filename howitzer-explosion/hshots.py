"""Shot definitions and frame renderer for the 155 mm howitzer explosion-comparison segment.

  python3 hshots.py <shot> <out_dir> [--sim <cache_dir>] [--res 1280x720] [--spp N] [--frames a-b | i,j,k]

Shots: card, load, ram, charge, fire (gun position) and fall, impact, radius, after (town).
Time base: t = seconds after the charge fires; the shell lands at T_HIT.  One sim frame is 1/120 s.
"""
import bpy, sys, os, math, json, time, argparse
HERE = os.path.dirname(os.path.abspath(__file__))
for p in ("grenade-explosion", "rpg7-explosion", "mortar-explosion"):
    sys.path.insert(0, os.path.join(HERE, "..", p))
sys.path.insert(0, HERE)
import numpy as np
from mathutils import Vector, Quaternion
import manta_fix  # noqa: F401
import env, figure, fx
import shots as gshots
import mshots as ms
from smoke_mat import blast_material
from util import *
import hconst as C, h777, htown, hcrew
from h777 import aim_quat

FPS = C.FPS; DT = C.MASTER_DT; T_HIT = C.T_HIT
D = math.radians
shake = gshots.shake
SIM_OF = {"fire": "launch", "impact": "impact", "radius": "impact"}
SET_OF = {"load": "gun", "ram": "gun", "charge": "gun", "fire": "gun", "fall": "town", "impact": "town", "radius": "town", "after": "town"}

class Rings(ms.GroundRings):
    SPEC = [("lethal", C.LETHAL_R, 0.60, (1.0, 0.10, 0.05), 6.0), ("casualty", C.CASUALTY_R, 0.60, (1.0, 0.62, 0.10), 6.0), ("m67", C.M67_R, 0.30, (1.0, 0.92, 0.80), 5.0)]

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
            self.fire0 = 9.0 if kind == "launch" else 15.0
            bm_ = blast_material(density=5.0, fire=self.fire0, ambient=0.16) if kind == "launch" else blast_material(density=8.0, fire=self.fire0, ambient=0.06)
            self.dom.data.materials.append(bm_); self.fire_node = bm_.node_tree.nodes[bm_["fire_node"]]
            for nd in bm_.node_tree.nodes:
                if nd.type == 'VECT_MATH' and nd.operation == 'POWER':
                    nd.inputs[1].default_value = (0.72, 0.72, 0.72) if kind == "impact" else (0.62, 0.62, 0.62)
                if nd.type == 'VALTORGB':
                    for el, c in zip(sorted(nd.color_ramp.elements, key=lambda e: e.position),
                                     [(0, 0, 0), (0.55, 0.05, 0.0), (0.95, 0.22, 0.02), (1.0, 0.42, 0.07), (1.0, 0.62, 0.22)]):
                        el.color = (*c, 1)
            self.dom.hide_render = True
        else:
            bpy.ops.wm.read_factory_settings(use_empty=True)
        sc = self.sc = bpy.context.scene; sc.render.fps = FPS
        if which == "gun":
            self.env_col, self.ground = htown.build_gun_position(sc)
            self.ground.data.materials[0].node_tree.nodes["Blast"].outputs[0].default_value = 0.0
            col = self.col = bpy.data.collections.new("ACTION"); sc.collection.children.link(col)
            self.gun = h777.build_gun(col, elev=hcrew.EL_LOAD)
            for k in ("tube", "breech", "tray", "tray_arm"):
                self.gun[k].rotation_mode = 'QUATERNION'
            self.shell = h777.Shell(col); self.charge = h777.Charge(col); self.rammer = h777.build_rammer(col)
            self.rope = new_obj("Lanyard", bpy.data.meshes.new("rope"), col, simple_mat("LanyardMat", (0.42, 0.36, 0.24), rough=0.9))
            self.ghost = figure.ghost_material()
            self.men = {n: figure.Figure(col, "Ghost_" + n, self.ghost) for n in hcrew.NAMES}
            self.l_muzzle = ms.point_light(col, "MuzzleFlash", (1.0, 0.66, 0.38), 0.5); self.l_muzzle.location = C.MUZZLE + C.BORE * 1.0
        else:
            self.env_col, self.ground = htown.build_town(sc)
            self.blast_node = self.ground.data.materials[0].node_tree.nodes["Blast"]
            col = self.col = bpy.data.collections.new("ACTION"); sc.collection.children.link(col)
            self.town = htown.Town(col)
            self.shell = h777.Shell(col)
            self.frags = ms.FragField(col, n=760, rmax=C.CASUALTY_R); self.ejecta = ms.Ejecta(col, scale=1.7); self.rings = Rings(col)
            self.l_hit = ms.point_light(col, "HitFlash", (1.0, 0.56, 0.24), 1.2); self.l_hit.location = (0, -0.5, 1.8)
        cd = bpy.data.cameras.new("Cam"); self.cam = bpy.data.objects.new("Cam", cd); sc.collection.objects.link(self.cam); sc.camera = self.cam
        cd.clip_start = 0.02; cd.clip_end = 8000; cd.sensor_width = 36; cd.sensor_fit = 'HORIZONTAL'
        self.cam.rotation_mode = 'QUATERNION'
        self.setup_render()

    def _rope(self, t):
        a = hcrew.breech_pt(t, hcrew.LEVER); b = hcrew.lanyard_hand(t); L_ = np.linalg.norm(b - a)
        sag = max(0.0, 0.34 - 0.5 * max(L_ - 2.25, 0.0)) * min(1.0, L_ / 1.0) * (1 - smoothstep(-0.17, -0.03, t))
        u = np.linspace(0, 1, 14); path = a[None] * (1 - u)[:, None] + b[None] * u[:, None]; path[:, 2] -= sag * np.sin(np.pi * u)
        v, f, tt = tube(path, np.full(14, 0.006), 6); me = new_mesh("rope", v, [f]); me.materials.append(self.rope.data.materials[0])
        old = self.rope.data; self.rope.data = me; bpy.data.meshes.remove(old)

    def set_time(self, t, dt_out, opt):
        sc = self.sc; mb = opt.get("motion_blur", True); sc.render.use_motion_blur = mb
        if self.which == "gun":
            G = self.gun
            h777.set_elevation(G, hcrew.elev(t))
            G["tube"].location = (-C.recoil(t), 0, C.BZ)
            G["breech"].rotation_quaternion = Quaternion((0, 1, 0), hcrew.breech_angle(t)); h777.set_tray(G, hcrew.tray_phi(t))
            for n, fig in self.men.items():
                fig.set_pose(hcrew.pose(n, min(t, 2.0)))
            def sstate(tt):
                p, a = hcrew.shell_state(tt); return p, aim_quat(a)
            self.shell.set_visible(t < C.T_EXIT + 0.4)
            self.key3(self.shell.root, sstate, t, dt_out, mb and t > 0)
            self.charge.set_visible(-7.45 < t < 0)
            p, a = hcrew.charge_state(t); self.charge.root.location = p; self.charge.root.rotation_quaternion = aim_quat(a)
            rv = -10.6 < t < -8.25
            for o in self.rammer.children:
                o.hide_render = not rv
            p, a = hcrew.rammer_state(t); self.rammer.location = p; self.rammer.rotation_quaternion = aim_quat(a)
            self.rope.hide_render = t < -4.0
            if t >= -4.0:
                self._rope(t)
            self.l_muzzle.data.energy = 20000.0 * opt.get("flash", 1.0) * math.exp(-t / 0.014) if 0 <= t < 0.14 else 0.0
            self.l_muzzle.hide_render = self.l_muzzle.data.energy < 5.0
        else:
            td = t - T_HIT; hit = td >= 0
            self.shell.set_visible(not hit)
            if not hit:
                def fstate(tt):
                    p, v = C.fall_state(tt - T_HIT); v = v / np.linalg.norm(v)
                    return p - v * C.SHELL_LEN, aim_quat(v, 2 * math.pi * 1.5 * (tt - T_HIT))
                self.key3(self.shell.root, fstate, t, dt_out, mb)
            self.town.update(td)
            self.blast_node.outputs[0].default_value = 0.8 if hit else 0.0
            self.ground.data.shape_keys.key_blocks["Crater155"].value = 1.0 if hit else 0.0
            self.frags.update(td if opt.get("frags", True) else -1.0, opt.get("frag_gain", 1.0)); self.ejecta.update(td, 0.5 * dt_out)
            self.rings.update(opt.get("rings", {}))
            self.l_hit.data.energy = 260000.0 * opt.get("flash", 1.0) * math.exp(-td / 0.018) if 0 <= td < 0.25 else 0.0
            self.l_hit.hide_render = self.l_hit.data.energy < 5.0
        if self.dom is not None:
            self.dom.hide_render = t < self.T0
            self.fire_node.inputs[1].default_value = self.fire0 * (0.06 + 0.94 * math.exp(-max(t - self.T0, 0.0) / 0.05))

# ----------------------------------------------------------------------------- shots: gun position
def _rt(t0, n, cam):
    """Real-time shot from t0; cam(u, t) -> (pos, target, lens)."""
    def frame(st, i):
        t = t0 + i / FPS; dt = 1.0 / FPS
        st.set_time(t, dt, {})
        pos, tgt, lens = cam(i / (n - 1), t)
        st.look(np.array(pos), np.array(tgt), lens, fstop=5.6, focus=float(np.linalg.norm(np.array(tgt) - np.array(pos))))
        return t, dt, dict(samples=10, shutter=0.4, anchors={"breech": hcrew.bore_pt(t, C.S_BREECH)})
    return n, frame

def shot_load(n=90):
    """Breech opens, tray swings in, cannoneers 4 and 5 bring the projectile up and slide it onto the tray."""
    return _rt(-16.25, n, lambda u, t: ((-2.9 + 0.3 * u, 0.55, 3.40), (0.70, -0.60, 1.10), 26.0))

def shot_ram(n=52):
    """Seen from the right rear, outside the trail: the two cannoneers run the projectile home with the rammer staff."""
    return _rt(-10.5, n, lambda u, t: ((-5.2 + 0.25 * u, -3.0, 1.80), (-1.3, 0.0, 1.20), 24.0))

def shot_charge(n=90):
    """Cannoneer 2 loads the propelling charge and closes the breech; cannoneer 1 hooks the lanyard."""
    return _rt(-7.3, n, lambda u, t: ((-2.4 - 0.2 * u, -0.15, 3.05), (1.08, 0.0, 1.30), 28.0))

def shot_fire(n=112, lead=52):
    """The tube is laid to the firing elevation, the chief drops his arm, the lanyard is pulled - then slow motion."""
    def frame(st, i):
        if i < lead:
            sf = 0; t = -(lead - i) / FPS - 0.002; dt = 1.0 / FPS
        elif i < lead + 40:
            sf = i - lead + 1; t = (sf - 1) * DT; dt = DT
        else:
            sf = 40 + 2 * (i - lead - 40 + 1); t = (sf - 1) * DT; dt = 2 * DT
        st.set_time(t, dt, {})
        u = i / (n - 1)
        pos = np.array([7.4 - 0.5 * u, -7.9, 1.60 + 0.20 * u])
        tgt = np.array([1.7, 0.0, 2.10 + 0.35 * smoothstep(lead / n, 1.0, u)])
        off, rq = shake(t - 0.012, 2.2)
        q = st.look(pos + off, tgt, 23.0)
        st.cam.rotation_quaternion = q @ rq
        return t, dt, dict(samples=8, sim=sf, shutter=0.3, anchors={"muzzle": C.MUZZLE})
    return n, frame

# ----------------------------------------------------------------------------- shots: town
def shot_fall(n=72):
    """Real time, last three seconds of flight: the camera rides down behind the shell towards the town."""
    td0, td1 = -3.02, -0.03
    def cam_at(t):
        d = t - T_HIT; p, v = C.fall_state(d); v = v / np.linalg.norm(v)
        up = np.array([0, 0, 1.0]) - v * v[2]; up /= np.linalg.norm(up)
        u = (d - td0) / (td1 - td0)
        pos = p - v * lerp(2.9, 2.4, u) + up * lerp(0.60, 0.48, u) + np.array([0, -0.34, 0])
        aim = p + v * lerp(0.6, 0.0, u) + up * 0.10
        return pos, (Vector(aim) - Vector(pos)).to_track_quat('-Z', 'Y')
    def frame(st, i):
        td = lerp(td0, td1, i / (n - 1)); t = T_HIT + td; dt = (td1 - td0) / (n - 1)
        st.set_time(t, dt, {})
        pos, q = cam_at(t)
        st.look(pos, None, 24.0, quat=q)
        st.key3(st.cam, cam_at, t, dt, True)
        return t, dt, dict(samples=10, shutter=0.3, anchors={"target": (0, 0, 0)})
    return n, frame

def _slow(i, pre, one, k=2):
    if i < pre:
        return 0, T_HIT - (pre - i) * DT, DT
    if i < pre + one:
        sf = i - pre + 1; return sf, T_HIT + (sf - 1) * DT, DT
    sf = one + k * (i - pre - one + 1); return sf, T_HIT + (sf - 1) * DT, k * DT

def shot_impact(n=120):
    """Down the street: the shell comes in, bursts 3 m from the house front, and the front comes down."""
    def frame(st, i):
        sf, t, dt = _slow(i, 8, 52, 2)
        st.set_time(t, dt, {})
        u = i / (n - 1)
        pos = np.array([-13.0 - 0.4 * u, -4.5, 1.70 + 0.3 * u])
        tgt = np.array([0.5, 2.6, 2.8 + 1.6 * smoothstep(0.15, 1.0, u)])
        off, rq = shake(t - T_HIT - 0.06, 2.4)
        q = st.look(pos + off, tgt, 22.0)
        st.cam.rotation_quaternion = q @ rq
        return t, dt, dict(samples=8, sim=sf, shutter=0.25, anchors={"hit": (0, 0, 0.5)})
    return n, frame

def shot_radius(n=96, one=26):
    """From the air: fragment strikes spread out; the published lethal and casualty radii are drawn on the town."""
    def frame(st, i):
        if i < one:
            sf = i + 1; dt = DT
        else:
            sf = one + 2 * (i - one + 1); dt = 2 * DT
        td = (sf - 1) * DT; t = T_HIT + td
        r_front = min(C.CASUALTY_R, 900.0 * max(td - 0.004, 0.0))
        rings = {"lethal": min(C.LETHAL_R, r_front), "casualty": r_front if r_front >= C.LETHAL_R else 0.0, "m67": C.M67_R if td > 0.55 else 0.0}
        st.set_time(t, dt, dict(frag_gain=2.3))
        u = i / (n - 1)
        pos = np.array([-78.0 + 10 * u, -128.0 + 6 * u, 118.0 + 6 * u])
        st.look(pos, np.array([0.0, 8.0, 0.0]), 24.0)
        a_ = D(-48)
        an = {"centre": (0, 0, 0.3), "lethal": (C.LETHAL_R * math.cos(a_), C.LETHAL_R * math.sin(a_), 0.3), "casualty": (C.CASUALTY_R * math.cos(a_), C.CASUALTY_R * math.sin(a_), 0.3),
              "m67": (C.M67_R * math.cos(D(-160)), C.M67_R * math.sin(D(-160)), 0.3)}
        return t, dt, dict(samples=10, sim=sf, shutter=0.25, anchors=an, extra=dict(r_front=float(r_front)), circles=rings)
    return n, frame

def shot_after(n=84):
    """Aftermath: the crater in the street and the opened house, then up and back over the roofs."""
    A = np.array([-7.0, -4.9, 1.8]); B = np.array([-10.0, -5.4, 5.0]); E = np.array([-17.0, -11.0, 15.0])
    def frame(st, i):
        t = T_HIT + 20.0; dt = 1.0 / FPS
        st.set_time(t, dt, dict(motion_blur=False, frags=False))
        u = smoothstep(0.10, 1.0, i / (n - 1))
        pos = (1 - u) ** 2 * A + 2 * u * (1 - u) * B + u * u * E
        tgt = lerp(np.array([0.3, 2.4, 2.2]), np.array([1.0, 4.5, 2.2]), smoothstep(0.2, 1.0, u))
        st.look(pos, tgt, 24.0)
        return t, dt, dict(samples=12, anchors={"crater": (0, 0, 0.0), "wall": (0.0, htown.HIT_Y, 3.4)})
    return n, frame

SHOTS = {"load": shot_load, "ram": shot_ram, "charge": shot_charge, "fire": shot_fire, "fall": shot_fall, "impact": shot_impact, "radius": shot_radius,
         "after": shot_after}

# ----------------------------------------------------------------------------- title card (studio)
def render_card(out_dir, res, spp, frames, n=72):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    pivot = bpy.data.objects.new("Pivot", None); sc.collection.objects.link(pivot)
    G = h777.build_gun(elev=D(32.0)); G["root"].parent = pivot; G["root"].location = (-1.6, 0, 0)
    S = h777.Shell(); S.root.parent = pivot; S.root.location = (2.6, -2.2, 0.0); S.root.rotation_quaternion = aim_quat((0.0, 0.0, 1.0))
    prof = [(-80.0, 0.0), (7.5, 0.0)] + [(7.5 + 2.4 * math.sin(a), 2.4 * (1 - math.cos(a))) for a in np.linspace(0, math.pi / 2, 12)[1:]] + [(9.9, 40.0)]
    V = np.array([[x, y, z] for (y, z) in prof for x in (-60.0, 60.0)])
    new_obj("Backdrop", new_mesh("bd", V, [grid_faces(len(prof), 2)]), None, simple_mat("BackdropMat", (0.64, 0.61, 0.56), rough=0.85))
    w = bpy.data.worlds.new("Studio"); sc.world = w; w.use_nodes = True
    w.node_tree.nodes["Background"].inputs[0].default_value = (0.75, 0.78, 0.82, 1); w.node_tree.nodes["Background"].inputs[1].default_value = 0.30
    def area(loc, size, power, color=(1, 1, 1)):
        L_ = bpy.data.lights.new("a", 'AREA'); L_.size = size; L_.energy = power; L_.color = color
        o = bpy.data.objects.new("a", L_); sc.collection.objects.link(o); o.location = loc
        o.rotation_euler = (Vector((0, 0, 1.4)) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    area((8.0, -9.0, 9.5), 8.0, 2500, (1.0, 0.96, 0.9)); area((-10.0, -6.0, 3.5), 9.0, 800, (0.8, 0.9, 1.0)); area((-3.0, 8.0, 8.0), 7.0, 2700)
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); sc.collection.objects.link(cam); sc.camera = cam
    cam.data.lens = 85; cam.data.clip_start = 0.05; cam.data.sensor_width = 36
    cam.location = (0.0, -54.0, 2.6); cam.rotation_euler = (math.radians(88.6), 0, 0)
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
        if os.path.exists(os.path.join(out_dir, "f%04d.png" % i)):
            continue
        pivot.rotation_euler = (0, 0, math.radians(125) + math.radians(20) * math.sin(2 * math.pi * u))
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
    tl = dict(T_HIT=T_HIT, T_EXIT=C.T_EXIT, V0=C.V0, RANGE=C.RANGE, APEX=C.APEX, TOF=C.TOF, ELEV_DEG=math.degrees(C.ELEV), ELEV_MILS=math.degrees(C.ELEV) * 6400 / 360,
              V_HIT=C.V_HIT, FALL_DEG=math.degrees(C.FALL_ANGLE), LETHAL_R=C.LETHAL_R, CASUALTY_R=C.CASUALTY_R, M67_R=C.M67_R, fps=FPS)
    if st.which == "town":
        tl["gap"] = st.town.gap
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
        if st.which == "town" and td < 0:
            p, v = C.fall_state(td); m["alt"] = float(p[2]); m["v"] = float(np.linalg.norm(v)); m["dist"] = float(np.hypot(p[0], p[2]))
        if st.which == "gun":
            m["elev_mils"] = float(math.degrees(hcrew.elev(t)) * 6400 / 360); m["recoil"] = float(C.recoil(t))
        m.update(info.get("extra", {}))
        for name, r in info.get("circles", {}).items():
            pts = []
            for a_ in np.linspace(0, 2 * math.pi, 121):
                v = world_to_camera_view(sc, st.cam, Vector((r * math.cos(a_), r * math.sin(a_), 0.2))); pts.append([float(v.x), float(1 - v.y)])
            m["circle_" + name] = pts if r > 0.5 else []
        meta[str(i)] = m
        sc.render.filepath = fp
        bpy.ops.render.render(write_still=True)
        print("FRAME %s %d t=%.4f sim=%d %.1fs" % (a.shot, i, t, sf, time.time() - t0)); sys.stdout.flush()
        json.dump(meta, open(meta_path, "w"))
    sys.stdout.flush(); os._exit(0)

if __name__ == "__main__":
    main()
