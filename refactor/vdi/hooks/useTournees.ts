/**
 * useTournees Hook - Tournée Management with Realtime Sync
 *
 * Hook pour gestion complète des tournées:
 * - CRUD operations (Create, Read, Update, Delete)
 * - Realtime subscriptions multi-devices
 * - Activation/désactivation avec reset automatique pianos Vert
 * - Stats et progression
 *
 * @example
 * ```tsx
 * function TourneesManager() {
 *   const {
 *     tournees,
 *     activeTournee,
 *     createTournee,
 *     activateTournee,
 *     addPianoToTournee
 *   } = useTournees('vincent-dindy');
 *
 *   return <div>...</div>;
 * }
 * ```
 */

import { useState, useEffect, useCallback, useMemo } from 'react';
import { supabase, subscribeToTournees } from '@lib/supabase.client';
import { formatSupabaseError, getCurrentUserEmail } from '@lib/supabase.client';
import { generateTourneeId, parseDate } from '@lib/utils';
import type {
  Tournee,
  TourneeCreate,
  TourneeUpdate,
  TourneeStatus,
  TourneeStats,
  Etablissement
} from '@types/tournee.types';

// ==========================================
// TYPES
// ==========================================

interface UseTourneesOptions {
  /** Auto-fetch au mount */
  autoFetch?: boolean;

  /** Enable Realtime subscriptions */
  enableRealtime?: boolean;

  /** Charger seulement tournées actives */
  onlyActive?: boolean;

  /** Filtrer par technicien (email) */
  technicianEmail?: string;
}

interface UseTourneesReturn {
  /** Toutes les tournées */
  tournees: Tournee[];

  /** Tournée actuellement active (une seule max) */
  activeTournee: Tournee | null;

  /** Loading state */
  loading: boolean;

  /** Error state */
  error: string | null;

  /** Créer nouvelle tournée */
  createTournee: (data: TourneeCreate) => Promise<Tournee>;

  /** Modifier tournée */
  updateTournee: (id: string, updates: Partial<TourneeUpdate>) => Promise<void>;

  /** Supprimer tournée */
  deleteTournee: (id: string) => Promise<void>;

  /** Activer tournée (désactive les autres) */
  activateTournee: (id: string) => Promise<void>;

  /** Marquer tournée comme terminée */
  completeTournee: (id: string) => Promise<void>;

  /** Réanimer tournée archivée (→ planifiee) */
  reanimateTournee: (id: string) => Promise<void>;

  /** Ajouter piano à tournée */
  addPianoToTournee: (tourneeId: string, pianoId: string) => Promise<void>;

  /** Retirer piano de tournée */
  removePianoFromTournee: (tourneeId: string, pianoId: string) => Promise<void>;

  /** Batch: Marquer pianos comme "Top" dans une tournée */
  batchMarkAsTopInTournee: (tourneeId: string, pianoIds: string[]) => Promise<void>;

  /** Check si piano dans tournée */
  isPianoInTournee: (pianoId: string, tourneeId: string) => boolean;

  /** Get stats d'une tournée */
  getTourneeStats: (tourneeId: string) => TourneeStats | null;

  /** Refresh tournées */
  refreshTournees: () => Promise<void>;

  /** Dernière sync */
  lastSync: Date | null;
}

// ==========================================
// HOOK
// ==========================================

