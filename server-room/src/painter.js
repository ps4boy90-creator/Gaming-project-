// Procedural PBR texture painter.
//
// Every shape is drawn into up to four canvases at once so one drawing call
// produces a matching set of maps:
//   c  albedo (sRGB)
//   h  height (grey, 0.5 = flush) -> converted to a tangent-space normal map
//   o  "ORM": R = 1, G = roughness, B = metalness (three.js reads G/B)
//   e  emissive (optional)
//
// A material spec is { c, h, r, m, e, a } — any key may be omitted to leave
// that layer untouched (e.g. { h: 0.2 } only carves the height map).

import * as THREE from 'three';

function makeCtx(w, h) {
  const canvas = document.createElement('canvas');
  canvas.width = w;
  canvas.height = h;
  return canvas.getContext('2d', { willReadFrequently: true });
}

const grey = (v) => {
  const n = Math.round(Math.max(0, Math.min(1, v)) * 255);
  return `rgb(${n},${n},${n})`;
};
const ormStyle = (r, m) =>
  `rgb(255,${Math.round(Math.max(0, Math.min(1, r)) * 255)},${Math.round(Math.max(0, Math.min(1, m)) * 255)})`;

export const FONT = 'Arial, Helvetica, sans-serif';

export class Painter {
  constructor(w, h, { base = '#808080', r = 0.6, m = 0, emissive = false } = {}) {
    this.w = w;
    this.h = h;
    this.L = { c: makeCtx(w, h), h: makeCtx(w, h), o: makeCtx(w, h) };
    if (emissive) this.L.e = makeCtx(w, h);
    this.L.c.fillStyle = base;
    this.L.c.fillRect(0, 0, w, h);
    this.L.h.fillStyle = grey(0.5);
    this.L.h.fillRect(0, 0, w, h);
    this.L.o.fillStyle = ormStyle(r, m);
    this.L.o.fillRect(0, 0, w, h);
    if (this.L.e) {
      this.L.e.fillStyle = '#000';
      this.L.e.fillRect(0, 0, w, h);
    }
    this.regions = {};
    this.cur = null;
  }

  // Draw `fn(ctx)` once per layer the material touches, with fillStyle preset.
  paint(mat, fn) {
    const { L } = this;
    const alpha = mat.a ?? 1;
    if (mat.c != null) {
      L.c.globalAlpha = alpha;
      L.c.fillStyle = mat.c;
      L.c.strokeStyle = mat.c;
      fn(L.c);
      L.c.globalAlpha = 1;
    }
    if (mat.h != null) {
      L.h.globalAlpha = mat.ha ?? 1;
      L.h.fillStyle = grey(mat.h);
      L.h.strokeStyle = grey(mat.h);
      fn(L.h);
      L.h.globalAlpha = 1;
    }
    if (mat.r != null) {
      L.o.globalAlpha = alpha;
      L.o.fillStyle = ormStyle(mat.r, mat.m ?? 0);
      L.o.strokeStyle = L.o.fillStyle;
      fn(L.o);
      L.o.globalAlpha = 1;
    }
    if (L.e && (mat.e != null || (mat.c != null && alpha >= 1))) {
      L.e.fillStyle = mat.e ?? '#000';
      L.e.strokeStyle = L.e.fillStyle;
      fn(L.e);
    }
  }

  rect(x, y, w, h, mat) {
    this.paint(mat, (c) => c.fillRect(x, y, w, h));
  }

  rrect(x, y, w, h, r, mat) {
    this.paint(mat, (c) => {
      c.beginPath();
      c.roundRect(x, y, w, h, r);
      c.fill();
    });
  }

  circle(x, y, r, mat) {
    this.paint(mat, (c) => {
      c.beginPath();
      c.arc(x, y, r, 0, Math.PI * 2);
      c.fill();
    });
  }

  poly(pts, mat) {
    this.paint(mat, (c) => {
      c.beginPath();
      c.moveTo(pts[0][0], pts[0][1]);
      for (let i = 1; i < pts.length; i++) c.lineTo(pts[i][0], pts[i][1]);
      c.closePath();
      c.fill();
    });
  }

  line(x0, y0, x1, y1, width, mat) {
    this.paint(mat, (c) => {
      c.lineWidth = width;
      c.lineCap = 'round';
      c.beginPath();
      c.moveTo(x0, y0);
      c.lineTo(x1, y1);
      c.stroke();
    });
  }

