/**
 * Supabase Client with Realtime Support
 *
 * Client TypeScript configuré pour:
 * - Authentification
 * - CRUD operations type-safe
 * - Realtime subscriptions (Mac ↔ iPad sync)
 * - Error handling élégant
 *
 * @example
 * ```ts
 * import { supabase, subscribeToTournees } from '@lib/supabase.client';
 *
 * // Fetch data
 * const { data, error } = await supabase.from('tournees').select('*');
 *
 * // Subscribe to changes
 * const unsubscribe = subscribeToTournees((tournee) => {
 *   console.log('Tournée updated:', tournee);
 * });
 * ```
 */

import { createClient, SupabaseClient, RealtimeChannel } from '@supabase/supabase-js';
import type { Database } from '@types/supabase.types';
import type { Piano, PianoUpdate } from '@types/piano.types';
import type { Tournee } from '@types/tournee.types';

// ==========================================
// CLIENT SETUP
// ==========================================

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL;
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY;

if (!supabaseUrl || !supabaseAnonKey) {
  throw new Error(
    'Missing Supabase env vars. Check VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY in .env'
  );
}

/**
 * Supabase client singleton
 * Type-safe avec Database types auto-generated
 */
export const supabase: SupabaseClient<Database> = createClient(
  supabaseUrl,
  supabaseAnonKey,
  {
    auth: {
      persistSession: true,
      autoRefreshToken: true
    },
    realtime: {
      params: {
        eventsPerSecond: 10 // Throttle pour performance
      }
    }
  }
);

// ==========================================
// REALTIME SUBSCRIPTIONS
// ==========================================

/**
 * Type pour événements Realtime
 */
export type RealtimeEvent<T> = {
  eventType: 'INSERT' | 'UPDATE' | 'DELETE';
  new: T | null;
  old: T | null;
  timestamp: string;
};

/**
 * Callback type pour subscriptions
 */
export type RealtimeCallback<T> = (event: RealtimeEvent<T>) => void;

/**
 * Subscribe aux changements de pianos Vincent d'Indy
 *
 * @param callback - Function appelée à chaque changement
 * @returns Unsubscribe function
 *
 * @example
 * ```ts
 * const unsubscribe = subscribeToPianos((event) => {
 *   if (event.eventType === 'UPDATE') {
 *     updatePianoInState(event.new);
 *   }
 * });
 *
 * // Cleanup
 * unsubscribe();
 * ```
 */
export function subscribeToPianos(
  callback: RealtimeCallback<PianoUpdate>
): () => void {
  const channel: RealtimeChannel = supabase
    .channel('vincent_dindy_piano_updates_changes')
    .on(
      'postgres_changes',
      {
        event: '*',
        schema: 'public',
        table: 'vincent_dindy_piano_updates'
      },
      (payload) => {
        callback({
          eventType: payload.eventType as 'INSERT' | 'UPDATE' | 'DELETE',
          new: payload.new as PianoUpdate | null,
          old: payload.old as PianoUpdate | null,
          timestamp: new Date().toISOString()
        });
      }
    )
    .subscribe();

  // Return cleanup function
  return () => {
    supabase.removeChannel(channel);
  };
}

/**
 * Subscribe aux changements de tournées
 *
 * @param etablissement - Filtrer par établissement
 * @param callback - Function appelée à chaque changement
 * @returns Unsubscribe function
 *
 * @example
 * ```ts
 * const unsubscribe = subscribeToTournees('vincent-dindy', (event) => {
 *   if (event.eventType === 'INSERT') {
 *     addTourneeToState(event.new);
 *   }
 * });
 * ```
 */
export function subscribeToTournees(
  etablissement: string,
  callback: RealtimeCallback<Tournee>
): () => void {
  const channel: RealtimeChannel = supabase
    .channel(`tournees_${etablissement}`)
    .on(
      'postgres_changes',
      {
        event: '*',
        schema: 'public',
        table: 'tournees',
        filter: `etablissement=eq.${etablissement}`
      },
      (payload) => {
        callback({
          eventType: payload.eventType as 'INSERT' | 'UPDATE' | 'DELETE',
          new: payload.new as Tournee | null,
          old: payload.old as Tournee | null,
          timestamp: new Date().toISOString()
        });
      }
    )
    .subscribe();

  return () => {
    supabase.removeChannel(channel);
  };
}

