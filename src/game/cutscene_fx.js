/**
 * Animated cutscene painters.
 *
 * A cutscene step can name one of these instead of (or under) a still, and it
 * repaints the whole 768x432 cutscene frame every tick. The pan, the letterbox,
 * the text and the broadcast treatment all still apply on top, so an animated
 * beat and a painted one are the same kind of thing to everything downstream.
 *
 * Two rules hold the look together:
 *
 *   - Characters are drawn on the *gameplay* pixel grid. The figure is painted
 *     into a 384x216 scratch surface and blitted at 2x with smoothing off, so
 *     Hale is made of exactly the same size pixels in a cutscene as he is when
 *     you are walking him around. The painted rooms are finer than that, and
 *     the contrast is the point: the character belongs to the game, the room
 *     belongs to the picture.
 *   - Everything is greys. No painter introduces a colour the monochrome
 *     conversion would have had to remove.
 *
 * A painter is { images, draw(ctx, api) } where api carries:
 *   w, h        the frame size
 *   phase       which beat of the animation this step is
 *   t, T, k     seconds into the step, its duration, and eased progress 0..1
 *   clock       seconds since the cutscene started
 *   assets, audio, cache
 */

import { drawText, measure } from '../gfx/text.js';

const INK = '#0b0b0c';

/** A 384x216 scratch surface: the gameplay grid, for anything character-sized. */
function scratch(cache) {
  if (!cache.scratch) {
    const canvas = document.createElement('canvas');
    canvas.width = 384;
    canvas.height = 216;
    const ctx = canvas.getContext('2d');
    ctx.imageSmoothingEnabled = false;
    cache.scratch = { canvas, ctx };
  }
  const s = cache.scratch;
  s.ctx.clearRect(0, 0, 384, 216);
  return s;
}

function surface(cache, key, w, h, paint) {
  if (!cache[key]) {
    const canvas = document.createElement('canvas');
    canvas.width = w;
    canvas.height = h;
    const ctx = canvas.getContext('2d');
    ctx.imageSmoothingEnabled = false;
    paint(ctx, w, h);
    cache[key] = canvas;
  }
  return cache[key];
}

const lerp = (a, b, t) => a + (b - a) * t;
const ease = (t) => t * t * (3 - 2 * t);

/**
 * One frame of the player's own sprite sheet, darkened to a silhouette with a
 * rim of moonlight down one side.
 *
 * Built once per cutscene and cached. The character in a cutscene has to be
 * *the* character -- a stick figure drawn to match reads as a different person,
 * and I tried that first. What the sheet does not have is a lying-down frame or
 * a sit-up, so the animation rotates the standing frame about the hip instead,
 * which is what sitting up is.
 */
function silhouette(cache, assets, frame, flip = false) {
  const key = `sil_${frame}_${flip ? 'f' : 'n'}`;
  if (cache[key]) return cache[key];
  if (!assets.images.has('sprites/scientist/scientist.png')
    || !assets.json.has('sprites/scientist/scientist.json')) return null;
  const atlas = assets.image('sprites/scientist/scientist.png');
  const spec = assets.data('sprites/scientist/scientist.json');
  const f = spec.frames[frame];
  if (!f) return null;

  const canvas = document.createElement('canvas');
  canvas.width = f.w;
  canvas.height = f.h;
  const c = canvas.getContext('2d');
  c.imageSmoothingEnabled = false;
  if (flip) { c.translate(f.w, 0); c.scale(-1, 1); }
  c.drawImage(atlas, f.x, f.y, f.w, f.h, 0, 0, f.w, f.h);
  // Knock him back to near-black, keeping just enough of the coat's own
  // shading to stop him being a paper cut-out.
  c.globalCompositeOperation = 'source-atop';
  c.fillStyle = 'rgba(6,6,8,0.86)';
  c.fillRect(0, 0, f.w, f.h);
  c.globalCompositeOperation = 'source-over';
  cache[key] = canvas;
  return canvas;
}

