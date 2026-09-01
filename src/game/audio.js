/**
 * All sound is synthesised at runtime. There are no audio files in the repo:
 * a facility hum, wind, footsteps and a fluorescent buzz are cheap to generate
 * and expensive to store, and generated tones can be shaped per-scene from the
 * same ambience name the editor already exposes.
 *
 * Nothing is created until the first user gesture, because browsers refuse to
 * start an AudioContext before one.
 */
const AMBIENCE = {
  none: null,
  night_cabin: { drone: 58, droneGain: 0.020, noise: 0.006, filter: 380, wobble: 0.08 },
  forest_night: { drone: 44, droneGain: 0.014, noise: 0.018, filter: 900, wobble: 0.20 },
  facility_hum: { drone: 100, droneGain: 0.030, noise: 0.010, filter: 620, wobble: 0.04 },
  basement: { drone: 34, droneGain: 0.038, noise: 0.008, filter: 240, wobble: 0.02 },
};

export class Audio {
  constructor() {
    this.ctx = null;
    this.master = null;
    this.ambienceNodes = null;
    this.ambienceName = 'none';
    this.enabled = true;
    this.volume = 0.7;
  }

  /** Safe to call repeatedly; the first call after a gesture is the one that works. */
  resume() {
    if (!this.enabled) return;
    if (!this.ctx) {
      const AC = window.AudioContext || window.webkitAudioContext;
      if (!AC) { this.enabled = false; return; }
      this.ctx = new AC();
      this.master = this.ctx.createGain();
      this.master.gain.value = this.volume;
      this.master.connect(this.ctx.destination);
      if (this.ambienceName !== 'none') this.setAmbience(this.ambienceName, true);
    }
    if (this.ctx.state === 'suspended') this.ctx.resume();
  }

  setVolume(v) {
    this.volume = v;
    if (this.master) this.master.gain.value = v;
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
    gain.connect(this.master);
    const sources = [];

    const osc = this.ctx.createOscillator();
    osc.type = 'sine';
    osc.frequency.value = preset.drone;
    const oscGain = this.ctx.createGain();
    oscGain.gain.value = preset.droneGain;
    osc.connect(oscGain).connect(gain);
    osc.start();
    sources.push(osc);

    // A slow detuned partner makes the drone breathe instead of sitting flat.
    const osc2 = this.ctx.createOscillator();
    osc2.type = 'sine';
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
      land: { type: 'noise', freq: 420, dur: 0.14, gain: 0.20, q: 0.8 },
      paper: { type: 'noise', freq: 2600, dur: 0.16, gain: 0.10, q: 0.9 },
      pickup: { type: 'tone', freq: 660, to: 990, dur: 0.14, gain: 0.10 },
      terminal: { type: 'tone', freq: 440, to: 560, dur: 0.10, gain: 0.07 },
      door: { type: 'noise', freq: 260, dur: 0.34, gain: 0.16, q: 0.6 },
      metal: { type: 'noise', freq: 180, dur: 0.42, gain: 0.18, q: 0.5 },
      locked: { type: 'tone', freq: 180, to: 120, dur: 0.16, gain: 0.11 },
      save: { type: 'tone', freq: 520, to: 780, dur: 0.32, gain: 0.09 },
      blip: { type: 'tone', freq: 880, to: 880, dur: 0.04, gain: 0.05 },
    }[name];
    if (!spec) return;

    const gain = this.ctx.createGain();
    const peak = (spec.gain || 0.1) * (opts.gain || 1);
    gain.gain.setValueAtTime(0.0001, t);
    gain.gain.exponentialRampToValueAtTime(peak, t + 0.008);
    gain.gain.exponentialRampToValueAtTime(0.0001, t + spec.dur);
    gain.connect(this.master);

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
}
