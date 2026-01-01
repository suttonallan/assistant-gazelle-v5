/**
 * PDAInventoryTable Component - Inventaire Pianos Place des Arts
 *
 * Basé sur InventoryTable mais avec fonctionnalités spécifiques:
 * - Mapping abréviations PDA ↔ Pianos Gazelle
 * - Alertes pour abréviations non mappées
 * - Confrontation demandes ↔ pianos
 * - Vue de jumelage avec suggestions
 *
 * @example
 * ```tsx
 * <PDAInventoryTable />
 * ```
 */

import React, { useState, useMemo, useRef, useEffect } from 'react';
import { usePianos } from '@hooks/usePianos';
import { usePDAPianoMappings } from '@hooks/usePDAPianoMappings';
import { useRangeSelection, getSelectAllState } from '@hooks/useRangeSelection';
import { useBatchOperations } from '@hooks/useBatchOperations';
import { LastTunedBadge } from '@components/shared/LastTunedBadge';
import { PianoStatusPill } from '@components/shared/PianoStatusPill';
import { PianoMappingModal } from './PianoMappingModal';
import { formatDateShort } from '@lib/utils';
import type { Piano, PianoSortConfig } from '@types/piano.types';
import type { PianoMappingStats } from '@types/pda.types';

// ==========================================
// TYPES
// ==========================================

interface PDAInventoryTableProps {
  // Pas de props pour l'instant, utilise 'place-des-arts' par défaut
}

// ==========================================
// COMPONENT
// ==========================================

