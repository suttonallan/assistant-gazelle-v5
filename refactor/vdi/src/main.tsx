/**
 * VDI Main Entry Point - App avec Dashboard
 */

import React, { useState } from 'react';
import ReactDOM from 'react-dom/client';
import { VDIDashboard } from '../components/VDIDashboard/VDIDashboard';
import { VDIInventory } from '../components/VDIInventory';
import { TourneesView } from '../components/VDITournees/TourneesView';
import { TechnicianView } from '../components/VDITournees/TechnicianView';
import { AdminImpersonationBar } from '../components/shared/AdminImpersonationBar';
import './index.css';

// ==========================================
// TYPES
// ==========================================

export type VDIView = 'dashboard' | 'inventory' | 'tournees' | 'techniciens' | 'sync';

// ==========================================
// APP COMPONENT
// ==========================================

function App() {
  const [currentView, setCurrentView] = useState<VDIView>('dashboard');

  const handleNavigate = (view: VDIView) => {
    setCurrentView(view);
  };

  const handleBackToDashboard = () => {
    setCurrentView('dashboard');
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Admin Impersonation Bar - TOUJOURS en haut si admin */}
      <AdminImpersonationBar />

      {/* Top Navigation Bar - Affiché seulement si PAS sur dashboard */}
      {currentView !== 'dashboard' && (
        <nav className="bg-white border-b border-gray-200 shadow-sm sticky top-0 z-50">
          <div className="max-w-full px-6 py-4">
            <div className="flex items-center justify-between">
              <button
                onClick={handleBackToDashboard}
                className="flex items-center gap-2 text-blue-600 hover:text-blue-700 font-medium transition-colors"
              >
                <span className="text-xl">←</span>
                <span>Retour au Dashboard</span>
              </button>

              <div className="flex items-center gap-4">
                <span className="text-2xl">
                  {currentView === 'inventory' && '📦'}
                  {currentView === 'tournees' && '🗺️'}
                  {currentView === 'techniciens' && '👨‍🔧'}
                  {currentView === 'sync' && '🔄'}
                </span>
                <h1 className="text-xl font-bold text-gray-900">
                  {currentView === 'inventory' && 'Inventaire'}
                  {currentView === 'tournees' && 'Tournées'}
                  {currentView === 'techniciens' && 'Techniciens'}
                  {currentView === 'sync' && 'Sync Gazelle'}
                </h1>
              </div>

              <div className="w-40" /> {/* Spacer pour centrer */}
            </div>
          </div>
        </nav>
      )}

      {/* Main Content */}
      <main className={currentView === 'dashboard' ? '' : 'px-6 py-8'}>
        {currentView === 'dashboard' && (
          <VDIDashboard onNavigate={handleNavigate} />
        )}

        {currentView === 'inventory' && (
          <VDIInventory />
        )}

        {currentView === 'tournees' && (
          <div className="h-[calc(100vh-80px)]">
            <TourneesView etablissement="vincent-dindy" />
          </div>
        )}

        {currentView === 'techniciens' && (
          <TechnicianView etablissement="vincent-dindy" />
        )}

        {currentView === 'sync' && (
          <div className="max-w-4xl mx-auto text-center py-12">
            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-12">
              <span className="text-6xl mb-4 block">🔄</span>
              <h2 className="text-2xl font-bold text-gray-900 mb-4">
                Sync Gazelle - En développement
              </h2>
              <p className="text-gray-600 mb-6">
                Le script de push vers l'API Gazelle sera implémenté ici.
              </p>
              <p className="text-sm text-gray-500">
                Cette fonctionnalité permettra de synchroniser les modifications locales
                (statut, notes, observations) vers l'API Gazelle de manière bidirectionnelle.
              </p>
            </div>
          </div>
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
