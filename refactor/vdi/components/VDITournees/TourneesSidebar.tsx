/**
 * TourneesSidebar - Panneau latéral de gestion des tournées
 *
 * Fonctionnalités:
 * - Liste des tournées (actives, planifiées, archivées)
 * - Créer une nouvelle tournée
 * - Activer/Archiver une tournée
 * - Filtrer par statut
 */

import React, { useState } from 'react';
import { useTournees } from '@hooks/useTournees';
import type { Etablissement, Tournee } from '@types/tournee.types';
import { TourneeCard } from './TourneeCard';
import { CreateTourneeModal } from './CreateTourneeModal';
import { EditTourneeFormModal } from './EditTourneeFormModal';

interface TourneesSidebarProps {
  etablissement: Etablissement;
  className?: string;
  selectedTourneeId?: string | null;
  onSelectTournee?: (id: string | null) => void;
}

type StatusFilter = 'all' | 'active' | 'planned' | 'archived';

export function TourneesSidebar({
  etablissement,
  className = '',
  selectedTourneeId,
  onSelectTournee
}: TourneesSidebarProps) {
  const {
    tournees,
    loading,
    error,
    activeTournee,
    createTournee,
    activateTournee,
    updateTournee,
    reanimateTournee,
    deleteTournee
  } = useTournees(etablissement);

  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all');
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [editingTournee, setEditingTournee] = useState<Tournee | null>(null);

  // Filtrer tournées par statut
  const filteredTournees = tournees.filter((t) => {
    if (statusFilter === 'all') return true;
    if (statusFilter === 'active') return t.status === 'en_cours';
    if (statusFilter === 'planned') return t.status === 'planifiee';
    if (statusFilter === 'archived') return t.status === 'archivee';
    return true;
  });

  // Stats pour badges
  const stats = {
    active: tournees.filter((t) => t.status === 'en_cours').length,
    planned: tournees.filter((t) => t.status === 'planifiee').length,
    archived: tournees.filter((t) => t.status === 'archivee').length
  };

  return (
    <>
      <div className={`flex flex-col h-full bg-white border-r border-gray-200 ${className}`}>
        {/* Header */}
        <div className="p-4 border-b border-gray-200">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-gray-900">Tournées</h2>
            <button
              onClick={() => setShowCreateModal(true)}
              className="px-3 py-1.5 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 transition-colors"
            >
              + Nouvelle
            </button>
          </div>

          {/* Filtres */}
          <div className="flex gap-2">
            <FilterButton
              label="Toutes"
              count={tournees.length}
              active={statusFilter === 'all'}
              onClick={() => setStatusFilter('all')}
            />
            <FilterButton
              label="Active"
              count={stats.active}
              active={statusFilter === 'active'}
              color="green"
              onClick={() => setStatusFilter('active')}
            />
            <FilterButton
              label="Planifiées"
              count={stats.planned}
              active={statusFilter === 'planned'}
              color="blue"
              onClick={() => setStatusFilter('planned')}
            />
            <FilterButton
              label="Archivées"
              count={stats.archived}
              active={statusFilter === 'archived'}
              color="gray"
              onClick={() => setStatusFilter('archived')}
            />
          </div>
        </div>

        {/* Liste des tournées */}
        <div className="flex-1 overflow-y-auto p-4 space-y-3">
          {loading && (
            <div className="text-center py-8 text-gray-500">
              Chargement des tournées...
            </div>
          )}

          {error && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-sm text-red-800">
              ❌ Erreur: {error}
            </div>
          )}

          {!loading && !error && filteredTournees.length === 0 && (
            <div className="text-center py-8 text-gray-500">
              {statusFilter === 'all'
                ? 'Aucune tournée. Créez-en une!'
                : `Aucune tournée ${statusFilter === 'active' ? 'active' : statusFilter === 'planned' ? 'planifiée' : 'archivée'}.`}
            </div>
          )}

          {!loading &&
            !error &&
            filteredTournees.map((tournee) => (
              <TourneeCard
                key={tournee.id}
                tournee={tournee}
                isActive={String(tournee.id) === String(activeTournee?.id)}
                isSelected={String(tournee.id) === String(selectedTourneeId)}
                onClick={() => {
                  // TOUJOURS garder une tournée sélectionnée - ne pas permettre désélection
                  // Comparaison stricte avec String() pour éviter les problèmes de typage
                  if (String(tournee.id) !== String(selectedTourneeId)) {
                    onSelectTournee?.(tournee.id);
                  }
                }}
                onActivate={() => activateTournee(tournee.id)}
                onArchive={() => updateTournee(tournee.id, { status: 'archivee' })}
                onReanimate={() => reanimateTournee(tournee.id)}
                onOpenEditModal={() => setEditingTournee(tournee)}
                onDelete={() => {
                  if (confirm(`Supprimer la tournée "${tournee.nom}" ?`)) {
                    deleteTournee(tournee.id);
                  }
                }}
              />
            ))}
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-gray-200 bg-gray-50">
          <div className="text-xs text-gray-500">
            {activeTournee ? (
              <div className="flex items-center gap-2">
                <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
                <span>
                  Tournée active: <strong>{activeTournee.nom}</strong>
                </span>
              </div>
            ) : (
              <span>Aucune tournée active</span>
            )}
          </div>
        </div>
      </div>

      {/* Modal création */}
      {showCreateModal && (
        <CreateTourneeModal
          etablissement={etablissement}
          onClose={() => setShowCreateModal(false)}
          onCreate={async (data) => {
            await createTournee(data);
            setShowCreateModal(false);
          }}
        />
      )}

      {/* Modal édition */}
      {editingTournee && (
        <EditTourneeFormModal
          tournee={editingTournee}
          onClose={() => setEditingTournee(null)}
          onSave={async (tourneeId, updates) => {
            await updateTournee(tourneeId, updates);
            setEditingTournee(null);
          }}
        />
      )}
    </>
  );
}

// ==========================================
// FILTER BUTTON
// ==========================================

interface FilterButtonProps {
  label: string;
  count: number;
  active: boolean;
  color?: 'green' | 'blue' | 'gray';
  onClick: () => void;
}

function FilterButton({ label, count, active, color = 'blue', onClick }: FilterButtonProps) {
  const colorClasses = {
    green: active
      ? 'bg-green-100 text-green-800 border-green-300'
      : 'bg-white text-gray-700 border-gray-200 hover:bg-green-50',
    blue: active
      ? 'bg-blue-100 text-blue-800 border-blue-300'
      : 'bg-white text-gray-700 border-gray-200 hover:bg-blue-50',
    gray: active
      ? 'bg-gray-200 text-gray-800 border-gray-400'
      : 'bg-white text-gray-700 border-gray-200 hover:bg-gray-50'
  };

  return (
    <button
      onClick={onClick}
      className={`flex-1 px-2 py-1.5 text-xs font-medium border rounded-lg transition-colors ${colorClasses[color]}`}
    >
      {label}
      {count > 0 && (
        <span className="ml-1 px-1.5 py-0.5 bg-white bg-opacity-50 rounded">
          {count}
        </span>
      )}
    </button>
  );
}
