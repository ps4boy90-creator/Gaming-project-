"""Procedural outdoor grenade range: sky, sun, ground, dry grass, stones, sandbag pit,
crates, drums, fence, tree line and distant hills. Blast point is the world origin;
the thrower stands at x = THROW_X and throws along +X. Everything is deterministic."""
import bpy, math
import numpy as np
from util import *

SUN_ELEV = math.radians(31.0)
SUN_AZ = math.radians(118.0)          # direction TO the sun, measured from +X towards +Y
def sun_dir():
    return np.array([math.cos(SUN_AZ) * math.cos(SUN_ELEV), math.sin(SUN_AZ) * math.cos(SUN_ELEV), math.sin(SUN_ELEV)])

def ground_h(x, y):
    """Gentle analytic undulation of the range floor (metres)."""
    x = np.asarray(x, np.float64); y = np.asarray(y, np.float64)
    h = 0.030 * np.sin(x * 0.31 + 0.7) * np.cos(y * 0.27 - 0.4) + 0.018 * np.sin(x * 0.83 + y * 0.61 + 1.9) \
        + 0.008 * np.sin(x * 2.3 - 1.1) * np.sin(y * 2.9 + 0.3)
    r2 = x * x + y * y
    return h * (1 - np.exp(-r2 / 9.0))        # dead flat right at the blast point

# ------------------------------------------------------------------ world
def make_world(sc, strength=0.05):
    w = bpy.data.worlds.new("RangeSky"); sc.world = w; w.use_nodes = True
    nt = w.node_tree; N = nt.nodes; L = nt.links
    bg = N["Background"]
    sky = N.new("ShaderNodeTexSky"); sky.sky_type = 'MULTIPLE_SCATTERING'
    sky.sun_disc = False
    sky.sun_elevation = SUN_ELEV
    sky.sun_rotation = math.pi / 2 - SUN_AZ      # node measures clockwise from +Y
    sky.altitude = 300; sky.air_density = 1.0; sky.aerosol_density = 1.6; sky.ozone_density = 1.0
    # --- procedural cloud deck projected on a plane above the camera
    tc = N.new("ShaderNodeTexCoord")
    sep = N.new("ShaderNodeSeparateXYZ"); L.new(tc.outputs["Generated"], sep.inputs[0])
    zc = N.new("ShaderNodeMath"); zc.operation = 'MAXIMUM'; zc.inputs[1].default_value = 0.035
    L.new(sep.outputs["Z"], zc.inputs[0])
    dv = N.new("ShaderNodeVectorMath"); dv.operation = 'DIVIDE'
    cz = N.new("ShaderNodeCombineXYZ"); L.new(zc.outputs[0], cz.inputs[0]); L.new(zc.outputs[0], cz.inputs[1]); cz.inputs[2].default_value = 1.0
    L.new(tc.outputs["Generated"], dv.inputs[0]); L.new(cz.outputs[0], dv.inputs[1])
    def cloud_noise(offset):
        mp = N.new("ShaderNodeMapping"); mp.inputs["Location"].default_value = offset
        mp.inputs["Scale"].default_value = (0.36, 0.36, 0.0)
        L.new(dv.outputs[0], mp.inputs["Vector"])
        nz = N.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 1.0; nz.inputs["Detail"].default_value = 9
        nz.inputs["Roughness"].default_value = 0.62; nz.inputs["Distortion"].default_value = 0.25
        L.new(mp.outputs[0], nz.inputs["Vector"])
        return nz
    n1 = cloud_noise((3.1, 7.7, 0.0))
    sd = sun_dir()
    n2 = cloud_noise((3.1 + 0.10 * sd[0], 7.7 + 0.10 * sd[1], 0.0))
    cov = N.new("ShaderNodeMapRange"); cov.inputs["From Min"].default_value = 0.53; cov.inputs["From Max"].default_value = 0.70
    cov.interpolation_type = 'SMOOTHSTEP'; L.new(n1.outputs["Fac"], cov.inputs["Value"])
    shd = N.new("ShaderNodeMapRange"); shd.inputs["From Min"].default_value = 0.50; shd.inputs["From Max"].default_value = 0.80
    shd.inputs["To Min"].default_value = 1.0; shd.inputs["To Max"].default_value = 0.42
    L.new(n2.outputs["Fac"], shd.inputs["Value"])
    # fade the deck out towards the horizon (haze)
    hz = N.new("ShaderNodeMapRange"); hz.inputs["From Min"].default_value = 0.02; hz.inputs["From Max"].default_value = 0.22
    L.new(sep.outputs["Z"], hz.inputs["Value"])
    covh = N.new("ShaderNodeMath"); covh.operation = 'MULTIPLY'
    L.new(cov.outputs["Result"], covh.inputs[0]); L.new(hz.outputs["Result"], covh.inputs[1])
    ccol = N.new("ShaderNodeVectorMath"); ccol.operation = 'SCALE'
    ccol.inputs[0].default_value = (1.0, 0.97, 0.93); L.new(shd.outputs["Result"], ccol.inputs["Scale"])
    cs = N.new("ShaderNodeVectorMath"); cs.operation = 'SCALE'; cs.inputs["Scale"].default_value = 26.0
    L.new(ccol.outputs[0], cs.inputs[0])
    mix = N.new("ShaderNodeMix"); mix.data_type = 'RGBA'
    L.new(covh.outputs[0], mix.inputs["Factor"]); L.new(sky.outputs["Color"], mix.inputs["A"]); L.new(cs.outputs[0], mix.inputs["B"])
    L.new(mix.outputs["Result"], bg.inputs["Color"])
    bg.inputs["Strength"].default_value = strength
    w["cloud_scale_node"] = cs.name
    # sun lamp (sharper control than the sky's disc)
    sl = bpy.data.lights.new("Sun", 'SUN'); sl.energy = 5.2; sl.angle = math.radians(1.1); sl.color = (1.0, 0.93, 0.82)
    so = bpy.data.objects.new("Sun", sl); sc.collection.objects.link(so)
    so.rotation_euler = Vector(sd).to_track_quat('Z', 'Y').to_euler()
    return w

