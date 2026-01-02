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
  getSyncStatusIcon,
  pianosFiltres
}) {

  const toggleExpand = (piano) => {
    if (expandedPianoId === piano.id) {
      // Fermer
      setExpandedPianoId(null);
      setTravailInput('');
      setObservationsInput('');
      setIsWorkCompleted(false);
    } else {
      // Ouvrir et charger les données
      setExpandedPianoId(piano.id);
      setTravailInput(piano.travail || '');
      setObservationsInput(piano.observations || '');
      setIsWorkCompleted(piano.is_work_completed || false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-100 p-4">
      {/* Filtres compacts pour la vue technicien */}
      <div className="bg-white rounded-lg shadow p-3 mb-4">
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
