"""Shot definitions and frame renderer for the M67 explosion-comparison segment.

  python3 shots.py <shot> <out_dir> [--sim <cache_dir>] [--res 1280x720] [--spp N] [--frames a-b | i,j,k]

Shots: card, throw, follow, macro, blast, top.   Time base: t = seconds after release;
the fuze fires at T_DET. After detonation every sim ("master") frame is 1/120 s.
"""
import bpy, sys, os, math, json, time, argparse
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import numpy as np
from mathutils import Vector, Quaternion, Matrix
import manta_fix  # noqa: F401
import env, grenade, figure, fx
from smoke_mat import blast_material
from util import *

FPS = 24
MASTER_DT = 1.0 / 120.0
R = grenade.R

# ----------------------------------------------------------------------------- grenade flight
class Trajectory:
    """Throw -> flight -> bounce -> roll -> rest, integrated once. Rest point is the world origin."""
    def __init__(self, v0=15.5, elev=math.radians(40.0), z0=1.93, dt=0.0005, t_end=7.0):
        n = int(t_end / dt) + 1
        self.dt = dt; self.t = np.arange(n) * dt
        s = np.zeros(n); z = np.zeros(n); vs_a = np.zeros(n); vz_a = np.zeros(n)
        q = np.zeros((n, 4)); self.events = []
        vs, vz = v0 * math.cos(elev), v0 * math.sin(elev)
        ps, pz = 0.0, z0
        mode = "air"
        quat = Quaternion((1, 0, 0), math.radians(25)) @ Quaternion((0, 1, 0), math.radians(-40))
        spin_axis = Vector((0.22, 1.0, 0.18)).normalized(); spin = 12.0
        t_rest = None
        for i in range(n):
            s[i], z[i], vs_a[i], vz_a[i] = ps, pz, vs, vz; q[i] = quat
            if mode == "air":
                vz -= 9.81 * dt; ps += vs * dt; pz += vz * dt
                if pz <= R and vz < 0:
                    pz = R; self.events.append((i * dt, ps, abs(vz)))
                    vz = -0.22 * vz; vs *= 0.50
                    spin_axis = Vector((0.05, 1.0, 0.1)).normalized(); spin = 0.45 * vs / R
                    if vz < 0.9:
                        mode = "roll"; vz = 0.0
                w = spin_axis * spin
            elif mode == "roll":
                vs = max(0.0, vs - 0.42 * 9.81 * dt); ps += vs * dt
                w = Vector((0.0, 1.0, 0.0)) * (0.5 * vs / R)
                if vs <= 0.0:
                    mode = "rest"; t_rest = i * dt
            else:
                w = Vector((0, 0, 0))
            ang = w.length * dt
            if ang > 1e-9:
                quat = (Quaternion(w.normalized(), ang) @ quat).normalized()
        self.t_rest = t_rest; self.t_land = self.events[0][0]
        # settle: let the fuze flop onto the ground over the last moments of the roll
        ir = int(t_rest / dt); q_end = Quaternion(q[ir])
        axis = q_end @ Vector((0, 0, 1))
        hd = math.atan2(axis.y, axis.x) if math.hypot(axis.x, axis.y) > 0.15 else 0.6
        th = math.radians(108)
        tgt_axis = Vector((math.cos(hd) * math.sin(th), math.sin(hd) * math.sin(th), math.cos(th)))
        fix = axis.rotation_difference(tgt_axis)
        i0 = int((t_rest - 0.30) / dt)
        for i in range(i0, n):
            u = smoothstep(0.0, 1.0, min(1.0, (i - i0) / max(1, (ir + int(0.10 / dt) - i0))))
            wob = 0.10 * math.exp(-max(0.0, (i - ir) * dt) / 0.10) * math.sin((i - ir) * dt * 38.0) if i > ir else 0.0
            qq = Quaternion((1, 0, 0, 0)).slerp(fix, u) @ Quaternion(q[min(i, ir)])
            if wob:
                qq = Quaternion(Vector((-math.sin(hd), math.cos(hd), 0)), wob) @ qq
            q[i] = qq
        self.s, self.z, self.q, self.vs, self.vz = s, z, q, vs_a, vz_a
        self.s_rest = s[-1]
        self.release = None; self.heading = 0.0
    def place(self, release_local_y, release_z):
        """World frame: rest at the origin; returns the thrower base x that makes the hand meet the path."""
        self.heading = math.atan2(-release_local_y, self.s_rest)
        ch, sh = math.cos(self.heading), math.sin(self.heading)
        self.release = np.array([-self.s_rest * ch, -self.s_rest * sh, 0.0])
        return self.release
    def _i(self, t):
        return int(min(max(t, 0.0), self.t[-1]) / self.dt)
    def pos(self, t):
        i = self._i(t); ch, sh = math.cos(self.heading), math.sin(self.heading)
        return np.array([self.release[0] + self.s[i] * ch, self.release[1] + self.s[i] * sh, self.z[i]])
    def vel(self, t):
        i = self._i(t); ch, sh = math.cos(self.heading), math.sin(self.heading)
        return np.array([self.vs[i] * ch, self.vs[i] * sh, self.vz[i]])
    def quat(self, t):
        return Quaternion(self.q[self._i(t)])
    def pos_smooth(self, t, w=0.07, n=9):
        return np.mean([self.pos(t + d) for d in np.linspace(-w, w, n)], axis=0)