/**
 * Subscribe à une tournée spécifique (pour performance)
 *
 * @param tourneeId - ID de la tournée
 * @param callback - Function appelée aux changements
 */
export function subscribeToTournee(
  tourneeId: string,
  callback: RealtimeCallback<Tournee>
): () => void {
  const channel: RealtimeChannel = supabase
    .channel(`tournee_${tourneeId}`)
    .on(
      'postgres_changes',
      {
        event: '*',
        schema: 'public',
        table: 'tournees',
        filter: `id=eq.${tourneeId}`
      },
      (payload) => {
        callback({
          eventType: payload.eventType as 'INSERT' | 'UPDATE' | 'DELETE',
          new: payload.new as Tournee | null,
          old: payload.old as Tournee | null,
          timestamp: new Date().toISOString()
        });
      }
    )
    .subscribe();

  return () => {
    supabase.removeChannel(channel);
  };
}

// ==========================================
// HELPER FUNCTIONS
// ==========================================

/**
 * Check si connecté à Supabase
 */
export async function isConnected(): Promise<boolean> {
  try {
    const { error } = await supabase.from('tournees').select('id').limit(1);
    return !error;
  } catch {
    return false;
  }
}

/**
 * Get current user email (pour updatedBy)
 */
export async function getCurrentUserEmail(): Promise<string | null> {
  const {
    data: { user }
  } = await supabase.auth.getUser();
  return user?.email || null;
}

/**
 * Format Supabase error pour affichage user-friendly
 */
export function formatSupabaseError(error: unknown): string {
  if (!error) return 'Erreur inconnue';

  if (typeof error === 'object' && error !== null && 'message' in error) {
    const message = (error as { message: string }).message;

    // Traduire erreurs communes
    if (message.includes('duplicate key')) {
      return 'Cet élément existe déjà';
    }
    if (message.includes('foreign key')) {
      return 'Référence invalide';
    }
    if (message.includes('not found')) {
      return 'Élément introuvable';
    }
    if (message.includes('permission')) {
      return 'Permission refusée';
    }

    return message;
  }

  return String(error);
}

/**
 * Retry logic pour requêtes Supabase
 *
 * @example
 * ```ts
 * const data = await withRetry(async () => {
 *   const { data, error } = await supabase.from('tournees').select('*');
 *   if (error) throw error;
 *   return data;
 * });
 * ```
 */
export async function withRetry<T>(
  fn: () => Promise<T>,
  maxRetries = 3,
  delayMs = 1000
): Promise<T> {
  let lastError: unknown;

  for (let i = 0; i < maxRetries; i++) {
    try {
      return await fn();
    } catch (error) {
      lastError = error;
      if (i < maxRetries - 1) {
        await new Promise((resolve) => setTimeout(resolve, delayMs * (i + 1)));
      }
    }
  }

  throw lastError;
}

/**
 * Batch upsert helper (pour piano updates)
 *
 * @example
 * ```ts
 * await batchUpsert('vincent_dindy_piano_updates', updates, 'piano_id');
 * ```
 */
export async function batchUpsert<T extends Record<string, unknown>>(
  table: string,
  records: T[],
  conflictColumn: string
): Promise<{ data: T[] | null; error: unknown }> {
  try {
    const { data, error } = await supabase
      .from(table)
      .upsert(records, {
        onConflict: conflictColumn,
        ignoreDuplicates: false
      })
      .select();

    return { data: data as T[] | null, error };
  } catch (error) {
    return { data: null, error };
  }
}

// ==========================================
// DEBUGGING HELPERS
// ==========================================

/**
 * Enable debug logs pour Realtime
 */
export function enableRealtimeDebug() {
  if (import.meta.env.VITE_ENABLE_DEBUG_LOGS === 'true') {
    supabase.realtime.setAuth(supabaseAnonKey);
    console.log('[Supabase] Realtime debug enabled');
  }
}

/**
 * Log Realtime connection status
 */
export function logRealtimeStatus() {
  const channels = supabase.getChannels();
  console.log(`[Supabase] Active channels: ${channels.length}`);
  channels.forEach((channel) => {
    console.log(`  - ${channel.topic} (${channel.state})`);
  });
}

// Auto-enable debug en dev
if (import.meta.env.DEV) {
  enableRealtimeDebug();
}

// Export default pour usage simple
export default supabase;
