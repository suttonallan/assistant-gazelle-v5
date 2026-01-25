import { useState, useEffect } from 'react'
import { API_URL } from '../utils/apiConfig'

/**
 * SyncDashboard - Tableau de Bord Unifié V6
 *
 * Vue unique et épurée:
 * - HAUT: Statut système (Vert/Rouge)
 * - MILIEU: Timeline des imports Gazelle
 * - BAS: Emails envoyés/prévus (alertes dernière minute)
 */
export default function SyncDashboard({ currentUser }) {
  const [syncLogs, setSyncLogs] = useState([])
  const [syncStats, setSyncStats] = useState(null)
  const [lateAlerts, setLateAlerts] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [lastRefresh, setLastRefresh] = useState(new Date())

  useEffect(() => {
    loadAllData()
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
    setLastRefresh(new Date())
    setLoading(false)
  }

  const loadSyncLogs = async () => {
    try {
      const response = await fetch(`${API_URL}/api/sync-logs/recent?limit=15`)
      if (response.ok) {
        const data = await response.json()
        setSyncLogs(data.logs || [])
      }
    } catch (err) {
      console.error('Erreur sync logs:', err)
      setError(err.message)
    }
  }

  const loadSyncStats = async () => {
    try {
      const response = await fetch(`${API_URL}/api/sync-logs/stats`)
      if (response.ok) {
        const data = await response.json()
        setSyncStats(data)
      }
    } catch (err) {
      console.error('Erreur sync stats:', err)
    }
  }

  const loadLateAlerts = async () => {
    try {
      const response = await fetch(`${API_URL}/api/alertes-rv/late-assignment?limit=20`)
      if (response.ok) {
        const data = await response.json()
        setLateAlerts(data.alerts || [])
      }
    } catch (err) {
      console.error('Erreur late alerts:', err)
    }
  }

  const formatTime = (isoString) => {
    if (!isoString) return '--:--'
    try {
      return new Date(isoString).toLocaleTimeString('fr-CA', { hour: '2-digit', minute: '2-digit' })
    } catch { return '--:--' }
  }

  const formatDate = (isoString) => {
    if (!isoString) return 'N/A'
    try {
      return new Date(isoString).toLocaleDateString('fr-CA', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' })
    } catch { return isoString }
  }

  const formatRelative = (isoString) => {
    if (!isoString) return 'N/A'
    const diff = Date.now() - new Date(isoString).getTime()
    const mins = Math.floor(diff / 60000)
    if (mins < 1) return "À l'instant"
    if (mins < 60) return `${mins} min`
    const hours = Math.floor(mins / 60)
    if (hours < 24) return `${hours}h`
    return formatDate(isoString)
  }

  // Déterminer le statut système
  const getSystemStatus = () => {
    if (!syncStats || !syncLogs.length) return { status: 'unknown', color: 'gray', text: 'Chargement...' }

    const lastLog = syncLogs[0]
    const lastSyncTime = new Date(lastLog?.created_at || 0)
    const hoursSinceSync = (Date.now() - lastSyncTime.getTime()) / 3600000

    if (lastLog?.status === 'error') {
      return { status: 'error', color: 'red', text: 'Erreur dernière sync' }
    }
    if (hoursSinceSync > 2) {
      return { status: 'warning', color: 'yellow', text: `Dernière sync: ${formatRelative(lastLog?.created_at)}` }
    }
    return { status: 'ok', color: 'green', text: 'Système opérationnel' }
  }

  const systemStatus = getSystemStatus()
  const pendingAlerts = lateAlerts.filter(a => a.status === 'pending')
  const sentAlerts = lateAlerts.filter(a => a.status === 'sent')

  const extractStats = (log) => {
    const stats = log.stats || log.tables_updated || {}
    if (typeof stats === 'string') {
      try { return JSON.parse(stats) } catch { return {} }
    }
    return stats
  }

  if (loading && syncLogs.length === 0) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-pulse text-gray-500">Chargement...</div>
      </div>
    )
  }

  return (
    <div className="max-w-6xl mx-auto px-4 py-6 space-y-6">

      {/* ═══════════════════════════════════════════════════════════════
          SECTION 1: STATUT SYSTÈME (en haut)
          ═══════════════════════════════════════════════════════════════ */}
      <div className={`rounded-xl p-6 shadow-lg border-2 ${
        systemStatus.color === 'green' ? 'bg-green-50 border-green-400' :
        systemStatus.color === 'red' ? 'bg-red-50 border-red-400' :
        systemStatus.color === 'yellow' ? 'bg-yellow-50 border-yellow-400' :
        'bg-gray-50 border-gray-300'
      }`}>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            {/* Indicateur LED */}
            <div className={`w-5 h-5 rounded-full animate-pulse ${
              systemStatus.color === 'green' ? 'bg-green-500' :
              systemStatus.color === 'red' ? 'bg-red-500' :
              systemStatus.color === 'yellow' ? 'bg-yellow-500' :
              'bg-gray-400'
            }`} />
            <div>
              <h1 className="text-xl font-bold text-gray-800">Tableau de Bord</h1>
              <p className={`text-sm ${
                systemStatus.color === 'green' ? 'text-green-700' :
                systemStatus.color === 'red' ? 'text-red-700' :
                'text-yellow-700'
              }`}>
                {systemStatus.text}
              </p>
            </div>
          </div>

          {/* Stats rapides */}
          <div className="flex gap-6 text-center">
            <div>
              <div className="text-2xl font-bold text-gray-800">{syncStats?.success_count || 0}</div>
              <div className="text-xs text-gray-500">Syncs (24h)</div>
            </div>
            <div>
              <div className="text-2xl font-bold text-orange-600">{pendingAlerts.length}</div>
              <div className="text-xs text-gray-500">En attente</div>
            </div>
            <div>
              <div className="text-2xl font-bold text-green-600">{sentAlerts.length}</div>
              <div className="text-xs text-gray-500">Envoyées</div>
            </div>
          </div>

          <button
            onClick={loadAllData}
            disabled={loading}
            className="px-4 py-2 bg-white border border-gray-300 rounded-lg text-sm font-medium hover:bg-gray-50 transition-colors disabled:opacity-50"
          >
            {loading ? '⏳' : '🔄'} Actualiser
          </button>
        </div>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg">
          ⚠️ {error}
        </div>
      )}

      {/* ═══════════════════════════════════════════════════════════════
          SECTION 2: TIMELINE DES IMPORTS (milieu)
          ═══════════════════════════════════════════════════════════════ */}
      <div className="bg-white rounded-xl shadow-lg overflow-hidden">
        <div className="px-6 py-4 bg-gray-50 border-b border-gray-200">
          <h2 className="text-lg font-semibold text-gray-800">
            📅 Timeline des Synchronisations
          </h2>
        </div>

        <div className="divide-y divide-gray-100 max-h-[350px] overflow-y-auto">
          {syncLogs.length === 0 ? (
            <div className="py-12 text-center text-gray-400">
              Aucune synchronisation enregistrée
            </div>
          ) : (
            syncLogs.map((log, idx) => {
              const stats = extractStats(log)
              const isSuccess = log.status === 'success'
              const isError = log.status === 'error'

              return (
                <div key={log.id || idx} className={`px-6 py-4 flex items-center gap-4 hover:bg-gray-50 ${isError ? 'bg-red-50' : ''}`}>
                  {/* Heure */}
                  <div className="w-16 text-center">
                    <div className="text-lg font-mono font-bold text-gray-700">
                      {formatTime(log.created_at)}
                    </div>
                  </div>

                  {/* Indicateur */}
                  <div className={`w-3 h-3 rounded-full flex-shrink-0 ${
                    isSuccess ? 'bg-green-500' : isError ? 'bg-red-500' : 'bg-yellow-500'
                  }`} />

                  {/* Contenu */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-gray-900 truncate">
                        {log.script_name || 'Sync Gazelle'}
                      </span>
                      {log.execution_time_seconds && (
                        <span className="text-xs text-gray-400">
                          ({log.execution_time_seconds}s)
                        </span>
                      )}
                    </div>
                    {log.message && (
                      <p className="text-sm text-gray-500 truncate">{log.message}</p>
                    )}
                    {(log.error_details || log.error_message) && (
                      <p className="text-sm text-red-600 truncate">
                        ❌ {log.error_details || log.error_message}
                      </p>
                    )}
                  </div>

                  {/* Stats badges */}
                  <div className="flex gap-1 flex-shrink-0">
                    {stats.appointments !== undefined && (
                      <span className="bg-blue-100 text-blue-800 text-xs px-2 py-1 rounded">
                        {stats.appointments} RV
                      </span>
                    )}
                    {stats.clients !== undefined && stats.clients > 0 && (
                      <span className="bg-gray-100 text-gray-600 text-xs px-2 py-1 rounded">
                        {stats.clients} clients
                      </span>
                    )}
                  </div>
                </div>
              )
            })
          )}
        </div>
      </div>

      {/* ═══════════════════════════════════════════════════════════════
          SECTION 3: EMAILS ENVOYÉS/PRÉVUS (bas)
          ═══════════════════════════════════════════════════════════════ */}
      <div className="bg-white rounded-xl shadow-lg overflow-hidden">
        <div className="px-6 py-4 bg-gray-50 border-b border-gray-200 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-gray-800">
            ✉️ Alertes Email (Dernière Minute)
          </h2>
          <div className="flex gap-3 text-sm">
            <span className="bg-yellow-100 text-yellow-800 px-3 py-1 rounded-full">
              {pendingAlerts.length} en attente
            </span>
            <span className="bg-green-100 text-green-800 px-3 py-1 rounded-full">
              {sentAlerts.length} envoyées
            </span>
          </div>
        </div>

        <div className="divide-y divide-gray-100 max-h-[300px] overflow-y-auto">
          {lateAlerts.length === 0 ? (
            <div className="py-12 text-center text-gray-400">
              Aucune alerte email
            </div>
          ) : (
            lateAlerts.map((alert, idx) => {
              const isPending = alert.status === 'pending'
              const isSent = alert.status === 'sent'
              const isFailed = alert.status === 'failed'

              return (
                <div key={alert.id || idx} className={`px-6 py-4 flex items-center gap-4 ${
                  isPending ? 'bg-yellow-50' : isFailed ? 'bg-red-50' : 'hover:bg-gray-50'
                }`}>
                  {/* Icône statut */}
                  <div className="w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0 text-xl">
                    {isPending ? '📤' : isSent ? '✅' : '❌'}
                  </div>

                  {/* Contenu */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-gray-900">
                        {alert.appointment_date} {alert.appointment_time?.slice(0, 5)}
                      </span>
                      <span className="text-gray-400">→</span>
                      <span className="text-gray-700 truncate">
                        {alert.technician_first_name || ''} {alert.technician_last_name || alert.technician_id}
                      </span>
                    </div>
                    <div className="text-sm text-gray-500 truncate">
                      {alert.client_name || 'Client N/A'}
                      {alert.technician_email && (
                        <span className="text-gray-400 ml-2">({alert.technician_email})</span>
                      )}
                    </div>
                  </div>

                  {/* Timing */}
                  <div className="text-right text-xs text-gray-500 flex-shrink-0">
                    {isPending && alert.scheduled_send_at && (
                      <div>Envoi: {formatDate(alert.scheduled_send_at)}</div>
                    )}
                    {isSent && alert.sent_at && (
                      <div className="text-green-600">Envoyé: {formatRelative(alert.sent_at)}</div>
                    )}
                    {isFailed && (
                      <div className="text-red-600">Échec</div>
                    )}
                  </div>
                </div>
              )
            })
          )}
        </div>
      </div>

      {/* Footer info */}
      <div className="text-center text-xs text-gray-400">
        Dernière actualisation: {lastRefresh.toLocaleTimeString('fr-CA')} •
        Sync horaire 7h-21h • Buffer 5 min avant envoi
      </div>
    </div>
  )
}
