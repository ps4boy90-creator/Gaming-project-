// Procedural room tone: fan-wall noise, blower hum, a little high whine,
// positional rumble from each CRAC, and a latch click for rack doors.
export class Ambience {
  constructor() {
    this.ctx = null;
    this.muted = false;
  }

  start(cracPositions = []) {
    if (this.ctx) { this.ctx.resume(); return; }
    const AC = window.AudioContext || window.webkitAudioContext;
    if (!AC) return;
    const ctx = (this.ctx = new AC());
    const master = (this.master = ctx.createGain());
    master.gain.value = 0;
    master.connect(ctx.destination);
    master.gain.linearRampToValueAtTime(this.muted ? 0 : 0.6, ctx.currentTime + 2.5);

    const noise = (seconds, brown) => {
      const len = Math.floor(ctx.sampleRate * seconds);
      const buf = ctx.createBuffer(1, len, ctx.sampleRate);
      const d = buf.getChannelData(0);
      let last = 0;
      for (let i = 0; i < len; i++) {
        const w = Math.random() * 2 - 1;
        if (brown) { last = (last + 0.02 * w) / 1.02; d[i] = last * 3.5; } else d[i] = w;
      }
      const src = ctx.createBufferSource();
      src.buffer = buf;
      src.loop = true;
      src.start();
      return src;
    };
    const chain = (...nodes) => { for (let i = 0; i < nodes.length - 1; i++) nodes[i].connect(nodes[i + 1]); return nodes[nodes.length - 1]; };
    const gain = (v) => { const g = ctx.createGain(); g.gain.value = v; return g; };
    const filt = (type, f, q = 0.7) => { const b = ctx.createBiquadFilter(); b.type = type; b.frequency.value = f; b.Q.value = q; return b; };

    chain(noise(4, true), filt('lowpass', 420), gain(0.55), master);
    chain(noise(3, false), filt('bandpass', 1900, 0.5), gain(0.05), master);
    chain(noise(3, false), filt('highpass', 5200, 0.5), gain(0.012), master);
    for (const [f, type, g] of [[118, 'sawtooth', 0.018], [236, 'sine', 0.011], [3150, 'sine', 0.0022], [4710, 'sine', 0.0012]]) {
      const o = ctx.createOscillator();
      o.type = type;
      o.frequency.value = f;
      const lfo = ctx.createOscillator();
      lfo.frequency.value = 0.07 + Math.random() * 0.1;
      const depth = gain(f * 0.004);
      lfo.connect(depth).connect(o.frequency);
      lfo.start();
      o.start();
      chain(o, filt('lowpass', Math.max(600, f * 1.5)), gain(g), master);
    }
    for (const p of cracPositions) {
      const pan = ctx.createPanner();
      pan.panningModel = 'HRTF';
      pan.distanceModel = 'inverse';
      pan.refDistance = 1.2;
      pan.rolloffFactor = 1.3;
      if (pan.positionX) { pan.positionX.value = p.x; pan.positionY.value = 1.2; pan.positionZ.value = p.z; }
      else pan.setPosition(p.x, 1.2, p.z);
      chain(noise(2.5, true), filt('lowpass', 260), gain(0.5), pan);
      const hum = ctx.createOscillator();
      hum.frequency.value = 59.5;
      hum.start();
      chain(hum, gain(0.05), pan);
      pan.connect(master);
    }
  }

  listen(x, y, z, yaw) {
    const ctx = this.ctx;
    if (!ctx) return;
    const L = ctx.listener;
    const fx = -Math.sin(yaw), fz = -Math.cos(yaw);
    if (L.positionX) {
      L.positionX.value = x; L.positionY.value = y; L.positionZ.value = z;
      L.forwardX.value = fx; L.forwardY.value = 0; L.forwardZ.value = fz;
      L.upX.value = 0; L.upY.value = 1; L.upZ.value = 0;
    } else {
      L.setPosition(x, y, z);
      L.setOrientation(fx, 0, fz, 0, 1, 0);
    }
  }

  click(open = true) {
    const ctx = this.ctx;
    if (!ctx || this.muted) return;
    const t = ctx.currentTime;
    const len = Math.floor(ctx.sampleRate * 0.05);
    const buf = ctx.createBuffer(1, len, ctx.sampleRate);
    const d = buf.getChannelData(0);
    for (let i = 0; i < len; i++) d[i] = (Math.random() * 2 - 1) * Math.exp(-i / (len * 0.12));
    const src = ctx.createBufferSource();
    src.buffer = buf;
    const hp = ctx.createBiquadFilter();
    hp.type = 'bandpass';
    hp.frequency.value = open ? 2600 : 1800;
    const g = ctx.createGain();
    g.gain.value = 0.5;
    src.connect(hp).connect(g).connect(this.master);
    src.start(t);
    const thump = ctx.createOscillator();
    thump.frequency.setValueAtTime(open ? 140 : 110, t);
    thump.frequency.exponentialRampToValueAtTime(50, t + 0.09);
    const tg = ctx.createGain();
    tg.gain.setValueAtTime(0.25, t);
    tg.gain.exponentialRampToValueAtTime(0.001, t + 0.12);
    thump.connect(tg).connect(this.master);
    thump.start(t);
    thump.stop(t + 0.13);
  }

  toggleMute() {
    this.muted = !this.muted;
    if (this.ctx) this.master.gain.setTargetAtTime(this.muted ? 0 : 0.6, this.ctx.currentTime, 0.1);
    return this.muted;
  }
}
