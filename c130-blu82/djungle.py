"""The target: tall, dense rain forest on gently rolling ground, and what the burst does to it.

Nobody and nothing man-made is in it.  The forest is invented: three storeys of trees, the tallest about 45 m (the
published limit for the bomb is trees 150 ft tall and 4 ft thick), closed canopy, undergrowth.
What the burst leaves is built to the published result: a clearing about 260 ft (79 m) across in which nothing
stands, almost no crater (a dish a few metres across and a hand deep), and hardly any debris piled at the edge.
Inside that circle the trunks are snapped off and thrown down pointing away from the centre; the innermost are broken
up altogether; round the clearing the trees are stripped and left leaning.  The radii of those zones other than the
clearing itself, and the timing, are staging (see dconst).

Jungle(sc, col, kind)   kind "out": the whole forest; "sec": only the half behind the plane y = 0, with the ground cut
AirFloor(sc, col)       the forest from 1,800 m up, for the shots of the aircraft
"""
import bpy, math, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
for p in ("grenade-explosion", "rpg7-explosion", "mortar-explosion", "howitzer-explosion", "reaper-hellfire"):
    sys.path.insert(0, os.path.join(HERE, "..", p))
sys.path.insert(0, HERE)
from mathutils import Quaternion, Vector
from qgeo import Shell, box as gbox, revolve, plate, loft, ellipsoid, paint_mat, EX, EY, EZ
from util import new_mesh, new_obj, grid_faces, nodemat, smoothstep, fbm
import env
import dconst as C
env.SUN_ELEV = math.radians(56.0)                                     # a high tropical sun (the shared sky module's default is a low one)

R_OBJ = 236.0                                                         # single trees out to here; beyond, the canopy is one surface
R_OBJ2 = 296.0                                                        # in the full forest a further ring of single trees, added for the wide view of the burst
CANOPY_Z = 31.0
BARK = [(0.16, 0.13, 0.10, 1), (0.20, 0.17, 0.13, 1), (0.12, 0.10, 0.08, 1)]
GREENS = [(0.035, 0.085, 0.020), (0.050, 0.105, 0.025), (0.028, 0.070, 0.022), (0.060, 0.115, 0.030), (0.040, 0.095, 0.035)]

def ground_h(x, y):
    """Rolling ground, level round the burst point."""
    x = np.asarray(x, float); y = np.asarray(y, float); r = np.hypot(x, y)
    h = 9.0 * np.sin(x * 0.0061 + 0.8) * np.cos(y * 0.0053 - 0.3) + 5.0 * np.sin(x * 0.013 - y * 0.011 + 2.0) + 60.0 * np.sin(x * 0.0011 + 1.3) * np.sin(y * 0.0014 + 0.4) + 160.0 * (np.sin(x * 0.00037 - 0.9) * np.cos(y * 0.00031 + 2.2) + 0.75)
    k = np.clip((r - 70.0) / 500.0, 0, 1); k = k * k * (3 - 2 * k)
    return (h - (9.0 * math.sin(0.8) * math.cos(-0.3) + 5.0 * math.sin(2.0) + 60.0 * math.sin(1.3) * math.sin(0.4) + 160.0 * (math.sin(-0.9) * math.cos(2.2) + 0.75))) * k + 0.12 * np.sin(x * 0.4 + 1.0) * np.cos(y * 0.35) * np.clip(r / 20.0, 0, 1)

def _h2(ix, iy, seed):
    n = (ix * 374761393 + iy * 668265263 + seed * 1442695041) & 0xFFFFFFFF; n = ((n ^ (n >> 13)) * 1274126177) & 0xFFFFFFFF; return ((n ^ (n >> 16)) & 0xFFFF) / 65535.0

def crown_h(x, y, cell=9.0):
    """Bumps like tree crowns seen from above: for every point the height of the nearest of a jittered grid of domes."""
    x = np.asarray(x, float); y = np.asarray(y, float); gx = np.floor(x / cell).astype(np.int64); gy = np.floor(y / cell).astype(np.int64); best = np.full(x.shape, -9.0)
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            cx = gx + dx; cy = gy + dy; px = (cx + 0.15 + 0.7 * _h2(cx, cy, 1)) * cell; py = (cy + 0.15 + 0.7 * _h2(cx, cy, 2)) * cell; rr = cell * (0.62 + 0.25 * _h2(cx, cy, 3)); top = 7.0 * _h2(cx, cy, 4)
            d2 = ((x - px) ** 2 + (y - py) ** 2) / (rr * rr); best = np.maximum(best, top + 4.5 * (1 - d2))
    return np.maximum(best, -3.0)

