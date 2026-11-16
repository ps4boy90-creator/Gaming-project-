"""Shot definitions and frame renderer for the RPG-7 explosion-comparison segment.

  python3 rshots.py <shot> <out_dir> [--sim <cache_dir>] [--res 1280x720] [--spp N] [--frames a-b | i,j,k]

Shots: card, fire, follow, impact, behind, after.   Time base: t = seconds after the trigger;
the warhead hits the wall at T_HIT.  One sim ("master") frame is 1/240 s.
"""
import bpy, sys, os, math, json, time, argparse
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, "..", "grenade-explosion")); sys.path.insert(0, HERE)
import numpy as np
from mathutils import Vector, Quaternion
import manta_fix  # noqa: F401
import env, figure, fx
import shots as gshots                      # reuse the M67 segment's render setup, camera helpers and shake
from smoke_mat import blast_material
from util import *
import rconst as C, rpg7, wall as wallmod

FPS = C.FPS; DT = C.MASTER_DT; T_HIT = C.T_HIT
D = math.radians
shake = gshots.shake
SIM_OF = {"fire": "launch", "impact": "impact", "behind": "impact"}

# ----------------------------------------------------------------------------- Ghost Man: firing stance
POSE = dict(pelvis=(0.0, 0.0, 0.94), pelvis_yaw=D(-40), lean=(0.10, 0.0, 1.0), chest_yaw=D(-42), foot_l=(0.27, 0.10, 0.0), foot_r=(-0.24, -0.15, 0.0),
            foot_yaw_l=D(-8), foot_yaw_r=D(-62), elbow_r=(0.15, -0.55, -0.85), elbow_l=(0.35, 0.45, -0.85), head_yaw=D(-5),
            hand_r=(0.2, -0.15, 1.3), hand_l=(0.1, -0.1, 1.3))
_j = figure.solve(POSE)
_lsh = _j["sho_r"] + _j["side_c"] * 0.035 + np.array([0, 0, 0.088])          # where the tube sits, figure-local
_gz = float(env.ground_h(C.SHOULDER[0] - _lsh[0], C.SHOULDER[1] - _lsh[1]))
POSE["pelvis"] = (0.0, 0.0, 0.94 + (C.SHOULDER[2] - _gz - _lsh[2]))
MAN_BASE = np.array([C.SHOULDER[0] - _lsh[0], C.SHOULDER[1] - _lsh[1], _gz])

def kick(t):
    return (1 - math.exp(-t / 0.03)) * math.exp(-t / 0.35) if t > 0 else 0.0

def launcher_state(t):
    """Muzzle position and orientation: steady aim with a little sway, then the launch jolt (pivoting on the shoulder)."""
    th = D(2.4) * kick(t) + D(0.22) * math.sin(1.9 * t + 0.5)
    yw = D(0.15) * math.sin(1.3 * t + 2.0)
    q = Quaternion((0, 0, 1), yw) @ Quaternion((0, 1, 0), -th) @ rpg7.aim_quat(C.AIM)
    sh = Vector(C.SHOULDER) + Vector((-0.014 * kick(t), 0, 0))
    return np.array(sh + q @ Vector((-C.SHOULDER_X, 0, 0))), q

def man_pose(t):
    m, q = launcher_state(t)
    p = dict(POSE); k = kick(t)
    gr = np.array(Vector(m) + q @ Vector(rpg7.GRIP_R)) - MAN_BASE; gl = np.array(Vector(m) + q @ Vector(rpg7.GRIP_L)) - MAN_BASE
    p["hand_r"] = gr + np.array([-0.030, -0.011, -0.044]); p["hand_l"] = gl + np.array([0.021, 0.032, -0.039])
    p["pelvis"] = (POSE["pelvis"][0] - 0.022 * k, 0.0, POSE["pelvis"][2]); p["lean"] = (0.10 - 0.07 * k, 0.0, 1.0)
    return p

