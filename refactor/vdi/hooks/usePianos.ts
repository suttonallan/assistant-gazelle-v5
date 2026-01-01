/**
 * usePianos Hook - Piano Management with Realtime Sync
 *
 * Hook principal pour:
 * - Fetch pianos depuis Gazelle API + Supabase overlays
 * - Realtime subscriptions (Mac ↔ iPad sync)
 * - Filtrage et tri
 * - Updates optimistes
 *
 * @example
 * ```tsx
 * function PianosTable() {
 *   const {
 *     pianos,
 *     loading,
 *     error,
 *     updatePiano,
 *     refreshPianos
 *   } = usePianos('vincent-dindy');
 *
 *   return <div>{pianos.map(p => <PianoRow piano={p} />)}</div>;
 * }
 * ```
 */

import { useState, useEffect, useCallback, useMemo } from 'react';
import { supabase, subscribeToPianos } from '@lib/supabase.client';
import { formatSupabaseError } from '@lib/supabase.client';
import { keysToSnakeCase, keysToCamelCase } from '@lib/utils';
import type { Piano, PianoUpdate, PianoFilters, PianoSortConfig } from '@types/piano.types';
import type { Etablissement } from '@types/tournee.types';

// ==========================================
// TYPES
// ==========================================

interface UsePianosOptions {
  /** Auto-fetch au mount */
  autoFetch?: boolean;

  /** Filtres initiaux */
  initialFilters?: PianoFilters;

  /** Tri initial */
  initialSort?: PianoSortConfig;

  /** Enable Realtime subscriptions */
  enableRealtime?: boolean;

  /** Inclure les pianos masqués (isHidden=true) */
  includeHidden?: boolean;
}

interface UsePianosReturn {
  /** Liste des pianos */
  pianos: Piano[];

  /** Loading state */
  loading: boolean;

  /** Error state */
  error: string | null;

  /** Pianos filtrés (selon filters) */
  filteredPianos: Piano[];

  /** Filters actuels */
  filters: PianoFilters;

  /** Changer filters */
  setFilters: (filters: PianoFilters) => void;

  /** Sort config actuel */
  sortConfig: PianoSortConfig | null;

  /** Changer tri */
  setSortConfig: (config: PianoSortConfig | null) => void;

  /** Refresh pianos depuis API */
  refreshPianos: () => Promise<void>;

  /** Update un piano (optimiste) */
  updatePiano: (pianoId: string, updates: Partial<PianoUpdate>) => Promise<void>;

  /** Get piano par ID */
  getPiano: (pianoId: string) => Piano | undefined;

  /** Dernière sync */
  lastSync: Date | null;
}

// ==========================================
// HOOK
// ==========================================

