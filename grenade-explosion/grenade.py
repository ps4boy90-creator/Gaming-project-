"""Procedural M67 fragmentation grenade (own model).

Proportions follow the TM 43-0001-29 data-sheet drawing and reference photos: 63.5 mm
steel sphere, 3.53 in (89.7 mm) overall, a block-shaped M213 fuze head on a short neck,
and the safety lever ("spoon"): a hood over the fuze top that hooks onto the hinge lug
with two tabs, then one nearly straight tapered strip that runs down at ~20 degrees,
just touches the ball near its widest point, stands clear of it lower down and ends in
a small outward curl. Safety pin + pull ring and the wire safety clip are separate."""
import bpy, math, os
import numpy as np
from util import *

R = 0.03175          # body radius (2.5 in diameter)
HERE = os.path.dirname(os.path.abspath(__file__))

def _stencil_texture():
    """Yellow stencilled body markings as an equirect mask image."""
    path = os.path.join(HERE, "assets", "grenade_markings.png")
    if not os.path.exists(path):
        from PIL import Image, ImageDraw, ImageFont
        W, H = 2048, 1024
        im = Image.new("L", (W, H), 0); d = ImageDraw.Draw(im)
        f1 = ImageFont.truetype(os.path.join(HERE, "assets", "SairaStencilOne-Regular.ttf"), 46)
        f2 = ImageFont.truetype(os.path.join(HERE, "assets", "SairaStencilOne-Regular.ttf"), 34)
        def block(cx, lines):
            y = 330
            for txt, f in lines:
                w = d.textlength(txt, font=f)
                d.text((cx - w / 2, y), txt, fill=255, font=f); y += f.size + 12
        block(W * 0.50, [("GRENADE, HAND", f1), ("FRAG, DELAY, M67", f1), ("COMP B", f2), ("LOT CC-26K104-011", f2)])
        im = im.resize((W, H))
        im.save(path)
    img = bpy.data.images.load(path); img.colorspace_settings.name = "Non-Color"
    return img

def materials():
    mats = {}
    # --- body: olive drab enamel over cast steel, yellow stencil
    m, N, L, P = nodemat("GrenadeBody")
    tc = N.new("ShaderNodeTexCoord")
    noise = N.new("ShaderNodeTexNoise"); noise.inputs["Scale"].default_value = 45; noise.inputs["Detail"].default_value = 6
    L.new(tc.outputs["Object"], noise.inputs["Vector"])
    big = N.new("ShaderNodeTexNoise"); big.inputs["Scale"].default_value = 9; big.inputs["Detail"].default_value = 3
    L.new(tc.outputs["Object"], big.inputs["Vector"])
    ramp = N.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.30; ramp.color_ramp.elements[0].color = (0.030, 0.038, 0.014, 1)
    ramp.color_ramp.elements[1].position = 0.75; ramp.color_ramp.elements[1].color = (0.062, 0.076, 0.030, 1)
    L.new(big.outputs["Fac"], ramp.inputs["Fac"])
    tex = N.new("ShaderNodeTexImage"); tex.image = _stencil_texture(); tex.extension = 'REPEAT'
    uv = N.new("ShaderNodeUVMap"); L.new(uv.outputs["UV"], tex.inputs["Vector"])
    # wear the stencil with noise so it looks sprayed
    wear = N.new("ShaderNodeMath"); wear.operation = 'MULTIPLY'
    wr = N.new("ShaderNodeMapRange"); wr.inputs["From Min"].default_value = 0.28; wr.inputs["From Max"].default_value = 0.55
    L.new(noise.outputs["Fac"], wr.inputs["Value"])
    L.new(tex.outputs["Color"], wear.inputs[0]); L.new(wr.outputs["Result"], wear.inputs[1])
    mix = N.new("ShaderNodeMix"); mix.data_type = 'RGBA'
    mix.inputs["B"].default_value = (0.72, 0.52, 0.035, 1)
    L.new(wear.outputs[0], mix.inputs["Factor"]); L.new(ramp.outputs["Color"], mix.inputs["A"])
    L.new(mix.outputs["Result"], P.inputs["Base Color"])
    rr = N.new("ShaderNodeMapRange"); rr.inputs["To Min"].default_value = 0.38; rr.inputs["To Max"].default_value = 0.62
    L.new(noise.outputs["Fac"], rr.inputs["Value"]); L.new(rr.outputs["Result"], P.inputs["Roughness"])
    P.inputs["Metallic"].default_value = 0.0
    P.inputs["Coat Weight"].default_value = 0.15; P.inputs["Coat Roughness"].default_value = 0.35
    bump = N.new("ShaderNodeBump"); bump.inputs["Strength"].default_value = 0.22; bump.inputs["Distance"].default_value = 0.0006
    fine = N.new("ShaderNodeTexNoise"); fine.inputs["Scale"].default_value = 900; fine.inputs["Detail"].default_value = 2
    L.new(tc.outputs["Object"], fine.inputs["Vector"])
    L.new(fine.outputs["Fac"], bump.inputs["Height"]); L.new(bump.outputs["Normal"], P.inputs["Normal"])
    mats["body"] = m
    # --- fuze: die-cast head, dull olive-grey finish
    m, N, L, P = nodemat("GrenadeFuze")
    P.inputs["Base Color"].default_value = (0.085, 0.095, 0.062, 1); P.inputs["Metallic"].default_value = 0.5
    tc = N.new("ShaderNodeTexCoord"); n2 = N.new("ShaderNodeTexNoise"); n2.inputs["Scale"].default_value = 260
    L.new(tc.outputs["Object"], n2.inputs["Vector"])
    r2 = N.new("ShaderNodeMapRange"); r2.inputs["To Min"].default_value = 0.45; r2.inputs["To Max"].default_value = 0.66
    L.new(n2.outputs["Fac"], r2.inputs["Value"]); L.new(r2.outputs["Result"], P.inputs["Roughness"])
    mats["fuze"] = m
    # --- lever: painted sheet steel
    m, N, L, P = nodemat("GrenadeLever")
    P.inputs["Base Color"].default_value = (0.050, 0.060, 0.026, 1); P.inputs["Roughness"].default_value = 0.42
    P.inputs["Metallic"].default_value = 0.35
    mats["lever"] = m
    mats["steel"] = simple_mat("GrenadeSteel", (0.62, 0.62, 0.60), rough=0.28, metal=1.0)
    return mats

