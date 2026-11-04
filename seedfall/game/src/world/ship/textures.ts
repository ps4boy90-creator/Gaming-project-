import * as THREE from 'three';

/* Procedural, tileable PBR textures painted on canvases at boot. No downloaded assets. */

function hash2(x: number, y: number, seed: number): number {
  let h = (x * 374761393 + y * 668265263 + seed * 1442695041) | 0;
  h = Math.imul(h ^ (h >>> 13), 1274126177);
  h ^= h >>> 16;
  return (h >>> 0) / 4294967295;
}

/** Periodic value noise: tiles every `period` lattice cells. */
function vnoise(x: number, y: number, period: number, seed: number): number {
  const xi = Math.floor(x);
  const yi = Math.floor(y);
  const xf = x - xi;
  const yf = y - yi;
  const u = xf * xf * (3 - 2 * xf);
  const v = yf * yf * (3 - 2 * yf);
  const x0 = ((xi % period) + period) % period;
  const y0 = ((yi % period) + period) % period;
  const x1 = (x0 + 1) % period;
  const y1 = (y0 + 1) % period;
  const a = hash2(x0, y0, seed);
  const b = hash2(x1, y0, seed);
  const c = hash2(x0, y1, seed);
  const d = hash2(x1, y1, seed);
  return a + (b - a) * u + (c - a) * v + (a - b - c + d) * u * v;
}

/** Tileable fBm over texture space (u,v in 0..1). */
export function fbm(u: number, v: number, basePeriod: number, octaves: number, seed: number): number {
  let amp = 0.5;
  let sum = 0;
  let norm = 0;
  let p = basePeriod;
  for (let o = 0; o < octaves; o++) {
    sum += amp * vnoise(u * p, v * p, p, seed + o * 17);
    norm += amp;
    amp *= 0.5;
    p *= 2;
  }
  return sum / norm;
}

interface Layers {
  w: number;
  h: number;
  height: Float32Array;
  albedo: Float32Array; // rgb 0..1 (sRGB)
  rough: Float32Array;
  alpha?: Float32Array;
}

function layers(w: number, h: number): Layers {
  return {
    w,
    h,
    height: new Float32Array(w * h),
    albedo: new Float32Array(w * h * 3),
    rough: new Float32Array(w * h),
  };
}

function canvas(w: number, h: number): [HTMLCanvasElement, CanvasRenderingContext2D] {
  const c = document.createElement('canvas');
  c.width = w;
  c.height = h;
  return [c, c.getContext('2d', { willReadFrequently: false })!];
}

function toTexture(c: HTMLCanvasElement, srgb: boolean): THREE.CanvasTexture {
  const t = new THREE.CanvasTexture(c);
  t.wrapS = t.wrapT = THREE.RepeatWrapping;
  t.colorSpace = srgb ? THREE.SRGBColorSpace : THREE.NoColorSpace;
  t.anisotropy = 8;
  t.generateMipmaps = true;
  t.minFilter = THREE.LinearMipmapLinearFilter;
  t.needsUpdate = true;
  return t;
}

export interface PBRSet {
  map: THREE.Texture;
  normalMap: THREE.Texture;
  roughnessMap: THREE.Texture;
  alphaMap?: THREE.Texture;
}

/** Bake layers into map/normal/roughness textures. Row 0 of the arrays is v = 0 (bottom). */
function bake(L: Layers, normalStrength: number): PBRSet {
  const { w, h } = L;
  const [ca, xa] = canvas(w, h);
  const [cn, xn] = canvas(w, h);
  const [cr, xr] = canvas(w, h);
  const ia = xa.createImageData(w, h);
  const inn = xn.createImageData(w, h);
  const ir = xr.createImageData(w, h);
  const H = L.height;
  for (let y = 0; y < h; y++) {
    const py = h - 1 - y; // canvas row (top-down)
    for (let x = 0; x < w; x++) {
      const i = y * w + x;
      const o = (py * w + x) * 4;
      ia.data[o] = Math.max(0, Math.min(255, L.albedo[i * 3] * 255));
      ia.data[o + 1] = Math.max(0, Math.min(255, L.albedo[i * 3 + 1] * 255));
      ia.data[o + 2] = Math.max(0, Math.min(255, L.albedo[i * 3 + 2] * 255));
      ia.data[o + 3] = L.alpha ? L.alpha[i] * 255 : 255;
      const xl = (x - 1 + w) % w;
      const xr2 = (x + 1) % w;
      const yd = (y - 1 + h) % h;
      const yu = (y + 1) % h;
      const dhdu = (H[y * w + xr2] - H[y * w + xl]) * normalStrength;
      const dhdv = (H[yu * w + x] - H[yd * w + x]) * normalStrength;
      let nx = -dhdu;
      let ny = -dhdv;
      let nz = 1;
      const len = Math.hypot(nx, ny, nz);
      nx /= len;
      ny /= len;
      nz /= len;
      inn.data[o] = (nx * 0.5 + 0.5) * 255;
      inn.data[o + 1] = (ny * 0.5 + 0.5) * 255;
      inn.data[o + 2] = (nz * 0.5 + 0.5) * 255;
      inn.data[o + 3] = 255;
      const r = Math.max(0, Math.min(1, L.rough[i])) * 255;
      ir.data[o] = r;
      ir.data[o + 1] = r; // three reads roughness from G
      ir.data[o + 2] = r;
      ir.data[o + 3] = 255;
    }
  }
  xa.putImageData(ia, 0, 0);
  xn.putImageData(inn, 0, 0);
  xr.putImageData(ir, 0, 0);
  return { map: toTexture(ca, true), normalMap: toTexture(cn, false), roughnessMap: toTexture(cr, false) };
}

