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
      // OPTION 1: Utiliser le proxy Vite (recommandé en dev)
      // OPTION 2: URL complète si proxy ne fonctionne pas (décommenter pour tester)
      // Utiliser le proxy Vite par défaut (recommandé)
      // Si VITE_USE_DIRECT_API=true, utiliser l'URL directe pour debug
      const useDirectUrl = import.meta.env.VITE_USE_DIRECT_API === 'true';
      const apiBaseUrl = useDirectUrl 
        ? 'http://127.0.0.1:8000'  // Utiliser 127.0.0.1 au lieu de localhost
        : '';
      
      // Le proxy Vite enlève /api, donc on utilise /api/... pour que le proxy le transforme en /...
      // Exemple: /api/vincent-dindy/pianos -> proxy -> http://127.0.0.1:8000/vincent-dindy/pianos
      const apiEndpoint = 
        etablissement === 'place-des-arts' 
          ? `${apiBaseUrl}/api/place-des-arts/pianos`
          : `${apiBaseUrl}/api/vincent-dindy/pianos`;
      
      // Déterminer la table Supabase selon l'établissement
      const supabaseTable = 
        etablissement === 'place-des-arts'
          ? 'place_des_arts_piano_updates'  // TODO: Créer cette table ou utiliser vincent_dindy_piano_updates avec filtre
          : 'vincent_dindy_piano_updates';

      console.log('[usePianos] Fetch pianos depuis:', apiEndpoint, '(proxy:', !useDirectUrl, ')');

      // ÉTAPE 1: Fetch pianos depuis Gazelle API (données statiques)
      // PROTECTION: Gestion robuste des erreurs réseau
      let response: Response;
      try {
        response = await fetch(
          `${apiEndpoint}?include_inactive=${includeHidden}`,
          {
            method: 'GET',
            headers: {
              'Content-Type': 'application/json',
            },
            // Timeout implicite via AbortController si nécessaire
          }
        );
      } catch (fetchError: any) {
        // Erreur réseau (CORS, connexion refusée, timeout, etc.)
        console.error('[usePianos] Erreur réseau lors du fetch:', fetchError);
        const errorMessage = fetchError.message || 'Erreur de connexion';
        const detailedError = 
          errorMessage.includes('Failed to fetch') || errorMessage.includes('NetworkError')
            ? `Impossible de se connecter au serveur. Vérifiez que le backend est lancé sur http://localhost:8000`
            : `Erreur réseau: ${errorMessage}`;
        
        setError(detailedError);
        setPianos([]); // Vider la liste en cas d'erreur
        setLoading(false);
        return; // Sortir de la fonction
      }

      if (!response.ok) {
        const errorText = await response.text().catch(() => 'Erreur inconnue');
        console.error('[usePianos] Erreur HTTP:', response.status, errorText);
        throw new Error(`HTTP ${response.status}: ${response.statusText}. ${errorText}`);
      }

      let data: any;
      try {
        data = await response.json();
      } catch (jsonError: any) {
        console.error('[usePianos] Erreur parsing JSON:', jsonError);
        throw new Error(`Réponse invalide du serveur: ${jsonError.message}`);
      }

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
          // Support both piano_id (new) and gazelle_id (old) for compatibility
          const pianoId = overlay.piano_id || overlay.gazelle_id;
          if (pianoId) {
            overlayMap.set(pianoId, overlay);
          }
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
      console.log('[usePianos] Fetch réussi:', transformedPianos.length, 'pianos chargés');
    } catch (err) {
      console.error('[usePianos] Fetch error:', err);
      const errorMessage = err instanceof Error 
        ? err.message 
        : typeof err === 'string' 
          ? err 
          : 'Erreur inconnue lors du chargement des pianos';
      
      // Message d'erreur plus détaillé pour l'utilisateur
      const userFriendlyMessage = errorMessage.includes('Failed to fetch') || errorMessage.includes('connexion')
        ? `❌ Impossible de se connecter au serveur backend.\n\nVérifiez que le serveur Python est lancé sur http://localhost:8000\n\nErreur technique: ${errorMessage}`
        : errorMessage;
      
      setError(userFriendlyMessage);
      setPianos([]);  // Vider la liste en cas d'erreur pour éviter d'afficher d'anciennes données
    } finally {
      setLoading(false);
    }
  }, [etablissement, includeHidden]);

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
        // Filtrer les champs qui ne doivent pas être envoyés à Supabase
        const { pianoId: _, updatedBy, ...fieldsToUpdate } = updates;
        
        // Convert to snake_case pour API Python
        const snakeCaseUpdates = keysToSnakeCase(fieldsToUpdate);

        // Déterminer la table selon l'établissement
        const supabaseTable = 
          etablissement === 'place-des-arts'
            ? 'place_des_arts_piano_updates'  // TODO: Créer cette table
            : 'vincent_dindy_piano_updates';
        
        // Préparer les données pour Supabase
        const supabaseData: Record<string, any> = {
          piano_id: pianoId,
          updated_at: new Date().toISOString()
        };

        // Ajouter updated_by si fourni
        if (updatedBy) {
          supabaseData.updated_by = updatedBy;
        }

        // Ajouter tous les autres champs convertis en snake_case
        Object.assign(supabaseData, snakeCaseUpdates);
        
        const { error: updateError } = await supabase
          .from('vincent_dindy_piano_updates')  // TODO: Utiliser supabaseTable quand créée
          .upsert(supabaseData, { onConflict: 'piano_id' });

        if (updateError) {
          throw updateError;
        }
      } catch (err) {
        console.error('[usePianos] Update error:', err);
        // Rollback optimistic update - mais ne pas re-lancer fetchPianos si ça échoue
        // pour éviter les boucles infinies
        try {
          await fetchPianos();
        } catch (fetchErr) {
          console.error('[usePianos] Rollback fetch also failed:', fetchErr);
          // Ne pas propager l'erreur de fetch pour éviter double erreur
        }
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