def _lathe(profile, segs=48):
    """Revolve (r, z) profile around Z."""
    pr = np.asarray(profile, np.float64); n = len(pr)
    a = np.linspace(0, 2 * np.pi, segs, endpoint=False)
    v = np.stack([pr[:, None, 0] * np.cos(a)[None], pr[:, None, 0] * np.sin(a)[None],
                  np.repeat(pr[:, 1:2], segs, 1)], -1).reshape(-1, 3)
    return v, grid_faces(n, segs, wrap_v=True)

def build(col=None, with_pin=True, with_lever=True, name="Grenade"):
    """Returns (root_empty, lever_object_or_None). Origin = centre of the body sphere, +Z = fuze."""
    mats = materials()
    root = bpy.data.objects.new(name, None); (col or bpy.context.scene.collection).objects.link(root)
    root.empty_display_size = 0.05
    def child(ob):
        ob.parent = root; return ob
    # body: sphere with equatorial seam + flat-ish base + fuze well collar
    nu, nv = 128, 72
    P, F, UV = ellipsoid((0, 0, 0), (R, R, R), nu, nv)
    lat = np.arcsin(np.clip(P[:, 2] / R, -1, 1))
    seam = 0.00045 * np.exp(-(lat / 0.035) ** 2)
    base = -0.0016 * np.exp(-((lat + np.pi / 2) / 0.30) ** 2)
    P = P * (1 + (seam + base)[:, None] / R)
    body = child(new_obj(name + "_body", new_mesh("gbody", P, [F], uvs=UV), col, mats["body"]))
    # collar cast with the body, then the fuze: round neck + die-cast block head
    v, f = _lathe([(0.0092, 0.0290), (0.0092, 0.0325), (0.0086, 0.0332), (0.0070, 0.0333)])
    child(new_obj(name + "_collar", new_mesh("gcollar", v, [f]), col, mats["body"]))
    v, f = _lathe([(0.0076, 0.0326), (0.0076, 0.0370), (0.0001, 0.0370)], 40)
    child(new_obj(name + "_neck", new_mesh("gneck", v, [f]), col, mats["fuze"]))
    g = Geo()
    def box(c, s):
        x, y, z = s; cx, cy, cz = c
        vv = np.array([[sx * x / 2 + cx, sy * y / 2 + cy, sz * z / 2 + cz] for sx in (-1, 1) for sy in (-1, 1) for sz in (-1, 1)])
        ff = np.array([[0, 1, 3, 2], [4, 6, 7, 5], [0, 4, 5, 1], [2, 3, 7, 6], [0, 2, 6, 4], [1, 5, 7, 3]])
        g.add(vv, ff)
    box((0, 0, 0.0459), (0.0190, 0.0170, 0.0182))                       # fuze head, z 36.8 .. 55.0 mm
    box((-0.0100, 0, 0.0546), (0.0032, 0.0150, 0.0030))                 # web carrying the hinge lug
    box((-0.0030, 0, 0.0556), (0.0125, 0.0050, 0.0012))                 # striker lying on the primer
    blk = child(new_obj(name + "_block", g.mesh("gblock", smooth=False), col, mats["fuze"]))
    bv = blk.modifiers.new("bevel", 'BEVEL'); bv.width = 0.0011; bv.segments = 3
    def wire(nm, path, r, mat, closed=False, segs=10):
        path = np.asarray(path, np.float64)
        if closed:
            path = np.vstack([path, path[:2]])
        res = tube(path, np.full(len(path), r), segs, caps=not closed)
        return child(new_obj(name + nm, new_mesh("g" + nm, res[0], [res[1]] if closed else [res[1], res[2]]), col, mat))
    wire("_lug", [(LUG[0], -0.0080, LUG[1]), (LUG[0], 0.0080, LUG[1])], 0.0013, mats["steel"])
    for sy in (-1, 1):                                                   # striker torsion spring coils
        wire("_spring", [(-0.0086, sy * 0.0027, 0.0559), (-0.0086, sy * 0.0042, 0.0559)], 0.0010, mats["steel"])
    lever = None
    if with_lever:
        lever = build_lever(col, mats["lever"], name + "_lever"); child(lever)
    if with_pin:
        # safety pin through the lever ears and the fuze head, split legs spread on the far side
        px, pz = 0.0045, 0.0532
        wire("_pin", [(px, -0.0118, pz), (px, 0.0110, pz)], 0.0010, mats["steel"])
        for sx in (-1, 1):
            wire("_pinleg", [(px, 0.0108, pz), (px + sx * 0.0008, 0.0128, pz), (px + sx * 0.0026, 0.0165, pz)], 0.0006, mats["steel"])
        a = np.linspace(0, 2 * np.pi, 25)[:-1]
        eye = np.array([px, -0.0134, pz])
        wire("_pineye", eye + 0.0018 * np.stack([0 * a, np.cos(a), np.sin(a)], 1), 0.0008, mats["steel"], closed=True, segs=8)
        # pull ring (27 mm) hanging through the eye, standing up beside the fuze
        u = np.array([-0.553, -0.352, 0.755]); w = np.array([0.747, 0.191, 0.636])
        a = np.linspace(0, 2 * np.pi, 73)[:-1]
        ring = (eye + np.array([0, -0.0016, 0]) + 0.0135 * u) + 0.0135 * (np.cos(a)[:, None] * -u + np.sin(a)[:, None] * w)
        wire("_ring", ring, 0.0009, mats["steel"], closed=True)
        # wire safety clip: round the fuze neck, over the lever, with a finger tab beyond it
        a = np.linspace(np.pi / 2, 3 * np.pi / 2, 15)
        loop = [(0.0084 * math.cos(t), 0.0084 * math.sin(t), 0.0350) for t in a]
        loop += [(0.0100, -0.0099, 0.0356), (0.0233, -0.0099, 0.0378), (0.0233, 0.0099, 0.0378), (0.0100, 0.0099, 0.0356)]
        wire("_clip", loop, 0.0007, mats["steel"], closed=True, segs=8)
        wire("_cliptab", [(0.0233, -0.0045, 0.0378), (0.0305, -0.0045, 0.0402), (0.0312, -0.0035, 0.0405), (0.0312, 0.0035, 0.0405),
                          (0.0305, 0.0045, 0.0402), (0.0233, 0.0045, 0.0378)], 0.0007, mats["steel"], segs=8)
    return root, lever

