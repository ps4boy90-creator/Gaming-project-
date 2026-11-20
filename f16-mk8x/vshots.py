"""Shot definitions and frame renderer for the F-16 / Mk 82 / Mk 83 / Mk 84 explosion-comparison segment.

  python3 vshots.py <shot> <out_dir> [--sim <cache_root>] [--res 1280x720] [--spp N] [--frames a-b | i,j,k]

Shots: card, intro82/83/84 (studio); approach, release (air set); fall, impact82/83/84, radius82/83/84, after
(ground set).  The bombs are shown one at a time: each has its own introduction, impact and radius shot, and the
radius shots share one camera so that the growth from one bomb to the next can be read directly.
Time base: t = seconds after the Mk 82 is released; one sim frame is 1/60 s.  In the ground set the bunker being
hit stands at the origin ("focus"); the others are about 155 m up or down the run.
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
from qtruck import Piece
from qgeo import aim_quat, Shell, box as gbox, plate
from smoke_mat import blast_material
from util import *
import vconst as C, vf16

FPS = C.FPS; SDT = C.SIM_DT
D = math.radians
shake = gshots.shake
KINDS = C.ORDER; TAG = {"mk82": "82", "mk83": "83", "mk84": "84"}
FOCUS = {"fall": "mk82", "after": "mk83"}; SIM_OF = {}
for _k in KINDS:
    FOCUS["impact" + TAG[_k]] = _k; FOCUS["radius" + TAG[_k]] = _k; SIM_OF["impact" + TAG[_k]] = _k; SIM_OF["radius" + TAG[_k]] = _k
AIR = ("approach", "release")
STORE = {}

def _hit84():
    """A 2,000 lb bomb on a bunker this size: every roof bay fails; the middle ones fall in, the rest are thrown clear."""
    H = {}
    for i in range(4):
        for j in range(3):
            dx, dy = i - 1.5, j - 1.0
            if (i, j) in ((1, 1), (2, 1)):
                H[(i, j)] = ((0.5 * dx, 0.3, -3.0), 0.45 + 0.1 * (i - 1), 1.5 if i == 1 else -1.5)
            elif (i, j) in ((1, 2), (2, 0)):
                H[(i, j)] = ((1.5 * dx, 1.0 * dy, -2.0), 0.55, 1.2)
            else:
                H[(i, j)] = ((5.5 * dx + 1.5, 8.0 * dy + (1.0 if dy == 0 else 0.0), 9.0 + 1.5 * ((i + j) % 3)), 0.20, 5.0 if (i + j) % 2 else -5.0)
    return H

# ----------------------------------------------------------------------------- the bunkers
class Bunker:
    """Reinforced-concrete box with earth banked against three sides and a steel door in the open face (towards -Y).
    The roof is cast in twelve bays so that the bays a bomb breaks can fall in or be thrown clear.  What each bomb
    does follows the published picture for general-purpose bombs on hardened targets: cratering, spalling and a
    holed roof rather than a destroyed structure."""
    HIT = {"mk82": {(1, 1): ((0.6, 0.2, -2.5), 0.45, 1.6), (2, 1): ((5.0, 1.5, 8.0), 0.20, 5.0)},
           "mk83": {(1, 1): ((0.4, 0.3, -3.0), 0.40, 1.5), (2, 1): ((0.8, -0.3, -2.0), 0.55, -1.2), (1, 0): ((-2.0, -7.0, 9.0), 0.20, 6.0), (2, 0): ((3.0, -9.0, 7.0), 0.20, -5.0),
                    (1, 2): ((-1.0, 0.5, -2.5), 0.60, 1.0), (2, 2): ((7.0, 5.0, 10.0), 0.20, 4.0), (0, 1): ((-8.0, 1.0, 8.0), 0.20, -4.0), (3, 1): ((0.5, 0.0, -2.0), 0.50, 1.3)},
           "mk84": _hit84()}
    def __init__(self, col, name, kind, pos):
        B = C.BUNK; lx, ly, h, w, rt = B["lx"], B["ly"], B["h"], B["wall"], B["roof"]; self.kind = kind; self.pos = np.asarray(pos, float); o = self.pos
        mat = bpy.data.materials.get("BunkerConcrete") or htown.concrete_material("BunkerConcrete"); grey = (1, 1, 1, 1)
        S = Shell()
        for c, sz in (((0, ly / 2 - w / 2, (h - rt) / 2), (lx, w, h - rt)), ((-lx / 2 + w / 2, 0, (h - rt) / 2), (w, ly, h - rt)), ((lx / 2 - w / 2, 0, (h - rt) / 2), (w, ly, h - rt)),
                      ((-lx / 4 - 0.4, -ly / 2 + w / 2, (h - rt) / 2), (lx / 2 - 0.8, w, h - rt)), ((lx / 4 + 0.4, -ly / 2 + w / 2, (h - rt) / 2), (lx / 2 - 0.8, w, h - rt)),
                      ((0, -ly / 2 + w / 2, h - rt - 0.25), (1.6, w, 0.5))):
            S.add(*gbox(o + np.array(c), sz), color=grey)
        self.shell = new_obj(name + "_Walls", S.mesh(name + "_walls"), col, mat)
        I = Shell(); I.add(*gbox(o + np.array([0, 0, 0.06]), (lx - 2 * w, ly - 2 * w, 0.1)), color=(0.02, 0.02, 0.02, 1)); I.add(*gbox(o + np.array([0, -ly / 2 + w + 0.02, 1.0]), (1.5, 0.06, 2.0)), color=(0.05, 0.055, 0.05, 1))
        new_obj(name + "_Inside", I.mesh(name + "_inside"), col, simple_mat(name + "Dark", (0.03, 0.03, 0.03), rough=0.8))
        # earth bank on the two ends and the back
        E = Shell(); z1 = h - 0.35; run = 4.2; sand = (1, 1, 1, 1)
        ring = [(-lx / 2, -ly / 2), (-lx / 2, ly / 2), (lx / 2, ly / 2), (lx / 2, -ly / 2)]; out = [(-lx / 2 - run, -ly / 2 - 0.5), (-lx / 2 - run, ly / 2 + run), (lx / 2 + run, ly / 2 + run), (lx / 2 + run, -ly / 2 - 0.5)]
        V = np.array([[x, y, z1] for x, y in ring] + [[x, y, 0.0] for x, y in out]) + o[None]; E.add(V, np.array([[0, 1, 5, 4], [1, 2, 6, 5], [2, 3, 7, 6]]), None, sand)
        em = bpy.data.materials.get("BunkerEarth") or simple_mat("BunkerEarth", (0.33, 0.27, 0.19), rough=0.95)
        self.bank = new_obj(name + "_Bank", E.mesh(name + "_bank"), col, em)
        self.roof = {}; hit = self.HIT[kind]; bx, by = lx / 4, ly / 3
        for i in range(4):
            for j in range(3):
                c = np.array([-lx / 2 + bx * (i + 0.5), -ly / 2 + by * (j + 0.5), h - rt / 2]); P = Shell(); P.add(*gbox((0, 0, 0), (bx - 0.02, by - 0.02, rt)), color=grey)
                ob = new_obj("%s_Roof%d%d" % (name, i, j), P.mesh("%s_roof%d%d" % (name, i, j)), col, mat)
                if (i, j) in hit:
                    v0, zr, spin = hit[(i, j)]; rq = Quaternion((0.35 + 0.2 * i, 0.5 - 0.3 * j, 0.2), 0.5 + 0.25 * j).normalized() if zr > 0.3 else Quaternion((0.2, 1, 0.1), 0.15)
                    self.roof[(i, j)] = Piece(ob, o + c, v0, (0.6 - 0.3 * j, 1.0, 0.25 * i - 0.3), spin, zr, (rq.w, rq.x, rq.y, rq.z), drag=0.3)
                else:
                    ob.location = o + c
        sm, N, L, Pn = nodemat(name + "Scorch"); tc = N.new("ShaderNodeTexCoord"); sep = N.new("ShaderNodeSeparateXYZ"); L.new(tc.outputs["UV"], sep.inputs[0])
        nz = N.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 0.9; L.new(tc.outputs["Object"], nz.inputs["Vector"])
        ed = N.new("ShaderNodeMapRange"); ed.inputs["From Min"].default_value = 1.0; ed.inputs["From Max"].default_value = 0.35; L.new(sep.outputs["X"], ed.inputs["Value"])
        nm = N.new("ShaderNodeMapRange"); nm.inputs["From Min"].default_value = 0.25; nm.inputs["From Max"].default_value = 0.6; L.new(nz.outputs["Fac"], nm.inputs["Value"])
        self.gain = N.new("ShaderNodeValue"); m1 = N.new("ShaderNodeMath"); m1.operation = 'MULTIPLY'; L.new(ed.outputs[0], m1.inputs[0]); L.new(nm.outputs[0], m1.inputs[1])
        m2 = N.new("ShaderNodeMath"); m2.operation = 'MULTIPLY'; L.new(m1.outputs[0], m2.inputs[0]); L.new(self.gain.outputs[0], m2.inputs[1]); L.new(m2.outputs[0], Pn.inputs["Alpha"])
        Pn.inputs["Base Color"].default_value = (0.012, 0.011, 0.010, 1); Pn.inputs["Roughness"].default_value = 0.9
        R = 2.2 * C.R_STRUCT[kind] / 16.0 * 5.0; na, nr = 48, 6; a = np.linspace(0, 2 * np.pi, na, endpoint=False); r = np.linspace(0.02, 1.0, nr); A, Rr = np.meshgrid(a, r, indexing="ij")
        for zz, rad, nm_ in ((h + 0.012, min(R, 4.2), "roof"), (0.05, R, "ground")):
            V = np.stack([o[0] + rad * Rr * np.cos(A), o[1] + rad * Rr * np.sin(A), np.full_like(A, zz)], -1).reshape(-1, 3)
            if nm_ == "roof":
                V[:, 0] = np.clip(V[:, 0], o[0] - lx / 2, o[0] + lx / 2); V[:, 1] = np.clip(V[:, 1], o[1] - ly / 2, o[1] + ly / 2)
            ob = new_obj("%s_Scorch_%s" % (name, nm_), new_mesh("scorch", V, [grid_faces(na, nr, wrap_u=True)], uvs=np.stack([Rr, A / (2 * np.pi)], -1).reshape(-1, 2)), col, sm); ob.visible_shadow = False
    def update(self, td):
        for pc in self.roof.values():
            p, q = pc.at(td); pc.ob.location = p; pc.ob.rotation_quaternion = q
        self.gain.outputs[0].default_value = 0.9 * smoothstep(0.0, 0.25, td)

# ----------------------------------------------------------------------------- scene
def jet_xform(t):
    return C.jet_pos(t) + np.array([0, 0, 0.3 * math.sin(0.9 * t)]), Quaternion((1, 0, 0), D(1.5) * math.sin(0.7 * t)) @ Quaternion((0, 1, 0), D(-2.0))

def bomb_xform(which, t):
    """Target frame: on its pylon until released, then on its own trajectory, nose along the flight path."""
    t0 = C.REL[which]
    if t <= t0:
        p, q = jet_xform(t); return p + np.array(q @ Vector(STORE[which])), q
    so = np.array(jet_xform(t0)[1] @ Vector(STORE[which])); p0 = jet_xform(t0)[0] + so; p, v = C.bomb_state(which, t)
    return np.array([p[0] + so[0], p[1], p0[2] - (C.ALT - p[2])]), aim_quat(v)

class Stage(gshots.Stage):
    def __init__(self, air, focus="mk82", sim_dir=None):
        self.air = air; self.focus = focus; self.dom = None; self.off = np.zeros(3) if air else C.BUNKER[focus].copy()
        if sim_dir and os.path.exists(os.path.join(sim_dir, "sim.blend")):
            bpy.ops.wm.open_mainfile(filepath=os.path.join(sim_dir, "sim.blend"))
            for o in list(bpy.data.objects):
                if o.name.startswith("E_"):
                    bpy.data.objects.remove(o, do_unlink=True)
            self.dom = bpy.data.objects["BlastDomain"]; self.dom.data.materials.clear()
            self.fire0 = 34.0; bm_ = blast_material(density=7.5, fire=self.fire0, ambient=0.06); self.dom.data.materials.append(bm_); self.fire_node = bm_.node_tree.nodes[bm_["fire_node"]]
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
        self.jet = vf16.build(col); STORE.update(self.jet["pos"])
        self.bombs = {k: vf16.Bomb(col, vf16.BOMBS[k], k + "_dropped") for k in KINDS}
        for b in self.jet["bombs"].values():
            b.ob.hide_render = True
        if air:
            self.env_col, self.floor = qenv.build_air(sc, alt=C.ALT)
        else:
            rng = np.random.default_rng(11); np.random.seed(11); ec = self.env_col = bpy.data.collections.new("ENV"); sc.collection.children.link(ec)
            env.make_world(sc); self.ground = env.build_ground(ec); htown.sandy(self.ground); env.build_stones(ec, rng, -200.0); htown.desert_hills(ec, rng, 2.4)
            self.blast_node = self.ground.data.materials[0].node_tree.nodes["Blast"]
            self.bunkers = {k: Bunker(col, "Bunker_" + k, k, C.BUNKER[k] - self.off) for k in KINDS}
            s = C.R_STRUCT[focus] / 16.0
            self.frags = ms.FragField(col, n=260, rmax=C.R_BLAST[focus]); self.ejecta = ms.Ejecta(col, scale=1.6 * s)
            self.ejecta.c_ob.location = (0, 0, C.BUNK["h"]); self.ejecta.s_ob.location = (0, 0, C.BUNK["h"])
            self.l_hit = ms.point_light(col, "HitFlash", (1.0, 0.58, 0.26), 1.5); self.l_hit.location = (0.0, -1.0, C.BUNK["h"] + 2.0)
            self.plumes = {}
            for k in KINDS:
                p = Plume(col); q = C.BUNKER[k] - self.off
                for o in (p.ob, p.fl):
                    o.location = (q[0], q[1], C.BUNK["h"] - 2.2)
                p.ob.scale = {"mk82": (0.5, 0.5, 0.6), "mk83": (0.65, 0.65, 0.75), "mk84": (0.85, 0.85, 0.95)}[k]; p.glow.location = (q[0], q[1], C.BUNK["h"] + 0.5); self.plumes[k] = p
        cd = bpy.data.cameras.new("Cam"); self.cam = bpy.data.objects.new("Cam", cd); sc.collection.objects.link(self.cam); sc.camera = self.cam
        cd.clip_start = 0.05; cd.clip_end = 2.0e6 if air else 9000; cd.sensor_width = 36; cd.sensor_fit = 'HORIZONTAL'
        self.cam.rotation_mode = 'QUATERNION'
        self.setup_render()
        self.haze_mr = [nd for nd in sc.compositing_node_group.nodes if nd.bl_idname == "ShaderNodeMapRange"][0]; self.haze0 = 0.62
        # The depth pass is taken from single samples, so through smoke it flickers between the smoke and whatever lies behind it,
        # which speckled the haze.  A small blur of the haze amount removes the speckle.
        ng = sc.compositing_node_group; mix = [nd for nd in ng.nodes if nd.bl_idname == "ShaderNodeMix"][0]
        lk = [l for l in ng.links if l.to_node == mix and l.to_socket.name == "Factor"][0]; src = lk.from_socket; ng.links.remove(lk)
        bl = ng.nodes.new("CompositorNodeBlur"); bl.inputs["Size"].default_value[0] = 6.0; bl.inputs["Size"].default_value[1] = 6.0
        ng.links.new(src, bl.inputs["Image"]); ng.links.new(bl.outputs["Image"], mix.inputs["Factor"])
        if air:
            self.haze_mr.inputs["From Min"].default_value = 3000.0; self.haze_mr.inputs["From Max"].default_value = 90000.0; self.haze0 = 0.22
            for nd in sc.compositing_node_group.nodes:
                if nd.bl_idname == "ShaderNodeMath" and nd.operation == 'LESS_THAN':
                    nd.inputs[1].default_value = 5.0e6

    def w(self, p):
        """Target-frame point -> this stage's coordinates (air: relative to the aircraft's level track; ground: to the focus bunker)."""
        return np.asarray(p, float) - self.off

    def set_time(self, t, dt_out, opt):
        sc = self.sc; mb = opt.get("motion_blur", True); sc.render.use_motion_blur = mb
        self.haze_mr.inputs["To Max"].default_value = self.haze0 * opt.get("haze", 1.0)
        base = (lambda tt: C.jet_pos(tt)) if self.air else (lambda tt: self.off)          # air set: everything is seen from the aircraft's own track
        self.key3(self.jet["root"], lambda tt: (jet_xform(tt)[0] - base(tt), jet_xform(tt)[1]), t, dt_out, mb)
        for k, b in self.bombs.items():
            b.ob.hide_render = (t >= C.T_HIT[k])
            self.key3(b.ob, lambda tt, k=k: (bomb_xform(k, tt)[0] - base(tt), bomb_xform(k, tt)[1]), t, dt_out, mb)
        if self.air:
            self.floor.location = (-C.V_JET * t, 0, 0); return
        td = t - C.T_HIT[self.focus]; hit = td >= 0
        for k, bk in self.bunkers.items():
            bk.update(t - C.T_HIT[k])
        self.blast_node.outputs[0].default_value = 0.0
        self.frags.update(td if opt.get("frags", False) else -1.0, opt.get("frag_gain", 1.0)); self.ejecta.update(td if td < 7 else -1.0, 0.5 * dt_out)
        self.l_hit.data.energy = 900000.0 * (C.R_STRUCT[self.focus] / 16.0) ** 2 * math.exp(-td / 0.03) if 0 <= td < 0.3 else 0.0
        self.l_hit.hide_render = self.l_hit.data.energy < 5.0
        for k, p in self.plumes.items():                                  # concrete does not burn: grey-black smoke only, no flames
            p.update(bool(opt.get("plume", False)), t + {"mk82": 0.0, "mk83": 3.7, "mk84": 7.1}[k]); p.fl.hide_render = True; p.glow.hide_render = True
        if self.dom is not None:
            self.dom.hide_render = not hit
            self.fire_node.inputs[1].default_value = self.fire0 * (0.10 + 0.90 * math.exp(-max(td, 0.0) / 0.22))

# ----------------------------------------------------------------------------- shots: air set
def shot_approach(n=96):
    """Air to air on the sunlit side: the F-16 running in at 450 kt with a Mk 82 under the left wing, a Mk 83 under the right
    and a Mk 84 on the centre line."""
    def frame(st, i):
        t = -6.0 + i / FPS; dt = 1.0 / FPS; u = i / (n - 1)
        st.set_time(t, dt, {})
        a = D(lerp(32.0, 74.0, smoothstep(0, 1, u))); r = lerp(26.0, 20.0, u)
        pos = np.array([r * math.cos(a), r * math.sin(a), lerp(-3.5, 2.5, u)]); st.look(pos, np.array([0.0, 0.0, 0.0]), 36.0)
        return t, dt, dict(samples=24, shutter=0.4, anchors={k: tuple(st.jet["pos"][k]) for k in KINDS})
    return n, frame

def shot_release(n=144, lead=12):
    """From ahead and below, riding with the jet (3x slow): the Mk 82 leaves the left wing, the Mk 83 the right wing 0.6 s
    later, the Mk 84 the centre line 0.6 s after that."""
    def frame(st, i):
        if i < lead:
            t = -(lead - i) / FPS - 0.002; dt = 1.0 / FPS
        else:
            dt = 1.0 / 72.0; t = (i - lead) * dt
        st.set_time(t, dt, dict(shutter=0.2)); u = i / (n - 1)
        if not hasattr(st, "fill"):                                     # light thrown back up by the desert, so the underside reads
            fl = bpy.data.lights.new("GroundFill", 'SUN'); fl.energy = 1.3; fl.color = (1.0, 0.90, 0.76); fl.use_shadow = False
            st.fill = bpy.data.objects.new("GroundFill", fl); st.sc.collection.objects.link(st.fill); st.fill.rotation_euler = (math.pi * 0.94, 0.25, 0)
        d = max(0.0, 2.0 * t + 4.9 * t * t) if t > 0 else 0.0; d = 5.0 * (1.0 - math.exp(-d / 5.0))       # tilt down a little after the first bomb, then settle
        pos = np.array([11.4 - 1.0 * u, 0.5, -3.2 - 0.25 * d]); st.look(pos, np.array([-1.2, 0.0, -1.3 - 0.30 * d]), 28.0)
        an = {k: tuple(bomb_xform(k, t)[0] - C.jet_pos(t)) for k in KINDS}
        return t, dt, dict(samples=36, shutter=0.2, anchors=an)
    return n, frame

# ----------------------------------------------------------------------------- shots: ground set
def shot_fall(n=64):
    """Real time: the camera rides down behind the Mk 82 for its last 2.6 seconds, onto the first bunker."""
    T = C.T_HIT["mk82"]; t0, t1 = T - 2.65, T - 0.04
    def cam_at(st, t):
        p, q = bomb_xform("mk82", t); p = st.w(p); v = C.bomb_state("mk82", t)[1]; d = v / np.linalg.norm(v); up = np.array([0, 0, 1.0]) - d * d[2]; up /= np.linalg.norm(up)
        u = (t - t0) / (t1 - t0); pos = p - d * lerp(5.2, 4.2, u) + up * lerp(1.1, 0.9, u) + np.array([0, -0.7, 0])
        return pos, (Vector(p + d * 3.0) - Vector(pos)).to_track_quat('-Z', 'Y')
    def frame(st, i):
        t = lerp(t0, t1, i / (n - 1)); dt = (t1 - t0) / (n - 1)
        st.set_time(t, dt, dict(haze=0.6)); pos, q = cam_at(st, t); st.look(pos, None, 26.0, quat=q); st.key3(st.cam, lambda tt: cam_at(st, tt), t, dt, True)
        p, v = C.bomb_state("mk82", t)
        return t, dt, dict(samples=14, shutter=0.3, anchors={"target": (0, 0, C.BUNK["h"])}, extra=dict(alt=float(p[2]), v=float(np.linalg.norm(v))))
    return n, frame

def _sim(i, pre, one, T):
    if i < pre:
        return 0, T - (pre - i) * SDT, SDT
    if i < pre + one:
        sf = i - pre + 1; return sf, T + (sf - 1) * SDT, SDT
    sf = one + 2 * (i - pre - one + 1); return sf, T + (sf - 1) * SDT, 2 * SDT

def shot_impact(kind, n=120):
    """From the open side of the bunker: the bomb strikes the roof (2.5x slow, then 1.25x).  Same lens for every bomb; the
    camera stands back in proportion to the bomb's radius."""
    T = C.T_HIT[kind]; f = C.R_STRUCT[kind] / 16.0
    def frame(st, i):
        sf, t, dt = _sim(i, 8, 70, T); st.set_time(t, dt, {}); u = i / (n - 1)
        pos = np.array([16.0 * f + 3.0 * u, -44.0 * f - 5.0 * u, 2.2 + 1.5 * u]); tgt = np.array([2.0, 0.0, 4.5 * f + 7.0 * f * smoothstep(0.1, 1.0, u)])
        off, rq = shake(t - T - 0.13 * f, 2.4); q = st.look(pos + off, tgt, 27.0); st.cam.rotation_quaternion = q @ rq
        return t, dt, dict(samples=14, sim=sf, shutter=0.25, anchors={"hit": (0, 0, C.BUNK["h"])})
    return n, frame