/**
 * Draw a silhouette standing on `foot`, leaning `angle` radians from upright,
 * pivoting about the hip -- about 45% of the way up from the feet.
 */
function pose(g, sprite, footX, footY, angle = 0, bob = 0, rim = null) {
  if (!sprite) return;
  const hipUp = sprite.height * 0.45;
  g.save();
  g.translate(footX, footY - hipUp + bob);
  g.rotate(angle);
  // A pixel of moonlight along his leading edge, drawn as an offset copy
  // underneath. Without it he is a hole in a dark room rather than a man in
  // one -- there is no other light on him from this side.
  if (rim) g.drawImage(rim, -sprite.width / 2 - 1, -(sprite.height - hipUp) - 1);
  g.drawImage(sprite, -sprite.width / 2, -(sprite.height - hipUp));
  g.restore();
}

/** The same frame as a flat light shape, for the rim underneath. */
function rimOf(cache, assets, frame) {
  const key = `rim_${frame}`;
  if (cache[key]) return cache[key];
  const sil = silhouette(cache, assets, frame);
  if (!sil) return null;
  const canvas = document.createElement('canvas');
  canvas.width = sil.width;
  canvas.height = sil.height;
  const c = canvas.getContext('2d');
  c.imageSmoothingEnabled = false;
  c.drawImage(sil, 0, 0);
  c.globalCompositeOperation = 'source-in';
  c.fillStyle = 'rgba(198,198,198,0.55)';
  c.fillRect(0, 0, canvas.width, canvas.height);
  cache[key] = canvas;
  return canvas;
}

// --------------------------------------------------------------------- waking

/**
 * Everything below is in the 384x216 scratch grid, measured off the bedroom
 * still: the pillow is at x=64, the bed's surface at y=136, its near edge at
 * y=155, the floor in front of it at y=192, and the window at x=236.
 */
const BED = { hipX: 112, hipY: 134, edgeX: 168, edgeY: 152, standX: 188 };
const FLOOR = 196;
const WINDOW_X = 236;

