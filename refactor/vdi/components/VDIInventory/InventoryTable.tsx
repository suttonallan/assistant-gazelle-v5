/**
 * InventoryTable Component - Gestion Inventaire Pianos
 *
 * Table ultra-réactive avec:
 * - Shift+Clic range selection
 * - Inline toggle isHidden
 * - Tri + filtres
 * - Batch operations
 *
 * @example
 * ```tsx
 * <InventoryTable
 *   pianos={pianos}
 *   onToggleHidden={handleToggle}
 *   onBatchHide={handleBatchHide}
 * />
 * ```
 */

import React, { useState, useMemo, useRef, useEffect } from 'react';
import { usePianos } from '@hooks/usePianos';
import { usePianoColors } from '@hooks/usePianoColors';
import { useRangeSelection, getSelectAllState } from '@hooks/useRangeSelection';
import { useBatchOperations } from '@hooks/useBatchOperations';
import { LastTunedBadge } from '@components/shared/LastTunedBadge';
import { PianoStatusPill } from '@components/shared/PianoStatusPill';
import { formatDateShort } from '@lib/utils';
import type { Piano, PianoSortConfig, PianoFilters } from '@types/piano.types';

// ==========================================
// TYPES
// ==========================================

interface InventoryTableProps {
  /** Institution ID */
  etablissement: 'vincent-dindy' | 'orford' | 'place-des-arts';
}

// ==========================================
// COMPONENT
// ==========================================

