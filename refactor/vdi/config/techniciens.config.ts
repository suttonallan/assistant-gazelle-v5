/**
 * ╔═══════════════════════════════════════════════════════════════════════════╗
 * ║                    CONFIGURATION CENTRALISÉE DES TECHNICIENS              ║
 * ║                          SOURCE DE VÉRITÉ UNIQUE - V7                     ║
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
// TYPES
// ==========================================

export interface Technicien {
  // Identifiants
  gazelleId: string;
  supabaseId: string;

  // Informations personnelles
  prenom: string;
  nom: string;
  nomComplet: string;
  abbreviation: string;
  username: string;

  // Contact
  email: string;
  slack: string | null;

  // Rôle et permissions
  role: 'admin' | 'technicien' | 'assistant';
  isAdmin: boolean;
  isTechnicien: boolean;
  isAssistant: boolean;
}

export type TechnicienKey = 'allan' | 'nicolas' | 'jeanphilippe';

// ==========================================
// MAPPING COMPLET DES TECHNICIENS
// ==========================================

export const TECHNICIENS: Record<TechnicienKey, Technicien> = {
  allan: {
    // Identifiants
    gazelleId: 'usr_ofYggsCDt2JAVeNP',
    supabaseId: 'usr_ofYggsCDt2JAVeNP',

    // Informations personnelles
    prenom: 'Allan',
    nom: 'Sutton',
    nomComplet: 'Allan Sutton',
    abbreviation: 'Allan',
    username: 'allan',

    // Contact
    email: 'asutton@piano-tek.com',
    slack: null,

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
};

// ==========================================
// LISTES UTILITAIRES
// ==========================================

/**
 * Liste des techniciens sous forme de tableau
 */
export const TECHNICIENS_LISTE: Technicien[] = Object.values(TECHNICIENS);

/**
 * Liste des IDs Gazelle uniquement
 */
export const GAZELLE_IDS: string[] = TECHNICIENS_LISTE.map(t => t.gazelleId);

/**
 * Liste des emails uniquement
 */
export const EMAILS: string[] = TECHNICIENS_LISTE.map(t => t.email);

/**
 * Liste des usernames uniquement
 */
export const USERNAMES: string[] = TECHNICIENS_LISTE.map(t => t.username);

// ==========================================
// FONCTIONS UTILITAIRES
// ==========================================

/**
 * Récupérer un technicien par son ID Gazelle
 */
export function getTechnicienById(gazelleId: string): Technicien | null {
  return TECHNICIENS_LISTE.find(t => t.gazelleId === gazelleId) || null;
}

/**
 * Récupérer un technicien par son email
 */
export function getTechnicienByEmail(email: string): Technicien | null {
  if (!email) return null;
  const emailLower = email.toLowerCase();
  return TECHNICIENS_LISTE.find(t => t.email.toLowerCase() === emailLower) || null;
}

/**
 * Récupérer un technicien par son username
 */
export function getTechnicienByUsername(username: string): Technicien | null {
  if (!username) return null;
  const usernameLower = username.toLowerCase();
  return TECHNICIENS_LISTE.find(t => t.username.toLowerCase() === usernameLower) || null;
}

/**
 * Convertir un nom (Nicolas, Nick, etc.) vers le username normalisé
 */
export function nomVersUsername(nom: string): string | null {
  if (!nom) return null;

  const nomLower = nom.toLowerCase().trim();

  const variations: Record<string, string> = {
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
  };

  return variations[nomLower] || null;
}

/**
 * Obtenir l'abbréviation d'affichage (ex: "Nick" au lieu de "Nicolas")
 */
export function getAbbreviation(gazelleId: string): string {
  const tech = getTechnicienById(gazelleId);
  return tech?.abbreviation || tech?.prenom || 'Inconnu';
}

/**
 * Vérifier si un ID Gazelle est valide
 */
export function isValidGazelleId(gazelleId: string): boolean {
  return GAZELLE_IDS.includes(gazelleId);
}

/**
 * Obtenir le nom complet d'un technicien par son ID Gazelle
 */
export function getNomComplet(gazelleId: string): string {
  const tech = getTechnicienById(gazelleId);
  return tech?.nomComplet || 'Inconnu';
}

// ==========================================
// EXPORT PAR DÉFAUT
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
  isValidGazelleId,
  getNomComplet
};