export const WAKE = {
  images: ['stills/cabin_prologue.png'],

  draw(ctx, api) {
    const { w, h, cache, phase, k, t } = api;
    const room = api.assets.images.has('stills/cabin_prologue.png')
      ? api.assets.image('stills/cabin_prologue.png') : null;
    ctx.fillStyle = '#000';
    ctx.fillRect(0, 0, w, h);
    if (room) ctx.drawImage(room, 0, 0, w, h);

    const s = scratch(cache);
    const g = s.ctx;
    const side = silhouette(cache, api.assets, 'side');
    const back = silhouette(cache, api.assets, 'back');

    // How far out of bed he is, 0..1, and how much of the bed the blanket
    // still covers. Both are continuous across the phases so nothing snaps.
    let lean = -Math.PI / 2;         // -90 degrees is flat on his back
    let hipX = BED.hipX;
    let hipY = BED.hipY;
    let blanket = 1;
    let sprite = side;
    let bob = 0;

    if (phase === 'sleep') {
      bob = Math.sin(t * 1.05) * 0.7;                     // breathing
    } else if (phase === 'stir') {
      if (api.audio) {
        // The clock. Rung from here rather than from a step so it can be a
        // bell that keeps going, not a single beep.
        const ring = Math.floor(t / 0.55);
        if (ring !== cache.lastRing && ring < 6) {
          cache.lastRing = ring;
          api.audio.play('alarm');
        }
      }
      bob = Math.sin(t * 9) * 1.4 * Math.min(1, t / 0.4);  // he flinches awake
      lean = -Math.PI / 2 + Math.min(0.18, t * 0.12);
    } else if (phase === 'sit') {
      // Sitting up: the body swings about the hip while the hip itself slides
      // to the edge of the bed.
      const e = ease(k);
      lean = lerp(-Math.PI / 2 + 0.18, 0, e);
      hipX = lerp(BED.hipX, BED.edgeX, e);
      hipY = lerp(BED.hipY, BED.edgeY, e);
      blanket = 1 - e;
      if (api.audio && !cache.rustled && k > 0.2) {
        cache.rustled = true;
        api.audio.play('paper', { gain: 0.6 });
      }
    } else if (phase === 'stand') {
      // Up off the edge and a step clear of the bed.
      const e = ease(k);
      lean = 0;
      hipX = lerp(BED.edgeX, BED.standX, e);
      hipY = lerp(BED.edgeY, FLOOR - 44, e);
      blanket = 0;
    } else if (phase === 'walk') {
      const e = ease(k);
      lean = 0;
      hipX = lerp(BED.standX, WINDOW_X, e);
      hipY = FLOOR - 44;
      blanket = 0;
      bob = [0, -1, 0, 1][Math.floor(t * 8) % 4];
      if (api.audio) {
        const step = Math.floor(t * 4);
        if (step !== cache.lastFoot) {
          cache.lastFoot = step;
          api.audio.play('walk', { gain: 0.45 });
        }
      }
    } else if (phase === 'window') {
      lean = 0;
      hipX = WINDOW_X;
      hipY = FLOOR - 44;
      blanket = 0;
      sprite = back || side;                              // he turns to the glass
      bob = Math.sin(t * 1.3) * 0.4;
    }

    if (blanket > 0) {
      // The blanket over him, falling away as he rises. Drawn from the bed's
      // surface so the shape in it is a body in a bed rather than a man on top
      // of one.
      g.fillStyle = '#0c0c0d';
      g.beginPath();
      g.moveTo(74, 152);
      g.quadraticCurveTo(120, 132 - blanket * 6, 178 - blanket * 8, 150);
      g.lineTo(178, 160);
      g.lineTo(74, 160);
      g.closePath();
      g.fill();
    }

    // Feet are 55% of the sprite below the hip; pose() takes the foot point.
    const footY = hipY + (side ? side.height * 0.55 : 48);
    pose(g, sprite, hipX, footY, lean, bob,
      rimOf(cache, api.assets, phase === 'window' ? 'back' : 'side'));

    ctx.imageSmoothingEnabled = false;
    ctx.drawImage(s.canvas, 0, 0, w, h);

    if (phase === 'walk' || phase === 'window') {
      // Moonlight off the window onto the floor he is crossing.
      const grad = ctx.createLinearGradient(0, h * 0.6, 0, h);
      grad.addColorStop(0, 'rgba(206,206,206,0.055)');
      grad.addColorStop(1, 'rgba(206,206,206,0)');
      ctx.fillStyle = grad;
      ctx.fillRect(w * 0.40, h * 0.6, w * 0.42, h * 0.4);
    }
  },
};

// ---------------------------------------------------------------- the drive

function pineStrip(ctx, w, h, { count, base, height, width, tone, seed }) {
  let n = seed;
  const rnd = () => {
    n = (n * 1103515245 + 12345) & 0x7fffffff;
    return n / 0x7fffffff;
  };
  ctx.clearRect(0, 0, w, h);
  ctx.fillStyle = tone;
  for (let i = 0; i < count; i++) {
    const cx = (i + rnd() * 0.7) * (w / count);
    const tall = height * (0.7 + rnd() * 0.6);
    const wide = width * (0.7 + rnd() * 0.5);
    const tiers = Math.max(4, Math.round(tall / 14));
    for (let tier = 0; tier < tiers; tier++) {
      const f = tier / tiers;
      const half = (wide * (1 - f * 0.8)) / 2;
      const top = base - tall * (f + 1 / tiers);
      const bottom = base - tall * f + 2;
      ctx.fillRect(Math.round(cx - half), Math.round(top),
        Math.max(1, Math.round(half * 2)), Math.max(1, Math.round(bottom - top)));
    }
    ctx.fillRect(Math.round(cx - 1), Math.round(base - tall * 0.1), 2, Math.round(tall * 0.12));
  }
}

