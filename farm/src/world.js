/**
 * The farm: a clapboard farmhouse and a gambrel barn in a fenced yard, a
 * paddock, a dirt road, and conifer forest closing in on every side.
 *
 * Everything is authored in metres with +Y up, +X east and +Z south. The
 * player arrives on the road to the south, so the house and the barn both
 * face roughly south: the first thing seen is the porch light, the barn lamp
 * and a black wall of trees behind them.
 *
 * build() returns the vertex data plus everything the rest of the game needs
 * to agree with it: lights, colliders, where the tracks run, and how high the
 * floor is at any point. Building and collision share the same site
 * transforms (see math.js) so a wall and its collider cannot drift apart.
 */
import { Mesh, KIND, stick, wall } from './geom.js';
import { drape, tube } from './detail.js';
import { buildInterior } from './interior.js';
import { buildTruck, TRUCK_BOXES } from './truck.js';
import { L, TILES } from './textures.js';
import {
  rotY, rotX, rotZ, translate, chain, xformPoint, xformDir, normalize,
  siteToWorld, worldToSite, smoothstep,
} from './math.js';
import { makeRng } from '../../src/core/rng.js';

export const SITE = {
  house: { x: -9, z: -6, yaw: 0.1 },
  barn: { x: 19, z: -15, yaw: -0.28 },
  truck: { x: 0.2, z: 4.4, yaw: 0.42 },
};
export const SPAWN = { x: 4.6, z: 20.5, yaw: 0.12, pitch: 0.03 };

// House and barn proportions, shared by the builders, colliders and floor.
// `split` is where the furnished ground floor stops and the empty shell above it
// begins; `wall` is the thickness of an outside wall; `lean` is the kitchen.
const H = {
  hw: 4.5, hd: 3.5, found: 0.5, top: 6.0, porch: 2.3, wall: 0.14, room: 2.6, split: 3.3,
  lean: { x: -2.4, w: 4.0, d: 2.6, top: 3.0 },
};
const B = { hw: 4.5, hl: 6.5, wall: 4.2, kneeX: 2.7, kneeY: 7.0, ridge: 8.3, doorW: 1.75, doorH: 3.6, ajar: 1.3 };

const TRIM = [0.9, 0.88, 0.82];
const DARK_WOOD = [0.42, 0.4, 0.38];
const WARM = [1.0, 0.7, 0.4];
const SODIUM = [1.0, 0.6, 0.24];

/* ----------------------------------------------------------- terrain --- */

function hash2(ix, iz) {
  let h = Math.imul(ix, 374761393) ^ Math.imul(iz, 668265263);
  h = Math.imul(h ^ (h >>> 13), 1274126177);
  return ((h ^ (h >>> 16)) >>> 0) / 4294967296;
}
function vnoise(x, z) {
  const ix = Math.floor(x), iz = Math.floor(z);
  const tx = x - ix, tz = z - iz;
  const sx = tx * tx * (3 - 2 * tx), sz = tz * tz * (3 - 2 * tz);
  const a = hash2(ix, iz), b = hash2(ix + 1, iz), c = hash2(ix, iz + 1), d = hash2(ix + 1, iz + 1);
  return a + (b - a) * sx + (c - a) * sz + (a - b - c + d) * sx * sz;
}

/** Dead flat under the buildings, rolling once it is out among the trees. */
export function groundHeight(x, z) {
  const m = smoothstep(38, 100, Math.hypot(x - 8, z + 7));
  return m * ((vnoise(x / 70, z / 70) - 0.42) * 15 + (vnoise(x / 19 + 7, z / 19 + 3) - 0.5) * 2.4);
}

/** The clearing: an ellipse with a ragged edge. Everything outside is forest. */
const clearingEdge = (x, z) => {
  const ex = (x - 11) / 60, ez = (z + 8) / 35;
  return ex * ex + ez * ez - (vnoise(x / 15 + 3, z / 15 + 9) - 0.5) * 0.42;
};

/** Dirt tracks as line segments [x1, z1, x2, z2, width]; the shader paints them. */
export const PATHS = [
  [-180, 22, 180, 22, 4.4],       // the road
  [4, 22, 4, 6, 3.2],             // driveway, through the gate
  [4, 6, 8, -1, 3.0],
  [8, -1, 17, -6.5, 3.0],         // on to the barn doors
  [4, 6, -8.3, 1.2, 1.5],         // footpath to the porch steps
];
/** Worn bare ground [x, z, radius]. */
export const PATCHES = [[17.3, -6.9, 4.6], [-8.3, 0.7, 1.9], [4, 14, 2.6], [34.5, -5, 3.2]];

/* ----------------------------------------------------------- helpers --- */

/**
 * A sash window on the wall plane z = 0, facing +Z. No hole is cut: the pane
 * sits just proud of the siding inside a deep frame, which at night reads the
 * same and keeps the walls to one quad each.
 */
function sashWindow(m, x, y, w, h, lit, glow = 1) {
  const trim = { layer: L.plain, col: TRIM };
  m.quad([x - w / 2, y, 0.03], [x + w / 2, y, 0.03], [x + w / 2, y + h, 0.03], [x - w / 2, y + h, 0.03], {
    layer: lit ? L.windowLit : L.windowDark, fit: true, emit: lit ? glow : 0, occ: 0.5,
  });
  const t = 0.1, d = 0.08;
  m.box(x - w / 2 - t / 2, y + h / 2, d / 2, t, h + 2 * t, d, trim);
  m.box(x + w / 2 + t / 2, y + h / 2, d / 2, t, h + 2 * t, d, trim);
  m.box(x, y + h + t / 2 + 0.02, d / 2 + 0.01, w + 2 * t + 0.08, t + 0.04, d + 0.02, trim);
  m.box(x, y - 0.04, 0.08, w + 2 * t + 0.12, 0.08, 0.16, trim);   // sill
  m.box(x, y + h / 2, 0.05, w, 0.06, 0.04, trim);                 // meeting rail
  m.box(x, y + h / 2, 0.045, 0.035, h, 0.03, trim);               // centre muntin
}

/**
 * A window you can see through, fitted into a hole in a wall `t` thick:
 * casing and sill outside, two sashes in the reveal, casing, stool and apron
 * inside, and a pair of curtains on a rod. There is no glass -- it would need
 * a blended pass of its own -- and at night, behind curtains, it is not missed.
 */
