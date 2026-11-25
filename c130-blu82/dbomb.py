"""BLU-82/B: the bomb with its fuze extender, the cradle and airdrop platform it rides out of the aircraft on, and its
two parachutes.

Bomb frame: the middle of the bomb's length at the origin, nose towards +X.
From sources (see README): a thin-walled steel tank 54 in across with a conical nose, 141.6 in long, 15,000 lb with 12,600 lb
of slurry explosive; a 36 in fuze extender on the nose that fires it three feet above the ground; olive drab with a
yellow band round the nose.  It is tied
down on a cradle on an airdrop platform, pulled out of the open ramp by an extraction parachute, and then falls nose
down under a smaller stabilising parachute while cradle and platform fall away.
The proportions of nose, bands, lugs, cradle and platform are taken from photographs of the museum examples; the
parachutes' sizes are in dconst.
"""
import bpy, math, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "grenade-explosion")); sys.path.insert(0, os.path.join(HERE, "..", "reaper-hellfire")); sys.path.insert(0, HERE)
from qgeo import *
from util import new_obj, new_mesh, grid_faces, nodemat
import dconst as C

L = C.LEN; R = C.DIA / 2; X0 = L / 2; CL = C.CONE_L; NR = C.NOSE_R; EXT = C.EXT
OD = (0.070, 0.085, 0.040, 1); OD2 = (0.095, 0.105, 0.060, 1); STRAP = (0.30, 0.27, 0.17, 1); STEEL = (0.20, 0.20, 0.21, 1); YELLOW = (0.62, 0.50, 0.06, 1); PACK = (0.085, 0.095, 0.050, 1)
ALU = (0.42, 0.43, 0.44, 1); WOODC = (0.40, 0.29, 0.15, 1); PLY = (0.50, 0.38, 0.20, 1); NYLON = (0.72, 0.72, 0.68, 1); NYLON_OD = (0.20, 0.23, 0.13, 1)
BAND_X = (X0 - CL - 0.30, X0 - CL - 1.25, -X0 + 0.38)                   # the three bands with their lifting lugs

def r_out(s):
    """Outer radius s metres behind the front of the nose."""
    if s <= 0:
        return 0.0
    if s < CL:
        return NR + (R - NR) * s / CL
    return R

def _case():
    S = Shell(); prof = [(X0, 0.0), (X0, NR), (X0 - CL, R), (-X0 + 0.10, R), (-X0 + 0.03, R - 0.05), (-X0, R - 0.16), (-X0, 0.0)]
    S.add(*revolve(prof[::-1], 56), color=OD)
    S.add(*revolve([(X0 - CL * 0.20, r_out(CL * 0.20) + 0.002), (X0 - CL * 0.28, r_out(CL * 0.28) + 0.002)], 56), color=YELLOW)                    # the yellow band of a high-explosive filling, round the nose
    for bx in BAND_X:                                                  # bands, each with a lifting lug on top
        S.add(*revolve([(bx + 0.045, R + 0.006), (bx - 0.045, R + 0.006)], 56), color=STRAP)
        S.add(*box((bx, 0.0, R + 0.05), (0.10, 0.14, 0.10)), color=STEEL); S.add(*revolve([(-0.02, 0.045), (-0.02, 0.085), (0.02, 0.085), (0.02, 0.045)], 12, axis=EY, origin=(bx, 0.0, R + 0.16), side=EX), color=STEEL)
    return S.mesh("blu82_case", sharp=math.radians(30))