# ----------------------------------------------------------------------------- rocket exhaust
class Trail:
    """Sustainer smoke trail as real fog-volume grids (Mesh to Volume + Volume Displace), split into age bands that
    get wider and thinner behind the rocket, plus an emissive flame sheath at the nozzle ring."""
    BANDS = [(0.0, 0.9, 0.012, 13.0), (0.7, 2.8, 0.018, 7.5), (2.4, 6.5, 0.026, 4.6), (6.0, 13.0, 0.036, 3.0), (12.0, 26.0, 0.05, 2.0), (24.0, 70.0, 0.07, 1.3)]
    def __init__(self, col, rocket_root):
        self.p0 = C.NOSE0 + C.AIM * (C.S_IGN + rpg7.NOZZLE_X); self.length = C.DIST - C.S_IGN - rpg7.NOZZLE_X - 0.03
        q = rpg7.aim_quat(C.AIM); self.segs = []
        tex = bpy.data.textures.new("TrailClouds", 'CLOUDS'); tex.noise_scale = 0.22; tex.noise_depth = 4
        for k, (a, b, vox, dens) in enumerate(self.BANDS):
            hull = new_obj("TrailHull%d" % k, bpy.data.meshes.new("hull"), col); hull.location = self.p0; hull.rotation_mode = 'QUATERNION'
            hull.rotation_quaternion = q; hull.hide_render = True
            vol = bpy.data.objects.new("TrailVol%d" % k, bpy.data.volumes.new("TrailVol%d" % k)); col.objects.link(vol)
            m = vol.modifiers.new("m2v", 'MESH_TO_VOLUME'); m.object = hull; m.density = 1.0; m.resolution_mode = 'VOXEL_SIZE'; m.voxel_size = vox
            m.interior_band_width = 3.0 * vox
            d = vol.modifiers.new("disp", 'VOLUME_DISPLACE'); d.texture = tex; d.texture_map_mode = 'GLOBAL'; d.strength = 1.5 * (0.05 + 0.02 * k)
            d.texture_sample_radius = 1.0; d.texture_mid_level = (0.5, 0.5, 0.5)
            mat = bpy.data.materials.new("TrailMat%d" % k); mat.use_nodes = True; nt = mat.node_tree; N = nt.nodes; L = nt.links; N.clear()
            out = N.new("ShaderNodeOutputMaterial"); at = N.new("ShaderNodeAttribute"); at.attribute_name = "density"
            mul = N.new("ShaderNodeMath"); mul.operation = 'MULTIPLY'; mul.inputs[1].default_value = dens; L.new(at.outputs["Fac"], mul.inputs[0])
            pv = N.new("ShaderNodeVolumePrincipled"); pv.inputs["Color"].default_value = (0.82, 0.81, 0.79, 1); pv.inputs["Anisotropy"].default_value = 0.35
            L.new(mul.outputs[0], pv.inputs["Density"]); L.new(pv.outputs[0], out.inputs["Volume"])
            vol.data.materials.append(mat); vol.hide_render = True
            self.segs.append((a, b, hull, vol))
        # flame sheath: emissive, fading along its length and towards its silhouette
        prof = [(0.0, 0.020), (-0.03, 0.036), (-0.09, 0.046), (-0.20, 0.044), (-0.34, 0.032), (-0.48, 0.016), (-0.58, 0.002)]
        g = Geo(); rpg7.lathe(g, prof, 20)
        fm = bpy.data.materials.new("MotorFlame"); fm.use_nodes = True; nt = fm.node_tree; N = nt.nodes; L = nt.links; N.clear()
        out = N.new("ShaderNodeOutputMaterial"); tc = N.new("ShaderNodeTexCoord"); sep = N.new("ShaderNodeSeparateXYZ"); L.new(tc.outputs["Object"], sep.inputs[0])
        mr = N.new("ShaderNodeMapRange"); mr.inputs["From Min"].default_value = -0.58; mr.inputs["From Max"].default_value = 0.0; L.new(sep.outputs["X"], mr.inputs["Value"])
        ramp = N.new("ShaderNodeValToRGB"); e = ramp.color_ramp.elements
        e[0].position = 0.0; e[0].color = (0.9, 0.12, 0.01, 1); e[1].position = 1.0; e[1].color = (1.0, 0.70, 0.30, 1)
        mid = ramp.color_ramp.elements.new(0.55); mid.color = (1.0, 0.32, 0.04, 1); L.new(mr.outputs["Result"], ramp.inputs["Fac"])
        nz = N.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 18.0; nz.inputs["Detail"].default_value = 3; L.new(tc.outputs["Object"], nz.inputs["Vector"])
        self.flick = N.new("ShaderNodeMapping"); L.new(tc.outputs["Object"], self.flick.inputs[0]); L.new(self.flick.outputs[0], nz.inputs["Vector"])
        lw = N.new("ShaderNodeLayerWeight"); lw.inputs["Blend"].default_value = 0.35
        def mth(op, x, y):
            n = N.new("ShaderNodeMath"); n.operation = op
            for k, v in enumerate((x, y)):
                if isinstance(v, (int, float)):
                    n.inputs[k].default_value = v
                else:
                    L.new(v, n.inputs[k])
            return n.outputs[0]
        alpha = mth('MULTIPLY', mth('POWER', mr.outputs["Result"], 1.3), mth('MULTIPLY', mth('POWER', mth('SUBTRACT', 1.0, lw.outputs["Facing"]), 1.6), mth('ADD', nz.outputs["Fac"], 0.15)))
        em = N.new("ShaderNodeEmission"); em.inputs["Strength"].default_value = 4.0; L.new(ramp.outputs["Color"], em.inputs["Color"])
        tr = N.new("ShaderNodeBsdfTransparent"); mx = N.new("ShaderNodeMixShader"); L.new(alpha, mx.inputs[0]); L.new(tr.outputs[0], mx.inputs[1]); L.new(em.outputs[0], mx.inputs[2])
        L.new(mx.outputs[0], out.inputs["Surface"])
        self.flame = new_obj("MotorFlame", g.mesh("flame"), col, fm); self.flame.parent = rocket_root; self.flame.location = (rpg7.NOZZLE_X - 0.005, 0, 0)
        self.flame.visible_shadow = False; self.flame.hide_render = True

    def update(self, x_head, visible, flame):
        self.flame.hide_render = not flame
        self.flick.inputs["Location"].default_value = (x_head * 0.7, 0, 0)
        x1 = min(x_head, self.length)
        for a, b, hull, vol in self.segs:
            lo = max(x_head - b, 0.0); hi = min(x_head - a, x1)
            on = visible and hi - lo > 0.02
            vol.hide_render = not on
            if not on:
                continue
            xs = np.linspace(hi, lo, 14)
            rr = 0.030 + 0.050 * np.sqrt(np.maximum(x_head - xs, 0.0))
            g = Geo(); v, f, t = tube(np.stack([xs, 0 * xs, 0 * xs], 1), rr, 14); g.add(v, f); g.add(v, t)
            me = g.mesh("hull"); old = hull.data; hull.data = me; bpy.data.meshes.remove(old)

