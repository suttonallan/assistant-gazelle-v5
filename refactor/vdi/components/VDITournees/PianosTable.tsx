/**
 * PianosTable Component - Table Principale Dashboard
 *
 * Table ultra-réactive avec:
 * - Shift+Clic range selection performant
 * - Couleurs dynamiques selon tournée active
 * - Inline editing (À faire, Travail, Observations)
 * - Tri + filtres
 * - Animations fluides
 */

import React, { useState, useMemo, useRef, useEffect } from 'react';
import { usePianos } from '@hooks/usePianos';
import { useTournees } from '@hooks/useTournees';
import { usePianoColors } from '@hooks/usePianoColors';
import { useRangeSelection, getSelectAllState } from '@hooks/useRangeSelection';
import { LastTunedBadge } from '@components/shared/LastTunedBadge';
import { PianoStatusPill } from '@components/shared/PianoStatusPill';
import { BatchToolbar } from './BatchToolbar';
import { formatDateShort } from '@lib/utils';
import type { Piano, PianoSortConfig } from '@types/piano.types';

// ==========================================
// TYPES
// ==========================================

interface PianosTableProps {
  etablissement: 'vincent-dindy' | 'orford' | 'place-des-arts';
  selectedTourneeId?: string | null;
}

// ==========================================
// COMPONENT
// ==========================================

