/**
 * Tournée Types - Architecture réutilisable multi-institutions
 *
 * Gestion des tournées d'accordage avec:
 * - CRUD operations
 * - Statut lifecycle
 * - Sync Supabase Realtime
 */

/** Statut d'une tournée dans son cycle de vie */
export enum TourneeStatus {
  /** Planifiée mais pas encore démarrée */
  Planned = 'planifiee',

  /** Actuellement en cours (une seule active à la fois) */
  Active = 'en_cours',

  /** Terminée et archivée */
  Completed = 'terminee'
}

/** Établissement supporté */
export type Etablissement = 'vincent-dindy' | 'orford' | 'place-des-arts';

/**
 * Tournée complète
 *
 * @remarks
 * - Une seule tournée peut être Active à la fois par établissement
 * - Les pianos Vert sont ceux complétés dans la tournée Active
 * - Quand nouvelle tournée activée, tous les Vert reset
 */
export interface Tournee {
  /** Unique ID - format: tournee_{timestamp} */
  id: string;

  /** Nom de la tournée (ex: "Tournée Hiver 2025") */
  nom: string;

  /** Date de début planifiée */
  dateDebut: Date;

  /** Date de fin planifiée */
  dateFin: Date;

  /** Statut actuel */
  status: TourneeStatus;

  /** Établissement concerné */
  etablissement: Etablissement;

  /** Email du technicien responsable principal */
  technicienResponsable: string | null;

  /**
   * Emails des techniciens assistants (optionnel)
   * @remarks Permet d'assigner plusieurs techniciens à une tournée
   */
  techniciensAssistants: string[];

  /**
   * Liste des IDs Gazelle des pianos inclus
   * @remarks Toujours des gazelleId, jamais serial numbers
   */
  pianoIds: string[];

  /**
   * Set des IDs Gazelle des pianos marqués "Top" (priorité haute) dans cette tournée
   * @remarks Sous-ensemble de pianoIds
   */
  topPianoIds: Set<string>;

  /** Notes optionnelles de la tournée */
  notes: string | null;

  /** Date de création */
  createdAt: Date;

  /** Dernière modification */
  updatedAt: Date;

  /** Créé par (email) */
  createdBy: string;
}

/**
 * Payload pour créer une nouvelle tournée
 */
export interface TourneeCreate {
  /** Nom de la tournée */
  nom: string;

  /** Date de début */
  dateDebut: Date;

  /** Date de fin */
  dateFin: Date;

  /** Établissement */
  etablissement: Etablissement;

  /** Technicien responsable (email) - optionnel */
  technicienResponsable?: string;

  /** Techniciens assistants (emails) - optionnel */
  techniciensAssistants?: string[];

  /** Notes optionnelles */
  notes?: string;

  /** IDs pianos initiaux (optionnel) */
  pianoIds?: string[];
}

/**
 * Payload pour modifier une tournée existante
 */
export interface TourneeUpdate {
  /** ID de la tournée */
  id: string;

  /** Nouveau nom */
  nom?: string;

  /** Nouvelle date début */
  dateDebut?: Date;

  /** Nouvelle date fin */
  dateFin?: Date;

  /** Nouveau statut */
  status?: TourneeStatus;

  /** Nouveau responsable */
  technicienResponsable?: string;

  /** Nouveaux techniciens assistants */
  techniciensAssistants?: string[];

  /** Nouvelles notes */
  notes?: string;

  /** Nouveaux piano IDs */
  pianoIds?: string[];
}

/**
 * Opération d'ajout/retrait piano dans tournée
 */
export interface TourneePianoOperation {
  /** ID de la tournée */
  tourneeId: string;

  /** ID Gazelle du piano */
  pianoId: string;

  /** Ajouter ou retirer */
  operation: 'add' | 'remove';
}

/**
 * Filtre pour requêtes tournées
 */
export interface TourneeFilters {
  /** Filtrer par statut */
  status?: TourneeStatus[];

  /** Filtrer par établissement */
  etablissement?: Etablissement;

  /** Filtrer par responsable */
  technicienResponsable?: string;

  /** Date range */
  dateRange?: {
    start?: Date;
    end?: Date;
  };
}

/**
 * Réponse API pour fetch tournées
 */
export interface TourneesResponse {
  tournees: Tournee[];
  count: number;
  activeTournee: Tournee | null;
}

/**
 * Stats d'une tournée
 */
export interface TourneeStats {
  /** ID de la tournée */
  tourneeId: string;

  /** Total pianos dans la tournée */
  totalPianos: number;

  /** Pianos complétés */
  completed: number;

  /** Pianos proposés (Jaune) */
  proposed: number;

  /** Pianos Top (Ambre) */
  top: number;

  /** Progression en % */
  progressPercent: number;

  /** Temps estimé restant (basé sur vélocité) */
  estimatedDaysRemaining: number | null;
}

/**
 * Helper: Tournée minimaliste pour sélection
 */
export interface TourneeListItem {
  id: string;
  nom: string;
  status: TourneeStatus;
  dateDebut: Date;
  dateFin: Date;
  pianoCount: number;
}

/**
 * Événement Realtime pour tournée
 */
export interface TourneeRealtimeEvent {
  eventType: 'INSERT' | 'UPDATE' | 'DELETE';
  new: Tournee | null;
  old: Tournee | null;
}

/**
 * Configuration lifecycle d'une tournée
 */
export interface TourneeLifecycleConfig {
  /** Autoriser plusieurs tournées actives simultanément */
  allowMultipleActive: boolean;

  /** Auto-archiver après date de fin */
  autoArchiveAfterEndDate: boolean;

  /** Jours de grâce avant archivage automatique */
  archiveGraceDays: number;

  /** Interdire modifications si terminée */
  lockCompletedTournees: boolean;
}

/**
 * Options d'activation de tournée
 */
export interface TourneeActivationOptions {
  /** ID de la tournée à activer */
  tourneeId: string;

  /**
   * Désactiver automatiquement les autres tournées actives
   * @default true
   */
  deactivateOthers?: boolean;

  /**
   * Reset les pianos Vert des anciennes tournées
   * @default true
   */
  resetCompletedPianos?: boolean;
}
