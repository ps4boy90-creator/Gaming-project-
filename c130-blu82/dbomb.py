"""BLU-82/B on its wooden cradle and airdrop platform, with the extraction and stabilising parachutes.

Bomb frame: middle of the 3.60 m body at the origin, nose towards +X.
From sources (National Museum of the USAF, Air Force Armament Museum): a thin-walled steel tank 141.6 in long and
54 in across holding 12,600 lb of slurry explosive; a nose fuze on a 38-inch extender; the body sat on a wooden
cradle strapped to an airdrop platform; a stabilising parachute packed on its rear end; a 15 ft extraction parachute.
Estimated from photographs: the cone of the nose, the dished rear end and the parachute pack, the hoisting lugs, the
shape of the cradle, the webbing, and the size and cut of both parachutes.  The inside (cut-open view) is a diagram.
"""
import bpy, math, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "grenade-explosion")); sys.path.insert(0, os.path.join(HERE, "..", "reaper-hellfire")); sys.path.insert(0, HERE)
from qgeo import *
from util import new_obj, grid_faces, nodemat
import dconst as C

L = C.BLU_L; R = C.BLU_D / 2; NL = C.NOSE_L; EXT = C.EXT_L; R_TIP = 0.17
OLIVE = (0.085, 0.100, 0.055, 1); OLIVE2 = (0.070, 0.082, 0.046, 1); YELLOW = (0.70, 0.52, 0.03, 1); STEEL = (0.22, 0.22, 0.23, 1); BRASS = (0.42, 0.30, 0.10, 1); DARK = (0.03, 0.03, 0.03, 1)
WOOD = (0.36, 0.25, 0.13, 1); WOOD2 = (0.28, 0.19, 0.10, 1); ALU = (0.50, 0.51, 0.52, 1); WEB = (0.55, 0.50, 0.36, 1); PACK = (0.30, 0.31, 0.22, 1)
CUTC = (0.10, 0.105, 0.115, 1); FILLC = (0.27, 0.245, 0.20, 1); BOOST = (0.62, 0.22, 0.10, 1); FUZEC = (0.60, 0.44, 0.14, 1)
CANOPY = (0.74, 0.73, 0.66, 1); CANOPY2 = (0.30, 0.36, 0.22, 1); LINE = (0.80, 0.79, 0.72, 1)

def r_out(s):
    """Outer radius s metres behind the front end of the tank (where the extender is screwed in)."""
    if s < NL:
        u = s / NL; return R_TIP + (R - R_TIP) * (u ** 0.82)
    if s > L - 0.16:
        return R - 0.10 * ((s - (L - 0.16)) / 0.16) ** 2
    return R

def _st():
    return sorted(set(list(np.linspace(0.0, NL, 14)) + [NL + 0.02, L - 0.16] + list(np.linspace(L - 0.16, L, 6))))

def _body():
    S = Shell(); st = _st()
    S.add(*revolve([(L / 2, 0.0)] + [(L / 2 - s, r_out(s)) for s in st] + [(-L / 2, 0.0)], 48), color=OLIVE)
    for s in (NL + 0.02, L - 0.20):                                   # the weld seams where nose and rear end join the barrel
        S.add(*revolve([(L / 2 - s + 0.03, R + 0.006), (L / 2 - s - 0.03, R + 0.006)], 48), color=OLIVE2)
    S.add(*revolve([(L / 2 - NL - 0.34, R + 0.002), (L / 2 - NL - 0.44, R + 0.002)], 48), color=YELLOW)             # high-explosive band
    for x in (0.55, -0.75):                                           # hoisting lugs on top
        S.add(*box((x, 0, R + 0.05), (0.16, 0.05, 0.14)), color=STEEL)
    S.add(*revolve([(-L / 2 + 0.02, 0.36), (-L / 2 - 0.30, 0.36), (-L / 2 - 0.34, 0.30), (-L / 2 - 0.34, 0.0)], 28), color=PACK)                 # the stabilising parachute, packed
    S.add(*revolve([(L / 2 + 0.07, R_TIP + 0.02), (L / 2 - 0.04, R_TIP + 0.05)], 24), color=STEEL)                                           # adapter ring
    return S.mesh("blu82_body", sharp=math.radians(40))

def _probe():
    """Fuze extender and nose fuze: the tip is EXT ahead of the tank."""
    S = Shell(); x0 = L / 2
    S.add(*revolve([(x0 + 0.02, 0.085), (x0 + 0.14, 0.085), (x0 + 0.17, 0.045), (x0 + EXT - 0.26, 0.045)], 20), color=STEEL)
    S.add(*revolve([(x0 + EXT - 0.27, 0.060), (x0 + EXT - 0.10, 0.060), (x0 + EXT - 0.03, 0.040), (x0 + EXT, 0.022), (x0 + EXT, 0.0)], 20), color=BRASS)                # the fuze
    for k in range(4):                                                # arming vane
        a = k * math.pi / 2 + 0.4; er = np.array([0, math.cos(a), math.sin(a)]); n = np.cross(EX, er) * 0.8 + EX * 0.6
        S.add(*plate([EX * (x0 + EXT - 0.045) + er * 0.02, EX * (x0 + EXT - 0.045) + er * 0.085, EX * (x0 + EXT - 0.015) + er * 0.085, EX * (x0 + EXT - 0.015) + er * 0.02], n, 0.004), color=STEEL)
    return S.mesh("blu82_probe", sharp=math.radians(40))

