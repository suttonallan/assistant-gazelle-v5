/**
 * Service pour récupérer les techniciens depuis Supabase profiles
 * Source unique de vérité pour les noms et IDs des techniciens
 */

// Cette fonction sera appelée depuis le backend via API
// Pour l'instant, on crée un service qui sera complété
export const getTechniciansFromProfiles = async (apiUrl) => {
  try {
    // Appeler l'endpoint backend qui récupère depuis Supabase profiles
    // Utilise la config centralisée pour déterminer l'URL du backend
    const backendUrl = apiUrl || (import.meta.env.PROD
      ? (import.meta.env.VITE_API_URL || 'https://assistant-gazelle-v5-api.onrender.com')
      : 'http://localhost:8000')
    const response = await fetch(`${backendUrl}/api/technicians/profiles`)
    
    if (!response.ok) {
      throw new Error(`Erreur ${response.status}: ${response.statusText}`)
    }
    
    const data = await response.json()
    return data.technicians || []
  } catch (err) {
    console.error('❌ Erreur chargement techniciens depuis profiles:', err)
    return []
  }
}

/**
 * Mappe les techniciens depuis profiles vers le format attendu par l'inventaire
 * Format attendu: { id, name, username }
 */
export const mapTechniciansToInventoryFormat = (profiles) => {
  return profiles.map(profile => {
    // MAPPING FLEXIBLE - Gérer plusieurs formats de champs
    const name = profile.first_name || profile.name || profile.email?.split('@')[0] || 'Sans nom'
    const username = profile.username || profile.email?.split('@')[0] || name.toLowerCase()
    
    return {
      id: profile.gazelle_user_id || profile.id,
      gazelle_user_id: profile.gazelle_user_id || profile.id, // ID Gazelle est la clé
      name: name,
      username: username,
      first_name: profile.first_name || name,
      last_name: profile.last_name || '',
      email: profile.email || ''
    }
  })
}
