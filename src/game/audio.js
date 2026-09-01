import { Radio } from './radio.js';

/**
 * All sound is synthesised at runtime. There are no audio files in the repo:
 * a facility hum, wind, footsteps and a fluorescent buzz are cheap to generate
 * and expensive to store, and generated tones can be shaped per-scene from the
 * same ambience name the editor already exposes.
 *
 * The whole mix leaves through a 1950s radio (see radio.js), which band-limits
 * it to roughly 300 Hz - 3.5 kHz. Everything below is therefore pitched to
 * survive that:
 *
 *   - Drone fundamentals sit near or above the high-pass, and the oscillators
 *     are triangles rather than sines. A 34 Hz sine through a 300 Hz high-pass
 *     is *silence* -- it has no harmonics to leave behind. A triangle at 105 Hz
 *     keeps its third and fifth harmonics, which is exactly how a small speaker
 *     reproduces bass: you hear the harmonics, not the note.
 *   - The noise beds are low-passed well above the high-pass, or they vanish.
 *   - The one-shots were re-tuned off the low shelf for the same reason.
 *
 * Nothing is created until the first user gesture, because browsers refuse to
 * start an AudioContext before one.
 */
const AMBIENCE = {
  none: null,
  night_cabin: { drone: 110, droneGain: 0.020, noise: 0.006, filter: 900, wobble: 0.08 },
  forest_night: { drone: 132, droneGain: 0.013, noise: 0.018, filter: 1600, wobble: 0.20 },
  facility_hum: { drone: 120, droneGain: 0.028, noise: 0.010, filter: 1200, wobble: 0.04 },
  basement: { drone: 105, droneGain: 0.034, noise: 0.008, filter: 800, wobble: 0.02 },
  // Inside the Veridian: engine at a steady cruise, plus tyre roar. More noise
  // and more wobble than anywhere else in the game -- it is the one moving
  // scene, and the wobble is what says the road is not smooth.
  driving: { drone: 98, droneGain: 0.030, noise: 0.030, filter: 1900, wobble: 0.26 },
};

export class Audio {
  constructor() {
    this.ctx = null;
    this.master = null;
    this.preMaster = null;
    this.musicBus = null;
    this.radio = null;
    this.ambienceNodes = null;
    this.ambienceName = 'none';
    this.enabled = true;
    this.volume = 0.7;
    this.musicVolume = 0.8;
    this.radioAmount = 1;
  }

  /** Safe to call repeatedly; the first call after a gesture is the one that works. */
  resume() {
    if (!this.enabled) return;
    if (!this.ctx) {
      const AC = window.AudioContext || window.webkitAudioContext;
      if (!AC) { this.enabled = false; return; }
      this.ctx = new AC();

      // master is the last thing before the speakers; everything the game
      // makes meets at preMaster and goes through the radio to reach it.
      this.master = this.ctx.createGain();
      this.master.gain.value = this.volume;
      this.master.connect(this.ctx.destination);

      this.preMaster = this.ctx.createGain();
      this.radio = new Radio(this.ctx, this._noiseBuffer(3));
      this.preMaster.connect(this.radio.input);
      this.radio.output.connect(this.master);
      this.radio.setAmount(this.radioAmount);

      // Music has its own bus so it can be balanced or silenced without
      // touching the footsteps.
      this.musicBus = this.ctx.createGain();
      this.musicBus.gain.value = this.musicVolume;
      this.musicBus.connect(this.preMaster);

      if (this.ambienceName !== 'none') this.setAmbience(this.ambienceName, true);
    }
    if (this.ctx.state === 'suspended') this.ctx.resume();
  }

  setVolume(v) {
    this.volume = v;
    if (this.master) this.master.gain.value = v;
  }

  setMusicVolume(v) {
    this.musicVolume = v;
    if (this.musicBus) this.musicBus.gain.value = v;
  }

  /** 0 bypasses the radio entirely and the game sounds modern and full-range. */
  setRadioAmount(a) {
    this.radioAmount = a;
    if (this.radio) this.radio.setAmount(a);
  }

  /** Called from the game's fixed update, for the radio's scheduled crackle. */
  update(dt) {
    if (this.radio) this.radio.update(dt);
  }

  _noiseBuffer(seconds = 2) {
    const rate = this.ctx.sampleRate;
    const buf = this.ctx.createBuffer(1, rate * seconds, rate);
    const data = buf.getChannelData(0);
    let last = 0;
    for (let i = 0; i < data.length; i++) {
      // Brown-ish noise: closer to wind and room tone than white noise, which
      // reads as tape hiss.
      last = (last + (Math.random() * 2 - 1) * 0.02) * 0.996;
      data[i] = last;
    }
    return buf;
  }