function fitWindow(m, x, y, w, h, t, cloth) {
  const trim = { layer: L.plain, col: TRIM };
  const e = 0.1, d = 0.08;
  m.box(x - w / 2 - e / 2, y + h / 2, d / 2, e, h + 2 * e, d, trim);
  m.box(x + w / 2 + e / 2, y + h / 2, d / 2, e, h + 2 * e, d, trim);
  m.box(x, y + h + e / 2 + 0.02, d / 2 + 0.01, w + 2 * e + 0.08, e + 0.04, d + 0.02, trim);
  m.box(x, y - 0.04, 0.08, w + 2 * e + 0.12, 0.08, 0.16, trim);
  // Sashes: a frame round each, a bar down the middle, the lower one set back.
  for (const [y0, z] of [[y + h / 2, -0.04], [y, -0.075]]) {
    const hh = h / 2;
    m.box(x, y0 + 0.02, z, w, 0.04, 0.03, trim); m.box(x, y0 + hh - 0.02, z, w, 0.04, 0.03, trim);
    m.box(x - w / 2 + 0.02, y0 + hh / 2, z, 0.04, hh, 0.03, trim); m.box(x + w / 2 - 0.02, y0 + hh / 2, z, 0.04, hh, 0.03, trim);
    m.box(x, y0 + hh / 2, z, 0.025, hh, 0.02, trim);
  }
  const zi = -t;
  m.box(x - w / 2 - 0.045, y + h / 2, zi - 0.01, 0.09, h + 0.18, 0.02, trim);
  m.box(x + w / 2 + 0.045, y + h / 2, zi - 0.01, 0.09, h + 0.18, 0.02, trim);
  m.box(x, y + h + 0.05, zi - 0.012, w + 0.24, 0.1, 0.024, trim);
  m.box(x, y - 0.015, zi - 0.045, w + 0.26, 0.03, 0.09, trim);       // stool
  m.box(x, y - 0.08, zi - 0.01, w + 0.18, 0.1, 0.02, trim);         // apron
  if (!cloth) return;
  const rod = y + h + 0.13, zr = zi - 0.125, pw = w * (cloth.open === undefined ? 0.36 : cloth.open);
  tube(m, [[x - w / 2 - 0.16, rod, zr], [x + w / 2 + 0.16, rod, zr]], 0.012, 8, { layer: L.plain, col: [0.3, 0.22, 0.12], gloss: 0.6 });
  for (const s of [-1, 1]) tube(m, [[x + s * (w / 2 + 0.12), rod, zi], [x + s * (w / 2 + 0.12), rod, zr]], 0.007, 6, { layer: L.plain, col: [0.3, 0.22, 0.12] }, false);
  for (const s of [-1, 1]) {
    const left = s < 0 ? x - w / 2 - 0.1 : x + w / 2 + 0.1 - pw;
    m.at(translate(left, y - 0.2, zr), () => {
      const hang = () => drape(m, pw, h + 0.32, Math.max(2, Math.round(pw / 0.11)), 0.022, cloth);
      // Curtains lit from behind belong to their room's switch: when the lamp
      // goes off they stop glowing, so they are kept as a separate part.
      if (cloth.glowsWith) cloth.glowsWith.parts.push(m.part(hang)); else hang();
    });
  }
}

/** The casing round a doorway, outside. The door itself is hung separately. */
function casing(m, x, y, w, h) {
  const trim = { layer: L.plain, col: TRIM };
  m.box(x - w / 2 - 0.06, y + h / 2, 0.04, 0.12, h + 0.12, 0.08, trim);
  m.box(x + w / 2 + 0.06, y + h / 2, 0.04, 0.12, h + 0.12, 0.08, trim);
  m.box(x, y + h + 0.07, 0.05, w + 0.34, 0.14, 0.1, trim);
}

/** Roof plane from a lower edge to an upper edge, running the length of the building. */
function roofPlane(m, x0, y0, x1, y1, z0, z1, th, top, under, edge) {
  if (x0 < x1) m.slab([x0, y0, z0], [x0, y0, z1], [x1, y1, z1], [x1, y1, z0], th, top, under, edge);
  else m.slab([x0, y0, z1], [x0, y0, z0], [x1, y1, z0], [x1, y1, z1], th, top, under, edge);
}

const siteMatrix = (s, y = 0) => chain(translate(s.x, y, s.z), rotY(s.yaw));

/**
 * Register a box that blocks moonlight, given in a site's own coordinates.
 * The scene has no shadow maps; the shader instead asks, for each pixel,
 * whether a ray toward the moon passes through one of a handful of boxes.
 * Each box must sit just inside the thing it stands for, or that thing's own
 * sunlit faces would start inside the box and shade themselves.
 */
function castShadow(w, site, cx, cz, hx, hz, y0, y1) {
  const [x, z] = siteToWorld(site, cx, cz);
  w.occluders.push({ x, z, hx, hz, yaw: site.yaw, y0, y1 });
}

/* ------------------------------------------------------------- house --- */

