import React, { useState, useEffect } from 'react'

console.log('[HumidityAlertsDashboard.jsx] Module chargé')

function HumidityAlertsDashboard() {
  const [stats, setStats] = useState(null)
  const [unresolvedAlerts, setUnresolvedAlerts] = useState([])
  const [resolvedAlerts, setResolvedAlerts] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [activeTab, setActiveTab] = useState('unresolved') // unresolved | resolved | archived

  const API_URL = import.meta.env.VITE_API_URL || ''

  // Charger les données au démarrage
  useEffect(() => {
    loadAllData()
    // Refresh toutes les 30 secondes
    const interval = setInterval(loadAllData, 30000)
    return () => clearInterval(interval)
  }, [])

  const loadAllData = async () => {
    console.log('[HumidityAlertsDashboard] Chargement des données...')
    setLoading(true)
    setError(null)

    try {
      // Charger les stats
      const statsRes = await fetch(`${API_URL}/api/humidity-alerts/stats`)
      if (!statsRes.ok) throw new Error(`Stats: ${statsRes.status}`)
      const statsData = await statsRes.json()
      setStats(statsData)
      console.log('[HumidityAlertsDashboard] Stats:', statsData)

      // Charger les alertes non résolues
      const unresolvedRes = await fetch(`${API_URL}/api/humidity-alerts/unresolved`)
      if (!unresolvedRes.ok) throw new Error(`Unresolved: ${unresolvedRes.status}`)
      const unresolvedData = await unresolvedRes.json()
      setUnresolvedAlerts(unresolvedData.alerts || [])
      console.log('[HumidityAlertsDashboard] Non résolues:', unresolvedData.count)

      // Charger les alertes résolues
      const resolvedRes = await fetch(`${API_URL}/api/humidity-alerts/resolved`)
      if (!resolvedRes.ok) throw new Error(`Resolved: ${resolvedRes.status}`)
      const resolvedData = await resolvedRes.json()
      setResolvedAlerts(resolvedData.alerts || [])
      console.log('[HumidityAlertsDashboard] Résolues:', resolvedData.count)

      setLoading(false)
    } catch (err) {
      console.error('[HumidityAlertsDashboard] Erreur:', err)
      setError(err.message)
      setLoading(false)
    }
  }

  const handleResolve = async (alertId) => {
    if (!confirm('Marquer cette alerte comme résolue?')) return

    try {
      const res = await fetch(`${API_URL}/api/humidity-alerts/resolve/${alertId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ notes: 'Résolu depuis le dashboard' })
      })

      if (!res.ok) throw new Error(`Erreur ${res.status}`)

      console.log('[HumidityAlertsDashboard] Alerte résolue:', alertId)
      loadAllData() // Recharger les données
    } catch (err) {
      console.error('[HumidityAlertsDashboard] Erreur résolution:', err)
      alert(`Erreur: ${err.message}`)
    }
  }

  const handleArchive = async (alertId) => {
    if (!confirm('Archiver cette alerte?')) return

    try {
      const res = await fetch(`${API_URL}/api/humidity-alerts/archive/${alertId}`, {
        method: 'POST'
      })

      if (!res.ok) throw new Error(`Erreur ${res.status}`)

      console.log('[HumidityAlertsDashboard] Alerte archivée:', alertId)
      loadAllData() // Recharger les données
    } catch (err) {
      console.error('[HumidityAlertsDashboard] Erreur archivage:', err)
      alert(`Erreur: ${err.message}`)
    }
  }

  if (loading && !stats) {
    return (
      <div style={{ padding: '2rem', textAlign: 'center' }}>
        <div style={{ fontSize: '1.2rem', color: '#666' }}>
          ⏳ Chargement des alertes...
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div style={{ padding: '2rem' }}>
        <div style={{
          backgroundColor: '#ffebee',
          color: '#c62828',
          padding: '1rem',
          borderRadius: '8px',
          border: '1px solid #ef9a9a'
        }}>
          <strong>❌ Erreur:</strong> {error}
          <br />
          <button
            onClick={loadAllData}
            style={{
              marginTop: '1rem',
              padding: '0.5rem 1rem',
              backgroundColor: '#1976d2',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer'
            }}
          >
            Réessayer
          </button>
        </div>
      </div>
    )
  }

  const currentAlerts = activeTab === 'unresolved' ? unresolvedAlerts : resolvedAlerts

  return (
    <div>
      {/* Stats Cards */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
        gap: '1rem',
        marginBottom: '2rem'
      }}>
        <div style={{
          backgroundColor: 'white',
          padding: '1.5rem',
          borderRadius: '8px',
          boxShadow: '0 2px 4px rgba(0,0,0,0.1)'
        }}>
          <div style={{ fontSize: '0.9rem', color: '#666', marginBottom: '0.5rem' }}>
            Total
          </div>
          <div style={{ fontSize: '2rem', fontWeight: 'bold', color: '#1976d2' }}>
            {stats?.total_alerts || 0}
          </div>
        </div>

        <div style={{
          backgroundColor: 'white',
          padding: '1.5rem',
          borderRadius: '8px',
          boxShadow: '0 2px 4px rgba(0,0,0,0.1)'
        }}>
          <div style={{ fontSize: '0.9rem', color: '#666', marginBottom: '0.5rem' }}>
            Non résolues
          </div>
          <div style={{ fontSize: '2rem', fontWeight: 'bold', color: '#d32f2f' }}>
            {stats?.unresolved || 0}
          </div>
        </div>

        <div style={{
          backgroundColor: 'white',
          padding: '1.5rem',
          borderRadius: '8px',
          boxShadow: '0 2px 4px rgba(0,0,0,0.1)'
        }}>
          <div style={{ fontSize: '0.9rem', color: '#666', marginBottom: '0.5rem' }}>
            Résolues
          </div>
          <div style={{ fontSize: '2rem', fontWeight: 'bold', color: '#388e3c' }}>
            {stats?.resolved || 0}
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div style={{
        backgroundColor: 'white',
        borderRadius: '8px',
        boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
        overflow: 'hidden'
      }}>
        <div style={{
          display: 'flex',
          borderBottom: '1px solid #e0e0e0'
        }}>
          <button
            onClick={() => setActiveTab('unresolved')}
            style={{
              flex: 1,
              padding: '1rem',
              backgroundColor: activeTab === 'unresolved' ? '#1976d2' : 'transparent',
              color: activeTab === 'unresolved' ? 'white' : '#666',
              border: 'none',
              cursor: 'pointer',
              fontWeight: activeTab === 'unresolved' ? 'bold' : 'normal',
              transition: 'all 0.2s'
            }}
          >
            🔴 Non résolues ({unresolvedAlerts.length})
          </button>
          <button
            onClick={() => setActiveTab('resolved')}
            style={{
              flex: 1,
              padding: '1rem',
              backgroundColor: activeTab === 'resolved' ? '#1976d2' : 'transparent',
              color: activeTab === 'resolved' ? 'white' : '#666',
              border: 'none',
              cursor: 'pointer',
              fontWeight: activeTab === 'resolved' ? 'bold' : 'normal',
              transition: 'all 0.2s'
            }}
          >
            ✅ Résolues ({resolvedAlerts.length})
          </button>
        </div>

        {/* Liste des alertes */}
        <div style={{ padding: '1rem' }}>
          {currentAlerts.length === 0 ? (
            <div style={{
              textAlign: 'center',
              padding: '3rem',
              color: '#999'
            }}>
              {activeTab === 'unresolved'
                ? '🎉 Aucune alerte non résolue'
                : '📋 Aucune alerte résolue'
              }
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              {currentAlerts.map((alert) => (
                <div
                  key={alert.id}
                  style={{
                    backgroundColor: '#f5f5f5',
                    padding: '1rem',
                    borderRadius: '8px',
                    border: '1px solid #e0e0e0'
                  }}
                >
                  <div style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'start',
                    marginBottom: '0.5rem'
                  }}>
                    <div>
                      <div style={{
                        fontSize: '1.1rem',
                        fontWeight: 'bold',
                        marginBottom: '0.25rem'
                      }}>
                        {alert.client_name || 'Client inconnu'}
                      </div>
                      <div style={{ fontSize: '0.9rem', color: '#666' }}>
                        {alert.piano_make && alert.piano_model
                          ? `${alert.piano_make} ${alert.piano_model}`
                          : 'Piano non spécifié'
                        }
                      </div>
                    </div>
                    <div style={{
                      display: 'inline-block',
                      padding: '0.25rem 0.75rem',
                      backgroundColor: getAlertTypeColor(alert.alert_type),
                      color: 'white',
                      borderRadius: '12px',
                      fontSize: '0.85rem',
                      fontWeight: 'bold'
                    }}>
                      {getAlertTypeLabel(alert.alert_type)}
                    </div>
                  </div>

                  <div style={{
                    padding: '0.75rem',
                    backgroundColor: 'white',
                    borderRadius: '4px',
                    marginBottom: '0.5rem',
                    fontSize: '0.95rem'
                  }}>
                    {alert.description}
                  </div>

                  <div style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    fontSize: '0.85rem',
                    color: '#666'
                  }}>
                    <div>
                      📅 {new Date(alert.observed_at).toLocaleString('fr-FR')}
                    </div>
                    <div style={{ display: 'flex', gap: '0.5rem' }}>
                      {!alert.is_resolved && (
                        <button
                          onClick={() => handleResolve(alert.id)}
                          style={{
                            padding: '0.5rem 1rem',
                            backgroundColor: '#388e3c',
                            color: 'white',
                            border: 'none',
                            borderRadius: '4px',
                            cursor: 'pointer',
                            fontSize: '0.85rem'
                          }}
                        >
                          ✅ Résoudre
                        </button>
                      )}
                      <button
                        onClick={() => handleArchive(alert.id)}
                        style={{
                          padding: '0.5rem 1rem',
                          backgroundColor: '#757575',
                          color: 'white',
                          border: 'none',
                          borderRadius: '4px',
                          cursor: 'pointer',
                          fontSize: '0.85rem'
                        }}
                      >
                        📦 Archiver
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

function getAlertTypeColor(type) {
  const colors = {
    alimentation: '#d32f2f',
    housse: '#f57c00',
    reservoir: '#1976d2',
    environnement: '#388e3c'
  }
  return colors[type] || '#757575'
}

function getAlertTypeLabel(type) {
  const labels = {
    alimentation: '⚡ Alimentation',
    housse: '🛡️ Housse',
    reservoir: '💧 Réservoir',
    environnement: '🌡️ Environnement'
  }
  return labels[type] || type
}

export default HumidityAlertsDashboard
