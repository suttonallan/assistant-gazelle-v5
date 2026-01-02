/**
 * VDI_TourneesManager - Sidebar de gestion des tournées
 *
 * Fonctionnalités:
 * - Formulaire de création de tournée
 * - Liste des tournées avec sélection
 * - Assignation technicien
 * - Actions: Activer, Terminer, Supprimer
 * - Affichage du nombre de pianos par tournée
 */

import React from 'react';

export default function VDI_TourneesManager({
  // État
  tournees,
  newTournee,
  setNewTournee,
  selectedTourneeId,
  setSelectedTourneeId,
  setShowOnlySelected,
  setSelectedIds,

  // Actions
  handleCreateTournee,
  handleDeleteTournee,
  handleActiverTournee,
  handleConclureTournee,
  loadTournees,

  // Utilitaires
  getTourneePianos
}) {

  const handleTourneeClick = (tournee) => {
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
  };

  const handleTechnicienChange = async (e, tourneeId) => {
    e.stopPropagation();
    const existing = JSON.parse(localStorage.getItem('tournees_accords') || '[]');
    const updated = existing.map(t =>
      t.id === tourneeId ? { ...t, technicien_assigne: e.target.value } : t
    );
    localStorage.setItem('tournees_accords', JSON.stringify(updated));
    await loadTournees();
  };

  return (
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
                onClick={() => handleTourneeClick(tournee)}
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
                        onChange={(e) => handleTechnicienChange(e, tournee.id)}
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
  );
}
