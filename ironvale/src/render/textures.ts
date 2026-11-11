import * as THREE from 'three';
import { RNG } from '../core/util';

/** Procedural canvas textures. Each texture spans `span` world tiles. */
export interface FloorTex {
  tex: THREE.Texture;
  span: number;
  rough: number;
}

function mk(size: number): [HTMLCanvasElement, CanvasRenderingContext2D] {
  const c = document.createElement('canvas');
  c.width = c.height = size;
  return [c, c.getContext('2d')!];
}

function finish(c: HTMLCanvasElement, aniso = 8): THREE.Texture {
  const t = new THREE.CanvasTexture(c);
  t.wrapS = t.wrapT = THREE.RepeatWrapping;
  t.colorSpace = THREE.SRGBColorSpace;
  t.anisotropy = aniso;
  t.generateMipmaps = true;
  t.minFilter = THREE.LinearMipmapLinearFilter;
  return t;
}

function rgb(hex: number, mul = 1): string {
  const r = Math.min(255, ((hex >> 16) & 255) * mul) | 0;
  const g = Math.min(255, ((hex >> 8) & 255) * mul) | 0;
  const b = Math.min(255, (hex & 255) * mul) | 0;
  return `rgb(${r},${g},${b})`;
}

/** wrap-around soft speckle noise */
function speckle(ctx: CanvasRenderingContext2D, size: number, r: RNG, count: number, minR: number, maxR: number, colors: string[], alpha: number) {
  ctx.globalAlpha = alpha;
  for (let i = 0; i < count; i++) {
    const x = r.next() * size, y = r.next() * size, rad = r.range(minR, maxR);
    ctx.fillStyle = r.pick(colors);
    for (const ox of [-size, 0, size])
      for (const oy of [-size, 0, size]) {
        if (x + ox + rad < 0 || x + ox - rad > size || y + oy + rad < 0 || y + oy - rad > size) continue;
        ctx.beginPath();
        ctx.arc(x + ox, y + oy, rad, 0, Math.PI * 2);
        ctx.fill();
      }
  }
  ctx.globalAlpha = 1;
}

