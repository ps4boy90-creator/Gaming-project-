import { defineConfig } from 'vite';
import { viteSingleFile } from 'vite-plugin-singlefile';

// SINGLE=1 produces one self-contained HTML file (dist-single/index.html).
const single = process.env.SINGLE === '1';

export default defineConfig({
  base: './',
  plugins: single ? [viteSingleFile()] : [],
  build: {
    target: 'es2022',
    outDir: single ? 'dist-single' : 'dist',
    chunkSizeWarningLimit: 4000,
  },
  server: { host: true, port: 5173 },
});
