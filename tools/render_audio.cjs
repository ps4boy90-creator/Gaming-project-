const { chromium } = require('playwright-core');
const fs = require('fs');
const path = require('path');
/**
 * Render listenable captures of the score and the radio to .wav.
 *
 * Automated spectral checks can prove the chain is band-limited; they cannot
 * say whether the hiss sits at the right level. This renders the real graph
 * through an OfflineAudioContext so the result can be listened to and judged.
 *
 *   python3 -m http.server 8000 &
 *   node tools/render_audio.cjs [outDir]
 */
const CHROME = process.env.CHROME || '/opt/pw-browsers/chromium-1194/chrome-linux/chrome';
const BASE = process.env.BASE || 'http://127.0.0.1:8000';
const OUT = process.argv[2] || path.join(__dirname, 'audio-preview');

const SECONDS = 26;
const RATE = 44100;

/** Interleaved float samples to a 16-bit PCM wav. */
function wav(channels, rate) {
  const len = channels[0].length;
  const n = channels.length;
  const buf = Buffer.alloc(44 + len * n * 2);
  buf.write('RIFF', 0);
  buf.writeUInt32LE(36 + len * n * 2, 4);
  buf.write('WAVE', 8);
  buf.write('fmt ', 12);
  buf.writeUInt32LE(16, 16);
  buf.writeUInt16LE(1, 20);
  buf.writeUInt16LE(n, 22);
  buf.writeUInt32LE(rate, 24);
  buf.writeUInt32LE(rate * n * 2, 28);
  buf.writeUInt16LE(n * 2, 32);
  buf.writeUInt16LE(16, 34);
  buf.write('data', 36);
  buf.writeUInt32LE(len * n * 2, 40);
  let o = 44;
  for (let i = 0; i < len; i++) {
    for (let c = 0; c < n; c++) {
      const v = Math.max(-1, Math.min(1, channels[c][i]));
      buf.writeInt16LE(Math.round(v * 32767), o);
      o += 2;
    }
  }
  return buf;
}

(async () => {
  fs.mkdirSync(OUT, { recursive: true });
  const browser = await chromium.launch({
    executablePath: CHROME,
    args: ['--no-sandbox', '--autoplay-policy=no-user-gesture-required'],
  });
  const page = await browser.newPage();
  page.on('pageerror', (e) => console.log('PAGEERROR', e.message));
  await page.goto(`${BASE}/index.html`);
  await page.waitForFunction(() => window.game, null, { timeout: 15000 });

  const takes = [
    { name: 'cabin-calm', preset: 'cabin', ambience: 'night_cabin', tension: 0, radio: 1 },
    { name: 'facility-calm', preset: 'facility', ambience: 'facility_hum', tension: 0.15, radio: 1 },
    { name: 'aperture-tense', preset: 'aperture', ambience: 'basement', tension: 1, radio: 1 },
    { name: 'aperture-noradio', preset: 'aperture', ambience: 'basement', tension: 1, radio: 0 },
  ];

  for (const take of takes) {
    const data = await page.evaluate(async ({ take, SECONDS, RATE }) => {
      const [{ Radio }, { Music }, { Audio }] = await Promise.all([
        import('./src/game/radio.js'), import('./src/game/music.js'), import('./src/game/audio.js'),
      ]);
      const ctx = new OfflineAudioContext(2, RATE * SECONDS, RATE);

      // Brown noise, the same shape audio.js builds at runtime.
      const noise = ctx.createBuffer(1, RATE * 3, RATE);
      const nd = noise.getChannelData(0);
      let last = 0;
      for (let i = 0; i < nd.length; i++) {
        last = (last + (Math.random() * 2 - 1) * 0.02) * 0.996;
        nd[i] = last;
      }

      const master = ctx.createGain();
      master.gain.value = 0.7;
      master.connect(ctx.destination);
      const radio = new Radio(ctx, noise);
      radio.output.connect(master);
      radio.setAmount(take.radio);
      radio.setTension(take.tension);

      const pre = radio.input;
      const music = new Music(ctx, pre, noise);
      music.setPreset(take.preset);
      music.setTension(take.tension);

      // Room tone, built the same way setAmbience does.
      const amb = Audio.ambiencePreset(take.ambience);
      if (amb) {
        const g = ctx.createGain();
        g.gain.value = 1;
        g.connect(pre);
        for (const [mult, level] of [[1, 1], [1.5, 0.45]]) {
          const o = ctx.createOscillator();
          o.type = 'triangle';
          o.frequency.value = amb.drone * mult + (mult > 1 ? amb.wobble : 0);
          const og = ctx.createGain();
          og.gain.value = amb.droneGain * level;
          o.connect(og).connect(g);
          o.start();
        }
        const ns = ctx.createBufferSource();
        ns.buffer = noise;
        ns.loop = true;
        const f = ctx.createBiquadFilter();
        f.type = 'lowpass';
        f.frequency.value = amb.filter;
        const ng = ctx.createGain();
        ng.gain.value = amb.noise * 40;
        ns.connect(f).connect(ng).connect(g);
        ns.start();
      }

      // Schedule the score and the radio's imperfections across the timeline.
      const [lo, hi] = music.preset.gap;
      const squeeze = 1 - 0.45 * take.tension;
      let t = 1.5;
      while (t < SECONDS - 4) {
        const oct = music.preset.octaves[Math.floor(Math.random() * music.preset.octaves.length)];
        music.strike(music._pickDegree(), oct, 1, t);
        if (Math.random() < 0.3) music.strike(music._pickDegree(), oct, 0.7, t + 1.1);
        t += Math.max(3, (lo + Math.random() * (hi - lo)) * squeeze * 0.45);
      }
      if (take.radio > 0) {
        for (let c = 1; c < SECONDS - 1; c += (2.5 + Math.random() * 5) * (1 - 0.5 * take.tension)) {
          radio._crackle(c);
        }
        for (let d = 4; d < SECONDS - 2; d += 7 + Math.random() * 8) radio._dropout(d);
        if (take.tension > 0.45) for (let wq = 6; wq < SECONDS - 4; wq += 11) radio._whistle(wq);
      }

      const rendered = await ctx.startRendering();
      return [Array.from(rendered.getChannelData(0)), Array.from(rendered.getChannelData(1))];
    }, { take, SECONDS, RATE });

    const file = path.join(OUT, `${take.name}.wav`);
    fs.writeFileSync(file, wav(data, RATE));
    let peak = 0;
    for (const v of data[0]) { const a = Math.abs(v); if (a > peak) peak = a; }
    console.log(`  ${take.name}.wav  ${SECONDS}s  peak ${peak.toFixed(3)}${peak > 0.99 ? '  CLIPPING' : ''}`);
  }

  await browser.close();
})();
