import { useState, useEffect } from 'react'

import { API_URL } from '../utils/apiConfig'

export default function AlertesRV({ currentUser }) {
  const [unconfirmedAppointments, setUnconfirmedAppointments] = useState([])
  const [alerts, setAlerts] = useState([])
  const [loading, setLoading] = useState(true)
  const [stats, setStats] = useState(null)
  const [sendingAlert, setSendingAlert] = useState(null)

  useEffect(() => {
    loadData()
    // Recharger toutes les minutes
    const interval = setInterval(loadData, 60000)
    return () => clearInterval(interval)
  }, [])

  const loadData = async () => {
    try {
      setLoading(true)

      // Charger les RV non confirmés
      const unconfirmedRes = await fetch(`${API_URL}/alertes-rv/check`)
      const unconfirmedData = await unconfirmedRes.json()
      setUnconfirmedAppointments(unconfirmedData.unconfirmed || [])

      // Charger les alertes envoyées
      const alertsRes = await fetch(`${API_URL}/alertes-rv/alerts`)
      const alertsData = await alertsRes.json()
      setAlerts(alertsData.alerts || [])

      // Charger les stats
      const statsRes = await fetch(`${API_URL}/alertes-rv/stats`)
      const statsData = await statsRes.json()
      setStats(statsData)

    } catch (err) {
      console.error('Erreur chargement alertes RV:', err)
    } finally {
      setLoading(false)
    }
  }

  const handleSendAlert = async (appointment) => {
    if (!confirm(`Envoyer une alerte à ${appointment.client_name} (${appointment.client_email}) ?`)) {
      return
    }

    setSendingAlert(appointment.id)
    try {
      const response = await fetch(`${API_URL}/alertes-rv/send/${appointment.id}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          appointment_id: appointment.id,
          client_name: appointment.client_name,
          client_email: appointment.client_email,
          appointment_date: appointment.appointment_date,
          alert_sent_by: currentUser.email
        })
      })

      if (response.ok) {
        alert('✅ Alerte envoyée avec succès !')
        loadData()
      } else {
        alert('❌ Erreur lors de l\'envoi de l\'alerte')
      }
    } catch (err) {
      console.error('Erreur envoi alerte:', err)
      alert('❌ Erreur lors de l\'envoi de l\'alerte')
    } finally {
      setSendingAlert(null)
    }
  }

  const formatDate = (isoString) => {
    const date = new Date(isoString)
    return date.toLocaleString('fr-CA', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  if (loading && unconfirmedAppointments.length === 0) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-500">Chargement des alertes RV...</div>
      </div>
    )
  }

  return (
    <div className="max-w-7xl mx-auto px-4 py-6">
      {/* En-tête */}
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-gray-800 mb-2">
          Alertes de Rendez-vous Non Confirmés
        </h2>
        <p className="text-gray-600">
          Suivi et notification des clients qui n'ont pas confirmé leur RV
        </p>
      </div>

      {/* Stats rapides */}
      {stats && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
          <div className="bg-white rounded-lg shadow p-6">
            <div className="text-sm text-gray-600 mb-1">RV non confirmés</div>
            <div className="text-3xl font-bold text-red-600">{unconfirmedAppointments.length}</div>
          </div>
          <div className="bg-white rounded-lg shadow p-6">
            <div className="text-sm text-gray-600 mb-1">Alertes envoyées (7j)</div>
            <div className="text-3xl font-bold text-gray-800">{stats.alerts_last_7_days}</div>
          </div>
          <div className="bg-white rounded-lg shadow p-6">
            <div className="text-sm text-gray-600 mb-1">Total alertes</div>
            <div className="text-3xl font-bold text-gray-800">{stats.total_alerts_sent}</div>
          </div>
          <div className="bg-white rounded-lg shadow p-6">
            <div className="text-sm text-gray-600 mb-1">Taux de confirmation</div>
            <div className="text-3xl font-bold text-green-600">
              {stats.by_status?.confirmed && stats.total_alerts_sent > 0
                ? Math.round((stats.by_status.confirmed / stats.total_alerts_sent) * 100)
                : 0}%
            </div>
          </div>
        </div>
      )}

      {/* RV non confirmés nécessitant action */}
      <div className="bg-white rounded-lg shadow mb-6">
        <div className="px-6 py-4 border-b border-gray-200 flex justify-between items-center">
          <h3 className="text-lg font-semibold text-gray-800">
            ⚠️ Rendez-vous nécessitant une alerte ({unconfirmedAppointments.length})
          </h3>
          <button
            onClick={loadData}
            className="px-3 py-1 text-sm bg-blue-50 hover:bg-blue-100 text-blue-600 rounded transition-colors"
          >
            🔄 Actualiser
          </button>
        </div>

        <div className="divide-y divide-gray-200">
          {unconfirmedAppointments.length === 0 ? (
            <div className="px-6 py-12 text-center text-gray-500">
              ✅ Aucun RV non confirmé nécessitant une alerte
            </div>
          ) : (
            unconfirmedAppointments.map((apt) => (
              <div key={apt.id} className="px-6 py-4 hover:bg-gray-50 transition-colors">
                <div className="flex items-center justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-2">
                      <span className="font-medium text-gray-900">{apt.client_name}</span>
                      <span className="text-sm text-gray-500">•</span>
                      <span className="text-sm text-gray-600">{apt.client_email}</span>
                      <span className="px-2 py-1 bg-orange-100 text-orange-700 text-xs rounded-full">
                        Technicien: {apt.technician}
                      </span>
                    </div>
                    <div className="text-sm text-gray-600">
                      📅 RV prévu : {formatDate(apt.appointment_date)}
                      <span className="ml-3 text-red-600">
                        (Non confirmé depuis {Math.ceil((new Date() - new Date(apt.created_at)) / (1000 * 60 * 60 * 24))} jours)
                      </span>
                    </div>
                  </div>
                  <button
                    onClick={() => handleSendAlert(apt)}
                    disabled={sendingAlert === apt.id}
                    className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors disabled:bg-gray-300 disabled:cursor-not-allowed"
                  >
                    {sendingAlert === apt.id ? '⏳ Envoi...' : '📧 Envoyer alerte'}
                  </button>
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Historique des alertes envoyées */}
      <div className="bg-white rounded-lg shadow">
        <div className="px-6 py-4 border-b border-gray-200">
          <h3 className="text-lg font-semibold text-gray-800">
            📜 Historique des alertes envoyées ({alerts.length})
          </h3>
        </div>

        <div className="divide-y divide-gray-200 max-h-[500px] overflow-y-auto">
          {alerts.length === 0 ? (
            <div className="px-6 py-12 text-center text-gray-500">
              Aucune alerte envoyée pour le moment
            </div>
          ) : (
            alerts.map((alert) => (
              <div key={alert.id} className="px-6 py-4">
                <div className="flex items-start gap-3">
                  <div className="w-10 h-10 rounded-full bg-blue-500 flex items-center justify-center text-white font-bold flex-shrink-0">
                    📧
                  </div>
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="font-medium text-gray-900">{alert.client_name}</span>
                      <span className="text-sm text-gray-500">
                        a reçu une alerte
                      </span>
                      <span className={`px-2 py-1 text-xs rounded-full ${
                        alert.status === 'confirmed' ? 'bg-green-100 text-green-700' :
                        alert.status === 'cancelled' ? 'bg-red-100 text-red-700' :
                        'bg-gray-100 text-gray-700'
                      }`}>
                        {alert.status === 'confirmed' ? 'Confirmé' :
                         alert.status === 'cancelled' ? 'Annulé' : 'Envoyé'}
                      </span>
                    </div>
                    <div className="text-sm text-gray-600">
                      📧 {alert.client_email} •
                      📅 RV: {formatDate(alert.appointment_date)} •
                      👤 Envoyé par {alert.alert_sent_by.split('@')[0]} •
                      🕒 {formatDate(alert.alert_sent_at)}
                    </div>
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
