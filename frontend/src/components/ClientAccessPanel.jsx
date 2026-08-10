import React, { useState, useRef, useEffect } from 'react'
import { API_URL } from '../utils/apiConfig'
import BriefingCard from './BriefingCard'

/**
 * ClientAccessPanel — Recherche rapide de clients
 *
 * Permet à Louise (ou tout utilisateur autorisé) de chercher
 * n'importe quel client par nom pour consulter sa fiche avant
 * un appel téléphonique ou un e-mail.
 */
// Mots-clés du mode "RV conjoint"
const JOINT_RV_KEYWORDS = [
  'rv conjoint', 'rendez-vous conjoint', 'conjoint',
  'accompagn', 'accompagne', 'apprenti',
  'duplique', 'dupliquer', 'duplica',
  'ajoute', 'ajouter', 'mets',
  'fais un rv', 'fais le rv', 'fais un rendez',
  'avec margot', 'avec nicolas', 'avec allan', 'avec jp', 'avec jean-philippe',
]

// Mots-clés du mode "révision de soumission"
const REVIEW_ESTIMATE_KEYWORDS = [
  'soumission', 'devis', 'estimate',
  'améliore', 'amelior', 'révise', 'revise',
  'analyse', 'corrige', 'critique',
]

// Mots-clés du mode "recherche libre par mot-clé dans events/notes"
// Patterns interrogatifs typiques
const SEARCH_KEYWORD_PATTERNS = [
  'chez quel', 'chez qui',
  'qui a ', 'quel client', 'quels clients', 'quels pianos',
  'retrouve', 'cherche dans', 'cherche-moi',
  'trouve la note', 'trouve le rv', 'trouve les rv',
  'où est-ce que', 'quand a-t-on',
  'récemment fait', 'a été fait',
]

function detectActionType(text) {
  if (!text) return null
  const lower = text.toLowerCase().trim()

  const hasNumber = /#?\d{4,6}/.test(lower)
  const dupVerb = /(duplique|dupliqu|duplica|copie|copi|clone|clonu|inspir)/.test(lower)

  // 0. Duplication de facture / soumission (brouillon) — priorité sur révision/RV
  if (dupVerb && hasNumber && lower.includes('facture')) return 'duplicate_invoice'
  if (dupVerb && hasNumber && (lower.includes('soumission') || lower.includes('devis') || lower.includes('estimate'))) return 'duplicate_estimate'

  // 0b. Création / réactivation d'une soumission à partir d'un numéro existant.
  //     On part d'une COPIE (brouillon) de la soumission source, que l'utilisateur
  //     ajuste ensuite (ex. remettre les prix à jour).
  //     Ex : « fais une nouvelle soumission pour réactiver #11766 avec le prix à jour ».
  //     DOIT passer AVANT la révision : sinon le simple mot « soumission » aiguille la
  //     demande vers review_estimate, qui REFUSE toute création (« pas une révision »).
  const createVerb = /(nouvelle|nouveau|cree|crée|creer|créer|reactiv|réactiv|refais|refait|refaire|repart|prepare|prépare|monte|monter|genere|génère|generer|générer)/.test(lower)
  if (createVerb && hasNumber && (lower.includes('soumission') || lower.includes('devis') || lower.includes('estimate'))) {
    return 'duplicate_estimate'
  }

  // 1. Révision de soumission : doit contenir 'soumission/devis/estimate' OU un verbe d'amélioration + un # ou nom
  const hasReviewVerb = REVIEW_ESTIMATE_KEYWORDS.some(kw => lower.includes(kw))
  if (hasReviewVerb && (lower.includes('soumission') || lower.includes('devis') || lower.includes('estimate') || hasNumber)) {
    return 'review_estimate'
  }

  // 2. Recherche libre par mot-clé : patterns interrogatifs
  if (SEARCH_KEYWORD_PATTERNS.some(p => lower.includes(p))) {
    return 'search_keyword'
  }

  // 3. RV conjoint
  if (JOINT_RV_KEYWORDS.some(kw => lower.includes(kw))) {
    return 'joint_rv'
  }

  // 4. Heuristique de longueur : phrase longue avec un mot d'action
  if (lower.length > 20 && (hasReviewVerb || JOINT_RV_KEYWORDS.some(kw => lower.includes(kw)))) {
    return hasReviewVerb ? 'review_estimate' : 'joint_rv'
  }
  return null
}

