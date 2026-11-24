"""Rockwell B-1B Lancer with one weapons bay that opens on a rotary launcher of eight GBU-31(V)3/B bombs.

Aircraft frame: nose towards +X, left +Y, up +Z; geometry is laid out by station s (metres aft of the nose tip),
x = X0 - s, with the wing pivots near the origin.
From sources (USAF fact sheet; T.O. 1B-1B-1 description; USAF Weapons File): 44.5 m long, 10.4 m high; span 41.8 m
with the wings forward (15 degrees) and 24.1 m swept (67.5 degrees); blended wing and body; four F101 engines in two
nacelles under the wing roots near the pivots; all-moving tailplanes on the fin; small structural-mode-control vanes
beside the nose; three weapons bays, each taking a 4.5 m rotary launcher with eight 2,000 lb stores.
Section shapes, the glove's outline, nacelle, fin and tailplane proportions and the bay's exact place are estimated
from photographs.  The landing gear is up and not modelled; there are no panel lines or markings.
"""
import bpy, math, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "grenade-explosion")); sys.path.insert(0, os.path.join(HERE, "..", "reaper-hellfire")); sys.path.insert(0, HERE)
from qgeo import *
from util import new_obj, new_mesh, grid_faces, simple_mat
import pconst as C, pbomb

X0 = 22.0
GREY = (0.060, 0.064, 0.072, 1); GREY2 = (0.072, 0.076, 0.084, 1); RADOME = (0.050, 0.052, 0.056, 1); GLASS = (0.008, 0.009, 0.012, 1); BLACK = (0.006, 0.006, 0.007, 1); METAL = (0.11, 0.10, 0.09, 1); WHITE = (0.62, 0.63, 0.62, 1)
PIVOT_S = 22.0; PIVOT_Y = 4.4; PANEL = 16.6
BAY = (11.9, 16.5); BAY_W = 1.06; N_STORES = 8
# s, centre z, half width, height up, depth down, squareness
_FUS = [(0.0, -0.50, 0.015, 0.015, 0.015, 2.0), (0.8, -0.46, 0.20, 0.19, 0.20, 2.0), (2.2, -0.36, 0.52, 0.48, 0.52, 2.0), (4.0, -0.22, 0.92, 0.86, 0.90, 2.1), (5.4, -0.10, 1.18, 1.18, 1.10, 2.2), (6.6, 0.0, 1.34, 1.50, 1.22, 2.2),
        (8.4, 0.04, 1.44, 1.58, 1.30, 2.3), (10.5, 0.05, 1.50, 1.52, 1.34, 2.5), (14.0, 0.05, 1.54, 1.46, 1.36, 2.7), (22.0, 0.05, 1.54, 1.42, 1.36, 2.7), (29.0, 0.06, 1.48, 1.38, 1.32, 2.6), (33.0, 0.12, 1.28, 1.24, 1.16, 2.4),
        (37.0, 0.24, 0.92, 0.92, 0.80, 2.2), (40.5, 0.40, 0.52, 0.54, 0.42, 2.0), (43.4, 0.52, 0.22, 0.22, 0.18, 2.0), (44.4, 0.56, 0.03, 0.03, 0.03, 2.0)]

def P(s, y, z):
    return np.array([X0 - s, y, z])

def fus(s):
    a = np.array(_FUS); return [float(np.interp(s, a[:, 0], a[:, k])) for k in range(1, 6)]

def fus_pt(s, ang, out=0.0):
    """Point on the fuselage skin at station s and angle ang (radians; 0 = left side, pi/2 = top), pushed out by `out`."""
    zc, w, up, dn, e = fus(s); p = 2.0 / e; cs, sn = math.cos(ang), math.sin(ang)
    return np.array([X0 - s, (w + out) * math.copysign(abs(cs) ** p, cs), zc + ((up if sn > 0 else dn) + out) * math.copysign(abs(sn) ** p, sn)])

def _fuselage(S):
    ss = sorted(set(list(0.0 + 44.4 * np.linspace(0, 1, 110) ** 1.08) + [BAY[0] - 0.02, BAY[0] + 0.02, BAY[1] - 0.02, BAY[1] + 0.02])); m = 56; th = np.linspace(0, 2 * np.pi, m, endpoint=False); rings = []; cols = []
    for s in ss:
        zc, w, up, dn, e = fus(s); p = 2.0 / e; cs, sn = np.cos(th), np.sin(th)
        y = w * np.sign(cs) * np.abs(cs) ** p; z = zc + np.where(sn > 0, up, dn) * np.sign(sn) * np.abs(sn) ** p; c = np.tile(np.array(GREY if s > 3.6 else RADOME), (m, 1))
        if BAY[0] < s < BAY[1]:                                        # the open bay is a recess pushed up into the belly; the doors cover it when shut
            inb = (sn < 0) & (np.abs(y) < BAY_W); z = np.where(inb, zc + 0.78, z); c[inb] = WHITE
        rings.append(np.stack([np.full(m, X0 - s), y, z], 1)); cols.append(c)
    V, Q, T = loft(rings); n = len(ss) * m; c = np.tile(np.array(GREY), (len(V), 1)); c[:n] = np.concatenate(cols); S.add(V, Q, T, c)
    S.add(*revolve([(0.0, 0.016), (-1.1, 0.02)], 6, axis=EX, origin=P(0.0, 0, -0.50)), color=METAL)                                # nose probe
    def window(s0, s1, a0, a1):
        ss_ = np.linspace(s0, s1, 5); aa = np.radians(np.linspace(a0, a1, 6)); S.add(np.array([fus_pt(s, a, 0.012) for s in ss_ for a in aa]), grid_faces(5, 6), None, GLASS)
    for sg in (1, -1):                                                 # windscreen panes and side windows
        window(5.05, 6.25, 90 - sg * 6, 90 - sg * 40); window(5.25, 6.55, 90 - sg * 44, 90 - sg * 66); window(6.75, 7.5, 90 - sg * 40, 90 - sg * 62)

