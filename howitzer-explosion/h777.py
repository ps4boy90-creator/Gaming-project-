"""M777A2 155 mm lightweight towed howitzer in firing position, the M795 HE projectile, a five-increment
MACS propelling charge and the rammer staff, modelled from published data and reference photos.

Gun root (local +X = direction of fire, origin = ground under the trunnions, +Z up, +Y = left):
  * low body with two forward stabilisers, two widely splayed trails with self-digging spades, one road
    wheel on a hydrogas arm each side (swung up clear of the ground), A-frame saddle with sight and handwheels;
  * cradle (object "Cradle", origin on the trunnion axis, local +X = bore): four long titanium tubes joined
    by yokes, two recoil cylinders and the accumulator; the trunnions sit 0.8 m ahead of the breech face;
  * recoiling parts (object "Tube", child of the cradle): 155 mm tube, double-baffle muzzle brake with the
    towing eye, breech ring;
  * breech block carrier (object "Breech", hinged on top of the breech ring, swings up to open);
  * loading tray (object "Tray", swings from the left of the cradle into line with the bore).
"""
import bpy, math, os, sys, tempfile
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
for p in ("grenade-explosion", "rpg7-explosion", "mortar-explosion"):
    sys.path.insert(0, os.path.join(HERE, "..", p))
from mathutils import Quaternion, Vector
from util import *
import rpg7, m120
from rpg7 import lathe, ring, pipe, box, _finish, _root, aim_quat
from m120 import cyl, disc_wheel, lathe_uv
import hconst as C

BREECH_OPEN = math.radians(150.0)
TRAY_STOW = math.radians(-115.0)
TRAY_PIVOT = np.array([C.S_BREECH - 0.05, 0.42, -0.06])         # cradle-local point on the tray's swing axis (parallel to the bore)
TRAY_LEN = 0.98
LANYARD_AT = np.array([-0.60, -0.20, 0.06])         # cradle-local position of the firing-mechanism lever (breech closed)
R_SHELL = 0.0770

def materials():
    if "HwGreen" in bpy.data.materials:
        return {m.name: m for m in bpy.data.materials if m.name[:2] in ("Hw", "Sh")}
    M = {}
    def metal(name, col, metallic, lo, hi, scale=60, bump=0.10):
        m, N, L, P = nodemat(name); P.inputs["Base Color"].default_value = (*col, 1); P.inputs["Metallic"].default_value = metallic
        tc, n = rpg7._noise_rough(N, L, P, scale, lo, hi)
        b = N.new("ShaderNodeBump"); b.inputs["Strength"].default_value = bump; b.inputs["Distance"].default_value = 0.0006
        f = N.new("ShaderNodeTexNoise"); f.inputs["Scale"].default_value = 420; L.new(tc.outputs["Object"], f.inputs["Vector"])
        L.new(f.outputs["Fac"], b.inputs["Height"]); L.new(b.outputs["Normal"], P.inputs["Normal"])
        M[name] = m; return m
    metal("HwGreen", (0.070, 0.092, 0.050), 0.25, 0.48, 0.70)           # carriage, cradle, tube: matt green paint
    metal("HwDark", (0.030, 0.032, 0.030), 0.6, 0.42, 0.62)             # breech parts, fittings
    metal("HwBare", (0.42, 0.42, 0.41), 0.95, 0.22, 0.38)               # piston rods, worn steel
    M["HwRubber"] = simple_mat("HwRubber", (0.016, 0.016, 0.016), rough=0.82)
    M["HwLens"] = simple_mat("HwLens", (0.01, 0.02, 0.04), rough=0.03, metal=0.6)
    M["HwWood"] = simple_mat("HwWood", (0.20, 0.13, 0.07), rough=0.6)
    metal("ShBand", (0.72, 0.42, 0.20), 1.0, 0.25, 0.40)                # gilding-metal rotating band
    metal("ShFuze", (0.50, 0.50, 0.48), 0.9, 0.28, 0.42)
    M["ShCharge"] = simple_mat("ShCharge", (0.52, 0.40, 0.22), rough=0.8)
    M["ShChargeEnd"] = simple_mat("ShChargeEnd", (0.12, 0.10, 0.08), rough=0.8)
    M["ShPlug"] = simple_mat("ShPlug", (0.55, 0.50, 0.40), rough=0.5, metal=0.6)
    m, N, L, P = nodemat("ShBody")                                        # olive drab with yellow markings
    img = bpy.data.images.load(_marking_png()); img.pack()
    tx = N.new("ShaderNodeTexImage"); tx.image = img; tx.extension = 'CLIP'
    mix = N.new("ShaderNodeMix"); mix.data_type = 'RGBA'
    mix.inputs["A"].default_value = (0.066, 0.080, 0.028, 1); mix.inputs["B"].default_value = (0.80, 0.56, 0.03, 1)
    L.new(tx.outputs["Alpha"], mix.inputs["Factor"]); L.new(mix.outputs["Result"], P.inputs["Base Color"])
    P.inputs["Metallic"].default_value = 0.15; rpg7._noise_rough(N, L, P, 80, 0.42, 0.6)
    M["ShBody"] = m
    return M