def _extender():
    """The 36 in fuze extender: a tube on the nose with the fuze and its arming vane at the far end."""
    S = Shell(); x0 = X0
    S.add(*revolve([(x0 + EXT - 0.20, 0.050), (x0, 0.050)], 14), color=OD2); S.add(*revolve([(x0 + 0.06, 0.11), (x0, 0.11)], 14), color=STEEL)
    S.add(*revolve([(x0 + EXT, 0.0), (x0 + EXT, 0.028), (x0 + EXT - 0.05, 0.040), (x0 + EXT - 0.20, 0.046)], 14), color=(0.33, 0.30, 0.16, 1))          # the fuze
    for k in range(4):                                                 # arming vane
        a = k * math.pi / 2; d = np.array([0.0, math.cos(a), math.sin(a)]); S.add(*box(np.array([x0 + EXT - 0.07, 0, 0]) + d * 0.075, (0.012, 0.03, 0.07), rot=np.stack([EX, np.cross(d, EX), d], 1)), color=STEEL)
    return S.mesh("blu82_extender", sharp=math.radians(40))

def _pack():
    """The stabilising parachute's pack, strapped on the flat rear end."""
    S = Shell(); S.add(*revolve([(-X0, 0.44), (-X0 - 0.20, 0.42), (-X0 - 0.30, 0.30), (-X0 - 0.32, 0.0)], 20), color=PACK); return S.mesh("blu82_pack", sharp=math.radians(50))

def _stencil(lines=("BOMB BLU-82/B", "15000 LB  GSX", "LOT   NET WT"), h=0.055):
    """Yellow stencilling on the side of the drum, as on the museum examples."""
    out = []
    for k, txt in enumerate(lines):
        cu = bpy.data.curves.new("st", 'FONT'); cu.body = txt; cu.size = h / 0.70; cu.align_x = 'LEFT'; cu.align_y = 'CENTER'; cu.space_character = 1.15
        tmp = bpy.data.objects.new("st_tmp", cu); bpy.context.scene.collection.objects.link(tmp); bpy.context.view_layer.update()
        me = bpy.data.meshes.new_from_object(tmp.evaluated_get(bpy.context.evaluated_depsgraph_get())); bpy.data.objects.remove(tmp, do_unlink=True); bpy.data.curves.remove(cu)
        co = np.zeros(len(me.vertices) * 3); me.vertices.foreach_get("co", co); co = co.reshape(-1, 3); a0 = math.radians(12.0) - k * 0.13 / R
        V = np.stack([-0.65 + co[:, 0], -(R + 0.004) * np.cos(a0 + co[:, 1] / R), (R + 0.004) * np.sin(a0 + co[:, 1] / R)], 1)           # on the right-hand side of the drum, reading towards the nose
        fq = [list(p.vertices) for p in me.polygons]; out.append((V, fq)); bpy.data.meshes.remove(me)
    S = Shell()
    for V, fq in out:
        S.add(V, [f for f in fq if len(f) == 4], [f for f in fq if len(f) == 3], YELLOW)
    return S.mesh("blu82_stencil", sharp=3.0)

PLAT = (3.66, 2.74, 0.10)                                             # the airdrop platform: 12 ft by 9 ft
CRADLE_H = 0.46                                                       # how far the cradle holds the drum above the platform

def _platform():
    """Cradle and platform in the bomb's frame (the bomb lies level on them): an aluminium platform with a dark timber
    cradle, plywood chocks and tie-down straps over the bands."""
    S = Shell(); zp = -R - CRADLE_H; xc = -0.25
    S.add(*box((xc, 0, zp - PLAT[2] / 2), PLAT), color=ALU)
    for sy in (1, -1):
        S.add(*box((xc, sy * (PLAT[1] / 2 - 0.05), zp + 0.03), (PLAT[0], 0.10, 0.16)), color=ALU)                                   # side rails
        S.add(*box((xc - 0.1, sy * 0.48, zp + CRADLE_H * 0.5), (2.5, 0.22, CRADLE_H)), color=WOODC)                                   # cradle bearers
        for bx in BAND_X:                                              # straps from each lug down to the rails
            p0 = np.array([bx, sy * 0.10, R + 0.10]); p1 = np.array([bx + 0.35, sy * (PLAT[1] / 2 - 0.12), zp + 0.08])
            for q0, q1 in ((p0, np.array([bx, sy * R * 0.98, 0.0])), (np.array([bx, sy * R * 0.98, 0.0]), p1)):
                d = q1 - q0; ln = np.linalg.norm(d); ex = d / ln; ey = np.cross(EX, ex); ey = ey / (np.linalg.norm(ey) + 1e-9); S.add(*box((q0 + q1) / 2, (ln, 0.012, 0.045), rot=np.stack([ex, ey, np.cross(ex, ey)], 1)), color=NYLON_OD)
    for bx in (xc - 1.15, xc + 1.0):
        S.add(*box((bx, 0, zp + CRADLE_H * 0.5), (0.20, 1.5, CRADLE_H)), color=WOODC)                                               # cross members
    S.add(*box((X0 - CL - 0.1, 0, zp + 0.22), (0.5, 0.9, 0.40)), color=PLY)                                                          # plywood chock under the nose
    return S.mesh("blu82_platform", sharp=math.radians(40))

