/**
 * The pickup: a square-bodied half-ton from the late seventies, the kind that
 * is still parked beside every farmhouse because it still starts.
 *
 * It follows the same rules as the buildings -- flat faces, hard edges, the
 * detail in the paint -- but a vehicle is recognised by its outline in a way a
 * wall is not, so the outline is where the polygons go: wheel arches cut into
 * the flanks, a body crease running nose to tail, a hood that crowns, a cab
 * that leans in toward the roof, a windscreen that rakes back. Everything else
 * is trim laid on top: seams, handles, mirrors, wipers, lamps.
 *
 * Local axes: +X is the driver's right, +Y up, and the truck faces -Z. Every
 * part that has a twin is built once and mirrored. Winding is not preserved
 * by mirroring and does not need to be: the shader lights whichever side of a
 * face is looking at the camera.
 */
import { stick } from './geom.js';
import { L } from './textures.js';
import { rotX, rotY, rotZ, translate, chain, cross, sub, normalize, dot } from './math.js';

// Stations along the body, front to back, and the heights that define it.
const FRONT = -2.55, COWL = -1.05, CAB_BACK = 0.62, BED_FRONT = 0.67, REAR = 2.55;
const AXLE_F = -1.6, AXLE_R = 1.6, WHEEL_R = 0.38, ARCH_R = 0.5;
const SILL = 0.42, CREASE = 1.0, CREASE_TOP = 1.045, BELT = 1.18, RAIL = 1.2, ROOF = 1.8;
const WIDE = 0.97;      // half width below the crease
const UPPER = 0.94;     // and above it
const HOOD_X = 0.87;    // where the fender rolls over into the hood
const BED_IN = 0.85, BED_FLOOR = 0.8;
const hoodY = (z) => 1.1 + ((z - FRONT) / (COWL - FRONT)) * 0.065;

/**
 * Boxes that stand in for the truck when casting the moon's shadow, as
 * [centre x, centre z, half x, half z, bottom, top] in truck space. They are
 * kept inside the bodywork: a face that pokes out of its own shadow box is
 * lit correctly, one that sits inside it would shade itself.
 */
export const TRUCK_BOXES = [
  [0, 0, 0.92, 2.5, 0.44, 0.76],                    // chassis and floor
  [0, (FRONT + COWL) / 2, 0.86, 0.72, 0.76, 1.06],  // engine bay
  [0, -0.05, 0.78, 0.55, 0.76, 1.74],               // cab
];

