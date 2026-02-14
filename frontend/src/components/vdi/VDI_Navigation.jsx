/**
 * VDI_Navigation - Composant de navigation avec pill buttons
 *
 * Switche entre les vues "Gestion & Pianos" (Nicolas) et "Technicien"
 */

import React from 'react';

export default function VDI_Navigation({ currentView, setCurrentView, setSelectedIds, hideNickView }) {
  // Pas de navigation si vue forcée (technicien-only mode)
  if (hideNickView) return null;

  const handleViewChange = (viewKey) => {
    setCurrentView(viewKey);
    setSelectedIds(new Set());
  };

  const tabs = [
    { key: 'nicolas', label: 'Gestion & Pianos' },
    { key: 'technicien', label: 'Technicien' },
    { key: 'vdi', label: 'À valider' },
  ];

  return (
    <div className="flex gap-2 mb-4">
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
  );
}