function buildHouse(m, w) {
  const { hw, hd, found: F, top: T, porch: pd } = H;
  const M = siteMatrix(SITE.house);
  const rise = hd * Math.tan(38 * Math.PI / 180), ridge = T + rise;
  const siding = { layer: L.siding, occ: [0.9, 0.9, 0.68, 0.68] };
  const trim = { layer: L.plain, col: TRIM };
  const wood = { layer: L.wood };
  const shade = { layer: L.wood, col: DARK_WOOD, occ: 0.2 };
  const { x: lx, w: lw, d: ld, top: lt } = H.lean;     // the kitchen lean-to
  const WT = H.wall, SP = H.split;
  const low = { layer: L.siding, occ: 0.9 };
  // What the inside of each outside wall is finished in, room by room.
  const dining = { layer: L.wallpaper }, hall = { layer: L.plaster, col: [0.9, 0.86, 0.76] };
  const living = { layer: L.wallpaper, col: [0.8, 0.88, 0.86] }, kitchen = { layer: L.plaster, col: [0.84, 0.88, 0.76] };
  const sheer = { layer: L.fabric, col: [0.9, 0.84, 0.7], emit: 0.16, glowsWith: w.groups.dining };   // lit from behind
  const heavy = { layer: L.fabric, col: [0.36, 0.22, 0.2] };
  const win = (x, y0, wd, hg) => ({ x0: x - wd / 2, x1: x + wd / 2, y0, y1: y0 + hg });

  m.at(M, () => {
    m.box(0, F / 2, 0, hw * 2 + 0.14, F, hd * 2 + 0.14, { layer: L.brick, col: [0.66, 0.64, 0.62], skip: 'y' });
    m.box(0, (SP + T) / 2, 0, hw * 2, T - SP, hd * 2, { ...siding, skip: 'yY' });      // the upper storey is still a shell
    m.tri([hw, T, hd], [hw, T, -hd], [hw, ridge, 0], { layer: L.siding, occ: 0.75 });
    m.tri([-hw, T, -hd], [-hw, T, hd], [-hw, ridge, 0], { layer: L.siding, occ: 0.75 });
    for (const sx of [-1, 1]) for (const sz of [-1, 1]) {            // corner boards
      m.box(sx * (hw + 0.01), (F + T) / 2, sz * (hd + 0.01), 0.16, T - F, 0.16, trim);
    }
    m.box(0, T - 0.12, hd + 0.02, hw * 2, 0.24, 0.05, trim);         // frieze boards
    m.box(0, T - 0.12, -hd - 0.02, hw * 2, 0.24, 0.05, trim);

    // Gable roof, ridge running east-west.
    const e = 0.5, g = 0.4, drop = e * Math.tan(38 * Math.PI / 180);
    const top = { layer: L.shingle }, edge = { layer: L.plain, col: TRIM, occ: 0.85 };
    for (const s of [1, -1]) {
      const a = [-s * (hw + g), T - drop + 0.1, s * (hd + e)], b = [s * (hw + g), T - drop + 0.1, s * (hd + e)];
      m.slab(a, b, [s * (hw + g), ridge + 0.1, 0], [-s * (hw + g), ridge + 0.1, 0], 0.14, top, shade, edge);
    }
    m.box(0, ridge + 0.13, 0, (hw + g) * 2, 0.08, 0.3, { layer: L.shingle, col: [0.7, 0.7, 0.7] });

    // Chimney up the east gable.
    m.box(hw + 0.37, 5.0, -0.8, 0.74, 10.0, 0.9, { layer: L.brick, skip: 'y' });
    m.box(hw + 0.37, 10.06, -0.8, 0.9, 0.12, 1.06, { layer: L.brick, col: [0.6, 0.6, 0.6] });

    // Front wall: door, two windows down, three up.
    m.at(translate(0, 0, hd), () => {
      const holes = [{ x0: -0.475, x1: 0.475, y0: F, y1: F + 2.05 }, win(-2.75, F + 0.85, 1.0, 1.5), win(2.75, F + 0.85, 1.0, 1.5)];
      for (const [a, b, inner] of [[-hw, -1.1, dining], [-1.1, 1.1, hall], [1.1, hw, living]]) wall(m, a, b, F, SP, holes, low, inner, WT, trim);
      casing(m, 0, F, 0.95, 2.05);
      fitWindow(m, -2.75, F + 0.85, 1.0, 1.5, WT, sheer);
      fitWindow(m, 2.75, F + 0.85, 1.0, 1.5, WT, heavy);
      sashWindow(m, -2.75, 4.15, 0.95, 1.3, false);
      sashWindow(m, 0, 4.15, 0.95, 1.3, false);
      sashWindow(m, 2.75, 4.15, 0.95, 1.3, true, 0.55);
      m.box(0.85, 2.72, 0.07, 0.14, 0.2, 0.14, { layer: L.plain, col: [0.1, 0.1, 0.1] });   // porch lamp
      m.box(0.85, 2.58, 0.1, 0.09, 0.11, 0.09, { layer: L.plain, col: WARM, emit: 4 });
      m.quad([-0.55, F + 0.012, 0.8], [0.55, F + 0.012, 0.8], [0.55, F + 0.012, 0.15], [-0.55, F + 0.012, 0.15],
        { layer: L.hay, col: [0.35, 0.3, 0.26], occ: 0.3 });                                 // doormat
    });
    m.at(chain(translate(-hw, 0, 0), rotY(-Math.PI / 2)), () => {     // west wall
      wall(m, -hd, hd, F, SP, [win(1.7, F + 0.85, 1.0, 1.5), win(-1.7, F + 0.85, 1.0, 1.5)], low, dining, WT, trim);
      fitWindow(m, 1.7, F + 0.85, 1.0, 1.5, WT, sheer);
      fitWindow(m, -1.7, F + 0.85, 1.0, 1.5, WT, sheer);
      sashWindow(m, 1.7, 4.15, 0.95, 1.3, false);
      sashWindow(m, -1.7, 4.15, 0.95, 1.3, false);
      sashWindow(m, 0, T + 0.7, 0.6, 0.8, false);
    });
    m.at(chain(translate(hw, 0, 0), rotY(Math.PI / 2)), () => {       // east wall
      wall(m, -hd, hd, F, SP, [win(-2.0, F + 0.85, 1.0, 1.5), win(2.4, F + 0.85, 0.9, 1.5)], low, living, WT, trim);
      fitWindow(m, -2.0, F + 0.85, 1.0, 1.5, WT, heavy);
      fitWindow(m, 2.4, F + 0.85, 0.9, 1.5, WT, heavy);
      sashWindow(m, -2.0, 4.15, 0.95, 1.3, false);
      sashWindow(m, 2.4, 4.15, 0.9, 1.3, false);
    });
    m.at(chain(translate(0, 0, -hd), rotY(Math.PI)), () => {          // back wall
      // Seen from behind the house, so left and right are swapped: the living
      // room is on the low side, and the stretch the lean-to covers is a
      // kitchen wall on its outer face, with the doorway through to it.
      const holes = [win(-3.7, F + 0.95, 0.8, 1.3), { x0: 1.95, x1: 2.95, y0: F, y1: F + 2.05 }, { x0: -2.75, x1: -1.85, y0: F, y1: F + 2.0 }];
      const out = (a) => (a >= 0.4 && a < 4.4 ? kitchen : low);
      for (const [a, b, inner] of [[-hw, -1.1, living], [-1.1, 0.4, hall], [0.4, 1.1, hall], [1.1, 4.4, dining], [4.4, hw, dining]]) {
        wall(m, a, b, F, SP, holes, out(a), inner, WT, trim);
      }
      casing(m, -2.3, F, 0.9, 2.0);
      fitWindow(m, -3.7, F + 0.95, 0.8, 1.3, WT, heavy);
      sashWindow(m, -2.4, 4.15, 0.95, 1.3, false);
      sashWindow(m, 2.4, 4.15, 0.95, 1.3, false);
      m.box(-2.3, F / 2, 0.45, 1.5, F, 0.9, { layer: L.brick, col: [0.62, 0.6, 0.58] });   // back stoop
      m.box(-2.3, F / 4, 1.05, 1.2, F / 2, 0.3, { layer: L.brick, col: [0.58, 0.56, 0.54] });  // and a step down from it
    });

    // Kitchen lean-to off the back.
    m.box(lx, F / 2, -hd - ld / 2, lw + 0.12, F, ld + 0.12, { layer: L.brick, col: [0.66, 0.64, 0.62], skip: 'y' });
    m.at(chain(translate(lx - lw / 2, 0, -hd - ld / 2), rotY(-Math.PI / 2)), () => wall(m, -ld / 2, ld / 2, F, lt, [], low, kitchen, WT, trim));
    m.at(chain(translate(lx + lw / 2, 0, -hd - ld / 2), rotY(Math.PI / 2)), () => wall(m, -ld / 2, ld / 2, F, lt, [], low, kitchen, WT, trim));
    m.at(chain(translate(lx, 0, -hd - ld), rotY(Math.PI)), () => {
      wall(m, -lw / 2, lw / 2, F, lt, [win(0, F + 1.0, 1.3, 1.1)], low, kitchen, WT, trim);
      fitWindow(m, 0, F + 1.0, 1.3, 1.1, WT, { layer: L.fabric, col: [0.86, 0.8, 0.62], emit: 0.14, open: 0.3, glowsWith: w.groups.kitchen });
    });
    m.slab([lx + lw / 2 + 0.3, lt - 0.1, -hd - ld - 0.4], [lx - lw / 2 - 0.3, lt - 0.1, -hd - ld - 0.4],
      [lx - lw / 2 - 0.3, lt + 0.75, -hd], [lx + lw / 2 + 0.3, lt + 0.75, -hd], 0.12, top, shade, edge);
    for (const sx of [-1, 1]) {                                        // lean-to gable infill
      const x = lx + sx * lw / 2;
      const p = [[x, lt, -hd - ld], [x, lt, -hd], [x, lt + 0.7, -hd]];
      m.tri(...(sx > 0 ? [p[1], p[0], p[2]] : p), { layer: L.siding, occ: 0.7 });
    }

    // Porch: deck, posts, shed roof, railings, steps.
    const pz = hd + pd;
    m.box(0, F - 0.06, hd + pd / 2, hw * 2, 0.12, pd, { ...wood, occ: 0.45 });
    m.box(0, (F - 0.12) / 2, pz - 0.03, hw * 2, F - 0.12, 0.05, { layer: L.wood, col: DARK_WOOD, occ: 0.6 });
    for (const sx of [-1, 1]) m.box(sx * (hw - 0.03), (F - 0.12) / 2, hd + pd / 2, 0.05, F - 0.12, pd, { layer: L.wood, col: DARK_WOOD, occ: 0.6 });
    const posts = [-4.4, -2.6, -0.95, 0.95, 2.6, 4.4];
    for (const x of posts) m.box(x, F + 1.26, pz - 0.1, 0.13, 2.52, 0.13, trim);
    m.box(0, F + 2.6, pz - 0.1, hw * 2, 0.16, 0.16, trim);
    m.slab([-hw - 0.25, 3.12, pz + 0.38], [hw + 0.25, 3.12, pz + 0.38], [hw + 0.25, 3.78, hd], [-hw - 0.25, 3.78, hd],
      0.1, top, { layer: L.wood, col: [0.7, 0.68, 0.62], occ: 0.12 }, edge);
    const rail = (ax, az, bx, bz) => {
      stick(m, [ax, F + 0.9, az], [bx, F + 0.9, bz], 0.07, 0.06, trim);
      stick(m, [ax, F + 0.13, az], [bx, F + 0.13, bz], 0.05, 0.05, trim);
      const n = Math.max(1, Math.round(Math.hypot(bx - ax, bz - az) / 0.16));
      for (let i = 1; i < n; i++) {
        const t = i / n;
        m.box(ax + (bx - ax) * t, F + 0.51, az + (bz - az) * t, 0.035, 0.72, 0.035, trim);
      }
    };
    for (let i = 0; i < posts.length - 1; i++) if (i !== 2) rail(posts[i], pz - 0.1, posts[i + 1], pz - 0.1);
    rail(-4.4, hd, -4.4, pz - 0.1);
    rail(4.4, hd, 4.4, pz - 0.1);
    m.box(0, F * 2 / 6, pz + 0.15, 1.8, F * 2 / 3, 0.3, wood);          // steps
    m.box(0, F / 6, pz + 0.45, 1.8, F / 3, 0.3, wood);

    // A chair on the porch, turned a little toward the road.
    m.at(chain(translate(-2.9, F, hd + 1.0), rotY(0.3)), () => {
      const c = { layer: L.wood, col: [0.8, 0.78, 0.7] };
      m.box(0, 0.42, 0, 0.5, 0.05, 0.48, c);
      m.box(0, 0.78, -0.23, 0.5, 0.7, 0.04, c);
      for (const sx of [-1, 1]) {
        m.box(sx * 0.22, 0.21, 0.2, 0.05, 0.42, 0.05, c);
        m.box(sx * 0.22, 0.21, -0.2, 0.05, 0.42, 0.05, c);
        m.box(sx * 0.27, 0.62, 0, 0.05, 0.04, 0.5, c);
      }
    });

    // Split logs stacked against the east wall, ends out.
    const rng = makeRng(91);
    for (let row = 0; row < 5; row++) for (let i = 0; i < 9 - (row > 3 ? 2 : 0); i++) {
      const r = 0.1 + rng() * 0.035;
      m.at(chain(translate(hw + 0.08, 0.12 + row * 0.2, 1.0 + i * 0.235 + (row % 2) * 0.11), rotZ(-Math.PI / 2)), () =>
        m.cyl(r, r, 0.48 + rng() * 0.08, 6, { layer: L.bark, cap: { layer: L.wood, col: [1.0, 0.86, 0.66] } }));
    }
  });

  // Lights. Windows throw a warm trapezoid outwards; none of them cast shadows,
  // so each is a spot aimed away from the wall to keep it off the far side.
  // These are the outdoor ones (mode 2): the rooms have their own, and a porch
  // light that reached through the front wall would undo every one of them.
  // The ones standing in for light spilling out of a window go off with the
  // room behind it, so each is handed to that room's switch.
  const lamp = (p, color, range, dir, cos, room) => {
    const light = {
      pos: xformPoint(M, p), color, range, mode: 2,
      dir: dir ? normalize(xformDir(M, dir)) : [0, -1, 0], cos: dir ? cos : -2,
    };
    w.lights.push(light);
    if (room) room.lights.push(light);
  };
  lamp([0.85, 2.55, hd + 0.3], WARM.map((c) => c * 2.6), 12);
  lamp([-2.75, 2.2, hd + 0.2], WARM.map((c) => c * 1.4), 7, [0, -0.55, 1], 0.35, w.groups.dining);
  lamp([-hw - 0.2, 2.2, 1.7], WARM.map((c) => c * 2.2), 11, [-1, -0.6, 0], 0.3, w.groups.dining);
  lamp([lx, 2.1, -hd - ld - 0.2], WARM.map((c) => c * 1.8), 10, [0, -0.6, -1], 0.3, w.groups.kitchen);
  lamp([2.75, 4.8, hd + 0.2], WARM.map((c) => c * 0.8), 6, [0, -0.8, 1], 0.3);
  w.halos.push({ pos: xformPoint(M, [0.85, 2.58, hd + 0.18]), color: WARM, size: 1.5 });

  const S = SITE.house;
  const obb = (lx2, lz2, hx, hz) => {
    const [x, z] = siteToWorld(S, lx2, lz2);
    w.boxes.push({ x, z, hx, hz, yaw: S.yaw });
  };
  // Outside walls as runs between the doorways. `run` takes the two ends of a
  // wall's centre line; everything indoors is axis-aligned in house space.
  const run = (x0, z0, x1, z1, th = 0.07) => obb((x0 + x1) / 2, (z0 + z1) / 2, Math.abs(x1 - x0) / 2 + th, Math.abs(z1 - z0) / 2 + th);
  const c = WT / 2;
  run(-hw, hd - c, -0.475, hd - c); run(0.475, hd - c, hw, hd - c);
  run(-hw, -hd + c, -2.95, -hd + c); run(-1.95, -hd + c, 1.85, -hd + c); run(2.75, -hd + c, hw, -hd + c);
  run(-hw + c, -hd, -hw + c, hd); run(hw - c, -hd, hw - c, hd);
  run(lx - lw / 2 + c, -hd - ld, lx - lw / 2 + c, -hd); run(lx + lw / 2 - c, -hd - ld, lx + lw / 2 - c, -hd);
  run(lx - lw / 2, -hd - ld + c, lx + lw / 2, -hd - ld + c);
  w.house = {
    x: S.x, z: S.z, yaw: S.yaw, hx: hw - 0.02, hz: hd - 0.02, ceiling: SP,
    lean: [lx - lw / 2 + 0.02, -hd - ld + 0.02, lx + lw / 2 - 0.02, -hd + 0.02],
  };
  buildInterior(m, w, M, H, { run, obb, hall, dining, living, kitchen, site: S });
  castShadow(w, S, 0, 0, hw - 0.04, hd - 0.04, 0, T);                  // walls
  castShadow(w, S, 0, 0, hw - 0.04, hd / 2, T, T + rise / 2 - 0.1);    // the roof, as far as a box fits under it
  castShadow(w, S, lx, -hd - ld / 2, lw / 2 - 0.04, ld / 2, 0, lt);
  obb(hw + 0.37, -0.8, 0.42, 0.5);
  obb(hw + 0.3, 2.0, 0.32, 1.2);                 // woodpile
  obb(-2.725, hd + pd - 0.1, 1.775, 0.08);       // porch rails either side of the steps
  obb(2.725, hd + pd - 0.1, 1.775, 0.08);
  obb(-4.4, hd + pd / 2, 0.08, pd / 2);
  obb(4.4, hd + pd / 2, 0.08, pd / 2);
  obb(-2.9, hd + 1.0, 0.3, 0.3);                 // chair
}

