import * as THREE from 'three';

export const SIGN_FONT = '"Barlow Condensed", "Arial Narrow", "Roboto Condensed", "DejaVu Sans Condensed", sans-serif';
export const MONO_FONT = '"IBM Plex Mono", "DejaVu Sans Mono", "Courier New", monospace';

export interface AtlasRect {
  x: number;
  y: number;
  w: number;
  h: number;
  /** u0, v0 (bottom-left), u1, v1 (top-right) in texture space */
  uv: [number, number, number, number];
}

/** Shelf-packed canvas atlas: many signs or screens, one texture, one draw call. */
export class Atlas {
  canvas: HTMLCanvasElement;
  ctx: CanvasRenderingContext2D;
  texture: THREE.CanvasTexture;
  /** Open shelves, one per cell height, so mixed sizes pack tightly. */
  private shelves: { y: number; h: number; x: number }[] = [];
  private nextY = 0;

  constructor(public size = 2048) {
    this.canvas = document.createElement('canvas');
    this.canvas.width = this.canvas.height = size;
    this.ctx = this.canvas.getContext('2d')!;
    this.texture = new THREE.CanvasTexture(this.canvas);
    this.texture.colorSpace = THREE.SRGBColorSpace;
    this.texture.anisotropy = 8;
  }

  alloc(w: number, h: number): AtlasRect {
    const pad = 4;
    let shelf = this.shelves.find((s) => s.h === h && s.x + w + pad <= this.size);
    if (!shelf) {
      if (this.nextY + h > this.size) {
        console.warn('Atlas full; reusing the first cell');
        shelf = this.shelves[0] ?? { y: 0, h, x: 0 };
        shelf.x = 0;
      } else {
        shelf = { y: this.nextY, h, x: 0 };
        this.shelves.push(shelf);
        this.nextY += h + pad;
      }
    }
    const x = shelf.x;
    const y = shelf.y;
    shelf.x += w + pad;
    return { x, y, w, h, uv: [x / this.size, 1 - (y + h) / this.size, (x + w) / this.size, 1 - y / this.size] };
  }

  commit(): void {
    this.texture.needsUpdate = true;
  }
}

function fitText(ctx: CanvasRenderingContext2D, text: string, maxW: number, size: number, weight: string, family: string): number {
  let s = size;
  ctx.font = `${weight} ${s}px ${family}`;
  while (ctx.measureText(text).width > maxW && s > 8) {
    s -= 2;
    ctx.font = `${weight} ${s}px ${family}`;
  }
  return s;
}

/** Back-lit door plate: accent bar, room code, room name. */
export function drawDoorSign(a: Atlas, code: string, name: string, accent: string, sub = ''): AtlasRect {
  const r = a.alloc(384, 96);
  const c = a.ctx;
  c.save();
  c.translate(r.x, r.y);
  c.scale(0.75, 0.75);
  c.fillStyle = '#14181b';
  c.fillRect(0, 0, 512, 128);
  c.fillStyle = accent;
  c.fillRect(0, 0, 22, 128);
  c.strokeStyle = 'rgba(255,255,255,0.08)';
  c.lineWidth = 2;
  c.strokeRect(1, 1, 510, 126);
  c.fillStyle = 'rgba(232,236,232,0.6)';
  c.font = `500 22px ${MONO_FONT}`;
  c.textBaseline = 'top';
  c.fillText(code, 44, 14);
  c.fillStyle = '#eef0ec';
  fitText(c, name.toUpperCase(), 440, 58, '600', SIGN_FONT);
  c.textBaseline = 'alphabetic';
  c.fillText(name.toUpperCase(), 42, sub ? 92 : 104);
  if (sub) {
    c.fillStyle = accent;
    c.font = `500 18px ${MONO_FONT}`;
    c.fillText(sub.toUpperCase(), 44, 118);
  }
  c.restore();
  return r;
}

