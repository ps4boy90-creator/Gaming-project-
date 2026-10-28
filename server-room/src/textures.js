// Procedural surface textures for everything that isn't a device faceplate.
import * as THREE from 'three';
import { Painter, FONT } from './painter.js';
import { Rng } from './util.js';

// Raised-floor tile, 2×2 tiles per texture (1.2 m) so repetition is less obvious.
export function floorTiles() {
  const S = 1024, T = 512;
  const p = new Painter(S, S, { base: '#b4b7b9', r: 0.42, m: 0 });
  const rng = new Rng(7);
  for (let ty = 0; ty < 2; ty++) {
    for (let tx = 0; tx < 2; tx++) {
      const x = tx * T, y = ty * T;
      const tint = rng.range(-6, 6);
      const c = Math.round(178 + tint);
      p.rect(x, y, T, T, { c: `rgb(${c},${c + 3},${c + 5})`, h: 0.5, r: rng.range(0.36, 0.46), m: 0 });
      // speckled high-pressure laminate
      const flecks = [];
      for (let i = 0; i < 1400; i++) flecks.push([x + rng.range(4, T - 4), y + rng.range(4, T - 4)]);
      p.holes(flecks.slice(0, 700), 0.9, { c: '#8d9195', a: 0.55 });
      p.holes(flecks.slice(700), 0.8, { c: '#d6d9db', a: 0.5 });
      // scuffs and traffic wear
      for (let i = 0; i < 5; i++) {
        p.circle(x + rng.range(40, T - 40), y + rng.range(40, T - 40), rng.range(18, 70), { c: '#7d8084', a: 0.05, r: 0.55, m: 0 });
      }
      for (let i = 0; i < 6; i++) {
        const sx = x + rng.range(30, T - 30), sy = y + rng.range(30, T - 30);
        p.line(sx, sy, sx + rng.range(-60, 60), sy + rng.range(-12, 12), rng.range(1, 2.5), { c: '#55585c', a: 0.12 });
      }
      // PVC edge band and the joint between tiles
      p.strokeRect(x, y, T, T, 6, { c: '#3d4043', h: 0.42, r: 0.6, m: 0 });
      p.strokeRect(x, y, T, T, 2, { c: '#141516', h: 0.2, r: 0.9, m: 0 });
    }
  }
  p.grain(0, 0, S, S, 0.02, { rough: 0.04, seed: 3 });
  return p.textures({ normalStrength: 2.5, blur: 1, repeat: [1, 1] });
}

// 25% open-area perforated airflow tile.
export function perfTile() {
  const S = 512;
  const p = new Painter(S, S, { base: '#9a9fa4', r: 0.38, m: 0.8 });
  p.grain(0, 0, S, S, 0.03, { rough: 0.08, seed: 9 });
  const pts = [];
  const pitch = 20.5;
  for (let y = 34; y < S - 30; y += pitch) for (let x = 34; x < S - 30; x += pitch) pts.push([x, y]);
  p.holes(pts, 5.8, { c: '#0b0c0d', h: 0.1, r: 0.95, m: 0 });
  // damper blades visible through holes
  p.holes(pts.filter((_, i) => i % 3 === 0), 2.5, { c: '#24272a', a: 0.6 });
  p.strokeRect(0, 0, S, S, 6, { c: '#3d4043', h: 0.42, r: 0.6, m: 0 });
  p.strokeRect(0, 0, S, S, 2, { c: '#141516', h: 0.2, r: 0.9, m: 0 });
  p.strokeRect(14, 14, S - 28, S - 28, 3, { h: 0.6 });
  return p.textures({ normalStrength: 3, blur: 1, repeat: [1, 1] });
}

