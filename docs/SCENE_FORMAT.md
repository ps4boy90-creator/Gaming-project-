# Scene format

A scene is one JSON file in `src/scenes/`, plus one line in
`src/scenes/manifest.js`. The editor reads and writes exactly this format, so a
file can be hand-edited and reopened in the editor without losing anything.

```json
{
  "id": "cabin_bedroom",
  "name": "Cabin -- Bedroom",
  "size": { "w": 384, "h": 216 },
  "allowJump": false,
  "ambience": "night_cabin",
  "layers": [ … ],
  "collision": [ … ],
  "ambient": { "color": "#0b1030", "strength": 0.58 },
  "entities": [ … ]
}
```

| Key | Meaning |
|---|---|
| `id` | Must match the key in `manifest.js`. Doors target scenes by this. |
| `size` | The scene in native pixels. The screen is 384×216; anything larger scrolls. |
| `allowJump` | Off by default. A scientist walking a facility should feel grounded. |
| `ambience` | Name from `Audio.ambienceNames()`: `none`, `night_cabin`, `forest_night`, `facility_hum`, `basement`. |
| `music` | Optional score bed: `cabin`, `road`, `facility`, `deep`, `aperture`, `silent`. Leave it out and one is derived from `ambience`. |
| `ambient` | The colour and depth of the dark. `strength` 0 is full daylight, 1 is pitch black. |

## Layers

Painted images, drawn back to front.

```json
{ "image": "backdrops/cabin_landing/wall.png", "parallax": 1, "overPlayer": false, "repeat": false }
```

| Field | Meaning |
|---|---|
| `image` | Path under `assets/`. |
| `parallax` | Scroll rate. `1` moves with the world, `0.3` sits far away, `1.08` sits in front. |
| `parallaxY` | Vertical rate, if it should differ from `parallax`. |
| `overPlayer` | Draw after the player — doorframes, pillars, foreground posts. |
| `repeat` | Tile horizontally, so a narrow far layer can cover a wide scene. |
| `offsetX` / `offsetY` / `alpha` | Optional placement and opacity. |

## Collision

Axis-aligned rectangles drawn over the artwork. There is no tile grid: the
scenes are hand-painted, and boxes follow the painting far more closely than a
grid would.

```json
{ "x": 0, "y": 204, "w": 384, "h": 12, "type": "solid" }
```

| `type` | Behaviour |
|---|---|
| `solid` | Blocks from every direction. |
| `oneway` | Catches a fall from above only — ledges, stair landings. |
| `ladder` | Not solid; climbable while overlapped. |
| `block` | Solid, but tinted differently in the editor. For invisible walls. |

A lip up to 6px tall is stepped over automatically, so door sills and rug edges
do not stop a walk.

## Entities

Every entity is `{ type, id, x, y, props }`. **`x` is the horizontal centre and
`y` is the bottom edge** — entities are positioned by their feet, matching the
sprite origin, so a taller frame never appears to sink into the floor. Trigger
zones also carry `w` and `h`.

The full property list for every type lives in one place —
`src/game/entities.js`, in the `ENTITY_TYPES` table. The editor's inspector is
generated from it, so that table and the editor can never disagree.

| Type | What it does |
|---|---|
| `player_start` | A named spawn point. Doors arrive at one by `props.id`. |
| `door` | Travels to another scene. Optional `requiresFlag` with a `lockedText` refusal. |
| `note` | Readable pages, filed into the journal. |
| `terminal` | Multi-page screen that sets a flag once read — how investigation unlocks progress. |
| `item` | Enters the inventory and sets a flag. |
| `trigger` | A zone that fires on entry: a line of monologue, a flag, a camera shake, a cutscene. |
| `light` | Colour, radius, intensity, warmth, flicker profile. |
| `prop` | A decorative image, and/or something examinable. |
| `save_point` | Writes progress. |
| `clue` | A physical detail he *observes*. Files into the journal as evidence and sets a flag a deduction listens for. Says something shorter on a second look. |
| `container` | A drawer, locker or cabinet. Optionally gated; may yield an item once, then reads as empty. |
| `keypad` | A coded lock. The player types the digits. Sets a flag on the correct code -- gate a door on that. |