  strokeRect(x, y, w, h, width, mat) {
    this.paint(mat, (c) => {
      c.lineWidth = width;
      c.strokeRect(x + width / 2, y + width / 2, w - width, h - width);
    });
  }

  text(str, x, y, size, mat, { weight = 700, align = 'left', font = FONT, spacing = 0 } = {}) {
    this.paint(mat, (c) => {
      c.font = `${weight} ${size}px ${font}`;
      c.textAlign = align;
      c.textBaseline = 'middle';
      if (spacing && 'letterSpacing' in c) c.letterSpacing = `${spacing}px`;
      c.fillText(str, x, y);
      if (spacing && 'letterSpacing' in c) c.letterSpacing = '0px';
    });
  }

  // Many circles in one path per layer — used for perforations and vents.
  holes(points, r, mat) {
    this.paint(mat, (c) => {
      c.beginPath();
      for (const [x, y] of points) {
        c.moveTo(x + r, y);
        c.arc(x, y, r, 0, Math.PI * 2);
      }
      c.fill();
    });
  }

  hexGrid(x, y, w, h, pitch, r, mat) {
    const pts = [];
    const dy = pitch * 0.866;
    let row = 0;
    for (let yy = y + r + 1; yy <= y + h - r - 1; yy += dy, row++) {
      const off = (row % 2) * pitch * 0.5;
      for (let xx = x + r + 1 + off; xx <= x + w - r - 1; xx += pitch) pts.push([xx, yy]);
    }
    this.holes(pts, r, mat);
  }

  // Per-pixel albedo/roughness variation so flat paint doesn't read as CG.
  grain(x, y, w, h, amount, { rough = 0, seed = 1, scale = 1 } = {}) {
    x = Math.max(0, Math.floor(x));
    y = Math.max(0, Math.floor(y));
    w = Math.min(this.w - x, Math.ceil(w));
    h = Math.min(this.h - y, Math.ceil(h));
    if (w <= 0 || h <= 0) return;
    let s = seed * 9301 + 49297;
    const rnd = () => ((s = (s * 16807) % 2147483647) / 2147483647);
    const img = this.L.c.getImageData(x, y, w, h);
    const d = img.data;
    const orm = rough ? this.L.o.getImageData(x, y, w, h) : null;
    for (let j = 0; j < h; j++) {
      for (let i = 0; i < w; i++) {
        const k = (j * w + i) * 4;
        const n = (rnd() - 0.5) * 2 * amount * 255 * scale;
        d[k] += n;
        d[k + 1] += n;
        d[k + 2] += n;
        if (orm) orm.data[k + 1] += (rnd() - 0.5) * 2 * rough * 255;
      }
    }
    this.L.c.putImageData(img, x, y);
    if (orm) this.L.o.putImageData(orm, x, y);
  }

  // ---- region bookkeeping for atlases ----------------------------------
  region(name, x, y, w, h) {
    const r = {
      name, x, y, w, h,
      // canvas textures are flipped, so v runs bottom-up in UV space
      uv: [x / this.w, 1 - (y + h) / this.h, w / this.w, h / this.h],
      leds: [],
      anchors: [],
    };
    this.regions[name] = r;
    this.cur = r;
    return r;
  }

  // Register an indicator LED at canvas coords; kind drives its animation.
  // Port LEDs (link/act) belong to the most recently registered anchor, so a
  // port that ends up without a cable can keep its LEDs dark.
  led(x, y, kind = 'pwr', color = 'green', lens = true) {
    const r = this.cur;
    if (lens) this.circle(x, y, 3, { c: '#1d2421', h: 0.6, r: 0.15, m: 0 });
    const port = kind === 'link' || kind === 'act' || kind === 'psu' ? r.anchors.length - 1 : -1;
    r.leds.push({ u: (x - r.x) / r.w, v: (y - r.y) / r.h, kind, color, port });
  }

  // Register a cable attachment point (port, inlet...).
  anchor(x, y, type, extra = {}) {
    const r = this.cur;
    r.anchors.push({ u: (x - r.x) / r.w, v: (y - r.y) / r.h, type, ...extra });
  }

