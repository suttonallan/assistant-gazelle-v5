import { useState, useEffect } from 'react'

// Utiliser le proxy Vite en développement, ou l'URL de production
const API_URL = import.meta.env.VITE_API_URL || (import.meta.env.DEV ? '' : 'https://assistant-gazelle-v5-api.onrender.com')

export default function DashboardHome({ currentUser }) {
  const [activities, setActivities] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    loadActivities()
    // Recharger toutes les 30 secondes
    const interval = setInterval(loadActivities, 30000)
    return () => clearInterval(interval)
  }, [])

  const loadActivities = async () => {
    try {
      setLoading(true)
      // Utiliser /api pour que le proxy Vite redirige vers le backend
      const response = await fetch(`${API_URL}/api/vincent-dindy/activity?limit=50`)
      const data = await response.json()
      setActivities(data.activities || [])
      setError(null)
    } catch (err) {
      console.error('Erreur chargement activités:', err)
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const formatDate = (isoString) => {
    if (!isoString) return 'Date inconnue'
    const date = new Date(isoString)
    const now = new Date()
    const diffMs = now - date
    const diffMins = Math.floor(diffMs / 60000)
    const diffHours = Math.floor(diffMs / 3600000)
    const diffDays = Math.floor(diffMs / 86400000)

    if (diffMins < 1) return "À l'instant"
    if (diffMins < 60) return `Il y a ${diffMins} min`
    if (diffHours < 24) return `Il y a ${diffHours}h`
    if (diffDays < 7) return `Il y a ${diffDays}j`

    return date.toLocaleDateString('fr-CA', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  const getStatusBadge = (status) => {
    const badges = {
      'selected': { color: 'bg-yellow-100 text-yellow-800', text: 'Sélectionné' },
      'completed': { color: 'bg-green-100 text-green-800', text: 'Complété' },
      'normal': { color: 'bg-gray-100 text-gray-800', text: 'Normal' },
      'proposed': { color: 'bg-blue-100 text-blue-800', text: 'Proposé' }
    }
    const badge = badges[status] || { color: 'bg-gray-100 text-gray-600', text: status }
    return (
      <span className={`px-2 py-1 rounded-full text-xs font-medium ${badge.color}`}>
        {badge.text}
      </span>
    )
  }

  const getUserInitials = (email) => {
    if (!email) return '??'
    const name = email.split('@')[0]
    return name.charAt(0).toUpperCase()
  }

  const getUserColor = (email) => {
    const colors = [
      'bg-blue-500',
      'bg-green-500',
      'bg-purple-500',
      'bg-pink-500',
      'bg-indigo-500',
      'bg-red-500'
    ]
    const hash = email?.split('').reduce((acc, char) => acc + char.charCodeAt(0), 0) || 0
    return colors[hash % colors.length]
  }

  if (loading && activities.length === 0) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-500">Chargement de l'historique...</div>
      </div>
    )
  }

  return (
    <div className="max-w-7xl mx-auto px-4 py-6">
      {/* En-tête */}
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-gray-800 mb-2">
          Tableau de bord - Historique d'activité
        </h2>
        <p className="text-gray-600">
          Suivi des modifications effectuées sur les pianos
        </p>
      </div>

      {/* Stats rapides */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        <div className="bg-white rounded-lg shadow p-6">
          <div className="text-sm text-gray-600 mb-1">Total modifications</div>
          <div className="text-3xl font-bold text-gray-800">{activities.length}</div>
        </div>
        <div className="bg-white rounded-lg shadow p-6">
          <div className="text-sm text-gray-600 mb-1">Dernière modification</div>
          <div className="text-lg font-semibold text-gray-800">
            {activities.length > 0 ? formatDate(activities[0].updated_at) : 'Aucune'}
          </div>
        </div>
        <div className="bg-white rounded-lg shadow p-6">
          <div className="text-sm text-gray-600 mb-1">Utilisateurs actifs</div>
          <div className="text-3xl font-bold text-gray-800">
            {new Set(activities.map(a => a.updated_by)).size}
          </div>
        </div>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg mb-4">
          Erreur: {error}
        </div>
      )}

      {/* Liste des activités */}
      <div className="bg-white rounded-lg shadow overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-200 flex justify-between items-center">
          <h3 className="text-lg font-semibold text-gray-800">
            Activités récentes ({activities.length})
          </h3>
          <button
            onClick={loadActivities}
            className="px-3 py-1 text-sm bg-blue-50 hover:bg-blue-100 text-blue-600 rounded transition-colors"
          >
            🔄 Actualiser
          </button>
        </div>

        <div className="divide-y divide-gray-200 max-h-[600px] overflow-y-auto">
          {activities.length === 0 ? (
            <div className="px-6 py-12 text-center text-gray-500">
              Aucune activité enregistrée pour le moment
            </div>
          ) : (
            activities.map((activity, index) => (
              <div
                key={`${activity.piano_id}-${index}`}
                className="px-6 py-4 hover:bg-gray-50 transition-colors"
              >
                <div className="flex items-start gap-4">
                  {/* Avatar utilisateur */}
                  <div className={`w-10 h-10 rounded-full ${getUserColor(activity.updated_by)} flex items-center justify-center text-white font-bold flex-shrink-0`}>
                    {getUserInitials(activity.updated_by)}
                  </div>

                  {/* Contenu */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="font-medium text-gray-900">
                        {activity.updated_by?.split('@')[0] || 'Utilisateur inconnu'}
                      </span>
                      <span className="text-gray-500 text-sm">
                        a modifié le piano
                      </span>
                      <span className="font-mono text-sm bg-gray-100 px-2 py-0.5 rounded">
                        {activity.piano_id}
                      </span>
                    </div>

                    <div className="flex items-center gap-3 text-sm text-gray-600 mb-2">
                      <span>{formatDate(activity.updated_at)}</span>
                      {activity.status && getStatusBadge(activity.status)}
                    </div>

                    {activity.observations && (
                      <div className="text-sm text-gray-700 bg-gray-50 px-3 py-2 rounded border-l-2 border-blue-400">
                        💬 {activity.observations}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  )
}
