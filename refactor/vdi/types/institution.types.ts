/**
 * Institution Configuration Types
 *
 * Architecture réutilisable permettant de configurer
 * le comportement pour chaque institution sans dupliquer le code
 */

import type { PianoStatus } from './piano.types';
import type { Etablissement, TourneeLifecycleConfig } from './tournee.types';

/**
 * Règle de couleur pour un piano
 */
export interface ColorRule {
  /** Priorité (plus haute = appliquée en premier) */
  priority: number;

  /** Classe CSS Tailwind */
  className: string;

  /** Fonction de test */
  condition: (piano: any, context: ColorRuleContext) => boolean;

  /** Nom de la règle (pour debug) */
  name: string;
}

/**
 * Contexte pour évaluation des règles couleur
 */
export interface ColorRuleContext {
  /** ID de la tournée active (si applicable) */
  activeTourneeId: string | null;

  /** IDs des pianos sélectionnés (pour batch) */
  selectedPianoIds: Set<string>;

  /** IDs des pianos marqués "Top" dans la tournée affichée */
  topPianosInTournee: Set<string>;

  /** Date actuelle */
  currentDate: Date;
}

/**
 * Configuration des couleurs par institution
 */
export interface ColorRulesConfig {
  /** Activer la priorité Ambre pour pianos Top */
  enableTopPriority: boolean;

  /** Activer le système Vert basé sur tournée */
  enableCompletedTracking: boolean;

  /** Règles personnalisées (ordre = priorité) */
  customRules?: ColorRule[];
}

/**
 * Configuration des fonctionnalités par institution
 */
export interface InstitutionFeatures {
  /** Système de tournées activé */
  tournees: boolean;

  /** Priorité Top (Ambre) pour concerts */
  topPriority: boolean;

  /** Vue mobile pour techniciens */
  mobileView: boolean;

  /** Batch operations */
  batchOperations: boolean;

  /** Shift+Clic selection par plage */
  rangeSelection: boolean;

  /** Rapports techniciens */
  technicianReports: boolean;

  /** Sync Realtime Supabase */
  realtimeSync: boolean;
}

/**
 * Limites et quotas par institution
 */
export interface InstitutionLimits {
  /** Nombre maximum de pianos */
  maxPianos: number;

  /** Nombre maximum de tournées actives simultanées */
  maxActiveTournees: number;

  /** Nombre maximum de pianos par tournée */
  maxPianosPerTournee: number;

  /** Jours maximum pour une tournée */
  maxTourneeDurationDays: number;
}

/**
 * Configuration complète d'une institution
 */
export interface InstitutionConfig {
  /** Identifiant unique */
  id: Etablissement;

  /** Nom complet */
  name: string;

  /** Nom court (pour UI) */
  shortName: string;

  /** Client ID Gazelle */
  gazelleClientId: string;

  /** Fonctionnalités activées */
  features: InstitutionFeatures;

  /** Règles de couleur */
  colorRules: ColorRulesConfig;

  /** Limites et quotas */
  limits: InstitutionLimits;

  /** Configuration lifecycle tournées */
  tourneeLifecycle: TourneeLifecycleConfig;

  /** Chemins API */
  apiPaths: {
    pianos: string;
    tournees: string;
    reports: string;
    inventory: string;
  };

  /** Configuration UI */
  ui: {
    /** Couleur principale (Tailwind class) */
    primaryColor: string;

    /** Afficher logo institution */
    showLogo: boolean;

    /** URL logo */
    logoUrl?: string;

    /** Colonnes visibles par défaut dans table */
    defaultVisibleColumns: string[];

    /** Format d'affichage délai */
    delayFormat: 'weeks' | 'days' | 'months';
  };

  /** Rôles et permissions */
  roles: {
    /** Emails admins avec tous droits */
    admins: string[];

    /** Emails techniciens avec droits limités */
    technicians: string[];

    /** Emails lecture seule */
    readonly: string[];
  };
}

/**
 * Registry de toutes les institutions configurées
 */
export type InstitutionRegistry = Record<Etablissement, InstitutionConfig>;

/**
 * Helper: Récupérer config d'une institution
 */
export type GetInstitutionConfig = (id: Etablissement) => InstitutionConfig;

/**
 * Template de configuration par défaut
 */
export interface InstitutionConfigTemplate {
  /** Nom template */
  name: string;

  /** Description */
  description: string;

  /** Config partielle (sera merged avec defaults) */
  partial: Partial<InstitutionConfig>;
}

/**
 * Présets de configuration
 */
export enum InstitutionPreset {
  /** Configuration complète (Vincent d'Indy) */
  Full = 'full',

  /** Configuration basique (inventaire simple) */
  Basic = 'basic',

  /** Configuration tournées uniquement */
  TourneesOnly = 'tournees-only',

  /** Configuration mobile-first */
  MobileFirst = 'mobile-first'
}
