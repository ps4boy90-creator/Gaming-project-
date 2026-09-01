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

## Add a deduction

`DEDUCTIONS` in `src/game/deductions.js`. Place clues in scenes whose flags
match `requires`, and gate a door on `setsFlag`:

```js
{
  id: 'the_ring_is_still_open',
  title: 'It never closed',
  requires: ['clue_power_log', 'clue_aperture', 'clue_field_reading'],
  needed: 2,
  line: "Nine days and the draw has not fallen by a watt.",
  portrait: 'worried',
  setsFlag: 'knows_still_open',
  note: ['...'],                  // the journal entry
}
```

Then run `python3 tools/check_scenes.py`. It will tell you if a clue is
unplaced, if nothing sets a flag you gated on, or if you have accidentally put
a deduction's evidence behind the door that deduction unlocks.

The editor's flag panel names which deduction each flag feeds, so a clue wired
to nothing is visible while you are authoring rather than during playtesting.

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

## Add a score bed

`MUSIC_PRESETS` in `src/game/music.js`. Root in Hz, how loud each layer sits,
the filter cutoff, and the range of seconds between struck notes:

```js
observation: { root: 155.6, drone: 0.05, pad: 0.02, air: 0.014,
               brightness: 1200, gap: [16, 34], octaves: [1, 2] },
```

Pitch it to survive the radio: the whole mix is high-passed at 300 Hz, so a
root below that is heard through its harmonics, which is why the drone voices
are triangles rather than sines. Then set `music` on a scene, or add it to
`AMBIENCE_TO_MUSIC` to make it the default for an ambience name.

## Tuning the radio

`src/game/radio.js`. The constants at the top are the character: `HP_HZ` and
`LP_CLEAR` set the band, `LP_DEGRADED` is where it closes to at full tension,
`HUM_HZ` is the rectifier ripple. The cabinet resonances and the valve curve are
in the constructor.

One thing to know before changing the order of the chain: the valve stage is
followed by a second band limit on purpose. Saturation fed a band-limited signal
generates intermodulation products whose difference tones land *below* the
passband — about 12 dB of bass that the first high-pass had already removed.

After any change run `node tools/render_audio.cjs` and listen, then
`node tools/verify/audio.cjs` to confirm the spectrum and that nothing clips.

## Add a cutscene

Add it to `CUTSCENES` in `src/scenes/manifest.js`, then set a trigger's
`cutscene` property to its id. Every still it can show is preloaded at boot,
step cuts included. See [SCENE_FORMAT.md](SCENE_FORMAT.md#cutscenes) for the step
vocabulary.

To animate one instead, add a painter to `SCENE_FX` in
`src/game/cutscene_fx.js` — `{ images, draw(ctx, api) }`, where `api` carries
the frame size, the current `phase`, seconds into the step, the cutscene clock,
the assets and a per-playing `cache` for prebuilt layers. Build scrolling layers
into cached canvases once and blit only the band each occupies; anything
character-sized goes through the 384×216 scratch surface so it lands on the
gameplay pixel grid.

Author the still at **768×432**, not 384×216: cutscenes render to their own
surface at twice the gameplay resolution. `tools/verify/pixels.py stills
assets/stills` holds every one of them to the same bounds — monochrome, exposed
between 14 and 120 mean, at least 24 greys, highlights not blown.

## Notes on the architecture

- **Fixed timestep.** Physics run at exactly 60 Hz (`src/core/loop.js`); the
  render pass interpolates. Walking speed is identical on any monitor.
- **One backbuffer.** Everything draws at 384×216 and is scaled once at the end
  (`src/core/screen.js`). Scaling individual sprites instead would leave uneven
  pixels wherever a sprite landed on a fractional coordinate. Cutscenes are the
  one exception: they draw to a second surface at 768×432 and `present()` blits
  whichever is active. Gameplay's path through `render()` is untouched, and
  `tools/verify/cutscenes.cjs` proves it pixel-for-pixel against a baseline.
- **Lighting is two passes.** A darkness sheet tinted by `ambient` with holes
  carved where lights fall, then the lights' own colour added back on top. That
  second pass is what makes a lamp read as *warm* rather than merely as brighter.
- **Entities are data.** They are plain objects dispatched through a behaviour
  table, not classes. A scene file is fully declarative.
- **No fail state.** There is deliberately no damage, death or timer anywhere in
  the engine. Progress is knowledge: flags, notes and items.
