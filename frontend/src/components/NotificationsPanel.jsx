import { useState, useEffect } from 'react'

const API_URL = import.meta.env.VITE_API_URL || 'https://assistant-gazelle-v5-api.onrender.com'

export default function NotificationsPanel({ currentUser }) {
  const [activeTab, setActiveTab] = useState('deductions') // deductions, alerts, imports

  // Logs de déduction d'inventaire
  const [deductionLogs, setDeductionLogs] = useState([])
  const [deductionsLoading, setDeductionsLoading] = useState(true)

  // Alertes RV
  const [pendingAlerts, setPendingAlerts] = useState([])
  const [alertsHistory, setAlertsHistory] = useState([])
  const [alertsLoading, setAlertsLoading] = useState(true)

  // Statistiques d'import
  const [importSummary, setImportSummary] = useState([])
  const [importsLoading, setImportsLoading] = useState(true)

  const [error, setError] = useState(null)

  useEffect(() => {
    if (activeTab === 'deductions') {
      loadDeductionLogs()
    } else if (activeTab === 'alerts') {
      loadAlerts()
    } else if (activeTab === 'imports') {
      loadImportSummary()
    }
  }, [activeTab])

  const loadDeductionLogs = async () => {
    try {
      setDeductionsLoading(true)
      const response = await fetch(`${API_URL}/inventaire/deduction-logs?limit=100`)
      const data = await response.json()
      setDeductionLogs(data.logs || [])
      setError(null)
    } catch (err) {
      console.error('Erreur chargement logs déduction:', err)
      setError(err.message)
    } finally {
      setDeductionsLoading(false)
    }
  }

  const loadAlerts = async () => {
    try {
      setAlertsLoading(true)

      // Charger les alertes en attente ET l'historique
      const [pendingRes, historyRes] = await Promise.all([
        fetch(`${API_URL}/alertes-rv/pending`),
        fetch(`${API_URL}/alertes-rv/history?limit=50`)
      ])

      const pendingData = await pendingRes.json()
      const historyData = await historyRes.json()

      setPendingAlerts(pendingData.alerts || [])
      setAlertsHistory(historyData.history || [])
      setError(null)
    } catch (err) {
      console.error('Erreur chargement alertes:', err)
      setError(err.message)
    } finally {
      setAlertsLoading(false)
    }
  }

  const loadImportSummary = async () => {
    try {
      setImportsLoading(true)
      const response = await fetch(`${API_URL}/inventaire/deduction-summary?days=30`)
      const data = await response.json()
      setImportSummary(data.summary || [])
      setError(null)
    } catch (err) {
      console.error('Erreur chargement résumé imports:', err)
      setError(err.message)
    } finally {
      setImportsLoading(false)
    }
  }

  const formatDate = (isoString) => {
    if (!isoString) return 'Date inconnue'
    const date = new Date(isoString)
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
      'success': { color: 'bg-green-100 text-green-800', icon: '✓', text: 'Succès' },
      'error': { color: 'bg-red-100 text-red-800', icon: '✗', text: 'Erreur' },
      'skipped': { color: 'bg-yellow-100 text-yellow-800', icon: '⊘', text: 'Ignoré' },
      'pending': { color: 'bg-orange-100 text-orange-800', icon: '⏳', text: 'En attente' },
      'resolved': { color: 'bg-gray-100 text-gray-600', icon: '✓', text: 'Résolu' }
    }
    const badge = badges[status] || { color: 'bg-gray-100 text-gray-600', icon: '?', text: status }
    return (
      <span className={`px-2 py-1 rounded-full text-xs font-medium ${badge.color}`}>
        {badge.icon} {badge.text}
      </span>
    )
  }

  const resolveAlert = async (alertId) => {
    try {
      const response = await fetch(`${API_URL}/alertes-rv/resolve/${alertId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          resolved_by: currentUser?.email || 'admin'
        })
      })

      if (!response.ok) throw new Error('Erreur lors de la résolution')

      // Recharger les alertes
      await loadAlerts()
    } catch (err) {
      alert('Erreur: ' + err.message)
    }
  }

  return (
    <div className="max-w-7xl mx-auto px-4 py-6">
      {/* En-tête */}
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-gray-800 mb-2">
          📊 Notifications & Logs
        </h2>
        <p className="text-gray-600">
          Suivi des déductions d'inventaire, alertes RV et importations
        </p>
      </div>

      {/* Onglets */}
      <div className="border-b border-gray-200 mb-6">
        <nav className="-mb-px flex space-x-8">
          <button
            onClick={() => setActiveTab('deductions')}
            className={`pb-4 px-1 border-b-2 font-medium text-sm transition-colors ${
              activeTab === 'deductions'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            📦 Déductions d'inventaire
          </button>
          <button
            onClick={() => setActiveTab('alerts')}
            className={`pb-4 px-1 border-b-2 font-medium text-sm transition-colors ${
              activeTab === 'alerts'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            🔔 Alertes RV
            {pendingAlerts.length > 0 && (
              <span className="ml-2 bg-red-500 text-white text-xs rounded-full px-2 py-0.5">
                {pendingAlerts.length}
              </span>
            )}
          </button>
          <button
            onClick={() => setActiveTab('imports')}
            className={`pb-4 px-1 border-b-2 font-medium text-sm transition-colors ${
              activeTab === 'imports'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            📥 Résumé d'imports
          </button>
        </nav>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg mb-4">
          Erreur: {error}
        </div>
      )}

      {/* Contenu - Déductions d'inventaire */}
      {activeTab === 'deductions' && (
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <div className="px-6 py-4 border-b border-gray-200 flex justify-between items-center">
            <h3 className="text-lg font-semibold text-gray-800">
              Logs de déduction ({deductionLogs.length})
            </h3>
            <button
              onClick={loadDeductionLogs}
              className="px-3 py-1 text-sm bg-blue-50 hover:bg-blue-100 text-blue-600 rounded transition-colors"
            >
              🔄 Actualiser
            </button>
          </div>

          <div className="divide-y divide-gray-200 max-h-[600px] overflow-y-auto">
            {deductionsLoading ? (
              <div className="px-6 py-12 text-center text-gray-500">
                Chargement...
              </div>
            ) : deductionLogs.length === 0 ? (
              <div className="px-6 py-12 text-center text-gray-500">
                Aucune déduction enregistrée pour le moment
              </div>
            ) : (
              deductionLogs.map((log, index) => (
                <div
                  key={log.id || index}
                  className="px-6 py-4 hover:bg-gray-50 transition-colors"
                >
                  <div className="flex items-start gap-4">
                    <div className="flex-1">
                      <div className="flex items-center gap-3 mb-2">
                        {getStatusBadge(log.status)}
                        <span className="text-sm text-gray-600">
                          {formatDate(log.created_at)}
                        </span>
                      </div>

                      <div className="grid grid-cols-2 gap-4 text-sm">
                        <div>
                          <span className="text-gray-600">Technicien:</span>
                          <span className="ml-2 font-medium text-gray-900">{log.technicien}</span>
                        </div>
                        <div>
                          <span className="text-gray-600">Facture:</span>
                          <span className="ml-2 font-mono text-xs bg-gray-100 px-2 py-0.5 rounded">
                            {log.invoice_id}
                          </span>
                        </div>
                        <div>
                          <span className="text-gray-600">Service:</span>
                          <span className="ml-2 text-gray-900">{log.service_name}</span>
                        </div>
                        <div>
                          <span className="text-gray-600">Matériel:</span>
                          <span className="ml-2 font-medium text-gray-900">
                            {log.material_code} - {log.material_name}
                          </span>
                        </div>
                        <div>
                          <span className="text-gray-600">Quantité:</span>
                          <span className="ml-2 font-bold text-red-600">
                            -{log.quantity_deducted}
                          </span>
                        </div>
                      </div>

                      {log.error_message && (
                        <div className="mt-2 text-xs text-red-600 bg-red-50 px-3 py-2 rounded">
                          ⚠️ {log.error_message}
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      )}

      {/* Contenu - Alertes RV */}
      {activeTab === 'alerts' && (
        <div className="space-y-6">
          {/* Alertes en attente */}
          {pendingAlerts.length > 0 && (
            <div className="bg-white rounded-lg shadow overflow-hidden">
              <div className="px-6 py-4 border-b border-gray-200 bg-orange-50">
                <h3 className="text-lg font-semibold text-orange-800">
                  ⚠️ Alertes en attente ({pendingAlerts.length})
                </h3>
              </div>

              <div className="divide-y divide-gray-200">
                {pendingAlerts.map((alert, index) => (
                  <div
                    key={alert.id || index}
                    className="px-6 py-4 hover:bg-gray-50 transition-colors"
                  >
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex-1">
                        <div className="flex items-center gap-3 mb-2">
                          {getStatusBadge('pending')}
                          <span className="font-medium text-gray-900">
                            {alert.technician_name}
                          </span>
                          <span className="text-sm text-gray-600">
                            ({alert.technician_email})
                          </span>
                        </div>

                        <div className="text-sm text-gray-700">
                          <span className="font-medium">{alert.appointment_count}</span> RV non confirmé(s)
                        </div>

                        <div className="text-xs text-gray-500 mt-1">
                          Envoyé: {formatDate(alert.sent_at)}
                        </div>
                      </div>

                      <button
                        onClick={() => resolveAlert(alert.id)}
                        className="px-3 py-1 text-sm bg-green-50 hover:bg-green-100 text-green-700 rounded transition-colors"
                      >
                        ✓ Marquer résolu
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Historique des alertes */}
          <div className="bg-white rounded-lg shadow overflow-hidden">
            <div className="px-6 py-4 border-b border-gray-200 flex justify-between items-center">
              <h3 className="text-lg font-semibold text-gray-800">
                Historique des alertes ({alertsHistory.length})
              </h3>
              <button
                onClick={loadAlerts}
                className="px-3 py-1 text-sm bg-blue-50 hover:bg-blue-100 text-blue-600 rounded transition-colors"
              >
                🔄 Actualiser
              </button>
            </div>

            <div className="divide-y divide-gray-200 max-h-[600px] overflow-y-auto">
              {alertsLoading ? (
                <div className="px-6 py-12 text-center text-gray-500">
                  Chargement...
                </div>
              ) : alertsHistory.length === 0 ? (
                <div className="px-6 py-12 text-center text-gray-500">
                  Aucun historique d'alerte pour le moment
                </div>
              ) : (
                alertsHistory.map((alert, index) => (
                  <div
                    key={alert.id || index}
                    className="px-6 py-4 hover:bg-gray-50 transition-colors"
                  >
                    <div className="flex items-start gap-4">
                      <div className="flex-1">
                        <div className="flex items-center gap-3 mb-2">
                          {getStatusBadge(alert.status || 'resolved')}
                          <span className="font-medium text-gray-900">
                            {alert.technician_name}
                          </span>
                          <span className="text-sm text-gray-600">
                            ({alert.technician_email})
                          </span>
                        </div>

                        <div className="text-sm text-gray-700">
                          <span className="font-medium">{alert.appointment_count}</span> RV non confirmé(s)
                        </div>

                        <div className="text-xs text-gray-500 mt-1">
                          Envoyé: {formatDate(alert.sent_at)}
                          {alert.resolved_at && (
                            <> • Résolu: {formatDate(alert.resolved_at)}</>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      )}

      {/* Contenu - Résumé d'imports */}
      {activeTab === 'imports' && (
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <div className="px-6 py-4 border-b border-gray-200 flex justify-between items-center">
            <h3 className="text-lg font-semibold text-gray-800">
              Résumé des imports (30 derniers jours)
            </h3>
            <button
              onClick={loadImportSummary}
              className="px-3 py-1 text-sm bg-blue-50 hover:bg-blue-100 text-blue-600 rounded transition-colors"
            >
              🔄 Actualiser
            </button>
          </div>

          <div className="divide-y divide-gray-200 max-h-[600px] overflow-y-auto">
            {importsLoading ? (
              <div className="px-6 py-12 text-center text-gray-500">
                Chargement...
              </div>
            ) : importSummary.length === 0 ? (
              <div className="px-6 py-12 text-center text-gray-500">
                Aucun import enregistré pour le moment
              </div>
            ) : (
              importSummary.map((summary, index) => (
                <div
                  key={summary.id || index}
                  className="px-6 py-4 hover:bg-gray-50 transition-colors"
                >
                  <div className="flex items-start gap-4">
                    <div className="flex-1">
                      <div className="flex items-center gap-3 mb-3">
                        <span className="font-medium text-gray-900">
                          📅 {summary.sync_date}
                        </span>
                        {summary.errors_count > 0 && (
                          <span className="bg-red-100 text-red-800 text-xs px-2 py-1 rounded">
                            {summary.errors_count} erreur(s)
                          </span>
                        )}
                      </div>

                      <div className="grid grid-cols-3 gap-4 text-sm">
                        <div className="bg-blue-50 rounded p-3">
                          <div className="text-xs text-blue-600 mb-1">Factures traitées</div>
                          <div className="text-2xl font-bold text-blue-900">
                            {summary.invoices_processed || 0}
                          </div>
                        </div>
                        <div className="bg-green-50 rounded p-3">
                          <div className="text-xs text-green-600 mb-1">Déductions</div>
                          <div className="text-2xl font-bold text-green-900">
                            {summary.total_deductions || 0}
                          </div>
                        </div>
                        <div className="bg-purple-50 rounded p-3">
                          <div className="text-xs text-purple-600 mb-1">Techniciens</div>
                          <div className="text-2xl font-bold text-purple-900">
                            {summary.techniciens_affected?.length || 0}
                          </div>
                        </div>
                      </div>

                      {summary.techniciens_affected && summary.techniciens_affected.length > 0 && (
                        <div className="mt-3 text-xs text-gray-600">
                          Techniciens affectés: {summary.techniciens_affected.join(', ')}
                        </div>
                      )}
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
