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
S_WIDE = 1.95 * KL                                      # the body is widest here, then narrows gently to the joint with the tail
R_JOINT = 0.395 * KD; R_END = 0.045 * KD                # radius at the joint and at the end of the tail cone (it runs out nearly to a point)
FIN_S = (L - 1.32 * KL, L - 1.15 * KL, L - 0.41 * KL, L - 0.41 * KL)   # a fin: root leading edge, tip leading edge, tip trailing edge, root trailing edge (short swept fins; the cone runs on behind them: IWM CH 15363, CH 15369)
HOLE_S = CL + 0.66 * KL; HOLE_R = 0.085 * KD            # the three hand-holes in the tail cone that give access to the pistols
TAIL_NO = "NO 82 MK I" if TAG == "grandslam" else "NO 78 MK I"
BAND_S = (0.305 * KL, 0.355 * KL)                       # the red band: round the point of the nose, where the photograph shows a light ring
MARK_S = 1.62 * KL                                      # the filling is stencilled round the body here
FIN_R = C.TAIL_W / 2                                    # the fins stand a little wider than the body
BODY = (0.060, 0.082, 0.052, 1); TAILC = (0.27, 0.29, 0.28, 1); BAND_R = (0.42, 0.035, 0.030, 1); STEEL = (0.20, 0.20, 0.21, 1); STENCIL = (0.62, 0.62, 0.58, 1)

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
    u = (s - CL) / (L - CL); return R_JOINT + (R_END - R_JOINT) * (0.6 * u + 0.4 * u * u)        # a slightly swelling cone

def _st_case():
    return sorted(set([0.0, 0.004, 0.012, 0.03, 0.06] + list(np.linspace(0.10, NL, 22)) + list(np.linspace(NL, CL, 26)) ))

def _st_tail():
    return list(np.linspace(CL, L, 14))

def _case():
    S = Shell(); st = _st_case()
    S.add(*revolve([(X0 - s, r_out(s)) for s in st][::-1] , 48), color=BODY)
    S.add(*revolve([(X0 - CL - 0.002, r_out(CL)), (X0 - CL - 0.002, 0.0)], 48), color=BODY)
    S.add(*revolve([(X0 - s, r_out(s) + 0.0015) for s in np.linspace(BAND_S[0], BAND_S[1], 4)][::-1], 48), color=BAND_R)   # "green over-all; red band near nose" (OP 1665, both bombs)
    return S.mesh(TAG + "_case", sharp=math.radians(40))

def _fin_pts():
    a, b, c, d = FIN_S; q = lambda s, r: np.array([X0 - s, 0.0, r])
    return [q(a, r_out(a) - 0.012), q(b, FIN_R), q(c, FIN_R), q(d, r_out(d) - 0.012)]

def _tail():
    """The tail cone and its fins.  The fins stand at 45 degrees to the vertical and are each turned 5 degrees about their
    own radial line, all the same way round."""
    S = Shell(); st = _st_tail()
    S.add(*revolve([(X0 - s, r_out(s)) for s in st][::-1], 40), color=TAILC)
    S.add(*revolve([(X0 - L - 0.05 * KD, 0.0), (X0 - L - 0.03 * KD, R_END * 0.6), (X0 - L, R_END)][::-1], 40), color=TAILC)      # the rounded end of the cone
    for k in range(3):                                      # hand-holes, 120 degrees apart: dark discs
        a0 = math.radians(-35.0 + 120.0 * k); ang = np.linspace(0, 2 * np.pi, 20, endpoint=False); rs = np.linspace(0.0, HOLE_R, 3); V = []
        for t in ang:
            for rr in rs:
                s_ = HOLE_S + rr * math.cos(t); r_ = r_out(s_) + 0.004; a_ = a0 + rr * math.sin(t) / r_; V.append((X0 - s_, r_ * math.sin(a_), r_ * math.cos(a_)))
        S.add(np.array(V), grid_faces(20, 3, wrap_u=True), None, (0.012, 0.012, 0.012, 1))
    S.add(*revolve([(X0 - CL - 0.15 * KL, R_JOINT + 0.012), (X0 - CL + 0.02, R_JOINT + 0.012)], 40), color=BODY)   # the band that bolts the tail to the case
    P = _fin_pts(); mid = (FIN_S[0] + FIN_S[3]) / 2; c5, s5 = math.cos(math.radians(C.FIN_CANT)), math.sin(math.radians(C.FIN_CANT))
    cant = np.array([[c5, -s5, 0], [s5, c5, 0], [0, 0, 1.0]]); piv = np.array([X0 - mid, 0.0, 0.0])
    for k in range(4):
        a = math.pi / 4 + k * math.pi / 2; ca, sa = math.cos(a), math.sin(a); rot = np.array([[1, 0, 0], [0, ca, -sa], [0, sa, ca]])
        V, Q, T = plate(P, EY, 0.05 * KD); V = ((V - piv) @ cant.T + piv) @ rot.T; S.add(V, Q, T, TAILC)
    return S.mesh(TAG + "_tail", sharp=math.radians(40))

