/* Milestone 1 writing: VESTA's lines, the crew's mail, objectives and flavour text. */

export const VESTA_ROOMS: Record<string, string> = {
  cabin: 'Your quarters, Specialist. Unchanged since you went under. I dusted.',
  'r-corridor': 'Deck Two, crew. Most of the crew are still in revival. Please keep your voice down; they will not hear you, but it is a habit.',
  lounge: 'Recreation lounge. The music library is open to waking crew.',
  galley: 'Galley and mess. The coffee is real. The eggs are not.',
  med: 'Medical bay. Doctor Varga is still in revival. Please do not touch the surgical arm.',
  gym: 'Gymnasium and showers. Muscle atrophy after long cryo is normal. Walk it off.',
  arbor: 'The arboretum. Forty thousand seed lines for Haven. These are the few we let grow.',
  'c-corridor': 'Deck One, command.',
  bridge: 'The bridge. Opening the blinders. Orbital insertion is complete; we are four hundred and ten kilometres above KX-7c.',
  dome: 'Observation dome. The telescope is calibrated for surface survey.',
  comms: 'Comms and navigation. The signal is still playing. It has not stopped for thirty-one hours.',
  ready: "The captain's ready room. She has not slept in it.",
  briefing: 'Briefing room. Survey plan drafts are on the wall display.',
  's-corridor': 'Deck Three, science.',
  lab: 'Your laboratory. It has been waiting a long time for something to study.',
  specimen: 'Specimen containment. Currently empty. Protocol Seven requires it to stay that way until decontamination is verified.',
  lifesupport: 'Life support. Everything you are breathing passes through this room twice an hour.',
  workshop: "Workshop and armory. Firearms are released on the captain's authority only.",
  spine: 'Main spine. Cryo Vault Three is to port. The hangar is aft.',
  vault: 'Cryo Vault 3, the nursery. A hundred and forty-four sleepers in this section. Two did not survive the flare. The snow is condensation from the cooling plant. It is harmless, and I find it beautiful.',
  sleepbay: 'Crew sleep bay. Fourteen pods, in pairs, as the charter intended. Captain Hale\'s pod has been sealed. I am sorry.',
  suitroom: 'Suit room. Your suit has been pressure-tested. Please do not take the helmet off on the surface.',
  decon: 'Decontamination airlock. The cycle takes ninety seconds. Please do not skip it.',
  hangar: 'Hangar bay. The Kestrel is fuelled and cradled. The Mule is in standby.',
};

export interface Mail {
  id: string;
  from: string;
  subject: string;
  date: string;
  body: string[];
}

