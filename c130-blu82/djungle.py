"""The target: dense rain forest on gently rolling ground, and what the burst leaves of it.

Three storeys, as such forest is described: scattered emergent trees 42 to 52 m tall, a closed main canopy 26 to 36 m
up (about 95 trees to the hectare), and undergrowth beneath.  Inside 300 m of the aim point every canopy tree is its
own object; beyond that the canopy is one rough green surface to the horizon.  The place is invented.

Jungle(sc, col).update(td)   td = seconds after the burst
What the burst does to each tree depends on its distance (radii in dconst): inside R_CLEAR it is gone, leaving a stump;
out to R_DOWN it is stripped and thrown down pointing away from the burst; out to R_STRIP its leaves are burnt off
and it is left leaning; beyond that it only sways.  Nobody is modelled.
"""
import bpy, bmesh, math, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
for p in ("grenade-explosion", "reaper-hellfire"):
    sys.path.insert(0, os.path.join(HERE, "..", p))
sys.path.insert(0, HERE)
from mathutils import Quaternion, Vector
from qgeo import Shell, box as gbox, revolve, EX, EY, EZ
from util import new_mesh, new_obj, grid_faces, nodemat, smoothstep, fbm
import env
import dconst as C

R_NEAR = 300.0                                                        # single trees inside this radius
R_ACT = C.R_STRIP * 1.45                                              # trees inside this radius can move
CAN_H = 31.0                                                          # mean height of the main canopy
LEAF = [(0.030, 0.070, 0.018, 1), (0.040, 0.085, 0.022, 1), (0.024, 0.058, 0.020, 1), (0.050, 0.092, 0.026, 1)]
BARK = (0.115, 0.095, 0.075, 1); BARK2 = (0.22, 0.19, 0.155, 1); WOOD = (0.52, 0.42, 0.27, 1); EARTH = (0.36, 0.26, 0.165, 1); EARTH2 = (0.27, 0.19, 0.12, 1); FLOOR = (0.040, 0.050, 0.022, 1)
SCORCH = (0.030, 0.026, 0.022, 1)

def terrain(x, y):
    """Height of the ground: low rolling hills, level at the aim point."""
    x = np.asarray(x, np.float64); y = np.asarray(y, np.float64); r = np.hypot(x, y)
    h = 26.0 * (fbm(x / 520.0 + 3.1, y / 520.0 - 1.7, 5, 3) - 0.5) + 7.0 * (fbm(x / 140.0, y / 140.0, 9, 3) - 0.5)
    return h * np.clip((r - 35.0) / 160.0, 0.0, 1.0) ** 1.5

def _ico(sub=2):
    bm = bmesh.new(); bmesh.ops.create_icosphere(bm, subdivisions=sub, radius=1.0); bm.verts.ensure_lookup_table()
    V = np.array([v.co[:] for v in bm.verts]); F = np.array([[v.index for v in f.verts] for f in bm.faces]); bm.free(); return V, F

_ICO = None

def _blob(S, rng, c, r, flat=0.62, colors=LEAF, sub=2):
    """One mass of foliage: a lumpy flattened ball, darker underneath."""
    global _ICO
    if _ICO is None:
        _ICO = {1: _ico(1), 2: _ico(2)}
    V0, F = _ICO[sub]; ph = rng.uniform(0, 6.28, 3); k = 1.0 + 0.22 * np.sin(V0[:, 0] * 3.1 + ph[0]) * np.sin(V0[:, 1] * 2.7 + ph[1]) + 0.16 * np.sin(V0[:, 2] * 4.3 + ph[2] + V0[:, 0] * 2.0)
    V = V0 * k[:, None] * np.array([r, r, r * flat]) + np.asarray(c); base = np.array(colors[int(rng.integers(len(colors)))]); sh = 0.45 + 0.55 * np.clip((V0[:, 2] + 0.5) / 1.3, 0, 1)
    col = np.tile(base, (len(V), 1)); col[:, :3] *= sh[:, None] * float(rng.uniform(0.85, 1.15)); S.add(V, None, F, col)

