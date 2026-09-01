/**
 * The one piece of global state the whole investigation runs on.
 *
 * Triggers, terminals and items set flags; doors, props and lights read them.
 * Because both sides are plain strings chosen in the editor, an entire chain of
 * discoveries -- read the log, find the card, open the stairwell -- can be
 * authored without writing any code. The editor's flag browser lists every
 * name referenced in a scene so a typo shows up as an orphan rather than as a
 * door that silently never opens.
 */
export class Flags {
  constructor(initial = {}) {
    this.values = { ...initial };
    this.listeners = new Set();
  }

  get(name) {
    return this.values[name];
  }

  has(name) {
    return !!this.values[name];
  }

  set(name, value = true) {
    if (!name) return;
    const before = this.values[name];
    this.values[name] = value;
    if (before !== value) {
      for (const fn of [...this.listeners]) fn(name, value, before);
    }
  }

  clear(name) {
    this.set(name, false);
  }

  onChange(fn) {
    this.listeners.add(fn);
    return () => this.listeners.delete(fn);
  }

  /**
   * Evaluate a gate on an entity. Accepts a single flag name, or an object
   * with `all` / `any` / `none` lists, so conditions can grow past one flag
   * without changing every call site.
   */
  test(condition) {
    if (!condition) return true;
    if (typeof condition === 'string') return this.has(condition);
    if (Array.isArray(condition)) return condition.every((c) => this.test(c));
    const { all, any, none } = condition;
    if (all && !all.every((f) => this.has(f))) return false;
    if (any && !any.some((f) => this.has(f))) return false;
    if (none && none.some((f) => this.has(f))) return false;
    return true;
  }

  toJSON() {
    // Only truthy flags are worth persisting; false is the default.
    return Object.fromEntries(Object.entries(this.values).filter(([, v]) => v));
  }

  load(data) {
    this.values = { ...(data || {}) };
    for (const fn of [...this.listeners]) fn(null, null, null);
  }
}
