"""Tallboy (Bomb, H.E., M.C., 12,000 lb): the steel case and the light-alloy tail with its four offset fins.
With LANC_BOMB=grandslam the same outline is drawn to the Grand Slam's length and width (22,000 lb): the larger bomb
was the same design scaled up, with a slightly longer tail.

Bomb frame: the middle of the bomb's length at the origin, nose towards +X; s = metres behind the tip of the nose.
From sources (see README): 21 ft long, 38 in across, about 12,000 lb with 5,200 lb of Torpex; a one-piece steel case
with a heavy nose; a conical tail of light alloy about as long as the case, with four fins set at 5 degrees to spin
the bomb; three pistols in the base of the case, each firing down an exploder tube into the filling.
The outline between those figures (the curve of the nose, where the body is widest, the taper to the tail joint, the
outline of the fins) is drawn after photographs and published drawings.
"""
import bpy, math, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "grenade-explosion")); sys.path.insert(0, os.path.join(HERE, "..", "reaper-hellfire")); sys.path.insert(0, HERE)
from qgeo import *
from util import new_obj, grid_faces
import lconst as C

L = C.TB_L; R = C.TB_D / 2; NL = C.NOSE_L; CL = C.CASE_L; X0 = L / 2
KL = C.K_L; KD = C.K_D; TAG = C.BOMB                    # scale on a Tallboy's length and width; prefix of the mesh names
S_WIDE = 1.80 * KL                                      # the body is widest here, then narrows gently to the joint with the tail
R_JOINT = 0.385 * KD; R_END = 0.115 * KD                # radius at the joint and at the end of the tail cone
FIN_S = (L - (L - CL) * 0.612, L - (L - CL) * 0.463, L - 0.03, L)   # a fin: root leading edge, tip leading edge, tip trailing edge, root trailing edge
FIN_R = C.TAIL_W / 2                                    # the fins stand a little wider than the body
BODY = (0.060, 0.082, 0.052, 1); TAILC = (0.118, 0.135, 0.112, 1); BAND_R = (0.42, 0.035, 0.030, 1); BAND_G = (0.16, 0.34, 0.14, 1); STEEL = (0.20, 0.20, 0.21, 1)

def r_out(s):
    """Outer radius s metres behind the tip of the nose."""
    if s <= 0:
        return 0.0
    if s < NL:                                          # tangent ogive
        rho = (R * R + NL * NL) / (2 * R); return max(math.sqrt(max(rho * rho - (NL - s) ** 2, 0.0)) + R - rho, 0.0)
    if s <= S_WIDE:
        return R
    if s <= CL:
        u = (s - S_WIDE) / (CL - S_WIDE); return R - (R - R_JOINT) * u ** 1.8
    u = (s - CL) / (L - CL); return R_JOINT + (R_END - R_JOINT) * (0.9 * u + 0.1 * u * u)

def _st_case():
    return sorted(set([0.0, 0.004, 0.012, 0.03, 0.06] + list(np.linspace(0.10, NL, 22)) + list(np.linspace(NL, CL, 26)) ))

def _st_tail():
    return list(np.linspace(CL, L, 14))

def _case():
    S = Shell(); st = _st_case()
    S.add(*revolve([(X0 - s, r_out(s)) for s in st][::-1] , 48), color=BODY)
    S.add(*revolve([(X0 - CL - 0.002, r_out(CL)), (X0 - CL - 0.002, 0.0)], 48), color=BODY)
    for s0, w, c in (((0.98 * KL, 0.050 * KL, BAND_R),) if TAG == "grandslam" else ((0.98, 0.050, BAND_R), (1.10, 0.050, BAND_G))):   # bands round the nose (the Grand Slam: "green over-all; red band near nose", OP 1665)
        S.add(*revolve([(X0 - s, r_out(s) + 0.0015) for s in np.linspace(s0, s0 + w, 4)][::-1], 48), color=c)
    return S.mesh(TAG + "_case", sharp=math.radians(40))

def _fin_pts():
    a, b, c, d = FIN_S; q = lambda s, r: np.array([X0 - s, 0.0, r])
    return [q(a, r_out(a) - 0.012), q(b, FIN_R), q(c, FIN_R), q(d, r_out(d) - 0.012)]

def _tail():
    """The tail cone and its fins.  The fins stand at 45 degrees to the vertical and are each turned 5 degrees about their
    own radial line, all the same way round."""
    S = Shell(); st = _st_tail()
    S.add(*revolve([(X0 - s, r_out(s)) for s in st][::-1], 40), color=TAILC)
    S.add(*revolve([(X0 - L, R_END), (X0 - L, 0.0)], 40), color=TAILC)
    S.add(*revolve([(X0 - CL - 0.07 * KL, R_JOINT + 0.012), (X0 - CL + 0.01, R_JOINT + 0.012)], 40), color=TAILC)   # the band that bolts the tail to the case
    P = _fin_pts(); mid = (FIN_S[0] + FIN_S[3]) / 2; c5, s5 = math.cos(math.radians(C.FIN_CANT)), math.sin(math.radians(C.FIN_CANT))
    cant = np.array([[c5, -s5, 0], [s5, c5, 0], [0, 0, 1.0]]); piv = np.array([X0 - mid, 0.0, 0.0])
    for k in range(4):
        a = math.pi / 4 + k * math.pi / 2; ca, sa = math.cos(a), math.sin(a); rot = np.array([[1, 0, 0], [0, ca, -sa], [0, sa, ca]])
        V, Q, T = plate(P, EY, 0.016 * KD); V = ((V - piv) @ cant.T + piv) @ rot.T; S.add(V, Q, T, TAILC)
    return S.mesh(TAG + "_tail", sharp=math.radians(40))

class Bomb:
    """root (quaternion) carries `spin` (an empty turned about the bomb's long axis), which carries the parts."""
    def __init__(self, col=None, name=C.NAME.replace(" ", ""), parts=("case", "tail")):
        col = col or bpy.context.scene.collection; D = bpy.data.meshes; M = bpy.data.materials
        pm = M.get("BombPaint") or paint_mat("BombPaint", rough=0.50, bump=0.03)
        self.root = bpy.data.objects.new(name, None); col.objects.link(self.root); self.root.rotation_mode = 'QUATERNION'
        self.spin = bpy.data.objects.new(name + "_Spin", None); col.objects.link(self.spin); self.spin.parent = self.root; self.spin.rotation_mode = 'XYZ'
        def ob(nm, mesh_name, make):
            me = D.get(mesh_name) or make()
            if not me.materials:
                me.materials.append(pm)
            o = bpy.data.objects.new(name + "_" + nm, me); col.objects.link(o); o.parent = self.spin; return o
        self.ob = self.root; self.case = self.tail = None
        if "case" in parts:
            self.case = ob("case", TAG + "_case", _case)
        if "tail" in parts:
            self.tail = ob("tail", TAG + "_tail", _tail)

    def turn(self, angle):
        """Angle (radians) turned about the long axis since release."""
        self.spin.rotation_euler = (angle, 0.0, 0.0)

    def hide(self, case=None, tail=None):
        for o, v in ((self.case, case), (self.tail, tail)):
            if o is not None and v is not None:
                o.hide_render = v
