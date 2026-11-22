"""The sea for the Tomahawk segment: the surface from above, the water from below, and the effects of the launch
(gas and bubbles under water, the plume of spray at the surface, the booster's smoke trail)."""
import bpy, math, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
for p in ("grenade-explosion", "rpg7-explosion", "mortar-explosion", "howitzer-explosion", "reaper-hellfire"):
    sys.path.insert(0, os.path.join(HERE, "..", p))
sys.path.insert(0, HERE)
import env
from util import new_mesh, new_obj, grid_faces, nodemat
from qshots import Puffs, _vol_mat
import tconst as C

# ----------------------------------------------------------------------------- water surface
def ocean_mat():
    """Deep water seen from the air: dark, glossy, with a long swell and wind ripples as bump (they drift with the Time value)."""
    m, N, L, P = nodemat("Ocean"); P.inputs["Base Color"].default_value = (0.004, 0.020, 0.036, 1); P.inputs["Roughness"].default_value = 0.09
    tc = N.new("ShaderNodeTexCoord"); tv = N.new("ShaderNodeValue"); tv.name = "Time"; prev = None
    for k, (scale, detail, strength, dist, vel) in enumerate(((0.045, 3.0, 0.55, 1.6, (1.8, 0.6)), (0.34, 4.0, 0.30, 0.20, (0.9, -0.5)), (2.6, 3.0, 0.12, 0.03, (0.4, 0.3)))):
        off = N.new("ShaderNodeCombineXYZ")
        for j in (0, 1):
            mu = N.new("ShaderNodeMath"); mu.operation = 'MULTIPLY'; mu.inputs[1].default_value = -vel[j]; L.new(tv.outputs[0], mu.inputs[0]); L.new(mu.outputs[0], off.inputs[j])
        add = N.new("ShaderNodeVectorMath"); add.operation = 'ADD'; L.new(tc.outputs["Object"], add.inputs[0]); L.new(off.outputs[0], add.inputs[1])
        n = N.new("ShaderNodeTexNoise"); n.inputs["Scale"].default_value = scale; n.inputs["Detail"].default_value = detail; n.inputs["Roughness"].default_value = 0.55; L.new(add.outputs[0], n.inputs["Vector"])
        b = N.new("ShaderNodeBump"); b.inputs["Strength"].default_value = strength; b.inputs["Distance"].default_value = dist; L.new(n.outputs["Fac"], b.inputs["Height"])
        if prev is not None:
            L.new(prev.outputs["Normal"], b.inputs["Normal"])
        prev = b
    L.new(prev.outputs["Normal"], P.inputs["Normal"])
    return m, tv

def build_sea(sc):
    """Sky, sun and open sea out to the horizon (z = 0)."""
    col = bpy.data.collections.new("ENV"); sc.collection.children.link(col); env.make_world(sc)
    na = 160; rr = np.concatenate([[0.0], np.geomspace(40.0, 9.0e5, 70)]); a = np.linspace(0, 2 * np.pi, na, endpoint=False)
    A, Rr = np.meshgrid(a, rr, indexing="ij"); V = np.stack([Rr * np.cos(A), Rr * np.sin(A), np.zeros_like(A)], -1).reshape(-1, 3)
    m, tv = ocean_mat(); ob = new_obj("Sea", new_mesh("sea", V, [grid_faces(na, len(rr), wrap_u=True)]), col, m)
    return col, ob, tv

