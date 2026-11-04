# SEEDFALL: browser build

The playable game, built with **three.js + TypeScript + Vite**. Everything is procedural:
textures, the planet, the ship and the sound are all generated in the browser, so there are no
asset downloads.

**Current milestone: M1 "Home".** Wake up aboard the CSV *Meridian*, walk all three decks, the
spine, the cryo vault and the hangar, sit or lie down anywhere, survey KX-7c through the
telescope, and sleep in your bunk to save.

## Run it

```bash
npm install
npm run dev          # http://localhost:5173 with hot reload
npm run build        # type-check + production build in dist/
npm run preview      # serve dist/ on http://localhost:4173
```

## Controls

| Action | Keyboard / mouse | Touch |
|---|---|---|
| Move / look | WASD / mouse | left stick / drag right side |
| Sprint / crouch / jump | Shift / C / Space | Run / Crouch buttons |
| Lean | Q / E | — |
| Use, sit, lie down | F | Use |
| Stand up | Space (or move) | Stand |
| Flashlight | L | Light |
| Pause | Esc | Menu |

If the browser refuses pointer lock, the game falls back to click-and-drag to look.

## Tests

Both scripts drive the built game in headless Chromium (Playwright). Start `npm run preview`
first.

```bash
node tests/smoke.mjs            # functional playtest, 31 checks; exits non-zero on failure
node tests/shots.mjs            # screenshots of key rooms into tests/shots/
Q=medium node tests/shots.mjs   # same, at medium quality
```

The smoke test uses the `window.__seedfall` debug hooks (`teleport`, `aim`, `step`, `flags`, …).
`step(seconds)` runs the simulation at a fixed 30 Hz without rendering, so the checks don't
depend on frame rate.

## Publish as a single page

```bash
npm run build && node scripts/publish.mjs publish/seedfall.html
```

This inlines the CSS and JS into one HTML file, which is what the shareable artifact link
serves.

## Code map

```
src/
  main.ts                 game flow, interactions, readers, lift, telescope, sleep/save
  core/                   input (keys, pointer lock, touch), events, ship clock, save/settings
  player/player.ts        first-person body: walk, sprint, crouch, lean, jump, sit, lie down
  world/collision.ts      AABB world with a spatial grid: push-out, ground, ceiling, raycast
  world/ship/
    layout.ts             the Meridian: decks 1–3, lift, spine, cryo vault, suit room, decon, hangar
    kit.ts                walls with doors and windows, rooms, light fixtures, seats, items
    props.ts, craft.ts    furniture and equipment; the Kestrel lander and the Mule lifter
    materials.ts          PBR material library;  textures.ts: procedural canvas textures
    atlas.ts              signage, posters and console screens packed into two atlases
    doors.ts, lights.ts   sliding doors; a fixed pool of point lights reassigned by distance
    exterior.ts           collector sails, trusses, drive section
  world/orbit/orbit.ts    KX-7c: cubemap-baked surface and clouds, atmosphere, sun, moons, stars, orbit
  render/pipeline.ts      render passes: interior → backdrop, optional GTAO, bloom, tone map, film finish
  audio/audio.ts          procedural audio: hum, vents, footsteps, doors, lift, music, the signal
  ui/hud.ts               HUD, readers, menus, touch controls
  systems/                story text (VESTA, mail, objectives) and the colonist manifest
```

### How the planet stays behind the ship

The interior renders first and writes depth. The orbit backdrop renders second: it follows the
camera and every vertex is pushed to the far plane, so it only shows through window openings.
The window glass is drawn last. The planet surface and clouds are baked once into cubemaps at
load, so each frame only samples textures.
