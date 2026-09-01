import { CollisionWorld } from './collision.js';
import { Backdrop } from '../gfx/backdrop.js';
import { hydrate, isActive } from './entities.js';
import { SCENES } from '../scenes/manifest.js';

/**
 * A scene is painted backdrop layers, a list of collision rectangles, lights,
 * and entities. There is no tile grid: the reference art is hand-painted, and
 * boxes drawn over the artwork in the editor follow it far more closely than
 * any grid would.
 */
export class Scene {
  constructor(data, assets) {
    this.id = data.id;
    this.name = data.name || data.id;
    this.raw = data;
    this.size = data.size || { w: 384, h: 216 };
    this.allowJump = !!data.allowJump;
    this.ambient = data.ambient || { color: '#000010', strength: 0 };
    this.ambience = data.ambience || 'none';
    this.entities = (data.entities || []).map(hydrate);
    this.backdrop = new Backdrop(data.layers || [], assets);
    this.world = new CollisionWorld(data.collision || [], this.size);
  }

  /**
   * Scenes registered here win over the manifest. The editor uses this to
   * test-play the scene currently on its canvas without writing a file.
   */
  static overrides = new Map();

  static async loadData(id) {
    if (Scene.overrides.has(id)) return Scene.overrides.get(id);
    const path = SCENES[id];
    if (!path) throw new Error(`Unknown scene "${id}". Add it to src/scenes/manifest.js.`);
    const res = await fetch(path);
    if (!res.ok) throw new Error(`Could not load scene "${id}" from ${path} (${res.status})`);
    return res.json();
  }

  /** Image paths a scene needs, so they can all be loaded before it renders. */
  static assetsFor(data) {
    const images = (data.layers || []).map((l) => l.image);
    for (const e of data.entities || []) {
      if (e.type === 'prop' && e.props && e.props.image) images.push(e.props.image);
    }
    return [...new Set(images.filter(Boolean))];
  }

  /** Every light currently switched on, given the flags. */
  lights(flags) {
    return this.entities
      .filter((e) => e.type === 'light' && !e.removed && isActive(e, flags))
      .map((e) => ({ x: e.x, y: e.y, ...e.props }));
  }

  spawn(name) {
    const starts = this.entities.filter((e) => e.type === 'player_start');
    const match = starts.find((e) => e.props.id === name) || starts[0];
    if (!match) {
      // Better to drop the player in the middle of the room than to refuse to
      // load a scene someone is still building.
      console.warn(`Scene "${this.id}" has no player_start; using the centre.`);
      return { x: this.size.w / 2, y: this.size.h / 2, facing: 1 };
    }
    return { x: match.x, y: match.y, facing: match.props.facing === 'left' ? -1 : 1 };
  }

  /** Props that draw in the world, split by whether they occlude the player. */
  props(flags, over) {
    return this.entities.filter((e) =>
      e.type === 'prop'
      && !e.removed
      && !!e.props.overPlayer === over
      && e.props.image
      && isActive(e, flags));
  }
}
