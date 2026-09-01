import { drawText, drawParagraph, wrap, lineHeight, charWidth, measure } from '../gfx/text.js';

export const INK = '#e8e6dc';
export const INK_DIM = '#9a9689';
export const PANEL_BG = 'rgba(10,11,17,0.90)';
export const PANEL_EDGE = '#4a4b58';
export const ACCENT = '#c9a44c';

/** A framed panel: filled body, hairline border, and a darker inner shadow line. */
export function panel(ctx, x, y, w, h, { bg = PANEL_BG, edge = PANEL_EDGE } = {}) {
  ctx.fillStyle = bg;
  ctx.fillRect(x, y, w, h);
  ctx.fillStyle = edge;
  ctx.fillRect(x, y, w, 1);
  ctx.fillRect(x, y + h - 1, w, 1);
  ctx.fillRect(x, y, 1, h);
  ctx.fillRect(x + w - 1, y, 1, h);
  ctx.fillStyle = 'rgba(0,0,0,0.35)';
  ctx.fillRect(x + 1, y + 1, w - 2, 1);
}

/** A small caption bubble above a world position, used for interaction prompts. */
export function prompt(ctx, text, screenX, screenY, { key = 'E' } = {}) {
  const label = `${key}  ${text}`;
  const w = measure(label) + 10;
  const h = lineHeight() + 6;
  const x = Math.round(screenX - w / 2);
  const y = Math.round(screenY - h);
  panel(ctx, x, y, w, h, { bg: 'rgba(10,11,17,0.86)' });
  drawText(ctx, key, x + 5, y + 4, { color: ACCENT });
  drawText(ctx, text, x + 5 + charWidth() * 3, y + 4, { color: INK });
}

/** Centre-anchored single line, for titles and cutscene cards. */
export function centered(ctx, text, y, width, opts = {}) {
  drawText(ctx, text, Math.round((width - measure(text)) / 2), y, opts);
}

/**
 * The journal: everything found so far. Two columns -- notes on the left,
 * objects on the right -- with the selected note's pages filling the body.
 */
export function drawJournal(ctx, journal, state, w, h) {
  ctx.fillStyle = 'rgba(6,7,11,0.94)';
  ctx.fillRect(0, 0, w, h);

  drawText(ctx, 'JOURNAL', 12, 10, { color: ACCENT });
  drawText(ctx, 'ESC to close   UP/DOWN to select', 12, h - 14, { color: INK_DIM });

  const listW = 118;
  panel(ctx, 8, 22, listW, h - 42);

  if (journal.notes.length === 0) {
    drawText(ctx, 'Nothing yet.', 14, 30, { color: INK_DIM });
  }
  journal.notes.forEach((note, i) => {
    const y = 28 + i * lineHeight();
    if (y > h - 50) return;
    const selected = i === state.index;
    if (selected) {
      ctx.fillStyle = 'rgba(201,164,76,0.18)';
      ctx.fillRect(10, y - 2, listW - 4, lineHeight());
    }
    const title = note.title.length > 17 ? `${note.title.slice(0, 16)}.` : note.title;
    drawText(ctx, title, 14, y, { color: selected ? ACCENT : INK });
  });

  const bodyX = listW + 16;
  const bodyW = w - bodyX - 8;
  panel(ctx, bodyX, 22, bodyW, h - 42);

  const note = journal.notes[state.index];
  if (note) {
    drawText(ctx, note.title, bodyX + 6, 28, { color: ACCENT });
    const lines = wrap(note.pages.join('\n\n'), bodyW - 12);
    drawParagraph(ctx, lines.slice(0, Math.floor((h - 60) / lineHeight())), bodyX + 6, 28 + lineHeight() + 2, { color: INK });
  }

  if (journal.items.length) {
    const y = h - 34;
    drawText(ctx, 'CARRYING:', 12, y, { color: INK_DIM });
    drawText(ctx, journal.items.map((i) => i.name).join(', '), 12 + measure('CARRYING: '), y, { color: INK });
  }
}