const smooth = (a: number, b: number, x: number) => {
  const t = Math.min(1, Math.max(0, (x - a) / (b - a)));
  return t * t * (3 - 2 * t);
};

/** Groove profile: 1 at a seam line, falling to 0 over `width` (in texture units). */
function seam(d: number, width: number): number {
  return 1 - smooth(0, width, Math.abs(d));
}

/** Wall cladding: 2.0 m wide × 4.0 m tall tile; v = 0 is the deck floor. */
export function wallPanels(seed = 1): PBRSet {
  const w = 512;
  const h = 1024;
  const L = layers(w, h);
  const rows = [0, 0.12 / 4, 1.15 / 4, 2.3 / 4, 3.0 / 4, 1]; // seam heights in v
  for (let y = 0; y < h; y++) {
    const v = y / h;
    for (let x = 0; x < w; x++) {
      const u = x / w;
      const i = y * w + x;
      // panel ids for subtle per-panel variation
      let row = 0;
      while (row < rows.length - 2 && v > rows[row + 1]) row++;
      const col = u < 0.5 ? 0 : 1;
      const pid = hash2(col, row, seed);
      // seams
      let g = 0;
      for (const r of rows) g = Math.max(g, seam(v - r, 1.6 / h));
      g = Math.max(g, seam(u, 2 / w), seam(u - 0.5, 2 / w), seam(u - 1, 2 / w));
      // fasteners near panel corners
      let bolt = 0;
      for (const r of rows.slice(1, 5)) {
        for (const cu of [0.035, 0.465, 0.535, 0.965]) {
          const dd = Math.hypot((u - cu) * 2.0, (v - (r - 0.012)) * 4.0) * 100; // in cm
          bolt = Math.max(bolt, 1 - smooth(0.4, 0.9, dd));
        }
      }
      const n = fbm(u, v, 8, 4, seed + 3);
      const fine = fbm(u, v, 64, 2, seed + 9);
      const kick = v < rows[1] ? 1 : 0;
      L.height[i] = -g * 0.9 + bolt * 0.5 + (fine - 0.5) * 0.04;
      // albedo: warm off-white composite, darker kick plate, grime toward the floor
      const grime = (1 - smooth(0, 0.22, v)) * 0.35 + (n - 0.5) * 0.06;
      const tint = (pid - 0.5) * 0.035;
      let r = 0.78 + tint - grime * 0.25;
      let gg = 0.79 + tint - grime * 0.25;
      let b = 0.76 + tint - grime * 0.22;
      if (kick) {
        r = 0.2 + n * 0.05;
        gg = 0.21 + n * 0.05;
        b = 0.22 + n * 0.05;
      }
      const dark = 1 - g * 0.55;
      L.albedo[i * 3] = r * dark;
      L.albedo[i * 3 + 1] = gg * dark;
      L.albedo[i * 3 + 2] = b * dark;
      L.rough[i] = kick ? 0.55 + n * 0.2 : 0.42 + pid * 0.12 + (fine - 0.5) * 0.1 + g * 0.2;
    }
  }
  return bake(L, 18);
}

