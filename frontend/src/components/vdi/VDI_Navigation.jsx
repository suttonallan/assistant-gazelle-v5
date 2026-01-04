/**
 * VDI_Navigation - Composant de navigation avec pill buttons
 *
 * Switche entre les vues "Gestion & Pianos" (Nicolas) et "Technicien"
 */

import React from 'react';

export default function VDI_Navigation({
  currentView,
  setCurrentView,
  setSelectedIds,
  hideNickView,
  selectedLocation,
  setSelectedLocation
}) {
  // Pas de navigation si vue forcée (technicien-only mode)
  if (hideNickView) return null;

  const handleViewChange = (viewKey) => {
    setCurrentView(viewKey);
    setSelectedIds(new Set());
  };

  const tabs = [
    { key: 'nicolas', label: 'Gestion & Pianos' },
    { key: 'technicien', label: 'Technicien' },
  ];

  const etablissements = [
    { value: 'vincent-dindy', label: '🎹 Vincent d\'Indy' },
    { value: 'orford', label: '🏔️ Orford' },
    { value: 'place-des-arts', label: '🎭 Place des Arts' },
  ];

  return (
    <div className="flex gap-4 mb-4 items-center">
      {/* Navigation pills */}
      <div className="flex gap-2">
        {tabs.map(tab => (
          <button
            key={tab.key}
            onClick={() => handleViewChange(tab.key)}
            className={`px-4 py-2 text-sm font-medium rounded-full transition-colors ${
              currentView === tab.key
                ? 'bg-blue-500 text-white shadow-sm'
                : 'bg-white text-gray-700 hover:bg-gray-50 border border-gray-200'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Sélecteur d'établissement */}
      <div className="flex items-center gap-2">
        <label className="text-sm font-medium text-gray-700">Établissement:</label>
        <select
          value={selectedLocation}
          onChange={(e) => setSelectedLocation(e.target.value)}
          className="px-3 py-2 text-sm border border-gray-300 rounded-lg bg-white hover:bg-gray-50 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
        >
          {etablissements.map(etab => (
            <option key={etab.value} value={etab.value}>
              {etab.label}
            </option>
          ))}
        </select>
      </div>
    </div>
  );
}