# ------------------------------------------------------------------ materials
def mat_ground():
    m, N, L, P = nodemat("RangeDirt")
    tc = N.new("ShaderNodeTexCoord")
    def noise(scale, detail=6, rough=0.6):
        n = N.new("ShaderNodeTexNoise"); n.inputs["Scale"].default_value = scale; n.inputs["Detail"].default_value = detail
        n.inputs["Roughness"].default_value = rough; L.new(tc.outputs["Object"], n.inputs["Vector"]); return n
    big = noise(0.12, 5); mid = noise(1.3, 6); fine = noise(55, 4); grit = noise(420, 2)
    r1 = N.new("ShaderNodeValToRGB"); e = r1.color_ramp.elements
    e[0].position = 0.28; e[0].color = (0.160, 0.112, 0.070, 1); e[1].position = 0.72; e[1].color = (0.335, 0.250, 0.160, 1)
    L.new(big.outputs["Fac"], r1.inputs["Fac"])
    r2 = N.new("ShaderNodeValToRGB"); e = r2.color_ramp.elements
    e[0].position = 0.35; e[0].color = (0.62, 0.60, 0.58, 1); e[1].position = 0.70; e[1].color = (1.18, 1.12, 1.02, 1)
    L.new(mid.outputs["Fac"], r2.inputs["Fac"])
    mul = N.new("ShaderNodeMix"); mul.data_type = 'RGBA'; mul.blend_type = 'MULTIPLY'; mul.inputs["Factor"].default_value = 1.0
    L.new(r1.outputs["Color"], mul.inputs["A"]); L.new(r2.outputs["Color"], mul.inputs["B"])
    r3 = N.new("ShaderNodeValToRGB"); e = r3.color_ramp.elements
    e[0].position = 0.30; e[0].color = (0.72, 0.72, 0.72, 1); e[1].position = 0.75; e[1].color = (1.15, 1.15, 1.15, 1)
    L.new(fine.outputs["Fac"], r3.inputs["Fac"])
    mul2 = N.new("ShaderNodeMix"); mul2.data_type = 'RGBA'; mul2.blend_type = 'MULTIPLY'; mul2.inputs["Factor"].default_value = 1.0
    L.new(mul.outputs["Result"], mul2.inputs["A"]); L.new(r3.outputs["Color"], mul2.inputs["B"])
    # dried-mud cracks
    vor = N.new("ShaderNodeTexVoronoi"); vor.feature = 'DISTANCE_TO_EDGE'; vor.inputs["Scale"].default_value = 12.0
    wob = N.new("ShaderNodeVectorMath"); wob.operation = 'ADD'
    wsc = N.new("ShaderNodeVectorMath"); wsc.operation = 'SCALE'; wsc.inputs["Scale"].default_value = 0.10
    wn = noise(3.0, 3); L.new(wn.outputs["Color"], wsc.inputs[0])
    L.new(tc.outputs["Object"], wob.inputs[0]); L.new(wsc.outputs[0], wob.inputs[1]); L.new(wob.outputs[0], vor.inputs["Vector"])
    crack = N.new("ShaderNodeMapRange"); crack.inputs["From Min"].default_value = 0.0; crack.inputs["From Max"].default_value = 0.022
    crack.inputs["To Min"].default_value = 0.0; crack.inputs["To Max"].default_value = 1.0
    L.new(vor.outputs["Distance"], crack.inputs["Value"])
    crm = N.new("ShaderNodeMapRange"); crm.inputs["From Min"].default_value = 0.56; crm.inputs["From Max"].default_value = 0.70
    L.new(mid.outputs["Fac"], crm.inputs["Value"])     # cracks only in patches
    crf = N.new("ShaderNodeMix"); crf.data_type = 'FLOAT'; crf.inputs[2].default_value = 1.0
    L.new(crm.outputs["Result"], crf.inputs[0]); L.new(crack.outputs["Result"], crf.inputs[3])
    dark = N.new("ShaderNodeMix"); dark.data_type = 'RGBA'; dark.blend_type = 'MULTIPLY'
    dark.inputs["B"].default_value = (0.45, 0.42, 0.40, 1)
    inv = N.new("ShaderNodeMath"); inv.operation = 'SUBTRACT'; inv.inputs[0].default_value = 1.0
    L.new(crf.outputs[0], inv.inputs[1]); L.new(inv.outputs[0], dark.inputs["Factor"]); L.new(mul2.outputs["Result"], dark.inputs["A"])
    # --- scorch + ejecta from the blast (animated by the "Blast" value node, 0 -> 1 at detonation)
    blast = N.new("ShaderNodeValue"); blast.name = blast.label = "Blast"; blast.outputs[0].default_value = 0.0
    geo = N.new("ShaderNodeNewGeometry")
    sepp = N.new("ShaderNodeSeparateXYZ"); L.new(geo.outputs["Position"], sepp.inputs[0])
    cmb = N.new("ShaderNodeCombineXYZ"); L.new(sepp.outputs["X"], cmb.inputs[0]); L.new(sepp.outputs["Y"], cmb.inputs[1])
    rad = N.new("ShaderNodeVectorMath"); rad.operation = 'LENGTH'; L.new(cmb.outputs[0], rad.inputs[0])
    nrm = N.new("ShaderNodeVectorMath"); nrm.operation = 'NORMALIZE'; L.new(cmb.outputs[0], nrm.inputs[0])
    rays = N.new("ShaderNodeTexNoise"); rays.inputs["Scale"].default_value = 9.0; rays.inputs["Detail"].default_value = 4
    L.new(nrm.outputs[0], rays.inputs["Vector"])                    # depends on direction only -> radial streaks
    reach = N.new("ShaderNodeMapRange"); reach.inputs["From Min"].default_value = 0.30; reach.inputs["From Max"].default_value = 0.78
    reach.inputs["To Min"].default_value = 0.55; reach.inputs["To Max"].default_value = 2.6
    L.new(rays.outputs["Fac"], reach.inputs["Value"])
    rr = N.new("ShaderNodeMath"); rr.operation = 'DIVIDE'; L.new(rad.outputs["Value"], rr.inputs[0]); L.new(reach.outputs["Result"], rr.inputs[1])
    sc_ = N.new("ShaderNodeMapRange"); sc_.inputs["From Min"].default_value = 0.25; sc_.inputs["From Max"].default_value = 1.0
    sc_.inputs["To Min"].default_value = 1.0; sc_.inputs["To Max"].default_value = 0.0; sc_.interpolation_type = 'SMOOTHSTEP'
    L.new(rr.outputs[0], sc_.inputs["Value"])
    scf = N.new("ShaderNodeMath"); scf.operation = 'MULTIPLY'; L.new(sc_.outputs["Result"], scf.inputs[0]); L.new(blast.outputs[0], scf.inputs[1])
    scm = N.new("ShaderNodeMath"); scm.operation = 'MULTIPLY'; scm.inputs[1].default_value = 0.93; L.new(scf.outputs[0], scm.inputs[0])
    burnt = N.new("ShaderNodeMix"); burnt.data_type = 'RGBA'; burnt.inputs["B"].default_value = (0.018, 0.016, 0.015, 1)
    L.new(scm.outputs[0], burnt.inputs["Factor"]); L.new(dark.outputs["Result"], burnt.inputs["A"])
    L.new(burnt.outputs["Result"], P.inputs["Base Color"])
    P.inputs["Roughness"].default_value = 0.93; P.inputs["Specular IOR Level"].default_value = 0.25
    # bump
    b1 = N.new("ShaderNodeBump"); b1.inputs["Strength"].default_value = 0.55; b1.inputs["Distance"].default_value = 0.035
    L.new(mid.outputs["Fac"], b1.inputs["Height"])
    b2 = N.new("ShaderNodeBump"); b2.inputs["Strength"].default_value = 0.65; b2.inputs["Distance"].default_value = 0.008
    L.new(fine.outputs["Fac"], b2.inputs["Height"]); L.new(b1.outputs["Normal"], b2.inputs["Normal"])
    b3 = N.new("ShaderNodeBump"); b3.inputs["Strength"].default_value = 0.5; b3.inputs["Distance"].default_value = 0.0015
    L.new(grit.outputs["Fac"], b3.inputs["Height"]); L.new(b2.outputs["Normal"], b3.inputs["Normal"])
    b4 = N.new("ShaderNodeBump"); b4.inputs["Strength"].default_value = 0.9; b4.inputs["Distance"].default_value = 0.012
    L.new(crf.outputs[0], b4.inputs["Height"]); L.new(b3.outputs["Normal"], b4.inputs["Normal"])
    L.new(b4.outputs["Normal"], P.inputs["Normal"])
    return m

