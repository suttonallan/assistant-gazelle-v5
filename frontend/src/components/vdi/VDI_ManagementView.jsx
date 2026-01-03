/**
 * VDI_ManagementView - Vue de gestion des pianos pour Nicolas
 *
 * Fonctionnalités:
 * - Bannière de sélection de tournée
 * - Boutons de vue (Inventaire, Tout voir, Sélection)
 * - Filtres (usage, mois depuis accord)
 * - Actions batch (statut, usage, masquer)
 * - Tableau complet des pianos avec tri
 * - Édition inline (à faire, notes)
 * - Push vers Gazelle
 */

import React, { useState } from 'react';

export default function VDI_ManagementView({
  // État pianos
  pianosFiltres,
  pianos,
  setPianos,
  stats,

  // Tournées
  tournees,
  selectedTourneeId,
  setSelectedTourneeId,
  setShowOnlySelected,
  getTourneePianos,

  // Filtres
  showOnlySelected,
  showAllPianos,
  setShowAllPianos,
  filterUsage,
  setFilterUsage,
  filterAccordDepuis,
  setFilterAccordDepuis,
  usages,

  // Sélection
  selectedIds,
  setSelectedIds,
  selectAllCheckboxRef,

  // Actions
  loadPianosFromAPI,
  loading,
  selectAll,
  deselectAll,
  toggleProposed,
  toggleSelected,
  batchSetStatus,
  batchSetUsage,
  batchHideFromInventory,
  handlePushToGazelle,
  savePianoToAPI,

  // Push Gazelle
  readyForPushCount,
  pushInProgress,

  // Édition inline
  editingAFaireId,
  setEditingAFaireId,
  aFaireInput,
  setAFaireInput,
  editingNotesId,
  setEditingNotesId,
  notesInput,
  setNotesInput,

  // Tri
  sortConfig,
  handleSort,

  // Utilitaires
  getRowClass,
  moisDepuisAccord,
  formatDateRelative,
  getSyncStatusIcon,
  isPianoInTournee,
  filterEtage,
  setFilterEtage,
  currentUser
}) {
  // Vérification des données en haut du rendu
  if (pianos && !Array.isArray(pianos)) {
    console.error('Pianos is not an array:', pianos);
    return <div>Erreur: Format de données invalide</div>;
  }

  // État local pour l'édition du champ "Travail Effectué"
  const [editingTravailId, setEditingTravailId] = useState(null);
  const [travailInput, setTravailInput] = useState('');
  const [isWorkCompletedMap, setIsWorkCompletedMap] = useState(new Map());

  // Initialisation blindée: s'assurer que pianos est toujours un tableau
  const allPianos = Array.isArray(pianos) ? pianos : [];
  const allPianosFiltres = Array.isArray(pianosFiltres) ? pianosFiltres : [];

  // Vérifier si une tournée est active (pour afficher les boutons de complétion)
  const isTourneeActive = selectedTourneeId !== null;

  const SortIcon = ({ columnKey }) => {
    if (sortConfig.key !== columnKey) return <span className="text-gray-300 ml-1">⇅</span>;
    return <span className="text-blue-600 ml-1">{sortConfig.direction === 'asc' ? '▲' : '▼'}</span>;
  };

  const ColumnHeader = ({ columnKey, children }) => (
    <th
      onClick={() => handleSort(columnKey)}
      className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100 select-none"
    >
      <div className="flex items-center">
        {children}
        <SortIcon columnKey={columnKey} />
      </div>
    </th>
  );

  return (
    <div className="flex-1">
      {/* Barre d'outils - Nick */}
      <div className="bg-white rounded-lg shadow p-4 mb-4 space-y-3">
        {/* Header avec tournée sélectionnée */}
        {selectedTourneeId && (
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 mb-3">
            <div className="flex justify-between items-center">
              <div>
                <span className="text-sm font-medium text-blue-900">
                  🎹 Tournée: {tournees.find(t => t.id === selectedTourneeId)?.nom || 'Inconnue'}
                </span>
                <p className="text-xs text-blue-700 mt-1">
                  Sélectionnez les pianos à inclure dans cette tournée
                </p>
              </div>
              <button
                onClick={() => {
                  setSelectedTourneeId(null);
                  setShowOnlySelected(false);
                }}
                className="text-sm text-blue-600 hover:text-blue-800"
              >
                ✕ Désélectionner
              </button>
            </div>
          </div>
        )}

        {/* Boutons de vue */}
        <div className="flex gap-3 items-center flex-wrap">
          <button
            onClick={() => {
              setShowOnlySelected(false);
              setShowAllPianos(false);
            }}
            className={`px-4 py-2 rounded text-sm font-medium ${!showOnlySelected && !showAllPianos ? 'bg-blue-500 text-white' : 'bg-gray-100 hover:bg-gray-200'}`}
          >
            📦 Inventaire ({pianos.filter(p => p.isInCsv !== false).length})
          </button>
          <button
            onClick={() => {
              setShowOnlySelected(false);
              setShowAllPianos(true);
            }}
            className={`px-4 py-2 rounded text-sm font-medium ${!showOnlySelected && showAllPianos ? 'bg-purple-500 text-white' : 'bg-gray-100 hover:bg-gray-200'}`}
            title="Afficher tous les pianos (même ceux masqués de l'inventaire)"
          >
            📋 Tout voir ({stats.total})
          </button>
          <button
            onClick={() => {
              setShowOnlySelected(true);
              setShowAllPianos(false);
            }}
            className={`px-4 py-2 rounded text-sm font-medium ${showOnlySelected ? 'bg-blue-500 text-white' : 'bg-gray-100 hover:bg-gray-200'}`}
          >
            {selectedTourneeId ? (
              <>🎯 Pianos de cette tournée ({getTourneePianos(selectedTourneeId).length})</>
            ) : (
              <>🎯 Projet de tournée ({stats.proposed + stats.completed})</>
            )}
          </button>
          <button
            onClick={async () => {
              await loadPianosFromAPI();
            }}
            className="px-4 py-2 rounded text-sm font-medium bg-green-500 text-white hover:bg-green-600 disabled:opacity-50"
            disabled={loading}
            title="Rafraîchir les données depuis Gazelle"
          >
            {loading ? '⏳ Sync...' : '🔄 Sync Gazelle'}
          </button>
        </div>

        {/* Filtres */}
        <div className="flex gap-4 flex-wrap items-center border-t pt-3">
          <select value={filterUsage} onChange={(e) => setFilterUsage(e.target.value)} className="border rounded px-2 py-1 text-sm">
            <option value="all">Tous usages</option>
            {usages.map(u => <option key={u} value={u}>{u}</option>)}
            <option value="">Sans usage</option>
          </select>

          <select value={filterAccordDepuis} onChange={(e) => setFilterAccordDepuis(parseInt(e.target.value))} className="border rounded px-2 py-1 text-sm">
            <option value={0}>Tous</option>
            <option value={3}>3+ mois</option>
            <option value={6}>6+ mois</option>
            <option value={12}>12+ mois</option>
          </select>

          <select value={filterEtage} onChange={(e) => setFilterEtage(e.target.value)} className="border rounded px-2 py-1 text-sm">
            <option value="all">Tous étages</option>
            <option value="1">1er étage</option>
            <option value="2">2e étage</option>
            <option value="3">3e étage</option>
            <option value="4">4e étage</option>
            <option value="5">5e étage</option>
          </select>
        </div>

        {/* Actions multiples */}
        <div className="flex gap-3 flex-wrap items-center border-t pt-3">
          <button onClick={selectAll} className="px-3 py-1 rounded text-sm bg-gray-200 hover:bg-gray-300">☑ Tous</button>
          <button onClick={deselectAll} className="px-3 py-1 rounded text-sm bg-gray-200 hover:bg-gray-300">☐ Aucun</button>

          {/* Bouton Push vers Gazelle */}
          {readyForPushCount > 0 && (
            <button
              onClick={handlePushToGazelle}
              className="px-4 py-2 rounded text-sm font-medium bg-green-600 text-white hover:bg-green-700 disabled:opacity-50"
              disabled={pushInProgress}
            >
              {pushInProgress ? (
                '⏳ Envoi en cours...'
              ) : (
                `📤 Envoyer à Gazelle (${readyForPushCount})`
              )}
            </button>
          )}

          {selectedIds.size > 0 && (
            <>
              <span className="text-purple-600 font-medium text-sm">{selectedIds.size} sel.</span>
              <button onClick={() => batchSetStatus('top')} className="px-3 py-1 rounded text-sm bg-amber-400">→ Top</button>
              <button onClick={() => batchSetStatus('proposed')} className="px-3 py-1 rounded text-sm bg-yellow-400">→ À faire</button>
              <button onClick={() => batchSetStatus('normal')} className="px-3 py-1 rounded text-sm bg-white border">→ Retirer</button>
              <select onChange={(e) => { if (e.target.value) batchSetUsage(e.target.value); }} className="border rounded px-2 py-1 text-sm" value="">
                <option value="">Usage...</option>
                {usages.map(u => <option key={u} value={u}>{u}</option>)}
              </select>
              <button
                onClick={batchHideFromInventory}
                className="px-3 py-1 rounded text-sm bg-red-100 hover:bg-red-200 text-red-700 border border-red-300"
                title="Masquer les pianos sélectionnés de l'inventaire"
              >
                🚫 Masquer de l'inventaire
              </button>
            </>
          )}
        </div>
      </div>

      {/* Table */}
      <div className="bg-white rounded-lg shadow overflow-hidden">
        <table className="w-full">
          <thead>
            <tr className="bg-gray-50 border-b">
              <th className="px-2 py-3 w-10">
                <input
                  ref={selectAllCheckboxRef}
                  type="checkbox"
                  onChange={(e) => e.target.checked ? selectAll() : deselectAll()}
                  className="rounded"
                />
              </th>
              <ColumnHeader columnKey="local">Local</ColumnHeader>
              <ColumnHeader columnKey="piano">Piano</ColumnHeader>
              <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase"># Série</th>
              <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase">Usage</th>
              <ColumnHeader columnKey="mois">Mois</ColumnHeader>
              <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase">Sync</th>
              <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase bg-yellow-50">À faire (Nick)</th>
              <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase bg-blue-50">Travail Effectué</th>
              <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                Statut
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {allPianosFiltres.map((piano) => {
              const mois = moisDepuisAccord(piano?.dernierAccord);

              return (
                <tr
                  key={piano.id}
                  className={`${getRowClass(piano)} hover:opacity-80`}
                >
                  <td className="px-2 py-3 text-center">
                    <input
                      type="checkbox"
                      checked={selectedIds.has(piano.id)}
                      onChange={() => toggleSelected(piano.id)}
                      className="rounded"
                    />
                  </td>
                  <td className="px-3 py-3 text-sm font-medium">{piano.local}</td>
                  <td className="px-3 py-3 text-sm">{piano.piano}</td>
                  <td className="px-3 py-3 text-sm text-gray-500 font-mono">{piano.serie}</td>
                  <td className="px-3 py-3 text-sm text-gray-500">{piano.usage || '-'}</td>
                  <td className={`px-3 py-3 text-sm font-medium ${mois === 999 ? 'text-gray-400' : mois >= 12 ? 'text-red-600' : mois >= 6 ? 'text-orange-500' : 'text-green-600'}`}>
                    {piano?.dernierAccord ? formatDateRelative(piano.dernierAccord) : 'N/A'}
                  </td>

                  {/* Colonne Sync Status */}
                  <td className="px-3 py-3 text-sm">
                    {piano.sync_status && (
                      <span title={`Sync: ${piano.sync_status}`} className="text-lg">
                        {getSyncStatusIcon(piano.sync_status)}
                      </span>
                    )}
                  </td>

                  {/* Colonne "À faire" de Nick */}
                  <td className="px-3 py-3 bg-yellow-50" onClick={(e) => e.stopPropagation()}>
                    {editingAFaireId === piano.id ? (
                      <input
                        type="text"
                        value={aFaireInput}
                        onChange={(e) => setAFaireInput(e.target.value)}
                        onKeyDown={async (e) => {
                          if (e.key === 'Enter') {
                            // Mise à jour optimiste
                            setPianos(allPianos.map(p =>
                              p.id === piano.id ? { ...p, aFaire: aFaireInput } : p
                            ));
                            setEditingAFaireId(null);
                            setAFaireInput('');
                            // Sauvegarder via API
                            await savePianoToAPI(piano.id, { aFaire: aFaireInput });
                          }
                        }}
                        onBlur={async () => {
                          // Mise à jour optimiste
                          setPianos(allPianos.map(p =>
                            p.id === piano.id ? { ...p, aFaire: aFaireInput } : p
                          ));
                          setEditingAFaireId(null);
                          const valueToSave = aFaireInput;
                          setAFaireInput('');
                          // Sauvegarder via API
                          await savePianoToAPI(piano.id, { aFaire: valueToSave });
                        }}
                        className="border rounded px-2 py-1 text-sm w-full"
                        placeholder="Instructions..."
                        autoFocus
                      />
                    ) : (
                      <span
                        className="text-sm cursor-text"
                        onClick={() => { setEditingAFaireId(piano.id); setAFaireInput(piano.aFaire || ''); }}
                      >
                        {piano.aFaire || <span className="text-gray-400">Cliquer...</span>}
                      </span>
                    )}
                  </td>

                  {/* Colonne Travail Effectué */}
                  <td className="px-3 py-3 bg-blue-50" onClick={(e) => e.stopPropagation()}>
                    {editingTravailId === piano.id ? (
                      <div className="space-y-2">
                        <textarea
                          value={travailInput}
                          onChange={(e) => setTravailInput(e.target.value)}
                          onBlur={async () => {
                            try {
                              const travailValue = travailInput.trim();
                              setPianos(allPianos.map(p =>
                                p.id === piano.id ? { ...p, travail: travailValue } : p
                              ));
                              setEditingTravailId(null);
                              setTravailInput('');
                              await savePianoToAPI(piano.id, { travail: travailValue });
                            } catch (err) {
                              console.error('Erreur sauvegarde travail:', err);
                              alert(`Erreur lors de la sauvegarde: ${err.message}`);
                              setEditingTravailId(piano.id);
                              setTravailInput(travailInput);
                            }
                          }}
                          className="border rounded px-2 py-1 text-xs w-full"
                          placeholder="Travail effectué (accord, réglages...)"
                          rows="3"
                          autoFocus
                        />
                        {isTourneeActive && (
                          <div className="space-y-1">
                            <label className="flex items-center gap-1 text-xs">
                              <input
                                type="checkbox"
                                checked={isWorkCompletedMap.get(piano.id) || false}
                                onChange={(e) => {
                                  const newMap = new Map(isWorkCompletedMap);
                                  newMap.set(piano.id, e.target.checked);
                                  setIsWorkCompletedMap(newMap);
                                }}
                                className="rounded"
                              />
                              <span>Travail complété / Prêt pour Gazelle</span>
                            </label>
                            <button
                              onClick={async () => {
                                const isCompleted = isWorkCompletedMap.get(piano.id) || false;
                                if (!isCompleted) {
                                  alert('Veuillez cocher "Travail complété" avant de pousser vers Gazelle');
                                  return;
                                }
                                try {
                                  // Sauvegarder travail et is_work_completed
                                  await savePianoToAPI(piano.id, {
                                    travail: travailInput.trim(),
                                    is_work_completed: true,
                                    status: 'completed'
                                  });
                                  
                                  // Mise à jour optimiste
                                  setPianos(allPianos.map(p =>
                                    p.id === piano.id ? {
                                      ...p,
                                      travail: travailInput.trim(),
                                      is_work_completed: true,
                                      status: 'completed'
                                    } : p
                                  ));
                                  
                                  // Push vers Gazelle
                                  // Déterminer le nom du technicien depuis currentUser
                                  let technicianName = 'Nicolas'; // Défaut
                                  try {
                                    if (currentUser) {
                                      // Essayer de déterminer le nom depuis currentUser
                                      if (currentUser.name) {
                                        technicianName = currentUser.name;
                                      } else if (currentUser.email) {
                                        // Mapper email vers nom de technicien si nécessaire
                                        const email = (currentUser.email || '').toLowerCase();
                                        if (email.includes('nicolas') || email.includes('lessard')) {
                                          technicianName = 'Nicolas';
                                        } else if (email.includes('allan') || email.includes('sutton')) {
                                          technicianName = 'Allan';
                                        }
                                      }
                                    }
                                  } catch (err) {
                                    console.error('Erreur détermination nom technicien:', err);
                                    technicianName = 'Nicolas'; // Fallback sûr
                                  }
                                  
                                  const apiUrl = import.meta.env.VITE_API_URL || (import.meta.env.DEV ? '' : 'https://assistant-gazelle-v5-api.onrender.com');
                                  const response = await fetch(
                                    `${apiUrl}/api/vincent-dindy/pianos/${piano.id}/complete-service?technician_name=${encodeURIComponent(technicianName)}&auto_push=true`,
                                    { method: 'POST' }
                                  );
                                  
                                  if (!response.ok) {
                                    const error = await response.json();
                                    throw new Error(error.detail || 'Erreur lors du push vers Gazelle');
                                  }
                                  
                                  const result = await response.json();
                                  // Fermer l'édition
                                  setEditingTravailId(null);
                                  setTravailInput('');
                                  setIsWorkCompletedMap(prev => {
                                    const newMap = new Map(prev);
                                    newMap.delete(piano.id);
                                    return newMap;
                                  });
                                  
                                  // Recharger les données
                                  await loadPianosFromAPI();
                                  
                                  alert('✅ Travail sauvegardé et poussé vers Gazelle!');
                                } catch (err) {
                                  console.error('❌ Erreur:', err);
                                  alert(`Erreur: ${err.message}`);
                                }
                              }}
                              className="w-full px-2 py-1 bg-green-500 text-white text-xs rounded hover:bg-green-600"
                            >
                              Sauvegarder & Push
                            </button>
                          </div>
                        )}
                      </div>
                    ) : (
                      <span
                        className="text-xs cursor-text block whitespace-pre-wrap"
                        onClick={() => {
                          setEditingTravailId(piano.id);
                          setTravailInput(piano.travail || '');
                          setIsWorkCompletedMap(prev => {
                            const newMap = new Map(prev);
                            newMap.set(piano.id, piano.is_work_completed || false);
                            return newMap;
                          });
                        }}
                      >
                        {piano.travail || <span className="text-gray-400">Cliquer...</span>}
                      </span>
                    )}
                  </td>

                  {/* Colonne Statut - Cliquer pour changer */}
                  <td
                    className="px-3 py-3 text-sm cursor-pointer"
                    onClick={() => toggleProposed(piano.id)}
                    title="Cliquer pour changer le statut (Normal → À faire → Complété → Normal)"
                  >
                    {piano.status === 'top' && <span className="px-2 py-1 bg-amber-400 rounded text-xs font-medium">Top</span>}
                    {piano.status === 'proposed' && <span className="px-2 py-1 bg-yellow-400 rounded text-xs">À faire</span>}
                    {piano.status === 'completed' && <span className="px-2 py-1 bg-green-400 rounded text-xs">Complété</span>}
                    {piano.status === 'normal' && <span className="text-gray-400">-</span>}
                  </td>
                </tr>
              );
            })}
        </tbody>
        </table>

        {allPianosFiltres.length === 0 && (
          <div className="p-8 text-center text-gray-500">Aucun piano.</div>
        )}
      </div>

      {/* Légende */}
      <div className="mt-4 bg-white rounded-lg shadow p-3 flex gap-4 text-sm flex-wrap">
        <span key="legend-normal" className="flex items-center gap-1"><span className="w-3 h-3 bg-white border rounded"></span> Normal</span>
        <span key="legend-top" className="flex items-center gap-1"><span className="w-3 h-3 bg-amber-200 rounded"></span> Top (priorité élevée)</span>
        <span key="legend-proposed" className="flex items-center gap-1"><span className="w-3 h-3 bg-yellow-200 rounded"></span> À faire</span>
        <span key="legend-work-in-progress" className="flex items-center gap-1"><span className="w-3 h-3 bg-blue-200 rounded"></span> Travail en cours</span>
        <span key="legend-completed" className="flex items-center gap-1"><span className="w-3 h-3 bg-green-200 rounded"></span> Complété</span>
        <span key="legend-sync-pending" className="flex items-center gap-1">⏳ En attente</span>
        <span key="legend-sync-pushed" className="flex items-center gap-1">✅ Envoyé</span>
        <span key="legend-sync-modified" className="flex items-center gap-1">🔄 Modifié</span>
        <span key="legend-sync-error" className="flex items-center gap-1">⚠️ Erreur</span>
      </div>
    </div>
  );
}
