/**
 * Inside the farmhouse: a hall, a dining room, a kitchen in the lean-to and a
 * living room, furnished as if somebody had just stepped out.
 *
 * Nothing here is a box standing in for a thing. Legs are turned on a lathe,
 * cushions and appliances have rounded edges, rails and handles are swept
 * tubes, curtains and coats hang in folds (see detail.js). The house itself
 * stays as plain as the rest of the farm -- flat walls, flat floors -- because
 * walls are flat; it is the objects in a room that give its scale away.
 *
 * Everything is authored in house space with the floor at y = 0. Front is +Z,
 * so the dining room is on the -X side, the living room on +X, and the
 * kitchen is beyond the back wall at -Z.
 *
 *            -4.4        -1.1   1.1         4.4
 *    -6.0  +--kitchen----+
 *    -3.4  +------. .----+------+-----------+
 *          |             |stair |    back door, armchair
 *          |   dining    |  box |  sofa  ·  fireplace
 *          |             +--. --+        living
 *          |             ·      ·  books        TV
 *     3.4  +----window---+-door-+---window--+
 *                          porch
 */
import { stick, wall, plate as holed } from './geom.js';
import { lathe, roundBox, tube, drape, sphere } from './detail.js';
import { L } from './textures.js';
import { rotX, rotY, rotZ, translate, chain, xformPoint } from './math.js';
import { makeRng } from '../../src/core/rng.js';

const WARM = [1.0, 0.72, 0.42];

/**
 * The furnishing kit: materials, and the pieces and helpers both storeys are
 * built from. Everything it makes lands wherever the mesh builder currently
 * is, so the same chair can be set down in the dining room or a bedroom.
 */
export function makeKit(m, w, M, H, env) {
  const F = H.found, CH = H.room;
  const IW = H.hw - H.wall, ID = H.hd - H.wall;          // inner faces of the outside walls
  const PX = 1.1, PT = 0.12;                             // the two partitions, and how thick
  const DOOR = [0.42, 1.82];                               // the cased openings off the hall, along Z
  // Colliders made while furnishing belong to the storey being furnished.
  let level = 0;
  const setLevel = (v) => { level = v; };
  const tag = (fn) => (...a) => { const n = w.boxes.length; fn(...a); for (let i = n; i < w.boxes.length; i++) w.boxes[i].level = level; };
  const run = tag(env.run), obb = tag(env.obb);

  /* ---- materials ---- */
  const white = { layer: L.plain, col: [0.9, 0.88, 0.82] };
  const oak = { layer: L.grain, gloss: 0.35 };
  const dark = { layer: L.grain, col: [0.5, 0.44, 0.4], gloss: 0.4 };
  const pine = { layer: L.grain, col: [1.5, 1.34, 1.05], gloss: 0.25 };
  const china = { layer: L.plain, col: [0.86, 0.86, 0.8], gloss: 0.9 };
  const brass = { layer: L.plain, col: [0.6, 0.44, 0.16], gloss: 0.9 };
  const chrome = { layer: L.plain, col: [0.5, 0.52, 0.55], gloss: 1 };
  const iron = { layer: L.plain, col: [0.045, 0.045, 0.05], gloss: 0.5 };
  const enamel = { layer: L.plain, col: [0.8, 0.8, 0.74], gloss: 0.7 };
  const black = { layer: L.plain, col: [0.03, 0.03, 0.034], gloss: 0.8 };
  const pit = { layer: L.plain, col: [0.015, 0.015, 0.017] };
  const cloth = (r, g, b, more = {}) => ({ layer: L.fabric, col: [r, g, b], ...more });
  const glow = (col, emit) => ({ layer: L.plain, col, emit });

  // `group` names the switch a light answers to (see world.js: groups).
  const light = (p, color, range, room, group, more = {}) => {
    const l = { pos: xformPoint(M, [p[0], p[1] + F, p[2]]), color, range, dir: [0, -1, 0], cos: -2, mode: 1, room, ...more };
    w.lights.push(l);
    w.groups[group].lights.push(l);
  };
  /** Something that can be used, placed wherever the builder currently is. */
  const usable = (local, reach, what) => w.things.push({ pos: xformPoint(m.m, local), reach, ...what });
  /** A glowing piece that a switch turns off: built apart so it can be dimmed. */
  const glows = (group, fn, more = {}) => w.groups[group].parts.push(Object.assign(m.part(fn), more));
  const at = (x, y, z, yaw, fn) => m.at(chain(translate(x, y, z), rotY(yaw || 0)), fn);

  /* ---- pieces used in more than one room ---- */

  /** A leg turned with a couple of beads and a taper to the foot. */
  const leg = (x, z, h, r, mat = oak, seg = 12) => m.at(translate(x, 0, z), () => lathe(m, [
    [r * 0.55, 0], [r * 0.7, h * 0.04], [r * 0.6, h * 0.1], [r * 0.82, h * 0.34], [r, h * 0.46], [r * 0.66, h * 0.52],
    [r * 0.98, h * 0.6], [r * 0.86, h * 0.78], [r, h * 0.84], [r, h],
  ], seg, mat));

  /** A picture in a moulded frame, on the wall plane z = 0 looking down +Z. */
  const frame = (wd, hg, fit, mat = dark) => {
    const b = 0.045;
    for (const [x, y, sx, sy] of [[0, hg / 2 + b / 2, wd + 2 * b, b], [0, -hg / 2 - b / 2, wd + 2 * b, b], [-wd / 2 - b / 2, 0, b, hg], [wd / 2 + b / 2, 0, b, hg]]) {
      roundBox(m, x, y, 0.016, sx, sy, 0.032, 0.012, 1, mat);
    }
    m.quad([-wd / 2, -hg / 2, 0.008], [wd / 2, -hg / 2, 0.008], [wd / 2, hg / 2, 0.008], [-wd / 2, hg / 2, 0.008], { layer: L.picture, fit, gloss: 0.5 });
  };
  const LANDSCAPE = [0.02, 0.05, 0.48, 0.95], PORTRAIT = [0.56, 0.08, 0.94, 0.96];

  /** A lamp: turned base, a shade, and a bulb that is either on or not. */
  const lamp = (h, shadeR, group, base = china) => {
    lathe(m, [[0.07, 0], [0.075, 0.012], [0.03, 0.03], [0.05, h * 0.2], [0.062, h * 0.34], [0.03, h * 0.5], [0.012, h * 0.56], [0.012, h * 0.74]], 16, base);
    const s0 = h * 0.62, s1 = h;
    glows(group, () => {
      lathe(m, [[shadeR, s0], [shadeR * 0.62, s1]], 20, cloth(0.92, 0.82, 0.6, { emit: 0.85 }));
      m.at(translate(0, h * 0.8, 0), () => sphere(m, 0.03, 8, glow(WARM, 3)));
    });
    usable([0, h * 0.8, 0], 1.9, { group, noun: 'the lamp' });
  };

  /** A panelled door leaf: hinge on the local Y axis, running along +X. */
  const leaf = (dw, dh) => () => {
    const half = dw / 2;
    roundBox(m, half, dh / 2, 0, dw, dh, 0.045, 0.006, 1, { layer: L.plain, col: [0.72, 0.7, 0.62] });
    for (const z of [-0.026, 0.026]) for (const [fx, fy, ph] of [[-1, 0.79, 0.26], [1, 0.79, 0.26], [-1, 0.485, 0.23], [1, 0.485, 0.23], [-1, 0.2, 0.25], [1, 0.2, 0.25]]) {
      roundBox(m, half + fx * dw * 0.223, dh * fy, z, dw * 0.32, dh * ph, 0.012, 0.005, 1, { layer: L.plain, col: [0.64, 0.62, 0.55] });
    }
    for (const z of [-1, 1]) m.at(chain(translate(dw - 0.07, 1.0, z * 0.022), rotX(z * Math.PI / 2)), () => lathe(m, [[0.03, 0], [0.03, 0.008], [0.012, 0.014], [0.012, 0.04], [0.03, 0.052], [0.032, 0.066], [0.02, 0.08], [0, 0.082]], 14, brass));
  };
  /**
   * Hang a door. It sits in the outer face of the wall, so that its outside
   * is lit by the porch and its inside by the hall, and swings into the room.
   */
  const hang = (x, z, dw, dh, shut, open, y = 0) => at(x, y, z, 0, () => {
    const box = { x: 0, z: 0, hx: 0, hz: 0, yaw: 0, level };
    w.boxes.push(box);
    w.doors.push({ kind: 'swing', noun: 'door', site: env.site, part: m.part(leaf(dw, dh)), box, hinge: [x, z], width: dw, shut, open });
  });

  /** A dining chair, facing +Z, with its origin on the floor under the seat. */
  const chair = (seat) => {
    for (const x of [-0.19, 0.19]) {
      leg(x, 0.19, 0.44, 0.022, oak, 10);
      tube(m, [[x, 0, -0.19], [x, 0.44, -0.2], [x * 1.03, 0.72, -0.235], [x * 1.05, 0.96, -0.28]], (t) => 0.02 - t * 0.004, 8, oak);
      tube(m, [[x, 0.16, 0.19], [x, 0.18, -0.19]], 0.011, 6, oak, false);
    }
    tube(m, [[-0.19, 0.13, 0.19], [0.19, 0.13, 0.19]], 0.011, 6, oak, false);
    tube(m, [[-0.19, 0.2, -0.19], [0.19, 0.2, -0.19]], 0.011, 6, oak, false);
    roundBox(m, 0, 0.455, 0, 0.45, 0.04, 0.44, 0.016, 2, oak);
    roundBox(m, 0, 0.495, 0.005, 0.41, 0.05, 0.39, 0.024, 2, seat);
    tube(m, [[-0.2, 0.93, -0.275], [-0.1, 0.955, -0.292], [0.1, 0.955, -0.292], [0.2, 0.93, -0.275]], 0.024, 8, oak);
    tube(m, [[-0.195, 0.6, -0.218], [0, 0.6, -0.232], [0.195, 0.6, -0.218]], 0.013, 6, oak, false);
    for (const x of [-0.1, -0.033, 0.033, 0.1]) tube(m, [[x, 0.6, -0.228], [x, 0.78, -0.262], [x, 0.94, -0.288]], 0.008, 6, oak, false);
  };

  /** A plate, a bowl, a mug -- all the same idea, a profile spun round. */
  const plate = (r, mat = china) => lathe(m, [[0, 0.004], [r * 0.55, 0.004], [r * 0.62, 0.008], [r, 0.022], [r, 0.026], [r * 0.6, 0.012], [0, 0.01]], 20, mat);
  const bowl = (r, h, mat = china) => lathe(m, [[0, 0.004], [r * 0.4, 0.004], [r * 0.5, 0.012], [r * 0.9, h * 0.7], [r, h], [r * 0.97, h], [r * 0.84, h * 0.66], [r * 0.4, 0.022], [0, 0.02]], 20, mat);
  const mug = (mat = china) => {
    lathe(m, [[0, 0.003], [0.034, 0.003], [0.038, 0.012], [0.04, 0.09], [0.036, 0.09], [0.034, 0.016], [0, 0.014]], 14, mat);
    tube(m, [[0.038, 0.074, 0], [0.062, 0.07, 0], [0.068, 0.046, 0], [0.058, 0.024, 0], [0.038, 0.02, 0]], 0.006, 6, mat, false);
  };
  const candlestick = () => {
    lathe(m, [[0.045, 0], [0.048, 0.01], [0.018, 0.022], [0.014, 0.06], [0.024, 0.075], [0.012, 0.09], [0.012, 0.17], [0.026, 0.185], [0.026, 0.195], [0.012, 0.195]], 14, brass);
    lathe(m, [[0.011, 0.195], [0.011, 0.36], [0.004, 0.368], [0, 0.368]], 10, { layer: L.plain, col: [0.86, 0.82, 0.7] });
  };

  return { setLevel, run, obb, F, CH, IW, ID, PX, PT, DOOR, PORTRAIT, white, oak, dark, pine, china, brass, chrome, iron, enamel, black, pit, cloth, glow, light, usable, glows, at, leg, frame, LANDSCAPE, lamp, leaf, hang, chair, plate, bowl, mug, candlestick };
}

