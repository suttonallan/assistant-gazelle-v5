/**
 * VDIInventory - Page Principale Inventaire
 *
 * Route: /vdi/inventaire
 *
 * Page complète pour gestion inventaire pianos:
 * - Table avec Shift+Clic
 * - Batch hide/show
 * - Filtres et recherche
 * - Stats globales
 */

import React from 'react';
import { InventoryTable } from './InventoryTable';

export function VDIInventory() {
  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto px-4 py-8">
        {/* Page Header */}
        <div className="mb-6">
          <h1 className="text-3xl font-bold text-gray-900">
            Inventaire Vincent d'Indy
          </h1>
          <p className="text-gray-600 mt-2">
            Gérez la visibilité des pianos dans le système
          </p>
        </div>

        {/* Main Table */}
        <InventoryTable etablissement="vincent-dindy" />

        {/* Footer Instructions */}
        <div className="mt-6 bg-blue-50 border border-blue-200 rounded-lg p-4">
          <h3 className="text-sm font-semibold text-blue-900 mb-2">
            💡 Astuce: Sélection Rapide
          </h3>
          <ul className="text-sm text-blue-800 space-y-1">
            <li>• <strong>Clic simple</strong>: Sélectionner/désélectionner un piano</li>
            <li>• <strong>Shift+Clic</strong>: Sélectionner une plage de pianos</li>
            <li>• <strong>Checkbox "Tout"</strong>: Sélectionner/désélectionner tous les pianos affichés</li>
          </ul>
        </div>
      </div>
    </div>
  );
}

export default VDIInventory;
