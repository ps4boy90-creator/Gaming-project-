// Faceplate atlas for every rack-mounted device: front and rear panels for
// servers, storage, switches, patch panels, UPS and so on.
//
// Layout: 2048×2048, two 1024px columns, 96px per rack unit (a 19" panel is
// ~10.9:1 per U; 1024:96 is within 2% of that). Each device painter also
// records LED positions (animated later by the LED shader) and cable anchors
// (ports and power inlets the cable generator plugs into).

import { Painter } from './painter.js';
import { Rng } from './util.js';

const UPX = 96;
const W = 1024;
const E = 36; // rack ear width in px

const M = {
  body: { c: '#3e4146', h: 0.5, r: 0.45, m: 0.1 },
  bodyBlk: { c: '#323438', h: 0.5, r: 0.5, m: 0.05 },
  bodyLt: { c: '#4a4d53', h: 0.56, r: 0.42, m: 0.15 },
  rearGrey: { c: '#5a5e65', h: 0.5, r: 0.45, m: 0.4 },
  plastic: { c: '#2c2d31', h: 0.55, r: 0.62, m: 0 },
  plasticHi: { c: '#36383d', h: 0.62, r: 0.55, m: 0 },
  caddy: { c: '#404348', h: 0.6, r: 0.55, m: 0.05 },
  grey: { c: '#4a4e55', h: 0.58, r: 0.5, m: 0.2 },
  hole: { c: '#050506', h: 0.18, r: 0.95, m: 0 },
  deep: { c: '#020203', h: 0.05, r: 1, m: 0 },
  silver: { c: '#aeb4bb', h: 0.66, r: 0.3, m: 0.95 },
  steel: { c: '#7b8188', h: 0.6, r: 0.38, m: 0.9 },
  zinc: { c: '#90969d', h: 0.55, r: 0.42, m: 0.85 },
  gold: { c: '#c49b3c', r: 0.3, m: 1 },
  label: { c: '#e6e4dc', h: 0.53, r: 0.75, m: 0 },
  ink: { c: '#1a1a1a', r: 0.7, m: 0 },
  inkLt: { c: '#b5bac0', r: 0.6, m: 0 },
  terra: { c: '#c0623a', h: 0.66, r: 0.5, m: 0 },
  blue: { c: '#2e6ab0', h: 0.64, r: 0.45, m: 0 },
  vgaBlue: { c: '#22356e', h: 0.6, r: 0.5, m: 0 },
};
const shade = (h) => ({ h });

// ---------------------------------------------------------------- helpers --
function thumbscrew(p, cx, cy, r = 8) {
  p.circle(cx, cy, r + 1.5, { h: 0.4 });
  p.circle(cx, cy, r, M.silver);
  p.circle(cx, cy, r * 0.62, { c: '#8a9097', h: 0.6 });
  p.line(cx - r * 0.45, cy, cx + r * 0.45, cy, 2, { c: '#3a3d41', h: 0.45 });
}

function ears(p, x, y, w, h, mat = M.bodyLt, screws = true) {
  p.rect(x, y, E, h, mat);
  p.rect(x + w - E, y, E, h, mat);
  p.rect(x + E - 2, y, 2, h, shade(0.35));
  p.rect(x + w - E, y, 2, h, shade(0.35));
  if (!screws) return;
  const n = Math.round(h / UPX);
  for (let i = 0; i < n; i++) {
    const cy = y + UPX / 2 + i * UPX;
    thumbscrew(p, x + E / 2, cy);
    thumbscrew(p, x + w - E / 2, cy);
  }
}

function base(p, x, y, w, h, mat, seed) {
  p.rect(x, y, w, h, mat);
  p.grain(x, y, w, h, 0.018, { rough: 0.05, seed });
  p.rect(x, y, w, 2, shade(0.62));
  p.rect(x, y + h - 2, w, 2, shade(0.38));
}

function usb(p, x, y, vertical = false) {
  const [w, h] = vertical ? [9, 20] : [20, 9];
  p.rect(x - 1, y - 1, w + 2, h + 2, M.silver);
  p.rect(x, y, w, h, M.deep);
  if (vertical) p.rect(x + 2, y + 2, 3, h - 4, { c: '#1f4fa0', h: 0.5, r: 0.5, m: 0 });
  else p.rect(x + 2, y + 2, w - 4, 3, { c: '#1f4fa0', h: 0.5, r: 0.5, m: 0 });
}

function vga(p, x, y) {
  p.poly([[x, y], [x + 46, y], [x + 42, y + 18], [x + 4, y + 18]], M.silver);
  p.poly([[x + 4, y + 3], [x + 42, y + 3], [x + 39, y + 15], [x + 7, y + 15]], M.vgaBlue);
  const pts = [];
  for (let i = 0; i < 5; i++) pts.push([x + 11 + i * 6, y + 6]);
  for (let i = 0; i < 5; i++) pts.push([x + 13 + i * 5.5, y + 12]);
  p.holes(pts, 1.2, M.deep);
  p.circle(x - 5, y + 9, 3, M.silver);
  p.circle(x + 51, y + 9, 3, M.silver);
}

function rj45(p, x, y, w = 26, h = 22, leds = true, ledColor = 'green') {
  p.rect(x, y, w, h, M.silver);
  p.rect(x + 2, y + 2, w - 4, h - 4, M.deep);
  p.rect(x + w * 0.32, y + h - 6, w * 0.36, 4, { c: '#0c0c0d', h: 0.02 });
  for (let i = 0; i < 8; i++) p.rect(x + 5 + i * ((w - 10) / 8), y + 3, 1.2, 4, M.gold);
  p.anchor(x + w / 2, y + h / 2, 'eth');
  if (leds) {
    p.led(x + 5, y + h - 4, 'link', ledColor, false);
    p.led(x + w - 5, y + h - 4, 'act', 'amber', false);
  }
}

