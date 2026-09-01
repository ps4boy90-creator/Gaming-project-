import { GLYPHS, GLYPH_W, GLYPH_H, FALLBACK } from '../assets/font5x7.js';
import { createSurface } from '../core/screen.js';

const TRACKING = 1;   // pixels between glyphs
const LEADING = 3;    // extra pixels between lines

const atlasCache = new Map();

/**
 * Compile the whole font into one canvas in a single colour. Tinting per draw
 * call would mean a composite operation per glyph; baking one atlas per colour
 * costs a few kilobytes and makes text drawing a plain drawImage.
 */
function atlasFor(color) {
  if (atlasCache.has(color)) return atlasCache.get(color);

  const keys = Object.keys(GLYPHS);
  const surface = createSurface(keys.length * GLYPH_W, GLYPH_H);
  const { ctx } = surface;
  ctx.fillStyle = color;

  const index = new Map();
  keys.forEach((ch, i) => {
    const x = i * GLYPH_W;
    index.set(ch, x);
    GLYPHS[ch].split('/').forEach((row, y) => {
      for (let cx = 0; cx < row.length; cx++) {
        if (row[cx] === '#') ctx.fillRect(x + cx, y, 1, 1);
      }
    });
  });

  const atlas = { canvas: surface.canvas, index };
  atlasCache.set(color, atlas);
  return atlas;
}

export const charWidth = () => GLYPH_W + TRACKING;
export const lineHeight = () => GLYPH_H + LEADING;
export const measure = (text) => text.length * charWidth() - TRACKING;

/** Greedy word wrap to a pixel width. Returns an array of lines. */
export function wrap(text, maxWidth) {
  const lines = [];
  for (const paragraph of String(text).split('\n')) {
    if (paragraph === '') { lines.push(''); continue; }
    let line = '';
    for (const word of paragraph.split(' ')) {
      const candidate = line ? `${line} ${word}` : word;
      if (measure(candidate) <= maxWidth || !line) {
        line = candidate;
      } else {
        lines.push(line);
        line = word;
      }
    }
    if (line) lines.push(line);
  }
  return lines;
}

/**
 * Draw a single line. `limit` truncates to N characters, which is how the
 * typewriter reveal works without re-wrapping the text every frame.
 */
export function drawText(ctx, text, x, y, { color = '#e8e6dc', limit = Infinity } = {}) {
  const atlas = atlasFor(color);
  const str = String(text);
  let cursor = Math.round(x);
  const top = Math.round(y);
  const count = Math.min(str.length, limit);

  for (let i = 0; i < count; i++) {
    const ch = str[i];
    if (ch !== ' ') {
      const sx = atlas.index.has(ch) ? atlas.index.get(ch) : atlas.index.get(FALLBACK);
      if (sx !== undefined) {
        ctx.drawImage(atlas.canvas, sx, 0, GLYPH_W, GLYPH_H, cursor, top, GLYPH_W, GLYPH_H);
      }
    }
    cursor += charWidth();
  }
  return cursor - TRACKING - Math.round(x);
}

/** Draw wrapped lines. `limit` counts characters across the whole block. */
export function drawParagraph(ctx, lines, x, y, opts = {}) {
  let remaining = opts.limit === undefined ? Infinity : opts.limit;
  lines.forEach((line, i) => {
    if (remaining <= 0) return;
    drawText(ctx, line, x, y + i * lineHeight(), { ...opts, limit: remaining });
    remaining -= line.length;
  });
}

/** Ink-coloured drop shadow, for text that has to sit over busy artwork. */
export function drawTextShadowed(ctx, text, x, y, opts = {}) {
  drawText(ctx, text, x + 1, y + 1, { ...opts, color: opts.shadow || '#0a0a10' });
  drawText(ctx, text, x, y, opts);
}

export const totalChars = (lines) => lines.reduce((n, l) => n + l.length, 0);