export function buildTruck(m, M) {
  const paint = { layer: L.paint };
  const low = { layer: L.paint, col: [0.74, 0.7, 0.64] };            // road dirt below the crease
  const shadeIn = { layer: L.paint, col: [0.6, 0.6, 0.6], occ: 0.55 };
  const dark = { layer: L.plain, col: [0.035, 0.035, 0.04] };
  const pit = { layer: L.plain, col: [0.02, 0.02, 0.022], occ: 0.15 };
  const rubber = { layer: L.plain, col: [0.03, 0.03, 0.032] };
  const chrome = { layer: L.plain, col: [0.3, 0.31, 0.34] };
  const glass = { layer: L.glass, fit: true, occ: 0.8 };

  /** Build something for both sides: P mirrors a point across the centreline. */
  const sides = (fn) => { for (const s of [-1, 1]) fn(s, (x, y, z) => [s * x, y, z]); };

  /** A smaller copy of a quad, floated just off its plane: glazing in a frame. */
  const inset = (pts, k, lift, out) => {
    const c = [0, 1, 2].map((a) => pts.reduce((t, p) => t + p[a], 0) / pts.length);
    let n = normalize(cross(sub(pts[1], pts[0]), sub(pts[3], pts[0])));
    if (dot(n, out) < 0) n = n.map((v) => -v);
    return pts.map((p) => p.map((v, a) => c[a] + (v - c[a]) * k + n[a] * lift));
  };

  m.at(M, () => {
    /* ---- flanks: wheel arches, the crease, fenders, doors, bed sides ---- */
    const arch = (cz) => [0, 36, 72, 108, 144, 180].map((deg) => {
      const a = (deg * Math.PI) / 180;
      return [cz + Math.cos(a) * ARCH_R, Math.max(SILL, 0.4 + Math.sin(a) * ARCH_R)];
    });
    sides((s, P) => {
      const panel = (z0, y0, z1, y1) => m.quad(P(WIDE, y0, z0), P(WIDE, y1, z1), P(WIDE, CREASE, z1), P(WIDE, CREASE, z0), low);
      panel(FRONT, 0.54, AXLE_F - ARCH_R, SILL);
      panel(AXLE_F + ARCH_R, SILL, AXLE_R - ARCH_R, SILL);
      panel(AXLE_R + ARCH_R, SILL, REAR, 0.5);
      for (const cz of [AXLE_F, AXLE_R]) {
        const a = arch(cz);
        for (let i = 0; i < 5; i++) {
          const [z0, y0] = a[i], [z1, y1] = a[i + 1];
          m.quad(P(WIDE, y0, z0), P(WIDE, y1, z1), P(WIDE, CREASE, z1), P(WIDE, CREASE, z0), low);
          stick(m, P(WIDE + 0.012, y0, z0), P(WIDE + 0.012, y1, z1), 0.05, 0.05, low);       // the flared lip
          m.quad(P(WIDE, y0, z0), P(WIDE, y1, z1), P(WIDE - 0.36, y1, z1), P(WIDE - 0.36, y0, z0), pit);
        }
        m.poly(a.map(([z, y]) => P(WIDE - 0.36, y, z)), pit);                                 // back of the wheel well
      }

      m.quad(P(WIDE, CREASE, FRONT), P(WIDE, CREASE, REAR), P(UPPER, CREASE_TOP, REAR), P(UPPER, CREASE_TOP, FRONT), paint);
      // Front fender, rolling over into the hood.
      m.quad(P(UPPER, CREASE_TOP, FRONT), P(UPPER, CREASE_TOP, COWL), P(UPPER, hoodY(COWL) - 0.035, COWL), P(UPPER, hoodY(FRONT) - 0.035, FRONT), paint);
      m.quad(P(UPPER, hoodY(FRONT) - 0.035, FRONT), P(UPPER, hoodY(COWL) - 0.035, COWL), P(HOOD_X, hoodY(COWL), COWL), P(HOOD_X, hoodY(FRONT), FRONT), paint);
      m.quad(P(HOOD_X, hoodY(FRONT), FRONT), P(HOOD_X, hoodY(COWL), COWL), P(0, hoodY(COWL) + 0.022, COWL), P(0, hoodY(FRONT) + 0.022, FRONT), paint);
      // Door skin above the crease, then the bed side.
      m.quad(P(UPPER, CREASE_TOP, COWL), P(UPPER, CREASE_TOP, CAB_BACK), P(UPPER, BELT, CAB_BACK), P(UPPER, BELT, COWL), paint);
      m.quad(P(UPPER, CREASE_TOP, BED_FRONT), P(UPPER, CREASE_TOP, REAR), P(UPPER, RAIL, REAR), P(UPPER, RAIL, BED_FRONT), paint);

      // Door shut lines, handle, belt moulding, marker lamps.
      const d0 = COWL + 0.05, d1 = CAB_BACK - 0.1;
      for (const z of [d0, d1]) {
        m.box(s * (WIDE + 0.003), (0.5 + CREASE) / 2, z, 0.008, CREASE - 0.5, 0.016, dark);
        m.box(s * (UPPER + 0.003), (CREASE_TOP + BELT) / 2, z, 0.008, BELT - CREASE_TOP, 0.016, dark);
      }
      m.box(s * (WIDE + 0.003), 0.5, (d0 + d1) / 2, 0.008, 0.016, d1 - d0, dark);
      m.box(s * (UPPER + 0.016), 1.11, d1 - 0.2, 0.03, 0.035, 0.14, chrome);
      stick(m, P(UPPER + 0.006, BELT, COWL), P(UPPER + 0.006, BELT, CAB_BACK), 0.03, 0.022, chrome);
      m.box(s * (WIDE + 0.004), 0.9, FRONT + 0.14, 0.01, 0.05, 0.11, { layer: L.plain, col: [0.75, 0.4, 0.06] });
      m.box(s * (WIDE + 0.004), 0.9, REAR - 0.14, 0.01, 0.05, 0.11, { layer: L.plain, col: [0.42, 0.03, 0.03] });

      /* ---- cab: pillars lean in, the screen rakes back ---- */
      const a0 = P(0.93, BELT, COWL), a1 = P(0.8, ROOF, -0.62), b0 = P(0.93, BELT, CAB_BACK), b1 = P(0.8, ROOF, 0.54);
      m.quad(a0, b0, b1, a1, paint);
      m.quad(...inset([a0, b0, b1, a1], 0.84, 0.012, [s, 0.2, 0]), glass);
      stick(m, P(0.928, 1.22, -0.45), P(0.83, 1.73, -0.45), 0.024, 0.022, dark);           // quarter-light divider
      stick(m, P(0.81, ROOF + 0.006, -0.64), P(0.81, ROOF + 0.006, 0.56), 0.03, 0.022, dark);   // drip rail
      m.quad(P(0.8, ROOF, -0.62), P(0.8, ROOF, 0.54), P(0, ROOF + 0.028, 0.54), P(0, ROOF + 0.028, -0.62), paint);
      stick(m, P(0.94, 1.24, -0.96), P(1.1, 1.3, -0.99), 0.018, 0.018, dark);              // mirror arm and head
      m.box(s * 1.12, 1.33, -0.99, 0.03, 0.22, 0.15, chrome);

      /* ---- bed: inner walls, rail tops, corner posts with the lamps ---- */
      m.quad(P(BED_IN, BED_FLOOR, BED_FRONT + 0.05), P(BED_IN, BED_FLOOR, REAR - 0.06), P(BED_IN, RAIL, REAR - 0.06), P(BED_IN, RAIL, BED_FRONT + 0.05), shadeIn);
      m.quad(P(BED_IN, RAIL, BED_FRONT), P(UPPER, RAIL, BED_FRONT), P(UPPER, RAIL, REAR), P(BED_IN, RAIL, REAR), paint);
      for (const z of [1.0, 1.6, 2.2]) m.box(s * 0.895, RAIL + 0.002, z, 0.05, 0.004, 0.07, pit);   // stake pockets
      m.quad(P(0.8, 0.62, REAR), P(UPPER, 0.62, REAR), P(UPPER, RAIL, REAR), P(0.8, RAIL, REAR), paint);
      m.box(s * 0.8, 0.91, REAR + 0.003, 0.012, 0.58, 0.006, dark);                        // tailgate shut line
      m.box(s * 0.875, 0.9, REAR + 0.01, 0.1, 0.34, 0.02, { layer: L.plain, col: [0.44, 0.03, 0.03] });
      m.box(s * 0.875, 0.7, REAR + 0.01, 0.1, 0.06, 0.02, { layer: L.plain, col: [0.6, 0.6, 0.56] });
      m.quad(P(0.66, 0.14, AXLE_R + 0.56), P(0.96, 0.14, AXLE_R + 0.56), P(0.96, 0.52, AXLE_R + 0.56), P(0.66, 0.52, AXLE_R + 0.56), rubber);   // mud flap
    });

    /* ---- nose ---- */
    m.quad([-WIDE, 0.54, FRONT], [WIDE, 0.54, FRONT], [WIDE, CREASE, FRONT], [-WIDE, CREASE, FRONT], paint);
    m.poly([[-UPPER, CREASE, FRONT], [UPPER, CREASE, FRONT], [UPPER, hoodY(FRONT) - 0.035, FRONT], [HOOD_X, hoodY(FRONT), FRONT],
      [0, hoodY(FRONT) + 0.022, FRONT], [-HOOD_X, hoodY(FRONT), FRONT], [-UPPER, hoodY(FRONT) - 0.035, FRONT]], paint);
    m.quad([0.9, 0.63, FRONT - 0.02], [-0.9, 0.63, FRONT - 0.02], [-0.9, 1.05, FRONT - 0.02], [0.9, 1.05, FRONT - 0.02], { layer: L.grille, fit: true });
    m.box(0, 0.555, FRONT - 0.1, 2.0, 0.15, 0.15, chrome);                                  // bumper
    for (const x of [-0.42, 0.42]) m.box(x, 0.57, FRONT - 0.185, 0.07, 0.2, 0.03, chrome);  // over-riders
    m.box(0, 0.46, FRONT + 0.04, 1.7, 0.1, 0.08, dark);                                     // valance

    /* ---- screen, cowl, wipers, back of the cab ---- */
    const screen = [[-0.93, BELT, COWL], [0.93, BELT, COWL], [0.8, ROOF, -0.62], [-0.8, ROOF, -0.62]];
    m.quad(...screen, paint);
    m.quad(...inset(screen, 0.9, 0.012, [0, 0.5, -1]), glass);
    m.box(0, hoodY(COWL) + 0.024, COWL + 0.045, 1.5, 0.012, 0.09, pit);                     // cowl vent
    const onScreen = (x, f) => [x, BELT + f * (ROOF - BELT) + 0.016, COWL + f * 0.43 - 0.022];
    stick(m, onScreen(-0.55, 0.08), onScreen(-0.08, 0.13), 0.014, 0.014, dark);
    stick(m, onScreen(0.12, 0.08), onScreen(0.6, 0.13), 0.014, 0.014, dark);
    m.quad([0.93, BELT, CAB_BACK], [-0.93, BELT, CAB_BACK], [-0.8, ROOF, 0.54], [0.8, ROOF, 0.54], paint);
    const backZ = (y) => CAB_BACK - ((y - BELT) / (ROOF - BELT)) * 0.08 + 0.012;
    m.quad([-0.6, 1.36, backZ(1.36)], [0.6, 1.36, backZ(1.36)], [0.6, 1.7, backZ(1.7)], [-0.6, 1.7, backZ(1.7)], glass);
    m.quad([UPPER, SILL, CAB_BACK], [-UPPER, SILL, CAB_BACK], [-UPPER, BELT, CAB_BACK], [UPPER, BELT, CAB_BACK], shadeIn);
    stick(m, [0.78, hoodY(-1.25), -1.25], [0.82, 2.05, -1.18], 0.012, 0.012, dark);         // aerial

    /* ---- bed floor, bulkhead, tailgate, and what is riding in it ---- */
    const bf = BED_FRONT + 0.05, br = REAR - 0.06;
    m.quad([-BED_IN, BED_FLOOR, br], [BED_IN, BED_FLOOR, br], [BED_IN, BED_FLOOR, bf], [-BED_IN, BED_FLOOR, bf],
      { layer: L.metal, col: [0.4, 0.42, 0.42], tile: 0.9, occ: 0.7 });
    m.quad([-UPPER, SILL, BED_FRONT], [UPPER, SILL, BED_FRONT], [UPPER, RAIL, BED_FRONT], [-UPPER, RAIL, BED_FRONT], shadeIn);
    m.quad([-BED_IN, BED_FLOOR, bf], [BED_IN, BED_FLOOR, bf], [BED_IN, RAIL, bf], [-BED_IN, RAIL, bf], shadeIn);
    m.quad([-BED_IN, RAIL, BED_FRONT], [BED_IN, RAIL, BED_FRONT], [BED_IN, RAIL, bf], [-BED_IN, RAIL, bf], paint);
    m.quad([-0.8, 0.62, REAR], [0.8, 0.62, REAR], [0.8, RAIL, REAR], [-0.8, RAIL, REAR], paint);
    m.quad([-BED_IN, BED_FLOOR, br], [BED_IN, BED_FLOOR, br], [BED_IN, RAIL, br], [-BED_IN, RAIL, br], shadeIn);
    m.quad([-BED_IN, RAIL, br], [BED_IN, RAIL, br], [BED_IN, RAIL, REAR], [-BED_IN, RAIL, REAR], paint);
    m.quad([-0.62, 0.74, REAR + 0.006], [0.62, 0.74, REAR + 0.006], [0.62, 1.08, REAR + 0.006], [-0.62, 1.08, REAR + 0.006],
      { layer: L.paint, col: [0.84, 0.84, 0.84], uvOff: [0.37, 0.21] });                    // pressed panel
    for (const y of [0.74, 1.08]) m.box(0, y, REAR + 0.008, 1.24, 0.012, 0.006, dark);
    for (const x of [-0.62, 0.62]) m.box(x, 0.91, REAR + 0.008, 0.012, 0.34, 0.006, dark);
    m.box(0, 1.135, REAR + 0.014, 0.17, 0.035, 0.022, chrome);                              // latch
    m.quad([-WIDE, 0.5, REAR], [WIDE, 0.5, REAR], [WIDE, 0.62, REAR], [-WIDE, 0.62, REAR], low);
    m.box(0, 0.52, REAR + 0.1, 2.0, 0.14, 0.17, chrome);                                    // step bumper
    m.box(0, 0.593, REAR + 0.1, 1.1, 0.006, 0.15, rubber);
    m.quad([-0.15, 0.455, REAR + 0.188], [0.15, 0.455, REAR + 0.188], [0.15, 0.585, REAR + 0.188], [-0.15, 0.585, REAR + 0.188], { layer: L.plate, fit: true });

    m.box(0, 1.12, bf + 0.25, 1.84, 0.34, 0.46, { layer: L.metal, col: [0.52, 0.54, 0.58], tile: 0.4 });   // crossover toolbox
    m.box(0, 1.3, bf + 0.25, 1.86, 0.02, 0.48, { layer: L.plain, col: [0.3, 0.31, 0.33] });
    m.at(translate(0.32, BED_FLOOR, 1.72), () => {                                          // the spare, lying flat
      m.cyl(WHEEL_R, WHEEL_R, 0.24, 14, { layer: L.tire, cap: rubber });
      m.at(translate(0, 0.242, 0), () => m.cyl(0.235, 0.235, 0.01, 12, { layer: L.plain, col: [0.62, 0.62, 0.58] }));
      m.at(translate(0, 0.25, 0), () => m.cyl(0.1, 0.07, 0.03, 10, pit));
    });
    m.at(chain(translate(-0.48, BED_FLOOR + 0.03, 1.55), rotY(0.06)), () => m.box(0, 0, 0, 0.2, 0.05, 1.7, { layer: L.wood, uvRot: true }));
    m.at(chain(translate(-0.4, BED_FLOOR + 0.08, 1.5), rotY(-0.1)), () => m.box(0, 0, 0, 0.2, 0.05, 1.5, { layer: L.wood, uvRot: true, col: [0.85, 0.8, 0.72] }));

    /* ---- underneath ---- */
    m.box(0, 0.37, 0, 1.4, 0.16, 4.6, pit);
    stick(m, [-0.82, WHEEL_R, AXLE_R], [0.82, WHEEL_R, AXLE_R], 0.1, 0.1, pit);
    m.box(0, WHEEL_R, AXLE_R, 0.3, 0.27, 0.3, pit);
    m.at(chain(translate(0.6, 0.31, REAR - 0.34), rotX(Math.PI / 2)), () => m.cyl(0.035, 0.035, 0.42, 7, { layer: L.metal, col: [0.4, 0.34, 0.3], tile: 0.3 }));

    /* ---- wheels: steel rims, small hubcaps, the fronts left turned ---- */
    const wheel = (s, z, steer) => m.at(chain(translate(s * 0.835, WHEEL_R, z), rotY(steer), rotZ((-s * Math.PI) / 2), translate(0, -0.13, 0)), () => {
      m.cyl(WHEEL_R, WHEEL_R, 0.26, 14, { layer: L.tire, cap: rubber, capBottom: true });
      m.at(translate(0, 0.262, 0), () => m.cyl(0.245, 0.235, 0.012, 12, { layer: L.plain, col: [0.42, 0.42, 0.39] }));
      m.at(translate(0, 0.274, 0), () => m.cyl(0.19, 0.19, 0.004, 12, pit, true));          // the slotted ring
      m.at(translate(0, 0.278, 0), () => m.cyl(0.12, 0.085, 0.035, 10, chrome));
    });
    for (const s of [-1, 1]) { wheel(s, AXLE_F, 0.3); wheel(s, AXLE_R, 0); }
  });
}
