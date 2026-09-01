import { fxImages } from '../game/cutscene_fx.js';

/**
 * Every scene the game can travel to, and every cutscene it can play.
 *
 * Add a scene by dropping its JSON in this folder and adding one line here.
 * The editor reads this list too, so a new scene shows up in the door
 * inspector's target dropdown without any further wiring.
 */
export const SCENES = {
  cabin_bedroom: 'src/scenes/cabin_bedroom.json',
  cabin_landing: 'src/scenes/cabin_landing.json',
  cabin_drive: 'src/scenes/cabin_drive.json',
  station_gate: 'src/scenes/station_gate.json',
  station_lobby: 'src/scenes/station_lobby.json',
  office_wing: 'src/scenes/office_wing.json',
  canteen: 'src/scenes/canteen.json',
  laboratory: 'src/scenes/laboratory.json',
  security_room: 'src/scenes/security_room.json',
  stairwell: 'src/scenes/stairwell.json',
  sublevel_3: 'src/scenes/sublevel_3.json',
};

export const START_SCENE = 'cabin_bedroom';
export const START_SPAWN = 'wake';

/**
 * Cutscenes are scripted passes over a still, an animated painter, or both.
 * See game/cutscene.js for the step vocabulary and game/cutscene_fx.js for the
 * painters.
 */
