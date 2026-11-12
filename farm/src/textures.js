/**
 * Every surface in the farm, painted at load time.
 *
 * The look being chased uses photographs for its textures: soft, a little
 * muddy, and recognisably real materials rather than pixel art. There are no
 * photographs here -- the repository ships no binary art for this scene -- so
 * each material is built the way a photo of it reads at night: a base colour,
 * broad low-frequency staining, the material's own structure (board lines,
 * shingle courses, mortar), then fine grain. They are filtered smoothly, never
 * nearest-neighbour: the softness is the point.
 *
 * All layers are 512 x 512 and tile, and all go into one texture array so the
 * whole scene draws in a single call.
 */
import { makeRng } from '../../src/core/rng.js';

export const SIZE = 512;
const S = SIZE;

/** Layer order is the array order; `tile` is metres per repeat. */
export const LAYERS = [
  { name: 'siding', tile: 1.2 },
  { name: 'barn', tile: 1.8 },
  { name: 'shingle', tile: 2.4 },
  { name: 'wood', tile: 0.6 },
  { name: 'brick', tile: 1.6 },
  { name: 'grass', tile: 3.0 },
  { name: 'dirt', tile: 2.5 },
  { name: 'bark', tile: 1.0 },
  { name: 'spruce', tile: 1 },
  { name: 'pine', tile: 1 },
  { name: 'tuft', tile: 1 },
  { name: 'windowLit', tile: 1 },
  { name: 'windowDark', tile: 1 },
  { name: 'door', tile: 1 },
  { name: 'metal', tile: 1.6 },
  { name: 'hay', tile: 1.2 },
  { name: 'plain', tile: 1.0 },
  { name: 'paint', tile: 1.4 },
  { name: 'glass', tile: 1 },
  { name: 'tire', tile: 0.26 },
  { name: 'grille', tile: 1 },
  { name: 'plate', tile: 1 },
  { name: 'wallpaper', tile: 1.0 },
  { name: 'plaster', tile: 2.0 },
  { name: 'lino', tile: 0.6 },
  { name: 'fabric', tile: 0.5 },
  { name: 'rug', tile: 1 },
  { name: 'grain', tile: 0.8 },
  { name: 'static', tile: 1 },
  { name: 'picture', tile: 1 },
  { name: 'clockface', tile: 1 },
  { name: 'tile', tile: 0.6 },
  { name: 'print', tile: 1 },
];
export const L = Object.fromEntries(LAYERS.map((l, i) => [l.name, i]));
export const TILES = LAYERS.map((l) => l.tile);

function surface() {
  const c = typeof OffscreenCanvas !== 'undefined'
    ? new OffscreenCanvas(S, S)
    : Object.assign(document.createElement('canvas'), { width: S, height: S });
  return c.getContext('2d', { willReadFrequently: true });
}

/** Tileable fractal value noise in 0..1. `base` is the coarsest lattice period. */
function fbm(rng, base = 4, octaves = 5) {
  const out = new Float32Array(S * S);
  let amp = 1, total = 0;
  for (let o = 0; o < octaves; o++) {
    const P = base << o;
    const lat = new Float32Array(P * P);
    for (let i = 0; i < lat.length; i++) lat[i] = rng();
    const cell = S / P;
    for (let y = 0; y < S; y++) {
      const fy = y / cell, y0 = Math.floor(fy), ty = fy - y0;
      const sy = ty * ty * (3 - 2 * ty);
      const r0 = (y0 % P) * P, r1 = ((y0 + 1) % P) * P;
      for (let x = 0; x < S; x++) {
        const fx = x / cell, x0 = Math.floor(fx), tx = fx - x0;
        const sx = tx * tx * (3 - 2 * tx);
        const c0 = x0 % P, c1 = (x0 + 1) % P;
        const a = lat[r0 + c0] + (lat[r0 + c1] - lat[r0 + c0]) * sx;
        const b = lat[r1 + c0] + (lat[r1 + c1] - lat[r1 + c0]) * sx;
        out[y * S + x] += (a + (b - a) * sy) * amp;
      }
    }
    total += amp;
    amp *= 0.5;
  }
  for (let i = 0; i < out.length; i++) out[i] /= total;
  return out;
}

/** Rewrite every pixel: fn(r, g, b, a, index, x, y) -> [r, g, b, a]. */
function grade(ctx, fn) {
  const img = ctx.getImageData(0, 0, S, S);
  const d = img.data;
  for (let i = 0, p = 0; i < d.length; i += 4, p++) {
    const o = fn(d[i], d[i + 1], d[i + 2], d[i + 3], p, p % S, (p / S) | 0);
    d[i] = o[0]; d[i + 1] = o[1]; d[i + 2] = o[2]; d[i + 3] = o[3] === undefined ? d[i + 3] : o[3];
  }
  ctx.putImageData(img, 0, 0);
}

/** Draw something nine times so it wraps cleanly across the tile edges. */
function wrapped(ctx, fn) {
  for (const dx of [-S, 0, S]) for (const dy of [-S, 0, S]) {
    ctx.save(); ctx.translate(dx, dy); fn(); ctx.restore();
  }
}
const rgb = (r, g, b, a = 1) => `rgba(${r | 0},${g | 0},${b | 0},${a})`;

