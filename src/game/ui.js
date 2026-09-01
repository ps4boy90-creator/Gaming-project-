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

export const JOURNAL_TABS = ['EVIDENCE', 'DEDUCTIONS', 'CARRYING'];

/** The rows shown on a given tab, so input and drawing agree on the count. */
export function journalRows(journal, tab) {
  if (tab === 1) return journal.deductions;
  if (tab === 2) return journal.items;
  return journal.notes;
}

/**
 * The case file. Three tabs, because the three things he accumulates are
 * different in kind: evidence is what he found, deductions are what it means,
 * and the deductions tab doubles as the objective list -- it is the only place
 * that tells the player how far into the story they actually are.
 */
export function drawJournal(ctx, journal, state, w, h) {
  ctx.fillStyle = 'rgba(6,7,11,0.94)';
  ctx.fillRect(0, 0, w, h);

  // Tab strip
  let tx = 10;
  JOURNAL_TABS.forEach((label, i) => {
    const active = i === state.tab;
    const tw = measure(label) + 12;
    if (active) {
      ctx.fillStyle = 'rgba(201,164,76,0.16)';
      ctx.fillRect(tx, 6, tw, lineHeight() + 6);
      ctx.fillStyle = ACCENT;
      ctx.fillRect(tx, 6 + lineHeight() + 5, tw, 1);
    }
    let count = journalRows(journal, i).length;
    drawText(ctx, label, tx + 6, 10, { color: active ? ACCENT : INK_DIM });
    if (count) {
      drawText(ctx, String(count), tx + 6 + measure(label) + 3, 10, { color: active ? INK : '#5c6070' });
    }
    tx += tw + 4;
  });

  drawText(ctx, 'LEFT/RIGHT tab   UP/DOWN select   ESC close', 10, h - 12, { color: INK_DIM });

  const rows = journalRows(journal, state.tab);
  const top = 26;
  const listH = h - top - 20;
  const listW = 116;
  panel(ctx, 8, top, listW, listH);

  if (rows.length === 0) {
    const empty = [
      'Nothing found yet.',
      "Nothing worked out yet.",
      'Carrying nothing.',
    ][state.tab];
    drawText(ctx, empty, 13, top + 6, { color: INK_DIM });
  }

  // Scroll the list so the selection stays visible in a long case file.
  const perPage = Math.floor((listH - 10) / lineHeight());
  const first = Math.max(0, Math.min(state.index - Math.floor(perPage / 2), rows.length - perPage));
  const start = Math.max(0, first);

  rows.slice(start, start + perPage).forEach((row, i) => {
    const index = start + i;
    const y = top + 6 + i * lineHeight();
    const selected = index === state.index;
    if (selected) {
      ctx.fillStyle = 'rgba(201,164,76,0.18)';
      ctx.fillRect(10, y - 2, listW - 4, lineHeight());
    }
    const label = row.title || row.name || '';
    const clipped = label.length > 17 ? `${label.slice(0, 16)}.` : label;
    drawText(ctx, clipped, 13, y, { color: selected ? ACCENT : INK });
  });

  const bodyX = listW + 16;
  const bodyW = w - bodyX - 8;
  panel(ctx, bodyX, top, bodyW, listH);

  const row = rows[state.index];
  if (row) {
    drawText(ctx, row.title || row.name || '', bodyX + 6, top + 6, { color: ACCENT });
    const text = row.pages ? row.pages.join('\n\n') : (row.description || '');
    const lines = wrap(text, bodyW - 12);
    const room = Math.floor((listH - lineHeight() - 12) / lineHeight());
    drawParagraph(ctx, lines.slice(0, room), bodyX + 6, top + 6 + lineHeight() + 3, { color: INK });
  }
}
