/**
 * AdminImpersonationBar - Bandeau de simulation de rôle
 *
 * Visible SEULEMENT pour les admins.
 * Permet de tester l'interface selon différents rôles.
 *
 * Features:
 * - Dropdown pour changer de vue (Admin / Assistant / Technicien)
 * - Indicateur visuel orange quand en mode simulation
 * - Bouton "Retour à ma vue" pour reset
 *
 * @example
 * ```tsx
 * <AdminImpersonationBar />
 * ```
 */

import React from 'react';
import { useViewContext } from '@hooks/useViewContext';
import type { UserRole } from '@types/auth.types';

// ==========================================
// CONSTANTS
// ==========================================

const ROLE_LABELS: Record<UserRole, string> = {
  admin: '👑 Vue Admin',
  assistant: '📋 Vue Assistant',
  technicien: '🔧 Vue Technicien'
};

const ROLE_ICONS: Record<UserRole, string> = {
  admin: '👑',
  assistant: '📋',
  technicien: '🔧'
};

// ==========================================
// COMPONENT
// ==========================================

export function AdminImpersonationBar() {
  const {
    activeViewRole,
    isImpersonating,
    canImpersonate,
    switchView,
    resetView
  } = useViewContext();

  // Pas admin → Ne rien afficher
  if (!canImpersonate) {
    return null;
  }

  return (
    <div
      className={`
        sticky top-0 z-50 px-6 py-3
        flex items-center justify-between
        transition-colors duration-200
        ${
          isImpersonating
            ? 'bg-orange-100 border-b-2 border-orange-500'
            : 'bg-blue-50 border-b border-blue-300'
        }
      `}
    >
      {/* Left: Label + Dropdown */}
      <div className="flex items-center gap-4">
        <span
          className={`
            text-sm font-semibold uppercase tracking-wide
            ${isImpersonating ? 'text-orange-900' : 'text-blue-900'}
          `}
        >
          {isImpersonating ? '🎭 Mode Simulation' : '👑 Admin'}
        </span>

        <select
          value={activeViewRole}
          onChange={(e) => switchView(e.target.value as UserRole)}
          className={`
            px-3 py-1.5 rounded-lg border font-medium text-sm
            focus:outline-none focus:ring-2
            transition-colors
            ${
              isImpersonating
                ? 'bg-white border-orange-300 text-orange-900 focus:ring-orange-500'
                : 'bg-white border-blue-300 text-blue-900 focus:ring-blue-500'
            }
          `}
        >
          <option value="admin">{ROLE_LABELS.admin}</option>
          <option value="assistant">{ROLE_LABELS.assistant}</option>
          <option value="technicien">{ROLE_LABELS.technicien}</option>
        </select>
      </div>

      {/* Right: Current view indicator + Reset button */}
      <div className="flex items-center gap-4">
        {/* Current View Indicator */}
        <div className="flex items-center gap-2 text-sm">
          <span className="text-gray-600">Vue active:</span>
          <span
            className={`
              px-2 py-1 rounded font-medium
              ${
                isImpersonating
                  ? 'bg-orange-200 text-orange-900'
                  : 'bg-blue-200 text-blue-900'
              }
            `}
          >
            {ROLE_ICONS[activeViewRole]} {ROLE_LABELS[activeViewRole].split(' ')[1]}
          </span>
        </div>

        {/* Reset Button (visible seulement si impersonating) */}
        {isImpersonating && (
          <button
            onClick={resetView}
            className="
              text-sm font-medium text-orange-700 hover:text-orange-900
              underline decoration-dotted
              transition-colors
            "
          >
            Retour à ma vue →
          </button>
        )}
      </div>
    </div>
  );
}

export default AdminImpersonationBar;
