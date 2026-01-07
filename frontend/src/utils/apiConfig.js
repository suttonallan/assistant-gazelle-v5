// Configuration centralisée pour les appels API
// En développement, force l'utilisation du proxy Vite (URL vide)
// En production, utilise VITE_API_URL ou l'URL par défaut
export const API_URL = import.meta.env.PROD 
  ? (import.meta.env.VITE_API_URL || 'https://assistant-gazelle-v5-api.onrender.com')
  : ''




