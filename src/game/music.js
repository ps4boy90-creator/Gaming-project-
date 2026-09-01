import { makeRng, clamp, lerp } from '../core/rng.js';

/**
 * A generative score: a low drone, a pad that never quite arrives, and single
 * struck notes that ring out and decay, minutes apart.
 *
 * Written rather than recorded for two reasons. A two-minute loop becomes
 * obvious within one playthrough of a game this slow; and a bed that is
 * re-rolled from a scale each time can respond to how much of the mystery the
 * player has assembled, which a file cannot.
 *
 * Everything here is pitched to survive the radio chain the whole mix runs
 * through. A 300 Hz high-pass removes the fundamentals of the drone entirely --
 * which is fine and in fact correct, because that is exactly what a small
 * speaker does. The harmonics are what you hear, so the drone voices are
 * triangle and sawtooth rather than sine, and the struck notes sit an octave or
 * two up, right in the middle of the passband.
 */

// Natural minor at rest. As tension rises the second flattens -- the note that
// makes a room feel wrong -- and eventually the tritone becomes available.
const MINOR = [0, 2, 3, 5, 7, 8, 10];
const PHRYGIAN = [0, 1, 3, 5, 7, 8, 10];
const TRITONE = 6;

// Weighted toward the root, minor third and fifth, so it reads as a key even
// though it never resolves.
const DEGREE_WEIGHTS = [4, 1, 3, 2, 4, 2, 1];

export const MUSIC_PRESETS = {
  silent: null,
  cabin: { root: 174.6, drone: 0.055, pad: 0.030, air: 0.010, brightness: 1500, gap: [14, 30], octaves: [1, 2] },
  road: { root: 146.8, drone: 0.045, pad: 0.014, air: 0.020, brightness: 1900, gap: [18, 38], octaves: [1, 2] },
  facility: { root: 164.8, drone: 0.050, pad: 0.026, air: 0.016, brightness: 1300, gap: [12, 26], octaves: [1, 2] },
  deep: { root: 130.8, drone: 0.062, pad: 0.032, air: 0.014, brightness: 1000, gap: [10, 22], octaves: [1, 2] },
  aperture: { root: 123.5, drone: 0.070, pad: 0.040, air: 0.012, brightness: 900, gap: [7, 16], octaves: [1, 2, 3] },
};

/** Scenes carry an `ambience` already; this is the sensible default score for each. */
export const AMBIENCE_TO_MUSIC = {
  none: 'silent',
  night_cabin: 'cabin',
  forest_night: 'road',
  facility_hum: 'facility',
  basement: 'deep',
};

const semitone = (root, s) => root * Math.pow(2, s / 12);

export class Music {
  constructor(ctx, destination, noiseBuffer) {
    this.ctx = ctx;
    this.noise = noiseBuffer;
    this.rng = makeRng(1954);
    this.tension = 0;
    this.presetName = 'silent';
    this.preset = null;
    this.voice = null;
    this.nextNoteIn = 6;

    this.out = ctx.createGain();
    this.out.gain.value = 1;
    this.out.connect(destination);

    // Reverb is what turns oscillators into a room with something in it. A dry
    // struck note sounds like a synthesiser; the same note with a long tail
    // sounds like a piano in a building nobody is in.
    this.reverb = ctx.createConvolver();
    this.reverb.buffer = this._impulse(3.6);
    this.reverbGain = ctx.createGain();
    this.reverbGain.gain.value = 0.35;
    this.reverb.connect(this.reverbGain).connect(this.out);
  }

  _impulse(seconds) {
    const rate = this.ctx.sampleRate;
    const len = Math.floor(rate * seconds);
    const buf = this.ctx.createBuffer(2, len, rate);
    for (let ch = 0; ch < 2; ch++) {
      const data = buf.getChannelData(ch);
      let last = 0;
      for (let i = 0; i < len; i++) {
        const t = i / len;
        // Exponential decay over lightly smoothed noise. The smoothing darkens
        // the tail, which reads as a large concrete space rather than a plate.
        const white = Math.random() * 2 - 1;
        last = last * 0.72 + white * 0.28;
        data[i] = last * Math.pow(1 - t, 2.6);
      }
    }
    return buf;
  }

