"""Blast side effects that are cheaper to do analytically than in the fluid sim:
dirt clods, glowing fragments, the flash light, impact dust puffs and the radius rings."""
import bpy, math
import numpy as np
from util import *

G = 9.81

class Ballistic:
    """N particles with linear drag + gravity, analytic in time. They stop where they hit the ground."""
    def __init__(self, n, rng, speed, elev_deg, drag, size, origin=(0, 0, 0.12), spread=0.25):
        az = rng.uniform(0, 2 * np.pi, n)
        el = np.radians(rng.uniform(elev_deg[0], elev_deg[1], n))
        sp = rng.uniform(speed[0], speed[1], n) * rng.uniform(0.35, 1.0, n) ** 0.7
        self.v0 = np.stack([np.cos(az) * np.cos(el), np.sin(az) * np.cos(el), np.sin(el)], 1) * sp[:, None]
        self.p0 = np.asarray(origin)[None] + self.v0 / (sp[:, None] + 1e-9) * rng.uniform(0, spread, (n, 1))
        self.k = rng.uniform(drag[0], drag[1], n)
        self.size = rng.uniform(size[0], size[1], n) * rng.uniform(0.5, 1.0, n)
        self.n = n
        self.shape = rng.uniform(0.6, 1.0, (n, 2))
        self.roll = rng.uniform(0, 6.283, n)
        # ground hit time by sampling
        ts = np.linspace(0, 6, 1500)
        z = self._pos(ts[None, :])[..., 2]
        below = z < 0.0
        idx = np.where(below.any(1), below.argmax(1), len(ts) - 1)
        idx[~below.any(1)] = len(ts) - 1
        self.t_hit = ts[idx]
        self.p_hit = self._pos(self.t_hit[:, None])[:, 0, :]; self.p_hit[:, 2] = 0.0
    def _pos(self, t):
        k = self.k[:, None]; t = np.asarray(t, float)
        g = np.array([0, 0, -G])
        a = self.v0[:, None, :] - g[None, None, :] / k[..., None]
        e = (1 - np.exp(-k * t))[..., None]
        return self.p0[:, None, :] + a * e / k[..., None] + g[None, None, :] * (t[..., None] / k[..., None])
    def state(self, t):
        """positions (n,3), velocities (n,3), alive-in-air mask at time t (seconds since detonation)."""
        tt = np.minimum(max(t, 0.0), self.t_hit)
        p = self._pos(tt[:, None])[:, 0, :]
        k = self.k[:, None]; g = np.array([0, 0, -G])
        v = (self.v0 - g[None] / k) * np.exp(-k * tt[:, None]) + g[None] / k
        air = t < self.t_hit
        v = v * air[:, None]
        p[~air] = self.p_hit[~air]
        return p, v, air

_OCT = np.array([[1, 0, 0], [-1, 0, 0], [0, 1, 0], [0, -1, 0], [0, 0, 1], [0, 0, -1]], float)
_OCT_F = np.array([[0, 2, 4], [2, 1, 4], [1, 3, 4], [3, 0, 4], [2, 0, 5], [1, 2, 5], [3, 1, 5], [0, 3, 5]])

def streak_mesh(name, p, v, size, shutter, shape=None, min_len=1.0, width_scale=1.0):
    """One octahedron per particle, stretched along its velocity by speed*shutter (cheap motion blur)."""
    n = len(p)
    sp = np.linalg.norm(v, axis=1)
    d = np.where(sp[:, None] > 1e-6, v / (sp[:, None] + 1e-9), np.array([[1.0, 0, 0]]))
    ref = np.where(np.abs(d[:, 2:3]) < 0.9, np.array([[0, 0, 1.0]]), np.array([[1.0, 0, 0]]))
    a = np.cross(d, ref); a /= np.linalg.norm(a, axis=1, keepdims=True) + 1e-12
    b = np.cross(d, a)
    half = np.maximum(size * min_len, 0.5 * sp * shutter + size)
    w = size * width_scale
    sh = np.ones((n, 2)) if shape is None else shape
    V = (p[:, None, :] + _OCT[None, :, 0:1] * d[:, None, :] * half[:, None, None]
         + _OCT[None, :, 1:2] * a[:, None, :] * (w * sh[:, 0])[:, None, None]
         + _OCT[None, :, 2:3] * b[:, None, :] * (w * sh[:, 1])[:, None, None])
    F = (_OCT_F[None] + (np.arange(n) * 6)[:, None, None]).reshape(-1, 3)
    return new_mesh(name, V.reshape(-1, 3), [F], smooth=False)