def chute_mesh(name, d_nom, gores=20, rings=6, slots=True, color=NYLON, lines=1.0):
    """A ring-slot parachute in its own frame: the point where the lines meet at the origin, the canopy along +Z.
    d_nom is its nominal diameter; inflated it is about two thirds of that across."""
    S = Shell(); Rc = 0.34 * d_nom; Ll = lines * d_nom; hz = math.sqrt(max(Ll * Ll - Rc * Rc, 0.01)); th = np.linspace(math.radians(8), math.radians(88), rings + 1); a = np.linspace(0, 2 * np.pi, gores + 1)
    P_ = lambda t, aa, s=1.0: np.array([Rc * math.sin(t) * math.cos(aa) * s, Rc * math.sin(t) * math.sin(aa) * s, hz + Rc * 0.55 * math.cos(t)])
    for k in range(rings):                                             # concentric rings of cloth with open slots between them
        t0, t1 = th[k], th[k + 1] - (math.radians(3.2) if slots and k < rings - 1 else 0.0); V = []; Q = []
        for j in range(gores):
            bulge = 1.035                                              # each gore bellies out between its lines
            n = len(V); am = (a[j] + a[j + 1]) / 2; V += [P_(t0, a[j]), P_(t0, am, bulge), P_(t0, a[j + 1]), P_(t1, a[j]), P_(t1, am, bulge), P_(t1, a[j + 1])]; Q += [[n, n + 1, n + 4, n + 3], [n + 1, n + 2, n + 5, n + 4]]
        S.add(np.array(V), np.array(Q), None, color)
    for j in range(gores):                                             # suspension lines
        p1 = P_(th[-1], a[j]); ln = np.linalg.norm(p1); ex = p1 / ln; ey = np.cross(EZ, ex); ey /= np.linalg.norm(ey); S.add(*box(p1 / 2, (ln, 0.018, 0.018), rot=np.stack([ex, ey, np.cross(ex, ey)], 1)), color=NYLON)
    return S.mesh(name, sharp=math.radians(60))

def jeep_mesh():
    """An M151 quarter-ton truck as plain shapes, 3.4 m long, for scale."""
    S = Shell(); S.add(*box((0.0, 0, 0.66), (3.3, 1.60, 0.46)), color=OD2); S.add(*box((1.10, 0, 1.00), (1.05, 1.50, 0.24)), color=OD2)                # tub and bonnet
    S.add(*box((0.52, 0, 1.36), (0.05, 1.50, 0.50)), color=(0.03, 0.04, 0.05, 1)); S.add(*box((0.52, 0, 1.63), (0.07, 1.56, 0.05)), color=OD2)        # windscreen and its frame
    for sy in (0.42, -0.42):
        S.add(*box((-0.10, sy, 1.02), (0.50, 0.50, 0.14)), color=PACK); S.add(*box((-0.33, sy, 1.24), (0.10, 0.50, 0.42)), color=PACK)                 # two seats
    S.add(*box((-1.10, 0, 1.02), (0.55, 1.30, 0.16)), color=PACK); S.add(*revolve([(-0.06, 0.0), (-0.06, 0.34), (0.06, 0.34), (0.06, 0.0)], 14, axis=EX, origin=(-1.72, 0.0, 0.95), side=EY), color=(0.02, 0.02, 0.022, 1))   # rear seat, spare wheel
    for wx in (1.05, -1.05):
        for sg in (1, -1):
            S.add(*revolve([(-0.10, 0.0), (-0.10, 0.36), (0.10, 0.36), (0.10, 0.0)], 14, axis=EY, origin=(wx, sg * 0.70, 0.36), side=EX), color=(0.02, 0.02, 0.022, 1))
    return S.mesh("jeep", sharp=math.radians(40))