def point_light(col, name, color, soft=0.3):
    ld = bpy.data.lights.new(name, 'POINT'); ld.shadow_soft_size = soft; ld.color = color; ld.energy = 0.0
    ob = bpy.data.objects.new(name, ld); col.objects.link(ob); return ob

# ----------------------------------------------------------------------------- scene
class Stage(gshots.Stage):
    def __init__(self, sim_dir=None, kind=None):
        self.dom = None; self.T0 = {"launch": 0.0, "impact": T_HIT}.get(kind, 0.0)
        if sim_dir and os.path.exists(os.path.join(sim_dir, "sim.blend")):
            bpy.ops.wm.open_mainfile(filepath=os.path.join(sim_dir, "sim.blend"))
            for o in list(bpy.data.objects):
                if o.name.startswith("E_"):
                    bpy.data.objects.remove(o, do_unlink=True)
            self.dom = bpy.data.objects["BlastDomain"]
            self.dom.data.materials.clear()
            self.fire0 = 45.0 if kind == "launch" else 60.0
            bm_ = blast_material(density=9.0, fire=self.fire0, ambient=0.11) if kind == "launch" else blast_material(fire=self.fire0)
            self.dom.data.materials.append(bm_); self.fire_node = bm_.node_tree.nodes[bm_["fire_node"]]
            self.dom.hide_render = True
        else:
            bpy.ops.wm.read_factory_settings(use_empty=True)
        sc = self.sc = bpy.context.scene; sc.render.fps = FPS
        self.env_col, self.ground = env.build(sc, C.SHOOT_X)
        self.ground.data.materials[0].node_tree.nodes["Blast"].outputs[0].default_value = 0.0
        col = self.col = bpy.data.collections.new("ACTION"); sc.collection.children.link(col)
        self.launcher = rpg7.build_launcher(col)
        self.rocket = rpg7.Rocket(col)
        self.ghost = figure.ghost_material()
        self.man = figure.Figure(col, "GhostMan", self.ghost); self.man.ob.location = MAN_BASE
        self.wall = wallmod.Wall(col)
        self.trail = Trail(col, self.rocket.root)
        self.l_motor = point_light(col, "MotorGlow", (1.0, 0.55, 0.25), 0.08)
        self.l_hit = point_light(col, "HitFlash", (1.0, 0.72, 0.42), 0.4); self.l_hit.location = (-0.40, 0, C.ZI)
        self.l_exit = point_light(col, "ExitFlash", (1.0, 0.66, 0.36), 0.3); self.l_exit.location = (C.WALL_T + 0.5, 0, C.ZI)
        self.l_breech = point_light(col, "BreechFlash", (1.0, 0.70, 0.42), 0.3); self.l_breech.location = C.BREECH - C.AIM * 0.5
        self.l_muzzle = point_light(col, "MuzzleFlash", (1.0, 0.72, 0.45), 0.2); self.l_muzzle.location = C.MUZZLE + C.AIM * 0.3
        cd = bpy.data.cameras.new("Cam"); self.cam = bpy.data.objects.new("Cam", cd); sc.collection.objects.link(self.cam); sc.camera = self.cam
        cd.clip_start = 0.02; cd.clip_end = 6000; cd.sensor_width = 36; cd.sensor_fit = 'HORIZONTAL'
        self.cam.rotation_mode = 'QUATERNION'
        self._pose_t = None
        self.setup_render()

    def rocket_state(self, t):
        return C.nose(t), rpg7.aim_quat(C.AIM, C.SPIN * max(t - C.T_EXIT, 0.0))

    def set_time(self, t, dt_out, opt):
        sc = self.sc; td = t - T_HIT
        mb = opt.get("motion_blur", True); sc.render.use_motion_blur = mb
        # shooter + launcher
        if opt.get("man", True):
            tp = min(t, 3.0)
            if self._pose_t is None or abs(tp - self._pose_t) > 1e-9:
                self.man.set_pose(man_pose(tp)); self._pose_t = tp
            self.man.ob.hide_render = False
        else:
            self.man.ob.hide_render = True
        self.key3(self.launcher, launcher_state, t, dt_out, False)
        # rocket: in the tube, in flight, gone at impact
        flying = td < 0
        self.rocket.set_visible(flying)
        if flying:
            s = C.travel(t)
            self.rocket.set_fins(D(9 + 61 * smoothstep(0.47, 1.9, s)), visible=s > 0.47)
            self.key3(self.rocket.root, self.rocket_state, t, dt_out, mb and opt.get("rocket_blur", True))
        self.rocket.tracer_em.inputs["Strength"].default_value = 60.0 if (C.T_EXIT < t < T_HIT) else 0.0
        # sustainer exhaust
        burning = t > C.T_IGN and opt.get("trail", True)
        self.trail.update(C.travel(t) - C.S_IGN, burning, burning and flying)
        self.l_motor.data.energy = 90.0 if (burning and flying) else 0.0
        self.l_motor.location = C.nose(t) + C.AIM * (rpg7.NOZZLE_X - 0.30) + np.array([0, 0, 0.09])
        # launch flashes
        self.l_breech.data.energy = 4500.0 * math.exp(-t / 0.010) if 0 <= t < 0.1 else 0.0
        self.l_muzzle.data.energy = 1500.0 * math.exp(-t / 0.008) if 0 <= t < 0.1 else 0.0
        # impact
        self.wall.update(td, shutter=0.5 * dt_out)
        fl = opt.get("flash", 1.0)
        self.l_hit.data.energy = 55000.0 * fl * math.exp(-td / 0.014) if 0 <= td < 0.25 else 0.0
        self.l_exit.data.energy = 22000.0 * fl * math.exp(-td / 0.010) if 0 <= td < 0.2 else 0.0
        for l in (self.l_motor, self.l_hit, self.l_exit, self.l_breech, self.l_muzzle):
            l.hide_render = l.data.energy < 5.0
        if self.dom is not None:
            self.dom.hide_render = t < self.T0
            # the flash of a detonation is over in a few tens of milliseconds; what is left is smoke and dust
            self.fire_node.inputs[1].default_value = self.fire0 * (0.10 + 0.90 * math.exp(-max(t - self.T0, 0.0) / 0.030))

