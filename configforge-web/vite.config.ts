/// <reference types="vitest" />
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [vue(), tailwindcss()],
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        timeout: 120000, // 2 minutes for long-running pipeline + AI diagnosis
      }
    }
  },
  test: {
    environment: 'happy-dom',
    exclude: ['e2e/**', '**/node_modules/**', '**/dist/**'],
    setupFiles: ['./tests/setup.ts'],
  }
})