TRAJ = Trajectory()
_p0 = figure.solve(figure.throw_pose(0.0))
_hand0 = _p0["wri_r"] + (_p0["wri_r"] - _p0["elb_r"]) / np.linalg.norm(_p0["wri_r"] - _p0["elb_r"]) * 0.085
TRAJ.__init__(z0=float(_hand0[2]))
_rel = TRAJ.place(float(_hand0[1]), float(_hand0[2]))
THROW_X = float(_rel[0] - _hand0[0])           # thrower base position on the X axis
THROW_BASE = np.array([THROW_X, 0.0, 0.0])
TRAJ.release = np.array([_rel[0], float(_hand0[1]), 0.0])
T_DET = round(TRAJ.t_rest + 0.95, 2)           # fuze delay (s after release)

def hand_grenade_pos(joints):
    hd = joints["wri_r"] - joints["elb_r"]; hd /= np.linalg.norm(hd)
    return THROW_BASE + joints["wri_r"] + hd * 0.085

# ----------------------------------------------------------------------------- scene
class Stage:
    def __init__(self, sim_dir=None, with_sim=True, top=False):
        self.dom = None
        if with_sim and sim_dir and os.path.exists(os.path.join(sim_dir, "sim.blend")):
            bpy.ops.wm.open_mainfile(filepath=os.path.join(sim_dir, "sim.blend"))
            for o in list(bpy.data.objects):
                if o.name.startswith("E_"):
                    bpy.data.objects.remove(o, do_unlink=True)
            self.dom = bpy.data.objects["BlastDomain"]
            self.dom.data.materials.clear(); self.dom.data.materials.append(blast_material())
            self.dom.hide_render = True
        else:
            bpy.ops.wm.read_factory_settings(use_empty=True)
        sc = self.sc = bpy.context.scene
        sc.render.fps = FPS
        self.env_col, self.ground = env.build(sc, THROW_X)
        self.blast_node = self.ground.data.materials[0].node_tree.nodes["Blast"]
        col = self.col = bpy.data.collections.new("ACTION"); sc.collection.children.link(col)
        self.gren, _ = grenade.build(col, with_pin=False, with_lever=False, name="Grenade")
        self.gren.rotation_mode = 'QUATERNION'
        mats = {m.name: m for m in bpy.data.materials}
        self.lever = grenade.build_lever(col, mats["GrenadeLever"], "Spoon"); self.lever.rotation_mode = 'QUATERNION'
        self.ghost = figure.ghost_material()
        self.thrower = figure.Figure(col, "Thrower", self.ghost); self.thrower.ob.location = THROW_BASE
        self.extras = []
        if top:      # standing silhouettes for scale on the radius rings
            for name, (x, y), yaw in (("Scale5", (5.0 * math.cos(-0.62), 5.0 * math.sin(-0.62)), 2.6), ("Scale15", (15.0 * math.cos(-0.62), 15.0 * math.sin(-0.62)), 2.5)):
                f = figure.Figure(col, name, self.ghost); f.set_pose(figure.STAND)
                f.ob.location = (x, y, float(env.ground_h(x, y))); f.ob.rotation_euler = (0, 0, yaw); self.extras.append(f)
        self.blast = fx.Blast(col)
        self.rings = fx.Rings(col, env.ground_h)
        self.puffs = []
        for k, (te, se, vimp) in enumerate(TRAJ.events[:2]):
            p = TRAJ.pos(te); self.puffs.append((te, min(1.0, vimp / 9.0), fx.Puff(col, "Puff%d" % k, (p[0], p[1], 0.0), seed=3.0 + k)))
        cd = bpy.data.cameras.new("Cam"); self.cam = bpy.data.objects.new("Cam", cd); sc.collection.objects.link(self.cam); sc.camera = self.cam
        cd.clip_start = 0.02; cd.clip_end = 6000; cd.sensor_width = 36; cd.sensor_fit = 'HORIZONTAL'
        self.cam.rotation_mode = 'QUATERNION'
        self._pose_t = None
        self.setup_render()

    def setup_render(self):
        sc = self.sc
        sc.render.engine = 'CYCLES'; c = sc.cycles
        c.device = 'CPU'; c.use_denoising = True; c.denoiser = 'OPENIMAGEDENOISE'; c.denoising_quality = 'FAST'
        c.denoising_input_passes = 'RGB_ALBEDO_NORMAL'
        c.use_adaptive_sampling = False
        c.max_bounces = 6; c.diffuse_bounces = 2; c.glossy_bounces = 3; c.transmission_bounces = 6; c.transparent_max_bounces = 6
        c.volume_bounces = 2; c.volume_step_rate = 1.25; c.volume_max_steps = 256
        c.caustics_reflective = False; c.caustics_refractive = False; c.sample_clamp_indirect = 8.0; c.sample_clamp_direct = 0.0
        sc.render.use_persistent_data = True
        sc.render.image_settings.file_format = 'PNG'; sc.render.image_settings.color_mode = 'RGB'; sc.render.image_settings.compression = 20
        sc.view_settings.view_transform = 'AgX'; sc.view_settings.look = 'AgX - Medium High Contrast'; sc.view_settings.exposure = 0.0
        sc.render.threads_mode = 'AUTO'
        bpy.context.view_layer.use_pass_z = True
        self.setup_compositor()

    def setup_compositor(self):
        sc = self.sc
        ng = bpy.data.node_groups.new("Comp", "CompositorNodeTree")
        ng.interface.new_socket(name="Image", in_out='OUTPUT', socket_type='NodeSocketColor')
        N = ng.nodes; L = ng.links
        rl = N.new("CompositorNodeRLayers"); out = N.new("NodeGroupOutput")
        # aerial perspective from depth (not applied to the sky itself)
        mr = N.new("ShaderNodeMapRange"); mr.inputs["From Min"].default_value = 45.0; mr.inputs["From Max"].default_value = 2400.0
        mr.inputs["To Min"].default_value = 0.0; mr.inputs["To Max"].default_value = 0.62; mr.clamp = True
        L.new(rl.outputs["Depth"], mr.inputs["Value"])
        pw = N.new("ShaderNodeMath"); pw.operation = 'POWER'; pw.inputs[1].default_value = 0.72; L.new(mr.outputs["Result"], pw.inputs[0])
        lt = N.new("ShaderNodeMath"); lt.operation = 'LESS_THAN'; lt.inputs[1].default_value = 50000.0; L.new(rl.outputs["Depth"], lt.inputs[0])
        fac = N.new("ShaderNodeMath"); fac.operation = 'MULTIPLY'; L.new(pw.outputs[0], fac.inputs[0]); L.new(lt.outputs[0], fac.inputs[1])
        mix = N.new("ShaderNodeMix"); mix.data_type = 'RGBA'
        mix.inputs["B"].default_value = (0.62, 0.72, 0.86, 1.0)
        L.new(fac.outputs[0], mix.inputs["Factor"]); L.new(rl.outputs["Image"], mix.inputs["A"])
        gl = N.new("CompositorNodeGlare")
        gl.inputs["Type"].default_value = 'Bloom'; gl.inputs["Threshold"].default_value = 1.6; gl.inputs["Strength"].default_value = 0.35
        gl.inputs["Size"].default_value = 0.55; gl.inputs["Smoothness"].default_value = 0.3
        L.new(mix.outputs["Result"], gl.inputs["Image"])
        L.new(gl.outputs["Image"], out.inputs[0])
        sc.compositing_node_group = ng
        sc.render.use_compositing = True
        sc.render.compositor_device = 'CPU'
        self.haze_mix = mix; self.glare = gl

    # ---- per-frame state
    def set_time(self, t, dt_out, opt):
        """Put every animated element at real time t (s after release). dt_out = real seconds per output frame."""
        sc = self.sc
        td = t - T_DET
        # thrower (only re-meshed when it can be seen / changes)
        if opt.get("thrower", True):
            tp = min(t, 2.5)
            if self._pose_t is None or abs(tp - self._pose_t) > 1e-6:
                self.joints = self.thrower.set_pose(figure.throw_pose(tp)); self._pose_t = tp
            self.thrower.ob.hide_render = False
        else:
            self.thrower.ob.hide_render = True
            self.joints = figure.solve(figure.throw_pose(min(t, 2.5)))
        # grenade + spoon
        def gstate(tt):
            if tt < 0:
                j = figure.solve(figure.throw_pose(tt))
                return hand_grenade_pos(j), TRAJ.quat(0.0)
            p = TRAJ.pos(tt); p[2] += float(env.ground_h(p[0], p[1])) * (1.0 if tt > TRAJ.t_land else 0.0)
            return p, TRAJ.quat(tt)
        self.gstate = gstate
        exploded = bool(td >= 0)
        self.gren.hide_render = exploded
        for ch in self.gren.children:
            ch.hide_render = exploded
        mb = opt.get("motion_blur", False)
        sc.render.use_motion_blur = mb
        place = lambda ob, fn: self.key3(ob, fn, t, dt_out, mb)
        place(self.gren, gstate)
        def lstate(tt):
            if tt < 0.05:
                return gstate(tt)
            tau = tt - 0.05
            p0, q0 = gstate(0.05)
            v = TRAJ.vel(0.05) + np.array([-2.2, -1.4, 2.4])
            p = p0 + v * tau + np.array([0, 0, -4.905]) * tau * tau
            q = Quaternion(Vector((0.5, 0.8, 0.3)).normalized(), 30.0 * tau) @ q0
            return p, q
        self.lever.hide_render = bool(exploded or (t > 0.05 and lstate(t)[0][2] < 0.03))
        place(self.lever, lstate)
        # landing puffs
        for te, strength, puff in self.puffs:
            puff.update(t - te if opt.get("puffs", True) else -1.0, strength, drift=TRAJ.vel(te - 0.01) * 0.08)
        # blast
        self.blast_node.outputs[0].default_value = 1.0 if exploded else 0.0
        self.ground.data.shape_keys.key_blocks["Crater"].value = 1.0 if exploded else 0.0
        self.blast.update(td, shutter=0.5 * dt_out, frag_width=opt.get("frag_width", 1.0), flash_scale=opt.get("flash", 1.0),
                          frag_reach=opt.get("frag_reach", 1.0))
        if self.dom is not None:
            self.dom.hide_render = not exploded
        self.rings.update(opt.get("rings", {}))

    def key3(self, ob, fn, t, dt_out, mb=True):
        """Place `ob` at fn(t) -> (loc, quat); with motion blur, add linear keys one output frame either side."""
        ob.animation_data_clear()
        F = self.sc.frame_current
        if mb:
            for k in (-1, 0, 1):
                loc, q = fn(t + k * dt_out)
                ob.location = loc; ob.rotation_quaternion = q
                ob.keyframe_insert("location", frame=F + k); ob.keyframe_insert("rotation_quaternion", frame=F + k)
            act = ob.animation_data.action
            try:
                fcs = list(act.fcurves)
            except AttributeError:
                fcs = [fc for layer in act.layers for strip in layer.strips for bag in strip.channelbags for fc in bag.fcurves]
            for fc in fcs:
                for kp in fc.keyframe_points:
                    kp.interpolation = 'LINEAR'
        loc, q = fn(t); ob.location = loc; ob.rotation_quaternion = q

    def look(self, pos, target, lens, roll=0.0, fstop=None, focus=None, quat=None):
        cam = self.cam; cam.animation_data_clear()
        cam.location = pos
        if quat is None:
            d = Vector(target) - Vector(pos)
            quat = d.to_track_quat('-Z', 'Y')
            if roll:
                quat = quat @ Quaternion((0, 0, 1), roll)
        cam.rotation_quaternion = quat
        cam.data.lens = lens
        if fstop:
            cam.data.dof.use_dof = True; cam.data.dof.aperture_fstop = fstop
            cam.data.dof.focus_distance = focus if focus else (Vector(target) - Vector(pos)).length
        else:
            cam.data.dof.use_dof = False
        return quat