/** Painted stencil lettering on a transparent background, with a little wear. */
export function drawStencil(a: Atlas, text: string, color: string, w = 640, h = 96, seed = 1): AtlasRect {
  const r = a.alloc(w, h);
  const c = a.ctx;
  c.save();
  c.translate(r.x, r.y);
  c.clearRect(0, 0, w, h);
  c.fillStyle = color;
  const size = fitText(c, text, w - 20, h * 0.86, '700', SIGN_FONT);
  c.textBaseline = 'middle';
  c.font = `700 ${size}px ${SIGN_FONT}`;
  c.fillText(text, 8, h / 2 + 4);
  // wear: knock out specks
  c.globalCompositeOperation = 'destination-out';
  let s = seed * 9301;
  const rnd = () => ((s = (s * 9301 + 49297) % 233280) / 233280);
  for (let i = 0; i < 260; i++) {
    c.globalAlpha = 0.3 + rnd() * 0.7;
    c.beginPath();
    c.arc(rnd() * w, rnd() * h, 1 + rnd() * 3.5, 0, Math.PI * 2);
    c.fill();
  }
  c.restore();
  return r;
}

/** A printed poster (Haven Colonial Trust propaganda, safety notices). */
export function drawPoster(a: Atlas, title: string, lines: string[], accent: string): AtlasRect {
  const r = a.alloc(384, 512);
  const c = a.ctx;
  c.save();
  c.translate(r.x, r.y);
  const g = c.createLinearGradient(0, 0, 0, 512);
  g.addColorStop(0, '#1c2b33');
  g.addColorStop(0.55, '#4a5a4a');
  g.addColorStop(1, '#c49a4a');
  c.fillStyle = g;
  c.fillRect(0, 0, 384, 512);
  // stylised horizon and planet
  c.fillStyle = 'rgba(255,240,200,0.9)';
  c.beginPath();
  c.arc(270, 140, 40, 0, Math.PI * 2);
  c.fill();
  c.fillStyle = '#20302a';
  c.beginPath();
  c.moveTo(0, 330);
  c.quadraticCurveTo(190, 280, 384, 320);
  c.lineTo(384, 512);
  c.lineTo(0, 512);
  c.fill();
  c.fillStyle = '#efe9da';
  c.fillRect(0, 380, 384, 132);
  c.fillStyle = accent;
  c.fillRect(0, 380, 384, 8);
  c.fillStyle = '#16191a';
  fitText(c, title.toUpperCase(), 340, 44, '700', SIGN_FONT);
  c.textBaseline = 'top';
  c.fillText(title.toUpperCase(), 22, 398);
  c.font = `500 15px ${MONO_FONT}`;
  lines.forEach((l, i) => c.fillText(l, 22, 450 + i * 20));
  c.restore();
  return r;
}

export type ScreenKind =
  | 'orbit' | 'telemetry' | 'status' | 'vitals' | 'dna' | 'cryo' | 'hangar'
  | 'music' | 'mail' | 'comms' | 'lab' | 'lift' | 'nav' | 'decon' | 'map';

