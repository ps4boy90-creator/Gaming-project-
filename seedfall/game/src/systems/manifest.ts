/** Deterministic colonist manifest for cryo pod nameplates. */
const FIRST = [
  'Amara', 'Teodor', 'Ines', 'Kwame', 'Lucia', 'Ravi', 'Mei', 'Oskar', 'Farah', 'Jonah', 'Sanna', 'Diego',
  'Leilani', 'Tomasz', 'Aiko', 'Malik', 'Noor', 'Elias', 'Priya', 'Bram', 'Zofia', 'Kenji', 'Ayesha', 'Callum',
  'Yara', 'Mateo', 'Hana', 'Idris', 'Freya', 'Nikolai', 'Adaora', 'Sven', 'Rosa', 'Tariq', 'Elin', 'Joaquin',
];
const LAST = [
  'Lindqvist', 'Marsh', 'Barros', 'Mensah-Hale', 'Ferreira', 'Iyer', 'Zhou', 'Nyberg', 'Haddad', 'Okafor', 'Virtanen',
  'Delgado', 'Kahale', 'Wiśniewski', 'Tanaka', 'Rahman', 'Sato', 'Varga', 'Ostrowski', 'Achebe', 'Moreau', 'Kowal',
  'Hussain', 'MacLeod', 'Abara', 'Quispe', 'Novak', 'Brandt-Ito', 'Solberg', 'Petrov', 'Eze', 'Halvorsen',
];
const JOBS = [
  'hydrologist', 'soil chemist', 'structural engineer', 'agronomist', 'paediatric nurse', 'geologist',
  'teacher', 'machinist', 'botanist', 'electrician', 'surgeon', 'mycologist', 'water engineer', 'baker',
  'cartographer', 'midwife', 'carpenter', 'veterinarian', 'atmospheric chemist', 'welder', 'archivist',
  'seed-bank technician', 'mechanic', 'beekeeper (no bees yet)', 'logistics officer', 'potter',
];

function rng(seed: number): () => number {
  let s = (seed * 2654435761) >>> 0;
  return () => {
    s = (s ^ (s << 13)) >>> 0;
    s = (s ^ (s >>> 17)) >>> 0;
    s = (s ^ (s << 5)) >>> 0;
    return s / 4294967296;
  };
}

export function colonist(pod: number, failed: boolean): string {
  const r = rng(pod + 101);
  const name = `${FIRST[Math.floor(r() * FIRST.length)]} ${LAST[Math.floor(r() * LAST.length)]}`;
  const age = 19 + Math.floor(r() * 44);
  const job = JOBS[Math.floor(r() * JOBS.length)];
  const id = String(pod).padStart(4, '0');
  if (failed) {
    return `POD ${id} · ${name}, ${age} · ${job}\nStatus: deceased · flare event, day 2,213. Next of kin: pod ${String(pod + 1).padStart(4, '0')}.`;
  }
  const temp = (2.8 + r() * 0.6).toFixed(1);
  const fam = r() < 0.45 ? ` Family: pods ${String(pod + 1).padStart(4, '0')}–${String(pod + 2).padStart(4, '0')}.` : '';
  return `POD ${id} · ${name}, ${age} · ${job}\nStatus: stable · ${temp} °C · dreaming (EEG theta).${fam}`;
}