def mat_vcol(name, rough=0.8, translucent=0.0, bump_scale=0.0, tint=(1, 1, 1)):
    """Diffuse material reading the per-vertex 'col' attribute (optionally with leaf translucency)."""
    m, N, L, P = nodemat(name)
    a = N.new("ShaderNodeAttribute"); a.attribute_name = "col"
    mul = N.new("ShaderNodeMix"); mul.data_type = 'RGBA'; mul.blend_type = 'MULTIPLY'; mul.inputs["Factor"].default_value = 1.0
    mul.inputs["B"].default_value = (*tint, 1); L.new(a.outputs["Color"], mul.inputs["A"])
    L.new(mul.outputs["Result"], P.inputs["Base Color"]); P.inputs["Roughness"].default_value = rough
    P.inputs["Specular IOR Level"].default_value = 0.3
    if bump_scale:
        tc = N.new("ShaderNodeTexCoord"); n = N.new("ShaderNodeTexNoise"); n.inputs["Scale"].default_value = bump_scale
        n.inputs["Detail"].default_value = 5; L.new(tc.outputs["Object"], n.inputs["Vector"])
        b = N.new("ShaderNodeBump"); b.inputs["Strength"].default_value = 0.6; b.inputs["Distance"].default_value = 0.01
        L.new(n.outputs["Fac"], b.inputs["Height"]); L.new(b.outputs["Normal"], P.inputs["Normal"])
    if translucent:
        out = N["Material Output"]
        tr = N.new("ShaderNodeBsdfTranslucent"); L.new(mul.outputs["Result"], tr.inputs["Color"])
        mx = N.new("ShaderNodeMixShader"); mx.inputs[0].default_value = translucent
        L.new(P.outputs[0], mx.inputs[1]); L.new(tr.outputs[0], mx.inputs[2]); L.new(mx.outputs[0], out.inputs["Surface"])
    return m

