import { useState, useEffect } from 'react'
import VincentDIndyDashboard from './components/VincentDIndyDashboard'
import LoginScreen from './components/LoginScreen'
import DashboardHome from './components/DashboardHome'
import AlertesRV from './components/AlertesRV'
import InventaireDashboard from './components/InventaireDashboard'
import NickDashboard from './components/dashboards/NickDashboard'
import LouiseDashboard from './components/dashboards/LouiseDashboard'
import JeanPhilippeDashboard from './components/dashboards/JeanPhilippeDashboard'
import AssistantWidget from './components/AssistantWidget'
import { getUserRole, ROLES } from './config/roles'

function App() {
  const [currentUser, setCurrentUser] = useState(null)
  const [currentView, setCurrentView] = useState('dashboard') // 'dashboard', 'pianos', 'alertes-rv', 'inventaire', 'tournees'
  const [simulatedRole, setSimulatedRole] = useState(null) // Pour tester les rôles sans auth

  // Charger l'utilisateur depuis localStorage au démarrage
  useEffect(() => {
    const savedUser = localStorage.getItem('currentUser')
    if (savedUser) {
      try {
        setCurrentUser(JSON.parse(savedUser))
      } catch (e) {
        localStorage.removeItem('currentUser')
      }
    }
  }, [])

  // Déterminer le rôle effectif (simulé ou réel)
  const effectiveRole = simulatedRole || getUserRole(currentUser?.email)

  const handleLogin = (user) => {
    setCurrentUser(user)
  }

  const handleLogout = () => {
    localStorage.removeItem('currentUser')
    setCurrentUser(null)
    setSimulatedRole(null) // Réinitialiser le rôle simulé
  }

  if (!currentUser) {
    return <LoginScreen onLogin={handleLogin} />
  }

  // Rendu conditionnel selon le rôle
  const renderDashboard = () => {
    switch (effectiveRole) {
      case 'nick':
        return <NickDashboard currentUser={currentUser} />
      case 'louise':
        return <LouiseDashboard currentUser={currentUser} />
      case 'jeanphilippe':
        return <JeanPhilippeDashboard currentUser={currentUser} />
      case 'admin':
      default:
        // Dashboard admin (actuel)
        if (currentView === 'dashboard') {
          return <DashboardHome currentUser={currentUser} />
        } else if (currentView === 'alertes-rv') {
          return <AlertesRV currentUser={currentUser} />
        } else if (currentView === 'inventaire') {
          return <InventaireDashboard currentUser={currentUser} />
        } else if (currentView === 'tournees') {
          return <NickDashboard currentUser={currentUser} />
        } else {
          return <VincentDIndyDashboard currentUser={currentUser} />
        }
    }
  }

  return (
    <div className="App">
      {/* Header avec nom d'utilisateur */}
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 py-3 flex justify-between items-center">
          <div className="flex items-center gap-6">
            <div className="flex items-center gap-3">
              <span className="text-2xl">🎹</span>
              <h1 className="text-xl font-semibold text-gray-800">Assistant Gazelle V5</h1>
            </div>

            {/* Navigation (seulement pour les admins) */}
            {effectiveRole === 'admin' && (
              <nav className="flex gap-2">
                <button
                  onClick={() => setCurrentView('dashboard')}
                  className={`px-4 py-2 text-sm rounded-lg transition-colors ${
                    currentView === 'dashboard'
                      ? 'bg-blue-100 text-blue-700 font-medium'
                      : 'text-gray-600 hover:bg-gray-100'
                  }`}
                >
                  📊 Dashboard
                </button>
                <button
                  onClick={() => setCurrentView('pianos')}
                  className={`px-4 py-2 text-sm rounded-lg transition-colors ${
                    currentView === 'pianos'
                      ? 'bg-blue-100 text-blue-700 font-medium'
                      : 'text-gray-600 hover:bg-gray-100'
                  }`}
                >
                  🎹 Pianos
                </button>
                <button
                  onClick={() => setCurrentView('alertes-rv')}
                  className={`px-4 py-2 text-sm rounded-lg transition-colors ${
                    currentView === 'alertes-rv'
                      ? 'bg-blue-100 text-blue-700 font-medium'
                      : 'text-gray-600 hover:bg-gray-100'
                  }`}
                >
                  🔔 Alertes RV
                </button>
                <button
                  onClick={() => setCurrentView('inventaire')}
                  className={`px-4 py-2 text-sm rounded-lg transition-colors ${
                    currentView === 'inventaire'
                      ? 'bg-blue-100 text-blue-700 font-medium'
                      : 'text-gray-600 hover:bg-gray-100'
                  }`}
                >
                  📦 Inventaire
                </button>
                <button
                  onClick={() => setCurrentView('tournees')}
                  className={`px-4 py-2 text-sm rounded-lg transition-colors ${
                    currentView === 'tournees'
                      ? 'bg-blue-100 text-blue-700 font-medium'
                      : 'text-gray-600 hover:bg-gray-100'
                  }`}
                >
                  🎼 Tournées
                </button>
              </nav>
            )}
          </div>

          <div className="flex items-center gap-4">
            {/* Sélecteur de rôle pour test (temporaire - seulement pour admin) */}
            {currentUser?.email === 'allan@pianotekinc.com' && (
              <select
                value={simulatedRole || effectiveRole}
                onChange={(e) => setSimulatedRole(e.target.value)}
                className="px-3 py-1 text-sm border border-gray-300 rounded bg-yellow-50"
                title="Sélecteur de rôle (temporaire pour test)"
              >
                <option value="admin">Admin</option>
                <option value="nick">Nick</option>
                <option value="louise">Louise</option>
                <option value="jeanphilippe">Jean-Philippe</option>
              </select>
            )}

            <div className="text-right">
              <div className="text-sm font-medium text-gray-800">{currentUser?.name || 'Test User'}</div>
              <div className="text-xs text-gray-500">
                {ROLES[effectiveRole]?.name || 'Administrateur'}
              </div>
            </div>
            <button
              onClick={handleLogout}
              className="px-4 py-2 text-sm bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-lg transition-colors"
            >
              Déconnexion
            </button>
          </div>
        </div>
      </header>

      {/* Contenu principal */}
      {renderDashboard()}

      {/* Assistant Widget (disponible pour tous les profils) */}
      <AssistantWidget
        currentUser={currentUser}
        role={effectiveRole}
      />
    </div>
  )
}

export default App