function sfp(p, x, y, w = 36, h = 16, kind = 'sfp') {
  p.rect(x, y, w, h, M.silver);
  p.rect(x + 2, y + 2, w - 4, h - 4, M.deep);
  p.rect(x + 3, y + h / 2 - 1, w - 6, 2, { c: '#2c2f33', h: 0.12 });
  p.anchor(x + w / 2, y + h / 2, kind);
}

function c14(p, x, y) {
  // IEC C14 inlet, 34×26
  p.rect(x - 2, y - 2, 38, 30, { c: '#121314', h: 0.62, r: 0.6, m: 0 });
  p.poly([[x + 4, y + 2], [x + 30, y + 2], [x + 32, y + 10], [x + 32, y + 24], [x + 2, y + 24], [x + 2, y + 10]], M.deep);
  p.rect(x + 9, y + 9, 3, 9, M.silver);
  p.rect(x + 22, y + 9, 3, 9, M.silver);
  p.rect(x + 15.5, y + 4, 3, 7, M.silver);
  p.anchor(x + 17, y + 13, 'psu');
}

function c13(p, x, y) {
  // IEC C13 outlet (female), 30×24
  p.rect(x, y, 30, 24, { c: '#0f1011', h: 0.6, r: 0.6, m: 0 });
  p.poly([[x + 5, y + 3], [x + 25, y + 3], [x + 27, y + 9], [x + 27, y + 21], [x + 3, y + 21], [x + 3, y + 9]], { c: '#191a1c', h: 0.5 });
  p.rect(x + 8, y + 9, 3, 8, M.deep);
  p.rect(x + 19, y + 9, 3, 8, M.deep);
  p.rect(x + 13.5, y + 5, 3, 6, M.deep);
}

function fanGrill(p, cx, cy, r, mat = M.steel) {
  p.circle(cx, cy, r, M.deep);
  p.circle(cx, cy, r * 0.32, { c: '#1d1e20', h: 0.4 });
  p.paint(mat, (c) => {
    c.lineWidth = 2;
    for (let k = 1; k <= 4; k++) {
      c.beginPath();
      c.arc(cx, cy, (r * k) / 4.2, 0, Math.PI * 2);
      c.stroke();
    }
    for (let a = 0; a < 4; a++) {
      c.beginPath();
      c.moveTo(cx + Math.cos(a * 1.5708 + 0.3) * r * 0.2, cy + Math.sin(a * 1.5708 + 0.3) * r * 0.2);
      c.lineTo(cx + Math.cos(a * 1.5708 + 0.3) * r, cy + Math.sin(a * 1.5708 + 0.3) * r);
      c.stroke();
    }
  });
}

function slotVent(p, x, y, w, h, slotW = 4, pitch = 8, mat = M.hole) {
  for (let xx = x + 2; xx + slotW <= x + w - 2; xx += pitch) p.rrect(xx, y, slotW, h, slotW / 2, mat);
}

function psu(p, x, y, w, h, side, rng) {
  // Hot-swap power supply: fan grill, C14 inlet, pull handle, status LED.
  p.rect(x, y, w, h, M.zinc);
  p.grain(x, y, w, h, 0.03, { rough: 0.08, seed: rng.int(1, 9999) });
  p.rect(x, y, w, 2, shade(0.7));
  p.rect(x, y, 2, h, shade(0.7));
  p.rect(x, y + h - 2, w, 2, shade(0.3));
  const fr = Math.min(h * 0.38, 34);
  const fanX = side === 0 ? x + 12 + fr : x + w - 12 - fr;
  if (h < 120) p.hexGrid(fanX - fr, y + h / 2 - fr, fr * 2, fr * 2, 6, 2.2, M.hole);
  else fanGrill(p, fanX, y + h / 2, fr);
  const inX = side === 0 ? fanX + fr + 14 : fanX - fr - 50;
  c14(p, inX, y + h / 2 - 13);
  // handle loop
  const hx = side === 0 ? x + w - 22 : x + 6;
  p.rrect(hx, y + 6, 16, h - 12, 6, { c: '#141516', h: 0.75, r: 0.5, m: 0 });
  p.rrect(hx + 4, y + 12, 8, h - 24, 3, { c: '#060607', h: 0.3 });
  p.rect(side === 0 ? hx - 12 : hx + 18, y + h - 16, 10, 10, M.terra);
  p.led(side === 0 ? inX + 44 : inX - 8, y + 12, 'psu', 'green');
}

function pcieCover(p, x, y, w, h, vertical = false) {
  p.rect(x, y, w, h, M.steel);
  p.rect(x, y, w, 1.5, shade(0.7));
  if (vertical) {
    for (let yy = y + 10; yy + 14 < y + h - 8; yy += 12) p.rrect(x + 6, yy, w - 12, 5, 2.5, M.hole);
    p.circle(x + w / 2, y + 5, 3, M.silver);
  } else {
    slotVent(p, x + 10, y + 5, w - 26, h - 10, 4, 8);
    p.circle(x + w - 8, y + h / 2, 3, M.silver);
  }
}

