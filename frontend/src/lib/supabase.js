import { createClient } from '@supabase/supabase-js'

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL || 'https://beblgzvmjqkcillmcavk.supabase.co'
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY || ''

// Créer le client seulement si on a les deux variables
// Sinon, retourner null (les composants utiliseront l'API backend à la place)
let supabase = null

if (supabaseUrl && supabaseAnonKey) {
  try {
    supabase = createClient(supabaseUrl, supabaseAnonKey)
  } catch (err) {
    console.warn('Impossible de créer le client Supabase:', err)
  }
} else {
  console.warn('VITE_SUPABASE_ANON_KEY manquant. Utilisez l\'API backend pour les mises à jour.')
}

export { supabase }
