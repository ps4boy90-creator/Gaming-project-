/**
 * Everything the player has found, kept so clues can be re-read. In a game
 * with no combat this is the progression system: the only thing that changes
 * over time is what he knows.
 */
export class Journal {
  constructor() {
    this.notes = [];
    this.items = [];
    this.deductions = [];
    this.unread = 0;
  }

  addNote({ id, title, pages, source }) {
    const key = id || title;
    if (this.notes.some((n) => n.key === key)) return false;
    this.notes.push({
      key,
      title: title || 'Untitled',
      pages: Array.isArray(pages) ? pages : [String(pages || '')],
      source: source || null,
      found: Date.now(),
    });
    this.unread++;
    return true;
  }

  addItem({ id, name, description }) {
    const key = id || name;
    if (this.items.some((i) => i.key === key)) return false;
    this.items.push({ key, name: name || 'Object', description: description || '' });
    return true;
  }

  hasItem(key) {
    return this.items.some((i) => i.key === key);
  }

  hasNote(key) {
    return this.notes.some((n) => n.key === key);
  }

  /**
   * A realization. Kept apart from evidence because it is a different kind of
   * thing: evidence is what he found, a deduction is what it means. The
   * journal's Deductions tab doubles as the objective list.
   */
  addDeduction({ id, title, pages }) {
    if (this.deductions.some((d) => d.key === id)) return false;
    this.deductions.push({
      key: id,
      title: title || 'Realization',
      pages: Array.isArray(pages) ? pages : [String(pages || '')],
      found: Date.now(),
    });
    this.unread++;
    return true;
  }

  markRead() {
    this.unread = 0;
  }

  toJSON() {
    return { notes: this.notes, items: this.items, deductions: this.deductions };
  }

  load(data) {
    this.notes = (data && data.notes) || [];
    this.items = (data && data.items) || [];
    this.deductions = (data && data.deductions) || [];
    this.unread = 0;
  }
}