export function makeFloorTextures(): Record<string, FloorTex> {
  const out: Record<string, FloorTex> = {};
  const r = new RNG(77);

  // ---- grass (lawn inside the plot)
  {
    const S = 512, [c, x] = mk(S);
    x.fillStyle = rgb(0x6fa653);
    x.fillRect(0, 0, S, S);
    speckle(x, S, r, 260, 14, 46, [rgb(0x79b25b), rgb(0x669c4d), rgb(0x74ab57)], 0.35);
    speckle(x, S, r, 2600, 0.8, 2.2, [rgb(0x86bf66), rgb(0x5c9146), rgb(0x8fc470)], 0.5);
    out.grass = { tex: finish(c), span: 8, rough: 0.95 };
  }
  // ---- wild grass (outside the plot)
  {
    const S = 512, [c, x] = mk(S);
    x.fillStyle = rgb(0x5f964a);
    x.fillRect(0, 0, S, S);
    speckle(x, S, r, 300, 16, 60, [rgb(0x6aa350), rgb(0x578c44), rgb(0x64994c), rgb(0x709f4e)], 0.4);
    speckle(x, S, r, 3200, 0.8, 2.4, [rgb(0x7bb55d), rgb(0x4f8340), rgb(0x86b862)], 0.5);
    out.wild = { tex: finish(c), span: 10, rough: 0.95 };
  }
  // ---- dirt
  {
    const S = 512, [c, x] = mk(S);
    x.fillStyle = rgb(0xa68662);
    x.fillRect(0, 0, S, S);
    speckle(x, S, r, 220, 12, 40, [rgb(0xb09069), rgb(0x9a7b59), rgb(0xa98a66)], 0.4);
    speckle(x, S, r, 1800, 0.8, 2.6, [rgb(0x8c6f50), rgb(0xbb9c76), rgb(0x7f6447)], 0.5);
    out.dirt = { tex: finish(c), span: 6, rough: 0.98 };
  }
  // ---- concrete: 2x2 tile slabs
  {
    const S = 512, [c, x] = mk(S);
    x.fillStyle = rgb(0xb9bbb8);
    x.fillRect(0, 0, S, S);
    speckle(x, S, r, 120, 20, 70, [rgb(0xc2c4c0), rgb(0xb0b2af), rgb(0xbdbfbb)], 0.35);
    speckle(x, S, r, 2400, 0.6, 1.6, [rgb(0xa4a6a3), rgb(0xcfd1cd)], 0.5);
    x.strokeStyle = 'rgba(70,74,78,0.55)';
    x.lineWidth = 3;
    for (let i = 0; i <= 2; i++) {
      x.beginPath(); x.moveTo(i * 256, 0); x.lineTo(i * 256, S); x.stroke();
      x.beginPath(); x.moveTo(0, i * 256); x.lineTo(S, i * 256); x.stroke();
    }
    out.concrete = { tex: finish(c), span: 4, rough: 0.9 };
  }
  // ---- sealed concrete (dark, 1 tile joints)
  {
    const S = 512, [c, x] = mk(S);
    x.fillStyle = rgb(0x6f7b86);
    x.fillRect(0, 0, S, S);
    speckle(x, S, r, 140, 20, 80, [rgb(0x76838e), rgb(0x68747f), rgb(0x717e89)], 0.4);
    speckle(x, S, r, 1500, 0.6, 1.4, [rgb(0x808d98), rgb(0x5f6b75)], 0.4);
    x.strokeStyle = 'rgba(40,46,54,0.5)';
    x.lineWidth = 2.5;
    for (let i = 0; i <= 4; i++) {
      x.beginPath(); x.moveTo(i * 128, 0); x.lineTo(i * 128, S); x.stroke();
      x.beginPath(); x.moveTo(0, i * 128); x.lineTo(S, i * 128); x.stroke();
    }
    out.polished = { tex: finish(c), span: 4, rough: 0.55 };
  }
  // ---- white tile: 2 tiles per world tile
  {
    const S = 512, n = 8, t = S / n, [c, x] = mk(S);
    x.fillStyle = rgb(0xc3cbcf);
    x.fillRect(0, 0, S, S);
    for (let i = 0; i < n; i++)
      for (let j = 0; j < n; j++) {
        const v = r.range(0.96, 1.03);
        x.fillStyle = rgb(0xe9eef0, v);
        x.fillRect(i * t + 2, j * t + 2, t - 4, t - 4);
      }
    out.tile = { tex: finish(c), span: 4, rough: 0.35 };
  }
  // ---- checker
  {
    const S = 512, n = 8, t = S / n, [c, x] = mk(S);
    x.fillStyle = rgb(0x9aa0a3);
    x.fillRect(0, 0, S, S);
    for (let i = 0; i < n; i++)
      for (let j = 0; j < n; j++) {
        const v = r.range(0.96, 1.04);
        x.fillStyle = (i + j) % 2 ? rgb(0xe6e2d6, v) : rgb(0x5d6a75, v);
        x.fillRect(i * t + 1.5, j * t + 1.5, t - 3, t - 3);
      }
    out.checker = { tex: finish(c), span: 4, rough: 0.4 };
  }
  // ---- wood planks (run along X)
  {
    const S = 512, rows = 16, h = S / rows, [c, x] = mk(S);
    for (let j = 0; j < rows; j++) {
      let px = -r.range(0, 200);
      while (px < S) {
        const len = r.range(140, 300);
        x.fillStyle = rgb(r.pick([0xb78455, 0xa97748, 0xc08f5f, 0xb07d4e, 0x9f6f43]), r.range(0.95, 1.05));
        x.fillRect(px, j * h, len, h);
        x.fillStyle = 'rgba(60,35,15,0.5)';
        x.fillRect(px, j * h, 2, h);
        px += len;
      }
      x.fillStyle = 'rgba(60,35,15,0.45)';
      x.fillRect(0, j * h, S, 1.5);
    }
    x.globalAlpha = 0.06;
    for (let i = 0; i < 300; i++) {
      x.fillStyle = r.chance(0.5) ? '#000' : '#fff';
      x.fillRect(r.next() * S, r.next() * S, r.range(20, 90), 1);
    }
    x.globalAlpha = 1;
    out.wood = { tex: finish(c), span: 4, rough: 0.6 };
  }
  // ---- carpet
  {
    const S = 256, [c, x] = mk(S);
    x.fillStyle = rgb(0x4d6788);
    x.fillRect(0, 0, S, S);
    speckle(x, S, r, 5000, 0.5, 1.2, [rgb(0x587394), rgb(0x435c7b), rgb(0x5f7b9c)], 0.6);
    out.carpet = { tex: finish(c), span: 2, rough: 1 };
  }
  // ---- asphalt
  {
    const S = 512, [c, x] = mk(S);
    x.fillStyle = rgb(0x4a4e54);
    x.fillRect(0, 0, S, S);
    speckle(x, S, r, 120, 20, 70, [rgb(0x50545a), rgb(0x44484e)], 0.4);
    speckle(x, S, r, 5000, 0.5, 1.5, [rgb(0x5c6066), rgb(0x3a3e43), rgb(0x666a70)], 0.6);
    out.asphalt = { tex: finish(c), span: 6, rough: 0.95 };
  }
  // ---- paving: brick-bond stone blocks, 2 per tile
  {
    const S = 512, rows = 8, h = S / rows, [c, x] = mk(S);
    x.fillStyle = rgb(0x8d8a82);
    x.fillRect(0, 0, S, S);
    for (let j = 0; j < rows; j++) {
      const off = j % 2 ? h : 0;
      for (let i = -1; i < 5; i++) {
        x.fillStyle = rgb(r.pick([0xc2bdb0, 0xb7b2a5, 0xcac5b8, 0xbdb7a8]), r.range(0.96, 1.04));
        x.fillRect(i * h * 2 + off + 2, j * h + 2, h * 2 - 4, h - 4);
      }
    }
    speckle(x, S, r, 1500, 0.6, 1.5, [rgb(0xa6a195), rgb(0xd4cfc2)], 0.35);
    out.paving = { tex: finish(c), span: 4, rough: 0.9 };
  }
  // ---- sports court
  {
    const S = 256, [c, x] = mk(S);
    x.fillStyle = rgb(0x3f8f8a);
    x.fillRect(0, 0, S, S);
    speckle(x, S, r, 3000, 0.5, 1.3, [rgb(0x479a95), rgb(0x38837f)], 0.5);
    out.court = { tex: finish(c), span: 2, rough: 0.8 };
  }
  // ---- road asphalt with dashed centre line (spans 8 along, 4 across)
  {
    const W = 512, H = 256, c = document.createElement('canvas');
    c.width = W; c.height = H;
    const x = c.getContext('2d')!;
    x.fillStyle = rgb(0x3f4349);
    x.fillRect(0, 0, W, H);
    for (let i = 0; i < 4000; i++) {
      x.fillStyle = r.pick([rgb(0x4b4f55), rgb(0x35393e), rgb(0x565a60)]);
      x.globalAlpha = 0.6;
      x.fillRect(r.next() * W, r.next() * H, 1.6, 1.6);
    }
    x.globalAlpha = 0.95;
    x.fillStyle = '#e9e4c8';
    x.fillRect(40, H / 2 - 4, 180, 8);
    x.fillRect(296, H / 2 - 4, 180, 8);
    x.fillStyle = '#d8d8d2';
    x.fillRect(0, 10, W, 5);
    x.fillRect(0, H - 15, W, 5);
    x.globalAlpha = 1;
    out.road = { tex: finish(c), span: 8, rough: 0.9 };
  }
  return out;
}