/* -------------------------------------------------------------- barn --- */

function buildBarn(m, w) {
  const { hw, hl, wall, kneeX, kneeY, ridge, doorW, doorH, ajar } = B;
  const M = siteMatrix(SITE.barn);
  const planks = { layer: L.barn, occ: [0.9, 0.9, 0.72, 0.72] };
  const trim = { layer: L.plain, col: TRIM };
  // The inside gets no sky at all. Without shadows that is the only thing
  // stopping moonlight shining straight through the roof onto the floor.
  const inside = { layer: L.wood, uvRot: true, col: [0.62, 0.58, 0.52], occ: 0.05 };
  const beam = { layer: L.wood, col: [0.7, 0.64, 0.56], occ: 0.05 };
  const rng = makeRng(57);

  m.at(M, () => {
    // Outer shell: long walls, back gable, front gable around the doorway.
    m.quad([hw, 0, hl], [hw, 0, -hl], [hw, wall, -hl], [hw, wall, hl], planks);
    m.quad([-hw, 0, -hl], [-hw, 0, hl], [-hw, wall, hl], [-hw, wall, -hl], planks);
    m.poly([[hw, 0, -hl], [-hw, 0, -hl], [-hw, wall, -hl], [-kneeX, kneeY, -hl], [0, ridge, -hl], [kneeX, kneeY, -hl], [hw, wall, -hl]], { layer: L.barn });
    m.quad([-hw, 0, hl], [-doorW, 0, hl], [-doorW, wall, hl], [-hw, wall, hl], planks);
    m.quad([doorW, 0, hl], [hw, 0, hl], [hw, wall, hl], [doorW, wall, hl], planks);
    m.quad([-doorW, doorH, hl], [doorW, doorH, hl], [doorW, wall, hl], [-doorW, wall, hl], { layer: L.barn });
    m.poly([[-hw, wall, hl], [hw, wall, hl], [kneeX, kneeY, hl], [0, ridge, hl], [-kneeX, kneeY, hl]], { layer: L.barn, occ: 0.8 });

    // Inner shell, a hand's width in, so the interior can be lit differently.
    const i = 0.1;
    m.quad([hw - i, 0, -hl + i], [hw - i, 0, hl - i], [hw - i, wall, hl - i], [hw - i, wall, -hl + i], inside);
    m.quad([-hw + i, 0, hl - i], [-hw + i, 0, -hl + i], [-hw + i, wall, -hl + i], [-hw + i, wall, hl - i], inside);
    m.poly([[-hw, 0, -hl + i], [hw, 0, -hl + i], [hw, wall, -hl + i], [kneeX, kneeY, -hl + i], [0, ridge, -hl + i], [-kneeX, kneeY, -hl + i], [-hw, wall, -hl + i]], inside);
    m.quad([-doorW, 0, hl - i], [-hw, 0, hl - i], [-hw, wall, hl - i], [-doorW, wall, hl - i], inside);
    m.quad([hw, 0, hl - i], [doorW, 0, hl - i], [doorW, wall, hl - i], [hw, wall, hl - i], inside);
    m.poly([[hw, wall, hl - i], [-hw, wall, hl - i], [-kneeX, kneeY, hl - i], [0, ridge, hl - i], [kneeX, kneeY, hl - i]], inside);
    m.quad([doorW, doorH, hl - i], [-doorW, doorH, hl - i], [-doorW, wall, hl - i], [doorW, wall, hl - i], inside);
    m.quad([-hw + i, 0.03, hl - i], [hw - i, 0.03, hl - i], [hw - i, 0.03, -hl + i], [-hw + i, 0.03, -hl + i],
      { layer: L.dirt, col: [0.8, 0.76, 0.66], occ: 0.05 });

    // Gambrel roof in corrugated iron: two steep planes, two shallow.
    const g = 0.5, sl = Math.hypot(kneeX - hw, kneeY - wall);
    const ex = hw + 0.45 * (hw - kneeX) / sl, ey = wall - 0.45 * (kneeY - wall) / sl;
    const top = { layer: L.metal }, under = { layer: L.wood, col: [0.5, 0.46, 0.42], occ: 0.04 };
    const edge = { layer: L.plain, col: TRIM, occ: 0.85 };
    for (const s of [-1, 1]) {
      roofPlane(m, s * ex, ey, s * kneeX, kneeY + 0.04, -hl - g, hl + g, 0.1, top, under, edge);
      roofPlane(m, s * (kneeX + 0.12), kneeY - 0.02, 0, ridge + 0.06, -hl - g, hl + g, 0.1, top, under, edge);
    }

    // Trim: corners, the doorway, and a stone footing.
    for (const sx of [-1, 1]) for (const sz of [-1, 1]) m.box(sx * hw, wall / 2, sz * hl, 0.18, wall, 0.18, trim);
    m.box(-doorW - 0.1, doorH / 2, hl + 0.03, 0.2, doorH, 0.06, trim);
    m.box(doorW + 0.1, doorH / 2, hl + 0.03, 0.2, doorH, 0.06, trim);
    m.box(0, doorH + 0.1, hl + 0.03, doorW * 2 + 0.4, 0.2, 0.06, trim);
    for (const sx of [-1, 1]) m.box(sx * (hw + 0.04), 0.14, 0, 0.12, 0.28, hl * 2 + 0.1, { layer: L.brick, col: [0.6, 0.6, 0.6] });
    m.box(0, 0.14, -hl - 0.04, hw * 2 + 0.1, 0.28, 0.12, { layer: L.brick, col: [0.6, 0.6, 0.6] });

    // Sliding doors on a rail. The left leaf is shut; the right has been
    // rolled back just far enough to walk through.
    const leafShape = () => {
      const lw = doorW, lh = doorH;
      m.box(lw / 2, lh / 2, 0, lw, lh, 0.06, { layer: L.barn, col: [0.86, 0.84, 0.84] });
      const t = { layer: L.plain, col: TRIM };
      for (const y of [0.09, lh / 2, lh - 0.09]) m.box(lw / 2, y, 0.045, lw, 0.16, 0.03, t);
      for (const x of [0.08, lw - 0.08]) m.box(x, lh / 2, 0.045, 0.16, lh, 0.03, t);
      for (const y0 of [0, lh / 2]) {                       // an X brace in each half
        stick(m, [0.12, y0 + 0.14, 0.04], [lw - 0.12, y0 + lh / 2 - 0.12, 0.04], 0.025, 0.13, t);
        stick(m, [0.12, y0 + lh / 2 - 0.12, 0.04], [lw - 0.12, y0 + 0.14, 0.04], 0.025, 0.13, t);
      }
    };
    m.at(translate(-doorW, 0.06, hl + 0.11), leafShape);
    // The right-hand leaf is the one that moves: it starts where it was left,
    // rolled most of the way back, and can be slid shut or right open.
    const box = { x: 0, z: 0, hx: 0, hz: 0, yaw: 0 };
    w.boxes.push(box);
    w.doors.push({
      kind: 'slide', noun: 'barn door', site: SITE.barn, part: m.part(leafShape), box,
      shutX: 0, openX: doorW, start: ajar / doorW, y: 0.06, z: hl + 0.11, width: doorW, reach: 2.8,
    });
    m.box(0.65, doorH + 0.26, hl + 0.13, doorW * 2 + ajar + 0.4, 0.07, 0.07, { layer: L.plain, col: [0.12, 0.12, 0.13] });

    // Hayloft door and hoist beam in the gable.
    m.box(0, 5.5, hl + 0.03, 1.3, 1.6, 0.05, { layer: L.barn, col: [0.8, 0.8, 0.8] });
    for (const sx of [-1, 1]) m.box(sx * 0.7, 5.5, hl + 0.05, 0.14, 1.74, 0.05, trim);
    for (const y of [4.63, 6.37]) m.box(0, y, hl + 0.05, 1.54, 0.14, 0.05, trim);
    stick(m, [-0.6, 4.72, hl + 0.06], [0.6, 6.28, hl + 0.06], 0.025, 0.12, trim);
    stick(m, [-0.6, 6.28, hl + 0.06], [0.6, 4.72, hl + 0.06], 0.025, 0.12, trim);
    m.box(0, 7.55, hl + 0.55, 0.16, 0.16, 1.3, { layer: L.wood, col: DARK_WOOD });

    // Yard lamp on a gooseneck over the doors.
    stick(m, [0, 4.42, hl], [0, 4.42, hl + 0.72], 0.04, 0.04, { layer: L.plain, col: [0.1, 0.1, 0.1] });
    m.at(translate(0, 4.26, hl + 0.72), () => m.cyl(0.3, 0.07, 0.17, 10, { layer: L.plain, col: [0.12, 0.13, 0.12] }));
    m.box(0, 4.26, hl + 0.72, 0.1, 0.08, 0.1, { layer: L.plain, col: SODIUM, emit: 5 });

    // Inside: posts, tie beams, a loft over the back half, a ladder up to it.
    for (const sx of [-1, 1]) for (const z of [-3.5, 0, 3.5]) m.box(sx * 1.9, 2.0, z, 0.2, 4.0, 0.2, beam);
    for (const z of [-3.5, 0, 3.5]) m.box(0, 4.0, z, hw * 2 - 0.3, 0.2, 0.2, beam);
    m.slab([-hw + i, 3.0, -0.4], [hw - i, 3.0, -0.4], [hw - i, 3.0, -hl + i], [-hw + i, 3.0, -hl + i], 0.1, beam, beam, beam);
    for (let x = -3.6; x <= 3.7; x += 1.2) m.box(x, 2.8, -3.4, 0.1, 0.2, 6.0, beam);
    for (const sx of [-0.25, 0.25]) stick(m, [1.3 + sx, 0, 0.75], [1.3 + sx, 3.3, -0.35], 0.05, 0.08, beam);
    for (let k = 1; k < 11; k++) {
      const t = k / 11;
      stick(m, [1.05, 3.3 * t, 0.75 - 1.1 * t], [1.55, 3.3 * t, 0.75 - 1.1 * t], 0.04, 0.04, beam);
    }
    const bale = (x, y, z, yaw) => m.at(chain(translate(x, y, z), rotY(yaw)), () =>
      m.box(0, 0.23, 0, 0.95, 0.46, 0.5, { layer: L.hay, col: [0.9, 0.86, 0.8], occ: 0.05 }));
    for (const [x, y, z] of [[-3.6, 0, -5.6], [-2.6, 0, -5.7], [-3.5, 0, -5.0], [-3.1, 0.46, -5.5], [-3.6, 0.46, -5.0], [-3.3, 0.92, -5.4]]) bale(x, y, z, (rng() - 0.5) * 0.3);
    for (let k = 0; k < 9; k++) bale(-3.4 + (k % 3) * 1.05, 3.0 + ((k / 3) | 0) * 0.46, -5.4 + rng() * 0.6, (rng() - 0.5) * 0.4);
    for (const [x, z, s] of [[3.7, -5.5, 0.7], [3.6, -4.6, 0.55], [3.75, -5.45, 0.5]]) {
      m.box(x, s / 2 + (s < 0.52 ? 0.7 : 0), z, s, s, s, { layer: L.wood, col: [0.8, 0.74, 0.62], occ: 0.05 });
    }
    m.at(translate(3.6, 0, 2.6), () => m.cyl(0.3, 0.3, 0.9, 10, { layer: L.metal, col: [0.5, 0.6, 0.7], occ: 0.05 }));
    m.box(-3.9, 0.86, 2.4, 0.7, 0.06, 2.6, beam);                       // workbench
    for (const z of [1.2, 3.6]) for (const x of [-4.2, -3.6]) m.box(x, 0.43, z, 0.07, 0.86, 0.07, beam);

    // Outside, by the open door: barrels and a couple of crates.
    m.at(translate(3.6, 0, hl + 0.7), () => m.cyl(0.3, 0.3, 0.9, 10, { layer: L.metal, col: [0.9, 0.5, 0.36] }));
    m.at(translate(4.25, 0, hl + 0.55), () => m.cyl(0.3, 0.3, 0.9, 10, { layer: L.metal, col: [0.5, 0.56, 0.6] }));
    m.box(-3.6, 0.3, hl + 0.55, 0.6, 0.6, 0.6, { layer: L.wood, col: [0.9, 0.84, 0.72] });
    m.box(-2.9, 0.22, hl + 0.5, 0.45, 0.44, 0.45, { layer: L.wood, col: [0.8, 0.76, 0.66] });
  });

  w.lights.push({
    pos: xformPoint(M, [0, 4.2, hl + 0.72]), color: SODIUM.map((c) => c * 5.5), range: 17,
    dir: normalize(xformDir(M, [0, -1, 0.1])), cos: 0.36, flicker: true,
  });
  w.halos.push({ pos: xformPoint(M, [0, 4.24, hl + 0.72]), color: SODIUM, size: 2.4, flicker: true });

  const S = SITE.barn;
  const obb = (lx, lz, hx, hz) => {
    const [x, z] = siteToWorld(S, lx, lz);
    w.boxes.push({ x, z, hx, hz, yaw: S.yaw });
  };
  obb(-hw, 0, 0.14, hl + 0.1);
  obb(hw, 0, 0.14, hl + 0.1);
  castShadow(w, S, 0, 0, hw - 0.04, hl - 0.04, 0, wall);
  castShadow(w, S, 0, 0, kneeX - 0.1, hl - 0.04, wall, kneeY - 0.15);
  obb(0, -hl, hw, 0.14);
  obb((-hw - doorW) / 2, hl, (hw - doorW) / 2, 0.14);
  obb((hw + doorW) / 2, hl, (hw - doorW) / 2, 0.14);        // the sliding leaf brings its own
  obb(-doorW / 2, hl + 0.1, doorW / 2, 0.1);                // the shut leaf
  for (const sx of [-1, 1]) for (const z of [-3.5, 0, 3.5]) obb(sx * 1.9, z, 0.13, 0.13);
  obb(-3.2, -5.4, 1.0, 0.7);
  obb(3.65, -5.1, 0.45, 0.8);
  obb(-3.9, 2.4, 0.4, 1.35);
  obb(3.6, 2.6, 0.32, 0.32);
  obb(3.9, hl + 0.62, 0.65, 0.35);
  obb(-3.3, hl + 0.52, 0.65, 0.33);
}

