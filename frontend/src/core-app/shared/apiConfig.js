// Configuration centralisée pour les appels API
// En développement, utilise directement le backend sur port 8000
// En production, utilise VITE_API_URL ou l'URL par défaut
export const API_URL = import.meta.env.PROD 
  ? (import.meta.env.VITE_API_URL || 'https://assistant-gazelle-v5-api.onrender.com')
  : 'http://localhost:8000'
