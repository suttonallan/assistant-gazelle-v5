import React, { useState, useMemo, useEffect } from 'react';
import { submitReport, getReports, getPianos, updatePiano } from '../api/vincentDIndyApi';

// Configuration de l'API - sera remplacée par la variable d'environnement en production
const API_URL = import.meta.env.VITE_API_URL || 'https://assistant-gazelle-v5-api.onrender.com';

const VincentDIndyDashboard = () => {
  const [pianos, setPianos] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const [currentView, setCurrentView] = useState('nicolas');
  const [showOnlySelected, setShowOnlySelected] = useState(false); // Nicolas : filtrer sur pianos sélectionnés
  const [showOnlyProposed, setShowOnlyProposed] = useState(false); // Technicien : filtrer sur pianos à faire uniquement
  const [searchLocal, setSearchLocal] = useState(''); // Technicien : recherche par local

  const [sortConfig, setSortConfig] = useState({ key: 'local', direction: 'asc' });
  const [filterUsage, setFilterUsage] = useState('all');
  const [filterAccordDepuis, setFilterAccordDepuis] = useState(0);
  const [selectedIds, setSelectedIds] = useState(new Set());
  
  // Pour vue technicien - piano développé
  const [expandedPianoId, setExpandedPianoId] = useState(null);
  const [travailInput, setTravailInput] = useState('');
  const [observationsInput, setObservationsInput] = useState('');

  // Pour vue Nicolas - édition "à faire"
  const [editingAFaireId, setEditingAFaireId] = useState(null);
  const [aFaireInput, setAFaireInput] = useState('');

  const usages = ['Piano', 'Accompagnement', 'Pratique', 'Concert', 'Enseignement', 'Loisir'];

  // Charger les pianos depuis l'API au montage du composant
  useEffect(() => {
    loadPianosFromAPI();
  }, []);

  const loadPianosFromAPI = async () => {
    try {
      setLoading(true);
      setError(null);
      console.log('🔄 Chargement des pianos depuis:', API_URL);

      const data = await getPianos(API_URL);
      console.log('✅ Données reçues:', data);
      console.log('📊 Nombre de pianos:', data.count || data.pianos?.length || 0);

      if (data.error) {
        console.error('❌ Erreur API:', data.message);
        setError(data.message || 'Erreur lors du chargement des pianos');
        setPianos([]);
      } else {
        setPianos(data.pianos || []);
        if (data.debug) {
          console.log('🔍 Debug:', data.debug);
        }
      }
    } catch (err) {
      console.error('❌ Erreur lors du chargement des pianos:', err);
      setError(err.message || 'Erreur lors du chargement des pianos');
      setPianos([]);
    } finally {
      setLoading(false);
    }
  };

  // Fonction pour sauvegarder un piano via l'API
  const savePianoToAPI = async (pianoId, updates) => {
    try {
      await updatePiano(API_URL, pianoId, updates);
      console.log('✅ Piano sauvegardé:', pianoId, updates);
    } catch (err) {
      console.error('❌ Erreur lors de la sauvegarde:', err);
      alert(`Erreur lors de la sauvegarde: ${err.message}`);
      // Recharger depuis l'API en cas d'erreur
      await loadPianosFromAPI();
    }
  };

  const moisDepuisAccord = (dateStr) => {
    const date = new Date(dateStr);
    const now = new Date();
    return Math.floor((now - date) / (1000 * 60 * 60 * 24 * 30));
  };

  const handleSort = (key) => {
    setSortConfig(prev => ({
      key,
      direction: prev.key === key && prev.direction === 'asc' ? 'desc' : 'asc'
    }));
  };

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

  const pianosFiltres = useMemo(() => {
    let result = [...pianos];

    if (currentView === 'nicolas') {
      // Onglet Nicolas : par défaut tous les pianos, ou filtrer sur les jaunes/verts si demandé
      if (showOnlySelected) {
        result = result.filter(p => p.status === 'proposed' || p.status === 'completed');
      }
      // Sinon : tous les pianos (pas de filtre)
    } else if (currentView === 'technicien') {
      // Par défaut : tous les pianos. Si demandé : seulement les pianos à faire (proposed)
      if (showOnlyProposed) {
        result = result.filter(p => p.status === 'proposed');
      }

      // Filtre de recherche par local (vue technicien)
      if (searchLocal.trim()) {
        result = result.filter(p =>
          p.local.toLowerCase().includes(searchLocal.toLowerCase())
        );
      }
    }

    if (filterUsage !== 'all') {
      result = result.filter(p => filterUsage === '' ? !p.usage : p.usage === filterUsage);
    }
    if (filterAccordDepuis > 0) {
      result = result.filter(p => moisDepuisAccord(p.dernierAccord) >= filterAccordDepuis);
    }

    result.sort((a, b) => {
      switch (sortConfig.key) {
        case 'local':
          return sortConfig.direction === 'asc' 
            ? a.local.localeCompare(b.local, undefined, { numeric: true })
            : b.local.localeCompare(a.local, undefined, { numeric: true });
        case 'piano':
          return sortConfig.direction === 'asc' ? a.piano.localeCompare(b.piano) : b.piano.localeCompare(a.piano);
        case 'accord':
          const aTime = new Date(a.dernierAccord).getTime();
          const bTime = new Date(b.dernierAccord).getTime();
          return sortConfig.direction === 'asc' ? aTime - bTime : bTime - aTime;
        case 'mois':
          const aMois = moisDepuisAccord(a.dernierAccord);
          const bMois = moisDepuisAccord(b.dernierAccord);
          return sortConfig.direction === 'asc' ? aMois - bMois : bMois - aMois;
        default:
          return 0;
      }
    });

    return result;
  }, [pianos, sortConfig, filterUsage, filterAccordDepuis, currentView, showOnlySelected, showOnlyProposed, searchLocal]);

  // Actions
  const toggleProposed = async (id) => {
    const piano = pianos.find(p => p.id === id);
    if (!piano) return;

    // Cycle à 3 états : normal → proposed (jaune) → completed (vert) → normal
    let newStatus;
    if (piano.status === 'normal' || !piano.status) {
      newStatus = 'proposed'; // Blanc → Jaune
    } else if (piano.status === 'proposed') {
      newStatus = 'completed'; // Jaune → Vert
    } else if (piano.status === 'completed') {
      newStatus = 'normal'; // Vert → Blanc
    }

    // Mise à jour optimiste
    setPianos(pianos.map(p =>
      p.id === id ? { ...p, status: newStatus } : p
    ));

    // Sauvegarder via API
    await savePianoToAPI(id, { status: newStatus });
  };

  const toggleSelected = (id) => {
    setSelectedIds(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const selectAll = () => setSelectedIds(new Set(pianosFiltres.map(p => p.id)));
  const deselectAll = () => setSelectedIds(new Set());

  const batchSetStatus = async (status) => {
    // Sauvegarder les IDs sélectionnés avant de vider
    const idsToUpdate = Array.from(selectedIds);

    // Mise à jour optimiste
    const updatedPianos = pianos.map(p => selectedIds.has(p.id) ? { ...p, status } : p);
    setPianos(updatedPianos);

    // Désélectionner immédiatement
    setSelectedIds(new Set());

    // Sauvegarder chaque piano via API (utiliser idsToUpdate au lieu de selectedIds)
    for (const id of idsToUpdate) {
      await savePianoToAPI(id, { status });
    }
  };

  const batchSetUsage = async (usage) => {
    // Sauvegarder les IDs sélectionnés avant de vider
    const idsToUpdate = Array.from(selectedIds);

    // Mise à jour optimiste
    setPianos(pianos.map(p => selectedIds.has(p.id) ? { ...p, usage } : p));

    // Désélectionner immédiatement
    setSelectedIds(new Set());

    // Sauvegarder chaque piano via API (utiliser idsToUpdate au lieu de selectedIds)
    for (const id of idsToUpdate) {
      await savePianoToAPI(id, { usage });
    }
  };


  // Technicien - toggle expand
  const toggleExpand = (piano) => {
    if (expandedPianoId === piano.id) {
      setExpandedPianoId(null);
    } else {
      setExpandedPianoId(piano.id);
      setTravailInput(piano.travail || '');
      setObservationsInput(piano.observations || '');
    }
  };

  // Technicien - sauvegarder (connecté à l'API)
  const saveTravail = async (id) => {
    const piano = pianos.find(p => p.id === id);
    if (!piano) return;

    try {
      // Créer le rapport pour l'API
      const report = {
        technician_name: 'Technicien', // TODO: Récupérer depuis l'authentification
        client_name: 'École Vincent-d\'Indy',
        date: new Date().toISOString().split('T')[0],
        report_type: 'maintenance',
        description: `Travail effectué sur piano ${piano.piano} (Série: ${piano.serie}) - Local: ${piano.local}`,
        notes: piano.aFaire ? `À faire: ${piano.aFaire}\n\nTravail: ${travailInput}\n\nObservations: ${observationsInput}` : `Travail: ${travailInput}\n\nObservations: ${observationsInput}`,
        hours_worked: null
      };

      // Envoyer le rapport à l'API
      await submitReport(API_URL, report);

      // Mise à jour optimiste
      setPianos(pianos.map(p =>
        p.id === id ? { ...p, travail: travailInput, observations: observationsInput, status: 'completed' } : p
      ));

      // Sauvegarder le piano via API
      await savePianoToAPI(id, {
        travail: travailInput,
        observations: observationsInput,
        status: 'completed'
      });

      // Passer au suivant
      const currentIndex = pianosFiltres.findIndex(p => p.id === id);
      const nextPiano = pianosFiltres[currentIndex + 1];
      if (nextPiano && nextPiano.status === 'proposed') {
        setExpandedPianoId(nextPiano.id);
        setTravailInput(nextPiano.travail || '');
        setObservationsInput(nextPiano.observations || '');
      } else {
        setExpandedPianoId(null);
      }
    } catch (error) {
      console.error('Erreur lors de la sauvegarde:', error);
      alert('Erreur lors de la sauvegarde du rapport. Veuillez réessayer.');
    }
  };

  const stats = {
    total: pianos.length,
    proposed: pianos.filter(p => p.status === 'proposed').length,
    completed: pianos.filter(p => p.status === 'completed').length,
  };

  const getRowClass = (piano) => {
    if (selectedIds.has(piano.id)) return 'bg-purple-200';
    switch (piano.status) {
      case 'proposed': return 'bg-yellow-200';
      case 'completed': return 'bg-green-200';
      default: return 'bg-white';
    }
  };

  // ============ VUE TECHNICIEN (mobile-friendly) ============
  if (currentView === 'technicien') {
    if (loading) {
      return (
        <div className="min-h-screen bg-gray-100 flex items-center justify-center">
          <div className="text-center">
            <div className="text-lg text-gray-600">Chargement des pianos...</div>
          </div>
        </div>
      );
    }

    if (error) {
      return (
        <div className="min-h-screen bg-gray-100 flex items-center justify-center">
          <div className="text-center bg-white p-6 rounded-lg shadow">
            <div className="text-red-600 mb-2">⚠️ Erreur</div>
            <div className="text-sm text-gray-600">{error}</div>
            <button
              onClick={() => window.location.reload()}
              className="mt-4 px-4 py-2 bg-blue-500 text-white rounded"
            >
              Réessayer
            </button>
          </div>
        </div>
      );
    }

    return (
      <div className="min-h-screen bg-gray-100">
        {/* Header compact */}
        <div className="bg-white shadow p-3 sticky top-0 z-10">
          <div className="flex justify-between items-center">
            <h1 className="text-lg font-bold">🎹 Tournée</h1>
            <div className="flex gap-2 text-xs">
              <span className="px-2 py-1 bg-yellow-200 rounded">{stats.proposed} à faire</span>
              <span className="px-2 py-1 bg-green-200 rounded">{stats.completed} ✓</span>
            </div>
          </div>
          {/* Onglets */}
          <div className="flex mt-2 text-xs">
            {['nicolas', 'technicien'].map(view => (
              <button
                key={view}
                onClick={() => setCurrentView(view)}
                className={`flex-1 py-2 ${currentView === view ? 'bg-blue-500 text-white rounded' : 'text-gray-500'}`}
              >
                {view === 'nicolas' ? 'Nicolas' : 'Technicien'}
              </button>
            ))}
          </div>
          {/* Boutons de filtrage */}
          <div className="mt-2 flex gap-2">
            <button
              onClick={() => setShowOnlyProposed(false)}
              className={`flex-1 py-1 px-2 text-xs rounded ${!showOnlyProposed ? 'bg-blue-500 text-white' : 'bg-gray-100'}`}
            >
              Tous ({stats.total})
            </button>
            <button
              onClick={() => setShowOnlyProposed(true)}
              className={`flex-1 py-1 px-2 text-xs rounded ${showOnlyProposed ? 'bg-blue-500 text-white' : 'bg-gray-100'}`}
            >
              À faire ({stats.proposed})
            </button>
          </div>

          {/* Barre de recherche par local */}
          <div className="mt-2">
            <input
              type="text"
              placeholder="Rechercher par local (ex: 301)"
              value={searchLocal}
              onChange={(e) => setSearchLocal(e.target.value)}
              className="w-full px-3 py-2 border rounded text-sm"
            />
          </div>
        </div>

        {/* Liste accordéon */}
        <div className="p-2 space-y-2">
          {pianosFiltres.length === 0 ? (
            <div className="bg-white rounded-lg p-6 text-center text-gray-500">
              {showOnlyProposed ? 'Aucun piano à faire.' : 'Aucun piano trouvé.'}
            </div>
          ) : (
            pianosFiltres.map(piano => {
              const isExpanded = expandedPianoId === piano.id;
              const mois = moisDepuisAccord(piano.dernierAccord);

              return (
                <div key={piano.id} className={`rounded-lg shadow overflow-hidden ${piano.status === 'completed' ? 'bg-green-100' : 'bg-white'}`}>
                  {/* Ligne principale - cliquable */}
                  <div 
                    onClick={() => toggleExpand(piano)}
                    className="p-3 flex justify-between items-center cursor-pointer active:bg-gray-100"
                  >
                    <div className="flex items-center gap-3">
                      <span className="text-lg font-bold text-gray-700">{piano.local}</span>
                      <span className="text-gray-600">{piano.piano}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      {piano.status === 'completed' && <span className="text-green-600">✓</span>}
                      <span className={`text-sm ${mois >= 6 ? 'text-orange-500' : 'text-gray-400'}`}>{mois}m</span>
                      <span className="text-gray-400">{isExpanded ? '▲' : '▼'}</span>
                    </div>
                  </div>

                  {/* Détails - développé */}
                  {isExpanded && (
                    <div className="border-t bg-gray-50 p-3 space-y-3">
                      {/* Infos */}
                      <div className="grid grid-cols-2 gap-2 text-sm">
                        <div><span className="text-gray-500">Série:</span> {piano.serie}</div>
                        <div><span className="text-gray-500">Type:</span> {piano.type === 'D' ? 'Droit' : 'Queue'}</div>
                        <div><span className="text-gray-500">Dernier:</span> {piano.dernierAccord}</div>
                        <div><span className="text-gray-500">Usage:</span> {piano.usage || '-'}</div>
                      </div>

                      {/* Note "à faire" de Nicolas */}
                      {piano.aFaire && (
                        <div className="bg-yellow-100 p-2 rounded text-sm">
                          <span className="font-medium">📋 À faire:</span> {piano.aFaire}
                        </div>
                      )}

                      {/* Formulaire technicien */}
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">🔧 Travail effectué</label>
                        <textarea
                          value={travailInput}
                          onChange={(e) => setTravailInput(e.target.value)}
                          className="w-full border rounded p-2 text-sm h-20"
                          placeholder="Accord, réglages..."
                        />
                      </div>

                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">📝 Observations</label>
                        <textarea
                          value={observationsInput}
                          onChange={(e) => setObservationsInput(e.target.value)}
                          className="w-full border rounded p-2 text-sm h-20"
                          placeholder="Problèmes, recommandations..."
                        />
                      </div>

                      <button
                        onClick={() => saveTravail(piano.id)}
                        className="w-full bg-green-500 text-white py-3 rounded-lg font-medium active:bg-green-600"
                      >
                        💾 Sauvegarder → Suivant
                      </button>
                    </div>
                  )}
                </div>
              );
            })
          )}
        </div>
      </div>
    );
  }

  // ============ VUES PRÉPARATION ET VALIDATION ============
  if (loading) {
    return (
      <div className="min-h-screen bg-gray-100 flex items-center justify-center">
        <div className="text-center">
          <div className="text-lg text-gray-600">Chargement des pianos...</div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-100 flex items-center justify-center">
        <div className="text-center bg-white p-6 rounded-lg shadow">
          <div className="text-red-600 mb-2">⚠️ Erreur</div>
          <div className="text-sm text-gray-600">{error}</div>
          <button
            onClick={() => window.location.reload()}
            className="mt-4 px-4 py-2 bg-blue-500 text-white rounded"
          >
            Réessayer
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-100 p-4">
      {/* Header */}
      <div className="bg-white rounded-lg shadow mb-4">
        <div className="p-4 border-b">
          <div className="flex justify-between items-start">
            <div>
              <h1 className="text-2xl font-bold text-gray-800">🎹 Vincent-d'Indy</h1>
              <div className="flex gap-4 mt-2 text-sm flex-wrap">
                <span className="px-2 py-1 bg-gray-200 rounded">{stats.total} pianos</span>
                <span className="px-2 py-1 bg-yellow-200 rounded">{stats.proposed} à faire</span>
                <span className="px-2 py-1 bg-green-200 rounded">{stats.completed} complétés</span>
              </div>
            </div>
            <button
              onClick={loadPianosFromAPI}
              className="px-3 py-1 text-xs bg-gray-100 hover:bg-gray-200 border rounded"
              title="Rafraîchir les données depuis l'API"
            >
              🔄 Rafraîchir
            </button>
          </div>
        </div>
        
        {/* Onglets */}
        <div className="flex">
          {[
            { key: 'nicolas', label: 'Nicolas' },
            { key: 'technicien', label: 'Technicien' },
          ].map(tab => (
            <button
              key={tab.key}
              onClick={() => { setCurrentView(tab.key); setSelectedIds(new Set()); }}
              className={`flex-1 px-4 py-3 text-sm font-medium border-b-2 ${
                currentView === tab.key
                  ? 'border-blue-500 text-blue-600 bg-blue-50'
                  : 'border-transparent text-gray-500 hover:bg-gray-50'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* Barre d'outils - Nicolas */}
      {currentView === 'nicolas' && (
        <div className="bg-white rounded-lg shadow p-4 mb-4 space-y-3">
          {/* Boutons de vue */}
          <div className="flex gap-3 items-center">
            <button
              onClick={() => setShowOnlySelected(false)}
              className={`px-4 py-2 rounded text-sm font-medium ${!showOnlySelected ? 'bg-blue-500 text-white' : 'bg-gray-100 hover:bg-gray-200'}`}
            >
              📋 Tous les pianos ({stats.total})
            </button>
            <button
              onClick={() => setShowOnlySelected(true)}
              className={`px-4 py-2 rounded text-sm font-medium ${showOnlySelected ? 'bg-blue-500 text-white' : 'bg-gray-100 hover:bg-gray-200'}`}
            >
              🎯 Projet de tournée ({stats.proposed + stats.completed})
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
          </div>

          {/* Actions multiples */}
          <div className="flex gap-3 flex-wrap items-center border-t pt-3">
            <button onClick={selectAll} className="px-3 py-1 rounded text-sm bg-gray-200 hover:bg-gray-300">☑ Tous</button>
            <button onClick={deselectAll} className="px-3 py-1 rounded text-sm bg-gray-200 hover:bg-gray-300">☐ Aucun</button>

            {selectedIds.size > 0 && (
              <>
                <span className="text-purple-600 font-medium text-sm">{selectedIds.size} sel.</span>
                <button onClick={() => batchSetStatus('proposed')} className="px-3 py-1 rounded text-sm bg-yellow-400">→ À faire</button>
                <button onClick={() => batchSetStatus('normal')} className="px-3 py-1 rounded text-sm bg-white border">→ Retirer</button>
                <select onChange={(e) => { if (e.target.value) batchSetUsage(e.target.value); }} className="border rounded px-2 py-1 text-sm" value="">
                  <option value="">Usage...</option>
                  {usages.map(u => <option key={u} value={u}>{u}</option>)}
                </select>
              </>
            )}
          </div>
        </div>
      )}

      {/* Table */}
      <div className="bg-white rounded-lg shadow overflow-hidden">
        <table className="w-full">
          <thead>
            <tr className="bg-gray-50 border-b">
              {currentView === 'nicolas' && (
                <th className="px-2 py-3 w-10">
                  <input
                    type="checkbox"
                    checked={selectedIds.size === pianosFiltres.length && pianosFiltres.length > 0}
                    onChange={(e) => e.target.checked ? selectAll() : deselectAll()}
                    className="rounded"
                  />
                </th>
              )}
              <ColumnHeader columnKey="local">Local</ColumnHeader>
              <ColumnHeader columnKey="piano">Piano</ColumnHeader>
              <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase"># Série</th>
              <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase">Usage</th>
              <ColumnHeader columnKey="mois">Mois</ColumnHeader>
              {currentView === 'nicolas' && (
                <>
                  <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase bg-yellow-50">À faire (Nicolas)</th>
                  <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase bg-green-50">Travail / Obs. (Tech)</th>
                </>
              )}
              <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                Statut
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {pianosFiltres.map((piano) => {
              const mois = moisDepuisAccord(piano.dernierAccord);

              return (
                <tr
                  key={piano.id}
                  className={`${getRowClass(piano)} ${currentView === 'nicolas' ? 'cursor-pointer hover:opacity-80' : ''}`}
                  onClick={() => {
                    if (currentView === 'nicolas') toggleProposed(piano.id);
                  }}
                >
                  {currentView === 'nicolas' && (
                    <td className="px-2 py-3 text-center" onClick={(e) => e.stopPropagation()}>
                      <input
                        type="checkbox"
                        checked={selectedIds.has(piano.id)}
                        onChange={() => toggleSelected(piano.id)}
                        className="rounded"
                      />
                    </td>
                  )}
                  <td className="px-3 py-3 text-sm font-medium">{piano.local}</td>
                  <td className="px-3 py-3 text-sm">{piano.piano}</td>
                  <td className="px-3 py-3 text-sm text-gray-500 font-mono">{piano.serie}</td>
                  <td className="px-3 py-3 text-sm text-gray-500">{piano.usage || '-'}</td>
                  <td className={`px-3 py-3 text-sm font-medium ${mois >= 12 ? 'text-red-600' : mois >= 6 ? 'text-orange-500' : 'text-green-600'}`}>
                    {mois}
                  </td>

                  {/* Colonnes pour l'onglet Nicolas */}
                  {currentView === 'nicolas' && (
                    <>
                      {/* Colonne "À faire" de Nicolas */}
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

                      {/* Colonne des notes du technicien */}
                      <td className="px-3 py-3 bg-green-50 text-xs">
                        {piano.travail && (
                          <div><strong>Travail:</strong> {piano.travail}</div>
                        )}
                        {piano.observations && (
                          <div className="mt-1"><strong>Obs:</strong> {piano.observations}</div>
                        )}
                        {!piano.travail && !piano.observations && (
                          <span className="text-gray-400">-</span>
                        )}
                      </td>
                    </>
                  )}

                  {/* Colonne Statut */}
                  <td className="px-3 py-3 text-sm">
                    {piano.status === 'proposed' && <span className="px-2 py-1 bg-yellow-400 rounded text-xs">À faire</span>}
                    {piano.status === 'completed' && <span className="px-2 py-1 bg-green-400 rounded text-xs">Complété</span>}
                    {piano.status === 'normal' && <span className="text-gray-400">-</span>}
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
        <span className="flex items-center gap-1"><span className="w-3 h-3 bg-white border rounded"></span> Normal</span>
        <span className="flex items-center gap-1"><span className="w-3 h-3 bg-yellow-200 rounded"></span> À faire</span>
        <span className="flex items-center gap-1"><span className="w-3 h-3 bg-green-200 rounded"></span> Complété</span>
      </div>
    </div>
  );
};

export default VincentDIndyDashboard;

