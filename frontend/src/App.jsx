import { useState, useEffect } from 'react'
import { Fab, Drawer, IconButton } from '@mui/material'
import { Chat as ChatIcon, Close as CloseIcon } from '@mui/icons-material'
import VincentDIndyDashboard from './components/VincentDIndyDashboard'
import OrfordDashboard from './components/OrfordDashboard'
import LoginScreen from './components/LoginScreen'
import SyncDashboard from './components/SyncDashboard' // 📊 Dashboard Unifié V6
import InventaireDashboard from './components/InventaireDashboard'
import NickDashboard from './components/dashboards/NickDashboard'
import LouiseDashboard from './components/dashboards/LouiseDashboard'
import JeanPhilippeDashboard from './components/dashboards/JeanPhilippeDashboard'
import PlaceDesArtsDashboard from './components/place_des_arts/PlaceDesArtsDashboard'
import AssistantWidget from './components/AssistantWidget'
import ChatIntelligent from './components/ChatIntelligent'
import MaJournee from './components/MaJournee' // 🧠 Briefings Intelligents V2
import TravelFeeCalculator from './components/admin/TravelFeeCalculator'
import KilometersCalculator from './components/admin/KilometersCalculator'
import ChatStats from './components/ChatStats'
import ErrorBoundary from './components/ErrorBoundary'
import { getUserRole, ROLES } from './config/roles'

// V7 Imports - Master Template Vincent d'Indy (527 lignes)
import VDIInventoryWrapper from './components/VDIInventoryWrapper'