def _trunk(S, h, rb, rt, lean=(0.0, 0.0), n=8, color=BARK):
    zs = [0.0, 0.008 * h, 0.04 * h, h * 0.5, h]; rs = [rb * 1.7, rb * 1.25, rb, (rb + rt) / 2, rt]; a = np.linspace(0, 2 * np.pi, n, endpoint=False); rows = []
    for z, r in zip(zs, rs):
        rows.append(np.stack([r * np.cos(a) + lean[0] * (z / h) ** 2, r * np.sin(a) + lean[1] * (z / h) ** 2, np.full(n, z)], 1))
    S.add(np.concatenate(rows), grid_faces(len(zs), n, wrap_v=True), None, color)

def _tree_variant(rng, h, cr, rb, k):
    """Meshes of one kind of tree: trunk, crown, and the same crown stripped to its limbs."""
    T = Shell(); lean = (float(rng.uniform(-0.03, 0.03)) * h, float(rng.uniform(-0.03, 0.03)) * h); _trunk(T, h * 0.86, rb, rb * 0.42, lean)
    Cr = Shell(); B = Shell(); top = np.array([lean[0], lean[1], h * 0.84]); nb = int(rng.integers(6, 10))
    _blob(Cr, rng, top + np.array([0, 0, cr * 0.16]), cr * 0.74)
    for j in range(nb):
        a = 2 * math.pi * j / nb + float(rng.uniform(-0.3, 0.3)); d = cr * float(rng.uniform(0.50, 0.85)); c = top + np.array([d * math.cos(a), d * math.sin(a), float(rng.uniform(-0.34, 0.14)) * cr])
        _blob(Cr, rng, c, cr * float(rng.uniform(0.40, 0.58)))
        e = c - top; L_ = np.linalg.norm(e); ex = e / L_; ey = np.cross(EZ, ex); ey /= np.linalg.norm(ey); ez = np.cross(ex, ey)             # a limb out to each mass of leaves
        for S_ in (Cr, B):
            S_.add(*gbox(top + e * 0.5, (L_, rb * 0.34, rb * 0.34), rot=np.stack([ex, ey, ez], 1)), color=BARK)
    return T.mesh("jt_trunk%d" % k, sharp=1.2), Cr.mesh("jt_crown%d" % k, sharp=3.0), B.mesh("jt_bare%d" % k, sharp=1.2)

def leaf_mat():
    """Foliage: colours from the 'col' attribute, each tree a little different, matt with a faint sheen."""
    m, N, L, P = nodemat("JungleLeaf"); a = N.new("ShaderNodeAttribute"); a.attribute_name = "col"; oi = N.new("ShaderNodeObjectInfo")
    mr = N.new("ShaderNodeMapRange"); mr.inputs["To Min"].default_value = 0.70; mr.inputs["To Max"].default_value = 1.35; L.new(oi.outputs["Random"], mr.inputs["Value"])
    mx = N.new("ShaderNodeMixRGB"); mx.blend_type = 'MULTIPLY'; mx.inputs[0].default_value = 1.0; L.new(a.outputs["Color"], mx.inputs[1]); L.new(mr.outputs[0], mx.inputs[2])
    tc = N.new("ShaderNodeTexCoord"); n = N.new("ShaderNodeTexNoise"); n.inputs["Scale"].default_value = 34.0; n.inputs["Detail"].default_value = 6; n.inputs["Roughness"].default_value = 0.65; L.new(tc.outputs["Object"], n.inputs["Vector"])
    m2 = N.new("ShaderNodeMapRange"); m2.inputs["To Min"].default_value = 0.35; m2.inputs["To Max"].default_value = 1.7; L.new(n.outputs["Fac"], m2.inputs["Value"])
    mx2 = N.new("ShaderNodeMixRGB"); mx2.blend_type = 'MULTIPLY'; mx2.inputs[0].default_value = 1.0; L.new(mx.outputs[0], mx2.inputs[1]); L.new(m2.outputs[0], mx2.inputs[2]); L.new(mx2.outputs[0], P.inputs["Base Color"])
    b = N.new("ShaderNodeBump"); b.inputs["Strength"].default_value = 1.0; b.inputs["Distance"].default_value = 0.02; L.new(n.outputs["Fac"], b.inputs["Height"]); L.new(b.outputs["Normal"], P.inputs["Normal"])
    P.inputs["Roughness"].default_value = 0.62
    return m

