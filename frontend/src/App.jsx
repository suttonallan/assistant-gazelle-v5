import { useState, useEffect } from 'react'
import VincentDIndyDashboard from './components/VincentDIndyDashboard'
import LoginScreen from './components/LoginScreen'
import DashboardHome from './components/DashboardHome'
import AlertesRV from './components/AlertesRV'
import InventaireDashboard from './components/InventaireDashboard'
import NotificationsPanel from './components/NotificationsPanel'
import NickDashboard from './components/dashboards/NickDashboard'
import LouiseDashboard from './components/dashboards/LouiseDashboard'
import JeanPhilippeDashboard from './components/dashboards/JeanPhilippeDashboard'
import PlaceDesArtsDashboard from './components/place_des_arts/PlaceDesArtsDashboard'
import AssistantWidget from './components/AssistantWidget'
import ChatIntelligent from './components/ChatIntelligent'
import TravelFeeCalculator from './components/admin/TravelFeeCalculator'
import KilometersCalculator from './components/admin/KilometersCalculator'
import { getUserRole, ROLES } from './config/roles'

function FestiveDecor({ show }) {
  if (!show) return null
  return (
    <>
      {/* Sapin décoré */}
      <div className="festive-tree" aria-hidden="true">
        <svg viewBox="0 0 180 260" role="presentation">
          <defs>
            <linearGradient id="treeGrad" x1="0%" y1="0%" x2="0%" y2="100%">
              <stop offset="0%" stopColor="#1c7c54" />
              <stop offset="100%" stopColor="#0f5a3d" />
            </linearGradient>
            <linearGradient id="trunkGrad" x1="0%" y1="0%" x2="0%" y2="100%">
              <stop offset="0%" stopColor="#8b5a2b" />
              <stop offset="100%" stopColor="#5c3b1a" />
            </linearGradient>
          </defs>
          <polygon points="90,10 20,110 160,110" fill="#e0b31a" />
          <polygon points="90,40 25,140 155,140" fill="url(#treeGrad)" />
          <polygon points="90,90 30,190 150,190" fill="url(#treeGrad)" />
          <polygon points="90,140 40,230 140,230" fill="url(#treeGrad)" />
          <rect x="75" y="220" width="30" height="30" rx="4" fill="url(#trunkGrad)" />
          {/* Guirlandes */}
          <path d="M35 140 C70 150, 110 150, 145 135" stroke="#f6c453" strokeWidth="6" fill="none" strokeLinecap="round" />
          <path d="M40 175 C80 188, 105 188, 140 172" stroke="#f6c453" strokeWidth="6" fill="none" strokeLinecap="round" />
          {/* Boules */}
          {[ [60,120,'#e63946'], [120,125,'#3c6e71'], [70,165,'#e63946'], [110,170,'#f4a261'], [90,200,'#3c6e71'] ].map((b,i)=>(
            <circle key={i} cx={b[0]} cy={b[1]} r="8" fill={b[2]} stroke="white" strokeWidth="2" />
          ))}
          {/* Étoile */}
          <polygon points="90,18 96,34 114,34 100,44 106,60 90,50 74,60 80,44 66,34 84,34" fill="#ffd166" />
        </svg>
      </div>
      {/* Traîneau du Père Noël */}
      <div className="festive-sleigh" aria-hidden="true">
        <svg viewBox="0 0 260 140" role="presentation">
          <defs>
            <linearGradient id="sledBody" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stopColor="#b82030" />
              <stop offset="100%" stopColor="#e63946" />
            </linearGradient>
          </defs>
          <path d="M30 90 C60 110, 140 110, 190 90 L210 90 C220 90, 225 95, 225 105 C225 120, 210 125, 195 122 L70 122 C50 122, 35 112, 30 100 Z" fill="url(#sledBody)" stroke="#5a0f1a" strokeWidth="4" />
          <rect x="55" y="65" width="90" height="30" rx="10" fill="#ffd166" stroke="#c68a12" strokeWidth="3" />
          <circle cx="80" cy="118" r="8" fill="#f6c453" />
          <circle cx="180" cy="118" r="8" fill="#f6c453" />
          <path d="M40 115 C60 135, 140 135, 220 115" stroke="#5a0f1a" strokeWidth="6" fill="none" strokeLinecap="round" />
          <path d="M200 70 C220 65, 230 55, 235 40" stroke="#5a0f1a" strokeWidth="6" fill="none" strokeLinecap="round" />
          <path d="M210 65 C230 60, 238 52, 242 40" stroke="#5a0f1a" strokeWidth="4" fill="none" strokeLinecap="round" />
        </svg>
      </div>
    </>
  )
}

