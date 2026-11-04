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
  /** Optional per-texel metalness, baked into the blue channel of the roughness map. */
  metal?: Float32Array;
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
  /** True when the roughness map's blue channel holds metalness. */
  metal?: boolean;
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
      ir.data[o + 2] = L.metal ? Math.max(0, Math.min(1, L.metal[i])) * 255 : r; // three reads metalness from B
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

/* ------------------------------------------------------------------ spaceship surfaces */

/** Crew-area wall, 2 m × 4 m tile, v = 0 at the deck: kick plate, dark equipment band with
 *  vents, a trim band, white padded quilting, and a technical upper band. */
export function paddedWall(seed = 21): PBRSet {
  const w = 512;
  const h = 1024;
  const L = layers(w, h);
  for (let y = 0; y < h; y++) {
    const v = y / h;
    const ym = v * 4;
    for (let x = 0; x < w; x++) {
      const u = x / w;
      const xm = u * 2;
      const i = y * w + x;
      const n = fbm(u, v, 8, 3, seed);
      let r = 0.8;
      let g = 0.81;
      let b = 0.79;
      let hgt = 0;
      let rough = 0.6;
      if (ym < 0.12) {
        r = g = b = 0.12 + n * 0.04;
        rough = 0.55;
        hgt = -0.2;
      } else if (ym < 1.0) {
        // lower equipment panels with vent slots and fasteners
        const px = xm % 1.0;
        const py = ym - 0.12;
        const seamV = Math.max(seam(px, 0.006), seam(px - 1, 0.006));
        const seamH = Math.max(seam(ym - 0.12, 0.006), seam(ym - 1.0, 0.006));
        const vent = px > 0.18 && px < 0.52 && py > 0.32 && py < 0.58 && (py * 40) % 1 < 0.45 ? 1 : 0;
        let bolt = 0;
        for (const [bx, by] of [[0.04, 0.05], [0.96, 0.05], [0.04, 0.83], [0.96, 0.83]]) bolt = Math.max(bolt, 1 - smooth(0.004, 0.009, Math.hypot(px - bx, py - by)));
        const tag = px > 0.66 && px < 0.86 && py > 0.6 && py < 0.7 ? 1 : 0;
        const pid = hash2(Math.floor(xm), 7, seed);
        const base = 0.27 + pid * 0.04 + n * 0.03;
        r = base;
        g = base * 1.02;
        b = base * 1.06;
        if (tag) {
          r = 0.72;
          g = 0.7;
          b = 0.6;
        }
        hgt = -Math.max(seamV, seamH) - vent * 0.7 + bolt * 0.5;
        if (vent) r = g = b = 0.04;
        rough = 0.42 + n * 0.15;
      } else if (ym < 1.14) {
        r = g = b = 0.2;
        hgt = -0.1;
        rough = 0.5;
      } else if (ym < 2.56) {
        // padded quilting, 0.5 m × 0.355 m cushions
        const cx = (xm / 0.5) % 1;
        const cy = ((ym - 1.14) / 0.355) % 1;
        const ex = Math.pow(Math.abs(cx * 2 - 1), 4);
        const ey = Math.pow(Math.abs(cy * 2 - 1), 4);
        const pillow = (1 - ex) * (1 - ey);
        const stitchX = seam(cx, 0.02) + seam(cx - 1, 0.02);
        const stitchY = seam(cy, 0.03) + seam(cy - 1, 0.03);
        const button = 1 - smooth(0.0, 0.035, Math.hypot(Math.min(cx, 1 - cx) * 0.5, Math.min(cy, 1 - cy) * 0.355));
        hgt = pillow * 1.2 - Math.min(1, stitchX + stitchY) * 0.4 - button * 0.4;
        const shade = 0.78 + pillow * 0.05 + n * 0.03;
        r = shade;
        g = shade * 1.01;
        b = shade * 0.985;
        rough = 0.55 + (1 - pillow) * 0.15;
      } else if (ym < 2.62) {
        r = g = b = 0.16;
        hgt = -0.3;
      } else {
        const sV = Math.max(seam(xm % 1.0, 0.006), seam((xm % 1.0) - 1, 0.006));
        r = g = b = 0.4 + n * 0.04;
        hgt = -sV;
        rough = 0.5;
      }
      L.height[i] = hgt;
      L.albedo[i * 3] = r;
      L.albedo[i * 3 + 1] = g;
      L.albedo[i * 3 + 2] = b;
      L.rough[i] = rough;
    }
  }
  return bake(L, 10);
}