// Mineral-fibre ceiling tile in a white T-bar grid.
export function ceilingTile() {
  const S = 512;
  const p = new Painter(S, S, { base: '#dcdcd7', r: 0.92, m: 0 });
  const rng = new Rng(31);
  // fissures and pinholes
  for (let i = 0; i < 500; i++) {
    const x = rng.range(10, S - 10), y = rng.range(10, S - 10);
    const len = rng.range(2, 9), a = rng.range(0, Math.PI * 2);
    p.line(x, y, x + Math.cos(a) * len, y + Math.sin(a) * len, rng.range(0.8, 1.8), { c: '#a9a9a3', h: 0.35, a: 0.6 });
  }
  const pins = [];
  for (let i = 0; i < 2200; i++) pins.push([rng.range(8, S - 8), rng.range(8, S - 8)]);
  p.holes(pins, 0.9, { c: '#b9b9b3', h: 0.4, a: 0.7 });
  p.grain(0, 0, S, S, 0.025, { seed: 33 });
  // T-bar (white enamel) and tegular reveal
  p.strokeRect(0, 0, S, S, 14, { c: '#c9c9c4', h: 0.3, r: 0.8, m: 0 });
  p.strokeRect(0, 0, S, S, 9, { c: '#f1f1ee', h: 0.85, r: 0.35, m: 0.2 });
  p.strokeRect(0, 0, S, S, 2, { c: '#d8d8d4', h: 0.9 });
  return p.textures({ normalStrength: 2, blur: 1, repeat: [1, 1] });
}

// Painted drywall with orange-peel texture.
export function wallPaint() {
  const S = 512;
  const p = new Painter(S, S, { base: '#cfd2d1', r: 0.86, m: 0 });
  const rng = new Rng(41);
  for (let i = 0; i < 70; i++) {
    p.circle(rng.range(0, S), rng.range(0, S), rng.range(30, 110), { c: rng.chance(0.5) ? '#c6c9c8' : '#d6d9d8', a: 0.08 });
  }
  const bumps = [];
  for (let i = 0; i < 9000; i++) bumps.push([rng.range(0, S), rng.range(0, S)]);
  p.holes(bumps, 1.6, { h: 0.58, ha: 0.5 });
  p.grain(0, 0, S, S, 0.012, { seed: 43 });
  return p.textures({ normalStrength: 1.2, blur: 2, repeat: [1, 1] });
}

// Black powder-coat (fine orange peel) for rack frames, doors, cabinets.
export function powderCoat(color = '#141517', seed = 51) {
  const S = 256;
  const p = new Painter(S, S, { base: color, r: 0.5, m: 0.05 });
  const rng = new Rng(seed);
  const bumps = [];
  for (let i = 0; i < 5000; i++) bumps.push([rng.range(0, S), rng.range(0, S)]);
  p.holes(bumps, 1.2, { h: 0.6, ha: 0.45 });
  p.grain(0, 0, S, S, 0.015, { rough: 0.06, seed });
  return p.textures({ normalStrength: 1.5, blur: 1, repeat: [6, 6] });
}

// Front face of a vertical mounting rail: 42U of square holes with U numbers.
export function rackPost() {
  const PU = 64, H = PU * 42, Wd = 64;
  const p = new Painter(Wd, H, { base: '#2c2e31', r: 0.45, m: 0.2 });
  p.grain(0, 0, Wd, H, 0.02, { seed: 61 });
  const mm = PU / 44.45;
  for (let u = 0; u < 42; u++) {
    const y0 = H - (u + 1) * PU; // canvas y of the top of this U
    for (const off of [6.35, 22.225, 38.1]) {
      const cy = y0 + PU - off * mm;
      p.rect(Wd - 30, cy - 3.6 * mm, 9.5 * mm, 9.5 * mm, { c: '#020203', h: 0.1, r: 1, m: 0 });
    }
    p.rect(0, y0, Wd, 1, { c: '#2a2c30', h: 0.45 });
    p.text(String(u + 1), 16, y0 + PU / 2, 15, { c: '#c9ccd0', r: 0.6, m: 0 }, { align: 'center', weight: 700 });
  }
  return p.textures({ normalStrength: 2, blur: 1 });
}

// Hexagonal perforation for rack doors: white = metal, black = hole.
export function doorPerforation() {
  const Wd = 128, H = 111;
  const c = document.createElement('canvas');
  c.width = Wd; c.height = H;
  const ctx = c.getContext('2d');
  ctx.fillStyle = '#fff';
  ctx.fillRect(0, 0, Wd, H);
  ctx.fillStyle = '#000';
  const pitch = 32, dy = 27.75;
  for (let row = -1; row <= 4; row++) {
    for (let col = -1; col <= 4; col++) {
      const x = col * pitch + (row % 2 ? pitch / 2 : 0), y = row * dy;
      ctx.beginPath();
      for (let k = 0; k < 6; k++) {
        const a = Math.PI / 6 + (k * Math.PI) / 3;
        const px = x + Math.cos(a) * 14.2, py = y + Math.sin(a) * 14.2;
        k ? ctx.lineTo(px, py) : ctx.moveTo(px, py);
      }
      ctx.closePath();
      ctx.fill();
    }
  }
  const t = new THREE.CanvasTexture(c);
  t.wrapS = t.wrapT = THREE.RepeatWrapping;
  t.anisotropy = 8;
  t.colorSpace = THREE.NoColorSpace;
  return t;
}

