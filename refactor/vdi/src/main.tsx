/**
 * VDI V7 - Entry Point MINIMAL
 *
 * PAS de navigation ici - la navigation vient de V5 App.jsx
 * Ce fichier sert uniquement de point d'entrée pour le contenu V7
 */

import React, { useState } from 'react';
import ReactDOM from 'react-dom/client';
import { VDIInventory } from '../components/VDIInventory';
import { TourneesView } from '../components/VDITournees/TourneesView';
import { TechnicianView } from '../components/VDITournees/TechnicianView';
import './index.css';

// ==========================================
// TYPES
// ==========================================

export type VDIView = 'inventory' | 'tournees' | 'techniciens';

// ==========================================
// APP COMPONENT (MINIMAL - PAS DE NAVIGATION)
// ==========================================

function App() {
  // Par défaut: afficher l'inventaire (Master Template 528 lignes)
  const [currentView, setCurrentView] = useState<VDIView>('inventory');

  return (
    <div className="min-h-screen bg-gray-50">
      {/* PAS de bandeau de navigation ici - il vient de V5 */}

      {/* Main Content - Direct, sans padding superflu */}
      <main>
        {currentView === 'inventory' && (
          <VDIInventory />
        )}

        {currentView === 'tournees' && (
          <div className="h-screen">
            <TourneesView etablissement="vincent-dindy" />
          </div>
        )}

        {currentView === 'techniciens' && (
          <TechnicianView etablissement="vincent-dindy" />
        )}
      </main>
    </div>
  );
}

// ==========================================
// RENDER
// ==========================================

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