function nicCard(p, x, y, w, h, kind = 'sfp', n = 2, vertical = false) {
  p.rect(x, y, w, h, M.steel);
  p.rect(x, y, w, 1.5, shade(0.7));
  if (!vertical) {
    for (let i = 0; i < n; i++) {
      if (kind === 'sfp') sfp(p, x + 14 + i * 44, y + (h - 16) / 2, 36, 16, 'sfp');
      else if (kind === 'qsfp') sfp(p, x + 12 + i * 58, y + (h - 18) / 2, 50, 18, 'qsfp');
      else rj45(p, x + 12 + i * 30, y + (h - 22) / 2, 26, 22, true);
      p.led(x + 14 + i * (kind === 'qsfp' ? 58 : 44) - 6, y + 5, 'link', 'green', false);
    }
    p.circle(x + w - 8, y + h / 2, 3, M.silver);
  } else {
    for (let i = 0; i < n; i++) {
      const yy = y + 18 + i * 62;
      if (kind === 'qsfp') {
        p.rect(x + (w - 22) / 2, yy, 22, 52, M.silver);
        p.rect(x + (w - 22) / 2 + 2, yy + 2, 18, 48, M.deep);
        p.anchor(x + w / 2, yy + 26, 'qsfp');
      } else {
        rj45(p, x + (w - 26) / 2, yy, 26, 22, true);
      }
      p.led(x + w / 2 + 16, yy + 4, 'link', 'green', false);
    }
    p.circle(x + w / 2, y + 6, 3, M.silver);
  }
}

// 2.5" drive carrier standing upright (SFF bays in 1U / 2U servers)
function carrierSFF(p, x, y, w, h, rng, accent = M.terra) {
  p.rrect(x, y, w, h, 2, M.caddy);
  p.rect(x + 1, y + h - 1, w - 2, 1, shade(0.25));
  const meshTop = y + 16, meshH = h * 0.56;
  p.rrect(x + 4, meshTop, w - 8, meshH, 1, { c: '#26282c', h: 0.48 });
  p.hexGrid(x + 4, meshTop, w - 8, meshH, 5, 1.6, M.hole);
  // release button and latch
  p.rrect(x + 5, y + h - 22, w - 10, 11, 2, accent);
  p.rect(x + 4, y + h - 8, w - 8, 3, { c: '#0a0a0b', h: 0.25 });
  p.led(x + w * 0.3, y + 8, 'disk', 'green', true);
  p.led(x + w * 0.72, y + 8, rng.chance(0.03) ? 'fault' : 'pwr', rng.chance(0.03) ? 'amber' : 'green', true);
}

// 3.5" drive carrier lying flat (LFF bays)
function carrierLFF(p, x, y, w, h, rng, accent = M.terra) {
  p.rrect(x, y, w, h, 3, { c: '#3d4046', h: 0.6, r: 0.48, m: 0.12 });
  p.rect(x + 2, y + h - 2, w - 4, 2, shade(0.28));
  const hw = Math.min(56, w * 0.26);
  // lever handle
  p.rrect(x + 4, y + 4, hw, h - 8, 3, { c: '#2a2b2f', h: 0.72, r: 0.5, m: 0 });
  p.rect(x + 10, y + h / 2 - 2, hw - 16, 4, { c: '#08080a', h: 0.4 });
  p.rrect(x + hw - 12, y + 8, 10, h - 16, 2, accent);
  // ventilation mesh
  p.rrect(x + hw + 10, y + 6, w - hw - 16, h - 12, 2, { c: '#2a2c30', h: 0.5 });
  p.hexGrid(x + hw + 10, y + 6, w - hw - 16, h - 12, 6, 2.1, M.hole);
  p.led(x + 12, y + 10, 'disk', 'green', true);
  p.led(x + 12, y + h - 10, rng.chance(0.03) ? 'fault' : 'pwr', rng.chance(0.03) ? 'amber' : 'green', true);
}

function bezelSlats(p, x, y, w, h) {
  p.rect(x, y, w, h, { c: '#26272b', h: 0.55, r: 0.55, m: 0 });
  p.paint({ c: '#050506', h: 0.25 }, (c) => {
    c.save();
    c.beginPath();
    c.rect(x + 6, y + 6, w - 12, h - 12);
    c.clip();
    c.lineWidth = 3.5;
    for (let xx = x - h; xx < x + w + h; xx += 9) {
      c.beginPath();
      c.moveTo(xx, y + h);
      c.lineTo(xx + h * 0.6, y);
      c.stroke();
    }
    c.restore();
  });
}

