/**
 * Auth & Role Types
 */

// ==========================================
// USER ROLES
// ==========================================

export type UserRole = 'admin' | 'assistant' | 'technicien';

// ==========================================
// AUTH USER
// ==========================================

export interface AuthUser {
  /** Email de l'utilisateur */
  email: string;

  /** Rôle réel de l'utilisateur (immuable, provient de Supabase) */
  role: UserRole;

  /** Nom d'affichage */
  displayName?: string;
}

// ==========================================
// VIEW CONTEXT (pour impersonation)
// ==========================================

export interface ViewContext {
  /** Rôle réel de l'utilisateur connecté (immuable) */
  realRole: UserRole;

  /** Rôle actuellement visualisé (peut être différent si admin simule) */
  activeViewRole: UserRole;

  /** True si l'admin simule un autre rôle */
  isImpersonating: boolean;

  /** True si l'utilisateur peut changer de vue (= admin) */
  canImpersonate: boolean;

  /** Changer le rôle visualisé */
  switchView: (role: UserRole) => void;

  /** Revenir à sa propre vue */
  resetView: () => void;
}

// ==========================================
// ROLE PERMISSIONS (pour référence)
// ==========================================

export const ROLE_PERMISSIONS = {
  admin: {
    canViewAll: true,
    canEditAll: true,
    canManageTournees: true,
    canManageUsers: true,
    canImpersonate: true
  },
  assistant: {
    canViewAll: true,
    canEditAll: false,
    canManageTournees: true,
    canManageUsers: false,
    canImpersonate: false
  },
  technicien: {
    canViewAll: false, // Voit seulement ses pianos assignés
    canEditAll: false,
    canManageTournees: false,
    canManageUsers: false,
    canImpersonate: false
  }
} as const;

export default AuthUser;