# ----------------------------------------------------------------------------- materials
def leaf_mat():
    m = bpy.data.materials.get("JungleLeaf")
    if m:
        return m
    m = env.mat_vcol("JungleLeaf", rough=0.62, translucent=0.18); return m

def canopy_mat(air=False):
    """The closed canopy as one surface: crowns drawn with a cell pattern, the gaps between them dark."""
    name = "CanopyAir" if air else "CanopyFar"; m = bpy.data.materials.get(name)
    if m:
        return m
    m, N, L, P = nodemat(name); tc = N.new("ShaderNodeTexCoord"); geo = N.new("ShaderNodeNewGeometry")
    vo = N.new("ShaderNodeTexVoronoi"); vo.inputs["Scale"].default_value = 1.0 / 10.0; vo.feature = 'F1'; L.new(geo.outputs["Position"], vo.inputs["Vector"])
    nz = N.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 1.0 / 180.0; nz.inputs["Detail"].default_value = 4; L.new(geo.outputs["Position"], nz.inputs["Vector"])
    cr = N.new("ShaderNodeValToRGB"); e = cr.color_ramp.elements; e[0].position = 0.0; e[0].color = (0.085, 0.170, 0.040, 1); e[1].position = 0.75; e[1].color = (0.012, 0.034, 0.010, 1)
    L.new(vo.outputs["Distance"], cr.inputs["Fac"])
    mixc = N.new("ShaderNodeMixRGB"); mixc.blend_type = 'MULTIPLY'; mixc.inputs[0].default_value = 0.85; L.new(cr.outputs["Color"], mixc.inputs[1])
    tint = N.new("ShaderNodeValToRGB"); t = tint.color_ramp.elements; t[0].position = 0.3; t[0].color = (0.55, 0.75, 0.55, 1); t[1].position = 0.7; t[1].color = (1.0, 1.0, 0.75, 1); L.new(nz.outputs["Fac"], tint.inputs["Fac"]); L.new(tint.outputs["Color"], mixc.inputs[2])
    hue = N.new("ShaderNodeMixRGB"); hue.blend_type = 'MULTIPLY'; hue.inputs[0].default_value = 0.35; L.new(mixc.outputs[0], hue.inputs[1]); L.new(vo.outputs["Color"], hue.inputs[2])
    col_out = hue.outputs[0]
    if air:                                                           # a brown river winding through it
        sp = N.new("ShaderNodeSeparateXYZ"); L.new(geo.outputs["Position"], sp.inputs[0])
        rn = N.new("ShaderNodeTexNoise"); rn.inputs["Scale"].default_value = 1.0 / 1500.0; rn.inputs["Detail"].default_value = 2; rn.noise_dimensions = '1D' if hasattr(rn, "noise_dimensions") else rn.noise_dimensions
        L.new(sp.outputs["X"], rn.inputs["W"])
        off = N.new("ShaderNodeMath"); off.operation = 'MULTIPLY_ADD'; off.inputs[1].default_value = 2600.0; off.inputs[2].default_value = -1900.0; L.new(rn.outputs["Fac"], off.inputs[0])
        dy = N.new("ShaderNodeMath"); dy.operation = 'SUBTRACT'; L.new(sp.outputs["Y"], dy.inputs[0]); L.new(off.outputs[0], dy.inputs[1])
        ab = N.new("ShaderNodeMath"); ab.operation = 'ABSOLUTE'; L.new(dy.outputs[0], ab.inputs[0])
        lt = N.new("ShaderNodeMath"); lt.operation = 'LESS_THAN'; lt.inputs[1].default_value = 34.0; L.new(ab.outputs[0], lt.inputs[0])
        rv = N.new("ShaderNodeMixRGB"); rv.inputs[2].default_value = (0.13, 0.10, 0.06, 1); L.new(lt.outputs[0], rv.inputs[0]); L.new(col_out, rv.inputs[1]); col_out = rv.outputs[0]
    L.new(col_out, P.inputs["Base Color"]); P.inputs["Roughness"].default_value = 0.7; P.inputs["Specular IOR Level"].default_value = 0.2
    bp = N.new("ShaderNodeBump"); bp.inputs["Strength"].default_value = 1.0; bp.inputs["Distance"].default_value = 5.0; inv = N.new("ShaderNodeMath"); inv.operation = 'SUBTRACT'; inv.inputs[0].default_value = 1.0
    L.new(vo.outputs["Distance"], inv.inputs[1]); L.new(inv.outputs[0], bp.inputs["Height"]); L.new(bp.outputs["Normal"], P.inputs["Normal"])
    return m