// ---------------------------------------------------------------- devices --
const FRONT = {
  srv1u_a(p, x, y, w, h, rng) {
    base(p, x, y, w, h, M.body, 11);
    ears(p, x, y, w, h);
    p.rrect(x + 40, y + 8, 154, 80, 4, M.plastic);
    p.circle(x + 62, y + 30, 11, M.silver);
    p.circle(x + 62, y + 30, 8, M.plasticHi);
    p.led(x + 62, y + 30, 'pwr', 'green', false);
    p.led(x + 88, y + 30, 'pwr', 'blue');
    p.led(x + 104, y + 30, 'id', 'blue');
    p.text('KESTREL  R1', x + 50, y + 66, 14, M.inkLt, { weight: 700, spacing: 1 });
    p.rect(x + 160, y + 54, 26, 24, M.label);
    for (let i = 0; i < 10; i++) carrierSFF(p, x + 206 + i * 58, y + 7, 56, 82, rng);
    p.rrect(x + 794, y + 8, 186, 80, 3, M.plastic);
    p.hexGrid(x + 798, y + 12, 112, 72, 7, 2.6, M.hole);
    usb(p, x + 920, y + 18);
    vga(p, x + 924, y + 54);
  },

  srv1u_b(p, x, y, w, h, rng) {
    base(p, x, y, w, h, { c: '#3d4045', h: 0.5, r: 0.4, m: 0.25 }, 12);
    ears(p, x, y, w, h, { c: '#474b51', h: 0.55, r: 0.4, m: 0.25 });
    for (let i = 0; i < 4; i++) carrierLFF(p, x + 44 + i * 212, y + 12, 206, 72, rng, M.terra);
    p.rrect(x + 896, y + 8, 88, 80, 3, M.plastic);
    p.circle(x + 916, y + 28, 10, M.silver);
    p.circle(x + 916, y + 28, 7, M.plasticHi);
    p.led(x + 916, y + 28, 'pwr', 'green', false);
    p.led(x + 940, y + 22, 'pwr', 'green');
    p.led(x + 958, y + 22, 'pwr', 'green');
    p.text('NORDSTAK', x + 940, y + 72, 11, M.inkLt, { align: 'center' });
    usb(p, x + 932, y + 40);
  },

  srv1u_c(p, x, y, w, h, rng) {
    base(p, x, y, w, h, M.bodyBlk, 13);
    ears(p, x, y, w, h, M.bodyBlk);
    bezelSlats(p, x + 40, y + 6, w - 80, h - 12);
    p.rrect(x + 430, y + 32, 164, 32, 4, M.silver);
    p.text('HALCYON', x + 512, y + 49, 17, M.ink, { align: 'center', spacing: 3 });
    p.rect(x + 880, y + 20, 80, 4, { c: '#5aa0ff', e: '#3a7bff', h: 0.55, r: 0.3, m: 0 });
    p.circle(x + 920, y + 66, 8, M.silver);
    p.rect(x + 919, y + 61, 2, 10, M.deep);
    p.led(x + 18, y + 22, 'pwr', 'green');
    p.led(x + w - 18, y + 22, 'pwr', 'blue');
  },

  srv2u_a(p, x, y, w, h, rng) {
    base(p, x, y, w, h, M.body, 21);
    ears(p, x, y, w, h, M.bodyLt, false);
    // control ears
    thumbscrew(p, x + 18, y + 170);
    thumbscrew(p, x + w - 18, y + 170);
    p.circle(x + 18, y + 26, 10, M.silver);
    p.circle(x + 18, y + 26, 7, M.plasticHi);
    p.led(x + 18, y + 26, 'pwr', 'green', false);
    p.led(x + 18, y + 54, 'pwr', 'blue');
    p.led(x + 18, y + 72, 'id', 'blue');
    usb(p, x + 13, y + 92, true);
    usb(p, x + w - 22, y + 20, true);
    p.rect(x + w - 30, y + 60, 24, 40, { c: '#1b1c1f', h: 0.6, r: 0.5, m: 0 });
    for (let r = 0; r < 3; r++)
      for (let c = 0; c < 4; c++) carrierLFF(p, x + 42 + c * 236, y + 6 + r * 61, 232, 58, rng, M.blue);
  },

  srv2u_b(p, x, y, w, h, rng) {
    base(p, x, y, w, h, M.body, 22);
    ears(p, x, y, w, h, M.bodyLt, false);
    thumbscrew(p, x + 18, y + 170);
    thumbscrew(p, x + w - 18, y + 170);
    p.circle(x + 18, y + 26, 10, M.silver);
    p.circle(x + 18, y + 26, 7, M.plasticHi);
    p.led(x + 18, y + 26, 'pwr', 'green', false);
    p.led(x + 18, y + 54, 'pwr', 'blue');
    usb(p, x + 13, y + 80, true);
    usb(p, x + w - 22, y + 20, true);
    for (let i = 0; i < 24; i++) carrierSFF(p, x + 44 + i * 39, y + 8, 37, 176, rng, M.terra);
  },

  srv2u_c(p, x, y, w, h, rng) {
    base(p, x, y, w, h, M.bodyBlk, 23);
    ears(p, x, y, w, h, M.bodyBlk);
    p.rrect(x + 40, y + 6, w - 80, h - 12, 6, { c: '#2c2e32', h: 0.62, r: 0.5, m: 0.1 });
    p.rect(x + 40, y + 6, w - 80, 10, { c: '#7d838b', h: 0.66, r: 0.32, m: 0.9 });
    p.rect(x + 40, y + h - 16, w - 80, 10, { c: '#7d838b', h: 0.66, r: 0.32, m: 0.9 });
    p.hexGrid(x + 48, y + 22, w - 96, h - 44, 8, 3.1, M.hole);
    p.rrect(x + 410, y + 74, 204, 44, 5, { c: '#111214', h: 0.7, r: 0.4, m: 0 });
    p.text('HALCYON  X2', x + 512, y + 96, 18, { c: '#cfd4da', r: 0.4, m: 0.6 }, { align: 'center', spacing: 3 });
    p.rect(x + 820, y + 76, 110, 40, { c: '#0a1418', e: '#0a1820', h: 0.6, r: 0.2, m: 0 });
    p.text('SYS  OK', x + 875, y + 96, 15, { c: '#6fe3ff', e: '#4fd8ff' }, { align: 'center', font: 'monospace' });
    p.led(x + 18, y + 30, 'pwr', 'green');
    p.led(x + w - 18, y + 30, 'id', 'blue');
  },

  storage4u(p, x, y, w, h, rng) {
    base(p, x, y, w, h, { c: '#303338', h: 0.5, r: 0.42, m: 0.15 }, 41);
    ears(p, x, y, w, h, { c: '#3b3e44', h: 0.55, r: 0.42, m: 0.15 });
    p.rect(x + 40, y + 4, w - 80, 34, { c: '#2a2b2f', h: 0.6, r: 0.55, m: 0 });
    p.text('ARRAYCORE  9400', x + 56, y + 21, 16, M.inkLt, { spacing: 2 });
    p.rect(x + 700, y + 9, 170, 24, { c: '#081016', e: '#061018', h: 0.62, r: 0.2, m: 0 });
    p.text('CTRL A  ONLINE', x + 785, y + 21, 13, { c: '#79d0ff', e: '#4cc3ff' }, { align: 'center', font: 'monospace' });
    p.led(x + 900, y + 21, 'pwr', 'green');
    p.led(x + 920, y + 21, 'pwr', 'blue');
    p.led(x + 940, y + 21, 'heartbeat', 'green');
    for (let r = 0; r < 6; r++)
      for (let c = 0; c < 4; c++) carrierLFF(p, x + 42 + c * 236, y + 42 + r * 57, 232, 54, rng, M.blue);
  },

  gpu4u(p, x, y, w, h, rng) {
    base(p, x, y, w, h, M.body, 44);
    ears(p, x, y, w, h);
    p.rrect(x + 40, y + 6, 420, 96, 3, M.plastic);
    for (let i = 0; i < 10; i++) carrierSFF(p, x + 44 + i * 41, y + 9, 39, 90, rng);
    p.rrect(x + 470, y + 6, 512, 96, 3, M.plastic);
    p.text('TITAN  G8', x + 500, y + 34, 22, M.inkLt, { spacing: 4 });
    p.text('8 × ACCELERATOR', x + 500, y + 66, 13, { c: '#8a9097' }, { spacing: 2 });
    p.circle(x + 930, y + 40, 12, M.silver);
    p.circle(x + 930, y + 40, 9, M.plasticHi);
    p.led(x + 930, y + 40, 'pwr', 'green', false);
    p.led(x + 900, y + 40, 'pwr', 'blue');
    p.led(x + 960, y + 76, 'heartbeat', 'green');
    // massive honeycomb intake with the fan wall visible behind it
    p.rect(x + 40, y + 108, w - 80, h - 116, { c: '#4a4e54', h: 0.6, r: 0.38, m: 0.6 });
    p.hexGrid(x + 44, y + 112, w - 88, h - 124, 10, 4.2, { c: '#0b0c0e', h: 0.15, r: 0.9, m: 0 });
    for (let i = 0; i < 6; i++) {
      p.circle(x + 120 + i * 157, y + 108 + (h - 116) / 2, 66, { c: '#16171a', a: 0.35 });
      p.circle(x + 120 + i * 157, y + 108 + (h - 116) / 2, 18, { c: '#1d1f22', a: 0.5 });
    }
  },

  switch48(p, x, y, w, h, rng) {
    base(p, x, y, w, h, { c: '#34363b', h: 0.5, r: 0.48, m: 0.1 }, 51);
    ears(p, x, y, w, h, { c: '#3c3e43', h: 0.55, r: 0.45, m: 0.1 });
    p.text('NX-4848', x + 46, y + 22, 15, M.inkLt, { spacing: 1 });
    const st = ['SYS', 'PSU', 'FAN', 'STK'];
    st.forEach((s, i) => {
      p.led(x + 52 + (i % 2) * 48, y + 46 + Math.floor(i / 2) * 24, i === 0 ? 'heartbeat' : 'pwr', 'green');
      p.text(s, x + 60 + (i % 2) * 48, y + 46 + Math.floor(i / 2) * 24, 9, M.inkLt);
    });
    for (let g = 0; g < 4; g++) {
      const gx = x + 156 + g * 176;
      p.rect(gx - 4, y + 12, 172, 72, { c: '#28292d', h: 0.48 });
      for (let i = 0; i < 6; i++) {
        rj45(p, gx + i * 28, y + 16, 26, 26, true, 'green');
        rj45(p, gx + i * 28, y + 54, 26, 26, true, 'green');
      }
      p.text(String(g * 12 + 1), gx, y + 8, 8, M.inkLt);
    }
    for (let i = 0; i < 4; i++) {
      const sx = x + 868 + (i % 2) * 52, sy = y + 18 + Math.floor(i / 2) * 36;
      sfp(p, sx, sy, 44, 20, 'sfp');
      p.led(sx + 22, sy - 5, 'link', 'green', false);
    }
  },

  spine32(p, x, y, w, h, rng) {
    base(p, x, y, w, h, { c: '#36383d', h: 0.5, r: 0.45, m: 0.1 }, 52);
    ears(p, x, y, w, h, { c: '#3e4045', h: 0.55, r: 0.45, m: 0.1 });
    p.text('SPX-32Q', x + 44, y + 24, 14, M.inkLt, { spacing: 1 });
    p.led(x + 52, y + 52, 'heartbeat', 'green');
    p.led(x + 72, y + 52, 'pwr', 'green');
    p.led(x + 92, y + 52, 'pwr', 'green');
    for (let i = 0; i < 16; i++) {
      for (let r = 0; r < 2; r++) {
        const sx = x + 126 + i * 52, sy = y + 14 + r * 40;
        sfp(p, sx, sy, 46, 26, 'qsfp');
        p.led(sx + 23, r === 0 ? sy - 4 : sy + 30, 'link', rng.chance(0.85) ? 'green' : 'blue', false);
      }
    }
  },

  patch48(p, x, y, w, h, rng) {
    base(p, x, y, w, h, { c: '#2e3034', h: 0.5, r: 0.55, m: 0.05 }, 53);
    ears(p, x, y, w, h, { c: '#2e3034', h: 0.55, r: 0.55, m: 0.05 }, false);
    p.circle(x + 18, y + 48, 6, { c: '#0b0b0c', h: 0.2 });
    p.circle(x + w - 18, y + 48, 6, { c: '#0b0b0c', h: 0.2 });
    p.rect(x + 66, y + 3, 892, 10, { c: '#e8e6de', h: 0.54, r: 0.8, m: 0 });
    p.rect(x + 66, y + 83, 892, 10, { c: '#e8e6de', h: 0.54, r: 0.8, m: 0 });
    for (let i = 0; i < 24; i++) {
      for (let r = 0; r < 2; r++) {
        const kx = x + 68 + i * 37, ky = y + 18 + r * 34;
        p.rect(kx, ky, 32, 28, { c: '#0e0f10', h: 0.42 });
        p.rect(kx + 3, ky + 3, 26, 22, M.deep);
        p.rect(kx + 9, ky + 20, 14, 4, { c: '#0b0b0c', h: 0.02 });
        for (let k = 0; k < 8; k++) p.rect(kx + 6 + k * 2.6, ky + 4, 1, 4, M.gold);
        p.anchor(kx + 16, ky + 14, 'eth');
      }
      p.text(String(i + 1), x + 84 + i * 37, y + 8, 8, M.ink, { align: 'center' });
      p.text(String(i + 25), x + 84 + i * 37, y + 88, 8, M.ink, { align: 'center' });
    }
  },

  blank(p, x, y, w, h) {
    base(p, x, y, w, h, { c: '#2f3135', h: 0.5, r: 0.55, m: 0.05 }, 61);
    p.grain(x, y, w, h, 0.012, { rough: 0.06, seed: 62 });
    p.rect(x + 40, y + 30, w - 80, 2, shade(0.42));
    p.rect(x + 40, y + h - 32, w - 80, 2, shade(0.58));
    p.circle(x + 18, y + 48, 7, { c: '#2a2c2f', h: 0.62, r: 0.4, m: 0.8 });
    p.circle(x + w - 18, y + 48, 7, { c: '#2a2c2f', h: 0.62, r: 0.4, m: 0.8 });
    p.line(x + 14, y + 48, x + 22, y + 48, 2, { c: '#0f1011', h: 0.45 });
    p.line(x + w - 22, y + 48, x + w - 14, y + 48, 2, { c: '#0f1011', h: 0.45 });
  },

  cablemgr(p, x, y, w, h) {
    base(p, x, y, w, h, { c: '#161719', h: 0.3, r: 0.8, m: 0 }, 71);
    ears(p, x, y, w, h, { c: '#2e3034', h: 0.55, r: 0.55, m: 0.05 }, false);
    p.circle(x + 18, y + 48, 6, M.silver);
    p.circle(x + w - 18, y + 48, 6, M.silver);
    p.rect(x + 40, y + 2, w - 80, 10, { c: '#2d2e31', h: 0.8, r: 0.6, m: 0 });
    p.rect(x + 40, y + h - 12, w - 80, 10, { c: '#2d2e31', h: 0.8, r: 0.6, m: 0 });
    for (let xx = x + 46; xx < x + w - 60; xx += 31) {
      p.rrect(xx, y + 12, 14, h - 24, 3, { c: '#303135', h: 0.9, r: 0.55, m: 0 });
    }
  },

  ups2u(p, x, y, w, h, rng) {
    base(p, x, y, w, h, { c: '#3a3c40', h: 0.5, r: 0.5, m: 0.1 }, 81);
    ears(p, x, y, w, h, { c: '#34363b', h: 0.55, r: 0.45, m: 0.5 });
    p.rrect(x + 40, y + 6, w - 80, h - 12, 8, { c: '#303236', h: 0.62, r: 0.55, m: 0 });
    for (let r = 0; r < 9; r++) p.rrect(x + 60, y + 24 + r * 17, 280, 6, 3, M.hole);
    for (let r = 0; r < 9; r++) p.rrect(x + 684, y + 24 + r * 17, 280, 6, 3, M.hole);
    p.rect(x + 382, y + 30, 210, 74, { c: '#0b1a12', e: '#0a2416', h: 0.58, r: 0.15, m: 0 });
    p.text('ONLINE', x + 394, y + 48, 15, { c: '#8ef0b8', e: '#7af0a8' }, { font: 'monospace' });
    p.text('LOAD 43%  OUT 230V', x + 394, y + 70, 13, { c: '#8ef0b8', e: '#7af0a8' }, { font: 'monospace' });
    p.text('BATT 100%  RT 38m', x + 394, y + 90, 13, { c: '#8ef0b8', e: '#7af0a8' }, { font: 'monospace' });
    for (let i = 0; i < 4; i++) p.circle(x + 400 + i * 52, y + 140, 11, { c: '#3b3e43', h: 0.7, r: 0.4, m: 0 });
    p.led(x + 618, y + 44, 'pwr', 'green');
    p.led(x + 618, y + 66, 'off', 'amber');
    p.text('VOLTARA 3000', x + 486, y + 172, 14, M.inkLt, { align: 'center', spacing: 2 });
  },

  kvm1u(p, x, y, w, h) {
    base(p, x, y, w, h, M.bodyBlk, 91);
    ears(p, x, y, w, h, M.bodyBlk, false);
    p.rrect(x + 46, y + 18, 26, 60, 6, M.silver);
    p.rrect(x + w - 72, y + 18, 26, 60, 6, M.silver);
    p.rect(x + 90, y + 34, w - 180, 28, { c: '#0f1012', h: 0.4 });
    p.text('CONSOLE  KVM 17"', x + 512, y + 48, 14, M.inkLt, { align: 'center', spacing: 2 });
    p.led(x + 820, y + 48, 'pwr', 'green');
    usb(p, x + 850, y + 44);
  },
};