def canopy_mat():
    """The far canopy seen as one surface: the same greens, broken into crowns by noise at the scale of a tree."""
    m, N, L, P = nodemat("JungleCanopy"); tc = N.new("ShaderNodeTexCoord")
    v = N.new("ShaderNodeTexVoronoi"); v.inputs["Scale"].default_value = 1.0 / 11.0; L.new(tc.outputs["Object"], v.inputs["Vector"])
    cr = N.new("ShaderNodeValToRGB"); e = cr.color_ramp.elements; e[0].position = 0.0; e[0].color = (0.050, 0.092, 0.026, 1); e[1].position = 0.75; e[1].color = (0.012, 0.030, 0.010, 1); L.new(v.outputs["Distance"], cr.inputs["Fac"])
    hs = N.new("ShaderNodeHueSaturation"); L.new(cr.outputs["Color"], hs.inputs["Color"]); sp = N.new("ShaderNodeSeparateColor"); L.new(v.outputs["Color"], sp.inputs[0])
    mr = N.new("ShaderNodeMapRange"); mr.inputs["To Min"].default_value = 0.65; mr.inputs["To Max"].default_value = 1.45; L.new(sp.outputs[0], mr.inputs["Value"]); L.new(mr.outputs[0], hs.inputs["Value"])
    big = N.new("ShaderNodeTexNoise"); big.inputs["Scale"].default_value = 1.0 / 420.0; big.inputs["Detail"].default_value = 7; big.inputs["Roughness"].default_value = 0.6; L.new(tc.outputs["Object"], big.inputs["Vector"])        # the forest is not one green: patches at the scale of hills
    bm_ = N.new("ShaderNodeMapRange"); bm_.inputs["From Min"].default_value = 0.3; bm_.inputs["From Max"].default_value = 0.7; bm_.inputs["To Min"].default_value = 0.55; bm_.inputs["To Max"].default_value = 1.5; L.new(big.outputs["Fac"], bm_.inputs["Value"])
    mb = N.new("ShaderNodeMixRGB"); mb.blend_type = 'MULTIPLY'; mb.inputs[0].default_value = 1.0; L.new(hs.outputs["Color"], mb.inputs[1]); L.new(bm_.outputs[0], mb.inputs[2])
    L.new(mb.outputs[0], P.inputs["Base Color"]); P.inputs["Roughness"].default_value = 0.65
    b = N.new("ShaderNodeBump"); b.inputs["Strength"].default_value = 1.0; b.inputs["Distance"].default_value = 4.0; b.invert = True; L.new(v.outputs["Distance"], b.inputs["Height"]); L.new(b.outputs["Normal"], P.inputs["Normal"])
    return m

def ground_mat():
    m, N, L, P = nodemat("JungleFloor"); a = N.new("ShaderNodeAttribute"); a.attribute_name = "col"; tc = N.new("ShaderNodeTexCoord"); prev = a.outputs["Color"]
    for scale, lo, hi in ((0.06, 0.70, 1.25), (0.9, 0.78, 1.20), (9.0, 0.85, 1.14)):
        n = N.new("ShaderNodeTexNoise"); n.inputs["Scale"].default_value = scale; n.inputs["Detail"].default_value = 5; L.new(tc.outputs["Object"], n.inputs["Vector"])
        mr = N.new("ShaderNodeMapRange"); mr.inputs["To Min"].default_value = lo; mr.inputs["To Max"].default_value = hi; L.new(n.outputs["Fac"], mr.inputs["Value"])
        mx = N.new("ShaderNodeMixRGB"); mx.blend_type = 'MULTIPLY'; mx.inputs[0].default_value = 1.0; L.new(prev, mx.inputs[1]); L.new(mr.outputs[0], mx.inputs[2]); prev = mx.outputs[0]
    L.new(prev, P.inputs["Base Color"]); P.inputs["Roughness"].default_value = 0.95
    return m

def arrival(d):
    """Seconds after the burst at which the blast reaches distance d (fast near the bomb, the speed of sound far out)."""
    return d / (345.0 + 1500.0 * math.exp(-d / 35.0))

