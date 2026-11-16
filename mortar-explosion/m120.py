"""US Army M120 120 mm mortar (M298 cannon, M190 bipod, M9 baseplate, M67 sight unit) and the M934A1 HE
cartridge, modelled from the field-manual data and reference photos.

Mortar root (local +X = direction of fire, origin = ground under the baseplate socket, +Z up, +Y = left):
  * M298 cannon: 69 in (1.753 m) smooth-bore tube with a screwed-in base cap that ends in a ball, a thicker
    lower half with collars, a muzzle ring and the white alignment line on top; black phosphate finish.
  * M190 bipod: buffer-housing clamp round the tube, traversing screw with handwheel, elevating column with
    crank, two legs with spade feet, cross-levelling strut and the leg chain; olive drab.
  * M9 baseplate: a 0.92 m "rounded triangle" dish with a central socket, ribs and carrying handles.
  * M67 sight unit on the dovetail at the left end of the traversing assembly.
Cannon object: local +X = bore, origin = ball centre.  It is a child of the root so it can recoil.

Round (local +X = nose, origin = tail end): fin assembly, tail boom with horseshoe propellant increments,
aluminium tail cone, olive-drab body with yellow markings and the multi-option fuze; 711 mm long, 120 mm.
"""
import bpy, math, os, sys, tempfile
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "grenade-explosion")); sys.path.insert(0, os.path.join(HERE, "..", "rpg7-explosion"))
from mathutils import Quaternion, Vector
from util import *
import rpg7
from rpg7 import lathe, ring, pipe, box, _finish, _root, aim_quat
import mconst as C

CLAMP_S = 1.03                    # bore-x of the bipod clamp
GRIP_LO = 0.330                   # round-x of the lower hand
GRIP_HI = 0.500                   # round-x of the upper hand
BODY_R = 0.0595

def materials():
    if "MtSteel" in bpy.data.materials:
        return {m.name: m for m in bpy.data.materials if m.name[:2] in ("Mt", "Rd")}
    M = {}
    def metal(name, col, metallic, lo, hi, scale=90, bump=0.12):
        m, N, L, P = nodemat(name); P.inputs["Base Color"].default_value = (*col, 1); P.inputs["Metallic"].default_value = metallic
        tc, n = rpg7._noise_rough(N, L, P, scale, lo, hi)
        b = N.new("ShaderNodeBump"); b.inputs["Strength"].default_value = bump; b.inputs["Distance"].default_value = 0.0005
        f = N.new("ShaderNodeTexNoise"); f.inputs["Scale"].default_value = 500; L.new(tc.outputs["Object"], f.inputs["Vector"])
        L.new(f.outputs["Fac"], b.inputs["Height"]); L.new(b.outputs["Normal"], P.inputs["Normal"])
        M[name] = m; return m
    metal("MtSteel", (0.020, 0.021, 0.023), 0.75, 0.42, 0.62)             # cannon: black phosphate / paint
    metal("MtOlive", (0.085, 0.098, 0.052), 0.30, 0.45, 0.66)             # bipod, baseplate
    metal("MtBare", (0.30, 0.30, 0.29), 0.95, 0.30, 0.45)                 # screws, worn steel
    metal("MtChain", (0.045, 0.045, 0.045), 0.9, 0.4, 0.6)
    M["MtWhite"] = simple_mat("MtWhite", (0.78, 0.78, 0.74), rough=0.6)
    M["MtRubber"] = simple_mat("MtRubber", (0.012, 0.012, 0.012), rough=0.75)
    M["MtLens"] = simple_mat("MtLens", (0.01, 0.02, 0.04), rough=0.03, metal=0.6)
    metal("RdAlu", (0.66, 0.66, 0.64), 1.0, 0.28, 0.42)
    metal("RdFuze", (0.075, 0.062, 0.050), 0.7, 0.35, 0.5)
    metal("RdBrass", (0.62, 0.46, 0.18), 1.0, 0.25, 0.4)
    M["RdCharge"] = simple_mat("RdCharge", (0.72, 0.62, 0.42), rough=0.85)
    M["RdBand"] = simple_mat("RdBand", (0.80, 0.80, 0.76), rough=0.5)
    # olive-drab body with yellow stencil markings from a generated texture
    m, N, L, P = nodemat("RdBody")
    img = bpy.data.images.load(_marking_png()); img.pack()
    tx = N.new("ShaderNodeTexImage"); tx.image = img; tx.extension = 'CLIP'
    mix = N.new("ShaderNodeMix"); mix.data_type = 'RGBA'
    mix.inputs["A"].default_value = (0.072, 0.086, 0.030, 1); mix.inputs["B"].default_value = (0.80, 0.56, 0.03, 1)
    L.new(tx.outputs["Alpha"], mix.inputs["Factor"]); L.new(mix.outputs["Result"], P.inputs["Base Color"])
    P.inputs["Metallic"].default_value = 0.15; rpg7._noise_rough(N, L, P, 90, 0.42, 0.6)
    M["RdBody"] = m
    return M

