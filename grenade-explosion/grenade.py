"""Procedural M67-style fragmentation grenade (own model, built from public dimensions:
63.5 mm steel sphere body, M213-type fuze with safety lever and pull ring)."""
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
    # --- fuze: zinc die-cast, parkerised grey-green
    m, N, L, P = nodemat("GrenadeFuze")
    P.inputs["Base Color"].default_value = (0.12, 0.125, 0.105, 1); P.inputs["Metallic"].default_value = 0.85
    tc = N.new("ShaderNodeTexCoord"); n2 = N.new("ShaderNodeTexNoise"); n2.inputs["Scale"].default_value = 260
    L.new(tc.outputs["Object"], n2.inputs["Vector"])
    r2 = N.new("ShaderNodeMapRange"); r2.inputs["To Min"].default_value = 0.34; r2.inputs["To Max"].default_value = 0.58
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
    # neck collar + fuze body (lathe)
    prof = [(0.0000, R + 0.0005), (0.0128, R + 0.0005), (0.0134, R - 0.0020), (0.0134, R - 0.0080)]
    v, f = _lathe([(0.0134, 0.0235), (0.0134, 0.0300), (0.0128, 0.0312), (0.0105, 0.0316)])
    child(new_obj(name + "_collar", new_mesh("gcollar", v, [f]), col, mats["body"]))
    fz = [(0.0102, 0.0300), (0.0102, 0.0345), (0.0118, 0.0348), (0.0118, 0.0392), (0.0096, 0.0396),
          (0.0096, 0.0520), (0.0090, 0.0528), (0.0072, 0.0532), (0.0072, 0.0560), (0.0001, 0.0562)]
    v, f = _lathe(fz, 40)
    child(new_obj(name + "_fuze", new_mesh("gfuze", v, [f]), col, mats["fuze"]))
    # hinge block on top of the fuze (lever pivots here)
    g = Geo()
    def box(c, s):
        x, y, z = s; cx, cy, cz = c
        vv = np.array([[sx * x / 2 + cx, sy * y / 2 + cy, sz * z / 2 + cz] for sx in (-1, 1) for sy in (-1, 1) for sz in (-1, 1)])
        ff = np.array([[0, 1, 3, 2], [4, 6, 7, 5], [0, 4, 5, 1], [2, 3, 7, 6], [0, 2, 6, 4], [1, 5, 7, 3]])
        g.add(vv, ff)
    box((-0.0035, 0, 0.0585), (0.012, 0.0165, 0.009))
    box((-0.0090, 0.0066, 0.0625), (0.006, 0.0030, 0.008)); box((-0.0090, -0.0066, 0.0625), (0.006, 0.0030, 0.008))
    blk = child(new_obj(name + "_block", g.mesh("gblock", smooth=False), col, mats["fuze"]))
    bv = blk.modifiers.new("bevel", 'BEVEL'); bv.width = 0.0006; bv.segments = 2
    lever = None
    if with_lever:
        lever = build_lever(col, mats["lever"], name + "_lever"); child(lever)
    if with_pin:
        # cotter pin through the fuze + pull ring
        pv, pf, pt = tube([(0.0015, -0.0125, 0.0570), (0.0015, 0.0105, 0.0570)], [0.0011, 0.0011], 10)
        child(new_obj(name + "_pin", new_mesh("gpin", pv, [pf, pt]), col, mats["steel"]))
        a = np.linspace(0, 2 * np.pi, 57)[:-1]
        cen = np.array([0.0015, -0.0125 - 0.0128, 0.0500])
        ring = cen + np.stack([0.25 * 0.0135 * np.cos(a), 0.0135 * np.sin(a) * 0.93, 0.0135 * np.cos(a) * 0.97 - 0.0135 * 0.2 * np.sin(a)], 1)
        ring = np.vstack([ring, ring[:2]])
        rv, rf, rt = tube(ring, np.full(len(ring), 0.0011), 10, caps=False)
        child(new_obj(name + "_ring", new_mesh("gring", rv, [rf]), col, mats["steel"]))
    return root, lever

def build_lever(col, mat, name="Lever"):
    """Safety lever ('spoon'): strip hooked over the fuze top, running down the body contour."""
    pts = []
    pts += [(-0.0105, 0.0655), (-0.0090, 0.0672), (0.0040, 0.0672), (0.0118, 0.0660), (0.0138, 0.0630), (0.0138, 0.0420)]
    r = R + 0.0026
    for ang in np.linspace(math.radians(26), math.radians(104), 18):
        pts.append((r * math.sin(ang), r * math.cos(ang)))
    pts += [(pts[-1][0] + 0.0016, pts[-1][1] - 0.0030)]
    pts = np.array(pts)
    # resample smoothly
    d = np.r_[0, np.cumsum(np.linalg.norm(np.diff(pts, axis=0), axis=1))]
    s = np.linspace(0, d[-1], 70)
    px = np.interp(s, d, pts[:, 0]); pz = np.interp(s, d, pts[:, 1])
    k = np.ones(5) / 5
    px[2:-2] = np.convolve(px, k, mode="valid"); pz[2:-2] = np.convolve(pz, k, mode="valid")
    w = np.interp(s / d[-1], [0, 0.25, 0.45, 1.0], [0.0075, 0.0075, 0.0088, 0.0098])   # half width
    left = np.stack([px, -w, pz], 1); right = np.stack([px, w, pz], 1)
    v = np.empty((len(s) * 2, 3)); v[0::2] = left; v[1::2] = right
    me = new_mesh("glever", v, [grid_faces(len(s), 2)])
    ob = new_obj(name, me, col, mat)
    so = ob.modifiers.new("solid", 'SOLIDIFY'); so.thickness = 0.0013; so.offset = 0
    bv = ob.modifiers.new("bevel", 'BEVEL'); bv.width = 0.0003; bv.segments = 1
    return ob
