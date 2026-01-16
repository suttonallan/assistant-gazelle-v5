import React, { useState, useEffect } from 'react'
import { API_URL } from '../utils/apiConfig'

/**
 * Carte spéciale pour les alertes de maintenance institutionnelle
 *
 * Affiche les alertes housse/PL/réservoir uniquement pour:
 * - Vincent d'Indy
 * - Place des Arts
 * - Orford
 *
 * Clignote en rouge s'il y a des alertes non résolues
 */
const MaintenanceAlertsCard = () => {
  const [alerts, setAlerts] = useState([])
  const [stats, setStats] = useState({ total: 0, unresolved: 0, resolved: 0 })
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [lastUpdate, setLastUpdate] = useState(null)

  // Clients institutionnels à surveiller
  const INSTITUTIONAL_CLIENTS = [
    'Vincent d\'Indy',
    'Place des Arts',
    'Orford'
  ]

  // Charger les alertes
  const loadAlerts = async () => {
    try {
      setLoading(true)
      setError(null)

      // Récupérer les alertes actives (non résolues) pour les institutions
      const response = await fetch(
        `${API_URL}/api/humidity-alerts/institutional`,
        {
          method: 'GET',
          headers: { 'Content-Type': 'application/json' }
        }
      )

      if (!response.ok) {
        throw new Error(`Erreur ${response.status}`)
      }

      const data = await response.json()

      setAlerts(data.alerts || [])
      setStats(data.stats || { total: 0, unresolved: 0, resolved: 0 })
      setLastUpdate(new Date())

    } catch (err) {
      console.error('Erreur chargement alertes maintenance:', err)
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadAlerts()
    // Rafraîchir toutes les 5 minutes
    const interval = setInterval(loadAlerts, 5 * 60 * 1000)
    return () => clearInterval(interval)
  }, [])

  // Styles avec animation clignotante si alertes non résolues
  const cardClassName = stats.unresolved > 0
    ? 'bg-red-50 border-2 border-red-500 rounded-lg shadow-lg p-6 animate-pulse-slow'
    : 'bg-white border border-gray-200 rounded-lg shadow p-6'

  const headerClassName = stats.unresolved > 0
    ? 'text-red-700 font-bold text-xl mb-4 flex items-center'
    : 'text-gray-800 font-bold text-xl mb-4 flex items-center'

  if (loading && alerts.length === 0) {
    return (
      <div className="bg-white border border-gray-200 rounded-lg shadow p-6">
        <div className="animate-pulse">
          <div className="h-6 bg-gray-200 rounded w-3/4 mb-4"></div>
          <div className="h-4 bg-gray-200 rounded w-1/2"></div>
        </div>
      </div>
    )
  }

  return (
    <div className={cardClassName}>
      {/* En-tête avec icône d'alerte si nécessaire */}
      <div className={headerClassName}>
        {stats.unresolved > 0 && (
          <svg className="w-6 h-6 mr-2 animate-bounce" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
          </svg>
        )}
        <span>🏛️ Alertes Maintenance Institutionnelle</span>
      </div>

      {/* Statistiques */}
      <div className="grid grid-cols-3 gap-4 mb-6">
        <div className="text-center">
          <div className="text-2xl font-bold text-gray-800">{stats.total}</div>
          <div className="text-sm text-gray-600">Total</div>
        </div>
        <div className="text-center">
          <div className={`text-2xl font-bold ${stats.unresolved > 0 ? 'text-red-600' : 'text-green-600'}`}>
            {stats.unresolved}
          </div>
          <div className="text-sm text-gray-600">Non résolues</div>
        </div>
        <div className="text-center">
          <div className="text-2xl font-bold text-green-600">{stats.resolved}</div>
          <div className="text-sm text-gray-600">Résolues</div>
        </div>
      </div>

      {/* Clients surveillés */}
      <div className="mb-4 p-3 bg-blue-50 rounded border border-blue-200">
        <div className="text-sm text-blue-800 font-medium mb-1">Institutions surveillées:</div>
        <div className="text-xs text-blue-700">
          {INSTITUTIONAL_CLIENTS.join(' • ')}
        </div>
      </div>

      {/* Liste des alertes non résolues */}
      {stats.unresolved > 0 && (
        <div className="space-y-3">
          <div className="font-semibold text-red-700 mb-2">⚠️ Alertes actives:</div>
          {alerts.filter(a => !a.is_resolved).map((alert, idx) => (
            <div key={idx} className="bg-white border-l-4 border-red-500 p-3 rounded shadow-sm">
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center mb-1">
                    <span className={`
                      px-2 py-1 text-xs font-semibold rounded mr-2
                      ${alert.alert_type === 'housse' ? 'bg-orange-100 text-orange-800' : ''}
                      ${alert.alert_type === 'alimentation' ? 'bg-red-100 text-red-800' : ''}
                      ${alert.alert_type === 'reservoir' ? 'bg-blue-100 text-blue-800' : ''}
                    `}>
                      {alert.alert_type === 'housse' && '🛡️ Housse'}
                      {alert.alert_type === 'alimentation' && '🔌 Alimentation'}
                      {alert.alert_type === 'reservoir' && '💧 Réservoir'}
                    </span>
                    <span className="text-sm font-medium text-gray-900">
                      {alert.client_name || 'Client inconnu'}
                    </span>
                  </div>
                  {/* Numéro de local et piano */}
                  <div className="text-xs text-gray-600 mb-2 space-y-1">
                    <div>
                      📍 <span className="font-medium">Local:</span> {alert.room_number || 'N/A'} •
                      🎹 <span className="font-medium">Piano:</span> {alert.piano_make} {alert.piano_model || ''}
                    </div>
                  </div>
                  {/* Note exacte du technicien */}
                  <div className="text-sm text-gray-700 bg-gray-50 p-2 rounded border-l-2 border-gray-300 mb-2">
                    <div className="text-xs text-gray-500 font-semibold mb-1">Note du technicien:</div>
                    <div className="italic">"{alert.technician_note || alert.description}"</div>
                  </div>
                  {/* Date */}
                  <div className="text-xs text-gray-400">
                    📅 {new Date(alert.observed_at).toLocaleDateString('fr-CA')}
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Message si aucune alerte */}
      {stats.total === 0 && !loading && (
        <div className="text-center py-8 text-gray-500">
          <svg className="w-16 h-16 mx-auto mb-3 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <div className="text-lg font-medium">Aucune alerte détectée</div>
          <div className="text-sm">Tout est en ordre dans les institutions surveillées</div>
        </div>
      )}

      {/* Alertes résolues (collapsible) */}
      {stats.resolved > 0 && (
        <details className="mt-4">
          <summary className="cursor-pointer text-sm text-gray-600 hover:text-gray-800 font-medium">
            ✅ {stats.resolved} alerte{stats.resolved > 1 ? 's' : ''} résolue{stats.resolved > 1 ? 's' : ''}
          </summary>
          <div className="mt-2 space-y-2">
            {alerts.filter(a => a.is_resolved).map((alert, idx) => (
              <div key={idx} className="bg-green-50 border-l-4 border-green-500 p-2 rounded text-sm">
                <div className="font-medium text-green-800">{alert.client_name}</div>
                <div className="text-gray-600 text-xs">{alert.description}</div>
              </div>
            ))}
          </div>
        </details>
      )}

      {/* Footer avec dernière mise à jour */}
      <div className="mt-4 pt-4 border-t border-gray-200 flex items-center justify-between">
        <button
          onClick={loadAlerts}
          disabled={loading}
          className="text-sm text-blue-600 hover:text-blue-800 font-medium disabled:text-gray-400"
        >
          {loading ? '🔄 Actualisation...' : '🔄 Actualiser'}
        </button>
        {lastUpdate && (
          <div className="text-xs text-gray-500">
            Mis à jour: {lastUpdate.toLocaleTimeString('fr-CA')}
          </div>
        )}
      </div>

      {/* Erreur */}
      {error && (
        <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded text-sm text-red-700">
          ⚠️ Erreur: {error}
        </div>
      )}
    </div>
  )
}

// Style CSS personnalisé pour l'animation pulse lente
const style = document.createElement('style')
style.textContent = `
  @keyframes pulse-slow {
    0%, 100% {
      opacity: 1;
    }
    50% {
      opacity: 0.8;
    }
  }

  .animate-pulse-slow {
    animation: pulse-slow 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
  }
`
document.head.appendChild(style)

export default MaintenanceAlertsCard
