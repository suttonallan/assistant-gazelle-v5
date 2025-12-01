import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  base: '/assistant-gazelle-v5/',
  build: {
    outDir: 'dist'
  }
})

