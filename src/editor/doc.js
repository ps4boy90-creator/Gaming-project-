import { makeEntity, hydrate, ENTITY_TYPES } from '../game/entities.js';

const AUTOSAVE_KEY = 'veridian.editor.doc';
const MAX_UNDO = 60;

export function blankScene(id = 'new_scene') {
  return {
    id,
    name: 'New scene',
    size: { w: 768, h: 216 },
    allowJump: false,
    ambience: 'none',
    layers: [],
    collision: [{ x: 0, y: 180, w: 768, h: 36, type: 'solid' }],
    ambient: { color: '#0b1030', strength: 0.5 },
    entities: [
      { ...makeEntity('player_start', 64, 180), id: 'player_start_1' },
    ],
  };
}

/**
 * The scene being edited, plus undo history.
 *
 * History is a stack of whole-document snapshots. Scenes are small -- a few
 * kilobytes of JSON -- so storing complete states is far simpler and more
 * reliable than tracking per-field deltas, and undo can never desynchronise.
 */
export class EditorDoc {
  constructor(scene = blankScene()) {
    this.scene = scene;
    this.undoStack = [];
    this.redoStack = [];
    this.dirty = false;
    this.onChange = null;
  }

  snapshot() {
    return JSON.parse(JSON.stringify(this.scene));
  }

  /** Call before any mutation you want undoable. */
  begin() {
    this.undoStack.push(this.snapshot());
    if (this.undoStack.length > MAX_UNDO) this.undoStack.shift();
    this.redoStack.length = 0;
  }

  commit() {
    this.dirty = true;
    this.autosave();
    if (this.onChange) this.onChange();
  }

  undo() {
    if (!this.undoStack.length) return false;
    this.redoStack.push(this.snapshot());
    this.scene = this.undoStack.pop();
    this.commit();
    return true;
  }

  redo() {
    if (!this.redoStack.length) return false;
    this.undoStack.push(this.snapshot());
    this.scene = this.redoStack.pop();
    this.commit();
    return true;
  }

  load(scene) {
    this.begin();
    const next = JSON.parse(JSON.stringify(scene));
    next.entities = (next.entities || []).map(hydrate);
    next.collision = (next.collision || []).map((r) => ({ type: 'solid', ...r }));
    next.layers = next.layers || [];
    next.size = next.size || { w: 768, h: 216 };
    next.ambient = next.ambient || { color: '#0b1030', strength: 0.5 };
    // Older scenes kept lights in their own array; fold them into entities so
    // the editor has exactly one kind of light to manage.
    if (Array.isArray(next.lights)) {
      next.lights.forEach((l, i) => {
        const e = makeEntity('light', l.x, l.y);
        e.id = `light_${i + 1}`;
        Object.assign(e.props, l);
        delete e.props.x;
        delete e.props.y;
        next.entities.push(e);
      });
      delete next.lights;
    }
    this.scene = next;
    this.commit();
  }

  /** The JSON the game actually reads. Editor-only keys never reach it. */
  export() {
    const s = this.snapshot();
    s.entities = s.entities.map((e) => {
      const out = { type: e.type, id: e.id, x: Math.round(e.x), y: Math.round(e.y) };
      if (ENTITY_TYPES[e.type] && ENTITY_TYPES[e.type].resizable) {
        out.w = Math.round(e.w);
        out.h = Math.round(e.h);
      }
      out.props = e.props;
      return out;
    });
    s.collision = s.collision.map((r) => ({
      x: Math.round(r.x), y: Math.round(r.y), w: Math.round(r.w), h: Math.round(r.h), type: r.type,
    }));
    return s;
  }

  autosave() {
    try {
      localStorage.setItem(AUTOSAVE_KEY, JSON.stringify(this.scene));
    } catch (err) {
      console.warn('Editor autosave failed:', err);
    }
  }

  static restore() {
    try {
      const raw = localStorage.getItem(AUTOSAVE_KEY);
      return raw ? JSON.parse(raw) : null;
    } catch (err) {
      return null;
    }
  }

  static clearAutosave() {
    try { localStorage.removeItem(AUTOSAVE_KEY); } catch (err) { /* nothing to do */ }
  }
}
