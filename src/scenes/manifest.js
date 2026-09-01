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
 * Cutscenes are scripted passes over a single still. See game/cutscene.js for
 * the step vocabulary.
 */
export const CUTSCENES = {
  /**
   * Opens the story in the register of a 1960s anthology broadcast: third
   * person, past tense, a narrator standing above the events rather than
   * inside them. Played over black, which needs no art and is also the right
   * look. It also gives the radio treatment something to be -- without a
   * narrator framing it, the band-limited audio is a striking effect with
   * nothing explaining why the whole piece sounds transmitted.
   */
  prologue: {
    id: 'prologue',
    image: 'stills/cabin_prologue.png',
    ambience: 'night_cabin',
    fadeFrom: 1,
    skippable: true,
    view: { x: 60, y: 40, w: 620, h: 349 },
    steps: [
      { fadeTo: 0, duration: 1.6 },
      { view: { x: 0, y: 0, w: 768, h: 432 }, duration: 12.0 },
      { text: 'Consider a man named Elias Hale.', style: 'narration', duration: 3.4 },
      { text: 'Thirty-eight years old. A research physicist. Nine years of the same road up the same mountain, to the same locked gate, at the same hour of the same morning.',
        style: 'narration', duration: 6.2 },
      { text: 'Today he will oversleep by forty minutes.', style: 'narration', duration: 3.4 },
      { text: 'He will spend the rest of his life being grateful for it.',
        style: 'narration', duration: 4.0 },
      { text: null, duration: 0.6 },
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

  /** The one quiet stretch between the cabin and the building. */
  drive: {
    id: 'drive',
    image: 'stills/drive_night.png',
    ambience: 'forest_night',
    fadeFrom: 1,
    skippable: true,
    view: { x: 120, y: 70, w: 520, h: 293 },
    steps: [
      { fadeTo: 0, duration: 1.8 },
      { view: { x: 0, y: 0, w: 768, h: 432 }, duration: 9.0,
        text: 'Forty minutes of switchbacks, and not one car coming the other way.' },
      { text: null, duration: 0.5 },
      { text: "Margaret's voice on the machine, on a loop, the whole way up.", duration: 4.0 },
      { fadeTo: 1, duration: 1.6 },
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
 * Every still any cutscene can show, including ones a step cuts to partway
 * through. The boot loader preloads these: a cutscene fires from inside a
 * trigger, where there is nothing to await and nowhere to put a failure.
 */
export function cutsceneImages() {
  const out = new Set();
  for (const def of Object.values(CUTSCENES)) {
    if (def.image) out.add(def.image);
    for (const step of def.steps || []) if (step.image) out.add(step.image);
  }
  return [...out];
}
