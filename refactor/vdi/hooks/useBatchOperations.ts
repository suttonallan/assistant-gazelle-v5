/**
 * useBatchOperations Hook - Bulk Piano Updates
 *
 * Gestion des opérations groupées avec:
 * - Updates optimistes
 * - Batch API calls
 * - Error handling et rollback
 * - Progress tracking
 *
 * @example
 * ```tsx
 * function BatchToolbar({ selectedIds }) {
 *   const { batchUpdateStatus, batchUpdateUsage, loading } = useBatchOperations();
 *
 *   return (
 *     <button
 *       onClick={() => batchUpdateStatus(selectedIds, 'top')}
 *       disabled={loading}
 *     >
 *       Marquer comme Top
 *     </button>
 *   );
 * }
 * ```
 */

import { useState, useCallback } from 'react';
import { supabase, getCurrentUserEmail } from '@lib/supabase.client';
import { formatSupabaseError } from '@lib/supabase.client';
import { keysToSnakeCase } from '@lib/utils';
import type { PianoStatus, PianoUsage, PianoUpdate } from '@types/piano.types';

// ==========================================
// TYPES
// ==========================================

interface BatchOperationOptions {
  /** Callback succès */
  onSuccess?: (count: number) => void;

  /** Callback erreur */
  onError?: (error: string) => void;

  /** Callback progression */
  onProgress?: (current: number, total: number) => void;

  /** Update optimiste (UI avant API) */
  optimistic?: boolean;
}

interface UseBatchOperationsReturn {
  /** Loading state */
  loading: boolean;

  /** Error state */
  error: string | null;

  /** Progression (0-100) */
  progress: number;

  /** Batch update status */
  batchUpdateStatus: (
    pianoIds: Set<string> | string[],
    status: PianoStatus,
    options?: BatchOperationOptions
  ) => Promise<void>;

  /** Batch update usage */
  batchUpdateUsage: (
    pianoIds: Set<string> | string[],
    usage: PianoUsage,
    options?: BatchOperationOptions
  ) => Promise<void>;

  /** Batch update custom fields */
  batchUpdate: (
    updates: PianoUpdate[],
    options?: BatchOperationOptions
  ) => Promise<void>;

  /** Batch add to tournée */
  batchAddToTournee: (
    pianoIds: Set<string> | string[],
    tourneeId: string,
    options?: BatchOperationOptions
  ) => Promise<void>;

  /** Batch set visibility (hide/show pianos) */
  batchSetVisibility: (
    pianoIds: Set<string> | string[],
    isHidden: boolean,
    options?: BatchOperationOptions
  ) => Promise<void>;

  /** Reset state */
  reset: () => void;
}

// ==========================================
// HOOK
// ==========================================