/* ------------------------------------------------------------ fences --- */

function fence(m, w, pts, rng) {
  const wood = { layer: L.wood, col: [0.78, 0.74, 0.68] };
  for (let s = 0; s < pts.length - 1; s++) {
    const [ax, az] = pts[s], [bx, bz] = pts[s + 1];
    const len = Math.hypot(bx - ax, bz - az), n = Math.max(1, Math.round(len / 2.4));
    const yaw = Math.atan2(-(bz - az), bx - ax);
    let prev = null;
    for (let i = 0; i <= n; i++) {
      const t = i / n, x = ax + (bx - ax) * t, z = az + (bz - az) * t, y = groundHeight(x, z);
      m.at(chain(translate(x, y, z), rotY(yaw), rotZ((rng() - 0.5) * 0.07), rotX((rng() - 0.5) * 0.07)), () =>
        m.box(0, 0.62, 0, 0.11, 1.34, 0.11, wood));
      if (prev) {
        for (const h of [0.34, 0.72, 1.1]) {
          if (rng() < 0.035) continue;                      // a rail gone missing
          const sag = rng() < 0.07 ? -0.25 : 0;             // or hanging by one end
          stick(m, [prev.x, prev.y + h, prev.z], [x, y + h + sag, z], 0.035, 0.1, wood);
        }
      }
      if (rng() < 0.55) w.tufts.push([x + (rng() - 0.5) * 0.8, z + (rng() - 0.5) * 0.8, 0.7 + rng() * 0.5]);
      prev = { x, y, z };
    }
    w.boxes.push({ x: (ax + bx) / 2, z: (az + bz) / 2, hx: len / 2 + 0.06, hz: 0.12, yaw });
  }
}

