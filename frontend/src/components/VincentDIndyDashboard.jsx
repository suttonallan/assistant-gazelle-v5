// LOG: Début du fichier VincentDIndyDashboard.jsx
console.log('[VincentDIndyDashboard] Fichier chargé - ligne 1');

import React, { useState, useMemo, useEffect, useRef, useCallback } from 'react';
import { submitReport, getReports, getPianos, updatePiano, getActivity } from '../api/vincentDIndyApi';
import VDI_Navigation from './vdi/VDI_Navigation';
import VDI_TechnicianView from './vdi/VDI_TechnicianView';
import VDI_ManagementView from './vdi/VDI_ManagementView';
import VDI_NotesView from './vdi/VDI_NotesView';

// Configuration de l'API - utiliser le proxy Vite en développement
const API_URL = import.meta.env.VITE_API_URL || (import.meta.env.DEV ? '' : 'https://assistant-gazelle-v5-api.onrender.com');

const VincentDIndyDashboard = ({ currentUser, initialView = 'nicolas', hideNickView = false, institution = 'vincent-dindy' }) => {
  // Note: hideLocationSelector était utilisé pour masquer le sélecteur d'établissement,
  // mais le sélecteur a été supprimé avec le header sticky
  const [pianos, setPianos] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Si hideNickView est true, forcer la vue technicien et empêcher le changement
  const [currentView, setCurrentView] = useState(hideNickView ? 'technicien' : initialView);
  
  // Si hideNickView est true, empêcher le changement de vue
  useEffect(() => {
    if (hideNickView && currentView !== 'technicien') {
      setCurrentView('technicien');
    }
  }, [hideNickView, currentView]);
  const [showOnlySelected, setShowOnlySelected] = useState(false); // Nick : filtrer sur pianos sélectionnés
  const [showOnlyProposed, setShowOnlyProposed] = useState(false); // Technicien : filtrer sur pianos à faire uniquement
  const [searchLocal, setSearchLocal] = useState(''); // Technicien : recherche par local
  const [showAllPianos, setShowAllPianos] = useState(false); // Afficher tous les pianos (même masqués de l'inventaire)

  const [sortConfig, setSortConfig] = useState({ key: 'local', direction: 'asc' });
  const [filterUsage, setFilterUsage] = useState('all');
  const [filterAccordDepuis, setFilterAccordDepuis] = useState(0);
  const [filterEtage, setFilterEtage] = useState('all'); // Filtre par étage (1, 2, 3, etc. ou 'all')
  const [selectedIds, setSelectedIds] = useState(new Set());

  // Ref pour la checkbox "sélectionner tous"
  const selectAllCheckboxRef = useRef(null);

  // Pour vue technicien - piano développé
  const [expandedPianoId, setExpandedPianoId] = useState(null);
  const [travailInput, setTravailInput] = useState('');
  const [observationsInput, setObservationsInput] = useState('');
  const [isWorkCompleted, setIsWorkCompleted] = useState(false);

  // Pour vue Nick - édition "à faire" et "notes"
  const [editingAFaireId, setEditingAFaireId] = useState(null);
  const [aFaireInput, setAFaireInput] = useState('');
  const [editingNotesId, setEditingNotesId] = useState(null);
  const [notesInput, setNotesInput] = useState('');

  // Pour sélection de l'établissement
  const [selectedLocation, setSelectedLocation] = useState('vincent-dindy');

  // Pour le volet "Tournées" dans la vue technicien - institution sélectionnée
  const [selectedInstitutionForTechnician, setSelectedInstitutionForTechnician] = useState(institution);
  
  // Debug: log de l'institution initiale
  useEffect(() => {
    console.log('[VincentDIndyDashboard] Institution initiale:', institution, 'selectedInstitutionForTechnician:', selectedInstitutionForTechnician);
  }, [institution, selectedInstitutionForTechnician]);

  // Pour push vers Gazelle
  const [readyForPushCount, setReadyForPushCount] = useState(0);
  const [pushInProgress, setPushInProgress] = useState(false);

  const usages = ['Piano', 'Accompagnement', 'Pratique', 'Concert', 'Enseignement', 'Loisir'];

  const loadPianosFromAPI = useCallback(async (targetInstitution = null) => {
    try {
      setLoading(true);
      setError(null);
      // Utiliser l'institution cible si fournie, sinon l'institution du dashboard
      const institutionToLoad = targetInstitution || institution;
      console.log('🔄 Chargement des pianos depuis:', API_URL, 'pour institution:', institutionToLoad);

      // Toujours charger TOUS les pianos (include_inactive=true)
      // Le filtrage se fera côté frontend via showAllPianos
      const url = `${API_URL}/api/${institutionToLoad}/pianos?include_inactive=true`;
      const response = await fetch(url);
      const data = await response.json();

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
  }, [institution]); // Recharger les pianos si l'institution change

  // Fonction pour sauvegarder un piano via l'API
  const savePianoToAPI = async (pianoId, updates) => {
    try {
      // Ajouter automatiquement la signature de l'utilisateur
      const updatesWithUser = {
        ...updates,
        updated_by: currentUser?.email || currentUser?.name || 'Unknown'
      };

      // Utiliser l'institution dynamique au lieu de vincent-dindy hardcodé
      const response = await fetch(`${API_URL}/api/${institution}/pianos/${pianoId}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(updatesWithUser),
      });

      if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: 'Erreur inconnue' }));
        throw new Error(error.detail || `Erreur ${response.status}`);
      }

      console.log('✅ Piano sauvegardé par', currentUser?.name, ':', pianoId, updatesWithUser);
      return response.json();
    } catch (err) {
      console.error('❌ Erreur lors de la sauvegarde:', err);
      alert(`Erreur lors de la sauvegarde: ${err.message}`);
      // Recharger depuis l'API en cas d'erreur
      await loadPianosFromAPI();
    }
  };

  const moisDepuisAccord = (dateStr) => {
    if (!dateStr || dateStr.trim() === '') return 999;
    const date = new Date(dateStr);
    if (isNaN(date.getTime())) return 999;
    const now = new Date();
    const diffDays = Math.floor((now - date) / (1000 * 60 * 60 * 24));
    if (diffDays < 30) return diffDays / 30; // Fraction < 1 pour le tri
    return Math.floor(diffDays / 30);
  };

  // Format de date relatif compact (1j, 2j, 1s, 1m, etc.)
  const formatDateRelative = (dateStr) => {
    if (!dateStr || dateStr.trim() === '') return '-';
    const date = new Date(dateStr);
    if (isNaN(date.getTime())) return '-';
    
    const now = new Date();
    const diffMs = now - date;
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
    const diffWeeks = Math.floor(diffDays / 7);
    const diffMonths = Math.floor(diffDays / 30);
    
    if (diffDays === 0) return 'Aujourd\'hui';
    if (diffDays === 1) return '1j';
    if (diffDays < 7) return `${diffDays}j`;
    if (diffWeeks === 1) return '1s';
    if (diffWeeks < 4) return `${diffWeeks}s`;
    if (diffMonths === 1) return '1m';
    if (diffMonths < 12) return `${diffMonths}m`;
    const diffYears = Math.floor(diffMonths / 12);
    return `${diffYears}a`;
  };


  // Obtenir l'ID unique d'un piano - TOUJOURS le gazelleId
  const getPianoUniqueId = (piano) => {
    return piano.gazelleId;  // UNIQUEMENT gazelleId, rien d'autre
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

    // Filtre d'inventaire : masquer les pianos avec is_hidden=true (sauf si "Tout voir" activé)
    if (!showAllPianos) {
      result = result.filter(p => !p.is_hidden);
    }

    // Logique normale : appliquer les filtres selon la vue
    if (currentView === 'nicolas') {
      // Vue Nicolas : pas de filtre par défaut (tous les pianos)
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

    // Appliquer les filtres usage, accord, étage
    if (filterUsage !== 'all') {
      result = result.filter(p => filterUsage === '' ? !p.usage : p.usage === filterUsage);
    }
    if (filterAccordDepuis > 0) {
      result = result.filter(p => moisDepuisAccord(p.dernierAccord) >= filterAccordDepuis);
    }
    // Filtre par étage (premier chiffre du local: 112 = 1er étage, 302 = 3ème étage)
    if (filterEtage !== 'all' && currentView === 'nicolas') {
      const etageNum = parseInt(filterEtage);
      result = result.filter(p => {
        if (!p.local) return false;
        const match = p.local.match(/^\d/); // Premier chiffre
        return match && parseInt(match[0]) === etageNum;
      });
    }

    result.sort((a, b) => {
      switch (sortConfig.key) {
        case 'local':
          const aLocal = a.local || '';
          const bLocal = b.local || '';
          return sortConfig.direction === 'asc'
            ? aLocal.localeCompare(bLocal, undefined, { numeric: true })
            : bLocal.localeCompare(aLocal, undefined, { numeric: true });
        case 'piano':
          const aPiano = a.piano || '';
          const bPiano = b.piano || '';
          return sortConfig.direction === 'asc' ? aPiano.localeCompare(bPiano) : bPiano.localeCompare(aPiano);
        case 'accord':
          const aTime = a.dernierAccord ? new Date(a.dernierAccord).getTime() : 0;
          const bTime = b.dernierAccord ? new Date(b.dernierAccord).getTime() : 0;
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
  }, [pianos, sortConfig, filterUsage, filterAccordDepuis, filterEtage, currentView, showOnlySelected, showOnlyProposed, searchLocal, showAllPianos, moisDepuisAccord]);

  // Gérer l'état indeterminate de la checkbox "sélectionner tous"
  useEffect(() => {
    if (selectAllCheckboxRef.current && pianosFiltres.length >= 0) {
      const allSelected = selectedIds.size === pianosFiltres.length && pianosFiltres.length > 0;
      const someSelected = selectedIds.size > 0 && selectedIds.size < pianosFiltres.length;
      selectAllCheckboxRef.current.checked = allSelected;
      selectAllCheckboxRef.current.indeterminate = someSelected;
    }
  }, [selectedIds.size, pianosFiltres.length]);

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

  const toggleSelected = async (id) => {
    // Trouver le piano correspondant
    const piano = pianos.find(p => p.id === id);

    if (!piano) {
      console.error('❌ Piano non trouvé:', id);
      return;
    }

    console.log('\n✅ TOGGLE PIANO:', piano.serie || id);
    console.log('   Piano ID (gazelleId):', piano.id);

    // Toggle la sélection visuelle
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

  const batchHideFromInventory = async () => {
    // Sauvegarder les IDs sélectionnés avant de vider
    const idsToUpdate = Array.from(selectedIds);

    if (idsToUpdate.length === 0) {
      alert('Aucun piano sélectionné');
      return;
    }

    // Confirmation
    if (!confirm(`Masquer ${idsToUpdate.length} piano(s) de l'inventaire?`)) {
      return;
    }

    // Mise à jour optimiste
    setPianos(pianos.map(p => selectedIds.has(p.id) ? { ...p, is_hidden: true } : p));

    // Désélectionner immédiatement
    setSelectedIds(new Set());

    // Sauvegarder chaque piano via API
    for (const id of idsToUpdate) {
      await savePianoToAPI(id, { isHidden: true });
    }
  };


  // Technicien - toggle expand
  const toggleExpand = (piano) => {
    if (expandedPianoId === piano.id) {
      setExpandedPianoId(null);
    } else {
      setExpandedPianoId(piano.id);
      setTravailInput(piano.travail || '');
      setIsWorkCompleted(piano.is_work_completed || false);
    }
  };

  // Technicien - auto-save (appelé par debounce dans VDI_TechnicianView)
  // Accepte la valeur en paramètre pour le mode auto-save
  const saveTravail = async (id, value) => {
    const noteValue = value !== undefined ? value : travailInput;
    const piano = pianos.find(p => p.id === id);
    if (!piano) return;

    // Mise à jour optimiste
    setPianos(pianos.map(p =>
      p.id === id ? { ...p, travail: noteValue, status: noteValue ? 'work_in_progress' : p.status } : p
    ));

    // Sauvegarder le piano via API
    await savePianoToAPI(id, { travail: noteValue });
  };


  // Charger les pianos depuis l'API au montage du composant
  useEffect(() => {
    console.log('[VincentDIndyDashboard] useEffect de chargement initial déclenché');
    try {
      loadPianosFromAPI();
    } catch (e) {
      console.error('[VincentDIndyDashboard] Erreur dans useEffect de chargement:', e);
      alert(`Erreur au chargement initial: ${e.message}\n\nStack: ${e.stack}`);
    }
  }, [loadPianosFromAPI, institution]); // Recharger si l'institution change

  // Handler pour changement d'institution depuis le volet tournées
  const handleInstitutionChangeForTechnician = useCallback(async (newInstitution) => {
    setSelectedInstitutionForTechnician(newInstitution);
    await loadPianosFromAPI(newInstitution);
  }, [loadPianosFromAPI]);

  // Charger le compteur de pianos prêts pour push
  useEffect(() => {
    const loadReadyCount = async () => {
      try {
        const response = await fetch(`${API_URL}/api/${institution}/pianos-ready-for-push`);
        if (response.ok) {
          const data = await response.json();
          setReadyForPushCount(data.count || 0);
      }
    } catch (err) {
        console.error('Erreur chargement pianos prêts:', err);
    }
  };

    if (currentView === 'nicolas') {
      loadReadyCount();
    }
  }, [pianos, currentView, institution]);


  // Calcul des stats avec protection contre les erreurs
  const stats = useMemo(() => {
    if (!pianos || !Array.isArray(pianos)) {
      return { total: 0, top: 0, proposed: 0, completed: 0 };
    }
    return {
      total: pianos.length,
      top: pianos.filter(p => p && p.status === 'top').length,
      proposed: pianos.filter(p => p && (p.status === 'proposed' || (p.aFaire && p.aFaire.trim() !== ''))).length,
      completed: pianos.filter(p => p && p.status === 'completed').length,
    };
  }, [pianos]);

  // Note: tourneesStats était affiché dans l'ancien header sticky, mais n'est plus nécessaire
  // Si besoin futur, décommenter :
  // const tourneesStats = useMemo(() => {
  //   if (!tournees || !Array.isArray(tournees)) {
  //     return { 'vincent-dindy': 0, 'orford': 0 };
  //   }
  //   return {
  //     'vincent-dindy': tournees.filter(t => t && t.etablissement === 'vincent-dindy').length,
  //     'orford': tournees.filter(t => t && t.etablissement === 'orford').length,
  //   };
  // }, [tournees]);

  const getRowClass = (piano) => {
    // Coloration basée sur le statut du piano
    // Priorité 1: Sélection (mauve)
    if (selectedIds.has(piano.id)) return 'bg-purple-100';

    // Priorité 2: Haute priorité (ambre)
    if (piano.status === 'top') return 'bg-amber-200';

    // Priorité 3: Travail complété (vert)
    if (piano.status === 'completed' && piano.is_work_completed) return 'bg-green-200';

    // Priorité 4: Travail en cours (bleu)
    // IMPORTANT: Utiliser seulement 'travail' pour éviter confusion avec 'observations' Gazelle (donateur, etc.)
    if (piano.status === 'work_in_progress' ||
        (piano.travail && piano.travail.trim() !== '' && !piano.is_work_completed)) {
      return 'bg-blue-200';
    }

    // Priorité 5: Proposé, à faire = jaune
    if (piano.status === 'proposed' || (piano.aFaire && piano.aFaire.trim() !== '')) {
      return 'bg-yellow-200';
    }

    // Par défaut: blanc
    return 'bg-white';
  };

  // Fonction helper pour icône sync status
  const getSyncStatusIcon = (syncStatus) => {
    switch (syncStatus) {
      case 'pending': return '⏳';
      case 'pushed': return '✅';
      case 'modified': return '🔄';
      case 'error': return '⚠️';
      default: return '';
    }
  };

  // Fonction push vers Gazelle
  const handlePushToGazelle = async () => {
    if (readyForPushCount === 0) {
      alert('Aucun piano prêt pour être envoyé à Gazelle.');
      return;
    }

    if (!confirm(`Envoyer ${readyForPushCount} piano(s) vers Gazelle?`)) {
      return;
    }

    setPushInProgress(true);

    try {
      const response = await fetch(`${API_URL}/api/${institution}/push-to-gazelle`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          technician_id: 'usr_HcCiFk7o0vZ9xAI0', // Nick par défaut
          dry_run: false
        })
      });

      const result = await response.json();

      if (result.success) {
        alert(`✅ ${result.pushed_count}/${result.total_pianos} piano(s) envoyé(s) avec succès!`);
        await loadPianosFromAPI(); // Recharger pour mettre à jour sync_status
      } else {
        alert(`⚠️ ${result.pushed_count || 0}/${result.total_pianos || 0} piano(s) envoyé(s), ${result.error_count || 0} erreur(s).\n\nVoir console pour détails.`);
        console.error('Erreurs push:', result.results?.filter(r => r.status === 'error') || []);
      }
    } catch (err) {
      alert(`❌ Erreur lors du push: ${err.message}`);
      console.error(err);
    } finally {
      setPushInProgress(false);
    }
  };

  // Gestion des états de chargement et d'erreur (pour toutes les vues)
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
      <div className="min-h-screen bg-gray-100 flex items-center justify-center p-4">
        <div className="text-center bg-white p-6 rounded-lg shadow max-w-md w-full">
          <div className="text-red-600 mb-2 text-lg font-semibold">⚠️ Erreur</div>
          <div className="text-sm text-gray-600 mb-4">{error}</div>
          <button
            onClick={() => {
              setError(null);
              loadPianosFromAPI();
            }}
            className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
          >
            Réessayer
          </button>
        </div>
      </div>
    );
  }

  // ============ NAVIGATION UNIFIÉE ============
  // Composant externe pour la navigation (pill buttons)

  // ============ VUE MODE VDI (review travail des techniciens) ============
  if (currentView === 'vdi') {
    const pianosAvecTravail = pianos.filter(p => p.travail && p.travail.trim() !== '');
    const pianosCompletes = pianos.filter(p => p.is_work_completed);
    const pianosEnCours = pianosAvecTravail.filter(p => !p.is_work_completed);

    return (
      <div className="min-h-screen bg-gray-100">
        <VDI_Navigation
          currentView={currentView}
          setCurrentView={setCurrentView}
          setSelectedIds={setSelectedIds}
          hideNickView={hideNickView}
        />
        <div className="w-full max-w-lg mx-auto px-4 py-4">
          {/* Résumé */}
          <div className="bg-white rounded-lg shadow p-4 mb-4">
            <div className="text-lg font-semibold text-gray-800 mb-2">Travail des techniciens</div>
            <div className="flex gap-4 text-sm">
              <span className="text-green-700 font-medium">{pianosCompletes.length} complété(s)</span>
              <span className="text-blue-700 font-medium">{pianosEnCours.length} en cours</span>
              <span className="text-gray-500">{pianos.length} total</span>
            </div>
          </div>

          {/* Liste des pianos avec travail */}
          {pianosAvecTravail.length === 0 ? (
            <div className="bg-white rounded-lg shadow p-8 text-center text-gray-500">
              Aucun piano avec du travail effectué pour l'instant.
            </div>
          ) : (
            <div className="space-y-3">
              {pianosAvecTravail.map(piano => (
                <div key={piano.id} className={`bg-white rounded-lg shadow overflow-hidden border-l-4 ${
                  piano.is_work_completed ? 'border-green-500' : 'border-blue-400'
                }`}>
                  <div className="p-4">
                    <div className="flex justify-between items-start mb-2">
                      <div>
                        <span className="font-bold text-gray-800 text-lg">{piano.local}</span>
                        <span className="text-gray-500 ml-2">{piano.piano}{piano.modele ? ` ${piano.modele}` : ''}</span>
                      </div>
                      <span className={`text-xs font-semibold px-2 py-1 rounded-full ${
                        piano.is_work_completed
                          ? 'bg-green-100 text-green-700'
                          : 'bg-blue-100 text-blue-700'
                      }`}>
                        {piano.is_work_completed ? 'Complété' : 'En cours'}
                      </span>
                    </div>
                    {piano.aFaire && (
                      <div className="text-sm text-yellow-800 bg-yellow-50 rounded p-2 mb-2">
                        <span className="font-medium">À faire:</span> {piano.aFaire}
                      </div>
                    )}
                    <div className="text-sm text-gray-700 bg-gray-50 rounded p-2 whitespace-pre-wrap">
                      {piano.travail}
                    </div>
                    {piano.sync_status && (
                      <div className="mt-2 text-xs text-gray-400">
                        Sync: {piano.sync_status}
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    );
  }

  // ============ VUE TECHNICIEN (mobile-friendly) ============
  if (currentView === 'technicien') {
    console.log('🔧 [VincentDIndyDashboard] Rendu vue technicien');
    console.log('🔧 [VincentDIndyDashboard] Props pour VDI_TechnicianView:', {
      selectedInstitutionForTechnician,
      institution,
      finalSelectedInstitution: selectedInstitutionForTechnician || institution
    });
    
    return (
      <div className="min-h-screen bg-gray-100">
        <VDI_Navigation
          currentView={currentView}
          setCurrentView={setCurrentView}
          setSelectedIds={setSelectedIds}
          hideNickView={hideNickView}
        />
        {/* Container simulé téléphone portable - centré avec bordure et ombre */}
        <div className="w-full max-w-md mx-auto px-4 py-4 sm:px-3 sm:py-2">
          <div className="bg-white rounded-lg shadow-lg border border-gray-200 overflow-hidden">
            <VDI_TechnicianView
              pianos={pianos}
              stats={stats}
              showOnlyProposed={showOnlyProposed}
              setShowOnlyProposed={setShowOnlyProposed}
              searchLocal={searchLocal}
              setSearchLocal={setSearchLocal}
              expandedPianoId={expandedPianoId}
              setExpandedPianoId={setExpandedPianoId}
              travailInput={travailInput}
              setTravailInput={setTravailInput}
              saveTravail={saveTravail}
              moisDepuisAccord={moisDepuisAccord}
              formatDateRelative={formatDateRelative}
              pianosFiltres={pianosFiltres}
              selectedInstitution={selectedInstitutionForTechnician || institution}
              setSelectedInstitution={setSelectedInstitutionForTechnician}
              onInstitutionChange={handleInstitutionChangeForTechnician}
            />
                      </div>
        </div>
      </div>
    );
  }

  // ============ VUE NICOLAS (Gestion & Pianos) ============
  // Si on arrive ici, c'est que currentView === 'nicolas' (ou autre vue non-technicien)
  return (
    <div className="min-h-screen bg-gray-100 p-4">
      {/* Navigation unifiée */}
      <VDI_Navigation
        currentView={currentView}
        setCurrentView={setCurrentView}
        setSelectedIds={setSelectedIds}
        hideNickView={hideNickView}
      />

        {/* Vue Gestion & Pianos */}
        {currentView === 'nicolas' && (
          <VDI_ManagementView
            pianosFiltres={pianosFiltres}
            pianos={pianos}
            setPianos={setPianos}
            stats={stats}
            institution={institution}
            currentUser={currentUser}
            setShowOnlySelected={setShowOnlySelected}
            showOnlySelected={showOnlySelected}
            showAllPianos={showAllPianos}
            setShowAllPianos={setShowAllPianos}
            filterUsage={filterUsage}
            setFilterUsage={setFilterUsage}
            filterAccordDepuis={filterAccordDepuis}
            setFilterAccordDepuis={setFilterAccordDepuis}
            usages={usages}
            selectedIds={selectedIds}
            setSelectedIds={setSelectedIds}
            selectAllCheckboxRef={selectAllCheckboxRef}
            loadPianosFromAPI={loadPianosFromAPI}
            loading={loading}
            selectAll={selectAll}
            deselectAll={deselectAll}
            toggleProposed={toggleProposed}
            toggleSelected={toggleSelected}
            batchSetStatus={batchSetStatus}
            batchSetUsage={batchSetUsage}
            batchHideFromInventory={batchHideFromInventory}
            handlePushToGazelle={handlePushToGazelle}
            savePianoToAPI={savePianoToAPI}
            readyForPushCount={readyForPushCount}
            pushInProgress={pushInProgress}
            editingAFaireId={editingAFaireId}
            setEditingAFaireId={setEditingAFaireId}
            aFaireInput={aFaireInput}
            setAFaireInput={setAFaireInput}
            editingNotesId={editingNotesId}
            setEditingNotesId={setEditingNotesId}
            notesInput={notesInput}
            setNotesInput={setNotesInput}
            sortConfig={sortConfig}
            handleSort={handleSort}
            getRowClass={getRowClass}
            moisDepuisAccord={moisDepuisAccord}
            formatDateRelative={formatDateRelative}
            getSyncStatusIcon={getSyncStatusIcon}
            filterEtage={filterEtage}
            setFilterEtage={setFilterEtage}
          />
        )}
    </div>
  );
};

export default VincentDIndyDashboard;
