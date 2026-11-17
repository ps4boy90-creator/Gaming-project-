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
TRAY_ARM = math.hypot(0.32, C.BZ - 0.02)            # radius of the tray's swing
TRAY_PIVOT = np.array([C.S_BREECH - 0.02, -0.32, 0.02])       # cradle-frame point on the swing axis: the right-hand slide of the cradle
TRAY_OUT = TRAY_STOW = math.radians(15.0)           # swing angles: lying outboard of the right slide (loading, and stowed for firing) ...
TRAY_IN = math.pi - math.atan2(C.BZ - 0.02, 0.32)   # ... and swung up and in, in line with the bore
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

def _put(g, tmp, R=None, t=(0, 0, 0)):
    """Add the contents of a scratch Geo to g after rotating (3x3) and translating."""
    V = np.concatenate(tmp.v); V = (V @ np.asarray(R).T if R is not None else V) + np.asarray(t, float)
    for k, fl in tmp.f.items():
        g.add(V, np.concatenate(fl))

def wheel(g_tire, g_rim, g_dark, c, r=0.44, w=0.29, yaw=0.0, outer=1.0):
    """Road wheel: tyre with shoulders and tread grooves, rim with hand holes, hub and lug nuts. Axis = local Y turned by yaw;
    outer = +1/-1 says which side carries the nuts (the other takes the swing arm)."""
    R = rot_z(yaw) @ np.array([[0, 1.0, 0], [1.0, 0, 0], [0, 0, 1.0]])                      # lathe X axis -> wheel axis
    tmp = Geo(); lathe(tmp, [(-w * 0.46, r * 0.63), (-w / 2, r * 0.74), (-w / 2, r * 0.88), (-w * 0.40, r * 0.975), (-w * 0.30, r), (w * 0.30, r), (w * 0.40, r * 0.975), (w / 2, r * 0.88), (w / 2, r * 0.74), (w * 0.46, r * 0.63)], 44)
    _put(g_tire, tmp, R, c)
    for k in range(5):                                                                        # tread grooves
        tmp = Geo(); x = -w * 0.26 + w * 0.13 * k; lathe(tmp, [(x - 0.007, r + 0.0005), (x - 0.007, r + 0.005), (x + 0.007, r + 0.005), (x + 0.007, r + 0.0005)], 44); _put(g_dark, tmp, R, c)
    o = outer; tmp = Geo()
    lathe(tmp, [(-w * 0.46, r * 0.635), (-w * 0.40, r * 0.60), (-w * 0.30, r * 0.56), (-w * 0.27, r * 0.24), (-w * 0.27, 0.001)], 36)
    lathe(tmp, [(w * 0.46, r * 0.635), (w * 0.40, r * 0.60), (w * 0.30, r * 0.56), (w * 0.27, r * 0.24), (w * 0.27, 0.001)], 36)
    cyl(tmp, (o * w * 0.27, 0, 0), (o * w * 0.40, 0, 0), r * 0.17, 16); cyl(tmp, (o * w * 0.27, 0, 0), (o * (w * 0.27 + 0.012), 0, 0), r * 0.36, 24)
    for k in range(8):
        a = 2 * math.pi * k / 8; cyl(tmp, (o * w * 0.27, r * 0.27 * math.cos(a), r * 0.27 * math.sin(a)), (o * (w * 0.27 + 0.034), r * 0.27 * math.cos(a), r * 0.27 * math.sin(a)), 0.017, 6)
    _put(g_rim, tmp, R, c)
    tmp = Geo()
    for k in range(8):                                                                        # hand holes
        a = 2 * math.pi * (k + 0.5) / 8
        for sg in (-1, 1):
            cyl(tmp, (sg * (w * 0.29 - 0.004), r * 0.455 * math.cos(a), r * 0.455 * math.sin(a)), (sg * (w * 0.29 + 0.006), r * 0.455 * math.cos(a), r * 0.455 * math.sin(a)), r * 0.062, 10)
    _put(g_dark, tmp, R, c)

def _bolts(g, pts, axis=(0, 0, 1), r=0.018, h=0.016):
    a = np.asarray(axis, float)
    for p_ in pts:
        cyl(g, np.asarray(p_, float), np.asarray(p_, float) + a * h, r, 6)

def holed_plate(g, c, eu, ev, hu, hv, r, th, cells=1, n=20):
    """Flat plate (centre c, in-plane axes eu/ev, half sizes hu/hv, thickness th) with one round hole of radius r in each of `cells`
    equal cells along eu."""
    c = np.asarray(c, float); eu = np.asarray(eu, float); ev = np.asarray(ev, float); en = np.cross(eu, ev); cu = hu / cells
    for k in range(cells):
        cc = c + eu * (-hu + cu * (2 * k + 1))
        ang = sorted(set([round(2 * math.pi * q / n, 6) for q in range(n)] + [round(math.atan2(sv * hv, su * cu) % (2 * math.pi), 6) for su in (-1, 1) for sv in (-1, 1)]))
        m = len(ang); ci = []; pe = []
        for a in ang:
            ca, sa = math.cos(a), math.sin(a); f = min(cu / max(abs(ca), 1e-9), hv / max(abs(sa), 1e-9))
            ci.append(eu * (r * ca) + ev * (r * sa)); pe.append(eu * (f * ca) + ev * (f * sa))
        V = np.array([cc + q + en * z for z in (-th / 2, th / 2) for q in ci + pe])
        F = []
        for q in range(m):
            q2 = (q + 1) % m
            F += [[2 * m + q, 2 * m + q2, 3 * m + q2, 3 * m + q], [q2, q, m + q, m + q2], [q, q2, 2 * m + q2, 2 * m + q], [m + q2, m + q, 3 * m + q, 3 * m + q2]]
        g.add(V, F)