function buildFences(m, w) {
  const rng = makeRng(123);
  const wood = { layer: L.wood, col: [0.78, 0.74, 0.68] };
  fence(m, w, [[5.8, 14], [30, 14], [30, -3.4]], rng);
  fence(m, w, [[30, -6.6], [30, -30], [-28, -30], [-28, 14], [2.2, 14]], rng);
  fence(m, w, [[30, -2], [54, -2], [54, -30], [30, -30]], rng);

  // The yard gate, left standing open.
  for (const x of [2.2, 5.8]) m.box(x, 0.85, 14, 0.16, 1.7, 0.16, wood);
  const hinge = { x: 2.2, z: 14, yaw: 1.5 };
  m.at(chain(translate(hinge.x, 0, hinge.z), rotY(hinge.yaw)), () => {
    for (const y of [0.3, 0.6, 0.9, 1.2]) m.box(1.75, y, 0, 3.4, 0.09, 0.04, wood);
    for (const x of [0.1, 1.75, 3.4]) m.box(x, 0.75, 0, 0.09, 1.0, 0.05, wood);
    stick(m, [0.1, 0.3, 0.03], [3.4, 1.2, 0.03], 0.03, 0.09, wood);
  });
  const [gx, gz] = siteToWorld(hinge, 1.75, 0);
  w.boxes.push({ x: gx, z: gz, hx: 1.75, hz: 0.1, yaw: hinge.yaw });
}