export function buildInterior(m, w, M, H, env) {
  const K = makeKit(m, w, M, H, env);
  const { setLevel, run, obb, F, CH, IW, ID, PX, PT, DOOR, PORTRAIT, white, oak, dark, pine, china, brass, chrome, iron, enamel, black, pit, cloth, glow, light, usable, glows, at, leg, frame, LANDSCAPE, lamp, leaf, hang, chair, plate, bowl, mug, candlestick } = K;

  m.at(chain(M, translate(0, F, 0)), () => {
    /* =============================================================== shell */
    const boards = { layer: L.wood, col: [0.74, 0.56, 0.4], gloss: 0.3 };
    m.quad([-IW, 0.004, ID], [IW, 0.004, ID], [IW, 0.004, -ID], [-IW, 0.004, -ID], boards);
    holed(m, -IW, -ID, IW, ID, CH, [H.stair.x0, -ID, H.stair.x1, H.stair.zs], { layer: L.plaster });
    // Partitions either side of the hall, each with a wide cased opening.
    const opening = [{ x0: DOOR[0], x1: DOOR[1], y0: 0, y1: 2.1 }];
    m.at(chain(translate(-PX - PT / 2, 0, 0), rotY(-Math.PI / 2)), () => wall(m, -ID, ID, 0, CH, opening, env.dining, env.hall, PT, white));
    m.at(chain(translate(PX - PT / 2, 0, 0), rotY(-Math.PI / 2)), () => wall(m, -ID, ID, 0, CH, opening, env.hall, env.living, PT, white));
    run(-PX, -ID, -PX, DOOR[0]); run(-PX, DOOR[1], -PX, ID);
    run(PX, -ID, PX, DOOR[0]); run(PX, DOOR[1], PX, ID);
    for (const px of [-PX, PX]) for (const side of [-1, 1]) {      // casings round both openings, both faces
      const x = px + side * (PT / 2 + 0.01);
      for (const z of DOOR) m.box(x, 1.08, z + (z === DOOR[0] ? -0.045 : 0.045), 0.02, 2.16, 0.09, white);
      m.box(x, 2.15, (DOOR[0] + DOOR[1]) / 2, 0.024, 0.11, DOOR[1] - DOOR[0] + 0.24, white);
    }
    // Skirting, run by run, leaving the doorways alone.
    const skirt = (x0, z0, x1, z1) => stick(m, [x0, 0.065, z0], [x1, 0.065, z1], 0.018, 0.13, white);
    const e = 0.012;
    skirt(-IW + e, -ID, -IW + e, ID); skirt(IW - e, -ID, IW - e, -1.65); skirt(IW - e, 0.05, IW - e, ID);
    skirt(-IW, ID - e, -0.56, ID - e); skirt(0.56, ID - e, IW, ID - e);
    skirt(-IW, -ID + e, -2.95, -ID + e); skirt(-1.95, -ID + e, 1.8, -ID + e); skirt(2.8, -ID + e, IW, -ID + e);
    for (const px of [-PX, PX]) for (const s of [-1, 1]) {
      const x = px + s * (PT / 2 + e);
      skirt(x, -ID, x, DOOR[0] - 0.09); skirt(x, DOOR[1] + 0.09, x, ID);
    }

    // Front and back doors, both shut and neither locked.
    hang(-0.47, H.hd - 0.02, 0.94, 2.03, 0, 1.75);
    hang(2.75, -H.hd + 0.02, 0.9, 1.98, Math.PI, Math.PI + 1.75);
    m.quad([-0.5, 0.01, ID - 0.15], [0.5, 0.01, ID - 0.15], [0.5, 0.01, ID - 0.85], [-0.5, 0.01, ID - 0.85], cloth(0.3, 0.26, 0.2));   // mat

    // Casing round the back doorway, inside.
    at(2.3, 0, -ID, 0, () => {
      for (const s of [-1, 1]) m.box(s * 0.5, 1.03, 0.012, 0.1, 2.06, 0.024, white);
      m.box(0, 2.06, 0.014, 1.2, 0.11, 0.028, white);
    });

    /* ================================================================ hall */
    {
      // The boxed stair, behind a door at the foot of it (the flight itself
      // is built with the upper floor, in upstairs.js).
      const { x0: sx0, x1: sx1, zd: sz } = H.stair;
      const sd0 = sx0 + 0.065, sd1 = sx1 - 0.065;                    // the doorway
      at(0, 0, sz, 0, () => wall(m, sx0, sx1, 0, CH, [{ x0: sd0, x1: sd1, y0: 0, y1: 2.0 }], env.hall, env.hall, 0.06, white));
      m.quad([sx0, 0, -ID], [sx0, 0, sz], [sx0, CH, sz], [sx0, CH, -ID], env.hall);
      at((sx0 + sx1) / 2, 0, sz, 0, () => {
        for (const s of [-1, 1]) m.box(s * 0.42, 1.03, 0.012, 0.08, 2.06, 0.024, white);
        m.box(0, 2.06, 0.014, 0.94, 0.1, 0.028, white);
      });
      hang(sd1, sz - 0.01, sd1 - sd0, 1.98, Math.PI, Math.PI + 1.52);
      run(sx0, sz, sd0, sz, 0.035); run(sd1, sz, sx1, sz, 0.035); run(sx0, -ID, sx0, sz);
      skirt(sx0, sz + e, sx1, sz + e); skirt(sx0 - e, -ID, sx0 - e, sz);

      m.quad([-0.42, 0.008, 2.3], [0.42, 0.008, 2.3], [0.42, 0.008, -2.6], [-0.42, 0.008, -2.6], { layer: L.rug, fit: true, col: [0.62, 0.56, 0.6] });

      // Console table by the door: telephone, lamp, keys in a dish.
      at(PX - PT / 2 - 0.19, 0, 2.5, 0, () => {
        roundBox(m, 0, 0.8, 0, 0.36, 0.03, 1.0, 0.012, 2, oak);
        m.box(0, 0.72, 0, 0.3, 0.12, 0.92, oak);
        for (const z of [-0.22, 0.22]) m.at(chain(translate(-0.15, 0.72, z), rotZ(Math.PI / 2)), () => lathe(m, [[0.014, 0], [0.006, 0.008], [0.006, 0.02], [0.015, 0.028], [0.012, 0.038], [0, 0.04]], 10, brass));
        for (const [x, z] of [[-0.14, -0.45], [0.14, -0.45], [-0.14, 0.45], [0.14, 0.45]]) leg(x, z, 0.66, 0.022, oak, 10);
        at(0.02, 0.815, 0.3, 0, () => lamp(0.46, 0.15, 'hall', { layer: L.plain, col: [0.3, 0.42, 0.36], gloss: 0.9 }));
        at(-0.04, 0.815, 0.0, 0.2, () => bowl(0.07, 0.035, brass));
        // A rotary telephone: body, cradle, handset, dial, and a coiled cord.
        at(0, 0.815, -0.26, -0.25, () => {
          usable([0, 0.1, 0], 1.7, { label: 'Pick up the telephone', say: 'The line is dead.' });
          roundBox(m, 0, 0.045, 0, 0.2, 0.09, 0.22, 0.035, 3, black);
          m.at(chain(translate(0, 0.07, 0.04), rotX(-0.5)), () => {
            lathe(m, [[0.062, 0], [0.066, 0.006], [0.062, 0.012], [0.03, 0.012]], 20, { layer: L.plain, col: [0.6, 0.6, 0.56], gloss: 0.8 });
            for (let k = 0; k < 10; k++) at(Math.sin(k * 0.54 + 0.5) * 0.047, 0.013, Math.cos(k * 0.54 + 0.5) * 0.047, 0, () => lathe(m, [[0.0075, 0], [0.0075, 0.002]], 8, pit));
          });
          for (const s of [-1, 1]) roundBox(m, s * 0.07, 0.1, -0.07, 0.03, 0.03, 0.05, 0.01, 1, black);
          tube(m, [[-0.105, 0.118, -0.07], [-0.07, 0.132, -0.07], [0, 0.138, -0.07], [0.07, 0.132, -0.07], [0.105, 0.118, -0.07]], (t) => 0.016 + Math.pow(Math.abs(t - 0.5) * 2, 3) * 0.012, 10, black);
          const coil = [];
          for (let k = 0; k <= 70; k++) {
            const t = k / 70, a = t * 44;
            coil.push([-0.11 - t * 0.02 + Math.cos(a) * 0.009, 0.11 - Math.sin(t * Math.PI) * 0.03 - t * 0.09 + Math.sin(a) * 0.009, -0.07 + t * 0.2]);
          }
          tube(m, coil, 0.0028, 5, black, false);
        });
      });
      obb(PX - PT / 2 - 0.19, 2.5, 0.19, 0.52);
      at(PX - PT / 2, 1.5, 2.5, -Math.PI / 2, () => {                                    // mirror over it
        frame(0.5, 0.7, [0, 0, 0.01, 0.01], oak);
        m.quad([-0.25, -0.35, 0.01], [0.25, -0.35, 0.01], [0.25, 0.35, 0.01], [-0.25, 0.35, 0.01], { layer: L.glass, fit: true, col: [2.2, 2.3, 2.5], gloss: 1 });
      });

      // Pegs on the wall: a coat, a hat, a scarf.
      at(-PX + PT / 2, 1.62, -0.9, Math.PI / 2, () => {
        roundBox(m, 0, 0, 0.012, 1.3, 0.1, 0.024, 0.008, 1, oak);
        for (const x of [-0.5, -0.17, 0.17, 0.5]) tube(m, [[x, 0, 0.02], [x, 0, 0.07], [x, 0.03, 0.095]], 0.008, 6, brass);
        m.at(translate(-0.72, -1.2, 0.09), () => drape(m, 0.44, 1.2, 3, 0.03, cloth(0.2, 0.2, 0.16)));
        m.at(translate(-0.02, -0.86, 0.085), () => drape(m, 0.16, 0.86, 2, 0.012, cloth(0.5, 0.16, 0.14)));
        m.at(chain(translate(0.5, 0.02, 0.15), rotX(1.25)), () => lathe(m, [[0.16, 0], [0.162, 0.006], [0.09, 0.012], [0.082, 0.07], [0.07, 0.11], [0, 0.118]], 18, cloth(0.32, 0.26, 0.18)));
      });
      // Umbrella stand.
      at(-0.84, 0, -0.05, 0, () => {
        lathe(m, [[0.11, 0], [0.12, 0.02], [0.1, 0.1], [0.115, 0.5], [0.13, 0.54], [0.118, 0.54], [0.104, 0.5], [0.09, 0.03], [0, 0.03]], 18, { layer: L.plain, col: [0.2, 0.3, 0.34], gloss: 0.9 });
        for (const [a, b] of [[0.03, 0.2], [-0.04, -0.3]]) m.at(chain(translate(a, 0.03, b * 0.1), rotZ(b * 0.3)), () => {
          lathe(m, [[0.006, 0], [0.03, 0.08], [0.022, 0.6], [0.01, 0.66]], 10, cloth(0.06, 0.06, 0.08));
          tube(m, [[0, 0.66, 0], [0, 0.82, 0], [0.02, 0.86, 0], [0.05, 0.85, 0], [0.058, 0.8, 0]], 0.009, 6, dark);
        });
      });
      obb(-0.84, -0.05, 0.13, 0.13);

      // The clock at the end of the passage.
      at(-0.45, 0, -ID + 0.17, 0, () => {
        usable([0, 1.6, 0.2], 1.9, { label: 'Look at the clock', say: 'Twenty to midnight. It has stopped.' });
        roundBox(m, 0, 0.26, 0, 0.5, 0.52, 0.3, 0.012, 1, dark);
        roundBox(m, 0, 1.05, 0, 0.38, 1.1, 0.24, 0.01, 1, dark);
        m.quad([-0.13, 0.62, 0.122], [0.13, 0.62, 0.122], [0.13, 1.5, 0.122], [-0.13, 1.5, 0.122], pit);
        for (const x of [-0.15, 0.15]) roundBox(m, x, 1.06, 0.126, 0.04, 0.96, 0.02, 0.006, 1, dark);
        for (const y of [0.6, 1.52]) roundBox(m, 0, y, 0.126, 0.34, 0.04, 0.02, 0.006, 1, dark);
        tube(m, [[0, 1.46, 0.128], [0.04, 0.86, 0.128]], 0.005, 6, brass, false);
        m.at(chain(translate(0.045, 0.8, 0.126), rotX(Math.PI / 2)), () => lathe(m, [[0.06, 0], [0.062, 0.004], [0.03, 0.01], [0, 0.011]], 20, brass));
        roundBox(m, 0, 1.86, 0, 0.5, 0.52, 0.3, 0.014, 1, dark);
        m.at(chain(translate(0, 1.86, 0.153), rotX(Math.PI / 2)), () => lathe(m, [[0.19, 0], [0.2, 0.008], [0.175, 0.016], [0.172, 0.006]], 28, brass));
        m.quad([-0.17, 1.69, 0.158], [0.17, 1.69, 0.158], [0.17, 2.03, 0.158], [-0.17, 2.03, 0.158], { layer: L.clockface, fit: [0.07, 0.07, 0.93, 0.93], gloss: 0.6 });
        roundBox(m, 0, 2.14, 0, 0.56, 0.06, 0.34, 0.02, 2, dark);
        for (const x of [-0.22, 0, 0.22]) at(x, 2.17, 0, 0, () => lathe(m, [[0.02, 0], [0.026, 0.01], [0.012, 0.02], [0.028, 0.05], [0.02, 0.075], [0.004, 0.11], [0, 0.112]], 12, dark));
      });
      obb(-0.45, -ID + 0.17, 0.27, 0.18);

      at(sx0 - 0.004, 1.5, -1.6, -Math.PI / 2, () => frame(0.3, 0.4, PORTRAIT));
      at(sx0 - 0.004, 1.52, -2.3, -Math.PI / 2, () => frame(0.26, 0.34, PORTRAIT, oak));
      light([0.72, 1.2, 2.8], WARM.map((c) => c * 0.62), 6.5, [-PX + 0.06, -ID, PX - 0.06, ID], 'hall');
    }

    /* ======================================================== dining room */
    {
      const TX = -3.0, TZ = 0.3;
      m.quad([TX - 1.15, 0.007, TZ + 1.6], [TX + 1.15, 0.007, TZ + 1.6], [TX + 1.15, 0.007, TZ - 1.6], [TX - 1.15, 0.007, TZ - 1.6], { layer: L.rug, fit: true, col: [0.7, 0.66, 0.62] });
      at(TX, 0, TZ, 0, () => {
        roundBox(m, 0, 0.745, 0, 1.0, 0.045, 1.9, 0.016, 2, { ...oak, gloss: 0.55 });
        m.box(0, 0.67, 0, 0.82, 0.1, 1.72, oak);
        for (const sx of [-1, 1]) for (const sz of [-1, 1]) leg(sx * 0.41, sz * 0.86, 0.72, 0.046, oak, 16);
        m.quad([-0.2, 0.769, 0.8], [0.2, 0.769, 0.8], [0.2, 0.769, -0.8], [-0.2, 0.769, -0.8], cloth(0.62, 0.6, 0.5));     // runner
        // Laid for a meal that did not happen.
        for (const [x, z] of [[-0.3, -0.5], [0.3, -0.5], [-0.3, 0.5], [0.3, 0.5]]) {
          at(x, 0.768, z, 0, () => plate(0.125));
          at(x + Math.sign(x) * 0.02, 0.768, z - 0.2, 0, () => lathe(m, [[0, 0.003], [0.03, 0.003], [0.033, 0.01], [0.038, 0.1], [0.035, 0.1], [0.03, 0.014], [0, 0.012]], 14, { layer: L.plain, col: [0.5, 0.56, 0.58], gloss: 1 }));
        }
        at(0, 0.77, 0, 0, () => {
          bowl(0.15, 0.08, { layer: L.plain, col: [0.5, 0.36, 0.2], gloss: 0.5 });
          for (const [x, z, c] of [[0.05, 0.03, [0.5, 0.1, 0.08]], [-0.06, 0.02, [0.56, 0.44, 0.1]], [0, -0.07, [0.4, 0.46, 0.14]], [0.01, 0.06, [0.5, 0.12, 0.08]]]) {
            at(x, 0.075, z, 0, () => sphere(m, 0.042, 12, { layer: L.plain, col: c, gloss: 0.5 }, 0.9));
          }
        });
        for (const z of [-0.36, 0.36]) at(0, 0.77, z, 0, candlestick);
        at(0.18, 0.77, 0.74, 0.4, () => {                                         // a jug
          lathe(m, [[0, 0.004], [0.05, 0.004], [0.062, 0.03], [0.07, 0.1], [0.05, 0.17], [0.046, 0.2], [0.056, 0.22], [0.05, 0.22], [0.04, 0.2], [0.06, 0.1], [0, 0.02]], 18, china);
          tube(m, [[0.05, 0.19, 0], [0.09, 0.18, 0], [0.1, 0.12, 0], [0.068, 0.07, 0]], 0.008, 6, china, false);
        });
      });
      obb(TX, TZ, 0.5, 0.95);
      const seat = cloth(0.42, 0.2, 0.18);
      // One chair on the window side has been pushed back, as if somebody got
      // up. The two by the door are tucked in, so the way in stays clear.
      for (const [x, z, yaw] of [[TX - 0.74, TZ - 0.45, Math.PI / 2], [TX - 0.96, TZ + 0.6, Math.PI / 2 + 0.5], [TX + 0.74, TZ - 0.45, -Math.PI / 2],
        [TX + 0.74, TZ + 0.45, -Math.PI / 2 - 0.08], [TX, TZ - 1.22, 0], [TX + 0.04, TZ + 1.24, Math.PI + 0.06]]) {
        at(x, 0, z, yaw, () => chair(seat));
        obb(x, z, 0.23, 0.23);
      }
      // Pendant over the table.
      at(TX, 0, TZ, 0, () => {
        tube(m, [[0, CH, 0], [0, 1.95, 0]], 0.006, 6, pit, false);
        lathe(m, [[0.03, CH - 0.03], [0.05, CH - 0.03], [0.05, CH], [0, CH]], 14, brass);
        lathe(m, [[0.03, 1.98], [0.045, 1.93], [0.24, 1.76], [0.25, 1.74], [0.236, 1.74], [0.04, 1.9]], 24, { layer: L.plain, col: [0.16, 0.3, 0.24], gloss: 0.9 });
        glows('dining', () => {
          lathe(m, [[0.228, 1.746], [0.04, 1.895]], 24, glow([1, 0.86, 0.6], 1.2));
          m.at(translate(0, 1.8, 0), () => sphere(m, 0.04, 12, glow(WARM, 4)));
        });
        usable([0, 1.8, 0], 2.4, { group: 'dining', noun: 'the light' });
      });
      light([TX, 1.72, TZ], WARM.map((c) => c * 0.95), 8, [-IW, -ID, -PX - 0.06, ID], 'dining');

      // Sideboard on the kitchen wall.
      at(-3.66, 0, -ID + 0.25, 0, () => {
        roundBox(m, 0, 0.5, 0, 1.3, 0.72, 0.46, 0.012, 1, dark);
        roundBox(m, 0, 0.885, 0, 1.36, 0.035, 0.5, 0.014, 2, { ...dark, gloss: 0.6 });
        for (const [x, z] of [[-0.6, -0.18], [0.6, -0.18], [-0.6, 0.18], [0.6, 0.18]]) leg(x, z, 0.14, 0.03, dark, 10);
        for (const x of [-0.42, 0, 0.42]) {
          roundBox(m, x, 0.42, 0.232, 0.38, 0.5, 0.014, 0.006, 1, { layer: L.grain, col: [0.58, 0.5, 0.46], gloss: 0.4 });
          roundBox(m, x, 0.42, 0.24, 0.26, 0.38, 0.01, 0.005, 1, { layer: L.grain, col: [0.44, 0.38, 0.34], gloss: 0.4 });
          roundBox(m, x, 0.765, 0.232, 0.38, 0.12, 0.014, 0.006, 1, { layer: L.grain, col: [0.58, 0.5, 0.46], gloss: 0.4 });
          m.at(chain(translate(x, 0.765, 0.24), rotX(Math.PI / 2)), () => lathe(m, [[0.016, 0], [0.007, 0.008], [0.007, 0.02], [0.017, 0.03], [0, 0.036]], 10, brass));
          m.at(chain(translate(x + 0.14, 0.44, 0.246), rotX(Math.PI / 2)), () => lathe(m, [[0.012, 0], [0.006, 0.006], [0.012, 0.022], [0, 0.026]], 10, brass));
        }
        // A valve radio, a stack of plates, dried flowers in a vase.
        at(-0.36, 0.903, 0.02, 0.12, () => {
          roundBox(m, 0, 0.13, 0, 0.42, 0.26, 0.2, 0.05, 3, { layer: L.grain, col: [0.9, 0.7, 0.5], gloss: 0.6 });
          m.quad([-0.17, 0.05, 0.102], [0.05, 0.05, 0.102], [0.05, 0.21, 0.102], [-0.17, 0.21, 0.102], cloth(0.5, 0.42, 0.3));
          m.quad([0.07, 0.11, 0.102], [0.18, 0.11, 0.102], [0.18, 0.2, 0.102], [0.07, 0.2, 0.102], glow([0.9, 0.66, 0.3], 0.5));
          for (const x of [0.09, 0.16]) m.at(chain(translate(x, 0.065, 0.1), rotX(Math.PI / 2)), () => lathe(m, [[0.018, 0], [0.018, 0.014], [0.014, 0.018], [0, 0.018]], 12, black));
        });
        at(0.2, 0.903, 0, 0, () => { for (let k = 0; k < 6; k++) m.at(translate(0, k * 0.013, 0), () => plate(0.12)); });
        at(0.5, 0.903, -0.04, 0, () => {
          lathe(m, [[0, 0.004], [0.04, 0.004], [0.06, 0.05], [0.066, 0.12], [0.03, 0.2], [0.026, 0.25], [0.036, 0.27], [0.03, 0.27], [0.022, 0.25], [0, 0.03]], 18, { layer: L.plain, col: [0.26, 0.34, 0.5], gloss: 0.95 });
          const r = makeRng(5);
          for (let k = 0; k < 9; k++) {
            const a = r() * 6.3, s = 0.05 + r() * 0.1, h = 0.5 + r() * 0.2;
            tube(m, [[0, 0.25, 0], [Math.cos(a) * s * 0.4, 0.25 + (h - 0.25) * 0.55, Math.sin(a) * s * 0.4], [Math.cos(a) * s, h, Math.sin(a) * s]], 0.0035, 5, { layer: L.plain, col: [0.4, 0.34, 0.2] }, false);
            at(Math.cos(a) * s, h, Math.sin(a) * s, 0, () => sphere(m, 0.016, 8, { layer: L.plain, col: [0.56, 0.4 + r() * 0.2, 0.26] }, 1.4));
          }
        });
      });
      obb(-3.66, -ID + 0.25, 0.68, 0.26);
      at(-3.66, 1.62, -ID + 0.004, 0, () => frame(0.7, 0.5, LANDSCAPE));

      // Dresser in the corner by the front window: open shelves over cupboards.
      at(-3.86, 0, ID - 0.23, Math.PI, () => {
        roundBox(m, 0, 0.44, 0, 1.0, 0.88, 0.44, 0.012, 1, pine);
        roundBox(m, 0, 0.9, 0, 1.06, 0.035, 0.48, 0.014, 2, pine);
        for (const x of [-0.25, 0.25]) {
          roundBox(m, x, 0.44, 0.222, 0.44, 0.74, 0.014, 0.006, 1, { layer: L.grain, col: [1.34, 1.2, 0.94] });
          roundBox(m, x, 0.44, 0.23, 0.3, 0.58, 0.01, 0.005, 1, { layer: L.grain, col: [1.14, 1.0, 0.8] });
          m.at(chain(translate(x - Math.sign(x) * 0.17, 0.5, 0.236), rotX(Math.PI / 2)), () => lathe(m, [[0.013, 0], [0.006, 0.006], [0.013, 0.022], [0, 0.026]], 10, brass));
        }
        m.box(0, 1.56, -0.2, 1.0, 1.3, 0.02, pine);
        for (const x of [-0.49, 0.49]) m.box(x, 1.56, -0.07, 0.022, 1.3, 0.28, pine);
        roundBox(m, 0, 2.22, -0.06, 1.08, 0.05, 0.34, 0.02, 2, pine);
        for (const y of [1.3, 1.72]) {
          m.box(0, y, -0.07, 0.96, 0.022, 0.28, pine);
          for (let k = 0; k < 5; k++) m.at(chain(translate(-0.38 + k * 0.19, y + 0.012 + 0.092, -0.15), rotX(Math.PI / 2 - 0.16)), () => plate(0.09, k % 2 ? china : { layer: L.plain, col: [0.4, 0.5, 0.68], gloss: 0.9 }));
        }
        for (let k = 0; k < 4; k++) at(-0.3 + k * 0.2, 0.918, 0.06, k, () => mug(k % 2 ? china : { layer: L.plain, col: [0.56, 0.3, 0.2], gloss: 0.9 }));
      });
      obb(-3.86, ID - 0.23, 0.54, 0.25);
      // A clock and a portrait between the west windows.
      at(-IW + 0.004, 1.86, 0, Math.PI / 2, () => {
        m.at(rotX(Math.PI / 2), () => lathe(m, [[0.17, 0], [0.18, 0.012], [0.16, 0.03], [0.15, 0.012]], 28, dark));
        m.quad([-0.15, -0.15, 0.014], [0.15, -0.15, 0.014], [0.15, 0.15, 0.014], [-0.15, 0.15, 0.014], { layer: L.clockface, fit: [0.07, 0.07, 0.93, 0.93], gloss: 0.6 });
      });
      at(-IW + 0.004, 1.2, 0, Math.PI / 2, () => frame(0.34, 0.44, PORTRAIT));
    }

    /* ============================================================ kitchen */
    {
      const KX0 = H.lean.x - H.lean.w / 2 + H.wall, KX1 = H.lean.x + H.lean.w / 2 - H.wall;
      const KN = -H.hd - H.lean.d + H.wall, KS = -H.hd, KH = 2.42;
      m.quad([KX0, 0.004, KS], [KX1, 0.004, KS], [KX1, 0.004, KN], [KX0, 0.004, KN], { layer: L.lino, gloss: 0.25 });
      m.quad([KX0, KH, KN], [KX1, KH, KN], [KX1, KH, KS], [KX0, KH, KS], { layer: L.plaster });
      m.quad([-2.95, 0.006, -ID], [-1.95, 0.006, -ID], [-1.95, 0.006, KS], [-2.95, 0.006, KS], { layer: L.wood, col: [0.5, 0.4, 0.3] });   // threshold
      const cab = { layer: L.plain, col: [0.5, 0.6, 0.5], gloss: 0.4 }, cabIn = { layer: L.plain, col: [0.42, 0.52, 0.43], gloss: 0.4 };
      const top = { layer: L.plain, col: [0.42, 0.4, 0.36], gloss: 0.6 }, steel = { layer: L.metal, col: [0.9, 0.92, 0.96], tile: 3, gloss: 1 };
      const CZ = KN + 0.3, CX0 = KX0, CX1 = -1.36, CY = 0.88;                    // the counter run
      m.box((CX0 + CX1) / 2, 0.05, CZ + 0.02, CX1 - CX0, 0.1, 0.52, pit);
      m.box((CX0 + CX1) / 2, 0.47, CZ, CX1 - CX0, 0.74, 0.58, cab);
      const doors = 6, dw = (CX1 - CX0) / doors;
      for (let k = 0; k < doors; k++) {
        const x = CX0 + dw * (k + 0.5), z = CZ + 0.292;
        roundBox(m, x, 0.4, z, dw - 0.03, 0.54, 0.018, 0.007, 1, cab);
        roundBox(m, x, 0.4, z + 0.009, dw - 0.14, 0.42, 0.01, 0.005, 1, cabIn);
        roundBox(m, x, 0.765, z, dw - 0.03, 0.13, 0.018, 0.007, 1, cab);
        tube(m, [[x - 0.05, 0.765, z + 0.009], [x - 0.05, 0.765, z + 0.03], [x + 0.05, 0.765, z + 0.03], [x + 0.05, 0.765, z + 0.009]], 0.006, 6, chrome, false);
        m.at(chain(translate(x + (k % 2 ? -1 : 1) * (dw / 2 - 0.07), 0.6, z + 0.016), rotX(Math.PI / 2)), () => lathe(m, [[0.012, 0], [0.006, 0.006], [0.013, 0.02], [0, 0.024]], 10, chrome));
      }
      // Worktop in four pieces round a real sink.
      const SX0 = H.lean.x - 0.3, SX1 = H.lean.x + 0.3, SZ0 = CZ - 0.16, SZ1 = CZ + 0.18;
      roundBox(m, (CX0 + SX0) / 2, CY, CZ, SX0 - CX0, 0.04, 0.64, 0.012, 1, top);
      roundBox(m, (SX1 + CX1) / 2, CY, CZ, CX1 - SX1, 0.04, 0.64, 0.012, 1, top);
      m.box((SX0 + SX1) / 2, CY, (SZ1 + CZ + 0.32) / 2, SX1 - SX0, 0.04, CZ + 0.32 - SZ1, top);
      m.box((SX0 + SX1) / 2, CY, (SZ0 + CZ - 0.32) / 2, SX1 - SX0, 0.04, SZ0 - (CZ - 0.32), top);
      const by = CY - 0.17;
      m.quad([SX0, by, SZ1], [SX1, by, SZ1], [SX1, by, SZ0], [SX0, by, SZ0], steel);
      m.quad([SX0, by, SZ0], [SX1, by, SZ0], [SX1, CY + 0.02, SZ0], [SX0, CY + 0.02, SZ0], steel);
      m.quad([SX1, by, SZ1], [SX0, by, SZ1], [SX0, CY + 0.02, SZ1], [SX1, CY + 0.02, SZ1], steel);
      m.quad([SX0, by, SZ1], [SX0, by, SZ0], [SX0, CY + 0.02, SZ0], [SX0, CY + 0.02, SZ1], steel);
      m.quad([SX1, by, SZ0], [SX1, by, SZ1], [SX1, CY + 0.02, SZ1], [SX1, CY + 0.02, SZ0], steel);
      at(H.lean.x, by + 0.002, CZ, 0, () => lathe(m, [[0.03, 0], [0.03, 0.003], [0.012, 0.003]], 12, pit));
      at(H.lean.x, CY + 0.02, SZ0 - 0.07, 0, () => {                             // mixer tap
        lathe(m, [[0.03, 0], [0.03, 0.012], [0.016, 0.02], [0.014, 0.05]], 14, chrome);
        tube(m, [[0, 0.04, 0], [0, 0.26, 0], [0, 0.31, 0.03], [0, 0.32, 0.1], [0, 0.29, 0.16], [0, 0.25, 0.17]], 0.011, 10, chrome);
        for (const s of [-1, 1]) at(s * 0.1, 0, 0, 0, () => {
          lathe(m, [[0.022, 0], [0.022, 0.01], [0.012, 0.016], [0.012, 0.05], [0.02, 0.058], [0, 0.064]], 12, chrome);
          for (const a of [0, Math.PI / 2]) m.at(chain(translate(0, 0.05, 0), rotY(a)), () => tube(m, [[-0.034, 0, 0], [0.034, 0, 0]], 0.006, 6, chrome));
        });
      });
      // Draining rack with three plates and a glass, upside down.
      at(SX1 + 0.32, CY + 0.021, CZ, 0, () => {
        for (const z of [-0.14, 0.14]) tube(m, [[-0.2, 0.01, z], [0.2, 0.01, z]], 0.005, 6, chrome);
        for (let k = 0; k < 9; k++) tube(m, [[-0.18 + k * 0.045, 0.01, -0.14], [-0.18 + k * 0.045, 0.01, 0.14]], 0.003, 5, chrome, false);
        for (let k = 0; k < 3; k++) m.at(chain(translate(-0.13 + k * 0.045, 0.125, 0), rotZ(Math.PI / 2 - 0.2)), () => plate(0.115));
        m.at(chain(translate(0.13, 0.115, 0.03), rotX(Math.PI)), () => lathe(m, [[0, 0.003], [0.03, 0.003], [0.036, 0.1], [0.033, 0.1], [0.028, 0.012], [0, 0.01]], 14, { layer: L.plain, col: [0.5, 0.56, 0.58], gloss: 1 }));
      });
      // Bread bin and toaster at the far end.
      at(CX0 + 0.3, CY + 0.021, CZ - 0.04, 0, () => {
        roundBox(m, 0, 0.11, 0, 0.42, 0.22, 0.3, 0.07, 3, enamel);
        tube(m, [[-0.06, 0.13, 0.152], [-0.06, 0.13, 0.17], [0.06, 0.13, 0.17], [0.06, 0.13, 0.152]], 0.006, 6, chrome, false);
      });
      at(CX0 + 0.82, CY + 0.021, CZ - 0.06, 0.1, () => {
        roundBox(m, 0, 0.09, 0, 0.26, 0.18, 0.15, 0.035, 3, chrome);
        for (const z of [-0.03, 0.03]) m.box(0, 0.181, z, 0.18, 0.004, 0.022, pit);
        roundBox(m, 0.14, 0.11, 0, 0.02, 0.03, 0.04, 0.008, 1, black);
      });
      m.quad([KX0, CY + 0.02, KN + 0.004], [-0.58, CY + 0.02, KN + 0.004], [-0.58, 1.48, KN + 0.004], [KX0, 1.48, KN + 0.004], { layer: L.tile, gloss: 0.7 });
      // Wall cupboards either side of the window.
      for (const [x0, x1] of [[KX0, -3.15], [-1.65, KX1]]) {
        m.box((x0 + x1) / 2, 1.9, KN + 0.16, x1 - x0, 0.74, 0.32, cab);
        const n = Math.round((x1 - x0) / 0.5), dw2 = (x1 - x0) / n;
        for (let k = 0; k < n; k++) {
          const x = x0 + dw2 * (k + 0.5);
          roundBox(m, x, 1.9, KN + 0.33, dw2 - 0.03, 0.68, 0.018, 0.007, 1, cab);
          roundBox(m, x, 1.9, KN + 0.339, dw2 - 0.14, 0.54, 0.01, 0.005, 1, cabIn);
          m.at(chain(translate(x + (k % 2 ? -1 : 1) * (dw2 / 2 - 0.07), 1.64, KN + 0.345), rotX(Math.PI / 2)), () => lathe(m, [[0.012, 0], [0.006, 0.006], [0.013, 0.02], [0, 0.024]], 10, chrome));
        }
      }
      run(CX0, CZ, CX1, CZ, 0.3);

      // The cooker: four rings, a kettle, a pan left on.
      const VX = -0.95;
      at(VX, 0, CZ + 0.02, 0, () => {
        roundBox(m, 0, 0.45, 0, 0.74, 0.9, 0.62, 0.022, 2, enamel);
        roundBox(m, 0, 0.905, 0, 0.74, 0.018, 0.62, 0.008, 1, black);
        roundBox(m, 0, 0.42, 0.312, 0.6, 0.5, 0.02, 0.01, 1, enamel);
        m.quad([-0.2, 0.34, 0.324], [0.2, 0.34, 0.324], [0.2, 0.56, 0.324], [-0.2, 0.56, 0.324], { layer: L.glass, fit: true, gloss: 1 });
        tube(m, [[-0.25, 0.7, 0.322], [-0.25, 0.7, 0.36], [0.25, 0.7, 0.36], [0.25, 0.7, 0.322]], 0.011, 8, chrome, false);
        roundBox(m, 0, 1.0, -0.28, 0.74, 0.18, 0.06, 0.016, 1, enamel);
        for (let k = 0; k < 5; k++) m.at(chain(translate(-0.26 + k * 0.13, 1.0, -0.25), rotX(Math.PI / 2)), () => lathe(m, [[0.026, 0], [0.026, 0.006], [0.018, 0.01], [0.018, 0.026], [0, 0.028]], 14, black));
        for (const [x, z, r] of [[-0.18, 0.13, 0.09], [0.18, 0.13, 0.075], [-0.18, -0.13, 0.075], [0.18, -0.13, 0.09]]) {
          for (const k of [0.3, 0.55, 0.8, 1]) {
            const ring = [];
            for (let a = 0; a <= 20; a++) ring.push([x + Math.cos(a * 0.314) * r * k, 0.922, z + Math.sin(a * 0.314) * r * k]);
            tube(m, ring, 0.006, 6, iron, false);
          }
          at(x, 0.915, z, 0, () => lathe(m, [[r + 0.02, 0], [r + 0.02, 0.004], [r + 0.012, 0.006]], 20, chrome));
        }
        at(-0.18, 0.93, -0.13, 0.7, () => {                                       // kettle
          lathe(m, [[0, 0.004], [0.08, 0.004], [0.092, 0.02], [0.096, 0.08], [0.07, 0.14], [0.04, 0.16], [0.04, 0.166], [0, 0.17]], 20, chrome);
          at(0, 0.166, 0, 0, () => lathe(m, [[0.012, 0], [0.008, 0.012], [0.016, 0.022], [0, 0.028]], 10, black));
          tube(m, [[0.085, 0.07, 0], [0.13, 0.11, 0], [0.16, 0.15, 0]], (t) => 0.018 - t * 0.008, 8, chrome);
          tube(m, [[-0.06, 0.15, 0], [-0.07, 0.22, 0], [0, 0.25, 0], [0.07, 0.22, 0], [0.06, 0.15, 0]], 0.008, 8, black, false);
        });
        at(0.18, 0.93, 0.13, 0.3, () => {                                          // saucepan
          lathe(m, [[0, 0.004], [0.085, 0.004], [0.09, 0.012], [0.09, 0.1], [0.084, 0.1], [0.084, 0.016], [0, 0.014]], 20, { layer: L.plain, col: [0.34, 0.35, 0.37], gloss: 0.9 });
          tube(m, [[0.088, 0.085, 0], [0.14, 0.09, 0], [0.26, 0.095, 0]], 0.011, 8, black);
        });
      });
      obb(VX, CZ + 0.02, 0.38, 0.32);

      // Refrigerator against the house wall, with things stuck to it.
      at(-0.96, 0, KS - 0.36, Math.PI, () => {
        roundBox(m, 0, 0.86, 0, 0.72, 1.72, 0.66, 0.04, 3, { layer: L.plain, col: [0.84, 0.82, 0.72], gloss: 0.8 });
        m.box(0, 1.26, 0.331, 0.7, 0.012, 0.004, pit);
        for (const [y0, y1] of [[0.9, 1.2], [1.34, 1.6]]) tube(m, [[-0.28, y0, 0.33], [-0.28, y0, 0.37], [-0.28, y1, 0.37], [-0.28, y1, 0.33]], 0.012, 8, chrome, false);
        m.quad([0.02, 0.8, 0.334], [0.2, 0.8, 0.334], [0.2, 1.06, 0.334], [0.02, 1.06, 0.334], { layer: L.print, fit: [0.03, 0.05, 0.47, 0.95] });
        m.quad([0.08, 1.4, 0.334], [0.22, 1.4, 0.334], [0.22, 1.58, 0.334], [0.08, 1.58, 0.334], { layer: L.picture, fit: [0.56, 0.08, 0.94, 0.96] });
        for (const [x, y, c] of [[0.11, 1.07, [0.6, 0.1, 0.1]], [0.15, 1.59, [0.14, 0.3, 0.6]], [-0.05, 1.5, [0.6, 0.5, 0.1]]]) {
          m.at(chain(translate(x, y, 0.334), rotX(Math.PI / 2)), () => lathe(m, [[0.013, 0], [0.013, 0.005], [0, 0.007]], 10, { layer: L.plain, col: c, gloss: 0.8 }));
        }
        m.box(-0.14, 1.86, 0, 0.2, 0.28, 0.07, { layer: L.print, fit: [0.52, 0, 1, 1] });                // cereal
        at(0.16, 1.722, 0.02, 0, () => bowl(0.13, 0.07, { layer: L.plain, col: [0.5, 0.2, 0.14], gloss: 0.9 }));
      });
      obb(-0.96, KS - 0.36, 0.38, 0.35);

      // West wall: pans on a rail, a bin, a stool.
      at(KX0 + 0.004, 1.62, KS - 0.95, Math.PI / 2, () => {
        tube(m, [[-0.55, 0, 0.05], [0.55, 0, 0.05]], 0.008, 8, chrome);
        for (const x of [-0.5, 0.5]) tube(m, [[x, 0, 0], [x, 0, 0.05]], 0.006, 6, chrome, false);
        for (const [x, r] of [[-0.34, 0.13], [0, 0.11], [0.32, 0.09]]) {
          tube(m, [[x, 0, 0.05], [x, -0.03, 0.05]], 0.004, 5, chrome, false);
          tube(m, [[x, -0.03, 0.045], [x, -0.2, 0.04]], 0.009, 8, black);
          m.at(chain(translate(x, -0.2 - r, 0.02), rotX(Math.PI / 2)), () => lathe(m, [[0, 0.003], [r * 0.86, 0.003], [r, 0.04], [r * 0.97, 0.04], [r * 0.84, 0.01], [0, 0.01]], 20, iron));
        }
      });
      at(KX0 + 0.26, 0, KS - 0.32, 0, () => {
        lathe(m, [[0.15, 0], [0.16, 0.02], [0.19, 0.56], [0.2, 0.58], [0.2, 0.6], [0.1, 0.66], [0, 0.67]], 20, { layer: L.plain, col: [0.3, 0.36, 0.3], gloss: 0.6 });
        at(0, 0.668, 0, 0, () => lathe(m, [[0.02, 0], [0.012, 0.012], [0.024, 0.03], [0, 0.036]], 10, black));
      });
      obb(KX0 + 0.26, KS - 0.32, 0.2, 0.2);
      at(-3.3, 0, KS - 0.9, 0.4, () => {
        lathe(m, [[0.16, 0.6], [0.165, 0.615], [0.15, 0.63], [0, 0.635]], 20, pine);
        lathe(m, [[0, 0.6], [0.16, 0.6]], 20, pine);
        for (let k = 0; k < 3; k++) {
          const a = k * 2.094;
          tube(m, [[Math.cos(a) * 0.1, 0.6, Math.sin(a) * 0.1], [Math.cos(a) * 0.19, 0, Math.sin(a) * 0.19]], (t) => 0.018 - t * 0.005, 8, pine);
        }
        const ring = [];
        for (let a = 0; a <= 16; a++) ring.push([Math.cos(a * 0.3927) * 0.155, 0.22, Math.sin(a * 0.3927) * 0.155]);
        tube(m, ring, 0.008, 6, pine, false);
      });
      obb(-3.3, KS - 0.9, 0.17, 0.17);
      at(-2.4, 0.008, CZ + 0.62, 0, () => m.quad([-0.4, 0, 0.25], [0.4, 0, 0.25], [0.4, 0, -0.25], [-0.4, 0, -0.25], cloth(0.44, 0.3, 0.2)));
      at(KX1 - 0.004, 1.55, KS - 1.9, -Math.PI / 2, () => m.quad([-0.14, -0.2, 0], [0.14, -0.2, 0], [0.14, 0.2, 0], [-0.14, 0.2, 0], { layer: L.print, fit: [0.03, 0.05, 0.47, 0.95] }));
      // A globe on the ceiling, left on.
      at(H.lean.x, KH, -4.75, 0, () => {
        lathe(m, [[0.07, 0], [0.07, -0.03], [0.04, -0.045]], 16, enamel);
        glows('kitchen', () => m.at(translate(0, -0.14, 0), () => sphere(m, 0.11, 18, glow([1, 0.94, 0.76], 1.5))));
        usable([0, -0.14, 0], 2.6, { group: 'kitchen', noun: 'the light' });
      });
      light([H.lean.x, KH - 0.2, -4.75], [0.6, 0.56, 0.43], 6.5, [KX0, KN, KX1, KS + 0.2], 'kitchen');
    }

    /* ======================================================== living room */
    {
      const LX0 = PX + PT / 2;
      m.quad([1.85, 0.007, -0.1], [3.95, 0.007, -0.1], [3.95, 0.007, -3.1], [1.85, 0.007, -3.1], { layer: L.rug, fit: true, col: [0.56, 0.64, 0.7] });

      // Chimney breast, hearth and mantel on the east wall.
      const FX = IW, FZ = -0.8, depth = 0.36;
      const brick = { layer: L.brick, col: [0.9, 0.86, 0.82] }, soot = { layer: L.brick, col: [0.14, 0.13, 0.12] };
      m.box(FX - depth / 2, 0.625, FZ - 0.625, depth, 1.25, 0.45, brick);
      m.box(FX - depth / 2, 0.625, FZ + 0.625, depth, 1.25, 0.45, brick);
      m.box(FX - depth / 2, 1.0, FZ, depth, 0.5, 0.8, brick);
      m.box(FX - depth / 2, (1.25 + CH) / 2, FZ, depth, CH - 1.25, 1.7, { ...env.living, skip: 'y' });
      m.quad([FX - 0.02, 0, FZ - 0.4], [FX - 0.02, 0, FZ + 0.4], [FX - 0.02, 0.75, FZ + 0.4], [FX - 0.02, 0.75, FZ - 0.4], soot);
      m.quad([FX - depth, 0.012, FZ - 0.4], [FX, 0.012, FZ - 0.4], [FX, 0.012, FZ + 0.4], [FX - depth, 0.012, FZ + 0.4], soot);
      m.box(FX - depth - 0.24, 0.02, FZ, 0.5, 0.04, 1.9, { layer: L.brick, col: [0.5, 0.5, 0.5] });
      at(FX - 0.2, 0, FZ, 0, () => {                                               // grate, logs, a last ember
        for (const z of [-0.26, -0.13, 0, 0.13, 0.26]) tube(m, [[-0.1, 0.1, z], [0.12, 0.1, z]], 0.008, 6, iron);
        for (const x of [-0.1, 0.12]) tube(m, [[x, 0, -0.28], [x, 0.1, -0.28], [x, 0.1, 0.28], [x, 0, 0.28]], 0.008, 6, iron, false);
        for (const [y, z, a, c] of [[0.14, -0.06, 0.1, 0.16], [0.14, 0.1, -0.2, 0.2], [0.21, 0.02, 0.5, 0.12]]) {
          m.at(chain(translate(0, y, z), rotY(a), rotX(Math.PI / 2), translate(0, -0.2, 0)), () => lathe(m, [[0, 0], [0.045, 0], [0.05, 0.02], [0.046, 0.38], [0, 0.4]], 10, { layer: L.bark, col: [c, c, c] }));
        }
        roundBox(m, 0.02, 0.105, 0.02, 0.1, 0.03, 0.3, 0.014, 1, glow([1, 0.3, 0.06], 0.9));
      });
      at(FX - depth / 2 - 0.06, 1.3, FZ, 0, () => {
        roundBox(m, 0, 0, 0, 0.52, 0.06, 1.96, 0.02, 2, { ...dark, gloss: 0.5 });
        for (const z of [-0.78, 0.78]) roundBox(m, 0.04, -0.1, z, 0.3, 0.16, 0.1, 0.03, 2, dark);
        at(-0.08, 0.03, 0, -Math.PI / 2, () => {                                   // mantel clock
          roundBox(m, 0, 0.14, 0, 0.32, 0.28, 0.12, 0.05, 3, { layer: L.grain, col: [0.7, 0.5, 0.36], gloss: 0.7 });
          m.at(chain(translate(0, 0.15, 0.06), rotX(Math.PI / 2)), () => lathe(m, [[0.096, 0], [0.1, 0.006], [0.086, 0.012], [0.084, 0.004]], 24, brass));
          m.quad([-0.084, 0.066, 0.066], [0.084, 0.066, 0.066], [0.084, 0.234, 0.066], [-0.084, 0.234, 0.066], { layer: L.clockface, fit: [0.07, 0.07, 0.93, 0.93], gloss: 0.6 });
        });
        for (const z of [-0.62, 0.62]) at(-0.06, 0.03, z, 0, candlestick);
        for (const [z, a] of [[-0.34, 0.25], [0.36, -0.2]]) m.at(chain(translate(-0.02, 0.15, z), rotY(-Math.PI / 2 + a), rotX(-0.16)), () => frame(0.13, 0.18, PORTRAIT, brass));
      });
      at(FX - depth - 0.004, 1.92, FZ, -Math.PI / 2, () => frame(0.96, 0.62, LANDSCAPE));
      obb(FX - depth / 2, FZ, depth / 2, 0.85);
      at(FX - depth - 0.16, 0, FZ - 0.98, 0, () => {                               // fire irons
        lathe(m, [[0.09, 0], [0.095, 0.012], [0.02, 0.03], [0.012, 0.06], [0.012, 0.66], [0.03, 0.68], [0.012, 0.7], [0, 0.72]], 14, iron);
        for (const a of [0, 2.1, 4.2]) tube(m, [[Math.cos(a) * 0.045, 0.64, Math.sin(a) * 0.045], [Math.cos(a) * 0.06, 0.1, Math.sin(a) * 0.06]], 0.006, 6, iron);
      });
      at(FX - depth - 0.28, 0, FZ + 1.06, 0, () => {                               // log basket
        lathe(m, [[0, 0.01], [0.2, 0.01], [0.24, 0.04], [0.27, 0.3], [0.255, 0.3], [0.225, 0.05], [0, 0.03]], 18, cloth(0.5, 0.36, 0.2));
        for (const [x, a] of [[-0.08, 0.2], [0.07, -0.3], [0, 1.2]]) m.at(chain(translate(x, 0.2 + Math.abs(a) * 0.05, 0), rotY(a), rotX(Math.PI / 2), translate(0, -0.19, 0)), () =>
          lathe(m, [[0, 0], [0.05, 0], [0.055, 0.02], [0.05, 0.36], [0, 0.38]], 10, { layer: L.bark }));
      });
      obb(FX - depth - 0.28, FZ + 1.06, 0.26, 0.26);

      // Sofa along the hall wall, facing the fire.
      const sofa = cloth(0.3, 0.36, 0.3), cushion = cloth(0.34, 0.4, 0.33);
      at(LX0 + 0.47, 0, -1.85, Math.PI / 2, () => {
        roundBox(m, 0, 0.23, 0, 2.1, 0.26, 0.9, 0.05, 3, sofa);
        roundBox(m, 0, 0.56, -0.38, 2.1, 0.76, 0.16, 0.06, 3, sofa);
        for (const s of [-1, 1]) {
          roundBox(m, s * 0.97, 0.44, 0.02, 0.2, 0.62, 0.92, 0.09, 4, sofa);
          for (const z of [-0.34, 0.36]) at(s * 0.93, 0, z, 0, () => lathe(m, [[0.02, 0], [0.03, 0.03], [0.036, 0.1]], 10, dark));
        }
        for (const x of [-0.58, 0, 0.58]) {
          roundBox(m, x, 0.435, 0.06, 0.57, 0.17, 0.72, 0.065, 4, cushion);
          m.at(chain(translate(x, 0.73, -0.27), rotX(-0.2)), () => roundBox(m, 0, 0, 0, 0.57, 0.42, 0.19, 0.08, 4, cushion));
        }
        m.at(chain(translate(-0.66, 0.66, 0.02), rotY(0.4), rotX(-0.35)), () => roundBox(m, 0, 0, 0, 0.38, 0.38, 0.13, 0.062, 4, cloth(0.5, 0.3, 0.16)));
        m.at(chain(translate(0.7, 0.64, 0.0), rotY(-0.3), rotX(-0.3)), () => roundBox(m, 0, 0, 0, 0.36, 0.36, 0.13, 0.062, 4, cloth(0.6, 0.54, 0.4)));
        m.at(chain(translate(0.14, 0.53, 0.2), rotY(0.2)), () => {                 // a blanket, folded and left
          roundBox(m, 0, 0, 0, 0.5, 0.05, 0.34, 0.025, 2, cloth(0.5, 0.18, 0.16));
          roundBox(m, 0.02, 0.045, 0.01, 0.46, 0.045, 0.3, 0.022, 2, cloth(0.46, 0.16, 0.15));
        });
      });
      obb(LX0 + 0.47, -1.85, 0.47, 1.07);
      // Side table and a lamp, switched on.
      at(LX0 + 0.3, 0, -3.1, 0, () => {
        lathe(m, [[0.23, 0.56], [0.24, 0.575], [0.22, 0.59], [0, 0.592]], 24, { ...oak, gloss: 0.5 });
        lathe(m, [[0, 0.56], [0.23, 0.56]], 24, oak);
        lathe(m, [[0.16, 0], [0.17, 0.014], [0.04, 0.04], [0.03, 0.1], [0.045, 0.28], [0.03, 0.42], [0.06, 0.52], [0.1, 0.56]], 16, oak);
        at(0.02, 0.592, 0, 0, () => lamp(0.5, 0.17, 'living', { layer: L.plain, col: [0.5, 0.26, 0.16], gloss: 0.9 }));
        at(-0.13, 0.592, 0.12, 0.6, () => mug({ layer: L.plain, col: [0.3, 0.4, 0.5], gloss: 0.9 }));
      });
      obb(LX0 + 0.3, -3.1, 0.27, 0.24);
      light([LX0 + 0.34, 1.0, -2.95], WARM.map((c) => c * 0.7), 6, [LX0, -ID, IW, ID], 'living');

      // Coffee table: a paper, a magazine, an ashtray, the remote. It stands
      // well clear of the sofa: the strip between them is the only way from
      // the hall to the back door, and it has to be wide enough to walk.
      at(3.22, 0, -1.75, 0, () => {
        roundBox(m, 0, 0.41, 0, 0.5, 0.035, 1.0, 0.014, 2, { ...dark, gloss: 0.6 });
        roundBox(m, 0, 0.16, 0, 0.42, 0.02, 0.9, 0.008, 1, dark);
        for (const sx of [-1, 1]) for (const sz of [-1, 1]) at(sx * 0.2, 0, sz * 0.44, 0, () => lathe(m, [[0.014, 0], [0.02, 0.05], [0.026, 0.39]], 10, dark));
        m.at(chain(translate(0.0, 0.4285, 0.2), rotY(0.2)), () => m.quad([-0.15, 0, 0.21], [0.15, 0, 0.21], [0.15, 0, -0.21], [-0.15, 0, -0.21], { layer: L.print, fit: [0.03, 0.05, 0.47, 0.95] }));
        m.at(chain(translate(-0.06, 0.431, -0.24), rotY(-0.5)), () => {
          m.box(0, 0, 0, 0.21, 0.006, 0.28, { layer: L.plain, col: [0.8, 0.78, 0.7] });
          m.quad([-0.105, 0.0035, 0.14], [0.105, 0.0035, 0.14], [0.105, 0.0035, -0.14], [-0.105, 0.0035, -0.14], { layer: L.print, fit: [0.52, 0.02, 0.98, 0.98], gloss: 0.4 });
        });
        at(0.12, 0.4285, -0.06, 0, () => lathe(m, [[0, 0.003], [0.06, 0.003], [0.07, 0.012], [0.072, 0.03], [0.06, 0.03], [0.052, 0.012], [0, 0.01]], 18, { layer: L.plain, col: [0.36, 0.4, 0.3], gloss: 1 }));
        m.at(chain(translate(-0.12, 0.44, 0.4), rotY(0.7)), () => roundBox(m, 0, 0, 0, 0.05, 0.022, 0.17, 0.008, 1, black));
        at(0.14, 0.4285, 0.38, 2, () => mug());
      });
      obb(3.22, -1.75, 0.25, 0.5);

      // Armchair in the corner by the back window, and a standard lamp.
      at(3.62, 0, -2.78, -0.35, () => {
        const c = cloth(0.42, 0.28, 0.2);
        roundBox(m, 0, 0.23, 0, 0.82, 0.26, 0.82, 0.05, 3, c);
        roundBox(m, 0, 0.6, -0.35, 0.82, 0.84, 0.16, 0.07, 3, c);
        for (const s of [-1, 1]) roundBox(m, s * 0.35, 0.45, 0.02, 0.18, 0.56, 0.82, 0.085, 4, c);
        roundBox(m, 0, 0.43, 0.05, 0.5, 0.16, 0.64, 0.065, 4, cloth(0.46, 0.31, 0.22));
        m.at(chain(translate(0, 0.74, -0.24), rotX(-0.22)), () => roundBox(m, 0, 0, 0, 0.5, 0.44, 0.18, 0.08, 4, cloth(0.46, 0.31, 0.22)));
      });
      obb(3.62, -2.78, 0.46, 0.46);
      at(IW - 0.28, 0, 0.95, 0, () => {
        lathe(m, [[0.15, 0], [0.16, 0.014], [0.03, 0.04], [0.016, 0.1]], 18, brass);
        tube(m, [[0, 0.08, 0], [0, 1.42, 0]], 0.012, 8, brass);
        lathe(m, [[0.2, 1.3], [0.12, 1.58]], 24, cloth(0.8, 0.7, 0.5));
      });

      // Bookcase by the door, with the books actually in it.
      at(LX0 + 0.15, 0, 2.58, Math.PI / 2, () => {
        const wd = 1.36, hg = 1.9, dp = 0.3;
        for (const s of [-1, 1]) m.box(s * (wd / 2 - 0.011), hg / 2, 0, 0.022, hg, dp, dark);
        m.box(0, hg / 2, -dp / 2 + 0.006, wd, hg, 0.012, { layer: L.grain, col: [0.36, 0.32, 0.3] });
        roundBox(m, 0, hg + 0.02, 0.01, wd + 0.06, 0.04, dp + 0.04, 0.016, 2, dark);
        m.box(0, 0.05, 0, wd, 0.1, dp, dark);
        const r = makeRng(31);
        const palette = [[0.42, 0.14, 0.12], [0.14, 0.24, 0.2], [0.16, 0.18, 0.34], [0.5, 0.4, 0.22], [0.26, 0.2, 0.16], [0.56, 0.52, 0.44], [0.34, 0.12, 0.2]];
        for (let s = 0; s < 5; s++) {
          const y = 0.1 + s * 0.36;
          m.box(0, y + 0.011, 0, wd - 0.04, 0.022, dp - 0.02, dark);
          if (s === 4) break;
          let x = -wd / 2 + 0.04;
          while (x < wd / 2 - 0.09) {
            if (r() < 0.07) { x += 0.05 + r() * 0.1; continue; }                  // a gap, a book taken out
            const bw = 0.022 + r() * 0.034, bh = 0.2 + r() * 0.1, bd = 0.15 + r() * 0.07, col = palette[(r() * palette.length) | 0];
            const lean = r() < 0.08 ? 0.16 : 0;
            m.at(chain(translate(x + bw / 2, y + 0.022, -dp / 2 + 0.02 + bd / 2), rotZ(-lean)), () => {
              roundBox(m, 0, bh / 2, 0, bw, bh, bd, 0.004, 1, cloth(...col));
              m.box(0, bh * 0.76, bd / 2 + 0.0006, bw * 0.84, 0.03, 0.001, { layer: L.plain, col: [0.62, 0.5, 0.26], gloss: 0.6 });
            });
            x += bw + 0.003 + lean * 0.3;
          }
        }
        at(0.3, hg + 0.04, 0.02, 0, () => {                                         // a globe on top
          lathe(m, [[0.08, 0], [0.085, 0.012], [0.02, 0.03], [0.012, 0.09]], 16, dark);
          m.at(chain(translate(0, 0.2, 0), rotZ(0.4)), () => sphere(m, 0.12, 20, { layer: L.plaster, col: [0.36, 0.56, 0.66], gloss: 0.7 }));
        });
        at(-0.36, hg + 0.04, 0.02, 0.3, () => frame(0.16, 0.2, PORTRAIT, brass));
      });
      obb(LX0 + 0.15, 2.58, 0.16, 0.7);

      // The television in the far corner, on a cabinet with a video recorder
      // and three tapes. It is on. There is nothing on it.
      at(3.82, 0, 2.82, -2.36, () => {
        roundBox(m, 0, 0.3, 0, 0.92, 0.44, 0.46, 0.012, 1, dark);
        for (const sx of [-1, 1]) for (const sz of [-1, 1]) at(sx * 0.4, 0, sz * 0.18, 0, () => lathe(m, [[0.014, 0], [0.024, 0.08]], 10, dark));
        m.box(0, 0.3, 0.226, 0.84, 0.3, 0.012, pit);
        roundBox(m, -0.12, 0.26, 0.19, 0.44, 0.09, 0.07, 0.008, 1, black);
        m.box(-0.2, 0.27, 0.227, 0.2, 0.022, 0.004, pit);
        m.box(0.02, 0.255, 0.227, 0.07, 0.014, 0.004, glow([0.2, 1, 0.3], 1.2));
        for (let k = 0; k < 3; k++) m.at(chain(translate(0.27 + k * 0.012, 0.21 + k * 0.027, 0.14), rotY(k * 0.2 - 0.2)), () => {
          m.box(0, 0, 0, 0.19, 0.025, 0.105, black);
          m.box(0, 0, 0.0535, 0.14, 0.015, 0.001, { layer: L.plain, col: [0.8, 0.78, 0.7] });
        });
        roundBox(m, 0, 0.82, 0, 0.74, 0.58, 0.5, 0.045, 3, { layer: L.grain, col: [0.62, 0.5, 0.42], gloss: 0.6 });
        roundBox(m, -0.07, 0.83, 0.246, 0.52, 0.44, 0.02, 0.03, 3, black);
        // The screen goes dark when the set is switched off, not merely unlit.
        glows('tv', () => roundBox(m, -0.07, 0.83, 0.256, 0.46, 0.38, 0.012, 0.045, 3, { layer: L.static, emit: 1.7, gloss: 1, tile: 0.7 }), { offTint: [0.02, 0.022, 0.026] });
        usable([-0.07, 0.83, 0.3], 2.3, { group: 'tv', noun: 'the television' });
        for (const y of [0.98, 0.9]) m.at(chain(translate(0.27, y, 0.25), rotX(Math.PI / 2)), () => lathe(m, [[0.03, 0], [0.03, 0.008], [0.022, 0.012], [0.022, 0.03], [0, 0.032]], 14, { layer: L.plain, col: [0.5, 0.5, 0.48], gloss: 0.9 }));
        m.quad([0.215, 0.6, 0.252], [0.325, 0.6, 0.252], [0.325, 0.82, 0.252], [0.215, 0.82, 0.252], { layer: L.metal, col: [0.12, 0.12, 0.12], tile: 0.12 });
        at(0.06, 1.11, -0.05, 0, () => {                                            // the aerial
          lathe(m, [[0.05, 0], [0.052, 0.008], [0.02, 0.03], [0.014, 0.04]], 14, black);
          for (const s of [-1, 1]) tube(m, [[0, 0.03, 0], [s * 0.3, 0.52, -0.06]], (t) => 0.004 - t * 0.0015, 6, chrome);
        });
      });
      obb(3.82, 2.82, 0.5, 0.5);
      light([3.44, 0.86, 2.44], [0.26, 0.36, 0.62], 5.5, [LX0, -ID, IW, ID], 'tv', { tv: true });

      at(LX0 + 0.004, 1.6, -1.85, Math.PI / 2, () => frame(0.8, 0.56, LANDSCAPE));
    }
  });
}
