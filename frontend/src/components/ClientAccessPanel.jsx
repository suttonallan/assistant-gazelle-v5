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
// Mots-clés qui déclenchent le mode "action assistant" (RV conjoint, etc.)
// au lieu de la recherche client classique.
const ACTION_KEYWORDS = [
  'rv conjoint', 'rendez-vous conjoint', 'conjoint',
  'accompagn', 'accompagne', 'apprenti',
  'duplique', 'dupliquer', 'duplica',
  'ajoute', 'ajouter', 'mets',
  'fais un rv', 'fais le rv', 'fais un rendez',
  'avec margot', 'avec nicolas', 'avec allan', 'avec jp', 'avec jean-philippe',
]

function isActionRequest(text) {
  if (!text) return false
  const lower = text.toLowerCase().trim()
  // Heuristique : long (>20 chars) OU contient un mot-clé d'action
  if (lower.length > 20 && ACTION_KEYWORDS.some(kw => lower.includes(kw))) return true
  if (ACTION_KEYWORDS.some(kw => lower.includes(kw))) return true
  return false
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
  // États pour le mode "action assistant"
  const [assistantResult, setAssistantResult] = useState(null)
  const [loadingAssistant, setLoadingAssistant] = useState(false)
  const [assistantError, setAssistantError] = useState(null)

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

  // Soumission via Entrée — déclenche l'assistant si c'est une requête d'action
  const handleSubmit = async (e) => {
    if (e) e.preventDefault()
    const text = searchTerm.trim()
    if (!text) return
    if (!isActionRequest(text)) return  // sinon on laisse l'autocomplete gérer

    setLoadingAssistant(true)
    setAssistantResult(null)
    setAssistantError(null)
    setShowSuggestions(false)

    try {
      const resp = await fetch(`${API_URL}/api/assistant/joint-appointment`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: text,
          current_user_first_name: currentUser?.firstName || currentUser?.name?.split(' ')[0] || null,
        }),
      })
      const data = await resp.json()
      if (!resp.ok) {
        setAssistantError(data.detail || `Erreur ${resp.status}`)
      } else {
        setAssistantResult(data)
      }
    } catch (err) {
      setAssistantError(err.message || 'Erreur réseau')
    } finally {
      setLoadingAssistant(false)
    }
  }

  const clearAssistant = () => {
    setAssistantResult(null)
    setAssistantError(null)
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
              {(loadingSuggestions || loadingAssistant) && (
                <div className="absolute right-3 top-1/2 -translate-y-1/2">
                  <div className="animate-spin h-4 w-4 border-2 border-teal-500 border-t-transparent rounded-full"></div>
                </div>
              )}
            </div>
            {isActionRequest(searchTerm) && (
              <button
                type="submit"
                disabled={loadingAssistant}
                className="px-3 py-2 text-sm bg-teal-600 hover:bg-teal-700 text-white rounded-lg transition-colors disabled:opacity-50"
                title="Exécuter la demande"
              >
                ➤
              </button>
            )}
            {(selectedClient || assistantResult || assistantError) && (
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

      {/* Réponse de l'assistant (mode action) */}
      {(assistantResult || assistantError) && (
        <div className="mt-4">
          <div className="text-xs font-semibold text-teal-700 uppercase tracking-wider mb-2">
            🤖 Assistant
          </div>

          {assistantError && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-xl text-sm">
              ⚠️ {assistantError}
            </div>
          )}

          {assistantResult && assistantResult.success && (
            <div className="bg-green-50 border border-green-200 text-green-800 px-4 py-3 rounded-xl text-sm">
              <div className="font-semibold mb-1">✅ RV conjoint créé</div>
              <div className="text-xs space-y-0.5">
                <div>
                  <strong>{assistantResult.companion_tech}</strong> a été ajouté(e) comme accompagnateur(trice) au RV de <strong>{assistantResult.source_tech}</strong> chez <strong>{assistantResult.client_name}</strong> le {assistantResult.date}.
                </div>
                <div className="text-gray-600 mt-1">
                  Event original : <code className="text-xs">{assistantResult.source_event_id}</code>
                </div>
                <div className="text-gray-600">
                  Event clone (PERSONAL, pas de notif client) : <code className="text-xs">{assistantResult.clone_event_id}</code>
                </div>
                {assistantResult.annotation_warning && (
                  <div className="text-yellow-700 mt-1">⚠️ {assistantResult.annotation_warning}</div>
                )}
              </div>
            </div>
          )}

          {assistantResult && !assistantResult.success && (
            <div className="bg-yellow-50 border border-yellow-200 text-yellow-800 px-4 py-3 rounded-xl text-sm">
              <div className="font-semibold mb-1">⚠️ Demande non exécutée</div>
              <div className="text-xs">{assistantResult.error || assistantResult.message}</div>
              {assistantResult.candidates && assistantResult.candidates.length > 0 && (
                <div className="mt-2">
                  <div className="font-semibold text-xs">RV candidats :</div>
                  <ul className="text-xs mt-1 space-y-0.5">
                    {assistantResult.candidates.map(c => (
                      <li key={c.id}>
                        • {c.start?.slice(0,16)} — {c.client || c.title}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}
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
