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

  // Pour vue "À valider" - édition inline des notes technicien
  const [editingTravailId, setEditingTravailId] = useState(null);
  const [editingTravailText, setEditingTravailText] = useState('');
  const [editingHistoryId, setEditingHistoryId] = useState(null);
  const [editingHistoryText, setEditingHistoryText] = useState('');

  // Historique des services validés/poussés
  const [serviceHistory, setServiceHistory] = useState([]);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [tourneeInProgress, setTourneeInProgress] = useState(false);

  // Historique Gazelle (timeline_entries) - accordéon dans vue "À valider"
  const [expandedGazelleHistoryId, setExpandedGazelleHistoryId] = useState(null);
  const [gazelleHistoryData, setGazelleHistoryData] = useState({});
  const [gazelleHistoryLoading, setGazelleHistoryLoading] = useState(false);

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

  // Charger l'historique des services poussés (nouveau système piano_service_records)
  const loadServiceHistory = useCallback(async () => {
    setHistoryLoading(true);
    try {
      const r = await fetch(`${API_URL}/api/service-records/${institution}/history?limit=100`);
      if (r.ok) {
        const data = await r.json();
        // Transformer les records en format compatible avec l'affichage historique
        const records = (data.records || []).map(rec => ({
          id: rec.id,
          piano_id: rec.piano_id,
          gazelle_piano_id: rec.piano_id,
          piano_local: rec.piano_local || '',
          piano_name: rec.piano_name || '',
          a_faire: rec.a_faire || '',
          travail: rec.travail || '',
          observations: rec.observations || '',
          service_date: rec.completed_at || rec.pushed_at || '',
          validated_at: rec.validated_at || '',
          pushed_at: rec.pushed_at || '',
          status: rec.status,
          gazelle_event_id: rec.gazelle_event_id || '',
          created_at: rec.created_at || '',
        }));
        setServiceHistory(records);
      }
    } catch (e) {
      console.error('Erreur chargement historique:', e);
    } finally {
      setHistoryLoading(false);
    }
  }, [institution]);

  // Fonction pour sauvegarder un piano via l'API
  const savePianoToAPI = async (pianoId, updates) => {
    try {
      // Ajouter automatiquement la signature de l'utilisateur
      const updatesWithUser = {
        ...updates,
        updated_by: currentUser?.email || currentUser?.name || 'Unknown'
      };

      // Préfixer le champ travail avec [INITIALES] pour identifier l'auteur
      if (updatesWithUser.travail !== undefined && updatesWithUser.travail.trim() !== '') {
        const initials = currentUser?.initials || currentUser?.name?.[0] || '?';
        const prefix = `[${initials}]`;
        if (!updatesWithUser.travail.startsWith(prefix)) {
          // Remplacer un éventuel préfixe existant d'un autre utilisateur
          const textWithoutPrefix = updatesWithUser.travail.replace(/^\[.+?\]\s*/, '');
          updatesWithUser.travail = `${prefix} ${textWithoutPrefix}`;
        }
      }

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

    // Cycle à 3 états : blanc → jaune (à faire) → ambre (Top) → blanc
    let newStatus;
    let label;
    if (piano.status === 'normal' || !piano.status) {
      newStatus = 'proposed';
      label = 'À faire';
    } else if (piano.status === 'proposed') {
      newStatus = 'top';
      label = 'Top priorité';
    } else if (piano.status === 'top') {
      newStatus = 'normal';
      label = 'Normal';
    } else {
      newStatus = 'normal';
      label = 'Normal';
    }

    if (!window.confirm(`Changer le statut de ${piano.local || piano.piano} à « ${label} » ?`)) return;

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

  // Technicien - marquer un piano comme terminé (bouton ✓)
  // Utilise la nouvelle API fiches de service
  const markWorkCompleted = async (id, completed = true) => {
    // Mise à jour optimiste
    setPianos(pianos.map(p =>
      p.id === id ? { ...p, is_work_completed: completed } : p
    ));

    const inst = selectedInstitutionForTechnician || institution;
    try {
      await fetch(`${API_URL}/api/service-records/${inst}/piano/${id}/complete`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ completed_by: currentUser?.email || currentUser?.name || '' })
      });
    } catch (e) {
      console.error('Erreur markWorkCompleted via service-records:', e);
      // Fallback: ancienne API
      await savePianoToAPI(id, { isWorkCompleted: completed });
    }
  };

  // Technicien - auto-save (appelé par debounce dans VDI_TechnicianView)
  // Utilise la nouvelle API fiches de service
  const saveTravail = async (id, value) => {
    const noteValue = value !== undefined ? value : travailInput;
    const piano = pianos.find(p => p.id === id);
    if (!piano) return;

    // Auto-préfixer les initiales du technicien (ex: [AB], [NG], [GL])
    let noteToSave = noteValue;
    const initials = currentUser?.initials;
    if (initials && noteToSave.trim() && !noteToSave.startsWith(`[${initials}]`)) {
      noteToSave = noteToSave.replace(/^\[.+?\]\s*/, '');
      noteToSave = `[${initials}] ${noteToSave}`;
    }

    // Mise à jour optimiste
    setPianos(pianos.map(p =>
      p.id === id ? { ...p, travail: noteToSave, status: noteToSave ? 'work_in_progress' : p.status } : p
    ));

    const inst = selectedInstitutionForTechnician || institution;
    try {
      await fetch(`${API_URL}/api/service-records/${inst}/piano/${id}/notes`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          travail: noteToSave,
          technician_email: currentUser?.email || ''
        })
      });
    } catch (e) {
      console.error('Erreur saveTravail via service-records:', e);
      // Fallback: ancienne API
      await savePianoToAPI(id, { travail: noteToSave });
    }
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

  // Charger l'historique quand on passe sur l'onglet "À valider"
  useEffect(() => {
    if (currentView === 'vdi') {
      loadServiceHistory();
    }
  }, [currentView, loadServiceHistory]);

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
      proposed: pianos.filter(p => p && p.status === 'proposed').length,
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

    // Priorité 2: Top priorité (ambre)
    if (piano.status === 'top') return 'bg-orange-200';

    // Priorité 3: Proposé (jaune)
    if (piano.status === 'proposed') {
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

  // --- Chargement historique Gazelle (utilisé par vue "À valider") ---
  const loadGazelleHistory = async (pianoId, gazelleId) => {
    const idToFetch = gazelleId || pianoId;
    if (!idToFetch) return;
    if (gazelleHistoryData[idToFetch]) return;

    setGazelleHistoryLoading(true);
    try {
      console.log('[À valider] Chargement historique pour piano:', idToFetch);
      const r = await fetch(`${API_URL}/api/vincent-dindy/pianos/${idToFetch}/timeline?limit=200`);
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const data = await r.json();
      console.log('[À valider] Données brutes:', data.entries?.slice(0, 2));

      const entries = (data.entries || []).map(e => ({
        date: e.date || '',
        text: e.summary || e.comment || '',
        entry_type: e.type || 'NOTE',
        user: e.user || '',
        source: e.source || 'gazelle'
      })).filter(e => e.text.trim());

      console.log('[À valider] Entrées transformées:', entries.slice(0, 2));

      setGazelleHistoryData(prev => ({
        ...prev,
        [idToFetch]: entries
      }));
    } catch (e) {
      console.error('Erreur chargement historique:', e);
      setGazelleHistoryData(prev => ({
        ...prev,
        [idToFetch]: []
      }));
    } finally {
      setGazelleHistoryLoading(false);
    }
  };

  // ============ Données "À VALIDER" — calculées avant les early returns pour respecter les hooks ============
  // Utilise service_record.status (nouveau système piano_service_records)
  // Pianos pending = ont une fiche draft ou completed (technicien a travaillé)
  const pendingPianos = useMemo(() => pianos
    .filter(p => {
      const srStatus = p.service_record?.status;
      return srStatus === 'draft' || srStatus === 'completed';
    })
    .map(p => ({
      _type: 'pending',
      _key: `pending-${p.id}`,
      _sortDate: p.service_record?.completed_at || p.updated_at || p.dernierAccord || '1970-01-01',
      pianoId: p.id,
      gazelleId: p.gazelleId || p.id,
      local: p.local,
      pianoName: `${p.piano}${p.modele ? ` ${p.modele}` : ''}`,
      aFaire: p.aFaire || '',
      travail: p.travail,
      serviceDate: p.service_record?.completed_at || p.updated_at || '',
      status: 'pending',
      isCompleted: p.service_record?.status === 'completed',
    })), [pianos]);

  // Pianos validés (notes visibles, en attente de push)
  const validatedPianos = useMemo(() => pianos
    .filter(p => p.service_record?.status === 'validated')
    .map(p => ({
      _type: 'validated_piano',
      _key: `vp-${p.id}`,
      _sortDate: p.service_record?.completed_at || p.updated_at || p.dernierAccord || '1970-01-01',
      pianoId: p.id,
      gazelleId: p.gazelleId || p.id,
      local: p.local,
      pianoName: `${p.piano}${p.modele ? ` ${p.modele}` : ''}`,
      aFaire: p.aFaire || '',
      travail: p.travail || '',
      serviceDate: p.service_record?.completed_at || p.updated_at || '',
      status: 'validated',
    })), [pianos]);

  // Pianos poussés — plus besoin car le push nettoie les fiches
  // Les fiches pushed sont dans l'historique (piano_service_records avec status=pushed)
  const pushedPianos = useMemo(() => [], []);

  // Fonction de chargement d'historique Gazelle (définie ici pour le useEffect)
  const loadGazelleHistoryForPreload = useCallback(async (pianoId, gazelleId) => {
    const idToFetch = gazelleId || pianoId;
    if (!idToFetch || gazelleHistoryData[idToFetch]) return;
    try {
      const r = await fetch(`${API_URL}/api/vincent-dindy/pianos/${idToFetch}/timeline?limit=200`);
      if (!r.ok) return;
      const data = await r.json();
      const entries = (data.entries || []).map(e => ({
        date: e.date || '',
        text: e.summary || e.comment || '',
        entry_type: e.type || 'NOTE',
        user: e.user || '',
        source: e.source || 'gazelle'
      })).filter(e => e.text.trim());
      setGazelleHistoryData(prev => ({ ...prev, [idToFetch]: entries }));
    } catch (e) {
      setGazelleHistoryData(prev => ({ ...prev, [idToFetch]: [] }));
    }
  }, [gazelleHistoryData]);

  // Pré-chargement de l'historique pour les pianos pending/validated/pushed
  useEffect(() => {
    if (currentView !== 'vdi') return;
    const loadHistoryForPianos = async () => {
      const idsToLoad = [];
      [...pendingPianos, ...validatedPianos, ...pushedPianos].forEach(row => {
        const id = row.gazelleId || row.pianoId;
        if (id && !gazelleHistoryData[id]) {
          idsToLoad.push({ pianoId: row.pianoId, gazelleId: row.gazelleId });
        }
      });
      for (let i = 0; i < idsToLoad.length; i += 5) {
        const batch = idsToLoad.slice(i, i + 5);
        await Promise.all(batch.map(({ pianoId, gazelleId }) =>
          loadGazelleHistoryForPreload(pianoId, gazelleId)
        ));
      }
    };
    if (pendingPianos.length > 0 || validatedPianos.length > 0 || pushedPianos.length > 0) {
      loadHistoryForPianos();
    }
  }, [currentView, pendingPianos.length, validatedPianos.length, pushedPianos.length, loadGazelleHistoryForPreload]);

  // ============ EARLY RETURNS (après tous les hooks) ============
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

  // ============ VUE "À VALIDER" — liste unifiée avec historique ============
  if (currentView === 'vdi') {
    // Entrées historique (from piano_service_records pushed)
    // Enrichir avec les données piano locales (local, nom)
    const pianoLookup = {};
    pianos.forEach(p => { pianoLookup[p.id] = p; });

    // Dédoublonner : exclure les pianos déjà représentés par pendingPianos/validatedPianos
    const livePianoIds = new Set([
      ...pendingPianos.map(p => p.pianoId),
      ...validatedPianos.map(p => p.pianoId),
    ]);
    const historyRows = serviceHistory
      .filter(h => !livePianoIds.has(h.piano_id))
      .map(h => {
        const piano = pianoLookup[h.piano_id] || {};
        return {
          _type: 'history',
          _key: `history-${h.id}`,
          _sortDate: h.service_date || h.validated_at || h.created_at || '1970-01-01',
          entryId: h.id,
          pianoId: h.piano_id,
          gazelleId: h.piano_id,
          local: h.piano_local || piano.local || '',
          pianoName: h.piano_name || `${piano.piano || ''}${piano.modele ? ` ${piano.modele}` : ''}`,
          aFaire: h.a_faire || '',
          travail: h.travail || '',
          serviceDate: h.service_date || '',
          status: h.status,
          validatedAt: h.validated_at,
          pushedAt: h.pushed_at,
          gazelleEventId: h.gazelle_event_id,
        };
      });

    // Liste unifiée, anti-chronologique
    const allRows = [...pendingPianos, ...validatedPianos, ...pushedPianos, ...historyRows]
      .sort((a, b) => (b._sortDate || '').localeCompare(a._sortDate || ''));

    const pendingCount = pendingPianos.length;
    const validatedCount = validatedPianos.length;
    const pushedCount = pushedPianos.length;

    // --- Actions --- (utilise le nouveau système piano_service_records)
    const handleValidate = async (pianoId) => {
      try {
        const r = await fetch(`${API_URL}/api/service-records/${institution}/validate`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            piano_ids: [pianoId],
            validated_by: currentUser?.email || currentUser?.name || 'Unknown',
          }),
        });
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        // Recharger pianos pour refléter le nouveau status de la fiche
        await loadPianosFromAPI();
        await loadServiceHistory();
      } catch (e) {
        alert('Erreur validation: ' + e.message);
      }
    };

    const handleValidateAll = async () => {
      if (pendingCount === 0) return;
      // Ne valider que les fiches "completed" (technicien a cliqué Terminé)
      const completedPianos = pendingPianos.filter(p => p.isCompleted);
      if (completedPianos.length === 0) {
        alert('Aucun piano marqué "Terminé" par le technicien. Seuls les pianos terminés peuvent être validés.');
        return;
      }
      if (!confirm(`Valider ${completedPianos.length} piano(s) terminé(s)?`)) return;
      try {
        const ids = completedPianos.map(p => p.pianoId);
        const r = await fetch(`${API_URL}/api/service-records/${institution}/validate`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            piano_ids: ids,
            validated_by: currentUser?.email || currentUser?.name || 'Unknown',
          }),
        });
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        await loadPianosFromAPI();
        await loadServiceHistory();
      } catch (e) {
        alert('Erreur validation: ' + e.message);
      }
    };

    const handlePushToGazelle = async () => {
      if (validatedCount === 0) return;
      if (!confirm(`Pousser ${validatedCount} piano(s) validé(s) vers Gazelle?`)) return;
      setPushInProgress(true);
      try {
        const r = await fetch(`${API_URL}/api/service-records/${institution}/push`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({}),
        });
        const data = await r.json();
        if (data.success && data.pushed_count > 0) {
          alert(`${data.pushed_count} fiche(s) poussée(s) vers Gazelle.`);
        } else if (data.pushed_count === 0) {
          alert('Aucune fiche à pousser.');
        } else {
          alert('Erreur: ' + JSON.stringify(data));
        }
        await loadPianosFromAPI();
        await loadServiceHistory();
      } catch (e) {
        alert('Erreur push: ' + e.message);
      } finally {
        setPushInProgress(false);
      }
    };

    // Nettoyage des anciens services (overlays legacy + fiches orphelines)
    const handleCleanup = async () => {
      if (!confirm('Nettoyer tous les anciens services résiduels? Cela va:\n- Vider les notes legacy des overlays\n- Abandonner les fiches draft/completed orphelines')) return;
      setTourneeInProgress(true);
      try {
        const r = await fetch(`${API_URL}/api/vincent-dindy/service-history/tournee-terminee?institution_slug=${institution}`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({}),
        });
        const data = await r.json();
        if (data.success) {
          alert(`Nettoyage terminé: ${data.total_cleaned} entrée(s) nettoyée(s).`);
          await loadPianosFromAPI();
          await loadServiceHistory();
        } else {
          alert('Erreur: ' + (data.detail || JSON.stringify(data)));
        }
      } catch (e) {
        alert('Erreur nettoyage: ' + e.message);
      } finally {
        setTourneeInProgress(false);
      }
    };

    const handleSaveHistoryEdit = async () => {
      if (!editingHistoryId) return;
      try {
        const r = await fetch(`${API_URL}/api/vincent-dindy/service-history/${editingHistoryId}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ travail: editingHistoryText }),
        });
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        setEditingHistoryId(null);
        setEditingHistoryText('');
        await loadServiceHistory();
      } catch (e) {
        alert('Erreur sauvegarde: ' + e.message);
      }
    };

    const toggleGazelleHistory = (pianoId, gazelleId) => {
      const idToUse = gazelleId || pianoId;
      if (expandedGazelleHistoryId === idToUse) {
        // Fermer si on clique sur le même piano
        setExpandedGazelleHistoryId(null);
      } else {
        // Ouvrir ce piano (ferme automatiquement l'autre)
        setExpandedGazelleHistoryId(idToUse);
        loadGazelleHistory(pianoId, gazelleId);
      }
    };

    // Cliquer sur une ligne = ouvrir son historique
    const handleRowClick = (row) => {
      const idToUse = row.gazelleId || row.pianoId;
      // Si déjà ouvert sur ce piano, ne rien faire (laisser l'utilisateur lire)
      if (expandedGazelleHistoryId === idToUse) return;
      // Sinon, ouvrir l'historique de ce piano
      setExpandedGazelleHistoryId(idToUse);
      loadGazelleHistory(row.pianoId, row.gazelleId);
    };

    // --- Badge statut ---
    const StatusBadge = ({ status }) => {
      const cfg = {
        pending:   { bg: 'bg-blue-100',  text: 'text-blue-700',  label: 'À valider' },
        validated: { bg: 'bg-green-100', text: 'text-green-700', label: 'Validé' },
        pushed:    { bg: 'bg-gray-100',  text: 'text-gray-500',  label: 'Poussé' },
        error:     { bg: 'bg-red-100',   text: 'text-red-700',   label: 'Erreur' },
      };
      const c = cfg[status] || cfg.pending;
      return (
        <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold ${c.bg} ${c.text}`}>
          {c.label}
        </span>
      );
    };

    // --- Rendu notes avec édition inline ---
    const NotesCell = ({ row }) => {
      // Obtenir le dernier service de l'historique pour ce piano
      const historyId = row.gazelleId || row.pianoId;
      const historyEntries = gazelleHistoryData[historyId] || [];
      const lastService = historyEntries.length > 0 ? historyEntries[0] : null;

      // Composant pour afficher le dernier service (réutilisé)
      const LastServiceDisplay = () => {
        if (!lastService) return null;
        const dateStr = lastService.date ? (() => {
          try {
            const d = new Date(lastService.date);
            if (isNaN(d.getTime())) return lastService.date.slice(0, 10);
            return d.toLocaleDateString('fr-CA', { day: 'numeric', month: 'short', year: '2-digit' });
          } catch {
            return lastService.date.slice(0, 10) || '';
          }
        })() : '';

        return (
          <div className="mt-1.5 pt-1.5 border-t border-gray-200">
            <div className="text-[10px] text-gray-400 mb-0.5">Dernier service {dateStr ? `(${dateStr})` : ''}</div>
            <div className="text-[11px] text-gray-500 line-clamp-2">{lastService.text}</div>
          </div>
        );
      };

      // Pending → edit via piano directly
      if (row._type === 'pending') {
        if (editingTravailId === row.pianoId) {
          return (
            <div className="space-y-1.5">
              <textarea
                value={editingTravailText}
                onChange={(e) => setEditingTravailText(e.target.value)}
                className="w-full border border-blue-300 rounded p-2 text-xs h-24 resize-y focus:outline-none focus:ring-2 focus:ring-blue-300"
                autoFocus
              />
              <div className="flex gap-1.5">
                <button
                  onClick={async () => {
                    setPianos(pianos.map(p =>
                      p.id === row.pianoId ? { ...p, travail: editingTravailText } : p
                    ));
                    await savePianoToAPI(row.pianoId, { travail: editingTravailText });
                    setEditingTravailId(null);
                  }}
                  className="px-2 py-1 text-xs font-medium rounded bg-blue-500 text-white hover:bg-blue-600"
                >Sauvegarder</button>
                <button
                  onClick={() => setEditingTravailId(null)}
                  className="px-2 py-1 text-xs font-medium rounded bg-gray-200 text-gray-700 hover:bg-gray-300"
                >Annuler</button>
              </div>
              <LastServiceDisplay />
            </div>
          );
        }
        return (
          <div>
            <div
              onClick={(e) => { e.stopPropagation(); setEditingTravailId(row.pianoId); setEditingTravailText(row.travail); }}
              className="whitespace-pre-wrap cursor-pointer hover:bg-blue-50 hover:text-blue-700 rounded px-1 -mx-1 py-0.5 transition-colors"
              title="Cliquer pour modifier"
            >{row.travail}</div>
            <LastServiceDisplay />
          </div>
        );
      }

      // Validated piano (live, from piano row) → read-only with green styling
      if (row._type === 'validated_piano') {
        // Editable via history entry (Nicolas peut corriger avant push)
        if (editingHistoryId === `vp-${row.pianoId}`) {
          return (
            <div className="space-y-1.5">
              <textarea
                value={editingHistoryText}
                onChange={(e) => setEditingHistoryText(e.target.value)}
                className="w-full border border-green-300 rounded p-2 text-xs h-24 resize-y focus:outline-none focus:ring-2 focus:ring-green-300"
                autoFocus
              />
              <div className="flex gap-1.5">
                <button
                  onClick={async () => {
                    // Sauvegarder via l'API service-records (fiche active du piano)
                    try {
                      await fetch(`${API_URL}/api/service-records/${institution}/piano/${row.pianoId}/notes`, {
                        method: 'PUT',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ travail: editingHistoryText }),
                      });
                    } catch (e) {
                      console.error('Erreur sauvegarde:', e);
                    }
                    setEditingHistoryId(null);
                    setEditingHistoryText('');
                    await loadPianosFromAPI();
                  }}
                  className="px-2 py-1 text-xs font-medium rounded bg-green-500 text-white hover:bg-green-600"
                >Sauvegarder</button>
                <button
                  onClick={() => setEditingHistoryId(null)}
                  className="px-2 py-1 text-xs font-medium rounded bg-gray-200 text-gray-700 hover:bg-gray-300"
                >Annuler</button>
              </div>
            </div>
          );
        }
        return (
          <div
            onClick={() => { setEditingHistoryId(`vp-${row.pianoId}`); setEditingHistoryText(row.travail); }}
            className="whitespace-pre-wrap cursor-pointer hover:bg-green-50 hover:text-green-700 rounded px-1 -mx-1 py-0.5 transition-colors"
            title="Cliquer pour modifier avant le push"
          >{row.travail}</div>
        );
      }

      // History entries (pushed) → read-only
      if (row._type === 'history') {
        return <div className="whitespace-pre-wrap text-gray-500">{row.travail}</div>;
      }

      // Pushed → read-only
      return <div className="whitespace-pre-wrap text-gray-500">{row.travail}</div>;
    };

    return (
      <div className="min-h-screen bg-gray-100">
        <VDI_Navigation
          currentView={currentView}
          setCurrentView={setCurrentView}
          setSelectedIds={setSelectedIds}
          hideNickView={hideNickView}
        />
        <div className="w-full max-w-7xl mx-auto px-4 py-4 space-y-4">

          {/* Barre d'actions */}
          <div className="flex items-center justify-between flex-wrap gap-2">
            <div className="flex items-center gap-3">
              {pendingCount > 0 && (
                <span className="text-xs font-semibold text-blue-700 bg-blue-50 px-2 py-1 rounded-full">
                  {pendingCount} à valider
                </span>
              )}
              {validatedCount > 0 && (
                <span className="text-xs font-semibold text-green-700 bg-green-50 px-2 py-1 rounded-full">
                  {validatedCount} validé{validatedCount > 1 ? 's' : ''} (à pousser)
                </span>
              )}
              {serviceHistory.length > 0 && (
                <span className="text-xs font-semibold text-gray-600 bg-gray-100 px-2 py-1 rounded-full">
                  {serviceHistory.length} historique
                </span>
              )}
              {allRows.length === 0 && !historyLoading && (
                <span className="text-sm text-gray-500">Aucune entrée.</span>
              )}
            </div>
            <div className="flex gap-2">
              {pendingCount > 0 && (
                <button
                  onClick={handleValidateAll}
                  className="px-3 py-1.5 text-xs font-medium bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors"
                >
                  Valider tout ({pendingCount})
                </button>
              )}
              {validatedCount > 0 && (
                <button
                  onClick={handlePushToGazelle}
                  disabled={pushInProgress}
                  className="px-3 py-1.5 text-xs font-medium bg-orange-500 text-white rounded-lg hover:bg-orange-600 disabled:opacity-50 transition-colors"
                >
                  {pushInProgress ? 'Envoi...' : `Pousser vers Gazelle (${validatedCount})`}
                </button>
              )}
              <button
                onClick={handleCleanup}
                disabled={tourneeInProgress}
                className="px-3 py-1.5 text-xs font-medium bg-gray-500 text-white rounded-lg hover:bg-gray-600 disabled:opacity-50 transition-colors"
              >
                {tourneeInProgress ? 'Nettoyage...' : 'Nettoyer anciens'}
              </button>
            </div>
          </div>

          {/* Tableau unifié */}
          {historyLoading && allRows.length === 0 ? (
            <div className="bg-white rounded-lg shadow p-6 text-center text-gray-500">Chargement...</div>
          ) : allRows.length === 0 ? (
            <div className="bg-white rounded-lg shadow p-6 text-center text-gray-500">
              Aucun service en attente de validation ou dans l'historique.
            </div>
          ) : (
            <div className="bg-white rounded-lg shadow overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-gray-50 border-b text-left text-xs font-medium text-gray-500 uppercase">
                    <th className="px-3 py-2 w-20">Statut</th>
                    <th className="px-3 py-2">Local</th>
                    <th className="px-3 py-2">Piano</th>
                    <th className="px-3 py-2">À faire</th>
                    <th className="px-3 py-2">Notes technicien</th>
                    <th className="px-3 py-2 w-24">Service</th>
                    <th className="px-3 py-2 w-28 text-center">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {allRows.map(row => {
                    const historyId = row.gazelleId || row.pianoId;
                    const isExpanded = expandedGazelleHistoryId === historyId;
                    const historyEntries = gazelleHistoryData[historyId] || [];

                    return (
                      <React.Fragment key={row._key}>
                        <tr
                          onClick={() => handleRowClick(row)}
                          className={`cursor-pointer ${
                            row.status === 'pending' ? 'bg-blue-50/30 hover:bg-blue-50' :
                            row.status === 'validated' ? 'bg-green-50/30 hover:bg-green-50' :
                            row.status === 'error' ? 'bg-red-50/30' :
                            'bg-gray-50/30 hover:bg-gray-50'
                          }`}
                        >
                          <td className="px-3 py-2"><StatusBadge status={row.status} /></td>
                          <td className="px-3 py-2 font-medium whitespace-nowrap">{row.local}</td>
                          <td className="px-3 py-2 whitespace-nowrap text-gray-600">{row.pianoName}</td>
                          <td className="px-3 py-2 text-xs text-gray-600">{row.aFaire || '-'}</td>
                          <td className="px-3 py-2 text-xs text-gray-800 max-w-md">
                            <NotesCell row={row} />
                          </td>
                          <td className="px-3 py-2 text-[10px] text-gray-400 whitespace-nowrap">
                            {row.serviceDate ? new Date(row.serviceDate).toLocaleDateString('fr-CA', { day: 'numeric', month: 'short' }) : '-'}
                          </td>
                          <td className="px-3 py-2 text-center">
                            <div className="flex items-center justify-center gap-1">
                              {row.status === 'pending' && (
                                <button
                                  onClick={() => handleValidate(row.pianoId)}
                                  className="px-2 py-1 text-xs font-medium bg-green-500 text-white rounded hover:bg-green-600 transition-colors"
                                >
                                  Valider
                                </button>
                              )}
                              <button
                                onClick={() => toggleGazelleHistory(row.pianoId, row.gazelleId)}
                                className={`p-1 rounded transition-colors ${
                                  isExpanded
                                    ? 'text-blue-600 bg-blue-100'
                                    : 'text-gray-400 hover:text-blue-600'
                                }`}
                                title="Voir l'historique d'entretien"
                              >
                                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                                </svg>
                              </button>
                            </div>
                          </td>
                        </tr>
                        {/* Accordéon historique */}
                        {isExpanded && (
                          <tr className="bg-blue-50/50">
                            <td colSpan="7" className="px-4 py-3">
                              <div className="text-xs font-semibold text-blue-800 mb-2">
                                📋 Historique de Service {gazelleHistoryLoading ? '(chargement...)' : `(${historyEntries.length} entrées)`}
                              </div>
                              {gazelleHistoryLoading ? (
                                <div className="text-xs text-gray-500 italic">Chargement de l'historique...</div>
                              ) : historyEntries.length === 0 ? (
                                <div className="text-xs text-gray-500 italic">Aucun historique trouvé pour ce piano.</div>
                              ) : (
                                <div className="space-y-1.5 max-h-64 overflow-y-auto pr-2">
                                  {historyEntries.map((entry, idx) => (
                                    <div
                                      key={idx}
                                      className="bg-white p-2 rounded border-l-4 border-blue-400 shadow-sm"
                                    >
                                      <div className="flex items-start gap-2 text-[11px]">
                                        <span className="text-blue-600 font-medium min-w-[75px]">
                                          {(() => {
                                            if (!entry.date) return '—';
                                            try {
                                              const d = new Date(entry.date);
                                              if (isNaN(d.getTime())) return entry.date.slice(0, 10);
                                              return d.toLocaleDateString('fr-CA', { day: 'numeric', month: 'short', year: '2-digit' });
                                            } catch {
                                              return entry.date.slice(0, 10) || '—';
                                            }
                                          })()}
                                        </span>
                                        <span className={`uppercase min-w-[55px] font-medium ${
                                          entry.entry_type === 'SERVICE' ? 'text-green-600' :
                                          entry.entry_type === 'MEASUREMENT' ? 'text-purple-600' :
                                          'text-gray-400'
                                        }`}>
                                          {entry.entry_type === 'SERVICE_ENTRY_MANUAL' ? 'Service' :
                                           entry.entry_type === 'MEASUREMENT' ? 'Mesure' :
                                           entry.entry_type === 'SERVICE' ? (entry.source === 'local' ? 'Local' : 'Service') :
                                           entry.entry_type || 'Note'}
                                        </span>
                                        {entry.user && (
                                          <span className="text-gray-400 min-w-[80px]">{entry.user}</span>
                                        )}
                                        <p className="text-gray-700 whitespace-pre-wrap flex-1 line-clamp-2">
                                          {entry.text}
                                        </p>
                                      </div>
                                    </div>
                                  ))}
                                </div>
                              )}
                            </td>
                          </tr>
                        )}
                      </React.Fragment>
                    );
                  })}
                </tbody>
              </table>
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
              markWorkCompleted={markWorkCompleted}
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
            savePianoToAPI={savePianoToAPI}
            editingAFaireId={editingAFaireId}
            setEditingAFaireId={setEditingAFaireId}
            aFaireInput={aFaireInput}
            setAFaireInput={setAFaireInput}
            sortConfig={sortConfig}
            handleSort={handleSort}
            getRowClass={getRowClass}
            moisDepuisAccord={moisDepuisAccord}
            formatDateRelative={formatDateRelative}
            filterEtage={filterEtage}
            setFilterEtage={setFilterEtage}
            handlePushToGazelle={handlePushToGazelle}
            readyForPushCount={readyForPushCount}
            pushInProgress={pushInProgress}
          />
        )}
    </div>
  );
};

export default VincentDIndyDashboard;
