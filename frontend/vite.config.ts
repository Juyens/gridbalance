import vue from '@vitejs/plugin-vue'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue()],
  // Relative asset paths so pywebview can load the build from disk.
  base: './',
  // Cytoscape alone is ~600 kB; the app runs from disk, so one bundle is fine.
  build: { chunkSizeWarningLimit: 1000 },
})
