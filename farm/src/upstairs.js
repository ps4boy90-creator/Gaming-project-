/**
 * The staircase and everything at the top of it: a landing with a balustrade
 * round the stairwell, a bedroom either side, and a bathroom over the front
 * door. Every room has a door and every door opens.
 *
 * It is built with the same kit as the ground floor (see interior.js) and to
 * the same rule: furniture is modelled round, the house stays flat-walled.
 * What is new here is height. Two floors share one footprint, so colliders
 * are tagged with the storey they belong to and lamps only light their own.
 *
 *            -4.4        -1.1   1.1         4.4
 *    -3.4  +-------------+--+---+-----------+
 *          |             |  |^^^|  drawers
 *          |  west bed   |  |^^^|      east bedroom
 *          |   (dark)    ·  +---·   (the lit window)
 *          |        desk |landing|  bed
 *     1.6  |             +--. --+
 *          |             | bath |
 *     3.4  +----window---+--win-+---window--+
 */
import { wall, plate as holed } from './geom.js';
import { lathe, roundBox, tube, drape, sphere } from './detail.js';
import { L } from './textures.js';
import { rotX, rotY, rotZ, translate, scaling, chain } from './math.js';
import { makeKit } from './interior.js';
import { makeRng } from '../../src/core/rng.js';

const WARM = [1.0, 0.72, 0.42];