def _cutaway():
    """The far half of the bomb (y > 0, seen from -Y) with the cut face on the plane y = 0: thin wall, the filling, the booster behind the nose."""
    S = Shell(); st = _st(); a = np.linspace(-math.pi / 2, math.pi / 2, 25); w = C.WALL
    V = np.array([[L / 2 - s, r_out(s) * math.cos(t), r_out(s) * math.sin(t)] for s in st for t in a]); S.add(V, grid_faces(len(st), len(a)), None, OLIVE)
    V = np.array([[L / 2 - s, 0.0, f * r_out(s)] for s in st for f in (-1.0, 1.0)]); S.add(V, grid_faces(len(st), 2), None, CUTC)                     # the steel, seen edge on
    st2 = [s for s in st if 0.02 <= s <= L - 0.02] ; rin = lambda s: max(r_out(s) - max(w, 0.012), 0.0)                                             # drawn 12 mm thick so that it can be seen at all
    V = np.array([[L / 2 - s, -0.003, f * rin(s)] for s in st2 for f in (-1.0, 1.0)]); S.add(V, grid_faces(len(st2), 2), None, FILLC)
    S.add(*box((L / 2 - 0.36, -0.006, 0.0), (0.62, 0.004, 0.20)), color=BOOST)                                                                         # booster
    S.add(*box((L / 2 - 0.02, -0.006, 0.0), (0.10, 0.004, 0.09)), color=DARK)                                                          # the train through the extender
    S.add(*revolve([(-L / 2 + 0.02, 0.36), (-L / 2 - 0.30, 0.36), (-L / 2 - 0.34, 0.30), (-L / 2 - 0.34, 0.0)], 28), color=PACK)
    return S.mesh("blu82_cut", sharp=math.radians(40))

SADDLE_X = (0.85, -0.95)

def _cradle():
    """Platform, wooden cradle and webbing, in the bomb's frame (the platform's top is AXIS_H - PLAT_H below the axis)."""
    S = Shell(); zf = -C.AXIS_H; zp = zf + C.PLAT_H; xc = -0.05
    S.add(*box((xc, 0, zf + C.PLAT_H / 2), (C.PLAT_L, C.PLAT_W, C.PLAT_H)), color=ALU)
    for sg in (1, -1):
        S.add(*box((xc, sg * (C.PLAT_W / 2 - 0.04), zp + 0.03), (C.PLAT_L, 0.08, 0.06)), color=STEEL)                                  # side rails
        S.add(*box((xc, sg * 0.50, zp + 0.05), (C.PLAT_L - 0.3, 0.14, 0.10)), color=WOOD2)                                             # long timbers
    a = np.linspace(-math.radians(62), math.radians(62), 15)
    for x in SADDLE_X:                                                # two saddles cut to the tank
        top = np.array([[R * math.sin(t), -R * math.cos(t)] for t in a]); hw = R * math.sin(a[-1]) + 0.10; zb = zp + 0.10
        P2 = np.vstack([[[-hw, zb]], [[-hw, top[0, 1] + 0.02]], top, [[hw, top[-1, 1] + 0.02]], [[hw, zb]]])
        V = np.array([[x + dx, y, z] for dx in (-0.09, 0.09) for (y, z) in P2]); m = len(P2); j = np.arange(m); j1 = (j + 1) % m
        S.add(V, np.stack([j, j1, j1 + m, j + m], 1), None, WOOD)
        for dx in (-0.09, 0.09):
            S.add(np.array([[x + dx, y, z] for (y, z) in P2] + [[x + dx, y, zb] for (y, z) in P2]), grid_faces(2, m), None, WOOD)
    for x in (1.0, 0.1, -1.1):                                        # webbing over the tank, down to the platform's rails
        t = np.linspace(-math.radians(118), math.radians(118), 30); ring = [(R + 0.012) * np.array([0, math.sin(q), math.cos(q)]) for q in t]
        ring = [np.array([0, -(C.PLAT_W / 2 - 0.10), zp + 0.05])] + ring + [np.array([0, C.PLAT_W / 2 - 0.10, zp + 0.05])]
        for p, q in zip(ring[:-1], ring[1:]):
            d = q - p; n = np.cross(d, EX); n /= np.linalg.norm(n); S.add(*plate([p + EX * (x - 0.04), q + EX * (x - 0.04), q + EX * (x + 0.04), p + EX * (x + 0.04)], n, 0.006), color=WEB)
    return S.mesh("blu82_cradle", sharp=math.radians(35))

