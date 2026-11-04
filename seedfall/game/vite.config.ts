import { defineConfig } from 'vite';

export default defineConfig({
  base: './',
  build: {
    target: 'es2022',
    outDir: 'dist',
    assetsInlineLimit: 0,
    chunkSizeWarningLimit: 2500,
    rollupOptions: { output: { manualChunks: undefined, inlineDynamicImports: true } },
  },
  server: { host: true, port: 5173 },
  preview: { host: true, port: 4173 },
});
