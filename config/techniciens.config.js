/**
 * ╔═══════════════════════════════════════════════════════════════════════════╗
 * ║                    CONFIGURATION CENTRALISÉE DES TECHNICIENS              ║
 * ║                          SOURCE DE VÉRITÉ UNIQUE                          ║
 * ╚═══════════════════════════════════════════════════════════════════════════╝
 *
 * Ce fichier est la SEULE source de vérité pour toutes les informations des techniciens.
 * TOUS les autres fichiers doivent importer depuis ici.
 *
 * ⚠️ NE JAMAIS dupliquer ces informations ailleurs dans le code!
 * ⚠️ TOUJOURS importer depuis ce fichier.
 *
 * Utilisation:
 *   import { TECHNICIENS, getTechnicienById, getTechnicienByEmail } from '@config/techniciens.config'
 */

// ==========================================
// MAPPING COMPLET DES TECHNICIENS
// ==========================================

export const TECHNICIENS = {
  allan: {
    // Identifiants
    gazelleId: 'usr_ofYggsCDt2JAVeNP',
    supabaseId: 'usr_ofYggsCDt2JAVeNP', // Même ID pour Gazelle et Supabase

    // Informations personnelles
    prenom: 'Allan',
    nom: 'Sutton',
    nomComplet: 'Allan Sutton',
    abbreviation: 'Allan',
    username: 'allan',

    // Contact
    email: 'asutton@piano-tek.com',
    slack: null, // Réservé pour usage futur

    // Rôle et permissions
    role: 'admin',
    isAdmin: true,
    isTechnicien: true,
    isAssistant: false
  },

  nicolas: {
    // Identifiants
    gazelleId: 'usr_HcCiFk7o0vZ9xAI0',
    supabaseId: 'usr_HcCiFk7o0vZ9xAI0',

    // Informations personnelles
    prenom: 'Nicolas',
    nom: 'Lessard',
    nomComplet: 'Nicolas Lessard',
    abbreviation: 'Nick', // ⭐ IMPORTANT: Afficher "Nick" dans l'UI
    username: 'nicolas',

    // Contact
    email: 'nlessard@piano-tek.com',
    slack: null,

    // Rôle et permissions
    role: 'technicien',
    isAdmin: false,
    isTechnicien: true,
    isAssistant: false
  },

  jeanphilippe: {
    // Identifiants
    gazelleId: 'usr_ReUSmIJmBF86ilY1',
    supabaseId: 'usr_ReUSmIJmBF86ilY1',

    // Informations personnelles
    prenom: 'Jean-Philippe',
    nom: 'Reny',
    nomComplet: 'Jean-Philippe Reny',
    abbreviation: 'JP',
    username: 'jeanphilippe',

    // Contact
    email: 'jpreny@gmail.com',
    slack: null,

    // Rôle et permissions
    role: 'technicien',
    isAdmin: false,
    isTechnicien: true,
    isAssistant: false
  }
}

// ==========================================
// LISTES UTILITAIRES
// ==========================================

/**
 * Liste des techniciens sous forme de tableau
 * Utiliser pour boucles, dropdowns, etc.
 */
export const TECHNICIENS_LISTE = Object.values(TECHNICIENS)

/**
 * Liste des IDs Gazelle uniquement
 */
export const GAZELLE_IDS = TECHNICIENS_LISTE.map(t => t.gazelleId)

/**
 * Liste des emails uniquement
 */
export const EMAILS = TECHNICIENS_LISTE.map(t => t.email)

/**
 * Liste des usernames uniquement
 */
export const USERNAMES = TECHNICIENS_LISTE.map(t => t.username)

// ==========================================
// FONCTIONS UTILITAIRES
// ==========================================

/**
 * Récupérer un technicien par son ID Gazelle
 * @param {string} gazelleId - ID Gazelle (ex: "usr_HcCiFk7o0vZ9xAI0")
 * @returns {Object|null} Objet technicien ou null si non trouvé
 */
export function getTechnicienById(gazelleId) {
  return TECHNICIENS_LISTE.find(t => t.gazelleId === gazelleId) || null
}

/**
 * Récupérer un technicien par son email
 * @param {string} email - Email du technicien
 * @returns {Object|null} Objet technicien ou null si non trouvé
 */
export function getTechnicienByEmail(email) {
  if (!email) return null
  const emailLower = email.toLowerCase()
  return TECHNICIENS_LISTE.find(t => t.email.toLowerCase() === emailLower) || null
}

/**
 * Récupérer un technicien par son username
 * @param {string} username - Username (ex: "nicolas", "allan")
 * @returns {Object|null} Objet technicien ou null si non trouvé
 */
export function getTechnicienByUsername(username) {
  if (!username) return null
  const usernameLower = username.toLowerCase()
  return TECHNICIENS_LISTE.find(t => t.username.toLowerCase() === usernameLower) || null
}

/**
 * Convertir un nom (Nicolas, Nick, etc.) vers le username normalisé
 * Gère les variations de noms et les alias
 * @param {string} nom - Nom ou alias (ex: "Nick", "Nicolas", "Allan")
 * @returns {string|null} Username normalisé ou null
 */
export function nomVersUsername(nom) {
  if (!nom) return null

  const nomLower = nom.toLowerCase().trim()

  // Mapping des variations de noms
  const variations = {
    'nicolas': 'nicolas',
    'nick': 'nicolas',
    'nicolas lessard': 'nicolas',
    'n. lessard': 'nicolas',

    'allan': 'allan',
    'allan sutton': 'allan',
    'a. sutton': 'allan',

    'jean-philippe': 'jeanphilippe',
    'jeanphilippe': 'jeanphilippe',
    'jp': 'jeanphilippe',
    'jean philippe': 'jeanphilippe',
    'j-p reny': 'jeanphilippe'
  }

  return variations[nomLower] || null
}

/**
 * Obtenir l'abbréviation d'affichage (ex: "Nick" au lieu de "Nicolas")
 * @param {string} gazelleId - ID Gazelle
 * @returns {string} Abbréviation pour affichage UI
 */
export function getAbbreviation(gazelleId) {
  const tech = getTechnicienById(gazelleId)
  return tech?.abbreviation || tech?.prenom || 'Inconnu'
}

/**
 * Vérifier si un ID Gazelle est valide
 * @param {string} gazelleId - ID à vérifier
 * @returns {boolean} true si l'ID existe
 */
export function isValidGazelleId(gazelleId) {
  return GAZELLE_IDS.includes(gazelleId)
}

// ==========================================
// EXPORTS PAR DÉFAUT
// ==========================================

export default {
  TECHNICIENS,
  TECHNICIENS_LISTE,
  GAZELLE_IDS,
  EMAILS,
  USERNAMES,
  getTechnicienById,
  getTechnicienByEmail,
  getTechnicienByUsername,
  nomVersUsername,
  getAbbreviation,
  isValidGazelleId
}