def build_underwater(sc):
    """Blue-green water with the bright, rippling surface overhead.  Returns the collection and the surface's Time value."""
    col = bpy.data.collections.new("ENV"); sc.collection.children.link(col)
    w = bpy.data.worlds.new("Water"); sc.world = w; w.use_nodes = True; N = w.node_tree.nodes; L = w.node_tree.links; bg = N["Background"]
    tc = N.new("ShaderNodeTexCoord"); sep = N.new("ShaderNodeSeparateXYZ"); L.new(tc.outputs["Generated"], sep.inputs[0])
    ramp = N.new("ShaderNodeValToRGB"); e = ramp.color_ramp.elements; e[0].position = 0.0; e[0].color = (0.0, 0.004, 0.014, 1); e[1].position = 1.0; e[1].color = (0.01, 0.16, 0.24, 1)
    el = ramp.color_ramp.elements.new(0.5); el.color = (0.0, 0.020, 0.045, 1)
    mr = N.new("ShaderNodeMapRange"); mr.inputs["From Min"].default_value = -1.0; mr.inputs["From Max"].default_value = 1.0; L.new(sep.outputs["Z"], mr.inputs["Value"])
    L.new(mr.outputs[0], ramp.inputs["Fac"]); L.new(ramp.outputs["Color"], bg.inputs["Color"]); bg.inputs["Strength"].default_value = 1.0
    sl = bpy.data.lights.new("SunDown", 'SUN'); sl.energy = 4.5; sl.angle = math.radians(9.0); sl.color = (0.62, 0.92, 1.0)
    so = bpy.data.objects.new("SunDown", sl); sc.collection.objects.link(so); so.rotation_euler = (math.radians(14), math.radians(-18), 0)
    # the water itself: scatters blue-green, swallows red
    wm = bpy.data.materials.new("WaterBody"); wm.use_nodes = True; N = wm.node_tree.nodes; L = wm.node_tree.links; N.clear()
    out = N.new("ShaderNodeOutputMaterial"); sca = N.new("ShaderNodeVolumeScatter"); ab = N.new("ShaderNodeVolumeAbsorption"); add = N.new("ShaderNodeAddShader")
    sca.inputs["Color"].default_value = (0.20, 0.62, 0.72, 1); sca.inputs["Density"].default_value = 0.0045; sca.inputs["Anisotropy"].default_value = 0.55
    ab.inputs["Color"].default_value = (0.10, 0.62, 0.86, 1); ab.inputs["Density"].default_value = 0.022
    L.new(sca.outputs[0], add.inputs[0]); L.new(ab.outputs[0], add.inputs[1]); L.new(add.outputs[0], out.inputs["Volume"])
    bpy.ops.mesh.primitive_cube_add(size=1); box = bpy.context.active_object; box.name = "WaterBody"; box.scale = (900, 900, 140); box.location = (0, 0, -70.0); box.data.materials.append(wm)
    for c_ in list(box.users_collection):
        c_.objects.unlink(box)
    col.objects.link(box); box.visible_shadow = False
    # the surface from below: a bright ceiling whose ripples drift
    sm = bpy.data.materials.new("SurfaceBelow"); sm.use_nodes = True; N = sm.node_tree.nodes; L = sm.node_tree.links; N.clear()
    out = N.new("ShaderNodeOutputMaterial"); em = N.new("ShaderNodeEmission"); tcn = N.new("ShaderNodeTexCoord"); tv = N.new("ShaderNodeValue"); tv.name = "Time"
    off = N.new("ShaderNodeCombineXYZ"); mu = N.new("ShaderNodeMath"); mu.operation = 'MULTIPLY'; mu.inputs[1].default_value = 0.8; L.new(tv.outputs[0], mu.inputs[0]); L.new(mu.outputs[0], off.inputs[0])
    add = N.new("ShaderNodeVectorMath"); add.operation = 'ADD'; L.new(tcn.outputs["Object"], add.inputs[0]); L.new(off.outputs[0], add.inputs[1])
    n = N.new("ShaderNodeTexNoise"); n.inputs["Scale"].default_value = 0.42; n.inputs["Detail"].default_value = 4; n.inputs["Roughness"].default_value = 0.55; n.inputs["Distortion"].default_value = 1.4; L.new(add.outputs[0], n.inputs["Vector"])
    rp = N.new("ShaderNodeValToRGB"); e = rp.color_ramp.elements; e[0].position = 0.40; e[0].color = (0.01, 0.13, 0.20, 1); e[1].position = 0.70; e[1].color = (0.55, 0.95, 1.0, 1)
    L.new(n.outputs["Fac"], rp.inputs["Fac"]); L.new(rp.outputs["Color"], em.inputs["Color"]); em.inputs["Strength"].default_value = 1.5; L.new(em.outputs[0], out.inputs["Surface"])
    a = np.linspace(0, 2 * np.pi, 64, endpoint=False); V = np.vstack([[0, 0, 0.0], np.stack([4000 * np.cos(a), 4000 * np.sin(a), np.zeros(64)], 1)]); k = np.arange(64)
    surf = new_obj("SurfaceBelow", new_mesh("surface_below", V, [np.stack([np.zeros(64, int), 1 + (k + 1) % 64, 1 + k], 1)], smooth=False), col, sm); surf.visible_shadow = False
    return col, tv