def shake(tt, amp, seed=0.0):
    """Decaying camera shake: returns (position offset, small rotation quaternion)."""
    if tt <= 0:
        return np.zeros(3), Quaternion()
    a = amp * math.exp(-tt / 0.30) * min(1.0, tt / 0.004)
    s = lambda f, ph: math.sin(2 * math.pi * f * tt + ph + seed)
    off = np.array([s(19, 0.3) + 0.5 * s(43, 1.1), s(23, 2.1) + 0.5 * s(37, 0.2), s(17, 4.0) + 0.5 * s(51, 2.9)]) * 0.012 * a
    rot = Quaternion((1, 0, 0), 0.010 * a * (s(21, 1.7) + 0.5 * s(47, 0.4))) @ Quaternion((0, 1, 0), 0.008 * a * (s(26, 3.3) + 0.5 * s(39, 5.0))) \
        @ Quaternion((0, 0, 1), 0.006 * a * s(15, 0.9))
    return off, rot

# ----------------------------------------------------------------------------- shots
def sim_frame(t):
    return int(round((t - T_DET) / MASTER_DT)) + 1 if t >= T_DET - 1e-9 else 0

def shot_throw(n=70):
    t0, t1 = -1.72, 0.50
    def frame(st, i):
        u = i / (n - 1); t = lerp(t0, t1, u); dt = (t1 - t0) / (n - 1)
        opt = dict(motion_blur=True)
        st.set_time(t, dt, opt)
        B = THROW_BASE
        pos = B + np.array([-2.75 + 0.55 * u, -3.55 + 0.25 * u, 1.18 + 0.10 * u])
        g, _ = st.gstate(t)
        body = B + np.array([0.35, 0.0, 1.28])
        w = smoothstep(0.02, 0.50, t)
        tgt = body * (1 - 0.22 * w) + (0.22 * w) * np.array([g[0], g[1], g[2]])
        st.look(pos, tgt, 30.0, fstop=4.0, focus=float(np.linalg.norm(body - pos)))
        return t, dt, dict(samples=10, anchors={"grenade": g})
    return n, frame

