import React, { useState, useEffect } from 'react'
import { supabase } from '../lib/supabase'

const API_URL = import.meta.env.VITE_API_URL || 'https://assistant-gazelle-v5-api.onrender.com'

/**
 * Outil visuel pour associer les items internes aux items MSL Gazelle
 * Suggère automatiquement des matches basés sur la similarité des noms
 */
const MSLMatchingTool = () => {
  const [suggestions, setSuggestions] = useState([])
  const [loading, setLoading] = useState(true)
  const [processing, setProcessing] = useState(false)
  const [filter, setFilter] = useState('all') // all, high, medium, low

  useEffect(() => {
    loadSuggestions()
  }, [])

  const similarity = (a, b) => {
    const longer = a.length > b.length ? a : b
    const shorter = a.length > b.length ? b : a
    if (longer.length === 0) return 1.0

    const editDistance = (s1, s2) => {
      s1 = s1.toLowerCase()
      s2 = s2.toLowerCase()
      const costs = []
      for (let i = 0; i <= s1.length; i++) {
        let lastValue = i
        for (let j = 0; j <= s2.length; j++) {
          if (i === 0) {
            costs[j] = j
          } else if (j > 0) {
            let newValue = costs[j - 1]
            if (s1.charAt(i - 1) !== s2.charAt(j - 1)) {
              newValue = Math.min(Math.min(newValue, lastValue), costs[j]) + 1
            }
            costs[j - 1] = lastValue
            lastValue = newValue
          }
        }
        if (i > 0) costs[s2.length] = lastValue
      }
      return costs[s2.length]
    }

    return (longer.length - editDistance(longer, shorter)) / longer.length
  }

  const loadSuggestions = async () => {
    try {
      setLoading(true)

      // Charger le catalogue
      const response = await fetch(`${API_URL}/inventaire/catalogue`)
      const data = await response.json()
      const items = data.produits || []

      // Séparer MSL et items internes
      const mslItems = items.filter(i => i.gazelle_product_id)
      const internalItems = items.filter(i => !i.gazelle_product_id && i.is_inventory_item)

      // Générer les suggestions
      const matches = []

      for (const internal of internalItems) {
        if (!internal.nom) continue

        let bestMatch = null
        let bestScore = 0

        for (const msl of mslItems) {
          if (!msl.nom) continue

          const score = similarity(internal.nom, msl.nom)

          if (score > bestScore) {
            bestScore = score
            bestMatch = msl
          }
        }

        if (bestMatch && bestScore >= 0.4) {
          matches.push({
            id: `${internal.code_produit}-${bestMatch.gazelle_product_id}`,
            score: bestScore,
            confidence: bestScore >= 0.8 ? 'high' : bestScore >= 0.6 ? 'medium' : 'low',
            internal,
            msl: bestMatch,
            status: 'pending' // pending, approved, rejected
          })
        }
      }

      // Trier par score décroissant
      matches.sort((a, b) => b.score - a.score)

      setSuggestions(matches)

    } catch (err) {
      console.error('Erreur chargement suggestions:', err)
    } finally {
      setLoading(false)
    }
  }

  const approveMatch = async (suggestion) => {
    try {
      setProcessing(true)

      // Mettre à jour l'item interne avec le gazelle_product_id
      const { error } = await supabase
        .from('produits_catalogue')
        .update({
          gazelle_product_id: suggestion.msl.gazelle_product_id
        })
        .eq('code_produit', suggestion.internal.code_produit)

      if (error) throw error

      // Retirer de la liste
      setSuggestions(suggestions.filter(s => s.id !== suggestion.id))

    } catch (err) {
      alert('Erreur: ' + err.message)
    } finally {
      setProcessing(false)
    }
  }

  const rejectMatch = (suggestion) => {
    // Retirer de la liste
    setSuggestions(suggestions.filter(s => s.id !== suggestion.id))
  }

  const filteredSuggestions = suggestions.filter(s => {
    if (filter === 'all') return true
    return s.confidence === filter
  })

  const stats = {
    total: suggestions.length,
    high: suggestions.filter(s => s.confidence === 'high').length,
    medium: suggestions.filter(s => s.confidence === 'medium').length,
    low: suggestions.filter(s => s.confidence === 'low').length
  }

  if (loading) {
    return (
      <div style={{ padding: '40px', textAlign: 'center', color: '#999' }}>
        Analyse des associations possibles...
      </div>
    )
  }

  return (
    <div style={{ padding: '20px', maxWidth: '1400px', margin: '0 auto' }}>
      {/* Header */}
      <div style={{ marginBottom: '24px' }}>
        <h2 style={{ fontSize: '20px', fontWeight: '400', margin: '0 0 8px 0', color: '#2c3e50' }}>
          🔗 Association Inventaire ↔ MSL Gazelle
        </h2>
        <p style={{ fontSize: '13px', color: '#7f8c8d', margin: 0, fontWeight: '300' }}>
          Suggestions automatiques basées sur la similarité des noms
        </p>
      </div>

      {/* Stats et filtres */}
      <div style={{
        display: 'flex',
        gap: '12px',
        marginBottom: '20px',
        flexWrap: 'wrap',
        alignItems: 'center'
      }}>
        <button
          onClick={() => setFilter('all')}
          style={{
            padding: '8px 16px',
            border: `2px solid ${filter === 'all' ? '#3498db' : '#e0e0e0'}`,
            backgroundColor: filter === 'all' ? '#e3f2fd' : 'white',
            borderRadius: '4px',
            fontSize: '13px',
            cursor: 'pointer',
            fontWeight: filter === 'all' ? '500' : '400'
          }}
        >
          Toutes ({stats.total})
        </button>

        <button
          onClick={() => setFilter('high')}
          style={{
            padding: '8px 16px',
            border: `2px solid ${filter === 'high' ? '#27ae60' : '#e0e0e0'}`,
            backgroundColor: filter === 'high' ? '#e8f5e9' : 'white',
            borderRadius: '4px',
            fontSize: '13px',
            cursor: 'pointer',
            fontWeight: filter === 'high' ? '500' : '400'
          }}
        >
          🟢 Haute confiance ({stats.high})
        </button>

        <button
          onClick={() => setFilter('medium')}
          style={{
            padding: '8px 16px',
            border: `2px solid ${filter === 'medium' ? '#f39c12' : '#e0e0e0'}`,
            backgroundColor: filter === 'medium' ? '#fff3e0' : 'white',
            borderRadius: '4px',
            fontSize: '13px',
            cursor: 'pointer',
            fontWeight: filter === 'medium' ? '500' : '400'
          }}
        >
          🟡 Moyenne ({stats.medium})
        </button>

        <button
          onClick={() => setFilter('low')}
          style={{
            padding: '8px 16px',
            border: `2px solid ${filter === 'low' ? '#e67e22' : '#e0e0e0'}`,
            backgroundColor: filter === 'low' ? '#ffeaa7' : 'white',
            borderRadius: '4px',
            fontSize: '13px',
            cursor: 'pointer',
            fontWeight: filter === 'low' ? '500' : '400'
          }}
        >
          🟠 Faible ({stats.low})
        </button>
      </div>

      {/* Liste des suggestions */}
      {filteredSuggestions.length === 0 ? (
        <div style={{
          padding: '60px',
          textAlign: 'center',
          color: '#95a5a6',
          fontSize: '14px',
          backgroundColor: '#f8f9fa',
          borderRadius: '8px',
          border: '2px dashed #e0e0e0'
        }}>
          {stats.total === 0
            ? '✅ Tous les items internes sont déjà associés!'
            : 'Aucune suggestion dans cette catégorie'
          }
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {filteredSuggestions.map(sugg => {
            const confidenceColor = {
              high: '#27ae60',
              medium: '#f39c12',
              low: '#e67e22'
            }[sugg.confidence]

            const confidenceLabel = {
              high: '🟢 Haute confiance',
              medium: '🟡 Moyenne',
              low: '🟠 Faible'
            }[sugg.confidence]

            return (
              <div
                key={sugg.id}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '20px',
                  padding: '20px',
                  backgroundColor: 'white',
                  border: '1px solid #e0e0e0',
                  borderRadius: '8px',
                  boxShadow: '0 1px 3px rgba(0,0,0,0.05)'
                }}
              >
                {/* Score et confiance */}
                <div style={{
                  minWidth: '120px',
                  textAlign: 'center',
                  borderRight: '1px solid #e0e0e0',
                  paddingRight: '20px'
                }}>
                  <div style={{
                    fontSize: '28px',
                    fontWeight: '300',
                    color: confidenceColor,
                    marginBottom: '4px'
                  }}>
                    {Math.round(sugg.score * 100)}%
                  </div>
                  <div style={{
                    fontSize: '11px',
                    color: '#7f8c8d',
                    textTransform: 'uppercase',
                    letterSpacing: '0.5px'
                  }}>
                    {confidenceLabel}
                  </div>
                </div>

                {/* Items à associer */}
                <div style={{ flex: 1 }}>
                  {/* Item interne */}
                  <div style={{ marginBottom: '12px' }}>
                    <div style={{ fontSize: '11px', color: '#7f8c8d', marginBottom: '4px' }}>
                      📦 INVENTAIRE INTERNE
                    </div>
                    <div style={{ fontSize: '14px', fontWeight: '500', color: '#2c3e50' }}>
                      {sugg.internal.nom}
                    </div>
                    <div style={{ fontSize: '11px', color: '#95a5a6', marginTop: '2px' }}>
                      Code: {sugg.internal.code_produit}
                    </div>
                  </div>

                  {/* Flèche */}
                  <div style={{
                    fontSize: '20px',
                    color: '#bdc3c7',
                    marginBottom: '12px'
                  }}>
                    ↓
                  </div>

                  {/* Item MSL */}
                  <div>
                    <div style={{ fontSize: '11px', color: '#7f8c8d', marginBottom: '4px' }}>
                      🔗 MSL GAZELLE
                    </div>
                    <div style={{ fontSize: '14px', fontWeight: '500', color: '#3498db' }}>
                      {sugg.msl.nom}
                    </div>
                    <div style={{ fontSize: '11px', color: '#95a5a6', marginTop: '2px' }}>
                      ID: {sugg.msl.gazelle_product_id} • Prix: {sugg.msl.prix_unitaire?.toFixed(2) || 0}$
                    </div>
                  </div>
                </div>

                {/* Actions */}
                <div style={{
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '8px',
                  minWidth: '140px'
                }}>
                  <button
                    onClick={() => approveMatch(sugg)}
                    disabled={processing}
                    style={{
                      padding: '10px 16px',
                      backgroundColor: '#27ae60',
                      color: 'white',
                      border: 'none',
                      borderRadius: '4px',
                      fontSize: '13px',
                      fontWeight: '500',
                      cursor: processing ? 'not-allowed' : 'pointer',
                      opacity: processing ? 0.6 : 1,
                      transition: 'all 0.2s'
                    }}
                    onMouseEnter={(e) => {
                      if (!processing) e.target.style.backgroundColor = '#229954'
                    }}
                    onMouseLeave={(e) => {
                      e.target.style.backgroundColor = '#27ae60'
                    }}
                  >
                    ✓ Associer
                  </button>

                  <button
                    onClick={() => rejectMatch(sugg)}
                    disabled={processing}
                    style={{
                      padding: '10px 16px',
                      backgroundColor: 'white',
                      color: '#95a5a6',
                      border: '1px solid #e0e0e0',
                      borderRadius: '4px',
                      fontSize: '13px',
                      fontWeight: '400',
                      cursor: processing ? 'not-allowed' : 'pointer',
                      opacity: processing ? 0.6 : 1,
                      transition: 'all 0.2s'
                    }}
                    onMouseEnter={(e) => {
                      if (!processing) {
                        e.target.style.backgroundColor = '#f8f9fa'
                        e.target.style.color = '#e74c3c'
                      }
                    }}
                    onMouseLeave={(e) => {
                      e.target.style.backgroundColor = 'white'
                      e.target.style.color = '#95a5a6'
                    }}
                  >
                    ✗ Ignorer
                  </button>
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}

export default MSLMatchingTool