# ----------------------------------------------------------------------------- clouds of puffs
class Cloud:
    """A cloud of overlapping lumpy puffs.  Puffs can be put into classes (young / middle / old) that each have their own density."""
    def __init__(self, col, name, n, seed, color, noise_scale=0.7, lo=0.30, hi=0.62, emission=None, shadow=True, classes=1, copies=4, aniso=0.3):
        self.P = Puffs(n, seed); self.n = n; self.classes = classes; self.copies = copies; self.name = name
        m, fade, tv, sep = _vol_mat(name + "Mat", color, noise_scale, lo, hi, rise=0.5, emission=emission)
        for nd in m.node_tree.nodes:
            if nd.bl_idname == "ShaderNodeVolumePrincipled":
                nd.inputs["Anisotropy"].default_value = aniso
        self.mats = [m] + [m.copy() for _ in range(classes * copies - 1)]
        self.ob = new_obj(name, bpy.data.meshes.new(name), col, m); self.ob.hide_render = True; self.ob.visible_shadow = shadow
    def update(self, idx, cen, rad, gains, t=0.0, cls=None):
        idx = np.asarray(idx, int); self.ob.hide_render = len(idx) < 1
        if len(idx) < 1:
            return
        me = self.P.mesh(self.name, idx, np.asarray(cen, float), rad, self.mats)
        c = np.zeros(len(idx), int) if cls is None else np.asarray(cls, int)
        me.polygons.foreach_set("material_index", np.repeat(c * self.copies + idx % self.copies, len(self.P.F)).astype(np.int32))
        old = self.ob.data; self.ob.data = me; bpy.data.meshes.remove(old)
        gains = [gains] * self.classes if np.isscalar(gains) else gains
        for k, mt in enumerate(self.mats):
            f = mt.node_tree.nodes["Fade"]; g = gains[k // self.copies]; f.inputs["To Min"].default_value = g; f.inputs["To Max"].default_value = g
            mt.node_tree.nodes["Time"].outputs[0].default_value = t

def bubble_mat(name="Bubbles"):
    m, N, L, P = nodemat(name); P.inputs["Base Color"].default_value = (0.80, 0.95, 1.0, 1); P.inputs["Roughness"].default_value = 0.12
    P.inputs["Emission Color"].default_value = (0.55, 0.85, 0.95, 1); P.inputs["Emission Strength"].default_value = 0.35
    return m

class Specks:
    """Many small solid blobs (air bubbles under water, drops of spray above it), rebuilt each frame."""
    def __init__(self, col, name, n, seed, mat):
        self.P = Puffs(n, seed); self.n = n; self.mat = mat; self.name = name
        self.ob = new_obj(name, bpy.data.meshes.new(name), col, mat); self.ob.hide_render = True; self.ob.visible_shadow = False
    def update(self, idx, cen, rad):
        idx = np.asarray(idx, int); self.ob.hide_render = len(idx) < 1
        if len(idx) < 1:
            return
        me = self.P.mesh(self.name, idx, np.asarray(cen, float), rad, [self.mat]); old = self.ob.data; self.ob.data = me; bpy.data.meshes.remove(old)

def nozzle_at(t):
    """Sea set: where the booster's nozzle is, and the unit vector the exhaust leaves along."""
    p, v, _ = C.launch_state(t); d = v / (np.linalg.norm(v) + 1e-9); return p - d * (C.LEN / 2 + 0.69), -d

class Launch:
    """Everything the launch leaves behind it, under and over the water."""
    def __init__(self, col, underwater):
        self.under = underwater; rng = np.random.default_rng(71)
        if underwater:
            # gas from the capsule's gas generator at the hatch, then the booster's exhaust as a rising column of bubbles
            self.gas = Cloud(col, "LaunchGas", 150, 5, (0.80, 0.93, 0.97), noise_scale=1.1, lo=0.28, hi=0.60, classes=2, shadow=False, aniso=0.5)
            self.g_t = np.concatenate([rng.uniform(0.0, 0.45, 50), np.linspace(C.T_IGN, C.T_CLEAR + 0.25, 100)]); self.g_hatch = np.arange(150) < 50
            self.bub = Specks(col, "LaunchBubbles", 900, 9, bubble_mat()); self.b_t = np.concatenate([rng.uniform(0.0, 0.6, 300), rng.uniform(C.T_IGN, C.T_CLEAR + 0.3, 600)]); self.b_hatch = np.arange(900) < 300
            self.b_r = rng.uniform(0.025, 0.085, 900); self.b_up = rng.uniform(0.5, 2.4, 900); self.b_ph = rng.uniform(0, 6.28, 900)
        else:
            ts = [C.T_BROACH]                                             # smoke: one puff about every 2.4 m of flight until burnout
            while ts[-1] < C.T_BURNOUT:
                ts.append(ts[-1] + 2.4 / max(C.launch_state(ts[-1])[2], 8.0))
            self.s_t = np.array(ts); self.smoke = Cloud(col, "BoostSmoke", len(ts), 13, (0.93, 0.93, 0.91), noise_scale=0.55, lo=0.20, hi=0.56, classes=3, copies=3)
            self.s_p = np.array([nozzle_at(t)[0] for t in ts]); self.s_d = np.array([nozzle_at(t)[1] for t in ts])
            self.spray = Cloud(col, "Spray", 190, 21, (0.94, 0.97, 1.0), noise_scale=1.2, lo=0.26, hi=0.60, classes=2, aniso=0.6)
            self.sp_t = C.T_BROACH + np.concatenate([rng.uniform(-0.03, 0.75, 120), rng.uniform(0.0, 1.3, 70)]); self.sp_col = np.arange(190) < 120
            a = rng.uniform(0, 2 * np.pi, 190); self.sp_dir = np.stack([np.cos(a), np.sin(a)], 1); self.sp_up = rng.uniform(6.0, 25.0, 190); self.sp_out = np.where(self.sp_col, rng.uniform(0.3, 4.5, 190), rng.uniform(4.0, 9.5, 190))
            m, N, L, P = nodemat("Drops"); P.inputs["Base Color"].default_value = (0.9, 0.95, 1.0, 1); P.inputs["Roughness"].default_value = 0.15
            self.drops = Specks(col, "Drops", 600, 23, m); self.d_t = C.T_BROACH + rng.uniform(-0.02, 0.9, 600); a = rng.uniform(0, 2 * np.pi, 600); el = np.radians(rng.uniform(48, 88, 600)); sp = rng.uniform(7.0, 27.0, 600)
            self.d_v = np.stack([sp * np.cos(el) * np.cos(a), sp * np.cos(el) * np.sin(a), sp * np.sin(el)], 1); self.d_r = rng.uniform(0.03, 0.10, 600)
            # the patch of foam left on the surface
            fm, N, L, P = nodemat("Foam"); tc = N.new("ShaderNodeTexCoord"); n = N.new("ShaderNodeTexNoise"); n.inputs["Scale"].default_value = 0.9; n.inputs["Detail"].default_value = 6; L.new(tc.outputs["Object"], n.inputs["Vector"])
            sep = N.new("ShaderNodeSeparateXYZ"); L.new(tc.outputs["UV"], sep.inputs[0]); ed = N.new("ShaderNodeMapRange"); ed.inputs["From Min"].default_value = 1.0; ed.inputs["From Max"].default_value = 0.25; L.new(sep.outputs["X"], ed.inputs["Value"])
            nm = N.new("ShaderNodeMapRange"); nm.inputs["From Min"].default_value = 0.36; nm.inputs["From Max"].default_value = 0.62; L.new(n.outputs["Fac"], nm.inputs["Value"])
            self.foam_gain = N.new("ShaderNodeValue"); m1 = N.new("ShaderNodeMath"); m1.operation = 'MULTIPLY'; L.new(ed.outputs[0], m1.inputs[0]); L.new(nm.outputs[0], m1.inputs[1])
            m2 = N.new("ShaderNodeMath"); m2.operation = 'MULTIPLY'; L.new(m1.outputs[0], m2.inputs[0]); L.new(self.foam_gain.outputs[0], m2.inputs[1]); L.new(m2.outputs[0], P.inputs["Alpha"])
            P.inputs["Base Color"].default_value = (0.85, 0.92, 0.95, 1); P.inputs["Roughness"].default_value = 0.6
            na, nr = 64, 8; a = np.linspace(0, 2 * np.pi, na, endpoint=False); r = np.linspace(0.02, 1.0, nr); A, Rr = np.meshgrid(a, r, indexing="ij")
            V = np.stack([Rr * np.cos(A), Rr * np.sin(A), np.full_like(A, 0.03)], -1).reshape(-1, 3)
            self.foam = new_obj("Foam", new_mesh("foam", V, [grid_faces(na, nr, wrap_u=True)], uvs=np.stack([Rr, A / (2 * np.pi)], -1).reshape(-1, 2)), col, fm); self.foam.visible_shadow = False

    def update(self, t):
        if self.under:
            age = t - self.g_t; idx = np.nonzero((age > 0) & (age < 6.0))[0]; a = age[idx]; R = self.gas.P.rnd[idx]; hat = self.g_hatch[idx]
            hx = C.sub_bow_x(0.0) - C.HATCH_X                                                              # where the hatch was when the gas left (it barely moves in this time)
            cen = np.zeros((len(idx), 3))
            for j, i in enumerate(idx):
                cen[j] = np.array([hx, 0.0, C.HATCH_Z + 0.4]) if hat[j] else nozzle_at(self.g_t[i])[0]
            cen[:, 0] += 0.9 * a ** 0.7 * R[:, 0]; cen[:, 1] += 0.9 * a ** 0.7 * R[:, 1]; cen[:, 2] += np.where(hat, 1.6, 1.1) * a + 0.4 * a ** 0.7 * R[:, 2]
            ok = cen[:, 2] < -0.3; rad = (np.where(hat, 0.45, 0.50) + np.where(hat, 0.9, 0.75) * a ** 0.6) * self.gas.P.size[idx] * np.clip(a / 0.06, 0.2, 1.0)
            self.gas.update(idx[ok], cen[ok], rad[ok], [0.55, 1.1], t, cls=(~hat[ok]).astype(int))
            age = t - self.b_t; idx = np.nonzero((age > 0) & (age < 9.0))[0]; a = age[idx]; R = self.bub.P.rnd[idx]; hat = self.b_hatch[idx]; cen = np.zeros((len(idx), 3))
            for j, i in enumerate(idx):
                cen[j] = np.array([hx, 0.0, C.HATCH_Z + 0.3]) if hat[j] else nozzle_at(self.b_t[i])[0]
            wob = 0.18 * np.sin(3.0 * a + self.b_ph[idx]); cen[:, 0] += (0.5 + 0.9 * a ** 0.6) * R[:, 0] + wob; cen[:, 1] += (0.5 + 0.9 * a ** 0.6) * R[:, 1] + wob; cen[:, 2] += self.b_up[idx] * a + 0.5 * R[:, 2]
            ok = cen[:, 2] < -0.1; self.bub.update(idx[ok], cen[ok], self.b_r[idx][ok])
            return
        # ---- smoke trail
        age = t - self.s_t; idx = np.nonzero(age > 0.0)[0]; a = age[idx]; R = self.smoke.P.rnd[idx]
        cen = self.s_p[idx] + self.s_d[idx] * (9.0 * (1 - np.exp(-a / 0.35)))[:, None]                    # the exhaust carries it a few metres back along the jet
        cen[:, 0] += -1.2 * a + 0.55 * a ** 0.75 * R[:, 0]; cen[:, 1] += 0.7 * a + 0.55 * a ** 0.75 * R[:, 1]; cen[:, 2] += 0.35 * a ** 0.75 * R[:, 2]
        cen[:, 2] = np.maximum(cen[:, 2], 0.6 + 0.5 * a ** 0.5)
        rad = (1.0 + 1.9 * a ** 0.5) * np.clip(a / 0.10, 0.35, 1.0) * self.smoke.P.size[idx]; low = self.s_p[idx][:, 2] < 6.0; rad = np.where(low, rad * 1.5, rad)     # exhaust on the water billows
        cls = np.where(a < 1.2, 0, np.where(a < 4.5, 1, 2)); self.smoke.update(idx, cen, rad, [1.9, 0.95, 0.45], t, cls=cls)
        # ---- spray
        age = t - self.sp_t; idx = np.nonzero((age > 0) & (age < 5.0))[0]; a = age[idx]; R = self.spray.P.rnd[idx]; colm = self.sp_col[idx]
        k = 0.55; z = np.where(colm, self.sp_up[idx] * (1 - np.exp(-k * a)) / k - 0.5 * 9.81 * a * a * 0.55, 0.5 + 0.6 * a ** 0.5); out = self.sp_out[idx] * (1 - np.exp(-0.9 * a)) / 0.9
        cen = np.stack([self.sp_dir[idx, 0] * out + 0.3 * R[:, 0], self.sp_dir[idx, 1] * out + 0.3 * R[:, 1], z], 1); ok = cen[:, 2] > 0.1
        rad = (0.40 + np.where(colm, 0.75, 1.05) * a ** 0.7) * self.spray.P.size[idx] * np.clip((np.where(colm, 3.2, 5.0) - a) / 1.0, 0.0, 1.0)
        self.spray.update(idx[ok], cen[ok], rad[ok], [1.5, 0.55], t, cls=(~colm[ok]).astype(int))
        age = t - self.d_t; idx = np.nonzero((age > 0) & (age < 5.0))[0]; a = age[idx]
        cen = self.d_v[idx] * a[:, None] * np.exp(-0.25 * a)[:, None]; cen[:, 2] -= 0.5 * 9.81 * a * a; ok = cen[:, 2] > 0.0; self.drops.update(idx[ok], cen[ok], self.d_r[idx][ok])
        tb = t - C.T_BROACH; self.foam.hide_render = tb < 0; r = 2.0 + 9.0 * (1 - math.exp(-max(tb, 0) / 2.0)); self.foam.scale = (r, r, 1); self.foam_gain.outputs[0].default_value = 0.95 * min(1.0, max(tb, 0) / 0.3)