def soil_mat(name="JungleSoil"):
    """Dark, littered forest floor; inside the clearing, after the burst, pale churned soil with a scorched middle."""
    m = bpy.data.materials.get(name)
    if m:
        return m
    m, N, L, P = nodemat(name); geo = N.new("ShaderNodeNewGeometry")
    n1 = N.new("ShaderNodeTexNoise"); n1.inputs["Scale"].default_value = 0.35; n1.inputs["Detail"].default_value = 8; L.new(geo.outputs["Position"], n1.inputs["Vector"])
    n2 = N.new("ShaderNodeTexNoise"); n2.inputs["Scale"].default_value = 3.0; n2.inputs["Detail"].default_value = 6; L.new(geo.outputs["Position"], n2.inputs["Vector"])
    floor = N.new("ShaderNodeValToRGB"); e = floor.color_ramp.elements; e[0].position = 0.35; e[0].color = (0.030, 0.026, 0.016, 1); e[1].position = 0.70; e[1].color = (0.075, 0.062, 0.032, 1); L.new(n1.outputs["Fac"], floor.inputs["Fac"])
    bare = N.new("ShaderNodeValToRGB"); e = bare.color_ramp.elements; e[0].position = 0.30; e[0].color = (0.21, 0.135, 0.085, 1); e[1].position = 0.72; e[1].color = (0.40, 0.31, 0.22, 1); L.new(n2.outputs["Fac"], bare.inputs["Fac"])
    ln = N.new("ShaderNodeVectorMath"); ln.operation = 'LENGTH'; L.new(geo.outputs["Position"], ln.inputs[0])
    wob = N.new("ShaderNodeMath"); wob.operation = 'MULTIPLY_ADD'; wob.inputs[1].default_value = 14.0; L.new(n1.outputs["Fac"], wob.inputs[0]); L.new(ln.outputs["Value"], wob.inputs[2])
    ring = N.new("ShaderNodeMapRange"); ring.inputs["From Min"].default_value = C.R_LZ + 12.0; ring.inputs["From Max"].default_value = C.R_LZ - 2.0; L.new(wob.outputs[0], ring.inputs["Value"])
    core = N.new("ShaderNodeMapRange"); core.inputs["From Min"].default_value = 26.0; core.inputs["From Max"].default_value = 6.0; core.inputs["To Max"].default_value = 0.75; L.new(wob.outputs[0], core.inputs["Value"])
    blast = N.new("ShaderNodeValue"); blast.name = "Blast"; blast.outputs[0].default_value = 0.0
    f1 = N.new("ShaderNodeMath"); f1.operation = 'MULTIPLY'; L.new(ring.outputs[0], f1.inputs[0]); L.new(blast.outputs[0], f1.inputs[1])
    f2 = N.new("ShaderNodeMath"); f2.operation = 'MULTIPLY'; L.new(core.outputs[0], f2.inputs[0]); L.new(blast.outputs[0], f2.inputs[1])
    m1 = N.new("ShaderNodeMixRGB"); L.new(f1.outputs[0], m1.inputs[0]); L.new(floor.outputs["Color"], m1.inputs[1]); L.new(bare.outputs["Color"], m1.inputs[2])
    m2 = N.new("ShaderNodeMixRGB"); m2.inputs[2].default_value = (0.055, 0.050, 0.046, 1); L.new(f2.outputs[0], m2.inputs[0]); L.new(m1.outputs[0], m2.inputs[1])
    L.new(m2.outputs[0], P.inputs["Base Color"]); P.inputs["Roughness"].default_value = 0.95
    bp = N.new("ShaderNodeBump"); bp.inputs["Strength"].default_value = 0.7; bp.inputs["Distance"].default_value = 0.25; L.new(n2.outputs["Fac"], bp.inputs["Height"]); L.new(bp.outputs["Normal"], P.inputs["Normal"])
    return m

def cut_mat():
    """The face of the cut ground: a dark layer of roots and humus over red-brown tropical soil."""
    m, N, L, P = nodemat("SoilCut"); geo = N.new("ShaderNodeNewGeometry"); sp = N.new("ShaderNodeSeparateXYZ"); L.new(geo.outputs["Position"], sp.inputs[0])
    mp = N.new("ShaderNodeMapping"); mp.inputs["Scale"].default_value = (0.25, 0.25, 1.4); L.new(geo.outputs["Position"], mp.inputs["Vector"])
    nz = N.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 1.0; nz.inputs["Detail"].default_value = 7; L.new(mp.outputs[0], nz.inputs["Vector"])
    zz = N.new("ShaderNodeMath"); zz.operation = 'MULTIPLY_ADD'; zz.inputs[1].default_value = 1.6; L.new(nz.outputs["Fac"], zz.inputs[0]); L.new(sp.outputs["Z"], zz.inputs[2])
    cr = N.new("ShaderNodeValToRGB"); e = cr.color_ramp.elements; e[0].position = 0.0; e[0].color = (0.115, 0.062, 0.036, 1); e[1].position = 1.0; e[1].color = (0.030, 0.024, 0.016, 1)
    a = e.new(0.55); a.color = (0.185, 0.095, 0.050, 1); b = e.new(0.88); b.color = (0.105, 0.070, 0.040, 1)
    mr = N.new("ShaderNodeMapRange"); mr.inputs["From Min"].default_value = -9.0; mr.inputs["From Max"].default_value = 1.1; L.new(zz.outputs[0], mr.inputs["Value"]); L.new(mr.outputs[0], cr.inputs["Fac"])
    L.new(cr.outputs["Color"], P.inputs["Base Color"]); P.inputs["Roughness"].default_value = 0.95
    return m

