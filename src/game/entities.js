/**
 * Every placeable thing in a scene, described once.
 *
 * A single table drives three consumers: the game (how it behaves), the editor
 * (what the property form looks like), and the docs. Adding a new entity type
 * means adding one entry here -- the editor picks it up with no changes, which
 * is the whole point of keeping the schema and the behaviour together.
 *
 * Field types understood by the inspector:
 *   string | text | pages | number | bool | color | select | flag | scene | image
 */

export const ENTITY_TYPES = {
  player_start: {
    label: 'Player start',
    color: '#63d68a',
    icon: 'P',
    box: { w: 16, h: 46 },
    interactive: false,
    fields: {
      id: { type: 'string', default: 'start', help: 'Doors arrive here by this name.' },
      facing: { type: 'select', options: ['right', 'left'], default: 'right' },
    },
  },

  door: {
    label: 'Door',
    color: '#e2c15a',
    icon: 'D',
    box: { w: 20, h: 46 },
    interactive: true,
    fields: {
      to: { type: 'scene', default: '', help: 'Scene id to travel to.' },
      spawn: { type: 'string', default: 'start', help: 'player_start id in that scene.' },
      prompt: { type: 'string', default: 'Open' },
      requiresFlag: { type: 'flag', default: '', help: 'Leave empty for an unlocked door.' },
      lockedText: { type: 'text', default: "It's locked." },
      setsFlag: { type: 'flag', default: '', help: 'Set when the door is used.' },
      sound: { type: 'select', options: ['door', 'metal', 'none'], default: 'door' },
    },
  },

  note: {
    label: 'Note',
    color: '#d9d3c2',
    icon: 'N',
    box: { w: 14, h: 16 },
    interactive: true,
    fields: {
      title: { type: 'string', default: 'Note' },
      pages: { type: 'pages', default: ['...'], help: 'One entry per page.' },
      prompt: { type: 'string', default: 'Read' },
      setsFlag: { type: 'flag', default: '' },
      once: { type: 'bool', default: false, help: 'Disappear after reading.' },
    },
  },

  terminal: {
    label: 'Terminal',
    color: '#6fd3e0',
    icon: 'T',
    box: { w: 22, h: 24 },
    interactive: true,
    fields: {
      title: { type: 'string', default: 'Terminal' },
      pages: { type: 'pages', default: ['> _'] },
      prompt: { type: 'string', default: 'Use' },
      requiresFlag: { type: 'flag', default: '' },
      lockedText: { type: 'text', default: 'The screen is dead.' },
      setsFlag: { type: 'flag', default: '', help: 'Set once fully read. This is how progress unlocks.' },
      portrait: { type: 'select', options: ['', 'neutral', 'stern', 'worried', 'resolute', 'smile'], default: '' },
    },
  },

  item: {
    label: 'Item',
    color: '#e08f5a',
    icon: 'I',
    box: { w: 12, h: 12 },
    interactive: true,
    fields: {
      name: { type: 'string', default: 'Keycard' },
      description: { type: 'text', default: '' },
      prompt: { type: 'string', default: 'Take' },
      setsFlag: { type: 'flag', default: '', help: 'Doors gate on this.' },
      line: { type: 'text', default: '', help: 'Said on pickup.' },
    },
  },

  trigger: {
    label: 'Trigger zone',
    color: '#b07ae0',
    icon: 'Z',
    box: { w: 48, h: 64 },
    interactive: false,
    resizable: true,
    fields: {
      once: { type: 'bool', default: true },
      requiresFlag: { type: 'flag', default: '' },
      setsFlag: { type: 'flag', default: '' },
      line: { type: 'text', default: '', help: 'Inner monologue when entered.' },
      portrait: { type: 'select', options: ['', 'neutral', 'stern', 'worried', 'resolute', 'smile'], default: '' },
      cutscene: { type: 'string', default: '', help: 'Cutscene id to play.' },
      shake: { type: 'number', default: 0 },
      sound: { type: 'string', default: '' },
    },
  },

  light: {
    label: 'Light',
    color: '#ffd479',
    icon: 'L',
    box: { w: 10, h: 10 },
    interactive: false,
    fields: {
      color: { type: 'color', default: '#ffb457' },
      radius: { type: 'number', default: 90, min: 4, max: 640 },
      intensity: { type: 'number', default: 1, min: 0, max: 3, step: 0.05 },
      warmth: { type: 'number', default: 0.5, min: 0, max: 1, step: 0.05, help: 'How much colour the light adds back.' },
      flicker: { type: 'select', options: ['steady', 'candle', 'fluorescent', 'dying', 'pulse'], default: 'steady' },
      phase: { type: 'number', default: 0, help: 'Offsets the flicker so identical lamps differ.' },
      requiresFlag: { type: 'flag', default: '' },
    },
  },

  prop: {
    label: 'Prop',
    color: '#8fa0b8',
    icon: 'R',
    box: { w: 24, h: 24 },
    interactive: false,
    fields: {
      image: { type: 'image', default: '', help: 'Path under assets/, e.g. props/car_veridian/side.png' },
      flip: { type: 'bool', default: false },
      overPlayer: { type: 'bool', default: false },
      requiresFlag: { type: 'flag', default: '' },
      examine: { type: 'text', default: '', help: 'If set, the prop can be examined.' },
      prompt: { type: 'string', default: 'Look' },
    },
  },

  clue: {
    label: 'Clue',
    color: '#e0d06a',
    icon: 'C',
    box: { w: 16, h: 18 },
    interactive: true,
    fields: {
      title: { type: 'string', default: 'Something odd' },
      pages: { type: 'pages', default: ['...'], help: 'What he notices, one page per block.' },
      prompt: { type: 'string', default: 'Examine' },
      setsFlag: { type: 'flag', default: '', help: 'The evidence flag a deduction listens for.' },
      repeatText: { type: 'text', default: '', help: 'Said instead on a second look.' },
      evidence: { type: 'bool', default: true, help: 'File it in the journal under Evidence.' },
      portrait: { type: 'select', options: ['', 'neutral', 'stern', 'worried', 'resolute', 'smile'], default: '' },
    },
  },

  container: {
    label: 'Container',
    color: '#9a7ad0',
    icon: 'B',
    box: { w: 20, h: 22 },
    interactive: true,
    fields: {
      name: { type: 'string', default: 'Drawer' },
      prompt: { type: 'string', default: 'Open' },
      requiresFlag: { type: 'flag', default: '' },
      lockedText: { type: 'text', default: "It's locked." },
      openText: { type: 'text', default: '', help: 'Said on opening, before anything is taken.' },
      givesItem: { type: 'string', default: '', help: 'Item name. Leave empty for an empty container.' },
      itemDescription: { type: 'text', default: '' },
      itemFlag: { type: 'flag', default: '' },
      emptyText: { type: 'text', default: 'Nothing else in it.' },
      setsFlag: { type: 'flag', default: '' },
    },
  },

  keypad: {
    label: 'Keypad',
    color: '#6ad0a8',
    icon: 'K',
    box: { w: 12, h: 16 },
    interactive: true,
    fields: {
      code: { type: 'string', default: '0000', help: 'Digits the player must enter.' },
      prompt: { type: 'string', default: 'Keypad' },
      requiresFlag: { type: 'flag', default: '', help: 'What he must know before he will even try.' },
      noCodeText: { type: 'text', default: "Four digits. I don't have four digits." },
      successText: { type: 'text', default: 'The bolt draws back.' },
      wrongText: { type: 'text', default: 'Three short beeps. Not that.' },
      setsFlag: { type: 'flag', default: '', help: 'Set on the correct code -- gate the door on this.' },
    },
  },

  save_point: {
    label: 'Save point',
    color: '#7ee0b0',
    icon: 'S',
    box: { w: 16, h: 24 },
    interactive: true,
    fields: {
      prompt: { type: 'string', default: 'Rest' },
      line: { type: 'text', default: 'Progress recorded.' },
    },
  },
};

