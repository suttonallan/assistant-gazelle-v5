// Configuration centralisée pour les appels API
// En développement, force l'utilisation du proxy Vite (URL vide)
// En production, utilise VITE_API_URL ou l'URL par défaut

// Détection robuste de l'environnement
const isProduction = import.meta.env.PROD || import.meta.env.MODE === 'production'

// URL de l'API
// Priorité: 1. VITE_API_URL (variable d'environnement), 2. URL par défaut Render, 3. Vide (dev)
export const API_URL = isProduction
  ? (import.meta.env.VITE_API_URL || 'https://assistant-gazelle-v5-api.onrender.com')
  : ''

// Debug en développement (pour vérifier la configuration)
if (!isProduction) {
  console.log('[apiConfig] Mode développement - API_URL vide (utilise proxy Vite)')
} else {
  console.log('[apiConfig] Mode production - API_URL:', API_URL)
}