def mat_burlap():
    m, N, L, P = nodemat("Burlap")
    a = N.new("ShaderNodeAttribute"); a.attribute_name = "col"
    uv = N.new("ShaderNodeUVMap")
    w1 = N.new("ShaderNodeTexWave"); w1.inputs["Scale"].default_value = 70; w1.bands_direction = 'X'
    w2 = N.new("ShaderNodeTexWave"); w2.inputs["Scale"].default_value = 70; w2.bands_direction = 'Y'
    for w in (w1, w2):
        w.inputs["Distortion"].default_value = 1.2; w.inputs["Detail"].default_value = 1; L.new(uv.outputs["UV"], w.inputs["Vector"])
    mxw = N.new("ShaderNodeMath"); mxw.operation = 'MAXIMUM'; L.new(w1.outputs["Fac"], mxw.inputs[0]); L.new(w2.outputs["Fac"], mxw.inputs[1])
    tc = N.new("ShaderNodeTexCoord"); dn = N.new("ShaderNodeTexNoise"); dn.inputs["Scale"].default_value = 6; dn.inputs["Detail"].default_value = 5
    L.new(tc.outputs["Object"], dn.inputs["Vector"])
    dr = N.new("ShaderNodeMapRange"); dr.inputs["From Min"].default_value = 0.3; dr.inputs["From Max"].default_value = 0.7
    dr.inputs["To Min"].default_value = 0.42; dr.inputs["To Max"].default_value = 1.12; L.new(dn.outputs["Fac"], dr.inputs["Value"])
    wv = N.new("ShaderNodeMapRange"); wv.inputs["To Min"].default_value = 0.55; wv.inputs["To Max"].default_value = 1.08; L.new(mxw.outputs[0], wv.inputs["Value"])
    k = N.new("ShaderNodeMath"); k.operation = 'MULTIPLY'; L.new(dr.outputs["Result"], k.inputs[0]); L.new(wv.outputs["Result"], k.inputs[1])
    sc = N.new("ShaderNodeVectorMath"); sc.operation = 'SCALE'; L.new(a.outputs["Color"], sc.inputs[0]); L.new(k.outputs[0], sc.inputs["Scale"])
    L.new(sc.outputs[0], P.inputs["Base Color"]); P.inputs["Roughness"].default_value = 0.9
    P.inputs["Sheen Weight"].default_value = 0.3
    b = N.new("ShaderNodeBump"); b.inputs["Strength"].default_value = 1.0; b.inputs["Distance"].default_value = 0.004
    L.new(mxw.outputs[0], b.inputs["Height"]); L.new(b.outputs["Normal"], P.inputs["Normal"])
    return m

def mat_wood(name="Wood", base=(0.30, 0.20, 0.11), dark=(0.11, 0.07, 0.04)):
    """Weathered planks: grain runs along the UV 'u' axis."""
    m, N, L, P = nodemat(name)
    uv = N.new("ShaderNodeUVMap")
    mp = N.new("ShaderNodeMapping"); mp.inputs["Scale"].default_value = (2.0, 42.0, 1.0); L.new(uv.outputs["UV"], mp.inputs["Vector"])
    n = N.new("ShaderNodeTexNoise"); n.inputs["Scale"].default_value = 1.0; n.inputs["Detail"].default_value = 8; n.inputs["Distortion"].default_value = 1.4
    L.new(mp.outputs[0], n.inputs["Vector"])
    a = N.new("ShaderNodeAttribute"); a.attribute_name = "col"
    ramp = N.new("ShaderNodeValToRGB"); e = ramp.color_ramp.elements
    e[0].position = 0.32; e[0].color = (*dark, 1); e[1].position = 0.70; e[1].color = (*base, 1)
    L.new(n.outputs["Fac"], ramp.inputs["Fac"])
    mul = N.new("ShaderNodeMix"); mul.data_type = 'RGBA'; mul.blend_type = 'MULTIPLY'; mul.inputs["Factor"].default_value = 1.0
    L.new(ramp.outputs["Color"], mul.inputs["A"]); L.new(a.outputs["Color"], mul.inputs["B"])
    L.new(mul.outputs["Result"], P.inputs["Base Color"]); P.inputs["Roughness"].default_value = 0.78
    b = N.new("ShaderNodeBump"); b.inputs["Strength"].default_value = 0.5; b.inputs["Distance"].default_value = 0.003
    L.new(n.outputs["Fac"], b.inputs["Height"]); L.new(b.outputs["Normal"], P.inputs["Normal"])
    return m

def mat_drum():
    m, N, L, P = nodemat("Drum")
    tc = N.new("ShaderNodeTexCoord")
    n = N.new("ShaderNodeTexNoise"); n.inputs["Scale"].default_value = 5.0; n.inputs["Detail"].default_value = 8; n.inputs["Roughness"].default_value = 0.7
    L.new(tc.outputs["Object"], n.inputs["Vector"])
    a = N.new("ShaderNodeAttribute"); a.attribute_name = "col"
    rust = N.new("ShaderNodeMapRange"); rust.inputs["From Min"].default_value = 0.52; rust.inputs["From Max"].default_value = 0.66
    L.new(n.outputs["Fac"], rust.inputs["Value"])
    mx = N.new("ShaderNodeMix"); mx.data_type = 'RGBA'; mx.inputs["B"].default_value = (0.16, 0.065, 0.025, 1)
    L.new(rust.outputs["Result"], mx.inputs["Factor"]); L.new(a.outputs["Color"], mx.inputs["A"])
    L.new(mx.outputs["Result"], P.inputs["Base Color"])
    rr = N.new("ShaderNodeMapRange"); rr.inputs["To Min"].default_value = 0.38; rr.inputs["To Max"].default_value = 0.85
    L.new(rust.outputs["Result"], rr.inputs["Value"]); L.new(rr.outputs["Result"], P.inputs["Roughness"])
    mt = N.new("ShaderNodeMapRange"); mt.inputs["To Min"].default_value = 0.6; mt.inputs["To Max"].default_value = 0.0
    L.new(rust.outputs["Result"], mt.inputs["Value"]); L.new(mt.outputs["Result"], P.inputs["Metallic"])
    return m

# ------------------------------------------------------------------ geometry builders
def box_geo(g, size, center=(0, 0, 0), rot=None, color=(1, 1, 1, 1), grain_axis=0):
    """Box with per-face UVs whose u runs along `grain_axis` (metres)."""
    sx, sy, sz = np.asarray(size) / 2
    faces = [((1, 0, 0), (0, 1, 0), (0, 0, 1)), ((-1, 0, 0), (0, -1, 0), (0, 0, 1)), ((0, 1, 0), (-1, 0, 0), (0, 0, 1)),
             ((0, -1, 0), (1, 0, 0), (0, 0, 1)), ((0, 0, 1), (1, 0, 0), (0, 1, 0)), ((0, 0, -1), (1, 0, 0), (0, -1, 0))]
    h = np.array([sx, sy, sz])
    for n, u, v in faces:
        n = np.array(n, float); u = np.array(u, float); v = np.array(v, float)
        c = n * h
        P = np.array([c - u * h - v * h, c + u * h - v * h, c + u * h + v * h, c - u * h + v * h])
        gu = np.zeros(3); gu[grain_axis] = 1.0
        ga = [a for a in range(3) if a != grain_axis and abs(n[a]) < 0.5]
        gv = np.zeros(3); gv[ga[0] if abs(n[grain_axis]) < 0.5 else (grain_axis + 1) % 3] = 1.0
        uvs = np.stack([P @ gu, P @ gv], 1)
        if rot is not None:
            P = P @ np.asarray(rot).T
        g.add(P + np.asarray(center), [[0, 1, 2, 3]], uv=uvs + np.random.uniform(0, 5, 2), color=color)