/** Service-area wall: grey plating with greebles (vents, inset panels, rivet rows, labels). */
export function techPanels(seed = 31): PBRSet {
  const w = 512;
  const h = 1024;
  const L = layers(w, h);
  const rowsM = [0, 0.12, 0.9, 1.9, 2.6, 4];
  for (let y = 0; y < h; y++) {
    const v = y / h;
    const ym = v * 4;
    let row = 0;
    while (row < rowsM.length - 2 && ym > rowsM[row + 1]) row++;
    const y0 = rowsM[row];
    const y1 = rowsM[row + 1];
    for (let x = 0; x < w; x++) {
      const u = x / w;
      const xm = u * 2;
      const i = y * w + x;
      const col = Math.floor(xm);
      const px = xm - col;
      const py = (ym - y0) / (y1 - y0);
      const pid = hash2(col, row, seed);
      const n = fbm(u, v, 8, 3, seed + 1);
      const sm = Math.max(seam(px, 0.005), seam(px - 1, 0.005), seam(ym - y0, 0.006), seam(ym - y1, 0.006));
      let feat = 0;
      let dark = 0;
      const kind = Math.floor(pid * 5);
      if (row === 0) dark = 1;
      else if (kind === 0) {
        // vent slots
        if (px > 0.15 && px < 0.85 && py > 0.25 && py < 0.75 && (px * 36) % 1 < 0.4) {
          feat = -0.6;
          dark = 0.85;
        }
      } else if (kind === 1) {
        // inset hatch with handle
        const inside = px > 0.12 && px < 0.88 && py > 0.12 && py < 0.88;
        const edge = inside && (px < 0.14 || px > 0.86 || py < 0.14 || py > 0.86);
        if (edge) feat = -0.5;
        if (px > 0.7 && px < 0.8 && py > 0.45 && py < 0.55) feat = 0.6;
      } else if (kind === 2) {
        // rivet rows
        if ((Math.abs(py - 0.1) < 0.02 || Math.abs(py - 0.9) < 0.02) && (px * 20) % 1 < 0.25) feat = 0.5;
      } else if (kind === 3) {
        // label plate
        if (px > 0.1 && px < 0.45 && py > 0.65 && py < 0.8) feat = 0.15;
      }
      const base = (row === 0 ? 0.13 : 0.34 + pid * 0.06) + (n - 0.5) * 0.05;
      let r = base;
      let g = base * 1.02;
      let b = base * 1.05;
      if (kind === 3 && feat === 0.15) {
        r = 0.78;
        g = 0.74;
        b = 0.55;
      }
      const k = 1 - dark * 0.85 - sm * 0.5;
      L.height[i] = feat - sm;
      L.albedo[i * 3] = r * k;
      L.albedo[i * 3 + 1] = g * k;
      L.albedo[i * 3 + 2] = b * k;
      L.rough[i] = 0.45 + n * 0.2 + dark * 0.2;
    }
  }
  return bake(L, 10);
}

/** Dark technical ceiling plates with round vents, 2 m tile. */
export function techCeiling(seed = 41): PBRSet {
  const s = 512;
  const L = layers(s, s);
  for (let y = 0; y < s; y++) {
    const v = y / s;
    for (let x = 0; x < s; x++) {
      const u = x / s;
      const i = y * s + x;
      const pu = (u * 2) % 1;
      const pv = (v * 4) % 1;
      const sm = Math.max(seam(pu, 0.01), seam(pu - 1, 0.01), seam(pv, 0.02), seam(pv - 1, 0.02));
      const cell = hash2(Math.floor(u * 2), Math.floor(v * 4), seed);
      const vent = cell > 0.6 ? 1 - smooth(0.16, 0.2, Math.hypot(pu - 0.5, (pv - 0.5) * 0.5)) : 0;
      const ring = cell > 0.6 ? seam(Math.hypot(pu - 0.5, (pv - 0.5) * 0.5) - 0.2, 0.02) : 0;
      const slots = vent > 0 && (pu * 30) % 1 < 0.4 ? 1 : 0;
      const n = fbm(u, v, 6, 3, seed);
      L.height[i] = -sm - vent * slots * 0.5 + ring * 0.4;
      const c = (0.16 + cell * 0.04 + n * 0.03) * (1 - sm * 0.6) * (1 - vent * slots * 0.8);
      L.albedo[i * 3] = c;
      L.albedo[i * 3 + 1] = c * 1.02;
      L.albedo[i * 3 + 2] = c * 1.06;
      L.rough[i] = 0.5 + n * 0.2;
    }
  }
  return bake(L, 6);
}