# ----------------------------------------------------------------------------- shots
def shot_fire(n=90):
    """Three-quarter front view of Ghost Man: steady aim in real time, then the launch and backblast in slow motion."""
    lead = 30
    def frame(st, i):
        if i < lead:
            sf = 0; t = -(lead - i) / FPS - 0.004; dt = 1.0 / FPS
        else:
            sf = i - lead + 1; t = (sf - 1) * DT; dt = DT
        st.set_time(t, dt, dict(man=True))
        u = i / (n - 1)
        pos = C.SHOULDER + np.array([0.75 - 0.25 * u, -2.50 - 0.25 * u, 0.02 + 0.04 * u])
        tgt = C.SHOULDER + np.array([-0.15 - 1.0 * smoothstep(0.35, 1.0, u), 0.0, -0.16])
        off, rq = shake(t - 0.004, 0.8)
        q = st.look(pos + off, tgt, 28.0, fstop=4.0, focus=float(np.linalg.norm(C.SHOULDER - pos)))
        st.cam.rotation_quaternion = q @ rq
        return t, dt, dict(samples=10, sim=sf, shutter=0.3, anchors={"muzzle": C.MUZZLE})
    return n, frame

def shot_follow(n=78, side=-1.0):
    """Chase camera flying beside the rocket: fins snap open, the sustainer lights, the wall comes up."""
    t0, t1 = 0.0096, T_HIT - 0.006
    def cam_at(t):
        u = (t - t0) / (t1 - t0); nose = C.nose(t)
        off = np.array([lerp(-0.70, 0.75, smoothstep(0, 1, u)), side * lerp(0.95, 0.70, u), lerp(0.16, 0.12, u)])
        pos = nose + off; aim = nose - C.AIM * lerp(0.42, 0.30, u)
        return pos, (Vector(aim) - Vector(pos)).to_track_quat('-Z', 'Y')
    def frame(st, i):
        u = i / (n - 1); t = lerp(t0, t1, u); dt = (t1 - t0) / (n - 1)
        st.set_time(t, dt, dict(man=False))
        pos, q = cam_at(t)
        st.look(pos, None, 40.0, fstop=5.6, focus=float(np.linalg.norm(C.nose(t) - C.AIM * 0.35 - pos)), quat=q)
        st.key3(st.cam, cam_at, t, dt, True)
        return t, dt, dict(samples=10, shutter=0.4, anchors={"rocket": C.nose(t) - C.AIM * 0.35})
    return n, frame