def build_ground(col):
    nx, ny = 760, 520
    xs = np.linspace(-52, 30, nx); ys = np.linspace(-24, 32, ny)
    X, Y = np.meshgrid(xs, ys, indexing="ij")
    Z = ground_h(X, Y) + 0.012 * (fbm(X * 1.7, Y * 1.7, 3, 4) - 0.5) + 0.004 * (fbm(X * 9, Y * 9, 9, 3) - 0.5)
    V = np.stack([X, Y, Z], -1).reshape(-1, 3)
    me = new_mesh("ground_near", V, [grid_faces(nx, ny)])
    # shallow crater + rim as a shape key (switched on at detonation)
    ob = new_obj("GroundNear", me, col, mat_ground())
    ob.shape_key_add(name="Basis")
    sk = ob.shape_key_add(name="Crater")
    r = np.sqrt(V[:, 0] ** 2 + V[:, 1] ** 2)
    ang = np.arctan2(V[:, 1], V[:, 0])
    rough = 1 + 0.25 * np.sin(ang * 7 + 0.5) + 0.15 * np.sin(ang * 13 + 2.0)
    dz = -0.085 * np.exp(-(r / (0.26 * rough)) ** 2) + 0.030 * np.exp(-((r - 0.42 * rough) / 0.16) ** 2)
    co = V.copy(); co[:, 2] += dz
    sk.data.foreach_set("co", co.astype(np.float32).ravel())
    sk.value = 0.0
    # far plain out to the horizon
    R0 = 2600
    a = np.linspace(0, 2 * np.pi, 96, endpoint=False)
    ring = np.stack([R0 * np.cos(a), R0 * np.sin(a), np.full_like(a, -0.03)], 1)
    vv = np.vstack([[0, 0, -0.03], ring]); k = np.arange(96)
    tri = np.stack([np.zeros(96, int), 1 + k, 1 + (k + 1) % 96], 1)
    new_obj("GroundFar", new_mesh("ground_far", vv, [tri], smooth=False), col, ob.data.materials[0])
    return ob

def build_grass(col, rng, throw_x):
    """Dry grass tufts as curved blade strips (one mesh)."""
    n = 16000
    px = rng.uniform(-51, 29, n * 3); py = rng.uniform(-23, 31, n * 3)
    dens = fbm(px * 0.18, py * 0.18, 21, 3)
    keep = dens > 0.50
    r = np.hypot(px, py); keep &= r > 2.1                       # bare patch at the impact point
    keep &= ~((np.abs(px - throw_x) < 2.2) & (np.abs(py) < 2.6))   # trampled throwing pit
    keep &= ~((px > -3.5) & (px < 0.6) & (np.abs(py) < 0.8))       # landing / roll lane kept visible
    px = px[keep][:n]; py = py[keep][:n]; n = len(px)
    blades = rng.integers(7, 15, n); nb = int(blades.sum())
    tid = np.repeat(np.arange(n), blades)
    bx = px[tid] + rng.normal(0, 0.035, nb); by = py[tid] + rng.normal(0, 0.035, nb)
    tall = (0.5 + 1.2 * fbm(px * 0.6, py * 0.6, 5, 2))[tid]
    hgt = rng.uniform(0.10, 0.34, nb) * tall
    yaw = rng.uniform(0, 2 * np.pi, nb); lean = rng.uniform(0.15, 0.75, nb)
    wid = rng.uniform(0.0028, 0.0055, nb)
    seg = 4
    t = np.linspace(0, 1, seg)[None, :]                                # (1,seg)
    out = (lean[:, None] * hgt[:, None]) * t ** 2                      # outward bend
    up = hgt[:, None] * (t - 0.18 * lean[:, None] * t ** 2)
    cx = bx[:, None] + np.cos(yaw)[:, None] * out; cy = by[:, None] + np.sin(yaw)[:, None] * out
    cz = ground_h(bx, by)[:, None] + up - 0.01
    w = wid[:, None] * (1 - 0.92 * t)                                  # taper
    sx = -np.sin(yaw)[:, None] * w; sy = np.cos(yaw)[:, None] * w
    L_ = np.stack([cx - sx, cy - sy, cz], -1); R_ = np.stack([cx + sx, cy + sy, cz], -1)
    V = np.stack([L_, R_], 2).reshape(-1, 3)                           # blade, seg, side
    base = (np.arange(nb) * seg * 2)[:, None, None]
    s = np.arange(seg - 1)[None, :, None] * 2
    quad = np.array([0, 1, 3, 2])[None, None, :]
    F = (base + s + quad).reshape(-1, 4)
    dry = np.clip(rng.normal(0.72, 0.2, n), 0, 1)[tid]
    c0 = np.array([0.115, 0.150, 0.035]); c1 = np.array([0.50, 0.37, 0.14])
    colr = c0[None] * (1 - dry[:, None]) + c1[None] * dry[:, None]
    colr = colr * rng.uniform(0.7, 1.15, (nb, 1))
    C = np.repeat(colr, seg * 2, 0) * np.tile(np.repeat(np.linspace(0.55, 1.1, seg), 2), nb)[:, None]
    C = np.concatenate([C, np.ones((len(C), 1))], 1)
    me = new_mesh("grass", V, [F], attrs={"col": C})
    return new_obj("Grass", me, col, mat_vcol("GrassMat", rough=0.6, translucent=0.35))

