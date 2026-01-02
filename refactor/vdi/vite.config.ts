import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './'),
      '@types': path.resolve(__dirname, './types'),
      '@hooks': path.resolve(__dirname, './hooks'),
      '@lib': path.resolve(__dirname, './lib'),
      '@components': path.resolve(__dirname, './components'),
      '@config': path.resolve(__dirname, './config')
    }
  },
  server: {
    port: 5174,
    strictPort: false, // Permet d'utiliser un autre port si 5174 est occupé
    open: true,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000', // Utilise 127.0.0.1 au lieu de localhost
        changeOrigin: true,
        secure: false,
        rewrite: (path) => {
          // Le backend FastAPI a les routes montées directement (sans /api)
          // Donc /api/vincent-dindy/pianos devient /vincent-dindy/pianos
          const rewritten = path.replace(/^\/api/, '');
          console.log('[Vite Proxy]', path, '->', rewritten);
          return rewritten;
        },
        configure: (proxy, _options) => {
          proxy.on('error', (err, _req, _res) => {
            console.error('[Vite Proxy Error]', err);
          });
          proxy.on('proxyReq', (proxyReq, req, _res) => {
            console.log('[Vite Proxy] Proxying:', req.method, req.url, '->', proxyReq.path);
          });
          proxy.on('proxyRes', (proxyRes, req, _res) => {
            console.log('[Vite Proxy] Response:', req.url, '->', proxyRes.statusCode);
          });
        }
      }
    }
  }
});
