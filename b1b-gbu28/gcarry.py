"""The B-1B of segment 09 with one GBU-28 on a pylon under the left side of its forward fuselage.

The GBU-28 is not a B-1B weapon: in service it is dropped by the F-15E and the B-2 (first by the F-111F).  What the
B-1B has flown, in tests from 2024, is the GBU-28's 5,000 lb successor, the GBU-72, on Boeing's Load Adaptable Modular
pylon at the forward right hardpoint.  The pylon here stands in that place; its shape is a plain fairing, not Boeing's.
"""
import bpy, math, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
for p in ("grenade-explosion", "reaper-hellfire", "b1b-blu109"):
    sys.path.insert(0, os.path.join(HERE, "..", p))
sys.path.insert(0, HERE)
from qgeo import Shell, wing, box, paint_mat
from util import new_obj
import pb1b, gbomb
import gconst as C

PY_Y = 1.15; PY_S = (11.2, 16.0); PY_Z = (-0.90, -1.58)
STORE = pb1b.P(13.6, PY_Y, PY_Z[1] - 0.03 - C.BLU_D / 2)              # middle of the warhead, aircraft frame

def _pylon():
    S = Shell(); V, Q, T = wing(pb1b.P(PY_S[0], PY_Y, PY_Z[0]), PY_S[1] - PY_S[0], 0.075, pb1b.P(PY_S[0] + 0.35, PY_Y, PY_Z[1]), PY_S[1] - PY_S[0] - 0.7, 0.075, (0, 1, 0), n=16, k=3, tip_round=False)
    S.add(V, Q, T, pb1b.GREY2)
    for s in (13.6 - 0.381, 13.6 + 0.381):                               # the two ejector feet over the bomb's lugs
        S.add(*box(pb1b.P(s, PY_Y, PY_Z[1] - 0.02), (0.20, 0.16, 0.06)), color=pb1b.METAL)
    return S.mesh("b1_pylon", sharp=math.radians(40))

class Carrier:
    def __init__(self, col=None, name="B1B"):
        col = col or bpy.context.scene.collection
        self.jet = pb1b.B1B(col, name, stores=False); self.root = self.jet.root
        pm = bpy.data.materials.get("B1Paint")
        self.pylon = new_obj(name + "_Pylon", bpy.data.meshes.get("b1_pylon") or _pylon(), col, pm); self.pylon.parent = self.root
        self.store = gbomb.Bomb(col, name + "_Store"); self.store.root.parent = self.root; self.store.root.location = tuple(STORE)
        self.jet.set(C_SWEEP, 0.0, 0.0)

C_SWEEP = 67.5