def _canopy(d, n_gore=20, slots=5, c1=CANOPY, c2=CANOPY2, lines=1.0):
    """A ring-slot canopy in its own frame: the lines meet at the origin and the canopy trails towards -X.  d = nominal diameter."""
    S = Shell(); r0 = 0.34 * d; depth = 0.26 * d; ll = lines * d; a = np.linspace(0, 2 * math.pi, n_gore, endpoint=False)
    prof = lambda u: (-(ll + depth * (1 - math.cos(u * math.pi / 2)) ), r0 * math.cos(u * math.pi / 2 * 0.94) if u > 0 else r0)     # u = 0 at the skirt, 1 at the vent
    us = np.linspace(0.0, 1.0, 2 * slots + 2)
    for k in range(slots + 1):                                        # cloth rings with open slots between them
        u0, u1 = us[2 * k], us[2 * k + 1] if k < slots else 0.93
        if k == slots:
            u0 = us[2 * k]
        rr = np.linspace(u0, u1, 4); rings = []
        for u in rr:
            x, r = prof(u); bulge = 1.0 + 0.045 * np.cos(n_gore * a)                                                 # the cloth bellies out between the lines
            rings.append(np.stack([np.full(n_gore * 1, x), r * bulge * np.cos(a), r * bulge * np.sin(a)], 1))
        V = np.concatenate(rings); S.add(V, grid_faces(len(rr), n_gore, wrap_v=True), None, c1 if k % 2 == 0 else c2)
    for q in a[:: max(n_gore // 10, 1)]:                              # suspension lines
        p1 = np.array([prof(0.0)[0], r0 * math.cos(q), r0 * math.sin(q)]); n = np.cross(p1, EX); n /= np.linalg.norm(n); w = 0.012 * max(d / 4.5, 1.0)
        S.add(*plate([n * w, p1 + n * w, p1 - n * w, -n * w], np.cross(p1 / np.linalg.norm(p1), n), 0.006), color=LINE)
    return S.mesh("canopy_%.1f" % d, sharp=math.radians(50))

def cloth_mat():
    m = bpy.data.materials.get("ChuteCloth")
    if m:
        return m
    m, N, Lk, P = nodemat("ChuteCloth"); a = N.new("ShaderNodeAttribute"); a.attribute_name = "col"; Lk.new(a.outputs["Color"], P.inputs["Base Color"]); P.inputs["Roughness"].default_value = 0.85
    try:
        P.inputs["Subsurface Weight"].default_value = 0.0; P.inputs["Sheen Weight"].default_value = 0.3
    except Exception:
        pass
    m.use_backface_culling = False
    return m

class Chute:
    """A parachute on its lines.  ob (quaternion): the lines meet at its origin, the canopy trails along its -X axis."""
    def __init__(self, col=None, name="Chute", d=C.STAB_D, lines=1.0, **kw):
        col = col or bpy.context.scene.collection; self.d = d
        self.ob = bpy.data.objects.new(name, _canopy(d, lines=lines, **kw)); col.objects.link(self.ob); self.ob.rotation_mode = 'QUATERNION'
        if not self.ob.data.materials:
            self.ob.data.materials.append(cloth_mat())
    def set(self, open_=1.0, breathe=0.0):
        """open_: 0 = a streamer, 1 = full; breathe: a small phase for the canopy's pulsing."""
        k = 0.10 + 0.90 * open_; k *= 1.0 + 0.04 * math.sin(breathe) * open_; self.ob.scale = (1.0 - 0.12 * (1 - open_), k, k)

class Bomb:
    """ob (quaternion) carries the body and the probe (or the cut-open half)."""
    def __init__(self, col=None, name="BLU82", cut=False):
        col = col or bpy.context.scene.collection; D = bpy.data.meshes; M = bpy.data.materials
        pm = M.get("BombPaint") or paint_mat("BombPaint", rough=0.60, bump=0.05)
        self.ob = bpy.data.objects.new(name, None); col.objects.link(self.ob); self.ob.rotation_mode = 'QUATERNION'; self.parts = []
        for nm, make in ((("blu82_cut", _cutaway),) if cut else (("blu82_body", _body),)) + (("blu82_probe", _probe),):
            me = D.get(nm) or make()
            if not me.materials:
                me.materials.append(pm)
            o = bpy.data.objects.new(name + "_" + nm, me); col.objects.link(o); o.parent = self.ob; self.parts.append(o)
    def hide(self, v):
        for o in self.parts:
            o.hide_render = v

class Cradle:
    """Platform, cradle and webbing; same frame as the bomb it carries."""
    def __init__(self, col=None, name="Cradle"):
        col = col or bpy.context.scene.collection; M = bpy.data.materials; pm = M.get("CradlePaint") or paint_mat("CradlePaint", rough=0.75, bump=0.3)
        me = bpy.data.meshes.get("blu82_cradle") or _cradle()
        if not me.materials:
            me.materials.append(pm)
        self.ob = bpy.data.objects.new(name, me); col.objects.link(self.ob); self.ob.rotation_mode = 'QUATERNION'
