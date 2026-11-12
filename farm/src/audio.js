/**
 * The night, synthesised. Like the rest of this repository there are no audio
 * files: wind is filtered noise on a slow swell, the crickets are pulsed
 * sines, the owl is two falling tones, and footsteps are shaped noise bursts
 * that change with what is underfoot.
 *
 * The mix is deliberately thin and band-limited -- camcorder audio, not a
 * soundtrack -- and it closes down when you step inside the barn.
 */
export class Ambience {
  constructor() { this.ctx = null; }

  start() {
    if (this.ctx) { this.ctx.resume(); return; }
    const AC = window.AudioContext || window.webkitAudioContext;
    if (!AC) return;
    const ctx = (this.ctx = new AC());
    const master = (this.master = ctx.createGain());
    master.gain.value = 0.0;
    master.gain.linearRampToValueAtTime(0.8, ctx.currentTime + 3);
    const tape = ctx.createBiquadFilter();
    tape.type = 'lowpass'; tape.frequency.value = 7000;
    master.connect(tape).connect(ctx.destination);

    const noise = ctx.createBuffer(1, ctx.sampleRate * 4, ctx.sampleRate);
    const d = noise.getChannelData(0);
    for (let i = 0; i < d.length; i++) d[i] = Math.random() * 2 - 1;
    this.noise = noise;
    const loop = (filterType, freq, q) => {
      const src = ctx.createBufferSource(); src.buffer = noise; src.loop = true;
      const f = ctx.createBiquadFilter(); f.type = filterType; f.frequency.value = freq; f.Q.value = q;
      const g = ctx.createGain(); g.gain.value = 0;
      src.connect(f).connect(g).connect(master); src.start();
      return g;
    };
    this.wind = loop('lowpass', 320, 0.4);       // the body of the wind
    this.trees = loop('bandpass', 2400, 0.6);    // needles hissing
    this.hiss = loop('highpass', 5000, 0.3);     // tape
    this.hiss.gain.value = 0.012;
    this.snow = loop('bandpass', 3200, 0.4);     // the television, on with nothing tuned

    // Crickets: three voices, each a short train of chirps on its own clock.
    this.crickets = ctx.createGain(); this.crickets.gain.value = 0.05;
    this.crickets.connect(master);
    for (const [freq, period, pan] of [[4300, 0.71, -0.6], [4650, 0.93, 0.5], [3900, 1.27, 0.1]]) {
      const len = Math.round(ctx.sampleRate * period);
      const buf = ctx.createBuffer(1, len, ctx.sampleRate);
      const c = buf.getChannelData(0);
      for (let pulse = 0; pulse < 3; pulse++) {
        const at = Math.round(ctx.sampleRate * pulse * 0.034), n = Math.round(ctx.sampleRate * 0.017);
        for (let i = 0; i < n; i++) c[at + i] = Math.sin((i / ctx.sampleRate) * freq * Math.PI * 2) * Math.sin((i / n) * Math.PI) ** 2;
      }
      const src = ctx.createBufferSource(); src.buffer = buf; src.loop = true;
      const p = ctx.createStereoPanner ? ctx.createStereoPanner() : ctx.createGain();
      if (p.pan) p.pan.value = pan;
      src.connect(p).connect(this.crickets); src.start();
    }

    // The yard lamp's ballast: a mains hum you only hear up close.
    const hum = ctx.createOscillator(); hum.type = 'sawtooth'; hum.frequency.value = 120;
    const hf = ctx.createBiquadFilter(); hf.type = 'lowpass'; hf.frequency.value = 500;
    this.hum = ctx.createGain(); this.hum.gain.value = 0;
    hum.connect(hf).connect(this.hum).connect(master); hum.start();

    this.t = 0; this.nextOwl = 14 + Math.random() * 20;
  }

  /** `s` is { inside, lampDistance, tvDistance }. */
  update(dt, s) {
    const ctx = this.ctx;
    if (!ctx) return;
    this.t += dt;
    const now = ctx.currentTime;
    const gust = 0.5 + 0.5 * Math.sin(this.t * 0.23) * Math.sin(this.t * 0.071 + 1.3);
    const shelter = s.inside ? 0.35 : 1;
    this.wind.gain.setTargetAtTime((0.05 + gust * 0.09) * shelter, now, 0.4);
    this.trees.gain.setTargetAtTime((0.008 + gust * 0.03) * shelter, now, 0.4);
    this.crickets.gain.setTargetAtTime(0.05 * (s.inside ? 0.25 : 1), now, 0.5);
    this.hum.gain.setTargetAtTime(0.03 / (1 + s.lampDistance * s.lampDistance * 0.05), now, 0.2);
    this.snow.gain.setTargetAtTime(0.11 / (1 + s.tvDistance * s.tvDistance * 0.5), now, 0.25);
    if (this.t > this.nextOwl) {
      this.nextOwl = this.t + 35 + Math.random() * 60;
      this.owl(s.inside ? 0.3 : 1);
    }
  }

  owl(level) {
    const ctx = this.ctx, t0 = ctx.currentTime + 0.05;
    [0, 0.42, 0.95].forEach((at, i) => {
      const o = ctx.createOscillator(), g = ctx.createGain();
      o.type = 'sine';
      o.frequency.setValueAtTime(i === 2 ? 330 : 350, t0 + at);
      o.frequency.exponentialRampToValueAtTime(i === 2 ? 270 : 320, t0 + at + 0.4);
      g.gain.setValueAtTime(0, t0 + at);
      g.gain.linearRampToValueAtTime(0.035 * level, t0 + at + 0.06);
      g.gain.exponentialRampToValueAtTime(0.0005, t0 + at + (i === 2 ? 0.7 : 0.3));
      o.connect(g).connect(this.master);
      o.start(t0 + at); o.stop(t0 + at + 0.8);
    });
  }

  step(surface, run) {
    const ctx = this.ctx;
    if (!ctx) return;
    const t0 = ctx.currentTime;
    const src = ctx.createBufferSource(); src.buffer = this.noise;
    const f = ctx.createBiquadFilter(), g = ctx.createGain();
    const [type, freq, q, level, len] = {
      grass: ['bandpass', 1700, 0.7, 0.07, 0.16],
      dirt: ['bandpass', 800, 0.9, 0.1, 0.11],
      wood: ['lowpass', 380, 1.5, 0.22, 0.09],
    }[surface];
    f.type = type; f.frequency.value = freq * (0.9 + Math.random() * 0.2); f.Q.value = q;
    g.gain.setValueAtTime(level * (run ? 1.4 : 1), t0);
    g.gain.exponentialRampToValueAtTime(0.0008, t0 + len);
    src.connect(f).connect(g).connect(this.master);
    src.start(t0, Math.random() * 3, len + 0.02);
    if (surface === 'wood') {          // the board gives under you
      const o = ctx.createOscillator(), og = ctx.createGain();
      o.frequency.setValueAtTime(95, t0); o.frequency.exponentialRampToValueAtTime(55, t0 + 0.12);
      og.gain.setValueAtTime(0.16, t0); og.gain.exponentialRampToValueAtTime(0.001, t0 + 0.14);
      o.connect(og).connect(this.master); o.start(t0); o.stop(t0 + 0.16);
    }
  }
}