def _circle(r):
    return [(r * math.cos(a), r * math.sin(a), 0.2) for a in np.linspace(0, 2 * np.pi, 97)]

def shot_radius(kind, n=96):
    """From the air, full frame, with exactly the same camera for all three bombs.  The circles of the smaller bombs
    already shown are passed on as well, so the overlay can draw them faintly for comparison."""
    T = C.T_HIT[kind]; prev = KINDS[:KINDS.index(kind)]
    def frame(st, i):
        sf = 1 + int(1.55 * i); t = T + (sf - 1) * SDT; dt = 1.55 * SDT
        st.set_time(t, dt, dict(frags=True, frag_gain=1.6, haze=0.5)); u = i / (n - 1)
        pos = np.array([-27.0 + 3 * u, -112.0, 126.0 + 3 * u]); st.look(pos, np.array([2.0, -14.0, 4.0]), 30.0)
        at = lambda r, a: (r * math.cos(D(a)), r * math.sin(D(a)), 0.2)
        an = {"struct": at(C.R_STRUCT[kind], -38), "blast": at(C.R_BLAST[kind], -142)}; paths = {"struct": _circle(C.R_STRUCT[kind]), "blast": _circle(C.R_BLAST[kind])}
        for k in prev:
            an["g_" + k] = at(C.R_BLAST[k], 90); paths["g_" + k] = _circle(C.R_BLAST[k])
        return t, dt, dict(samples=12, sim=sf, shutter=0.25, anchors=an, paths=paths)
    return n, frame

