/**
 * VDI App - Application principale
 *
 * Navigation par onglets entre:
 * - Inventaire Pianos (InventoryTable)
 * - Tournées (PianosTable via TourneesView)
 * - Techniciens (TechnicianView)
 */

import React, { useState } from 'react';
import { InventoryTable } from './components/VDIInventory/InventoryTable';
import { TourneesView } from './components/VDITournees/TourneesView';
import { TechnicianView } from './components/VDITournees/TechnicianView';

// ==========================================
// TYPES
// ==========================================

type VDIView = 'inventaire' | 'tournees' | 'techniciens';

// ==========================================
// COMPONENT
// ==========================================

export function App() {
  const [activeView, setActiveView] = useState<VDIView>('inventaire');

  // ==========================================
  // RENDER
  // ==========================================

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Navigation Tabs */}
      <nav className="bg-white border-b border-gray-200 shadow-sm sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-6">
          <div className="flex space-x-1">
            <TabButton
              label="📦 Inventaire Pianos"
              isActive={activeView === 'inventaire'}
              onClick={() => setActiveView('inventaire')}
            />
            <TabButton
              label="🗺️ Tournées"
              isActive={activeView === 'tournees'}
              onClick={() => setActiveView('tournees')}
            />
            <TabButton
              label="👨‍🔧 Techniciens"
              isActive={activeView === 'techniciens'}
              onClick={() => setActiveView('techniciens')}
            />
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-6 py-8">
        {activeView === 'inventaire' && (
          <InventoryTable etablissement="vincent-dindy" />
        )}

        {activeView === 'tournees' && (
          <div className="h-[calc(100vh-180px)]">
            <TourneesView etablissement="vincent-dindy" />
          </div>
        )}

        {activeView === 'techniciens' && (
          <div className="h-[calc(100vh-180px)]">
            <TechnicianView etablissement="vincent-dindy" />
          </div>
        )}
      </main>
    </div>
  );
}

// ==========================================
// SUBCOMPONENTS
// ==========================================

interface TabButtonProps {
  label: string;
  isActive: boolean;
  onClick: () => void;
}

function TabButton({ label, isActive, onClick }: TabButtonProps) {
  return (
    <button
      onClick={onClick}
      className={`
        px-6 py-3 text-sm font-medium transition-colors
        border-b-2
        ${
          isActive
            ? 'border-blue-600 text-blue-600 bg-blue-50'
            : 'border-transparent text-gray-600 hover:text-gray-900 hover:border-gray-300'
        }
      `}
    >
      {label}
    </button>
  );
}

export default App;