export function PDAInventoryTable({}: PDAInventoryTableProps) {
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
  } = usePianos('place-des-arts', {
    includeHidden: true
  });

  const {
    mappings,
    loading: mappingsLoading,
    stats,
    createMapping,
    updateMapping,
    deleteMapping,
    refresh: refreshMappings
  } = usePDAPianoMappings();

  const { batchSetVisibility, loading: batchLoading } = useBatchOperations();

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
  const [showUnmappedOnly, setShowUnmappedOnly] = useState(false);
  const [mappingModalOpen, setMappingModalOpen] = useState(false);
  const [selectedPianoForMapping, setSelectedPianoForMapping] = useState<Piano | null>(null);
  const selectAllCheckboxRef = useRef<HTMLInputElement>(null);

  // ==========================================
  // COMPUTED
  // ==========================================

  // Créer un map pour lookup rapide: gazelle_piano_id → abbreviation
  const pianoToAbbreviationMap = useMemo(() => {
    const map = new Map<string, string>();
    mappings.forEach((m) => {
      map.set(m.gazelle_piano_id, m.piano_abbreviation);
    });
    return map;
  }, [mappings]);

  // Créer un map pour lookup rapide: abbreviation → stats
  const abbreviationStatsMap = useMemo(() => {
    const map = new Map<string, PianoMappingStats>();
    stats.forEach((s) => {
      map.set(s.abbreviation, s);
    });
    return map;
  }, [stats]);

      // Enrichir les pianos avec les données de mapping
  const enrichedPianos = useMemo(() => {
    return filteredPianos.map((piano) => {
      const abbreviation = pianoToAbbreviationMap.get(piano.gazelleId);
      const abbreviationStats = abbreviation
        ? abbreviationStatsMap.get(abbreviation)
        : undefined;
      const mapping = mappings.find((m) => m.gazelle_piano_id === piano.gazelleId);

      return {
        ...piano,
        pdaAbbreviation: abbreviation,
        pdaStats: abbreviationStats,
        pdaMapping: mapping
      };
    });
  }, [filteredPianos, pianoToAbbreviationMap, abbreviationStatsMap, mappings]);

  // Appliquer les filtres additionnels
  const displayedPianos = useMemo(() => {
    let result = [...enrichedPianos];

    // Search filter
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase();
      result = result.filter(
        (p) =>
          p.make.toLowerCase().includes(query) ||
          p.location.toLowerCase().includes(query) ||
          (p.model && p.model.toLowerCase().includes(query)) ||
          (p.serialNumber && p.serialNumber.toLowerCase().includes(query)) ||
          (p.pdaAbbreviation && p.pdaAbbreviation.toLowerCase().includes(query))
      );
    }

    // Hidden-only filter
    if (showHiddenOnly) {
      result = result.filter((p) => p.isHidden);
    }

    // Unmapped-only filter (pianos sans abréviation mappée)
    if (showUnmappedOnly) {
      result = result.filter((p) => !p.pdaAbbreviation);
    }

    return result;
  }, [enrichedPianos, searchQuery, showHiddenOnly, showUnmappedOnly]);

  // Compter les abréviations non mappées
  const unmappedAbbreviations = useMemo(() => {
    return stats.filter((s) => !s.mapped && s.request_count > 0);
  }, [stats]);

  // Compter les mappings incertains
  const uncertainMappings = useMemo(() => {
    return mappings.filter((m) => m.is_uncertain);
  }, [mappings]);

  // Select All checkbox state
  const { checked: selectAllChecked, indeterminate: selectAllIndeterminate } =
    getSelectAllState(selectedCount, displayedPianos.length);

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

  const handleToggleHidden = async (piano: Piano) => {
    try {
      await updatePiano(piano.gazelleId, {
        pianoId: piano.gazelleId,
        isHidden: !piano.isHidden,
        updatedBy: 'current-user@example.com'
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
        onSuccess: () => {
          alert(`${selectedCount} piano(s) masqué(s)`);
          clearAll();
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
        onSuccess: () => {
          alert(`${selectedCount} piano(s) affiché(s)`);
          clearAll();
        },
        onError: (err) => alert(`Erreur: ${err}`)
      });
    } catch (err) {
      console.error('Batch show error:', err);
    }
  };

  const handleMapPiano = (piano: Piano) => {
    setSelectedPianoForMapping(piano);
    setMappingModalOpen(true);
  };

  const handleMappingComplete = async () => {
    await refreshMappings();
    await refreshPianos();
    setMappingModalOpen(false);
    setSelectedPianoForMapping(null);
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
      {/* ALERTE: Mappings incertains (priorité haute) */}
      {uncertainMappings.length > 0 && (
        <div className="bg-orange-50 border-l-4 border-orange-400 p-4">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-orange-800 font-semibold mb-1">
                ⚠️ {uncertainMappings.length} mapping(s) nécessite(nt) vérification
              </h3>
              <p className="text-orange-700 text-sm">
                Certains mappings sont marqués comme incertains et nécessitent une
                validation par le gestionnaire.
              </p>
            </div>
            <button
              onClick={() => setMappingModalOpen(true)}
              className="px-4 py-2 bg-orange-600 text-white rounded-lg hover:bg-orange-700 text-sm font-medium"
            >
              Vérifier maintenant
            </button>
          </div>
        </div>
      )}

      {/* ALERTE: Abréviations non mappées */}
      {unmappedAbbreviations.length > 0 && (
        <div className="bg-yellow-50 border-l-4 border-yellow-400 p-4">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-yellow-800 font-semibold mb-1">
                ⚠️ {unmappedAbbreviations.length} abréviation(s) non mappée(s)
              </h3>
              <p className="text-yellow-700 text-sm">
                {unmappedAbbreviations
                  .slice(0, 5)
                  .map((s) => `${s.abbreviation} (${s.request_count} demande(s))`)
                  .join(', ')}
                {unmappedAbbreviations.length > 5 &&
                  ` ... et ${unmappedAbbreviations.length - 5} autre(s)`}
              </p>
            </div>
            <button
              onClick={() => setMappingModalOpen(true)}
              className="px-4 py-2 bg-yellow-600 text-white rounded-lg hover:bg-yellow-700 text-sm font-medium"
            >
              Mapper maintenant
            </button>
          </div>
        </div>
      )}

      {/* HEADER & FILTERS */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-xl font-bold text-gray-900">
              Inventaire Pianos - Place des Arts
            </h2>
            <p className="text-sm text-gray-500 mt-1">
              {displayedPianos.length} piano(s) · {selectedCount} sélectionné(s)
              {uncertainMappings.length > 0 && (
                <span className="text-orange-600 ml-2 font-semibold">
                  · ⚠️ {uncertainMappings.length} mapping(s) incertain(s)
                </span>
              )}
              {unmappedAbbreviations.length > 0 && (
                <span className="text-yellow-600 ml-2">
                  · {unmappedAbbreviations.length} abréviation(s) non mappée(s)
                </span>
              )}
            </p>
          </div>

          <div className="flex gap-2">
            <button
              onClick={() => setMappingModalOpen(true)}
              className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
            >
              🔗 Gérer les mappings
            </button>
            <button
              onClick={refreshPianos}
              disabled={loading}
              className="px-4 py-2 text-sm bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors disabled:opacity-50"
            >
              🔄 Actualiser
            </button>
          </div>
        </div>

        {/* Search & Filters */}
        <div className="flex gap-3">
          <input
            type="text"
            placeholder="Rechercher piano, local, série, abréviation..."
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

          <label className="flex items-center gap-2 px-4 py-2 bg-gray-50 rounded-lg cursor-pointer hover:bg-gray-100">
            <input
              type="checkbox"
              checked={showUnmappedOnly}
              onChange={(e) => setShowUnmappedOnly(e.target.checked)}
              className="w-4 h-4"
            />
            <span className="text-sm font-medium text-gray-700">
              Non mappés
            </span>
          </label>
        </div>
      </div>

      {/* BATCH TOOLBAR */}
      {selectedCount > 0 && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
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
                  Abréviation PDA
                </th>

                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider">
                  Demandes
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

                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider">
                  Actions
                </th>
              </tr>
            </thead>

            <tbody className="divide-y divide-gray-200">
              {displayedPianos.map((piano) => (
                <PDAPianoRow
                  key={piano.gazelleId}
                  piano={piano}
                  isSelected={isSelected(piano.gazelleId)}
                  onClickCheckbox={(shiftKey) =>
                    handleClick(piano.gazelleId, shiftKey)
                  }
                  onToggleHidden={() => handleToggleHidden(piano)}
                  onMapPiano={() => handleMapPiano(piano)}
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

      {/* MAPPING MODAL */}
      {mappingModalOpen && (
        <PianoMappingModal
          isOpen={mappingModalOpen}
          onClose={() => {
            setMappingModalOpen(false);
            setSelectedPianoForMapping(null);
          }}
          selectedPiano={selectedPianoForMapping}
          onMappingComplete={handleMappingComplete}
        />
      )}
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

interface PDAPianoRowProps {
  piano: Piano & {
    pdaAbbreviation?: string;
    pdaStats?: PianoMappingStats;
    pdaMapping?: any;
  };
  isSelected: boolean;
  onClickCheckbox: (shiftKey: boolean) => void;
  onToggleHidden: () => void;
  onMapPiano: () => void;
}

function PDAPianoRow({
  piano,
  isSelected,
  onClickCheckbox,
  onToggleHidden,
  onMapPiano
}: PDAPianoRowProps) {
  const hasMapping = !!piano.pdaAbbreviation;
  const requestCount = piano.pdaStats?.request_count || 0;
  const isUncertain = piano.pdaMapping?.is_uncertain || false;

  return (
    <tr
      className={`
        ${isSelected ? 'ring-2 ring-blue-500' : ''}
        hover:shadow-sm transition-all duration-100
        ${isUncertain ? 'bg-orange-50 border-l-4 border-orange-400' : !hasMapping ? 'bg-yellow-50' : 'bg-white'}
      `}
    >
      {/* Checkbox */}
      <td className="px-4 py-3">
        <input
          type="checkbox"
          checked={isSelected}
          onMouseDown={(e: React.MouseEvent<HTMLInputElement>) => {
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

      {/* Abréviation PDA */}
      <td className="px-4 py-3">
        {hasMapping ? (
          <div className="flex items-center gap-2">
            <span
              className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${
                isUncertain
                  ? 'bg-orange-100 text-orange-700 border border-orange-300'
                  : 'bg-green-100 text-green-700'
              }`}
            >
              {piano.pdaAbbreviation}
            </span>
            {isUncertain && (
              <span
                className="text-orange-600 text-xs"
                title={piano.pdaMapping?.uncertainty_note || 'Mapping incertain'}
              >
                ⚠️
              </span>
            )}
          </div>
        ) : (
          <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-yellow-100 text-yellow-700">
            ⚠️ Non mappé
          </span>
        )}
      </td>

      {/* Demandes */}
      <td className="px-4 py-3">
        {hasMapping && requestCount > 0 ? (
          <span className="text-sm text-gray-700">
            {requestCount} demande(s)
          </span>
        ) : (
          <span className="text-sm text-gray-400">-</span>
        )}
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

      {/* Actions */}
      <td className="px-4 py-3">
        <button
          onClick={onMapPiano}
          className={`
            px-3 py-1 rounded-lg text-sm font-medium transition-colors
            ${
              hasMapping
                ? 'bg-blue-100 text-blue-700 hover:bg-blue-200'
                : 'bg-yellow-100 text-yellow-700 hover:bg-yellow-200'
            }
          `}
        >
          {hasMapping ? '✏️ Modifier' : '🔗 Mapper'}
        </button>
      </td>
    </tr>
  );
}

export default PDAInventoryTable;

