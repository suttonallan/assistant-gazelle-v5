import { useState, useRef, useEffect } from 'react'
import ClickableMessage from './ClickableMessage'
import ChatIntelligent from './ChatIntelligent'

import { API_URL } from '../utils/apiConfig'

/**
 * Widget Assistant Conversationnel
 *
 * Composant réutilisable pour tous les profils (Admin, Nick, Louise, Jean-Philippe).
 * Adapte les suggestions et les commandes selon le rôle de l'utilisateur.
 *
 * Props:
 * - currentUser: Objet utilisateur {name, email, role}
 * - role: Rôle de l'utilisateur ('admin', 'nick', 'louise', 'jeanphilippe')
 * - compact: Mode compact (false par défaut)
 * - onBackToDashboard: Callback pour revenir au dashboard (mobile)
 * - useChatIntelligent: Si true, utilise Chat Intelligent V6 au lieu de Assistant V4
 */
export default function AssistantWidget({ currentUser, role = 'admin', compact = false, onBackToDashboard, useChatIntelligent = false }) {
  // Détection mobile pour affichage plein écran
  const [isMobile, setIsMobile] = useState(false)
  
  useEffect(() => {
    const checkMobile = () => {
      setIsMobile(window.innerWidth < 768)
    }
    checkMobile()
    window.addEventListener('resize', checkMobile)
    return () => window.removeEventListener('resize', checkMobile)
  }, [])
  const [isOpen, setIsOpen] = useState(false)
  const [messages, setMessages] = useState([])
  const [inputValue, setInputValue] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const messagesEndRef = useRef(null)

  // Scroll automatique vers le bas
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // Message de bienvenue selon le rôle
  const getWelcomeMessage = () => {
    const welcomeMessages = {
      admin: "👋 Bonjour Allan ! Je peux vous aider avec les stats, les imports, les recherches de clients, etc.",
      nick: "👋 Salut Nick ! Je peux t'aider avec tes tournées, tes rendez-vous et ton inventaire.",
      louise: "👋 Bonjour Louise ! Je peux t'aider avec les rendez-vous, les recherches de clients et les stats.",
      jeanphilippe: "👋 Salut Jean-Philippe ! Je peux t'aider avec tes rendez-vous, les pianos et ton stock."
    }
    return welcomeMessages[role] || welcomeMessages.admin
  }

  // Suggestions rapides selon le rôle
  const getSuggestions = () => {
    const suggestions = {
      admin: [
        { text: ".aide", description: "Voir toutes les commandes" },
        { text: ".mes rv", description: "Mes prochains rendez-vous" },
        { text: ".stats", description: "Statistiques du système" },
        { text: ".cherche Yamaha", description: "Chercher un client/piano" }
      ],
      nick: [
        { text: ".mes rv", description: "Mes prochains rendez-vous" },
        { text: ".prochaines tournées", description: "Mes tournées à venir" },
        { text: ".stock cordes", description: "Stock de cordes disponible" },
        { text: ".aide", description: "Voir toutes les commandes" }
      ],
      louise: [
        { text: ".rv demain", description: "Rendez-vous de demain" },
        { text: ".cherche client", description: "Chercher un client" },
        { text: ".stats mois", description: "Stats du mois" },
        { text: ".aide", description: "Voir toutes les commandes" }
      ],
      jeanphilippe: [
        { text: ".mes rv", description: "Mes prochains rendez-vous" },
        { text: ".piano [numéro]", description: "Infos d'un piano" },
        { text: ".stock marteaux", description: "Stock de marteaux" },
        { text: ".aide", description: "Voir toutes les commandes" }
      ]
    }
    return suggestions[role] || suggestions.admin
  }

  // Envoyer une question à l'assistant
  const handleSendMessage = async (text = inputValue) => {
    if (!text.trim()) return

    const userMessage = { role: 'user', content: text }
    setMessages(prev => [...prev, userMessage])
    setInputValue('')
    setIsLoading(true)

    try {
      const response = await fetch(`${API_URL}/api/assistant/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          question: text,
          user_id: currentUser?.email || 'anonymous'
        })
      })

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`)
      }

      const data = await response.json()

      // Dédupliquer les entités cliquables (le backend peut encore renvoyer doublons client/contact)
      const rawEntities = data.structured_data?.clickable_entities || []
      const byNameCity = new Map()
      rawEntities.forEach((e) => {
        if (!e?.name) return
        const key = `${e.name.trim().toLowerCase()}|${(e.city || '').trim().toLowerCase()}`
        const existing = byNameCity.get(key)
        // Préférer toujours le type client sur contact pour la même personne
        if (!existing || (existing.type !== 'client' && e.type === 'client')) {
          byNameCity.set(key, e)
        }
      })
      const dedupedEntities = Array.from(byNameCity.values())

      const assistantMessage = {
        role: 'assistant',
        content: data.answer || "Désolé, je n'ai pas pu traiter votre demande.",
        metadata: {
          query_type: data.query_type,
          confidence: data.confidence,
          clickable_entities: dedupedEntities
        },
        structured_data: data.structured_data || null
      }

      setMessages(prev => [...prev, assistantMessage])
    } catch (error) {
      console.error('Erreur assistant:', error)
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: `❌ Erreur: ${error.message}. Vérifiez que l'API est démarrée.`,
        error: true
      }])
    } finally {
      setIsLoading(false)
    }
  }

  // Bouton d'ouverture (floating button en bas à droite)
  if (!isOpen) {
    return (
      <button
        onClick={() => {
          setIsOpen(true)
          if (messages.length === 0) {
            setMessages([{
              role: 'assistant',
              content: getWelcomeMessage()
            }])
          }
        }}
        className="fixed bottom-6 right-6 bg-blue-600 hover:bg-blue-700 text-white rounded-full p-4 shadow-lg transition-all hover:scale-110 z-50"
        title="Ouvrir l'assistant"
      >
        <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
        </svg>
        <span className="absolute -top-1 -right-1 bg-red-500 text-white text-xs rounded-full w-5 h-5 flex items-center justify-center">
          ?
        </span>
      </button>
    )
  }

  // Si useChatIntelligent est activé, utiliser Chat Intelligent V6
  if (useChatIntelligent && isOpen) {
    return (
      <div
        className={`fixed ${isMobile ? 'inset-0 w-full h-full rounded-none' : 'bottom-6 right-6 rounded-lg'} bg-white shadow-2xl border border-gray-200 z-50 flex flex-col`}
        style={isMobile ? {} : { width: '600px', maxWidth: '90vw', height: '80vh', maxHeight: '800px' }}
      >
        {/* Header */}
        <div className="bg-gradient-to-r from-blue-600 to-blue-700 text-white p-4 rounded-t-lg flex justify-between items-center">
          <h2 className="text-lg font-bold">mes journées, nos clients</h2>
          <button
            onClick={() => setIsOpen(false)}
            className="text-white/80 hover:text-white transition-colors"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-auto">
          <ChatIntelligent currentUser={currentUser} />
        </div>
      </div>
    )
  }

  // Widget ouvert (Assistant V4 - legacy)
  // Sur mobile, prendre toute la largeur et hauteur
  return (
    <div
      className={`fixed ${isMobile ? 'inset-0 w-full h-full rounded-none' : 'bottom-6 right-6 w-96 rounded-lg'} bg-white shadow-2xl border border-gray-200 z-50 flex flex-col`}
      style={isMobile ? {} : { height: compact ? '400px' : '600px' }}
    >

      {/* Header */}
      <div className="bg-gradient-to-r from-blue-600 to-blue-700 text-white p-4 rounded-t-lg flex justify-between items-center">
        <div className="flex items-center gap-2">
          {/* Bouton retour dashboard (visible sur mobile) */}
          {onBackToDashboard && (
            <button
              onClick={onBackToDashboard}
              className="text-white/80 hover:text-white mr-2 md:hidden"
              title="Retour au dashboard"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
              </svg>
            </button>
          )}
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
          </svg>
          <h3 className="font-semibold">Assistant Gazelle</h3>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setMessages([])}
            className="text-white/80 hover:text-white text-sm"
            title="Effacer l'historique"
          >
            🗑️
          </button>
          <button
            onClick={() => setIsOpen(false)}
            className="text-white/80 hover:text-white"
            title="Fermer"
          >
            ✕
          </button>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3 bg-gray-50">
        {messages.map((msg, idx) => (
          <div
            key={idx}
            className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`max-w-[80%] rounded-lg p-3 ${
                msg.role === 'user'
                  ? 'bg-blue-600 text-white'
                  : msg.error
                  ? 'bg-red-100 text-red-800 border border-red-300'
                  : 'bg-white border border-gray-200 text-gray-800'
              }`}
            >
              {msg.role === 'assistant' && msg.metadata?.clickable_entities && msg.metadata.clickable_entities.length > 0 ? (() => {
                // Dédupliquer aussi côté rendu (sécurité si anciens messages)
                const byNameCity = new Map()
                msg.metadata.clickable_entities.forEach((e) => {
                  if (!e?.name) return
                  const key = `${e.name.trim().toLowerCase()}|${(e.city || '').trim().toLowerCase()}`
                  const existing = byNameCity.get(key)
                  if (!existing || (existing.type !== 'client' && e.type === 'client')) {
                    byNameCity.set(key, e)
                  }
                })
                const unique = Array.from(byNameCity.values())

                // Recomposer le contenu pour n'afficher qu'une fois chaque client/contact
                const header = `🔍 **${unique.length} clients trouvés:**\n\n`
                const list = unique.map((e) => {
                  const city = e.city ? ` (${e.city})` : ''
                  const tag = e.type === 'contact' ? ' [Contact]' : ''
                  return `- **${e.name}**${city}${tag}`
                }).join('\n')
                const safeContent = unique.length > 0 ? `${header}${list}` : msg.content

                return (
                  <ClickableMessage
                    content={safeContent}
                    entities={unique}
                    currentUser={currentUser}
                    onAskQuestion={handleSendMessage}
                    onSelectClient={(entity) => {
                      console.log('Client sélectionné:', entity)
                    }}
                  />
                )
              })() : (
                <div className="text-sm whitespace-pre-wrap">{msg.content}</div>
              )}

              {/* Données structurées pour appointments (clients cliquables) */}
              {msg.structured_data?.appointments && (
                <div className="mt-3 space-y-2">
                  {msg.structured_data.appointments.map((appt, idx) => (
                    <div
                      key={idx}
                      className="p-2 bg-gray-50 rounded border border-gray-200 hover:bg-gray-100 cursor-pointer transition-colors"
                      onClick={() => {
                        if (appt.client_external_id) {
                          // Ouvrir les détails du client
                          handleSendMessage(`cherche client ${appt.client_external_id}`)
                        }
                      }}
                      title={appt.client_external_id ? "Cliquer pour voir les détails du client" : ""}
                    >
                      <div className="flex items-center justify-between">
                        <div>
                          <span className="font-medium text-blue-600 hover:text-blue-800">
                            {appt.client_name}
                          </span>
                          {appt.location && (
                            <span className="text-gray-500 text-xs ml-2">({appt.location})</span>
                          )}
                        </div>
                        <div className="text-xs text-gray-400">
                          {appt.appointment_time}
                        </div>
                      </div>
                      {appt.description && (
                        <div className="text-xs text-gray-600 mt-1">{appt.description}</div>
                      )}
                    </div>
                  ))}
                </div>
              )}

              {/* Métadonnées (query_type, confidence, etc.) */}
              {msg.metadata && (
                <div className="mt-2 pt-2 border-t border-gray-200 text-xs text-gray-500">
                  <div>Type: {msg.metadata.query_type}</div>
                  {msg.metadata.confidence && (
                    <div>Confiance: {(msg.metadata.confidence * 100).toFixed(0)}%</div>
                  )}
                </div>
              )}
            </div>
          </div>
        ))}

        {isLoading && (
          <div className="flex justify-start">
            <div className="bg-white border border-gray-200 rounded-lg p-3">
              <div className="flex items-center gap-2 text-gray-500">
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600"></div>
                <span className="text-sm">Réflexion en cours...</span>
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Suggestions rapides */}
      {messages.length <= 1 && (
        <div className="px-4 py-2 border-t border-gray-200 bg-gray-50">
          <div className="text-xs text-gray-500 mb-2">Suggestions :</div>
          <div className="flex flex-wrap gap-2">
            {getSuggestions().map((suggestion, idx) => (
              <button
                key={idx}
                onClick={() => handleSendMessage(suggestion.text)}
                className="px-3 py-1 text-xs bg-white border border-gray-300 rounded-full hover:bg-blue-50 hover:border-blue-300 transition-colors"
                title={suggestion.description}
              >
                {suggestion.text}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Input */}
      <div className="p-4 border-t border-gray-200 bg-white rounded-b-lg">
        <form onSubmit={(e) => { e.preventDefault(); handleSendMessage(); }} className="flex gap-2">
          <input
            type="text"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            placeholder="Posez votre question..."
            className="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
            disabled={isLoading}
          />
          <button
            type="submit"
            disabled={isLoading || !inputValue.trim()}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors text-sm font-medium"
          >
            Envoyer
          </button>
        </form>
        <div className="mt-2 text-xs text-gray-500 text-center">
          Tapez <code className="bg-gray-100 px-1 rounded">.aide</code> pour voir les commandes
        </div>
      </div>
    </div>
  )
}
