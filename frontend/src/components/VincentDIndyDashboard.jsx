// LOG: Début du fichier VincentDIndyDashboard.jsx
console.log('[VincentDIndyDashboard] Fichier chargé - ligne 1');

import React, { useState, useMemo, useEffect, useRef, useCallback } from 'react';
import { submitReport, getReports, getPianos, updatePiano, getTournees as getTourneesAPI, getActivity } from '../api/vincentDIndyApi';
import VDI_Navigation from './vdi/VDI_Navigation';
import VDI_TechnicianView from './vdi/VDI_TechnicianView';
import VDI_TourneesManager from './vdi/VDI_TourneesManager';
import VDI_ManagementView from './vdi/VDI_ManagementView';

// Configuration de l'API - utiliser le proxy Vite en développement
const API_URL = import.meta.env.VITE_API_URL || (import.meta.env.DEV ? '' : 'https://assistant-gazelle-v5-api.onrender.com');

const VincentDIndyDashboard = ({ currentUser, initialView = 'nicolas', hideNickView = false }) => {
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

  const loadPianosFromAPI = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      console.log('🔄 Chargement des pianos depuis:', API_URL);

      // Toujours charger TOUS les pianos (include_inactive=true)
      // Le filtrage se fera côté frontend via showAllPianos
      const url = `${API_URL}/vincent-dindy/pianos?include_inactive=true`;
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
  }, []); // Pas de dépendances - API_URL est constant

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
      } else if (travailInput) {
        newStatus = 'work_in_progress';
      }

      // Mise à jour optimiste
      setPianos(pianos.map(p =>
        p.id === id ? { 
          ...p, 
          travail: travailInput, 
          is_work_completed: isWorkCompleted,
          status: newStatus
        } : p
      ));

      // Sauvegarder le piano via API
      await savePianoToAPI(id, {
        travail: travailInput,
        isWorkCompleted: isWorkCompleted,
        status: newStatus
      });

      // Si le travail est marqué comme complété, pousser automatiquement vers Gazelle
      if (isWorkCompleted) {
        try {
          console.log(`🚀 Pushing piano ${id} to Gazelle (auto-push after completion)...`);
          const response = await fetch(
            `${API_URL}/vincent-dindy/pianos/${id}/complete-service?technician_name=Nicolas&auto_push=true`,
            { method: 'POST' }
          );

          if (!response.ok) {
            const error = await response.json();
            console.error('❌ Erreur lors du push vers Gazelle:', error);
            // Ne pas bloquer l'UX - le push peut être fait manuellement plus tard
          } else {
            const result = await response.json();
            console.log('✅ Piano pushé vers Gazelle:', result);
          }
        } catch (pushError) {
          console.error('❌ Exception lors du push vers Gazelle:', pushError);
          // Ne pas bloquer l'UX - le push peut être fait manuellement plus tard
        }
      }

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
  const loadTournees = useCallback(async () => {
    try {
      // Utiliser le service API centralisé
      const tournees = await getTourneesAPI(`${API_URL}`);
      setTournees(tournees);
    } catch (err) {
      console.error('Erreur chargement tournées:', err);
      // Fallback: essayer localStorage si l'API échoue
      try {
        const saved = localStorage.getItem('tournees_accords');
      if (saved) {
          setTournees(JSON.parse(saved));
      } else {
          setTournees([]);
        }
      } catch (localErr) {
        setTournees([]);
      }
    }
  }, []); // Pas de dépendances - API_URL est constant

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
  }, [loadPianosFromAPI, loadTournees]); // Maintenant mémorisés avec useCallback

  // Charger le compteur de pianos prêts pour push
  useEffect(() => {
    const loadReadyCount = async () => {
      try {
        const response = await fetch(`${API_URL}/vincent-dindy/pianos-ready-for-push`);
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

  /**
   * Fonction générique pour mettre à jour une tournée
   * Utilise l'API REST Supabase pour persister les changements
   *
   * @param {string} tourneeId - ID de la tournée à modifier
   * @param {object} updates - Objet contenant les champs à mettre à jour
   *                           Exemples: { nom: "...", status: "...", notes: "...", etc. }
   */
  const handleUpdateTournee = async (tourneeId, updates) => {
    try {
      console.log(`🔄 Mise à jour tournée ${tourneeId}:`, updates);

      // Import de la fonction API
      const { updateTournee } = await import('../api/vincentDIndyApi');

      // Appel API REST pour persister dans Supabase
      await updateTournee(`${API_URL}`, tourneeId, updates);

      console.log('✅ Tournée mise à jour dans Supabase');

      // Rafraîchir la liste des tournées depuis l'API
      await loadTournees();

      // Toast de succès (simple pour l'instant, peut être amélioré avec une lib de toast)
      const updateSummary = Object.keys(updates).join(', ');
      console.log(`✅ Tournée modifiée: ${updateSummary}`);

    } catch (err) {
      console.error('❌ Erreur mise à jour tournée:', err);
      alert(`❌ Erreur lors de la mise à jour: ${err.message}`);
      throw err; // Re-throw pour permettre la gestion d'erreur par le composant appelant
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
      const response = await fetch(`${API_URL}/vincent-dindy/push-to-gazelle`, {
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

  // ============ NAVIGATION UNIFIÉE ============
  // Composant externe pour la navigation (pill buttons)

  // ============ VUE TECHNICIEN (mobile-friendly) ============
  if (currentView === 'technicien') {
    return (
      <>
        <VDI_Navigation
          currentView={currentView}
          setCurrentView={setCurrentView}
          setSelectedIds={setSelectedIds}
          hideNickView={hideNickView}
        />
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
          observationsInput={observationsInput}
          setObservationsInput={setObservationsInput}
          isWorkCompleted={isWorkCompleted}
          setIsWorkCompleted={setIsWorkCompleted}
          saveTravail={saveTravail}
          moisDepuisAccord={moisDepuisAccord}
          formatDateRelative={formatDateRelative}
          getSyncStatusIcon={getSyncStatusIcon}
          pianosFiltres={pianosFiltres}
        />
      </>
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
          <div className="flex gap-4">
          {/* Sidebar Tournées */}
          <VDI_TourneesManager
            tournees={tournees}
            newTournee={newTournee}
            setNewTournee={setNewTournee}
            selectedTourneeId={selectedTourneeId}
            setSelectedTourneeId={setSelectedTourneeId}
            setShowOnlySelected={setShowOnlySelected}
            setSelectedIds={setSelectedIds}
            handleCreateTournee={handleCreateTournee}
            handleDeleteTournee={handleDeleteTournee}
            handleActiverTournee={handleActiverTournee}
            handleConclureTournee={handleConclureTournee}
            handleUpdateTournee={handleUpdateTournee}
            loadTournees={loadTournees}
            getTourneePianos={getTourneePianos}
          />

          {/* Zone principale - Management View */}
          <VDI_ManagementView
            pianosFiltres={pianosFiltres}
            pianos={pianos}
            setPianos={setPianos}
            stats={stats}
            tournees={tournees}
            selectedTourneeId={selectedTourneeId}
            setSelectedTourneeId={setSelectedTourneeId}
            setShowOnlySelected={setShowOnlySelected}
            getTourneePianos={getTourneePianos}
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
            isPianoInTournee={isPianoInTournee}
            filterEtage={filterEtage}
            setFilterEtage={setFilterEtage}
          />
          </div>
        )}
    </div>
  );
};

export default VincentDIndyDashboard;