  setAmbience(name, force = false) {
    if (!force && name === this.ambienceName) return;
    this.ambienceName = name;
    if (!this.ctx) return;

    if (this.ambienceNodes) {
      const { gain, sources } = this.ambienceNodes;
      gain.gain.setTargetAtTime(0, this.ctx.currentTime, 0.4);
      // Let the fade finish before tearing the graph down.
      setTimeout(() => sources.forEach((s) => { try { s.stop(); } catch (e) { /* already stopped */ } }), 1400);
      this.ambienceNodes = null;
    }

    const preset = AMBIENCE[name];
    if (!preset) return;

    const now = this.ctx.currentTime;
    const gain = this.ctx.createGain();
    gain.gain.value = 0;
    gain.gain.setTargetAtTime(1, now, 0.8);
    gain.connect(this.preMaster);
    const sources = [];

    const osc = this.ctx.createOscillator();
    // Triangle, not sine: the fundamental is filtered out downstream and a sine
    // has nothing left to give once it is gone.
    osc.type = 'triangle';
    osc.frequency.value = preset.drone;
    const oscGain = this.ctx.createGain();
    oscGain.gain.value = preset.droneGain;
    osc.connect(oscGain).connect(gain);
    osc.start();
    sources.push(osc);

    // A slow detuned partner makes the drone breathe instead of sitting flat.
    const osc2 = this.ctx.createOscillator();
    osc2.type = 'triangle';
    osc2.frequency.value = preset.drone * 1.5 + preset.wobble;
    const osc2Gain = this.ctx.createGain();
    osc2Gain.gain.value = preset.droneGain * 0.45;
    osc2.connect(osc2Gain).connect(gain);
    osc2.start();
    sources.push(osc2);

    const noise = this.ctx.createBufferSource();
    noise.buffer = this._noiseBuffer(3);
    noise.loop = true;
    const filter = this.ctx.createBiquadFilter();
    filter.type = 'lowpass';
    filter.frequency.value = preset.filter;
    const noiseGain = this.ctx.createGain();
    noiseGain.gain.value = preset.noise * 40;
    noise.connect(filter).connect(noiseGain).connect(gain);
    noise.start();
    sources.push(noise);

    this.ambienceNodes = { gain, sources };
  }

  /** One-shot effects, all built from an envelope over an oscillator or noise. */
  play(name, opts = {}) {
    if (!this.enabled || !this.ctx) return;
    const t = this.ctx.currentTime;
    const spec = {
      walk: { type: 'noise', freq: 900, dur: 0.07, gain: 0.10, q: 1.2 },
      run: { type: 'noise', freq: 1200, dur: 0.06, gain: 0.15, q: 1.2 },
      land: { type: 'noise', freq: 520, dur: 0.14, gain: 0.20, q: 0.8 },
      paper: { type: 'noise', freq: 2600, dur: 0.16, gain: 0.10, q: 0.9 },
      pickup: { type: 'tone', freq: 660, to: 990, dur: 0.14, gain: 0.10 },
      terminal: { type: 'tone', freq: 440, to: 560, dur: 0.10, gain: 0.07 },
      door: { type: 'noise', freq: 480, dur: 0.34, gain: 0.16, q: 0.6 },
      metal: { type: 'noise', freq: 390, dur: 0.42, gain: 0.18, q: 0.5 },
      locked: { type: 'tone', freq: 430, to: 320, dur: 0.16, gain: 0.13 },
      save: { type: 'tone', freq: 520, to: 780, dur: 0.32, gain: 0.09 },
      blip: { type: 'tone', freq: 880, to: 880, dur: 0.04, gain: 0.05 },
      // A wind-up bell: struck, not beeped. Well inside the radio's passband,
      // which is where a 1950s alarm clock would have lived anyway.
      alarm: { type: 'tone', freq: 1480, to: 1180, dur: 0.34, gain: 0.09 },
    }[name];
    if (!spec) return;

    const gain = this.ctx.createGain();
    const peak = (spec.gain || 0.1) * (opts.gain || 1);
    gain.gain.setValueAtTime(0.0001, t);
    gain.gain.exponentialRampToValueAtTime(peak, t + 0.008);
    gain.gain.exponentialRampToValueAtTime(0.0001, t + spec.dur);
    gain.connect(this.preMaster);

    if (spec.type === 'noise') {
      const src = this.ctx.createBufferSource();
      src.buffer = this._noiseBuffer(0.5);
      const filter = this.ctx.createBiquadFilter();
      filter.type = 'bandpass';
      filter.frequency.value = spec.freq * (0.9 + Math.random() * 0.2);
      filter.Q.value = spec.q || 1;
      src.connect(filter).connect(gain);
      src.start(t);
      src.stop(t + spec.dur + 0.05);
    } else {
      const osc = this.ctx.createOscillator();
      osc.type = 'triangle';
      osc.frequency.setValueAtTime(spec.freq, t);
      osc.frequency.exponentialRampToValueAtTime(Math.max(1, spec.to || spec.freq), t + spec.dur);
      osc.connect(gain);
      osc.start(t);
      osc.stop(t + spec.dur + 0.05);
    }
  }

  static ambienceNames() {
    return Object.keys(AMBIENCE);
  }

  /** Exposed so offline renders can rebuild a room tone without duplicating it. */
  static ambiencePreset(name) {
    return AMBIENCE[name] || null;
  }
}