  // ---- output ----------------------------------------------------------
  textures({ normalStrength = 3, blur = 1, anisotropy = 8, repeat = null, mipmaps = true } = {}) {
    const mk = (canvas, srgb) => {
      const t = new THREE.CanvasTexture(canvas);
      t.colorSpace = srgb ? THREE.SRGBColorSpace : THREE.NoColorSpace;
      t.anisotropy = anisotropy;
      t.generateMipmaps = mipmaps;
      t.minFilter = mipmaps ? THREE.LinearMipmapLinearFilter : THREE.LinearFilter;
      if (repeat) {
        t.wrapS = t.wrapT = THREE.RepeatWrapping;
        t.repeat.set(repeat[0], repeat[1]);
      }
      return t;
    };
    const out = {
      map: mk(this.L.c.canvas, true),
      normalMap: mk(normalFromHeight(this.L.h, normalStrength, blur, !!repeat), false),
      ormMap: mk(this.L.o.canvas, false),
    };
    if (this.L.e) out.emissiveMap = mk(this.L.e.canvas, true);
    return out;
  }
}

// Height canvas -> tangent-space normal map canvas.
export function normalFromHeight(ctx, strength = 3, blur = 1, wrap = false) {
  const { width: w, height: h } = ctx.canvas;
  const src = ctx.getImageData(0, 0, w, h).data;
  let hgt = new Float32Array(w * h);
  for (let i = 0; i < w * h; i++) hgt[i] = src[i * 4] / 255;
  for (let pass = 0; pass < blur; pass++) hgt = boxBlur(hgt, w, h, wrap);

  const out = document.createElement('canvas');
  out.width = w;
  out.height = h;
  const octx = out.getContext('2d');
  const img = octx.createImageData(w, h);
  const d = img.data;
  const at = wrap
    ? (x, y) => hgt[((y + h) % h) * w + ((x + w) % w)]
    : (x, y) => hgt[Math.min(h - 1, Math.max(0, y)) * w + Math.min(w - 1, Math.max(0, x))];
  for (let y = 0; y < h; y++) {
    for (let x = 0; x < w; x++) {
      const dx = (at(x + 1, y) - at(x - 1, y)) * strength;
      const dy = (at(x, y + 1) - at(x, y - 1)) * strength;
      // canvas y points down while texture v points up
      let nx = -dx, ny = dy, nz = 1;
      const len = Math.hypot(nx, ny, nz);
      nx /= len; ny /= len; nz /= len;
      const k = (y * w + x) * 4;
      d[k] = (nx * 0.5 + 0.5) * 255;
      d[k + 1] = (ny * 0.5 + 0.5) * 255;
      d[k + 2] = (nz * 0.5 + 0.5) * 255;
      d[k + 3] = 255;
    }
  }
  octx.putImageData(img, 0, 0);
  return out;
}

function boxBlur(src, w, h, wrap) {
  const tmp = new Float32Array(w * h);
  const out = new Float32Array(w * h);
  const cx = wrap ? (x) => (x + w) % w : (x) => Math.min(w - 1, Math.max(0, x));
  const cy = wrap ? (y) => (y + h) % h : (y) => Math.min(h - 1, Math.max(0, y));
  for (let y = 0; y < h; y++) {
    const row = y * w;
    for (let x = 0; x < w; x++) {
      tmp[row + x] = (src[row + cx(x - 1)] + src[row + x] + src[row + cx(x + 1)]) / 3;
    }
  }
  for (let y = 0; y < h; y++) {
    const up = cy(y - 1) * w, dn = cy(y + 1) * w, row = y * w;
    for (let x = 0; x < w; x++) out[row + x] = (tmp[up + x] + tmp[row + x] + tmp[dn + x]) / 3;
  }
  return out;
}

// Build a MeshStandardMaterial from painter output.
export function pbr(tex, extra = {}) {
  const mat = new THREE.MeshStandardMaterial({
    map: tex.map,
    normalMap: tex.normalMap,
    roughnessMap: tex.ormMap,
    metalnessMap: tex.ormMap,
    roughness: 1,
    metalness: 1,
    ...extra,
  });
  if (tex.emissiveMap) {
    mat.emissiveMap = tex.emissiveMap;
    mat.emissive = new THREE.Color(0xffffff);
  }
  return mat;
}
