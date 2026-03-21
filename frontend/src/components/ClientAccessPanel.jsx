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
export default function ClientAccessPanel({ currentUser }) {
  const [searchTerm, setSearchTerm] = useState('')
  const [suggestions, setSuggestions] = useState([])
  const [loadingSuggestions, setLoadingSuggestions] = useState(false)
  const [selectedClient, setSelectedClient] = useState(null)
  const [briefing, setBriefing] = useState(null)
  const [loadingBriefing, setLoadingBriefing] = useState(false)
  const [briefingError, setBriefingError] = useState(null)
  const [showSuggestions, setShowSuggestions] = useState(false)

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
      {/* Barre de recherche */}
      <div className="bg-gradient-to-r from-teal-50 to-cyan-50 rounded-xl px-4 py-4 border border-teal-200">
        <div className="flex items-center gap-2 mb-3">
          <span className="text-xl">📞</span>
          <div>
            <h3 className="font-semibold text-gray-800 text-sm">Accès rapide client</h3>
            <p className="text-xs text-gray-500">Cherchez un client avant un appel ou un courriel</p>
          </div>
        </div>

        <div className="relative" ref={searchRef}>
          <div className="flex gap-2">
            <div className="relative flex-1">
              <input
                type="text"
                value={searchTerm}
                onChange={(e) => handleSearchChange(e.target.value)}
                onFocus={() => suggestions.length > 0 && setShowSuggestions(true)}
                placeholder="Nom du client..."
                className="w-full px-4 py-2.5 rounded-lg border border-gray-300 focus:border-teal-500 focus:ring-1 focus:ring-teal-500 text-sm bg-white"
              />
              {loadingSuggestions && (
                <div className="absolute right-3 top-1/2 -translate-y-1/2">
                  <div className="animate-spin h-4 w-4 border-2 border-teal-500 border-t-transparent rounded-full"></div>
                </div>
              )}
            </div>
            {selectedClient && (
              <button
                onClick={clearSelection}
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
          {showSuggestions && suggestions.length === 0 && searchTerm.trim().length >= 2 && !loadingSuggestions && (
            <div className="absolute z-50 w-full mt-1 bg-white border border-gray-200 rounded-lg shadow-lg px-4 py-3 text-sm text-gray-500">
              Aucun client trouvé pour « {searchTerm} »
            </div>
          )}
        </div>
      </div>

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