export function paintLayers(seed = 7) {
  const rng = makeRng(seed);
  const R = (a, b) => a + (b - a) * rng();
  const stain = fbm(rng, 3, 5);   // broad weathering
  const fine = fbm(rng, 32, 3);   // surface grain
  const blot = fbm(rng, 6, 4);    // rust, moss, peeling

  /** Shared finishing pass: low-frequency staining plus grain. */
  const weather = (ctx, stainAmt, grainAmt, tint = [1, 1, 1]) => grade(ctx, (r, g, b, a, p) => {
    const k = (1 - stainAmt) + stainAmt * 2 * stain[p];
    const n = 1 + (fine[p] - 0.5) * grainAmt;
    return [r * k * n * tint[0], g * k * n * tint[1], b * k * n * tint[2]];
  });

  const painters = {
    // White clapboard: eight overlapping boards, each casting a line of shade
    // on the one below, with paint peeled back to grey wood in patches.
    siding(ctx) {
      const h = S / 8;
      for (let i = 0; i < 8; i++) {
        const v = R(0.9, 1.0);
        ctx.fillStyle = rgb(206 * v, 201 * v, 188 * v);
        ctx.fillRect(0, i * h, S, h);
        const g = ctx.createLinearGradient(0, i * h, 0, (i + 1) * h);
        g.addColorStop(0, 'rgba(0,0,0,0.55)');
        g.addColorStop(0.11, 'rgba(0,0,0,0.12)');
        g.addColorStop(0.2, 'rgba(0,0,0,0)');
        g.addColorStop(0.93, 'rgba(255,255,255,0.05)');
        g.addColorStop(1, 'rgba(255,255,255,0.14)');
        ctx.fillStyle = g;
        ctx.fillRect(0, i * h, S, h);
        for (let j = 0; j < 2; j++) {           // butt joints between board lengths
          ctx.fillStyle = 'rgba(30,26,22,0.5)';
          ctx.fillRect((R(0, S)) | 0, i * h, 2, h);
        }
      }
      wrapped(ctx, () => {                      // rain streaks
        for (let i = 0; i < 70; i++) {
          const x = R(0, S), y = R(0, S), len = R(30, 150);
          const g = ctx.createLinearGradient(0, y, 0, y + len);
          g.addColorStop(0, 'rgba(40,36,28,0.16)');
          g.addColorStop(1, 'rgba(40,36,28,0)');
          ctx.fillStyle = g;
          ctx.fillRect(x, y, R(2, 7), len);
        }
      });
      grade(ctx, (r, g, b, a, p) => {
        // Paint flaking back to grey wood: small, sparse, and only where the
        // fine grain says so, or it reads as camouflage rather than age.
        const peel = Math.max(0, Math.min(1, (blot[p] * 0.55 + fine[p] * 0.45 - 0.66) * 14)) * 0.5;
        return [r + (120 - r) * peel, g + (112 - g) * peel, b + (100 - b) * peel];
      });
      weather(ctx, 0.3, 0.16);
    },

    // Barn boards: vertical, oxide red gone brown, black gaps between them.
    barn(ctx) {
      const w = S / 8;
      for (let i = 0; i < 8; i++) {
        const v = R(0.72, 1.05);
        ctx.fillStyle = rgb(118 * v, 44 * v, 34 * v);
        ctx.fillRect(i * w, 0, w, S);
        ctx.fillStyle = 'rgba(8,5,4,0.9)';
        ctx.fillRect(i * w, 0, 3, S);
        ctx.fillStyle = 'rgba(255,220,200,0.07)';
        ctx.fillRect(i * w + 3, 0, 2, S);
        for (let k = 0; k < 26; k++) {          // grain
          ctx.fillStyle = rgb(20, 10, 8, R(0.05, 0.2));
          ctx.fillRect(i * w + R(4, w - 2), 0, 1, S);
        }
        for (const y of [40, 296]) {            // nail rows
          ctx.fillStyle = 'rgba(15,12,12,0.8)';
          ctx.fillRect(i * w + w * 0.3, y, 3, 3);
          ctx.fillRect(i * w + w * 0.7, y, 3, 3);
        }
      }
      grade(ctx, (r, g, b, a, p) => {
        const grey = Math.max(0, blot[p] - 0.45) * 1.5;   // paint worn to bare wood
        const m = (r + g + b) / 3 * 1.25;
        return [r + (m - r) * grey, g + (m * 0.95 - g) * grey, b + (m * 0.88 - b) * grey];
      });
      weather(ctx, 0.3, 0.25);
    },

    // Asphalt shingles: sixteen courses, tabs staggered, a shadow under each.
    shingle(ctx) {
      const h = S / 16, w = S / 8;
      for (let row = 0; row < 16; row++) {
        const off = (row % 2) * (w / 2);
        for (let i = -1; i < 9; i++) {
          const v = R(0.75, 1.1);
          ctx.fillStyle = rgb(62 * v, 60 * v, 62 * v);
          ctx.fillRect(i * w + off, S - (row + 1) * h, w - 2, h);
        }
        const y = S - row * h;
        const g = ctx.createLinearGradient(0, y - 7, 0, y);
        g.addColorStop(0, 'rgba(0,0,0,0)');
        g.addColorStop(1, 'rgba(0,0,0,0.6)');
        ctx.fillStyle = g;
        ctx.fillRect(0, y - 7, S, 7);
      }
      grade(ctx, (r, g, b, a, p) => {
        const moss = Math.max(0, blot[p] - 0.6) * 2.2;
        return [r + (48 - r) * moss, g + (62 - g) * moss, b + (38 - b) * moss];
      });
      weather(ctx, 0.25, 0.4);
    },

    // Bare weathered lumber: four planks, long grain, the odd knot.
    wood(ctx) {
      const h = S / 4;
      for (let i = 0; i < 4; i++) {
        const v = R(0.82, 1.05);
        ctx.fillStyle = rgb(124 * v, 110 * v, 92 * v);
        ctx.fillRect(0, i * h, S, h);
        for (let k = 0; k < 46; k++) {
          ctx.fillStyle = rgb(40, 32, 24, R(0.06, 0.26));
          ctx.fillRect(0, i * h + R(3, h - 2), S, R(1, 2.5));
        }
        ctx.fillStyle = 'rgba(10,8,6,0.85)';
        ctx.fillRect(0, i * h, S, 3);
        const kx = R(40, S - 40), ky = i * h + R(30, h - 30);
        ctx.fillStyle = 'rgba(48,36,26,0.7)';
        ctx.beginPath(); ctx.ellipse(kx, ky, R(8, 15), R(4, 7), 0, 0, 7); ctx.fill();
      }
      weather(ctx, 0.28, 0.3);
    },

    brick(ctx) {
      ctx.fillStyle = rgb(128, 122, 112);       // mortar
      ctx.fillRect(0, 0, S, S);
      const bh = S / 16, bw = S / 8;
      for (let row = 0; row < 16; row++) {
        const off = (row % 2) * (bw / 2);
        for (let i = -1; i < 9; i++) {
          const v = R(0.7, 1.08), hue = R(0, 1);
          ctx.fillStyle = rgb((118 + hue * 26) * v, (58 + hue * 10) * v, 46 * v);
          ctx.fillRect(i * bw + off + 2, row * bh + 2, bw - 5, bh - 5);
        }
      }
      weather(ctx, 0.3, 0.45);
    },

    // Grass from standing height: a dark mat with thousands of blade strokes.
    grass(ctx) {
      ctx.fillStyle = rgb(46, 58, 30);
      ctx.fillRect(0, 0, S, S);
      wrapped(ctx, () => {
        const r2 = makeRng(seed + 11);
        for (let i = 0; i < 5200; i++) {
          const x = r2() * S, y = r2() * S, a = (r2() - 0.5) * 2.2, len = 5 + r2() * 13;
          const t = r2();
          ctx.strokeStyle = rgb(38 + t * 62, 54 + t * 60, 24 + t * 26, 0.75);
          ctx.lineWidth = 1 + r2() * 1.4;
          ctx.beginPath(); ctx.moveTo(x, y); ctx.lineTo(x + Math.sin(a) * len, y - Math.cos(a) * len); ctx.stroke();
        }
      });
      weather(ctx, 0.42, 0.2);
    },

    dirt(ctx) {
      ctx.fillStyle = rgb(104, 84, 62);
      ctx.fillRect(0, 0, S, S);
      wrapped(ctx, () => {
        const r2 = makeRng(seed + 23);
        for (let i = 0; i < 420; i++) {
          const t = r2();
          ctx.fillStyle = rgb(70 + t * 80, 60 + t * 70, 48 + t * 60, 0.75);
          ctx.beginPath();
          ctx.ellipse(r2() * S, r2() * S, 1.5 + r2() * 4.5, 1.2 + r2() * 3, r2() * 3, 0, 7);
          ctx.fill();
        }
      });
      weather(ctx, 0.36, 0.5);
    },

    bark(ctx) {
      ctx.fillStyle = rgb(58, 46, 36);
      ctx.fillRect(0, 0, S, S);
      wrapped(ctx, () => {
        const r2 = makeRng(seed + 31);
        for (let i = 0; i < 380; i++) {
          const x = r2() * S, y = r2() * S, len = 30 + r2() * 110, t = r2();
          ctx.strokeStyle = rgb(22 + t * 66, 16 + t * 54, 12 + t * 42, 0.8);
          ctx.lineWidth = 2 + r2() * 5;
          ctx.beginPath(); ctx.moveTo(x, y);
          ctx.quadraticCurveTo(x + (r2() - 0.5) * 16, y + len / 2, x + (r2() - 0.5) * 10, y + len);
          ctx.stroke();
        }
      });
      weather(ctx, 0.2, 0.4);
    },

    // Conifers are flat cards, as they are in the games this imitates: the
    // silhouette against a lighter sky does all the work, so the painting is
    // about a ragged outline and nothing else.
    spruce(ctx) { conifer(ctx, makeRng(seed + 41), 0.86, 0.03, 0.43); },
    pine(ctx) { conifer(ctx, makeRng(seed + 43), 0.5, 0.04, 0.34); },

    tuft(ctx) {
      const r2 = makeRng(seed + 47);
      for (let i = 0; i < 64; i++) {
        const x0 = S * (0.24 + r2() * 0.52), h = S * (0.35 + r2() * 0.6), lean = (r2() - 0.5) * S * 0.5;
        const t = r2();
        ctx.strokeStyle = rgb(52 + t * 84, 66 + t * 70, 30 + t * 30);
        ctx.lineWidth = 3 + r2() * 5;
        ctx.lineCap = 'round';
        ctx.beginPath(); ctx.moveTo(x0, S);
        ctx.quadraticCurveTo(x0 + lean * 0.15, S - h * 0.6, x0 + lean, S - h);
        ctx.stroke();
      }
      keyAlpha(ctx, [60, 74, 36]);
    },

    // A lit, curtained window: the only "interior" the house has.
    windowLit(ctx) {
      const g = ctx.createRadialGradient(S * 0.5, S * 0.45, 20, S * 0.5, S * 0.5, S * 0.75);
      g.addColorStop(0, rgb(255, 214, 150));
      g.addColorStop(1, rgb(196, 118, 52));
      ctx.fillStyle = g; ctx.fillRect(0, 0, S, S);
      ctx.fillStyle = rgb(120, 84, 50, 0.55);   // far wall, a picture, a lampshade
      ctx.fillRect(S * 0.36, S * 0.2, S * 0.28, S * 0.22);
      ctx.fillStyle = rgb(255, 236, 190);
      ctx.beginPath(); ctx.moveTo(S * 0.44, S * 0.62); ctx.lineTo(S * 0.56, S * 0.62);
      ctx.lineTo(S * 0.6, S * 0.76); ctx.lineTo(S * 0.4, S * 0.76); ctx.fill();
      for (const side of [0, 1]) {              // curtains, in folds
        for (let i = 0; i < 9; i++) {
          const w = S * 0.36 / 9, x = side ? S - (i + 1) * w : i * w;
          ctx.fillStyle = i % 2 ? rgb(150, 82, 40, 0.86) : rgb(196, 118, 60, 0.8);
          ctx.fillRect(x, 0, w + 1, S);
        }
      }
      ctx.fillStyle = 'rgba(60,30,10,0.35)';
      ctx.fillRect(0, 0, S, S * 0.06);
      weather(ctx, 0.12, 0.1);
    },

    windowDark(ctx) {
      const g = ctx.createLinearGradient(0, 0, S, S);
      g.addColorStop(0, rgb(16, 22, 34));
      g.addColorStop(0.5, rgb(7, 10, 16));
      g.addColorStop(1, rgb(12, 17, 27));
      ctx.fillStyle = g; ctx.fillRect(0, 0, S, S);
      for (const side of [0, 1]) {
        for (let i = 0; i < 7; i++) {
          const w = S * 0.3 / 7, x = side ? S - (i + 1) * w : i * w;
          ctx.fillStyle = i % 2 ? 'rgba(60,66,76,0.22)' : 'rgba(34,38,46,0.2)';
          ctx.fillRect(x, 0, w + 1, S);
        }
      }
      ctx.fillStyle = 'rgba(120,140,170,0.06)'; // a slant of sky in the glass
      ctx.beginPath(); ctx.moveTo(S * 0.15, 0); ctx.lineTo(S * 0.5, 0); ctx.lineTo(S * 0.2, S); ctx.lineTo(0, S); ctx.fill();
    },

    door(ctx) {
      ctx.fillStyle = rgb(186, 180, 162); ctx.fillRect(0, 0, S, S);
      const panel = (x, y, w, h, glass) => {
        ctx.fillStyle = glass ? rgb(12, 16, 24) : rgb(170, 164, 146);
        ctx.fillRect(x, y, w, h);
        ctx.strokeStyle = 'rgba(30,26,20,0.75)'; ctx.lineWidth = 6;
        ctx.beginPath(); ctx.moveTo(x, y + h); ctx.lineTo(x, y); ctx.lineTo(x + w, y); ctx.stroke();
        ctx.strokeStyle = 'rgba(255,250,235,0.5)';
        ctx.beginPath(); ctx.moveTo(x + w, y); ctx.lineTo(x + w, y + h); ctx.lineTo(x, y + h); ctx.stroke();
      };
      panel(S * 0.14, S * 0.06, S * 0.31, S * 0.2, true);
      panel(S * 0.55, S * 0.06, S * 0.31, S * 0.2, true);
      panel(S * 0.14, S * 0.33, S * 0.31, S * 0.27);
      panel(S * 0.55, S * 0.33, S * 0.31, S * 0.27);
      panel(S * 0.14, S * 0.67, S * 0.31, S * 0.27);
      panel(S * 0.55, S * 0.67, S * 0.31, S * 0.27);
      ctx.fillStyle = rgb(150, 120, 60);
      ctx.beginPath(); ctx.arc(S * 0.9, S * 0.55, S * 0.03, 0, 7); ctx.fill();
      weather(ctx, 0.25, 0.2);
    },

    // Corrugated roofing with rust coming through.
    metal(ctx) {
      const img = ctx.createImageData(S, S);
      for (let p = 0; p < S * S; p++) {
        const x = p % S;
        const rib = 0.62 + 0.38 * Math.sin((x / 32) * Math.PI * 2);
        const rust = Math.min(1, Math.max(0, blot[p] - 0.5) * 4);
        const v = rib * (0.75 + 0.5 * stain[p]);
        img.data[p * 4] = (112 + (132 - 112) * rust) * v;
        img.data[p * 4 + 1] = (116 + (72 - 116) * rust) * v;
        img.data[p * 4 + 2] = (120 + (44 - 120) * rust) * v;
        img.data[p * 4 + 3] = 255;
      }
      ctx.putImageData(img, 0, 0);
      weather(ctx, 0, 0.3);
    },

    hay(ctx) {
      ctx.fillStyle = rgb(150, 124, 62); ctx.fillRect(0, 0, S, S);
      wrapped(ctx, () => {
        const r2 = makeRng(seed + 53);
        for (let i = 0; i < 2600; i++) {
          const x = r2() * S, y = r2() * S, a = (r2() - 0.5) * 1.2, len = 14 + r2() * 46, t = r2();
          ctx.strokeStyle = rgb(110 + t * 110, 88 + t * 96, 38 + t * 60, 0.8);
          ctx.lineWidth = 1 + r2() * 1.6;
          ctx.beginPath(); ctx.moveTo(x, y); ctx.lineTo(x + Math.cos(a) * len, y + Math.sin(a) * len); ctx.stroke();
        }
      });
      weather(ctx, 0.3, 0.2);
    },

    plain(ctx) {
      ctx.fillStyle = '#fff'; ctx.fillRect(0, 0, S, S);
      weather(ctx, 0.12, 0.16);
    },

    // Forty-year-old enamel: chalked by the sun, scratched, and rusting
    // through wherever water sits. The rust has a dark core and a bleeding
    // orange edge, which is what separates it from brown paint.
    paint(ctx) {
      ctx.fillStyle = rgb(94, 116, 116); ctx.fillRect(0, 0, S, S);
      wrapped(ctx, () => {
        const r2 = makeRng(seed + 61);
        for (let i = 0; i < 90; i++) {            // scratches, mostly along the body
          const x = r2() * S, y = r2() * S, len = 20 + r2() * 120, a = (r2() - 0.5) * 0.5;
          ctx.strokeStyle = r2() < 0.6 ? 'rgba(210,222,220,0.3)' : 'rgba(40,36,30,0.35)';
          ctx.lineWidth = 0.8 + r2() * 1.2;
          ctx.beginPath(); ctx.moveTo(x, y); ctx.lineTo(x + Math.cos(a) * len, y + Math.sin(a) * len); ctx.stroke();
        }
        for (let i = 0; i < 26; i++) {            // runs of rust below a chip
          const x = r2() * S, y = r2() * S, len = 30 + r2() * 90;
          const g = ctx.createLinearGradient(0, y, 0, y + len);
          g.addColorStop(0, 'rgba(96,60,36,0.4)'); g.addColorStop(1, 'rgba(96,60,36,0)');
          ctx.fillStyle = g; ctx.fillRect(x, y, 2 + r2() * 5, len);
        }
      });
      grade(ctx, (r, g, b, a, p) => {
        // Broad staining decides where the metal is going; fine grain breaks
        // the patch up, so it reads as scabbed paint and not as a spot.
        const v = blot[p] * 0.45 + stain[p] * 0.25 + fine[p] * 0.3;
        const edge = Math.max(0, Math.min(1, (v - 0.585) * 16)), core = Math.max(0, Math.min(1, (v - 0.64) * 16));
        const chalk = 0.84 + fine[p] * 0.32;
        let R = r * chalk, G = g * chalk, B = b * chalk;
        R += (112 - R) * edge * 0.7; G += (72 - G) * edge * 0.7; B += (46 - B) * edge * 0.7;
        R += (54 - R) * core; G += (36 - G) * core; B += (27 - B) * core;
        return [R, G, B];
      });
      weather(ctx, 0.22, 0.14);
    },

    // Car glass at night: nearly black, a band of sky across it, and dust.
    glass(ctx) {
      const g = ctx.createLinearGradient(0, 0, 0, S);
      g.addColorStop(0, rgb(26, 34, 50)); g.addColorStop(0.45, rgb(9, 12, 19)); g.addColorStop(1, rgb(5, 7, 11));
      ctx.fillStyle = g; ctx.fillRect(0, 0, S, S);
      ctx.fillStyle = 'rgba(150,170,205,0.07)';
      ctx.beginPath(); ctx.moveTo(S * 0.05, 0); ctx.lineTo(S * 0.42, 0); ctx.lineTo(S * 0.2, S); ctx.lineTo(-S * 0.1, S); ctx.fill();
      ctx.beginPath(); ctx.moveTo(S * 0.5, 0); ctx.lineTo(S * 0.58, 0); ctx.lineTo(S * 0.38, S); ctx.lineTo(S * 0.32, S); ctx.fill();
      grade(ctx, (r, gr, b, a, p) => { const d = 1 + (fine[p] - 0.5) * 0.5 + Math.max(0, stain[p] - 0.6) * 0.9; return [r * d + 3, gr * d + 3, b * d + 3]; });
    },

    // Tyre tread, wrapped round the wheel: U runs round the circumference and
    // one tile spans the tread from shoulder to shoulder.
    tire(ctx) {
      ctx.fillStyle = rgb(20, 20, 21); ctx.fillRect(0, 0, S, S);
      const pitch = S / 6;
      for (let i = 0; i < 6; i++) {
        for (let row = 0; row < 4; row++) {
          const y0 = S * (0.14 + row * 0.185), h = S * 0.15;
          const x0 = i * pitch + (row % 2) * pitch * 0.5;
          ctx.fillStyle = rgb(46, 45, 44);
          for (const dx of [0, -S]) ctx.fillRect(x0 + dx + 5, y0, pitch - 16, h);
        }
        for (const y0 of [0, S * 0.9]) {            // shoulder lugs
          ctx.fillStyle = rgb(38, 37, 36);
          ctx.fillRect(i * pitch + 8, y0, pitch * 0.55, S * 0.1);
        }
      }
      weather(ctx, 0.3, 0.5, [1.08, 1.0, 0.9]);     // road dust
    },

    // The whole front of the truck on one card: chrome surround, egg-crate
    // grille, square lamps and the amber lights under them. It is stretched
    // more than four to one across the nose, so everything is drawn narrow.
    grille(ctx) {
      ctx.fillStyle = rgb(150, 154, 160); ctx.fillRect(0, 0, S, S);
      ctx.fillStyle = rgb(12, 13, 15); ctx.fillRect(S * 0.012, S * 0.06, S * 0.976, S * 0.88);
      ctx.fillStyle = rgb(96, 100, 106);
      for (let i = 1; i < 30; i++) ctx.fillRect(S * 0.2 + (S * 0.6 * i) / 30, S * 0.08, 2, S * 0.84);
      for (let j = 1; j < 7; j++) ctx.fillRect(S * 0.2, S * 0.06 + (S * 0.88 * j) / 7, S * 0.6, 7);
      ctx.fillStyle = rgb(160, 164, 170); ctx.fillRect(S * 0.2, S * 0.46, S * 0.6, 26);   // centre bar
      for (const x of [0.03, 0.82]) {
        ctx.fillStyle = rgb(168, 172, 178); ctx.fillRect(S * x, S * 0.1, S * 0.15, S * 0.56);       // bezel
        const g = ctx.createLinearGradient(0, S * 0.14, 0, S * 0.62);
        g.addColorStop(0, rgb(196, 208, 214)); g.addColorStop(0.5, rgb(120, 132, 140)); g.addColorStop(1, rgb(160, 170, 174));
        ctx.fillStyle = g; ctx.fillRect(S * (x + 0.012), S * 0.15, S * 0.126, S * 0.46);            // lens
        ctx.fillStyle = 'rgba(30,36,40,0.5)';
        for (let k = 1; k < 5; k++) ctx.fillRect(S * (x + 0.012) + (S * 0.126 * k) / 5, S * 0.15, 1, S * 0.46);
        ctx.fillStyle = rgb(190, 112, 26); ctx.fillRect(S * (x + 0.012), S * 0.72, S * 0.126, S * 0.17);  // indicator
      }
      weather(ctx, 0.25, 0.3);
    },

    // A number plate from nowhere in particular.
    plate(ctx) {
      ctx.fillStyle = rgb(212, 208, 192); ctx.fillRect(0, 0, S, S);
      ctx.strokeStyle = rgb(40, 52, 78); ctx.lineWidth = 18; ctx.strokeRect(22, 22, S - 44, S - 44);
      ctx.fillStyle = rgb(34, 46, 74);
      ctx.save(); ctx.translate(S / 2, S * 0.6); ctx.scale(0.5, 1.5);
      ctx.font = 'bold 190px ui-monospace, Menlo, Consolas, monospace';
      ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
      ctx.fillText('4KR 917', 0, 0);
      ctx.restore();
      weather(ctx, 0.35, 0.3, [1.0, 0.96, 0.88]);
    },

    /* ---- indoors ---- */

    // Papered once, a long time ago: a stripe and a sprig, gone the colour of tea.
    wallpaper(ctx) {
      ctx.fillStyle = rgb(196, 186, 150); ctx.fillRect(0, 0, S, S);
      for (let i = 0; i < 8; i++) {
        ctx.fillStyle = i % 2 ? 'rgba(120,128,92,0.34)' : 'rgba(150,120,84,0.16)';
        ctx.fillRect(i * 64 + 22, 0, i % 2 ? 6 : 20, S);
      }
      for (let y = 0; y < 8; y++) for (let x = 0; x < 8; x++) {
        const cx = x * 64 + 5 + (y % 2) * 32, cy = y * 64 + 32;
        ctx.fillStyle = 'rgba(132,74,62,0.5)';
        for (let k = 0; k < 5; k++) { ctx.beginPath(); ctx.ellipse(cx + Math.cos(k * 1.257) * 6, cy + Math.sin(k * 1.257) * 6, 4.5, 3, k * 1.257, 0, 7); ctx.fill(); }
        ctx.fillStyle = 'rgba(86,104,66,0.55)';
        ctx.beginPath(); ctx.ellipse(cx - 3, cy + 15, 3, 8, 0.5, 0, 7); ctx.fill();
        ctx.beginPath(); ctx.ellipse(cx + 5, cy + 16, 3, 7, -0.5, 0, 7); ctx.fill();
      }
      weather(ctx, 0.34, 0.14, [1.0, 0.97, 0.9]);
    },

    plaster(ctx) {
      ctx.fillStyle = rgb(206, 200, 184); ctx.fillRect(0, 0, S, S);
      wrapped(ctx, () => {
        const r2 = makeRng(seed + 71);
        for (let i = 0; i < 9; i++) {              // hairline cracks
          let x = r2() * S, y = r2() * S;
          ctx.strokeStyle = 'rgba(70,62,50,0.16)'; ctx.lineWidth = 1;
          ctx.beginPath(); ctx.moveTo(x, y);
          for (let k = 0; k < 9; k++) { x += (r2() - 0.5) * 34; y += 10 + r2() * 26; ctx.lineTo(x, y); }
          ctx.stroke();
        }
      });
      weather(ctx, 0.26, 0.12);
    },

    // Kitchen lino: a two-by-two check, worn through where people stand.
    lino(ctx) {
      for (let y = 0; y < 2; y++) for (let x = 0; x < 2; x++) {
        ctx.fillStyle = (x + y) % 2 ? rgb(196, 188, 162) : rgb(92, 112, 96);
        ctx.fillRect(x * 256, y * 256, 256, 256);
      }
      ctx.strokeStyle = 'rgba(30,30,26,0.5)'; ctx.lineWidth = 3;
      ctx.strokeRect(0, 0, 256, 256); ctx.strokeRect(256, 256, 256, 256);
      weather(ctx, 0.4, 0.22, [1.0, 0.96, 0.88]);
    },

    // Upholstery weave, pale so that each piece of furniture can tint it.
    fabric(ctx) {
      ctx.fillStyle = rgb(190, 184, 172); ctx.fillRect(0, 0, S, S);
      for (let i = 0; i < S; i += 4) {
        ctx.fillStyle = 'rgba(60,54,46,0.2)'; ctx.fillRect(i, 0, 1.5, S);
        ctx.fillStyle = 'rgba(255,250,240,0.14)'; ctx.fillRect(0, i + 2, S, 1.5);
      }
      for (let i = 0; i < 4; i++) {
        ctx.fillStyle = 'rgba(70,62,54,0.11)';
        ctx.fillRect(i * 128 + 40, 0, 26, S); ctx.fillRect(0, i * 128 + 40, S, 26);
      }
      weather(ctx, 0.2, 0.3);
    },

    // One whole rug, stretched to fit whatever floor it is put on.
    rug(ctx) {
      ctx.fillStyle = rgb(110, 36, 34); ctx.fillRect(0, 0, S, S);
      const band = (m, col, w) => { ctx.strokeStyle = col; ctx.lineWidth = w; ctx.strokeRect(m, m, S - 2 * m, S - 2 * m); };
      band(14, rgb(196, 176, 130), 14); band(40, rgb(34, 42, 68), 22); band(66, rgb(196, 176, 130), 5);
      const r2 = makeRng(seed + 83);
      for (let i = 0; i < 44; i++) {                // repeat round the border
        const t = (i / 44) * 4, side = t | 0, f = t - side, e = 40;
        const [x, y] = [[e + f * (S - 2 * e), e], [S - e, e + f * (S - 2 * e)], [S - e - f * (S - 2 * e), S - e], [e, S - e - f * (S - 2 * e)]][side];
        ctx.fillStyle = i % 2 ? rgb(170, 62, 46) : rgb(206, 190, 150);
        ctx.beginPath(); ctx.moveTo(x, y - 8); ctx.lineTo(x + 8, y); ctx.lineTo(x, y + 8); ctx.lineTo(x - 8, y); ctx.fill();
      }
      // A lozenge medallion in close tones, cut with petals: it should read as
      // pattern from across the room, not as rings.
      const loz = (rx, ry, col) => { ctx.fillStyle = col; ctx.beginPath(); ctx.moveTo(S / 2, S / 2 - ry); ctx.lineTo(S / 2 + rx, S / 2); ctx.lineTo(S / 2, S / 2 + ry); ctx.lineTo(S / 2 - rx, S / 2); ctx.fill(); };
      loz(118, 160, rgb(40, 46, 66)); loz(100, 138, rgb(126, 44, 38)); loz(70, 98, rgb(52, 56, 74)); loz(42, 58, rgb(170, 150, 110));
      for (let k = 0; k < 12; k++) {
        const a = (k / 12) * Math.PI * 2;
        ctx.fillStyle = k % 2 ? rgb(160, 140, 104) : rgb(96, 36, 32);
        ctx.beginPath(); ctx.ellipse(S / 2 + Math.cos(a) * 52, S / 2 + Math.sin(a) * 72, 9, 15, a, 0, 7); ctx.fill();
      }
      for (let i = 0; i < 70; i++) {                // field
        const x = 90 + r2() * (S - 180), y = 90 + r2() * (S - 180);
        if (Math.hypot((x - S / 2) / 130, (y - S / 2) / 170) < 1.1) continue;
        ctx.fillStyle = r2() < 0.5 ? rgb(196, 176, 130) : rgb(40, 50, 80);
        ctx.beginPath(); ctx.moveTo(x, y - 7); ctx.lineTo(x + 5, y); ctx.lineTo(x, y + 7); ctx.lineTo(x - 5, y); ctx.fill();
      }
      weather(ctx, 0.3, 0.42, [0.94, 0.9, 0.84]);
    },

    // Furniture timber: one continuous board, long figure, under old varnish.
    grain(ctx) {
      ctx.fillStyle = rgb(128, 82, 46); ctx.fillRect(0, 0, S, S);
      wrapped(ctx, () => {
        const r2 = makeRng(seed + 89);
        for (let i = 0; i < 230; i++) {
          const y = r2() * S, t = r2();
          ctx.strokeStyle = rgb(60 + t * 90, 34 + t * 60, 16 + t * 36, 0.32);
          ctx.lineWidth = 0.8 + r2() * 2.4;
          ctx.beginPath(); ctx.moveTo(-10, y);
          ctx.bezierCurveTo(S * 0.3, y + (r2() - 0.5) * 22, S * 0.7, y + (r2() - 0.5) * 22, S + 10, y + (r2() - 0.5) * 8);
          ctx.stroke();
        }
      });
      weather(ctx, 0.24, 0.16);
    },

    // A television with nothing on it.
    static(ctx) {
      const img = ctx.createImageData(S, S), r2 = makeRng(seed + 97);
      for (let y = 0; y < S; y += 2) for (let x = 0; x < S; x += 2) {
        const v = Math.pow(r2(), 1.4) * 255;
        for (const o of [0, 4, S * 4, S * 4 + 4]) {
          const p = (y * S + x) * 4 + o;
          img.data[p] = v * 0.86; img.data[p + 1] = v * 0.93; img.data[p + 2] = v; img.data[p + 3] = 255;
        }
      }
      ctx.putImageData(img, 0, 0);
    },

    // Two pictures side by side, each used through half of the card: a
    // landscape in oils gone dark, and a studio portrait nobody has dusted.
    picture(ctx) {
      const g = ctx.createLinearGradient(0, 0, 0, S);
      g.addColorStop(0, rgb(120, 126, 110)); g.addColorStop(0.5, rgb(170, 150, 104)); g.addColorStop(0.56, rgb(70, 78, 50)); g.addColorStop(1, rgb(40, 44, 28));
      ctx.fillStyle = g; ctx.fillRect(0, 0, S / 2, S);
      ctx.fillStyle = rgb(52, 62, 44);
      ctx.beginPath(); ctx.moveTo(0, S * 0.56);
      for (let x = 0; x <= S / 2; x += 16) ctx.lineTo(x, S * 0.5 - Math.sin(x * 0.021) * 26 - Math.sin(x * 0.06) * 8);
      ctx.lineTo(S / 2, S * 0.62); ctx.lineTo(0, S * 0.62); ctx.fill();
      ctx.fillStyle = rgb(92, 40, 30); ctx.fillRect(S * 0.27, S * 0.5, S * 0.09, S * 0.09);       // a barn, far off
      ctx.beginPath(); ctx.moveTo(S * 0.26, S * 0.5); ctx.lineTo(S * 0.315, S * 0.44); ctx.lineTo(S * 0.37, S * 0.5); ctx.fill();
      const p = ctx.createRadialGradient(S * 0.75, S * 0.42, 10, S * 0.75, S * 0.5, S * 0.42);
      p.addColorStop(0, rgb(176, 160, 128)); p.addColorStop(1, rgb(58, 48, 36));
      ctx.fillStyle = p; ctx.fillRect(S / 2, 0, S / 2, S);
      ctx.fillStyle = rgb(34, 30, 26);                                                          // sitter
      ctx.beginPath(); ctx.ellipse(S * 0.75, S * 0.36, S * 0.075, S * 0.105, 0, 0, 7); ctx.fill();
      ctx.beginPath(); ctx.moveTo(S * 0.56, S); ctx.quadraticCurveTo(S * 0.6, S * 0.5, S * 0.75, S * 0.5);
      ctx.quadraticCurveTo(S * 0.9, S * 0.5, S * 0.94, S); ctx.fill();
      ctx.fillStyle = rgb(150, 134, 108);
      ctx.beginPath(); ctx.ellipse(S * 0.75, S * 0.37, S * 0.05, S * 0.075, 0, 0, 7); ctx.fill();
      weather(ctx, 0.3, 0.3, [0.92, 0.86, 0.74]);
    },

    // Twenty to midnight.
    clockface(ctx) {
      ctx.fillStyle = rgb(216, 208, 184); ctx.fillRect(0, 0, S, S);
      ctx.translate(S / 2, S / 2);
      ctx.strokeStyle = rgb(30, 26, 22); ctx.lineWidth = 6;
      ctx.beginPath(); ctx.arc(0, 0, S * 0.45, 0, 7); ctx.stroke();
      ctx.fillStyle = rgb(30, 26, 22); ctx.font = 'bold 54px Georgia, serif'; ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
      for (let h = 1; h <= 12; h++) {
        const a = (h / 12) * Math.PI * 2;
        ctx.fillText(String(h), Math.sin(a) * S * 0.36, -Math.cos(a) * S * 0.36);
      }
      for (let i = 0; i < 60; i++) {
        const a = (i / 60) * Math.PI * 2;
        ctx.save(); ctx.rotate(a); ctx.fillRect(-1.5, -S * 0.445, 3, i % 5 ? 10 : 20); ctx.restore();
      }
      const hand = (a, len, w) => { ctx.save(); ctx.rotate(a); ctx.fillRect(-w / 2, -len, w, len + 18); ctx.restore(); };
      hand(((11 + 40 / 60) / 12) * Math.PI * 2, S * 0.24, 12);
      hand((40 / 60) * Math.PI * 2, S * 0.36, 7);
      ctx.beginPath(); ctx.arc(0, 0, 12, 0, 7); ctx.fill();
      ctx.setTransform(1, 0, 0, 1, 0, 0);
      weather(ctx, 0.22, 0.16, [1.0, 0.96, 0.86]);
    },

    // Square white wall tile, four to a side, the grout gone grey.
    tile(ctx) {
      ctx.fillStyle = rgb(120, 116, 106); ctx.fillRect(0, 0, S, S);
      for (let y = 0; y < 4; y++) for (let x = 0; x < 4; x++) {
        const v = R(0.92, 1.0);
        ctx.fillStyle = rgb(214 * v, 214 * v, 204 * v);
        ctx.fillRect(x * 128 + 3, y * 128 + 3, 122, 122);
        const g = ctx.createLinearGradient(x * 128, y * 128, x * 128 + 128, y * 128 + 128);
        g.addColorStop(0, 'rgba(255,255,255,0.22)'); g.addColorStop(0.5, 'rgba(255,255,255,0)'); g.addColorStop(1, 'rgba(0,0,0,0.12)');
        ctx.fillStyle = g; ctx.fillRect(x * 128 + 3, y * 128 + 3, 122, 122);
      }
      weather(ctx, 0.2, 0.12, [1.0, 0.98, 0.92]);
    },

    // Printed matter, again two to a card: a newspaper and a magazine cover.
    print(ctx) {
      ctx.fillStyle = rgb(206, 200, 180); ctx.fillRect(0, 0, S / 2, S);
      ctx.fillStyle = rgb(30, 28, 26); ctx.fillRect(14, 16, S / 2 - 28, 46);
      ctx.fillRect(14, 78, S / 2 - 28, 4);
      ctx.fillStyle = rgb(120, 114, 100); ctx.fillRect(18, 96, 120, 96);
      ctx.fillStyle = 'rgba(40,38,34,0.6)';
      for (let col = 0; col < 3; col++) for (let y = 96; y < S - 20; y += 9) {
        if (col === 0 && y < 200) continue;
        ctx.fillRect(18 + col * 76 + (col ? 0 : 0), y, 62 + ((y * 7) % 9), 4);
      }
      ctx.fillStyle = rgb(150, 44, 36); ctx.fillRect(S / 2, 0, S / 2, S);
      ctx.fillStyle = rgb(226, 214, 180); ctx.fillRect(S / 2 + 18, 20, S / 2 - 36, 60);
      ctx.fillStyle = rgb(60, 74, 80); ctx.fillRect(S / 2 + 18, 110, S / 2 - 36, 260);
      ctx.fillStyle = rgb(196, 170, 120);
      ctx.beginPath(); ctx.ellipse(S * 0.75, S * 0.47, 50, 76, 0, 0, 7); ctx.fill();
      ctx.fillStyle = 'rgba(240,230,200,0.85)';
      for (let y = 396; y < S - 20; y += 22) ctx.fillRect(S / 2 + 18, y, 120 + ((y * 5) % 70), 9);
      weather(ctx, 0.24, 0.24, [1.0, 0.95, 0.84]);
    },
  };

  /**
   * One conifer. `crown` is how far down the trunk the foliage reaches (a
   * spruce is clothed nearly to the ground, a pine carries its crown high),
   * and `spread` its widest half-width as a fraction of the card.
   */
  function conifer(ctx, r2, crown, top, spread) {
    const cx = S / 2;
    ctx.fillStyle = rgb(30, 24, 18);
    ctx.beginPath();
    ctx.moveTo(cx - 9, S); ctx.lineTo(cx + 9, S); ctx.lineTo(cx + 2, S * 0.1); ctx.lineTo(cx - 2, S * 0.1);
    ctx.fill();
    const y0 = S * top, y1 = S * (top + (0.9 - top) * crown);
    const blob = (x, y, r) => {
      const t = r2();
      ctx.fillStyle = rgb(16 + t * 30, 30 + t * 42, 18 + t * 22);
      ctx.beginPath();
      const n = 6 + ((r2() * 3) | 0);
      for (let k = 0; k < n; k++) {
        const a = (k / n) * Math.PI * 2, rr = r * (0.45 + r2() * 0.75);
        const px = x + Math.cos(a) * rr * 1.35, py = y + Math.sin(a) * rr * 0.8;
        if (k) ctx.lineTo(px, py); else ctx.moveTo(px, py);
      }
      ctx.fill();
    };
    for (let i = 0; i < 330; i++) {
      const t = Math.pow(r2(), 0.75);
      const y = y0 + (y1 - y0) * t;
      const side = r2() < 0.5 ? -1 : 1;
      const len = S * (0.03 + Math.pow(t, 0.85) * spread) * (0.55 + r2() * 0.5);
      const droop = len * (0.2 + r2() * 0.3);
      const steps = 4 + ((len / 16) | 0);
      for (let s = 0; s <= steps; s++) {
        const u = s / steps;
        blob(cx + side * len * u, y + droop * u * u + (r2() - 0.5) * 6, 7 + (1 - u) * 9 + r2() * 5);
      }
    }
    keyAlpha(ctx, [26, 40, 24]);
  }

  /**
   * Cards are alpha-tested, and a filtered texture blends edge texels with
   * their transparent neighbours. Give those neighbours the foliage colour so
   * the blend stays green instead of fringing black.
   */
  function keyAlpha(ctx, fill) {
    grade(ctx, (r, g, b, a) => (a < 20 ? [fill[0], fill[1], fill[2], 0] : [r, g, b, 255]));
  }

  // WebGL ignores UNPACK_FLIP_Y for raw pixel uploads into a 3D texture, so
  // rows are flipped here: v = 0 is the bottom of every painting.
  return LAYERS.map(({ name }) => {
    const ctx = surface();
    painters[name](ctx);
    const src = ctx.getImageData(0, 0, S, S).data;
    const out = new Uint8Array(S * S * 4);
    for (let y = 0; y < S; y++) out.set(src.subarray((S - 1 - y) * S * 4, (S - y) * S * 4), y * S * 4);
    return out;
  });
}
