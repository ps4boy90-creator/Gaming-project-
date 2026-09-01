import { ENTITY_TYPES, entityBox, isActive } from './entities.js';
import { aabb } from './collision.js';
import { prompt as drawPrompt } from './ui.js';

// The painted rooms are drawn in perspective, so a desk surface sits well
// above the foreground floor the character walks on. The reach is deliberately
// generous upward so reading a note on a desk does not require pixel-perfect
// positioning.
const REACH = 26;

/**
 * What each entity type does when the player presses the interact key.
 *
 * `api` carries the systems a behaviour is allowed to touch: flags, journal,
 * reader, dialogue, audio, and the game itself for scene changes and saving.
 * Keeping the behaviours in one table -- rather than scattered through the
 * game loop -- means the list of what an entity can do is readable at a glance.
 */
export const BEHAVIOURS = {
  door(entity, api) {
    const p = entity.props;
    if (p.requiresFlag && !api.flags.has(p.requiresFlag)) {
      api.audio.play('locked');
      api.dialogue.say(p.lockedText || "It won't open.", { portrait: 'worried' });
      return;
    }
    if (p.setsFlag) api.flags.set(p.setsFlag);
    if (p.sound && p.sound !== 'none') api.audio.play(p.sound);
    api.game.travel(p.to, p.spawn);
  },

  note(entity, api) {
    const p = entity.props;
    api.audio.play('paper');
    api.reader.show({ title: p.title, pages: p.pages }, () => {
      api.journal.addNote({ id: entity.id, title: p.title, pages: p.pages });
      if (p.setsFlag) api.flags.set(p.setsFlag);
      if (p.once) entity.removed = true;
    });
  },

  terminal(entity, api) {
    const p = entity.props;
    if (p.requiresFlag && !api.flags.has(p.requiresFlag)) {
      api.audio.play('locked');
      api.dialogue.say(p.lockedText || 'Nothing responds.', { portrait: 'worried' });
      return;
    }
    api.audio.play('terminal');
    api.reader.show({ title: p.title, pages: p.pages, portrait: p.portrait }, () => {
      api.journal.addNote({ id: entity.id, title: p.title, pages: p.pages, source: 'terminal' });
      // The flag lands only after the last page closes, so the player has
      // genuinely seen what unlocked the way forward.
      if (p.setsFlag) api.flags.set(p.setsFlag);
    });
  },

  item(entity, api) {
    const p = entity.props;
    api.audio.play('pickup');
    api.journal.addItem({ id: entity.id, name: p.name, description: p.description });
    if (p.setsFlag) api.flags.set(p.setsFlag);
    api.dialogue.say(p.line || `Took the ${String(p.name).toLowerCase()}.`, { portrait: 'neutral' });
    entity.removed = true;
  },

  prop(entity, api) {
    const p = entity.props;
    if (!p.examine) return;
    api.dialogue.say(p.examine, { portrait: 'neutral' });
  },

  save_point(entity, api) {
    api.audio.play('save');
    api.game.save();
    api.dialogue.say(entity.props.line || 'Progress recorded.', { portrait: 'resolute' });
  },
};

/** Can this entity be interacted with right now? */
export function canInteract(entity, flags) {
  if (entity.removed) return false;
  const def = ENTITY_TYPES[entity.type];
  if (!def || !def.interactive) return false;
  if (entity.type === 'prop' && !entity.props.examine) return false;
  return isActive(entity, flags);
}

/**
 * Finds what the player is standing next to and draws the prompt over it.
 * Nearest-by-centre rather than first-match, so standing between a note and a
 * door reliably offers whichever is actually closer.
 */
export class Interaction {
  constructor() {
    this.target = null;
  }

  update(player, entities, flags) {
    const reach = {
      x: player.box.x - REACH,
      y: player.box.y - REACH,
      w: player.box.w + REACH * 2,
      h: player.box.h + REACH * 1.6,
    };

    let best = null;
    let bestDist = Infinity;
    for (const entity of entities) {
      if (!canInteract(entity, flags)) continue;
      const box = entityBox(entity);
      if (!aabb(reach, box)) continue;
      const dx = entity.x - player.x;
      // Vertical distance is weighted down: a note on a desk and a note on the
      // floor are both "right here" to a standing character.
      const dy = (box.y + box.h / 2) - (player.y - player.body.h / 2);
      const dist = dx * dx + dy * dy * 0.35;
      if (dist < bestDist) {
        bestDist = dist;
        best = entity;
      }
    }
    this.target = best;
    return best;
  }

  fire(api) {
    if (!this.target) return false;
    const behaviour = BEHAVIOURS[this.target.type];
    if (!behaviour) return false;
    behaviour(this.target, api);
    return true;
  }

  draw(ctx, camera) {
    if (!this.target) return;
    const box = entityBox(this.target);
    const label = this.target.props.prompt || 'Use';
    drawPrompt(ctx, label, box.x + box.w / 2 - camera.drawX, box.y - 3 - camera.drawY);
  }
}

/**
 * Trigger zones fire on entry rather than on a key press: monologue as he
 * walks into a room, a flag when he crosses a threshold, a cutscene at the
 * gate. `once` triggers remember they fired via a per-scene set.
 */
export function updateTriggers(player, entities, flags, api, fired) {
  for (const entity of entities) {
    if (entity.type !== 'trigger' || entity.removed) continue;
    const p = entity.props;
    if (p.requiresFlag && !flags.has(p.requiresFlag)) continue;
    const key = entity.id;
    const inside = aabb(player.box, entityBox(entity));

    if (!inside) {
      if (!p.once) fired.delete(key);
      continue;
    }
    if (fired.has(key)) continue;
    fired.add(key);

    if (p.setsFlag) flags.set(p.setsFlag);
    if (p.line) api.dialogue.say(p.line, { portrait: p.portrait });
    if (p.shake) api.camera.shake(p.shake);
    if (p.sound) api.audio.play(p.sound);
    if (p.cutscene) api.game.playCutscene(p.cutscene);
  }
}
