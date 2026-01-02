// LOG: Début du fichier VincentDIndyDashboard.jsx
console.log('[VincentDIndyDashboard] Fichier chargé - ligne 1');

import React, { useState, useMemo, useEffect, useRef } from 'react';
import { submitReport, getReports, getPianos, updatePiano } from '../api/vincentDIndyApi';

// Configuration de l'API - utiliser le proxy Vite en développement
const API_URL = import.meta.env.VITE_API_URL || (import.meta.env.DEV ? '' : 'https://assistant-gazelle-v5-api.onrender.com');

const VincentDIndyDashboard = ({ currentUser, initialView = 'nicolas', hideNickView = false, hideLocationSelector = false }) => {
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

  // Pour gestion des tournées
  const [tournees, setTournees] = useState([]);
  const [selectedTourneeId, setSelectedTourneeId] = useState(null); // Tournée actuellement sélectionnée
  const [newTournee, setNewTournee] = useState({
    nom: '',
    date_debut: '',
    date_fin: '',
    notes: ''
  });

  // Pour push vers Gazelle
  const [readyForPushCount, setReadyForPushCount] = useState(0);
  const [pushInProgress, setPushInProgress] = useState(false);

  const usages = ['Piano', 'Accompagnement', 'Pratique', 'Concert', 'Enseignement', 'Loisir'];

  // Charger les pianos depuis l'API au montage du composant
  useEffect(() => {
    console.log('[VincentDIndyDashboard] useEffect de chargement initial déclenché');
    try {
      loadPianosFromAPI();
      loadTournees();
    } catch (e) {
      console.error('[VincentDIndyDashboard] Erreur dans useEffect de chargement:', e);
      alert(`Erreur au chargement initial: ${e.message}\n\nStack: ${e.stack}`);
    }
  }, []);

  // Charger le compteur de pianos prêts pour push
  useEffect(() => {
    const loadReadyCount = async () => {
      try {
        const response = await fetch(`${API_URL}/api/vincent-dindy/pianos-ready-for-push`);
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
  }, [pianos, currentView]);

  const loadPianosFromAPI = async () => {
    try {
      setLoading(true);
      setError(null);
      console.log('🔄 Chargement des pianos depuis:', API_URL);

      // Toujours charger TOUS les pianos (include_inactive=true)
      // Le filtrage se fera côté frontend via showAllPianos
      const url = `${API_URL}/api/vincent-dindy/pianos?include_inactive=true`;
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
  };

  // Fonction pour sauvegarder un piano via l'API
  const savePianoToAPI = async (pianoId, updates) => {
    try {
      // Ajouter automatiquement la signature de l'utilisateur
      const updatesWithUser = {
        ...updates,
        updated_by: currentUser?.email || currentUser?.name || 'Unknown'
      };

      await updatePiano(API_URL, pianoId, updatesWithUser);
      console.log('✅ Piano sauvegardé par', currentUser?.name, ':', pianoId, updatesWithUser);
    } catch (err) {
      console.error('❌ Erreur lors de la sauvegarde:', err);
      alert(`Erreur lors de la sauvegarde: ${err.message}`);
      // Recharger depuis l'API en cas d'erreur
      await loadPianosFromAPI();
    }
  };

  const moisDepuisAccord = (dateStr) => {
    if (!dateStr || dateStr.trim() === '') return 999; // Valeur très élevée pour trier à la fin
    const date = new Date(dateStr);
    if (isNaN(date.getTime())) return 999; // Date invalide
    const now = new Date();
    return Math.floor((now - date) / (1000 * 60 * 60 * 24 * 30));
  };

  // Obtenir les pianos associés à une tournée
  const getTourneePianos = (tourneeId) => {
    if (!tourneeId) return [];
    const tournee = tournees.find(t => t.id === tourneeId);
    return tournee?.piano_ids || [];
  };

  // Vérifier si un piano est dans une tournée - utilise UNIQUEMENT gazelleId
  const isPianoInTournee = (piano, tourneeId) => {
    const tourneePianoIds = getTourneePianos(tourneeId);
    const pianoGzId = piano.gazelleId || piano.id;
    const isIn = tourneePianoIds.includes(pianoGzId);

    // Debug détaillé pour comprendre pourquoi test4 montre les pianos de test3
    if (window.DEBUG_TOURNEES) {
      console.log(`🔍 isPianoInTournee: ${piano.serie}`);
      console.log(`   tourneeId demandée: ${tourneeId}`);
      console.log(`   piano.gazelleId: ${piano.gazelleId}`);
      console.log(`   piano.id: ${piano.id}`);
      console.log(`   pianoGzId utilisé: ${pianoGzId}`);
      console.log(`   tourneePianoIds:`, tourneePianoIds);
      console.log(`   Résultat: ${isIn}`);
    }

    return isIn;
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

    // Filtre d'inventaire : masquer les pianos avec isInCsv=false (sauf si "Tout voir" activé)
    if (!showAllPianos) {
      result = result.filter(p => p.isInCsv !== false);
    }

    if (currentView === 'nicolas') {
      // Si une tournée est sélectionnée, filtrer sur les pianos de cette tournée
      if (selectedTourneeId && showOnlySelected) {
        result = result.filter(p => isPianoInTournee(p, selectedTourneeId));
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
  }, [pianos, sortConfig, filterUsage, filterAccordDepuis, currentView, showOnlySelected, showOnlyProposed, searchLocal, selectedTourneeId, tournees, showAllPianos]);

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
    console.log('   Tournée active:', selectedTourneeId);

    // Si une tournée est sélectionnée, gérer l'assignation automatiquement
    if (selectedTourneeId) {
      console.log('   → Ajout/retrait à la tournée...');
      await togglePianoInTournee(piano);

      // Recharger les tournées pour obtenir les données à jour
      await loadTournees();

      // Resynchroniser selectedIds avec la tournée mise à jour
      const tourneeData = JSON.parse(localStorage.getItem('tournees_accords') || '[]');
      const currentTournee = tourneeData.find(t => t.id === selectedTourneeId);
      if (currentTournee) {
        // Les piano_ids sont des gazelleId, on les utilise directement
        const tourneePianoIds = currentTournee.piano_ids || [];
        console.log('   → Tournée mise à jour, pianos:', tourneePianoIds.length);
        setSelectedIds(new Set(tourneePianoIds));
      }
    } else {
      // Pas de tournée sélectionnée, juste toggle la sélection visuelle
      console.log('   → Sélection visuelle seulement (pas de tournée)');
      setSelectedIds(prev => {
        const next = new Set(prev);
        if (next.has(id)) next.delete(id);
        else next.add(id);
        return next;
      });
    }
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
    setPianos(pianos.map(p => selectedIds.has(p.id) ? { ...p, isInCsv: false } : p));

    // Désélectionner immédiatement
    setSelectedIds(new Set());

    // Sauvegarder chaque piano via API
    for (const id of idsToUpdate) {
      await savePianoToAPI(id, { isInCsv: false });
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
      setIsWorkCompleted(piano.is_work_completed || false);
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

      // Déterminer le statut selon la logique de transition
      let newStatus = piano.status;
      if (isWorkCompleted) {
        newStatus = 'completed';
      } else if (travailInput || observationsInput) {
        newStatus = 'work_in_progress';
      }

      // Mise à jour optimiste
      setPianos(pianos.map(p =>
        p.id === id ? { 
          ...p, 
          travail: travailInput, 
          observations: observationsInput, 
          is_work_completed: isWorkCompleted,
          status: newStatus
        } : p
      ));

      // Sauvegarder le piano via API
      await savePianoToAPI(id, {
        travail: travailInput,
        observations: observationsInput,
        isWorkCompleted: isWorkCompleted,
        status: newStatus
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

  // ============ GESTION DES TOURNÉES ============
  const loadTournees = async () => {
    try {
      const saved = localStorage.getItem('tournees_accords')
      if (saved) {
        setTournees(JSON.parse(saved))
      } else {
        setTournees([])
      }
    } catch (err) {
      console.error('Erreur chargement tournées:', err)
      setTournees([])
    }
  };

  // Ajouter un piano à une tournée (utilise gazelleId si disponible)
  const addPianoToTournee = async (piano) => {
    if (!selectedTourneeId) return;

    const pianoUniqueId = getPianoUniqueId(piano);

    try {
      const existing = JSON.parse(localStorage.getItem('tournees_accords') || '[]');
      const updated = existing.map(t => {
        if (t.id === selectedTourneeId) {
          const currentPianos = t.piano_ids || [];
          if (!currentPianos.includes(pianoUniqueId)) {
            return { ...t, piano_ids: [...currentPianos, pianoUniqueId] };
          }
        }
        return t;
      });
      localStorage.setItem('tournees_accords', JSON.stringify(updated));
      await loadTournees();
    } catch (err) {
      console.error('Erreur ajout piano à tournée:', err);
    }
  };

  // Retirer un piano d'une tournée (utilise gazelleId si disponible)
  const removePianoFromTournee = async (piano) => {
    if (!selectedTourneeId) return;

    const pianoUniqueId = getPianoUniqueId(piano);

    try {
      const existing = JSON.parse(localStorage.getItem('tournees_accords') || '[]');
      const updated = existing.map(t => {
        if (t.id === selectedTourneeId) {
          const currentPianos = t.piano_ids || [];
          return { ...t, piano_ids: currentPianos.filter(id => id !== pianoUniqueId) };
        }
        return t;
      });
      localStorage.setItem('tournees_accords', JSON.stringify(updated));
      await loadTournees();
    } catch (err) {
      console.error('Erreur retrait piano de tournée:', err);
    }
  };

  // Toggle piano dans la tournée
  const togglePianoInTournee = async (piano) => {
    if (!selectedTourneeId) return;

    if (isPianoInTournee(piano, selectedTourneeId)) {
      await removePianoFromTournee(piano);
    } else {
      await addPianoToTournee(piano);
    }
  };

  const handleCreateTournee = async (e) => {
    e.preventDefault()

    if (!newTournee.nom || !newTournee.date_debut) {
      alert('⚠️ Veuillez remplir au minimum le nom et la date de début')
      return
    }

    try {
      const nouvelleTournee = {
        id: `tournee_${Date.now()}`,
        ...newTournee,
        etablissement: selectedLocation, // Ajouter l'établissement sélectionné
        technicien_responsable: currentUser?.email || 'nicolas@example.com',
        techniciens_assignes: [],
        status: 'planifiee',
        created_at: new Date().toISOString()
      }

      const existing = JSON.parse(localStorage.getItem('tournees_accords') || '[]')
      existing.push(nouvelleTournee)
      localStorage.setItem('tournees_accords', JSON.stringify(existing))

      alert('✅ Tournée créée avec succès!')
      setNewTournee({ nom: '', date_debut: '', date_fin: '', notes: '' })
      await loadTournees()

      // Sélectionner automatiquement la nouvelle tournée et vider la sélection
      setSelectedTourneeId(nouvelleTournee.id)
      setSelectedIds(new Set())
    } catch (err) {
      alert('❌ Erreur: ' + err.message)
    }
  };

  const handleDeleteTournee = async (tourneeId) => {
    if (!confirm('Êtes-vous sûr de vouloir supprimer cette tournée ?')) {
      return
    }

    try {
      const existing = JSON.parse(localStorage.getItem('tournees_accords') || '[]')
      const updated = existing.filter(t => t.id !== tourneeId)
      localStorage.setItem('tournees_accords', JSON.stringify(updated))

      alert('✅ Tournée supprimée')
      await loadTournees()
    } catch (err) {
      alert('❌ Erreur: ' + err.message)
    }
  };

  const handleActiverTournee = async (tourneeId) => {
    try {
      const existing = JSON.parse(localStorage.getItem('tournees_accords') || '[]')
      const updated = existing.map(t => ({
        ...t,
        status: t.id === tourneeId ? 'en_cours' : (t.status === 'en_cours' ? 'planifiee' : t.status)
      }))
      localStorage.setItem('tournees_accords', JSON.stringify(updated))

      alert('✅ Tournée activée')
      await loadTournees()
    } catch (err) {
      alert('❌ Erreur: ' + err.message)
    }
  };

  const handleConclureTournee = async (tourneeId) => {
    if (!confirm('Êtes-vous sûr de vouloir conclure cette tournée ?')) {
      return
    }

    try {
      const existing = JSON.parse(localStorage.getItem('tournees_accords') || '[]')
      const updated = existing.map(t => ({
        ...t,
        status: t.id === tourneeId ? 'terminee' : t.status
      }))
      localStorage.setItem('tournees_accords', JSON.stringify(updated))

      alert('✅ Tournée conclue')
      await loadTournees()
    } catch (err) {
      alert('❌ Erreur: ' + err.message)
    }
  };

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

  // Statistiques des tournées par établissement (avec protection)
  const tourneesStats = useMemo(() => {
    if (!tournees || !Array.isArray(tournees)) {
      return { 'vincent-dindy': 0, 'orford': 0 };
    }
    return {
      'vincent-dindy': tournees.filter(t => t && t.etablissement === 'vincent-dindy').length,
      'orford': tournees.filter(t => t && t.etablissement === 'orford').length,
    };
  }, [tournees]);

  const getRowClass = (piano) => {
    // Priorité 1: Sélection (mauve)
    if (selectedIds.has(piano.id)) return 'bg-purple-100';
    
    // Priorité 2: Haute priorité (ambre)
    if (piano.status === 'top') return 'bg-amber-200';
    
    // Priorité 3: Travail complété (vert)
    if (piano.status === 'completed' && piano.is_work_completed) return 'bg-green-200';
    
    // Priorité 4: Travail en cours (bleu) - NOUVEAU
    if (piano.status === 'work_in_progress' ||
        ((piano.travail || piano.observations) && !piano.is_work_completed)) {
      return 'bg-blue-200';
    }
    
    // Priorité 5: Proposé ou à faire (jaune)
    if (
      (selectedTourneeId && isPianoInTournee(piano, selectedTourneeId)) ||
      piano.status === 'proposed' ||
      (piano.aFaire && piano.aFaire.trim() !== '')
    ) return 'bg-yellow-200';
    
    // Défaut: Blanc
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
      const response = await fetch(`${API_URL}/api/vincent-dindy/push-to-gazelle`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          tournee_id: selectedTourneeId || null,
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

  // ============ VUE TECHNICIEN (mobile-friendly) ============
  if (currentView === 'technicien') {

    return (
      <div className="min-h-screen bg-gray-100">
        {/* Header compact */}
        <div className="bg-white shadow p-3 sticky top-0 z-10">
          <div className="flex justify-between items-center mb-2">
            <h1 className="text-lg font-bold">🎹 Tournée</h1>
            <div className="flex gap-2 text-xs">
              {stats.top > 0 && <span className="px-2 py-1 bg-amber-200 rounded">{stats.top} Top</span>}
              <span className="px-2 py-1 bg-yellow-200 rounded">{stats.proposed} à faire</span>
              <span className="px-2 py-1 bg-green-200 rounded">{stats.completed} ✓</span>
            </div>
          </div>
          {/* Sélecteur d'établissement - Masqué si hideLocationSelector */}
          {!hideLocationSelector && (
            <div className="flex gap-2 mb-2">
              <button
                onClick={() => setSelectedLocation('vincent-dindy')}
                className={`flex-1 py-1 px-3 text-sm rounded ${
                  selectedLocation === 'vincent-dindy'
                    ? 'bg-blue-500 text-white font-medium'
                    : 'bg-gray-100 text-gray-600'
                }`}
              >
                Vincent d'Indy <span className={`text-xs ml-1 ${selectedLocation === 'vincent-dindy' ? 'opacity-90' : 'opacity-60'}`}>({tourneesStats['vincent-dindy']})</span>
              </button>
              <button
                onClick={() => setSelectedLocation('orford')}
                className={`flex-1 py-1 px-3 text-sm rounded ${
                  selectedLocation === 'orford'
                    ? 'bg-blue-500 text-white font-medium'
                    : 'bg-gray-100 text-gray-600'
                }`}
              >
                Orford <span className={`text-xs ml-1 ${selectedLocation === 'orford' ? 'opacity-90' : 'opacity-60'}`}>({tourneesStats['orford']})</span>
              </button>
            </div>
          )}
          {/* Onglets - Masqué si hideNickView, on affiche seulement "Technicien" */}
          {hideNickView ? (
            <div className="flex mt-2 text-xs">
              <div className="flex-1 py-2 bg-blue-500 text-white rounded text-center font-medium">
                Technicien
              </div>
            </div>
          ) : (
            <div className="flex mt-2 text-xs">
              {['nicolas', 'technicien'].map(view => (
                <button
                  key={view}
                  onClick={() => setCurrentView(view)}
                  className={`flex-1 py-2 ${currentView === view ? 'bg-blue-500 text-white rounded' : 'text-gray-500'}`}
                >
                  {view === 'nicolas' ? 'Nick' : 'Technicien'}
                </button>
              ))}
            </div>
          )}
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
                <div key={piano.id} className={`rounded-lg shadow overflow-hidden ${
                  piano.status === 'top' ? 'bg-amber-100' :
                  (piano.status === 'completed' && piano.is_work_completed) ? 'bg-green-100' :
                  (piano.status === 'work_in_progress' || ((piano.travail || piano.observations) && !piano.is_work_completed)) ? 'bg-blue-100' :
                  (piano.status === 'proposed' || (piano.aFaire && piano.aFaire.trim() !== '')) ? 'bg-yellow-100' :
                  'bg-white'
                }`}>
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
                      {piano.sync_status && (
                        <span title={`Sync: ${piano.sync_status}`} className="text-base">
                          {getSyncStatusIcon(piano.sync_status)}
                        </span>
                      )}
                      <span className={`text-sm ${mois >= 6 ? 'text-orange-500' : 'text-gray-400'}`}>
                        {mois === 999 ? '-' : `${mois}m`}
                      </span>
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

                      {/* Note "à faire" de Nick */}
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

                      {/* Checkbox Travail complété */}
                      <div className="flex items-center gap-2">
                        <input
                          type="checkbox"
                          id={`completed-${piano.id}`}
                          checked={isWorkCompleted}
                          onChange={(e) => setIsWorkCompleted(e.target.checked)}
                          className="w-4 h-4"
                        />
                        <label htmlFor={`completed-${piano.id}`} className="font-medium text-sm">
                          ✅ Travail complété (prêt pour Gazelle)
                        </label>
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

  // ============ VUE NICOLAS (Gestion & Pianos) ============
  // Si on arrive ici, c'est que currentView === 'nicolas' (ou autre vue non-technicien)
  return (
    <div className="min-h-screen bg-gray-100 p-4">
      {/* Header */}
      <div className="bg-white rounded-lg shadow mb-4">
        <div className="p-4 border-b">
          <div className="flex justify-between items-start mb-3">
            <div>
              <h1 className="text-2xl font-bold text-gray-800">🎹 Tournées</h1>
              <div className="flex gap-4 mt-2 text-sm flex-wrap">
                <span className="px-2 py-1 bg-gray-200 rounded">{stats.total} pianos</span>
                {stats.top > 0 && <span className="px-2 py-1 bg-amber-200 rounded font-medium">{stats.top} Top</span>}
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

          {/* Sélecteur d'établissement */}
          <div className="flex gap-3">
            <button
              onClick={() => setSelectedLocation('vincent-dindy')}
              className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors ${
                selectedLocation === 'vincent-dindy'
                  ? 'bg-blue-500 text-white'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              Vincent d'Indy <span className={`text-xs ml-1 ${selectedLocation === 'vincent-dindy' ? 'opacity-90' : 'opacity-60'}`}>({tourneesStats['vincent-dindy']} tournées)</span>
            </button>
            <button
              onClick={() => setSelectedLocation('orford')}
              className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors ${
                selectedLocation === 'orford'
                  ? 'bg-blue-500 text-white'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              Orford <span className={`text-xs ml-1 ${selectedLocation === 'orford' ? 'opacity-90' : 'opacity-60'}`}>({tourneesStats['orford']} tournées)</span>
            </button>
          </div>
        </div>
        
        {/* Onglets */}
        <div className="flex">
          {[
            { key: 'nicolas', label: 'Gestion & Pianos' },
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

      {/* Vue Gestion & Pianos */}
      {currentView === 'nicolas' && (
        <div className="flex gap-4">
          {/* Sidebar Tournées */}
          <div className="w-80 flex-shrink-0">
            <div className="bg-white rounded-lg shadow p-4 sticky top-4">
              <h2 className="text-lg font-bold mb-4">🎹 Tournées</h2>

              {/* Formulaire création tournée compact */}
              <form onSubmit={handleCreateTournee} className="mb-4 pb-4 border-b">
                <input
                  type="text"
                  value={newTournee.nom}
                  onChange={(e) => setNewTournee({ ...newTournee, nom: e.target.value })}
                  placeholder="Nom de la tournée"
                  className="w-full px-3 py-2 border rounded-md text-sm mb-2"
                  required
                />
                <input
                  type="date"
                  value={newTournee.date_debut}
                  onChange={(e) => setNewTournee({ ...newTournee, date_debut: e.target.value })}
                  className="w-full px-3 py-2 border rounded-md text-sm mb-2"
                  required
                />
                <button
                  type="submit"
                  className="w-full px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 text-sm font-semibold"
                >
                  ➕ Créer
                </button>
              </form>

              {/* Liste des tournées */}
              <div className="space-y-2 max-h-96 overflow-y-auto">
                {tournees.length === 0 ? (
                  <p className="text-gray-500 text-sm">Aucune tournée</p>
                ) : (
                  tournees.map((tournee) => (
                    <div
                      key={tournee.id}
                      onClick={() => {
                        console.log('\n🎹 CLIC SUR TOURNÉE:', tournee.nom);
                        console.log('   ID tournée:', tournee.id);
                        console.log('   Piano IDs stockés:', tournee.piano_ids);
                        console.log('   Nombre de pianos:', (tournee.piano_ids || []).length);

                        setSelectedTourneeId(tournee.id);
                        setShowOnlySelected(false);

                        // VIDER les sélections - les checkboxes servent juste aux actions batch
                        // Elles ne doivent PAS refléter les pianos de la tournée
                        console.log('   → Vidage de selectedIds (checkboxes)');
                        setSelectedIds(new Set());
                      }}
                      className={`p-3 rounded-lg border-2 cursor-pointer transition-colors ${
                        selectedTourneeId === tournee.id
                          ? 'border-blue-500 bg-blue-50'
                          : 'border-gray-200 hover:border-blue-300'
                      }`}
                    >
                      <div className="flex justify-between items-start">
                        <div className="flex-1">
                          <h4 className="font-semibold text-sm">{tournee.nom}</h4>
                          <p className="text-xs text-gray-600 mt-1">
                            {new Date(tournee.date_debut).toLocaleDateString('fr-CA')}
                          </p>
                          <p className="text-xs text-blue-600 mt-1">
                            {getTourneePianos(tournee.id).length} pianos
                          </p>
                        </div>
                        <span className={`px-2 py-1 rounded text-xs font-semibold ${
                          tournee.status === 'terminee' ? 'bg-green-100 text-green-800' :
                          tournee.status === 'en_cours' ? 'bg-blue-100 text-blue-800' :
                          'bg-gray-100 text-gray-800'
                        }`}>
                          {tournee.status === 'terminee' ? '✓' :
                           tournee.status === 'en_cours' ? '▶' :
                           '○'}
                        </span>
                      </div>

                      {selectedTourneeId === tournee.id && (
                        <div className="mt-2 pt-2 border-t space-y-1">
                          {/* Assignation technicien */}
                          <div>
                            <select
                              value={tournee.technicien_assigne || ''}
                              onChange={async (e) => {
                                e.stopPropagation();
                                const existing = JSON.parse(localStorage.getItem('tournees_accords') || '[]');
                                const updated = existing.map(t =>
                                  t.id === tournee.id ? { ...t, technicien_assigne: e.target.value } : t
                                );
                                localStorage.setItem('tournees_accords', JSON.stringify(updated));
                                await loadTournees();
                              }}
                              className="w-full px-2 py-1 border rounded text-xs"
                              onClick={(e) => e.stopPropagation()}
                            >
                              <option value="">Assigner à...</option>
                              <option value="Nicolas">Nicolas</option>
                              <option value="Isabelle">Isabelle</option>
                              <option value="JP">JP</option>
                            </select>
                          </div>

                          {/* Boutons d'action */}
                          <div className="flex gap-1">
                            {tournee.status === 'planifiee' && (
                              <button
                                onClick={(e) => { e.stopPropagation(); handleActiverTournee(tournee.id); }}
                                className="flex-1 px-2 py-1 bg-green-100 text-green-700 rounded hover:bg-green-200 text-xs"
                              >
                                ▶ Activer
                              </button>
                            )}
                            {tournee.status === 'en_cours' && (
                              <button
                                onClick={(e) => { e.stopPropagation(); handleConclureTournee(tournee.id); }}
                                className="flex-1 px-2 py-1 bg-orange-100 text-orange-700 rounded hover:bg-orange-200 text-xs"
                              >
                                ✓ Terminer
                              </button>
                            )}
                            <button
                              onClick={(e) => { e.stopPropagation(); handleDeleteTournee(tournee.id); }}
                              className="px-2 py-1 bg-red-100 text-red-700 rounded hover:bg-red-200 text-xs"
                            >
                              🗑️
                            </button>
                          </div>
                        </div>
                      )}
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>

          {/* Zone principale des pianos */}
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
              {currentView === 'nicolas' && (
                <th className="px-2 py-3 w-10">
                  <input
                    ref={selectAllCheckboxRef}
                    type="checkbox"
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
              <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase">Sync</th>
              {currentView === 'nicolas' && (
                <>
                  <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase bg-yellow-50">À faire (Nick)</th>
                  <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase bg-blue-50">Notes (Tech)</th>
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
                  <td className={`px-3 py-3 text-sm font-medium ${mois === 999 ? 'text-gray-400' : mois >= 12 ? 'text-red-600' : mois >= 6 ? 'text-orange-500' : 'text-green-600'}`}>
                    {mois === 999 ? '-' : mois}
                  </td>

                  {/* Colonne Sync Status */}
                  <td className="px-3 py-3 text-sm">
                    {piano.sync_status && (
                      <span title={`Sync: ${piano.sync_status}`} className="text-lg">
                        {getSyncStatusIcon(piano.sync_status)}
                      </span>
                    )}
                  </td>

                  {/* Colonnes pour l'onglet Nick */}
                  {currentView === 'nicolas' && (
                    <>
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

                      {/* Colonne Notes (combinaison de Travail + Observations) */}
                      <td className="px-3 py-3 bg-blue-50" onClick={(e) => e.stopPropagation()}>
                        {editingNotesId === piano.id ? (
                          <textarea
                            value={notesInput}
                            onChange={(e) => setNotesInput(e.target.value)}
                            onBlur={async () => {
                              try {
                                // Mapper notes vers observations (le backend attend observations, pas notes)
                                const notesValue = notesInput.trim();
                                setPianos(pianos.map(p =>
                                  p.id === piano.id ? { 
                                    ...p, 
                                    notes: notesValue,
                                    observations: notesValue // Synchroniser avec observations
                                  } : p
                                ));
                                setEditingNotesId(null);
                                setNotesInput('');
                                // Sauvegarder avec observations (le backend n'accepte pas "notes")
                                await savePianoToAPI(piano.id, { observations: notesValue });
                              } catch (err) {
                                console.error('Erreur sauvegarde notes:', err);
                                alert(`Erreur lors de la sauvegarde: ${err.message}`);
                                // Restaurer l'état d'édition en cas d'erreur
                                setEditingNotesId(piano.id);
                                setNotesInput(notesInput);
                              }
                            }}
                            className="border rounded px-2 py-1 text-xs w-full"
                            placeholder="Notes du technicien (accord, humidité...)"
                            rows="3"
                            autoFocus
                          />
                        ) : (
                          <span
                            className="text-xs cursor-text block whitespace-pre-wrap"
                            onClick={() => { 
                              setEditingNotesId(piano.id); 
                              // Utiliser observations si disponible, sinon notes (pour compatibilité)
                              setNotesInput(piano.observations || piano.notes || ''); 
                            }}
                          >
                            {piano.observations || piano.notes || <span className="text-gray-400">Cliquer...</span>}
                          </span>
                        )}
                      </td>

                    </>
                  )}

                  {/* Colonne Statut */}
                  <td className="px-3 py-3 text-sm">
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

        {pianosFiltres.length === 0 && (
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
        </div>
      )}
    </div>
  );
};

export default VincentDIndyDashboard;