### `clue` versus `prop.examine`

Both are things you can look at, and the difference is the whole line between
atmosphere and progress:

- **`prop.examine`** is flavour. One line of monologue, nothing recorded,
  nothing unlocked. Use it freely -- a room with nothing incidental to look at
  feels like a set.
- **`clue`** is evidence. It opens the reader, files itself in the journal, and
  sets a flag that feeds a deduction. Every one of them moves the case forward.

### Deductions: how clues become progress

A door gated on a single flag makes the player hunt for one specific object.
The chain in `src/game/deductions.js` gates on *understanding* instead: each
deduction lists more clues than it needs (`needed` of `requires`), and fires a
**realization** once enough are in -- Hale says it aloud, it is filed in the
journal's Deductions tab, and its `setsFlag` opens the way forward.

```js
{
  id: 'stopped_0614',
  title: 'Everything stopped at 06:14',
  requires: ['clue_lobby_clock', 'clue_wristwatch', 'clue_radio', 'clue_door_log'],
  needed: 3,                       // any three of the four
  line: "...",
  setsFlag: 'knows_0614',          // and this is the keypad's gate
  note: ['...'],                   // what the journal records
}
```

Listing four and needing three means no single missable object can wedge the
game, and two players can reach the same conclusion by different routes.

`python3 tools/check_scenes.py` validates the whole graph: doors pointing at
real scenes and real spawns, gates nothing can open, clues no deduction listens
for, and -- the one that actually bites -- a deduction whose evidence is locked
behind the door its own flag opens.

### Flags: how an investigation is wired

Flags are plain strings. Triggers, terminals, notes and items **set** them;
doors, lights and props **gate** on them. Both sides are chosen in the editor, so
a whole chain of discoveries is authored without writing code:

> The front door is locked. Its `requiresFlag` is `heard_message`. The answering
> machine's `setsFlag` is `heard_message`, and only fires once the last page has
> been read. The player must listen before they can leave.

The editor's flag panel lists every name used in the scene and flags any that are
read but never set — usually a typo, occasionally a flag another scene sets.

## Cutscenes

Cutscenes live in `src/scenes/manifest.js`, not in scene files, because one can
be played from any scene. They are a scripted pass over a single still:

```js
arrival: {
  id: 'arrival',
  image: 'stills/facility_exterior_night.png',
  ambience: 'forest_night',
  fadeFrom: 1,
  view: { x: 40, y: 150, w: 384, h: 216 },
  steps: [
    { fadeTo: 0, duration: 2.2 },
    { text: 'BLACKRIDGE STATION', style: 'title', duration: 2.6 },
    { view: { x: 190, y: 96, w: 520, h: 293 }, duration: 7.0 },
    { text: "The barrier's up. Nobody's in the booth.", duration: 3.4 },
    { fadeTo: 1, duration: 1.8 }
  ]
}
```

`view` is a window onto the still, in the still's own pixels. Cutscenes render to
a **768×432** surface — twice the gameplay resolution — so a `768×432` window is
1:1 and anything smaller is a push in. A step may set several things at once.
`duration: 0` applies instantly and moves on; `waitForKey: true` holds.

A step may also carry `image`, which cuts to a second still by cross-fading over
that step's `duration` rather than snapping:

```js
{ image: 'stills/aperture_empty.png', view: { x: 120, y: 68, w: 528, h: 297 },
  duration: 4.0 }
```

Every still a cutscene can show is preloaded at boot — step cuts included, via
`cutsceneImages()` in the manifest — because a cutscene fires mid-step from a
trigger, where there is nothing to await and nowhere to put a failure.

Other fields: `letterbox: false` turns off the 2.39:1 bars (they are on by
default, and are most of what says the player is not in control), `skippable:
false` makes Escape do nothing, and `then: { scene, spawn }` hands off to a scene
when the cutscene ends instead of returning to the one it played over.