LUG = (-0.0108, 0.0553)        # hinge lug axis (x, z); the lever hooks over it

def lever_centerline(step=0.0005):
    """Side profile (x, z) of the lever's sheet centre, from the hinge end to the tip, and the
    arc length at the top corner. Top plate, one bend, a straight run tangent to the body, a
    slightly steeper lower run and an outward-curled tip."""
    P0 = np.array([LUG[0], 0.0576]); C = np.array([0.0132, 0.0576]); rc = R + 0.00165
    aT = math.atan2(C[1], C[0]) - math.acos(rc / np.linalg.norm(C))
    T = rc * np.array([math.cos(aT), math.sin(aT)])
    low = math.radians(10.0)
    E = T + (T[1] + 0.0220) / math.cos(low) * np.array([math.sin(low), -math.cos(low)])
    pts = [P0, C, T, E]
    for k in range(1, 7):
        ang = low + math.radians(45.0) * k / 6
        pts.append(pts[-1] + 0.0009 * np.array([math.sin(ang), -math.cos(ang)]))
    pts = np.array(pts)
    d = np.r_[0, np.cumsum(np.linalg.norm(np.diff(pts, axis=0), axis=1))]
    s = np.arange(0, d[-1], step)
    xz = np.stack([np.interp(s, d, pts[:, 0]), np.interp(s, d, pts[:, 1])], 1)
    k = 9; ker = np.ones(k) / k; h = k // 2                      # rounds the bends (about 3 mm radius)
    sm = xz.copy()
    for c in range(2):
        sm[h:-h, c] = np.convolve(xz[:, c], ker, mode="valid")
    return sm, s, d[1]