/** Diamond tread deck plate, 1 m tile. */
export function diamondPlate(seed = 51): PBRSet {
  const s = 512;
  const L = layers(s, s);
  const k = 16;
  for (let y = 0; y < s; y++) {
    const v = y / s;
    for (let x = 0; x < s; x++) {
      const u = x / s;
      const i = y * s + x;
      const cu = (u * k) % 1;
      const cv = (v * k) % 1;
      const odd = (Math.floor(u * k) + Math.floor(v * k)) % 2 === 0;
      const du = cu - 0.5;
      const dv = cv - 0.5;
      const a = odd ? du + dv : du - dv;
      const bb = odd ? du - dv : du + dv;
      const lozenge = 1 - smooth(0.05, 0.08, Math.abs(a) * 0.35 + Math.abs(bb) * 1.6 - 0.12);
      const sm = Math.max(seam(u, 0.003), seam(u - 1, 0.003), seam(v, 0.003), seam(v - 1, 0.003));
      const wear = smooth(0.45, 0.75, fbm(u, v, 3, 4, seed));
      const n = fbm(u, v, 12, 3, seed + 2);
      L.height[i] = lozenge * 0.6 - sm;
      const c = 0.2 + n * 0.05 + wear * 0.08 + lozenge * wear * 0.1;
      L.albedo[i * 3] = c;
      L.albedo[i * 3 + 1] = c * 1.01;
      L.albedo[i * 3 + 2] = c * 1.03;
      L.rough[i] = 0.55 - lozenge * 0.15 - wear * 0.12 + sm * 0.2;
    }
  }
  return bake(L, 4);
}

/** Floor grating: bars over a dark void, 1 m tile. */
export function grating(seed = 61): PBRSet {
  const s = 512;
  const L = layers(s, s);
  for (let y = 0; y < s; y++) {
    const v = y / s;
    for (let x = 0; x < s; x++) {
      const u = x / s;
      const i = y * s + x;
      const bar = (u * 32) % 1 < 0.28 ? 1 : 0;
      const cross = (v * 10) % 1 < 0.1 ? 1 : 0;
      const solid = Math.max(bar, cross);
      const n = fbm(u, v, 8, 3, seed);
      L.height[i] = solid ? 0.6 + cross * 0.2 : -0.8;
      const c = solid ? 0.26 + n * 0.06 : 0.015;
      L.albedo[i * 3] = c;
      L.albedo[i * 3 + 1] = c * 1.02;
      L.albedo[i * 3 + 2] = c * 1.05;
      L.rough[i] = solid ? 0.4 + n * 0.2 : 0.9;
    }
  }
  return bake(L, 5);
}


/** Covenant-style corridor wall: dark gunmetal equipment band below, champagne-gold metallic
 *  panels (some ribbed) above, 2 m × 4 m tile with v = 0 at the deck. Metalness is per texel. */