export const DRIVE = {
  images: ['stills/parts/car_side.png'],

  /**
   * A side-on drive, because that is the view the whole game is in.
   *
   * The first attempt put a vanishing-point road under a side elevation of the
   * car, which is two incompatible cameras in one frame: the car was in profile
   * and the road was receding away from it. Everything here scrolls
   * horizontally instead -- five bands at five speeds, from a ridge that barely
   * moves to trunks that cross the frame in a third of a second. Parallax is
   * the only depth cue a flat side view gets, so it has to do all the work.
   */
  draw(ctx, api) {
    const { w, h, cache, clock } = api;
    const horizon = Math.round(h * 0.52);
    const vergeY = Math.round(h * 0.68);
    const roadY = Math.round(h * 0.74);

    const sky = surface(cache, 'sky', w, h, (c) => {
      const grad = c.createLinearGradient(0, 0, 0, horizon);
      grad.addColorStop(0, '#080808');
      grad.addColorStop(1, '#232323');
      c.fillStyle = grad;
      c.fillRect(0, 0, w, horizon);
      let n = 7;
      const rnd = () => { n = (n * 1103515245 + 12345) & 0x7fffffff; return n / 0x7fffffff; };
      for (let i = 0; i < 240; i++) {
        const v = Math.round(70 + rnd() * 120);
        c.fillStyle = `rgb(${v},${v},${v})`;
        c.fillRect(Math.round(rnd() * w), Math.round(rnd() * horizon * 0.85), 1, 1);
      }
    });

    const ridge = surface(cache, 'ridge', w, h, (c) => {
      c.fillStyle = '#1a1a1a';
      let n = 31;
      const rnd = () => { n = (n * 1103515245 + 12345) & 0x7fffffff; return n / 0x7fffffff; };
      let y = horizon - 34;
      for (let x = 0; x < w; x += 4) {
        y += (rnd() - 0.5) * 11;
        y = Math.max(horizon - 68, Math.min(horizon - 12, y));
        c.fillRect(x, Math.round(y), 4, horizon - Math.round(y) + 2);
      }
    });
    const far = surface(cache, 'far', w, h,
      (c) => pineStrip(c, w, h, { count: 30, base: horizon + 8, height: 54, width: 26, tone: '#131313', seed: 11 }));
    const mid = surface(cache, 'mid', w, h,
      (c) => pineStrip(c, w, h, { count: 16, base: vergeY + 2, height: 118, width: 50, tone: '#0a0a0a', seed: 5 }));

    // Everything moves right: he is driving left, so the road runs backwards
    // past him towards the rear of the car.
    //
    // Each layer is blitted only over the band it actually occupies. Copying
    // five full 768x432 surfaces twice each is three and a half million pixels
    // a frame of mostly transparent nothing, and it costs half the frame rate.
    const scroll = (img, speed, y0, y1) => {
      const off = Math.round((clock * speed) % w);
      const sh = Math.max(1, Math.min(h, y1) - Math.max(0, y0));
      const sy = Math.max(0, y0);
      ctx.drawImage(img, 0, sy, w, sh, off, sy, w, sh);
      ctx.drawImage(img, 0, sy, w, sh, off - w, sy, w, sh);
    };

    ctx.drawImage(sky, 0, 0);
    scroll(ridge, 7, horizon - 72, horizon + 4);
    scroll(far, 38, horizon - 58, horizon + 12);
    scroll(mid, 104, vergeY - 126, vergeY + 6);

    // The verge, then the tarmac. Two flat bands: in a side view the road has
    // no perspective to give, so it gets tone and texture instead.
    ctx.fillStyle = '#0e0e0e';
    ctx.fillRect(0, vergeY, w, roadY - vergeY);
    const road = ctx.createLinearGradient(0, roadY, 0, h);
    road.addColorStop(0, '#222222');
    road.addColorStop(0.45, '#343434');
    road.addColorStop(1, '#242424');
    ctx.fillStyle = road;
    ctx.fillRect(0, roadY, w, h - roadY);
    ctx.fillStyle = '#3c3c3c';
    ctx.fillRect(0, roadY, w, 2);

    // Grit in the surface, scrolling with it, so the tarmac is moving even
    // where there is no marking on it.
    const grit = surface(cache, 'grit', w, h, (c) => {
      let n = 77;
      const rnd = () => { n = (n * 1103515245 + 12345) & 0x7fffffff; return n / 0x7fffffff; };
      for (let i = 0; i < 900; i++) {
        const v = Math.round(38 + rnd() * 26);
        c.fillStyle = `rgba(${v},${v},${v},0.5)`;
        c.fillRect(Math.round(rnd() * w), roadY + Math.round(rnd() * (h - roadY)), 2, 1);
      }
    });
    scroll(grit, 620, roadY, h);

    // The centre line, at the speed the tarmac is actually going past.
    const dashY = roadY + Math.round((h - roadY) * 0.52);
    const gap = 170;
    const offset = (clock * 640) % gap;
    for (let x = -gap + offset; x < w + gap; x += gap) {
      ctx.fillStyle = '#8e8e8e';
      ctx.fillRect(Math.round(x), dashY, 46, 5);
    }

    // Guard-rail posts on the far shoulder, at the verge speed.
    const postGap = 96;
    const postOff = (clock * 300) % postGap;
    for (let x = -postGap + postOff; x < w + postGap; x += postGap) {
      ctx.fillStyle = '#2e2e2e';
      ctx.fillRect(Math.round(x), vergeY - 18, 4, 20);
      ctx.fillStyle = '#b4b4b4';
      ctx.fillRect(Math.round(x) - 1, vergeY - 18, 6, 3);
    }

    // The sign, once, on a schedule -- it is a beat, not scenery.
    if (clock > 7.4 && clock < 13.0) {
      const f = (clock - 7.4) / 5.6;
      const x = Math.round(w * 1.05 - f * f * w * 1.9);
      const bw = measure('BLACKRIDGE STATION') + 18;
      const bh = 42;
      const y = vergeY - 84;
      ctx.fillStyle = '#1e1e1e';
      ctx.fillRect(x + Math.round(bw * 0.46), y + bh, 5, 86);
      ctx.fillStyle = '#c9c9c9';
      ctx.fillRect(x, y, bw, bh);
      ctx.fillStyle = '#0f0f0f';
      ctx.fillRect(x + 3, y + 3, bw - 6, bh - 6);
      // The game's own bitmap font, so the sign says something. At this size
      // it is legible for about a second, which is exactly how long you get to
      // read a road sign.
      drawText(ctx, 'BLACKRIDGE STATION', x + Math.round((bw - measure('BLACKRIDGE STATION')) / 2),
        y + 10, { color: '#d2d2d2' });
      drawText(ctx, '4', x + Math.round((bw - measure('4 MILES')) / 2), y + 24, { color: '#d2d2d2' });
      drawText(ctx, ' MILES', x + Math.round((bw - measure('4 MILES')) / 2) + measure('4'),
        y + 24, { color: '#d2d2d2' });
    }

    // The car: fixed in frame, riding the road.
    const car = api.assets.images.has('stills/parts/car_side.png')
      ? api.assets.image('stills/parts/car_side.png') : null;
    if (car) {
      const cw = Math.round(w * 0.52);
      const ch = Math.round(car.height * (cw / car.width));
      // Two frequencies: the suspension, and the surface under it.
      const bob = Math.sin(clock * 5.1) * 1.4 + Math.sin(clock * 11.3) * 0.8;
      const cx = Math.round(w / 2 - cw / 2 + 26);
      const cy = Math.round(h - ch - 44 + bob);

      ctx.fillStyle = 'rgba(0,0,0,0.65)';
      ctx.fillRect(cx + 16, cy + ch - 4, cw - 32, 7);
      ctx.imageSmoothingEnabled = false;
      ctx.drawImage(car, cx, cy, cw, ch);

      // Headlights, dropping onto the road ahead. Built once into its own
      // surface: the beam is the same shape every frame and only moves with
      // the car, and a hundred gradients a frame is most of a frame's budget.
      const lampX = cx + Math.round(cw * 0.05);
      const lampY = cy + Math.round(ch * 0.62);
      const beamH = 220;
      const beam = surface(cache, 'beam', lampX + 4, beamH, (c) => {
        for (let x = lampX; x >= 0; x -= 2) {
          const run = (lampX - x) / lampX;
          const centre = beamH * 0.18 + run * lampX * 0.36;
          const spread = 6 + run * 70;
          const amount = (1 - run * 0.8) ** 1.6 * 0.40;
          const grad = c.createLinearGradient(0, centre - spread * 0.5, 0, centre + spread);
          grad.addColorStop(0, 'rgba(0,0,0,0)');
          grad.addColorStop(0.4, `rgba(200,200,200,${amount.toFixed(3)})`);
          grad.addColorStop(1, 'rgba(0,0,0,0)');
          c.fillStyle = grad;
          c.fillRect(x, centre - spread * 0.5, 2, spread * 1.5);
        }
      });
      ctx.save();
      ctx.globalCompositeOperation = 'lighter';
      ctx.drawImage(beam, 0, Math.round(lampY - beamH * 0.18));
      ctx.restore();
      ctx.fillStyle = '#f2f2f2';
      ctx.fillRect(lampX - 5, lampY - 5, 8, 8);
    }

    // Trunks crossing between the camera and the car, a third of a second
    // each. Nothing else in the frame moves quickly, because everything else
    // is far away; these are what make the speed believable.
    //
    // Spaced and sized off an index hash rather than evenly: three identical
    // bars at a constant pitch stop reading as trees and start reading as the
    // frame of a window.
    const span = 1180;
    const travelled = clock * 1150;
    const first = Math.floor(travelled / span) - 1;
    for (let i = first; i < first + 4; i++) {
      const seed = Math.abs(Math.sin(i * 12.9898) * 43758.5453) % 1;
      const x = i * span + seed * span * 0.8 - travelled + w;
      if (x < -40 || x > w + 40) continue;
      const wide = Math.round(7 + seed * 16);
      const foot = roadY + Math.round(10 + seed * 26);
      ctx.fillStyle = '#000';
      ctx.fillRect(Math.round(x), 0, wide, foot);
      ctx.fillStyle = 'rgba(170,170,170,0.10)';
      ctx.fillRect(Math.round(x) + wide - 2, 0, 2, foot);
      // A few branches, so the near trees are not fence posts.
      ctx.fillStyle = '#000';
      for (let b = 0; b < 5; b++) {
        const by = Math.round(h * (0.06 + b * 0.11) + seed * 30);
        const reach = Math.round(18 + seed * 40 - b * 2);
        ctx.fillRect(Math.round(x) - reach, by, reach + wide, Math.max(2, Math.round(5 - b * 0.6)));
        ctx.fillRect(Math.round(x), by + 6, reach, Math.max(2, Math.round(4 - b * 0.5)));
      }
    }
  },
};

export const SCENE_FX = { wake: WAKE, drive: DRIVE };

/** Every image any painter needs, for the boot manifest. */
export function fxImages() {
  const out = new Set();
  for (const fx of Object.values(SCENE_FX)) for (const i of fx.images || []) out.add(i);
  return [...out];
}