/** Rubberised anti-slip deck tiles: 2.0 m tile, 1.0 m plates with raised studs. */
export function floorTiles(seed = 2): PBRSet {
  const s = 1024;
  const L = layers(s, s);
  const studs = 36; // per 2 m
  for (let y = 0; y < s; y++) {
    const v = y / s;
    for (let x = 0; x < s; x++) {
      const u = x / s;
      const i = y * s + x;
      const g = Math.max(seam(u, 2 / s), seam(u - 0.5, 2 / s), seam(u - 1, 2 / s), seam(v, 2 / s), seam(v - 0.5, 2 / s), seam(v - 1, 2 / s));
      const fu = (u * studs) % 1;
      const fv = (v * studs) % 1;
      const d = Math.hypot(fu - 0.5, fv - 0.5);
      const stud = 1 - smooth(0.17, 0.24, d);
      const plate = hash2(u < 0.5 ? 0 : 1, v < 0.5 ? 0 : 1, seed);
      const n = fbm(u, v, 6, 4, seed + 5);
      const wear = smooth(0.45, 0.75, fbm(u, v, 3, 3, seed + 11));
      L.height[i] = stud * 0.35 - g * 1.0 + (fbm(u, v, 128, 1, seed) - 0.5) * 0.05;
      const base = 0.13 + plate * 0.02 + n * 0.04 + wear * 0.05 + stud * wear * 0.06;
      L.albedo[i * 3] = base;
      L.albedo[i * 3 + 1] = base * 1.03;
      L.albedo[i * 3 + 2] = base * 1.08;
      L.rough[i] = 0.78 - stud * (0.18 + wear * 0.15) + g * 0.1;
    }
  }
  return bake(L, 10);
}

/** Ceiling: perforated acoustic panels, 2.0 m tile of 0.5 m squares. */
export function ceilingPanels(seed = 3): PBRSet {
  const s = 512;
  const L = layers(s, s);
  for (let y = 0; y < s; y++) {
    const v = y / s;
    for (let x = 0; x < s; x++) {
      const u = x / s;
      const i = y * s + x;
      const g = Math.max(seam((u * 4) % 1, 0.012), seam(((u * 4) % 1) - 1, 0.012), seam((v * 4) % 1, 0.012), seam(((v * 4) % 1) - 1, 0.012));
      const pu = (u * 4 * 14) % 1;
      const pv = (v * 4 * 14) % 1;
      const hole = 1 - smooth(0.12, 0.2, Math.hypot(pu - 0.5, pv - 0.5));
      const n = fbm(u, v, 4, 3, seed);
      L.height[i] = -g - hole * 0.4;
      const c = (0.62 + n * 0.05) * (1 - hole * 0.6) * (1 - g * 0.5);
      L.albedo[i * 3] = c;
      L.albedo[i * 3 + 1] = c;
      L.albedo[i * 3 + 2] = c * 1.02;
      L.rough[i] = 0.75;
    }
  }
  return bake(L, 6);
}

/** Brushed dark metal, 1 m tile. */
export function brushedMetal(seed = 4, base = 0.09): PBRSet {
  const s = 512;
  const L = layers(s, s);
  for (let y = 0; y < s; y++) {
    const v = y / s;
    for (let x = 0; x < s; x++) {
      const u = x / s;
      const i = y * s + x;
      const streak = vnoise(u * 4, v * 256, 4, seed) * 0.6 + vnoise(u * 16, v * 512, 16, seed + 1) * 0.4;
      const blot = fbm(u, v, 4, 3, seed + 2);
      L.height[i] = streak * 0.1;
      const c = base + streak * 0.025 + (blot - 0.5) * 0.03;
      L.albedo[i * 3] = c;
      L.albedo[i * 3 + 1] = c * 1.02;
      L.albedo[i * 3 + 2] = c * 1.06;
      L.rough[i] = 0.32 + streak * 0.12 + blot * 0.12;
    }
  }
  return bake(L, 2);
}

/** Satin painted surface for props and exterior hull, 2 m tile with faint panel lines. */
export function paint(seed = 5, rgb: [number, number, number] = [0.8, 0.81, 0.79], panelLines = false): PBRSet {
  const s = 512;
  const L = layers(s, s);
  for (let y = 0; y < s; y++) {
    const v = y / s;
    for (let x = 0; x < s; x++) {
      const u = x / s;
      const i = y * s + x;
      const n = fbm(u, v, 6, 4, seed);
      const fine = fbm(u, v, 48, 2, seed + 1);
      let g = 0;
      if (panelLines) {
        g = Math.max(seam(u, 1.5 / s), seam(u - 1, 1.5 / s), seam(v, 1.5 / s), seam(v - 1, 1.5 / s), seam(v - 0.375, 1.5 / s), seam(u - 0.625, 1.5 / s) * (v > 0.375 ? 1 : 0));
      }
      L.height[i] = (fine - 0.5) * 0.05 - g;
      const k = 1 + (n - 0.5) * 0.08 - g * 0.4;
      L.albedo[i * 3] = rgb[0] * k;
      L.albedo[i * 3 + 1] = rgb[1] * k;
      L.albedo[i * 3 + 2] = rgb[2] * k;
      L.rough[i] = 0.38 + n * 0.2 + g * 0.2;
    }
  }
  return bake(L, 8);
}

