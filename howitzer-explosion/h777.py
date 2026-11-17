"""M777A2 155 mm lightweight towed howitzer in firing position, the M795 HE projectile, a five-increment
MACS propelling charge and the rammer staff, modelled from published data, service photos and a detailed
scale-model reference.

Gun root (local +X = direction of fire, origin = ground under the trunnions, +Z up, +Y = left):
  * round turntable body low on the ground; two long forward stabilisers; two short, stout trails with wide
    ribbed scoop spades; one road wheel on a hydrogas arm each side, FORWARD beside the stabilisers;
    saddle arms with the gunner's two handwheels and sight (left) and the assistant gunner's handwheel (right);
  * cradle (object "Cradle", origin on the trunnion axis, local +X parallel to the bore): it pivots at its REAR
    end; two lower and two upper tubes, slotted side plates, an open trough behind the breech, recoil
    cylinders, accumulator and electronics on top; the bore axis runs BZ above the trunnion axis;
  * recoiling parts (object "Tube", child of the cradle): 155 mm tube, large muzzle brake with two round
    ports a side and the towing lug, breech ring 0.85 m ahead of the trunnions;
  * breech block carrier (object "Breech", hinged on top of the breech ring, swings up to open);
  * loading tray (objects "Tray" and "TrayArm"): a ribbed trough on the right that swings over into line.
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
TRAY_ARM = 0.475                                    # radius of the tray's swing
TRAY_PIVOT = np.array([C.S_BREECH - 0.02, -TRAY_ARM, C.BZ])   # cradle-frame point on the swing axis (parallel to the bore)
TRAY_OUT, TRAY_STOW, TRAY_IN = 0.0, math.pi / 2, math.pi     # swing angles: out to the right for loading, up for firing, in line with the bore
TRAY_LEN = 0.98
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
def _scoop(g, origin, td, tn, width=1.18):
    """Self-digging spade: a wide, shallow scoop with ribs inside, hinged on the end of the trail and lying back on the ground."""
    up = np.array([0, 0, 1.0]); origin = np.asarray(origin, float)
    us = np.linspace(0, 1, 9); prof = np.stack([0.02 + 0.92 * us, 0.16 - 0.50 * us ** 0.75], 1)       # (along td, z): from the hinge down to the lip
    m = len(prof)
    for th, flip in ((0.0, False), (-0.035, True)):                                                    # blade (two skins)
        V = np.array([origin + td * px + up * (pz + th) + tn * w for (px, pz) in prof for w in (-width / 2, width / 2)])
        g.add(V, grid_faces(m, 2, flip=flip))
    for w in np.linspace(-width / 2, width / 2, 5):                                                    # ribs standing on the blade, tapering to the lip
        hgt = 0.26 * (1 - us) ** 0.8 + 0.03
        V = np.array([origin + td * px + up * (pz + dz) + tn * (w + dw) for (px, pz), h in zip(prof, hgt) for dz in (0.0, h) for dw in (-0.02, 0.02)])
        F = []
        for k in range(m - 1):
            a0, b0 = 4 * k, 4 * (k + 1)
            F += [[a0, b0, b0 + 2, a0 + 2], [a0 + 1, a0 + 3, b0 + 3, b0 + 1], [a0 + 2, b0 + 2, b0 + 3, a0 + 3]]
        g.add(V, F)
    box_c = origin + td * 0.02 + up * 0.20                                                             # hinge beam across the top
    g.add(np.array([box_c + td * a + up * b + tn * c for a in (-0.07, 0.07) for b in (-0.08, 0.08) for c in (-width / 2, width / 2)]),
          [[0, 1, 3, 2], [4, 6, 7, 5], [0, 4, 5, 1], [2, 3, 7, 6], [0, 2, 6, 4], [1, 5, 7, 3]])

def build_gun(col=None, name="M777", elev=None):
    """Returns dict(root, cradle, tube, breech, tray, tray_arm, struts)."""
    M = materials(); elev = C.ELEV if elev is None else elev
    root = _root(name, col)
    cradle = _root("Cradle", col); cradle.parent = root; cradle.location = C.TRUN
    tube = _root("Tube", col); tube.parent = cradle; tube.location = (0, 0, C.BZ)
    SB, ST, SM, BZ = C.S_BREECH, C.S_TUBE, C.S_MUZZLE, C.BZ
    # --- recoiling parts (tube frame: bore axis = local X): breech ring, tube, big double-baffle muzzle brake with the towing lug
    gt = Geo(); gd = Geo(); gb = Geo(); gk0 = Geo()
    lathe(gt, [(SB, 0.094), (SB, 0.200), (SB + 0.03, 0.220), (SB + 0.42, 0.220), (SB + 0.50, 0.175), (2.10, 0.165), (3.20, 0.140), (4.40, 0.124), (ST, 0.114), (ST, 0.0775)], 56)
    lathe(gt, [(ST, 0.0775), (C.S_SEAT + 0.12, 0.0775), (C.S_SEAT + 0.04, 0.0900), (SB, 0.0920)], 48)                     # bore + powder chamber
    box(gt, (0.34, 0.36, 0.09), (SB + 0.22, 0.0, 0.232))
    for x, r_, w, h in ((SB + 0.02, 0.220, 0.04, 0.008), (SB + 0.40, 0.220, 0.04, 0.008), (3.25, 0.140, 0.06, 0.010), (ST - 0.25, 0.116, 0.05, 0.006)):
        ring(gt, x, r_, w, h, 56)
    lathe(gt, [(ST - 0.04, 0.114), (ST - 0.04, 0.160), (ST + 0.02, 0.215), (ST + 0.46, 0.215), (ST + 0.50, 0.195), (ST + 0.50, 0.085)], 8)   # brake body
    for sx in (ST + 0.135, ST + 0.355):                                                                                       # two large round ports each side
        for sy in (-1, 1):
            cyl(gk0, (sx, sy * 0.170, 0.0), (sx, sy * 0.203, 0.0), 0.088, 24); tmp = Geo()
            lathe(tmp, [(0.0, 0.088), (0.0, 0.104), (0.012, 0.104), (0.012, 0.088)], 24)
            Vr = np.concatenate(tmp.v)[:, [1, 0, 2]] * np.array([1, sy, 1]) + np.array([sx, sy * 0.196, 0.0])
            for k, fl in tmp.f.items():
                gt.add(Vr, np.concatenate(fl))
    box(gt, (0.30, 0.075, 0.11), (SM + 0.13, 0.0, -0.10)); ang = np.linspace(0, 2 * np.pi, 21)                                # towing lug with its eye
    pipe(gt, [(SM + 0.30 + 0.060 * math.cos(a), 0.0, -0.10 + 0.060 * math.sin(a)) for a in ang], [(0.038, 0.022)] * 21, 8)
    _finish(gt, "TubeSteel", col, M["HwGreen"], tube); _finish(gk0, "BrakePorts", col, M["HwDark"], tube)
    # --- breech block carrier (hinge on top of the breech ring; rotation about +Y swings it back and up)
    breech = _root("Breech", col); breech.parent = tube; breech.location = (SB, 0, 0.215)
    box(gd, (0.070, 0.330, 0.440), (-0.040, 0.0, -0.215))
    cyl(gd, (-0.01, 0, -0.215), (0.130, 0, -0.215), 0.0905, 40)
    for k in range(6):
        a = k * math.pi / 3
        cyl(gb, (0.02, 0.089 * math.cos(a), -0.215 + 0.089 * math.sin(a)), (0.12, 0.089 * math.cos(a), -0.215 + 0.089 * math.sin(a)), 0.012, 8)
    cyl(gd, (-0.085, 0, -0.215), (-0.040, 0, -0.215), 0.060, 24)                                                               # firing mechanism
    box(gd, (0.050, 0.120, 0.050), (-0.100, -0.110, -0.200)); cyl(gd, (-0.115, -0.170, -0.200), (-0.115, -0.200, -0.120), 0.010, 8)   # firing lever (right)
    box(gd, (0.090, 0.150, 0.090), (-0.050, 0.060, 0.040))                                                                     # primer feed mechanism
    cyl(gd, (-0.02, -0.19, 0.0), (-0.02, 0.19, 0.0), 0.028, 14)
    pipe(gd, [(-0.06, 0.175, -0.30), (-0.14, 0.215, -0.30), (-0.14, 0.215, -0.16)], [0.012] * 3, 8)                           # operating handle (left)
    _finish(gd, "BreechDark", col, M["HwDark"], breech); _finish(gb, "BreechBare", col, M["HwBare"], breech)
    # --- cradle (origin = trunnion axis): two lower tubes that carry the trunnions, two upper tubes, slotted side plates,
    #     the open trough behind the breech, front yoke, recoil cylinders, accumulator and electronics on top
    gc = Geo(); gr = Geo(); gk = Geo(); gs = Geo()
    for sy in (-1, 1):
        cyl(gc, (-0.18, sy * 0.30, 0.02), (3.18, sy * 0.30, 0.02), 0.072, 26)
        cyl(gc, (0.95, sy * 0.27, 0.50), (3.18, sy * 0.27, 0.50), 0.066, 26); cyl(gc, (3.18, sy * 0.27, 0.50), (3.26, sy * 0.27, 0.50), 0.066, 20, r1=0.030)
        cyl(gc, (0.95, sy * 0.27, 0.50), (0.88, sy * 0.27, 0.50), 0.066, 20, r1=0.035); cyl(gc, (3.18, sy * 0.30, 0.02), (3.26, sy * 0.30, 0.02), 0.072, 20, r1=0.035)
        box(gc, (2.20, 0.030, 0.40), (2.05, sy * 0.315, 0.26))                                           # side plate
        for k in range(7):
            box(gs, (0.170, 0.036, 0.115), (1.22 + 0.285 * k, sy * 0.317, 0.27))                         # lightening slots
        cyl(gc, (0.0, sy * 0.36, 0.0), (0.0, sy * 0.58, 0.0), 0.085, 24); box(gc, (0.30, 0.06, 0.26), (0.0, sy * 0.36, 0.03))        # trunnion
        cyl(gc, (1.30, sy * 0.105, 0.635), (3.00, sy * 0.105, 0.635), 0.050, 18); cyl(gr, (3.00, sy * 0.105, 0.635), (3.16, sy * 0.105, 0.635), 0.025, 12)   # recoil cylinders
    box(gc, (1.20, 0.60, 0.025), (0.42, 0.0, -0.035))                                                    # trough plate behind the breech
    for k in range(3):
        cyl(gs, (0.12 + 0.30 * k, 0, -0.050), (0.12 + 0.30 * k, 0, -0.020), 0.105, 20)                    # its oval holes
    cyl(gc, (-0.15, -0.30, 0.02), (-0.15, 0.30, 0.02), 0.060, 16)
    for sx in (0.95, 3.12):                                                                               # yokes
        box(gc, (0.08, 0.72, 0.05), (sx, 0, 0.575)); box(gc, (0.08, 0.72, 0.05), (sx, 0, -0.055))
        for sy in (-1, 1):
            box(gc, (0.08, 0.05, 0.60), (sx, sy * 0.345, 0.26))
    lathe(gc, [(3.02, 0.145), (3.02, 0.185), (3.24, 0.185), (3.24, 0.145)], 40, center=(0, 0, BZ))      # barrel collar
    cyl(gc, (1.10, 0.0, 0.73), (1.95, 0.0, 0.73), 0.072, 20)                                             # accumulator
    box(gc, (0.34, 0.30, 0.20), (2.30, -0.02, 0.76)); box(gc, (0.24, 0.22, 0.16), (2.72, 0.05, 0.74)); box(gk, (0.05, 0.26, 0.20), (1.02, -0.47, 0.72), rot=rot_z(-0.5))   # electronics, display
    pipe(gk, [(1.2, 0.36, 0.44), (1.8, 0.375, 0.47), (2.5, 0.37, 0.45), (3.0, 0.36, 0.44)], [0.012] * 4, 8)
    pipe(gk, [(1.2, -0.36, 0.40), (1.7, -0.38, 0.47), (2.3, -0.37, 0.52)], [0.012] * 3, 8)
    _finish(gc, "CradleGreen", col, M["HwGreen"], cradle); _finish(gr, "CradleRods", col, M["HwBare"], cradle); _finish(gk, "CradleHoses", col, M["HwDark"], cradle)
    _finish(gs, "CradleSlots", col, M["HwRubber"], cradle)
    # --- loading tray: ribbed trough carried on a swing arm on the right of the cradle (trough stays level; see set_tray)
    tray = _root("Tray", col); tray.parent = cradle
    gy = Geo(); a = np.linspace(math.radians(195), math.radians(345), 15); xs = np.array([0.0, -TRAY_LEN])
    for rr, flip in ((R_SHELL + 0.006, False), (R_SHELL + 0.016, True)):
        V = np.array([[x, rr * math.cos(t), rr * math.sin(t)] for x in xs for t in a]); gy.add(V, grid_faces(2, len(a), flip=flip))
    for x in np.linspace(-0.06, -TRAY_LEN + 0.06, 6):                                                    # ribs under the trough
        V = np.array([[x + dx, (R_SHELL + rr) * math.cos(t), (R_SHELL + rr) * math.sin(t)] for (dx, rr) in ((-0.012, 0.014), (-0.012, 0.034), (0.012, 0.034), (0.012, 0.014)) for t in a])
        gy.add(V, grid_faces(4, len(a)))
    _finish(gy, "TrayGreen", col, M["HwGreen"], tray)
    tray_arm = _root("TrayArm", col); tray_arm.parent = cradle; tray_arm.location = TRAY_PIVOT
    ga = Geo()
    for x in (-0.15, -0.75):
        beam(ga, (x, 0, 0), (x, -(TRAY_ARM - R_SHELL - 0.03), 0), (0.05, 0.05), up=(1, 0, 0))
    cyl(ga, (-0.05, 0, 0), (-0.85, 0, 0), 0.028, 14)
    _finish(ga, "TrayArmGreen", col, M["HwGreen"], tray_arm)
    # --- carriage: round turntable body, saddle arms, forward stabilisers, short trails with scoop spades, front road wheels
    gg = Geo(); gb2 = Geo(); gt2 = Geo(); grim = Geo(); gl = Geo(); gdk = Geo(); gtr = Geo()
    cyl(gg, (0.05, 0, 0.08), (0.05, 0, 0.30), 0.82, 56); cyl(gg, (0.05, 0, 0.30), (0.05, 0, 0.46), 0.74, 56); cyl(gg, (0.05, 0, 0.46), (0.05, 0, 0.50), 0.60, 48)
    for k in range(72):                                                                                   # traverse gear ring
        t = 2 * math.pi * k / 72; box(gdk, (0.030, 0.030, 0.055), (0.05 + 0.795 * math.cos(t), 0.795 * math.sin(t), 0.33), rot=rot_z(t))
    for sy in (-1, 1):
        # saddle arm up to the trunnion bearing
        P = [(-0.42, 0.48), (0.38, 0.48), (0.16, 1.02), (0.05, 1.08), (-0.05, 1.08), (-0.16, 1.02)]; n = len(P)
        V = np.array([[x, sy * 0.47, z] for x, z in P] + [[x, sy * 0.58, z] for x, z in P])
        gg.add(V, [[k, (k + 1) % n, n + (k + 1) % n, n + k] for k in range(n)]); gg.add(V, [list(range(n)), list(range(2 * n - 1, n - 1, -1))])
        cyl(gg, (0, sy * 0.57, C.TRUN[2]), (0, sy * 0.63, C.TRUN[2]), 0.12, 24)
        # forward stabiliser: long tapered leg with a small foot
        s0 = np.array([0.50, sy * 0.55, 0.29]); s1 = np.array([3.05, sy * 1.72, 0.14]); sd = (s1 - s0) / np.linalg.norm(s1 - s0); sn = np.cross([0, 0, 1.0], sd)
        beam(gg, s0, s1, (0.30, 0.34), (0.17, 0.15)); cyl(gg, s0 + [0, 0, -0.18], s0 + [0, 0, 0.18], 0.20, 18)
        box(gg, (0.40, 0.30, 0.045), s1 + sd * 0.05 + [0, 0, -0.10], rot=np.stack([sd, sn, [0, 0, 1.0]], 1))
        cyl(gdk, s0 + sd * 0.25 + [0, 0, 0.21], s0 + sd * 1.15 + [0, 0, 0.16], 0.040, 12)
        # trail: short and stout, with the scoop spade and its strut
        t0 = np.array([-0.50, sy * 0.55, 0.32]); t1 = np.array([-2.15, sy * 1.52, 0.34]); td = (t1 - t0) / np.linalg.norm(t1 - t0); tn = np.cross(td, [0, 0, 1.0])
        beam(gg, t0, t1, (0.50, 0.42), (0.42, 0.34)); cyl(gg, t0 + [0, 0, -0.22], t0 + [0, 0, 0.22], 0.26, 20)
        _scoop(gg, t1 + td * 0.06 + [0, 0, -0.02], td, tn)
        cyl(gdk, t1 - td * 0.80 + [0, 0, 0.24], t1 + td * 0.06 + [0, 0, 0.27], 0.045, 12)
        pipe(gdk, [t1 - td * 1.15 + tn * 0.26 + [0, 0, 0.0], t1 - td * 1.15 + tn * 0.35 + [0, 0, 0.0], t1 - td * 0.75 + tn * 0.35 + [0, 0, 0.0], t1 - td * 0.75 + tn * 0.26 + [0, 0, 0.0]], [0.014] * 4, 8)
        # road wheel on its hydrogas arm, beside the stabiliser, just clear of the ground
        c = np.array([1.12, sy * 1.26, 0.50]); wheel(gt2, grim, c)
        beam(gg, (0.45, sy * 0.80, 0.32), c - [0, sy * 0.19, 0], (0.17, 0.15), (0.14, 0.12)); cyl(gg, c - [0, sy * 0.24, 0], c - [0, sy * 0.10, 0], 0.090, 16)
        cyl(gdk, (0.30, sy * 0.84, 0.47), (0.85, sy * 1.00, 0.52), 0.060, 14)
        # tread plates on the body beside the saddle
        box(gtr, (0.55, 0.30, 0.025), (0.55, sy * 0.80, 0.435), rot=rot_z(sy * 0.42))
    cyl(gdk, (3.10, -1.74, 0.10), (3.10, -1.74, 0.40), 0.040, 12); cyl(gdk, (3.10, -1.74, 0.40), (3.10, -1.74, 2.60), 0.011, 8)          # antenna mast on the right stabiliser
    # gunner's side (left): two handwheels and the sight; assistant gunner's side (right): one handwheel
    box(gg, (0.20, 0.14, 0.24), (-0.34, 0.60, 0.86)); disc_wheel(gdk, (-0.50, 0.60, 0.86), (-1, 0, 0), 0.16, 0.012); cyl(gg, (-0.44, 0.60, 0.86), (-0.49, 0.60, 0.86), 0.024, 10)
    box(gg, (0.16, 0.14, 0.20), (-0.08, 0.66, 1.00)); disc_wheel(gdk, (-0.08, 0.80, 1.00), (0, 1, 0), 0.16, 0.012); cyl(gg, (-0.08, 0.72, 1.00), (-0.08, 0.79, 1.00), 0.024, 10)
    pipe(gg, [(0.02, 0.60, 1.08), (0.02, 0.64, 1.30), (0.02, 0.64, 1.46)], [0.042, 0.038, 0.034], 12)
    box(gdk, (0.13, 0.11, 0.16), (0.02, 0.64, 1.53)); cyl(gdk, (0.02, 0.64, 1.60), (0.02, 0.64, 1.72), 0.030, 12); cyl(gdk, (0.02, 0.64, 1.69), (-0.09, 0.64, 1.71), 0.024, 12)
    cyl(gl, (-0.092, 0.64, 1.71), (-0.095, 0.64, 1.71), 0.019, 12)
    box(gg, (0.18, 0.14, 0.24), (-0.10, -0.66, 0.98)); disc_wheel(gdk, (-0.10, -0.80, 0.98), (0, -1, 0), 0.16, 0.012); cyl(gg, (-0.10, -0.72, 0.98), (-0.10, -0.79, 0.98), 0.024, 10)
    for g_, nm, mt in ((gg, "CarriageGreen", "HwGreen"), (gb2, "CarriageRods", "HwBare"), (gt2, "Tyres", "HwRubber"), (grim, "Rims", "HwGreen"),
                       (gl, "SightLens", "HwLens"), (gdk, "CarriageDark", "HwDark"), (gtr, "TreadPlates", "HwDark")):
        if g_.v:
            _finish(g_, nm, col, M[mt], root)
    # balancing gear: a long strut each side from the back of the saddle arm up to the cradle (follows the elevation)
    struts = []
    for sy in (-1, 1):
        g1 = Geo(); cyl(g1, (0, 0, 0), (1, 0, 0), 0.052, 16); g2 = Geo(); cyl(g2, (0, 0, 0), (1, 0, 0), 0.028, 12)
        o1 = _finish(g1, "StrutBody", col, M["HwDark"], root); o2 = _finish(g2, "StrutRod", col, M["HwBare"], root)
        o1.rotation_mode = o2.rotation_mode = 'QUATERNION'; struts.append((sy, o1, o2))
    G = dict(root=root, cradle=cradle, tube=tube, breech=breech, tray=tray, tray_arm=tray_arm, struts=struts)
    set_elevation(G, elev); set_tray(G, TRAY_STOW)
    return G

def set_elevation(G, elev):
    q = aim_quat((math.cos(elev), 0, math.sin(elev))); G["cradle"].rotation_quaternion = q
    for sy, o1, o2 in G["struts"]:
        top = np.array(Vector(C.TRUN) + q @ Vector((1.90, sy * 0.40, 0.02))); bot = np.array([-0.30, sy * 0.66, 0.56]); d = top - bot; L_ = float(np.linalg.norm(d))
        qq = aim_quat(d / L_)
        o1.location = bot; o1.rotation_quaternion = qq; o1.scale = (min(1.25, L_ * 0.6), 1, 1)
        o2.location = bot; o2.rotation_quaternion = qq; o2.scale = (L_, 1, 1)

def tray_offset(phi):
    """Cradle-frame position of the trough's front-centre for swing angle phi (0 = out to the right, pi/2 = up, pi = in line)."""
    return np.array([C.S_BREECH - 0.02, TRAY_PIVOT[1] - TRAY_ARM * math.cos(phi), TRAY_PIVOT[2] + TRAY_ARM * math.sin(phi)])

def set_tray(G, phi):
    G["tray"].location = tray_offset(phi)
    G["tray_arm"].rotation_mode = 'QUATERNION'; G["tray_arm"].rotation_quaternion = Quaternion((1, 0, 0), -phi)

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

RAMMER_LEN = 3.60
def build_rammer(col=None, name="Rammer"):
    """Rammer staff: origin at the face of the head, +X = pushing direction (the pole runs back along -X)."""
    M = materials(); root = _root(name, col); g = Geo(); w = Geo()
    lathe(g, [(0.0, 0.0005), (0.0, 0.066), (-0.025, 0.070), (-0.075, 0.060), (-0.110, 0.030), (-0.20, 0.022)], 28)
    cyl(w, (-0.20, 0, 0), (-RAMMER_LEN, 0, 0), 0.019, 14)
    _finish(g, name + "Head", col, M["HwDark"], root); _finish(w, name + "Pole", col, M["HwWood"], root)
    return root