def shot_after(n=192):
    """Half a minute later: the camera travels down the run, stopping at each bunker in turn."""
    X = [float(C.BUNKER[k][0] - C.BUNKER["mk83"][0]) for k in KINDS]; t0 = C.T_HIT["mk84"] + 30.0
    def cam_at(st, t):
        u = min(max((t - t0) * FPS / (n - 1), -0.05), 1.05)
        x = X[0] + (X[1] - X[0]) * smoothstep(0.20, 0.42, u) + (X[2] - X[1]) * smoothstep(0.60, 0.82, u) + 14.0 * (u - 0.5)
        pos = np.array([x - 12.0, -45.0, 15.0 + 2.0 * u]); return pos, (Vector((x + 2.0, 0.0, 6.5)) - Vector(pos)).to_track_quat('-Z', 'Y')
    def frame(st, i):
        t = t0 + i / FPS; dt = 1.0 / FPS
        st.set_time(t, dt, dict(plume=True, haze=0.3)); pos, q = cam_at(st, t); st.look(pos, None, 28.0, quat=q); st.key3(st.cam, lambda tt: cam_at(st, tt), t, dt, True)
        return t, dt, dict(samples=32, shutter=0.35, anchors={k: (X[j], float(C.BUNKER[k][1] - C.BUNKER["mk83"][1]), 3.0) for j, k in enumerate(KINDS)})
    return n, frame