/** Fake but plausible console UI. */
export function drawScreen(a: Atlas, kind: ScreenKind, seed = 1, label = ''): AtlasRect {
  const W = 512;
  const H = 320;
  const r = a.alloc(384, 240);
  const c = a.ctx;
  let s = seed * 7919 + 1;
  const rnd = () => ((s = (s * 16807) % 2147483647) / 2147483647);
  // 1980s-style phosphor palette: green primary, amber alerts, warm white text
  const cyan = '#7cf28e';
  const dim = 'rgba(124,242,142,0.32)';
  const amber = '#ffb547';
  const white = '#d9f7d2';
  c.save();
  c.translate(r.x, r.y);
  c.scale(0.75, 0.75);
  c.fillStyle = '#020502';
  c.fillRect(0, 0, W, H);
  c.shadowBlur = 7;
  c.shadowColor = 'rgba(124,242,142,0.8)';
  // header
  c.fillStyle = 'rgba(143,227,210,0.08)';
  c.fillRect(0, 0, W, 30);
  c.fillStyle = cyan;
  c.font = `600 16px ${MONO_FONT}`;
  c.textBaseline = 'middle';
  const titles: Record<ScreenKind, string> = {
    orbit: 'ORBITAL TRACK · KX-7c',
    telemetry: 'TELEMETRY',
    status: 'SHIP SYSTEMS',
    vitals: 'BIOMONITOR',
    dna: 'SEQUENCER · IDLE',
    cryo: 'CRYO VAULT 3',
    hangar: 'KESTREL · LND-01',
    music: 'LOUNGE AUDIO',
    mail: 'PERSONAL TERMINAL',
    comms: 'SIGNAL MONITOR',
    lab: 'ANALYSIS QUEUE',
    lift: 'LIFT',
    nav: 'NAVIGATION',
    decon: 'DECONTAMINATION',
    map: 'SURFACE SURVEY',
  };
  c.fillText(label || titles[kind], 14, 15);
  c.fillStyle = amber;
  c.textAlign = 'right';
  c.fillText('VESTA', W - 14, 15);
  c.textAlign = 'left';
  c.strokeStyle = dim;
  c.fillStyle = white;
  c.lineWidth = 1.5;
  const lines = (arr: string[], x: number, y: number, color = white, size = 15) => {
    c.font = `500 ${size}px ${MONO_FONT}`;
    c.fillStyle = color;
    arr.forEach((t, i) => c.fillText(t, x, y + i * (size + 7)));
  };
  const graph = (x: number, y: number, w: number, h: number, color: string, amp = 0.4) => {
    c.strokeStyle = 'rgba(143,227,210,0.15)';
    for (let i = 0; i <= 4; i++) {
      c.beginPath();
      c.moveTo(x, y + (h * i) / 4);
      c.lineTo(x + w, y + (h * i) / 4);
      c.stroke();
    }
    c.strokeStyle = color;
    c.lineWidth = 2;
    c.beginPath();
    let v = 0.5;
    for (let i = 0; i <= 60; i++) {
      v = Math.min(0.95, Math.max(0.05, v + (rnd() - 0.5) * amp));
      const px = x + (w * i) / 60;
      const py = y + h * (1 - v);
      if (i === 0) c.moveTo(px, py);
      else c.lineTo(px, py);
    }
    c.stroke();
    c.lineWidth = 1.5;
  };
  switch (kind) {
    case 'orbit':
    case 'map': {
      const cx = 170;
      const cy = 178;
      const g = c.createRadialGradient(cx - 30, cy - 30, 10, cx, cy, 110);
      g.addColorStop(0, '#2e5b55');
      g.addColorStop(1, '#0a1b1a');
      c.fillStyle = g;
      c.beginPath();
      c.arc(cx, cy, 105, 0, Math.PI * 2);
      c.fill();
      c.strokeStyle = dim;
      for (let i = -2; i <= 2; i++) {
        c.beginPath();
        c.ellipse(cx, cy, 105, Math.abs(i) * 20 + 4, 0, 0, Math.PI * 2);
        c.stroke();
      }
      c.strokeStyle = amber;
      c.beginPath();
      c.ellipse(cx, cy, 135, 52, -0.35, 0, Math.PI * 2);
      c.stroke();
      c.fillStyle = amber;
      c.beginPath();
      c.arc(cx + 110, cy - 70, 5, 0, Math.PI * 2);
      c.fill();
      lines(['ALT   410.2 KM', 'PERIOD 94.1 MIN', 'INCL  63.8°', 'BETA  35.0°', '', 'SIGNAL  ACTIVE', 'SRC  N. CONTINENT'], 320, 70, white, 15);
      break;
    }
    case 'telemetry':
      graph(16, 50, 230, 110, cyan);
      graph(266, 50, 230, 110, amber, 0.25);
      graph(16, 190, 480, 100, cyan, 0.15);
      break;
    case 'status':
      lines(
        ['REACTOR      98.2%  NOMINAL', 'LIFE SUPPORT 100%   NOMINAL', 'SAILS        61%    DAMAGED', '  P3 P4      OFFLINE', 'CRYO         2,388  STABLE', 'HULL         99.7%', 'CONTAM.      0.00%'],
        18, 56, white, 16,
      );
      c.fillStyle = amber;
      c.fillRect(18, 98, 6, 40);
      break;
    case 'vitals': {
      c.strokeStyle = '#7ff0a0';
      c.lineWidth = 2;
      c.beginPath();
      for (let x = 0; x < 480; x++) {
        const t = (x % 120) / 120;
        const yv = t > 0.4 && t < 0.45 ? -60 : t > 0.45 && t < 0.5 ? 40 : Math.sin(t * 6) * 4;
        if (x === 0) c.moveTo(16 + x, 110 + yv);
        else c.lineTo(16 + x, 110 + yv);
      }
      c.stroke();
      lines(['HR 62   SPO2 98   T 36.4', 'CRYO RECOVERY  94%', 'PATIENT: —'], 18, 220, white, 17);
      break;
    }
    case 'dna':
      for (let i = 0; i < 64; i++) {
        const hgt = 20 + rnd() * 140;
        c.fillStyle = ['#8fe3d2', '#f0a83c', '#e4efe9', '#5aa0d0'][Math.floor(rnd() * 4)];
        c.fillRect(18 + i * 7.5, 230 - hgt, 5, hgt);
      }
      lines(['NO SAMPLE LOADED'], 18, 270, amber, 17);
      break;
    case 'cryo':
      for (let i = 0; i < 40; i++) {
        const x = 18 + (i % 10) * 48;
        const y = 50 + Math.floor(i / 10) * 44;
        const failed = i === 13 || i === 27;
        c.fillStyle = failed ? '#c0392b' : 'rgba(143,227,210,0.6)';
        c.fillRect(x, y, 40, 34);
        c.fillStyle = '#041010';
        c.font = `500 11px ${MONO_FONT}`;
        c.fillText(String(721 + i).padStart(4, '0'), x + 5, y + 17);
      }
      lines(['142 STABLE · 2 LOST · 3.1°C'], 18, 250, white, 17);
      break;
    case 'hangar':
      lines(['FUEL     100%', 'CRADLE   LOCKED', 'HULL     OK', 'DOORS    SEALED', 'CREW     0/4'], 18, 60, white, 18);
      c.strokeStyle = cyan;
      c.lineWidth = 2;
      c.beginPath();
      c.moveTo(300, 200);
      c.lineTo(470, 180);
      c.lineTo(480, 200);
      c.lineTo(470, 220);
      c.closePath();
      c.stroke();
      break;
    case 'music':
      lines(['NOW PLAYING', '', '"Long Dark, Low Sun"', 'MERIDIAN LIBRARY · 04', '', '▶  02:14 / 07:30'], 18, 60, white, 17);
      for (let i = 0; i < 24; i++) {
        const hgt = 10 + rnd() * 60;
        c.fillStyle = cyan;
        c.fillRect(300 + i * 8, 260 - hgt, 5, hgt);
      }
      break;
    case 'mail':
      lines(['INBOX (6)', '', '▸ VESTA — Revival notice', '▸ Capt. Okonkwo — Welcome back', '▸ K. Mensah — Sails', '▸ HCT — Charter excerpt', '▸ Y. Tanabe — Range day', '▸ Signal transcript'], 18, 52, white, 15);
      break;
    case 'comms':
      for (let i = 0; i < 120; i++) {
        const hgt = Math.abs(Math.sin(i * 0.35) * 40 + (rnd() - 0.5) * 30);
        c.fillStyle = i > 40 && i < 80 ? amber : dim;
        c.fillRect(16 + i * 4, 160 - hgt, 3, hgt * 2);
      }
      lines(['CARRIER UNKNOWN · 31H CONTINUOUS', 'CONTENT: HUMAN VOICE (HUMMING)'], 18, 250, amber, 15);
      break;
    case 'lab':
      lines(['QUEUE EMPTY', '', 'XENOBIOLOGY       —', 'XENOARCHAEOLOGY   —', 'SIGNALS           —', 'ENGINEERING       —'], 18, 56, white, 16);
      break;
    case 'lift':
      lines(['1  COMMAND', '2  CREW', '3  SCIENCE · SPINE'], 18, 80, white, 26);
      break;
    case 'nav':
      c.strokeStyle = dim;
      for (let i = 0; i < 12; i++) {
        c.beginPath();
        c.arc(256, 175, 20 + i * 12, 0, Math.PI * 2);
        c.stroke();
      }
      c.fillStyle = amber;
      c.fillRect(250, 70, 12, 12);
      lines(['HAVEN  7.1 LY', 'ETA    7Y 2M'], 18, 270, white, 15);
      break;
    case 'decon':
      lines(['CYCLE 90 S', 'UV · MIST · PURGE', '', 'PROTOCOL 7 IN EFFECT'], 18, 70, amber, 22);
      break;
  }
  // scanlines + vignette (CRT)
  c.shadowBlur = 0;
  c.fillStyle = 'rgba(0,0,0,0.28)';
  for (let y = 0; y < H; y += 3) c.fillRect(0, y, W, 1);
  const vg = c.createRadialGradient(W / 2, H / 2, H * 0.3, W / 2, H / 2, W * 0.7);
  vg.addColorStop(0, 'rgba(0,0,0,0)');
  vg.addColorStop(1, 'rgba(0,0,0,0.55)');
  c.fillStyle = vg;
  c.fillRect(0, 0, W, H);
  c.restore();
  return r;
}