class Chute:
    """A parachute and the line from it to its load.  place(p_load, p_dir, open_) puts the meeting point of its lines
    `riser` metres from p_load along p_dir and blows the canopy open (0 streaming .. 1 full)."""
    def __init__(self, col, name, d_nom, riser, **kw):
        self.riser = riser; me = bpy.data.meshes.get(name) or chute_mesh(name, d_nom, **kw); pm = bpy.data.materials.get("ChutePaint") or paint_mat("ChutePaint", rough=0.75)
        if not me.materials:
            me.materials.append(pm)
        self.ob = bpy.data.objects.new(name, me); col.objects.link(self.ob); self.ob.rotation_mode = 'QUATERNION'
        S = Shell(); S.add(*box((0, 0, -riser / 2), (0.035, 0.035, riser)), color=NYLON); rm = S.mesh(name + "_riser"); rm.materials.append(pm)
        self.line = bpy.data.objects.new(name + "_Riser", rm); col.objects.link(self.line); self.line.parent = self.ob

    def place(self, p_load, p_dir, open_=1.0):
        from mathutils import Vector
        d = Vector(p_dir).normalized(); self.ob.location = Vector(p_load) + d * self.riser; self.ob.rotation_quaternion = d.to_track_quat('Z', 'Y'); s = 0.12 + 0.88 * max(0.0, min(1.0, open_)); self.ob.scale = (s, s, 1.0)
        self.line.scale = (1.0 / s, 1.0 / s, 1.0)

    def hide(self, v):
        self.ob.hide_render = v; self.line.hide_render = v

class Bomb:
    """root (quaternion) carries the case, the extender, the parachute pack and the stencils; `platform` is a separate
    object so that it can fall away."""
    def __init__(self, col=None, name="BLU82", platform=True):
        col = col or bpy.context.scene.collection; D = bpy.data.meshes; M = bpy.data.materials
        pm = M.get("BombPaint") or paint_mat("BombPaint", rough=0.55, bump=0.03)
        self.root = bpy.data.objects.new(name, None); col.objects.link(self.root); self.root.rotation_mode = 'QUATERNION'; self.parts = []
        def ob(nm, mesh_name, make, parent):
            me = D.get(mesh_name) or make()
            if not me.materials:
                me.materials.append(pm)
            o = bpy.data.objects.new(name + "_" + nm, me); col.objects.link(o); o.parent = parent; return o
        self.case = ob("case", "blu82_case", _case, self.root); self.ext = ob("ext", "blu82_extender", _extender, self.root); self.pack = ob("pack", "blu82_pack", _pack, self.root); self.mark = ob("mark", "blu82_stencil", _stencil, self.root)
        self.parts = [self.case, self.ext, self.pack, self.mark]; self.platform = None
        if platform:
            self.platform = bpy.data.objects.new(name + "_Platform", D.get("blu82_platform") or _platform()); col.objects.link(self.platform); self.platform.rotation_mode = 'QUATERNION'
            if not self.platform.data.materials:
                self.platform.data.materials.append(pm)

    def hide(self, v):
        for o in self.parts:
            o.hide_render = v
