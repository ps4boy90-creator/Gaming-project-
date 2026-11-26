"""Northrop B-2A Spirit with its two weapons bays, each holding one GBU-57.

Aircraft frame: nose towards +X, left +Y, up +Z; the planform is laid out by x (metres aft of the nose apex), X = X0 - x.
From sources (USAF fact sheet): 52.4 m span, 21.0 m long, 5.18 m high (on its wheels), leading edges swept 33
degrees, a "double W" trailing edge whose edges are parallel to the leading edges, four engines buried in the wing
with intakes and exhausts on top, two weapons bays side by side under the middle; one GBU-57 in each.
The break points of the trailing edge, the thickness along the span, the humps over the crew and the engines, the
intake and exhaust shapes, the windows and the size and place of the bays are estimated from photographs and
published three-view drawings.  The landing gear is up; no panel lines or markings.
"""
import bpy, math, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "grenade-explosion")); sys.path.insert(0, os.path.join(HERE, "..", "reaper-hellfire")); sys.path.insert(0, HERE)
from qgeo import *
from util import new_obj, new_mesh, grid_faces, smoothstep
import wconst as C, wbomb

X0 = 10.5
GREY = (0.070, 0.074, 0.082, 1); GREY2 = (0.055, 0.058, 0.064, 1); GLASS = (0.008, 0.009, 0.012, 1); BLACK = (0.006, 0.006, 0.007, 1); WHITE = (0.55, 0.56, 0.55, 1); STEELC = (0.14, 0.14, 0.15, 1)
T33 = math.tan(math.radians(C.B2_SWEEP)); HALF = C.B2_SPAN / 2
TE = [(0.0, 18.05), (3.4, 15.84), (6.2, 17.66), (10.5, 14.87), (20.0, 21.04), (HALF, T33 * HALF)]      # (y, x) of the trailing edge's corners, every edge at 33 degrees
THICK = [(0.0, 4.1), (2.6, 3.9), (4.4, 3.2), (7.0, 1.9), (10.0, 1.15), (13.0, 0.75), (20.0, 0.42), (HALF, 0.04)]
BAY_X = (6.6, 13.1); BAY_Y = (0.35, 2.25); BAY_TOP = 0.62                                              # each bay: 6.5 m long, 1.9 m wide
ENG_Y = 4.4

def x_le(y):
    return T33 * abs(y)

def x_te(y):
    a = np.array(TE); return float(np.interp(abs(y), a[:, 0], a[:, 1]))

def _bump(x, y, xc, yc, rx, ry, h):
    e = ((x - xc) / rx) ** 2 + ((y - yc) / ry) ** 2; return h * math.exp(-e * 1.4) if e < 4 else 0.0

def surf(x, y):
    """(upper z, lower z) of the skin at x metres aft of the nose apex and span station y."""
    le = x_le(y); te = max(x_te(y), le + 0.05); c = te - le; u = min(max((x - le) / c, 0.0), 1.0)
    t = float(np.interp(abs(y), [p[0] for p in THICK], [p[1] for p in THICK]))
    sh = 2.6 * (0.2969 * math.sqrt(u) - 0.1260 * u - 0.3516 * u * u + 0.2843 * u ** 3 - 0.1036 * u ** 4) / 0.5 * 0.96      # NACA four-digit thickness, 1 at its thickest
    zu = 0.60 * t * sh; zl = -0.40 * t * sh; edge = min(u / 0.04, (1 - u) / 0.04, 1.0)
    zu += edge * (_bump(x, y, 5.6, 0.0, 3.4, 1.9, 0.78) + _bump(x, abs(y), 9.6, ENG_Y, 4.4, 1.55, 0.62))                  # over the crew, over each pair of engines
    return zu + 0.12, zl + 0.12

def P(x, y, z):
    return np.array([X0 - x, y, z])