def shot_follow(n=88):
    t0, t1 = 0.42, TRAJ.t_land + 0.62
    def cam_at(t):
        u = (t - t0) / (t1 - t0)
        g = TRAJ.pos_smooth(t)
        off = np.array([lerp(-0.50, 0.20, smoothstep(0, 1, u)), lerp(-0.40, -0.52, u), lerp(0.13, 0.05, u)])
        pos = g + off
        pos[2] = max(pos[2], 0.085 + float(env.ground_h(pos[0], pos[1])))
        aim = TRAJ.pos_smooth(t, 0.03) + np.array([0.03, 0, 0.0])
        return pos, (Vector(aim) - Vector(pos)).to_track_quat('-Z', 'Y')
    def frame(st, i):
        u = i / (n - 1); t = lerp(t0, t1, u); dt = (t1 - t0) / (n - 1)
        st.set_time(t, dt, dict(motion_blur=True, thrower=False))
        pos, q = cam_at(t)
        st.look(pos, None, 50.0, fstop=5.6, focus=float(np.linalg.norm(TRAJ.pos(t) - pos)), quat=q)
        st.key3(st.cam, cam_at, t, dt, True)      # camera travels with the grenade -> streaked background
        return t, dt, dict(samples=10, shutter=0.45, anchors={"grenade": TRAJ.pos(t)})
    return n, frame

