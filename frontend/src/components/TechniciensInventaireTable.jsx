import React, { useState, useEffect, useRef } from 'react'
import { TECHNICIENS_LISTE } from '../../../config/techniciens.config'

import { API_URL } from '../utils/apiConfig'

// Configuration des techniciens - SOURCE DE VÉRITÉ CENTRALISÉE
const TECHNICIENS = TECHNICIENS_LISTE.map(t => ({
  id: t.gazelleId,
  name: t.abbreviation, // ⭐ Abbréviation pour l'affichage UI (Nick, Allan, JP)
  prenom: t.prenom, // ⭐ Prénom complet pour requêtes API (Nicolas, Allan, Jean-Philippe)
  username: t.username
}))

/**
 * Composant réutilisable pour afficher l'inventaire des techniciens
 * Identique à l'onglet "Inventaire" de l'admin
 */
const TechniciensInventaireTable = ({ currentUser, allowComment = true }) => {
  const [products, setProducts] = useState([])
  const [loading, setLoading] = useState(true)
  const [comment, setComment] = useState('')
  const [updateFeedback, setUpdateFeedback] = useState({})
  const [isMobile, setIsMobile] = useState(window.innerWidth <= 768)
  const updateTimeoutRef = useRef({})

  // Map email addresses to TECHNICIENS usernames
  const getUsernameFromEmail = (email) => {
    const emailToUsername = {
      'asutton@piano-tek.com': 'allan',
      'nlessard@piano-tek.com': 'nicolas',
      'jpreny@gmail.com': 'jeanphilippe'
    }
    return emailToUsername[email?.toLowerCase()] || email?.split('@')[0] || 'test'
  }

  const currentUsername = getUsernameFromEmail(currentUser?.email)
  const currentUserIsAdmin = currentUser?.email === 'asutton@piano-tek.com'

  // Debug: afficher le mapping
  console.log('🔍 DEBUG Colonne Verte:', {
    userEmail: currentUser?.email,
    mappedUsername: currentUsername,
    availableUsernames: TECHNICIENS.map(t => t.username)
  })

  useEffect(() => {
    const handleResize = () => setIsMobile(window.innerWidth <= 768)
    window.addEventListener('resize', handleResize)
    return () => window.removeEventListener('resize', handleResize)
  }, [])

  useEffect(() => {
    loadInventory()
  }, [])

  const loadInventory = async () => {
    try {
      setLoading(true)
      const catalogueRes = await fetch(`${API_URL}/api/inventaire/catalogue`)
      if (!catalogueRes.ok) throw new Error('Erreur chargement catalogue')
      const catalogueData = await catalogueRes.json()

      // Créer le map de produits
      const productsMap = {}
      catalogueData.produits.forEach(prod => {
        const quantities = {}
        TECHNICIENS.forEach(tech => {
          quantities[tech.username] = 0
        })

        productsMap[prod.code_produit] = {
          id: prod.code_produit,
          code_produit: prod.code_produit,
          name: prod.nom,
          category: prod.categorie || 'Sans catégorie',
          variant_label: prod.variant_label,
          display_order: prod.display_order || 0,
          is_active: prod.is_active !== false,
          quantities
        }
      })

      // Mapping pour convertir les noms de techniciens de la DB vers les usernames
      const technicienMapping = {
        'Nicolas': 'nicolas',
        'Nick': 'nicolas',
        'nicolas': 'nicolas',
        'nicolas@example.com': 'nicolas',
        'Allan': 'allan',
        'allan': 'allan',
        'allan@example.com': 'allan',
        'Jean-Philippe': 'jeanphilippe',
        'jeanphilippe': 'jeanphilippe',
        'jeanphilippe@example.com': 'jeanphilippe'
      }

      // Charger les quantités réelles
      const inventaireRes = await fetch(`${API_URL}/api/inventaire/techniciens/all`)
      if (inventaireRes.ok) {
        const inventaireData = await inventaireRes.json()
        inventaireData.inventory?.forEach(item => {
          if (productsMap[item.code_produit]) {
            // Essayer de mapper le nom du technicien
            let techUsername = technicienMapping[item.technicien]

            // Si pas trouvé, essayer avec l'email
            if (!techUsername && item.technicien?.includes('@')) {
              const emailPart = item.technicien.split('@')[0].toLowerCase()
              techUsername = technicienMapping[emailPart] || emailPart
            }

            // Si toujours pas trouvé, utiliser le nom en lowercase
            if (!techUsername) {
              techUsername = item.technicien?.toLowerCase().replace('-', '')
            }

            if (productsMap[item.code_produit].quantities[techUsername] !== undefined) {
              productsMap[item.code_produit].quantities[techUsername] = item.quantite_stock || 0
            }
          }
        })
      }

      setProducts(Object.values(productsMap).filter(p => p.is_active))
    } catch (err) {
      console.error('Erreur chargement inventaire:', err)
    } finally {
      setLoading(false)
    }
  }

  const updateQuantity = async (codeProduit, techUsername, newValue, immediate = false) => {
    const newQty = parseInt(newValue) || 0
    const feedbackKey = codeProduit + techUsername

    // Mise à jour optimiste de l'UI
    setProducts(prev => prev.map(p =>
      p.code_produit === codeProduit
        ? { ...p, quantities: { ...p.quantities, [techUsername]: newQty } }
        : p
    ))

    // Feedback visuel
    setUpdateFeedback(prev => ({ ...prev, [feedbackKey]: true }))
    setTimeout(() => {
      setUpdateFeedback(prev => {
        const newFeedback = { ...prev }
        delete newFeedback[feedbackKey]
        return newFeedback
      })
    }, 500)

    // Debounce: annuler la requête précédente si elle existe
    if (updateTimeoutRef.current[feedbackKey]) {
      clearTimeout(updateTimeoutRef.current[feedbackKey])
    }

    // Si immediate (onBlur), sauvegarder tout de suite
    // Sinon, attendre 500ms après la dernière modification (debounce)
    const saveToDB = async () => {
      try {
        // Utiliser prenom de la config centralisée (jamais abbreviation!)
        const technicienName = TECHNICIENS.find(t => t.username === techUsername)?.prenom || techUsername

        const response = await fetch(`${API_URL}/api/inventaire/stock`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            code_produit: codeProduit,
            technicien: technicienName, // Toujours prenom: "Nicolas", "Allan", "Jean-Philippe"
            quantite_stock: newQty,
            type_transaction: 'ajustement',
            motif: 'Ajustement manuel depuis interface'
          })
        })
        
        if (!response.ok) {
          const errorData = await response.json().catch(() => ({ detail: 'Erreur inconnue' }))
          throw new Error(errorData.detail || `Erreur ${response.status}`)
        }
        
        const result = await response.json()
        console.log('✅ Stock mis à jour:', result)
        
        // IMPORTANT: Recharger l'inventaire après chaque modification réussie
        // pour s'assurer que l'UI reflète l'état réel de la DB
        // Cela évite les problèmes de race condition si l'utilisateur fait plusieurs modifications rapides
        await loadInventory()
      } catch (err) {
        console.error('Erreur sauvegarde:', err)
        // Recharger en cas d'erreur pour restaurer l'état correct
        await loadInventory()
      } finally {
        // Nettoyer la référence du timeout
        delete updateTimeoutRef.current[feedbackKey]
      }
    }

    if (immediate) {
      // Sauvegarder immédiatement (onBlur)
      await saveToDB()
    } else {
      // Debounce: attendre 500ms après la dernière modification
      updateTimeoutRef.current[feedbackKey] = setTimeout(saveToDB, 500)
    }
  }

  const submitComment = async () => {
    if (!comment.trim()) return

    try {
      const response = await fetch(`${API_URL}/api/inventaire/comment`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          text: comment,
          username: currentUser?.name || 'Technicien'
        })
      })
      const result = await response.json()
      if (result.success) {
        alert('✅ Commentaire envoyé au CTO!')
        setComment('')
      } else {
        alert('❌ ' + (result.message || 'Erreur envoi'))
      }
    } catch (err) {
      alert('❌ Erreur envoi commentaire: ' + err.message)
    }
  }

  // Liste triée sans regroupement par catégorie
  const sortedProducts = [...products].sort((a, b) => {
    const orderDiff = (a.display_order || 0) - (b.display_order || 0)
    if (orderDiff !== 0) return orderDiff
    return (a.name || '').localeCompare(b.name || '')
  })

  if (loading) {
    return <div className="p-8 text-center text-gray-500">Chargement...</div>
  }

  return (
    <div>
      {/* Zone commentaire rapide */}
      {allowComment && (
        <div className={`mb-4 bg-blue-50 border border-blue-200 rounded-lg ${isMobile ? 'p-3' : 'p-4'}`}>
          <label className={`block ${isMobile ? 'text-xs' : 'text-sm'} font-medium text-gray-700 mb-2`}>
            💬 Commentaire rapide {!isMobile && '(email au CTO)'}
          </label>
          <div className={`flex ${isMobile ? 'flex-col' : 'flex-row'} gap-2`}>
            <input
              type="text"
              value={comment}
              onChange={(e) => setComment(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && submitComment()}
              placeholder={isMobile ? "Commentaire..." : "Ex: Besoin urgent de coupelles brunes..."}
              className={`flex-1 border rounded ${isMobile ? 'px-2 py-2 text-base' : 'px-3 py-2 text-sm'}`}
            />
            <button
              onClick={submitComment}
              className={`${isMobile ? 'w-full px-4 py-2.5' : 'px-4 py-2'} bg-blue-600 text-white rounded hover:bg-blue-700 font-medium ${isMobile ? 'text-base' : 'text-sm'}`}
            >
              Envoyer
            </button>
          </div>
        </div>
      )}

      {/* Tableau multi-colonnes avec sticky - Optimisé mobile */}
      <div className="bg-white rounded-lg shadow overflow-auto" style={{ maxHeight: isMobile ? '80vh' : '70vh' }}>
        <table className="min-w-full border-collapse">
          <thead className="bg-gray-50 sticky top-0 z-10">
            <tr>
              <th className={`${isMobile ? 'px-2 py-2' : 'px-4 py-3'} text-left text-xs font-medium text-gray-500 uppercase border-b sticky left-0 bg-gray-50 z-20`}>
                Produit
              </th>
              {TECHNICIENS.map(tech => {
                // Abréviations mobiles personnalisées
                const mobileNames = {
                  'Allan': 'Alla',
                  'Jean-Philippe': 'J-Ph',
                  'Nick': 'Nick'
                }

                const isMyColumn = tech.username === currentUsername

                return (
                  <th
                    key={tech.username}
                    className={`${isMobile ? 'px-2 py-2' : 'px-4 py-3'} text-center text-xs font-medium uppercase border-b ${
                      isMyColumn ? 'bg-green-100 text-green-800 font-bold' : 'text-gray-500'
                    }`}
                  >
                    {isMobile ? (mobileNames[tech.name] || tech.name.substring(0, 4)) : tech.name}
                  </th>
                )
              })}
            </tr>
          </thead>
          <tbody>
            {sortedProducts.map(product => (
              <tr key={product.code_produit} className="hover:bg-gray-50 border-b">
                <td className={`${isMobile ? 'px-2 py-2' : 'px-4 py-3'} text-sm text-gray-900 sticky left-0 bg-white border-r font-medium`} style={{ minWidth: isMobile ? '150px' : '200px' }}>
                  <div className={isMobile ? 'text-xs' : 'text-sm'}>
                    {product.name}
                    {product.variant_label && (
                      <span className="text-xs text-gray-500 ml-1">
                        ({product.variant_label})
                      </span>
                    )}
                  </div>
                  {/* Code produit masqué pour tous les utilisateurs */}
                </td>

                {TECHNICIENS.map(tech => {
                  const qty = product.quantities?.[tech.username] || 0
                  const isMyColumn = tech.username === currentUsername
                  const feedbackKey = product.code_produit + tech.username
                  const hasFeedback = updateFeedback[feedbackKey]

                  return (
                    <td
                      key={tech.username}
                      className={`${isMobile ? 'px-1 py-2' : 'px-4 py-3'} text-center ${
                        isMyColumn ? 'bg-green-50' : ''
                      }`}
                    >
                      <input
                        type="number"
                        min="0"
                        value={qty}
                        onChange={(e) => updateQuantity(product.code_produit, tech.username, e.target.value, false)}
                        onBlur={(e) => {
                          // Sauvegarder immédiatement quand l'utilisateur quitte le champ
                          // pour s'assurer que la valeur est bien persistée
                          const newQty = parseInt(e.target.value) || 0
                          updateQuantity(product.code_produit, tech.username, newQty, true)
                        }}
                        onFocus={(e) => e.target.select()}
                        onClick={(e) => e.target.select()}
                        className={`${isMobile ? 'w-14 text-sm' : 'w-20 text-sm'} px-2 py-1 text-center border rounded ${
                          isMyColumn ? 'bg-green-100 border-green-400 font-bold text-green-900' : 'border-gray-300'
                        } ${hasFeedback ? 'bg-green-300' : ''}`}
                        style={hasFeedback ? { transition: 'background-color 0.3s' } : {}}
                      />
                    </td>
                  )
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

export default TechniciensInventaireTable
