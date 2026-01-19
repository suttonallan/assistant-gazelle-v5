/**
 * VDI_TechnicianView - Vue accordéon mobile pour les techniciens
 *
 * Affiche les pianos sous forme de cartes pliables avec:
 * - Filtres "Tous" / "À faire"
 * - Recherche par local
 * - Formulaire de saisie du travail effectué
 * - Sauvegarde et passage automatique au suivant
 */

import React from 'react';

export default function VDI_TechnicianView({
  // État global
  pianos,
  stats,

  // Filtres
  showOnlyProposed,
  setShowOnlyProposed,
  searchLocal,
  setSearchLocal,

  // Piano développé
  expandedPianoId,
  setExpandedPianoId,
  travailInput,
  setTravailInput,
  observationsInput,
  setObservationsInput,
  isWorkCompleted,
  setIsWorkCompleted,

  // Actions
  saveTravail,

  // Utilitaires
  moisDepuisAccord,
  formatDateRelative,
  getSyncStatusIcon,
  pianosFiltres,

  // Tournées (sélection institution) - avec valeurs par défaut
  selectedInstitution,
  setSelectedInstitution,
  onInstitutionChange
}) {

  const toggleExpand = (piano) => {
    if (expandedPianoId === piano.id) {
      // Fermer
      setExpandedPianoId(null);
      setTravailInput('');
      setIsWorkCompleted(false);
    } else {
      // Ouvrir et charger les données
      setExpandedPianoId(piano.id);
      setTravailInput(piano.travail || '');
      setIsWorkCompleted(piano.is_work_completed || false);
    }
  };

  const institutions = [
    { slug: 'vincent-dindy', name: "Vincent-d'Indy" },
    { slug: 'orford', name: 'Orford Musique' },
    { slug: 'place-des-arts', name: 'Place des Arts' }
  ];

  const handleInstitutionChange = (institutionSlug) => {
    console.log('🔄 Changement institution:', institutionSlug);
    if (setSelectedInstitution) {
      setSelectedInstitution(institutionSlug);
    }
    if (onInstitutionChange) {
      onInstitutionChange(institutionSlug);
    } else {
      console.warn('⚠️ onInstitutionChange non défini');
    }
  };

  // Utiliser selectedInstitution ou 'vincent-dindy' par défaut
  const currentInstitution = selectedInstitution || 'vincent-dindy';
  
  // Debug: afficher la valeur actuelle - LOGS TRÈS VISIBLES
  console.log('🏛️ ===== VDI_TechnicianView RENDU =====');
  console.log('🏛️ Props reçues:', {
    selectedInstitution,
    hasSetSelectedInstitution: !!setSelectedInstitution,
    hasOnInstitutionChange: !!onInstitutionChange,
    currentInstitution
  });
  console.log('🏛️ Institutions disponibles:', institutions.map(i => `${i.slug} (${i.name})`).join(', '));
  console.log('🏛️ Institution active:', currentInstitution);
  console.log('🏛️ ====================================');

  return (
    <div className="bg-gray-50">
      {/* Volet Tournées - Sélection institution - TOUJOURS AFFICHÉ - TEST VISIBILITÉ */}
      <div 
        className="bg-gradient-to-r from-blue-50 to-white p-4 mb-3 border-2 border-blue-400 shadow-lg rounded-lg"
        style={{ display: 'block', visibility: 'visible', opacity: 1 }}
        data-testid="institution-selector-panel"
      >
        <div className="text-base font-bold text-gray-900 mb-3 flex items-center gap-2">
          <span className="text-2xl">🏛️</span>
          <span>Tournées</span>
        </div>
        <div className="flex gap-2 mb-2">
          {institutions.map(inst => {
            const isActive = currentInstitution === inst.slug;
            return (
              <button
                key={inst.slug}
                onClick={() => {
                  console.log('🖱️ Clic sur institution:', inst.slug);
                  handleInstitutionChange(inst.slug);
                }}
                className={`flex-1 py-3 px-4 text-sm rounded-lg font-bold transition-all ${
                  isActive
                    ? 'bg-blue-600 text-white shadow-lg scale-105 ring-2 ring-blue-300'
                    : 'bg-white text-gray-700 hover:bg-blue-50 active:bg-blue-100 border-2 border-gray-300 hover:border-blue-400'
                }`}
              >
                {inst.name}
              </button>
            );
          })}
        </div>
        <div className="mt-2 text-xs text-gray-700 bg-blue-100 p-2 rounded border border-blue-300">
          <span className="font-semibold">Institution active:</span> <span className="font-bold text-blue-700">{currentInstitution}</span>
        </div>
      </div>

      {/* Filtres compacts pour la vue technicien */}
      <div className="bg-white p-3 mb-4 border-b border-gray-200">
        <div className="flex gap-2 mb-2">
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

        <input
          type="text"
          placeholder="Rechercher par local (ex: 301)"
          value={searchLocal}
          onChange={(e) => setSearchLocal(e.target.value)}
          className="w-full px-3 py-2 border rounded text-sm"
        />
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
                      <div><span className="text-gray-500">Dernier:</span> {formatDateRelative(piano.dernierAccord)}</div>
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