  setVolume(v) {
    this.out.gain.setTargetAtTime(clamp(v, 0, 1), this.ctx.currentTime, 0.15);
  }

  /** 0 is untroubled, 1 is the aperture. */
  setTension(t) {
    this.tension = clamp(t, 0, 1);
    if (!this.voice) return;
    const now = this.ctx.currentTime;
    // The root sags by detune rather than by a key change, so there is never a
    // moment where the music audibly "switches".
    const sag = Math.pow(2, (-3 * this.tension) / 12);
    for (const d of this.voice.droneOscs) {
      d.osc.frequency.setTargetAtTime(d.base * sag, now, 6);
    }
    for (const p of this.voice.padOscs) {
      p.osc.frequency.setTargetAtTime(p.base * sag, now, 6);
    }
    this.voice.padFilter.frequency.setTargetAtTime(
      lerp(this.preset.brightness, this.preset.brightness * 0.62, this.tension), now, 6);
  }

  setPreset(name) {
    const resolved = MUSIC_PRESETS[name] === undefined ? 'silent' : name;
    if (resolved === this.presetName) return;
    this.presetName = resolved;
    this.preset = MUSIC_PRESETS[resolved];

    if (this.voice) this._fadeOut(this.voice);
    this.voice = this.preset ? this._build(this.preset) : null;
    this.nextNoteIn = this.preset ? 4 + this.rng() * 6 : Infinity;
    if (this.voice) this.setTension(this.tension);
  }

  _fadeOut(voice) {
    const now = this.ctx.currentTime;
    voice.gain.gain.setTargetAtTime(0, now, 1.2);
    setTimeout(() => {
      for (const s of voice.sources) {
        try { s.stop(); } catch (e) { /* already stopped */ }
      }
    }, 4500);
  }

  _build(preset) {
    const ctx = this.ctx;
    const now = ctx.currentTime;
    const gain = ctx.createGain();
    gain.gain.value = 0;
    gain.gain.setTargetAtTime(1, now, 2.2);
    gain.connect(this.out);

    const sources = [];
    const droneOscs = [];
    const padOscs = [];

    // --- drone: root, fifth and an octave, slightly detuned against each other
    for (const [mult, level, type] of [[1, 1, 'triangle'], [1.5, 0.55, 'triangle'], [2, 0.35, 'sine']]) {
      const base = preset.root * mult;
      const osc = ctx.createOscillator();
      osc.type = type;
      osc.frequency.value = base;
      osc.detune.value = (this.rng() * 2 - 1) * 6;
      const g = ctx.createGain();
      g.gain.value = preset.drone * level;
      // A very slow amplitude wobble so the bed breathes instead of sitting.
      const lfo = ctx.createOscillator();
      lfo.type = 'sine';
      lfo.frequency.value = 0.05 + this.rng() * 0.07;
      const depth = ctx.createGain();
      depth.gain.value = preset.drone * level * 0.4;
      lfo.connect(depth).connect(g.gain);
      lfo.start();
      osc.connect(g).connect(gain);
      osc.start();
      sources.push(osc, lfo);
      droneOscs.push({ osc, base });
    }

    // --- pad: a chord that swells and recedes and never quite arrives
    const padFilter = ctx.createBiquadFilter();
    padFilter.type = 'lowpass';
    padFilter.frequency.value = preset.brightness;
    padFilter.Q.value = 0.8;
    const padGain = ctx.createGain();
    padGain.gain.value = preset.pad;
    padFilter.connect(padGain).connect(gain);
    padFilter.connect(this.reverb);

    for (const s of [0, 3, 7]) {
      const base = semitone(preset.root * 2, s);
      const osc = ctx.createOscillator();
      osc.type = 'sawtooth';
      osc.frequency.value = base;
      osc.detune.value = (this.rng() * 2 - 1) * 9;
      const g = ctx.createGain();
      g.gain.value = 0.22;
      osc.connect(g).connect(padFilter);
      osc.start();
      sources.push(osc);
      padOscs.push({ osc, base });
    }

    // Swell: a slow LFO on the pad level, plus a slower one on the filter.
    const swell = ctx.createOscillator();
    swell.type = 'sine';
    swell.frequency.value = 1 / (22 + this.rng() * 18);
    const swellDepth = ctx.createGain();
    swellDepth.gain.value = preset.pad * 0.75;
    swell.connect(swellDepth).connect(padGain.gain);
    swell.start();
    sources.push(swell);

    const sweep = ctx.createOscillator();
    sweep.type = 'sine';
    sweep.frequency.value = 1 / (31 + this.rng() * 20);
    const sweepDepth = ctx.createGain();
    sweepDepth.gain.value = preset.brightness * 0.28;
    sweep.connect(sweepDepth).connect(padFilter.frequency);
    sweep.start();
    sources.push(sweep);

    // --- air: so the silences are not digitally dead
    const air = ctx.createBufferSource();
    air.buffer = this.noise;
    air.loop = true;
    const airBand = ctx.createBiquadFilter();
    airBand.type = 'bandpass';
    airBand.frequency.value = 1100;
    airBand.Q.value = 0.5;
    const airGain = ctx.createGain();
    airGain.gain.value = preset.air;
    air.connect(airBand).connect(airGain).connect(gain);
    air.start();
    sources.push(air);

    return { gain, sources, droneOscs, padOscs, padFilter };
  }

