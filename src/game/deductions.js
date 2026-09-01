/**
 * What the player works out, and what it takes to work it out.
 *
 * A flag opening a door is fine for a keycard and wrong for a mystery: it makes
 * the player hunt for one specific object instead of understanding something.
 * Here, evidence accumulates and a *realization* fires once enough of it is in.
 *
 * Each deduction lists more clues than it needs (`needed` of `requires`), so no
 * single missable object can wedge the game, and two players can reach the same
 * conclusion by different routes.
 *
 * The clue flags themselves are set by `clue`, `note`, `terminal` and `item`
 * entities in the scene files -- all authored in the editor, none in code.
 */
export const DEDUCTIONS = [
  {
    id: 'nobody_left',
    title: 'Nobody left the building',
    requires: ['clue_cars', 'clue_signin', 'clue_coats', 'clue_gate_open'],
    needed: 3,
    line: "Thirty-one signed in. Nobody signed out. Every car is still in the lot and their coats are still on the hooks.",
    portrait: 'worried',
    setsFlag: 'knows_nobody_left',
    note: [
      'The barrier was up and the booth was empty. The lot is full -- I counted, near enough thirty vehicles.',
      'The ledger says thirty-one in, nothing out. Coats, bags, one umbrella still wet.',
      'They are not somewhere else. They did not go home.',
    ],
  },
  {
    id: 'stopped_0614',
    title: 'Everything stopped at 06:14',
    requires: ['clue_lobby_clock', 'clue_wristwatch', 'clue_radio', 'clue_door_log'],
    needed: 3,
    line: "The lobby clock. A watch on a desk. The door log's last line. Every one of them says six fourteen.",
    portrait: 'stern',
    setsFlag: 'knows_0614',
    note: [
      'Wall clock: 06:14. A wristwatch left on a desk: 06:14. The door log stops at 06:14:22.',
      'Clocks do not agree by accident. Whatever happened, it happened to the whole building at once.',
      'Four digits. If anything in here wants a code, I would start there.',
    ],
  },
  {
    id: 'mid_shift',
    title: 'It happened mid-shift, without warning',
    requires: ['clue_meals', 'clue_centrifuge', 'clue_cut_memo', 'clue_chair'],
    needed: 3,
    line: "Half-eaten food. A centrifuge still spinning. A sentence that stops in the middle of a word. Nobody was warned.",
    portrait: 'worried',
    setsFlag: 'knows_mid_shift',
    note: [
      'Trays still on the canteen tables, food half gone. A chair pushed back, not tucked in.',
      'A centrifuge in the lab is still running. Nine days of it.',
      "A memo on a terminal ends mid-word. There was no alarm, no evacuation, no order. They were interrupted.",
    ],
  },
  {
    id: 'the_test',
    title: 'The shutdown test caused it',
    requires: ['read_memo', 'clue_schedule', 'clue_dosimeters', 'clue_power_log'],
    needed: 3,
    line: "The shutdown test was booked for six. They were closing the aperture down. Closing it down is what opened it.",
    portrait: 'stern',
    setsFlag: 'knows_cause',
    note: [
      'The memo at home: Sublevel 3 closed pending the shutdown review.',
      "Lab schedule: APERTURE SHUTDOWN SEQUENCE, 06:00 Thursday. Fourteen minutes in, everything stops.",
      'Every dosimeter badge on the rack has gone black. Not a leak. A field, all at once, everywhere.',
    ],
  },
  {
    id: 'pulled_in',
    title: 'They were pulled through it',
    requires: ['clue_recording', 'clue_scoring', 'clue_trail', 'clue_no_bodies'],
    needed: 3,
    line: "Nothing came out. It pulled in. Everything in this building that could move went down those stairs at once.",
    portrait: 'worried',
    setsFlag: 'knows_taken',
    note: [
      'The security recording: eleven seconds, all of it toward the stairwell.',
      'Scoring on the stairwell walls, all running downward. Shoes, glasses, a badge -- a trail, in a line, going down.',
      'No bodies. No blood. Nothing burned. They were not killed here. They were taken somewhere.',
    ],
  },
  {
    id: 'survivor',
    title: 'Someone was left behind',
    requires: ['clue_barricade', 'clue_tally', 'clue_rations', 'read_vance_log'],
    needed: 3,
    line: "Nine days of tally marks on the inside of a store room door. Someone was behind that blast door when it happened.",
    portrait: 'resolute',
    setsFlag: 'knows_survivor',
    note: [
      'A store room barricaded from the inside. Water containers, ration wrappers, a lamp run down to nothing.',
      'Nine marks scratched into the paint. Nine days alone in a building this size.',
      "Margaret's handwriting. She was on Sublevel 2 when the field came up, and the blast door held.",
    ],
  },
  {
    id: 'she_followed',
    title: 'She went in after them',
    requires: ['clue_her_badge', 'read_vance_final', 'clue_aperture'],
    needed: 3,
    line: "She left her badge at the threshold so nobody could say she was taken. She walked in. She went after them.",
    portrait: 'resolute',
    setsFlag: 'knows_ending',
    note: [
      "Her badge, set down flat at the edge of the aperture. Not dropped. Placed.",
      "Her last note: 'If anyone reads this, it means the ring is still holding and someone finally came. I am not going to sit here for a tenth day.'",
      "She told me to come in early. Before the day shift. I did not listen to her, and that is the only reason I am standing here reading this.",
    ],
  },
];

/**
 * Watches the flag store and fires realizations as their evidence lands.
 *
 * It hangs off Flags.onChange rather than polling, so a realization arrives the
 * instant the last clue is filed. Firing is queued rather than immediate: the
 * caller drains the queue when the screen is free, which is what stops a card
 * from landing on top of a note the player is still reading.
 */
export class Deductions {
  constructor(deductions = DEDUCTIONS) {
    this.all = deductions;
    this.queue = [];
    this._unsubscribe = null;
  }

  /** How many of a deduction's clues are in. */
  progress(deduction, flags) {
    return deduction.requires.filter((f) => flags.has(f)).length;
  }

  isSatisfied(deduction, flags) {
    const needed = deduction.needed === undefined ? deduction.requires.length : deduction.needed;
    return this.progress(deduction, flags) >= needed;
  }

  /** Deductions whose evidence is complete but whose flag has not been set. */
  pending(flags) {
    return this.all.filter((d) => !flags.has(d.setsFlag) && this.isSatisfied(d, flags));
  }

  watch(flags) {
    this.stop();
    this._unsubscribe = flags.onChange(() => {
      for (const d of this.pending(flags)) {
        if (!this.queue.includes(d)) this.queue.push(d);
      }
    });
    // A save restored mid-investigation can already satisfy something that was
    // never announced; sweep once on attach so it is not lost.
    for (const d of this.pending(flags)) {
      if (!this.queue.includes(d)) this.queue.push(d);
    }
  }

  stop() {
    if (this._unsubscribe) this._unsubscribe();
    this._unsubscribe = null;
  }

  take() {
    return this.queue.shift() || null;
  }

  get waiting() {
    return this.queue.length > 0;
  }

  /** Which deduction a clue flag feeds. Used by the editor's flag panel. */
  static feeds(flagName) {
    return DEDUCTIONS
      .filter((d) => d.requires.includes(flagName))
      .map((d) => d.id);
  }

  /** Every clue flag any deduction listens for. */
  static allClueFlags() {
    return [...new Set(DEDUCTIONS.flatMap((d) => d.requires))].sort();
  }
}
