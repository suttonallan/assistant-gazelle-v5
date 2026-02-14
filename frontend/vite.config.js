import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig(({ mode }) => {
  // Charger les variables d'environnement selon le mode
  const isProduction = mode === 'production'
  
  return {
    plugins: [react()],
    // base: '/assistant-gazelle-v5/', // Désactivé pour développement local
    base: '/',
    build: {
      outDir: 'dist',
      // S'assurer que les variables d'environnement sont bien incluses
      envPrefix: 'VITE_'
    },
    // Exposer les variables d'environnement
    define: {
      // Vite expose déjà import.meta.env automatiquement
    },
    server: {
      port: 5174,
      open: false,
      headers: {
        'Cache-Control': 'no-store, no-cache, must-revalidate, max-age=0',
        'Pragma': 'no-cache',
        'Expires': '0'
      },
      proxy: {
        '/api': {
          target: 'http://localhost:8001',
          changeOrigin: true
        }
      }
    }
  }
})

