/** Tiny synthesised sound effects (no audio files). */
let ctx: AudioContext | null = null;
let muted = false;

export function setMuted(m: boolean) {
  muted = m;
}
export function isMuted() {
  return muted;
}

function ac(): AudioContext | null {
  if (muted) return null;
  try {
    if (!ctx) ctx = new (window.AudioContext || (window as any).webkitAudioContext)();
    if (ctx.state === 'suspended') void ctx.resume();
    return ctx;
  } catch {
    return null;
  }
}

function tone(freq: number, dur: number, type: OscillatorType = 'sine', vol = 0.08, slide = 0, delay = 0) {
  const c = ac();
  if (!c) return;
  const t0 = c.currentTime + delay;
  const o = c.createOscillator(), g = c.createGain();
  o.type = type;
  o.frequency.setValueAtTime(freq, t0);
  if (slide) o.frequency.exponentialRampToValueAtTime(Math.max(30, freq + slide), t0 + dur);
  g.gain.setValueAtTime(0, t0);
  g.gain.linearRampToValueAtTime(vol, t0 + 0.008);
  g.gain.exponentialRampToValueAtTime(0.0001, t0 + dur);
  o.connect(g).connect(c.destination);
  o.start(t0);
  o.stop(t0 + dur + 0.02);
}

export const sfx = {
  click: () => tone(520, 0.05, 'triangle', 0.05),
  place: () => { tone(220, 0.07, 'square', 0.04); tone(330, 0.09, 'triangle', 0.05, 0, 0.03); },
  error: () => tone(160, 0.16, 'sawtooth', 0.05, -60),
  cash: () => { tone(880, 0.08, 'triangle', 0.06); tone(1320, 0.14, 'triangle', 0.06, 0, 0.07); },
  good: () => { tone(523, 0.1, 'triangle', 0.06); tone(659, 0.1, 'triangle', 0.06, 0, 0.09); tone(784, 0.18, 'triangle', 0.06, 0, 0.18); },
  bad: () => { tone(300, 0.14, 'square', 0.05, -80); tone(200, 0.22, 'square', 0.05, -60, 0.13); },
  alarm: () => { for (let i = 0; i < 3; i++) { tone(740, 0.16, 'square', 0.05, 0, i * 0.36); tone(560, 0.16, 'square', 0.05, 0, i * 0.36 + 0.18); } },
  demolish: () => tone(110, 0.14, 'sawtooth', 0.06, -50),
};