let nextId = 1;

/** A new entity with every schema default filled in. */
export function makeEntity(type, x, y) {
  const def = ENTITY_TYPES[type];
  if (!def) throw new Error(`Unknown entity type: ${type}`);
  const props = {};
  for (const [key, field] of Object.entries(def.fields)) {
    props[key] = Array.isArray(field.default) ? [...field.default] : field.default;
  }
  const entity = { type, id: `${type}_${nextId++}`, x: Math.round(x), y: Math.round(y), props };
  if (def.resizable) {
    entity.w = def.box.w;
    entity.h = def.box.h;
  }
  return entity;
}

/** Fill in any props a hand-edited or older scene file left out. */
export function hydrate(entity) {
  const def = ENTITY_TYPES[entity.type];
  if (!def) return entity;
  const props = { ...entity.props };
  for (const [key, field] of Object.entries(def.fields)) {
    if (props[key] === undefined) {
      props[key] = Array.isArray(field.default) ? [...field.default] : field.default;
    }
  }
  const out = { ...entity, props };
  if (def.resizable) {
    out.w = entity.w === undefined ? def.box.w : entity.w;
    out.h = entity.h === undefined ? def.box.h : entity.h;
  }
  return out;
}

/** World-space rectangle, used for both interaction range and editor hit-testing. */
export function entityBox(entity) {
  const def = ENTITY_TYPES[entity.type];
  const w = entity.w || (def ? def.box.w : 16);
  const h = entity.h || (def ? def.box.h : 16);
  return { x: entity.x - w / 2, y: entity.y - h, w, h };
}

/** Whether the entity should exist right now, given the flags. */
export function isActive(entity, flags) {
  const gate = entity.props && entity.props.requiresFlag;
  // Doors and terminals stay present when locked -- being refused is the point.
  if (!gate) return true;
  if (entity.type === 'door' || entity.type === 'terminal') return true;
  return flags.has(gate);
}

/** Every flag name a scene mentions, for the editor's flag browser. */
export function flagsUsed(scene) {
  const names = new Set();
  for (const e of scene.entities || []) {
    for (const key of ['requiresFlag', 'setsFlag']) {
      const v = e.props && e.props[key];
      if (v) names.add(v);
    }
  }
  return [...names].sort();
}