def _scoop(g, hinge, td, tn, length=0.90, w0=0.86, w1=1.12):
    """Self-digging spade as on the M777: a broad curved scoop behind the trail, high at the hinge and sweeping down to a lip on the
    ground, with a rolled rim, low side walls and three curved ribs."""
    up = np.array([0, 0, 1.0]); o = np.asarray(hinge, float); o = np.array([o[0], o[1], 0.0])
    us = np.linspace(0, 1, 9); hw = (w0 + (w1 - w0) * us ** 0.8) / 2; m = len(us)
    zf = 0.02 + 0.50 * (1 - us) ** 2.1; xf = 0.04 + (length - 0.04) * us
    floor = np.array([o + td * xf[k] + up * zf[k] for k in range(m)])
    nrm = []
    for k in range(m):                                                                                # blade normal (up/back side)
        a, b = max(k - 1, 0), min(k + 1, m - 1); t = floor[b] - floor[a]; t /= np.linalg.norm(t); nn = np.cross(t, tn); nrm.append(nn if nn[2] > 0 else -nn)
    nrm = np.array(nrm)
    for th, flip in ((0.0, False), (-0.030, True)):                                                    # blade, two skins
        V = np.array([floor[k] + nrm[k] * th + tn * sgn * hw[k] for k in range(m) for sgn in (-1, 1)]); g.add(V, grid_faces(m, 2, flip=flip))
    V = np.array([floor[k] + nrm[k] * th + tn * sgn * hw[k] for sgn in (-1, 1) for k in (0, m - 1) for th in (0.0, -0.030)]); g.add(V, [[0, 1, 5, 4], [2, 6, 7, 3]])
    for sgn in (-1.0, 1.0):                                                                            # side walls with a rolled top edge
        wall = 0.10 + 0.10 * (1 - us)
        V = np.array([floor[k] + tn * sgn * (hw[k] - dw) + nrm[k] * dz for k in range(m) for (dw, dz) in ((0.0, -0.03), (0.0, wall[k]), (0.035, wall[k]), (0.035, 0.0))])
        g.add(V, grid_faces(m, 4, flip=sgn > 0))
    for q in (-0.48, 0.0, 0.48):                                                                       # three ribs
        rib = 0.05 + 0.15 * np.sin(np.pi * np.clip(us * 1.15, 0, 1)) ** 0.7
        V = np.array([floor[k] + tn * (q * hw[k] + dw) + nrm[k] * dz for k in range(m) for (dw, dz) in ((-0.016, 0.0), (-0.016, rib[k]), (0.016, rib[k]), (0.016, 0.0))])
        g.add(V, grid_faces(m, 4)); g.add(V[[0, 1, 2, 3]], [[0, 1, 2, 3]]); g.add(V[[-4, -3, -2, -1]], [[3, 2, 1, 0]])
    V = np.array([floor[-1] + tn * sgn * hw[-1] + nrm[-1] * dz + td * dx for sgn in (-1, 1) for (dx, dz) in ((0, -0.03), (0, 0.035), (0.05, 0.02), (0.05, -0.03))])
    g.add(V, [[0, 1, 5, 4], [1, 2, 6, 5], [2, 3, 7, 6], [3, 0, 4, 7], [0, 3, 2, 1], [4, 5, 6, 7]])     # cutting lip
    c = o + td * 0.0 + up * 0.36                                                                        # hinge beam across the top of the blade
    g.add(np.array([c + td * a + up * b + tn * q for a in (-0.07, 0.07) for b in (-0.20, 0.18) for q in (-w0 / 2, w0 / 2)]),
          [[0, 1, 3, 2], [4, 6, 7, 5], [0, 4, 5, 1], [2, 3, 7, 6], [0, 2, 6, 4], [1, 5, 7, 3]])

STAB_ANG = math.radians(47.0)                    # forward stabilisers, from the line of fire
TRAIL_ANG = math.radians(42.0)                   # trails, from the rear
TC = np.array([0.15, 0.0, 0.0])                    # centre of the turntable
WHEEL_C = np.array([1.60, 1.02, 0.46])             # left wheel centre (mirror for the right)