function App() {
  const [currentUser, setCurrentUser] = useState(null)
  const [currentView, setCurrentView] = useState('dashboard') // 'dashboard', 'pianos', 'alertes-rv', 'inventaire', 'tournees'
  const [simulatedRole, setSimulatedRole] = useState(null) // Pour tester les rôles sans auth
  const [isFestiveTheme, setIsFestiveTheme] = useState(() => {
    const saved = localStorage.getItem('festiveTheme')
    if (saved !== null) return saved === 'true'
    return false // désactivé par défaut
  })

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

  // Persistance + classe body pour le thème fêtes
  useEffect(() => {
    localStorage.setItem('festiveTheme', isFestiveTheme ? 'true' : 'false')
    const body = document.body
    if (isFestiveTheme) {
      body.classList.add('festive')
    } else {
      body.classList.remove('festive')
    }
  }, [isFestiveTheme])

  // Déterminer le rôle effectif (simulé ou réel)
  const effectiveRole = simulatedRole || getUserRole(currentUser?.email)

  // Créer un utilisateur effectif avec les bonnes propriétés selon le rôle simulé
  const effectiveUser = simulatedRole ? {
    ...currentUser,
    email: ROLES[simulatedRole]?.email || currentUser?.email,
    name: ROLES[simulatedRole]?.name.split(' ')[0] || currentUser?.name, // Premier mot du nom
    role: simulatedRole
  } : currentUser

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
        if (currentView === 'place-des-arts') {
          return <PlaceDesArtsDashboard currentUser={effectiveUser} />
        }
        // Par défaut, Nick voit uniquement l'inventaire
        return <InventaireDashboard currentUser={effectiveUser} />
      case 'louise':
        return <LouiseDashboard currentUser={effectiveUser} />
      case 'jeanphilippe':
        return <InventaireDashboard currentUser={effectiveUser} />
      case 'admin':
      default:
        // Dashboard admin (actuel)
        if (currentView === 'dashboard') {
          return <DashboardHome currentUser={effectiveUser} />
        } else if (currentView === 'notifications') {
          return <NotificationsPanel currentUser={effectiveUser} />
        } else if (currentView === 'alertes-rv') {
          return <AlertesRV currentUser={effectiveUser} />
        } else if (currentView === 'inventaire') {
          return <InventaireDashboard currentUser={effectiveUser} />
        } else if (currentView === 'tournees') {
          return <NickDashboard currentUser={effectiveUser} />
        } else if (currentView === 'place-des-arts') {
          return <PlaceDesArtsDashboard currentUser={effectiveUser} />
        } else if (currentView === 'chat') {
          return <ChatIntelligent currentUser={effectiveUser} />
        } else if (currentView === 'calculateur-frais') {
          return (
            <div className="space-y-8">
              <TravelFeeCalculator />
              <div className="border-t border-gray-200 pt-8">
                <KilometersCalculator />
              </div>
            </div>
          )
        } else {
          return <VincentDIndyDashboard currentUser={effectiveUser} />
        }
    }
  }

  return (
    <div className={`App ${isFestiveTheme ? 'festive' : ''}`}>
      <FestiveDecor show={isFestiveTheme} />
      {/* Header avec nom d'utilisateur */}
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 py-3 flex justify-between items-center">
          <div className="flex items-center gap-6">
            <div className="flex items-center gap-3">
              <span className="text-2xl">🎹</span>
              <h1 className="text-xl font-semibold text-gray-800">Assistant Gazelle V5</h1>
            </div>

            {/* Navigation conditionnelle par rôle */}
            {(effectiveRole === 'admin' || effectiveRole === 'nick' || effectiveRole === 'louise' || effectiveRole === 'jeanphilippe') && (
              <nav className="flex gap-2">
                {effectiveRole === 'nick' ? (
                  <>
                    {/* Inventaire - Nick */}
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

                    {/* Place des Arts - Nick */}
                    <button
                      onClick={() => setCurrentView('place-des-arts')}
                      className={`px-4 py-2 text-sm rounded-lg transition-colors ${
                        currentView === 'place-des-arts'
                          ? 'bg-blue-100 text-blue-700 font-medium'
                          : 'text-gray-600 hover:bg-gray-100'
                      }`}
                    >
                      🎭 Place des Arts
                    </button>
                  </>
                ) : effectiveRole === 'jeanphilippe' ? (
                  <>
                    {/* Inventaire - Jean-Philippe uniquement */}
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
                  </>
                ) : (
                  <>
                    {/* Dashboard - admin seulement */}
                    {effectiveRole === 'admin' && (
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
                    )}

                    {/* Notifications - admin seulement */}
                    {effectiveRole === 'admin' && (
                      <button
                        onClick={() => setCurrentView('notifications')}
                        className={`px-4 py-2 text-sm rounded-lg transition-colors ${
                          currentView === 'notifications'
                            ? 'bg-blue-100 text-blue-700 font-medium'
                            : 'text-gray-600 hover:bg-gray-100'
                        }`}
                      >
                        🔔 Notifications
                      </button>
                    )}

                    {/* Pianos - admin seulement */}
                    {effectiveRole === 'admin' && (
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
                    )}

                    {/* Alertes RV - admin seulement */}
                    {effectiveRole === 'admin' && (
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
                    )}

                    {/* Inventaire - accessible à tous (hors Nick déjà géré) */}
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

                    {/* Place des Arts - admin et louise */}
                    {(effectiveRole === 'admin' || effectiveRole === 'louise') && (
                      <button
                        onClick={() => setCurrentView('place-des-arts')}
                        className={`px-4 py-2 text-sm rounded-lg transition-colors ${
                          currentView === 'place-des-arts'
                            ? 'bg-blue-100 text-blue-700 font-medium'
                            : 'text-gray-600 hover:bg-gray-100'
                        }`}
                      >
                        🎭 Place des Arts
                      </button>
                    )}

                    {/* Tournées - admin et louise */}
                    {(effectiveRole === 'admin' || effectiveRole === 'louise') && (
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
                    )}

                    {/* Chat Intelligent - admin et louise */}
                    {(effectiveRole === 'admin' || effectiveRole === 'louise') && (
                      <button
                        onClick={() => setCurrentView('chat')}
                        className={`px-4 py-2 text-sm rounded-lg transition-colors ${
                          currentView === 'chat'
                            ? 'bg-blue-100 text-blue-700 font-medium'
                            : 'text-gray-600 hover:bg-gray-100'
                        }`}
                      >
                        💬 Ma Journée
                      </button>
                    )}

                    {/* Calculateur - admin et louise seulement */}
                    {(effectiveRole === 'admin' || effectiveRole === 'louise') && (
                      <button
                        onClick={() => setCurrentView('calculateur-frais')}
                        className={`px-4 py-2 text-sm rounded-lg transition-colors ${
                          currentView === 'calculateur-frais'
                            ? 'bg-blue-100 text-blue-700 font-medium'
                            : 'text-gray-600 hover:bg-gray-100'
                        }`}
                      >
                        💰 Calculateur
                      </button>
                    )}
                  </>
                )}
              </nav>
            )}
            {isFestiveTheme && (
              <span className="hidden sm:inline-flex items-center text-xs font-medium px-2 py-1 rounded-full bg-red-50 text-red-700 border border-red-100">
                Semaine des fêtes
              </span>
            )}
          </div>

          <div className="flex items-center gap-4">
            {/* Sélecteur de rôle pour test (temporaire - seulement pour admin) */}
            {currentUser?.email === 'asutton@piano-tek.com' && (
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
              onClick={() => setIsFestiveTheme((v) => !v)}
              className={`px-3 py-2 text-sm rounded-lg border transition-colors ${
                isFestiveTheme
                  ? 'bg-green-50 text-green-800 border-green-200'
                  : 'bg-white text-gray-600 border-gray-200 hover:bg-gray-50'
              }`}
              title="Activer/désactiver le thème des fêtes"
            >
              {isFestiveTheme ? 'Thème fêtes : ON' : 'Thème fêtes'}
            </button>
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
        currentUser={effectiveUser}
        role={effectiveRole}
        onBackToDashboard={currentView === 'assistant' ? () => setCurrentView('dashboard') : undefined}
      />
    </div>
  )
}

export default App