export function metalPanels(seed = 71): PBRSet {
  const w = 512;
  const h = 1024;
  const L = layers(w, h);
  L.metal = new Float32Array(w * h);
  for (let y = 0; y < h; y++) {
    const v = y / h;
    const ym = v * 4;
    for (let x = 0; x < w; x++) {
      const u = x / w;
      const xm = u * 2;
      const i = y * w + x;
      const n = fbm(u, v, 8, 3, seed);
      const grain = vnoise(u * 6, v * 900, 6, seed + 3);
      let r = 0.1;
      let g = 0.1;
      let b = 0.1;
      let hgt = 0;
      let rough = 0.5;
      let metal = 0.5;
      if (ym < 0.12) {
        r = g = b = 0.07 + n * 0.03;
        hgt = -0.2;
        metal = 0.6;
      } else if (ym < 0.95) {
        const px = xm % 1.0;
        const py = ym - 0.12;
        const seamV = Math.max(seam(px, 0.006), seam(px - 1, 0.006));
        const seamH = Math.max(seam(ym - 0.12, 0.006), seam(ym - 0.95, 0.006));
        const vent = px > 0.12 && px < 0.5 && py > 0.3 && py < 0.56 && (py * 44) % 1 < 0.45 ? 1 : 0;
        let bolt = 0;
        for (const [bx, by] of [[0.04, 0.05], [0.96, 0.05], [0.04, 0.78], [0.96, 0.78]]) bolt = Math.max(bolt, 1 - smooth(0.004, 0.009, Math.hypot(px - bx, py - by)));
        const base = 0.13 + hash2(Math.floor(xm), 3, seed) * 0.03 + n * 0.03;
        r = base;
        g = base * 1.02;
        b = base * 1.05;
        hgt = -Math.max(seamV, seamH) - vent * 0.7 + bolt * 0.5;
        if (vent) r = g = b = 0.02;
        rough = 0.42 + n * 0.12;
        metal = 0.55;
      } else if (ym < 1.15 || (ym >= 2.25 && ym < 2.35)) {
        r = 0.09;
        g = 0.09;
        b = 0.1;
        hgt = -0.15;
        rough = 0.4;
        metal = 0.7;
      } else if (ym < 2.25) {
        // champagne-gold panels, two rows of 0.55 m, 1.0 m wide
        const row = ym < 1.7 ? 0 : 1;
        const y0 = row === 0 ? 1.15 : 1.7;
        const px = xm % 1.0;
        const py = (ym - y0) / 0.55;
        const col = Math.floor(xm);
        const pid = hash2(col, row, seed + 9);
        const seamAll = Math.max(seam(px, 0.005), seam(px - 1, 0.005), seam(py * 0.55, 0.005), seam((py - 1) * 0.55, 0.005));
        const bevel = Math.max(1 - smooth(0.0, 0.02, px), 1 - smooth(0.0, 0.02, 1 - px), 1 - smooth(0.0, 0.035, py), 1 - smooth(0.0, 0.035, 1 - py));
        const ribbed = pid > 0.55 ? Math.max(0, Math.sin(py * Math.PI * 2 * 9)) * 0.5 * (py > 0.12 && py < 0.88 ? 1 : 0) : 0;
        let rivet = 0;
        for (let k = 0; k < 8; k++) {
          const rx = 0.06 + k * 0.125;
          rivet = Math.max(rivet, 1 - smooth(0.003, 0.007, Math.hypot(px - rx, (py - 0.06) * 0.55)), 1 - smooth(0.003, 0.007, Math.hypot(px - rx, (py - 0.94) * 0.55)));
        }
        const label = pid < 0.12 && px > 0.62 && px < 0.9 && py > 0.62 && py < 0.8 ? 1 : 0;
        const tint = (pid - 0.5) * 0.05;
        r = 0.6 + tint + grain * 0.06 + n * 0.04;
        g = 0.53 + tint + grain * 0.05 + n * 0.035;
        b = 0.4 + tint * 0.8 + grain * 0.04 + n * 0.03;
        if (label) {
          r = 0.82;
          g = 0.8;
          b = 0.72;
        }
        const dark = seamAll * 0.75;
        r *= 1 - dark;
        g *= 1 - dark;
        b *= 1 - dark;
        hgt = -seamAll + bevel * 0.25 + ribbed + rivet * 0.4 + (grain - 0.5) * 0.04;
        rough = 0.28 + n * 0.12 + grain * 0.08 + seamAll * 0.3 - ribbed * 0.05;
        metal = label ? 0.1 : 0.9;
      } else {
        const sV = Math.max(seam(xm % 1.0, 0.006), seam((xm % 1.0) - 1, 0.006));
        r = g = b = 0.12 + n * 0.03;
        hgt = -sV;
        rough = 0.45;
        metal = 0.6;
      }
      L.height[i] = hgt;
      L.albedo[i * 3] = r;
      L.albedo[i * 3 + 1] = g;
      L.albedo[i * 3 + 2] = b;
      L.rough[i] = rough;
      L.metal[i] = metal;
    }
  }
  const set = bake(L, 10);
  set.metal = true;
  return set;
}

/** Vertical gradient for light cones (bright at the top, gone at the bottom). */
export function coneGradient(): THREE.Texture {
  const [c, x] = canvas(4, 256);
  const g = x.createLinearGradient(0, 0, 0, 256);
  g.addColorStop(0, 'rgba(255,255,255,0)');
  g.addColorStop(0.6, 'rgba(255,255,255,0.25)');
  g.addColorStop(1, 'rgba(255,255,255,1)');
  x.fillStyle = g;
  x.fillRect(0, 0, 4, 256);
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  return t;
}