def build_gun(col=None, name="M777", elev=None):
    """Returns dict(root, cradle, tube, breech, tray, tray_arm, struts)."""
    M = materials(); elev = C.ELEV if elev is None else elev
    root = _root(name, col)
    cradle = _root("Cradle", col); cradle.parent = root; cradle.location = C.TRUN
    tube = _root("Tube", col); tube.parent = cradle; tube.location = (0, 0, C.BZ)
    SB, ST, SM, BZ = C.S_BREECH, C.S_TUBE, C.S_MUZZLE, C.BZ
    # ------------------------------------------------------------------ recoiling parts (tube frame: bore axis = local X)
    gt = Geo(); gd = Geo(); gb = Geo(); gk0 = Geo()
    lathe(gt, [(SB, 0.094), (SB, 0.205), (SB + 0.03, 0.228), (SB + 0.44, 0.228), (SB + 0.52, 0.182), (SB + 1.35, 0.176), (SB + 2.45, 0.160), (SB + 4.01, 0.150), (SB + 4.11, 0.128), (ST, 0.119), (ST, 0.0775)], 56)
    lathe(gt, [(ST, 0.0775), (C.S_SEAT + 0.12, 0.0775), (C.S_SEAT + 0.04, 0.0900), (SB, 0.0920)], 48)                     # bore + powder chamber
    box(gt, (0.36, 0.38, 0.10), (SB + 0.22, 0.0, 0.238))
    for x, r_, w, h in ((SB + 0.02, 0.228, 0.04, 0.008), (SB + 0.42, 0.228, 0.04, 0.008), (SB + 3.95, 0.150, 0.05, 0.006), (ST - 0.22, 0.121, 0.06, 0.008)):
        ring(gt, x, r_, w, h, 56)
    # muzzle brake: a box of plates behind a conical neck, two round ports through each side, baffles with the bore hole
    ex, ey, ez = np.eye(3); bx0 = ST + 0.02; bl = 0.50; hy = 0.215; hz = 0.200
    for sy in (-1, 1):
        holed_plate(gt, (bx0 + bl / 2, sy * hy, 0.0), ex, ez, bl / 2, hz, 0.098, 0.034, cells=2)
        for sx in (bx0 + bl * 0.25, bx0 + bl * 0.75):
            tmp = Geo(); lathe(tmp, [(0.0, 0.098), (0.0, 0.120), (0.012, 0.120), (0.012, 0.098)], 26); _put(gt, tmp, np.array([[0, 1.0, 0], [sy, 0, 0], [0, 0, 1.0]]), (sx, sy * (hy + 0.016), 0.0))
    for sz in (-1, 1):
        box(gt, (bl, 2 * hy + 0.034, 0.034), (bx0 + bl / 2, 0.0, sz * (hz + 0.017)))
    holed_plate(gt, (bx0, 0, 0), ey, ez, hy, hz, 0.120, 0.034); holed_plate(gt, (bx0 + bl / 2, 0, 0), ey, ez, hy, hz, 0.086, 0.030); holed_plate(gt, (bx0 + bl, 0, 0), ey, ez, hy, hz, 0.086, 0.034)
    lathe(gt, [(ST - 0.10, 0.119), (ST - 0.08, 0.150), (bx0, 0.185), (bx0, 0.119)], 40)
    V = np.array([[SM - 0.30, y, z] for y in (-0.085, 0.085) for z in (-0.275, -0.215)] + [[SM + 0.30, y, z] for y in (-0.050, 0.050) for z in (-0.262, -0.222)])
    gt.add(V, [[0, 1, 3, 2], [4, 6, 7, 5], [0, 4, 5, 1], [2, 3, 7, 6], [0, 2, 6, 4], [1, 5, 7, 3]])                            # towing tongue
    tmp = Geo(); lathe(tmp, [(-0.022, 0.045), (-0.022, 0.085), (0.022, 0.085), (0.022, 0.045)], 20); _put(gt, tmp, np.array([[0, 1.0, 0], [0, 0, 1.0], [1.0, 0, 0]]), (SM + 0.36, 0, -0.242))
    _finish(gt, "TubeSteel", col, M["HwGreen"], tube)
    # ------------------------------------------------------------------ breech block carrier (hinge on top of the breech ring)
    breech = _root("Breech", col); breech.parent = tube; breech.location = (SB, 0, 0.215)
    box(gd, (0.070, 0.340, 0.450), (-0.040, 0.0, -0.215))
    cyl(gd, (-0.01, 0, -0.215), (0.130, 0, -0.215), 0.0905, 40)
    for k in range(6):
        a = k * math.pi / 3
        cyl(gb, (0.02, 0.089 * math.cos(a), -0.215 + 0.089 * math.sin(a)), (0.12, 0.089 * math.cos(a), -0.215 + 0.089 * math.sin(a)), 0.012, 8)
    lathe(gd, [(-0.075, 0.001), (-0.075, 0.095), (-0.085, 0.105), (-0.095, 0.095), (-0.105, 0.105), (-0.115, 0.095), (-0.125, 0.105), (-0.135, 0.095), (-0.150, 0.085), (-0.150, 0.001)], 32,
          center=(0, 0, -0.215))                                                                                               # finned firing mechanism
    box(gd, (0.050, 0.150, 0.050), (-0.100, -0.150, -0.200)); cyl(gd, (-0.115, -0.215, -0.200), (-0.115, -0.250, -0.130), 0.010, 8)   # firing lever (right)
    box(gd, (0.090, 0.150, 0.090), (-0.050, 0.060, 0.040))                                                                     # primer feed mechanism
    cyl(gd, (-0.02, -0.19, 0.0), (-0.02, 0.19, 0.0), 0.028, 14)
    pipe(gd, [(-0.06, 0.175, -0.30), (-0.14, 0.215, -0.30), (-0.14, 0.215, -0.16)], [0.012] * 3, 8)                           # operating handle (left)
    _finish(gd, "BreechDark", col, M["HwDark"], breech); _finish(gb, "BreechBare", col, M["HwBare"], breech)
    # ------------------------------------------------------------------ cradle (origin = trunnion axis)
    gc = Geo(); gr = Geo(); gk = Geo(); gs = Geo()
    for sy in (-1, 1):
        # lower side cylinder: carries the trunnion, ribbed section at the rear, fat sleeve along the middle
        cyl(gc, (-0.22, sy * 0.32, 0.02), (3.18, sy * 0.32, 0.02), 0.086, 26); cyl(gc, (0.34, sy * 0.32, 0.02), (1.80, sy * 0.32, 0.02), 0.104, 28)
        cyl(gc, (-0.22, sy * 0.32, 0.02), (-0.30, sy * 0.32, 0.02), 0.086, 20, r1=0.050); cyl(gc, (3.18, sy * 0.32, 0.02), (3.30, sy * 0.32, 0.02), 0.086, 20, r1=0.040); cyl(gc, (3.30, sy * 0.32, 0.02), (3.34, sy * 0.32, 0.02), 0.022, 8)
        for k in range(9):
            ring(gk, 0.03 + 0.033 * k, 0.088, 0.016, 0.010, 24, center=(0, sy * 0.32, 0.02))
        # upper tube with domed caps
        cyl(gc, (0.98, sy * 0.29, 0.53), (3.18, sy * 0.29, 0.53), 0.080, 26); cyl(gc, (3.18, sy * 0.29, 0.53), (3.30, sy * 0.29, 0.53), 0.080, 20, r1=0.036); cyl(gc, (3.30, sy * 0.29, 0.53), (3.34, sy * 0.29, 0.53), 0.020, 8)
        cyl(gc, (0.98, sy * 0.29, 0.53), (0.89, sy * 0.29, 0.53), 0.080, 20, r1=0.040)
        # windowed box beam between them, with the buffer springs showing through
        box(gc, (2.10, 0.120, 0.300), (2.08, sy * 0.365, 0.275))
        for k in range(6):
            box(gs, (0.150 + (0.07 if k == 5 else 0), 0.126, 0.110), (1.38 + 0.300 * k, sy * 0.367, 0.275))
            for q in range(4):
                ring(gb, 1.325 + 0.300 * k + 0.036 * q, 0.030, 0.014, 0.012, 12, center=(0, sy * 0.415, 0.275))
        for sx in (1.56, 2.46):                                                                          # strap brackets
            box(gc, (0.050, 0.025, 0.70), (sx, sy * 0.435, 0.275)); _bolts(gk, [(sx, sy * 0.447, 0.275 + dz) for dz in (-0.27, -0.13, 0.13, 0.27)], axis=(0, sy, 0))
        cyl(gc, (0.0, sy * 0.38, 0.0), (0.0, sy * 0.60, 0.0), 0.088, 24); box(gc, (0.40, 0.07, 0.34), (0.02, sy * 0.425, 0.00)); _bolts(gk, [(0.11 * math.cos(a_), sy * 0.46, 0.11 * math.sin(a_)) for a_ in np.linspace(0, 2 * math.pi, 9)[:-1]], axis=(0, sy, 0), r=0.014)   # trunnion + its lug
    arch = [(-0.06 + 0.24 * math.sin(a_), -0.22 * math.cos(a_)) for a_ in np.linspace(0, math.pi, 13)]                   # trough plate, arched at the rear
    strip = [(-0.26, -0.30), (-0.26, -0.22)] + arch + [(-0.26, 0.22), (-0.26, 0.30)]
    for z, flip in ((-0.055, True), (-0.025, False)):
        P = [(x, y) for x, y in strip]; Q = [(1.06, y) for x, y in strip]
        Vz = np.array([[x, y, z] for x, y in P] + [[x, y, z] for x, y in Q]); gc.add(Vz, grid_faces(2, len(P), flip=flip))
    Vw = np.array([[x, y, z] for x, y in strip for z in (-0.055, -0.025)]); gc.add(Vw, grid_faces(len(strip), 2))
    _bolts(gk, [(0.02 + 0.15 * k, sy * 0.26, -0.026) for k in range(8) for sy in (-1, 1)])
    cyl(gc, (-0.20, -0.32, 0.02), (-0.20, -0.22, 0.02), 0.050, 14); cyl(gc, (-0.20, 0.22, 0.02), (-0.20, 0.32, 0.02), 0.050, 14)
    # yokes: rear frame at the breech, front plate with the bolted barrel collar
    for sy in (-1, 1):
        box(gc, (0.07, 0.07, 0.66), (0.98, sy * 0.385, 0.275))
    box(gc, (0.07, 0.84, 0.06), (0.98, 0, 0.61)); box(gc, (0.07, 0.84, 0.06), (0.98, 0, -0.06))
    box(gc, (0.07, 0.90, 0.80), (3.15, 0, 0.275)); lathe(gc, [(3.10, 0.150), (3.10, 0.235), (3.22, 0.235), (3.25, 0.205), (3.30, 0.195), (3.30, 0.150)], 44, center=(0, 0, BZ))
    _bolts(gk, [(3.22, 0.215 * math.cos(a), BZ + 0.215 * math.sin(a)) for a in np.linspace(0, 2 * math.pi, 13)[:-1]], axis=(1, 0, 0), r=0.016)
    # on top: the recuperator cylinder, a slimmer one beside it, electronics boxes with their cables, the chief's display
    cyl(gc, (1.22, 0.0, 0.675), (2.85, 0.0, 0.675), 0.088, 26); cyl(gc, (2.85, 0.0, 0.675), (3.10, 0.0, 0.640), 0.045, 16)
    for k in range(5):
        ring(gk, 1.25 + 0.035 * k, 0.090, 0.016, 0.012, 26, center=(0, 0, 0.675))
    cyl(gc, (1.45, -0.16, 0.655), (2.95, -0.16, 0.655), 0.045, 16); cyl(gr, (2.95, -0.16, 0.655), (3.10, -0.16, 0.655), 0.022, 10)
    box(gc, (0.40, 0.30, 0.24), (2.20, 0.25, 0.80)); _bolts(gk, [(2.20 + dx, 0.25 + dy, 0.92) for dx in (-0.17, 0.17) for dy in (-0.12, 0.12)])
    box(gc, (0.22, 0.20, 0.17), (1.72, -0.30, 0.74)); box(gc, (0.20, 0.16, 0.12), (1.62, 0.26, 0.70))
    for q in range(4):
        pipe(gk, [(2.00, 0.18 + 0.03 * q, 0.74), (1.80, 0.20 + 0.03 * q, 0.66), (1.50, 0.33, 0.60 - 0.02 * q), (1.20, 0.40, 0.50)], [0.011] * 4, 6)
    box(gk, (0.05, 0.28, 0.21), (1.08, -0.50, 0.74), rot=rot_z(-0.5)); pipe(gc, [(1.15, -0.36, 0.52), (1.10, -0.46, 0.64)], [0.025, 0.025], 8)
    # stowed ribbed panel along the lower left of the cradle
    tmp = Geo(); box(tmp, (1.02, 0.050, 0.46), (0, 0, 0))
    for k in range(7):
        box(tmp, (0.022, 0.030, 0.44), (-0.45 + 0.15 * k, 0.038, 0))
    for sz in (-1, 1):
        box(tmp, (1.02, 0.030, 0.022), (0, 0.038, sz * 0.22))
    _put(gc, tmp, rot_x(math.radians(-28)), (1.62, 0.455, -0.10))
    pipe(gk, [(1.25, 0.36, 0.44), (1.9, 0.44, 0.47), (2.6, 0.44, 0.45), (3.05, 0.40, 0.44)], [0.012] * 4, 8)
    pipe(gk, [(1.25, -0.40, 0.42), (1.8, -0.43, 0.46), (2.4, -0.42, 0.50)], [0.012] * 3, 8)
    # everything ahead of the trough was laid out with the breech 0.85 m ahead of the trunnions; slide it forward to the real breech
    # position (the slides, sleeves and trough plate simply get longer)
    DXC = SB - 0.85
    for g_ in (gc, gr, gk, gs, gb):
        for arr in g_.v:
            arr[:, 0] += DXC * (arr[:, 0] >= 0.885)
    for k in range(3):
        tmp = Geo(); cyl(tmp, (0, 0, -0.058), (0, 0, -0.022), 0.085, 22); _put(gs, tmp, np.diag([1.40, 1.0, 1.0]), (0.36 + 0.305 * k, 0, 0))
    _finish(gc, "CradleGreen", col, M["HwGreen"], cradle); _finish(gr, "CradleRods", col, M["HwBare"], cradle); _finish(gk, "CradleFittings", col, M["HwDark"], cradle)
    _finish(gs, "CradleSlots", col, M["HwRubber"], cradle); _finish(gb, "CradleSprings", col, M["HwBare"], cradle) if False else None
    # ------------------------------------------------------------------ loading tray (right): channel trough on a swing arm, stays level
    tray = _root("Tray", col); tray.parent = cradle
    gy = Geo(); a = np.linspace(math.radians(195), math.radians(345), 15); xs = np.array([0.0, -TRAY_LEN])
    for rr, flip in ((R_SHELL + 0.006, False), (R_SHELL + 0.016, True)):
        V = np.array([[x, rr * math.cos(t), rr * math.sin(t)] for x in xs for t in a]); gy.add(V, grid_faces(2, len(a), flip=flip))
    for x in np.linspace(-0.06, -TRAY_LEN + 0.06, 6):
        V = np.array([[x + dx, (R_SHELL + rr) * math.cos(t), (R_SHELL + rr) * math.sin(t)] for (dx, rr) in ((-0.012, 0.014), (-0.012, 0.034), (0.012, 0.034), (0.012, 0.014)) for t in a])
        gy.add(V, grid_faces(4, len(a)))
    for sy in (-1, 1):
        box(gy, (TRAY_LEN, 0.016, 0.055), (-TRAY_LEN / 2, sy * (R_SHELL + 0.012), 0.020))
    _finish(gy, "TrayGreen", col, M["HwGreen"], tray)
    tray_arm = _root("TrayArm", col); tray_arm.parent = cradle; tray_arm.location = TRAY_PIVOT
    ga = Geo()
    for x in (-0.15, -0.75):
        beam(ga, (x, 0, 0), (x, -(TRAY_ARM - R_SHELL - 0.03), 0), (0.05, 0.05), up=(1, 0, 0))
    cyl(ga, (-0.05, 0, 0), (-0.85, 0, 0), 0.028, 14)
    _finish(ga, "TrayArmGreen", col, M["HwGreen"], tray_arm)
    # ------------------------------------------------------------------ carriage
    gg = Geo(); gb2 = Geo(); gt2 = Geo(); grim = Geo(); gl = Geo(); gdk = Geo(); gtr = Geo()
    up = np.array([0, 0, 1.0])
    # turntable: base disc, toothed traverse ring, deck with bolt circle and hatch
    lathe_z = lambda g_, prof, segs=64: _put(g_, _lz(prof, segs), None, TC)
    def _lz(prof, segs):
        tmp = Geo(); lathe(tmp, [(z, r) for (r, z) in prof], segs); V = np.concatenate(tmp.v)[:, [1, 2, 0]]; t2 = Geo()
        for k, fl in tmp.f.items():
            t2.add(V, np.concatenate(fl))
        return t2
    lathe_z(gg, [(0.001, 0.06), (0.86, 0.06), (0.93, 0.12), (0.93, 0.30), (0.90, 0.30), (0.90, 0.375), (0.84, 0.375), (0.84, 0.445), (0.001, 0.445)])
    for k in range(96):
        t = 2 * math.pi * k / 96; box(gdk, (0.028, 0.026, 0.060), TC + [0.905 * math.cos(t), 0.905 * math.sin(t), 0.338], rot=rot_z(t))
    _bolts(gdk, [TC + [0.78 * math.cos(t), 0.78 * math.sin(t), 0.445] for t in np.linspace(0, 2 * math.pi, 29)[:-1]], r=0.016)
    _bolts(gdk, [TC + [0.935 * math.cos(t), 0.935 * math.sin(t), 0.21] for t in np.linspace(0, 2 * math.pi, 25)[:-1] if abs(math.sin(2 * t)) < 0.75], axis=(0, 0, 0), r=0.0) if False else None
    box(gg, (0.30, 0.22, 0.015), TC + [-0.52, 0.10, 0.452])
    for k in range(3):                                                                                  # lugs round the base of the turntable
        box(gg, (0.20, 0.10, 0.12), TC + [-0.93 * math.cos(0.5 * (k - 1)), 0.93 * math.sin(0.5 * (k - 1)), 0.14], rot=rot_z(math.pi - 0.5 * (k - 1)))
    for sy in (-1, 1):
        # --- saddle column: side plate up to the trunnion bearing, a post behind it carrying the balancing gear
        P = [(-0.34, 0.445), (0.36, 0.445), (0.22, 0.80), (0.13, 1.07), (0.04, 1.12), (-0.06, 1.12), (-0.15, 1.07), (-0.20, 0.90), (-0.34, 0.80)]; n = len(P)
        V = np.array([[x, sy * 0.47, z] for x, z in P] + [[x, sy * 0.60, z] for x, z in P])
        gg.add(V, [[k, (k + 1) % n, n + (k + 1) % n, n + k] for k in range(n)]); gg.add(V, [list(range(n)), list(range(2 * n - 1, n - 1, -1))])
        cyl(gg, (0, sy * 0.60, C.TRUN[2]), (0, sy * 0.66, C.TRUN[2]), 0.130, 28); _bolts(gdk, [(0.10 * math.cos(a_), sy * 0.66, C.TRUN[2] + 0.10 * math.sin(a_)) for a_ in np.linspace(0, 2 * math.pi, 9)[:-1]], axis=(0, sy, 0), r=0.013)
        box(gg, (0.56, 0.22, 0.10), (0.02, sy * 0.53, 0.49))
        box(gg, (0.13, 0.11, 0.32), (-0.27, sy * 0.61, 0.93)); cyl(gg, (-0.27, sy * 0.52, 1.02), (-0.27, sy * 0.68, 1.02), 0.055, 14)
        for q in (0.60, 0.72, 0.84):
            box(gdk, (0.012, 0.135, 0.07), (0.27 - (q - 0.445) * 0.39, sy * 0.535, q), rot=rot_y(-0.37))
        # --- forward stabiliser: fixed arm from the body, a big vertical hinge with a hex-headed pin, then the long tapering leg
        sd = np.array([math.cos(STAB_ANG), sy * math.sin(STAB_ANG), 0.0]); sn = np.cross(up, sd); Rs = np.stack([sd, sn, up], 1)
        beam(gg, TC + sd * 0.62 + up * 0.26, TC + sd * 1.26 + up * 0.27, (0.60, 0.36), (0.42, 0.34))
        hg = TC + sd * 1.32 + up * 0.27
        cyl(gg, hg - up * 0.22, hg + up * 0.22, 0.205, 24); cyl(gdk, hg + up * 0.22, hg + up * 0.265, 0.095, 6); cyl(gdk, hg - up * 0.25, hg - up * 0.22, 0.075, 6)
        s1 = TC + sd * 3.15 + up * 0.105; sm = hg + (s1 - hg) * 0.40 + up * 0.035
        beam(gg, hg + sd * 0.10, sm, (0.36, 0.36), (0.25, 0.30)); beam(gg, sm, s1, (0.25, 0.30), (0.19, 0.13))
        box(gg, (0.44, 0.36, 0.045), s1 + sd * 0.06 - up * 0.083, rot=Rs); box(gg, (0.07, 0.36, 0.15), s1 + sd * 0.26 - up * 0.045, rot=Rs)
        for q, w_, h_ in ((0.52, 0.34, 0.15), (0.98, 0.30, 0.12), (1.42, 0.24, 0.08)):                       # lightening pockets in the leg sides
            pc_ = hg + (s1 - hg) * (q / 1.83)
            for sg in (-1, 1):
                box(gdk, (w_, 0.012, h_), pc_ + sn * sg * (0.172 - 0.045 * q) + up * 0.02, rot=Rs)
        cyl(gdk, hg + sd * 0.16 + up * 0.215, hg + sd * 0.86 + up * 0.215, 0.040, 12); cyl(gb2, hg + sd * 0.86 + up * 0.215, hg + sd * 1.16 + up * 0.20, 0.020, 10)
        box(gtr, (0.50, 0.40, 0.022), TC + sd * 0.90 + up * 0.452, rot=Rs)                                    # perforated step on the arm
        cyl(gg, TC + sd * 0.90 + up * 0.30, TC + sd * 0.90 + up * 0.445, 0.05, 10)
        # --- trail: fixed arm, knuckle, short stout box, and the spade behind it
        td = np.array([-math.cos(TRAIL_ANG), sy * math.sin(TRAIL_ANG), 0.0]); tn = np.cross(td, up); Rt = np.stack([td, tn, up], 1)
        beam(gg, TC + td * 0.62 + up * 0.27, TC + td * 1.10 + up * 0.29, (0.66, 0.38), (0.52, 0.40))
        kn = TC + td * 1.16 + up * 0.30
        cyl(gg, kn - up * 0.23, kn + up * 0.23, 0.250, 24); cyl(gdk, kn + up * 0.23, kn + up * 0.275, 0.105, 6)
        t1 = TC + td * 1.74 + up * 0.33
        beam(gg, kn + td * 0.10, t1, (0.50, 0.44), (0.46, 0.40))
        for q in (0.24, 0.46):
            box(gg, (0.13, 0.32, 0.07), kn + td * q + up * 0.245, rot=Rt); _bolts(gdk, [kn + td * q + tn * sg * 0.10 + up * 0.28 for sg in (-1, 1)], r=0.022)
            box(gdk, (0.15, 0.012, 0.17), kn + td * (q + 0.01) + tn * 0.252 + up * 0.0, rot=Rt); box(gdk, (0.15, 0.012, 0.17), kn + td * (q + 0.01) - tn * 0.252 + up * 0.0, rot=Rt)
        for sg in (-1, 1):                                                                                    # lifting handles
            pipe(gdk, [kn + td * 0.20 + tn * sg * 0.25 + up * 0.14, kn + td * 0.20 + tn * sg * 0.36 + up * 0.14, kn + td * 0.50 + tn * sg * 0.36 + up * 0.14, kn + td * 0.50 + tn * sg * 0.25 + up * 0.14], [0.016] * 4, 8)
        box(gtr, (0.44, 0.38, 0.022), TC + td * 0.86 + up * 0.475, rot=Rt)
        hinge = TC + td * 1.86
        _scoop(gg, hinge, td, tn)
        for sg in (-1, 1):                                                                                    # hinge lugs between trail and spade
            box(gg, (0.26, 0.07, 0.30), t1 + td * 0.06 + tn * sg * 0.19 + up * 0.02, rot=Rt)
        cyl(gdk, t1 + td * 0.10 - tn * 0.30 + up * 0.04, t1 + td * 0.10 + tn * 0.30 + up * 0.04, 0.035, 12)
        cyl(gdk, kn + td * 0.16 + up * 0.31, hinge + td * 0.02 + up * 0.56, 0.045, 12); cyl(gb2, kn + td * 0.45 + up * 0.40, hinge + td * 0.30 + up * 0.36, 0.022, 8)
        pipe(gdk, [hinge + td * 0.02 + tn * 0.24 + up * 0.50, hinge + td * 0.02 + tn * 0.24 + up * 0.74, hinge + td * 0.02 - tn * 0.24 + up * 0.74, hinge + td * 0.02 - tn * 0.24 + up * 0.50], [0.018] * 4, 8)
        # --- road wheel: on a swing arm from the front of the body, ahead of the stabiliser
        c = WHEEL_C * np.array([1, sy, 1]); yaw = sy * math.radians(14.0)
        wheel(gt2, grim, gdk, c, yaw=yaw, outer=sy)
        ax = rot_z(yaw) @ np.array([0, 1.0, 0]); hub = c - ax * sy * 0.20; a0 = TC + np.array([0.86, sy * 0.30, 0.44])
        beam(gg, a0, hub, (0.20, 0.18), (0.16, 0.15)); cyl(gg, hub - ax * 0.08, hub + ax * 0.08, 0.12, 18); cyl(gg, a0 - ax * 0.10, a0 + ax * 0.10, 0.14, 18)
        cyl(gg, hub, c, 0.07, 14)
        cyl(gdk, TC + [0.58, sy * 0.50, 0.56], a0 + (hub - a0) * 0.50 + up * 0.11, 0.058, 14); cyl(gb2, a0 + (hub - a0) * 0.50 + up * 0.11, a0 + (hub - a0) * 0.78 + up * 0.09, 0.028, 10)
    # antenna mast on the right stabiliser: spring base and whip
    mp = TC + np.array([math.cos(STAB_ANG), -math.sin(STAB_ANG), 0]) * 3.13 + up * 0.17
    cyl(gdk, mp, mp + up * 0.16, 0.055, 12)
    for k in range(7):
        cyl(gdk, mp + up * (0.17 + 0.036 * k), mp + up * (0.19 + 0.036 * k), 0.038 - 0.001 * k, 10)
    cyl(gdk, mp + up * 0.16, mp + up * 0.44, 0.026, 10); cyl(gdk, mp + up * 0.44, mp + up * 0.60, 0.022, 10); cyl(gdk, mp + up * 0.60, mp + up * 3.05, 0.011, 8); cyl(gdk, mp + up * 3.05, mp + up * 3.08, 0.020, 8)
    # gunner's side (left): sight on its stalk, one handwheel out to the side on a long shaft, one low at the rear on a vertical gearbox
    box(gg, (0.26, 0.20, 0.30), (-0.12, 0.70, 0.84)); ax_a = np.array([-0.45, 0.89, 0.0]); ax_a /= np.linalg.norm(ax_a)
    pa = np.array([-0.16, 0.78, 0.88]); cyl(gg, pa, pa + ax_a * 0.36, 0.026, 10); disc_wheel(gdk, pa + ax_a * 0.37, ax_a, 0.18, 0.017)
    gbx = TC + np.array([-0.70, 0.56, 0.0]); cyl(gg, gbx + up * 0.30, gbx + up * 0.74, 0.075, 16); cyl(gg, gbx + up * 0.74, gbx + up * 0.80, 0.055, 12)
    ax_b = np.array([-0.94, 0.20, 0.28]); ax_b /= np.linalg.norm(ax_b); pb = gbx + up * 0.66
    cyl(gg, pb, pb + ax_b * 0.20, 0.026, 10); disc_wheel(gdk, pb + ax_b * 0.21, ax_b, 0.18, 0.017)
    box(gg, (0.16, 0.20, 0.24), (-0.42, 0.52, 0.70)); box(gdk, (0.12, 0.17, 0.20), (-0.50, 0.38, 0.86))
    for k in range(5):
        box(gg, (0.125, 0.012, 0.20), (-0.50, 0.31 + 0.035 * k, 0.86))
    pipe(gg, [(0.02, 0.62, 1.10), (0.04, 0.70, 1.26), (0.04, 0.72, 1.44)], [0.050, 0.044, 0.038], 12)
    box(gdk, (0.17, 0.14, 0.15), (0.04, 0.72, 1.51)); box(gdk, (0.11, 0.11, 0.13), (0.11, 0.81, 1.46)); cyl(gdk, (0.04, 0.72, 1.58), (0.04, 0.72, 1.74), 0.034, 12)
    box(gdk, (0.10, 0.09, 0.09), (0.04, 0.72, 1.76)); cyl(gdk, (0.04, 0.72, 1.76), (-0.10, 0.72, 1.78), 0.027, 12); cyl(gl, (-0.102, 0.72, 1.78), (-0.105, 0.72, 1.78), 0.021, 12)
    cyl(gdk, (0.00, 0.80, 1.52), (0.00, 0.88, 1.52), 0.024, 10); cyl(gdk, (-0.04, 0.66, 1.50), (-0.14, 0.66, 1.53), 0.020, 10)
    # assistant gunner's side (right): gearbox, handwheel, bolted flange block
    box(gg, (0.28, 0.22, 0.26), (-0.12, -0.71, 0.80)); ax_c = np.array([-0.60, -0.80, 0.0]); pc = np.array([-0.18, -0.80, 0.84])
    cyl(gg, pc, pc + ax_c * 0.30, 0.026, 10); disc_wheel(gdk, pc + ax_c * 0.31, ax_c, 0.18, 0.017)
    box(gg, (0.17, 0.17, 0.17), (0.12, -0.80, 0.78)); _bolts(gdk, [(0.12 + dx, -0.885, 0.78 + dz) for dx in (-0.055, 0.055) for dz in (-0.055, 0.055)], axis=(0, -1, 0), r=0.015); cyl(gdk, (0.12, -0.886, 0.78), (0.12, -0.892, 0.78), 0.04, 12)
    for g_, nm, mt in ((gg, "CarriageGreen", "HwGreen"), (gb2, "CarriageRods", "HwBare"), (gt2, "Tyres", "HwRubber"), (grim, "Rims", "HwGreen"),
                       (gl, "SightLens", "HwLens"), (gdk, "CarriageDark", "HwDark"), (gtr, "TreadPlates", "HwDark")):
        if g_.v:
            _finish(g_, nm, col, M[mt], root)
    # balancing gear: an equilibrator each side (cylinder on the cradle, bellows and rod back to the saddle post), plus the long
    # spring rod on the left; all follow the elevation
    struts = []
    for sy in (-1, 1):
        g1 = Geo(); cyl(g1, (0, 0, 0), (0.80, 0, 0), 0.070, 20); cyl(g1, (0, 0, 0), (-0.06, 0, 0), 0.070, 18, r1=0.035); cyl(g1, (0.80, 0, 0), (0.86, 0, 0), 0.050, 14)
        for k in range(8):
            ring(g1, 0.88 + 0.034 * k, 0.040, 0.020, 0.014, 16)
        g2 = Geo(); cyl(g2, (0, 0, 0), (1, 0, 0), 0.026, 12)
        o1 = _finish(g1, "EquilBody", col, M["HwGreen"], root); o2 = _finish(g2, "EquilRod", col, M["HwBare"], root)
        struts.append(dict(body=o1, rod=o2, bot=np.array([-0.27, sy * 0.59, 1.02]), top=np.array([1.42 + SB - 0.85, sy * 0.505, 0.10])))
    g1 = Geo()
    for k in range(14):
        ring(g1, 0.03 + 0.03 * k, 0.026, 0.016, 0.012, 12)
    g2 = Geo(); cyl(g2, (0, 0, 0), (1, 0, 0), 0.014, 8)
    o1 = _finish(g1, "RodSpring", col, M["HwBare"], root); o2 = _finish(g2, "RodLong", col, M["HwDark"], root)
    struts.append(dict(body=o1, rod=o2, bot=np.array([-0.46, 0.76, 0.62]), top=np.array([1.86 + SB - 0.85, 0.60, -0.04])))
    for st in struts:
        st["body"].rotation_mode = st["rod"].rotation_mode = 'QUATERNION'
    G = dict(root=root, cradle=cradle, tube=tube, breech=breech, tray=tray, tray_arm=tray_arm, struts=struts)
    set_elevation(G, elev); set_tray(G, TRAY_STOW)
    return G

def set_elevation(G, elev):
    q = aim_quat((math.cos(elev), 0, math.sin(elev))); G["cradle"].rotation_quaternion = q
    for st in G["struts"]:
        top = np.array(Vector(C.TRUN) + q @ Vector(st["top"])); d = st["bot"] - top; L_ = float(np.linalg.norm(d)); qq = aim_quat(d / L_)
        st["body"].location = top; st["body"].rotation_quaternion = qq
        st["rod"].location = top; st["rod"].rotation_quaternion = qq; st["rod"].scale = (L_, 1, 1)

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

RAMMER_LEN = 3.95
def build_rammer(col=None, name="Rammer"):
    """Rammer staff: origin at the face of the head, +X = pushing direction (the pole runs back along -X)."""
    M = materials(); root = _root(name, col); g = Geo(); w = Geo()
    lathe(g, [(0.0, 0.0005), (0.0, 0.066), (-0.025, 0.070), (-0.075, 0.060), (-0.110, 0.030), (-0.20, 0.022)], 28)
    cyl(w, (-0.20, 0, 0), (-RAMMER_LEN, 0, 0), 0.019, 14)
    _finish(g, name + "Head", col, M["HwDark"], root); _finish(w, name + "Pole", col, M["HwWood"], root)
    return root