class Blast:
    """Owns the non-fluid blast elements and updates them for a given time since detonation."""
    SPARKS = False   # glowing fragment streaks: stylised, not something a real camera sees, so off by default
    def __init__(self, col, seed=5):
        rng = np.random.default_rng(seed)
        self.col = col
        self.clods = Ballistic(520, rng, speed=(5, 34), elev_deg=(6, 82), drag=(1.2, 4.5), size=(0.006, 0.030))
        self.frags = Ballistic(90, rng, speed=(70, 150), elev_deg=(-2, 55), drag=(0.6, 1.6), size=(0.0025, 0.0045), origin=(0, 0, 0.25), spread=0.3)
        self.frag_life = rng.uniform(0.03, 0.13, self.frags.n) * rng.choice([1.0, 1.0, 1.8], self.frags.n)
        m, N, L, P = nodemat("ClodMat")
        P.inputs["Base Color"].default_value = (0.085, 0.062, 0.042, 1); P.inputs["Roughness"].default_value = 0.95
        self.clod_mat = m
        m = bpy.data.materials.new("FragMat"); m.use_nodes = True
        nt = m.node_tree; nt.nodes.clear()
        out = nt.nodes.new("ShaderNodeOutputMaterial"); em = nt.nodes.new("ShaderNodeEmission")
        em.inputs["Color"].default_value = (1.0, 0.62, 0.22, 1); em.inputs["Strength"].default_value = 30.0
        nt.links.new(em.outputs[0], out.inputs["Surface"])
        self.frag_mat = m; self.frag_em = em
        self.clod_ob = new_obj("Clods", bpy.data.meshes.new("clods"), col, self.clod_mat)
        self.frag_ob = new_obj("Frags", bpy.data.meshes.new("frags"), col, self.frag_mat)
        self.frag_ob.visible_shadow = False
        ld = bpy.data.lights.new("Flash", 'POINT'); ld.shadow_soft_size = 0.4; ld.color = (1.0, 0.70, 0.40); ld.energy = 0.0
        self.flash = bpy.data.objects.new("Flash", ld); col.objects.link(self.flash); self.flash.location = (0, 0, 0.55)

    def _swap(self, ob, me, mat):
        me.materials.append(mat); old = ob.data; ob.data = me; bpy.data.meshes.remove(old)

    def update(self, td, shutter, frag_width=1.0, flash_scale=1.0, frag_reach=1.0):
        """td: seconds since detonation (negative = before)."""
        on = td >= 0
        self.clod_ob.hide_render = not on; self.frag_ob.hide_render = not on
        self.flash.data.energy = 60000.0 * flash_scale * math.exp(-td / 0.016) if on else 0.0
        self.flash.hide_render = self.flash.data.energy < 5.0
        if not on:
            return
        p, v, air = self.clods.state(td)
        self._swap(self.clod_ob, streak_mesh("clods", p, v, self.clods.size, shutter, self.clods.shape), self.clod_mat)
        p, v, air = self.frags.state(td)
        life = self.frag_life * frag_reach
        fade = np.clip(1.0 - td / life, 0, 1) * air
        keep = (fade > 0.02) & self.SPARKS
        if keep.any():
            me = streak_mesh("frags", p[keep], v[keep], (self.frags.size * (0.35 + 0.65 * fade))[keep], shutter, width_scale=frag_width)
        else:
            me = bpy.data.meshes.new("frags")
        self._swap(self.frag_ob, me, self.frag_mat)
        self.frag_ob.hide_render = not bool(keep.any())