def rock_geo(g, rng, center, size, sub=2, color=(0.3, 0.27, 0.24, 1)):
    P, F, _ = ellipsoid((0, 0, 0), (1, 1, 1), 10 if sub < 3 else 22, 6 if sub < 3 else 14)
    seed = int(rng.integers(0, 9999))
    d = 1 + 0.85 * (fbm(P[:, 0] * 1.6 + 5, P[:, 1] * 1.6 + P[:, 2] * 2.1, seed, 3) - 0.5)
    P = P * d[:, None] * np.array([1.0, rng.uniform(0.6, 1.0), rng.uniform(0.35, 0.7)]) * size
    P = P @ rot_z(rng.uniform(0, 6.28)).T
    c = np.array(color) * np.r_[rng.uniform(0.7, 1.2) * np.ones(3), 1]
    g.add(P + np.asarray(center), F, color=c)

def build_stones(col, rng, throw_x):
    g = Geo()
    n = 2600
    r = np.abs(rng.normal(0, 7.0, n)) + 0.25; a = rng.uniform(0, 6.283, n)
    xs = r * np.cos(a); ys = r * np.sin(a)
    xs = np.r_[xs, rng.uniform(throw_x - 6, throw_x + 8, 600)]; ys = np.r_[ys, rng.uniform(-7, 7, 600)]
    for x, y in zip(xs, ys):
        s = float(np.exp(rng.normal(-4.3, 0.55)))            # ~1.3 cm median
        s = min(s, 0.06)
        tone = rng.choice([0, 1, 2], p=[0.5, 0.3, 0.2])
        c = [(0.15, 0.12, 0.09, 1), (0.20, 0.18, 0.155, 1), (0.10, 0.085, 0.07, 1)][tone]
        rock_geo(g, rng, (x, y, float(ground_h(x, y)) + s * 0.15), s, 2, c)
    for x, y, s in [(2.6, 3.4, 0.22), (-4.2, 2.1, 0.16), (3.9, -2.2, 0.13), (-1.6, 4.8, 0.3), (6.5, 1.5, 0.18), (throw_x + 3.5, -3.0, 0.25)]:
        rock_geo(g, rng, (x, y, float(ground_h(x, y)) + s * 0.1), s, 3, (0.19, 0.17, 0.145, 1))
    return new_obj("Stones", g.mesh("stones"), col, mat_vcol("StoneMat", rough=0.85, bump_scale=60))

def sandbag_geo(g, rng, center, yaw, size=(0.60, 0.30, 0.15)):
    P, F, UV = ellipsoid((0, 0, 0), (1, 1, 1), 20, 10, power=0.42)
    sag = 0.12 * (fbm(P[:, 0] * 2 + 3, P[:, 1] * 2, int(rng.integers(0, 9999)), 2) - 0.5)
    P = P * (1 + sag[:, None])
    P[:, 2] = np.sign(P[:, 2]) * np.abs(P[:, 2]) ** 1.25
    P = P * (np.asarray(size) / 2 * np.array([1.06, 1.08, 1.12]))
    P = P @ rot_z(yaw + rng.normal(0, 0.05)).T
    c = np.array([0.33, 0.265, 0.165]) * rng.uniform(0.6, 1.15) * np.array([1, rng.uniform(0.95, 1.03), rng.uniform(0.85, 1.05)])
    g.add(P + np.asarray(center), F, uv=UV * np.array([4.0, 2.0]) + rng.uniform(0, 1, 2), color=(*c, 1))

def build_sandbags(col, rng, throw_x):
    g = Geo()
    L_, W_, H_ = 0.60, 0.30, 0.145
    def wall(p0, p1, courses, taper=True):
        p0 = np.array(p0, float); p1 = np.array(p1, float)
        d = p1 - p0; length = np.linalg.norm(d); d /= length; yaw = math.atan2(d[1], d[0])
        for c in range(courses):
            nb = int(length / L_) + (0 if c % 2 == 0 else 1)
            off = 0 if c % 2 == 0 else -L_ / 2
            for i in range(nb):
                s = off + (i + 0.5) * L_
                if taper and (s < 0.15 * c or s > length - 0.15 * c):
                    continue
                p = p0 + d * s
                sandbag_geo(g, rng, (p[0] + rng.normal(0, 0.01), p[1] + rng.normal(0, 0.01), 0.07 + c * H_), yaw)
    xw = throw_x + 1.05
    wall((xw, -2.7), (xw, 2.7), 7)                     # front wall the thrower throws over
    wall((xw - 2.4, -2.85), (xw + 0.15, -2.85), 6)     # side wings
    wall((xw - 2.4, 2.85), (xw + 0.15, 2.85), 6)
    # a small observer berm near the target area
    wall((7.5, 6.0), (10.5, 7.2), 4)
    return new_obj("Sandbags", g.mesh("sandbags"), col, mat_burlap())

def crate_geo(g, rng, center, yaw, size=0.62, tone=1.0):
    R_ = rot_z(yaw); s = size; t = 0.022
    def add(sz, c, axis):
        cc = np.array([0.9, 0.86, 0.8]) * rng.uniform(0.65, 1.1) * tone
        box_geo(g, sz, center=np.asarray(center) + R_ @ np.asarray(c), rot=R_, color=(*cc, 1), grain_axis=axis)
    npl = 5; pw = s / npl
    for i in range(npl):
        o = -s / 2 + pw * (i + 0.5)
        add((s, pw - 0.006, t), (0, o, s - t / 2), 0); add((s, pw - 0.006, t), (0, o, t / 2), 0)       # top / bottom
        add((t, pw - 0.006, s - 2 * t), (s / 2 - t / 2, o, s / 2), 2); add((t, pw - 0.006, s - 2 * t), (-s / 2 + t / 2, o, s / 2), 2)
        add((pw - 0.006, t, s - 2 * t), (o, s / 2 - t / 2, s / 2), 2); add((pw - 0.006, t, s - 2 * t), (o, -s / 2 + t / 2, s / 2), 2)
    b = 0.07
    for sx in (-1, 1):
        for zc in (b / 2 + 0.01, s - b / 2 - 0.01):
            add((t, s + 0.01, b), (sx * (s / 2 + t / 2), 0, zc), 1); add((s + 2 * t, t, b), (0, sx * (s / 2 + t / 2), zc), 0)
        for yc in (-s / 2 + b / 2, s / 2 - b / 2):
            add((t, b, s - 2 * b), (sx * (s / 2 + t / 2), yc, s / 2), 2); add((b, t, s - 2 * b), (yc, sx * (s / 2 + t / 2), s / 2), 2)

