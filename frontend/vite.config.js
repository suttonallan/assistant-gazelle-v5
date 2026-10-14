import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Identifiant unique de chaque build : sert à détecter qu'une nouvelle
// version est en ligne (voir src/utils/miseAJour.js).
const BUILD_ID = String(Date.now())

const versionPlugin = {
  name: 'ptm-version-json',
  generateBundle() {
    this.emitFile({ type: 'asset', fileName: 'version.json', source: JSON.stringify({ build: BUILD_ID }) })
  }
}

export default defineConfig(({ mode }) => {
  // Charger les variables d'environnement selon le mode
  const isProduction = mode === 'production'
  
  return {
    plugins: [react(), versionPlugin],
    // base: '/assistant-gazelle-v5/', // Désactivé pour développement local
    base: isProduction ? '/assistant-gazelle-v5/' : '/',
    build: {
      outDir: 'dist',
      // S'assurer que les variables d'environnement sont bien incluses
      envPrefix: 'VITE_'
    },
    // Exposer les variables d'environnement
    define: {
      __BUILD_ID__: JSON.stringify(BUILD_ID)
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