def shot_macro(n=46):
    """Ground-level beauty shot: the grenade rolls past the lens, settles, and sits there until the fuze runs out."""
    def frame(st, i):
        t = T_DET - (n - i) / FPS; dt = 1.0 / FPS
        st.set_time(t, dt, dict(motion_blur=True, thrower=False))
        u = i / (n - 1)
        pos = np.array([-0.72 + 0.06 * u, 0.44 - 0.03 * u, 0.090 + 0.004 * math.sin(u * 5.0)])
        tgt = np.array([0.0, 0.0, 0.038])
        st.look(pos, tgt, 80.0, fstop=8.0, focus=float(np.linalg.norm(tgt - pos)) - 0.012)
        return t, dt, dict(samples=12, shutter=0.4, anchors={"grenade": TRAJ.pos(t)})
    return n, frame

def shot_blast(n=88):
    pre, one = 4, 62
    def frame(st, i):
        if i < pre:
            sf = 0; t = T_DET - (pre - i) * MASTER_DT; dt = MASTER_DT
        elif i < pre + one:
            sf = i - pre + 1; t = T_DET + (sf - 1) * MASTER_DT; dt = MASTER_DT
        else:
            sf = one + 2 * (i - pre - one + 1); t = T_DET + (sf - 1) * MASTER_DT; dt = 2 * MASTER_DT
        st.set_time(t, dt, dict(thrower=False, puffs=False))
        u = i / (n - 1)
        pos = np.array([2.35 - 0.25 * u, -5.9 + 0.55 * u, 0.58 + 0.05 * u])
        tgt = np.array([0.0, 0.0, 0.85 + 0.75 * smoothstep(0.1, 1.0, u)])
        off, rq = shake(t - T_DET - 0.016, 1.6)
        q = st.look(pos + off, tgt, 28.0, fstop=5.6, focus=6.0)
        st.cam.rotation_quaternion = q @ rq
        return t, dt, dict(samples=10, sim=sf, anchors={"blast": (0, 0, 0)})
    return n, frame

