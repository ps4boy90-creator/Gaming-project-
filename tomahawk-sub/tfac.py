"""The target: a small factory in the desert.  A block-walled hall with a sheet-metal roof on steel frames, an office
annex, a brick chimney, two tanks and a yard wall.  It is invented, and nobody is modelled in it.

The hall is built from separate wall panels, roof sheets and frames so that it can come apart: update(td) puts every
piece where it is td seconds after the warhead fires two metres above the middle of the floor.  Which pieces go where
is staging, guided by what a 120 kg charge does inside a light building: the roof is lifted off, the walls are blown
outwards, the steel frames nearest the burst are thrown down and the far ones are left leaning."""
import bpy, math, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
for p in ("grenade-explosion", "rpg7-explosion", "mortar-explosion", "howitzer-explosion", "reaper-hellfire"):
    sys.path.insert(0, os.path.join(HERE, "..", p))
sys.path.insert(0, HERE)
from mathutils import Quaternion, Vector
import htown
from qgeo import Shell, box as gbox, revolve, plate, paint_mat, EX, EY, EZ
from qtruck import Piece
from util import new_mesh, new_obj, grid_faces, nodemat, simple_mat, smoothstep
import tconst as C

F = C.FAC; LX, LY, H, RIDGE = F["lx"], F["ly"], F["h"], F["ridge"]
BLOCK = (0.50, 0.47, 0.42, 1); BLOCK2 = (0.42, 0.39, 0.35, 1); SHEET = (0.36, 0.38, 0.39, 1); RUST = (0.30, 0.17, 0.10, 1); STEEL = (0.20, 0.07, 0.05, 1); DARKC = (0.03, 0.03, 0.03, 1); BRICK = (0.33, 0.14, 0.09, 1)
BAY = 3.0

