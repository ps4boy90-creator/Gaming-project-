// Bundle the built game into one self-contained HTML page (CSS and JS inlined).
// Usage: npm run build && node scripts/publish.mjs [outFile]
import { readFileSync, writeFileSync, readdirSync, mkdirSync } from 'fs';
import { dirname, join } from 'path';
import { fileURLToPath } from 'url';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const out = process.argv[2] ?? join(root, 'publish', 'seedfall.html');
const assets = join(root, 'dist', 'assets');
const files = readdirSync(assets);
const css = readFileSync(join(assets, files.find((f) => f.endsWith('.css'))), 'utf8');
const js = readFileSync(join(assets, files.find((f) => f.endsWith('.js'))), 'utf8').replace(/<\/script/gi, '<\\/script');
const src = readFileSync(join(root, 'index.html'), 'utf8');
const body = src.slice(src.indexOf('<!-- @@BODY_START@@ -->') + 23, src.indexOf('<!-- @@BODY_END@@ -->')).trim();
const fonts = src.match(/<link rel="stylesheet" href="https:\/\/fonts\.googleapis\.com[^>]+>/)[0];

// Escape non-ASCII so the page decodes correctly whatever charset it is served with.
const hex = (c) => c.charCodeAt(0).toString(16).padStart(4, '0');
const jsSafe = js.replace(/[\u0080-\uffff]/g, (c) => `\\u${hex(c)}`);
const cssSafe = css.replace(/[\u0080-\uffff]/g, (c) => `\\${hex(c)} `);
const bodySafe = body.replace(/[\u0080-\uffff]/g, (c) => `&#x${hex(c)};`);

const page = `<title>SEEDFALL</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
${fonts}
<style>
${cssSafe}
</style>
${bodySafe}
<script type="module">
${jsSafe}
</script>
`;
mkdirSync(dirname(out), { recursive: true });
writeFileSync(out, page);
console.log(`wrote ${out} (${(page.length / 1024).toFixed(0)} KB)`);