# ----------------------------------------------------------------------------- trees
def _blob(rng, c, rad, base, cards=90):
    """One clump of foliage: a lumpy ball, darker underneath, with loose leaves standing off its surface."""
    out = []; V, Q, T = ellipsoid(c, rad, 12, 7); d = V - np.asarray(c); n = d / (np.linalg.norm(d / np.asarray(rad), axis=1, keepdims=True) + 1e-9) / np.asarray(rad)
    k = 1.0 + 0.22 * np.sin(d[:, 0] * 1.9 / rad[0] * 2 + rng.uniform(0, 6)) * np.cos(d[:, 1] * 2.3 / rad[1] * 2 + rng.uniform(0, 6)) + 0.12 * np.sin(d[:, 2] * 5.0 / rad[2] + rng.uniform(0, 6))
    V = np.asarray(c) + d * k[:, None]; zr = np.clip(d[:, 2] / rad[2], -1, 1); col = np.asarray(base)[None] * (0.42 + 0.58 * (zr[:, None] * 0.5 + 0.5)) * rng.uniform(0.85, 1.15, (len(V), 1))
    out.append((V, Q, T, np.concatenate([col, np.ones((len(V), 1))], 1)))
    p = rng.normal(0, 1, (cards, 3)); p[:, 2] = np.abs(p[:, 2]) * 0.8 + 0.1 * p[:, 2]; p /= np.linalg.norm(p, axis=1, keepdims=True); cc = np.asarray(c) + p * np.asarray(rad) * rng.uniform(0.92, 1.18, (cards, 1))
    u = rng.normal(0, 1, (cards, 3)); u /= np.linalg.norm(u, axis=1, keepdims=True); w = np.cross(u, rng.normal(0, 1, (cards, 3))); w /= np.linalg.norm(w, axis=1, keepdims=True)
    s = rng.uniform(0.35, 0.75, (cards, 1)) * (rad[0] / 4.0) ** 0.5; quad = np.stack([cc - u * s - w * s * 0.6, cc + u * s - w * s * 0.6, cc + u * s + w * s * 0.6, cc - u * s + w * s * 0.6], 1).reshape(-1, 3)
    lc = np.asarray(base)[None] * rng.uniform(0.7, 1.45, (cards, 1)) * (0.6 + 0.4 * (p[:, 2:3] * 0.5 + 0.5)); out.append((quad, np.arange(len(quad)).reshape(-1, 4), None, np.repeat(np.concatenate([lc, np.ones((cards, 1))], 1), 4, 0)))
    return out

def _limb(p0, p1, r0, r1, col, segs=7, sag=0.0):
    pts = [p0 + (p1 - p0) * u + np.array([0, 0, sag * 4 * u * (1 - u)]) for u in np.linspace(0, 1, 4)]; d = p1 - p0; d /= np.linalg.norm(d)
    side = np.cross(d, EZ if abs(d[2]) < 0.9 else EX); side /= np.linalg.norm(side); third = np.cross(d, side); a = np.linspace(0, 2 * np.pi, segs, endpoint=False)
    rings = [p[None] + (r0 + (r1 - r0) * u) * (np.cos(a)[:, None] * side[None] + np.sin(a)[:, None] * third[None]) for p, u in zip(pts, np.linspace(0, 1, 4))]
    V, Q, T = loft(rings); return (V, Q, T, np.tile(np.asarray(col), (len(V), 1)))

