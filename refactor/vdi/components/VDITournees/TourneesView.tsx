/**
 * TourneesView - Vue complète du système de tournées
 *
 * Layout:
 * - Sidebar gauche: Gestion des tournées
 * - Main: Table des pianos avec Shift+Clic et BatchToolbar
 */

import React, { useState, useEffect } from 'react';
import { TourneesSidebar } from './TourneesSidebar';
import { PianosTable } from './PianosTable';
import { useTournees } from '@hooks/useTournees';
import type { Etablissement } from '@types/tournee.types';

interface TourneesViewProps {
  etablissement: Etablissement;
}

export function TourneesView({ etablissement }: TourneesViewProps) {
  const { activeTournee, tournees } = useTournees(etablissement);
  const [selectedTourneeId, setSelectedTourneeId] = useState<string | null>(null);

  // Auto-sélectionner la tournée active au démarrage (ou la première tournée si aucune active)
  // selectedTourneeId est la SEULE source de vérité pour l'affichage
  useEffect(() => {
    if (!selectedTourneeId && tournees.length > 0) {
      const initialSelection = activeTournee?.id || tournees[0].id;
      setSelectedTourneeId(initialSelection);
    }
  }, [tournees, activeTournee, selectedTourneeId]);

  return (
    <div className="flex h-full gap-6">
      {/* Sidebar - 320px fixed */}
      <div className="w-80 flex-shrink-0">
        <TourneesSidebar
          etablissement={etablissement}
          className="h-full"
          selectedTourneeId={selectedTourneeId}
          onSelectTournee={setSelectedTourneeId}
        />
      </div>

      {/* Main Content - Flexible */}
      <div className="flex-1 min-w-0">
        <PianosTable
          etablissement={etablissement}
          selectedTourneeId={selectedTourneeId}
        />
      </div>
    </div>
  );
}