function isActionRequest(text) {
  return detectActionType(text) !== null
}

export default function ClientAccessPanel({ currentUser }) {
  const [searchTerm, setSearchTerm] = useState('')
  const [suggestions, setSuggestions] = useState([])
  const [loadingSuggestions, setLoadingSuggestions] = useState(false)
  const [selectedClient, setSelectedClient] = useState(null)
  const [briefing, setBriefing] = useState(null)
  const [loadingBriefing, setLoadingBriefing] = useState(false)
  const [briefingError, setBriefingError] = useState(null)
  const [showSuggestions, setShowSuggestions] = useState(false)
  // États pour le mode "assistant conversationnel" (fil + mémoire)
  const [conversation, setConversation] = useState([])   // [{role:'user'|'assistant', content}]
  const [convInput, setConvInput] = useState('')          // champ de réponse dans le fil
  const [convLoading, setConvLoading] = useState(false)

  const searchRef = useRef(null)
  const debounceRef = useRef(null)

  // Fermer les suggestions si clic en dehors
  useEffect(() => {
    const handleClickOutside = (e) => {
      if (searchRef.current && !searchRef.current.contains(e.target)) {
        setShowSuggestions(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  // Recherche avec debounce
  const handleSearchChange = (value) => {
    setSearchTerm(value)
    if (debounceRef.current) clearTimeout(debounceRef.current)

    // Si l'input ressemble à une requête d'action, on n'autocomplète pas
    if (isActionRequest(value)) {
      setSuggestions([])
      setShowSuggestions(false)
      return
    }

    if (value.trim().length < 2) {
      setSuggestions([])
      setShowSuggestions(false)
      return
    }

    debounceRef.current = setTimeout(async () => {
      setLoadingSuggestions(true)
      try {
        const resp = await fetch(
          `${API_URL}/api/briefing/search-clients?q=${encodeURIComponent(value.trim())}&limit=8`
        )
        if (resp.ok) {
          const data = await resp.json()
          setSuggestions(data.results || [])
          setShowSuggestions(true)
        }
      } catch (err) {
        console.error('Erreur recherche clients:', err)
      } finally {
        setLoadingSuggestions(false)
      }
    }, 300)
  }

  // Envoie un message dans le fil conversationnel (mémoire d'historique côté /converse)
  const sendConversation = async (text) => {
    const history = [...conversation, { role: 'user', content: text }]
    setConversation(history)
    setConvLoading(true)
    try {
      const resp = await fetch(`${API_URL}/api/assistant/converse`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          messages: history.map(m => ({ role: m.role, content: m.content })),
          current_user_first_name: currentUser?.firstName || currentUser?.name?.split(' ')[0] || null,
        }),
      })
      const data = await resp.json()
      const reply = resp.ok
        ? (data.reply || "Désolé, je n'ai pas pu répondre.")
        : (data.detail || `Erreur ${resp.status}`)
      setConversation(prev => [...prev, { role: 'assistant', content: reply }])
    } catch (err) {
      setConversation(prev => [...prev, { role: 'assistant', content: `⚠️ Erreur réseau : ${err.message}` }])
    } finally {
      setConvLoading(false)
    }
  }

  // Soumission via Entrée dans la barre de recherche — démarre le fil si c'est une action
  const handleSubmit = async (e) => {
    if (e) e.preventDefault()
    const text = searchTerm.trim()
    if (!text) return
    if (!detectActionType(text)) return  // sinon on laisse l'autocomplete gérer la recherche client
    setShowSuggestions(false)
    setSearchTerm('')
    sendConversation(text)
  }

  const clearAssistant = () => {
    setConversation([])
    setConvInput('')
    setSearchTerm('')
  }

  // Charger le briefing d'un client sélectionné
  const selectClient = async (client) => {
    setSelectedClient(client)
    setSearchTerm(client.name)
    setShowSuggestions(false)
    setSuggestions([])
    setLoadingBriefing(true)
    setBriefingError(null)
    setBriefing(null)

    try {
      const resp = await fetch(`${API_URL}/api/briefing/client/${client.client_id}`)
      if (!resp.ok) throw new Error(`Erreur ${resp.status}`)
      const data = await resp.json()
      setBriefing(data)
    } catch (err) {
      console.error('Erreur chargement briefing client:', err)
      setBriefingError(err.message)
    } finally {
      setLoadingBriefing(false)
    }
  }

  const clearSelection = () => {
    setSelectedClient(null)
    setBriefing(null)
    setBriefingError(null)
    setSearchTerm('')
    setSuggestions([])
  }

  return (
    <div className="mb-6">
      {/* Barre de recherche / assistant */}
      <div className="bg-gradient-to-r from-teal-50 to-cyan-50 rounded-xl px-4 py-4 border border-teal-200">
        <div className="flex items-center gap-2 mb-3">
          <span className="text-xl">💬</span>
          <div>
            <h3 className="font-semibold text-gray-800 text-sm">Assistant Gazelle</h3>
            <p className="text-xs text-gray-500">
              Cherchez un client par nom, ou tapez une demande (ex: « ajoute Margot au RV de Nicolas demain »)
            </p>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="relative" ref={searchRef}>
          <div className="flex gap-2">
            <div className="relative flex-1">
              <input
                type="text"
                value={searchTerm}
                onChange={(e) => handleSearchChange(e.target.value)}
                onFocus={() => suggestions.length > 0 && setShowSuggestions(true)}
                placeholder="Nom du client OU demande d'action..."
                className="w-full px-4 py-2.5 rounded-lg border border-gray-300 focus:border-teal-500 focus:ring-1 focus:ring-teal-500 text-sm bg-white"
              />
              {(loadingSuggestions || convLoading) && (
                <div className="absolute right-3 top-1/2 -translate-y-1/2">
                  <div className="animate-spin h-4 w-4 border-2 border-teal-500 border-t-transparent rounded-full"></div>
                </div>
              )}
            </div>
            {isActionRequest(searchTerm) && (
              <button
                type="submit"
                disabled={convLoading}
                className="px-3 py-2 text-sm bg-teal-600 hover:bg-teal-700 text-white rounded-lg transition-colors disabled:opacity-50"
                title="Envoyer à l'assistant"
              >
                ➤
              </button>
            )}
            {(selectedClient || conversation.length > 0) && (
              <button
                type="button"
                onClick={() => { clearSelection(); clearAssistant(); }}
                className="px-3 py-2 text-sm bg-gray-200 hover:bg-gray-300 rounded-lg transition-colors text-gray-600"
                title="Effacer"
              >
                ✕
              </button>
            )}
          </div>

          {/* Suggestions dropdown */}
          {showSuggestions && suggestions.length > 0 && (
            <div className="absolute z-50 w-full mt-1 bg-white border border-gray-200 rounded-lg shadow-lg max-h-64 overflow-y-auto">
              {suggestions.map((client) => (
                <button
                  key={client.client_id}
                  onClick={() => selectClient(client)}
                  className="w-full text-left px-4 py-3 hover:bg-teal-50 border-b border-gray-100 last:border-b-0 transition-colors"
                >
                  <div className="font-medium text-gray-800 text-sm">{client.name}</div>
                  <div className="text-xs text-gray-500 flex gap-3 mt-0.5">
                    {client.phone && <span>📱 {client.phone}</span>}
                    {client.city && <span>📍 {client.city}</span>}
                    {client.email && <span>✉️ {client.email}</span>}
                  </div>
                </button>
              ))}
            </div>
          )}

          {/* Aucun résultat */}
          {showSuggestions && suggestions.length === 0 && searchTerm.trim().length >= 2 && !loadingSuggestions && !isActionRequest(searchTerm) && (
            <div className="absolute z-50 w-full mt-1 bg-white border border-gray-200 rounded-lg shadow-lg px-4 py-3 text-sm text-gray-500">
              Aucun client trouvé pour « {searchTerm} »
            </div>
          )}
        </form>
      </div>

      {/* Fil conversationnel avec l'assistant (mémoire + champ de réponse toujours visible) */}
      {conversation.length > 0 && (
        <div className="mt-4">
          <div className="flex items-center justify-between mb-2">
            <div className="text-xs font-semibold text-teal-700 uppercase tracking-wider">
              🤖 Assistant
            </div>
            <button
              type="button"
              onClick={clearAssistant}
              className="text-xs text-gray-400 hover:text-gray-600 transition-colors"
              title="Effacer le fil"
            >
              Effacer le fil ✕
            </button>
          </div>

          <div className="space-y-2">
            {conversation.map((m, idx) => (
              <div key={idx} className={m.role === 'user' ? 'flex justify-end' : 'flex justify-start'}>
                <div
                  className={`px-3 py-2 rounded-2xl text-sm max-w-[85%] whitespace-pre-wrap ${
                    m.role === 'user'
                      ? 'bg-teal-600 text-white rounded-br-sm'
                      : 'bg-white border border-gray-200 text-gray-800 rounded-bl-sm'
                  }`}
                >
                  {m.content}
                </div>
              </div>
            ))}
            {convLoading && (
              <div className="flex justify-start">
                <div className="px-3 py-2 rounded-2xl bg-white border border-gray-200">
                  <div className="animate-spin h-4 w-4 border-2 border-teal-500 border-t-transparent rounded-full"></div>
                </div>
              </div>
            )}
          </div>

          {/* Champ de réponse — toujours visible pour continuer la conversation */}
          <form
            onSubmit={(e) => {
              e.preventDefault()
              const t = convInput.trim()
              if (t && !convLoading) { setConvInput(''); sendConversation(t) }
            }}
            className="mt-3 flex gap-2"
          >
            <input
              type="text"
              value={convInput}
              onChange={(e) => setConvInput(e.target.value)}
              placeholder="Répondre à l'assistant… (ex: « oui, réactive-la avec le prix à jour »)"
              className="flex-1 px-4 py-2.5 rounded-lg border border-gray-300 focus:border-teal-500 focus:ring-1 focus:ring-teal-500 text-sm bg-white"
            />
            <button
              type="submit"
              disabled={convLoading || !convInput.trim()}
              className="px-4 py-2 text-sm bg-teal-600 hover:bg-teal-700 text-white rounded-lg transition-colors disabled:opacity-50"
            >
              Envoyer
            </button>
          </form>
        </div>
      )}

      {/* Fiche client (briefing) */}
      {loadingBriefing && (
        <div className="flex items-center justify-center py-8">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-teal-600"></div>
          <span className="ml-3 text-gray-600 text-sm">Chargement de la fiche client...</span>
        </div>
      )}

      {briefingError && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-xl mt-4 text-sm">
          ⚠️ {briefingError}
        </div>
      )}

      {briefing && !loadingBriefing && (
        <div className="mt-4">
          <div className="flex items-center gap-2 mb-2">
            <span className="text-xs font-semibold text-teal-700 uppercase tracking-wider">
              Fiche client
            </span>
            {selectedClient?.phone && (
              <a
                href={`tel:${selectedClient.phone}`}
                className="text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded-full hover:bg-green-200 transition-colors"
              >
                📞 Appeler
              </a>
            )}
            {selectedClient?.email && (
              <a
                href={`mailto:${selectedClient.email}`}
                className="text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded-full hover:bg-blue-200 transition-colors"
              >
                ✉️ Courriel
              </a>
            )}
          </div>
          <BriefingCard
            briefing={briefing}
            currentUser={currentUser}
          />
        </div>
      )}
    </div>
  )
}
