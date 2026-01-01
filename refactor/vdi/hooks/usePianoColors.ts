/**
 * usePianoColors Hook - Dynamic Color Logic
 *
 * Logique métier VDV7 pour couleurs pianos:
 * - Priorité: Ambre > Vert > Jaune > Blanc
 * - Context-aware (tournée active, sélection)
 * - Configurable par institution
 *
 * @example
 * ```tsx
 * function PianoRow({ piano }) {
 *   const { getColor, getColorWithReason } = usePianoColors('vincent-dindy');
 *
 *   const className = getColor(piano);
 *   // "bg-green-200 border-green-400"
 *
 *   return <tr className={className}>...</tr>;
 * }
 * ```
 */

import { useMemo, useCallback } from 'react';
import { getColorRules } from '@config/institutions';
import type { Piano } from '@types/piano.types';
import type { Etablissement } from '@types/tournee.types';
import type { ColorRuleContext } from '@types/institution.types';

// ==========================================
// TYPES
// ==========================================

interface UsePianoColorsOptions {
  /** ID tournée active (pour logique Vert) */
  activeTourneeId?: string | null;

  /** IDs pianos sélectionnés (pour couleur Purple) */
  selectedPianoIds?: Set<string>;

  /** Pianos dans tournée active (pour couleur Jaune) */
  pianosInActiveTournee?: Set<string>;

  /** Pianos marqués "Top" dans la tournée affichée (pour couleur Ambre) */
  topPianosInTournee?: Set<string>;
}

interface ColorResult {
  /** Classe CSS Tailwind */
  className: string;

  /** Raison de la couleur (pour debug/tooltip) */
  reason: string;

  /** Priorité (pour tri si besoin) */
  priority: number;
}

interface UsePianoColorsReturn {
  /**
   * Get couleur d'un piano
   * @returns Classe CSS Tailwind
   */
  getColor: (piano: Piano) => string;

  /**
   * Get couleur avec raison (pour debug/tooltips)
   * @returns { className, reason, priority }
   */
  getColorWithReason: (piano: Piano) => ColorResult;

  /**
   * Get couleurs de tous pianos (batch optimisé)
   * @returns Map<pianoId, className>
   */
  getColorsMap: (pianos: Piano[]) => Map<string, string>;

  /**
   * Check si piano est prioritaire (Ambre ou Vert)
   */
  isPriority: (piano: Piano) => boolean;
}

// ==========================================
// HOOK
// ==========================================

