/**
 * BatchToolbar Component - Actions Groupées Ultra-Réactives
 *
 * Toolbar animée pour batch operations:
 * - Slide-in animation
 * - Progress indicator
 * - Actions: Top, À faire, Retirer, Masquer
 *
 * @example
 * ```tsx
 * <BatchToolbar
 *   selectedCount={5}
 *   onMarkAsTop={handleTop}
 *   onClear={clearSelection}
 * />
 * ```
 */

import React, { useEffect, useState } from 'react';
import { useBatchOperations } from '@hooks/useBatchOperations';
import { PianoStatus } from '@types/piano.types';
import type { PianoUsage } from '@types/piano.types';

// ==========================================
// TYPES
// ==========================================

interface BatchToolbarProps {
  /** IDs sélectionnés */
  selectedIds: Set<string>;

  /** Callback désélection */
  onClear: () => void;

  /** Callback après succès */
  onSuccess?: () => void;

  /** ID de la tournée active (pour ajouter pianos) */
  activeTourneeId?: string | null;

  /** ID de la tournée sélectionnée (pour préparation) */
  selectedTourneeId?: string | null;

  /** Fonction batch pour retirer pianos de tournée (RAPIDE) */
  batchRemovePianosFromTournee?: (tourneeId: string, pianoIds: string[]) => Promise<void>;

  /** Fonction batch pour marquer pianos comme Top dans une tournée - retourne nombre mis à jour */
  batchMarkAsTopInTournee?: (tourneeId: string, pianoIds: string[]) => Promise<number>;
}

// ==========================================
// COMPONENT
// ==========================================

