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

import React, { useState, useCallback } from 'react';
import { getUserRole } from '../../config/roles';

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
  const [timelinePiano, setTimelinePiano] = useState(null); // piano object when modal is open
  const [timelineEntries, setTimelineEntries] = useState([]);
  const [timelineLoading, setTimelineLoading] = useState(false);
  const [tlSort, setTlSort] = useState({ key: 'date', dir: 'desc' });
  const [tlFilter, setTlFilter] = useState('');
  const [tlTypeFilter, setTlTypeFilter] = useState('all');

  const openTimeline = useCallback(async (piano) => {
    setTimelinePiano(piano);
    setTimelineEntries([]);
    setTimelineLoading(true);
    try {
      const inst = institution || 'vincent-dindy';
      const r = await fetch(`${API_URL}/api/${inst}/pianos/${piano.id}/timeline?limit=200`);
      if (r.ok) {
        const data = await r.json();
        setTimelineEntries(data.entries || []);
      }
    } catch (e) {
      console.error('Erreur chargement timeline:', e);
    } finally {
      setTimelineLoading(false);
    }
  }, []);

  // Badge type timeline
  const TimelineTypeBadge = ({ type, source }) => {
    const cfg = {
      APPOINTMENT:             { bg: 'bg-blue-100',   text: 'text-blue-700',   label: 'RDV' },
      SERVICE:                 { bg: 'bg-green-100',  text: 'text-green-700',  label: source === 'local' ? 'Service (local)' : 'Service' },
      SERVICE_ENTRY_MANUAL:    { bg: 'bg-green-100',  text: 'text-green-700',  label: 'Service' },
      SERVICE_ENTRY_AUTOMATED: { bg: 'bg-green-100',  text: 'text-green-700',  label: 'Facture/Service' },
      USER_COMMENT:            { bg: 'bg-yellow-100', text: 'text-yellow-700', label: 'Note' },
      PIANO_MEASUREMENT:       { bg: 'bg-cyan-100',   text: 'text-cyan-700',   label: 'Mesure' },
      INVOICE:                 { bg: 'bg-purple-100', text: 'text-purple-700', label: 'Facture' },
      INVOICE_LOG:             { bg: 'bg-purple-100', text: 'text-purple-700', label: 'Facture' },
      ESTIMATE:                { bg: 'bg-orange-100', text: 'text-orange-700', label: 'Devis' },
      ESTIMATE_LOG:            { bg: 'bg-orange-100', text: 'text-orange-700', label: 'Devis' },
    };
    const c = cfg[type] || { bg: 'bg-gray-100', text: 'text-gray-600', label: type || '?' };
    return (
      <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold ${c.bg} ${c.text}`}>
        {c.label}
      </span>
    );
  };

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
          {handlePushToGazelle && (
            <button
              onClick={handlePushToGazelle}
              className={`px-4 py-2 rounded text-sm font-medium ${
                readyForPushCount > 0
                  ? 'bg-green-500 text-white hover:bg-green-600'
                  : 'bg-gray-100 text-gray-400 cursor-not-allowed'
              } disabled:opacity-50`}
              disabled={pushInProgress || readyForPushCount === 0}
              title={readyForPushCount > 0 ? `Envoyer ${readyForPushCount} piano(s) vers Gazelle` : 'Aucun piano à synchroniser'}
            >
              {pushInProgress ? '⏳ Envoi...' : `Sync Gazelle${readyForPushCount > 0 ? ` (${readyForPushCount})` : ''}`}
            </button>
          )}
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
              <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                Visible
              </th>
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

                  {/* Bouton historique */}
                  <td className="px-3 py-3 text-center" onClick={(e) => e.stopPropagation()}>
                    <button
                      onClick={() => openTimeline(piano)}
                      className="text-gray-400 hover:text-blue-600 transition-colors"
                      title="Voir l'historique d'entretien"
                    >
                      <svg className="w-4 h-4 inline" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
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
      </div>

      {/* Modal historique d'entretien — tableur */}
      {timelinePiano && (() => {
        // Type labels for filter dropdown
        const typeLabels = {
          SERVICE_ENTRY_MANUAL: 'Service',
          SERVICE_ENTRY_AUTOMATED: 'Facture/Service',
          SERVICE: 'Service (local)',
          PIANO_MEASUREMENT: 'Mesure',
          USER_COMMENT: 'Note',
          APPOINTMENT: 'RDV',
          INVOICE: 'Facture',
          INVOICE_LOG: 'Facture',
          ESTIMATE: 'Devis',
          ESTIMATE_LOG: 'Devis',
        };

        // Unique types in data
        const uniqueTypes = [...new Set(timelineEntries.map(e => e.type))];

        // Combined text for search
        const getText = (e) => [e.summary, e.comment, e.user, e.invoice_number].filter(Boolean).join(' ').toLowerCase();

        // Filter
        const filtered = timelineEntries.filter(e => {
          if (tlTypeFilter !== 'all' && e.type !== tlTypeFilter) return false;
          if (tlFilter && !getText(e).includes(tlFilter.toLowerCase())) return false;
          return true;
        });

        // Sort
        const sorted = [...filtered].sort((a, b) => {
          let va, vb;
          switch (tlSort.key) {
            case 'date': va = a.date || ''; vb = b.date || ''; break;
            case 'type': va = typeLabels[a.type] || a.type || ''; vb = typeLabels[b.type] || b.type || ''; break;
            case 'user': va = a.user || ''; vb = b.user || ''; break;
            default: va = ''; vb = '';
          }
          const cmp = typeof va === 'string' ? va.localeCompare(vb) : va - vb;
          return tlSort.dir === 'asc' ? cmp : -cmp;
        });

        const toggleSort = (key) => {
          setTlSort(prev => prev.key === key
            ? { key, dir: prev.dir === 'asc' ? 'desc' : 'asc' }
            : { key, dir: key === 'date' ? 'desc' : 'asc' }
          );
        };

        const SortArrow = ({ col }) => {
          if (tlSort.key !== col) return <span className="text-gray-300 ml-0.5">⇅</span>;
          return <span className="text-blue-600 ml-0.5">{tlSort.dir === 'asc' ? '▲' : '▼'}</span>;
        };

        const formatDate = (d) => d ? new Date(d).toLocaleDateString('fr-CA', { year: 'numeric', month: 'short', day: 'numeric' }) : '-';

        return (
          <div className="fixed inset-0 bg-black/40 z-50 flex items-start justify-center pt-8 px-4">
            <div className="bg-white rounded-xl shadow-2xl w-full max-w-5xl max-h-[85vh] flex flex-col">
              {/* Header */}
              <div className="flex items-center justify-between px-5 py-3 border-b bg-gray-50 rounded-t-xl">
                <div>
                  <h3 className="text-base font-bold text-gray-900">
                    Historique — {timelinePiano.local}
                  </h3>
                  <p className="text-xs text-gray-500">
                    {timelinePiano.piano}{timelinePiano.modele ? ` ${timelinePiano.modele}` : ''} — {timelinePiano.serie}
                    <span className="ml-2 text-gray-400">({filtered.length} entrée{filtered.length > 1 ? 's' : ''})</span>
                  </p>
                </div>
                <button
                  onClick={() => { setTimelinePiano(null); setTlFilter(''); setTlTypeFilter('all'); }}
                  className="text-gray-400 hover:text-gray-700 text-xl leading-none px-2"
                >
                  &times;
                </button>
              </div>

              {/* Filtres */}
              <div className="flex items-center gap-3 px-5 py-2 border-b bg-white">
                <input
                  type="text"
                  placeholder="Rechercher..."
                  value={tlFilter}
                  onChange={(e) => setTlFilter(e.target.value)}
                  className="border border-gray-300 rounded px-2.5 py-1.5 text-xs w-56 focus:outline-none focus:ring-1 focus:ring-blue-400"
                />
                <select
                  value={tlTypeFilter}
                  onChange={(e) => setTlTypeFilter(e.target.value)}
                  className="border border-gray-300 rounded px-2 py-1.5 text-xs bg-white focus:outline-none focus:ring-1 focus:ring-blue-400"
                >
                  <option value="all">Tous les types</option>
                  {uniqueTypes.map(t => (
                    <option key={t} value={t}>{typeLabels[t] || t}</option>
                  ))}
                </select>
              </div>

              {/* Tableau */}
              <div className="flex-1 overflow-auto">
                {timelineLoading ? (
                  <div className="text-center py-8 text-gray-500">Chargement...</div>
                ) : sorted.length === 0 ? (
                  <div className="text-center py-8 text-gray-500">
                    {timelineEntries.length === 0 ? 'Aucun historique.' : 'Aucun résultat pour ce filtre.'}
                  </div>
                ) : (
                  <table className="w-full text-xs">
                    <thead className="sticky top-0 bg-gray-50 z-10">
                      <tr className="border-b text-left text-[10px] font-semibold text-gray-500 uppercase">
                        <th className="px-3 py-2 w-28 cursor-pointer select-none" onClick={() => toggleSort('date')}>
                          Date <SortArrow col="date" />
                        </th>
                        <th className="px-3 py-2 w-28 cursor-pointer select-none" onClick={() => toggleSort('type')}>
                          Type <SortArrow col="type" />
                        </th>
                        <th className="px-3 py-2 w-32 cursor-pointer select-none" onClick={() => toggleSort('user')}>
                          Technicien <SortArrow col="user" />
                        </th>
                        <th className="px-3 py-2">Description</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-100">
                      {sorted.map((entry, idx) => (
                        <tr
                          key={entry.id || idx}
                          className={`hover:bg-blue-50/50 ${
                            entry.source === 'local' ? 'bg-green-50/30' : ''
                          }`}
                        >
                          <td className="px-3 py-2 text-gray-600 whitespace-nowrap align-top">
                            {formatDate(entry.date)}
                          </td>
                          <td className="px-3 py-2 align-top">
                            <TimelineTypeBadge type={entry.type} source={entry.source} />
                          </td>
                          <td className="px-3 py-2 text-gray-700 align-top">
                            {entry.user || '-'}
                          </td>
                          <td className="px-3 py-2 text-gray-800 align-top">
                            {entry.summary && entry.comment ? (
                              <>
                                <span className="font-medium">{entry.summary}</span>
                                <p className="whitespace-pre-wrap mt-0.5 text-gray-600">{entry.comment}</p>
                              </>
                            ) : (
                              <span className="whitespace-pre-wrap">{entry.comment || entry.summary || '-'}</span>
                            )}
                            {entry.invoice_number && (
                              <span className="ml-2 text-purple-500">#{entry.invoice_number}</span>
                            )}
                            {entry.source === 'local' && entry.status && (
                              <span className={`ml-2 text-[10px] px-1.5 py-0.5 rounded-full font-medium ${
                                entry.status === 'pushed' ? 'bg-gray-200 text-gray-600' : 'bg-green-100 text-green-700'
                              }`}>
                                {entry.status === 'pushed' ? 'Poussé' : entry.status === 'imported' ? 'Sheet' : 'Validé'}
                              </span>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </div>
            </div>
          </div>
        );
      })()}
    </div>
  );
}
