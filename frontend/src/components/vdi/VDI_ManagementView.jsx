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

import React, { useState, useCallback, useMemo } from 'react';
import { getUserRole } from '../../config/roles';
import PianoTimelineModal, { ClockIcon } from './PianoTimelineModal';

// Configuration de l'API
const API_URL = import.meta.env.VITE_API_URL || (import.meta.env.DEV ? '' : 'https://assistant-gazelle-v5-api.onrender.com');

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
  savePianoToAPI,
  removePianoFromTournee,

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
  setFilterEtage,

  // Sync Gazelle
  handlePushToGazelle,
  readyForPushCount,
  pushInProgress
}) {

  // Liste plate des SERVICES validés prêts à pousser (un piano peut en avoir
  // plusieurs le même jour via le bouton « Nouveau service » : fiche active
  // validée + fiches figées validées). C'est ce que le push enverra.
  const servicesAPousser = useMemo(() => {
    const out = [];
    (pianos || []).forEach(p => {
      const pianoLabel = `${p.piano || ''}${p.modele ? ` ${p.modele}` : ''}`.trim();
      const sr = p.service_record;
      if (sr && sr.status === 'validated') {
        out.push({ key: sr.id || `${p.id}-active`, local: p.local, piano: pianoLabel, travail: p.travail || '', frozen: false });
      }
      (p.frozen_records || []).forEach(fr => {
        if (fr.status === 'validated') {
          out.push({ key: fr.id, local: p.local, piano: pianoLabel, travail: fr.travail || '', frozen: true });
        }
      });
    });
    return out;
  }, [pianos]);

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

  // --- Timeline / Historique d'entretien ---
  // La modale est un composant partagé (PianoTimelineModal) : la vue TECHNICIEN
  // ouvre exactement la même, avec la même icône horloge. Ici on ne garde que
  // le piano sélectionné ; chargement, tri et filtres vivent dans le composant.
  const [timelinePiano, setTimelinePiano] = useState(null);

  const openTimeline = useCallback((piano) => setTimelinePiano(piano), []);

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
                setShowAllPianos(!showAllPianos);
              }}
              className={`px-4 py-2 rounded text-sm font-medium ${!showOnlySelected && showAllPianos ? 'bg-purple-500 text-white' : 'bg-gray-100 hover:bg-gray-200'}`}
              title={showAllPianos ? "Filtrer pour masquer les pianos cachés" : "Afficher tous les pianos (même ceux masqués de l'inventaire)"}
            >
              {showAllPianos ? `🔽 Filtrer (${pianos.filter(p => !p.is_hidden).length})` : `📋 Tout voir (${stats.total})`}
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
          {handlePushToGazelle && (
            <button
              onClick={handlePushToGazelle}
              className={`px-4 py-2 rounded text-sm font-medium ${
                readyForPushCount > 0
                  ? 'bg-green-500 text-white hover:bg-green-600'
                  : 'bg-gray-100 text-gray-400 cursor-not-allowed'
              } disabled:opacity-50`}
              disabled={pushInProgress || readyForPushCount === 0}
              title={servicesAPousser.length > 0 ? `Envoyer ${servicesAPousser.length} service(s) vers Gazelle` : 'Aucun service à synchroniser'}
            >
              {pushInProgress ? 'Envoi...' : `Sync Gazelle${servicesAPousser.length > 0 ? ` (${servicesAPousser.length})` : ''}`}
            </button>
          )}
        </div>

        {/* Services validés prêts à pousser — un par un (un piano peut en avoir
            plusieurs le même jour). Donne la visibilité avant le Sync. */}
        {servicesAPousser.length > 0 && (
          <div className="mt-3 border-t pt-3">
            <div className="text-sm font-semibold text-gray-700 mb-2">
              {servicesAPousser.length} service(s) à pousser
            </div>
            <div className="space-y-1">
              {servicesAPousser.map(s => (
                <div key={s.key} className="text-sm bg-green-50 border border-green-200 rounded px-2.5 py-1.5 flex items-start gap-2">
                  <span className="font-semibold text-gray-700 shrink-0">{s.local}</span>
                  <span className="text-gray-600 shrink-0">{s.piano}</span>
                  <span className="text-gray-700 flex-1">{s.travail || '(sans note)'}</span>
                  {s.frozen && (
                    <span className="text-xs text-emerald-700 bg-emerald-100 border border-emerald-300 rounded-full px-1.5 py-0.5 shrink-0">figé</span>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

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

          {selectedIds.size > 0 && (
            <>
              <span className="text-purple-600 font-medium text-sm">{selectedIds.size} sel.</span>
              <button 
                onClick={() => batchSetStatus('top')} 
                className="px-3 py-1 rounded text-sm bg-orange-400 hover:bg-orange-500"
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
              <button
                onClick={() => batchSetStatus('normal')}
                className="px-3 py-1 rounded text-sm bg-gray-300 hover:bg-gray-400"
                title="Retirer l'étiquette « à faire » des pianos sélectionnés (remettre à normal)"
              >
                Enlever « à faire »
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
              <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase bg-yellow-50">Note</th>
              {showAllPianos && (
                <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Visible
                </th>
              )}
              <th className="px-3 py-3 text-center text-xs font-medium text-gray-500 uppercase w-12">
                Hist.
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
                      <div className="flex items-center gap-1">
                        <span
                          className="text-sm cursor-text flex-1"
                          onClick={() => { setEditingAFaireId(piano.id); setAFaireInput(piano.aFaire || ''); }}
                        >
                          {piano.aFaire || <span className="text-gray-400">Cliquer...</span>}
                        </span>
                        {piano.aFaire && (
                          <button
                            onClick={async (e) => {
                              e.stopPropagation();
                              setPianos(pianos.map(p => p.id === piano.id ? { ...p, aFaire: '' } : p));
                              await savePianoToAPI(piano.id, { aFaire: '' });
                            }}
                            className="text-gray-400 hover:text-red-500 text-xs flex-shrink-0"
                            title="Effacer"
                          >✕</button>
                        )}
                      </div>
                    )}
                  </td>

                  {/* Colonne Visible - seulement en mode "Tout voir" */}
                  {showAllPianos && (
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
                  )}

                  {/* Bouton historique */}
                  <td className="px-3 py-3 text-center" onClick={(e) => e.stopPropagation()}>
                    <button
                      onClick={() => openTimeline(piano)}
                      className="text-gray-400 hover:text-blue-600 transition-colors"
                      title="Voir l'historique d'entretien"
                    >
                      <ClockIcon />
                    </button>
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
        <span key="legend-top" className="flex items-center gap-1"><span className="w-3 h-3 bg-orange-200 rounded"></span> Top (priorité)</span>
        <span key="legend-pushed" className="flex items-center gap-1"><span className="w-3 h-3 bg-green-100 rounded"></span> Poussé &lt; 21 jours</span>
      </div>

      {/* Modal historique d'entretien — tableur */}
      <PianoTimelineModal
        piano={timelinePiano}
        institution={institution || 'vincent-dindy'}
        onClose={() => setTimelinePiano(null)}
      />
    </div>
  );
}