export function InventoryTable({ etablissement }: InventoryTableProps) {
  // ==========================================
  // HOOKS
  // ==========================================

  const {
    pianos,
    loading,
    error,
    filteredPianos,
    filters,
    setFilters,
    sortConfig,
    setSortConfig,
    updatePiano,
    refreshPianos
  } = usePianos(etablissement, {
    includeHidden: true // Afficher TOUS les pianos dans inventaire
  });

  const { batchSetVisibility, loading: batchLoading } = useBatchOperations();

  // Inventaire: pas de coloration par tournée (toujours blanc)
  const { getColor } = usePianoColors(etablissement, {
    activeTourneeId: null,
    pianosInActiveTournee: new Set()
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

  const [searchQuery, setSearchQuery] = useState('');
  const [showHiddenOnly, setShowHiddenOnly] = useState(false);
  const selectAllCheckboxRef = useRef<HTMLInputElement>(null);

  // ==========================================
  // COMPUTED
  // ==========================================

  // Apply additional filters (search, hidden-only)
  const displayedPianos = useMemo(() => {
    let result = [...filteredPianos];

    // Search filter
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase();
      result = result.filter(
        (p) =>
          p.make.toLowerCase().includes(query) ||
          p.location.toLowerCase().includes(query) ||
          (p.model && p.model.toLowerCase().includes(query)) ||
          (p.serialNumber && p.serialNumber.toLowerCase().includes(query))
      );
    }

    // Hidden-only filter
    if (showHiddenOnly) {
      result = result.filter((p) => p.isHidden);
    }

    return result;
  }, [filteredPianos, searchQuery, showHiddenOnly]);

  // Select All checkbox state
  const { checked: selectAllChecked, indeterminate: selectAllIndeterminate } =
    getSelectAllState(selectedCount, displayedPianos.length);

  // ==========================================
  // EFFECTS
  // ==========================================

  // Update indeterminate state of "Select All" checkbox
  useEffect(() => {
    if (selectAllCheckboxRef.current) {
      selectAllCheckboxRef.current.indeterminate = selectAllIndeterminate;
    }
  }, [selectAllIndeterminate]);

  // ==========================================
  // HANDLERS
  // ==========================================

  const handleToggleHidden = async (piano: Piano) => {
    try {
      await updatePiano(piano.gazelleId, {
        pianoId: piano.gazelleId,
        isHidden: !piano.isHidden,
        updatedBy: 'current-user@example.com' // TODO: Get from auth
      });
    } catch (err) {
      console.error('Toggle hidden error:', err);
      alert('Erreur lors de la mise à jour');
    }
  };

  const handleBatchHide = async () => {
    if (selectedCount === 0) return;

    const confirmed = confirm(
      `Masquer ${selectedCount} piano(s) de l'inventaire?`
    );

    if (!confirmed) return;

    try {
      await batchSetVisibility(selectedIds, true, {
        onSuccess: async () => {
          alert(`${selectedCount} piano(s) masqué(s)`);
          clearAll();
          // CRITICAL: Force refresh pour voir les changements
          await refreshPianos();
        },
        onError: (err) => alert(`Erreur: ${err}`)
      });
    } catch (err) {
      console.error('Batch hide error:', err);
    }
  };

  const handleBatchShow = async () => {
    if (selectedCount === 0) return;

    try {
      await batchSetVisibility(selectedIds, false, {
        onSuccess: async () => {
          alert(`${selectedCount} piano(s) affiché(s)`);
          clearAll();
          // CRITICAL: Force refresh pour voir les changements
          await refreshPianos();
        },
        onError: (err) => alert(`Erreur: ${err}`)
      });
    } catch (err) {
      console.error('Batch show error:', err);
    }
  };

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
    <div className="space-y-4">
      {/* HEADER & FILTERS */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-xl font-bold text-gray-900">
              Inventaire Pianos
            </h2>
            <p className="text-sm text-gray-500 mt-1">
              {displayedPianos.length} piano(s) · {selectedCount} sélectionné(s)
            </p>
          </div>

          <button
            onClick={refreshPianos}
            disabled={loading}
            className="px-4 py-2 text-sm bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors disabled:opacity-50"
          >
            🔄 Actualiser
          </button>
        </div>

        {/* Search & Filters */}
        <div className="flex gap-3">
          <input
            type="text"
            placeholder="Rechercher piano, local, série..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />

          <label className="flex items-center gap-2 px-4 py-2 bg-gray-50 rounded-lg cursor-pointer hover:bg-gray-100">
            <input
              type="checkbox"
              checked={showHiddenOnly}
              onChange={(e) => setShowHiddenOnly(e.target.checked)}
              className="w-4 h-4"
            />
            <span className="text-sm font-medium text-gray-700">
              Masqués uniquement
            </span>
          </label>
        </div>
      </div>

      {/* BATCH TOOLBAR - STICKY */}
      {selectedCount > 0 && (
        <div className="sticky top-0 z-10 bg-blue-50 border border-blue-200 rounded-lg p-4 shadow-md">
          <div className="flex items-center justify-between">
            <span className="text-blue-900 font-medium">
              {selectedCount} piano(s) sélectionné(s)
            </span>

            <div className="flex gap-2">
              <button
                onClick={handleBatchShow}
                disabled={batchLoading}
                className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors disabled:opacity-50 text-sm font-medium"
              >
                👁️ Afficher
              </button>

              <button
                onClick={handleBatchHide}
                disabled={batchLoading}
                className="px-4 py-2 bg-orange-600 text-white rounded-lg hover:bg-orange-700 transition-colors disabled:opacity-50 text-sm font-medium"
              >
                🚫 Masquer
              </button>

              <button
                onClick={clearAll}
                className="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition-colors text-sm font-medium"
              >
                Annuler
              </button>
            </div>
          </div>
        </div>
      )}

      {/* TABLE */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
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
                    title="Sélectionner tout (Shift+Clic pour plage)"
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

                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider">
                  Type
                </th>

                <SortableHeader
                  label="Dernier Accord"
                  field="lastTuned"
                  currentSort={sortConfig}
                  onSort={handleSort}
                />

                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider">
                  Statut
                </th>

                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider">
                  Visibilité
                </th>
              </tr>
            </thead>

            <tbody className="divide-y divide-gray-200">
              {displayedPianos.map((piano) => (
                <PianoRow
                  key={piano.gazelleId}
                  piano={piano}
                  color={getColor(piano)}
                  isSelected={isSelected(piano.gazelleId)}
                  onClickCheckbox={(shiftKey) =>
                    handleClick(piano.gazelleId, shiftKey)
                  }
                  onToggleHidden={() => handleToggleHidden(piano)}
                />
              ))}
            </tbody>
          </table>

          {displayedPianos.length === 0 && (
            <div className="text-center py-12">
              <p className="text-gray-500">Aucun piano trouvé</p>
            </div>
          )}
        </div>
      </div>
    </div>
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
      className="px-4 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider cursor-pointer hover:bg-gray-100 transition-colors select-none"
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

interface PianoRowProps {
  piano: Piano;
  color: string;
  isSelected: boolean;
  onClickCheckbox: (shiftKey: boolean) => void;
  onToggleHidden: () => void;
}

function PianoRow({
  piano,
  color,
  isSelected,
  onClickCheckbox,
  onToggleHidden
}: PianoRowProps) {
  return (
    <tr
      className={`
        ${color}
        ${isSelected ? 'ring-2 ring-blue-500' : ''}
        hover:shadow-sm transition-all duration-100
      `}
    >
      {/* Checkbox */}
      <td className="px-4 py-3">
        <input
          type="checkbox"
          checked={isSelected}
          onMouseDown={(e: React.MouseEvent<HTMLInputElement>) => {
            // CRITICAL FIX: onMouseDown capture shiftKey (onChange ne fonctionne pas)
            e.preventDefault();
            e.stopPropagation();
            onClickCheckbox(e.shiftKey);
          }}
          onChange={() => {}}
          className="w-4 h-4 rounded cursor-pointer"
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
        <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-gray-100 text-gray-700">
          {piano.type}
        </span>
      </td>

      {/* Dernier Accord */}
      <td className="px-4 py-3">
        <LastTunedBadge lastTuned={piano.lastTuned} size="sm" />
      </td>

      {/* Statut */}
      <td className="px-4 py-3">
        <PianoStatusPill status={piano.status} size="sm" />
      </td>

      {/* Visibilité Toggle */}
      <td className="px-4 py-3">
        <button
          onClick={onToggleHidden}
          className={`
            px-3 py-1 rounded-lg text-sm font-medium transition-colors
            ${
              piano.isHidden
                ? 'bg-red-100 text-red-700 hover:bg-red-200'
                : 'bg-green-100 text-green-700 hover:bg-green-200'
            }
          `}
        >
          {piano.isHidden ? '🚫 Masqué' : '👁️ Visible'}
        </button>
      </td>
    </tr>
  );
}

export default InventoryTable;