def drum_geo(g, rng, center, color=(0.10, 0.16, 0.10), tilt=None):
    Rr, H = 0.29, 0.88
    prof = [(0.0, 0.0), (Rr - 0.01, 0.0), (Rr, 0.012)]
    for zc in (0.30, 0.58):
        prof += [(Rr, zc - 0.03), (Rr + 0.012, zc - 0.012), (Rr + 0.012, zc + 0.012), (Rr, zc + 0.03)]
    prof += [(Rr, H - 0.012), (Rr + 0.006, H), (Rr - 0.012, H), (Rr - 0.014, H - 0.02), (0.0, H - 0.02)]
    pr = np.array(prof); segs = 40
    a = np.linspace(0, 2 * np.pi, segs, endpoint=False)
    V = np.stack([pr[:, None, 0] * np.cos(a)[None], pr[:, None, 0] * np.sin(a)[None], np.repeat(pr[:, 1:2], segs, 1)], -1).reshape(-1, 3)
    if tilt is not None:
        V = V @ np.asarray(tilt).T
    g.add(V + np.asarray(center), grid_faces(len(pr), segs, wrap_v=True), color=(*color, 1))

def build_props(col, rng, throw_x):
    wood = mat_wood()
    g = Geo()
    # crates behind / beside the blast point (background of the close shot)
    crate_geo(g, rng, (1.9, 3.6, 0.0), 0.35); crate_geo(g, rng, (2.6, 3.9, 0.0), -0.2, 0.55)
    crate_geo(g, rng, (2.15, 3.72, 0.63), 0.9, 0.5)
    crate_geo(g, rng, (-3.4, 4.6, 0.0), 0.15, 0.7, 0.8)
    crate_geo(g, rng, (throw_x - 1.2, 1.9, 0.0), 0.1, 0.55); crate_geo(g, rng, (throw_x - 1.25, 1.3, 0.0), -0.08, 0.55)
    # fence line: posts + rails, beyond the target area
    yf = 13.0
    for x in np.arange(-48, 30, 2.6):
        hpost = rng.uniform(1.15, 1.3)
        cc = np.array([0.8, 0.76, 0.7]) * rng.uniform(0.6, 1.0)
        box_geo(g, (0.11, 0.11, hpost), center=(x, yf + rng.normal(0, 0.03), hpost / 2 - 0.05), rot=rot_y(rng.normal(0, 0.03)) @ rot_z(rng.uniform(0, 0.3)),
                color=(*cc, 1), grain_axis=2)
        for zr in (0.45, 0.92):
            if rng.random() < 0.93:
                box_geo(g, (2.66, 0.035, 0.11), center=(x + 1.3, yf - 0.07, zr + rng.normal(0, 0.012)), rot=rot_y(rng.normal(0, 0.012)),
                        color=(*(cc * rng.uniform(0.8, 1.15)), 1), grain_axis=0)
    # range marker stakes every 5 m along the throw line (side of the lane)
    for x in (-25, -20, -15, -10, -5):
        box_geo(g, (0.05, 0.05, 0.7), center=(x, -2.2, 0.3), color=(0.85, 0.8, 0.75, 1), grain_axis=2)
    ob = new_obj("WoodProps", g.mesh("woodprops", smooth=False), col, wood)
    g2 = Geo()
    drum_geo(g2, rng, (-2.3, 3.5, 0.0), (0.055, 0.075, 0.045)); drum_geo(g2, rng, (-1.65, 3.85, 0.0), (0.20, 0.045, 0.03))
    drum_geo(g2, rng, (4.4, 4.9, 0.29), (0.07, 0.075, 0.08), tilt=rot_z(0.6) @ rot_y(math.pi / 2))
    drum_geo(g2, rng, (throw_x - 1.9, 2.55, 0.0), (0.055, 0.075, 0.045))
    dob = new_obj("Drums", g2.mesh("drums"), col, mat_drum())
    return ob, dob

