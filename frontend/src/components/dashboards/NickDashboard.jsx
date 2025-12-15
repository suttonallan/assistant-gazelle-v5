import { useState, useEffect } from 'react'
import TechniciensInventaireTable from '../TechniciensInventaireTable'
import VincentDIndyDashboard from '../VincentDIndyDashboard'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

/**
 * Dashboard pour Nick (Gestionnaire)
 *
 * Fonctionnalités:
 * - Voir inventaire de tous les techniciens
 * - Créer des tournées d'accords
 * - Gérer les dates et noms de tournées
 */
const NickDashboard = ({ currentUser }) => {
  const [activeTab, setActiveTab] = useState('inventaire')
  const [tournees, setTournees] = useState([])
  const [selectedTournee, setSelectedTournee] = useState(null) // Pour afficher les détails d'une tournée

  // Formulaire nouvelle tournée
  const [newTournee, setNewTournee] = useState({
    nom: '',
    date_debut: '',
    date_fin: '',
    notes: ''
  })

  useEffect(() => {
    loadTournees()
  }, [])

  const loadTournees = async () => {
    try {
      // Pour l'instant, charger depuis localStorage
      // (en attendant la création de la table tournees_accords dans Supabase)
      const saved = localStorage.getItem('tournees_accords')
      if (saved) {
        setTournees(JSON.parse(saved))
      } else {
        setTournees([])
      }
    } catch (err) {
      console.error('Erreur chargement tournées:', err)
      setTournees([])
    }
  }

  const handleCreateTournee = async (e) => {
    e.preventDefault()

    if (!newTournee.nom || !newTournee.date_debut) {
      alert('⚠️ Veuillez remplir au minimum le nom et la date de début')
      return
    }

    try {
      // Créer la tournée avec un ID unique
      const nouvelleTournee = {
        id: `tournee_${Date.now()}`,
        ...newTournee,
        technicien_responsable: currentUser?.email || 'nicolas@example.com',
        techniciens_assignes: [], // Pour futur: liste des techniciens assignés à cette tournée
        status: 'planifiee',
        created_at: new Date().toISOString()
      }

      // Sauvegarder dans localStorage (temporaire)
      const existing = JSON.parse(localStorage.getItem('tournees_accords') || '[]')
      existing.push(nouvelleTournee)
      localStorage.setItem('tournees_accords', JSON.stringify(existing))

      alert('✅ Tournée créée avec succès!')
      setNewTournee({ nom: '', date_debut: '', date_fin: '', notes: '' })
      await loadTournees()
    } catch (err) {
      alert('❌ Erreur: ' + err.message)
    }
  }

  const handleDeleteTournee = async (tourneeId) => {
    if (!confirm('Êtes-vous sûr de vouloir supprimer cette tournée ?')) {
      return
    }

    try {
      const existing = JSON.parse(localStorage.getItem('tournees_accords') || '[]')
      const updated = existing.filter(t => t.id !== tourneeId)
      localStorage.setItem('tournees_accords', JSON.stringify(updated))

      alert('✅ Tournée supprimée')
      await loadTournees()
    } catch (err) {
      alert('❌ Erreur: ' + err.message)
    }
  }

  const handleActiverTournee = async (tourneeId) => {
    try {
      const existing = JSON.parse(localStorage.getItem('tournees_accords') || '[]')
      // Désactiver toutes les tournées, puis activer celle-ci
      const updated = existing.map(t => ({
        ...t,
        status: t.id === tourneeId ? 'en_cours' : (t.status === 'en_cours' ? 'planifiee' : t.status)
      }))
      localStorage.setItem('tournees_accords', JSON.stringify(updated))

      alert('✅ Tournée activée')
      await loadTournees()
    } catch (err) {
      alert('❌ Erreur: ' + err.message)
    }
  }

  const handleConclureTournee = async (tourneeId) => {
    if (!confirm('Êtes-vous sûr de vouloir conclure cette tournée ?')) {
      return
    }

    try {
      const existing = JSON.parse(localStorage.getItem('tournees_accords') || '[]')
      const updated = existing.map(t => ({
        ...t,
        status: t.id === tourneeId ? 'terminee' : t.status
      }))
      localStorage.setItem('tournees_accords', JSON.stringify(updated))

      alert('✅ Tournée conclue')
      await loadTournees()
    } catch (err) {
      alert('❌ Erreur: ' + err.message)
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
        <VincentDIndyDashboard currentUser={currentUser} tourneeId={selectedTournee.id} />
      </div>
    )
  }

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
        <TechniciensInventaireTable currentUser={currentUser} allowComment={true} />
      )}

      {activeTab === 'tournees' && (
        <div>
          <h2 className="text-xl font-bold mb-4">Créer une nouvelle tournée d'accords</h2>

          {/* Formulaire création tournée */}
          <form onSubmit={handleCreateTournee} className="bg-white rounded-lg shadow p-6 mb-6">
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Nom de la tournée *
              </label>
              <input
                type="text"
                value={newTournee.nom}
                onChange={(e) => setNewTournee({ ...newTournee, nom: e.target.value })}
                placeholder="ex: Tournée Place des Arts - Janvier 2025"
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                required
              />
            </div>

            <div className="flex gap-3 mb-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Date de début *
                </label>
                <input
                  type="date"
                  value={newTournee.date_debut}
                  onChange={(e) => setNewTournee({ ...newTournee, date_debut: e.target.value })}
                  className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  style={{ width: '170px' }}
                  required
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Date de fin
                </label>
                <input
                  type="date"
                  value={newTournee.date_fin}
                  onChange={(e) => setNewTournee({ ...newTournee, date_fin: e.target.value })}
                  className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  style={{ width: '170px' }}
                />
              </div>
            </div>

            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Notes
              </label>
              <textarea
                value={newTournee.notes}
                onChange={(e) => setNewTournee({ ...newTournee, notes: e.target.value })}
                placeholder="Notes additionnelles sur la tournée..."
                rows="3"
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <button
              type="submit"
              className="px-6 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 font-semibold"
            >
              ➕ Créer la tournée
            </button>
          </form>

          {/* Liste des tournées existantes */}
          <h3 className="text-lg font-bold mb-3">Tournées planifiées</h3>
          <div className="space-y-3">
            {tournees.length === 0 ? (
              <p className="text-gray-500">Aucune tournée planifiée</p>
            ) : (
              tournees.map((tournee, idx) => (
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

                      {tournee.status === 'planifiee' && (
                        <button
                          onClick={() => handleActiverTournee(tournee.id)}
                          className="px-3 py-1 bg-green-100 text-green-700 rounded hover:bg-green-200 text-sm font-medium"
                          title="Activer cette tournée"
                        >
                          ▶️ Activer
                        </button>
                      )}

                      {tournee.status === 'en_cours' && (
                        <button
                          onClick={() => handleConclureTournee(tournee.id)}
                          className="px-3 py-1 bg-orange-100 text-orange-700 rounded hover:bg-orange-200 text-sm font-medium"
                          title="Conclure cette tournée"
                        >
                          ✅ Conclure
                        </button>
                      )}

                      <button
                        onClick={() => setSelectedTournee(tournee)}
                        className="px-3 py-1 bg-blue-600 text-white rounded hover:bg-blue-700 text-sm font-medium"
                        title="Voir les pianos de cette tournée"
                      >
                        🎹 Voir les pianos
                      </button>
                      <button
                        onClick={() => handleDeleteTournee(tournee.id)}
                        className="px-3 py-1 bg-red-100 text-red-700 rounded hover:bg-red-200 text-sm font-medium"
                        title="Supprimer cette tournée"
                      >
                        🗑️
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

export default NickDashboard