/** Woven upholstery, 0.5 m tile. */
export function fabric(seed = 6, rgb: [number, number, number] = [0.18, 0.2, 0.23]): PBRSet {
  const s = 256;
  const L = layers(s, s);
  for (let y = 0; y < s; y++) {
    const v = y / s;
    for (let x = 0; x < s; x++) {
      const u = x / s;
      const i = y * s + x;
      const a = Math.sin(u * Math.PI * 2 * 64) * 0.5 + 0.5;
      const b = Math.sin(v * Math.PI * 2 * 64) * 0.5 + 0.5;
      const weave = ((Math.floor(u * 64) + Math.floor(v * 64)) % 2 === 0 ? a : b) * 0.6;
      const n = fbm(u, v, 4, 3, seed);
      L.height[i] = weave * 0.4;
      const k = 0.9 + weave * 0.15 + (n - 0.5) * 0.12;
      L.albedo[i * 3] = rgb[0] * k;
      L.albedo[i * 3 + 1] = rgb[1] * k;
      L.albedo[i * 3 + 2] = rgb[2] * k;
      L.rough[i] = 0.92;
    }
  }
  return bake(L, 3);
}

/** Crinkled gold collector film for the solar sails. */
export function sailFoil(seed = 7): PBRSet {
  const s = 512;
  const L = layers(s, s);
  for (let y = 0; y < s; y++) {
    const v = y / s;
    for (let x = 0; x < s; x++) {
      const u = x / s;
      const i = y * s + x;
      const r1 = 1 - Math.abs(fbm(u, v, 6, 4, seed) * 2 - 1);
      const r2 = 1 - Math.abs(fbm(u, v, 14, 3, seed + 4) * 2 - 1);
      const grid = Math.max(seam((u * 8) % 1, 0.01), seam((v * 8) % 1, 0.01));
      L.height[i] = r1 * r1 * 0.8 + r2 * 0.3 + grid * 0.3;
      const k = 0.85 + r1 * 0.2;
      L.albedo[i * 3] = 0.98 * k;
      L.albedo[i * 3 + 1] = 0.74 * k;
      L.albedo[i * 3 + 2] = 0.38 * k;
      L.rough[i] = 0.18 + r2 * 0.2 + grid * 0.3;
    }
  }
  return bake(L, 4);
}

/** Frosted cryo-pod canopy: albedo/roughness plus an alpha map of frost crystals. */
export function frost(seed = 8): PBRSet {
  const s = 512;
  const L = layers(s, s);
  L.alpha = new Float32Array(s * s);
  for (let y = 0; y < s; y++) {
    const v = y / s;
    for (let x = 0; x < s; x++) {
      const u = x / s;
      const i = y * s + x;
      const n = fbm(u, v, 5, 5, seed);
      const crystal = 1 - Math.abs(fbm(u, v, 24, 3, seed + 2) * 2 - 1);
      const f = smooth(0.35, 0.75, n) * 0.7 + crystal * crystal * 0.3;
      L.height[i] = f;
      L.albedo[i * 3] = 0.82;
      L.albedo[i * 3 + 1] = 0.9;
      L.albedo[i * 3 + 2] = 0.96;
      L.rough[i] = 0.15 + f * 0.7;
      L.alpha[i] = 0.25 + f * 0.6;
    }
  }
  const set = bake(L, 2);
  // separate alpha map (green channel)
  const [ca, xa] = canvas(s, s);
  const img = xa.createImageData(s, s);
  for (let y = 0; y < s; y++) {
    for (let x = 0; x < s; x++) {
      const a = L.alpha[y * s + x] * 255;
      const o = ((s - 1 - y) * s + x) * 4;
      img.data[o] = img.data[o + 1] = img.data[o + 2] = a;
      img.data[o + 3] = 255;
    }
  }
  xa.putImageData(img, 0, 0);
  set.alphaMap = toTexture(ca, false);
  return set;
}

