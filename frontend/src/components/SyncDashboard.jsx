import { useState, useEffect } from 'react'
import { API_URL } from '../utils/apiConfig'

/**
 * SyncDashboard V6 - Tableau de bord des synchronisations et alertes
 *
 * Affiche:
 * - Timeline des dernières synchronisations
 * - Rapport d'activité (RV détectés)
 * - Alertes "Dernière Minute" en attente ou envoyées
 */
export default function SyncDashboard({ currentUser }) {
  const [syncLogs, setSyncLogs] = useState([])
  const [syncStats, setSyncStats] = useState(null)
  const [lateAlerts, setLateAlerts] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [activeTab, setActiveTab] = useState('timeline')

  useEffect(() => {
    loadAllData()
    // Rafraîchir toutes les 60 secondes
    const interval = setInterval(loadAllData, 60000)
    return () => clearInterval(interval)
  }, [])

  const loadAllData = async () => {
    setLoading(true)
    await Promise.all([
      loadSyncLogs(),
      loadSyncStats(),
      loadLateAlerts()
    ])
    setLoading(false)
  }

  const loadSyncLogs = async () => {
    try {
      const response = await fetch(`${API_URL}/api/sync-logs/recent?limit=20`)
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`)
      }
      const data = await response.json()
      setSyncLogs(data.logs || [])
    } catch (err) {
      console.error('Erreur chargement sync logs:', err)
      setError(err.message)
    }
  }

  const loadSyncStats = async () => {
    try {
      const response = await fetch(`${API_URL}/api/sync-logs/stats`)
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`)
      }
      const data = await response.json()
      setSyncStats(data)
    } catch (err) {
      console.error('Erreur chargement sync stats:', err)
    }
  }

  const loadLateAlerts = async () => {
    try {
      const response = await fetch(`${API_URL}/api/alertes-rv/late-assignment?limit=50`)
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`)
      }
      const data = await response.json()
      setLateAlerts(data.alerts || [])
    } catch (err) {
      console.error('Erreur chargement late alerts:', err)
    }
  }

  const formatDate = (isoString) => {
    if (!isoString) return 'N/A'
    try {
      const date = new Date(isoString)
      return date.toLocaleString('fr-CA', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit'
      })
    } catch {
      return isoString
    }
  }

  const formatRelativeTime = (isoString) => {
    if (!isoString) return 'N/A'
    const date = new Date(isoString)
    const now = new Date()
    const diffMs = now - date
    const diffMins = Math.floor(diffMs / 60000)
    const diffHours = Math.floor(diffMs / 3600000)

    if (diffMins < 1) return "À l'instant"
    if (diffMins < 60) return `Il y a ${diffMins} min`
    if (diffHours < 24) return `Il y a ${diffHours}h`
    return formatDate(isoString)
  }

  const getStatusBadge = (status) => {
    const badges = {
      'success': { color: 'bg-green-100 text-green-800', icon: '✅', text: 'Succès' },
      'error': { color: 'bg-red-100 text-red-800', icon: '❌', text: 'Erreur' },
      'warning': { color: 'bg-yellow-100 text-yellow-800', icon: '⚠️', text: 'Attention' },
      'running': { color: 'bg-blue-100 text-blue-800', icon: '⏳', text: 'En cours' },
      'pending': { color: 'bg-yellow-100 text-yellow-800', icon: '📤', text: 'En attente' },
      'sent': { color: 'bg-green-100 text-green-800', icon: '✉️', text: 'Envoyé' },
      'failed': { color: 'bg-red-100 text-red-800', icon: '❌', text: 'Échec' }
    }
    const badge = badges[status] || { color: 'bg-gray-100 text-gray-600', icon: '❓', text: status }
    return (
      <span className={`px-2 py-1 rounded-full text-xs font-medium ${badge.color}`}>
        {badge.icon} {badge.text}
      </span>
    )
  }

  const extractStats = (log) => {
    const stats = log.stats || log.tables_updated || {}
    if (typeof stats === 'string') {
      try {
        return JSON.parse(stats)
      } catch {
        return {}
      }
    }
    return stats
  }

  if (loading && syncLogs.length === 0) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-500">Chargement du tableau de bord...</div>
      </div>
    )
  }

  return (
    <div className="max-w-7xl mx-auto px-4 py-6">
      {/* En-tête */}
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-gray-800 mb-2">
          📊 Dashboard Synchronisation V6
        </h2>
        <p className="text-gray-600">
          Suivi des imports Gazelle → Supabase et alertes dernière minute
        </p>
      </div>

      {/* Stats rapides */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        <div className="bg-white rounded-lg shadow p-6">
          <div className="text-sm text-gray-600 mb-1">Syncs (24h)</div>
          <div className="text-3xl font-bold text-blue-600">
            {syncStats?.total_syncs || 0}
          </div>
          <div className="text-xs text-gray-500">
            {syncStats?.success_count || 0} succès / {syncStats?.error_count || 0} erreurs
          </div>
        </div>
        <div className="bg-white rounded-lg shadow p-6">
          <div className="text-sm text-gray-600 mb-1">Dernière sync</div>
          <div className="text-lg font-semibold text-gray-800">
            {formatRelativeTime(syncStats?.last_sync)}
          </div>
        </div>
        <div className="bg-white rounded-lg shadow p-6">
          <div className="text-sm text-gray-600 mb-1">Alertes en attente</div>
          <div className="text-3xl font-bold text-orange-600">
            {lateAlerts.filter(a => a.status === 'pending').length}
          </div>
        </div>
        <div className="bg-white rounded-lg shadow p-6">
          <div className="text-sm text-gray-600 mb-1">Alertes envoyées</div>
          <div className="text-3xl font-bold text-green-600">
            {lateAlerts.filter(a => a.status === 'sent').length}
          </div>
        </div>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg mb-4">
          Erreur: {error}
        </div>
      )}

      {/* Onglets */}
      <div className="bg-white rounded-lg shadow overflow-hidden">
        <div className="border-b border-gray-200">
          <nav className="flex -mb-px">
            <button
              onClick={() => setActiveTab('timeline')}
              className={`px-6 py-4 text-sm font-medium border-b-2 ${
                activeTab === 'timeline'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              📅 Timeline Syncs
            </button>
            <button
              onClick={() => setActiveTab('alerts')}
              className={`px-6 py-4 text-sm font-medium border-b-2 ${
                activeTab === 'alerts'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              🔔 Alertes Dernière Minute
              {lateAlerts.filter(a => a.status === 'pending').length > 0 && (
                <span className="ml-2 bg-orange-500 text-white text-xs px-2 py-0.5 rounded-full">
                  {lateAlerts.filter(a => a.status === 'pending').length}
                </span>
              )}
            </button>
          </nav>
        </div>

        {/* Contenu Timeline */}
        {activeTab === 'timeline' && (
          <div className="p-6">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-lg font-semibold text-gray-800">
                Dernières synchronisations ({syncLogs.length})
              </h3>
              <button
                onClick={loadAllData}
                className="px-3 py-1 text-sm bg-blue-50 hover:bg-blue-100 text-blue-600 rounded transition-colors"
              >
                🔄 Actualiser
              </button>
            </div>

            <div className="divide-y divide-gray-200 max-h-[500px] overflow-y-auto">
              {syncLogs.length === 0 ? (
                <div className="py-12 text-center text-gray-500">
                  Aucune synchronisation enregistrée
                </div>
              ) : (
                syncLogs.map((log, index) => {
                  const stats = extractStats(log)
                  return (
                    <div key={log.id || index} className="py-4 hover:bg-gray-50">
                      <div className="flex items-start justify-between">
                        <div>
                          <div className="flex items-center gap-3 mb-1">
                            <span className="font-medium text-gray-900">
                              {log.script_name || 'Sync Gazelle'}
                            </span>
                            {getStatusBadge(log.status)}
                          </div>
                          <div className="text-sm text-gray-600">
                            {formatDate(log.created_at)}
                            {log.execution_time_seconds && (
                              <span className="ml-2 text-gray-400">
                                ({log.execution_time_seconds}s)
                              </span>
                            )}
                          </div>
                          {log.message && (
                            <div className="text-sm text-gray-700 mt-1">
                              {log.message}
                            </div>
                          )}
                        </div>
                        <div className="text-right text-sm">
                          {stats && Object.keys(stats).length > 0 && (
                            <div className="flex flex-wrap gap-2 justify-end">
                              {Object.entries(stats).map(([key, value]) => (
                                <span
                                  key={key}
                                  className="bg-gray-100 px-2 py-1 rounded text-xs"
                                >
                                  {key}: <strong>{value}</strong>
                                </span>
                              ))}
                            </div>
                          )}
                        </div>
                      </div>
                      {(log.error_details || log.error_message) && (
                        <div className="mt-2 text-sm text-red-600 bg-red-50 px-3 py-2 rounded">
                          ❌ {log.error_details || log.error_message}
                        </div>
                      )}
                    </div>
                  )
                })
              )}
            </div>
          </div>
        )}

        {/* Contenu Alertes */}
        {activeTab === 'alerts' && (
          <div className="p-6">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-lg font-semibold text-gray-800">
                Alertes Dernière Minute ({lateAlerts.length})
              </h3>
              <button
                onClick={loadLateAlerts}
                className="px-3 py-1 text-sm bg-blue-50 hover:bg-blue-100 text-blue-600 rounded transition-colors"
              >
                🔄 Actualiser
              </button>
            </div>

            {/* Résumé des alertes */}
            <div className="grid grid-cols-3 gap-4 mb-6">
              <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 text-center">
                <div className="text-2xl font-bold text-yellow-600">
                  {lateAlerts.filter(a => a.status === 'pending').length}
                </div>
                <div className="text-sm text-yellow-800">En attente</div>
              </div>
              <div className="bg-green-50 border border-green-200 rounded-lg p-4 text-center">
                <div className="text-2xl font-bold text-green-600">
                  {lateAlerts.filter(a => a.status === 'sent').length}
                </div>
                <div className="text-sm text-green-800">Envoyées</div>
              </div>
              <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-center">
                <div className="text-2xl font-bold text-red-600">
                  {lateAlerts.filter(a => a.status === 'failed').length}
                </div>
                <div className="text-sm text-red-800">Échouées</div>
              </div>
            </div>

            <div className="divide-y divide-gray-200 max-h-[400px] overflow-y-auto">
              {lateAlerts.length === 0 ? (
                <div className="py-12 text-center text-gray-500">
                  Aucune alerte dernière minute
                </div>
              ) : (
                lateAlerts.map((alert, index) => (
                  <div key={alert.id || index} className="py-4 hover:bg-gray-50">
                    <div className="flex items-start justify-between">
                      <div>
                        <div className="flex items-center gap-3 mb-1">
                          <span className="font-medium text-gray-900">
                            📅 {alert.appointment_date} {alert.appointment_time?.slice(0, 5) || ''}
                          </span>
                          {getStatusBadge(alert.status)}
                        </div>
                        <div className="text-sm text-gray-700">
                          <span className="font-medium">Client:</span> {alert.client_name || 'N/A'}
                        </div>
                        <div className="text-sm text-gray-600">
                          <span className="font-medium">Technicien:</span>{' '}
                          {alert.technician_first_name || ''} {alert.technician_last_name || alert.technician_id || 'N/A'}
                          {alert.technician_email && (
                            <span className="text-gray-400 ml-1">
                              ({alert.technician_email})
                            </span>
                          )}
                        </div>
                        {alert.location && (
                          <div className="text-sm text-gray-500">
                            📍 {alert.location}
                          </div>
                        )}
                      </div>
                      <div className="text-right text-sm text-gray-500">
                        <div>Créé: {formatRelativeTime(alert.created_at)}</div>
                        {alert.scheduled_send_at && (
                          <div>Envoi prévu: {formatDate(alert.scheduled_send_at)}</div>
                        )}
                        {alert.sent_at && (
                          <div className="text-green-600">
                            ✅ Envoyé: {formatDate(alert.sent_at)}
                          </div>
                        )}
                      </div>
                    </div>
                    {alert.error_message && (
                      <div className="mt-2 text-sm text-red-600 bg-red-50 px-3 py-2 rounded">
                        ❌ {alert.error_message}
                      </div>
                    )}
                  </div>
                ))
              )}
            </div>
          </div>
        )}
      </div>

      {/* Note d'information */}
      <div className="mt-6 bg-blue-50 border border-blue-200 rounded-lg p-4">
        <h4 className="font-medium text-blue-800 mb-2">ℹ️ Fonctionnement</h4>
        <ul className="text-sm text-blue-700 space-y-1">
          <li>• <strong>Sync horaire (7h-21h)</strong>: Détecte les nouveaux RV ou changements de technicien</li>
          <li>• <strong>Alertes Dernière Minute</strong>: Notifie les techniciens quand un RV leur est assigné dans les 24h</li>
          <li>• <strong>Buffer 5 min</strong>: Les alertes attendent 5 min avant envoi (évite les doublons)</li>
          <li>• <strong>Heures repos</strong>: Alertes programmées 07h05 si détection entre 21h-7h</li>
        </ul>
      </div>
    </div>
  )
}