def tree_mesh(rng, height=11.0):
    g = Geo(); leaves_v = []; leaves_c = []
    bark = (0.085, 0.065, 0.048, 1)
    trunk_top = height * rng.uniform(0.32, 0.42)
    pts = np.array([[0, 0, -0.3], [rng.normal(0, 0.1), rng.normal(0, 0.1), trunk_top * 0.5], [rng.normal(0, 0.2), rng.normal(0, 0.2), trunk_top]])
    v, f, t = tube(pts, [0.32, 0.25, 0.20], 10); g.add(v, f, color=bark); g.add(v, t, color=bark)
    tips = []
    nb = int(rng.integers(5, 8))
    for i in range(nb):
        az = i / nb * 6.283 + rng.normal(0, 0.3); el = rng.uniform(0.45, 1.25)
        ln = height * rng.uniform(0.30, 0.52)
        d = np.array([math.cos(az) * math.cos(el), math.sin(az) * math.cos(el), math.sin(el)])
        p0 = pts[2] - np.array([0, 0, rng.uniform(0, trunk_top * 0.25)])
        p1 = p0 + d * ln * 0.5 + np.array([0, 0, ln * 0.08]); p2 = p0 + d * ln + np.array([0, 0, ln * 0.22])
        v, f, t = tube(np.array([p0, p1, p2]), [0.15, 0.09, 0.03], 7); g.add(v, f, color=bark); g.add(v, t, color=bark)
        tips += [p1, p2, (p1 + p2) / 2 + rng.normal(0, 0.5, 3)]
        for j in range(2):
            az2 = az + rng.normal(0, 0.9); q = p1 + np.array([math.cos(az2), math.sin(az2), rng.uniform(0.2, 0.9)]) * ln * 0.45
            v, f, t = tube(np.array([p1, (p1 + q) / 2 + [0, 0, 0.15], q]), [0.07, 0.045, 0.02], 6); g.add(v, f, color=bark); g.add(v, t, color=bark)
            tips.append(q)
    tips.append(pts[2] + np.array([0, 0, height * 0.5]))
    # leaf clumps: clouds of small random quads around every branch tip
    for tip in tips:
        rad = height * rng.uniform(0.09, 0.2); nl = 620
        p = rng.normal(0, 1, (nl, 3)); p /= np.linalg.norm(p, axis=1, keepdims=True)
        p *= (rng.uniform(0.15, 1.0, (nl, 1)) ** 0.6) * rad * np.array([1.15, 1.15, 0.8])
        c = tip + p
        u = rng.normal(0, 1, (nl, 3)); u /= np.linalg.norm(u, axis=1, keepdims=True)
        w = np.cross(u, rng.normal(0, 1, (nl, 3))); w /= np.linalg.norm(w, axis=1, keepdims=True)
        s = rng.uniform(0.07, 0.14, (nl, 1))
        quad = np.stack([c - u * s - w * s * 0.6, c + u * s - w * s * 0.6, c + u * s + w * s * 0.6, c - u * s + w * s * 0.6], 1)
        leaves_v.append(quad.reshape(-1, 3))
        depth = 1 - np.linalg.norm(p, axis=1) / (rad * 1.2)
        base = np.array([0.060, 0.105, 0.024]) * rng.uniform(0.75, 1.25)
        cc = base[None] * (0.55 + 0.75 * (1 - depth[:, None])) * rng.uniform(0.75, 1.2, (nl, 1))
        leaves_c.append(np.repeat(np.concatenate([cc, np.ones((nl, 1))], 1), 4, 0))
    lv = np.concatenate(leaves_v); lc = np.concatenate(leaves_c)
    g.add(lv, np.arange(len(lv)).reshape(-1, 4), color=lc)
    return g.mesh("tree")

def build_trees(col, rng, throw_x):
    mat = mat_vcol("TreeMat", rough=0.7, translucent=0.25)
    variants = []
    for i in range(4):
        me = tree_mesh(rng, height=rng.uniform(9, 14)); me.materials.append(mat); variants.append(me)
    spots = []
    for x in np.arange(-150, 150, 6.5):                 # main line beyond the fence
        spots.append((x + rng.normal(0, 2.2), 48 + rng.uniform(0, 34)))
        if rng.random() < 0.7:
            spots.append((x + rng.normal(0, 3), 88 + rng.uniform(0, 40)))
    for y in np.arange(-70, 48, 9):                     # far end of the range (down-throw)
        spots.append((62 + rng.uniform(0, 30), y + rng.normal(0, 3)))
    for x in np.arange(-150, 110, 11):                  # sparse line behind the camera side (for shadows / top view)
        spots.append((x + rng.normal(0, 3), -62 - rng.uniform(0, 30)))
    for y in np.arange(-60, 50, 12):
        spots.append((throw_x - 45 - rng.uniform(0, 30), y + rng.normal(0, 3)))
    spots += [(-36.0, 22.0), (21.0, 30.0)]  # a few closer specimens for parallax
    for i, (x, y) in enumerate(spots):
        ob = bpy.data.objects.new("Tree%03d" % i, variants[int(rng.integers(0, 4))]); col.objects.link(ob)
        s = rng.uniform(0.8, 1.25)
        ob.location = (x, y, 0); ob.scale = (s, s, s * rng.uniform(0.9, 1.15)); ob.rotation_euler = (0, 0, rng.uniform(0, 6.283))
    return variants

def build_hills(col, rng):
    na, nr = 240, 14
    a = np.linspace(0, 2 * np.pi, na, endpoint=False); r = np.linspace(420, 1500, nr)
    A, Rr = np.meshgrid(a, r, indexing="ij")
    prof = np.sin(np.clip((Rr - 420) / 1080, 0, 1) * np.pi) ** 0.8
    hgt = 95 * prof * (0.25 + 0.9 * fbm(np.cos(A) * 2.2 + 5, np.sin(A) * 2.2 + 5, 77, 4)) * (0.6 + 0.6 * fbm(A * 3 + 9, Rr * 0.004, 31, 3))
    V = np.stack([Rr * np.cos(A), Rr * np.sin(A), hgt - 1.0], -1).reshape(-1, 3)
    me = new_mesh("hills", V, [grid_faces(na, nr, wrap_u=True)])
    m, N, L, P = nodemat("HillMat")
    tc = N.new("ShaderNodeTexCoord"); n = N.new("ShaderNodeTexNoise"); n.inputs["Scale"].default_value = 0.02; n.inputs["Detail"].default_value = 6
    L.new(tc.outputs["Object"], n.inputs["Vector"])
    ramp = N.new("ShaderNodeValToRGB"); e = ramp.color_ramp.elements
    e[0].position = 0.35; e[0].color = (0.035, 0.060, 0.022, 1); e[1].position = 0.70; e[1].color = (0.16, 0.14, 0.075, 1)
    L.new(n.outputs["Fac"], ramp.inputs["Fac"]); L.new(ramp.outputs["Color"], P.inputs["Base Color"]); P.inputs["Roughness"].default_value = 0.95
    return new_obj("Hills", me, col, m)

def build(sc, throw_x, seed=11):
    rng = np.random.default_rng(seed); np.random.seed(seed)
    col = bpy.data.collections.new("ENV"); sc.collection.children.link(col)
    make_world(sc)
    ground = build_ground(col)
    build_grass(col, rng, throw_x); build_stones(col, rng, throw_x); build_sandbags(col, rng, throw_x)
    build_props(col, rng, throw_x); build_trees(col, rng, throw_x); build_hills(col, rng)
    return col, ground
