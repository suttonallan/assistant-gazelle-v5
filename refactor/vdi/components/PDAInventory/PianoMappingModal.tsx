/**
 * PianoMappingModal - Modal pour mapper abréviations PDA ↔ Pianos Gazelle
 *
 * Affiche:
 * - Liste des abréviations non mappées (avec alertes)
 * - Liste des pianos disponibles
 * - Interface de jumelage
 */

import React, { useState, useMemo } from 'react';
import { usePianos } from '@hooks/usePianos';
import { usePDAPianoMappings } from '@hooks/usePDAPianoMappings';
import type { Piano } from '@types/piano.types';
import type { PianoMappingStats } from '@types/pda.types';

// ==========================================
// TYPES
// ==========================================

interface PianoMappingModalProps {
  isOpen: boolean;
  onClose: () => void;
  selectedPiano?: Piano | null;
  onMappingComplete: () => void;
}

// ==========================================
// COMPONENT
// ==========================================

export function PianoMappingModal({
  isOpen,
  onClose,
  selectedPiano,
  onMappingComplete
}: PianoMappingModalProps) {
  const { pianos } = usePianos('place-des-arts', { includeHidden: true });
  const {
    mappings,
    stats,
    createMapping,
    updateMapping,
    markUncertain,
    markCertain,
    deleteMapping,
    loading
  } = usePDAPianoMappings();

  const [selectedAbbreviation, setSelectedAbbreviation] = useState<string>('');
  const [selectedPianoId, setSelectedPianoId] = useState<string>('');
  const [searchAbbreviation, setSearchAbbreviation] = useState('');
  const [searchPiano, setSearchPiano] = useState('');
  const [isUncertain, setIsUncertain] = useState<boolean>(false);
  const [uncertaintyNote, setUncertaintyNote] = useState<string>('');

  // Filtrer les abréviations non mappées
  const unmappedAbbreviations = useMemo(() => {
    return stats
      .filter((s) => !s.mapped)
      .filter((s) =>
        searchAbbreviation
          ? s.abbreviation
              .toLowerCase()
              .includes(searchAbbreviation.toLowerCase())
          : true
      )
      .sort((a, b) => b.request_count - a.request_count); // Trier par nombre de demandes
  }, [stats, searchAbbreviation]);

  // Filtrer les pianos
  const filteredPianos = useMemo(() => {
    return pianos
      .filter((p) =>
        searchPiano
          ? p.make.toLowerCase().includes(searchPiano.toLowerCase()) ||
            p.location.toLowerCase().includes(searchPiano.toLowerCase()) ||
            (p.model && p.model.toLowerCase().includes(searchPiano.toLowerCase()))
          : true
      )
      .slice(0, 50); // Limiter à 50 pour performance
  }, [pianos, searchPiano]);

  // Si un piano est sélectionné depuis la table, pré-remplir
  React.useEffect(() => {
    if (selectedPiano) {
      setSelectedPianoId(selectedPiano.gazelleId);
      // Chercher si ce piano a déjà un mapping
      const existingMapping = mappings.find(
        (m) => m.gazelle_piano_id === selectedPiano.gazelleId
      );
      if (existingMapping) {
        setSelectedAbbreviation(existingMapping.piano_abbreviation);
      }
    }
  }, [selectedPiano, mappings]);

  const handleCreateMapping = async () => {
    if (!selectedAbbreviation || !selectedPianoId) {
      alert('Veuillez sélectionner une abréviation et un piano');
      return;
    }

    try {
      // Vérifier si l'abréviation est déjà mappée
      const existingMapping = mappings.find(
        (m) => m.piano_abbreviation === selectedAbbreviation
      );

      if (existingMapping) {
        // Mettre à jour le mapping existant
        await updateMapping(
          existingMapping.id,
          selectedPianoId,
          isUncertain,
          isUncertain ? uncertaintyNote : null
        );
      } else {
        // Créer un nouveau mapping
        const piano = pianos.find((p) => p.gazelleId === selectedPianoId);
        await createMapping(
          selectedAbbreviation,
          selectedPianoId,
          piano?.location,
          isUncertain,
          isUncertain ? uncertaintyNote : undefined
        );
      }

      // Reset form
      setIsUncertain(false);
      setUncertaintyNote('');
      onMappingComplete();
    } catch (err) {
      console.error('Error creating mapping:', err);
      alert('Erreur lors de la création du mapping');
    }
  };

  const handleDeleteMapping = async (abbreviation: string) => {
    const mapping = mappings.find((m) => m.piano_abbreviation === abbreviation);
    if (!mapping) return;

    if (!confirm(`Supprimer le mapping pour "${abbreviation}"?`)) return;

    try {
      await deleteMapping(mapping.id);
      onMappingComplete();
    } catch (err) {
      console.error('Error deleting mapping:', err);
      alert('Erreur lors de la suppression du mapping');
    }
  };

  const handleMarkUncertain = async (mappingId: string) => {
    const note = prompt('Note d\'incertitude (pourquoi ce mapping est incertain):');
    if (note === null) return; // User cancelled

    try {
      await updateMapping(mappingId, undefined, true, note);
      onMappingComplete();
    } catch (err) {
      console.error('Error marking uncertain:', err);
      alert('Erreur lors de la mise à jour');
    }
  };

  const handleMarkCertain = async (mappingId: string) => {
    try {
      await updateMapping(mappingId, undefined, false, null);
      onMappingComplete();
    } catch (err) {
      console.error('Error marking certain:', err);
      alert('Erreur lors de la mise à jour');
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      <div className="flex items-center justify-center min-h-screen px-4 pt-4 pb-20 text-center sm:block sm:p-0">
        {/* Backdrop */}
        <div
          className="fixed inset-0 transition-opacity bg-gray-500 bg-opacity-75"
          onClick={onClose}
        />

        {/* Modal */}
        <div className="inline-block align-bottom bg-white rounded-lg text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:max-w-6xl sm:w-full">
          {/* Header */}
          <div className="bg-blue-600 px-6 py-4">
            <h3 className="text-lg font-semibold text-white">
              🔗 Mapper Abréviations PDA ↔ Pianos Gazelle
            </h3>
            <p className="text-sm text-blue-100 mt-1">
              Jumelez les abréviations utilisées dans les demandes avec les vrais
              pianos de Gazelle
            </p>
          </div>

          {/* Content */}
          <div className="px-6 py-4">
            {/* Alerte abréviations non mappées */}
            {unmappedAbbreviations.length > 0 && (
              <div className="mb-4 bg-yellow-50 border-l-4 border-yellow-400 p-4">
                <div className="flex items-center">
                  <div className="flex-shrink-0">
                    <span className="text-yellow-400 text-2xl">⚠️</span>
                  </div>
                  <div className="ml-3">
                    <h4 className="text-yellow-800 font-semibold">
                      {unmappedAbbreviations.length} abréviation(s) non mappée(s)
                    </h4>
                    <p className="text-yellow-700 text-sm mt-1">
                      Ces abréviations sont utilisées dans les demandes mais ne sont
                      pas encore associées à un piano Gazelle.
                    </p>
                  </div>
                </div>
              </div>
            )}

            {/* Vue côte à côte */}
            <div className="grid grid-cols-2 gap-6">
              {/* Colonne gauche: Abréviations */}
              <div>
                <h4 className="text-sm font-semibold text-gray-700 mb-3">
                  Abréviations PDA
                </h4>

                <input
                  type="text"
                  placeholder="Rechercher abréviation..."
                  value={searchAbbreviation}
                  onChange={(e) => setSearchAbbreviation(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg mb-3 text-sm"
                />

                <div className="border border-gray-200 rounded-lg max-h-96 overflow-y-auto">
                  {unmappedAbbreviations.length === 0 ? (
                    <div className="p-4 text-center text-gray-500 text-sm">
                      Toutes les abréviations sont mappées! ✅
                    </div>
                  ) : (
                    <table className="w-full text-sm">
                      <thead className="bg-gray-50 sticky top-0">
                        <tr>
                          <th className="px-3 py-2 text-left text-xs font-semibold text-gray-700">
                            Abréviation
                          </th>
                          <th className="px-3 py-2 text-left text-xs font-semibold text-gray-700">
                            Demandes
                          </th>
                          <th className="px-3 py-2 text-left text-xs font-semibold text-gray-700">
                            Action
                          </th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-gray-200">
                        {unmappedAbbreviations.map((stat) => (
                          <tr
                            key={stat.abbreviation}
                            className={`
                              hover:bg-gray-50 cursor-pointer
                              ${
                                selectedAbbreviation === stat.abbreviation
                                  ? 'bg-blue-50'
                                  : ''
                              }
                            `}
                            onClick={() =>
                              setSelectedAbbreviation(stat.abbreviation)
                            }
                          >
                            <td className="px-3 py-2">
                              <span className="font-medium text-gray-900">
                                {stat.abbreviation}
                              </span>
                            </td>
                            <td className="px-3 py-2 text-gray-600">
                              {stat.request_count}
                            </td>
                            <td className="px-3 py-2">
                              <span className="text-yellow-600 text-xs">
                                ⚠️ Non mappé
                              </span>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  )}
                </div>
              </div>

              {/* Colonne droite: Pianos */}
              <div>
                <h4 className="text-sm font-semibold text-gray-700 mb-3">
                  Pianos Gazelle
                </h4>

                <input
                  type="text"
                  placeholder="Rechercher piano..."
                  value={searchPiano}
                  onChange={(e) => setSearchPiano(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg mb-3 text-sm"
                />

                <div className="border border-gray-200 rounded-lg max-h-96 overflow-y-auto">
                  {filteredPianos.length === 0 ? (
                    <div className="p-4 text-center text-gray-500 text-sm">
                      Aucun piano trouvé
                    </div>
                  ) : (
                    <table className="w-full text-sm">
                      <thead className="bg-gray-50 sticky top-0">
                        <tr>
                          <th className="px-3 py-2 text-left text-xs font-semibold text-gray-700">
                            Piano
                          </th>
                          <th className="px-3 py-2 text-left text-xs font-semibold text-gray-700">
                            Local
                          </th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-gray-200">
                        {filteredPianos.map((piano) => (
                          <tr
                            key={piano.gazelleId}
                            className={`
                              hover:bg-gray-50 cursor-pointer
                              ${
                                selectedPianoId === piano.gazelleId
                                  ? 'bg-blue-50'
                                  : ''
                              }
                            `}
                            onClick={() => setSelectedPianoId(piano.gazelleId)}
                          >
                            <td className="px-3 py-2">
                              <div>
                                <div className="font-medium text-gray-900">
                                  {piano.make}
                                </div>
                                {piano.model && (
                                  <div className="text-xs text-gray-500">
                                    {piano.model}
                                  </div>
                                )}
                              </div>
                            </td>
                            <td className="px-3 py-2 text-gray-600 text-xs">
                              {piano.location}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  )}
                </div>
              </div>
            </div>

            {/* Sélection actuelle */}
            {selectedAbbreviation && selectedPianoId && (
              <div className="mt-4 p-4 bg-blue-50 border border-blue-200 rounded-lg">
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm font-medium text-blue-900">
                        Mapping sélectionné:
                      </p>
                      <p className="text-sm text-blue-700 mt-1">
                        <span className="font-semibold">{selectedAbbreviation}</span>{' '}
                        ↔{' '}
                        <span className="font-semibold">
                          {
                            pianos.find((p) => p.gazelleId === selectedPianoId)
                              ?.make
                          }{' '}
                          ({pianos.find((p) => p.gazelleId === selectedPianoId)?.location})
                        </span>
                      </p>
                    </div>
                    <button
                      onClick={handleCreateMapping}
                      disabled={loading}
                      className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 text-sm font-medium"
                    >
                      {loading ? '⏳' : '✅'} Créer le mapping
                    </button>
                  </div>

                  {/* Option d'incertitude */}
                  <div className="border-t border-blue-200 pt-3">
                    <label className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={isUncertain}
                        onChange={(e) => {
                          setIsUncertain(e.target.checked);
                          if (!e.target.checked) setUncertaintyNote('');
                        }}
                        className="w-4 h-4"
                      />
                      <span className="text-sm text-orange-700 font-medium">
                        ⚠️ Marquer comme incertain (nécessite vérification)
                      </span>
                    </label>
                    {isUncertain && (
                      <textarea
                        placeholder="Note d'incertitude (ex: Plusieurs pianos possibles, localisation ambiguë...)"
                        value={uncertaintyNote}
                        onChange={(e) => setUncertaintyNote(e.target.value)}
                        className="mt-2 w-full px-3 py-2 border border-orange-300 rounded-lg text-sm focus:ring-2 focus:ring-orange-500 focus:border-transparent"
                        rows={2}
                      />
                    )}
                  </div>
                </div>
              </div>
            )}

            {/* Mappings existants */}
            {mappings.length > 0 && (
              <div className="mt-6">
                <h4 className="text-sm font-semibold text-gray-700 mb-3">
                  Mappings existants
                </h4>
                <div className="border border-gray-200 rounded-lg overflow-hidden">
                  <table className="w-full text-sm">
                    <thead className="bg-gray-50">
                      <tr>
                      <th className="px-3 py-2 text-left text-xs font-semibold text-gray-700">
                        Abréviation
                      </th>
                      <th className="px-3 py-2 text-left text-xs font-semibold text-gray-700">
                        Piano
                      </th>
                      <th className="px-3 py-2 text-left text-xs font-semibold text-gray-700">
                        Local
                      </th>
                      <th className="px-3 py-2 text-left text-xs font-semibold text-gray-700">
                        Statut
                      </th>
                      <th className="px-3 py-2 text-left text-xs font-semibold text-gray-700">
                        Action
                      </th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-200">
                      {mappings.map((mapping) => {
                        const piano = pianos.find(
                          (p) => p.gazelleId === mapping.gazelle_piano_id
                        );
                        return (
                          <tr
                            key={mapping.id}
                            className={`hover:bg-gray-50 ${
                              mapping.is_uncertain ? 'bg-orange-50' : ''
                            }`}
                          >
                            <td className="px-3 py-2">
                              <span className="font-medium text-gray-900">
                                {mapping.piano_abbreviation}
                              </span>
                            </td>
                            <td className="px-3 py-2 text-gray-600">
                              {piano?.make || 'Piano non trouvé'}
                            </td>
                            <td className="px-3 py-2 text-gray-600 text-xs">
                              {piano?.location || mapping.location || '-'}
                            </td>
                            <td className="px-3 py-2">
                              {mapping.is_uncertain ? (
                                <div className="flex items-center gap-1">
                                  <span className="text-orange-600 text-xs font-medium">
                                    ⚠️ Incertain
                                  </span>
                                  {mapping.uncertainty_note && (
                                    <span
                                      className="text-gray-400 cursor-help"
                                      title={mapping.uncertainty_note}
                                    >
                                      ℹ️
                                    </span>
                                  )}
                                </div>
                              ) : (
                                <span className="text-green-600 text-xs">✅ Confirmé</span>
                              )}
                            </td>
                            <td className="px-3 py-2">
                              <div className="flex gap-2">
                                {mapping.is_uncertain ? (
                                  <button
                                    onClick={() => handleMarkCertain(mapping.id)}
                                    className="text-green-600 hover:text-green-700 text-xs"
                                    title="Marquer comme certain"
                                  >
                                    ✅ Confirmer
                                  </button>
                                ) : (
                                  <button
                                    onClick={() => handleMarkUncertain(mapping.id)}
                                    className="text-orange-600 hover:text-orange-700 text-xs"
                                    title="Marquer comme incertain"
                                  >
                                    ⚠️ Incertain
                                  </button>
                                )}
                                <button
                                  onClick={() =>
                                    handleDeleteMapping(mapping.piano_abbreviation)
                                  }
                                  className="text-red-600 hover:text-red-700 text-xs"
                                >
                                  Supprimer
                                </button>
                              </div>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>

          {/* Footer */}
          <div className="bg-gray-50 px-6 py-4 flex justify-end gap-3">
            <button
              onClick={onClose}
              className="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition-colors text-sm font-medium"
            >
              Fermer
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default PianoMappingModal;