class Puff:
    """Small noise-shaped dust puff (homogeneous volume in a sphere) for ground impacts."""
    def __init__(self, col, name, loc, seed=0.0):
        P, F, _ = ellipsoid((0, 0, 0), (1, 1, 0.7), 16, 10)
        m = bpy.data.materials.new(name + "Mat"); m.use_nodes = True
        nt = m.node_tree; N = nt.nodes; L = nt.links; N.clear()
        out = N.new("ShaderNodeOutputMaterial")
        tc = N.new("ShaderNodeTexCoord")
        ln = N.new("ShaderNodeVectorMath"); ln.operation = 'LENGTH'; L.new(tc.outputs["Object"], ln.inputs[0])
        fall = N.new("ShaderNodeMapRange"); fall.inputs["From Min"].default_value = 0.25; fall.inputs["From Max"].default_value = 0.95
        fall.inputs["To Min"].default_value = 1.0; fall.inputs["To Max"].default_value = 0.0; L.new(ln.outputs["Value"], fall.inputs["Value"])
        nz = N.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 2.6; nz.inputs["Detail"].default_value = 4
        mp = N.new("ShaderNodeMapping"); mp.inputs["Location"].default_value = (seed, seed * 1.7, 0); L.new(tc.outputs["Object"], mp.inputs[0])
        L.new(mp.outputs[0], nz.inputs["Vector"])
        nr = N.new("ShaderNodeMapRange"); nr.inputs["From Min"].default_value = 0.38; nr.inputs["From Max"].default_value = 0.7
        L.new(nz.outputs["Fac"], nr.inputs["Value"])
        val = N.new("ShaderNodeValue"); val.outputs[0].default_value = 0.0
        m1 = N.new("ShaderNodeMath"); m1.operation = 'MULTIPLY'; L.new(fall.outputs["Result"], m1.inputs[0]); L.new(nr.outputs["Result"], m1.inputs[1])
        m2 = N.new("ShaderNodeMath"); m2.operation = 'MULTIPLY'; L.new(m1.outputs[0], m2.inputs[0]); L.new(val.outputs[0], m2.inputs[1])
        pv = N.new("ShaderNodeVolumePrincipled"); pv.inputs["Color"].default_value = (0.52, 0.42, 0.30, 1)
        L.new(m2.outputs[0], pv.inputs["Density"]); L.new(pv.outputs[0], out.inputs["Volume"])
        self.val = val
        self.ob = new_obj(name, new_mesh(name, P, [F]), col, m); self.ob.location = loc
        self.ob.hide_render = True; self.loc = np.asarray(loc, float)
    def update(self, age, strength=1.0, drift=(0.6, 0, 0)):
        if age < 0 or age > 1.6:
            self.ob.hide_render = True; return
        self.ob.hide_render = False
        r = 0.05 + 0.34 * strength * (1 - math.exp(-age / 0.22))
        self.ob.scale = (r, r, r)
        d = np.asarray(drift) * (1 - math.exp(-age / 0.3)) * 0.25
        self.ob.location = self.loc + d + np.array([0, 0, r * 0.45])
        self.val.outputs[0].default_value = 30.0 * strength * math.exp(-age / 0.45) * min(1.0, age / 0.02)

def emission_mat(name, color, strength, alpha=1.0):
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; N = nt.nodes; L = nt.links; N.clear()
    out = N.new("ShaderNodeOutputMaterial"); em = N.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = (*color, 1); em.inputs["Strength"].default_value = strength
    if alpha < 1.0:
        tr = N.new("ShaderNodeBsdfTransparent"); mx = N.new("ShaderNodeMixShader"); mx.inputs[0].default_value = alpha
        L.new(tr.outputs[0], mx.inputs[1]); L.new(em.outputs[0], mx.inputs[2]); L.new(mx.outputs[0], out.inputs["Surface"])
    else:
        L.new(em.outputs[0], out.inputs["Surface"])
    return m