export function usePianoColors(
  etablissement: Etablissement,
  options: UsePianoColorsOptions = {}
): UsePianoColorsReturn {
  const {
    activeTourneeId = null,
    selectedPianoIds = new Set(),
    pianosInActiveTournee = new Set(),
    topPianosInTournee = new Set()
  } = options;

  // Récupérer règles couleur de l'institution
  const colorRules = useMemo(() => {
    return getColorRules(etablissement);
  }, [etablissement]);

  // Context pour évaluation règles
  const context: ColorRuleContext = useMemo(
    () => ({
      activeTourneeId,
      selectedPianoIds,
      topPianosInTournee,
      currentDate: new Date()
    }),
    [activeTourneeId, selectedPianoIds, topPianosInTournee]
  );

  // ==========================================
  // GET COLOR (principal)
  // ==========================================

  const getColor = useCallback(
    (piano: Piano): string => {
      // Cas spécial: Piano dans tournée active → Jaune
      // (même si status !== 'proposed')
      const isPianoInActiveTournee =
        activeTourneeId && pianosInActiveTournee.has(piano.gazelleId);

      // Évaluer règles par priorité
      for (const rule of colorRules) {
        let shouldApply = rule.condition(piano, context);

        // Override pour Jaune: inclure pianos dans tournée active
        if (
          rule.name === 'Proposed or In Tournee (Yellow)' &&
          isPianoInActiveTournee
        ) {
          shouldApply = true;
        }

        if (shouldApply) {
          // DEBUG: Log pour pianos avec status proposed
          if (piano.status === 'proposed') {
            console.log(`[usePianoColors] Piano ${piano.location} (${piano.gazelleId}): status=${piano.status}, rule=${rule.name}, color=${rule.className}`);
          }
          return rule.className;
        }
      }

      // Fallback (normalement jamais atteint si règle "Normal" existe)
      return 'bg-white border-gray-200';
    },
    [colorRules, context, activeTourneeId, pianosInActiveTournee]
  );

  // ==========================================
  // GET COLOR WITH REASON (debug)
  // ==========================================

  const getColorWithReason = useCallback(
    (piano: Piano): ColorResult => {
      const isPianoInActiveTournee =
        activeTourneeId && pianosInActiveTournee.has(piano.gazelleId);

      for (const rule of colorRules) {
        let shouldApply = rule.condition(piano, context);

        if (
          rule.name === 'Proposed or In Tournee (Yellow)' &&
          isPianoInActiveTournee
        ) {
          shouldApply = true;
        }

        if (shouldApply) {
          return {
            className: rule.className,
            reason: rule.name,
            priority: rule.priority
          };
        }
      }

      return {
        className: 'bg-white border-gray-200',
        reason: 'Normal (default)',
        priority: 0
      };
    },
    [colorRules, context, activeTourneeId, pianosInActiveTournee]
  );

  // ==========================================
  // GET COLORS MAP (batch optimisé)
  // ==========================================

  const getColorsMap = useCallback(
    (pianos: Piano[]): Map<string, string> => {
      const map = new Map<string, string>();

      for (const piano of pianos) {
        map.set(piano.gazelleId, getColor(piano));
      }

      return map;
    },
    [getColor]
  );

  // ==========================================
  // IS PRIORITY
  // ==========================================

  const isPriority = useCallback(
    (piano: Piano): boolean => {
      const { reason } = getColorWithReason(piano);
      return (
        reason === 'Top Priority (Amber)' ||
        reason === 'Completed in Active Tournee (Green)'
      );
    },
    [getColorWithReason]
  );

  // ==========================================
  // RETURN
  // ==========================================

  return {
    getColor,
    getColorWithReason,
    getColorsMap,
    isPriority
  };
}

/**
 * Helper: Get badge color basé sur âge accord
 *
 * @example
 * ```tsx
 * const badgeColor = getLastTunedBadgeColor(piano.lastTuned);
 * <span className={`badge ${badgeColor}`}>+6s</span>
 * ```
 */
export function getLastTunedBadgeColor(lastTuned: Date | null): string {
  if (!lastTuned) return 'text-gray-400';

  const monthsAgo = Math.floor(
    (Date.now() - lastTuned.getTime()) / (1000 * 60 * 60 * 24 * 30)
  );

  if (monthsAgo <= 3) return 'text-green-600'; // Récent
  if (monthsAgo <= 6) return 'text-yellow-600'; // Moyen
  if (monthsAgo <= 12) return 'text-orange-600'; // Ancien
  return 'text-red-600'; // Très ancien
}

/**
 * Helper: Get icône basé sur statut piano
 */
export function getPianoStatusIcon(status: string): string {
  switch (status) {
    case 'top':
      return '⭐'; // Priorité haute
    case 'completed':
      return '✅'; // Complété
    case 'proposed':
      return '📋'; // À faire
    default:
      return '⚪'; // Normal
  }
}

/**
 * Helper: Get texte descriptif pour couleur (tooltips)
 */
export function getColorDescription(reason: string): string {
  switch (reason) {
    case 'Selected (Purple)':
      return 'Piano sélectionné pour action groupée';
    case 'Top Priority (Amber)':
      return 'Piano de concert - Priorité maximale';
    case 'Completed in Active Tournee (Green)':
      return 'Accordé dans la tournée active';
    case 'Proposed or In Tournee (Yellow)':
      return 'À accorder dans cette tournée';
    case 'Normal (White)':
      return 'Aucune action requise';
    default:
      return reason;
  }
}

export default usePianoColors;
