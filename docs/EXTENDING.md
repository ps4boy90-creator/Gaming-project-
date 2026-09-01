# Extending the engine

## Add a scene

1. Author it in `editor.html`, **Export JSON**, and save it to `src/scenes/`.
2. Add one line to `src/scenes/manifest.js`:

```js
export const SCENES = {
  cabin_bedroom: 'src/scenes/cabin_bedroom.json',
  sublevel_3: 'src/scenes/sublevel_3.json',   // ← new
};
```

That is the only wiring. The editor reads the same list, so the new scene
immediately appears in every door's target dropdown.

## Add an entity type

Everything about an entity lives in one table: `ENTITY_TYPES` in
`src/game/entities.js`. The game reads it for behaviour, the editor generates its
property form from it, and the docs describe it. Adding a type means adding one
entry:

```js
keypad: {
  label: 'Keypad',
  color: '#8fd08f',
  box: { w: 12, h: 16 },
  interactive: true,
  fields: {
    code: { type: 'string', default: '0000' },
    prompt: { type: 'string', default: 'Enter code' },
    setsFlag: { type: 'flag', default: '' },
    wrongText: { type: 'text', default: 'Three short beeps. Wrong.' },
  },
},
```

The editor picks this up with no changes at all — a "Keypad" chip appears in the
palette and its inspector shows those four fields.

Then give it behaviour in `BEHAVIOURS` in `src/game/interaction.js`:

```js
keypad(entity, api) {
  api.audio.play('terminal');
  if (api.journal.hasItem('code_note')) {
    api.flags.set(entity.props.setsFlag);
    api.dialogue.say('It opens.', { portrait: 'resolute' });
  } else {
    api.dialogue.say(entity.props.wrongText, { portrait: 'worried' });
  }
}
```

`api` carries the systems a behaviour is allowed to touch: `flags`, `journal`,
`dialogue`, `reader`, `audio`, `camera`, and `game` for travel, cutscenes and saving.

### Field types the inspector understands

`string` · `text` (multi-line) · `pages` (blocks separated by `---`) · `number`
(with `min`, `max`, `step`) · `bool` · `color` · `select` (with `options`) ·
`flag` (autocompletes from flags in use) · `scene` (dropdown of the manifest) ·
`image` (autocompletes from known asset paths).

Add `help: '…'` to any field and it appears under the control in the editor.

## Add a light flicker profile

`FLICKER` in `src/gfx/lighting.js` maps a name to a function returning an
intensity multiplier over time:

```js
strobe: (t) => ((t * 6) % 1 < 0.5 ? 1 : 0.05),
```

Then add the name to the `flicker` field's `options` in the `light` entity
schema, and it appears in the editor's dropdown.

## Add a sound

All audio is synthesised — there are no files. Add an entry to the spec table in
`Audio.play()` (`src/game/audio.js`):

```js
alarm: { type: 'tone', freq: 740, to: 480, dur: 0.5, gain: 0.12 },
```

`noise` entries are a band-passed noise burst (footsteps, doors, paper);
`tone` entries are a swept triangle wave (beeps, pickups). For a new room tone,
add a preset to `AMBIENCE` at the top of the same file and it becomes selectable
in the editor's scene panel.

## Add a cutscene

Add it to `CUTSCENES` in `src/scenes/manifest.js`, then set a trigger's
`cutscene` property to its id. Its image is preloaded automatically at boot.
See [SCENE_FORMAT.md](SCENE_FORMAT.md#cutscenes) for the step vocabulary.

## Notes on the architecture

- **Fixed timestep.** Physics run at exactly 60 Hz (`src/core/loop.js`); the
  render pass interpolates. Walking speed is identical on any monitor.
- **One backbuffer.** Everything draws at 384×216 and is scaled once at the end
  (`src/core/screen.js`). Scaling individual sprites instead would leave uneven
  pixels wherever a sprite landed on a fractional coordinate.
- **Lighting is two passes.** A darkness sheet tinted by `ambient` with holes
  carved where lights fall, then the lights' own colour added back on top. That
  second pass is what makes a lamp read as *warm* rather than merely as brighter.
- **Entities are data.** They are plain objects dispatched through a behaviour
  table, not classes. A scene file is fully declarative.
- **No fail state.** There is deliberately no damage, death or timer anywhere in
  the engine. Progress is knowledge: flags, notes and items.
