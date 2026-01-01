/**
 * Configuration Multi-Institutions
 *
 * Architecture réutilisable permettant d'adapter le système
 * pour Vincent d'Indy, Orford, Place des Arts, etc.
 *
 * @example
 * ```ts
 * import { getInstitutionConfig } from '@config/institutions';
 *
 * const config = getInstitutionConfig('vincent-dindy');
 * console.log(config.name); // "Conservatoire de musique de Montréal"
 * ```
 */

import type {
  InstitutionConfig,
  InstitutionRegistry,
  ColorRule
} from '@types/institution.types';
import type { Piano } from '@types/piano.types';
import { PianoStatus } from '@types/piano.types';
import { TourneeStatus } from '@types/tournee.types';

// ==========================================
// VINCENT D'INDY CONFIGURATION
// ==========================================

/**
 * Règles de couleur spécifiques Vincent d'Indy
 * Ordre = priorité descendante
 */
const vincentDIndyColorRules: ColorRule[] = [
  {
    name: 'Selected (Purple)',
    priority: 100,
    className: 'bg-purple-100 border-purple-300',
    condition: (piano: Piano, context) =>
      context.selectedPianoIds.has(piano.gazelleId)
  },
  {
    name: 'Top Priority (Amber)',
    priority: 90,
    className: 'bg-amber-200 border-amber-400',
    condition: (piano: Piano, context) =>
      context.topPianosInTournee.has(piano.gazelleId)
  },
  {
    name: 'Completed in Active Tournee (Green)',
    priority: 80,
    className: 'bg-green-200 border-green-400',
    condition: (piano: Piano, context) =>
      piano.status === PianoStatus.Completed &&
      piano.completedInTourneeId !== null &&
      piano.completedInTourneeId === context.activeTourneeId
  },
  {
    name: 'Proposed or In Tournee (Yellow)',
    priority: 70,
    className: 'bg-yellow-200 border-yellow-400',
    condition: (piano: Piano, context) => {
      // JAUNE = UNIQUEMENT si présent dans tournee_pianos
      // Le hook usePianoColors ajoute cette condition via isPianoInActiveTournee
      // On ne vérifie PAS le status 'proposed' ici
      return false;
    }
  },
  {
    name: 'Normal (White)',
    priority: 0,
    className: 'bg-white border-gray-200',
    condition: () => true // Défaut
  }
];

const VINCENT_DINDY_CONFIG: InstitutionConfig = {
  id: 'vincent-dindy',
  name: 'Conservatoire de musique de Montréal - Vincent d\'Indy',
  shortName: 'Vincent d\'Indy',
  gazelleClientId: import.meta.env.VITE_GAZELLE_CLIENT_ID_VDI || '',

  features: {
    tournees: true,
    inventory: true,
    topPriority: true,
    mobileView: true,
    batchOperations: true,
    rangeSelection: true,
    technicianReports: true,
    realtimeSync: true
  },

  colorRules: {
    enableTopPriority: true,
    enableCompletedTracking: true,
    customRules: vincentDIndyColorRules
  },

  limits: {
    maxPianos: 100,
    maxActiveTournees: 1,
    maxPianosPerTournee: 100,
    maxTourneeDurationDays: 90
  },

  tourneeLifecycle: {
    allowMultipleActive: false,
    autoArchiveAfterEndDate: false,
    archiveGraceDays: 7,
    lockCompletedTournees: true
  },

  apiPaths: {
    pianos: '/vincent-dindy/pianos',
    tournees: '/vincent-dindy/tournees',
    reports: '/vincent-dindy/reports',
    inventory: '/vincent-dindy/inventory'
  },

  ui: {
    primaryColor: 'blue',
    showLogo: false,
    defaultVisibleColumns: [
      'select',
      'local',
      'piano',
      'type',
      'lastTuned',
      'aFaire',
      'travail',
      'observations',
      'actions'
    ],
    delayFormat: 'weeks'
  },

  roles: {
    admins: [
      'michelle@example.com', // Remplacer par vrais emails
      'nick@example.com'
    ],
    technicians: [
      'jeanphilippe@example.com',
      'louise@example.com',
      'nicolas@example.com'
    ],
    readonly: []
  }
};

// ==========================================
// ORFORD CONFIGURATION (Template pour futur)
// ==========================================

const ORFORD_CONFIG: Partial<InstitutionConfig> = {
  id: 'orford',
  name: 'Centre d\'arts Orford',
  shortName: 'Orford',
  gazelleClientId: import.meta.env.VITE_GAZELLE_CLIENT_ID_ORFORD || '',

  features: {
    tournees: true,
    inventory: true,
    topPriority: false, // Pas de priorité Ambre à Orford
    mobileView: true,
    batchOperations: true,
    rangeSelection: false, // Shift+Clic désactivé
    technicianReports: false,
    realtimeSync: true
  },

  limits: {
    maxPianos: 50,
    maxActiveTournees: 1,
    maxPianosPerTournee: 50,
    maxTourneeDurationDays: 30
  },

  ui: {
    primaryColor: 'green',
    delayFormat: 'days'
  }

  // TODO: Compléter quand Orford sera intégré
};

