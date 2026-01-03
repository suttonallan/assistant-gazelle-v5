/**
 * VDI_TourneesManager - Sidebar de gestion des tournées
 *
 * Fonctionnalités:
 * - Formulaire de création de tournée
 * - Liste des tournées avec sélection
 * - Assignation technicien
 * - Actions: Activer, Terminer, Supprimer, Mettre en pause
 * - Édition inline: Nom, Dates, Notes
 * - Affichage du nombre de pianos par tournée
 */

import React, { useState } from 'react';

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
  handleUpdateTournee,
  loadTournees,

  // Utilitaires
  getTourneePianos
}) {
  // État local pour l'édition inline
  const [editingField, setEditingField] = useState(null); // Format: `${tourneeId}_${fieldName}`
  const [editValue, setEditValue] = useState('');

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

  /**
   * Démarre l'édition inline d'un champ
   */
  const startEditing = (tourneeId, fieldName, currentValue) => {
    setEditingField(`${tourneeId}_${fieldName}`);
    setEditValue(currentValue || '');
  };

  /**
   * Annule l'édition en cours
   */
  const cancelEditing = () => {
    setEditingField(null);
    setEditValue('');
  };

  /**
   * Sauvegarde la valeur éditée via l'API
   */
  const saveEdit = async (tourneeId, fieldName) => {
    try {
      // Construire l'objet de mise à jour avec le champ modifié
      const updates = { [fieldName]: editValue };

      // Appeler handleUpdateTournee qui gère l'API et le refresh
      await handleUpdateTournee(tourneeId, updates);

      // Réinitialiser l'état d'édition
      setEditingField(null);
      setEditValue('');
    } catch (err) {
      console.error('Erreur sauvegarde édition:', err);
      // L'erreur est déjà gérée par handleUpdateTournee (alert)
    }
  };

  /**
   * Gère le onBlur pour sauvegarder automatiquement
   */
  const handleBlur = async (tourneeId, fieldName) => {
    if (editingField === `${tourneeId}_${fieldName}`) {
      await saveEdit(tourneeId, fieldName);
    }
  };

  /**
   * Gère la touche Enter pour sauvegarder
   */
  const handleKeyDown = async (e, tourneeId, fieldName) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      await saveEdit(tourneeId, fieldName);
    } else if (e.key === 'Escape') {
      e.preventDefault();
      cancelEditing();
    }
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
                    {/* Nom éditable */}
                    {editingField === `${tournee.id}_nom` ? (
                      <input
                        type="text"
                        value={editValue}
                        onChange={(e) => setEditValue(e.target.value)}
                        onBlur={() => handleBlur(tournee.id, 'nom')}
                        onKeyDown={(e) => handleKeyDown(e, tournee.id, 'nom')}
                        onClick={(e) => e.stopPropagation()}
                        className="font-semibold text-sm border border-blue-400 rounded px-1 w-full"
                        autoFocus
                      />
                    ) : (
                      <h4
                        className="font-semibold text-sm cursor-text hover:bg-blue-100 rounded px-1"
                        onClick={(e) => {
                          e.stopPropagation();
                          if (selectedTourneeId === tournee.id) {
                            startEditing(tournee.id, 'nom', tournee.nom);
                          }
                        }}
                      >
                        {tournee.nom}
                      </h4>
                    )}

                    {/* Date début éditable */}
                    {editingField === `${tournee.id}_date_debut` ? (
                      <input
                        type="date"
                        value={editValue}
                        onChange={(e) => setEditValue(e.target.value)}
                        onBlur={() => handleBlur(tournee.id, 'date_debut')}
                        onKeyDown={(e) => handleKeyDown(e, tournee.id, 'date_debut')}
                        onClick={(e) => e.stopPropagation()}
                        className="text-xs text-gray-600 border border-blue-400 rounded px-1 mt-1 w-full"
                        autoFocus
                      />
                    ) : (
                      <p
                        className="text-xs text-gray-600 mt-1 cursor-text hover:bg-blue-100 rounded px-1"
                        onClick={(e) => {
                          e.stopPropagation();
                          if (selectedTourneeId === tournee.id) {
                            startEditing(tournee.id, 'date_debut', tournee.date_debut);
                          }
                        }}
                      >
                        {new Date(tournee.date_debut).toLocaleDateString('fr-CA')}
                      </p>
                    )}

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
                  <div className="mt-2 pt-2 border-t space-y-2">
                    {/* Date fin éditable */}
                    <div>
                      <label className="text-xs text-gray-600">Date fin:</label>
                      {editingField === `${tournee.id}_date_fin` ? (
                        <input
                          type="date"
                          value={editValue}
                          onChange={(e) => setEditValue(e.target.value)}
                          onBlur={() => handleBlur(tournee.id, 'date_fin')}
                          onKeyDown={(e) => handleKeyDown(e, tournee.id, 'date_fin')}
                          onClick={(e) => e.stopPropagation()}
                          className="w-full text-xs border border-blue-400 rounded px-1"
                          autoFocus
                        />
                      ) : (
                        <p
                          className="text-xs cursor-text hover:bg-blue-100 rounded px-1"
                          onClick={(e) => {
                            e.stopPropagation();
                            startEditing(tournee.id, 'date_fin', tournee.date_fin || '');
                          }}
                        >
                          {tournee.date_fin ? new Date(tournee.date_fin).toLocaleDateString('fr-CA') : 'Non définie'}
                        </p>
                      )}
                    </div>

                    {/* Notes éditables */}
                    <div>
                      <label className="text-xs text-gray-600">Notes:</label>
                      {editingField === `${tournee.id}_notes` ? (
                        <textarea
                          value={editValue}
                          onChange={(e) => setEditValue(e.target.value)}
                          onBlur={() => handleBlur(tournee.id, 'notes')}
                          onKeyDown={(e) => {
                            // Ctrl+Enter ou Cmd+Enter pour sauvegarder
                            if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
                              e.preventDefault();
                              saveEdit(tournee.id, 'notes');
                            } else if (e.key === 'Escape') {
                              e.preventDefault();
                              cancelEditing();
                            }
                          }}
                          onClick={(e) => e.stopPropagation()}
                          className="w-full text-xs border border-blue-400 rounded px-1 py-1"
                          rows="2"
                          autoFocus
                        />
                      ) : (
                        <p
                          className="text-xs cursor-text hover:bg-blue-100 rounded px-1 py-1 min-h-[2rem] whitespace-pre-wrap"
                          onClick={(e) => {
                            e.stopPropagation();
                            startEditing(tournee.id, 'notes', tournee.notes || '');
                          }}
                        >
                          {tournee.notes || 'Cliquez pour ajouter des notes...'}
                        </p>
                      )}
                    </div>

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
                    <div className="flex gap-1 flex-wrap">
                      {tournee.status === 'planifiee' && (
                        <button
                          onClick={(e) => { e.stopPropagation(); handleActiverTournee(tournee.id); }}
                          className="flex-1 px-2 py-1 bg-green-100 text-green-700 rounded hover:bg-green-200 text-xs"
                        >
                          ▶ Activer
                        </button>
                      )}
                      {tournee.status === 'en_cours' && (
                        <>
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              handleUpdateTournee(tournee.id, { status: 'planifiee' });
                            }}
                            className="flex-1 px-2 py-1 bg-yellow-100 text-yellow-700 rounded hover:bg-yellow-200 text-xs"
                            title="Mettre la tournée en pause (retour à planifiée)"
                          >
                            ⏸️ Pause
                          </button>
                          <button
                            onClick={(e) => { e.stopPropagation(); handleConclureTournee(tournee.id); }}
                            className="flex-1 px-2 py-1 bg-orange-100 text-orange-700 rounded hover:bg-orange-200 text-xs"
                          >
                            ✓ Terminer
                          </button>
                        </>
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