SHOTS = {"approach": shot_approach, "release": shot_release, "fall": shot_fall, "after": shot_after}
for _k in KINDS:
    SHOTS["impact" + TAG[_k]] = (lambda k=_k: shot_impact(k)); SHOTS["radius" + TAG[_k]] = (lambda k=_k: shot_radius(k))

# ----------------------------------------------------------------------------- title card (studio)
def _studio(spp, res):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    prof = [(-160.0, 0.0), (16.0, 0.0)] + [(16.0 + 5.0 * math.sin(a), 5.0 * (1 - math.cos(a))) for a in np.linspace(0, math.pi / 2, 12)[1:]] + [(21.0, 80.0)]
    V = np.array([[x, y, z] for (y, z) in prof for x in (-120.0, 120.0)])
    new_obj("Backdrop", new_mesh("bd", V, [grid_faces(len(prof), 2)]), None, simple_mat("BackdropMat", (0.64, 0.61, 0.56), rough=0.85))
    w = bpy.data.worlds.new("Studio"); sc.world = w; w.use_nodes = True
    w.node_tree.nodes["Background"].inputs[0].default_value = (0.75, 0.78, 0.82, 1); w.node_tree.nodes["Background"].inputs[1].default_value = 0.30
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); sc.collection.objects.link(cam); sc.camera = cam
    cam.data.clip_start = 0.05; cam.data.clip_end = 600; cam.data.sensor_width = 36
    sc.render.engine = 'CYCLES'; c = sc.cycles; c.samples = spp or 28; c.use_denoising = True; c.denoising_quality = 'HIGH'; c.max_bounces = 6
    use_device(sc)
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.view_settings.view_transform = 'AgX'; sc.view_settings.look = 'AgX - Medium High Contrast'
    sc.render.image_settings.file_format = 'PNG'; sc.render.use_persistent_data = True
    return sc, cam

