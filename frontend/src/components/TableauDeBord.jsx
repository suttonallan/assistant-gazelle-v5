import { useState, useEffect } from 'react'
import { Bell, AlertTriangle, Calendar, Database, CheckCircle, XCircle, Clock } from 'lucide-react'

/**
 * Tableau de Bord Unifié
 *
 * Regroupe toutes les alertes et informations système en une seule page épurée:
 * - Alertes (RV non confirmés + Maintenance pianos)
 * - Historique Pianos (modifications techniques récentes)
 * - État du Système (derniers imports)
 */
export default function TableauDeBord({ currentUser }) {
  const [unconfirmedAppointments, setUnconfirmedAppointments] = useState([])
  const [maintenanceAlerts, setMaintenanceAlerts] = useState([])
  const [pianoHistory, setPianoHistory] = useState([])
  const [systemStatus, setSystemStatus] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const API_URL = import.meta.env.VITE_API_URL || ''

  // Charger toutes les données au montage
  useEffect(() => {
    loadAllData()
    // Rafraîchir toutes les 5 minutes
    const interval = setInterval(loadAllData, 5 * 60 * 1000)
    return () => clearInterval(interval)
  }, [])

  const loadAllData = async () => {
    setLoading(true)
    setError(null)

    try {
      await Promise.all([
        loadUnconfirmedAppointments(),
        loadMaintenanceAlerts(),
        loadPianoHistory(),
        loadSystemStatus()
      ])
    } catch (err) {
      console.error('[TableauDeBord] Erreur chargement données:', err)
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const loadUnconfirmedAppointments = async () => {
    try {
      const response = await fetch(`${API_URL}/api/alertes/rv-non-confirmes`, {
        headers: { 'Cache-Control': 'no-cache' }
      })
      if (response.ok) {
        const data = await response.json()
        setUnconfirmedAppointments(data.appointments || [])
      }
    } catch (err) {
      console.error('[TableauDeBord] Erreur chargement RV:', err)
    }
  }

  const loadMaintenanceAlerts = async () => {
    try {
      const response = await fetch(`${API_URL}/api/alertes/maintenance`, {
        headers: { 'Cache-Control': 'no-cache' }
      })
      if (response.ok) {
        const data = await response.json()
        setMaintenanceAlerts(data.alerts || [])
      }
    } catch (err) {
      console.error('[TableauDeBord] Erreur chargement maintenance:', err)
    }
  }

  const loadPianoHistory = async () => {
    try {
      // Récupérer uniquement les modifications techniques (derniers 7 jours)
      const response = await fetch(`${API_URL}/api/pianos/history?days=7&type=technical`, {
        headers: { 'Cache-Control': 'no-cache' }
      })
      if (response.ok) {
        const data = await response.json()
        setPianoHistory(data.history || [])
      }
    } catch (err) {
      console.error('[TableauDeBord] Erreur chargement historique:', err)
    }
  }

  const loadSystemStatus = async () => {
    try {
      const response = await fetch(`${API_URL}/api/system/status`, {
        headers: { 'Cache-Control': 'no-cache' }
      })
      if (response.ok) {
        const data = await response.json()
        setSystemStatus(data)
      }
    } catch (err) {
      console.error('[TableauDeBord] Erreur chargement statut système:', err)
    }
  }

  const formatDate = (dateString) => {
    if (!dateString) return 'N/A'
    const date = new Date(dateString)
    const now = new Date()
    const diffMs = now - date
    const diffMins = Math.floor(diffMs / 60000)
    const diffHours = Math.floor(diffMs / 3600000)
    const diffDays = Math.floor(diffMs / 86400000)

    if (diffMins < 60) return `Il y a ${diffMins} min`
    if (diffHours < 24) return `Il y a ${diffHours}h`
    if (diffDays === 1) return 'Hier'
    if (diffDays < 7) return `Il y a ${diffDays} jours`

    return date.toLocaleDateString('fr-CA', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    })
  }

  if (loading) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-8">
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-8">
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <div className="flex items-start gap-3">
            <XCircle className="h-5 w-5 text-red-600 mt-0.5 flex-shrink-0" />
            <div>
              <h3 className="text-red-800 font-medium">Erreur de chargement</h3>
              <p className="text-red-700 text-sm mt-1">{error}</p>
              <button
                onClick={loadAllData}
                className="mt-3 px-4 py-2 bg-red-100 hover:bg-red-200 text-red-800 rounded-lg text-sm font-medium transition-colors"
              >
                Réessayer
              </button>
            </div>
          </div>
        </div>
      </div>
    )
  }

  const totalAlerts = unconfirmedAppointments.length + maintenanceAlerts.length

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      {/* En-tête */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">Tableau de bord</h1>
        <p className="text-gray-600">
          Vue d'ensemble de vos alertes et de l'état du système
        </p>
      </div>

      {/* Section Alertes */}
      <div className="mb-8">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-semibold text-gray-900 flex items-center gap-2">
            <Bell className="h-5 w-5 text-orange-600" />
            Alertes
            {totalAlerts > 0 && (
              <span className="ml-2 px-2.5 py-0.5 bg-orange-100 text-orange-800 text-sm font-medium rounded-full">
                {totalAlerts}
              </span>
            )}
          </h2>
          <button
            onClick={loadAllData}
            className="px-3 py-1.5 text-sm text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition-colors"
          >
            🔄 Actualiser
          </button>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Rendez-vous non confirmés */}
          <div className="bg-white border border-gray-200 rounded-lg shadow-sm overflow-hidden">
            <div className="bg-gradient-to-r from-orange-50 to-orange-100 px-4 py-3 border-b border-orange-200">
              <h3 className="font-medium text-gray-900 flex items-center gap-2">
                <Calendar className="h-4 w-4 text-orange-600" />
                Rendez-vous non confirmés
                {unconfirmedAppointments.length > 0 && (
                  <span className="ml-auto px-2 py-0.5 bg-orange-600 text-white text-xs font-medium rounded-full">
                    {unconfirmedAppointments.length}
                  </span>
                )}
              </h3>
            </div>
            <div className="p-4">
              {unconfirmedAppointments.length === 0 ? (
                <div className="text-center py-8 text-gray-500">
                  <CheckCircle className="h-8 w-8 mx-auto mb-2 text-green-500" />
                  <p className="text-sm">Aucun rendez-vous en attente</p>
                </div>
              ) : (
                <div className="space-y-3 max-h-96 overflow-y-auto">
                  {unconfirmedAppointments.slice(0, 10).map((appointment, index) => (
                    <div
                      key={index}
                      className="p-3 bg-orange-50 border border-orange-200 rounded-lg hover:bg-orange-100 transition-colors"
                    >
                      <div className="flex justify-between items-start mb-1">
                        <span className="font-medium text-gray-900">{appointment.client_name}</span>
                        <span className="text-xs text-gray-600">{formatDate(appointment.appointment_date)}</span>
                      </div>
                      {appointment.appointment_time && (
                        <div className="text-sm text-gray-700">
                          🕐 {appointment.appointment_time}
                        </div>
                      )}
                      {appointment.technician_name && (
                        <div className="text-sm text-gray-600 mt-1">
                          👤 {appointment.technician_name}
                        </div>
                      )}
                    </div>
                  ))}
                  {unconfirmedAppointments.length > 10 && (
                    <p className="text-xs text-gray-500 text-center pt-2">
                      ... et {unconfirmedAppointments.length - 10} autres
                    </p>
                  )}
                </div>
              )}
            </div>
          </div>

          {/* Alertes maintenance */}
          <div className="bg-white border border-gray-200 rounded-lg shadow-sm overflow-hidden">
            <div className="bg-gradient-to-r from-red-50 to-red-100 px-4 py-3 border-b border-red-200">
              <h3 className="font-medium text-gray-900 flex items-center gap-2">
                <AlertTriangle className="h-4 w-4 text-red-600" />
                Maintenance pianos
                {maintenanceAlerts.length > 0 && (
                  <span className="ml-auto px-2 py-0.5 bg-red-600 text-white text-xs font-medium rounded-full">
                    {maintenanceAlerts.length}
                  </span>
                )}
              </h3>
            </div>
            <div className="p-4">
              {maintenanceAlerts.length === 0 ? (
                <div className="text-center py-8 text-gray-500">
                  <CheckCircle className="h-8 w-8 mx-auto mb-2 text-green-500" />
                  <p className="text-sm">Tous les pianos sont à jour</p>
                </div>
              ) : (
                <div className="space-y-3 max-h-96 overflow-y-auto">
                  {maintenanceAlerts.slice(0, 10).map((alert, index) => (
                    <div
                      key={index}
                      className="p-3 bg-red-50 border border-red-200 rounded-lg hover:bg-red-100 transition-colors"
                    >
                      <div className="flex justify-between items-start mb-1">
                        <span className="font-medium text-gray-900">{alert.piano_info}</span>
                        <span className="text-xs text-gray-600">{alert.days_overdue} jours</span>
                      </div>
                      <div className="text-sm text-gray-700">
                        📍 {alert.client_name}
                      </div>
                      {alert.last_service_date && (
                        <div className="text-sm text-gray-600 mt-1">
                          Dernier service: {formatDate(alert.last_service_date)}
                        </div>
                      )}
                    </div>
                  ))}
                  {maintenanceAlerts.length > 10 && (
                    <p className="text-xs text-gray-500 text-center pt-2">
                      ... et {maintenanceAlerts.length - 10} autres
                    </p>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Section Historique Pianos */}
      <div className="mb-8">
        <h2 className="text-xl font-semibold text-gray-900 mb-4 flex items-center gap-2">
          <Clock className="h-5 w-5 text-blue-600" />
          Historique pianos (modifications techniques)
        </h2>
        <div className="bg-white border border-gray-200 rounded-lg shadow-sm overflow-hidden">
          {pianoHistory.length === 0 ? (
            <div className="text-center py-12 text-gray-500">
              <p className="text-sm">Aucune modification récente</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Date
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Piano
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Client
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Modification
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {pianoHistory.slice(0, 15).map((entry, index) => (
                    <tr key={index} className="hover:bg-gray-50">
                      <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-600">
                        {formatDate(entry.modified_at)}
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-900">
                        {entry.piano_info || 'N/A'}
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-700">
                        {entry.client_name || 'N/A'}
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-600">
                        {entry.change_description || 'Modification technique'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {pianoHistory.length > 15 && (
                <div className="px-4 py-3 bg-gray-50 border-t border-gray-200">
                  <p className="text-xs text-gray-500 text-center">
                    ... et {pianoHistory.length - 15} autres modifications
                  </p>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Section État du Système */}
      <div>
        <h2 className="text-xl font-semibold text-gray-900 mb-4 flex items-center gap-2">
          <Database className="h-5 w-5 text-green-600" />
          État du système
        </h2>
        <div className="bg-white border border-gray-200 rounded-lg shadow-sm p-4">
          {!systemStatus ? (
            <p className="text-sm text-gray-500">Chargement...</p>
          ) : (
            <div className="text-sm text-gray-700">
              <div className="flex items-center justify-between py-2 border-b border-gray-100">
                <span>Dernière synchronisation Gazelle</span>
                <span className="font-medium text-gray-900">
                  {formatDate(systemStatus.last_sync_date)}
                  {systemStatus.last_sync_status === 'success' ? (
                    <CheckCircle className="inline-block h-4 w-4 text-green-500 ml-2" />
                  ) : (
                    <XCircle className="inline-block h-4 w-4 text-red-500 ml-2" />
                  )}
                </span>
              </div>
              {systemStatus.last_sync_items && (
                <div className="flex items-center justify-between py-2">
                  <span>Items synchronisés</span>
                  <span className="font-medium text-gray-900">
                    {systemStatus.last_sync_items.toLocaleString()} items
                  </span>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
