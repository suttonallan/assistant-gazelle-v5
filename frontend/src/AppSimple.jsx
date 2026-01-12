import React, { useState, useEffect } from 'react'
import LoginScreen from './components/LoginScreen'
import HumidityAlertsDashboard from './components/HumidityAlertsDashboard'

console.log('[AppSimple.jsx] Module chargé')

function AppSimple() {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  // Charger l'utilisateur depuis localStorage
  useEffect(() => {
    console.log('[AppSimple.jsx] Chargement utilisateur...')
    try {
      const savedUser = localStorage.getItem('currentUser')
      if (savedUser) {
        const parsedUser = JSON.parse(savedUser)
        console.log('[AppSimple.jsx] Utilisateur trouvé:', parsedUser.email)
        setUser(parsedUser)
      }
    } catch (error) {
      console.error('[AppSimple.jsx] Erreur parsing utilisateur:', error)
    }
    setLoading(false)
  }, [])

  const handleLogin = (userData) => {
    console.log('[AppSimple.jsx] Login:', userData.email)
    setUser(userData)
    localStorage.setItem('currentUser', JSON.stringify(userData))
  }

  const handleLogout = () => {
    console.log('[AppSimple.jsx] Logout')
    setUser(null)
    localStorage.removeItem('currentUser')
  }

  if (loading) {
    return (
      <div style={{
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        height: '100vh',
        fontFamily: 'sans-serif'
      }}>
        <div>Chargement...</div>
      </div>
    )
  }

  if (!user) {
    return <LoginScreen onLogin={handleLogin} />
  }

  return (
    <div style={{
      minHeight: '100vh',
      backgroundColor: '#f5f5f5',
      fontFamily: 'sans-serif'
    }}>
      {/* Header */}
      <div style={{
        backgroundColor: '#1976d2',
        color: 'white',
        padding: '1rem 2rem',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        boxShadow: '0 2px 4px rgba(0,0,0,0.1)'
      }}>
        <h1 style={{ margin: 0, fontSize: '1.5rem' }}>
          🎹 Assistant Gazelle V5 - Alertes Humidité
        </h1>
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <span style={{ fontSize: '0.9rem' }}>
            {user.email}
          </span>
          <button
            onClick={handleLogout}
            style={{
              padding: '0.5rem 1rem',
              backgroundColor: 'rgba(255,255,255,0.2)',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer',
              fontSize: '0.9rem'
            }}
          >
            Déconnexion
          </button>
        </div>
      </div>

      {/* Contenu principal */}
      <div style={{ padding: '2rem' }}>
        <HumidityAlertsDashboard />
      </div>
    </div>
  )
}

export default AppSimple
