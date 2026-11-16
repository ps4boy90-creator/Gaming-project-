# Explosion Comparison · 02 — RPG-7 (PG-7V HEAT rocket) vs. a brick wall

Second segment of the series: "Ghost Man" (the transparent figure) shoulders an RPG-7, fires a
PG-7V rocket at a one-brick-thick wall 30 m away, and the camera shows what the warhead does.
Everything is procedural (Blender as a Python module, Cycles) and shares the outdoor range,
figure, render setup and post tools with [`../grenade-explosion`](../grenade-explosion).

| # | Shot | What it shows | Speed |
|---|------|---------------|-------|
| 1 | `card`   | RPG-7 with a loaded PG-7V on a studio backdrop + spec panel | – |
| 2 | `fire`   | Ghost Man aims, fires; launch flash, backblast and dust behind him | real time, then 10× slow |
| 3 | `follow` | Chase camera beside the rocket: fins spring open, the motor lights ~10 m out | ~57× slow |
| 4 | `impact` | The warhead hits the wall: flash, soot, brick dust, flying bricks | 10× → 5× slow |
| 5 | `behind` | Same hit from behind the wall: jet, spall cloud and bricks come out the far side | 10× slow |
| 6 | `after`  | Aftermath: the scorched breach, then a crane up over the debris field | real time |

## Files

- `rconst.py` — shared geometry and timing (wall, launcher line, rocket kinematics).
- `rpg7.py` — the models, built from public dimensions and reference photos: launcher (40 mm tube,
  950 mm, muzzle ring, iron sights, trigger group and pistol grip, rear grip, wooden heat shield with
  steel bands, blast bell, PGO-7 optical sight, sling) and the PG-7V round in flight configuration
  (fuze cap, conical nose, 85 mm body, nozzle block with six nozzles, motor tube, stabiliser tube,
  four fins, tail turbine, tracer).
- `wall.py` — brick wall made of ~1 570 individual bricks with their mortar (215 × 102.5 × 65 mm
  bricks, 10 mm joints, two stretcher wythes); the breach removes / snaps / loosens bricks, scorches
  the struck face and throws the removed bricks as tumbling debris with one bounce, plus small chips.
- `rsim.py` — two Mantaflow gas sims baked to OpenVDB: `launch` (backblast, muzzle puff, ground dust)
  and `impact` (fireball and soot on the face, brick dust, jet and spall cloud through the breach;
  the wall with its hole is a collision object).
- `rshots.py` — stage, firing stance and recoil for the figure, rocket exhaust (fog-volume smoke
  trail in age bands + flame sheath), lights, the six shots, frame renderer.
- `rpost.py` — 1080p master, title card, HUD (speed / distance / time read-outs, callouts), sound.
- `render_all.sh` — bakes the sims if needed, renders every shot (resumable) and runs post.

```
./render_all.sh <frames_root> <sim_root> [out.mp4]
```

## Numbers used

RPG-7: 40 mm launch tube, 950 mm long, 6.3 kg empty. PG-7V: 85 mm HEAT warhead, launched at about
115 m/s by the booster charge, sustainer motor ignites roughly 10 m from the muzzle and takes the
rocket towards ~300 m/s; effective range about 330 m; rated penetration 260 mm of steel armour.
In this scene the wall is 30 m away, so the rocket arrives after ~0.23 s at ~160 m/s.

The size of the breach and the debris throw are what this simulation produces for a 215 mm
unreinforced brick wall; they are an illustration, not test data.