// Vertical 0U PDU face: LCD, breakers, 24×C13 + 6×C19 outlets.
export function pduFace(feed = 'A') {
  const Wd = 128, H = 2048;
  const p = new Painter(Wd, H, { base: '#2b2c2f', r: 0.5, m: 0.1, emissive: true });
  p.grain(0, 0, Wd, H, 0.015, { seed: 71 });
  p.rect(10, 20, 108, 120, { c: '#0e0f10', h: 0.6, r: 0.4, m: 0 });
  p.rect(22, 34, 84, 46, { c: '#1a0606', e: '#2a0505', h: 0.6, r: 0.15, m: 0 });
  p.text(feed === 'A' ? '7.4' : '6.9', 64, 58, 30, { c: '#ff4a3a', e: '#ff3b2a' }, { align: 'center', font: 'monospace' });
  p.circle(40, 108, 7, { c: '#2f3236', h: 0.7 });
  p.circle(88, 108, 7, { c: '#2f3236', h: 0.7 });
  p.text(`FEED ${feed}`, 64, 160, 14, { c: '#c4c8cc', r: 0.6, m: 0 }, { align: 'center' });
  let y = 190;
  for (let g = 0; g < 4; g++) {
    p.rect(14, y, 100, 36, { c: '#1f2124', h: 0.62 });
    p.rect(40, y + 8, 48, 20, { c: '#090a0b', h: 0.7 });
    y += 52;
    for (let i = 0; i < 6; i++) {
      // portrait C13
      p.rect(36, y, 56, 62, { c: '#0f1011', h: 0.6, r: 0.6, m: 0 });
      p.rect(43, y + 6, 42, 50, { c: '#1a1b1d', h: 0.5 });
      p.rect(52, y + 14, 8, 6, { c: '#020203', h: 0.05 });
      p.rect(52, y + 38, 8, 6, { c: '#020203', h: 0.05 });
      p.rect(70, y + 25, 6, 8, { c: '#020203', h: 0.05 });
      y += 70;
    }
    p.rect(30, y, 68, 72, { c: '#0f1011', h: 0.6, r: 0.6, m: 0 });
    p.rect(38, y + 8, 52, 56, { c: '#1a1b1d', h: 0.5 });
    p.rect(48, y + 20, 7, 14, { c: '#020203', h: 0.05 });
    p.rect(72, y + 20, 7, 14, { c: '#020203', h: 0.05 });
    y += 84;
  }
  p.rect(0, 0, Wd, 6, { h: 0.7 });
  p.rect(0, H - 6, Wd, 6, { h: 0.3 });
  return p.textures({ normalStrength: 3, blur: 1 });
}

// Rack ID labels in a single atlas; returns uv rects per label.
export function labelAtlas(ids) {
  const CW = 128, CH = 48, cols = 8;
  const rows = Math.ceil(ids.length / cols);
  const Wd = CW * cols, H = 64 * Math.ceil((rows * CH) / 64);
  const c = document.createElement('canvas');
  c.width = Wd; c.height = H;
  const ctx = c.getContext('2d');
  ctx.fillStyle = '#111';
  ctx.fillRect(0, 0, Wd, H);
  const rects = {};
  ids.forEach((id, i) => {
    const x = (i % cols) * CW, y = Math.floor(i / cols) * CH;
    ctx.fillStyle = '#efeee8';
    ctx.fillRect(x + 2, y + 2, CW - 4, CH - 4);
    ctx.fillStyle = '#111';
    ctx.font = `800 30px ${FONT}`;
    ctx.textBaseline = 'middle';
    ctx.fillText(id, x + 10, y + CH / 2 + 1);
    // little barcode for asset tracking
    for (let k = 0; k < 18; k++) {
      const bw = ((id.charCodeAt(k % id.length) * (k + 3)) % 3) + 1;
      ctx.fillRect(x + 78 + k * 2.4, y + 10, bw * 0.8, CH - 20);
    }
    rects[id] = [x / Wd, 1 - (y + CH) / H, CW / Wd, CH / H];
  });
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  t.anisotropy = 8;
  return { texture: t, rects };
}