  /** Which scale degree to strike, weighted so it reads as a key. */
  _pickDegree() {
    const scale = this.tension > 0.45 ? PHRYGIAN : MINOR;
    let total = 0;
    for (const w of DEGREE_WEIGHTS) total += w;
    let r = this.rng() * total;
    for (let i = 0; i < scale.length; i++) {
      r -= DEGREE_WEIGHTS[i];
      if (r <= 0) return scale[i];
    }
    return scale[0];
  }

  /**
   * The struck note. A few detuned partials with a hard attack and a long
   * exponential decay -- the higher the partial, the faster it dies, which is
   * what makes it read as something hit rather than something played.
   */
  strike(semitones, octave = 1, level = 1, when) {
    if (!this.preset) return;
    const ctx = this.ctx;
    const t = when === undefined ? ctx.currentTime : when;
    const sag = Math.pow(2, (-3 * this.tension) / 12);
    const hz = semitone(this.preset.root * 2 * octave, semitones) * sag;
    const dur = 3.4 + this.rng() * 2.4;

    const bus = ctx.createGain();
    bus.gain.value = 0.055 * level;
    bus.connect(this.out);
    bus.connect(this.reverb);

    // Slight inharmonicity on the upper partials, as a real string has.
    for (const [mult, amp, decay] of [[1, 1, 1], [2.01, 0.42, 0.62], [3.04, 0.20, 0.4], [4.18, 0.09, 0.28]]) {
      const osc = ctx.createOscillator();
      osc.type = 'sine';
      osc.frequency.value = hz * mult;
      const g = ctx.createGain();
      const life = dur * decay;
      g.gain.setValueAtTime(0.0001, t);
      g.gain.exponentialRampToValueAtTime(amp, t + 0.006);
      g.gain.exponentialRampToValueAtTime(0.0001, t + life);
      osc.connect(g).connect(bus);
      osc.start(t);
      osc.stop(t + life + 0.05);
    }
  }

  update(dt) {
    if (!this.preset) return;
    this.nextNoteIn -= dt;
    if (this.nextNoteIn > 0) return;

    const octaves = this.preset.octaves;
    const octave = octaves[Math.floor(this.rng() * octaves.length)];
    const degree = this._pickDegree();
    this.strike(degree, octave);

    // Occasionally a second note answers it, which is as close as this gets to
    // a phrase.
    if (this.rng() < 0.28) {
      const answer = this._pickDegree();
      setTimeout(() => this.strike(answer, octave, 0.7), 900 + this.rng() * 1400);
    }
    // And rarely, once things are bad, the tritone.
    if (this.tension > 0.7 && this.rng() < 0.12) {
      setTimeout(() => this.strike(TRITONE, octave, 0.5), 1800 + this.rng() * 1600);
    }

    const [lo, hi] = this.preset.gap;
    const squeeze = lerp(1, 0.55, this.tension);
    this.nextNoteIn = (lo + this.rng() * (hi - lo)) * squeeze;
  }

  dispose() {
    if (this.voice) this._fadeOut(this.voice);
    this.voice = null;
    this.preset = null;
    this.presetName = 'silent';
  }

  static presetNames() {
    return Object.keys(MUSIC_PRESETS);
  }
}