export const CUTSCENES = {
  /**
   * Opens the story in the register of a 1960s anthology broadcast: third
   * person, past tense, a narrator standing above the events rather than
   * inside them. It also gives the radio treatment something to be -- without a
   * narrator framing it, the band-limited audio is a striking effect with
   * nothing explaining why the whole piece sounds transmitted.
   */
  prologue: {
    id: 'prologue',
    // Animated, not a pan across a photograph of an empty room: he is asleep in
    // it, the clock goes off, he sits up, gets out of bed and goes to the
    // window. The narration is written to the length of those movements rather
    // than the other way round.
    fx: 'wake',
    phase: 'sleep',
    ambience: 'night_cabin',
    fadeFrom: 1,
    skippable: true,
    view: { x: 40, y: 96, w: 460, h: 259 },
    steps: [
      { fadeTo: 0, duration: 2.4,
        text: 'Consider a man named Elias Hale.', style: 'narration' },
      { text: 'Thirty-eight years old. A research physicist. Nine years of the same road up the same mountain, to the same locked gate, at the same hour of the same morning.',
        style: 'narration', duration: 6.4 },

      // The clock. He has already overslept by the time it reaches him.
      { phase: 'stir', text: null, duration: 1.2 },
      { text: 'Today he will oversleep by forty minutes.', style: 'narration',
        duration: 3.2 },

      { phase: 'sit', view: { x: 20, y: 80, w: 520, h: 293 }, duration: 2.6, text: null },
      { phase: 'stand', duration: 1.4 },
      { text: 'He will spend the rest of his life being grateful for it.',
        style: 'narration', duration: 3.6 },

      // Out of bed and across to the window, the view opening out with him.
      { phase: 'walk', view: { x: 130, y: 40, w: 620, h: 349 }, duration: 3.0, text: null },
      { phase: 'window', view: { x: 210, y: 20, w: 520, h: 293 }, duration: 4.2 },
      { text: 'Forty minutes of dark road, and a building that has been waiting nine days for somebody to come back.',
        style: 'narration', duration: 5.6 },

      { text: null, duration: 0.6 },
      { view: { x: 0, y: 0, w: 768, h: 432 }, duration: 2.4 },
      { text: 'BLACKRIDGE STATION', style: 'title', duration: 3.0 },
      { text: null, duration: 0.5 },
      { fadeTo: 1, duration: 1.4 },
    ],
    then: { scene: 'cabin_bedroom', spawn: 'wake' },
  },

  /**
   * Closes it. Fired from a trigger in sublevel_3 once the last realization
   * has landed, so it can only be reached by a player who has actually
   * assembled the answer.
   */
  epilogue: {
    id: 'epilogue',
    // Two stills: he is standing at the threshold in the first and gone from
    // the second. The cross-fade between them is the only place in the game
    // where something happens to him rather than to the building.
    image: 'stills/aperture_reveal.png',
    ambience: 'basement',
    fadeFrom: 1,
    skippable: true,
    view: { x: 180, y: 90, w: 420, h: 236 },
    steps: [
      { fadeTo: 0, duration: 2.0 },
      { view: { x: 0, y: 0, w: 768, h: 432 }, duration: 12.0 },
      { text: 'Thirty-one people walked into a room on a Thursday morning, and the room kept them.',
        style: 'narration', duration: 5.2 },
      { text: 'A thirty-second stayed behind. She counted nine days on the inside of a door, wrote down everything she knew, and then went in after them.',
        style: 'narration', duration: 6.6 },
      { text: null, duration: 0.5 },
      { text: 'A thirty-third is standing at the edge of it now, holding a note that tells him to go home and tell somebody.',
        style: 'narration', duration: 6.0 },
      { text: 'He was late once, and it saved him.', style: 'narration', duration: 3.6 },
      { text: null, duration: 0.8 },
      // The cut. Slow enough to read as the room letting go of him.
      { image: 'stills/aperture_empty.png', view: { x: 120, y: 68, w: 528, h: 297 },
        duration: 4.0 },
      { view: { x: 0, y: 0, w: 768, h: 432 }, duration: 9.0,
        text: 'Whether that is mercy, or a sentence of a different kind, is not a question this station was built to measure.',
        style: 'narration' },
      { text: null, duration: 1.0 },
      { fadeTo: 1, duration: 2.4 },
    ],
  },

  /**
   * The one quiet stretch between the cabin and the building, and the only
   * moving scene in the game: three layers of forest at three speeds, a road
   * that streams past, a headlight beam on it, and the car riding the bumps.
   */
  drive: {
    id: 'drive',
    fx: 'drive',
    // The painted still stays as the fallback: if the car cut-out ever fails
    // to load, the beat plays as the picture it used to be rather than as a
    // black rectangle.
    image: 'stills/drive_night.png',
    ambience: 'driving',
    fadeFrom: 1,
    skippable: true,
    view: { x: 90, y: 50, w: 588, h: 331 },
    steps: [
      { fadeTo: 0, duration: 2.0 },
      { view: { x: 0, y: 0, w: 768, h: 432 }, duration: 4.4,
        text: 'Forty minutes of switchbacks, and not one car coming the other way.' },
      { text: null, duration: 1.0 },
      // The sign goes by at about eleven seconds in; the line lands on it.
      { text: 'Four miles. Same turning he has taken nine years running.', duration: 4.2 },
      { text: null, duration: 0.8 },
      { view: { x: 150, y: 84, w: 468, h: 263 }, duration: 4.0,
        text: "Margaret's voice on the machine, on a loop, the whole way up." },
      { text: null, duration: 1.0 },
      { fadeTo: 1, duration: 1.8 },
    ],
    then: { scene: 'station_gate', spawn: 'from_road' },
  },

  /** The most important object in the game should stop you, not be walked past. */
  aperture: {
    id: 'aperture',
    image: 'stills/aperture_reveal.png',
    ambience: 'basement',
    fadeFrom: 1,
    skippable: true,
    view: { x: 250, y: 130, w: 280, h: 157 },
    steps: [
      { fadeTo: 0, duration: 2.2 },
      { view: { x: 0, y: 0, w: 768, h: 432 }, duration: 8.0 },
      { text: 'It has been open for nine days.', duration: 3.6 },
      { text: 'Nothing about it suggests it is finished.', duration: 4.0 },
      { text: null, duration: 0.6 },
      { fadeTo: 1, duration: 1.4 },
    ],
  },

  arrival: {
    id: 'arrival',
    image: 'stills/facility_exterior_night.png',
    ambience: 'forest_night',
    fadeFrom: 1,
    // The still is 768x432 and the surface is the same size, so a view of
    // 768x432 is 1:1 and anything smaller is a push in.
    view: { x: 40, y: 150, w: 384, h: 216 },
    steps: [
      { fadeTo: 0, duration: 2.2 },
      { text: 'BLACKRIDGE STATION', style: 'title', duration: 2.6 },
      { text: null, duration: 0.4 },
      { view: { x: 190, y: 96, w: 520, h: 293 }, duration: 7.0 },
      { text: 'Forty minutes up the ridge. Same gate, same wire.', duration: 3.4 },
      { view: { x: 300, y: 150, w: 300, h: 169 }, duration: 5.0,
        text: "The barrier's up. Nobody's in the booth." },
      { text: null, duration: 0.6 },
      { fadeTo: 1, duration: 1.8 },
    ],
    // No hand-off: `drive` brings the player to the gate, and this plays there
    // as an establishing shot before they take control.
  },
};

/**
 * Every image any cutscene can need: its still, any still a step cuts to, and
 * everything the animated painters draw with. The boot loader preloads these,
 * because a cutscene fires from inside a trigger, where there is nothing to
 * await and nowhere to put a failure.
 */
export function cutsceneImages() {
  const out = new Set(fxImages());
  for (const def of Object.values(CUTSCENES)) {
    if (def.image) out.add(def.image);
    for (const step of def.steps || []) if (step.image) out.add(step.image);
  }
  return [...out];
}