/* ------------------------------------------------------------- props --- */

function buildProps(m, w) {
  const wood = { layer: L.wood, col: [0.7, 0.66, 0.6] };

  // Mailbox at the end of the drive.
  m.box(6.7, 0.55, 19.2, 0.1, 1.1, 0.1, wood);
  m.box(6.7, 1.2, 19.2, 0.2, 0.22, 0.48, { layer: L.metal, col: [0.7, 0.72, 0.76] });
  m.box(6.82, 1.3, 19.3, 0.02, 0.16, 0.1, { layer: L.plain, col: [0.6, 0.1, 0.08] });
  w.boxes.push({ x: 6.7, z: 19.2, hx: 0.15, hz: 0.28, yaw: 0 });

  // Utility poles along the road, lines sagging between them, and a service
  // drop to the house. Power lines against the sky are half of what makes a
  // rural night scene read as inhabited.
  const poles = [-150, -98, -46, 9.5, 62, 114, 166];
  const wire = { layer: L.plain, col: [0.03, 0.03, 0.035] };
  const top = (x) => groundHeight(x, 25.6) + 8.2;
  for (const x of poles) {
    const y = groundHeight(x, 25.6);
    m.at(translate(x, y - 0.3, 25.6), () => m.cyl(0.15, 0.11, 9.0, 7, { layer: L.bark, col: [0.7, 0.66, 0.6] }));
    m.box(x, y + 8.2, 25.6, 0.12, 0.12, 2.0, { layer: L.wood, col: DARK_WOOD });
    w.trunks.push([x, 25.6, 0.2]);
  }
  for (let i = 0; i < poles.length - 1; i++) {
    for (const dz of [-0.85, 0, 0.85]) {
      const n = 10;
      let prev = [poles[i], top(poles[i]) + 0.08, 25.6 + dz];
      for (let k = 1; k <= n; k++) {
        const t = k / n;
        const p = [poles[i] + (poles[i + 1] - poles[i]) * t,
          top(poles[i]) + (top(poles[i + 1]) - top(poles[i])) * t + 0.08 - Math.sin(t * Math.PI) * 1.1, 25.6 + dz];
        stick(m, prev, p, 0.035, 0.035, wire);
        prev = p;
      }
    }
  }
  const MH = siteMatrix(SITE.house);
  const eave = xformPoint(MH, [H.hw + 0.2, 5.7, H.hd + 0.3]);
  const from = [9.5, top(9.5) - 0.5, 25.6];
  let prev = from;
  for (let k = 1; k <= 12; k++) {
    const t = k / 12;
    const p = from.map((v, a) => v + (eave[a] - v) * t);
    p[1] -= Math.sin(t * Math.PI) * 1.3;
    stick(m, prev, p, 0.035, 0.035, wire);
    prev = p;
  }

  // An old pickup pulled up off the drive (see truck.js).
  const T = SITE.truck;
  buildTruck(m, siteMatrix(T));
  w.boxes.push({ x: T.x, z: T.z, hx: 1.03, hz: 2.74, yaw: T.yaw });
  w.things.push({ pos: xformPoint(siteMatrix(T), [-1.0, 1.15, -0.25]), reach: 1.9, locked: true, noun: 'truck', say: 'It\'s locked.' });
  for (const b of TRUCK_BOXES) castShadow(w, T, ...b);

  // Paddock: round bales and a water trough.
  for (const [x, z, a] of [[39, -10, 0.3], [43.5, -12.5, 1.2], [47, -23, 2.2]]) {
    m.at(chain(translate(x, groundHeight(x, z) + 0.78, z), rotY(a), translate(0.65, 0, 0), rotZ(Math.PI / 2)), () =>
      m.cyl(0.8, 0.8, 1.3, 14, { layer: L.hay, capBottom: true }));
    w.trunks.push([x, z, 0.95]);
  }
  const tg = { layer: L.metal, col: [0.7, 0.72, 0.74] };
  m.at(translate(37, groundHeight(37, -3.1), -3.1), () => {
    m.box(0, 0.08, 0, 2.2, 0.06, 0.7, tg);
    for (const s of [-1, 1]) m.box(0, 0.33, s * 0.33, 2.2, 0.5, 0.04, tg);
    for (const s of [-1, 1]) m.box(s * 1.08, 0.33, 0, 0.04, 0.5, 0.7, tg);
    m.quad([-1.06, 0.46, 0.31], [1.06, 0.46, 0.31], [1.06, 0.46, -0.31], [-1.06, 0.46, -0.31], { layer: L.windowDark, tile: 2 });
  });
  w.boxes.push({ x: 37, z: -3.1, hx: 1.15, hz: 0.4, yaw: 0 });

  // Washing left out on a line behind the house.
  const post = (x, z) => { m.box(x, 1.0, z, 0.08, 2.0, 0.08, wood); m.box(x, 1.95, z, 1.1, 0.07, 0.07, wood); w.trunks.push([x, z, 0.1]); };
  post(-19, -15); post(-19, -24);
  for (const dx of [-0.45, 0.45]) stick(m, [-19 + dx, 1.96, -15], [-19 + dx, 1.96, -24], 0.02, 0.02, wire);
  for (const [dx, z, wd, hg] of [[-0.45, -17.5, 1.6, 1.3], [0.45, -20.5, 1.2, 0.9], [-0.45, -21.6, 0.9, 1.1]]) {
    m.quad([-19 + dx, 1.95 - hg, z + wd / 2], [-19 + dx, 1.95 - hg, z - wd / 2], [-19 + dx, 1.95, z - wd / 2], [-19 + dx, 1.95, z + wd / 2],
      { layer: L.plain, col: [0.78, 0.78, 0.8], sway: [0.5, 0.5, 0, 0] });
  }
}

/* ------------------------------------------------------------ forest --- */

