/**
 * Piano Types - Architecture réutilisable multi-institutions
 *
 * Type safety strict pour:
 * - Données Gazelle API (immutables)
 * - Overlays Supabase (mutables)
 * - Updates optimistes
 */

/** Statut d'un piano dans le workflow de tournée */
export enum PianoStatus {
  /** État par défaut - aucune action requise */
  Normal = 'normal',

  /** Piano proposé pour la tournée (devient Jaune) */
  Proposed = 'proposed',

  /** Priorité haute - Piano de concert (devient Ambre) */
  Top = 'top',

  /** Travail complété dans la tournée active (devient Vert) */
  Completed = 'completed'
}

/** Type de piano (Grand, Digital Grand, Upright) */
export enum PianoType {
  Grand = 'G',
  DigitalGrand = 'D',
  Upright = 'U'
}

/** Catégories d'usage des pianos */
export enum PianoUsage {
  Piano = 'Piano',
  Accompagnement = 'Accompagnement',
  Pratique = 'Pratique',
  Concert = 'Concert',
  Enseignement = 'Enseignement',
  Loisir = 'Loisir'
}

/**
 * Piano complet - fusion Gazelle API + Supabase overlays
 *
 * @remarks
 * Les données Gazelle sont la source de vérité pour les infos techniques.
 * Les overlays Supabase contiennent le workflow (status, notes, etc.)
 */
export interface Piano {
  // ==========================================
  // GAZELLE DATA (immutable, source of truth)
  // ==========================================

  /** Unique ID from Gazelle - PRIMARY KEY */
  gazelleId: string;

  /** Serial number (peut être null ou dupliqué) */
  serialNumber: string | null;

  /** Manufacturer (Yamaha, Steinway, etc.) */
  make: string;

  /** Model name */
  model: string | null;

  /** Physical location (Local 123, Studio A, etc.) */
  location: string;

  /** Type de piano */
  type: PianoType;

  /** Date du dernier accord (calculé par Gazelle) */
  lastTuned: Date | null;

  /** Prochain service recommandé */
  nextService: Date | null;

  /** Intervalle de service en mois */
  serviceIntervalMonths: number;

  /** Tags Gazelle (array, ex: ["non"] pour masquer) */
  tags: string[];

  // ==========================================
  // SUPABASE OVERLAYS (mutable, workflow data)
  // ==========================================

  /** Statut dans le workflow de tournée */
  status: PianoStatus;

  /** Catégorie d'usage du piano */
  usage: PianoUsage | null;

  /** Tâches assignées par le gestionnaire (Nick) */
  aFaire: string | null;

  /** Travail effectué par le technicien */
  travail: string | null;

  /** Notes techniques et observations */
  observations: string | null;

  /**
   * ID de la tournée où ce piano a été complété
   * Utilisé pour déterminer si Vert ou non
   */
  completedInTourneeId: string | null;

  /**
   * Piano masqué de l'inventaire
   * Si true, n'apparaît PAS dans Tournées ni Technicien
   * Visible seulement dans Inventaire avec filtre
   */
  isHidden: boolean;

  /** Dernière mise à jour overlay */
  updatedAt: Date;

  /** Email de l'utilisateur ayant fait la MAJ */
  updatedBy: string | null;
}

/**
 * Données brutes de Gazelle GraphQL
 * Utilisé pour parsing initial avant fusion avec overlays
 */
export interface GazellePianoRaw {
  id: string;
  serialNumber?: string | null;
  make: string;
  model?: string | null;
  location: string;
  type: 'GRAND' | 'DIGITAL_GRAND' | 'UPRIGHT';
  status?: string;
  notes?: string;
  calculatedLastService?: string | null;
  calculatedNextService?: string | null;
  serviceIntervalMonths?: number;
  tags?: string[] | null;
}

/**
 * Update partiel d'un piano
 * Toutes propriétés optionnelles sauf pianoId et updatedBy
 */
export interface PianoUpdate {
  /** Gazelle ID du piano à modifier */
  pianoId: string;

  /** Nouveau statut */
  status?: PianoStatus;

  /** Nouvelle catégorie usage */
  usage?: PianoUsage;

  /** Nouvelles tâches à faire */
  aFaire?: string;

  /** Travail effectué */
  travail?: string;

  /** Nouvelles observations */
  observations?: string;

  /** Marquer comme complété dans une tournée */
  completedInTourneeId?: string | null;

  /** Travail complété (checkbox) */
  isWorkCompleted?: boolean;

  /** Date de complétion (pour push Gazelle) */
  completedAt?: string;

  /** Auteur de la modification (REQUIS) */
  updatedBy: string;
}

/**
 * Batch update - array de mises à jour
 */
export interface PianoBatchUpdate {
  updates: PianoUpdate[];
}

/**
 * Réponse API pour fetch pianos
 */
export interface PianosResponse {
  pianos: Piano[];
  count: number;
  source: 'gazelle' | 'cache';
  lastSync?: Date;
}

/**
 * Filtre pour requêtes pianos
 */
export interface PianoFilters {
  /** Filtrer par statut */
  status?: PianoStatus[];

  /** Filtrer par usage */
  usage?: PianoUsage[];

  /** Filtrer par type */
  type?: PianoType[];

  /** Filtrer par tournée */
  tourneeId?: string;

  /** Recherche texte (nom, local, serial) */
  search?: string;

  /** Filtrer par âge accord (mois) */
  lastTunedMonthsAgo?: {
    min?: number;
    max?: number;
  };
}

/**
 * Options de tri
 */
export type PianoSortField =
  | 'location'
  | 'make'
  | 'lastTuned'
  | 'status'
  | 'usage';

export type PianoSortOrder = 'asc' | 'desc';

export interface PianoSortConfig {
  field: PianoSortField;
  order: PianoSortOrder;
}

/**
 * Helper type: Piano ID (toujours gazelleId)
 */
export type PianoId = string;

/**
 * Helper: Piano minimaliste pour sélection
 */
export interface PianoListItem {
  gazelleId: string;
  make: string;
  model: string | null;
  location: string;
  status: PianoStatus;
}
