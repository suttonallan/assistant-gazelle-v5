/**
 * Hook pour gérer les mappings Place des Arts ↔ Pianos Gazelle
 */

import { useState, useEffect, useCallback } from 'react';
import { supabase } from '@lib/supabase.client';
import type { PDAPianoMapping, PianoMappingStats } from '@types/pda.types';

interface UsePDAPianoMappingsReturn {
  mappings: PDAPianoMapping[];
  loading: boolean;
  error: string | null;
  stats: PianoMappingStats[];
  createMapping: (abbreviation: string, gazellePianoId: string, location?: string, isUncertain?: boolean, uncertaintyNote?: string) => Promise<void>;
  updateMapping: (id: string, gazellePianoId?: string, isUncertain?: boolean, uncertaintyNote?: string) => Promise<void>;
  markUncertain: (id: string, note: string) => Promise<void>;
  markCertain: (id: string) => Promise<void>;
  deleteMapping: (id: string) => Promise<void>;
  refresh: () => Promise<void>;
}

/**
 * Récupère les abréviations uniques depuis les demandes Place des Arts
 */
async function getUniqueAbbreviations(): Promise<string[]> {
  try {
    const { data, error } = await supabase
      .from('place_des_arts_requests')
      .select('piano')
      .not('piano', 'is', null);

    if (error) throw error;

    // Extraire les abréviations uniques
    const abbreviations = new Set<string>();
    data?.forEach((row) => {
      if (row.piano && typeof row.piano === 'string') {
        abbreviations.add(row.piano.trim());
      }
    });

    return Array.from(abbreviations).sort();
  } catch (err) {
    console.error('[usePDAPianoMappings] Error fetching abbreviations:', err);
    return [];
  }
}

/**
 * Récupère les statistiques de mapping (abréviations + nombre de demandes)
 */
async function getMappingStats(
  mappings: PDAPianoMapping[]
): Promise<PianoMappingStats[]> {
  try {
    // Récupérer toutes les abréviations uniques
    const abbreviations = await getUniqueAbbreviations();

    // Créer un map pour lookup rapide
    const mappingMap = new Map<string, PDAPianoMapping>();
    mappings.forEach((m) => {
      mappingMap.set(m.piano_abbreviation, m);
    });

    // Compter les demandes par abréviation
    const statsPromises = abbreviations.map(async (abbr) => {
      const { data, error } = await supabase
        .from('place_des_arts_requests')
        .select('id, appointment_date')
        .eq('piano', abbr);

      if (error) throw error;

      const requestCount = data?.length || 0;
      const lastRequest = data
        ?.map((r) => r.appointment_date)
        .sort()
        .reverse()[0];

      const mapping = mappingMap.get(abbr);

      return {
        abbreviation: abbr,
        gazelle_piano_id: mapping?.gazelle_piano_id,
        request_count: requestCount,
        last_request_date: lastRequest,
        mapped: !!mapping
      };
    });

    return Promise.all(statsPromises);
  } catch (err) {
    console.error('[usePDAPianoMappings] Error fetching stats:', err);
    return [];
  }
}

export function usePDAPianoMappings(): UsePDAPianoMappingsReturn {
  const [mappings, setMappings] = useState<PDAPianoMapping[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [stats, setStats] = useState<PianoMappingStats[]>([]);

  const fetchMappings = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      const { data, error: fetchError } = await supabase
        .from('pda_piano_mappings')
        .select('*')
        .order('piano_abbreviation', { ascending: true });

      if (fetchError) throw fetchError;

      const formattedMappings: PDAPianoMapping[] = (data || []).map((m) => ({
        ...m,
        created_at: new Date(m.created_at),
        updated_at: new Date(m.updated_at)
      }));

      setMappings(formattedMappings);

      // Récupérer les stats
      const mappingStats = await getMappingStats(formattedMappings);
      setStats(mappingStats);
    } catch (err) {
      console.error('[usePDAPianoMappings] Error:', err);
      setError(err instanceof Error ? err.message : 'Erreur inconnue');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchMappings();
  }, [fetchMappings]);

  const createMapping = useCallback(
    async (abbreviation: string, gazellePianoId: string, location?: string, isUncertain?: boolean, uncertaintyNote?: string) => {
      try {
        const { error: insertError } = await supabase
          .from('pda_piano_mappings')
          .insert({
            piano_abbreviation: abbreviation,
            gazelle_piano_id: gazellePianoId,
            location: location || null,
            is_uncertain: isUncertain || false,
            uncertainty_note: uncertaintyNote || null
          });

        if (insertError) throw insertError;

        await fetchMappings();
      } catch (err) {
        console.error('[usePDAPianoMappings] Error creating mapping:', err);
        throw err;
      }
    },
    [fetchMappings]
  );

  const updateMapping = useCallback(
    async (id: string, gazellePianoId?: string, isUncertain?: boolean, uncertaintyNote?: string) => {
      try {
        const updateData: any = {};
        if (gazellePianoId !== undefined) updateData.gazelle_piano_id = gazellePianoId;
        if (isUncertain !== undefined) updateData.is_uncertain = isUncertain;
        if (uncertaintyNote !== undefined) updateData.uncertainty_note = uncertaintyNote;

        const { error: updateError } = await supabase
          .from('pda_piano_mappings')
          .update(updateData)
          .eq('id', id);

        if (updateError) throw updateError;

        await fetchMappings();
      } catch (err) {
        console.error('[usePDAPianoMappings] Error updating mapping:', err);
        throw err;
      }
    },
    [fetchMappings]
  );

  const markUncertain = useCallback(
    async (id: string, note: string) => {
      await updateMapping(id, undefined, true, note);
    },
    [updateMapping]
  );

  const markCertain = useCallback(
    async (id: string) => {
      await updateMapping(id, undefined, false, null);
    },
    [updateMapping]
  );

  const deleteMapping = useCallback(
    async (id: string) => {
      try {
        const { error: deleteError } = await supabase
          .from('pda_piano_mappings')
          .delete()
          .eq('id', id);

        if (deleteError) throw deleteError;

        await fetchMappings();
      } catch (err) {
        console.error('[usePDAPianoMappings] Error deleting mapping:', err);
        throw err;
      }
    },
    [fetchMappings]
  );

  return {
    mappings,
    loading,
    error,
    stats,
    createMapping,
    updateMapping,
    markUncertain,
    markCertain,
    deleteMapping,
    refresh: fetchMappings
  };
}

export default usePDAPianoMappings;

