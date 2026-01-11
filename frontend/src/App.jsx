import { useState, useEffect } from 'react'
import { Fab, Drawer, IconButton } from '@mui/material'
import { Chat as ChatIcon, Close as CloseIcon } from '@mui/icons-material'
import VincentDIndyDashboard from './components/VincentDIndyDashboard'
import LoginScreen from './components/LoginScreen'
import TableauDeBord from './components/TableauDeBord' // 🆕 Dashboard unifié
import InventaireDashboard from './components/InventaireDashboard'
import NickDashboard from './components/dashboards/NickDashboard'
import LouiseDashboard from './components/dashboards/LouiseDashboard'
import JeanPhilippeDashboard from './components/dashboards/JeanPhilippeDashboard'
import PlaceDesArtsDashboard from './components/place_des_arts/PlaceDesArtsDashboard'
import AssistantWidget from './components/AssistantWidget'
import ChatIntelligent from './components/ChatIntelligent'
import TravelFeeCalculator from './components/admin/TravelFeeCalculator'
import KilometersCalculator from './components/admin/KilometersCalculator'
import MaintenanceAlertsCard from './components/MaintenanceAlertsCard'
import ErrorBoundary from './components/ErrorBoundary'
import { getUserRole, ROLES } from './config/roles'

// V7 Imports - Master Template Vincent d'Indy (527 lignes)
import VDIInventoryWrapper from './components/VDIInventoryWrapper'

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
  const [currentView, setCurrentView] = useState('tableau-de-bord') // DÉFAUT: tableau-de-bord unifié
  const [simulatedRole, setSimulatedRole] = useState(null) // Pour tester les rôles sans auth
  const [chatOpen, setChatOpen] = useState(false) // Contrôle du chat flottant
  const [institutionsDropdownOpen, setInstitutionsDropdownOpen] = useState(false) // Dropdown Institutions
  const [institutions, setInstitutions] = useState([]) // Liste dynamique des institutions
  const [selectedLocation, setSelectedLocation] = useState('vincent-dindy') // Institution sélectionnée (défaut: vincent-dindy)
  const [isFestiveTheme, setIsFestiveTheme] = useState(() => {
    const saved = localStorage.getItem('festiveTheme')
    if (saved !== null) return saved === 'true'
    return false // désactivé par défaut
  })

  // Charger les institutions depuis l'API
  useEffect(() => {
    const loadInstitutions = async () => {
      try {
        const API_URL = import.meta.env.VITE_API_URL || ''
        const response = await fetch(`${API_URL}/api/institutions/list`)
        if (response.ok) {
          const data = await response.json()
          setInstitutions(data.institutions || [])
          console.log('[App.jsx] Institutions chargées:', data.institutions?.length || 0)
        } else {
          console.error('[App.jsx] Erreur chargement institutions:', response.status)
          // Fallback: liste par défaut si l'API échoue
          setInstitutions([
            { slug: 'vincent-dindy', name: "Vincent d'Indy" },
            { slug: 'place-des-arts', name: 'Place des Arts' },
            { slug: 'orford', name: 'Orford Musique' }
          ])
        }
      } catch (error) {
        console.error('[App.jsx] Erreur chargement institutions:', error)
        // Fallback: liste par défaut
        setInstitutions([
          { slug: 'vincent-dindy', name: "Vincent d'Indy" },
          { slug: 'place-des-arts', name: 'Place des Arts' },
          { slug: 'orford', name: 'Orford Musique' }
        ])
      }
    }
    loadInstitutions()
  }, [])

  // Charger l'utilisateur depuis localStorage au démarrage
  useEffect(() => {
    console.log('[App.jsx] useEffect chargement utilisateur - début');
    try {
      const savedUser = localStorage.getItem('currentUser')
      console.log('[App.jsx] Utilisateur sauvegardé trouvé:', savedUser ? 'OUI' : 'NON');
      if (savedUser) {
        try {
          const parsedUser = JSON.parse(savedUser)
          console.log('[App.jsx] Utilisateur parsé:', parsedUser?.email || parsedUser?.name);
          setCurrentUser(parsedUser)
        } catch (e) {
          console.error('[App.jsx] Erreur parsing utilisateur:', e);
          localStorage.removeItem('currentUser')
        }
      }
      console.log('[App.jsx] useEffect chargement utilisateur - fin');
    } catch (e) {
      console.error('[App.jsx] Erreur dans useEffect chargement utilisateur:', e);
      alert(`Erreur au chargement utilisateur: ${e.message}\n\nStack: ${e.stack}`);
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

  // Fermer le dropdown Institutions si on clique ailleurs
  useEffect(() => {
    if (!institutionsDropdownOpen) return
    
    const handleClickOutside = (event) => {
      // Vérifier si le clic est à l'extérieur du dropdown
      const dropdownContainer = event.target.closest('[data-dropdown="institutions"]')
      if (!dropdownContainer) {
        setInstitutionsDropdownOpen(false)
      }
    }
    
    // Utiliser setTimeout pour éviter que le clic sur le bouton ferme immédiatement
    const timeoutId = setTimeout(() => {
      document.addEventListener('click', handleClickOutside)
    }, 0)
    
    return () => {
      clearTimeout(timeoutId)
      document.removeEventListener('click', handleClickOutside)
    }
  }, [institutionsDropdownOpen])

  // Déterminer le rôle effectif (simulé ou réel)
  const effectiveRole = simulatedRole || getUserRole(currentUser?.email)

  // Fermer le dropdown Institutions quand le rôle change
  useEffect(() => {
    setInstitutionsDropdownOpen(false)
  }, [effectiveRole])

  // DÉSACTIVÉ: Initialisation vue par défaut - causait des boucles de redirection
  // La vue par défaut est maintenant 'inventaire' dans useState ci-dessus
  // Les utilisateurs peuvent naviguer librement sans redirections automatiques
  // useEffect(() => {
  //   // DÉSACTIVÉ pour éviter les boucles de redirection
  // }, [effectiveRole, currentView])

  // Créer un utilisateur effectif avec les bonnes propriétés selon le rôle simulé
  // IMPORTANT: Préserver gazelleId même lors de l'impersonation (nécessaire pour Chat Technicien)
  const effectiveUser = simulatedRole ? {
    ...currentUser,
    email: ROLES[simulatedRole]?.email || currentUser?.email,
    name: ROLES[simulatedRole]?.name.split(' ')[0] || currentUser?.name, // Premier mot du nom
    role: simulatedRole,
    gazelleId: currentUser?.gazelleId // ⭐ Préserver l'ID Gazelle du vrai utilisateur
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
        // Nick: Navigation par currentView (comme admin)
        if (currentView === 'inventaire') {
          return <NickDashboard currentUser={effectiveUser} />
        } else if (currentView === 'place-des-arts') {
          return <PlaceDesArtsDashboard currentUser={effectiveUser} />
        } else if (currentView === 'vincent-dindy-v7') {
          return (
            <ErrorBoundary componentName="Vincent d'Indy">
              <VincentDIndyDashboard currentUser={effectiveUser} institution="vincent-dindy" />
            </ErrorBoundary>
          )
        } else if (currentView === 'orford') {
          return (
            <ErrorBoundary componentName="Orford">
              <VincentDIndyDashboard currentUser={effectiveUser} institution="orford" />
            </ErrorBoundary>
          )
        } else if (currentView === 'calculateur-frais') {
          return (
            <ErrorBoundary componentName="Calculateur Frais">
              <div className="space-y-8">
                <TravelFeeCalculator />
                <div className="border-t border-gray-200 pt-8">
                  <KilometersCalculator />
                </div>
              </div>
            </ErrorBoundary>
          )
        }
        // Par défaut: Inventaire
        return <NickDashboard currentUser={effectiveUser} />
      case 'louise':
      case 'margot':
        // Louise & Margot: Navigation par currentView (comme admin)
        if (currentView === 'inventaire') {
          return (
            <ErrorBoundary componentName="Inventaire Dashboard">
              <InventaireDashboard currentUser={effectiveUser} />
            </ErrorBoundary>
          )
        } else if (currentView === 'calculateur-frais') {
          return (
            <ErrorBoundary componentName="Calculateur Frais">
              <div className="space-y-8">
                <TravelFeeCalculator />
                <div className="border-t border-gray-200 pt-8">
                  <KilometersCalculator />
                </div>
              </div>
            </ErrorBoundary>
          )
        } else if (currentView === 'vincent-dindy-v7') {
          return (
            <ErrorBoundary componentName="Vincent d'Indy">
              <VincentDIndyDashboard currentUser={effectiveUser} institution="vincent-dindy" />
            </ErrorBoundary>
          )
        } else if (currentView === 'orford') {
          return (
            <ErrorBoundary componentName="Orford">
              <VincentDIndyDashboard currentUser={effectiveUser} institution="orford" />
            </ErrorBoundary>
          )
        } else if (currentView === 'place-des-arts') {
          return (
            <ErrorBoundary componentName="Place des Arts">
              <PlaceDesArtsDashboard currentUser={effectiveUser} />
            </ErrorBoundary>
          )
        }
        // Par défaut: Inventaire
        return (
          <ErrorBoundary componentName="Inventaire Dashboard">
            <InventaireDashboard currentUser={effectiveUser} />
          </ErrorBoundary>
        )
      case 'jeanphilippe':
        // Jean-Philippe: Inventaire et Tournées (vue technicien)
        if (currentView === 'inventaire') {
          return (
            <ErrorBoundary componentName="Inventaire Dashboard">
              {/* Container style téléphone portable pour Jean-Philippe */}
              <div className="w-full max-w-md mx-auto px-4 py-4 sm:px-3 sm:py-2">
                <div className="bg-white rounded-lg shadow-lg border border-gray-200 overflow-hidden">
                  <InventaireDashboard currentUser={effectiveUser} />
                </div>
              </div>
            </ErrorBoundary>
          )
        } else if (currentView === 'tournees') {
          return (
            <ErrorBoundary componentName="Vincent d'Indy (Tournées)">
              <VincentDIndyDashboard 
                currentUser={effectiveUser} 
                initialView="technicien"
                hideNickView={true}
                hideLocationSelector={true}
              />
            </ErrorBoundary>
          )
        } else if (currentView === 'calculateur-frais') {
          return (
            <ErrorBoundary componentName="Calculateur Frais">
              {/* Container style téléphone portable pour Jean-Philippe */}
              <div className="w-full max-w-md mx-auto px-4 py-4 sm:px-3 sm:py-2">
                <div className="bg-white rounded-lg shadow-lg border border-gray-200 overflow-hidden p-4">
                  <div className="space-y-8">
                    <TravelFeeCalculator />
                    <div className="border-t border-gray-200 pt-8">
                      <KilometersCalculator />
                    </div>
                  </div>
                </div>
              </div>
            </ErrorBoundary>
          )
        }
        // Par défaut: Inventaire
        return (
          <ErrorBoundary componentName="Inventaire Dashboard">
            {/* Container style téléphone portable pour Jean-Philippe */}
            <div className="w-full max-w-md mx-auto px-4 py-4 sm:px-3 sm:py-2">
              <div className="bg-white rounded-lg shadow-lg border border-gray-200 overflow-hidden">
                <InventaireDashboard currentUser={effectiveUser} />
              </div>
            </div>
          </ErrorBoundary>
        )
      case 'admin':
      default:
        // Dashboard admin unifié
        if (currentView === 'tableau-de-bord' || currentView === 'dashboard') {
          return (
            <ErrorBoundary componentName="Tableau de Bord">
              <TableauDeBord currentUser={effectiveUser} />
            </ErrorBoundary>
          )
        } else if (currentView === 'configuration') {
          return (
            <ErrorBoundary componentName="Configuration">
              <div className="max-w-7xl mx-auto px-4 py-6">
                <h1 className="text-2xl font-bold text-gray-800 mb-6">⚙️ Configuration</h1>
                <MaintenanceAlertsCard />
              </div>
            </ErrorBoundary>
          )
        } else if (currentView === 'inventaire') {
          return (
            <ErrorBoundary componentName="Inventaire Dashboard">
              <InventaireDashboard currentUser={effectiveUser} />
            </ErrorBoundary>
          )
        } else if (currentView === 'tournees') {
          return (
            <ErrorBoundary componentName="Nick Dashboard">
              <NickDashboard currentUser={effectiveUser} />
            </ErrorBoundary>
          )
        } else if (currentView === 'place-des-arts') {
          return (
            <ErrorBoundary componentName="Place des Arts">
              <PlaceDesArtsDashboard currentUser={effectiveUser} />
            </ErrorBoundary>
          )
        } else if (currentView === 'chat') {
          return (
            <ErrorBoundary componentName="Chat Intelligent">
              <ChatIntelligent currentUser={effectiveUser} />
            </ErrorBoundary>
          )
        } else if (currentView === 'calculateur-frais') {
          return (
            <ErrorBoundary componentName="Calculateur Frais">
              <div className="space-y-8">
                <TravelFeeCalculator />
                <div className="border-t border-gray-200 pt-8">
                  <KilometersCalculator />
                </div>
              </div>
            </ErrorBoundary>
          )
        } else if (currentView === 'vincent-dindy-v7') {
          // Vincent d'Indy Dashboard (version restaurée, sans iframe)
          return (
            <ErrorBoundary componentName="Vincent d'Indy">
              <VincentDIndyDashboard currentUser={effectiveUser} institution="vincent-dindy" />
            </ErrorBoundary>
          )
        } else if (currentView === 'orford') {
          // Orford Dashboard (utilise le même composant que Vincent d'Indy mais avec institution="orford")
          return (
            <ErrorBoundary componentName="Orford">
              <VincentDIndyDashboard currentUser={effectiveUser} institution="orford" />
            </ErrorBoundary>
          )
        } else {
          // Fallback: Vincent d'Indy Dashboard
          return (
            <ErrorBoundary componentName="Vincent d'Indy">
              <VincentDIndyDashboard currentUser={effectiveUser} institution="vincent-dindy" />
            </ErrorBoundary>
          )
        }
    }
  }

  return (
    <>
      <ErrorBoundary componentName="Application principale">
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
            {(effectiveRole === 'admin' || effectiveRole === 'nick' || effectiveRole === 'louise' || effectiveRole === 'margot' || effectiveRole === 'jeanphilippe') && (
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

                    {/* Institutions - Nick - Dropdown */}
                    <div className="relative" data-dropdown="institutions">
                      <button
                        onClick={(e) => {
                          e.stopPropagation()
                          setInstitutionsDropdownOpen(!institutionsDropdownOpen)
                        }}
                        className={`px-4 py-2 text-sm rounded-lg transition-colors flex items-center gap-1 ${
                          currentView === 'vincent-dindy-v7' || currentView === 'place-des-arts'
                            ? 'bg-blue-100 text-blue-700 font-medium'
                            : 'text-gray-600 hover:bg-gray-100'
                        }`}
                      >
                        {currentView === 'vincent-dindy-v7' ? '🎹 Vincent d\'Indy' :
                         currentView === 'place-des-arts' ? '🎭 Place des Arts' :
                         '🏛️ Institutions'}
                        <span className="text-xs">▼</span>
                      </button>
                      {institutionsDropdownOpen && (
                        <div 
                          className="absolute top-full left-0 mt-1 bg-white border border-gray-200 rounded-lg shadow-lg py-1 z-50 min-w-[200px]"
                          onClick={(e) => e.stopPropagation()}
                        >
                          {institutions.map((inst) => {
                            // Mapping slug → currentView
                            const viewMap = {
                              'vincent-dindy': 'vincent-dindy-v7',
                              'place-des-arts': 'place-des-arts',
                              'orford': 'orford'
                            }
                            const viewValue = viewMap[inst.slug] || inst.slug
                            const isSelected = currentView === viewValue
                            
                            // Emoji par défaut (peut être amélioré avec options)
                            const emojiMap = {
                              'vincent-dindy': '🎹',
                              'place-des-arts': '🎭',
                              'orford': '🏛️'
                            }
                            const emoji = emojiMap[inst.slug] || '🏛️'
                            
                            return (
                              <button
                                key={inst.slug}
                                onClick={(e) => {
                                  e.stopPropagation()
                                  setCurrentView(viewValue)
                                  setSelectedLocation(inst.slug)
                                  setInstitutionsDropdownOpen(false)
                                }}
                                className={`w-full text-left px-4 py-2 text-sm transition-colors ${
                                  isSelected
                                    ? 'bg-blue-50 text-blue-700 font-medium'
                                    : 'text-gray-700 hover:bg-blue-50 hover:text-blue-700'
                                }`}
                              >
                                {emoji} {inst.name}
                              </button>
                            )
                          })}
                        </div>
                      )}
                    </div>
                  </>
                ) : effectiveRole === 'jeanphilippe' ? (
                  <>
                    {/* Inventaire - Jean-Philippe */}
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
                    
                    {/* Tournées - Jean-Philippe (vue technicien) */}
                    <button
                      onClick={() => setCurrentView('tournees')}
                      className={`px-4 py-2 text-sm rounded-lg transition-colors ${
                        currentView === 'tournees'
                          ? 'bg-blue-100 text-blue-700 font-medium'
                          : 'text-gray-600 hover:bg-gray-100'
                      }`}
                    >
                      🗺️ Tournées
                    </button>

                    {/* Calculateur - Jean-Philippe */}
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
                  </>
                ) : (
                  <>
                    {/* Tableau de Bord - admin seulement */}
                    {effectiveRole === 'admin' && (
                      <button
                        onClick={() => setCurrentView('tableau-de-bord')}
                        className={`px-4 py-2 text-sm rounded-lg transition-colors ${
                          currentView === 'tableau-de-bord' || currentView === 'dashboard'
                            ? 'bg-blue-100 text-blue-700 font-medium'
                            : 'text-gray-600 hover:bg-gray-100'
                        }`}
                      >
                        📊 Tableau de bord
                      </button>
                    )}

                    {/* Configuration - admin seulement */}
                    {effectiveRole === 'admin' && (
                      <button
                        onClick={() => setCurrentView('configuration')}
                        className={`px-4 py-2 text-sm rounded-lg transition-colors ${
                          currentView === 'configuration'
                            ? 'bg-blue-100 text-blue-700 font-medium'
                            : 'text-gray-600 hover:bg-gray-100'
                        }`}
                      >
                        ⚙️ Configuration
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

                    {/* Chat Technicien - Ma Journée */}
                    <button
                      onClick={() => setCurrentView('chat')}
                      className={`px-4 py-2 text-sm rounded-lg transition-colors ${
                        currentView === 'chat'
                          ? 'bg-blue-100 text-blue-700 font-medium'
                          : 'text-gray-600 hover:bg-gray-100'
                      }`}
                    >
                      🎵 Ma Journée
                    </button>

                    {/* Calculateur - admin, louise, margot, nick et jeanphilippe */}
                    {(effectiveRole === 'admin' || effectiveRole === 'louise' || effectiveRole === 'margot' || effectiveRole === 'nick' || effectiveRole === 'jeanphilippe') && (
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

                    {/* Institutions - Admin, Louise et Margot - Dropdown */}
                    {(effectiveRole === 'admin' || effectiveRole === 'louise' || effectiveRole === 'margot') && (
                      <div className="relative" data-dropdown="institutions">
                        <button
                          onClick={(e) => {
                            e.stopPropagation()
                            setInstitutionsDropdownOpen(!institutionsDropdownOpen)
                          }}
                          className={`px-4 py-2 text-sm rounded-lg transition-colors flex items-center gap-1 ${
                            currentView === 'vincent-dindy-v7' || currentView === 'place-des-arts'
                              ? 'bg-blue-100 text-blue-700 font-medium'
                              : 'text-gray-600 hover:bg-gray-100'
                          }`}
                        >
                          {currentView === 'vincent-dindy-v7' ? '🎹 Vincent d\'Indy' :
                           currentView === 'place-des-arts' ? '🎭 Place des Arts' :
                           '🏛️ Institutions'}
                          <span className="text-xs">▼</span>
                        </button>
                        {institutionsDropdownOpen && (
                          <div 
                            className="absolute top-full left-0 mt-1 bg-white border border-gray-200 rounded-lg shadow-lg py-1 z-50 min-w-[200px]"
                            onClick={(e) => e.stopPropagation()}
                          >
                            {institutions.map((inst) => {
                              // Mapping slug → currentView
                              const viewMap = {
                                'vincent-dindy': 'vincent-dindy-v7',
                                'place-des-arts': 'place-des-arts',
                                'orford': 'orford'
                              }
                              const viewValue = viewMap[inst.slug] || inst.slug
                              const isSelected = currentView === viewValue
                              
                              // Emoji par défaut (peut être amélioré avec options)
                              const emojiMap = {
                                'vincent-dindy': '🎹',
                                'place-des-arts': '🎭',
                                'orford': '🏛️'
                              }
                              const emoji = emojiMap[inst.slug] || '🏛️'
                              
                              return (
                                <button
                                  key={inst.slug}
                                  onClick={(e) => {
                                    e.stopPropagation()
                                    setCurrentView(viewValue)
                                    setSelectedLocation(inst.slug)
                                    setInstitutionsDropdownOpen(false)
                                  }}
                                  className={`w-full text-left px-4 py-2 text-sm transition-colors ${
                                    isSelected
                                      ? 'bg-blue-50 text-blue-700 font-medium'
                                      : 'text-gray-700 hover:bg-blue-50 hover:text-blue-700'
                                  }`}
                                >
                                  {emoji} {inst.name}
                                </button>
                              )
                            })}
                          </div>
                        )}
                      </div>
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
                <option value="margot">Margot</option>
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
        </div>
      </ErrorBoundary>

      {/* Chat Intelligent Widget - Remplace l'ancien assistant v4 */}
      <AssistantWidget
        currentUser={effectiveUser}
        role={effectiveRole}
        onBackToDashboard={currentView === 'assistant' ? () => setCurrentView('dashboard') : undefined}
        useChatIntelligent={true} // NOUVEAU: Utiliser Chat Intelligent au lieu de v4
        onOpenMaJournee={() => setCurrentView('chat')} // Ouvrir "Ma Journée" au clic sur le bouton bleu
      />
    </>
  )
}

export default App