def _slow(i, pre, one):
    """Slow-motion schedule around the hit: `pre` lead frames, `one` frames at 1 sim frame each, then 2 per frame."""
    if i < pre:
        return 0, T_HIT - (pre - i) * DT, DT
    if i < pre + one:
        sf = i - pre + 1; return sf, T_HIT + (sf - 1) * DT, DT
    sf = one + 2 * (i - pre - one + 1); return sf, T_HIT + (sf - 1) * DT, 2 * DT

def shot_impact(n=100):
    def frame(st, i):
        sf, t, dt = _slow(i, 8, 60)
        st.set_time(t, dt, dict(man=False))
        u = i / (n - 1)
        pos = np.array([-7.6 + 0.4 * u, -5.2 + 0.5 * u, 1.50 + 0.05 * u])
        tgt = np.array([0.3, 0.1, 1.35 + 0.30 * smoothstep(0.2, 1.0, u)])
        off, rq = shake(t - T_HIT - 0.012, 1.5)
        q = st.look(pos + off, tgt, 30.0, fstop=5.6, focus=8.5)
        st.cam.rotation_quaternion = q @ rq
        return t, dt, dict(samples=10, sim=sf, shutter=0.25, anchors={"hit": C.IMPACT})
    return n, frame

def shot_behind(n=64):
    """From behind the wall: the jet, the spall cloud and the bricks come out towards the lens."""
    def frame(st, i):
        sf, t, dt = _slow(i, 6, 200)
        st.set_time(t, dt, dict(man=False, trail=False))
        u = i / (n - 1)
        pos = np.array([6.2 - 0.3 * u, 2.4 - 0.2 * u, 1.05])
        off, rq = shake(t - T_HIT - 0.012, 1.2)
        q = st.look(pos + off, np.array([0.1, 0.0, 1.30]), 28.0, fstop=5.6, focus=6.0)
        st.cam.rotation_quaternion = q @ rq
        return t, dt, dict(samples=10, sim=sf, shutter=0.25, anchors={"hit": (C.WALL_T, 0, C.ZI)})
    return n, frame

