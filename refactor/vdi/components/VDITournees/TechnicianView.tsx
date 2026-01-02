/**
 * TechnicianView - Vue Technicien Mobile-Friendly
 *
 * Vue simplifiée pour techniciens sur le terrain:
 * - Affiche TOUS les pianos (blanc = normal, jaune = à faire, vert = complété)
 * - Cartes compactes pour scan rapide dans corridors
 * - Badge "3s" montrant dernier accord
 * - Actions rapides: Marquer complété, ajouter notes
 * - Optimisé mobile (iPad/téléphone)
 */

import React, { useState } from 'react';
import { usePianos } from '@hooks/usePianos';
import { useTournees } from '@hooks/useTournees';
import { usePianoColors } from '@hooks/usePianoColors';
import { LastTunedBadge } from '@components/shared/LastTunedBadge';
import type { Piano } from '@types/piano.types';
import type { Etablissement } from '@types/tournee.types';
import { formatDateShort } from '@lib/utils';

interface TechnicianViewProps {
  etablissement: Etablissement;
  technicianEmail?: string;
}

export function TechnicianView({
  etablissement,
  technicianEmail = 'current-tech@example.com'
}: TechnicianViewProps) {
  const { pianos, updatePiano, refreshPianos } = usePianos(etablissement, {
    includeHidden: false
  });
  const { activeTournee } = useTournees(etablissement);

  const [expandedPianoId, setExpandedPianoId] = useState<string | null>(null);
  const [workNotes, setWorkNotes] = useState<{ [key: string]: string }>({});
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('asc');
  const [floorFilter, setFloorFilter] = useState<string>('all');

  // Extract unique floors from piano locations
  const floors = Array.from(
    new Set(
      pianos
        .map((p) => {
          // Extract floor from location like "VD212" → "2", "VD3-45" → "3"
          const match = p.location.match(/VD(\d)/);
          return match ? match[1] : null;
        })
        .filter(Boolean)
    )
  ).sort() as string[];

  // Filter and sort pianos
  const filteredAndSortedPianos = pianos
    .filter((p) => {
      if (floorFilter === 'all') return true;
      const floor = p.location.match(/VD(\d)/)?.[1];
      return floor === floorFilter;
    })
    .sort((a, b) => {
      const comparison = a.location.localeCompare(b.location);
      return sortOrder === 'asc' ? comparison : -comparison;
    });

  // Déterminer la couleur d'un piano
  const getPianoColor = (piano: Piano): string => {
    const isInTournee = activeTournee?.pianoIds.includes(piano.gazelleId);
    const isCompleted = piano.status === 'completed';

    // Vert: piano complété (peu importe la tournée)
    if (isCompleted) return 'bg-green-50 border-green-400';

    // Jaune: piano dans la tournée active ET pas encore complété
    if (isInTournee && !isCompleted) return 'bg-yellow-200 border-yellow-400';

    // Blanc: tous les autres pianos (normal, proposed sans tournée, etc.)
    return 'bg-white border-gray-200';
  };

  // Stats (uniquement pour pianos dans tournée)
  const tourneePianos = pianos.filter((p) =>
    activeTournee?.pianoIds.includes(p.gazelleId)
  );
  const completed = tourneePianos.filter((p) => p.status === 'completed').length;
  const total = tourneePianos.length;
  const progress = total > 0 ? Math.round((completed / total) * 100) : 0;

  const handleMarkCompleted = async (piano: Piano) => {
    try {
      // Enregistrer la date de complétion
      const completedAt = new Date().toISOString();
      
      await updatePiano(piano.gazelleId, {
        pianoId: piano.gazelleId,
        status: 'completed',
        isWorkCompleted: true,  // CRITIQUE: Marquer comme work completed
        travail: workNotes[piano.gazelleId] || piano.travail || '',
        completedInTourneeId: activeTournee?.id,
        completedAt: completedAt,  // Date de complétion pour Gazelle
        updatedBy: technicianEmail
      });

      setWorkNotes((prev) => {
        const next = { ...prev };
        delete next[piano.gazelleId];
        return next;
      });

      // Ne pas appeler refreshPianos si updatePiano réussit (optimistic update déjà fait)
      // refreshPianos() est appelé automatiquement par updatePiano en cas d'erreur
    } catch (err) {
      console.error('Error marking completed:', err);
      alert('Erreur lors de la sauvegarde');
      // Recharger en cas d'erreur pour restaurer l'état
      await refreshPianos();
    }
  };

  const handleUndoCompleted = async (piano: Piano) => {
    try {
      await updatePiano(piano.gazelleId, {
        pianoId: piano.gazelleId,
        status: 'proposed',
        completedInTourneeId: null,
        updatedBy: technicianEmail
      });

      await refreshPianos();
    } catch (err) {
      console.error('Error undoing:', err);
      alert('Erreur lors de l\'annulation');
    }
  };

  if (!activeTournee) {
    return (
      <div className="max-w-2xl mx-auto p-6">
        <div className="bg-yellow-50 border-2 border-yellow-300 rounded-lg p-6 text-center">
          <div className="text-4xl mb-3">⚠️</div>
          <h2 className="text-xl font-bold text-yellow-900 mb-2">
            Aucune tournée active
          </h2>
          <p className="text-yellow-800">
            Contactez votre gestionnaire pour activer une tournée.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-3xl mx-auto pb-20">
      {/* Header */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 mb-6">
        <div className="flex items-start justify-between mb-4">
          <div>
            <h1 className="text-2xl font-bold text-gray-900 mb-1">
              {activeTournee.nom}
            </h1>
            <p className="text-sm text-gray-600">
              {formatDateShort(new Date(activeTournee.dateDebut))} →{' '}
              {formatDateShort(new Date(activeTournee.dateFin))}
            </p>
          </div>

          <button
            onClick={refreshPianos}
            className="px-3 py-2 bg-gray-100 hover:bg-gray-200 rounded-lg text-sm font-medium transition-colors"
          >
            🔄 Sync
          </button>
        </div>

        {/* Progress */}
        <div className="mb-3">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-gray-700">Progression</span>
            <span className="text-sm font-bold text-gray-900">
              {completed}/{total} pianos ({progress}%)
            </span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-3">
            <div
              className="bg-green-600 h-3 rounded-full transition-all duration-500"
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>

        {activeTournee.notes && (
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 text-sm text-blue-900">
            📝 {activeTournee.notes}
          </div>
        )}
      </div>

      {/* Filtres et Tri */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-3 mb-4">
        <div className="flex items-center gap-2 flex-wrap">
          {/* Floor filter */}
          <div className="flex items-center gap-1">
            <span className="text-xs text-gray-600">Étage:</span>
            <select
              value={floorFilter}
              onChange={(e) => setFloorFilter(e.target.value)}
              className="px-2 py-1 text-xs border border-gray-300 rounded bg-white"
            >
              <option value="all">Tous</option>
              {floors.map((floor) => (
                <option key={floor} value={floor}>
                  {floor}
                </option>
              ))}
            </select>
          </div>

          {/* Sort order */}
          <button
            onClick={() => setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc')}
            className="px-2 py-1 text-xs bg-gray-100 hover:bg-gray-200 rounded border border-gray-300"
          >
            {sortOrder === 'asc' ? '↑ Croissant' : '↓ Décroissant'}
          </button>

          <div className="flex-1" />

          <span className="text-xs text-gray-500">
            {filteredAndSortedPianos.length} piano(s)
          </span>
        </div>
      </div>

      {/* Liste des pianos */}
      <div className="space-y-2">
        {filteredAndSortedPianos.length === 0 && (
          <div className="bg-gray-50 border border-gray-200 rounded-lg p-8 text-center">
            <p className="text-gray-600">Aucun piano</p>
          </div>
        )}

        {filteredAndSortedPianos.map((piano) => {
          const isInTournee = activeTournee?.pianoIds.includes(piano.gazelleId);
          const isCompleted = piano.status === 'completed';
          const isExpanded = expandedPianoId === piano.gazelleId;

          return (
            <div
              key={piano.gazelleId}
              className={`
                rounded-lg border-2 overflow-hidden transition-all
                ${getPianoColor(piano)}
              `}
            >
              {/* Header - COMPACT */}
              <div
                className="p-2 cursor-pointer"
                onClick={() =>
                  setExpandedPianoId(isExpanded ? null : piano.gazelleId)
                }
              >
                <div className="flex items-center justify-between gap-2">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      {/* Status badge - only for tournee pianos */}
                      {isInTournee && (
                        <span
                          className={`
                            px-1.5 py-0.5 rounded text-xs font-bold
                            ${isCompleted ? 'bg-green-600 text-white' : 'bg-yellow-600 text-white'}
                          `}
                          title={isCompleted ? 'Piano complété' : 'Piano à faire'}
                        >
                          {isCompleted ? '✓' : '○'}
                        </span>
                      )}
                      {/* Type de piano badge */}
                      <span 
                        className="px-1.5 py-0.5 rounded text-xs font-bold bg-gray-200 text-gray-700"
                        title={
                          piano.type === 'G' ? 'Grand (piano à queue)' :
                          piano.type === 'U' ? 'Upright (piano droit)' :
                          piano.type === 'D' ? 'Digital Grand' :
                          'Type inconnu'
                        }
                      >
                        {piano.type}
                      </span>
                      <LastTunedBadge lastTuned={piano.lastTuned} size="xs" />
                    </div>

                    <div className="flex items-baseline gap-2">
                      <h3 className="text-sm font-bold text-gray-900 truncate">
                        {piano.location}
                      </h3>
                      <span className="text-xs text-gray-600 truncate">
                        {piano.make}
                      </span>
                    </div>

                    {piano.aFaire && isInTournee && (
                      <div className="mt-1 px-2 py-1 bg-yellow-100 border border-yellow-300 rounded text-xs text-yellow-900 truncate">
                        <span className="font-semibold">📋 Note de Nick:</span> {piano.aFaire}
                      </div>
                    )}
                  </div>

                  <div className="text-lg flex-shrink-0">
                    {isExpanded ? '▼' : '▶'}
                  </div>
                </div>
              </div>

              {/* Details (Expanded) */}
              {isExpanded && (
                <div className="border-t-2 border-gray-300 bg-white p-4 space-y-4">
                  {/* Note de Nick (À faire) - Affichage proéminent */}
                  {piano.aFaire && isInTournee && (
                    <div className="bg-yellow-50 border-2 border-yellow-400 rounded-lg p-3">
                      <div className="flex items-start gap-2">
                        <span className="text-yellow-600 text-lg">📋</span>
                        <div className="flex-1">
                          <div className="text-xs font-semibold text-yellow-800 uppercase mb-1">
                            Note de Nick
                          </div>
                          <div className="text-sm text-yellow-900 font-medium">
                            {piano.aFaire}
                          </div>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Info */}
                  <div className="grid grid-cols-2 gap-3 text-sm">
                    <div>
                      <span className="text-gray-600">Dernier accord:</span>
                      <div className="font-medium text-gray-900">
                        {piano.lastTuned
                          ? formatDateShort(piano.lastTuned)
                          : 'Inconnu'}
                      </div>
                    </div>
                    <div>
                      <span className="text-gray-600">Série:</span>
                      <div className="font-medium text-gray-900">
                        {piano.serialNumber || '-'}
                      </div>
                    </div>
                  </div>

                  {piano.observations && (
                    <div className="bg-gray-50 border border-gray-200 rounded-lg p-3 text-sm">
                      <div className="text-gray-600 font-medium mb-1">
                        Observations:
                      </div>
                      <div className="text-gray-900">{piano.observations}</div>
                    </div>
                  )}

                  {/* Work Notes - only for tournee pianos */}
                  {isInTournee && !isCompleted && (
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Travail effectué:
                      </label>
                      <textarea
                        value={workNotes[piano.gazelleId] || piano.travail || ''}
                        onChange={(e) =>
                          setWorkNotes({
                            ...workNotes,
                            [piano.gazelleId]: e.target.value
                          })
                        }
                        placeholder="Décrivez le travail effectué..."
                        rows={3}
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-sm"
                      />
                    </div>
                  )}

                  {piano.travail && isCompleted && (
                    <div className="bg-green-50 border border-green-200 rounded-lg p-3 text-sm">
                      <div className="text-green-800 font-medium mb-1">
                        ✓ Travail effectué:
                      </div>
                      <div className="text-green-900">{piano.travail}</div>
                    </div>
                  )}

                  {/* Actions - only for tournee pianos */}
                  {isInTournee && (
                    <div className="flex gap-2 pt-2 border-t border-gray-200">
                      {!isCompleted ? (
                        <button
                          onClick={() => handleMarkCompleted(piano)}
                          className="flex-1 px-4 py-3 bg-green-600 hover:bg-green-700 text-white font-bold rounded-lg transition-colors text-sm shadow-md"
                        >
                          ✓ Terminé
                        </button>
                      ) : (
                        <button
                          onClick={() => handleUndoCompleted(piano)}
                          className="flex-1 px-4 py-3 bg-yellow-600 hover:bg-yellow-700 text-white font-bold rounded-lg transition-colors text-sm shadow-md"
                        >
                          ↶ Annuler
                        </button>
                      )}
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
