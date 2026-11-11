// Copies the single-file build to play.html (double-click to play offline) and
// writes a head-less fragment (no doctype/html/head/body) for hosts that wrap the page themselves.
import { readFileSync, writeFileSync, copyFileSync } from 'node:fs';

const src = 'dist-single/index.html';
const html = readFileSync(src, 'utf8');
copyFileSync(src, 'play.html');

const pick = (re) => (html.match(re) || [''])[0];
const title = pick(/<title>[\s\S]*?<\/title>/);
const meta = pick(/<meta name="claude:viewport-fit-sides"[^>]*>/);
const fonts = pick(/<link rel="stylesheet" href="https:\/\/fonts\.googleapis\.com[^>]*>/);
const style = pick(/<style[^>]*>[\s\S]*?<\/style>/);
const s0 = html.indexOf('<script type="module"');
const s1 = html.lastIndexOf('</script>');
const script = html.slice(s0, s1 + 9).replace(/^<script type="module"[^>]*>/, '<script type="module">');
const body = '<div id="app">\n  <canvas id="view" tabindex="0" aria-label="Prison view"></canvas>\n  <div id="ui"></div>\n</div>';
const out = process.argv[2] || 'dist-single/fragment.html';
writeFileSync(out, [title, meta, fonts, style, body, script].join('\n') + '\n');
console.log('play.html', (html.length / 1024).toFixed(0) + ' kB;', out, 'written');