def _stencil(text="TORPEX D1", h=0.058, along=False, s0=None, a0=-28.0, color=None, name="_stencil"):
    """Stencilled lettering h high.  Round the body (the filling's name on the Tallboy in IWM CH 15363, feet towards the
    tail), or with along=True along the tail (its number, as on the Grand Slam in IWM CH 15369)."""
    s0 = MARK_S if s0 is None else s0; color = color or STENCIL
    cu = bpy.data.curves.new("stencil", 'FONT'); cu.body = text; cu.size = h * KD / 0.70; cu.align_x = 'CENTER'; cu.align_y = 'CENTER'; cu.space_character = 1.25
    tmp = bpy.data.objects.new("stencil_tmp", cu); bpy.context.scene.collection.objects.link(tmp); bpy.context.view_layer.update()
    me = bpy.data.meshes.new_from_object(tmp.evaluated_get(bpy.context.evaluated_depsgraph_get())); bpy.data.objects.remove(tmp, do_unlink=True); bpy.data.curves.remove(cu)
    co = np.zeros(len(me.vertices) * 3); me.vertices.foreach_get("co", co); co = co.reshape(-1, 3); out = np.zeros_like(co)
    for i, (u, v, _) in enumerate(co):                                # u along the line of text -> round the body; v up the letters -> towards the nose
        s = (s0 - u) if along else (s0 - v); r = r_out(s) + 0.003; a = math.radians(a0) - (v if along else u) / r; out[i] = (X0 - s, r * math.sin(a), r * math.cos(a))
    me.vertices.foreach_set("co", out.ravel()); me.update(); me.name = TAG + name
    at = me.attributes.new("col", 'FLOAT_COLOR', 'POINT'); at.data.foreach_set("color", np.tile(np.array(color, np.float32), len(me.vertices)))
    return me

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
        self.ob = self.root; self.case = self.tail = self.mark = None
        if "case" in parts:
            self.case = ob("case", TAG + "_case", _case)
            if TAG == "tallboy":                           # seen on the Tallboy's body; not on the side of the Grand Slam that was photographed
                self.mark = ob("mark", TAG + "_stencil", _stencil)
        self.tmark = None
        if "tail" in parts:
            self.tmark = ob("tmark", TAG + "_tailno", lambda: _stencil(TAIL_NO, 0.065, along=True, s0=CL + 0.95 * KL, a0=-62.0, color=(0.015, 0.015, 0.015, 1), name="_tailno"))
            self.tail = ob("tail", TAG + "_tail", _tail)

    def turn(self, angle):
        """Angle (radians) turned about the long axis since release."""
        self.spin.rotation_euler = (angle, 0.0, 0.0)

    def hide(self, case=None, tail=None):
        for o, v in ((self.case, case), (self.tail, tail), (self.mark, case), (self.tmark, tail)):
            if o is not None and v is not None:
                o.hide_render = v
