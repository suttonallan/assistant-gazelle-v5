import { useState, useEffect } from 'react'
import VincentDIndyDashboard from './components/VincentDIndyDashboard'
import LoginScreen from './components/LoginScreen'
import DashboardHome from './components/DashboardHome'
import AlertesRV from './components/AlertesRV'

function App() {
  const [currentUser, setCurrentUser] = useState(null)
  const [currentView, setCurrentView] = useState('dashboard') // 'dashboard', 'pianos', ou 'alertes-rv'

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

  const handleLogin = (user) => {
    setCurrentUser(user)
  }

  const handleLogout = () => {
    localStorage.removeItem('currentUser')
    setCurrentUser(null)
  }

  if (!currentUser) {
    return <LoginScreen onLogin={handleLogin} />
  }

  return (
    <div className="App">
      {/* Header avec nom d'utilisateur */}
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 py-3 flex justify-between items-center">
          <div className="flex items-center gap-6">
            <div className="flex items-center gap-3">
              <span className="text-2xl">🎹</span>
              <h1 className="text-xl font-semibold text-gray-800">Vincent-d'Indy</h1>
            </div>

            {/* Navigation (seulement pour les admins) */}
            {currentUser.role === 'admin' && (
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
              </nav>
            )}
          </div>

          <div className="flex items-center gap-4">
            <div className="text-right">
              <div className="text-sm font-medium text-gray-800">{currentUser.name}</div>
              <div className="text-xs text-gray-500">{currentUser.role === 'admin' ? 'Administrateur' : 'Technicien'}</div>
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
      {currentUser.role === 'admin' && currentView === 'dashboard' ? (
        <DashboardHome currentUser={currentUser} />
      ) : currentView === 'alertes-rv' ? (
        <AlertesRV currentUser={currentUser} />
      ) : (
        <VincentDIndyDashboard currentUser={currentUser} />
      )}
    </div>
  )
}

export default App