def tree_parts(rng, H, kind="canopy"):
    """Returns (wood, leaves): lists of (verts, quads, tris, colours).  The foot of the trunk is at the origin."""
    wood = []; leaves = []; bark = BARK[int(rng.integers(0, 3))]; base = np.array(GREENS[int(rng.integers(0, len(GREENS)))]) * rng.uniform(0.8, 1.2)
    if kind == "palm":
        lean = rng.normal(0, 0.10, 2); top = np.array([lean[0] * H, lean[1] * H, H]); wood.append(_limb(np.zeros(3), top, 0.20, 0.13, bark, 8, 0.0))
        for k in range(13):
            a = 2 * np.pi * k / 13 + rng.uniform(-0.2, 0.2); L_ = rng.uniform(3.0, 4.2); up = rng.uniform(0.15, 0.8); pts = []
            for u in np.linspace(0, 1, 6):
                r = L_ * u; pts.append(top + np.array([math.cos(a) * r, math.sin(a) * r, up * L_ * u - 1.15 * L_ * u * u]))
            pts = np.array(pts); n_ = np.array([-math.sin(a), math.cos(a), 0]); wd = 0.45 * np.sin(np.linspace(0.25, 3.0, 6))[:, None]
            V = np.concatenate([pts - n_ * wd, pts + n_ * wd]); c = base * rng.uniform(0.9, 1.4); leaves.append((V, grid_faces(2, 6), None, np.tile(np.array([*c, 1.0]), (len(V), 1))))
        return wood, leaves
    r0 = {"emergent": H / 58.0, "canopy": H / 62.0, "under": H / 70.0}[kind]; fork = H * {"emergent": 0.66, "canopy": 0.60, "under": 0.45}[kind]; top = np.array([rng.normal(0, 0.012) * H, rng.normal(0, 0.012) * H, fork])
    a = np.linspace(0, 2 * np.pi, 10, endpoint=False); rings = []
    for z, k in ((-0.6, 2.6), (0.4, 2.0), (1.6, 1.25), (3.2, 1.0)):                                # buttressed foot
        lob = 1.0 + (0.28 if z < 1.0 else 0.0) * np.cos(4 * a + 0.5); rings.append(np.stack([r0 * k * lob * np.cos(a), r0 * k * lob * np.sin(a), np.full(10, z)], 1))
    V, Q, T = loft(rings, cap0=False, cap1=False); wood.append((V, Q, T, np.tile(np.asarray(bark), (len(V), 1))))
    wood.append(_limb(np.array([0, 0, 3.2]), top, r0, r0 * 0.72, bark, 10))
    Rc = H * {"emergent": 0.20, "canopy": 0.19, "under": 0.20}[kind] * rng.uniform(0.9, 1.15); nb = int(rng.integers(5, 8)); tips = []
    for i in range(nb):
        az = i / nb * 6.283 + rng.normal(0, 0.25); el = rng.uniform(0.35, 0.95); ln = (H - fork) * rng.uniform(0.75, 1.05)
        d = np.array([math.cos(az) * math.cos(el), math.sin(az) * math.cos(el), math.sin(el)]); d[:2] *= Rc / max(ln * math.cos(el), 1e-3) * rng.uniform(0.7, 1.0)
        p1 = top + d * ln; p1[2] = min(p1[2], H * 0.93); wood.append(_limb(top - np.array([0, 0, rng.uniform(0, fork * 0.12)]), p1, r0 * 0.42, r0 * 0.12, bark, 6, sag=0.03 * ln)); tips.append(p1)
    tips.append(top + np.array([0, 0, (H - fork) * 0.8]))
    for tip in tips:
        rr = Rc * rng.uniform(0.42, 0.62); leaves += _blob(rng, tip + np.array([0, 0, rr * 0.15]), (rr, rr * rng.uniform(0.9, 1.1), rr * 0.55), base * rng.uniform(0.85, 1.2))
    return wood, leaves

def _mesh(name, parts):
    S = Shell()
    for V, Q, T, c in parts:
        S.add(V, Q, T, c)
    me = S.mesh(name, sharp=math.radians(50)); me.materials.append(leaf_mat()); return me

def stump_parts(rng, r0, h):
    a = np.linspace(0, 2 * np.pi, 10, endpoint=False); rings = []; bark = BARK[int(rng.integers(0, 3))]
    for z, k in ((-0.4, 2.4), (0.5, 1.7), (h * 0.7, 1.05), (h, 0.95)):
        jag = rng.uniform(0.0, 0.9, 10) * (0.5 if z == h else 0.0); rings.append(np.stack([r0 * k * np.cos(a), r0 * k * np.sin(a), z + jag], 1))
    V, Q, T = loft(rings, cap0=False, cap1=True); c = np.tile(np.asarray(bark), (len(V), 1)); c[-11:] = (0.50, 0.36, 0.20, 1); return [(V, Q, T, c)]   # the splintered wood is pale