/** Quad geometry with UVs mapped to an atlas rect. Centered, facing +Z. */
export function atlasQuad(w: number, h: number, rect: AtlasRect): THREE.BufferGeometry {
  const g = new THREE.PlaneGeometry(w, h);
  const uv = g.attributes.uv as THREE.BufferAttribute;
  const [u0, v0, u1, v1] = rect.uv;
  for (let i = 0; i < uv.count; i++) {
    uv.setXY(i, u0 + uv.getX(i) * (u1 - u0), v0 + uv.getY(i) * (v1 - v0));
  }
  return g;
}


/** Bold painted wall graphics (frame numbers, directions, warnings) on a transparent cell. */
export function drawGraphic(
  a: Atlas,
  text: string,
  o: { w?: number; h?: number; fg?: string; band?: string; sub?: string; chevrons?: boolean } = {},
): AtlasRect {
  const w = o.w ?? 640;
  const h = o.h ?? 96;
  const r = a.alloc(w, h);
  const c = a.ctx;
  c.save();
  c.translate(r.x, r.y);
  c.clearRect(0, 0, w, h);
  if (o.band) {
    c.fillStyle = o.band;
    c.fillRect(0, h * 0.08, w, h * 0.84);
  }
  if (o.chevrons) {
    c.fillStyle = o.band ? 'rgba(10,10,10,0.9)' : o.fg ?? '#eee';
    for (let i = 0; i < 3; i++) {
      for (const x0 of [8 + i * 22, w - 30 - i * 22]) {
        c.beginPath();
        c.moveTo(x0, h * 0.2);
        c.lineTo(x0 + 12, h * 0.5);
        c.lineTo(x0, h * 0.8);
        c.lineTo(x0 + 7, h * 0.8);
        c.lineTo(x0 + 19, h * 0.5);
        c.lineTo(x0 + 7, h * 0.2);
        c.fill();
      }
    }
  }
  c.fillStyle = o.fg ?? '#ececea';
  const pad = o.chevrons ? 90 : 10;
  const size = fitText(c, text, w - pad * 2 - (o.sub ? w * 0.2 : 0), h * 0.82, '700', SIGN_FONT);
  c.font = `700 ${size}px ${SIGN_FONT}`;
  c.textBaseline = 'middle';
  c.fillText(text, pad, h / 2 + 3);
  if (o.sub) {
    const tw = c.measureText(text).width;
    c.font = `600 ${Math.round(h * 0.24)}px ${MONO_FONT}`;
    c.fillText(o.sub, pad + tw + 12, h * 0.3);
  }
  // a little paint wear
  c.globalCompositeOperation = 'destination-out';
  let sd = (text.length * 7919 + w) | 0;
  const rnd = () => ((sd = (sd * 16807) % 2147483647) / 2147483647);
  for (let i = 0; i < 120; i++) {
    c.globalAlpha = 0.25 + rnd() * 0.5;
    c.beginPath();
    c.arc(rnd() * w, rnd() * h, 0.6 + rnd() * 2.2, 0, Math.PI * 2);
    c.fill();
  }
  c.restore();
  return r;
}