def shot_top(n=112):
    """Straight-down view: tight on the 5 m kill ring for the detonation, then a pull-back that reveals the 15 m ring."""
    lead = 30
    def frame(st, i):
        if i < lead:
            sf = 0; t = T_DET - (lead - i) / FPS; dt = 1.0 / FPS
        else:
            sf = 1 + 2 * (i - lead); t = T_DET + (sf - 1) * MASTER_DT; dt = 2 * MASTER_DT
        rings = dict(kill=smoothstep(3, 17, i), casualty=smoothstep(42, 64, i), ticks=smoothstep(1, 22, i) * (5.2 / 15.0) + smoothstep(40, 60, i) * (9.8 / 15.0))
        st.set_time(t, dt, dict(thrower=True, puffs=False, rings=rings, frag_width=5.0, frag_reach=2.2, flash=2.5))
        H = 15.5 + 22.5 * smoothstep(38, 80, i) + 1.5 * (i / (n - 1))
        off, rq = shake(t - T_DET - 0.05, 0.5)
        q = Quaternion((0, 0, 1), math.radians(-4.0 + 8.0 * i / (n - 1)))
        st.look(np.array([0.5, 0.0, H]) + off * 3, None, 20.0, quat=q @ rq)
        an = {"blast": (0, 0, 0.1), "kill": (5.0 * math.cos(-0.35), 5.0 * math.sin(-0.35), 0.1),
              "casualty": (15.0 * math.cos(0.42), 15.0 * math.sin(0.42), 0.1), "thrower": (THROW_X, 0, 1.0)}
        return t, dt, dict(samples=8, sim=sf, anchors=an)
    return n, frame

