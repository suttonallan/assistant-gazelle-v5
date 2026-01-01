/**
 * TourneeCard - Carte d'affichage d'une tournée
 *
 * Affiche:
 * - Nom, dates, statut
 * - Nombre de pianos
 * - Actions (activer, archiver, supprimer)
 */

import React from 'react';
import type { Tournee } from '@types/tournee.types';
import { formatDateShort } from '@lib/utils';

interface TourneeCardProps {
  tournee: Tournee;
  isActive: boolean;
  isSelected?: boolean;
  onClick?: () => void;
  onActivate: () => void;
  onArchive: () => void;
  onDelete: () => void;
  onReanimate?: () => void;
  onEdit?: () => void;
  onOpenEditModal?: () => void;
}

export function TourneeCard({
  tournee,
  isActive,
  isSelected = false,
  onClick,
  onActivate,
  onArchive,
  onDelete,
  onReanimate,
  onEdit,
  onOpenEditModal
}: TourneeCardProps) {
  // DEBUG: Log état sélection
  console.log(`[TourneeCard] ${tournee.nom}: isActive=${isActive}, isSelected=${isSelected}`);

  const statusConfig: Record<string, { label: string; color: string; icon: string }> = {
    en_cours: {
      label: 'Active',
      color: 'bg-green-100 text-green-800 border-green-300',
      icon: '✓'
    },
    planifiee: {
      label: 'Planifiée',
      color: 'bg-blue-100 text-blue-800 border-blue-300',
      icon: '📅'
    },
    archivee: {
      label: 'Archivée',
      color: 'bg-gray-100 text-gray-600 border-gray-300',
      icon: '📦'
    },
    terminee: {
      label: 'Complétée',
      color: 'bg-purple-100 text-purple-800 border-purple-300',
      icon: '✅'
    }
  };

  const config = statusConfig[tournee.status] || {
    label: tournee.status,
    color: 'bg-gray-100 text-gray-600 border-gray-300',
    icon: '❓'
  };
  const pianoCount = tournee.pianoIds.length;

  return (
    <div
      onClick={onClick}
      className={`
        group relative rounded-lg p-3 transition-all cursor-pointer
        ${
          isActive && isSelected
            ? 'bg-green-50 border-4 border-green-600 shadow-lg'
            : isActive
            ? 'bg-green-50 border-2 border-green-400 shadow-md'
            : isSelected
            ? 'bg-blue-50 border-4 border-blue-600 shadow-lg'
            : 'bg-white border-2 border-gray-200 hover:border-gray-300 hover:shadow-sm'
        }
      `}
    >
      {/* Badge Active */}
      {isActive && (
        <div className="absolute -top-2 -right-2 px-2 py-0.5 bg-green-600 text-white text-xs font-bold rounded-full shadow-md">
          ACTIVE
        </div>
      )}

      {/* Badge Sélectionnée */}
      {isSelected && !isActive && (
        <div className="absolute -top-2 -right-2 px-2 py-0.5 bg-blue-600 text-white text-xs font-bold rounded-full shadow-md">
          SÉLECTION
        </div>
      )}

      {/* Header */}
      <div className="flex items-start justify-between mb-2">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <h3 className="font-semibold text-gray-900 truncate">
              {tournee.nom}
            </h3>
            {onOpenEditModal && (
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onOpenEditModal();
                }}
                className="px-2 py-0.5 text-xs bg-gray-100 hover:bg-gray-200 rounded transition-colors"
                title="Éditer la tournée"
              >
                ✏️
              </button>
            )}
          </div>
          <div className="flex items-center gap-2 mt-1">
            <span className={`inline-flex items-center gap-1 px-2 py-0.5 text-xs font-medium border rounded ${config.color}`}>
              {config.icon} {config.label}
            </span>
            {pianoCount > 0 && (
              <span className="text-xs text-gray-600">
                🎹 {pianoCount} piano{pianoCount > 1 ? 's' : ''}
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Dates */}
      <div className="text-xs text-gray-600 mb-3 space-y-1">
        <div className="flex items-center gap-2">
          <span className="text-gray-500">Début:</span>
          <span className="font-medium">{formatDateShort(new Date(tournee.dateDebut))}</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-gray-500">Fin:</span>
          <span className="font-medium">{formatDateShort(new Date(tournee.dateFin))}</span>
        </div>
        {tournee.technicienResponsable && (
          <div className="flex items-center gap-2">
            <span className="text-gray-500">Responsable:</span>
            <span className="font-medium">{tournee.technicienResponsable}</span>
          </div>
        )}
        {tournee.techniciensAssistants && tournee.techniciensAssistants.length > 0 && (
          <div className="flex items-center gap-2">
            <span className="text-gray-500">Assistants:</span>
            <span className="font-medium text-xs">
              {tournee.techniciensAssistants.join(', ')}
            </span>
          </div>
        )}
      </div>

      {/* Notes (si présentes) */}
      {tournee.notes && (
        <div className="text-xs text-gray-600 mb-3 p-2 bg-gray-50 rounded border border-gray-200">
          {tournee.notes}
        </div>
      )}

      {/* Actions */}
      <div className="flex gap-2">
        {tournee.status === 'planifiee' && (
          <>
            <button
              onClick={(e) => {
                e.stopPropagation();
                onActivate();
              }}
              className="flex-1 px-3 py-1.5 bg-green-600 text-white text-xs font-medium rounded hover:bg-green-700 transition-colors"
            >
              ✓ Activer
            </button>
            <button
              onClick={(e) => {
                e.stopPropagation();
                onDelete();
              }}
              className="px-3 py-1.5 bg-red-600 text-white text-xs font-medium rounded hover:bg-red-700 transition-colors"
            >
              🗑️
            </button>
          </>
        )}

        {tournee.status === 'en_cours' && (
          <button
            onClick={(e) => {
              e.stopPropagation();
              onArchive();
            }}
            className="flex-1 px-3 py-1.5 bg-gray-600 text-white text-xs font-medium rounded hover:bg-gray-700 transition-colors"
          >
            📦 Archiver
          </button>
        )}

        {tournee.status === 'archivee' && (
          <>
            {onReanimate && (
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onReanimate();
                }}
                className="flex-1 px-3 py-1.5 bg-blue-600 text-white text-xs font-medium rounded hover:bg-blue-700 transition-colors"
              >
                🔄 Réanimer
              </button>
            )}
            <button
              onClick={(e) => {
                e.stopPropagation();
                onDelete();
              }}
              className="px-3 py-1.5 bg-red-600 text-white text-xs font-medium rounded hover:bg-red-700 transition-colors"
            >
              🗑️
            </button>
          </>
        )}
      </div>
    </div>
  );
}