def _glove(S):
    """The fixed inner wing that blends the body into the wing pivots."""
    for sg in (1, -1):
        st = []
        for y in np.linspace(1.05, 5.1, 10):
            sle = 9.4 + 3.25 * (y - 1.05); c = 31.6 - 1.1 * (y - 1.05) - sle; t = float(np.interp(y, [1.05, 3.0, 5.1], [1.70, 1.25, 0.62]))
            st.append((P(sle, sg * y, 0.08), c, t / c, (-1, 0, 0), (0, 0, 1)))
        V, Q, T = surface(st, 26); S.add(V, Q, T, GREY)

def _nacelles(S):
    for sg in (1, -1):
        st = [(19.2, -1.42, 1.55, 0.70), (20.0, -1.45, 1.66, 0.84), (24.0, -1.45, 1.70, 0.86), (28.5, -1.40, 1.66, 0.82), (30.6, -1.32, 1.50, 0.66)]
        m = 32; a = np.linspace(0, 2 * np.pi, m, endpoint=False); e = 2.0 / 3.4; cs, sn = np.cos(a), np.sin(a); sx = np.sign(cs) * np.abs(cs) ** e; sz = np.sign(sn) * np.abs(sn) ** e
        V, Q, T = loft([np.stack([np.full(m, X0 - s), sg * 4.05 + w * sx, zc + h * sz], 1) for s, zc, w, h in st], cap0=False); S.add(V, Q, T, GREY2)
        for k in (-1, 1):                                              # two intakes and two nozzles in each nacelle
            V, Q, T = loft([np.stack([np.full(m, X0 - s), sg * 4.05 + k * 0.80 + 0.70 * sx, -1.44 + 0.62 * sz], 1) for s in (19.25, 20.4)], cap0=False); S.add(V, Q, T, BLACK)
            S.add(*revolve([(0.0, 0.66), (0.5, 0.64), (1.25, 0.50)], 22, axis=-EX, origin=P(30.5, sg * 4.05 + k * 0.80, -1.34)), color=METAL)
            S.add(*revolve([(1.25, 0.48), (0.5, 0.52), (0.3, 0.0)], 22, axis=-EX, origin=P(30.5, sg * 4.05 + k * 0.80, -1.34)), color=BLACK)
        S.add(*box(P(19.6, sg * 4.05, -1.44), (1.0, 0.08, 1.30)), color=GREY2)                                                 # splitter between the two intakes
        S.add(*box(P(24.0, sg * 4.05, -0.52), (10.0, 2.4, 0.5)), color=GREY)                                                   # pylon fairing into the glove

def _tail(S):
    k = math.tan(math.radians(46.0))
    V, Q, T = wing(P(33.2, 0, 1.25), 8.2, 0.055, P(33.2 + k * 6.4, 0, 7.65), 2.7, 0.05, (0, 1, 0), n=18, k=5); S.add(V, Q, T, GREY)                # fin
    for sg in (1, -1):
        V, Q, T = wing(P(36.6, sg * 0.25, 2.75), 5.3, 0.06, P(36.6 + k * 6.5, sg * 6.83, 2.75), 1.7, 0.05, (0, 0, 1), n=16, k=5); S.add(V, Q, T, GREY)   # tailplanes
        dv = np.array([0, sg * math.cos(math.radians(30)), -math.sin(math.radians(30))]); n_ = np.array([0, sg * math.sin(math.radians(30)), math.cos(math.radians(30))])
        V, Q, T = wing(P(3.9, sg * 0.86, -0.28), 0.95, 0.07, P(4.2, sg * 0.86, -0.28) + dv * 0.92, 0.50, 0.06, n_, n=10, k=3); S.add(V, Q, T, GREY)      # structural-mode-control vanes
    S.add(*ellipsoid(P(39.6, 0, 2.75), (2.9, 0.42, 0.42)), color=GREY)                                                         # fairing where the tailplanes cross the fin