def _marking_png():
    """Yellow stencil lines of a US 155 mm HE projectile (u round the body, v along it, nose = top)."""
    from PIL import Image, ImageDraw, ImageFont
    Wd, Hd = 2048, 2048
    im = Image.new("RGBA", (Wd, Hd), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    fp = os.path.join(HERE, "..", "grenade-explosion", "assets", "BarlowCondensed-SemiBold.ttf")
    f1 = ImageFont.truetype(fp, 92); f2 = ImageFont.truetype(fp, 70)
    y = 880
    for s, f in (("155 H", f1), ("TNT", f1), ("PROJ M795", f1), ("LOT IOP 14D002-018", f2)):
        w = d.textlength(s, font=f); d.text(((Wd - w) / 2, y), s, font=f, fill=(255, 255, 255, 255)); y += f.size + 22
    for k in range(4):                                       # weight-zone squares
        d.rectangle([Wd / 2 - 130 + 70 * k, 760, Wd / 2 - 130 + 70 * k + 44, 804], fill=(255, 255, 255, 255))
    path = os.path.join(tempfile.gettempdir(), "m795_marking.png"); im.save(path)
    return path

def beam(g, p0, p1, sec0, sec1=None, up=(0, 0, 1.0)):
    """Tapered box beam between two points; sec = (width, height)."""
    p0 = np.asarray(p0, float); p1 = np.asarray(p1, float); sec1 = sec1 or sec0
    d = p1 - p0; L_ = np.linalg.norm(d); d /= L_
    a = np.cross(up, d); a /= np.linalg.norm(a); b = np.cross(d, a)
    V = []
    for p, (w, h) in ((p0, sec0), (p1, sec1)):
        for sa, sb in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
            V.append(p + a * sa * w / 2 + b * sb * h / 2)
    g.add(np.array(V), [[0, 1, 2, 3], [7, 6, 5, 4], [0, 4, 5, 1], [1, 5, 6, 2], [2, 6, 7, 3], [3, 7, 4, 0]])

def wheel(g_tire, g_rim, c, r=0.44, w=0.27):
    c = np.asarray(c, float)
    prof = [(-w / 2, r * 0.62), (-w / 2, r * 0.90), (-w * 0.36, r), (w * 0.36, r), (w / 2, r * 0.90), (w / 2, r * 0.62)]
    tmp = Geo(); lathe(tmp, prof, 36); V = np.concatenate(tmp.v)[:, [1, 0, 2]] + c            # axis along Y
    for k, fl in tmp.f.items():
        g_tire.add(V, np.concatenate(fl))
    tmp = Geo(); lathe(tmp, [(-w * 0.30, 0.001), (-w * 0.30, r * 0.60), (-w * 0.42, r * 0.63), (w * 0.42, r * 0.63), (w * 0.30, r * 0.60), (w * 0.30, 0.001)], 28)
    V = np.concatenate(tmp.v)[:, [1, 0, 2]] + c
    for k, fl in tmp.f.items():
        g_rim.add(V, np.concatenate(fl))

# ----------------------------------------------------------------------------- the gun
def build_gun(col=None, name="M777", elev=None):
    """Returns dict(root, cradle, tube, breech, tray, struts)."""
    M = materials(); elev = C.ELEV if elev is None else elev
    root = _root(name, col)
    cradle = _root("Cradle", col); cradle.parent = root; cradle.location = C.TRUN
    tube = _root("Tube", col); tube.parent = cradle
    SB, ST, SM = C.S_BREECH, C.S_TUBE, C.S_MUZZLE
    # --- recoiling parts: breech ring, tube, muzzle brake with the towing eye
    gt = Geo(); gd = Geo(); gb = Geo(); gk0 = Geo()
    lathe(gt, [(SB, 0.094), (SB, 0.205), (SB + 0.03, 0.225), (SB + 0.40, 0.225), (SB + 0.46, 0.170), (0.90, 0.162), (1.60, 0.136), (2.70, 0.118), (ST, 0.100), (ST, 0.0775)], 56)
    lathe(gt, [(ST, 0.0775), (C.S_SEAT + 0.12, 0.0775), (C.S_SEAT + 0.04, 0.0900), (SB, 0.0920)], 48)                     # bore + powder chamber
    box(gt, (0.36, 0.40, 0.10), (SB + 0.22, 0.0, 0.235)); box(gt, (0.30, 0.10, 0.34), (SB + 0.22, -0.245, 0.02))          # breech-ring lugs
    for x, r_, w, h in ((SB + 0.02, 0.225, 0.04, 0.008), (SB + 0.38, 0.225, 0.04, 0.008), (0.95, 0.160, 0.05, 0.006), (ST - 0.30, 0.103, 0.05, 0.006)):
        ring(gt, x, r_, w, h, 56)
    lathe(gt, [(ST - 0.03, 0.100), (ST - 0.03, 0.150), (ST + 0.02, 0.158), (ST + 0.40, 0.158), (ST + 0.45, 0.140), (ST + 0.45, 0.082)], 44)   # brake body
    for sx in (ST + 0.10, ST + 0.26):                                                                                         # dark side ports
        for sy in (-1, 1):
            box(gk0, (0.100, 0.020, 0.170), (sx + 0.05, sy * 0.152, 0.0)); box(gt, (0.020, 0.060, 0.200), (sx + 0.115, sy * 0.170, 0.0), rot=rot_z(sy * -0.5))
    ang = np.linspace(0, 2 * np.pi, 25)
    pipe(gt, [(SM + 0.09 + 0.085 * math.cos(a), 0.085 * math.sin(a), -0.02) for a in ang], [0.028] * 25, 10)                # towing eye
    box(gt, (0.10, 0.12, 0.10), (SM - 0.01, 0, -0.02))
    _finish(gt, "TubeSteel", col, M["HwGreen"], tube); _finish(gk0, "BrakePorts", col, M["HwDark"], tube)
    # --- breech block carrier (hinge on top of the breech ring; rotation about +Y swings it back and up)
    breech = _root("Breech", col); breech.parent = tube; breech.location = (SB, 0, 0.215)
    box(gd, (0.070, 0.330, 0.440), (-0.040, 0.0, -0.215))
    cyl(gd, (-0.01, 0, -0.215), (0.130, 0, -0.215), 0.0905, 40)
    for k in range(6):
        a = k * math.pi / 3
        cyl(gb, (0.02, 0.089 * math.cos(a), -0.215 + 0.089 * math.sin(a)), (0.12, 0.089 * math.cos(a), -0.215 + 0.089 * math.sin(a)), 0.012, 8)
    cyl(gd, (-0.085, 0, -0.215), (-0.040, 0, -0.215), 0.060, 24)
    box(gd, (0.050, 0.120, 0.050), (-0.100, 0.110, -0.200)); cyl(gd, (-0.115, 0.170, -0.200), (-0.115, 0.200, -0.120), 0.010, 8)     # firing lever (left)
    box(gd, (0.090, 0.150, 0.090), (-0.050, 0.060, 0.040))                                                                     # primer feed mechanism
    cyl(gd, (-0.02, -0.19, 0.0), (-0.02, 0.19, 0.0), 0.028, 14)
    pipe(gd, [(-0.06, -0.175, -0.33), (-0.16, -0.20, -0.33), (-0.16, -0.20, -0.20)], [0.012] * 3, 8)                         # operating handle
    _finish(gd, "BreechDark", col, M["HwDark"], breech); _finish(gb, "BreechBare", col, M["HwBare"], breech)
    # --- cradle: four long titanium tubes joined by yokes, two recoil cylinders, accumulator, trunnions
    gc = Geo(); gr = Geo(); gk = Geo()
    CT = [(0.215, 0.215), (-0.215, 0.215), (0.250, -0.165), (-0.250, -0.165)]
    for (y, z) in CT:
        cyl(gc, (SB + 0.05, y, z), (2.75, y, z), 0.078, 26); cyl(gc, (2.75, y, z), (2.78, y, z), 0.085, 26); cyl(gc, (SB + 0.02, y, z), (SB + 0.05, y, z), 0.085, 26)
    for sx, ln in ((-0.10, 0.20), (1.30, 0.10), (2.50, 0.30)):                                  # yokes: plates top and bottom, side webs (the tube passes between)
        box(gc, (ln, 0.60, 0.060), (sx, 0, 0.300)); box(gc, (ln, 0.66, 0.060), (sx, 0, -0.250))
        for sy in (-1, 1):
            box(gc, (ln, 0.050, 0.560), (sx, sy * 0.315, 0.025))
    box(gc, (0.22, 0.30, 0.20), (2.50, 0.0, 0.42))                                                # front housing on top of the cradle
    for sy in (-1, 1):
        cyl(gc, (0.25, sy * 0.085, 0.330), (2.20, sy * 0.085, 0.330), 0.052, 18); cyl(gr, (2.20, sy * 0.085, 0.330), (2.42, sy * 0.085, 0.330), 0.026, 12)   # recoil cylinders
        cyl(gc, (0.0, sy * 0.34, 0.0), (0.0, sy * 0.47, 0.0), 0.085, 24); box(gc, (0.26, 0.05, 0.30), (0.0, sy * 0.345, 0.0))                              # trunnions
    cyl(gc, (0.35, -0.36, 0.06), (1.25, -0.36, 0.06), 0.075, 20); cyl(gc, (0.30, -0.36, 0.06), (0.35, -0.36, 0.06), 0.05, 14)                               # accumulator
    box(gc, (2.60, 0.10, 0.030), (1.15, 0.0, -0.205))
    pipe(gk, [(0.2, 0.31, 0.30), (0.9, 0.325, 0.33), (1.7, 0.32, 0.31), (2.4, 0.31, 0.30)], [0.012] * 4, 8)
    pipe(gk, [(0.1, -0.30, 0.31), (0.6, -0.42, 0.20), (1.3, -0.44, 0.10)], [0.012] * 3, 8)
    _finish(gc, "CradleGreen", col, M["HwGreen"], cradle); _finish(gr, "CradleRods", col, M["HwBare"], cradle); _finish(gk, "CradleHoses", col, M["HwRubber"], cradle)
    # --- loading tray: trough on a swing arm (tray origin on the swing axis)
    tray = _root("Tray", col); tray.parent = cradle; tray.location = TRAY_PIVOT
    gy = Geo(); off = -TRAY_PIVOT; off[0] = 0.0
    a = np.linspace(math.radians(200), math.radians(340), 15); xs = np.array([0.02, -TRAY_LEN])
    for rr, flip in ((R_SHELL + 0.006, False), (R_SHELL + 0.016, True)):
        V = np.array([[x, off[1] + rr * math.cos(t), off[2] + rr * math.sin(t)] for x in xs for t in a])
        gy.add(V, grid_faces(2, len(a), flip=flip))
    for x in (-0.12, -0.62):
        beam(gy, (x, 0, 0), (x, off[1] * 0.80, off[2] - R_SHELL - 0.03), (0.06, 0.05), up=(1, 0, 0))
    cyl(gy, (0.0, 0, 0), (-0.80, 0, 0), 0.030, 14)
    _finish(gy, "TrayGreen", col, M["HwGreen"], tray)
    # --- carriage: low body, A-frame saddle, forward stabilisers, split trails with spades, one road wheel each side
    gg = Geo(); gb2 = Geo(); gt2 = Geo(); grim = Geo(); gl = Geo(); gdk = Geo()
    V = np.array([[0.95, 0.38], [0.75, 0.56], [-1.30, 0.56], [-1.58, 0.36], [-1.58, -0.36], [-1.30, -0.56], [0.75, -0.56], [0.95, -0.38]])
    n = len(V); Vb = np.array([[x, y, 0.13] for x, y in V] + [[x * 0.97, y * 0.92, 0.43] for x, y in V])
    gg.add(Vb, [[k, (k + 1) % n, n + (k + 1) % n, n + k] for k in range(n)]); gg.add(Vb, [list(range(n, 2 * n)), list(range(n - 1, -1, -1))])
    cyl(gg, (-0.05, 0, 0.43), (-0.05, 0, 0.53), 0.50, 44); cyl(gdk, (-0.05, 0, 0.53), (-0.05, 0, 0.56), 0.46, 44)                 # traverse bearing
    for sy in (-1, 1):
        # saddle cheek: an A-frame up to the trunnion
        apex = np.array([0.0, sy * 0.44, C.TRUN[2]])
        beam(gg, (0.50, sy * 0.44, 0.56), apex + [0.03, 0, 0.02], (0.08, 0.20), (0.08, 0.16), up=(0, 1, 0)); beam(gg, (-0.52, sy * 0.44, 0.56), apex + [-0.03, 0, 0.02], (0.08, 0.20), (0.08, 0.16), up=(0, 1, 0))
        beam(gg, (-0.58, sy * 0.44, 0.60), (0.56, sy * 0.44, 0.60), (0.08, 0.12), up=(0, 1, 0)); cyl(gg, apex - [0, sy * 0.05, 0], apex + [0, sy * 0.05, 0], 0.13, 24)
        # forward stabiliser: flat box beam with an upturned pad
        s0 = np.array([0.80, sy * 0.46, 0.27]); s1 = np.array([3.05, sy * 1.42, 0.13])
        beam(gg, s0, s1, (0.30, 0.20), (0.24, 0.12)); sd = (s1 - s0) / np.linalg.norm(s1 - s0)
        box(gg, (0.52, 0.40, 0.035), s1 + sd * 0.10 + [0, 0, -0.085], rot=np.stack([sd, np.cross([0, 0, 1.0], sd), [0, 0, 1.0]], 1))
        box(gg, (0.16, 0.40, 0.035), s1 + sd * 0.41 + [0, 0, -0.045], rot=np.stack([sd, np.cross([0, 0, 1.0], sd), [0, 0, 1.0]], 1) @ rot_y(math.radians(-32)))
        cyl(gdk, s0 + [0.0, 0, 0.10], s0 + sd * 0.9 + [0, 0, 0.16], 0.040, 12)                                                   # stabiliser ram
        # trail: stout box beam, widely splayed, with the big self-digging spade
        t0 = np.array([-1.35, sy * 0.50, 0.30]); t1 = np.array([-4.25, sy * 2.38, 0.26]); td = (t1 - t0) / np.linalg.norm(t1 - t0); tn = np.cross(td, [0, 0, 1.0])
        beam(gg, t0, t1, (0.36, 0.30), (0.30, 0.24)); cyl(gg, t0 + [0, 0, -0.17], t0 + [0, 0, 0.17], 0.20, 20)
        Rt = np.stack([td, tn, np.cross(td, tn)], 1)
        box(gg, (0.06, 1.05, 0.78), t1 + td * 0.20 + np.array([0, 0, -0.20]), rot=Rt @ rot_y(math.radians(-68)))                # spade blade
        box(gg, (0.50, 1.05, 0.05), t1 + td * 0.05 + np.array([0, 0, 0.145]), rot=Rt)                                           # spade top plate
        for sgn in (-1, 1):
            box(gg, (0.34, 0.03, 0.34), t1 + td * 0.10 + tn * sgn * 0.40 + np.array([0, 0, -0.03]), rot=Rt @ rot_y(math.radians(-35)))   # gussets
        pipe(gdk, [t1 - td * 0.95 + [0, 0, 0.13], t1 - td * 0.95 + [0, 0, 0.26], t1 - td * 0.55 + [0, 0, 0.26], t1 - td * 0.55 + [0, 0, 0.13]], [0.014] * 4, 8)
        cyl(gdk, t0 + td * 0.25 + tn * sy * -0.24 + [0, 0, 0.05], t0 + td * 1.25 + tn * sy * -0.22 + [0, 0, 0.05], 0.050, 14)    # trail damper
        cyl(gb2, t0 + td * 1.25 + tn * sy * -0.22 + [0, 0, 0.05], t0 + td * 1.75 + tn * sy * -0.21 + [0, 0, 0.05], 0.024, 10)
        # road wheel on its suspension arm, swung up clear of the ground
        c = np.array([-1.12, sy * 1.04, 0.63]); wheel(gt2, grim, c)
        beam(gg, (-0.25, sy * 0.58, 0.36), c - [0, sy * 0.20, 0], (0.16, 0.14)); cyl(gg, c - [0, sy * 0.24, 0], c - [0, sy * 0.10, 0], 0.085, 16)
        cyl(gdk, (-0.75, sy * 0.62, 0.52), (-0.10, sy * 0.62, 0.50), 0.065, 14)                                                    # hydrogas unit
    # gunner's side (left): sight mount with panoramic telescope, two handwheels on a gearbox; assistant gunner's side (right)
    box(gg, (0.20, 0.16, 0.34), (-0.32, 0.60, 1.08)); pipe(gg, [(-0.30, 0.60, 1.22), (-0.26, 0.66, 1.50), (-0.24, 0.66, 1.80)], [0.045, 0.040, 0.034], 12)
    box(gdk, (0.13, 0.11, 0.17), (-0.24, 0.66, 1.87)); cyl(gdk, (-0.24, 0.66, 1.95), (-0.24, 0.66, 2.08), 0.032, 12); cyl(gdk, (-0.24, 0.66, 2.05), (-0.35, 0.66, 2.07), 0.024, 12)
    cyl(gl, (-0.352, 0.66, 2.07), (-0.355, 0.66, 2.07), 0.019, 12); box(gdk, (0.16, 0.05, 0.12), (-0.26, 0.72, 1.55))
    disc_wheel(gdk, (-0.32, 0.76, 1.05), (0, 1, 0), 0.16, 0.012); cyl(gg, (-0.32, 0.66, 1.05), (-0.32, 0.75, 1.05), 0.024, 10)
    disc_wheel(gdk, (-0.52, 0.62, 1.20), (-1, 0, 0.2), 0.16, 0.012); cyl(gg, (-0.40, 0.62, 1.18), (-0.51, 0.62, 1.20), 0.024, 10)
    box(gg, (0.18, 0.14, 0.28), (-0.30, -0.60, 1.04)); disc_wheel(gdk, (-0.30, -0.75, 1.04), (0, -1, 0), 0.16, 0.012); cyl(gg, (-0.30, -0.66, 1.04), (-0.30, -0.74, 1.04), 0.024, 10)
    box(gdk, (0.07, 0.27, 0.21), (-0.10, -0.64, 1.42)); pipe(gg, [(-0.22, -0.60, 1.18), (-0.12, -0.63, 1.32)], [0.03, 0.03], 10)          # fire-control display
    for g_, nm, mt in ((gg, "CarriageGreen", "HwGreen"), (gb2, "CarriageRods", "HwBare"), (gt2, "Tyres", "HwRubber"), (grim, "Rims", "HwGreen"),
                       (gl, "SightLens", "HwLens"), (gdk, "CarriageDark", "HwDark")):
        _finish(g_, nm, col, M[mt], root)
    # balancing gear: two gas struts from the saddle up to the cradle (separate objects so they follow the elevation)
    struts = []
    for sy in (-1, 1):
        g1 = Geo(); cyl(g1, (0, 0, 0), (1, 0, 0), 0.055, 16); g2 = Geo(); cyl(g2, (0, 0, 0), (1, 0, 0), 0.030, 12)
        o1 = _finish(g1, "StrutBody", col, M["HwDark"], root); o2 = _finish(g2, "StrutRod", col, M["HwBare"], root)
        o1.rotation_mode = o2.rotation_mode = 'QUATERNION'; struts.append((sy, o1, o2))
    G = dict(root=root, cradle=cradle, tube=tube, breech=breech, tray=tray, struts=struts)
    set_elevation(G, elev)
    return G

def set_elevation(G, elev):
    q = aim_quat((math.cos(elev), 0, math.sin(elev))); G["cradle"].rotation_quaternion = q
    for sy, o1, o2 in G["struts"]:
        top = np.array(Vector(C.TRUN) + q @ Vector((1.30, sy * 0.36, -0.20))); bot = np.array([0.46, sy * 0.36, 0.60]); d = top - bot; L_ = float(np.linalg.norm(d))
        qq = aim_quat(d / L_)
        o1.location = bot; o1.rotation_quaternion = qq; o1.scale = (0.50, 1, 1)
        o2.location = bot; o2.rotation_quaternion = qq; o2.scale = (L_, 1, 1)

# ----------------------------------------------------------------------------- ammunition and tools
SHELL_PROF = [(0.000, 0.0005), (0.000, 0.0660), (0.085, R_SHELL - 0.0004), (0.092, R_SHELL - 0.0004)]
class Shell:
    """M795: origin at the base, +X towards the nose. plug=True shows the lifting plug instead of the fuze."""
    def __init__(self, col=None, name="M795", plug=False):
        M = materials(); self.root = _root(name, col); self.obs = []
        st = Geo(); bd = Geo(); band = Geo(); fz = Geo(); pl = Geo()
        lathe(st, SHELL_PROF, 48)
        lathe(band, [(0.092, R_SHELL), (0.094, 0.0792), (0.128, 0.0792), (0.130, R_SHELL)], 48)             # rotating band
        lathe(st, [(0.130, R_SHELL - 0.0004), (0.138, R_SHELL - 0.0004), (0.140, R_SHELL + 0.0004), (0.152, R_SHELL + 0.0004), (0.154, R_SHELL - 0.0004)], 48)  # obturator
        xs = np.linspace(0.154, 0.745, 22); u = np.clip((xs - 0.335) / (0.745 - 0.335), 0, 1)
        rr = R_SHELL - (R_SHELL - 0.0300) * (1 - np.sqrt(np.maximum(1 - u ** 2 * 0.985, 0))) / (1 - math.sqrt(0.015))      # secant-like ogive
        lathe_uv(bd, list(zip(xs, rr)), 56, 0.154, 0.745)
        if plug:
            lathe(pl, [(0.745, 0.0300), (0.770, 0.0300), (0.772, 0.020), (0.790, 0.020)], 24)
            ang = np.linspace(0, 2 * np.pi, 17); pipe(pl, [(0.812 + 0.022 * math.sin(a), 0.0, 0.022 * math.cos(a)) for a in ang], [0.007] * 17, 8)
        else:                                                                                                 # point-detonating fuze
            lathe(fz, [(0.745, 0.0300), (0.752, 0.0305), (0.764, 0.0300), (0.800, 0.0190), (0.835, 0.0095), (0.843, 0.0070), (0.843, 0.0005)], 36)
            ring(band, 0.760, 0.0302, 0.006, 0.0006, 36)
        for g_, nm, mt in ((st, "Base", "ShBody"), (bd, "Body", "ShBody"), (band, "Band", "ShBand"), (fz, "Fuze", "ShFuze"), (pl, "Plug", "ShPlug")):
            if g_.v:
                self.obs.append(_finish(g_, name + nm, col, M[mt], self.root))
    def set_visible(self, v):
        for o in self.obs:
            o.hide_render = not v

class Charge:
    """Five MACS M232A1 increments as one stick; origin at the rear face, +X forward."""
    def __init__(self, col=None, name="MACS"):
        M = materials(); self.root = _root(name, col); g = Geo(); e = Geo()
        for k in range(C.MACS_N):
            x0 = k * C.MACS_LEN
            lathe(g, [(x0 + 0.002, 0.030), (x0 + 0.002, 0.074), (x0 + 0.010, 0.0765), (x0 + C.MACS_LEN - 0.010, 0.0765), (x0 + C.MACS_LEN - 0.002, 0.074),
                      (x0 + C.MACS_LEN - 0.002, 0.030)], 40)
            lathe(e, [(x0 + 0.004, 0.0005), (x0 + 0.004, 0.031), (x0 + C.MACS_LEN - 0.004, 0.031), (x0 + C.MACS_LEN - 0.004, 0.0005)], 20)
        self.obs = [_finish(g, name + "Case", col, M["ShCharge"], self.root), _finish(e, name + "Core", col, M["ShChargeEnd"], self.root)]
    def set_visible(self, v):
        for o in self.obs:
            o.hide_render = not v

RAMMER_LEN = 2.70
def build_rammer(col=None, name="Rammer"):
    """Rammer staff: origin at the face of the head, +X = pushing direction (the pole runs back along -X)."""
    M = materials(); root = _root(name, col); g = Geo(); w = Geo()
    lathe(g, [(0.0, 0.0005), (0.0, 0.066), (-0.025, 0.070), (-0.075, 0.060), (-0.110, 0.030), (-0.20, 0.022)], 28)
    cyl(w, (-0.20, 0, 0), (-RAMMER_LEN, 0, 0), 0.019, 14)
    _finish(g, name + "Head", col, M["HwDark"], root); _finish(w, name + "Pole", col, M["HwWood"], root)
    return root