def _marking_png():
    """Yellow stencil lines as on a US HE mortar cartridge; u runs round the body, v along it (nose = top)."""
    from PIL import Image, ImageDraw, ImageFont
    Wd, Hd = 2048, 1536
    im = Image.new("RGBA", (Wd, Hd), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    fp = os.path.join(HERE, "..", "grenade-explosion", "assets", "BarlowCondensed-SemiBold.ttf")
    f1 = ImageFont.truetype(fp, 62); f2 = ImageFont.truetype(fp, 50)
    y = 560
    for s, f in (("CTG 120MM HE M934A1", f1), ("W/FZ MO M734A1", f2), ("COMP B", f1), ("LOT MA-11F024-006", f2)):
        w = d.textlength(s, font=f); d.text(((Wd - w) / 2, y), s, font=f, fill=(255, 255, 255, 255)); y += f.size + 16
    path = os.path.join(tempfile.gettempdir(), "m934_marking.png"); im.save(path)
    return path

def lathe_uv(g, prof, segs, v0, v1):
    """Like lathe(), with a seam and UVs: u = angle / 2pi, v = (x - v0) / (v1 - v0)."""
    p = np.asarray(prof, float); a = np.linspace(0, 2 * np.pi, segs + 1)
    V = np.stack([np.repeat(p[:, 0], segs + 1), np.outer(p[:, 1], np.cos(a)).ravel(), np.outer(p[:, 1], np.sin(a)).ravel()], 1)
    uv = np.stack([np.tile(1.0 - a / (2 * np.pi), len(p)), np.repeat((p[:, 0] - v0) / (v1 - v0), segs + 1)], 1)
    g.add(V, grid_faces(len(p), segs + 1), uv=uv)

def _basis(d):
    d = np.asarray(d, float); d = d / np.linalg.norm(d)
    a = np.cross(d, [0, 0, 1.0]) if abs(d[2]) < 0.95 else np.cross(d, [0, 1.0, 0]); a /= np.linalg.norm(a)
    return d, a, np.cross(d, a)

def cyl(g, p0, p1, r, segs=20, r1=None):
    """Capped cylinder / cone frustum between two points."""
    pipe(g, [p0, p1], [r, r if r1 is None else r1], segs)

def disc_wheel(g, c, axis, r, w, spokes=4):
    """Handwheel: rim torus-ish ring + spokes + knob."""
    d, a, b = _basis(axis); c = np.asarray(c, float)
    ang = np.linspace(0, 2 * np.pi, 25)
    pipe(g, [c + r * (np.cos(t) * a + np.sin(t) * b) for t in ang], [w] * 25, 8)
    for k in range(spokes):
        t = 2 * np.pi * k / spokes; cyl(g, c, c + r * (np.cos(t) * a + np.sin(t) * b), w * 0.7, 8)
    cyl(g, c - d * w, c + d * w, w * 1.6, 12)
    k = c + r * a; cyl(g, k, k + d * 0.05, w * 1.1, 10)

# ----------------------------------------------------------------------------- cannon
def build_cannon(col, parent):
    M = materials(); root = _root("Cannon", col); root.parent = parent
    st = Geo(); wh = Geo(); br = Geo()
    R_UP, R_LO = 0.0745, 0.0870
    ball = [(0.045 * math.cos(a), max(0.045 * math.sin(a), 0.0006)) for a in np.radians([50, 70, 90, 110, 130, 150, 165, 180])]
    lathe(st, [(1.753, 0.0603), (1.753, 0.0790), (1.716, 0.0790), (1.712, R_UP), (0.800, R_UP), (0.794, R_LO), (0.300, R_LO), (0.292, 0.0950),
               (0.218, 0.0950), (0.200, 0.0890), (0.150, 0.0740), (0.085, 0.0480), (0.066, 0.0345), (0.040, 0.0345)] + ball, 56)
    lathe(st, [(1.753, 0.0603), (0.262, 0.0603), (0.250, 0.0300), (0.250, 0.0006)], 56)          # bore
    cyl(br, (0.250, 0, 0), (0.266, 0, 0), 0.004, 10)                                               # firing pin
    for x, w, h in ((0.36, 0.034, 0.008), (0.505, 0.030, 0.011), (0.775, 0.034, 0.008), (1.20, 0.022, 0.004)):
        ring(st, x, R_LO if x < 0.79 else R_UP, w, h, 56)
    # cross-bored ball, carrier lugs, stud row, safety / firing selector on the base cap
    cyl(st, (0, -0.047, 0), (0, 0.047, 0), 0.012, 12)
    for sy in (-1, 1):
        box(st, (0.070, 0.022, 0.060), (0.640, sy * 0.094, 0.0))
    for k in range(7):
        x = 0.535 + 0.030 * k; a = math.radians(48)
        n = np.array([0, math.cos(a), -math.sin(a)]); cyl(st, np.array([x, 0, 0]) + n * 0.084, np.array([x, 0, 0]) + n * 0.098, 0.0075, 8)
    box(st, (0.034, 0.016, 0.030), (0.255, -0.094, 0.0)); cyl(st, (0.255, -0.100, 0.0), (0.255, -0.118, 0.0), 0.010, 10)
    box(st, (0.012, 0.012, 0.050), (0.255, -0.118, 0.022))
    # white alignment line on top (dashes), with a cross mark
    x = 0.335
    while x < 1.70:
        e = min(x + 0.165, 1.705)
        if not (0.99 < x < 1.07 or 0.99 < e < 1.07):
            r = R_LO if x < 0.79 else R_UP
            if x < 0.794 < e:
                e = 0.790
            box(wh, (e - x, 0.009, 0.0012), ((x + e) / 2, 0, r + 0.0004))
        x = e + 0.035 if e != 0.790 else 0.800
    box(wh, (0.008, 0.050, 0.0012), (1.455, 0, R_UP + 0.0004)); box(wh, (0.008, 0.050, 0.0012), (0.300 + 0.03, 0, R_LO + 0.0004))
    _finish(st, "CannonSteel", col, M["MtSteel"], root); _finish(wh, "CannonLine", col, M["MtWhite"], root); _finish(br, "CannonPin", col, M["MtBare"], root)
    return root

# ----------------------------------------------------------------------------- baseplate
def build_baseplate(col, parent):
    M = materials(); root = _root("Baseplate", col); root.parent = parent
    prof = np.array([(0.00, -0.012), (0.095, -0.012), (0.125, 0.022), (0.160, 0.022), (0.205, 0.004), (0.42, 0.012), (0.60, 0.060), (0.66, 0.068),
                     (0.90, 0.068), (0.965, 0.060), (1.0, 0.040), (1.0, -0.03)])
    na = 144; a = np.linspace(0, 2 * np.pi, na, endpoint=False)
    R = 0.452 * (1 + 0.035 * np.cos(3 * a))
    rho = prof[:, 0][:, None]; z = np.repeat(prof[:, 1][:, None], na, 1)
    rib = np.clip(np.cos(6 * a), 0, 1) ** 10
    z += (0.022 * rib[None, :]) * np.clip((rho - 0.20) / 0.1, 0, 1) * np.clip((0.62 - rho) / 0.2, 0, 1)
    r = rho * R[None, :]; r[0, :] = 0.0005
    V = np.stack([r * np.cos(a)[None, :], r * np.sin(a)[None, :], z], -1).reshape(-1, 3)
    g = Geo(); g.add(V, grid_faces(len(prof), na, wrap_v=True))
    hb = Geo()
    for k in range(3):                                         # carrying handles (upright U) and tie-down loops (flat)
        t = math.radians(60 + 120 * k); er = np.array([math.cos(t), math.sin(t), 0]); et = np.array([-math.sin(t), math.cos(t), 0])
        c = er * 0.385 + np.array([0, 0, 0.066])
        pipe(hb, [c - et * 0.060, c - et * 0.060 + [0, 0, 0.052], c - et * 0.045 + [0, 0, 0.064], c + et * 0.045 + [0, 0, 0.064], c + et * 0.060 + [0, 0, 0.052], c + et * 0.060],
             [0.0075] * 6, 10)
        t = math.radians(120 * k); er = np.array([math.cos(t), math.sin(t), 0]); et = np.array([-math.sin(t), math.cos(t), 0])
        c = er * 0.400 + np.array([0, 0, 0.072])
        pipe(hb, [c - et * 0.045, c - et * 0.045 + er * 0.050, c + et * 0.045 + er * 0.050, c + et * 0.045, c - et * 0.045], [0.006] * 5, 8)
    _finish(g, "BaseplateDish", col, M["MtOlive"], root, angle=30); _finish(hb, "BaseplateHandles", col, M["MtOlive"], root)
    return root

# ----------------------------------------------------------------------------- bipod + sight
def bipod_points():
    u = np.array([math.cos(C.ELEV), 0, math.sin(C.ELEV)]); n = np.array([math.sin(C.ELEV), 0, -math.cos(C.ELEV)])
    ball = np.array([0, 0, C.ZB]); pc = ball + u * CLAMP_S
    py = pc + n * 0.165
    ph = np.array([0.745, 0.0, 0.555])
    return dict(u=u, n=n, ball=ball, clamp=pc, yoke=py, hub=ph, foot_l=np.array([1.06, 0.60, 0.0]), foot_r=np.array([1.06, -0.60, 0.0]))

def build_bipod(col, parent):
    M = materials(); root = _root("Bipod", col); root.parent = parent
    P = bipod_points(); u, n, pc, py, ph = P["u"], P["n"], P["clamp"], P["yoke"], P["hub"]
    ol = Geo(); bare = Geo(); ch = Geo(); rb = Geo(); ln = Geo(); blk = Geo()
    ey = np.array([0, 1.0, 0])
    # buffer-housing clamp round the tube + clamp handle on the right
    q = aim_quat(u); Rm = np.array(q.to_matrix())
    def along(g_, prof, segs=40):
        tmp = Geo(); lathe(tmp, prof, segs); V = np.concatenate(tmp.v) @ Rm.T + pc
        for k, fl in tmp.f.items():
            g_.add(V, np.concatenate(fl))
    along(ol, [(-0.042, 0.0750), (-0.042, 0.0905), (-0.030, 0.0935), (0.030, 0.0935), (0.042, 0.0905), (0.042, 0.0750)])
    box(ol, (0.050, 0.030, 0.040), pc - ey * 0.105, rot=Rm); cyl(bare, pc - ey * 0.118, pc - ey * 0.118 + u * 0.095, 0.007, 8)
    cyl(rb, pc - ey * 0.118 + u * 0.090, pc - ey * 0.118 + u * 0.135, 0.012, 10)
    # two recoil-buffer cylinders from the clamp to the yoke
    for sy in (-1, 1):
        a0 = pc + ey * sy * 0.066 + n * 0.070; cyl(ol, a0, py + ey * sy * 0.066 + n * 0.02, 0.024, 16)
        cyl(bare, a0 - n * 0.030, a0, 0.011, 10); box(ol, (0.050, 0.050, 0.030), pc + ey * sy * 0.066 + n * 0.078, rot=Rm)
    # traversing assembly: screw housing, handwheel (right), dovetail + sight (left)
    cyl(ol, py - ey * 0.215, py + ey * 0.215, 0.027, 20); cyl(ol, py - ey * 0.085, py + ey * 0.085, 0.040, 20)
    cyl(bare, py - ey * 0.255, py - ey * 0.215, 0.012, 10); disc_wheel(ol, py - ey * 0.262, -ey, 0.058, 0.007)
    box(ol, (0.050, 0.036, 0.060), py + ey * 0.232 + np.array([0, 0, 0.012]))
    s0 = py + ey * 0.232 + np.array([0, 0, 0.042])                                       # M67 sight unit
    box(blk, (0.046, 0.034, 0.030), s0 + [0, 0, 0.015]); box(blk, (0.058, 0.050, 0.070), s0 + [0, 0, 0.065])
    cyl(blk, s0 + [0.010, 0, 0.100], s0 + [0.010, 0, 0.190], 0.017, 14); cyl(blk, s0 + [0.010, 0, 0.185], s0 + [-0.070, 0, 0.205], 0.014, 14)
    cyl(rb, s0 + [-0.066, 0, 0.204], s0 + [-0.092, 0, 0.210], 0.019, 14); cyl(ln, s0 + [-0.0925, 0, 0.2101], s0 + [-0.0935, 0, 0.2103], 0.013, 14)
    cyl(blk, s0 + [0.0, 0.025, 0.060], s0 + [0.0, 0.058, 0.060], 0.017, 14); cyl(blk, s0 + [0.029, 0, 0.050], s0 + [0.060, 0, 0.050], 0.015, 14)
    cyl(blk, s0 + [-0.029, 0, 0.075], s0 + [-0.050, 0, 0.075], 0.011, 12); box(blk, (0.040, 0.012, 0.012), s0 + [0.0, -0.031, 0.040])
    # elevating mechanism: outer housing through the hub, inner screw up to the yoke, crank
    d = (py - ph) / np.linalg.norm(py - ph)
    cyl(ol, ph - d * 0.285, ph + d * 0.135, 0.031, 18); cyl(ol, ph + d * 0.135, ph + d * 0.160, 0.036, 18); cyl(rb, ph - d * 0.300, ph - d * 0.285, 0.033, 18)
    cyl(bare, ph + d * 0.150, py - d * 0.030, 0.019, 14); cyl(ol, py - d * 0.060, py - d * 0.020, 0.030, 16)
    gb = ph + d * 0.105; cyl(ol, gb - ey * 0.060, gb + ey * 0.030, 0.026, 14)
    cyl(bare, gb - ey * 0.060, gb - ey * 0.100, 0.008, 8); cyl(bare, gb - ey * 0.100, gb - ey * 0.100 - d * 0.070, 0.007, 8)
    cyl(rb, gb - ey * 0.100 - d * 0.070, gb - ey * 0.150 - d * 0.070, 0.012, 10)
    # hub + legs + feet
    cyl(ol, ph - ey * 0.075, ph + ey * 0.075, 0.034, 18)
    for s, foot in ((1, P["foot_l"]), (-1, P["foot_r"])):
        top = ph + ey * s * 0.060; ld = (foot - top) / np.linalg.norm(foot - top)
        cyl(ol, top, foot - ld * 0.03, 0.0215, 16); cyl(ol, top + ld * 0.02, top + ld * 0.16, 0.027, 16)
        cyl(ol, foot - ld * 0.12, foot - ld * 0.02, 0.026, 16)
        cyl(ol, foot + [0, 0, 0.012], foot + [0, 0, 0.022], 0.060, 20); cyl(bare, foot + [0, 0, 0.012], foot + [0, 0, -0.07], 0.012, 8, r1=0.002)
        P["leg_dir_" + ("l" if s > 0 else "r")] = ld; P["leg_top_" + ("l" if s > 0 else "r")] = top
    # cross-levelling strut: left leg -> collar on the elevating housing, with a locking knob
    la = P["leg_top_l"] + P["leg_dir_l"] * 0.40; cb = ph + d * 0.02
    cyl(ol, la, cb + ey * 0.03, 0.013, 12); cyl(bare, la + (cb - la) * 0.45, la + (cb - la) * 0.80, 0.0085, 10)
    cyl(ol, la - P["leg_dir_l"] * 0.03, la + P["leg_dir_l"] * 0.03, 0.029, 14)
    kn = la + (cb - la) * 0.42; cyl(rb, kn, kn + np.array([0.05, 0.0, 0.03]), 0.016, 10)
    # chain between the legs (sagging)
    a0 = P["leg_top_l"] + P["leg_dir_l"] * 0.74; a1 = P["leg_top_r"] + P["leg_dir_r"] * 0.74
    for k in range(56):
        t0, t1 = k / 56.0, (k + 0.72) / 56.0
        p0 = lerp(a0, a1, t0) - np.array([0, 0, 0.11 * math.sin(math.pi * t0)]); p1 = lerp(a0, a1, t1) - np.array([0, 0, 0.11 * math.sin(math.pi * t1)])
        pipe(ch, [p0, p1], [(0.007, 0.0035), (0.007, 0.0035)] if k % 2 else [(0.0035, 0.007), (0.0035, 0.007)], 6)
    for g_, nm, mt in ((ol, "BipodOlive", "MtOlive"), (bare, "BipodBare", "MtBare"), (ch, "BipodChain", "MtChain"), (rb, "BipodRubber", "MtRubber"),
                       (ln, "SightLens", "MtLens"), (blk, "SightBody", "MtSteel")):
        _finish(g_, nm, col, M[mt], root)
    return root

def build_mortar(col=None, name="M120"):
    """Returns (root, cannon, baseplate, bipod).  The cannon is aimed along the bore at the set elevation."""
    root = _root(name, col)
    cannon = build_cannon(col, root); cannon.location = (0, 0, C.ZB); cannon.rotation_quaternion = aim_quat((math.cos(C.ELEV), 0, math.sin(C.ELEV)))
    base = build_baseplate(col, root); bip = build_bipod(col, root)
    return root, cannon, base, bip

# ----------------------------------------------------------------------------- round
class Round:
    def __init__(self, col=None, name="M934", increments=2):
        M = materials(); self.root = _root(name, col); self.obs = []
        al = Geo(); bd = Geo(); fz = Geo(); brs = Geo(); chg = Geo(); band = Geo()
        # fin assembly + tail boom (aluminium), primer end at x = 0
        lathe(al, [(0.000, 0.0005), (0.000, 0.0170), (0.004, 0.0225), (0.090, 0.0225), (0.094, 0.0200), (0.200, 0.0200), (0.205, 0.0260),
                   (0.300, 0.0490), (0.330, 0.0540)], 32)
        for k in range(8):
            a = 2 * np.pi * k / 8; e1 = np.array([0, math.cos(a), math.sin(a)]); e2 = np.array([0, -math.sin(a), math.cos(a)])
            pts = np.array([(0.004, 0.020), (0.004, 0.058), (0.050, 0.0595), (0.086, 0.040), (0.090, 0.020)])
            for sgn in (-1, 1):
                V = np.array([[x, 0, 0] for x, r in pts]) + np.outer(pts[:, 1], e1) + e2 * sgn * 0.0011
                al.add(V, [[0, 1, 2, 3, 4]] if sgn > 0 else [[4, 3, 2, 1, 0]])
            V = np.concatenate([np.array([[x, 0, 0] for x, r in pts]) + np.outer(pts[:, 1], e1) + e2 * s * 0.0011 for s in (-1, 1)])
            al.add(V, [[1, 2, 7, 6], [2, 3, 8, 7], [3, 4, 9, 8]])
        cyl(brs, (-0.0005, 0, 0), (0.002, 0, 0), 0.0085, 14)                                # primer
        for k in range(12):                                                                 # flash holes in the boom
            a = 2 * np.pi * k / 6 + (0.5 if k >= 6 else 0); x = 0.118 + 0.040 * (k // 6)
            e1 = np.array([0, math.cos(a), math.sin(a)]); cyl(brs, np.array([x, 0, 0]) + e1 * 0.0195, np.array([x, 0, 0]) + e1 * 0.0203, 0.0035, 8)
        # horseshoe propellant increments round the boom
        for k in range(increments):
            x = 0.110 + 0.036 * k
            ang = np.linspace(math.radians(28), math.radians(332), 30) + 0.9 * k
            pipe(chg, [(x, 0.036 * math.cos(t), 0.036 * math.sin(t)) for t in ang], [(0.0160, 0.0150)] * 30, 12)
        # body: olive drab, max diameter at the obturator band, long ogive to the fuze well
        lathe_uv(bd, [(0.330, 0.0540), (0.360, 0.0575), (0.384, 0.0590), (0.384, BODY_R), (0.455, BODY_R), (0.500, 0.0585), (0.540, 0.0548), (0.575, 0.0492),
                      (0.600, 0.0432), (0.618, 0.0375), (0.622, 0.0300)], 56, 0.330, 0.622)
        lathe(band, [(0.386, BODY_R + 0.0002), (0.386, BODY_R + 0.0011), (0.402, BODY_R + 0.0011), (0.402, BODY_R + 0.0002)], 56)   # obturator ring
        # M734A1 multi-option fuze
        lathe(fz, [(0.622, 0.0300), (0.626, 0.0305), (0.650, 0.0290), (0.652, 0.0262), (0.690, 0.0185), (0.704, 0.0135), (0.711, 0.0105), (0.711, 0.0005)], 40)
        ring(brs, 0.633, 0.0303, 0.006, 0.0006, 40); ring(brs, 0.6505, 0.0276, 0.004, 0.0010, 40)
        lathe(brs, [(0.7112, 0.0060), (0.7112, 0.0098), (0.7092, 0.0108)], 24)
        for g_, nm, mt in ((al, "Tail", "RdAlu"), (bd, "Body", "RdBody"), (fz, "Fuze", "RdFuze"), (brs, "Brass", "RdBrass"), (chg, "Charges", "RdCharge"), (band, "Band", "RdBand")):
            if g_.v:
                self.obs.append(_finish(g_, name + nm, col, M[mt], self.root))
    def set_visible(self, v):
        for o in self.obs:
            o.hide_render = not v