def _stations():
    ys = set(np.round(np.linspace(0.0, HALF, 64), 3)) | {p[0] for p in TE} | {0.0, BAY_Y[0], BAY_Y[0] + 0.03, BAY_Y[1] - 0.03, BAY_Y[1], HALF - 0.15}
    ys = sorted(y for y in ys if not (BAY_Y[0] < y < BAY_Y[0] + 0.03 or BAY_Y[1] - 0.03 < y < BAY_Y[1]))
    return [-y for y in ys[:0:-1]] + ys

N_C = 56; I_A = 22; I_B = 40                                          # points along the chord; the two that are put on the front and rear edges of the bays

def _wing(S):
    ys = _stations(); uni = (1 - np.cos(np.linspace(0, np.pi, N_C))) / 2; idx = np.arange(N_C); up = []; lo = []; cl = []
    for y in ys:
        le = x_le(y); te = max(x_te(y), le + 0.05); c = te - le
        ua = min(max((BAY_X[0] - le) / c, 0.05), 0.9); ub = min(max((BAY_X[1] - le) / c, ua + 0.05), 0.97); f = 1.0 - smoothstep(2.8, 5.5, abs(y))
        rem = np.interp(idx, [0, 6, I_A, I_B, N_C - 1], [0.0, min(0.035, ua / 3), ua, ub, 1.0]); u = uni + f * (rem - uni); xs = le + u * c
        zz = np.array([surf(x, y) for x in xs]); zu = zz[:, 0].copy(); zl = zz[:, 1].copy(); col = np.tile(np.array(GREY), (N_C, 1))
        if BAY_Y[0] < abs(y) < BAY_Y[1]:
            inb = (idx > I_A) & (idx < I_B); zl[inb] = np.minimum(BAY_TOP, zu[inb] - 0.10); col[inb] = WHITE
        up.append(np.stack([X0 - xs, np.full(N_C, y), zu], 1)); lo.append(np.stack([X0 - xs, np.full(N_C, y), zl], 1)); cl.append(col)
    n = len(ys); U_ = np.concatenate(up); L_ = np.concatenate(lo)
    S.add(U_, grid_faces(n, N_C), None, GREY); S.add(L_, grid_faces(n, N_C, flip=True), None, np.concatenate(cl))

def _patch(S, pts, col, lift=0.02):
    """A dark patch laid on the upper skin through the given (x, y) corners (intakes, exhausts, windows)."""
    V = [P(x, y, surf(x, y)[0] + lift) for x, y in pts]; S.add(*plate(V, EZ, 0.01), color=col)

def _details(S):
    for sg in (1, -1):
        for dy in (-0.75, 0.75):                                       # two intakes ahead of each engine hump, their lips cut in a zigzag
            y = sg * (ENG_Y + dy); x = 6.25
            S.add(*plate([P(x, y - 0.62, surf(x, y - 0.62)[0] - 0.02), P(x + 0.5, y, surf(x + 0.5, y)[0] - 0.02), P(x, y + 0.62, surf(x, y + 0.62)[0] - 0.02), P(x + 0.55, y + 0.62, surf(x + 1.5, y + 0.62)[0] + 0.05), P(x + 1.0, y, surf(x + 1.9, y)[0] + 0.12), P(x + 0.55, y - 0.62, surf(x + 1.5, y - 0.62)[0] + 0.05)], EX, 0.03), color=BLACK)
            _patch(S, [(13.5, y - 0.55), (13.5, y + 0.55), (15.5 + 0.3 * sg * dy, y + 0.50), (15.5 + 0.3 * sg * dy, y - 0.50)], BLACK)       # exhaust troughs behind the humps
        _patch(S, [(2.75, sg * 0.10), (2.95, sg * 1.05), (4.05, sg * 1.25), (4.2, sg * 0.10)], GLASS, 0.03)                                # windscreen
        _patch(S, [(3.15, sg * 1.18), (3.75, sg * 1.75), (4.6, sg * 1.80), (4.25, sg * 1.35)], GLASS, 0.03)                                # side window

