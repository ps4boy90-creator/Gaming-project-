/**
 * Everything the player has found, kept so clues can be re-read. In a game
 * with no combat this is the progression system: the only thing that changes
 * over time is what he knows.
 */
export class Journal {
  constructor() {
    this.notes = [];
    this.items = [];
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

  markRead() {
    this.unread = 0;
  }

  toJSON() {
    return { notes: this.notes, items: this.items };
  }

  load(data) {
    this.notes = (data && data.notes) || [];
    this.items = (data && data.items) || [];
    this.unread = 0;
  }
}