export const MAIL: Mail[] = [
  {
    id: 'revival',
    from: 'VESTA',
    subject: 'Revival notice',
    date: 'Day 2,214 · 00:40',
    body: [
      'Specialist, you were revived early, in the crew sleep bay on Deck 3. This is a summary of what you missed.',
      'Day 2,213, 03:12: a stellar flare struck the Meridian while the collector sails were deployed. Port collectors three and four were destroyed. Twelve cryo pods failed. Captain Elias Hale did not survive; his pod caught fire.',
      'Day 2,213, 11:50: during sail repairs, Comms detected a voice broadcasting from KX-7c, an uncharted world 0.2 light-years from our route. It is humming. It has not stopped.',
      'Acting Captain Adaeze Okonkwo ordered a diversion. We achieved orbit at 22:05. You were revived because a survey requires a xenobiologist.',
      'Your cryo recovery is at ninety-four percent. Drink water.',
    ],
  },
  {
    id: 'captain',
    from: 'Capt. Adaeze Okonkwo',
    subject: 'Welcome back',
    date: 'Day 2,214 · 05:58',
    body: [
      "I know this isn't Haven. I know half of you think I'm wrong. Seven more years in the pods, or a planet with breathable air right under us. I had to look.",
      'Survey first, decide second. Nobody lands until Hollis finishes pre-flight and I have your read on that world. Start with the telescope in the dome, then come find the orbital map on the bridge.',
      'And Specialist: Hale trusted you. So do I.',
      '— Ada',
    ],
  },
  {
    id: 'sails',
    from: 'Kofi Mensah',
    subject: 'Sails',
    date: 'Day 2,214 · 02:31',
    body: [
      'Port collectors 3 and 4 are shredded. You can see them from the gym window; it is not pretty. Starboard is holding. Recharge is at 61%.',
      "We'll make Haven. We'll just make it slower. Do not touch anything gold-coloured.",
      '— K',
    ],
  },
  {
    id: 'charter',
    from: 'Haven Colonial Trust',
    subject: 'Mission charter · excerpt',
    date: 'Pre-launch · archived',
    body: [
      'PROTOCOL 7. No crew member shall bring biological material from an uncharted world aboard a Trust vessel without full decontamination, sealed containment and the medical officer’s sign-off.',
      'PROTOCOL 7.2. The safety of sleeping colonists outranks the safety of waking crew.',
      'PROTOCOL 7.3. The ship’s systems will enforce these rules if the crew does not.',
    ],
  },
  {
    id: 'range',
    from: 'Yuki Tanabe',
    subject: 'Range day',
    date: 'Day 2,214 · 04:12',
    body: [
      "Armory's locked until the captain says otherwise. Come find me when you're upright and I'll walk you through the carbine.",
      "You probably won't need it. There's nothing alive down there, VESTA says. No birds, no insects, nothing on the scopes.",
      "Which is weird, right? It's a whole green planet.",
    ],
  },
  {
    id: 'signal',
    from: 'Comms log',
    subject: 'Signal transcript · KX-7c',
    date: 'Day 2,213 – ongoing',
    body: [
      'SOURCE: surface, northern continent, approx. 61°N.',
      'CARRIER: none matching any human standard.',
      'CONTENT: a human voice, female, humming. Melody unidentified; consistent with a folk lullaby.',
      'DURATION: continuous since detection. The melody repeats every 38 seconds. Each repeat varies very slightly, as if someone is still learning it.',
      'Listen at the Comms & Nav console, Deck 1.',
    ],
  },
];

export interface Objective {
  id: string;
  text: string;
}

export const OBJECTIVES: Objective[] = [
  { id: 'getup', text: 'Climb out of your pod. Press Space.' },
  { id: 'mail', text: 'Read your messages at the cabin terminal.' },
  { id: 'telescope', text: 'Survey KX-7c with the telescope in the observation dome (Deck 1).' },
  { id: 'orbitalMap', text: 'Check the orbital map on the bridge (Deck 1, forward).' },
  { id: 'kestrel', text: 'Inspect the Kestrel in the hangar (Deck 3, aft through the spine).' },
];

export const FREE_ROAM = 'Free time. Explore the Meridian. Sleep in your bunk to save.';

export const FLAVOR: Record<string, string> = {
  photo: 'You and Sam, the night before launch. Sam is still asleep two pods over, and will stay that way until Haven.',
  garden: 'The vertical garden. Herbs, lettuce, a stubborn chilli plant. It slopes up the wall so the crew can eat with something green in view.',
  trophy: 'An empty specimen shelf. You built it for Haven. Something tells you it will not stay empty.',
  captainlog: "Captain's log. Locked to Okonkwo's biometrics.\nThe last entry is timestamped four minutes ago.",
  hood: 'Fume hood. Filters at 100%. Nothing to analyse yet.',
  workbench: 'Workbench. Tools, a half-built drone, and a note in Yuki’s handwriting: "do NOT reorganise".',
  treadmill: 'You run for a while. Cryo legs. Your heart is pounding harder than it should.',
  'Containment tank · empty': 'Containment tank. Empty, sterile, 4 °C. Rated for anything up to a large dog.',
};

export const PLANET_FACTS = [
  ['Designation', 'KX-7c · "Verdance"'],
  ['Altitude', '410.2 km'],
  ['Orbital period', '40 min (ship)'],
  ['Surface gravity', '0.94 g'],
  ['Atmosphere', 'N₂ 77% · O₂ 19.4% · breathable'],
  ['Day length', '31 h 12 m'],
  ['Moons', '2'],
  ['Fauna detected', 'None'],
] as const;