export function useTournees(
  etablissement: Etablissement,
  options: UseTourneesOptions = {}
): UseTourneesReturn {
  const {
    autoFetch = true,
    enableRealtime = true,
    onlyActive = false,
    technicianEmail
  } = options;

  // State
  const [tournees, setTournees] = useState<Tournee[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [lastSync, setLastSync] = useState<Date | null>(null);

  // ==========================================
  // FETCH TOURNEES
  // ==========================================

  const fetchTournees = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      let query = supabase
        .from('tournees')
        .select('*')
        .eq('etablissement', etablissement)
        .order('date_debut', { ascending: false });

      if (onlyActive) {
        query = query.eq('status', 'en_cours');
      }

      // Filtrer par technicien si spécifié
      if (technicianEmail) {
        query = query.eq('technicien_responsable', technicianEmail);
      }

      const { data, error: fetchError } = await query;

      if (fetchError) throw fetchError;

      // Pour chaque tournée, fetch les pianos depuis tournee_pianos table
      const tourneesWithPianos = await Promise.all(
        (data || []).map(async (row) => {
          // Fetch piano IDs depuis table de jonction
          const { data: pianoRelations, error: pianoError } = await supabase
            .from('tournee_pianos')
            .select('gazelle_id, ordre, is_top')
            .eq('tournee_id', row.id)
            .order('ordre', { ascending: true, nullsFirst: false })
            .order('ajoute_le', { ascending: true });

          if (pianoError) {
            console.warn(`[useTournees] Error fetching pianos for ${row.id}:`, pianoError);
          }

          const pianoIds = (pianoRelations || []).map((rel) => rel.gazelle_id);
          const topPianoIds = new Set(
            (pianoRelations || [])
              .filter((rel) => rel.is_top === true)
              .map((rel) => rel.gazelle_id)
          );

          console.log(`[useTournees] Tournée ${row.id} (${row.nom}): ${pianoIds.length} pianos (${topPianoIds.size} top)`, pianoIds);

          return {
            id: row.id,
            nom: row.nom,
            dateDebut: parseDate(row.date_debut)!,
            dateFin: parseDate(row.date_fin)!,
            status: row.status as TourneeStatus,
            etablissement: row.etablissement as Etablissement,
            technicienResponsable: row.technicien_responsable,
            techniciensAssistants: row.techniciens_assistants || [],
            pianoIds,
            topPianoIds,
            notes: row.notes,
            createdAt: parseDate(row.created_at)!,
            updatedAt: parseDate(row.updated_at)!,
            createdBy: row.created_by
          } as Tournee;
        })
      );

      setTournees(tourneesWithPianos);
      setLastSync(new Date());
    } catch (err) {
      console.error('[useTournees] Fetch error:', err);
      setError(formatSupabaseError(err));
    } finally {
      setLoading(false);
    }
  }, [etablissement, onlyActive, technicianEmail]);

  // ==========================================
  // CREATE TOURNEE
  // ==========================================

  const createTournee = useCallback(
    async (data: TourneeCreate): Promise<Tournee> => {
      const userEmail = (await getCurrentUserEmail()) || 'unknown@system.com';

      const newTournee = {
        id: generateTourneeId(),
        nom: data.nom,
        date_debut: data.dateDebut.toISOString().split('T')[0],
        date_fin: data.dateFin.toISOString().split('T')[0],
        status: 'planifiee' as TourneeStatus,
        etablissement: data.etablissement,
        technicien_responsable: data.technicienResponsable,
        techniciens_assistants: data.techniciensAssistants || [],
        piano_ids: data.pianoIds || [], // jsonb type, pas besoin de JSON.stringify
        notes: data.notes || null,
        created_by: userEmail
      };

      const { data: inserted, error: insertError } = await supabase
        .from('tournees')
        .insert(newTournee)
        .select()
        .single();

      if (insertError) throw new Error(formatSupabaseError(insertError));

      // Transform et ajouter à state
      const tournee: Tournee = {
        id: inserted.id,
        nom: inserted.nom,
        dateDebut: parseDate(inserted.date_debut)!,
        dateFin: parseDate(inserted.date_fin)!,
        status: inserted.status as TourneeStatus,
        etablissement: inserted.etablissement as Etablissement,
        technicienResponsable: inserted.technicien_responsable,
        techniciensAssistants: inserted.techniciens_assistants || [],
        pianoIds: (inserted.piano_ids as string[]) || [],
        notes: inserted.notes,
        createdAt: parseDate(inserted.created_at)!,
        updatedAt: parseDate(inserted.updated_at)!,
        createdBy: inserted.created_by
      };

      setTournees((prev) => [tournee, ...prev]);

      return tournee;
    },
    []
  );

  // ==========================================
  // UPDATE TOURNEE
  // ==========================================

  const updateTournee = useCallback(
    async (id: string, updates: Partial<TourneeUpdate>) => {
      // Optimistic update
      setTournees((prev) =>
        prev.map((t) =>
          t.id === id
            ? {
                ...t,
                ...updates,
                updatedAt: new Date()
              }
            : t
        )
      );

      try {
        const dbUpdates: any = {};

        if (updates.nom) dbUpdates.nom = updates.nom;
        if (updates.dateDebut)
          dbUpdates.date_debut = updates.dateDebut.toISOString().split('T')[0];
        if (updates.dateFin) dbUpdates.date_fin = updates.dateFin.toISOString().split('T')[0];
        if (updates.status) dbUpdates.status = updates.status;
        if (updates.technicienResponsable)
          dbUpdates.technicien_responsable = updates.technicienResponsable;
        if (updates.techniciensAssistants !== undefined)
          dbUpdates.techniciens_assistants = updates.techniciensAssistants;
        if (updates.notes !== undefined) dbUpdates.notes = updates.notes;
        if (updates.pianoIds) dbUpdates.piano_ids = JSON.stringify(updates.pianoIds);

        const { error: updateError } = await supabase
          .from('tournees')
          .update(dbUpdates)
          .eq('id', id);

        if (updateError) throw updateError;
      } catch (err) {
        console.error('[useTournees] Update error:', err);
        // Rollback
        await fetchTournees();
        throw new Error(formatSupabaseError(err));
      }
    },
    [fetchTournees]
  );

  // ==========================================
  // DELETE TOURNEE
  // ==========================================

  const deleteTournee = useCallback(async (id: string) => {
    // Optimistic delete
    setTournees((prev) => prev.filter((t) => t.id !== id));

    try {
      const { error: deleteError } = await supabase.from('tournees').delete().eq('id', id);

      if (deleteError) throw deleteError;
    } catch (err) {
      console.error('[useTournees] Delete error:', err);
      // Rollback
      await fetchTournees();
      throw new Error(formatSupabaseError(err));
    }
  }, [fetchTournees]);

  // ==========================================
  // ACTIVATE TOURNEE
  // ==========================================

  const activateTournee = useCallback(
    async (id: string) => {
      try {
        // Utilise la fonction SQL activate_tournee
        // qui désactive automatiquement les autres tournées
        // et reset leurs pianos Vert via trigger
        const { data, error: activateError } = await supabase.rpc('activate_tournee', {
          p_tournee_id: id
        });

        if (activateError) throw activateError;

        // Refresh pour obtenir état à jour
        await fetchTournees();
      } catch (err) {
        console.error('[useTournees] Activate error:', err);
        throw new Error(formatSupabaseError(err));
      }
    },
    [fetchTournees]
  );

  // ==========================================
  // COMPLETE TOURNEE
  // ==========================================

  const completeTournee = useCallback(
    async (id: string) => {
      await updateTournee(id, { status: 'terminee' as TourneeStatus });
    },
    [updateTournee]
  );

  // ==========================================
  // REANIMATE TOURNEE
  // ==========================================

  const reanimateTournee = useCallback(
    async (id: string) => {
      await updateTournee(id, { status: 'planifiee' as TourneeStatus });
    },
    [updateTournee]
  );

  // ==========================================
  // PIANO OPERATIONS
  // ==========================================

  const addPianoToTournee = useCallback(
    async (tourneeId: string, pianoId: string) => {
      const tournee = tournees.find((t) => t.id === tourneeId);
      if (!tournee) throw new Error('Tournée introuvable');

      const userEmail = (await getCurrentUserEmail()) || 'unknown@system.com';

      // Insérer dans table de jonction
      const { error: insertError } = await supabase
        .from('tournee_pianos')
        .insert({
          tournee_id: tourneeId,
          gazelle_id: pianoId,
          ajoute_par: userEmail
        });

      if (insertError) {
        // Si déjà présent (constraint violation), ignorer
        if (insertError.code !== '23505') {
          throw insertError;
        }
      }

      // Optimistic update
      setTournees((prev) =>
        prev.map((t) =>
          t.id === tourneeId
            ? { ...t, pianoIds: [...new Set([...t.pianoIds, pianoId])] }
            : t
        )
      );

      // Refresh pour avoir l'ordre correct
      await fetchTournees();
    },
    [tournees, fetchTournees]
  );

  const removePianoFromTournee = useCallback(
    async (tourneeId: string, pianoId: string) => {
      const tournee = tournees.find((t) => t.id === tourneeId);
      if (!tournee) throw new Error('Tournée introuvable');

      // Supprimer de la table de jonction
      const { error: deleteError } = await supabase
        .from('tournee_pianos')
        .delete()
        .eq('tournee_id', tourneeId)
        .eq('gazelle_id', pianoId);

      if (deleteError) throw deleteError;

      // Optimistic update
      setTournees((prev) =>
        prev.map((t) =>
          t.id === tourneeId
            ? { ...t, pianoIds: t.pianoIds.filter((id) => id !== pianoId) }
            : t
        )
      );

      // Refresh pour confirmer
      await fetchTournees();
    },
    [tournees, fetchTournees]
  );

  /**
   * Batch remove multiple pianos from tournee (FAST)
   */
  const batchRemovePianosFromTournee = useCallback(
    async (tourneeId: string, pianoIds: string[]) => {
      const tournee = tournees.find((t) => t.id === tourneeId);
      if (!tournee) throw new Error('Tournée introuvable');

      // DELETE batch avec .in() - UNE SEULE requête SQL
      const { error: deleteError } = await supabase
        .from('tournee_pianos')
        .delete()
        .eq('tournee_id', tourneeId)
        .in('gazelle_id', pianoIds);

      if (deleteError) throw deleteError;

      // Optimistic update
      setTournees((prev) =>
        prev.map((t) =>
          t.id === tourneeId
            ? { ...t, pianoIds: t.pianoIds.filter((id) => !pianoIds.includes(id)) }
            : t
        )
      );

      // Refresh pour confirmer
      await fetchTournees();
    },
    [tournees, fetchTournees]
  );

  const batchMarkAsTopInTournee = useCallback(
    async (tourneeId: string, pianoIds: string[]): Promise<number> => {
      console.log('[useTournees] batchMarkAsTopInTournee called');
      console.log('  - tourneeId:', tourneeId);
      console.log('  - pianoIds:', pianoIds);

      const userEmail = (await getCurrentUserEmail()) || 'system@gazelle.com';

      // UPSERT pianos dans tournée avec is_top=true
      // Si piano déjà dans tournée → met à jour is_top
      // Si piano pas dans tournée → ajoute avec is_top=true
      const insertions = pianoIds.map((pianoId, index) => ({
        tournee_id: tourneeId,
        gazelle_id: pianoId,
        is_top: true,
        ajoute_par: userEmail,
        ordre: index + 1  // Ordre séquentiel
      }));

      const { data, error: upsertError } = await supabase
        .from('tournee_pianos')
        .upsert(insertions, {
          onConflict: 'tournee_id,gazelle_id',  // Clé unique composite
          ignoreDuplicates: false  // IMPORTANT: update si existe déjà
        })
        .select();

      console.log('[useTournees] Upsert result:', { data, error: upsertError, count: data?.length || 0 });

      if (upsertError) throw upsertError;

      const updatedCount = data?.length || 0;

      // Refresh pour mettre à jour topPianoIds
      console.log('[useTournees] Refreshing tournées...');
      await fetchTournees();
      console.log('[useTournees] Refresh complete');

      return updatedCount;
    },
    [fetchTournees]
  );

  const isPianoInTournee = useCallback(
    (pianoId: string, tourneeId: string): boolean => {
      const tournee = tournees.find((t) => t.id === tourneeId);
      return tournee ? tournee.pianoIds.includes(pianoId) : false;
    },
    [tournees]
  );

  // ==========================================
  // STATS
  // ==========================================

  const getTourneeStats = useCallback(
    (tourneeId: string): TourneeStats | null => {
      const tournee = tournees.find((t) => t.id === tourneeId);
      if (!tournee) return null;

      // Note: Ces stats nécessitent données pianos
      // Pour l'instant, stats basiques
      return {
        tourneeId,
        totalPianos: tournee.pianoIds.length,
        completed: 0, // À implémenter avec usePianos
        proposed: 0,
        top: 0,
        progressPercent: 0,
        estimatedDaysRemaining: null
      };
    },
    [tournees]
  );

  // ==========================================
  // COMPUTED: ACTIVE TOURNEE
  // ==========================================

  const activeTournee = useMemo(() => {
    return tournees.find((t) => t.status === 'en_cours') || null;
  }, [tournees]);

  // ==========================================
  // REALTIME SUBSCRIPTION
  // ==========================================

  useEffect(() => {
    if (!enableRealtime) return;

    const unsubscribe = subscribeToTournees(etablissement, (event) => {
      console.log('[useTournees] Realtime event:', event.eventType);

      if (event.eventType === 'INSERT' && event.new) {
        const newTournee: Tournee = {
          id: event.new.id,
          nom: event.new.nom,
          dateDebut: parseDate(event.new.date_debut as unknown as string)!,
          dateFin: parseDate(event.new.date_fin as unknown as string)!,
          status: event.new.status as TourneeStatus,
          etablissement: event.new.etablissement as Etablissement,
          technicienResponsable: event.new.technicien_responsable,
          pianoIds: (event.new.piano_ids as string[]) || [],
          notes: event.new.notes,
          createdAt: parseDate(event.new.created_at as unknown as string)!,
          updatedAt: parseDate(event.new.updated_at as unknown as string)!,
          createdBy: event.new.created_by
        };

        setTournees((prev) => [newTournee, ...prev]);
      } else if (event.eventType === 'UPDATE' && event.new) {
        setTournees((prev) =>
          prev.map((t) =>
            t.id === event.new!.id
              ? {
                  ...t,
                  nom: event.new!.nom,
                  status: event.new!.status as TourneeStatus,
                  pianoIds: (event.new!.piano_ids as string[]) || [],
                  updatedAt: new Date()
                }
              : t
          )
        );
      } else if (event.eventType === 'DELETE' && event.old) {
        setTournees((prev) => prev.filter((t) => t.id !== event.old!.id));
      }
    });

    return unsubscribe;
  }, [etablissement, enableRealtime]);

  // ==========================================
  // AUTO-FETCH
  // ==========================================

  useEffect(() => {
    if (autoFetch) {
      fetchTournees();
    }
  }, [autoFetch, fetchTournees]);

  // ==========================================
  // RETURN
  // ==========================================

  return {
    tournees,
    activeTournee,
    loading,
    error,
    createTournee,
    updateTournee,
    deleteTournee,
    activateTournee,
    completeTournee,
    reanimateTournee,
    addPianoToTournee,
    removePianoFromTournee,
    batchRemovePianosFromTournee,
    batchMarkAsTopInTournee,
    isPianoInTournee,
    getTourneeStats,
    refreshTournees: fetchTournees,
    lastSync
  };
}

export default useTournees;