class Factory:
    def __init__(self, col):
        rng = np.random.default_rng(33); self.pieces = []; self.col = col
        self.mat = bpy.data.materials.get("FactoryPaint") or paint_mat("FactoryPaint", rough=0.85, bump=0.4)
        self.metal = bpy.data.materials.get("FactoryMetal") or paint_mat("FactoryMetal", rough=0.45, metal=0.7)
        burst = np.array([0.0, 0.0, C.BURST_Z])
        def piece(name, S, pivot, speed, up, rest_z, flat, mat=None, keep=False, lean=None):
            """One loose part.  It is thrown away from the burst at `speed` (plus `up`), tumbles, and comes to rest lying flat."""
            ob = new_obj(name, S.mesh(name.lower()), col, mat or self.mat); pivot = np.array(pivot, float)
            if keep:
                ob.location = pivot; ob.rotation_mode = 'QUATERNION'
                if lean is not None:
                    self.pieces.append(("lean", ob, pivot, lean))
                return ob
            d = pivot - burst; d[2] = 0.0; dist = np.linalg.norm(d) + 1e-6; d /= dist
            v0 = d * speed * rng.uniform(0.75, 1.25) + np.array([rng.uniform(-1.5, 1.5), rng.uniform(-1.5, 1.5), up * rng.uniform(0.8, 1.25)])
            ax = np.cross(d, EZ) + rng.uniform(-0.3, 0.3, 3); rq = Quaternion(Vector(flat[0]), flat[1]) @ Quaternion((0, 0, 1), rng.uniform(-0.6, 0.6))
            self.pieces.append(("fly", Piece(ob, pivot, v0, ax, rng.uniform(1.5, 4.5) * rng.choice([-1, 1]), rest_z, (rq.w, rq.x, rq.y, rq.z), drag=0.25), 0.012 * dist)); return ob
        # ---- long walls: block panels one bay wide, with a strip of windows high up
        nb = int(LX / BAY)
        for sg in (1, -1):
            for i in range(nb):
                xc = -LX / 2 + BAY * (i + 0.5); S = Shell(); door = (sg < 0 and i in (3, 4))
                if door:
                    S.add(*gbox((0, 0, 2.1), (BAY - 0.02, 0.24, H - 4.2)), color=BLOCK)                                                                            # lintel above the door
                    S.add(*gbox((0, sg * 0.10, -H / 2 + 2.1), (BAY - 0.1, 0.06, 4.2)), color=RUST)                                                                  # sliding door leaf
                else:
                    S.add(*gbox((0, 0, 0), (BAY - 0.02, 0.24, H)), color=BLOCK if (i + (sg > 0)) % 2 else BLOCK2)
                    S.add(*gbox((0, sg * 0.125, H / 2 - 1.3), (BAY - 0.9, 0.02, 0.9)), color=DARKC)                                                                # window strip
                d = abs(xc); piece("Wall%+d_%d" % (sg, i), S, (xc, sg * LY / 2, H / 2), max(5.0, 19.0 - 0.9 * d), 3.0, 0.14, ((1, 0, 0), sg * math.pi / 2))
        # ---- gable ends: three panels each; they are the furthest from the burst and fall outwards last
        for sg in (1, -1):
            for j in range(3):
                yc = -LY / 2 + LY / 3 * (j + 0.5); S = Shell(); hh = H + RIDGE * (1 - abs(yc) / (LY / 2)) * 0.9
                S.add(*gbox((0, 0, (hh - H) / 2), (0.24, LY / 3 - 0.02, hh)), color=BLOCK2 if j % 2 else BLOCK)
                piece("Gable%+d_%d" % (sg, j), S, (sg * LX / 2, yc, H / 2), 5.5, 1.2, 0.14, ((0, 1, 0), -sg * math.pi / 2))
        # ---- roof: corrugated sheets on both slopes
        pitch = math.atan2(RIDGE, LY / 2); sl = (LY / 2) / math.cos(pitch) + 0.3
        for sg in (1, -1):
            for i in range(nb):
                xc = -LX / 2 + BAY * (i + 0.5); S = Shell(); q = Quaternion((1, 0, 0), sg * pitch).to_matrix(); rot = np.array(q)
                S.add(*gbox((0, 0, 0), (BAY - 0.03, sl, 0.05), rot=rot), color=SHEET if (i + (sg > 0)) % 3 else RUST)
                for k in range(-3, 4):                                                                                                 # ribs, so the sheets read as corrugated
                    S.add(*gbox((k * 0.42, 0, 0.03), (0.06, sl, 0.04), rot=rot), color=SHEET)
                piece("Roof%+d_%d" % (sg, i), S, (xc, sg * LY / 4, H + RIDGE / 2 + 0.05), max(3.0, 9.0 - 0.5 * abs(xc)), max(8.0, 24.0 - 1.4 * abs(xc)), 0.10, ((1, 0, 0), rng.uniform(-0.2, 0.2)), mat=self.metal)
        # ---- steel portal frames at every bay line: the middle ones are thrown down, the end ones left leaning
        for i in range(nb + 1):
            xc = -LX / 2 + BAY * i; S = Shell()
            for sg in (1, -1):
                S.add(*gbox((0, sg * (LY / 2 - 0.3), 0), (0.22, 0.22, H)), color=STEEL)
                q = np.array(Quaternion((1, 0, 0), sg * pitch).to_matrix()); S.add(*gbox((0, sg * LY / 4, H / 2 + RIDGE / 2), (0.20, sl - 0.3, 0.26), rot=q), color=STEEL)
            far = abs(xc) > LX / 2 - BAY * 1.5
            if far:
                piece("Frame%d" % i, S, (xc, 0, H / 2), 0, 0, 0, None, mat=self.metal, keep=True, lean=Quaternion((0, 1, 0), math.radians(13.0 if xc > 0 else -11.0)))
            else:
                piece("Frame%d" % i, S, (xc, 0, H / 2), 4.0 + 1.5 * abs(xc), 2.5, 0.16, ((0, 1, 0), math.pi / 2 * (1 if xc >= 0 else -1)), mat=self.metal)
        # ---- what stays: floor slab, machines, annex, chimney, tanks, yard wall
        S = Shell(); S.add(*gbox((0, 0, 0.06), (LX + 1.0, LY + 1.0, 0.12)), color=(0.30, 0.29, 0.27, 1))
        for (x, y, sx, sy, sz) in ((-7.5, 2.2, 3.2, 1.6, 1.9), (-2.5, -2.4, 2.4, 1.8, 1.5), (5.0, 2.6, 4.0, 1.4, 2.2), (8.5, -2.0, 2.0, 2.0, 1.7), (-9.5, -2.8, 1.6, 1.2, 1.1)):
            S.add(*gbox((x, y, 0.12 + sz / 2), (sx, sy, sz)), color=(0.10, 0.13, 0.11, 1)); S.add(*gbox((x, y, 0.12 + sz + 0.15), (sx * 0.5, sy * 0.5, 0.3)), color=(0.16, 0.16, 0.17, 1))
        ax0 = LX / 2 + 4.5; S.add(*gbox((ax0, -1.0, 1.75), (8.0, 6.0, 3.5)), color=BLOCK); S.add(*gbox((ax0, -1.0, 3.58), (8.4, 6.4, 0.16)), color=(0.28, 0.27, 0.25, 1))   # office annex
        for k in range(3):
            S.add(*gbox((ax0 - 2.6 + 2.6 * k, -4.02, 2.0), (1.3, 0.04, 1.1)), color=DARKC)
        S.add(*gbox((ax0 - 3.0, 2.02, 1.05), (1.0, 0.04, 2.1)), color=RUST)
        cx, cy = -LX / 2 - 5.0, 4.5                                                                                                    # chimney
        S.add(*revolve([(0.0, 1.05), (17.0, 0.62), (17.0, 0.45), (16.0, 0.45)], 20, axis=EZ, origin=(cx, cy, 0)), color=BRICK); S.add(*gbox((cx, cy, 1.0), (2.6, 2.6, 2.0)), color=BRICK)
        for k, (tx, ty) in enumerate(((-LX / 2 - 4.5, -4.5), (-LX / 2 - 8.5, -4.5))):                                                  # tanks on saddles
            S.add(*revolve([(-2.6, 0.0), (-2.5, 1.0), (-2.2, 1.25), (2.2, 1.25), (2.5, 1.0), (2.6, 0.0)], 22, axis=EY, origin=(tx, ty, 1.9)), color=(0.46, 0.47, 0.46, 1))
            for dy in (-1.4, 1.4):
                S.add(*gbox((tx, ty + dy, 0.4), (2.0, 0.4, 0.8)), color=BLOCK2)
        wl = 34.0                                                                                                                      # yard wall on three sides
        for (x, y, sx, sy) in ((0, 19.0, 2 * wl, 0.3), (-wl, 0, 0.3, 38.0), (wl, 0, 0.3, 38.0)):
            S.add(*gbox((x, y, 1.1), (sx, sy, 2.2)), color=BLOCK2)
        self.fixed = new_obj("FactoryFixed", S.mesh("factory_fixed"), col, self.mat)
        # ---- rubble that is only there afterwards (it appears inside the dust), and the scorch on the slab and the yard
        R = Shell(); n = 320; a = rng.uniform(0, 2 * np.pi, n); r = np.abs(rng.normal(0, 1, n)) * 9.0 + 1.0
        for k in range(n):
            x = r[k] * math.cos(a[k]) * 1.5; y = r[k] * math.sin(a[k]); s = rng.uniform(0.15, 0.6, 3) * (1.6 if r[k] < 8 else 1.0)
            q = np.array(Quaternion(Vector(rng.uniform(-1, 1, 3)).normalized(), rng.uniform(0, 3.1)).to_matrix())
            R.add(*gbox((x, y, 0.12 + s[2] * 0.3), s, rot=q), color=BLOCK if k % 3 else (SHEET if k % 2 else BLOCK2))
        self.rubble = new_obj("FactoryRubble", R.mesh("factory_rubble"), col, self.mat); self.rubble.hide_render = True
        sm, N, L, P = nodemat("FactoryScorch"); tc = N.new("ShaderNodeTexCoord"); sep = N.new("ShaderNodeSeparateXYZ"); L.new(tc.outputs["UV"], sep.inputs[0])
        nz = N.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 0.5; L.new(tc.outputs["Object"], nz.inputs["Vector"])
        ed = N.new("ShaderNodeMapRange"); ed.inputs["From Min"].default_value = 1.0; ed.inputs["From Max"].default_value = 0.30; L.new(sep.outputs["X"], ed.inputs["Value"])
        nm = N.new("ShaderNodeMapRange"); nm.inputs["From Min"].default_value = 0.25; nm.inputs["From Max"].default_value = 0.6; L.new(nz.outputs["Fac"], nm.inputs["Value"])
        self.gain = N.new("ShaderNodeValue"); m1 = N.new("ShaderNodeMath"); m1.operation = 'MULTIPLY'; L.new(ed.outputs[0], m1.inputs[0]); L.new(nm.outputs[0], m1.inputs[1])
        m2 = N.new("ShaderNodeMath"); m2.operation = 'MULTIPLY'; L.new(m1.outputs[0], m2.inputs[0]); L.new(self.gain.outputs[0], m2.inputs[1]); L.new(m2.outputs[0], P.inputs["Alpha"])
        P.inputs["Base Color"].default_value = (0.012, 0.011, 0.010, 1); P.inputs["Roughness"].default_value = 0.9
        na, nr = 56, 6; a = np.linspace(0, 2 * np.pi, na, endpoint=False); r = np.linspace(0.02, 1.0, nr); A, Rr = np.meshgrid(a, r, indexing="ij")
        V = np.stack([26.0 * Rr * np.cos(A), 19.0 * Rr * np.sin(A), np.full_like(A, 0.135)], -1).reshape(-1, 3)
        ob = new_obj("FactoryScorchDisc", new_mesh("factory_scorch", V, [grid_faces(na, nr, wrap_u=True)], uvs=np.stack([Rr, A / (2 * np.pi)], -1).reshape(-1, 2)), col, sm); ob.visible_shadow = False
        self.update(-1.0)

    def update(self, td):
        for it in self.pieces:
            if it[0] == "fly":
                p, q = it[1].at(td - it[2]); it[1].ob.location = p; it[1].ob.rotation_quaternion = q
            else:
                _, ob, pivot, lean = it; u = smoothstep(0.05, 0.9, td); q = Quaternion().slerp(lean, u); ob.rotation_quaternion = q
                ob.location = pivot + np.array(q @ Vector((0, 0, H / 2))) - np.array([0, 0, H / 2])                    # lean about the feet
        self.rubble.hide_render = td < 0.35; self.gain.outputs[0].default_value = 0.92 * smoothstep(0.0, 0.3, td)