def shot_after(n=84):
    """Aftermath: start on the breach, crane up and over the wall to look down on the debris field."""
    A = np.array([-3.3, -1.9, 1.45]); B = np.array([-2.6, -4.2, 5.5]); E = np.array([4.6, -2.2, 12.5])
    def frame(st, i):
        t = T_HIT + 9.0; dt = 1.0 / FPS
        st.set_time(t, dt, dict(man=False, trail=False, motion_blur=False))
        u = smoothstep(0.12, 1.0, i / (n - 1))
        pos = (1 - u) ** 2 * A + 2 * u * (1 - u) * B + u * u * E
        tgt = lerp(np.array([0.1, 0.0, 1.30]), np.array([4.2, 0.0, 0.2]), smoothstep(0.25, 1.0, u))
        st.look(pos, tgt, 28.0)
        an = {"hole": (0.0, 0.0, C.ZI), "far": (st.wall.reach, 0.0, 0.1), "wall": (0.1, 0.0, 0.1)}
        return t, dt, dict(samples=12, anchors=an)
    return n, frame

SHOTS = {"fire": shot_fire, "follow": shot_follow, "impact": shot_impact, "behind": shot_behind, "after": shot_after}

# ----------------------------------------------------------------------------- title card (studio)
def render_card(out_dir, res, spp, frames, n=72):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    pivot = bpy.data.objects.new("Pivot", None); sc.collection.objects.link(pivot)
    L = rpg7.build_launcher(sling=True); L.parent = pivot; L.location = (0.257, 0, 0.02)
    R = rpg7.Rocket(); R.root.parent = L; R.root.location = (C.SEAT, 0, 0); R.set_fins(0.1, False)
    prof = [(-9.0, -1.1), (2.2, -1.1)] + [(2.2 + 1.6 * math.sin(a), -1.1 + 1.6 * (1 - math.cos(a))) for a in np.linspace(0, math.pi / 2, 12)[1:]] + [(3.8, 9.0)]
    V = np.array([[x, y, z] for (y, z) in prof for x in (-12.0, 12.0)])
    new_obj("Backdrop", new_mesh("bd", V, [grid_faces(len(prof), 2)]), None, simple_mat("BackdropMat", (0.64, 0.61, 0.56), rough=0.85))
    w = bpy.data.worlds.new("Studio"); sc.world = w; w.use_nodes = True
    w.node_tree.nodes["Background"].inputs[0].default_value = (0.75, 0.78, 0.82, 1); w.node_tree.nodes["Background"].inputs[1].default_value = 0.30
    def area(loc, size, power, color=(1, 1, 1)):
        L_ = bpy.data.lights.new("a", 'AREA'); L_.size = size; L_.energy = power; L_.color = color
        o = bpy.data.objects.new("a", L_); sc.collection.objects.link(o); o.location = loc
        o.rotation_euler = (-Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    area((2.2, -2.6, 2.4), 2.6, 520, (1.0, 0.96, 0.9)); area((-3.0, -1.4, 0.4), 3.0, 170, (0.8, 0.9, 1.0)); area((-0.8, 2.4, 2.0), 2.2, 620)
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); sc.collection.objects.link(cam); sc.camera = cam
    cam.data.lens = 85; cam.data.clip_start = 0.05; cam.data.sensor_width = 36
    cam.location = (0.0, -4.9, 0.10); cam.rotation_euler = (math.radians(89.0), 0, 0)
    cam.data.shift_x = 0.25                                  # launcher sits in the left half
    sc.render.engine = 'CYCLES'; c = sc.cycles; c.samples = spp or 20; c.use_denoising = True; c.denoising_quality = 'HIGH'; c.max_bounces = 6
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.use_border = True; sc.render.use_crop_to_border = True
    sc.render.border_min_x = 0.0; sc.render.border_max_x = 0.50; sc.render.border_min_y = 0.0; sc.render.border_max_y = 1.0
    sc.view_settings.view_transform = 'AgX'; sc.view_settings.look = 'AgX - Medium High Contrast'
    sc.render.image_settings.file_format = 'PNG'; sc.render.use_persistent_data = True
    os.makedirs(out_dir, exist_ok=True)
    for i in (frames if frames is not None else range(n)):
        u = i / n
        pivot.rotation_euler = (math.radians(8) * math.sin(2 * math.pi * u), math.radians(-48), math.radians(-6) + math.radians(30) * math.sin(2 * math.pi * u))
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
    st = Stage(a.sim, SIM_OF.get(a.shot))
    sc = st.sc; sc.render.resolution_x, sc.render.resolution_y = res
    os.makedirs(a.out, exist_ok=True)
    json.dump(dict(T_HIT=T_HIT, T_IGN=C.T_IGN, T_EXIT=C.T_EXIT, DIST=C.DIST, V_HIT=C.V_HIT, fps=FPS, hole=st.wall.hole, reach=st.wall.reach),
              open(os.path.join(os.path.dirname(os.path.abspath(a.out)), "timeline.json"), "w"))
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
        meta[str(i)] = dict(t=float(t), td=float(t - T_HIT), sim=int(sf), v=float(C.speed(t)), togo=float(max(C.DIST - C.travel(t), 0.0)), anchors=an)
        sc.render.filepath = fp
        bpy.ops.render.render(write_still=True)
        print("FRAME %s %d t=%.4f sim=%d %.1fs" % (a.shot, i, t, sf, time.time() - t0)); sys.stdout.flush()
        json.dump(meta, open(meta_path, "w"))
    sys.stdout.flush(); os._exit(0)

if __name__ == "__main__":
    main()