KINDS = [("emergent", 44.0, 0.07), ("emergent", 40.0, 0.07), ("canopy", 35.0, 0.18), ("canopy", 32.0, 0.20), ("canopy", 29.0, 0.16), ("under", 21.0, 0.12), ("under", 16.0, 0.10), ("palm", 11.0, 0.05), ("palm", 8.0, 0.05)]

def tree_meshes(seed=5):
    """One set of meshes for every kind of tree: full, thinned (most leaves gone), bare, and its stump."""
    out = []
    for k, (kind, H, w) in enumerate(KINDS):
        nm = "tree%d" % k
        if nm + "_full" in bpy.data.meshes:
            out.append(tuple(bpy.data.meshes[nm + s] for s in ("_full", "_thin", "_bare", "_stump"))); continue
        rng = np.random.default_rng(seed + k); wood, leaves = tree_parts(rng, H, kind); r0 = H / 60.0 if kind != "palm" else 0.2
        out.append((_mesh(nm + "_full", wood + leaves), _mesh(nm + "_thin", wood + leaves[1::5]), _mesh(nm + "_bare", wood), _mesh(nm + "_stump", stump_parts(rng, r0, float(rng.uniform(1.2, 2.6))))))
    return out

def bush_mesh(k):
    nm = "bush%d" % k
    if nm in bpy.data.meshes:
        return bpy.data.meshes[nm]
    rng = np.random.default_rng(90 + k); parts = []
    for j in range(int(rng.integers(3, 6))):
        rr = rng.uniform(1.0, 2.2); c = np.array([rng.normal(0, 1.4), rng.normal(0, 1.4), rr * 0.7 + rng.uniform(0, 1.5)]); parts += _blob(rng, c, (rr, rr, rr * 0.8), np.array(GREENS[j % 5]) * rng.uniform(0.7, 1.1), cards=40)
    return _mesh(nm, parts)

def look_row(col, origin):
    ms = tree_meshes()
    for k, m in enumerate(ms):
        for j in range(3):
            new_obj("L%d_%d" % (k, j), m[j], col, None, (origin[0] - 80 + k * 20, origin[1] + j * 26, origin[2]))
        new_obj("Ls%d" % k, m[3], col, None, (origin[0] - 80 + k * 20 + 6, origin[1], origin[2]))