// ==========================================
// PLACE DES ARTS CONFIGURATION (Future)
// ==========================================

const PLACE_DES_ARTS_CONFIG: Partial<InstitutionConfig> = {
  id: 'place-des-arts',
  name: 'Place des Arts',
  shortName: 'PDA',
  gazelleClientId: import.meta.env.VITE_GAZELLE_CLIENT_ID_PDA || '',

  features: {
    tournees: false, // Place des Arts n'utilise pas le système de tournées
    inventory: true,
    topPriority: false,
    mobileView: false,
    batchOperations: true,
    rangeSelection: false,
    technicianReports: false,
    realtimeSync: false // Utilise système email existant
  },

  limits: {
    maxPianos: 200,
    maxActiveTournees: 0,
    maxPianosPerTournee: 0,
    maxTourneeDurationDays: 0
  }

  // TODO: Compléter quand Place des Arts sera intégré
};

// ==========================================
// REGISTRY & HELPERS
// ==========================================

/**
 * Registry centralisé de toutes les configurations
 */
export const INSTITUTION_REGISTRY: Partial<InstitutionRegistry> = {
  'vincent-dindy': VINCENT_DINDY_CONFIG
  // 'orford': ORFORD_CONFIG as InstitutionConfig,
  // 'place-des-arts': PLACE_DES_ARTS_CONFIG as InstitutionConfig
};

/**
 * Récupère la configuration d'une institution
 *
 * @param id - ID de l'institution
 * @returns Configuration complète
 * @throws Error si institution non trouvée
 *
 * @example
 * ```ts
 * const config = getInstitutionConfig('vincent-dindy');
 * if (config.features.tournees) {
 *   // Afficher UI tournées
 * }
 * ```
 */
export function getInstitutionConfig(
  id: keyof typeof INSTITUTION_REGISTRY
): InstitutionConfig {
  const config = INSTITUTION_REGISTRY[id];

  if (!config) {
    throw new Error(
      `Institution "${id}" not found in registry. Available: ${Object.keys(
        INSTITUTION_REGISTRY
      ).join(', ')}`
    );
  }

  return config;
}

/**
 * Vérifie si une fonctionnalité est activée pour une institution
 *
 * @example
 * ```ts
 * if (hasFeature('vincent-dindy', 'tournees')) {
 *   // Logique tournées
 * }
 * ```
 */
export function hasFeature(
  institutionId: keyof typeof INSTITUTION_REGISTRY,
  feature: keyof InstitutionConfig['features']
): boolean {
  const config = getInstitutionConfig(institutionId);
  return config.features[feature];
}

/**
 * Récupère les règles de couleur pour une institution
 *
 * @example
 * ```ts
 * const rules = getColorRules('vincent-dindy');
 * const pianoColor = rules.find(r => r.condition(piano, context))?.className;
 * ```
 */
export function getColorRules(
  institutionId: keyof typeof INSTITUTION_REGISTRY
): ColorRule[] {
  const config = getInstitutionConfig(institutionId);
  return config.colorRules.customRules || [];
}

/**
 * Vérifie si un utilisateur a le rôle admin
 */
export function isAdmin(
  institutionId: keyof typeof INSTITUTION_REGISTRY,
  userEmail: string
): boolean {
  const config = getInstitutionConfig(institutionId);
  return config.roles.admins.includes(userEmail);
}

/**
 * Vérifie si un utilisateur a le rôle technicien
 */
export function isTechnician(
  institutionId: keyof typeof INSTITUTION_REGISTRY,
  userEmail: string
): boolean {
  const config = getInstitutionConfig(institutionId);
  return config.roles.technicians.includes(userEmail);
}

/**
 * Récupère le rôle d'un utilisateur
 */
export function getUserRole(
  institutionId: keyof typeof INSTITUTION_REGISTRY,
  userEmail: string
): 'admin' | 'technician' | 'readonly' | null {
  const config = getInstitutionConfig(institutionId);

  if (config.roles.admins.includes(userEmail)) return 'admin';
  if (config.roles.technicians.includes(userEmail)) return 'technician';
  if (config.roles.readonly.includes(userEmail)) return 'readonly';

  return null;
}

/**
 * Liste toutes les institutions disponibles
 */
export function listInstitutions(): Array<{
  id: string;
  name: string;
  shortName: string;
}> {
  return Object.values(INSTITUTION_REGISTRY).map((config) => ({
    id: config!.id,
    name: config!.name,
    shortName: config!.shortName
  }));
}

// Export par défaut pour usage simple
export default VINCENT_DINDY_CONFIG;
