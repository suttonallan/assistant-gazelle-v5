/**
 * useViewContext Hook - User Impersonation pour Admin
 *
 * Permet à l'admin de simuler la vue d'un autre rôle (assistant/technicien)
 * SANS changer les permissions réelles ni les données chargées.
 *
 * SÉCURITÉ CRITIQUE:
 * - activeViewRole affecte SEULEMENT l'UI (conditional rendering)
 * - Les requêtes Supabase utilisent TOUJOURS le realRole
 *
 * @example
 * ```tsx
 * function MyComponent() {
 *   const { activeViewRole, isImpersonating } = useViewContext();
 *   const { user } = useAuth(); // Vrai rôle pour requêtes
 *
 *   // UI basée sur activeViewRole
 *   return (
 *     <>
 *       {activeViewRole === 'admin' && <AdminPanel />}
 *       {['admin', 'technicien'].includes(activeViewRole) && <TourneeView />}
 *     </>
 *   );
 * }
 * ```
 */

import { useState, useCallback, useMemo, useEffect } from 'react';
import { getCurrentUserEmail } from '@lib/supabase.client';
import type { UserRole, ViewContext } from '@types/auth.types';

// ==========================================
// CONSTANTS
// ==========================================

const STORAGE_KEY = 'vdi_active_view_role';

// ==========================================
// HELPER: Get Current User Role
// ==========================================

/**
 * Récupère le rôle de l'utilisateur depuis Supabase
 * TEMPORAIRE: Hardcodé à 'admin' pour dev
 * TODO: Remplacer par vraie logique Supabase RLS
 */
async function getCurrentUserRole(): Promise<UserRole> {
  const email = await getCurrentUserEmail();

  // TEMPORAIRE: Map email → role
  // TODO: Récupérer depuis table users Supabase
  if (email?.includes('allan')) return 'admin';
  if (email?.includes('michelle')) return 'assistant';
  if (email?.includes('nicolas') || email?.includes('nick')) return 'technicien';

  return 'admin'; // Default pour dev
}

// ==========================================
// HOOK
// ==========================================

export function useViewContext(): ViewContext {
  // État du rôle réel (immuable après init)
  const [realRole, setRealRole] = useState<UserRole>('admin');

  // État du rôle visualisé (peut changer si admin)
  const [activeViewRole, setActiveViewRole] = useState<UserRole>('admin');

  // ==========================================
  // INIT: Charger rôle réel
  // ==========================================

  useEffect(() => {
    getCurrentUserRole().then((role) => {
      setRealRole(role);

      // Restaurer dernière vue active si sauvegardée ET si admin
      if (role === 'admin') {
        const saved = localStorage.getItem(STORAGE_KEY) as UserRole | null;
        if (saved && ['admin', 'assistant', 'technicien'].includes(saved)) {
          setActiveViewRole(saved);
        } else {
          setActiveViewRole(role);
        }
      } else {
        // Non-admin: toujours sa propre vue
        setActiveViewRole(role);
      }
    });
  }, []);

  // ==========================================
  // COMPUTED
  // ==========================================

  const isImpersonating = useMemo(
    () => activeViewRole !== realRole,
    [activeViewRole, realRole]
  );

  const canImpersonate = useMemo(() => realRole === 'admin', [realRole]);

  // ==========================================
  // ACTIONS
  // ==========================================

  /**
   * Changer le rôle visualisé
   * Seulement pour admin
   */
  const switchView = useCallback(
    (targetRole: UserRole) => {
      if (!canImpersonate) {
        console.warn('[useViewContext] Only admins can switch views');
        return;
      }

      setActiveViewRole(targetRole);

      // Sauvegarder pour persistance
      localStorage.setItem(STORAGE_KEY, targetRole);
    },
    [canImpersonate]
  );

  /**
   * Revenir à sa propre vue
   */
  const resetView = useCallback(() => {
    setActiveViewRole(realRole);
    localStorage.removeItem(STORAGE_KEY);
  }, [realRole]);

  // ==========================================
  // RETURN
  // ==========================================

  return {
    realRole,
    activeViewRole,
    isImpersonating,
    canImpersonate,
    switchView,
    resetView
  };
}

export default useViewContext;