/** chain-link pattern with transparent holes */
export function makeFenceTexture(): THREE.Texture {
  const S = 128, [c, x] = mk(S);
  x.clearRect(0, 0, S, S);
  x.strokeStyle = 'rgba(205,212,220,1)';
  x.lineWidth = 3.2;
  const step = S / 4;
  for (let i = -4; i <= 8; i++) {
    x.beginPath(); x.moveTo(i * step, 0); x.lineTo(i * step + S, S); x.stroke();
    x.beginPath(); x.moveTo(i * step, 0); x.lineTo(i * step - S, S); x.stroke();
  }
  const t = finish(c, 4);
  return t;
}

/** soft radial gradient used for light pools */
export function makeGlowTexture(): THREE.Texture {
  const S = 128, [c, x] = mk(S);
  const g = x.createRadialGradient(S / 2, S / 2, 0, S / 2, S / 2, S / 2);
  g.addColorStop(0, 'rgba(255,255,255,1)');
  g.addColorStop(0.35, 'rgba(255,255,255,0.55)');
  g.addColorStop(0.7, 'rgba(255,255,255,0.14)');
  g.addColorStop(1, 'rgba(255,255,255,0)');
  x.fillStyle = g;
  x.fillRect(0, 0, S, S);
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  return t;
}

/** build-mode grid: one cell per tile */
export function makeGridTexture(): THREE.Texture {
  const S = 64, [c, x] = mk(S);
  x.clearRect(0, 0, S, S);
  x.strokeStyle = 'rgba(255,255,255,0.9)';
  x.lineWidth = 2;
  x.strokeRect(0, 0, S, S);
  const t = finish(c, 4);
  return t;
}