/** Yellow/black hazard chevrons, 1 m tile. */
export function hazard(seed = 9): PBRSet {
  const s = 256;
  const L = layers(s, s);
  for (let y = 0; y < s; y++) {
    const v = y / s;
    for (let x = 0; x < s; x++) {
      const u = x / s;
      const i = y * s + x;
      const stripe = ((u + v) * 5) % 1 < 0.5;
      const wear = smooth(0.55, 0.8, fbm(u, v, 8, 4, seed));
      const n = fbm(u, v, 32, 2, seed + 1);
      let r = stripe ? 0.85 : 0.04;
      let g = stripe ? 0.62 : 0.04;
      let b = stripe ? 0.05 : 0.04;
      r = r * (1 - wear) + 0.35 * wear;
      g = g * (1 - wear) + 0.36 * wear;
      b = b * (1 - wear) + 0.37 * wear;
      L.height[i] = n * 0.1 - wear * 0.05;
      L.albedo[i * 3] = r;
      L.albedo[i * 3 + 1] = g;
      L.albedo[i * 3 + 2] = b;
      L.rough[i] = 0.55 + wear * 0.3;
    }
  }
  return bake(L, 3);
}

/** Sliding door leaf (UV 0..1 across the leaf): ribbed panel, vision slit, hazard edge. */
export function doorLeaf(seed = 10): PBRSet {
  const w = 256;
  const h = 512;
  const L = layers(w, h);
  for (let y = 0; y < h; y++) {
    const v = y / h;
    for (let x = 0; x < w; x++) {
      const u = x / w;
      const i = y * w + x;
      const rib = v > 0.08 && v < 0.55 ? Math.max(0, Math.sin(v * Math.PI * 2 * 18)) * 0.3 : 0;
      const slit = u > 0.3 && u < 0.7 && v > 0.62 && v < 0.82 ? 1 : 0;
      const edge = u > 0.92 ? 1 : 0;
      const frame = Math.max(seam(u - 0.05, 0.01), seam(u - 0.95, 0.01), seam(v - 0.05, 0.006), seam(v - 0.95, 0.006), seam(v - 0.58, 0.006));
      const n = fbm(u, v, 6, 3, seed);
      L.height[i] = rib - frame * 0.6 - slit * 0.5;
      let r = 0.5 + (n - 0.5) * 0.06;
      let g = 0.52 + (n - 0.5) * 0.06;
      let b = 0.54 + (n - 0.5) * 0.06;
      if (edge) {
        const st = ((u * 3 + v * 12) % 1) < 0.5;
        r = st ? 0.85 : 0.05;
        g = st ? 0.6 : 0.05;
        b = st ? 0.05 : 0.05;
      }
      if (slit) r = g = b = 0.03;
      L.albedo[i * 3] = r * (1 - frame * 0.4);
      L.albedo[i * 3 + 1] = g * (1 - frame * 0.4);
      L.albedo[i * 3 + 2] = b * (1 - frame * 0.4);
      L.rough[i] = slit ? 0.05 : 0.45 + n * 0.15;
    }
  }
  return bake(L, 6);
}

/** Soft radial gradient used for mist sprites and light glows. */
export function radialGlow(size = 128): THREE.Texture {
  const [c, x] = canvas(size, size);
  const g = x.createRadialGradient(size / 2, size / 2, 0, size / 2, size / 2, size / 2);
  g.addColorStop(0, 'rgba(255,255,255,1)');
  g.addColorStop(0.4, 'rgba(255,255,255,0.35)');
  g.addColorStop(1, 'rgba(255,255,255,0)');
  x.fillStyle = g;
  x.fillRect(0, 0, size, size);
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  return t;
}

/** Wispy, tileable mist for low-lying cryo vapour. */
export function mist(seed = 12): THREE.Texture {
  const s = 256;
  const [c, x] = canvas(s, s);
  const img = x.createImageData(s, s);
  for (let y = 0; y < s; y++) {
    for (let xx = 0; xx < s; xx++) {
      const n = fbm(xx / s, y / s, 3, 5, seed);
      const a = smooth(0.4, 0.75, n) * 255;
      const o = (y * s + xx) * 4;
      img.data[o] = img.data[o + 1] = img.data[o + 2] = 255;
      img.data[o + 3] = a;
    }
  }
  x.putImageData(img, 0, 0);
  const t = new THREE.CanvasTexture(c);
  t.wrapS = t.wrapT = THREE.RepeatWrapping;
  t.colorSpace = THREE.SRGBColorSpace;
  return t;
}
