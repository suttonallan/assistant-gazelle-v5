import { useState } from 'react'
import TechniciensInventaireTable from '../TechniciensInventaireTable'
import VincentDIndyDashboard from '../VincentDIndyDashboard'
import TravelFeeCalculator from '../admin/TravelFeeCalculator'
import KilometersCalculator from '../admin/KilometersCalculator'

const API_URL = import.meta.env.VITE_API_URL || 'https://assistant-gazelle-v5-api.onrender.com'

/**
 * Dashboard pour Nick (Gestionnaire)
 *
 * Fonctionnalités:
 * - Voir inventaire de tous les techniciens
 * - Accéder au module Vincent d'Indy (tournées, pianos)
 * - Utiliser les calculateurs (frais de déplacement, kilomètres)
 */
const NickDashboard = ({ currentUser }) => {
  const [activeTab, setActiveTab] = useState('inventaire')

  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-gray-900">Dashboard Nick</h1>
        <p className="text-gray-600">Gestionnaire - Inventaire & tournées</p>
      </div>

      {/* Onglets */}
      <div className="border-b border-gray-200 mb-6">
        <nav className="flex gap-4">
          <button
            onClick={() => setActiveTab('inventaire')}
            className={`px-4 py-2 border-b-2 font-medium ${
              activeTab === 'inventaire'
                ? 'border-blue-600 text-blue-600'
                : 'border-transparent text-gray-600 hover:text-gray-900'
            }`}
          >
            📦 Inventaire techniciens
          </button>
          <button
            onClick={() => setActiveTab('vincent-dindy')}
            className={`px-4 py-2 border-b-2 font-medium ${
              activeTab === 'vincent-dindy'
                ? 'border-blue-600 text-blue-600'
                : 'border-transparent text-gray-600 hover:text-gray-900'
            }`}
          >
            🎵 Vincent d'Indy
          </button>
          <button
            onClick={() => setActiveTab('calculateur')}
            className={`px-4 py-2 border-b-2 font-medium ${
              activeTab === 'calculateur'
                ? 'border-blue-600 text-blue-600'
                : 'border-transparent text-gray-600 hover:text-gray-900'
            }`}
          >
            💰 Calculateur
          </button>
        </nav>
      </div>

      {/* Contenu selon onglet */}
      {activeTab === 'inventaire' && (
        <TechniciensInventaireTable currentUser={currentUser} allowComment={true} />
      )}

      {activeTab === 'vincent-dindy' && (
        <VincentDIndyDashboard currentUser={currentUser} />
      )}

      {activeTab === 'calculateur' && (
        <div className="space-y-8">
          <TravelFeeCalculator />
          <div className="border-t border-gray-200 pt-8">
            <KilometersCalculator />
          </div>
        </div>
      )}
    </div>
  )
}

export default NickDashboard
