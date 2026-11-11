import './ui/style.css';
import { Game } from './game';

function boot() {
  const canvas = document.getElementById('view') as HTMLCanvasElement;
  try {
    const game = new Game(canvas);
    (window as any).__game = game;
  } catch (e) {
    console.error(e);
    const ui = document.getElementById('ui')!;
    ui.innerHTML = `<div style="position:absolute;inset:0;display:grid;place-items:center;padding:24px;text-align:center;color:#e9edf0">
      <div><h1 style="font-family:var(--display);color:#f08a24;font-weight:400;margin:0 0 8px">IRONVALE</h1>
      <p>This game needs WebGL 2, which this browser or device could not start.</p>
      <p style="color:#9aa7b2;font-size:13px">${String((e as Error)?.message ?? e)}</p></div></div>`;
  }
}
boot();