function buildForest(m, w) {
  const rng = makeRng(2024);
  const nearTrack = (x, z) => Math.abs(z - 22) < 4.6 || (Math.abs(z - 25.6) < 1.2);
  // The clearing's edge is ragged; keep it from wandering inside the fences.
  const fenced = (x, z) => z > -33 && z < 17 && x > -31 && x < (z < 1 ? 57 : 33);
  const card = (x, y, z, wd, h, layer, col, sway, yaw0) => {
    for (let k = 0; k < 3; k++) {
      // Each card is mirrored at random, so three crossed cards of one
      // painting give eight different outlines.
      const fit = rng() < 0.5 ? [0, 0, 1, 1] : [1, 0, 0, 1];
      m.at(chain(translate(x, y, z), rotY(yaw0 + k * Math.PI / 3)), () =>
        m.quad([-wd / 2, 0, 0], [wd / 2, 0, 0], [wd / 2, h, 0], [-wd / 2, h, 0],
          { layer, fit, col, kind: KIND.FOLIAGE, sway: [0, 0, sway, sway], normal: [0, 1, 0] }));
    }
  };

  const cell = 3.3, R = 150;
  let count = 0;
  for (let gx = -R; gx < R; gx += cell) for (let gz = -R; gz < R; gz += cell) {
    const x = gx + rng() * cell, z = gz + rng() * cell;
    const e = clearingEdge(x, z);
    const keep = rng();
    if (e < 1 || nearTrack(x, z) || fenced(x, z) || Math.hypot(x, z) > R) continue;
    // A solid wall at the clearing's edge, thinning with depth: the fog hides
    // the back of the forest long before the trees run out.
    if (keep > (e < 1.5 ? 0.9 : e < 2.6 ? 0.55 : 0.3)) continue;
    // Stands and gaps rather than an even plantation: behind the front rank
    // the forest thins wherever a slow noise says so, and heights follow a
    // long tail so a few old trees stand well clear of the rest.
    const stand = vnoise(x / 11 + 31, z / 11 + 17);
    if (e > 1.2 && stand < 0.3) continue;
    const y = groundHeight(x, z) - 0.3;
    const h = (8.5 + 18 * Math.pow(rng(), 1.9)) * (0.75 + stand * 0.5), shade = 0.45 + rng() * 0.55;
    const pine = rng() < 0.3;
    card(x, y, z, h * (pine ? 0.42 : 0.4) * (0.75 + rng() * 0.6), h, pine ? L.pine : L.spruce,
      [shade * 0.9, shade, shade * 0.95], h / 26, rng() * 3);
    if (e < 1.9) {
      const r = 0.16 + h * 0.011;
      m.at(translate(x, y, z), () => m.cyl(r * 1.3, r * 0.6, h * 0.6, 6, { layer: L.bark, occ: 0.6 }, false));
      w.trunks.push([x, z, r + 0.12]);
      if (rng() < 0.5) w.tufts.push([x + (rng() - 0.5) * 3, z + (rng() - 0.5) * 3, 0.9 + rng() * 0.9]);
    }
    count++;
  }
  w.treeCount = count;

  // Rough grass: along the fences (queued by the fence builder), round the
  // buildings, and scattered through the clearing wherever nothing is mown.
  const tr = makeRng(77);
  const clear = (x, z) => {
    for (const s of [SITE.house, SITE.barn]) {
      const [lx, lz] = worldToSite(s, x, z);
      if (Math.abs(lx) < 5.2 && lz > -7.2 && lz < 7.2) return false;
    }
    for (const [x1, z1, x2, z2, wd] of PATHS) {
      const dx = x2 - x1, dz = z2 - z1;
      const t = Math.max(0, Math.min(1, ((x - x1) * dx + (z - z1) * dz) / (dx * dx + dz * dz)));
      if (Math.hypot(x - x1 - dx * t, z - z1 - dz * t) < wd / 2 + 0.5) return false;
    }
    return true;
  };
  for (let i = 0; i < 1500; i++) {
    const x = -60 + tr() * 140, z = -52 + tr() * 90;
    if (clearingEdge(x, z) > 1.15) continue;
    // Thick out in the meadow and the paddock, sparse on the kept yard.
    const yard = x > -28 && x < 30 && z > -30 && z < 14;
    if (yard && tr() < 0.8) continue;
    w.tufts.push([x, z, 0.5 + tr() * 0.7]);
  }
  for (const [x, z, s] of w.tufts) {
    if (!clear(x, z)) continue;
    const t = 0.45 + tr() * 0.55, dry = tr() < 0.3 ? 0.25 : 0;
    const yaw = tr() * 3, y = groundHeight(x, z) - 0.04;
    for (let k = 0; k < 2; k++) {
      m.at(chain(translate(x, y, z), rotY(yaw + k * 1.6)), () =>
        m.quad([-s * 0.6, 0, 0], [s * 0.6, 0, 0], [s * 0.6, s, 0], [-s * 0.6, s, 0], {
          layer: L.tuft, fit: true, col: [t + dry, t, t * 0.9], kind: KIND.FOLIAGE,
          sway: [0, 0, 0.3, 0.3], normal: [0, 1, 0],
        }));
    }
  }
}

function buildTerrain(m) {
  const step = 4, R = 176, t = 1 / TILES[L.grass];
  const normal = (x, z) => normalize([groundHeight(x - 1, z) - groundHeight(x + 1, z), 2, groundHeight(x, z - 1) - groundHeight(x, z + 1)]);
  const o = { layer: L.grass, kind: KIND.GROUND };
  for (let x = -R; x < R; x += step) for (let z = -R; z < R; z += step) {
    const c = [[x, z + step], [x + step, z + step], [x + step, z], [x, z]];
    for (const k of [0, 1, 2, 0, 2, 3]) {
      const [px, pz] = c[k];
      m._vert([px, groundHeight(px, pz), pz], normal(px, pz), px * t, -pz * t, o, 0);
    }
  }
}

/* -------------------------------------------------------------- floor --- */

/** Height of whatever the player is standing on: ground, porch deck or steps. */
export function floorHeight(x, z) {
  const [lx, lz] = worldToSite(SITE.house, x, z);
  const { hw, hd, porch, found, lean } = H;
  if (Math.abs(lx) < hw && lz > -hd && lz <= hd + porch) return found;          // the rooms and the porch
  if (Math.abs(lx - lean.x) < lean.w / 2 && lz > -hd - lean.d && lz <= -hd) return found;   // the kitchen
  if (Math.abs(lx - 2.3) < 0.75 && lz > -hd - 0.9 && lz <= -hd) return found;               // the back step
  if (Math.abs(lx - 2.3) < 0.6 && lz > -hd - 1.2 && lz <= -hd - 0.9) return found / 2;
  if (Math.abs(lx) < 0.95 && lz > hd + porch && lz < hd + porch + 0.6) return found * (1 - (lz - hd - porch) / 0.6);
  return groundHeight(x, z);
}

/** What is underfoot, for footstep sounds. */
export function surfaceAt(x, z) {
  const [lx, lz] = worldToSite(SITE.house, x, z);
  if (Math.abs(lx) < H.hw && lz > -H.hd && lz < H.hd + H.porch + 0.6) return 'wood';
  if (insideHouse(x, z)) return 'wood';
  const [bx, bz] = worldToSite(SITE.barn, x, z);
  if (Math.abs(bx) < B.hw && Math.abs(bz) < B.hl) return 'dirt';
  for (const [x1, z1, x2, z2, wd] of PATHS) {
    const dx = x2 - x1, dz = z2 - z1;
    const t = Math.max(0, Math.min(1, ((x - x1) * dx + (z - z1) * dz) / (dx * dx + dz * dz)));
    if (Math.hypot(x - x1 - dx * t, z - z1 - dz * t) < wd / 2) return 'dirt';
  }
  return 'grass';
}

/** True inside the barn, where the sky and the wind should both drop away. */
export function insideBarn(x, z) {
  const [bx, bz] = worldToSite(SITE.barn, x, z);
  return Math.abs(bx) < B.hw && Math.abs(bz) < B.hl;
}

/** True in any room of the farmhouse, kitchen included. */
export function insideHouse(x, z) {
  const [lx, lz] = worldToSite(SITE.house, x, z);
  const { hw, hd, lean } = H;
  return (Math.abs(lx) < hw && Math.abs(lz) < hd) || (Math.abs(lx - lean.x) < lean.w / 2 && lz > -hd - lean.d && lz <= -hd);
}

/** How far the player may wander: a little way into the trees, and along the road. */
export function inBounds(x, z) {
  return clearingEdge(x, z) < 1.75 || (Math.abs(z - 22) < 5 && Math.abs(x) < 120);
}

export function build() {
  const room = () => ({ on: true, lights: [], parts: [] });
  const w = {
    lights: [], halos: [], boxes: [], trunks: [], tufts: [], occluders: [], treeCount: 0,
    doors: [], things: [],                                   // what can be used
    groups: { hall: room(), dining: room(), kitchen: room(), living: room(), tv: room() },   // what a switch works
  };
  const m = new Mesh(TILES);
  buildTerrain(m);
  buildHouse(m, w);
  buildBarn(m, w);
  buildFences(m, w);
  buildProps(m, w);
  buildForest(m, w);
  return {
    vertices: m.finish(), vertexCount: m.count, fixedCount: m.fixed, parts: m.parts,
    doors: w.doors, things: w.things, groups: w.groups,
    lights: w.lights, halos: w.halos, boxes: w.boxes, trunks: w.trunks, occluders: w.occluders, treeCount: w.treeCount,
    house: w.house,
  };
}