function App() {
  const [currentUser, setCurrentUser] = useState(null)
  const [currentView, setCurrentView] = useState('chat') // DÉFAUT: Ma Journée pour tous
  const [simulatedRole, setSimulatedRole] = useState(null) // Pour tester les rôles sans auth
  const [chatOpen, setChatOpen] = useState(false) // Contrôle du chat flottant
  const [institutionsDropdownOpen, setInstitutionsDropdownOpen] = useState(false) // Dropdown Institutions
  const [institutions, setInstitutions] = useState([]) // Liste dynamique des institutions
  const [selectedLocation, setSelectedLocation] = useState('vincent-dindy') // Institution sélectionnée (défaut: vincent-dindy)

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
  // IMPORTANT: Utiliser le gazelleId du rôle simulé pour que le chat affiche les RV du bon technicien
  const effectiveUser = simulatedRole ? {
    ...currentUser,
    email: ROLES[simulatedRole]?.email || currentUser?.email,
    name: ROLES[simulatedRole]?.name.split(' ')[0] || currentUser?.name, // Premier mot du nom
    role: simulatedRole,
    id: ROLES[simulatedRole]?.gazelleId || currentUser?.gazelleId || currentUser?.id, // ⭐ ID Gazelle du rôle simulé (pour le chat)
    gazelleId: ROLES[simulatedRole]?.gazelleId || currentUser?.gazelleId // Alias pour compatibilité
  } : {
    ...currentUser,
    // ⭐ FIX: Garantir que l'ID Gazelle est disponible pour le chat
    id: currentUser?.gazelleId || ROLES[effectiveRole]?.gazelleId || currentUser?.id,
    gazelleId: currentUser?.gazelleId || ROLES[effectiveRole]?.gazelleId  // Alias explicite
  }

  // Debug: voir effectiveUser quand rôle simulé
  if (simulatedRole) {
    console.log('[App.jsx] simulatedRole:', simulatedRole, 'ROLES[simulatedRole]:', ROLES[simulatedRole])
    console.log('[App.jsx] effectiveUser.gazelleId:', effectiveUser.gazelleId)
  }

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
              <OrfordDashboard currentUser={effectiveUser} institution="orford" />
            </ErrorBoundary>
          )
        } else if (currentView === 'chat') {
          return (
            <ErrorBoundary componentName="Ma Journée">
              <MaJournee currentUser={effectiveUser} />
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
        // Par défaut: Ma Journée
        return (
          <ErrorBoundary componentName="Ma Journée">
            <MaJournee currentUser={effectiveUser} />
          </ErrorBoundary>
        )
      case 'louise':
      case 'margot':
        // Louise & Margot: Navigation par currentView (comme admin)
        if (currentView === 'inventaire') {
          return (
            <ErrorBoundary componentName="Inventaire Dashboard">
              <InventaireDashboard currentUser={effectiveUser} />
            </ErrorBoundary>
          )
        } else if (currentView === 'chat') {
          return (
            <ErrorBoundary componentName="Ma Journée">
              <MaJournee currentUser={effectiveUser} />
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
              <OrfordDashboard currentUser={effectiveUser} institution="orford" />
            </ErrorBoundary>
          )
        } else if (currentView === 'place-des-arts') {
          return (
            <ErrorBoundary componentName="Place des Arts">
              <PlaceDesArtsDashboard currentUser={effectiveUser} />
            </ErrorBoundary>
          )
        }
        // Par défaut: Ma Journée
        return (
          <ErrorBoundary componentName="Ma Journée">
            <MaJournee currentUser={effectiveUser} />
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
        } else if (currentView === 'chat') {
          return (
            <ErrorBoundary componentName="Ma Journée">
              <MaJournee currentUser={effectiveUser} />
            </ErrorBoundary>
          )
        }
        // Par défaut: Ma Journée
        return (
          <ErrorBoundary componentName="Ma Journée">
            <MaJournee currentUser={effectiveUser} />
          </ErrorBoundary>
        )
      case 'admin':
      default:
        // Dashboard admin unifié V6
        if (currentView === 'sync-dashboard' || currentView === 'tableau-de-bord' || currentView === 'dashboard') {
          return (
            <ErrorBoundary componentName="Tableau de Bord">
              <SyncDashboard currentUser={effectiveUser} />
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
            <ErrorBoundary componentName="Ma Journée">
              <MaJournee currentUser={effectiveUser} />
            </ErrorBoundary>
          )
        } else if (currentView === 'chat-stats') {
          return (
            <ErrorBoundary componentName="Chat Stats">
              <ChatStats />
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
        <div className="App">
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

                    {/* Chat - Nick */}
                    <button
                      onClick={() => setCurrentView('chat')}
                      className={`px-4 py-2 text-sm rounded-lg transition-colors ${
                        currentView === 'chat'
                          ? 'bg-blue-100 text-blue-700 font-medium'
                          : 'text-gray-600 hover:bg-gray-100'
                      }`}
                    >
                      📅 Ma Journée
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

                    {/* Chat - Jean-Philippe */}
                    <button
                      onClick={() => setCurrentView('chat')}
                      className={`px-4 py-2 text-sm rounded-lg transition-colors ${
                        currentView === 'chat'
                          ? 'bg-blue-100 text-blue-700 font-medium'
                          : 'text-gray-600 hover:bg-gray-100'
                      }`}
                    >
                      📅 Ma Journée
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
                    {/* Tableau de Bord Unifié V6 - admin seulement */}
                    {effectiveRole === 'admin' && (
                      <button
                        onClick={() => setCurrentView('sync-dashboard')}
                        className={`px-4 py-2 text-sm rounded-lg transition-colors ${
                          currentView === 'sync-dashboard' || currentView === 'tableau-de-bord' || currentView === 'dashboard'
                            ? 'bg-blue-100 text-blue-700 font-medium'
                            : 'text-gray-600 hover:bg-gray-100'
                        }`}
                      >
                        📊 Tableau de Bord
                      </button>
                    )}

                    {/* Chat Stats - admin seulement */}
                    {effectiveRole === 'admin' && (
                      <button
                        onClick={() => setCurrentView('chat-stats')}
                        className={`px-4 py-2 text-sm rounded-lg transition-colors ${
                          currentView === 'chat-stats'
                            ? 'bg-blue-100 text-blue-700 font-medium'
                            : 'text-gray-600 hover:bg-gray-100'
                        }`}
                      >
                        💬 Chat
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

                    {/* Chat - Louise et Margot */}
                    {(effectiveRole === 'louise' || effectiveRole === 'margot') && (
                      <button
                        onClick={() => setCurrentView('chat')}
                        className={`px-4 py-2 text-sm rounded-lg transition-colors ${
                          currentView === 'chat'
                            ? 'bg-blue-100 text-blue-700 font-medium'
                            : 'text-gray-600 hover:bg-gray-100'
                        }`}
                      >
                        📅 Ma Journée
                      </button>
                    )}

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
        onOpenMaJournee={() => {
          console.log('[App.jsx] onOpenMaJournee appelé, currentView avant:', currentView);
          setCurrentView('chat');
          console.log('[App.jsx] setCurrentView("chat") appelé');
        }} // Ouvrir l'Assistant au clic sur le bouton bleu
      />
    </>
  )
}

export default App