# ----------------------------------------------------------------------------- the site
class Jungle:
    def __init__(self, sc, col, kind="out", seed=3):
        self.kind = kind; self.col = col; rng = self.rng = np.random.default_rng(seed); sec = kind == "sec"
        env.make_world(sc)
        self._ground(col, sec)
        if not sec:
            self._far(col)
        ms = tree_meshes(); w = np.array([k[2] for k in KINDS]); w /= w.sum(); cell = 6.4; pts = []
        n = int(R_OBJ / cell) + 2
        for ix in range(-n, n + 1):
            for iy in range(-n, n + 1):
                x = (ix + rng.uniform(0.1, 0.9)) * cell; y = (iy + rng.uniform(0.1, 0.9)) * cell; r = math.hypot(x, y)
                if r > R_OBJ or r < 2.5 or (sec and not (-78.0 < y < -1.6 and abs(x) < 190.0)):
                    continue
                pts.append((x, y, r))
        if not sec:                                                   # the outer ring has its own random numbers, so the forest inside it stays as it was
            rng2 = np.random.default_rng(seed + 100); n2 = int(R_OBJ2 / cell) + 2
            for ix in range(-n2, n2 + 1):
                for iy in range(-n2, n2 + 1):
                    x = (ix + rng2.uniform(0.1, 0.9)) * cell; y = (iy + rng2.uniform(0.1, 0.9)) * cell; r = math.hypot(x, y)
                    if R_OBJ - 3.0 < r <= R_OBJ2:
                        pts.append((x, y, r))
        self.trees = []
        for (x, y, r) in pts:
            k = int(rng.choice(len(KINDS), p=w)); z = float(ground_h(x, y)); s = float(rng.uniform(0.86, 1.12)); yaw = float(rng.uniform(0, 6.283))
            ob = bpy.data.objects.new("T", ms[k][0]); col.objects.link(ob); ob.location = (x, y, z - 0.2); ob.rotation_mode = 'QUATERNION'; ob.scale = (s, s, s)
            az = math.atan2(y, x) + float(rng.normal(0, 0.16)); axis = Vector((-math.sin(az), math.cos(az), 0.0))             # it goes down turning about this, away from the burst
            st = None
            if r < C.R_LZ + 3.0:
                st = bpy.data.objects.new("S", ms[k][3]); col.objects.link(st); st.location = (x, y, z - 0.1); st.rotation_euler = (0, 0, yaw); st.scale = (s, s, s); st.hide_render = True
            self.trees.append(dict(ob=ob, k=k, r=r, axis=axis, yaw=Quaternion((0, 0, 1), yaw), stump=st, ph=float(rng.uniform(0, 6.283)), j=float(rng.uniform(0.85, 1.2)), state=0))
            ob.rotation_quaternion = self.trees[-1]["yaw"]
        self.ms = ms
        self.bushes = []
        rb = 150.0 if not sec else 190.0; nb = 0
        for _ in range(2600 if not sec else 900):
            x = float(rng.uniform(-rb, rb)); y = float(rng.uniform(-rb, rb)) if not sec else float(rng.uniform(-70.0, -1.0)); r = math.hypot(x, y)
            if r > rb or r < 1.5:
                continue
            ob = bpy.data.objects.new("B", bush_mesh(nb % 4)); nb += 1; col.objects.link(ob); s = float(rng.uniform(0.5, 1.2)); ob.location = (x, y, float(ground_h(x, y)) - 0.1); ob.scale = (s, s, s); ob.rotation_euler = (0, 0, float(rng.uniform(0, 6.283)))
            self.bushes.append((ob, r))
        self._debris(col, sec)
        ld = bpy.data.lights.new("Fireball", 'POINT'); ld.shadow_soft_size = 12.0; ld.color = (1.0, 0.62, 0.30); self.flash = bpy.data.objects.new("Fireball", ld); col.objects.link(self.flash); self.flash.location = (0, 0, 14.0)
        self.update(-1.0)

    def _ground(self, col, sec):
        m = soil_mat(); self.blast_node = m.node_tree.nodes["Blast"]; R = 255.0 if sec else 315.0; xs = np.arange(-R, R + 0.01, 1.25); ys = np.arange(-R, (0.0 if sec else R) + 0.01, 1.25); X, Y = np.meshgrid(xs, ys, indexing="ij")
        Z = ground_h(X, Y) + 0.10 * (fbm(X * 0.5, Y * 0.5, 3, 4) - 0.5) * np.clip(np.hypot(X, Y) / 6.0, 0, 1)
        me = new_mesh("jungle_ground", np.stack([X, Y, Z], -1).reshape(-1, 3), [grid_faces(len(xs), len(ys))]); self.ground = new_obj("Ground", me, col, m)
        r = np.hypot(X, Y).ravel(); dip = -float(np.mean(C.DIP_H)) * np.clip(1 - (r / (float(np.mean(C.DIP_D)) / 2)) ** 2, 0, None)        # the dish under the burst
        self.ground.shape_key_add(name="Basis"); kb = self.ground.shape_key_add(name="Dish"); co = np.stack([X, Y, Z], -1).reshape(-1, 3); co[:, 2] += dip; kb.data.foreach_set("co", co.ravel().astype(np.float32)); self.dish = kb
        if sec:                                                       # the cut face and a floor far below
            xs2 = np.arange(-R, R + 0.01, 2.5); top = ground_h(xs2, np.zeros_like(xs2)); V = np.array([[x, 0.0, z] for x, zt in zip(xs2, top) for z in (zt, -80.0)])
            self.cut = new_obj("GroundCut", new_mesh("ground_cut", V, [grid_faces(len(xs2), 2)], smooth=False), col, cut_mat())
            self.cut.shape_key_add(name="Basis"); kb2 = self.cut.shape_key_add(name="Dish"); V2 = V.copy(); V2[0::2, 2] -= float(np.mean(C.DIP_H)) * np.clip(1 - (np.abs(xs2) / (float(np.mean(C.DIP_D)) / 2)) ** 2, 0, None); kb2.data.foreach_set("co", V2.ravel().astype(np.float32)); self.dish2 = kb2

    def _far(self, col):
        na = 720; a = np.linspace(0, 2 * np.pi, na, endpoint=False); rr = np.concatenate([np.geomspace(R_OBJ2 - 6.0, 1500.0, 150), np.geomspace(1560.0, 60000.0, 60)]); A, Rr = np.meshgrid(a, rr, indexing="ij"); X = Rr * np.cos(A); Y = Rr * np.sin(A)
        Z = ground_h(X, Y) + CANOPY_Z + np.where(Rr < 1500.0, crown_h(X, Y), 0.0); Z[:, 0] -= 30.0                               # the inner edge turns down behind the first single trees
        self.far = new_obj("CanopyFar", new_mesh("canopy_far", np.stack([X, Y, Z], -1).reshape(-1, 3), [grid_faces(na, len(rr), wrap_u=True)]), col, canopy_mat())

    def _debris(self, col, sec):
        """What lies in the clearing afterwards: lengths of trunk and splintered wood, most of it thrown outwards."""
        rng = np.random.default_rng(21); S = Shell()
        for k in range(150 if not sec else 60):
            r = float(rng.uniform(10.0, C.R_LZ + 6.0)); az = float(rng.uniform(0, 6.283)) if not sec else float(rng.uniform(math.pi + 0.15, 2 * math.pi - 0.15)); x, y = r * math.cos(az), r * math.sin(az)
            ln = float(rng.uniform(2.0, 9.0)); rad = float(rng.uniform(0.10, 0.34)); d = az + float(rng.normal(0, 0.5)); dv = np.array([math.cos(d), math.sin(d), 0.0]); p = np.array([x, y, float(ground_h(x, y)) + rad * 0.8])
            V, Q, T, c = _limb(p - dv * ln / 2, p + dv * ln / 2, rad, rad * 0.8, BARK[k % 3], 7); S.add(V, Q, T, c)
        self.debris = new_obj("Debris", S.mesh("debris"), col, leaf_mat()); self.debris.hide_render = True

    def update(self, tb):
        """tb: seconds after the burst (negative before it)."""
        on = tb >= 0.0; self.blast_node.outputs[0].default_value = float(smoothstep(0.0, 0.25, tb)); self.dish.value = 1.0 if on else 0.0
        if self.kind == "sec":
            self.dish2.value = 1.0 if on else 0.0
        self.debris.hide_render = tb < 0.9
        e = (9.0e9 * math.exp(-tb / 0.22) if self.kind == "out" else 6.0e7 * math.exp(-tb / 0.03))                                  # the section is in slow motion and close: a short, weaker flash, or it hides everything
        e = e * min(1.0, tb / 0.006) if 0.0 < tb < 3.0 else 0.0; self.flash.data.energy = e; self.flash.hide_render = e < 1e3
        for T in self.trees:
            r = T["r"]; tau = tb - float(C.t_front(r)); ob = T["ob"]; k = T["k"]
            if tau <= 0.0:
                st = 0; ang = 0.0
            elif r < C.R_BARE:
                st = 3; ang = 0.0                                     # broken up: only the stump is left
            elif r < C.R_LZ:
                st = 2; Tf = (0.30 + r / 55.0) * T["j"]; u = tau / Tf; ang = math.radians(88.0) * (u * u if u < 1.0 else 1.0 + 0.035 * math.exp(-(u - 1) * 5.0) * math.sin((u - 1) * 13.0))
            elif r < C.R_LEAN:
                q = (r - C.R_LZ) / (C.R_LEAN - C.R_LZ); st = 2 if q < 0.35 else 1; fin = math.radians(58.0) * (1 - q) ** 1.6 * T["j"]; Tf = 0.9 + r / 70.0; u = min(tau / Tf, 1.0)
                ang = fin * (1 - (1 - u) ** 2) + math.radians(14.0) * (1 - q * 0.5) * math.exp(-tau / 1.6) * math.sin(tau * 5.2)
            else:
                st = 0; amp = math.radians(9.0) * math.exp(-(r - C.R_LEAN) / 90.0); ang = amp * math.exp(-tau / 2.2) * math.sin(tau * 4.4 + 0.3)
            if st != T["state"]:
                T["state"] = st; ob.data = self.ms[k][min(st, 2)]; ob.hide_render = st == 3
                if T["stump"] is not None:
                    T["stump"].hide_render = st < 2
            if st == 2 and r < C.R_LZ:                                # snapped off above the stump: the trunk lies beside it
                ob.location.z = float(ground_h(ob.location.x, ob.location.y)) + 0.3
            ob.rotation_quaternion = Quaternion(T["axis"], ang) @ T["yaw"]
        for ob, r in self.bushes:
            ob.hide_render = tb > float(C.t_front(r)) and r < C.R_LZ + 4.0

class AirFloor:
    """The forest seen from the aircraft: canopy over low hills out to the horizon, sliding past underneath."""
    def __init__(self, sc, col, alt=C.H_REL):
        env.make_world(sc)
        xs = np.concatenate([-np.geomspace(600000.0, 5200.0, 44), np.arange(-5000.0, 5000.1, 16.0), np.geomspace(5200.0, 600000.0, 44)]); X, Y = np.meshgrid(xs, xs, indexing="ij")
        Z = ground_h(X, Y) + np.where((np.abs(X) < 5000) & (np.abs(Y) < 5000), crown_h(X, Y, 16.0) * 1.3, 0.0) - alt - float(ground_h(0.0, 0.0))
        self.ob = new_obj("JungleFloor", new_mesh("jungle_floor", np.stack([X, Y, Z], -1).reshape(-1, 3), [grid_faces(len(xs), len(xs))]), col, canopy_mat(air=True))
