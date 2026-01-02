import { useState, useEffect } from 'react'
import TechniciensInventaireTable from '../TechniciensInventaireTable'
import VincentDIndyDashboard from '../VincentDIndyDashboard'

/**
 * Dashboard pour Jean-Philippe (Technicien)
 *
 * Fonctionnalités:
 * - Voir et modifier l'inventaire (3 colonnes: Allan, Jean-Philippe, Nick)
 * - Voir les tournées d'accords (lecture seule, pas de création)
 * - Voir les pianos à accorder lors d'une tournée
 */
const JeanPhilippeDashboard = ({ currentUser }) => {
  const [activeTab, setActiveTab] = useState('inventaire')
  const [tournees, setTournees] = useState([])
  const [selectedTournee, setSelectedTournee] = useState(null)

  useEffect(() => {
    loadTournees()
  }, [])

  const loadTournees = async () => {
    try {
      const saved = localStorage.getItem('tournees_accords')
      if (saved) {
        const allTournees = JSON.parse(saved)

        // Pour l'instant: afficher toutes les tournées actives
        // Futur: filtrer par techniciens_assignes
        // const myEmail = currentUser?.email
        // const myTournees = allTournees.filter(t =>
        //   t.status === 'en_cours' &&
        //   (t.techniciens_assignes.length === 0 || t.techniciens_assignes.includes(myEmail))
        // )

        setTournees(allTournees)
      } else {
        setTournees([])
      }
    } catch (err) {
      console.error('Erreur chargement tournées:', err)
      setTournees([])
    }
  }

  // Si une tournée est sélectionnée, afficher la vue des pianos
  if (selectedTournee) {
    return (
      <div className="p-6">
        <div className="mb-6 flex items-center justify-between">
          <div>
            <button
              onClick={() => setSelectedTournee(null)}
              className="mb-2 text-blue-600 hover:text-blue-800 flex items-center gap-2"
            >
              ← Retour aux tournées
            </button>
            <h1 className="text-3xl font-bold text-gray-900">{selectedTournee.nom}</h1>
            <p className="text-gray-600">
              📅 Du {new Date(selectedTournee.date_debut).toLocaleDateString('fr-CA')}
              {selectedTournee.date_fin && ` au ${new Date(selectedTournee.date_fin).toLocaleDateString('fr-CA')}`}
            </p>
          </div>
        </div>
        <VincentDIndyDashboard 
          currentUser={currentUser} 
          tourneeId={selectedTournee.id}
          initialView="technicien"
          hideNickView={true}
          hideLocationSelector={true}
        />
      </div>
    )
  }

  return (
    <div className="p-6">
      {/* PAS de titre - Navigation gérée par bandeau supérieur */}

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
            📦 Mon inventaire
          </button>
          <button
            onClick={() => setActiveTab('tournees')}
            className={`px-4 py-2 border-b-2 font-medium ${
              activeTab === 'tournees'
                ? 'border-blue-600 text-blue-600'
                : 'border-transparent text-gray-600 hover:text-gray-900'
            }`}
          >
            🎹 Tournées d'accords
          </button>
        </nav>
      </div>

      {/* Contenu selon onglet */}
      {activeTab === 'inventaire' && (
        <>
          <TechniciensInventaireTable currentUser={currentUser} allowComment={true} />
          <div className="mt-4 p-4 bg-blue-50 border border-blue-200 rounded-lg">
            <p className="text-sm text-blue-800">
              💡 <strong>Votre colonne est surlignée en vert</strong> - Vous pouvez modifier toutes les colonnes d'inventaire (la vôtre et celles des collègues).
            </p>
          </div>
        </>
      )}

      {activeTab === 'tournees' && (
        <div>
          <h2 className="text-xl font-bold mb-4">Tournée active</h2>
          <div className="space-y-3">
            {tournees.filter(t => t.status === 'en_cours').length === 0 ? (
              <p className="text-gray-500">Aucune tournée active pour le moment</p>
            ) : (
              tournees.filter(t => t.status === 'en_cours').map((tournee, idx) => (
                <div key={idx} className="bg-white rounded-lg shadow p-4 border-l-4 border-blue-600">
                  <div className="flex justify-between items-start">
                    <div className="flex-1">
                      <h4 className="font-bold text-gray-900">{tournee.nom}</h4>
                      <p className="text-sm text-gray-600 mt-1">
                        📅 Du {new Date(tournee.date_debut).toLocaleDateString('fr-CA')}
                        {tournee.date_fin && ` au ${new Date(tournee.date_fin).toLocaleDateString('fr-CA')}`}
                      </p>
                      {tournee.notes && (
                        <p className="text-sm text-gray-500 mt-2">{tournee.notes}</p>
                      )}
                    </div>
                    <div className="flex items-center gap-2">
                      <span className={`px-3 py-1 rounded text-sm font-semibold ${
                        tournee.status === 'terminee' ? 'bg-green-100 text-green-800' :
                        tournee.status === 'en_cours' ? 'bg-blue-100 text-blue-800' :
                        'bg-gray-100 text-gray-800'
                      }`}>
                        {tournee.status === 'terminee' ? 'Terminée' :
                         tournee.status === 'en_cours' ? 'En cours' :
                         'Planifiée'}
                      </span>
                      <button
                        onClick={() => setSelectedTournee(tournee)}
                        className="px-3 py-1 bg-blue-600 text-white rounded hover:bg-blue-700 text-sm font-medium"
                        title="Voir les pianos de cette tournée"
                      >
                        🎹 Voir les pianos
                      </button>
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  )
}

export default JeanPhilippeDashboard