class Rings:
    """Lethal / casualty radius rings drawn on the ground (emissive, so they sit *in* the scene and get hidden by smoke)."""
    SPEC = [("kill", 5.0, 0.16, (1.0, 0.10, 0.05), 7.0), ("casualty", 15.0, 0.20, (1.0, 0.60, 0.08), 7.0)]
    def __init__(self, col, ground_fn):
        self.col = col; self.gf = ground_fn; self.obs = {}
        for name, r, w, c, s in self.SPEC:
            ob = new_obj("Ring_" + name, bpy.data.meshes.new("ring"), col, emission_mat("RingMat_" + name, c, s))
            ob.visible_shadow = False; ob.visible_diffuse = False; ob.visible_glossy = False
            self.obs[name] = ob
        self.fill = new_obj("Ring_fill", bpy.data.meshes.new("fill"), col, emission_mat("RingFill", (1.0, 0.08, 0.03), 1.6, alpha=0.045))
        self.fill.visible_shadow = False; self.fill.visible_diffuse = False; self.fill.visible_glossy = False
        self.ticks = new_obj("Ring_ticks", bpy.data.meshes.new("ticks"), col, emission_mat("RingTick", (1.0, 0.92, 0.80), 5.0))
        self.ticks.visible_shadow = False; self.ticks.visible_diffuse = False
        self.set_visible(False)
    def set_visible(self, v):
        for ob in list(self.obs.values()) + [self.fill, self.ticks]:
            ob.hide_render = not v
    def _arc(self, r, w, frac, n=360, z=0.10, start=math.radians(90)):
        m = max(2, int(n * frac) + 1)
        a = start - np.linspace(0, 2 * np.pi * frac, m)          # clockwise from the top
        ca, sa = np.cos(a), np.sin(a)
        zi = self.gf(r * ca, r * sa) + z
        inner = np.stack([(r - w / 2) * ca, (r - w / 2) * sa, zi], 1); outer = np.stack([(r + w / 2) * ca, (r + w / 2) * sa, zi], 1)
        V = np.empty((m * 2, 3)); V[0::2] = inner; V[1::2] = outer
        return V, grid_faces(m, 2)
    def update(self, progress):
        """progress: dict name -> 0..1 draw-on fraction."""
        self.set_visible(any(v > 0 for v in progress.values()))
        for name, r, w, c, s in self.SPEC:
            f = progress.get(name, 0.0); ob = self.obs[name]
            ob.hide_render = f <= 0.001
            if f > 0.001:
                V, F = self._arc(r, w, f)
                me = new_mesh("ring", V, [F], smooth=False); me.materials.append(ob.data.materials[0])
                old = ob.data; ob.data = me; bpy.data.meshes.remove(old)
        f = progress.get("kill", 0.0)
        self.fill.hide_render = f < 0.999
        if f >= 0.999 and len(self.fill.data.vertices) == 0:
            a = np.linspace(0, 2 * np.pi, 96, endpoint=False); rr = np.linspace(0.6, 4.92, 10)
            A, R_ = np.meshgrid(a, rr, indexing="ij")
            V = np.stack([R_ * np.cos(A), R_ * np.sin(A), self.gf(R_ * np.cos(A), R_ * np.sin(A)) + 0.09], -1).reshape(-1, 3)
            me = new_mesh("fill", V, [grid_faces(96, 10, wrap_u=True)]); me.materials.append(self.fill.data.materials[0])
            old = self.fill.data; self.fill.data = me; bpy.data.meshes.remove(old)
        # metre ticks along the +X axis out to 15 m
        ft = progress.get("ticks", 0.0)
        self.ticks.hide_render = ft <= 0.001
        if ft > 0.001:
            g = Geo(); reach = 15.0 * ft
            for d in range(1, 16):
                if d > reach:
                    break
                ln = 0.9 if d % 5 == 0 else 0.42
                x = float(d); z = float(self.gf(x, 0.0)) + 0.10
                g.add([[x - 0.035, -ln / 2, z], [x + 0.035, -ln / 2, z], [x + 0.035, ln / 2, z], [x - 0.035, ln / 2, z]], [[0, 1, 2, 3]])
            z = 0.10
            g.add([[0.5, -0.03, z], [reach, -0.03, z], [reach, 0.03, z], [0.5, 0.03, z]], [[0, 1, 2, 3]])
            me = g.mesh("ticks", smooth=False); me.materials.append(self.ticks.data.materials[0])
            old = self.ticks.data; self.ticks.data = me; bpy.data.meshes.remove(old)