def _area(sc, loc, size, power, color=(1, 1, 1), aim=(0, 0, 3.5)):
    L_ = bpy.data.lights.new("a", 'AREA'); L_.size = size; L_.energy = power; L_.color = color
    o = bpy.data.objects.new("a", L_); sc.collection.objects.link(o); o.location = loc
    o.rotation_euler = (Vector(aim) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()

def render_card(out_dir, res, spp, frames, n=72):
    sc, cam = _studio(spp, res)
    pivot = bpy.data.objects.new("Pivot", None); sc.collection.objects.link(pivot)
    A = vf16.build(); A["root"].parent = pivot; A["root"].location = (0.5, 0, 4.2); A["root"].rotation_quaternion = Quaternion((1, 0, 0), D(-16)) @ Quaternion((0, 1, 0), D(-5))
    _area(sc, (12.0, -15.0, 17.0), 14.0, 8000, (1.0, 0.96, 0.9)); _area(sc, (-17.0, -10.0, 6.0), 16.0, 2600, (0.8, 0.9, 1.0)); _area(sc, (-5.0, 14.0, 14.0), 12.0, 8000)
    cam.data.lens = 85; cam.location = (0.0, -62.0, 5.4); cam.rotation_euler = (math.radians(88.6), 0, 0); cam.data.shift_x = 0.25
    sc.render.use_border = True; sc.render.use_crop_to_border = True
    sc.render.border_min_x = 0.0; sc.render.border_max_x = 0.50; sc.render.border_min_y = 0.0; sc.render.border_max_y = 1.0
    os.makedirs(out_dir, exist_ok=True)
    for i in (frames if frames is not None else range(n)):
        u = i / n
        if os.path.exists(os.path.join(out_dir, "f%04d.png" % i)):
            continue
        pivot.rotation_euler = (0, 0, math.radians(-128) + math.radians(18) * math.sin(2 * math.pi * u))
        sc.render.filepath = os.path.join(out_dir, "f%04d.png" % i)
        t = time.time(); bpy.ops.render.render(write_still=True)
        print("FRAME card %d %.1fs" % (i, time.time() - t)); sys.stdout.flush()

def render_intro(kind, out_dir, res, spp, frames, n=108):
    """One bomb on the studio backdrop.  The camera, lens and distance are identical for all three, so each bomb appears at
    its true size relative to the others.  It turns from a three-quarter view to a side view and then rolls slowly; the
    nose, tail, top and bottom are projected for the overlay's dimension lines."""
    from bpy_extras.object_utils import world_to_camera_view
    sc, cam = _studio(spp or 40, res); spec = vf16.BOMBS[kind]; L_, Dm = spec["L"], spec["D"]
    for nd in bpy.data.materials["BackdropMat"].node_tree.nodes:        # a dark set, so the white figures of the overlay read
        if nd.type == 'BSDF_PRINCIPLED':
            nd.inputs["Base Color"].default_value = (0.085, 0.09, 0.10, 1)
    sc.world.node_tree.nodes["Background"].inputs[1].default_value = 0.12
    b = vf16.Bomb(sc.collection, spec, "Intro_" + kind); b.ob.location = (0, 0, 1.1)
    _area(sc, (5.0, -7.0, 8.0), 7.0, 2100, (1.0, 0.96, 0.9), aim=(0, 0, 1.1)); _area(sc, (-7.0, -5.0, 3.0), 8.0, 650, (0.8, 0.9, 1.0), aim=(0, 0, 1.1)); _area(sc, (-2.0, 6.0, 7.0), 6.0, 900, aim=(0, 0, 1.1))
    cam.data.lens = 50; cam.location = (0.0, -9.5, 1.3); cam.rotation_euler = (math.radians(88.8), 0, 0); cam.data.shift_x = 0.11; cam.data.shift_y = -0.0565
    os.makedirs(out_dir, exist_ok=True); meta_path = os.path.join(out_dir, "meta.json"); meta = json.load(open(meta_path)) if os.path.exists(meta_path) else {}
    for i in (frames if frames is not None else range(n)):
        fp = os.path.join(out_dir, "f%04d.png" % i)
        if os.path.exists(fp):
            continue
        u = i / (n - 1); yaw = D(38.0) * (1.0 - smoothstep(0.0, 0.42, u)); roll = D(40.0) * u
        q = Quaternion((0, 0, 1), yaw) @ Quaternion((1, 0, 0), roll); b.ob.rotation_quaternion = q; bpy.context.view_layer.update()
        proj = lambda p: (lambda v: [float(v.x), float(1 - v.y), float(v.z)])(world_to_camera_view(sc, cam, Vector(p)))
        c0 = Vector((0, 0, 1.1)); ax = Quaternion((0, 0, 1), yaw) @ Vector((1, 0, 0))
        meta[str(i)] = dict(t=i / FPS, yaw=float(yaw), anchors={"nose": proj(c0 + ax * L_ / 2), "tail": proj(c0 - ax * L_ / 2), "top": proj(c0 + Vector((0, 0, Dm / 2))), "bot": proj(c0 - Vector((0, 0, Dm / 2))),
                                                                 "m0": proj(c0 + Vector((-0.5, 0, 0))), "m1": proj(c0 + Vector((0.5, 0, 0))), "floor": proj((0, 0, 0))})
        sc.render.filepath = fp; t = time.time(); bpy.ops.render.render(write_still=True)
        print("FRAME intro%s %d %.1fs" % (TAG[kind], i, time.time() - t)); sys.stdout.flush(); json.dump(meta, open(meta_path, "w"))

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
    if a.shot.startswith("intro"):
        render_intro("mk" + a.shot[5:], a.out, res, a.spp, gshots.parse_frames(a.frames, 108) if a.frames else None)
        sys.stdout.flush(); os._exit(0)
    n, frame = SHOTS[a.shot]()
    frames = gshots.parse_frames(a.frames, n)
    st = Stage(a.shot in AIR, FOCUS.get(a.shot, "mk82"), os.path.join(a.sim, SIM_OF[a.shot]) if (a.sim and a.shot in SIM_OF) else None)
    sc = st.sc; sc.render.resolution_x, sc.render.resolution_y = res
    use_device(sc)
    os.makedirs(a.out, exist_ok=True)
    tl = dict(ALT=C.ALT, V_JET=C.V_JET, REL=C.REL, SEP=C.SEP, TOF=C.TOF, T_HIT=C.T_HIT, V_HIT=C.V_HIT, ANGLE=C.ANGLE, FWD=C.FWD, R_STRUCT=C.R_STRUCT, R_BLAST=C.R_BLAST, BUNKER_X={k: float(C.BUNKER[k][0]) for k in KINDS}, fps=FPS)
    json.dump(tl, open(os.path.join(os.path.dirname(os.path.abspath(a.out)), "timeline.json"), "w"))
    meta_path = os.path.join(a.out, "meta.json")
    meta = json.load(open(meta_path)) if os.path.exists(meta_path) else {}
    from bpy_extras.object_utils import world_to_camera_view
    T = C.T_HIT[FOCUS.get(a.shot, "mk82")]
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
        m = dict(t=float(t), td=float(t - T), sim=int(sf), anchors={k: proj(p) for k, p in info.get("anchors", {}).items()})
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