export function usePianos(
  etablissement: Etablissement,
  options: UsePianosOptions = {}
): UsePianosReturn {
  const {
    autoFetch = true,
    includeHidden = false,
    initialFilters = {},
    initialSort = null,
    enableRealtime = true
  } = options;

  // State
  const [pianos, setPianos] = useState<Piano[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [filters, setFilters] = useState<PianoFilters>(initialFilters);
  const [sortConfig, setSortConfig] = useState<PianoSortConfig | null>(initialSort);
  const [lastSync, setLastSync] = useState<Date | null>(null);

  // ==========================================
  // FETCH PIANOS
  // ==========================================

  const fetchPianos = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      // Déterminer l'endpoint API selon l'établissement
      const apiEndpoint = 
        etablissement === 'place-des-arts' 
          ? '/api/place-des-arts/pianos'
          : '/api/vincent-dindy/pianos';
      
      // Déterminer la table Supabase selon l'établissement
      const supabaseTable = 
        etablissement === 'place-des-arts'
          ? 'place_des_arts_piano_updates'  // TODO: Créer cette table ou utiliser vincent_dindy_piano_updates avec filtre
          : 'vincent_dindy_piano_updates';

      // ÉTAPE 1: Fetch pianos depuis Gazelle API (données statiques)
      const response = await fetch(
        `${apiEndpoint}?include_inactive=${includeHidden}`
      );

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const data = await response.json();

      // ÉTAPE 2: Fetch overlays depuis Supabase (données dynamiques)
      // Note: Pour Place des Arts, on utilise temporairement la même table
      // mais on pourrait filtrer par client_id si ajouté à la table
      const { data: overlays, error: overlayError } = await supabase
        .from('vincent_dindy_piano_updates')  // TODO: Utiliser supabaseTable quand créée
        .select('*');

      if (overlayError) {
        console.warn('[usePianos] Overlay fetch error:', overlayError);
        // Continue sans overlays si erreur
      }

      // ÉTAPE 3: Créer map des overlays par gazelleId
      const overlayMap = new Map<string, any>();
      if (overlays) {
        overlays.forEach((overlay) => {
          overlayMap.set(overlay.gazelle_id, overlay);
        });
      }

      // ÉTAPE 4: Merger Gazelle data + Supabase overlays
      const transformedPianos: Piano[] = data.pianos.map((p: any) => {
        const gazelleId = p.gazelleId || p.id;
        const overlay = overlayMap.get(gazelleId);

        // Données statiques de Gazelle
        const gazelleData = {
          gazelleId,
          serialNumber: p.serie || p.serialNumber || null,
          make: p.piano || p.make || '',
          model: p.modele || p.model || null,
          location: p.local || p.location || '',
          type: p.type || 'U',
          lastTuned: p.dernierAccord ? new Date(p.dernierAccord) : (p.lastTuned ? new Date(p.lastTuned) : null),
          nextService: p.prochainAccord ? new Date(p.prochainAccord) : (p.nextService ? new Date(p.nextService) : null),
          serviceIntervalMonths: p.serviceIntervalMonths || 12,
          tags: p.tags || [],
          usage: p.usage || null,
          aFaire: p.aFaire || null
        };

        // CRITICAL: Vérifier étiquette "non" (masquer automatiquement)
        const hasNonTag = gazelleData.tags.some(
          (tag) => tag.toLowerCase() === 'non'
        );

        // Données dynamiques de Supabase (overlay prioritaire)
        const dynamicData = overlay
          ? {
              status: overlay.status || 'normal',
              notes: overlay.notes || null,
              observations: overlay.observations || null,
              travail: overlay.travail || null,
              lastTuned: overlay.last_tuned_date ? new Date(overlay.last_tuned_date) : gazelleData.lastTuned,
              completedInTourneeId: overlay.completed_in_tournee_id || null,
              // Si étiquette "non" OU is_hidden=true → masqué
              isHidden: hasNonTag || overlay.is_hidden || false,
              updatedAt: overlay.updated_at ? new Date(overlay.updated_at) : new Date(),
              updatedBy: overlay.updated_by || null
            }
          : {
              // Valeurs par défaut si pas d'overlay
              status: 'normal',
              notes: null,
              observations: null,
              travail: null,
              completedInTourneeId: null,
              // Si étiquette "non" → masqué automatiquement
              isHidden: hasNonTag,
              updatedAt: new Date(),
              updatedBy: null
            };

        // Merger les deux sources
        return {
          ...gazelleData,
          ...dynamicData
        };
      });

      setPianos(transformedPianos);
      setLastSync(new Date());
    } catch (err) {
      console.error('[usePianos] Fetch error:', err);
      setError(err instanceof Error ? err.message : 'Erreur inconnue');
    } finally {
      setLoading(false);
    }
  }, [includeHidden]);

  // ==========================================
  // UPDATE PIANO
  // ==========================================

  const updatePiano = useCallback(
    async (pianoId: string, updates: Partial<PianoUpdate>) => {
      // Optimistic update
      setPianos((prev) =>
        prev.map((p) =>
          p.gazelleId === pianoId
            ? {
                ...p,
                ...updates,
                updatedAt: new Date()
              }
            : p
        )
      );

      try {
        // Convert to snake_case pour API Python
        const snakeCaseUpdates = keysToSnakeCase(updates);

        // Déterminer la table selon l'établissement
        const supabaseTable = 
          etablissement === 'place-des-arts'
            ? 'place_des_arts_piano_updates'  // TODO: Créer cette table
            : 'vincent_dindy_piano_updates';
        
        const { error: updateError } = await supabase
          .from('vincent_dindy_piano_updates')  // TODO: Utiliser supabaseTable quand créée
          .upsert(
            {
              gazelle_id: pianoId,
              ...snakeCaseUpdates,
              updated_at: new Date().toISOString()
            },
            { onConflict: 'gazelle_id' }
          );

        if (updateError) {
          throw updateError;
        }
      } catch (err) {
        console.error('[usePianos] Update error:', err);
        // Rollback optimistic update
        await fetchPianos();
        throw new Error(formatSupabaseError(err));
      }
    },
    [fetchPianos]
  );

  // ==========================================
  // GET PIANO
  // ==========================================

  const getPiano = useCallback(
    (pianoId: string): Piano | undefined => {
      return pianos.find((p) => p.gazelleId === pianoId);
    },
    [pianos]
  );

  // ==========================================
  // FILTERED PIANOS
  // ==========================================

  const filteredPianos = useMemo(() => {
    let result = [...pianos];

    // CRITICAL: Filtre isHidden (sauf si includeHidden = true)
    if (!includeHidden) {
      result = result.filter((p) => !p.isHidden);
    }

    // Filtre par statut
    if (filters.status && filters.status.length > 0) {
      result = result.filter((p) => filters.status!.includes(p.status));
    }

    // Filtre par usage
    if (filters.usage && filters.usage.length > 0) {
      result = result.filter((p) => p.usage && filters.usage!.includes(p.usage));
    }

    // Filtre par type
    if (filters.type && filters.type.length > 0) {
      result = result.filter((p) => filters.type!.includes(p.type));
    }

    // Filtre par tournée
    if (filters.tourneeId) {
      // Cette logique sera complétée par useTournees
      // Pour l'instant, filtre par completedInTourneeId
      result = result.filter((p) => p.completedInTourneeId === filters.tourneeId);
    }

    // Filtre par recherche texte
    if (filters.search && filters.search.trim() !== '') {
      const searchLower = filters.search.toLowerCase();
      result = result.filter(
        (p) =>
          p.make.toLowerCase().includes(searchLower) ||
          p.location.toLowerCase().includes(searchLower) ||
          (p.model && p.model.toLowerCase().includes(searchLower)) ||
          (p.serialNumber && p.serialNumber.toLowerCase().includes(searchLower))
      );
    }

    // Filtre par âge accord
    if (filters.lastTunedMonthsAgo) {
      const { min, max } = filters.lastTunedMonthsAgo;
      result = result.filter((p) => {
        if (!p.lastTuned) return false;

        const monthsAgo = Math.floor(
          (Date.now() - p.lastTuned.getTime()) / (1000 * 60 * 60 * 24 * 30)
        );

        if (min !== undefined && monthsAgo < min) return false;
        if (max !== undefined && monthsAgo > max) return false;

        return true;
      });
    }

    // Appliquer tri
    if (sortConfig) {
      result.sort((a, b) => {
        const aVal = a[sortConfig.field];
        const bVal = b[sortConfig.field];

        if (aVal === bVal) return 0;

        let comparison = 0;
        if (aVal === null || aVal === undefined) {
          comparison = 1;
        } else if (bVal === null || bVal === undefined) {
          comparison = -1;
        } else if (aVal instanceof Date && bVal instanceof Date) {
          comparison = aVal.getTime() - bVal.getTime();
        } else {
          comparison = aVal < bVal ? -1 : 1;
        }

        return sortConfig.order === 'asc' ? comparison : -comparison;
      });
    }

    return result;
  }, [pianos, filters, sortConfig, includeHidden]);

  // ==========================================
  // REALTIME SUBSCRIPTION
  // ==========================================

  useEffect(() => {
    if (!enableRealtime) return;

    const unsubscribe = subscribeToPianos((event) => {
      console.log('[usePianos] Realtime event:', event.eventType);

      if (event.eventType === 'UPDATE' && event.new) {
        // Merge update dans state
        setPianos((prev) =>
          prev.map((p) =>
            p.gazelleId === event.new!.gazelleId
              ? {
                  ...p,
                  ...keysToCamelCase(event.new as any),
                  updatedAt: new Date()
                }
              : p
          )
        );
      } else if (event.eventType === 'INSERT' && event.new) {
        // Refresh complet si nouveau piano (rare)
        fetchPianos();
      }
    });

    return unsubscribe;
  }, [enableRealtime, fetchPianos]);

  // ==========================================
  // AUTO-FETCH
  // ==========================================

  useEffect(() => {
    if (autoFetch) {
      fetchPianos();
    }
  }, [autoFetch, fetchPianos]);

  // ==========================================
  // RETURN
  // ==========================================

  return {
    pianos,
    loading,
    error,
    filteredPianos,
    filters,
    setFilters,
    sortConfig,
    setSortConfig,
    refreshPianos: fetchPianos,
    updatePiano,
    getPiano,
    lastSync
  };
}

export default usePianos;
