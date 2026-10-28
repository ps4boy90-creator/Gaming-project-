// Bundles three.js and src/ into dist/data-hall-b.html: one self-contained
// file with no module loading, so it opens straight from disk or inside a
// sandboxed frame.
import * as esbuild from 'esbuild';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const three = path.join(root, 'node_modules/three');

const result = await esbuild.build({
  entryPoints: [path.join(root, 'src/main.js')],
  bundle: true,
  minify: true,
  format: 'iife',
  target: 'es2020',
  write: false,
  legalComments: 'none',
  plugins: [{
    name: 'three-local',
    setup(b) {
      b.onResolve({ filter: /^three$/ }, () => ({ path: path.join(three, 'build/three.module.js') }));
      b.onResolve({ filter: /^three\/addons\// }, (a) => ({ path: path.join(three, 'examples/jsm', a.path.slice('three/addons/'.length)) }));
    },
  }],
});

const js = result.outputFiles[0].text.replace(/<\/script/gi, '<\\/script');
let html = fs.readFileSync(path.join(root, 'index.html'), 'utf8');
html = html.replace(/<script type="importmap">[\s\S]*?<\/script>\n/, '');
html = html.replace('<script type="module" src="./src/main.js"></script>', () => `<script>\n${js}\n</script>`);
fs.mkdirSync(path.join(root, 'dist'), { recursive: true });
fs.writeFileSync(path.join(root, 'dist/data-hall-b.html'), html);
console.log(`dist/data-hall-b.html  ${(html.length / 1024).toFixed(0)} KB`);