SHOTS = {"throw": shot_throw, "follow": shot_follow, "macro": shot_macro, "blast": shot_blast, "top": shot_top}

# ----------------------------------------------------------------------------- title card (studio turntable)
def render_card(out_dir, res, spp, frames, n=72):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    root, lever = grenade.build(with_pin=True, with_lever=True)
    root.rotation_mode = 'XYZ'
    # seamless backdrop
    prof = [(-3.0, -0.11), (0.6, -0.11)] + [(0.6 + 0.6 * math.sin(a), -0.11 + 0.6 * (1 - math.cos(a))) for a in np.linspace(0, math.pi / 2, 12)[1:]] + [(1.2, 3.0)]
    V = np.array([[x, y, z] for (y, z) in prof for x in (-4.0, 4.0)])
    bd = new_obj("Backdrop", new_mesh("bd", V, [grid_faces(len(prof), 2)]), None, simple_mat("BackdropMat", (0.64, 0.61, 0.56), rough=0.85))
    w = bpy.data.worlds.new("Studio"); sc.world = w; w.use_nodes = True
    w.node_tree.nodes["Background"].inputs[0].default_value = (0.75, 0.78, 0.82, 1); w.node_tree.nodes["Background"].inputs[1].default_value = 0.30
    def area(loc, size, power, color=(1, 1, 1)):
        L_ = bpy.data.lights.new("a", 'AREA'); L_.size = size; L_.energy = power; L_.color = color
        o = bpy.data.objects.new("a", L_); sc.collection.objects.link(o); o.location = loc
        o.rotation_euler = (-Vector(loc)).to_track_quat('-Z', 'Y').to_euler(); return o
    area((0.30, -0.34, 0.34), 0.38, 7.5, (1.0, 0.96, 0.9)); area((-0.42, -0.16, 0.04), 0.45, 2.2, (0.8, 0.9, 1.0)); area((-0.12, 0.34, 0.28), 0.30, 9.0)
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); sc.collection.objects.link(cam); sc.camera = cam
    cam.data.lens = 85; cam.data.clip_start = 0.01; cam.data.sensor_width = 36
    cam.location = (0.0, -0.60, 0.035); cam.rotation_euler = (math.radians(89.0), 0, 0)
    cam.data.shift_x = 0.235                                 # grenade sits in the left third
    cam.data.dof.use_dof = True; cam.data.dof.aperture_fstop = 8.0; cam.data.dof.focus_distance = 0.60
    sc.render.engine = 'CYCLES'; c = sc.cycles; c.samples = spp or 14; c.use_denoising = True; c.denoising_quality = 'HIGH'
    c.max_bounces = 6
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.use_border = True; sc.render.use_crop_to_border = True
    sc.render.border_min_x = 0.0; sc.render.border_max_x = 0.50; sc.render.border_min_y = 0.0; sc.render.border_max_y = 1.0
    sc.view_settings.view_transform = 'AgX'; sc.view_settings.look = 'AgX - Medium High Contrast'
    sc.render.image_settings.file_format = 'PNG'; sc.render.use_persistent_data = True
    os.makedirs(out_dir, exist_ok=True)
    for i in (frames if frames is not None else range(n)):
        u = i / n
        root.rotation_euler = (math.radians(14), math.radians(-9), 2 * math.pi * u + math.radians(200))
        root.location = (0, 0, 0.004 * math.sin(2 * math.pi * u * 2))
        sc.render.filepath = os.path.join(out_dir, "f%04d.png" % i)
        t = time.time(); bpy.ops.render.render(write_still=True)
        print("FRAME card %d %.1fs" % (i, time.time() - t)); sys.stdout.flush()

