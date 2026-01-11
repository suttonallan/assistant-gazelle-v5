import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  // base: '/assistant-gazelle-v5/', // Désactivé pour développement local
  base: process.env.NODE_ENV === 'production' ? '/assistant-gazelle-v5/' : '/',
  build: {
    outDir: 'dist'
  },
  server: {
    port: 5174,
    open: false,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true
      }
    }
  }
})