const REAR = {
  rear1u(p, x, y, w, h, rng) {
    base(p, x, y, w, h, M.rearGrey, 101);
    psu(p, x + 8, y + 6, 184, 84, 0, rng);
    psu(p, x + w - 192, y + 6, 184, 84, 1, rng);
    pcieCover(p, x + 204, y + 8, 220, 38);
    nicCard(p, x + 204, y + 50, 220, 38, 'sfp', 2);
    vga(p, x + 444, y + 18);
    usb(p, x + 508, y + 22);
    usb(p, x + 508, y + 40);
    rj45(p, x + 548, y + 20, 26, 22, true);
    p.rect(x + 548, y + 46, 26, 8, M.label);
    for (let i = 0; i < 4; i++) rj45(p, x + 596 + i * 30, y + 20, 26, 22, true);
    p.circle(x + 740, y + 32, 9, M.blue);
    p.led(x + 740, y + 32, 'id', 'blue', false);
    slotVent(p, x + 444, y + 62, 360, 22, 4, 9);
    p.rect(x + 780, y + 14, 30, 30, { c: '#1c1d1f', h: 0.6 });
  },

  rear2u(p, x, y, w, h, rng) {
    base(p, x, y, w, h, M.rearGrey, 102);
    psu(p, x + 8, y + 102, 184, 84, 0, rng);
    psu(p, x + w - 192, y + 102, 184, 84, 1, rng);
    for (let i = 0; i < 3; i++) pcieCover(p, x + 8, y + 6 + i * 31, 184, 28);
    pcieCover(p, x + w - 192, y + 6, 184, 28);
    nicCard(p, x + w - 192, y + 37, 184, 28, 'rj45', 4);
    pcieCover(p, x + w - 192, y + 68, 184, 28);
    nicCard(p, x + 204, y + 8, 300, 40, 'sfp', 2);
    nicCard(p, x + 520, y + 8, 300, 40, 'sfp', 2);
    pcieCover(p, x + 204, y + 52, 300, 40);
    p.rect(x + 520, y + 52, 300, 40, M.steel);
    p.rect(x + 540, y + 60, 80, 24, { c: '#121314', h: 0.4 });
    p.rect(x + 640, y + 60, 80, 24, { c: '#121314', h: 0.4 });
    p.anchor(x + 580, y + 72, 'sas');
    vga(p, x + 214, y + 118);
    usb(p, x + 280, y + 120);
    usb(p, x + 280, y + 140);
    rj45(p, x + 320, y + 118, 26, 22, true);
    p.rect(x + 320, y + 144, 26, 8, M.label);
    for (let i = 0; i < 4; i++) rj45(p, x + 372 + i * 30, y + 118, 26, 22, true);
    p.circle(x + 520, y + 130, 9, M.blue);
    p.led(x + 520, y + 130, 'id', 'blue', false);
    slotVent(p, x + 214, y + 162, 600, 18, 4, 9);
    slotVent(p, x + 560, y + 112, 250, 40, 4, 9);
  },

  rear4u(p, x, y, w, h, rng) {
    base(p, x, y, w, h, { c: '#3d4046', h: 0.5, r: 0.45, m: 0.35 }, 104);
    for (const side of [0, 1]) {
      const px = side ? x + w - 196 : x + 8;
      p.rect(px, y + 6, 188, h - 12, M.zinc);
      p.grain(px, y + 6, 188, h - 12, 0.025, { seed: 105 + side });
      p.rect(px + 10, y + 16, 168, 168, { c: '#3a3d42', h: 0.5 });
      p.hexGrid(px + 12, y + 18, 164, 164, 8, 3.2, M.hole);
      c14(p, px + 76, y + 214);
      p.rrect(px + 20, y + 268, 148, 22, 6, { c: '#151618', h: 0.75 });
      p.led(px + 30, y + 330, 'pwr', 'green');
      p.led(px + 50, y + 330, 'pwr', 'green');
      p.rect(px + 140, y + 320, 30, 20, M.terra);
    }
    for (let k = 0; k < 2; k++) {
      const iy = y + 14 + k * 182;
      p.rect(x + 210, iy, 604, 170, { c: '#373a3f', h: 0.55, r: 0.45, m: 0.2 });
      p.rect(x + 216, iy + 6, 14, 158, M.terra);
      p.rect(x + 794, iy + 6, 14, 158, M.terra);
      p.text(k ? 'IOM B' : 'IOM A', x + 260, iy + 22, 13, M.inkLt, { spacing: 2 });
      for (let i = 0; i < 4; i++) {
        const sx = x + 262 + i * 70;
        p.rect(sx, iy + 50, 56, 30, { c: '#0e0f10', h: 0.42 });
        p.rect(sx + 4, iy + 54, 48, 22, M.deep);
        p.rect(sx + 8, iy + 82, 40, 6, M.blue);
        p.anchor(sx + 28, iy + 65, 'sas');
        p.led(sx + 28, iy + 44, 'link', 'green', false);
      }
      rj45(p, x + 560, iy + 52, 26, 22, true);
      rj45(p, x + 592, iy + 52, 26, 22, true);
      sfp(p, x + 640, iy + 52, 40, 18);
      sfp(p, x + 690, iy + 52, 40, 18);
      slotVent(p, x + 262, iy + 110, 500, 40, 4, 9);
      p.led(x + 740, iy + 22, 'heartbeat', 'green');
      p.led(x + 760, iy + 22, 'pwr', 'blue');
    }
  },

  reargpu(p, x, y, w, h, rng) {
    base(p, x, y, w, h, M.rearGrey, 106);
    for (let i = 0; i < 4; i++) psu(p, x + 8 + i * 254, y + 290, 246, 86, i % 2, rng);
    for (let i = 0; i < 9; i++) {
      const sx = x + 10 + i * 112;
      if (i % 2 === 0) nicCard(p, sx, y + 100, 104, 182, 'qsfp', 2, true);
      else pcieCover(p, sx, y + 100, 104, 182, true);
    }
    vga(p, x + 30, y + 30);
    usb(p, x + 100, y + 30);
    usb(p, x + 100, y + 50);
    rj45(p, x + 140, y + 30, 26, 22, true);
    for (let i = 0; i < 2; i++) rj45(p, x + 186 + i * 30, y + 30, 26, 22, true);
    slotVent(p, x + 300, y + 16, 700, 70, 5, 10);
  },

  rearsw(p, x, y, w, h, rng) {
    base(p, x, y, w, h, { c: '#3a3c40', h: 0.5, r: 0.45, m: 0.2 }, 107);
    psu(p, x + 8, y + 6, 180, 84, 0, rng);
    psu(p, x + w - 188, y + 6, 180, 84, 1, rng);
    for (let i = 0; i < 4; i++) {
      const fx = x + 204 + i * 156;
      p.rect(fx, y + 6, 148, 84, { c: '#2e3034', h: 0.55 });
      p.hexGrid(fx + 6, y + 10, 112, 76, 7, 2.7, M.hole);
      p.rrect(fx + 124, y + 14, 16, 68, 4, M.terra);
      p.led(fx + 132, y + 10, 'pwr', 'green', false);
    }
  },

  rearpatch(p, x, y, w, h) {
    base(p, x, y, w, h, { c: '#2c2e31', h: 0.5, r: 0.6, m: 0.1 }, 108);
    for (let i = 0; i < 24; i++) {
      for (let r = 0; r < 2; r++) {
        const kx = x + 68 + i * 37, ky = y + 18 + r * 34;
        p.rect(kx + 2, ky, 28, 28, { c: '#d6d6d0', h: 0.7, r: 0.6, m: 0 });
        p.rect(kx + 6, ky + 4, 20, 8, { c: '#3b6fb6', h: 0.75, r: 0.5, m: 0 });
      }
    }
  },

  rearups(p, x, y, w, h, rng) {
    base(p, x, y, w, h, { c: '#3a3c40', h: 0.5, r: 0.5, m: 0.15 }, 109);
    for (let i = 0; i < 8; i++) c13(p, x + 40 + (i % 4) * 40, y + 30 + Math.floor(i / 4) * 40);
    p.text('OUTPUT 1-8', x + 40, y + 120, 11, M.inkLt);
    fanGrill(p, x + 300, y + 96, 60);
    p.rect(x + 420, y + 50, 40, 70, { c: '#0e0f10', h: 0.65 });
    p.rect(x + 428, y + 62, 24, 30, { c: '#2b2d31', h: 0.8 });
    rj45(p, x + 500, y + 50, 26, 22, true);
    usb(p, x + 540, y + 54);
    c14(p, x + 900, y + 80);
    p.circle(x + 960, y + 150, 16, { c: '#1a1b1d', h: 0.7 });
    slotVent(p, x + 600, y + 30, 260, 130, 5, 11);
  },

  rearkvm(p, x, y, w, h) {
    base(p, x, y, w, h, M.bodyBlk, 110);
    vga(p, x + 300, y + 36);
    usb(p, x + 370, y + 40);
    rj45(p, x + 410, y + 36, 26, 22, true);
    c14(p, x + 700, y + 34);
  },

  rearblank(p, x, y, w, h) {
    base(p, x, y, w, h, { c: '#2c2e31', h: 0.5, r: 0.6, m: 0.1 }, 111);
  },
};