export function BatchToolbar({
  selectedIds,
  onClear,
  onSuccess,
  activeTourneeId,
  selectedTourneeId,
  batchRemovePianosFromTournee,
  batchMarkAsTopInTournee
}: BatchToolbarProps) {
  const {
    batchUpdateStatus,
    batchUpdateUsage,
    batchAddToTournee,
    loading,
    progress
  } = useBatchOperations();

  const [isVisible, setIsVisible] = useState(false);

  const selectedCount = selectedIds.size;

  // ==========================================
  // EFFECTS
  // ==========================================

  // Slide-in animation
  useEffect(() => {
    if (selectedCount > 0) {
      setTimeout(() => setIsVisible(true), 50);
    } else {
      setIsVisible(false);
    }
  }, [selectedCount]);

  // ==========================================
  // HANDLERS
  // ==========================================

  const handleMarkAsTop = async () => {
    // Utiliser tournée sélectionnée OU active
    const tourneeId = selectedTourneeId || activeTourneeId;

    if (!tourneeId) {
      alert('⚠️ Aucune tournée sélectionnée. Impossible de marquer comme Top.');
      return;
    }

    if (!batchMarkAsTopInTournee) {
      alert('❌ Fonction "Marquer Top" non disponible');
      return;
    }

    try {
      const selectedArray = Array.from(selectedIds);

      // UPDATE is_top=true dans tournee_pianos
      const updatedCount = await batchMarkAsTopInTournee(tourneeId, selectedArray);

      // Vérifier si des pianos ont été traités
      if (updatedCount === 0) {
        alert(`⚠️ Aucun piano traité. Une erreur s'est produite.`);
        return;
      }

      alert(`✅ ${updatedCount} piano(s) marqué(s) comme Top\n(ajoutés à la tournée si nécessaire)`);

      // Force refresh
      if (onSuccess) await onSuccess();
      onClear();
    } catch (err) {
      console.error('Batch mark as top error:', err);
      alert(`❌ Erreur: ${err}`);
    }
  };


  const handleRemove = async () => {
    // Utiliser tournée sélectionnée OU active
    const tourneeId = selectedTourneeId || activeTourneeId;

    if (!tourneeId) {
      alert('⚠️ Aucune tournée active. Impossible de retirer les pianos.');
      return;
    }

    if (!batchRemovePianosFromTournee) {
      alert('❌ Fonction de suppression non disponible');
      return;
    }

    const confirmed = confirm(
      `Retirer ${selectedCount} piano(s) de la tournée?`
    );

    if (!confirmed) return;

    try {
      // 1. DELETE batch - Retirer de la table tournee_pianos
      await batchRemovePianosFromTournee(tourneeId, Array.from(selectedIds));

      // 2. Reset status → 'normal' pour tous les pianos retirés
      await batchUpdateStatus(selectedIds, PianoStatus.Normal, {
        onSuccess: (count) => {
          console.log(`✅ Status réinitialisé pour ${count} piano(s)`);
        },
        onError: (err) => {
          console.error('Erreur reset status:', err);
        }
      });

      alert(`✅ ${selectedCount} piano(s) retiré(s) de la tournée`);

      // Force refresh pour mettre à jour compteur
      if (onSuccess) await onSuccess();
      onClear();
    } catch (err) {
      console.error('Batch remove error:', err);
      alert(`❌ Erreur lors du retrait: ${err}`);
    }
  };


  const handleAddToSelectedTournee = async () => {
    if (!selectedTourneeId) {
      alert('⚠️ Aucune tournée sélectionnée. Cliquez sur une tournée dans la sidebar.');
      return;
    }

    try {
      await batchAddToTournee(selectedIds, selectedTourneeId, {
        onSuccess: async (count) => {
          alert(`✅ ${count} piano(s) ajouté(s) à la tournée`);
          // Force refresh pour voir les changements
          if (onSuccess) await onSuccess();
          onClear();
        },
        onError: (err) => alert(`❌ Erreur: ${err}`)
      });
    } catch (err) {
      console.error('Batch add to tournee error:', err);
    }
  };

  // ==========================================
  // RENDER
  // ==========================================

  if (selectedCount === 0) return null;

  return (
    <div
      className={`
        fixed bottom-0 left-0 right-0 z-50
        bg-gradient-to-r from-blue-600 to-blue-700
        shadow-2xl
        transform transition-transform duration-300 ease-out
        ${isVisible ? 'translate-y-0' : 'translate-y-full'}
      `}
    >
      {/* Progress Bar */}
      {loading && progress > 0 && (
        <div className="absolute top-0 left-0 right-0 h-1 bg-blue-800">
          <div
            className="h-full bg-white transition-all duration-300"
            style={{ width: `${progress}%` }}
          />
        </div>
      )}

      <div className="max-w-7xl mx-auto px-4 py-4">
        <div className="flex items-center justify-between">
          {/* Left: Selection Info */}
          <div className="flex items-center gap-3">
            <div className="bg-white/20 backdrop-blur rounded-full px-4 py-2">
              <span className="text-white font-bold text-lg">
                {selectedCount}
              </span>
              <span className="text-blue-100 ml-2 text-sm">
                sélectionné{selectedCount > 1 ? 's' : ''}
              </span>
            </div>

            {loading && (
              <div className="flex items-center gap-2 text-white">
                <div className="animate-spin rounded-full h-4 w-4 border-2 border-white border-t-transparent" />
                <span className="text-sm">Traitement...</span>
              </div>
            )}
          </div>

          {/* Right: Actions */}
          <div className="flex items-center gap-2">
            {selectedTourneeId && (
              <ActionButton
                onClick={handleAddToSelectedTournee}
                disabled={loading}
                icon="➕"
                label="Ajouter à tournée"
                variant="blue"
              />
            )}

            <ActionButton
              onClick={handleMarkAsTop}
              disabled={loading}
              icon="⭐"
              label="Marquer Top"
              variant="amber"
            />

            <ActionButton
              onClick={handleRemove}
              disabled={loading}
              icon="↩️"
              label="Retirer"
              variant="gray"
            />

            <button
              onClick={onClear}
              disabled={loading}
              className="
                ml-4 px-4 py-2 rounded-lg
                bg-white/10 hover:bg-white/20
                text-white font-medium
                transition-colors
                disabled:opacity-50 disabled:cursor-not-allowed
              "
            >
              ✕ Annuler
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

// ==========================================
// SUBCOMPONENTS
// ==========================================

interface ActionButtonProps {
  onClick: () => void;
  disabled: boolean;
  icon: string;
  label: string;
  variant: 'amber' | 'yellow' | 'gray' | 'red' | 'blue';
}

function ActionButton({
  onClick,
  disabled,
  icon,
  label,
  variant
}: ActionButtonProps) {
  const variantClasses = {
    amber: 'bg-amber-500 hover:bg-amber-600',
    yellow: 'bg-yellow-500 hover:bg-yellow-600',
    gray: 'bg-gray-500 hover:bg-gray-600',
    red: 'bg-red-500 hover:bg-red-600',
    blue: 'bg-blue-500 hover:bg-blue-600'
  };

  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={`
        px-4 py-2 rounded-lg
        ${variantClasses[variant]}
        text-white font-medium
        transition-all duration-200
        hover:scale-105 active:scale-95
        disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100
        shadow-lg
      `}
    >
      <span className="mr-2">{icon}</span>
      {label}
    </button>
  );
}

export default BatchToolbar;