class Jungle:
    def __init__(self, sc, col, seed=23):
        rng = np.random.default_rng(seed); self.col = col; env.make_world(sc)
        self.paint = bpy.data.materials.get("JunglePaint") or env.mat_vcol("JunglePaint", rough=0.9, bump_scale=5); lm = leaf_mat(); gm = ground_mat()
        # ---- the ground near the aim point, before and after
        xs = np.arange(-R_NEAR - 20.0, R_NEAR + 20.01, 2.5); X, Y = np.meshgrid(xs, xs, indexing="ij"); Rr = np.hypot(X, Y); Z = terrain(X, Y) + 0.12 * (fbm(X * 0.4, Y * 0.4, 2, 3) - 0.5); F = grid_faces(len(xs), len(xs))
        c0 = np.tile(np.array(FLOOR, np.float32), X.shape + (1,))
        self.g0 = new_obj("Floor", new_mesh("floor", np.stack([X, Y, Z], -1).reshape(-1, 3), [F], attrs={"col": c0.reshape(-1, 4)}), col, gm)
        wob = 1.0 + 0.12 * np.sin(3 * np.arctan2(Y, X) + 0.6) + 0.07 * np.sin(8 * np.arctan2(Y, X) + 2.0); rr = Rr / wob
        k = np.clip((C.R_DOWN * 1.05 - rr) / (C.R_DOWN * 0.55), 0, 1)[..., None]; patch = (fbm(X * 0.35, Y * 0.35, 5, 3) > 0.5)[..., None]
        c1 = c0 * (1 - k) + np.where(patch, np.array(EARTH, np.float32), np.array(EARTH2, np.float32)) * k                       # bare earth where the forest floor has been swept off
        ks = np.clip((C.R_FIRE * 1.1 - rr) / (C.R_FIRE * 0.8), 0, 1)[..., None] * 0.75; c1 = c1 * (1 - ks) + np.array(SCORCH, np.float32) * ks
        Z1 = Z - C.DENT[0] * np.exp(-(rr / C.DENT[1]) ** 2)                                                                      # no crater: a dent a foot deep at most
        self.g1 = new_obj("FloorAfter", new_mesh("floor_after", np.stack([X, Y, Z1], -1).reshape(-1, 3), [F], attrs={"col": c1.reshape(-1, 4).astype(np.float32)}), col, gm)
        # ---- undergrowth: a rough green layer a few metres up, with a hole where it has been blown away
        xu = np.arange(-R_NEAR - 20.0, R_NEAR + 20.01, 3.0); Xu, Yu = np.meshgrid(xu, xu, indexing="ij"); Ru = np.hypot(Xu, Yu); Zu = terrain(Xu, Yu) + 2.0 + 5.5 * fbm(Xu / 7.0, Yu / 7.0, 4, 4); Fu = grid_faces(len(xu), len(xu))
        cu = np.tile(np.array(LEAF[2], np.float32), Xu.shape + (1,)); cu[..., :3] *= (0.55 + 0.8 * fbm(Xu / 5.0, Yu / 5.0, 6, 3))[..., None]
        self.u0 = new_obj("Undergrowth", new_mesh("undergrowth", np.stack([Xu, Yu, Zu], -1).reshape(-1, 3), [Fu], attrs={"col": cu.reshape(-1, 4)}), col, lm)
        keep = np.clip((Ru - C.R_DOWN * 0.92) / (C.R_STRIP * 1.05 - C.R_DOWN * 0.92), 0, 1); Zu1 = terrain(Xu, Yu) - 0.4 + (Zu - terrain(Xu, Yu) + 0.4) * keep
        cu1 = cu.copy(); cu1[..., :3] = cu[..., :3] * keep[..., None] + np.array(EARTH2[:3], np.float32) * (1 - keep[..., None]) * 0.9
        self.u1 = new_obj("UndergrowthAfter", new_mesh("undergrowth_after", np.stack([Xu, Yu, Zu1], -1).reshape(-1, 3), [Fu], attrs={"col": cu1.reshape(-1, 4).astype(np.float32)}), col, lm)
        # ---- the canopy beyond the single trees, out to the horizon
        na = 220; rr_ = np.concatenate([np.arange(R_NEAR - 14.0, 900.0, 4.0), np.geomspace(900.0, 9.0e4, 70)]); a = np.linspace(0, 2 * np.pi, na, endpoint=False); A, Rg = np.meshgrid(a, rr_, indexing="ij")
        Xc, Yc = Rg * np.cos(A), Rg * np.sin(A); fade = np.clip((4000.0 - Rg) / 3000.0, 0.0, 1.0)
        Zc = terrain(Xc, Yc) * np.clip((6000.0 - Rg) / 5000.0, 0, 1) + CAN_H - 4.0 + (11.0 * (fbm(Xc / 16.0, Yc / 16.0, 7, 4) - 0.3) + 5.0 * fbm(Xc / 5.5, Yc / 5.5, 8, 3)) * fade
        new_obj("CanopyFar", new_mesh("canopy_far", np.stack([Xc, Yc, Zc], -1).reshape(-1, 3), [grid_faces(na, len(rr_), wrap_u=True)]), col, canopy_mat())
        # ---- the trees
        kinds = [_tree_variant(rng, 1.0, float(rng.uniform(0.19, 0.24)), float(rng.uniform(0.010, 0.014)), k) for k in range(5)] + [_tree_variant(rng, 1.0, float(rng.uniform(0.17, 0.20)), float(rng.uniform(0.013, 0.017)), 5 + k) for k in range(2)]
        for tm, cm, bm_ in kinds:
            tm.materials.append(self.paint); cm.materials.append(lm); bm_.materials.append(self.paint)
        whole = []
        for k, (tm, cm, bm_) in enumerate(kinds):                         # trunk and crown as one mesh for the trees that never move
            S = Shell()
            for me in (tm, cm):
                co = np.zeros(len(me.vertices) * 3); me.vertices.foreach_get("co", co)
                colr = np.zeros(len(me.vertices) * 4, np.float32); me.attributes["col"].data.foreach_get("color", colr); fq = [list(p.vertices) for p in me.polygons]
                S.add(co.reshape(-1, 3), [f for f in fq if len(f) == 4], [f for f in fq if len(f) == 3], colr.reshape(-1, 4))
            wm = S.mesh("jt_whole%d" % k, sharp=3.0); wm.materials.append(lm); whole.append(wm)
        self.trees = []; cell = 10.3; g = np.arange(-R_NEAR, R_NEAR + 0.1, cell); n_far = 0
        for gx in g:
            for gy in g:
                x = gx + float(rng.uniform(-4.2, 4.2)); y = gy + float(rng.uniform(-4.2, 4.2)); d = math.hypot(x, y)
                if d > R_NEAR or rng.random() < 0.05:
                    continue
                emergent = rng.random() < 0.085; k = int(rng.integers(5, 7)) if emergent else int(rng.integers(0, 5)); h = float(rng.uniform(42.0, 52.0) if emergent else rng.uniform(26.0, 36.0))
                z = float(terrain(x, y)); yaw = float(rng.uniform(0, 6.283))
                if d > R_ACT:
                    o = bpy.data.objects.new("T", whole[k]); col.objects.link(o); o.location = (x, y, z - 0.2); o.scale = (h, h, h); o.rotation_euler = (0, 0, yaw); n_far += 1
                    continue
                root = bpy.data.objects.new("Tr", None); col.objects.link(root); root.location = (x, y, z - 0.2); root.scale = (h, h, h); root.rotation_mode = 'QUATERNION'
                tr = bpy.data.objects.new("Tt", kinds[k][0]); col.objects.link(tr); tr.parent = root; cr = bpy.data.objects.new("Tc", kinds[k][1]); col.objects.link(cr); cr.parent = root
                br = bpy.data.objects.new("Tb", kinds[k][2]); col.objects.link(br); br.parent = root
                az = math.atan2(y, x); self.trees.append(dict(root=root, trunk=tr, crown=cr, bare=br, d=d, az=az, yaw=yaw, h=h, ta=arrival(d), fall=float(rng.uniform(1.2, 2.6)), end=math.radians(float(rng.uniform(80.0, 93.0))),
                                                              lean=math.radians(float(rng.uniform(3.0, 16.0))), snap=bool(rng.random() < 0.28), skew=float(rng.uniform(-0.35, 0.35)), ph=float(rng.uniform(0, 6.28)), pos=(x, y, z)))
        self.n_trees = len(self.trees) + n_far
        # ---- what is left in the cleared ground: stumps, splintered trunks lying outwards, torn wood
        S = Shell(); L_ = Shell()
        for t in self.trees:
            x, y, z = t["pos"]; rb = 0.012 * t["h"]
            if 9.0 < t["d"] < C.R_CLEAR:                               # stumps are left standing, except close in, where trees are torn out whole
                hh = float(rng.uniform(0.3, 1.6)); S.add(*revolve([(0.0, rb * 1.7), (hh * 0.3, rb * 1.2), (hh, rb * 1.0), (hh + 0.25, rb * 0.3)], 7, axis=EZ, origin=(x, y, z - 0.2)), color=WOOD if rng.random() < 0.5 else BARK2)
                if rng.random() < 0.40:                                # part of its trunk, thrown outwards and left lying
                    dd = t["d"] + float(rng.uniform(6.0, 0.8 * C.R_CLEAR)); a_ = t["az"] + float(rng.uniform(-0.25, 0.25)); ln = float(rng.uniform(5.0, 14.0)); c = np.array([dd * math.cos(a_), dd * math.sin(a_), 0.0]); c[2] = float(terrain(c[0], c[1])) + rb
                    ex = np.array([math.cos(a_ + t["skew"]), math.sin(a_ + t["skew"]), 0.0]); ey = np.cross(EZ, ex); L_.add(*gbox(c, (ln, rb * 1.8, rb * 1.8), rot=np.stack([ex, ey, EZ], 1)), color=BARK2 if rng.random() < 0.6 else WOOD)
        for j in range(900):                                           # torn wood and limbs
            a_ = float(rng.uniform(0, 6.283)); dd = C.R_DOWN * float(rng.uniform(0.08, 1.1) ** 0.7); c = np.array([dd * math.cos(a_), dd * math.sin(a_), 0.0]); c[2] = float(terrain(c[0], c[1])) + 0.15
            ex = np.array([math.cos(a_ + float(rng.uniform(-0.9, 0.9))), math.sin(a_ + float(rng.uniform(-0.9, 0.9))), 0.0]); ey = np.cross(EZ, ex); L_.add(*gbox(c, (float(rng.uniform(1.0, 5.0)), float(rng.uniform(0.08, 0.3)), float(rng.uniform(0.08, 0.3))), rot=np.stack([ex, ey, EZ], 1)), color=[WOOD, BARK, BARK2][j % 3])
        self.stumps = new_obj("Stumps", S.mesh("stumps", sharp=1.0), col, self.paint); self.litter = new_obj("Litter", L_.mesh("litter", sharp=1.0), col, self.paint)
        self.update(-1.0)

    def update(self, td):
        fired = bool(td >= 0.08)
        self.g0.hide_render = fired; self.g1.hide_render = not fired; self.u0.hide_render = fired; self.u1.hide_render = not fired
        self.stumps.hide_render = not fired; self.litter.hide_render = bool(td < 1.2)
        for t in self.trees:
            d = t["d"]; u = td - t["ta"]; hit = u > 0; ax = Vector((-math.sin(t["az"] + t["skew"]), math.cos(t["az"] + t["skew"]), 0.0)); yaw = Quaternion((0, 0, 1), t["yaw"])
            if not hit:
                ang = 0.0; show = (True, True, False)
            elif d < C.R_CLEAR:
                ang = 0.0; show = (False, False, False)
            elif d < C.R_DOWN:
                gone = t["snap"] and d < (C.R_CLEAR + C.R_DOWN) / 2                              # some are broken off and carried away; the rest go over where they stand
                ang = t["end"] * min(1.0, (u / t["fall"])) ** 2; show = (not gone, False, False)
            elif d < C.R_STRIP:
                ang = t["lean"] * (1.0 - math.exp(-u / 0.5)) + math.radians(5.0) * math.exp(-u / 2.5) * math.sin(4.2 * u + t["ph"]); show = (True, False, True)
            else:
                ang = math.radians(6.0) * (C.R_STRIP / d) ** 2 * math.exp(-u / 3.0) * math.sin(3.6 * u); show = (True, True, False)
            t["root"].rotation_quaternion = Quaternion(ax, ang) @ yaw
            for o, s in zip((t["trunk"], t["crown"], t["bare"]), show):
                o.hide_render = not s