export function useBatchOperations(): UseBatchOperationsReturn {
  // State
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [progress, setProgress] = useState<number>(0);

  // ==========================================
  // HELPERS
  // ==========================================

  /**
   * Convert Set|Array → Array
   */
  const toArray = (ids: Set<string> | string[]): string[] => {
    return Array.isArray(ids) ? ids : Array.from(ids);
  };

  /**
   * Execute batch avec progress tracking
   */
  const executeBatch = useCallback(
    async (
      updates: PianoUpdate[],
      options: BatchOperationOptions = {}
    ) => {
      const { onSuccess, onError, onProgress, optimistic = false } = options;

      setLoading(true);
      setError(null);
      setProgress(0);

      try {
        const userEmail = (await getCurrentUserEmail()) || 'system@gazelle.com';

        // Enrichir updates avec updatedBy
        const enrichedUpdates = updates.map((u) => ({
          ...u,
          updatedBy: userEmail
        }));

        // Convert camelCase → snake_case pour Supabase
        const dbUpdates = enrichedUpdates.map((u) => {
          const snakeCase = keysToSnakeCase(u) as any;
          // Renommer pianoId → gazelle_id (obligatoire)
          snakeCase.gazelle_id = u.pianoId;
          delete snakeCase.piano_id;  // Supprimer piano_id si créé par keysToSnakeCase

          return snakeCase;
        });

        // Progress: 0 → 50% (preparation)
        setProgress(50);
        if (onProgress) onProgress(1, 2);

        // Batch upsert vers Supabase
        const { data, error: upsertError } = await supabase
          .from('vincent_dindy_piano_updates')
          .upsert(dbUpdates, {
            onConflict: 'gazelle_id',
            ignoreDuplicates: false
          })
          .select();

        if (upsertError) throw upsertError;

        // Progress: 100%
        setProgress(100);
        if (onProgress) onProgress(2, 2);

        // Success callback
        if (onSuccess) {
          onSuccess(enrichedUpdates.length);
        }

        // Reset progress après 500ms
        setTimeout(() => setProgress(0), 500);
      } catch (err) {
        console.error('[useBatchOperations] Error:', err);
        const errorMsg = formatSupabaseError(err);
        setError(errorMsg);

        if (onError) {
          onError(errorMsg);
        }

        setProgress(0);
        throw err;
      } finally {
        setLoading(false);
      }
    },
    []
  );

  // ==========================================
  // BATCH OPERATIONS
  // ==========================================

  /**
   * Batch update status
   */
  const batchUpdateStatus = useCallback(
    async (
      pianoIds: Set<string> | string[],
      status: PianoStatus,
      options?: BatchOperationOptions
    ) => {
      const ids = toArray(pianoIds);

      const updates: PianoUpdate[] = ids.map((pianoId) => ({
        pianoId,
        status,
        updatedBy: '' // Sera enrichi dans executeBatch
      }));

      await executeBatch(updates, options);
    },
    [executeBatch]
  );

  /**
   * Batch update usage
   */
  const batchUpdateUsage = useCallback(
    async (
      pianoIds: Set<string> | string[],
      usage: PianoUsage,
      options?: BatchOperationOptions
    ) => {
      const ids = toArray(pianoIds);

      const updates: PianoUpdate[] = ids.map((pianoId) => ({
        pianoId,
        usage,
        updatedBy: ''
      }));

      await executeBatch(updates, options);
    },
    [executeBatch]
  );

  /**
   * Batch update custom (flexible)
   */
  const batchUpdate = useCallback(
    async (updates: PianoUpdate[], options?: BatchOperationOptions) => {
      await executeBatch(updates, options);
    },
    [executeBatch]
  );

  /**
   * Batch add to tournée
   * Note: Utilise la table de jonction tournee_pianos
   */
  const batchAddToTournee = useCallback(
    async (
      pianoIds: Set<string> | string[],
      tourneeId: string,
      options?: BatchOperationOptions
    ) => {
      const { onSuccess, onError } = options || {};

      setLoading(true);
      setError(null);

      try {
        const ids = toArray(pianoIds);
        const userEmail = (await getCurrentUserEmail()) || 'unknown@system.com';

        // Batch insert dans table de jonction
        const insertions = ids.map((pianoId, index) => ({
          tournee_id: tourneeId,
          gazelle_id: pianoId,
          ajoute_par: userEmail,
          ordre: index + 1  // Ordre séquentiel
        }));

        const { error: insertError } = await supabase
          .from('tournee_pianos')
          .upsert(insertions, {
            onConflict: 'tournee_id,gazelle_id',  // Ignorer doublons
            ignoreDuplicates: true
          });

        if (insertError) throw insertError;

        if (onSuccess) onSuccess(ids.length);
      } catch (err) {
        console.error('[useBatchOperations] Add to tournée error:', err);
        const errorMsg = formatSupabaseError(err);
        setError(errorMsg);

        if (onError) onError(errorMsg);
        throw err;
      } finally {
        setLoading(false);
      }
    },
    []
  );

  /**
   * Batch set visibility (hide/show pianos)
   */
  const batchSetVisibility = useCallback(
    async (
      pianoIds: Set<string> | string[],
      isHidden: boolean,
      options?: BatchOperationOptions
    ) => {
      const ids = toArray(pianoIds);

      const updates: PianoUpdate[] = ids.map((pianoId) => ({
        pianoId,
        isHidden,
        updatedBy: '' // Sera enrichi dans executeBatch
      }));

      await executeBatch(updates, options);
    },
    [executeBatch]
  );

  /**
   * Reset state
   */
  const reset = useCallback(() => {
    setLoading(false);
    setError(null);
    setProgress(0);
  }, []);

  // ==========================================
  // RETURN
  // ==========================================

  return {
    loading,
    error,
    progress,
    batchUpdateStatus,
    batchUpdateUsage,
    batchUpdate,
    batchAddToTournee,
    batchSetVisibility,
    reset
  };
}

export default useBatchOperations;
