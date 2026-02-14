/**
 * VDI_ManagementView - Vue de gestion des pianos pour Nicolas
 *
 * Fonctionnalités:
 * - Bannière de sélection de tournée
 * - Boutons de vue (Inventaire, Tout voir, Sélection)
 * - Filtres (usage, mois depuis accord, étage)
 * - Actions batch (statut, usage, masquer)
 * - Tableau compact des pianos avec tri
 * - Édition inline (à faire)
 * - Push vers Gazelle
 */

import React from 'react';
import { getUserRole } from '../../config/roles';

export default function VDI_ManagementView({
  // État pianos
  pianosFiltres,
  pianos,
  setPianos,
  stats,

  // Institution
  institution,

  // Utilisateur
  currentUser,

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
  removePianoFromTournee,

  // Push Gazelle
  readyForPushCount,
  pushInProgress,

  // Édition inline
  editingAFaireId,
  setEditingAFaireId,
  aFaireInput,
  setAFaireInput,

  // Tri
  sortConfig,
  handleSort,

  // Utilitaires
  getRowClass,
  moisDepuisAccord,
  formatDateRelative,
  isPianoInTournee,
  filterEtage,
  setFilterEtage
}) {

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
            📦 Inventaire ({pianos.filter(p => !p.is_hidden).length})
          </button>
          {/* Mode Gestion de Parc (Tout voir) - Réservé Admin/Nicolas seulement */}
          {(getUserRole(currentUser?.email) === 'admin' || getUserRole(currentUser?.email) === 'nick') && (
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
          )}
          <button
            onClick={() => {
              setShowOnlySelected(true);
              setShowAllPianos(false);
            }}
            className={`px-4 py-2 rounded text-sm font-medium ${showOnlySelected ? 'bg-blue-500 text-white' : 'bg-gray-100 hover:bg-gray-200'}`}
          >
            {selectedTourneeId ? (
              <>🎯 Pianos de cette tournée ({pianos.filter(p => isPianoInTournee(p, selectedTourneeId) && (!p.is_hidden || showAllPianos)).length})</>
            ) : (
              <>🎯 Projet de tournée ({stats.proposed + stats.completed})</>
            )}
          </button>
          <button
            onClick={async () => {
              await loadPianosFromAPI();
            }}
            className="px-3 py-2 rounded text-sm font-medium bg-gray-100 hover:bg-gray-200 disabled:opacity-50"
            disabled={loading}
            title="Rafraîchir les données"
          >
            {loading ? '⏳...' : '🔄'}
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
              <button 
                onClick={() => batchSetStatus('top')} 
                className="px-3 py-1 rounded text-sm bg-amber-400 hover:bg-amber-500"
                title="Marquer les pianos sélectionnés comme priorité élevée"
              >
                → Top
              </button>
              <button 
                onClick={() => batchSetStatus('proposed')} 
                className="px-3 py-1 rounded text-sm bg-yellow-400 hover:bg-yellow-500"
                title="Marquer les pianos sélectionnés comme à faire"
              >
                → À faire
              </button>
              <select onChange={(e) => { if (e.target.value) batchSetUsage(e.target.value); }} className="border rounded px-2 py-1 text-sm" value="">
                <option value="">Usage...</option>
                {usages.map(u => <option key={u} value={u}>{u}</option>)}
              </select>
              {/* Mode Gestion de Parc (is_hidden) - Réservé Admin/Nicolas seulement */}
              {(getUserRole(currentUser?.email) === 'admin' || getUserRole(currentUser?.email) === 'nick') && (
                <button
                  onClick={batchHideFromInventory}
                  className="px-3 py-1 rounded text-sm bg-red-100 hover:bg-red-200 text-red-700 border border-red-300"
                  title="Masquer les pianos sélectionnés de l'inventaire"
                >
                  🚫 Masquer sel.
                </button>
              )}
              <button
                onClick={async () => {
                  if (selectedIds.size === 0) return;
                  // Batch show selected pianos
                  for (const pianoId of Array.from(selectedIds)) {
                    const piano = pianos.find(p => p.id === pianoId);
                    if (piano && piano.is_hidden) {
                      await savePianoToAPI(pianoId, { isHidden: false });
                    }
                  }
                  await loadPianosFromAPI();
                  deselectAll();
                }}
                className="px-3 py-1 rounded text-sm bg-green-100 hover:bg-green-200 text-green-700 border border-green-300"
                title="Afficher les pianos sélectionnés dans l'inventaire"
              >
                👁️ Afficher sel.
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
              <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase bg-yellow-50">À faire (Nick)</th>
              <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                Visible
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {pianosFiltres.map((piano) => {
              const mois = moisDepuisAccord(piano.dernierAccord);

              return (
                <tr
                  key={piano.id}
                  className={`${getRowClass(piano)} cursor-pointer hover:opacity-80`}
                  onClick={() => toggleProposed(piano.id)}
                >
                  <td className="px-2 py-3 text-center" onClick={(e) => e.stopPropagation()}>
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
                    {formatDateRelative(piano.dernierAccord)}
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
                            setPianos(pianos.map(p =>
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
                          setPianos(pianos.map(p =>
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

                  {/* Colonne Visible - simple checkbox */}
                  <td className="px-3 py-3 text-center" onClick={(e) => e.stopPropagation()}>
                    <input
                      type="checkbox"
                      checked={!piano.is_hidden}
                      onChange={async () => {
                        const newIsHidden = !piano.is_hidden;
                        setPianos(pianos.map(p =>
                          p.id === piano.id ? { ...p, is_hidden: newIsHidden } : p
                        ));
                        await savePianoToAPI(piano.id, { isHidden: newIsHidden });
                      }}
                      className="rounded"
                      title={piano.is_hidden ? 'Masqué — cocher pour afficher' : 'Visible — décocher pour masquer'}
                    />
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>

        {pianosFiltres.length === 0 && (
          <div className="p-8 text-center text-gray-500">Aucun piano.</div>
        )}
      </div>

      {/* Légende */}
      <div className="mt-4 bg-white rounded-lg shadow p-3 flex gap-4 text-sm flex-wrap">
        <span key="legend-normal" className="flex items-center gap-1"><span className="w-3 h-3 bg-white border rounded"></span> Normal</span>
        <span key="legend-proposed" className="flex items-center gap-1"><span className="w-3 h-3 bg-yellow-200 rounded"></span> À faire</span>
        <span key="legend-top" className="flex items-center gap-1"><span className="w-3 h-3 bg-amber-200 rounded"></span> Top (priorité)</span>
      </div>
    </div>
  );
}