def _door(sg, inner):
    """One bay door in its own frame: hinge along X at the origin; shut, it reaches towards the other door of its bay."""
    S = Shell(); L_ = BAY_X[1] - BAY_X[0]; w = (BAY_Y[1] - BAY_Y[0]) / 2; d = (1 if inner else -1) * sg
    for dz, col in ((0.0, GREY), (0.05, WHITE)):
        S.add(np.array([[x, y, dz] for x in (L_ / 2, -L_ / 2) for y in np.linspace(0.0, d * w, 4)]), grid_faces(2, 4), None, col)
    return S.mesh("b2_door%+d%d" % (sg, inner), sharp=3.0)

class B2:
    def __init__(self, col=None, name="B2", stores=True):
        col = col or bpy.context.scene.collection; M = bpy.data.materials
        self.root = bpy.data.objects.new(name, None); col.objects.link(self.root); self.root.rotation_mode = 'QUATERNION'
        pm = M.get("B2Paint") or paint_mat("B2Paint", rough=0.48, bump=0.02); me = bpy.data.meshes.get("b2_body")
        if me is None:
            S = Shell(); _wing(S); _details(S); me = S.mesh("b2_body", sharp=math.radians(30)); me.materials.append(pm)
        self.body = new_obj(name + "_Body", me, col); self.body.parent = self.root
        xc = (BAY_X[0] + BAY_X[1]) / 2; yc = (BAY_Y[0] + BAY_Y[1]) / 2; self.belly = surf(xc, yc)[1]; self.doors = []; self.stores = []
        for k, sg in enumerate((1, -1)):                               # bay 0 on the left, bay 1 on the right
            for inner in (0, 1):
                nm = "b2_door%+d%d" % (sg, inner); dm = bpy.data.meshes.get(nm) or _door(sg, inner)
                if not dm.materials:
                    dm.materials.append(pm)
                d = new_obj(name + "_Door%d%d" % (k, inner), dm, col); d.parent = self.root; d.location = (X0 - xc, sg * (BAY_Y[0] if inner else BAY_Y[1]), self.belly + 0.01); self.doors.append((d, sg, inner))
            if stores:
                b = wbomb.Bomb(col, name + "_Store%d" % k); b.ob.parent = self.root; b.ob.location = tuple(self.store_local(k)); self.stores.append(b)
        self.set(0.0)

    def bay_c(self, k=0):
        """Aircraft-frame middle of the mouth of bay k."""
        return np.array([X0 - (BAY_X[0] + BAY_X[1]) / 2, (1, -1)[k] * (BAY_Y[0] + BAY_Y[1]) / 2, self.belly])

    def store_local(self, k=0):
        """Aircraft-frame position of the middle of the bomb's body as it hangs in bay k."""
        return np.array([X0 - (BAY_X[0] + BAY_X[1]) / 2 + (C.GBU_L - C.BLU_L) / 2, (1, -1)[k] * (BAY_Y[0] + BAY_Y[1]) / 2, BAY_TOP - 0.22 - C.BLU_D / 2])

    def set(self, doors=0.0, gone=()):
        """doors: 0 shut .. 1 open (each door hangs straight down); gone: bays whose bomb has been released."""
        for d, sg, inner in self.doors:
            d.rotation_euler = ((-1 if inner else 1) * sg * math.radians(92.0) * doors, 0, 0)
        for k, b in enumerate(self.stores):
            b.hide(k in gone); b.set_fins(0.0)                          # in the bay the lattice fins lie folded back

if __name__ == "__main__":
    ys = np.linspace(-HALF, HALF, 4001); print("wing area %.0f m2 (published 478)" % np.trapezoid([max(x_te(y) - x_le(y), 0) for y in ys], ys), " length %.2f" % max(p[1] for p in TE))
    print("height of the body %.2f m" % (max(surf(x, 0)[0] for x in np.linspace(0, 19, 200)) - min(surf(x, 0)[1] for x in np.linspace(0, 19, 200))))
