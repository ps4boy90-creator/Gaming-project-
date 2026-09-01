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

`view` is a window onto the still, in the still's own pixels; a `384×216` window
is a 1:1 crop and anything larger is zoomed out. A step may set several things at
once. `duration: 0` applies instantly and moves on; `waitForKey: true` holds.
Every cutscene image is preloaded at boot, because a cutscene fires mid-step from
a trigger with no chance to await a load.