def build_lever(col, mat, name="Lever"):
    """Safety lever ('spoon') in grenade coordinates (origin = body centre, +Z = fuze, lever on +X)."""
    xz, s, sC = lever_centerline()
    L = s[-1]; n = len(s)
    t = np.gradient(xz, axis=0); t /= np.linalg.norm(t, axis=1)[:, None]
    nrm = np.stack([-t[:, 1], t[:, 0]], 1)                       # outward normal in the XZ plane
    after = np.clip((s - sC) / (L - sC), 0, 1)
    w = 0.0096 + (0.0052 - 0.0096) * after                       # half width: 19 mm hood -> 10 mm tip
    endu = np.clip((s - (L - 0.004)) / 0.004, 0, 1)
    w = w * np.maximum(np.sqrt(1 - endu ** 2), 0.3)              # rounded tip
    # side flanges folded towards the fuze: pin ears on the hood, fading out down the strip
    f = np.interp(s, [0, 0.005, sC + 0.004, sC + 0.036, L], [0.0003, 0.0060, 0.0060, 0.0003, 0.0003])
    # pressed stiffening rib down the middle of the strip
    ss = lambda a, b, x: (lambda u: u * u * (3 - 2 * u))(np.clip((x - a) / (b - a), 0, 1))
    rh = 0.0008 * ss(sC + 0.008, sC + 0.016, s) * (1 - ss(L - 0.014, L - 0.007, s))
    rw = np.minimum(0.0026, 0.6 * w)
    g = Geo()
    def strip(cols):
        """cols: list of (y, h) arrays; one smooth-shaded island."""
        m = len(cols)
        V = np.empty((n, m, 3))
        for j, (y, hgt) in enumerate(cols):
            V[:, j, 0] = xz[:, 0] + nrm[:, 0] * hgt; V[:, j, 1] = y; V[:, j, 2] = xz[:, 1] + nrm[:, 1] * hgt
        g.add(V.reshape(-1, 3), grid_faces(n, m))
    z0 = np.zeros(n)
    strip([(-w, z0), (-rw, z0), (-0.45 * rw, rh), (z0, rh), (0.45 * rw, rh), (rw, z0), (w, z0)])
    strip([(-w, -f), (-w, z0)]); strip([(w, z0), (w, -f)])
    # two hook tabs curling round the hinge lug
    a = np.radians(np.linspace(90, 262, 16)); r = xz[0, 1] - LUG[1]
    hx = LUG[0] + r * np.cos(a); hz = LUG[1] + r * np.sin(a)
    for sy in (-1, 1):
        V = np.empty((len(a), 2, 3))
        for j, y in enumerate((sy * 0.0060 - 0.0016, sy * 0.0060 + 0.0016)):
            V[:, j, 0] = hx; V[:, j, 1] = y; V[:, j, 2] = hz
        g.add(V.reshape(-1, 3), grid_faces(len(a), 2))
    ob = new_obj(name, g.mesh("glever"), col, mat)
    so = ob.modifiers.new("solid", 'SOLIDIFY'); so.thickness = 0.0012; so.offset = 0
    return ob