const labelCache = new Map<string, THREE.Texture>();
/** text label texture (cached) */
export function makeLabelTexture(text: string, color = '#ffffff', bg = 'rgba(20,24,30,0.72)'): THREE.Texture {
  const key = text + '|' + color + '|' + bg;
  let t = labelCache.get(key);
  if (t) return t;
  const c = document.createElement('canvas');
  const x = c.getContext('2d')!;
  const font = '600 34px system-ui, "Segoe UI", Roboto, Helvetica, Arial, sans-serif';
  x.font = font;
  const w = Math.ceil(x.measureText(text).width) + 36;
  c.width = w;
  c.height = 56;
  x.font = font;
  x.fillStyle = bg;
  const rr = 16;
  x.beginPath();
  x.roundRect(0, 0, w, 56, rr);
  x.fill();
  x.fillStyle = color;
  x.textBaseline = 'middle';
  x.fillText(text, 18, 30);
  t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  t.anisotropy = 4;
  labelCache.set(key, t);
  return t;
}

/** round status icon with a glyph, drawn with vector shapes only */
export function makeIconTexture(kind: string): THREE.Texture {
  const S = 96, [c, x] = mk(S);
  const colors: Record<string, string> = {
    sleep: '#4d63b8', angry: '#d8402f', hungry: '#e09a1f', fight: '#c22a2a', family: '#e0609a', medical: '#e84a4a',
    cuffs: '#59616e', escape: '#f0d020', contraband: '#8a4fd0', work: '#a97748', build: '#3b8fd9', alert: '#f08a24',
    shower: '#3aa7d6', toilet: '#6b8fa8', learn: '#3fae6a', calm: '#58b89a',
  };
  x.fillStyle = 'rgba(0,0,0,0.25)';
  x.beginPath(); x.arc(S / 2, S / 2 + 3, 42, 0, 7); x.fill();
  x.fillStyle = colors[kind] ?? '#555';
  x.beginPath(); x.arc(S / 2, S / 2, 42, 0, 7); x.fill();
  x.strokeStyle = 'rgba(255,255,255,0.95)';
  x.lineWidth = 5;
  x.beginPath(); x.arc(S / 2, S / 2, 39, 0, 7); x.stroke();
  x.fillStyle = '#fff';
  x.strokeStyle = '#fff';
  x.lineCap = 'round';
  x.lineJoin = 'round';
  x.textAlign = 'center';
  x.textBaseline = 'middle';
  const txt = (s: string, size = 52, dy = 3) => {
    x.font = `800 ${size}px system-ui, "Segoe UI", Roboto, Helvetica, Arial, sans-serif`;
    x.fillText(s, S / 2, S / 2 + dy);
  };
  switch (kind) {
    case 'sleep': txt('Z', 50); break;
    case 'angry': txt('!', 60); break;
    case 'fight': txt('!!', 50); break;
    case 'alert': txt('?', 58); break;
    case 'escape': x.fillStyle = '#222'; txt('!', 60); break;
    case 'medical':
      x.fillRect(S / 2 - 8, S / 2 - 26, 16, 52);
      x.fillRect(S / 2 - 26, S / 2 - 8, 52, 16);
      break;
    case 'hungry': // fork & knife
      x.lineWidth = 6;
      x.beginPath(); x.moveTo(36, 24); x.lineTo(36, 72); x.stroke();
      x.beginPath(); x.moveTo(28, 24); x.lineTo(28, 40); x.quadraticCurveTo(36, 48, 44, 40); x.lineTo(44, 24); x.stroke();
      x.beginPath(); x.moveTo(60, 72); x.lineTo(60, 24); x.quadraticCurveTo(72, 34, 60, 50); x.stroke();
      break;
    case 'family': // heart
      x.beginPath();
      x.moveTo(48, 72);
      x.bezierCurveTo(14, 48, 26, 22, 48, 38);
      x.bezierCurveTo(70, 22, 82, 48, 48, 72);
      x.fill();
      break;
    case 'cuffs':
      x.lineWidth = 7;
      x.beginPath(); x.arc(34, 50, 12, 0, 7); x.stroke();
      x.beginPath(); x.arc(62, 50, 12, 0, 7); x.stroke();
      break;
    case 'contraband': txt('$', 54); break;
    case 'work': case 'build': // wrench-ish: hammer
      x.lineWidth = 8;
      x.beginPath(); x.moveTo(34, 68); x.lineTo(58, 36); x.stroke();
      x.fillRect(46, 22, 28, 16);
      break;
    case 'shower':
      x.lineWidth = 5;
      for (let i = 0; i < 3; i++) { x.beginPath(); x.moveTo(34 + i * 14, 44); x.lineTo(30 + i * 14, 70); x.stroke(); }
      x.fillRect(28, 28, 40, 10);
      break;
    case 'toilet': txt('WC', 34); break;
    case 'learn': txt('A', 54); break;
    case 'calm': txt('~', 60, 0); break;
  }
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  return t;
}