def _panel(sg):
    """One swinging wing panel in its own frame: pivot at the origin, drawn at 15 degrees of sweep, tip towards sg*Y."""
    S = Shell(); k = math.tan(math.radians(C.SWEEP_FWD))
    V, Q, T = wing((1.75, sg * 0.35, 0.0), 5.3, 0.085, (1.75 - k * (PANEL - 0.35), sg * PANEL, 0.0), 1.55, 0.065, (0, 0, 1), n=18, k=7); S.add(V, Q, T, GREY)
    return S.mesh("b1_panel%+d" % sg, sharp=math.radians(36))

def _door(sg):
    """One bay door in its own frame: hinge along X at the origin, the door reaching towards the centre line when shut."""
    S = Shell(); n = 6; L_ = BAY[1] - BAY[0]; ys = np.linspace(0.0, -sg * BAY_W, n)
    for dz, col in ((0.0, GREY), (0.05, WHITE)):
        S.add(np.array([[x, y, dz + 0.035 * (abs(y) / BAY_W) ** 2] for x in (L_ / 2, -L_ / 2) for y in ys]), grid_faces(2, n), None, col)
    return S.mesh("b1_door%+d" % sg, sharp=3.0)

def _launcher():
    S = Shell(); L_ = 4.5
    S.add(*revolve([(L_ / 2, 0.0), (L_ / 2, 0.30), (L_ / 2 - 0.2, 0.52), (-L_ / 2 + 0.2, 0.52), (-L_ / 2, 0.30), (-L_ / 2, 0.0)], 16), color=WHITE)
    for k in range(N_STORES):
        a = 2 * math.pi * k / N_STORES; er = np.array([0, math.sin(a), -math.cos(a)])
        for x in (0.55, -0.20):
            S.add(*box(EX * x + er * 0.56, (0.5, 0.12, 0.12)), color=METAL)                                                    # ejector racks
    return S.mesh("b1_launcher", sharp=math.radians(40))

STORE_R = 0.52 + 0.085 + C.BLU_D / 2

class B1B:
    def __init__(self, col=None, name="B1B", stores=True):
        col = col or bpy.context.scene.collection; M = bpy.data.materials
        self.root = bpy.data.objects.new(name, None); col.objects.link(self.root); self.root.rotation_mode = 'QUATERNION'
        pm = M.get("B1Paint") or paint_mat("B1Paint", rough=0.50, bump=0.02)
        S = Shell(); _fuselage(S); _glove(S); _nacelles(S); _tail(S)
        self.body = new_obj(name + "_Body", S.mesh("b1_body", sharp=math.radians(32)), col, pm); self.body.parent = self.root
        self.panels = []
        for sg in (1, -1):
            w = new_obj(name + "_Wing%+d" % sg, bpy.data.meshes.get("b1_panel%+d" % sg) or _panel(sg), col, pm); w.parent = self.root; w.location = tuple(P(PIVOT_S, sg * PIVOT_Y, 0.10)); self.panels.append((w, sg))
        zc, w_, up, dn, e = fus((BAY[0] + BAY[1]) / 2); self.bay_c = P((BAY[0] + BAY[1]) / 2, 0.0, zc - 0.22); self.belly = zc - dn
        self.doors = []
        for sg in (1, -1):
            d = new_obj(name + "_Door%+d" % sg, bpy.data.meshes.get("b1_door%+d" % sg) or _door(sg), col, pm); d.parent = self.root
            d.location = (self.bay_c[0], sg * BAY_W, self.belly + 0.02); self.doors.append((d, sg))
        self.launcher = None; self.stores = []
        if stores:
            self.launcher = new_obj(name + "_Launcher", bpy.data.meshes.get("b1_launcher") or _launcher(), col, pm); self.launcher.parent = self.root; self.launcher.location = tuple(self.bay_c)
            for k in range(N_STORES):
                b = pbomb.Bomb(col, name + "_Store%d" % k); b.ob.parent = self.launcher; b.ob.rotation_mode = 'XYZ'; self.stores.append(b)
        self.set(C.SWEEP_AFT, 0.0, 0.0)

    def store_local(self, k=0):
        """Aircraft-frame position of the centre of the bomb on station k with the launcher at its starting angle (0 = bottom)."""
        a = 2 * math.pi * k / N_STORES; return self.bay_c + np.array([0.35, STORE_R * math.sin(a), -STORE_R * math.cos(a)])

    def set(self, sweep=None, doors=None, turn=0.0, gone=()):
        """sweep: leading-edge sweep in degrees (15 to 67.5); doors: 0 shut .. 1 open; turn: launcher angle; gone: stations already dropped."""
        if sweep is not None:
            for w, sg in self.panels:
                w.rotation_euler = (0, 0, sg * math.radians(sweep - C.SWEEP_FWD))
        if doors is not None:
            for d, sg in self.doors:
                d.rotation_euler = (sg * math.radians(118.0) * doors, 0, 0)
        if self.launcher is not None:
            self.launcher.rotation_euler = (turn, 0, 0)
            for k, b in enumerate(self.stores):
                a = 2 * math.pi * k / N_STORES; b.ob.location = (0.35, STORE_R * math.sin(a), -STORE_R * math.cos(a)); b.ob.rotation_euler = (a, 0, 0); b.ob.hide_render = k in gone