# ----------------------------------------------------------------------------- driver
def parse_frames(s, n):
    if not s:
        return list(range(n))
    if "-" in s and "," not in s:
        a, b = s.split("-"); return list(range(int(a), min(int(b), n - 1) + 1))
    return [int(x) for x in s.split(",")]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("shot"); ap.add_argument("out")
    ap.add_argument("--sim", default=None); ap.add_argument("--res", default="1280x720")
    ap.add_argument("--spp", type=int, default=0); ap.add_argument("--frames", default="")
    ap.add_argument("--save-blend", default="")
    a = ap.parse_args(sys.argv[1:])
    res = tuple(int(x) for x in a.res.split("x"))
    if a.shot == "card":
        render_card(a.out, res, a.spp, parse_frames(a.frames, 72) if a.frames else None)
        sys.stdout.flush(); os._exit(0)
    n, frame = SHOTS[a.shot]()
    frames = parse_frames(a.frames, n)
    need_sim = a.shot in ("blast", "top")
    st = Stage(a.sim, with_sim=need_sim, top=(a.shot == "top"))
    sc = st.sc
    sc.render.resolution_x, sc.render.resolution_y = res
    os.makedirs(a.out, exist_ok=True)
    json.dump(dict(T_DET=T_DET, events=[e[0] for e in TRAJ.events], t_rest=TRAJ.t_rest, throw_x=THROW_X, fps=FPS),
              open(os.path.join(os.path.dirname(os.path.abspath(a.out)), "timeline.json"), "w"))
    meta_path = os.path.join(a.out, "meta.json")
    meta = json.load(open(meta_path)) if os.path.exists(meta_path) else {}
    from bpy_extras.object_utils import world_to_camera_view
    for i in frames:
        fp = os.path.join(a.out, "f%04d.png" % i)
        if os.path.exists(fp) and not a.save_blend:
            continue
        t0 = time.time()
        # scene frame = sim cache frame after detonation (0 before)
        probe_t = None
        sc.frame_set(0)
        t, dt, info = frame(st, i)
        sf = info.get("sim", sim_frame(t))
        if sc.frame_current != sf:
            sc.frame_set(sf)
            t, dt, info = frame(st, i)
        sc.cycles.samples = a.spp or info.get("samples", 12)
        sc.render.motion_blur_shutter = info.get("shutter", 0.5)
        bpy.context.view_layer.update()
        an = {}
        for k, p in info.get("anchors", {}).items():
            v = world_to_camera_view(sc, st.cam, Vector(p)); an[k] = [float(v.x), float(1 - v.y), float(v.z)]
        meta[str(i)] = dict(t=float(t), td=float(t - T_DET), sim=int(sf), anchors=an)
        sc.render.filepath = fp
        bpy.ops.render.render(write_still=True)
        print("FRAME %s %d t=%.3f sim=%d %.1fs" % (a.shot, i, t, sf, time.time() - t0)); sys.stdout.flush()
        json.dump(meta, open(meta_path, "w"))
        if a.save_blend:
            bpy.ops.wm.save_as_mainfile(filepath=a.save_blend, copy=True)
    sys.stdout.flush(); os._exit(0)

if __name__ == "__main__":
    main()