export function buildUpstairs(m, w, M, H, env) {
  const {
    setLevel, run, obb, F, CH, IW, ID, PX, PT, PORTRAIT, LANDSCAPE, white, oak, dark, pine, china, brass, chrome,
    enamel, black, pit, cloth, glow, light, usable, glows, at, leg, frame, lamp, hang, chair, mug,
  } = makeKit(m, w, M, H, env);
  const U = H.split - F, UC = H.top - F - 0.1;          // upper floor and ceiling, above the ground floor
  const { x0: sx0, x1: sx1, zs: sz, zb, zt } = H.stair;
  const BZ = 1.56;                                      // the bathroom wall
  const D0 = -0.65, D1 = 0.2;                           // the bedroom doorways, along Z
  const HX = PX - PT / 2;                               // the landing's side walls
  const rng = makeRng(404);

  /* ---- pieces ---- */
  const knob = (mat = brass) => lathe(m, [[0.014, 0], [0.006, 0.008], [0.006, 0.018], [0.015, 0.026], [0.012, 0.036], [0, 0.038]], 10, mat);
  const post = (h, mat) => lathe(m, [[0.03, 0], [0.036, 0.04], [0.026, 0.1], [0.034, h * 0.34], [0.04, h * 0.42], [0.028, h * 0.47],
    [0.036, h * 0.76], [0.03, h * 0.92], [0.042, h * 0.95], [0.03, h * 0.985], [0, h]], 12, mat);

  /** A bed with turned posts and spindle ends, head at -Z, made up. */
  const bed = (wd, quilt, sheet) => {
    const hl = 1.0, spindles = Math.round(wd / 0.13);
    for (const sx of [-1, 1]) {
      at((sx * wd) / 2, 0, -hl, 0, () => post(1.28, dark));
      at((sx * wd) / 2, 0, hl, 0, () => post(0.8, dark));
      roundBox(m, (sx * wd) / 2, 0.36, 0, 0.04, 0.16, 2 * hl, 0.012, 1, dark);
    }
    for (const [z, lo, hi] of [[-hl, 0.5, 1.08], [hl, 0.4, 0.66]]) {
      roundBox(m, 0, hi, z, wd, 0.09, 0.04, 0.016, 1, dark);
      roundBox(m, 0, lo, z, wd, 0.09, 0.04, 0.012, 1, dark);
      for (let k = 1; k < spindles; k++) tube(m, [[-wd / 2 + (k * wd) / spindles, lo + 0.04, z], [-wd / 2 + (k * wd) / spindles, hi - 0.04, z]], 0.011, 6, dark, false);
    }
    roundBox(m, 0, 0.5, 0, wd - 0.06, 0.2, 2 * hl - 0.08, 0.06, 3, cloth(0.8, 0.78, 0.72));       // mattress
    roundBox(m, 0, 0.535, 0.24, wd + 0.06, 0.2, 1.4, 0.06, 3, quilt);                               // quilt, over the sides
    roundBox(m, 0, 0.64, -0.46, wd + 0.04, 0.06, 0.22, 0.03, 2, sheet);                             // the sheet turned down
    const n = wd > 1.2 ? 2 : 1;
    for (let k = 0; k < n; k++) m.at(chain(translate(((k - (n - 1) / 2) * wd) / 2, 0.67, -0.76), rotX(0.12)), () =>
      roundBox(m, 0, 0, 0, wd / n - 0.14, 0.13, 0.38, 0.06, 4, cloth(0.86, 0.84, 0.8)));
  };

  const nightstand = (mat) => {
    roundBox(m, 0, 0.37, 0, 0.42, 0.44, 0.36, 0.012, 1, mat);
    roundBox(m, 0, 0.605, 0, 0.46, 0.03, 0.4, 0.012, 2, mat);
    for (const sx of [-1, 1]) for (const s2 of [-1, 1]) leg(sx * 0.17, s2 * 0.14, 0.15, 0.022, mat, 8);
    roundBox(m, 0, 0.43, 0.184, 0.34, 0.16, 0.012, 0.005, 1, mat);
    m.at(chain(translate(0, 0.43, 0.19), rotX(Math.PI / 2)), () => knob());
  };

  const drawers = (wd, rows, mat) => {
    roundBox(m, 0, 0.56, 0, wd, 0.86, 0.46, 0.012, 1, mat);
    roundBox(m, 0, 1.005, 0, wd + 0.05, 0.035, 0.5, 0.014, 2, mat);
    for (const sx of [-1, 1]) for (const s2 of [-1, 1]) leg(sx * (wd / 2 - 0.06), s2 * 0.18, 0.14, 0.028, mat, 8);
    const dh = 0.8 / rows;
    for (let r = 0; r < rows; r++) {
      const y = 0.17 + dh * (r + 0.5);
      roundBox(m, 0, y, 0.232, wd - 0.08, dh - 0.03, 0.014, 0.006, 1, mat);
      for (const sx of [-1, 1]) m.at(chain(translate(sx * wd * 0.26, y, 0.24), rotX(Math.PI / 2)), () => knob());
    }
  };

  /** A casing round a doorway in a partition, on both faces. `along` is the axis the wall runs on. */
  const cased = (x, z, along, a, b, thick) => {
    for (const side of [-1, 1]) {
      const off = side * (thick / 2 + 0.01);
      if (along === 'z') {
        for (const e of [a, b]) m.box(x + off, U + 1.03, e + (e === a ? -0.045 : 0.045), 0.02, 2.06, 0.09, white);
        m.box(x + off, U + 2.08, (a + b) / 2, 0.024, 0.1, b - a + 0.22, white);
      } else {
        for (const e of [a, b]) m.box(e + (e === a ? -0.045 : 0.045), U + 1.03, z + off, 0.09, 2.06, 0.02, white);
        m.box((a + b) / 2, U + 2.08, z + off, b - a + 0.22, 0.1, 0.024, white);
      }
    }
  };
  const skirt = (x0, z0, x1, z1) => {
    const dx = x1 - x0, dz = z1 - z0;
    m.box((x0 + x1) / 2, U + 0.065, (z0 + z1) / 2, Math.abs(dx) + (dz ? 0.018 : 0), 0.13, Math.abs(dz) + (dx ? 0.018 : 0), white);
  };

  m.at(chain(M, translate(0, F, 0)), () => {
    /* ============================================================ the flight */
    setLevel(0);
    const steps = 14, rise = U / steps, going = (zb - zt) / (steps - 1), sw = sx1 - sx0, sc = (sx0 + sx1) / 2;
    for (let i = 0; i < steps - 1; i++) {
      const top = (i + 1) * rise, zc = zb - (i + 0.5) * going;
      m.box(sc, top / 2, zc, sw, top, going, { layer: L.plain, col: [0.78, 0.76, 0.7], skip: 'y' });
      roundBox(m, sc, top + 0.013, zc + 0.014, sw, 0.03, going + 0.032, 0.01, 1, oak);
    }
    // The head of the flight: a square of floor inside the well, level with
    // the landing, wide enough to turn on and step off sideways.
    m.box(sc, U / 2, (zt - ID) / 2, sw, U, zt + ID, { layer: L.plain, col: [0.78, 0.76, 0.7], skip: 'y' });
    m.quad([sx0, U + 0.002, zt + 0.02], [sx1, U + 0.002, zt + 0.02], [sx1, U + 0.002, -ID], [sx0, U + 0.002, -ID], { layer: L.wood, col: [0.7, 0.54, 0.4], gloss: 0.25 });
    roundBox(m, sc, U - 0.013, zt + 0.014, sw, 0.03, 0.06, 0.01, 1, oak);
    tube(m, [[sx1 - 0.07, 0.95, zb + 0.1], [sx1 - 0.07, U + 0.95, zt + 0.1]], 0.02, 8, oak);          // handrail
    for (const t of [0.08, 0.5, 0.92]) {
      const z = zb + 0.1 + (zt - zb) * t, y = 0.95 + U * t;
      tube(m, [[sx1 - 0.07, y - 0.025, z], [sx1 - 0.07, y - 0.06, z], [sx1, y - 0.07, z]], 0.007, 6, brass, false);
    }

    /* ============================================================= the shell */
    setLevel(1);
    holed(m, -IW, -ID, IW, ID, U, [sx0, -ID, sx1, sz], { layer: L.wood, col: [0.7, 0.54, 0.4], gloss: 0.25 });
    m.quad([-IW, UC, -ID], [IW, UC, -ID], [IW, UC, ID], [-IW, UC, ID], { layer: L.plaster });
    m.quad([sx0, CH, -ID], [sx0, CH, sz], [sx0, U, sz], [sx0, U, -ID], white);          // the thickness of the floor,
    m.quad([sx0, CH, sz], [sx1, CH, sz], [sx1, U, sz], [sx0, U, sz], white);            // seen from the stairs

    // Partitions, each with a bedroom doorway, and the bathroom wall across the front.
    const doorway = [{ x0: D0, x1: D1, y0: U, y1: U + 2.0 }];
    m.at(chain(translate(-PX - PT / 2, 0, 0), rotY(-Math.PI / 2)), () => {
      wall(m, -ID, BZ, CH, UC, doorway, env.bedW, env.hall, PT, white);
      wall(m, BZ, ID, CH, UC, [], env.bedW, env.bath, PT, white);
    });
    m.at(chain(translate(PX - PT / 2, 0, 0), rotY(-Math.PI / 2)), () => {
      wall(m, -ID, BZ, CH, UC, doorway, env.hall, env.bedE, PT, white);
      wall(m, BZ, ID, CH, UC, [], env.bath, env.bedE, PT, white);
    });
    m.at(chain(translate(0, 0, BZ), rotY(Math.PI)), () =>
      wall(m, -HX, HX, U, UC, [{ x0: -0.4, x1: 0.4, y0: U, y1: U + 2.0 }], env.hall, env.bath, 0.06, white));
    for (const px of [-PX, PX]) { run(px, -ID, px, D0); run(px, D1, px, ID); cased(px, 0, 'z', D0, D1, PT); }
    run(-HX, BZ + 0.03, -0.4, BZ + 0.03, 0.035); run(0.4, BZ + 0.03, HX, BZ + 0.03, 0.035);
    cased(0, BZ + 0.03, 'x', -0.4, 0.4, 0.06);

    // Three doors. The bedrooms' open into the rooms; the bathroom's opens
    // out, because there is a bath where it would otherwise have to go.
    hang(-PX, D1, D1 - D0, 1.98, Math.PI / 2, Math.PI / 2 + 1.5, U);
    hang(PX, D1, D1 - D0, 1.98, Math.PI / 2, Math.PI / 2 - 1.5, U);
    hang(0.4, BZ + 0.03, 0.8, 1.98, Math.PI, Math.PI - 1.5, U);

    /* =========================================================== the landing */
    {
      // Balustrade round the well: newels, a rail, and a turned baluster every hand's width.
      const edge = zt - 0.04, rail = U + 0.92;
      const newel = (x, z) => at(x, U, z, 0, () => {
        roundBox(m, 0, 0.52, 0, 0.09, 1.04, 0.09, 0.012, 1, dark);
        m.at(translate(0, 1.04, 0), () => lathe(m, [[0.05, 0], [0.056, 0.012], [0.03, 0.026], [0.046, 0.06], [0.03, 0.092], [0, 0.104]], 12, dark));
      });
      newel(sx0, sz); newel(sx0, edge); newel(sx1 - 0.05, sz);
      tube(m, [[sx0, rail, sz], [sx0, rail, edge]], 0.025, 8, dark);
      tube(m, [[sx0, rail, sz], [sx1 - 0.05, rail, sz]], 0.025, 8, dark);
      const baluster = (x, z) => at(x, U, z, 0, () => lathe(m, [[0.013, 0], [0.018, 0.06], [0.011, 0.13], [0.02, 0.36], [0.011, 0.5], [0.017, 0.78], [0.012, 0.9]], 8, white));
      for (let z = sz - 0.13; z > edge + 0.08; z -= 0.13) baluster(sx0, z);
      for (let x = sx0 + 0.13; x < sx1 - 0.1; x += 0.13) baluster(x, sz);
      run(sx0, edge, sx0, sz, 0.05); run(sx0, sz, sx1, sz, 0.05);

      m.quad([-0.74, U + 0.006, 1.3], [-0.14, U + 0.006, 1.3], [-0.14, U + 0.006, -2.9], [-0.74, U + 0.006, -2.9], { layer: L.rug, fit: true, col: [0.6, 0.58, 0.54] });
      at(-HX + 0.2, U, 1.12, Math.PI / 2, () => {                                   // a stand with a fern on it
        lathe(m, [[0.17, 0.7], [0.175, 0.715], [0.16, 0.73], [0, 0.732]], 20, oak);
        lathe(m, [[0.12, 0], [0.13, 0.014], [0.03, 0.04], [0.024, 0.3], [0.04, 0.5], [0.024, 0.62], [0.1, 0.7]], 14, oak);
        at(0, 0.732, 0, 0, () => {
          lathe(m, [[0, 0.004], [0.07, 0.004], [0.09, 0.03], [0.11, 0.15], [0.12, 0.16], [0.1, 0.16], [0.08, 0.04], [0, 0.03]], 16, { layer: L.plain, col: [0.5, 0.26, 0.16], gloss: 0.5 });
          for (let k = 0; k < 14; k++) {
            const a = k * 0.449 + rng(), r = 0.12 + rng() * 0.16, h = 0.24 + rng() * 0.2;
            tube(m, [[0, 0.14, 0], [Math.cos(a) * r * 0.4, 0.14 + h, Math.sin(a) * r * 0.4], [Math.cos(a) * r, 0.14 + h * 0.86, Math.sin(a) * r], [Math.cos(a) * r * 1.3, 0.14 + h * 0.5, Math.sin(a) * r * 1.3]],
              (t) => 0.012 * Math.sin(t * Math.PI) + 0.003, 5, { layer: L.plain, col: [0.14, 0.26 + rng() * 0.1, 0.1] }, false);
          }
        });
      });
      obb(-HX + 0.2, 1.12, 0.18, 0.18);
      at(-HX + 0.004, U + 1.55, -1.7, Math.PI / 2, () => frame(0.36, 0.46, PORTRAIT));
      at(-HX + 0.004, U + 1.55, -2.5, Math.PI / 2, () => frame(0.5, 0.36, LANDSCAPE, oak));
      skirt(-HX + 0.01, -ID, -HX + 0.01, D0 - 0.09); skirt(-HX + 0.01, D1 + 0.09, -HX + 0.01, BZ);
      skirt(HX - 0.01, sz, HX - 0.01, D0 - 0.09); skirt(HX - 0.01, D1 + 0.09, HX - 0.01, BZ);

      at(-0.45, UC, 0.4, 0, () => {                                                // the landing light
        lathe(m, [[0.09, 0], [0.09, -0.03], [0.05, -0.05]], 16, brass);
        glows('landing', () => m.at(translate(0, -0.11, 0), () => sphere(m, 0.1, 16, glow([1, 0.9, 0.7], 1.3), 0.7)));
        usable([0, -0.11, 0], 2.7, { group: 'landing', noun: 'the light' });
      });
      light([-0.45, UC - 0.3, 0.4], WARM.map((c) => c * 0.55), 7.5, [-HX, -ID, HX, BZ], 'landing');
    }

    /* ========================================================== east bedroom */
    {
      const X0 = PX + PT / 2, quilt = cloth(0.3, 0.36, 0.52);
      m.box(IW - 0.18, U + (UC - U) / 2, -0.8, 0.36, UC - U, 1.7, { ...env.bedE, skip: 'yY' });          // the chimney, coming up through
      obb(IW - 0.18, -0.8, 0.2, 0.86);
      m.quad([2.0, U + 0.006, 1.95], [3.9, U + 0.006, 1.95], [3.9, U + 0.006, -0.4], [2.0, U + 0.006, -0.4], { layer: L.rug, fit: true, col: [0.5, 0.56, 0.66] });
      at(3.3, U, 0.78, -Math.PI / 2, () => {
        bed(1.4, quilt, cloth(0.84, 0.82, 0.76));
        m.at(chain(translate(0.2, 0.64, 0.5), rotY(0.4)), () => roundBox(m, 0, 0, 0, 0.5, 0.05, 0.36, 0.024, 2, cloth(0.56, 0.5, 0.36)));   // a folded throw
      });
      obb(3.3, 0.78, 1.06, 0.76);
      for (const [x, z] of [[2.12, 1.62], [2.2, 1.78]]) m.at(chain(translate(x, U + 0.035, z), rotY(-1.4 + (z - 1.62))), () =>
        roundBox(m, 0, 0, 0, 0.1, 0.07, 0.26, 0.03, 2, cloth(0.36, 0.2, 0.16)));                                                       // slippers
      at(IW - 0.26, U, 1.74, -Math.PI / 2, () => {
        nightstand(dark);
        at(0.06, 0.62, -0.04, 0, () => lamp(0.44, 0.15, 'bedE', { layer: L.plain, col: [0.76, 0.74, 0.62], gloss: 0.9 }));
        at(-0.13, 0.62, 0.1, 0.4, () => {                                          // an alarm clock, stopped
          m.at(chain(translate(0, 0.06, 0), rotX(Math.PI / 2)), () => lathe(m, [[0.05, -0.02], [0.054, -0.015], [0.054, 0.015], [0.05, 0.02], [0, 0.02]], 16, brass));
          m.quad([-0.044, 0.016, 0.0205], [0.044, 0.016, 0.0205], [0.044, 0.104, 0.0205], [-0.044, 0.104, 0.0205], { layer: L.clockface, fit: [0.07, 0.07, 0.93, 0.93], gloss: 0.6 });
          for (const s of [-1, 1]) { at(s * 0.03, 0.118, 0, 0, () => sphere(m, 0.017, 8, brass, 0.7)); tube(m, [[s * 0.03, 0, 0.01], [s * 0.022, 0.02, 0]], 0.004, 5, brass, false); }
        });
        at(-0.1, 0.62, -0.1, 0, () => lathe(m, [[0, 0.003], [0.03, 0.003], [0.034, 0.1], [0.031, 0.1], [0.028, 0.012], [0, 0.01]], 12, { layer: L.plain, col: [0.5, 0.56, 0.58], gloss: 1 }));
      });
      obb(IW - 0.26, 1.74, 0.21, 0.24);
      at(3.5, U, -ID + 0.25, 0, () => {
        drawers(1.05, 4, dark);
        // On top: a mirror on a stand, a brush, a box with its lid shut.
        at(0, 1.022, -0.1, 0, () => {
          for (const s of [-1, 1]) tube(m, [[s * 0.24, 0, 0], [s * 0.24, 0.5, 0]], 0.012, 8, dark);
          m.at(chain(translate(0, 0.3, 0), rotX(-0.14)), () => {
            frame(0.4, 0.5, [0, 0, 0.01, 0.01], dark);
            m.quad([-0.2, -0.25, 0.01], [0.2, -0.25, 0.01], [0.2, 0.25, 0.01], [-0.2, 0.25, 0.01], { layer: L.glass, fit: true, col: [2.2, 2.3, 2.5], gloss: 1 });
          });
        });
        m.at(chain(translate(-0.3, 1.04, 0.1), rotY(0.5)), () => { roundBox(m, 0, 0, 0, 0.06, 0.03, 0.12, 0.014, 2, dark); tube(m, [[0, 0, 0.06], [0, 0, 0.16]], 0.008, 6, dark); });
        roundBox(m, 0.32, 1.06, 0.1, 0.16, 0.07, 0.11, 0.012, 1, { layer: L.grain, col: [0.9, 0.6, 0.4], gloss: 0.7 });
      });
      obb(3.5, -ID + 0.25, 0.56, 0.26);
      at(1.75, U, -2.7, 0.7, () => {                                               // a chair with a shirt over the back
        chair(cloth(0.3, 0.34, 0.44));
        m.at(translate(-0.22, 0.5, -0.31), () => drape(m, 0.44, 0.48, 3, 0.016, cloth(0.72, 0.74, 0.8)));
      });
      obb(1.75, -2.7, 0.24, 0.24);
      at(IW - 0.004, U + 1.75, 0.78, -Math.PI / 2, () => frame(0.5, 0.38, LANDSCAPE));
      skirt(X0 + 0.01, -ID, X0 + 0.01, D0 - 0.09); skirt(X0 + 0.01, D1 + 0.09, X0 + 0.01, ID);
      skirt(X0, -ID + 0.01, IW, -ID + 0.01); skirt(X0, ID - 0.01, IW, ID - 0.01);
      light([IW - 0.4, U + 1.02, 1.7], WARM.map((c) => c * 0.85), 7, [X0, -ID, IW, ID], 'bedE');
    }

    /* ========================================================== west bedroom */
    {
      const X1 = -PX - PT / 2;
      m.quad([-3.3, U + 0.006, 1.6], [-1.7, U + 0.006, 1.6], [-1.7, U + 0.006, -0.9], [-3.3, U + 0.006, -0.9], { layer: L.rug, fit: true, col: [0.7, 0.56, 0.5] });
      at(-3.33, U, -0.15, Math.PI / 2, () => {
        bed(0.95, cloth(0.56, 0.3, 0.26), cloth(0.84, 0.82, 0.76));
        at(0.1, 0.64, -0.36, 0.5, () => {                                          // a bear, sitting up against the pillow
          const fur = cloth(0.46, 0.32, 0.2);
          m.at(translate(0, 0.1, 0), () => sphere(m, 0.09, 12, fur, 1.15));
          m.at(translate(0, 0.26, 0.01), () => sphere(m, 0.068, 12, fur));
          for (const s of [-1, 1]) {
            m.at(translate(s * 0.05, 0.32, 0), () => sphere(m, 0.024, 8, fur));
            tube(m, [[s * 0.07, 0.16, 0.02], [s * 0.13, 0.1, 0.08]], 0.03, 8, fur);
            tube(m, [[s * 0.05, 0.04, 0.05], [s * 0.08, 0.03, 0.17]], 0.034, 8, fur);
            m.at(translate(s * 0.026, 0.275, 0.062), () => sphere(m, 0.008, 6, black));
          }
          m.at(translate(0, 0.245, 0.062), () => sphere(m, 0.026, 8, cloth(0.66, 0.54, 0.38), 0.8));
        });
      });
      obb(-3.33, -0.15, 1.06, 0.52);
      at(-IW + 0.26, U, 0.72, Math.PI / 2, () => {
        nightstand(pine);
        at(0.04, 0.62, -0.03, 0, () => lamp(0.4, 0.14, 'bedW', { layer: L.plain, col: [0.3, 0.4, 0.56], gloss: 0.9 }));
        m.at(chain(translate(-0.1, 0.635, 0.1), rotY(0.3)), () => roundBox(m, 0, 0, 0, 0.13, 0.026, 0.18, 0.005, 1, cloth(0.42, 0.14, 0.12)));
      });
      obb(-IW + 0.26, 0.72, 0.21, 0.24);
      // A desk under the front window, with the chair pushed back from it.
      at(-2.75, U, ID - 0.34, Math.PI, () => {
        roundBox(m, 0, 0.745, 0, 1.15, 0.035, 0.58, 0.014, 2, pine);
        m.box(0, 0.67, 0, 1.0, 0.1, 0.46, pine);
        for (const sx of [-1, 1]) for (const s2 of [-1, 1]) at(sx * 0.5, 0, s2 * 0.22, 0, () => lathe(m, [[0.016, 0], [0.022, 0.06], [0.03, 0.62], [0.03, 0.72]], 10, pine));
        m.at(chain(translate(0, 0.67, 0.236), rotX(Math.PI / 2)), () => knob());
        for (let k = 0; k < 4; k++) m.at(chain(translate(0.36, 0.777 + k * 0.03, -0.08), rotY(k * 0.23 - 0.3)), () =>
          roundBox(m, 0, 0, 0, 0.15, 0.028, 0.21, 0.005, 1, cloth(...[[0.16, 0.24, 0.2], [0.42, 0.14, 0.12], [0.5, 0.42, 0.22], [0.16, 0.18, 0.34]][k])));
        m.at(chain(translate(-0.05, 0.7635, 0.04), rotY(0.15)), () => m.quad([-0.11, 0, 0.15], [0.11, 0, 0.15], [0.11, 0, -0.15], [-0.11, 0, -0.15], { layer: L.print, fit: [0.03, 0.05, 0.47, 0.95] }));
        at(-0.4, 0.763, -0.12, 0, () => {                                          // pencils in a pot
          lathe(m, [[0, 0.003], [0.035, 0.003], [0.038, 0.09], [0.034, 0.09], [0.032, 0.01], [0, 0.008]], 12, { layer: L.plain, col: [0.5, 0.2, 0.14], gloss: 0.8 });
          for (let k = 0; k < 5; k++) tube(m, [[Math.cos(k * 1.3) * 0.012, 0.01, Math.sin(k * 1.3) * 0.012], [Math.cos(k * 1.3) * 0.03, 0.15 + (k % 2) * 0.02, Math.sin(k * 1.3) * 0.03]], 0.004, 5,
            { layer: L.plain, col: [[0.7, 0.6, 0.1], [0.5, 0.1, 0.1], [0.1, 0.3, 0.5]][k % 3] });
        });
        at(-0.36, 0.763, 0.12, 0, () => {                                          // an anglepoise, off
          lathe(m, [[0.07, 0], [0.072, 0.012], [0.02, 0.022], [0.012, 0.04]], 14, black);
          tube(m, [[0, 0.03, 0], [0.04, 0.28, 0], [0.2, 0.42, 0.02]], 0.007, 6, chrome);
          m.at(chain(translate(0.24, 0.4, 0.02), rotZ(-2.2)), () => lathe(m, [[0.02, 0], [0.03, 0.03], [0.075, 0.11]], 14, black));
        });
      });
      obb(-2.75, ID - 0.34, 0.6, 0.31);
      at(-2.62, U, ID - 1.02, 0.25, () => chair(cloth(0.26, 0.34, 0.28)));
      obb(-2.62, ID - 1.02, 0.24, 0.24);
      // Low shelves against the back wall, half full.
      at(-2.55, U, -ID + 0.17, 0, () => {
        const wd = 1.1, hg = 0.95, dp = 0.3;
        for (const s of [-1, 1]) m.box(s * (wd / 2 - 0.011), hg / 2, 0, 0.022, hg, dp, pine);
        m.box(0, hg / 2, -dp / 2 + 0.006, wd, hg, 0.012, pine);
        roundBox(m, 0, hg + 0.016, 0.01, wd + 0.05, 0.034, dp + 0.04, 0.014, 2, pine);
        const palette = [[0.42, 0.14, 0.12], [0.14, 0.24, 0.2], [0.16, 0.18, 0.34], [0.5, 0.4, 0.22], [0.56, 0.52, 0.44]];
        for (const y of [0.04, 0.36, 0.66]) {
          m.box(0, y + 0.011, 0, wd - 0.04, 0.022, dp - 0.02, pine);
          let x = -wd / 2 + 0.04;
          const until = -wd / 2 + 0.2 + rng() * 0.7;
          while (x < until) {
            const bw = 0.022 + rng() * 0.03, bh = 0.17 + rng() * 0.09, bd = 0.15 + rng() * 0.06;
            roundBox(m, x + bw / 2, y + 0.022 + bh / 2, -dp / 2 + 0.02 + bd / 2, bw, bh, bd, 0.004, 1, cloth(...palette[(rng() * palette.length) | 0]));
            x += bw + 0.003;
          }
        }
        at(0.3, hg + 0.034, 0, 0, () => {                                           // a wind-up tin car on top
          roundBox(m, 0, 0.04, 0, 0.16, 0.05, 0.07, 0.02, 2, { layer: L.plain, col: [0.56, 0.12, 0.1], gloss: 0.8 });
          roundBox(m, -0.01, 0.075, 0, 0.08, 0.04, 0.06, 0.016, 2, { layer: L.plain, col: [0.56, 0.12, 0.1], gloss: 0.8 });
          for (const sx of [-1, 1]) for (const s2 of [-1, 1]) m.at(chain(translate(sx * 0.05, 0.02, s2 * 0.036), rotX(Math.PI / 2)), () => lathe(m, [[0.02, -0.006], [0.02, 0.006], [0, 0.006]], 10, black));
        });
      });
      obb(-2.55, -ID + 0.17, 0.58, 0.17);
      at(-IW + 0.004, U + 1.7, -0.15, Math.PI / 2, () => frame(0.4, 0.3, LANDSCAPE, pine));
      skirt(X1 - 0.01, -ID, X1 - 0.01, D0 - 0.09); skirt(X1 - 0.01, D1 + 0.09, X1 - 0.01, ID);
      skirt(-IW, -ID + 0.01, X1, -ID + 0.01); skirt(-IW, ID - 0.01, X1, ID - 0.01);
      light([-IW + 0.4, U + 1.0, 0.7], WARM.map((c) => c * 0.8), 7, [-IW, -ID, X1, ID], 'bedW');
    }

    /* ============================================================== bathroom */
    {
      const Z0 = BZ + 0.06, white2 = { layer: L.plain, col: [0.84, 0.84, 0.8], gloss: 0.9 }, tiles = { layer: L.tile, gloss: 0.6 };
      m.quad([-HX, U + 0.004, ID], [HX, U + 0.004, ID], [HX, U + 0.004, Z0], [-HX, U + 0.004, Z0], { layer: L.lino, gloss: 0.3, col: [0.9, 0.96, 1] });
      m.quad([-HX + 0.004, U, Z0], [-HX + 0.004, U, ID], [-HX + 0.004, U + 1.25, ID], [-HX + 0.004, U + 1.25, Z0], tiles);      // tiled to the dado
      m.quad([HX - 0.004, U, ID], [HX - 0.004, U, Z0], [HX - 0.004, U + 1.25, Z0], [HX - 0.004, U + 1.25, ID], tiles);
      m.quad([-HX, U, ID - 0.004], [HX, U, ID - 0.004], [HX, U + 0.84, ID - 0.004], [-HX, U + 0.84, ID - 0.004], tiles);
      // A roll-top bath on four feet: a bowl turned on the lathe, then drawn out to length.
      at(-0.64, U, 2.5, 0, () => {
        m.at(chain(translate(0, 0.12, 0), scaling(1, 1, 2.1)), () => lathe(m, [[0.16, 0], [0.26, 0.03], [0.33, 0.2], [0.36, 0.46], [0.385, 0.49], [0.375, 0.51],
          [0.345, 0.48], [0.31, 0.2], [0.22, 0.07], [0, 0.06]], 24, white2));
        for (const sx of [-1, 1]) for (const s2 of [-1, 1]) at(sx * 0.2, 0, s2 * 0.5, 0, () => lathe(m, [[0.03, 0], [0.046, 0.03], [0.03, 0.08], [0.042, 0.14]], 10, black));
        tube(m, [[0.1, 0, -0.84], [0.1, 0.78, -0.84], [0.1, 0.84, -0.8], [0.1, 0.84, -0.68], [0.1, 0.8, -0.64]], 0.014, 8, chrome);
        tube(m, [[-0.1, 0, -0.84], [-0.1, 0.78, -0.84], [-0.1, 0.84, -0.8], [-0.1, 0.84, -0.68], [-0.1, 0.8, -0.64]], 0.014, 8, chrome);
        for (const s of [-1, 1]) at(s * 0.1, 0.86, -0.82, 0, () => { lathe(m, [[0.012, 0], [0.012, 0.03], [0.02, 0.04], [0, 0.046]], 10, chrome); tube(m, [[-0.03, 0.035, 0], [0.03, 0.035, 0]], 0.005, 6, chrome); });
      });
      obb(-0.64, 2.5, 0.4, 0.84);
      // Lavatory under the window, lid down.
      at(0.3, U, ID - 0.38, Math.PI, () => {
        m.at(scaling(1, 1, 1.25), () => lathe(m, [[0.11, 0], [0.13, 0.03], [0.1, 0.1], [0.13, 0.26], [0.19, 0.36], [0.2, 0.4], [0, 0.4]], 20, white2));
        m.at(chain(translate(0, 0.4, 0), scaling(1, 1, 1.25)), () => lathe(m, [[0.205, 0], [0.21, 0.012], [0.2, 0.024], [0, 0.028]], 20, { layer: L.grain, col: [0.5, 0.36, 0.26], gloss: 0.7 }));
        roundBox(m, 0, 0.62, -0.3, 0.44, 0.36, 0.17, 0.03, 2, white2);
        roundBox(m, 0, 0.815, -0.3, 0.47, 0.035, 0.2, 0.014, 1, white2);
        tube(m, [[-0.17, 0.73, -0.215], [-0.17, 0.73, -0.19], [-0.1, 0.72, -0.19]], 0.007, 6, chrome);
      });
      obb(0.3, ID - 0.42, 0.24, 0.36);
      // Pedestal basin on the bedroom wall, and a mirror over it.
      at(HX - 0.27, U, 2.3, -Math.PI / 2, () => {
        lathe(m, [[0.1, 0], [0.11, 0.03], [0.07, 0.1], [0.06, 0.58], [0.1, 0.7]], 16, white2);
        m.at(scaling(1.25, 1, 1), () => lathe(m, [[0.05, 0.69], [0.19, 0.71], [0.25, 0.81], [0.26, 0.85], [0.24, 0.85], [0.21, 0.79], [0.06, 0.745], [0, 0.745]], 22, white2));
        for (const s of [-1, 1]) at(s * 0.13, 0.85, -0.2, 0, () => { lathe(m, [[0.016, 0], [0.012, 0.04], [0.022, 0.05], [0, 0.056]], 10, chrome); tube(m, [[-0.026, 0.045, 0], [0.026, 0.045, 0]], 0.005, 6, chrome); });
        tube(m, [[0, 0.85, -0.2], [0, 0.93, -0.2], [0, 0.94, -0.12], [0, 0.91, -0.1]], 0.009, 8, chrome);
        m.at(chain(translate(0.2, 0.862, -0.12), rotY(0.4)), () => roundBox(m, 0, 0, 0, 0.07, 0.024, 0.045, 0.011, 2, { layer: L.plain, col: [0.8, 0.74, 0.5] }));   // soap
        at(-0.2, 0.85, -0.14, 0, () => {                                            // a tooth-glass
          lathe(m, [[0, 0.003], [0.026, 0.003], [0.03, 0.09], [0.027, 0.09], [0.024, 0.012], [0, 0.01]], 12, { layer: L.plain, col: [0.5, 0.56, 0.58], gloss: 1 });
          for (const [a, c] of [[0.3, [0.5, 0.1, 0.1]], [2.4, [0.1, 0.3, 0.5]]]) tube(m, [[Math.cos(a) * 0.008, 0.012, Math.sin(a) * 0.008], [Math.cos(a) * 0.03, 0.17, Math.sin(a) * 0.03]], 0.004, 5, { layer: L.plain, col: c });
        });
      });
      obb(HX - 0.27, 2.3, 0.27, 0.3);
      at(HX - 0.008, U + 1.56, 2.3, -Math.PI / 2, () => {
        frame(0.42, 0.56, [0, 0, 0.01, 0.01], white);
        m.quad([-0.21, -0.28, 0.01], [0.21, -0.28, 0.01], [0.21, 0.28, 0.01], [-0.21, 0.28, 0.01], { layer: L.glass, fit: true, col: [2.2, 2.3, 2.5], gloss: 1 });
        m.at(translate(0, 0.42, 0.03), () => {                                      // the light over the mirror
          m.box(0, 0, -0.01, 0.2, 0.05, 0.03, chrome);
          glows('bath', () => m.at(chain(translate(0, 0, 0.05), rotZ(Math.PI / 2)), () => lathe(m, [[0.03, -0.09], [0.036, -0.06], [0.036, 0.06], [0.03, 0.09], [0, 0.09]], 12, glow([0.96, 0.98, 0.9], 1.6))));
          usable([0, 0, 0.05], 2.4, { group: 'bath', noun: 'the light' });
        });
      });
      // Towel on a rail by the door, and a mat.
      at(0.72, U, Z0 + 0.004, 0, () => {
        tube(m, [[-0.24, 1.12, 0.07], [0.24, 1.12, 0.07]], 0.009, 8, chrome);
        for (const s of [-1, 1]) tube(m, [[s * 0.24, 1.12, 0], [s * 0.24, 1.12, 0.07]], 0.007, 6, chrome, false);
        m.at(translate(-0.19, 0.5, 0.085), () => drape(m, 0.38, 0.63, 2, 0.012, cloth(0.6, 0.7, 0.74)));
      });
      m.quad([-0.2, U + 0.01, 2.75], [0.3, U + 0.01, 2.75], [0.3, U + 0.01, 2.05], [-0.2, U + 0.01, 2.05], cloth(0.5, 0.56, 0.6));
      at(0.86, U, ID - 0.2, 0, () => {                                              // a lidded bin
        lathe(m, [[0.1, 0], [0.105, 0.012], [0.12, 0.27], [0.125, 0.28], [0.06, 0.31], [0, 0.315]], 16, enamel);
        at(0, 0.313, 0, 0, () => knob(black));
      });
      light([HX - 0.4, U + 1.95, 2.3], [0.6, 0.62, 0.54], 5.5, [-HX, Z0, HX, ID], 'bath');
    }
    setLevel(0);
  });
}