function side(p, x, y, w, h) {
  p.rect(x, y, w, h, { c: '#8a9096', h: 0.5, r: 0.42, m: 0.88 });
  p.grain(x, y, w, h, 0.04, { rough: 0.1, seed: 120 });
}

// Atlas placement: [name, column, startU, heightU, painter]
const LAYOUT = [
  ['srv1u_a', 0, 0, 1, FRONT.srv1u_a],
  ['srv1u_b', 0, 1, 1, FRONT.srv1u_b],
  ['srv1u_c', 0, 2, 1, FRONT.srv1u_c],
  ['srv2u_a', 0, 3, 2, FRONT.srv2u_a],
  ['srv2u_b', 0, 5, 2, FRONT.srv2u_b],
  ['srv2u_c', 0, 7, 2, FRONT.srv2u_c],
  ['storage4u', 0, 9, 4, FRONT.storage4u],
  ['switch48', 0, 13, 1, FRONT.switch48],
  ['spine32', 0, 14, 1, FRONT.spine32],
  ['patch48', 0, 15, 1, FRONT.patch48],
  ['blank', 0, 16, 1, FRONT.blank],
  ['cablemgr', 0, 17, 1, FRONT.cablemgr],
  ['ups2u', 0, 18, 2, FRONT.ups2u],
  ['kvm1u', 0, 20, 1, FRONT.kvm1u],
  ['rear1u', 1, 0, 1, REAR.rear1u],
  ['rear2u', 1, 1, 2, REAR.rear2u],
  ['rear4u', 1, 3, 4, REAR.rear4u],
  ['gpu4u', 1, 7, 4, FRONT.gpu4u],
  ['reargpu', 1, 11, 4, REAR.reargpu],
  ['rearsw', 1, 15, 1, REAR.rearsw],
  ['rearpatch', 1, 16, 1, REAR.rearpatch],
  ['rearups', 1, 17, 2, REAR.rearups],
  ['rearkvm', 1, 19, 1, REAR.rearkvm],
  ['rearblank', 1, 20, 1, REAR.rearblank],
];

export function buildDeviceAtlas() {
  const p = new Painter(2048, 2048, { base: '#1a1b1d', r: 0.6, m: 0.3, emissive: true });
  const rng = new Rng(4242);
  for (const [name, col, u0, hu, fn] of LAYOUT) {
    const x = col * W, y = u0 * UPX, h = hu * UPX;
    p.region(name, x, y, W, h);
    fn(p, x, y, W, h, rng);
  }
  p.region('side', 0, 21 * UPX, W, 2048 - 21 * UPX);
  side(p, 0, 21 * UPX, W, 2048 - 21 * UPX);
  const tex = p.textures({ normalStrength: 4, blur: 1, anisotropy: 8 });
  return { tex, regions: p.regions };
}