// Generic printed sign. draw(ctx, w, h) paints it; returns a material.
export function signMaterial(w, h, draw, { emissive = 0, rough = 0.55 } = {}) {
  const c = document.createElement('canvas');
  c.width = w; c.height = h;
  const ctx = c.getContext('2d');
  draw(ctx, w, h);
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  t.anisotropy = 8;
  const mat = new THREE.MeshStandardMaterial({ map: t, roughness: rough, metalness: 0 });
  if (emissive) {
    mat.emissiveMap = t;
    mat.emissive = new THREE.Color(0xffffff);
    mat.emissiveIntensity = emissive;
  }
  return mat;
}

// Downflow CRAC unit front: three service panels, louvres, controller display.
export function cracFace(name, supply, ret) {
  const Wd = 1024, H = 800; // 2.5 m × 1.95 m
  const p = new Painter(Wd, H, { base: '#d8d6cf', r: 0.5, m: 0.1, emissive: true });
  p.grain(0, 0, Wd, H, 0.015, { rough: 0.04, seed: 81 });
  const pw = Wd / 3;
  for (let i = 0; i < 3; i++) {
    const x = i * pw;
    p.strokeRect(x, 0, pw, H, 4, { c: '#9c9a94', h: 0.25, r: 0.7, m: 0 });
    // louvred return-air sections on the outer panels
    if (i !== 1) for (let y = 60; y < 330; y += 16) p.rect(x + 28, y, pw - 56, 7, { c: '#8f8d87', h: 0.3, r: 0.7, m: 0 });
    // quarter-turn latches
    for (const ly of [400, 700]) {
      p.circle(x + pw - 30, ly, 11, { c: '#2a2b2d', h: 0.7, r: 0.4, m: 0.3 });
      p.rect(x + pw - 31.5, ly - 8, 3, 16, { c: '#111', h: 0.4 });
    }
    p.rrect(x + pw / 2 - 50, 640, 100, 18, 8, { c: '#bdbbb4', h: 0.35 });
  }
  // controller at eye level on the centre panel
  p.rect(pw + 60, 170, pw - 120, 170, { c: '#2c2d30', h: 0.65, r: 0.4, m: 0 });
  p.rect(pw + 76, 184, pw - 152, 104, { c: '#0a1420', e: '#0c1a2a', h: 0.66, r: 0.1, m: 0 });
  const ink = { c: '#9fd7ff', e: '#86ccff' };
  p.text(name, pw + 88, 202, 15, ink, { font: 'monospace' });
  p.text(`SUPPLY  ${supply.toFixed(1)}°C`, pw + 88, 230, 17, ink, { font: 'monospace' });
  p.text(`RETURN  ${ret.toFixed(1)}°C`, pw + 88, 254, 17, ink, { font: 'monospace' });
  p.text('FAN 68%  RH 46%', pw + 88, 276, 13, { c: '#6fb8ea', e: '#5aa8e0' }, { font: 'monospace' });
  for (let i = 0; i < 5; i++) p.circle(pw + 100 + i * 46, 314, 9, { c: '#4a4c50', h: 0.75, r: 0.5, m: 0 });
  p.text('PRECISION COOLING  ·  DX-70', Wd / 2, 420, 15, { c: '#5b5a56', r: 0.6, m: 0 }, { align: 'center' });
  p.rect(0, H - 34, Wd, 34, { c: '#3a3a3c', h: 0.4, r: 0.6, m: 0.2 });
  return p.textures({ normalStrength: 2.5, blur: 1 });
}

// Grille texture for the CRAC top / return-air grilles (egg-crate).
export function eggCrate() {
  const S = 256;
  const p = new Painter(S, S, { base: '#e8e8e4', r: 0.5, m: 0.4 });
  for (let y = 0; y < S; y += 16) for (let x = 0; x < S; x += 16) p.rect(x + 2, y + 2, 12, 12, { c: '#191a1b', h: 0.05, r: 0.95, m: 0 });
  p.strokeRect(0, 0, S, S, 6, { c: '#f2f2ef', h: 0.8 });
  return p.textures({ normalStrength: 2, blur: 1 });
}