export function PianosTable({ etablissement, selectedTourneeId }: PianosTableProps) {
  // ==========================================
  // HOOKS
  // ==========================================

  const {
    pianos,
    loading,
    error,
    filteredPianos,
    sortConfig,
    setSortConfig,
    updatePiano,
    refreshPianos
  } = usePianos(etablissement);

  const { activeTournee, tournees, refreshTournees, batchRemovePianosFromTournee, batchMarkAsTopInTournee } = useTournees(etablissement);

  // LOG: Affichage tournée pour debug
  useEffect(() => {
    console.log('[PianosTable] Affichage tournée:', selectedTourneeId);
  }, [selectedTourneeId]);

  // Get tournée à afficher - selectedTourneeId est la SEULE source de vérité
  // Si selectedTourneeId est null, on utilise activeTournee comme fallback
  const displayedTournee = useMemo(() => {
    try {
      if (selectedTourneeId) {
        // Protection: vérifier que tournees est un array
        if (!Array.isArray(tournees)) {
          console.warn('[PianosTable] tournees n\'est pas un array:', tournees);
          return null;
        }
        // Comparaison stricte avec === pour éviter les problèmes de typage
        const found = tournees.find((t) => t && String(t.id) === String(selectedTourneeId));
        return found || null;
      }
      return activeTournee || null;
    } catch (err) {
      console.error('[PianosTable] Erreur dans displayedTournee useMemo:', err);
      return null;
    }
  }, [selectedTourneeId, tournees, activeTournee]);

  // Get pianos in displayed tournee
  const pianosInDisplayedTournee = useMemo(() => {
    try {
      if (!displayedTournee || !Array.isArray(displayedTournee.pianoIds)) {
        return new Set<string>();
      }
      return new Set(displayedTournee.pianoIds);
    } catch (err) {
      console.error('[PianosTable] Erreur dans pianosInDisplayedTournee useMemo:', err);
      return new Set<string>();
    }
  }, [displayedTournee]);

  // Get top pianos in displayed tournee
  const topPianosInDisplayedTournee = useMemo(() => {
    try {
      if (!displayedTournee || !(displayedTournee.topPianoIds instanceof Set)) {
        return new Set<string>();
      }
      return displayedTournee.topPianoIds;
    } catch (err) {
      console.error('[PianosTable] Erreur dans topPianosInDisplayedTournee useMemo:', err);
      return new Set<string>();
    }
  }, [displayedTournee]);

  const { getColor, getColorWithReason } = usePianoColors(etablissement, {
    activeTourneeId: displayedTournee?.id,
    pianosInActiveTournee: pianosInDisplayedTournee,
    topPianosInTournee: topPianosInDisplayedTournee
  });

  const {
    selectedIds,
    handleClick,
    selectAll,
    clearAll,
    isSelected,
    count: selectedCount
  } = useRangeSelection(filteredPianos.map((p) => p.gazelleId));

  // ==========================================
  // STATE
  // ==========================================

  const [editingPianoId, setEditingPianoId] = useState<string | null>(null);
  const [editValues, setEditValues] = useState<{
    aFaire?: string;
    travail?: string;
    observations?: string;
  }>({});

  const selectAllCheckboxRef = useRef<HTMLInputElement>(null);

  // ==========================================
  // COMPUTED
  // ==========================================

  const { checked: selectAllChecked, indeterminate: selectAllIndeterminate } =
    getSelectAllState(selectedCount, filteredPianos.length);

  // ==========================================
  // EFFECTS
  // ==========================================

  useEffect(() => {
    if (selectAllCheckboxRef.current) {
      selectAllCheckboxRef.current.indeterminate = selectAllIndeterminate;
    }
  }, [selectAllIndeterminate]);

  // ==========================================
  // HANDLERS
  // ==========================================

  const handleSort = (field: PianoSortConfig['field']) => {
    const newOrder =
      sortConfig?.field === field && sortConfig.order === 'asc' ? 'desc' : 'asc';
    setSortConfig({ field, order: newOrder });
  };

  const handleSelectAll = () => {
    if (selectAllChecked) {
      clearAll();
    } else {
      selectAll();
    }
  };

  const handleEdit = (piano: Piano) => {
    setEditingPianoId(piano.gazelleId);
    setEditValues({
      aFaire: piano.aFaire || '',
      travail: piano.travail || '',
      observations: piano.observations || ''
    });
  };

  const handleSaveEdit = async (pianoId: string) => {
    try {
      await updatePiano(pianoId, {
        pianoId,
        ...editValues,
        updatedBy: 'current-user@example.com' // TODO: Get from auth
      });

      setEditingPianoId(null);
      setEditValues({});
    } catch (err) {
      console.error('Save edit error:', err);
      alert('Erreur lors de la sauvegarde');
    }
  };

  const handleCancelEdit = () => {
    setEditingPianoId(null);
    setEditValues({});
  };

  const handleMarkCompleted = async (pianoId: string) => {
    try {
      // Enregistrer la date de complétion
      const completedAt = new Date().toISOString();
      
      await updatePiano(pianoId, {
        pianoId,
        status: 'completed',
        isWorkCompleted: true,
        completedAt: completedAt,  // Date de complétion pour Gazelle
        updatedBy: 'current-user@example.com' // TODO: Get from auth
      });
      // Ne pas appeler refreshPianos si updatePiano réussit (optimistic update déjà fait)
    } catch (err) {
      console.error('Mark completed error:', err);
      alert('Erreur lors du marquage comme terminé');
      // Recharger en cas d'erreur pour restaurer l'état
      await refreshPianos();
    }
  };

  const handleUnmarkCompleted = async (pianoId: string) => {
    try {
      await updatePiano(pianoId, {
        pianoId,
        status: 'normal',
        isWorkCompleted: false,
        updatedBy: 'current-user@example.com' // TODO: Get from auth
      });
      await refreshPianos();
    } catch (err) {
      console.error('Unmark completed error:', err);
      alert('Erreur lors de l\'annulation');
    }
  };

  // ==========================================
  // RENDER: LOADING / ERROR
  // ==========================================

  if (loading && pianos.length === 0) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Chargement des pianos...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4">
        <h3 className="text-red-800 font-semibold mb-2">Erreur</h3>
        <p className="text-red-600">{error}</p>
        <button
          onClick={refreshPianos}
          className="mt-3 px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700"
        >
          Réessayer
        </button>
      </div>
    );
  }

  // ==========================================
  // RENDER: TABLE
  // ==========================================

  return (
    <>
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
        {/* Header */}
        <div className="px-4 py-3 border-b border-gray-200 bg-gray-50">
          <div className="flex items-center justify-between">
            <div className="flex-1">
              <h3 className="text-lg font-bold text-gray-900">Pianos</h3>

              {/* Indicateur tournée affichée */}
              {displayedTournee && (
                <div className="flex items-center gap-2 mt-2">
                  <span className={`px-2 py-1 rounded text-xs font-medium ${
                    selectedTourneeId
                      ? 'bg-blue-100 text-blue-800 border border-blue-300'
                      : 'bg-green-100 text-green-800 border border-green-300'
                  }`}>
                    {selectedTourneeId ? '👁️ Affichage' : '✓ Active'}: {displayedTournee.nom}
                  </span>
                  <span className="text-xs text-gray-600">
                    {displayedTournee.pianoIds.length} piano(s) dans cette tournée
                  </span>
                </div>
              )}

              <p className="text-sm text-gray-500 mt-1">
                {filteredPianos.length} piano(s) total
                {selectedCount > 0 && ` · ${selectedCount} sélectionné(s)`}
              </p>
            </div>

            <button
              onClick={refreshPianos}
              disabled={loading}
              className="px-3 py-1.5 text-sm bg-gray-100 hover:bg-gray-200 rounded transition-colors disabled:opacity-50"
            >
              🔄 Sync
            </button>
          </div>
        </div>

        {/* Table */}
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="px-4 py-3 text-left w-12">
                  <input
                    ref={selectAllCheckboxRef}
                    type="checkbox"
                    checked={selectAllChecked}
                    onChange={handleSelectAll}
                    className="w-4 h-4 rounded cursor-pointer"
                    title="Sélectionner tout"
                  />
                </th>

                <SortableHeader
                  label="Local"
                  field="location"
                  currentSort={sortConfig}
                  onSort={handleSort}
                />

                <SortableHeader
                  label="Piano"
                  field="make"
                  currentSort={sortConfig}
                  onSort={handleSort}
                />

                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-700 uppercase">
                  Type
                </th>

                <SortableHeader
                  label="Dernier Accord"
                  field="lastTuned"
                  currentSort={sortConfig}
                  onSort={handleSort}
                />

                <SortableHeader
                  label="Statut"
                  field="status"
                  currentSort={sortConfig}
                  onSort={handleSort}
                />

                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-700 uppercase">
                  À Faire
                </th>

                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-700 uppercase">
                  Travail
                </th>

                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-700 uppercase">
                  Actions
                </th>
              </tr>
            </thead>

            <tbody className="divide-y divide-gray-200">
              {filteredPianos.map((piano) => {
                const isEditing = editingPianoId === piano.gazelleId;
                const { reason } = getColorWithReason(piano);

                return (
                  <tr
                    key={piano.gazelleId}
                    className={`
                      ${getColor(piano)}
                      ${isSelected(piano.gazelleId) ? 'ring-2 ring-blue-500' : ''}
                      hover:shadow-sm transition-all duration-100
                    `}
                    title={reason}
                  >
                    {/* Checkbox */}
                    <td className="px-4 py-3">
                      <input
                        type="checkbox"
                        checked={isSelected(piano.gazelleId)}
                        onMouseDown={(e: React.MouseEvent<HTMLInputElement>) => {
                          // CRITICAL FIX: onMouseDown capture shiftKey (onClick ne fonctionne pas)
                          e.preventDefault();
                          e.stopPropagation();
                          const shiftPressed = e.shiftKey;
                          console.log('[PianosTable] Checkbox mousedown - shiftKey:', shiftPressed);
                          handleClick(piano.gazelleId, shiftPressed);
                        }}
                        onChange={() => {}} // No-op pour éviter warning React
                        className="w-4 h-4 rounded cursor-pointer"
                        data-version="v2-shift-fix"
                      />
                    </td>

                    {/* Local */}
                    <td className="px-4 py-3 text-sm font-medium text-gray-900">
                      {piano.location}
                    </td>

                    {/* Piano */}
                    <td className="px-4 py-3">
                      <div className="text-sm">
                        <div className="font-medium text-gray-900">{piano.make}</div>
                        {piano.model && (
                          <div className="text-gray-500 text-xs">{piano.model}</div>
                        )}
                      </div>
                    </td>

                    {/* Type */}
                    <td className="px-4 py-3">
                      <span className="px-2 py-1 rounded-full text-xs font-medium bg-gray-100 text-gray-700">
                        {piano.type}
                      </span>
                    </td>

                    {/* Dernier Accord */}
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <LastTunedBadge lastTuned={piano.lastTuned} size="xs" />
                        {piano.lastTuned && (
                          <span className="text-xs text-gray-500">
                            {formatDateShort(piano.lastTuned)}
                          </span>
                        )}
                      </div>
                    </td>

                    {/* Statut */}
                    <td className="px-4 py-3">
                      <PianoStatusPill status={piano.status} size="sm" />
                    </td>

                    {/* À Faire */}
                    <td className="px-4 py-3">
                      {isEditing ? (
                        <input
                          type="text"
                          value={editValues.aFaire || ''}
                          onChange={(e) =>
                            setEditValues({ ...editValues, aFaire: e.target.value })
                          }
                          className="w-full px-2 py-1 text-sm border border-gray-300 rounded focus:ring-2 focus:ring-blue-500"
                          placeholder="Tâches..."
                        />
                      ) : (
                        <span className="text-sm text-gray-700">
                          {piano.aFaire || '-'}
                        </span>
                      )}
                    </td>

                    {/* Travail */}
                    <td className="px-4 py-3">
                      {isEditing ? (
                        <input
                          type="text"
                          value={editValues.travail || ''}
                          onChange={(e) =>
                            setEditValues({ ...editValues, travail: e.target.value })
                          }
                          className="w-full px-2 py-1 text-sm border border-gray-300 rounded focus:ring-2 focus:ring-blue-500"
                          placeholder="Travail effectué..."
                        />
                      ) : (
                        <span className="text-sm text-gray-700">
                          {piano.travail || '-'}
                        </span>
                      )}
                    </td>

                    {/* Actions */}
                    <td className="px-4 py-3">
                      {isEditing ? (
                        <div className="flex gap-1">
                          <button
                            onClick={() => handleSaveEdit(piano.gazelleId)}
                            className="px-2 py-1 text-xs bg-green-600 text-white rounded hover:bg-green-700"
                          >
                            ✓
                          </button>
                          <button
                            onClick={handleCancelEdit}
                            className="px-2 py-1 text-xs bg-gray-300 text-gray-700 rounded hover:bg-gray-400"
                          >
                            ✕
                          </button>
                        </div>
                      ) : (
                        <div className="flex gap-1 items-center">
                          <button
                            onClick={() => handleEdit(piano)}
                            className="px-2 py-1 text-xs bg-blue-100 text-blue-700 rounded hover:bg-blue-200"
                          >
                            ✏️ Éditer
                          </button>
                          {piano.status === 'completed' ? (
                            <button
                              onClick={() => handleUnmarkCompleted(piano.gazelleId)}
                              className="px-2 py-1 text-xs bg-yellow-100 text-yellow-700 rounded hover:bg-yellow-200"
                              title="Annuler le statut terminé"
                            >
                              ↶
                            </button>
                          ) : (
                            <button
                              onClick={() => handleMarkCompleted(piano.gazelleId)}
                              className="px-2 py-1 text-xs bg-green-100 text-green-700 rounded hover:bg-green-200"
                              title="Marquer comme terminé"
                            >
                              ✓ Terminé
                            </button>
                          )}
                        </div>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>

          {filteredPianos.length === 0 && (
            <div className="text-center py-12">
              <p className="text-gray-500">Aucun piano trouvé</p>
            </div>
          )}
        </div>
      </div>

      {/* Batch Toolbar (Fixed Bottom) */}
      <BatchToolbar
        selectedIds={selectedIds}
        onClear={clearAll}
        onSuccess={async () => {
          await Promise.all([refreshPianos(), refreshTournees()]);
        }}
        activeTourneeId={activeTournee?.id}
        selectedTourneeId={selectedTourneeId}
        batchRemovePianosFromTournee={batchRemovePianosFromTournee}
        batchMarkAsTopInTournee={batchMarkAsTopInTournee}
      />
    </>
  );
}

// ==========================================
// SUBCOMPONENTS
// ==========================================

interface SortableHeaderProps {
  label: string;
  field: PianoSortConfig['field'];
  currentSort: PianoSortConfig | null;
  onSort: (field: PianoSortConfig['field']) => void;
}

function SortableHeader({
  label,
  field,
  currentSort,
  onSort
}: SortableHeaderProps) {
  const isActive = currentSort?.field === field;
  const isAsc = currentSort?.order === 'asc';

  return (
    <th
      onClick={() => onSort(field)}
      className="px-4 py-3 text-left text-xs font-semibold text-gray-700 uppercase cursor-pointer hover:bg-gray-100 transition-colors select-none"
    >
      <div className="flex items-center gap-2">
        <span>{label}</span>
        <span className="text-gray-400">
          {isActive ? (isAsc ? '↑' : '↓') : '↕'}
        </span>
      </div>
    </th>
  );
}
