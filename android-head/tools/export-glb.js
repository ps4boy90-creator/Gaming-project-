#!/usr/bin/env node
/*
 * Exports the procedural android head in ../index.html to a binary glTF (android-head.glb).
 *
 *   npm i --no-save three@0.128.0 playwright     (plus `npx playwright install chromium` on a fresh machine)
 *   node tools/export-glb.js [out.glb]
 *
 * The page is loaded headless, the shell is switched to solid, the shader-cut seams
 * (jaw panel, eye and ear openings) are baked into real geometry, every mesh is named
 * "<system>.<part>", and the scene is written in metres (the page works in centimetres).
 */
const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright');

const PAGE = path.join(__dirname, '..', 'index.html');
const OUT = path.resolve(process.argv[2] || path.join(__dirname, '..', 'android-head.glb'));
const three = p => fs.readFileSync(require.resolve('three/' + p), 'utf8');

(async () => {
  const browser = await chromium.launch({ args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
  const page = await browser.newPage({ viewport: { width: 640, height: 480 } });
  page.on('pageerror', e => console.error('page error:', e.message));
  // serve three.js from node_modules so the export also works offline
  await page.route('**/three.min.js', r => r.fulfill({ body: three('build/three.min.js'), contentType: 'application/javascript' }));
  await page.route(/fonts\.(googleapis|gstatic)\.com/, r => r.abort());
  await page.goto('file://' + PAGE);
  await page.waitForFunction(() => window.__head && window.__head.G, null, { timeout: 60000 });
  await page.addScriptTag({ content: three('examples/js/exporters/GLTFExporter.js') });

  const result = await page.evaluate(() => new Promise((resolve, reject) => {
    const H = window.__head, G = H.G, T = G.T, PART = H.PART;
    H.UI.select(null);
    H.state.shell = 'solid'; H.state.jaw = 0; G.refresh();

    // bake the shell's shader seams into geometry: head panel, jaw panel, eye and ear openings
    const shell = PART.shell.meshes[0], jawShell = PART.jaw.meshes.find(m => m.userData.shell);
    const src = shell.geometry, pos = src.attributes.position, ix = src.index.array, headIx = [], jawIx = [];
    for (let t = 0; t < ix.length; t += 3) {
      const a = ix[t], b = ix[t + 1], c = ix[t + 2];
      const x = Math.abs(pos.getX(a) + pos.getX(b) + pos.getX(c)) / 3, y = (pos.getY(a) + pos.getY(b) + pos.getY(c)) / 3, z = (pos.getZ(a) + pos.getZ(b) + pos.getZ(c)) / 3;
      if (z > 4 && Math.pow(x - 3.2, 2) / 2.1 + Math.pow(y - 0.8, 2) / 0.8 < 1) continue;
      if (x > 5.5 && Math.hypot(y + 0.4, z + 0.9) < 0.42) continue;
      const L = -6.05 + Math.max(0, 8.7 - z) * 0.52;
      (z > 1.9 && y < L ? jawIx : headIx).push(a, b, c);
    }
    const sub = list => { const g = new T.BufferGeometry(); g.setAttribute('position', src.attributes.position); g.setAttribute('normal', src.attributes.normal); g.setIndex(list); return g; };
    shell.geometry = sub(headIx); jawShell.geometry = sub(jawIx);

    let meshes = 0, tris = 0;
    Object.keys(PART).forEach(id => PART[id].meshes.forEach((m, i) => {
      m.name = PART[id].sys + '.' + id + (PART[id].meshes.length > 1 ? '.' + String(i).padStart(2, '0') : '');
      m.material.name = m.name; meshes++;
      tris += (m.geometry.index ? m.geometry.index.count : m.geometry.attributes.position.count) / 3;
    }));
    G.head.name = 'AndroidHead';
    G.head.rotation.set(0, 0, 0);
    const root = new T.Group(); root.name = 'AndroidHead_m'; root.scale.setScalar(0.01); root.add(G.head); root.updateMatrixWorld(true);

    new T.GLTFExporter().parse(root, buf => {
      const u8 = new Uint8Array(buf); let bin = '';
      for (let i = 0; i < u8.length; i += 0x8000) bin += String.fromCharCode.apply(null, u8.subarray(i, i + 0x8000));
      resolve({ b64: btoa(bin), parts: Object.keys(PART).length, meshes, tris: Math.round(tris) });
    }, { binary: true, onlyVisible: true });
    setTimeout(() => reject(new Error('export timed out')), 120000);
  }));

  fs.writeFileSync(OUT, Buffer.from(result.b64, 'base64'));
  console.log(`${OUT}: ${(fs.statSync(OUT).size / 1048576).toFixed(1)} MB, ${result.parts} parts, ${result.meshes} meshes, ${result.tris} triangles`);
  process.exit(0);
})().catch(e => { console.error(e); process.exit(1); });
