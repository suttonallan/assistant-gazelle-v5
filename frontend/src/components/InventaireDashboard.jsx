import React, { useState, useEffect } from 'react'
import ExportButton from './ExportButton'
import { TECHNICIENS_LISTE } from '../../../config/techniciens.config'

import { API_URL } from '../utils/apiConfig'

// Configuration des techniciens - SOURCE DE VÉRITÉ CENTRALISÉE
// IMPORTANT: L'ordre dans ce tableau détermine l'ordre d'affichage des colonnes dans tous les onglets
const TECHNICIENS = TECHNICIENS_LISTE.map(t => ({
  id: t.gazelleId,
  name: t.abbreviation, // ⭐ Utilise l'abbréviation (Nick, Allan, JP)
  username: t.username
}))

const InventaireDashboard = ({ currentUser }) => {
  // États principaux
  const [products, setProducts] = useState([]) // Format V4: produits avec quantities par technicien
  const [transactions, setTransactions] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [activeTab, setActiveTab] = useState('inventaire') // 'inventaire', 'transactions', 'admin'

  // États pour interface technicien
  const [comment, setComment] = useState('')
  const [collapsedCategories, setCollapsedCategories] = useState(new Set())
  const [updateFeedback, setUpdateFeedback] = useState({}) // {productId: true} pour feedback vert

  // États pour admin
  const [catalogueAdmin, setCatalogueAdmin] = useState([])
  const [hasChanges, setHasChanges] = useState(false)
  const [draggedItem, setDraggedItem] = useState(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [editingProduct, setEditingProduct] = useState(null)
  const [showEditModal, setShowEditModal] = useState(false)

  // États pour onglet Types
  const [selectedProducts, setSelectedProducts] = useState(new Set())
  const [lastSelectedIndex, setLastSelectedIndex] = useState(null)
  const [batchType, setBatchType] = useState('produit')
  const [batchCommission, setBatchCommission] = useState(false)

  // États pour onglet Sync Gazelle
  const [gazelleProducts, setGazelleProducts] = useState([])
  const [duplicates, setDuplicates] = useState([])
  const [syncTab, setSyncTab] = useState('duplicates') // 'duplicates', 'import', 'manage'
  const [draggedDuplicate, setDraggedDuplicate] = useState(null)
  const [loadingGazelle, setLoadingGazelle] = useState(false)
  const [selectedGazelleIds, setSelectedGazelleIds] = useState(new Set())
  const [batchCategorie, setBatchCategorie] = useState('Services')
  const [batchGazelleType, setBatchGazelleType] = useState('service')
  const [batchHasCommission, setBatchHasCommission] = useState(false)
  const [batchCommissionRate, setBatchCommissionRate] = useState(0)

  // Détection mobile
  const [isMobile, setIsMobile] = useState(window.innerWidth <= 768)

  useEffect(() => {
    const handleResize = () => setIsMobile(window.innerWidth <= 768)
    window.addEventListener('resize', handleResize)
    return () => window.removeEventListener('resize', handleResize)
  }, [])

  // Charger l'inventaire complet (format V4)
  const loadInventory = async () => {
    try {
      setLoading(true)
      // TODO: Adapter l'endpoint pour retourner le format V4
      // Pour l'instant, on simule avec les données existantes
      const catalogueRes = await fetch(`${API_URL}/inventaire/catalogue`)
      if (!catalogueRes.ok) throw new Error('Erreur chargement catalogue')
      const catalogueData = await catalogueRes.json()

      // Créer le map de produits d'abord
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
          original_name: prod.nom,
          sku: prod.code_produit,
          category: prod.categorie || 'Sans catégorie',
          categorie: prod.categorie,
          variant_group: prod.variant_group,
          variant_label: prod.variant_label,
          prix_unitaire: prod.prix_unitaire,
          has_commission: prod.has_commission,
          commission_rate: prod.commission_rate,
          type_produit: prod.type_produit,
          display_order: prod.display_order || 0,
          is_active: prod.is_active !== false,
          quantities
        }
      })

      // Charger les stocks de chaque technicien SÉQUENTIELLEMENT
      console.log('🔍 === DÉBUT CHARGEMENT INVENTAIRES ===')
      console.log('📋 Ordre TECHNICIENS:', TECHNICIENS.map(t => `${t.name} (${t.username})`).join(', '))

      for (const tech of TECHNICIENS) {
        try {
          console.log(`📦 Chargement pour: ${tech.name} (username: ${tech.username})`)
          const res = await fetch(`${API_URL}/inventaire/stock/${tech.name}`)
          if (res.ok) {
            const invData = await res.json()
            console.log(`✅ Réponse API: technicien="${invData.technicien}", ${invData.inventaire?.length || 0} items`)

            // Prendre les 3 premiers produits comme échantillon
            const sampleItems = (invData.inventaire || []).slice(0, 3)
            sampleItems.forEach(item => {
              console.log(`   → ${item.code_produit}: ${item.quantite_stock} unités - ASSIGNÉ À "${tech.username}"`)
            })

            // Assigner les quantités - TOUJOURS utiliser le username du technicien de la boucle
            // PAS celui retourné par l'API (pour éviter problèmes de casse/format)
            invData.inventaire?.forEach(item => {
              if (productsMap[item.code_produit]) {
                productsMap[item.code_produit].quantities[tech.username] = item.quantite_stock || 0

                // Debug détaillé pour les premiers items
                if (item.code_produit === 'PROD-4' || item.code_produit === 'PROD-33') {
                  console.log(`   🔧 ASSIGNATION: ${item.code_produit} → quantities["${tech.username}"] = ${item.quantite_stock}`)
                }
              }
            })
          }
        } catch (err) {
          console.error(`❌ Erreur chargement inventaire ${tech.name}:`, err)
        }
      }

      console.log('🏁 === FIN CHARGEMENT INVENTAIRES ===')

      // Afficher un échantillon des quantités finales pour PROD-4 et PROD-33
      console.log('📊 Vérification quantités finales:')
      const testProducts = ['PROD-4', 'PROD-33']
      testProducts.forEach(code => {
        const prod = productsMap[code]
        if (prod) {
          console.log(`   ${code}:`)
          console.log(`     Allan (quantities.allan) = ${prod.quantities.allan}`)
          console.log(`     Nick (quantities.nicolas) = ${prod.quantities.nicolas}`)
          console.log(`     Jean-Philippe (quantities.jeanphilippe) = ${prod.quantities.jeanphilippe}`)
        }
      })

      // Convertir en liste et trier UNIQUEMENT par display_order (pas de tri alphabétique)
      const productsList = Object.values(productsMap)
      productsList.sort((a, b) => {
        const orderA = Number(a.display_order) || 999999
        const orderB = Number(b.display_order) || 999999
        return orderA - orderB
      })
      
      
      setProducts(productsList)
      setCatalogueAdmin(productsList)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  // Charger les transactions
  const loadTransactions = async () => {
    try {
      const response = await fetch(`${API_URL}/inventaire/transactions?limit=50`)
      if (!response.ok) throw new Error('Erreur chargement transactions')
      const data = await response.json()
      setTransactions(data.transactions || [])
    } catch (err) {
      console.error('Erreur transactions:', err)
    }
  }

  useEffect(() => {
    loadInventory()
    loadTransactions()
  }, [])

  // Mise à jour de quantité (édition inline)
  const updateQuantity = async (productId, techUsername, newQuantity) => {
    const quantityValue = parseInt(newQuantity) || 0
    
    // Mise à jour optimiste de l'état local (sans recharger la page)
    setProducts(prevProducts => 
      prevProducts.map(p => {
        if (p.code_produit === productId) {
          return {
            ...p,
            quantities: {
              ...p.quantities,
              [techUsername]: quantityValue
            }
          }
        }
        return p
      })
    )

    try {
      const response = await fetch(`${API_URL}/inventaire/stock`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          code_produit: productId,
          technicien: TECHNICIENS.find(t => t.username === techUsername)?.name || 'Allan',
          quantite_stock: quantityValue,
          type_transaction: 'ajustement',
          motif: 'Ajustement manuel'
        })
      })

      if (!response.ok) {
        // En cas d'erreur, recharger pour récupérer l'état correct
        await loadInventory()
        throw new Error('Erreur mise à jour')
      }

      // Feedback visuel vert 1 seconde
      setUpdateFeedback(prev => ({ ...prev, [productId + techUsername]: true }))
      setTimeout(() => {
        setUpdateFeedback(prev => {
          const newFeedback = { ...prev }
          delete newFeedback[productId + techUsername]
          return newFeedback
        })
      }, 1000)

      // Ne PAS recharger l'inventaire - la mise à jour optimiste suffit
    } catch (err) {
      // En cas d'erreur, recharger pour récupérer l'état correct
      await loadInventory()
      alert('Erreur: ' + err.message)
    }
  }

  // Envoyer commentaire rapide (notification Slack)
  const submitComment = async () => {
    if (!comment.trim()) return

    try {
      // TODO: Endpoint pour envoyer notification Slack
      const response = await fetch(`${API_URL}/inventaire/comment`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          text: comment,
          username: currentUser?.name || 'Utilisateur'
        })
      })

      if (!response.ok) throw new Error('Erreur envoi commentaire')

      alert('Commentaire envoyé, Slack a été notifié.')
      setComment('')
    } catch (err) {
      alert('Erreur: ' + err.message)
    }
  }

  // Grouper produits par catégorie (exclut les services de l'inventaire technicien)
  // Liste plate triée par display_order uniquement (pas de groupement par catégorie)
  const getSortedProducts = () => {
    return products
      .filter(p => p.is_active !== false)
      .filter(p => p.type_produit !== 'service') // Exclure les services
      .sort((a, b) => {
        const orderA = Number(a.display_order) || 999999
        const orderB = Number(b.display_order) || 999999
        return orderA - orderB
      })
  }

  // Toggle catégorie collapsed
  const toggleCategory = (category) => {
    setCollapsedCategories(prev => {
      const newSet = new Set(prev)
      if (newSet.has(category)) {
        newSet.delete(category)
      } else {
        newSet.add(category)
      }
      return newSet
    })
  }

  // Drag & Drop (admin)
  const handleDragStart = (e, product) => {
    setDraggedItem(product)
    e.dataTransfer.effectAllowed = 'move'
  }

  const handleDragOver = (e) => {
    e.preventDefault()
    e.dataTransfer.dropEffect = 'move'
  }

  const handleDrop = (e, targetProduct) => {
    e.preventDefault()
    if (!draggedItem || draggedItem.code_produit === targetProduct.code_produit) return

    const draggedIdx = catalogueAdmin.findIndex(p => p.code_produit === draggedItem.code_produit)
    const targetIdx = catalogueAdmin.findIndex(p => p.code_produit === targetProduct.code_produit)

    if (draggedIdx === -1 || targetIdx === -1) return

    const newCatalogue = [...catalogueAdmin]
    const [removed] = newCatalogue.splice(draggedIdx, 1)
    newCatalogue.splice(targetIdx, 0, removed)

    // Recalculer display_order
    newCatalogue.forEach((p, idx) => {
      p.display_order = idx + 1
    })

    setCatalogueAdmin(newCatalogue)
    setHasChanges(true)
    setDraggedItem(null)
  }

  const handleDragEnd = () => {
    setDraggedItem(null)
  }

  // Sauvegarder ordre (admin)
  const saveOrder = async () => {
    try {
      const response = await fetch(`${API_URL}/inventaire/catalogue/batch-order`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          products: catalogueAdmin.map(p => ({
            code_produit: p.code_produit,
            display_order: p.display_order
          }))
        })
      })

      if (!response.ok) throw new Error('Erreur sauvegarde')

      setHasChanges(false)
      await loadInventory()
      alert(`Ordre sauvegardé pour ${catalogueAdmin.length} produits`)
    } catch (err) {
      alert('Erreur: ' + err.message)
    }
  }

  // Filtrer produits (admin)
  const filteredProducts = searchQuery
    ? catalogueAdmin.filter(p =>
        p.name?.toLowerCase().includes(searchQuery.toLowerCase()) ||
        p.code_produit?.toLowerCase().includes(searchQuery.toLowerCase()) ||
        p.category?.toLowerCase().includes(searchQuery.toLowerCase()) ||
        p.variant_group?.toLowerCase().includes(searchQuery.toLowerCase())
      )
    : catalogueAdmin

  if (loading) {
    return (
      <div className="p-8 text-center">
        <div className="text-gray-500">Chargement...</div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="p-8">
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-700">
          Erreur: {error}
        </div>
      </div>
    )
  }

  const sortedProducts = getSortedProducts()
  const currentUserIsAdmin = currentUser?.role === 'admin'

  // Map email addresses to TECHNICIENS usernames
  const getUsernameFromEmail = (email) => {
    const emailToUsername = {
      'asutton@piano-tek.com': 'allan',
      'nlessard@piano-tek.com': 'nicolas',
      'jpreny@gmail.com': 'jeanphilippe'
    }
    return emailToUsername[email?.toLowerCase()] || email?.split('@')[0] || 'allan'
  }

  const currentUsername = getUsernameFromEmail(currentUser?.email)

  // Debug: afficher le mapping
  console.log('🟢 DEBUG InventaireDashboard - Colonne Verte:', {
    userEmail: currentUser?.email,
    userName: currentUser?.name,
    mappedUsername: currentUsername,
    isAdmin: currentUserIsAdmin,
    availableUsernames: TECHNICIENS.map(t => t.username)
  })

  return (
    <div className="max-w-7xl mx-auto px-4 py-6">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold text-gray-800">📦 Inventaire</h1>
        <div className="text-sm text-gray-600">
          {currentUser?.name || 'Utilisateur'}
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 mb-6 border-b border-gray-200">
        <button
          onClick={() => setActiveTab('inventaire')}
          className={`px-4 py-2 font-medium ${
            activeTab === 'inventaire'
              ? 'border-b-2 border-blue-500 text-blue-600'
              : 'text-gray-600 hover:text-gray-800'
          }`}
        >
          Inventaire
        </button>
        {currentUserIsAdmin && (
          <>
            <button
              onClick={() => setActiveTab('transactions')}
              className={`px-4 py-2 font-medium ${
                activeTab === 'transactions'
                  ? 'border-b-2 border-blue-500 text-blue-600'
                  : 'text-gray-600 hover:text-gray-800'
              }`}
            >
              Transactions
            </button>
            <button
              onClick={() => {
                setActiveTab('sync')
              }}
              className={`px-4 py-2 font-medium ${
                activeTab === 'sync'
                  ? 'border-b-2 border-blue-500 text-blue-600'
                  : 'text-gray-600 hover:text-gray-800'
              }`}
            >
              🔄 Sync Gazelle
            </button>
            <button
              onClick={() => {
                setActiveTab('admin')
                setCatalogueAdmin([...products])
                setSelectedProducts(new Set())
                setLastSelectedIndex(null)
              }}
              className={`px-4 py-2 font-medium ${
                activeTab === 'admin'
                  ? 'border-b-2 border-blue-500 text-blue-600'
                  : 'text-gray-600 hover:text-gray-800'
              }`}
            >
              Admin
            </button>
          </>
        )}
      </div>

      {/* ONGLET INVENTAIRE (UI Technicien V4) */}
      {activeTab === 'inventaire' && (
        <div>
          {/* Zone commentaire rapide */}
          <div className={`mb-4 bg-blue-50 border border-blue-200 rounded-lg ${isMobile ? 'p-3' : 'p-4'}`}>
            <label className={`block ${isMobile ? 'text-xs' : 'text-sm'} font-medium text-gray-700 mb-2`}>
              💬 Commentaire rapide {!isMobile && '(notifie le CTO via Slack)'}
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

          {/* Tableau multi-colonnes avec sticky - Optimisé mobile */}
          <div className="bg-white rounded-lg shadow overflow-auto" style={{ maxHeight: isMobile ? '80vh' : '70vh' }}>
            <table className="min-w-full border-collapse">
              <thead className="bg-gray-50 sticky top-0 z-10">
                <tr>
                  <th className={`${isMobile ? 'px-2 py-2' : 'px-4 py-3'} text-left text-xs font-medium text-gray-500 uppercase border-b sticky left-0 bg-gray-50 z-20`}>
                    Produit
                  </th>
                  {TECHNICIENS.map(tech => {
                    // Filtre mobile: affiche uniquement colonne utilisateur
                    if (isMobile && !currentUserIsAdmin && tech.username !== currentUsername) {
                      return null
                    }
                    return (
                      <th
                        key={tech.username}
                        className={`${isMobile ? 'px-2 py-2' : 'px-4 py-3'} text-center text-xs font-medium text-gray-500 uppercase border-b`}
                      >
                        {isMobile ? tech.name.substring(0, 4) : tech.name}
                      </th>
                    )
                  })}
                </tr>
              </thead>
              <tbody>
                {/* Liste plate sans catégories, triée par display_order */}
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
                          <div className="text-xs text-gray-400">
                            {product.code_produit}
                          </div>
                        </td>

                        {TECHNICIENS.map(tech => {
                          // Filtre mobile
                          if (isMobile && !currentUserIsAdmin && tech.username !== currentUsername) {
                            return null
                          }

                          const qty = product.quantities?.[tech.username] || 0
                          const isMyColumn = tech.username === currentUsername
                          const feedbackKey = product.code_produit + tech.username
                          const hasFeedback = updateFeedback[feedbackKey]

                          return (
                            <td
                              key={tech.username}
                              className={`${isMobile ? 'px-2 py-2' : 'px-4 py-3'} text-center`}
                            >
                              <input
                                type="number"
                                min="0"
                                value={qty}
                                onChange={(e) => updateQuantity(product.code_produit, tech.username, e.target.value)}
                                onFocus={(e) => e.target.select()}
                                onClick={(e) => e.target.select()}
                                className={`${isMobile ? 'w-16 text-base' : 'w-20 text-sm'} px-2 py-1 text-center border rounded ${
                                  isMyColumn ? 'bg-green-50 border-green-300 font-bold' : 'border-gray-300'
                                } ${hasFeedback ? 'bg-green-200' : ''}`}
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
      )}

      {/* ONGLET TRANSACTIONS */}
      {activeTab === 'transactions' && (
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Date</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Produit</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Technicien</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Type</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Quantité</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Motif</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {transactions.map((tx) => (
                <tr key={tx.id}>
                  <td className="px-4 py-3 text-sm text-gray-700">
                    {new Date(tx.created_at).toLocaleDateString('fr-CA')}
                  </td>
                  <td className="px-4 py-3 text-sm font-medium text-gray-900">{tx.code_produit}</td>
                  <td className="px-4 py-3 text-sm text-gray-700">{tx.technicien}</td>
                  <td className="px-4 py-3 text-sm">
                    <span className={`px-2 py-1 rounded text-xs ${
                      tx.type_transaction === 'ajout' ? 'bg-green-100 text-green-700' :
                      tx.type_transaction === 'retrait' ? 'bg-red-100 text-red-700' :
                      'bg-blue-100 text-blue-700'
                    }`}>
                      {tx.type_transaction}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-700 font-medium">
                    {tx.quantite > 0 ? '+' : ''}{tx.quantite}
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-700">{tx.motif || '-'}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {transactions.length === 0 && (
            <div className="p-8 text-center text-gray-500">Aucune transaction</div>
          )}
        </div>
      )}


      {/* ONGLET ADMIN (UI Admin V4) - Fusionné avec Types */}
      {activeTab === 'admin' && currentUserIsAdmin && (
        <div>
          {/* Barre d'actions batch (Types et Commissions) */}
          {selectedProducts.size > 0 && (
            <div className="mb-4 p-4 bg-gray-50 border border-gray-200 rounded-lg">
              <div className="flex gap-4 items-center flex-wrap">
                <div className="flex items-center gap-2">
                  <label className="text-sm font-medium text-gray-700">Type:</label>
                  <select
                    value={batchType}
                    onChange={(e) => {
                      setBatchType(e.target.value)
                      if (e.target.value === 'fourniture') {
                        setBatchCommission(false)
                      }
                    }}
                    className="border rounded px-3 py-2 text-sm"
                  >
                    <option value="produit">Produit</option>
                    <option value="service">Service</option>
                    <option value="fourniture">Fourniture</option>
                  </select>
                </div>

                <div className="flex items-center gap-2">
                  <label className="flex items-center gap-2 text-sm">
                    <input
                      type="checkbox"
                      checked={batchCommission}
                      onChange={(e) => setBatchCommission(e.target.checked)}
                      disabled={batchType === 'fourniture'}
                      className="w-4 h-4"
                    />
                    <span className={batchType === 'fourniture' ? 'text-gray-400' : 'text-gray-700'}>
                      Commissionnable (10%)
                    </span>
                  </label>
                </div>

                <button
                  onClick={async () => {
                    if (selectedProducts.size === 0) {
                      alert('Sélectionnez au moins un produit')
                      return
                    }

                    try {
                      const response = await fetch(`${API_URL}/inventaire/catalogue/batch-type-commission`, {
                        method: 'PATCH',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                          codes_produit: Array.from(selectedProducts),
                          type_produit: batchType,
                          has_commission: batchCommission
                        })
                      })

                      if (!response.ok) throw new Error('Erreur mise à jour')

                      const result = await response.json()
                      alert(result.message)

                      await loadInventory()
                      setSelectedProducts(new Set())
                      setLastSelectedIndex(null)
                    } catch (err) {
                      alert('Erreur: ' + err.message)
                    }
                  }}
                  disabled={selectedProducts.size === 0}
                  className={`px-4 py-2 rounded font-medium ${
                    selectedProducts.size > 0
                      ? 'bg-blue-600 text-white hover:bg-blue-700'
                      : 'bg-gray-300 text-gray-500 cursor-not-allowed'
                  }`}
                >
                  Appliquer à {selectedProducts.size} produit{selectedProducts.size > 1 ? 's' : ''}
                </button>
              </div>
            </div>
          )}

          {/* Toolbar */}
          <div className="mb-4 flex justify-between items-center flex-wrap gap-4">
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Rechercher: nom, code, catégorie, variante..."
              className="border rounded px-3 py-2 text-sm w-80"
            />

            <div className="flex gap-2">
              <ExportButton
                data={catalogueAdmin}
                filename="catalogue_admin"
              />
              <button
                onClick={saveOrder}
                className={`px-4 py-2 rounded font-medium ${
                  hasChanges
                    ? 'bg-blue-600 text-white hover:bg-blue-700'
                    : 'bg-gray-300 text-gray-600 cursor-not-allowed'
                }`}
                disabled={!hasChanges}
              >
                💾 Sauvegarder l'ordre
              </button>
            </div>
          </div>

          {/* Tableau admin avec drag&drop */}
          <div className="bg-white rounded-lg shadow overflow-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-center">
                    <input
                      type="checkbox"
                      checked={selectedProducts.size === filteredProducts.length && filteredProducts.length > 0}
                      onChange={(e) => {
                        if (e.target.checked) {
                          setSelectedProducts(new Set(filteredProducts.map(p => p.code_produit)))
                        } else {
                          setSelectedProducts(new Set())
                        }
                        setLastSelectedIndex(null)
                      }}
                      className="w-4 h-4"
                      title="Sélectionner tous les produits"
                    />
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Ordre</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Code</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Nom</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Catégorie</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Type</th>
                  <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">Commission</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Variante</th>
                  {TECHNICIENS.map(tech => (
                    <th key={tech.username} className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                      {tech.name}
                    </th>
                  ))}
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Actions</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {(() => {
                  // Créer liste triée une seule fois pour cohérence Shift+Clic
                  const sortedProducts = [...filteredProducts].sort((a, b) => (a.display_order || 0) - (b.display_order || 0))
                  return sortedProducts.map((product, index) => {
                    const isSelected = selectedProducts.has(product.code_produit)
                    const typeLabel = product.type_produit || '(non défini)'
                    const hasCommission = product.has_commission || false
                    
                    return (
                  <tr
                    key={product.code_produit}
                    draggable
                    onDragStart={(e) => handleDragStart(e, product)}
                    onDragOver={handleDragOver}
                    onDrop={(e) => handleDrop(e, product)}
                    onDragEnd={handleDragEnd}
                    className={`hover:bg-gray-50 cursor-move ${
                      draggedItem?.code_produit === product.code_produit ? 'opacity-50' : ''
                    } ${!product.is_active ? 'bg-gray-100 line-through text-gray-400' : ''} ${isSelected ? 'bg-blue-50' : ''}`}
                  >
                    <td className="px-4 py-3 text-center">
                      <input
                        type="checkbox"
                        checked={isSelected}
                        onMouseDown={(e) => {
                          // CRITICAL FIX: onMouseDown capture shiftKey correctement (onChange ne fonctionne pas)
                          e.preventDefault()
                          e.stopPropagation()

                          const shiftPressed = e.shiftKey
                          const newSelected = new Set(selectedProducts)

                          console.log('[Inventaire] Checkbox mousedown - shiftKey:', shiftPressed)

                          // Shift+Click : sélection range (TOUJOURS cocher, jamais décocher)
                          if (shiftPressed && lastSelectedIndex !== null) {
                            // Utiliser sortedProducts du scope parent (déjà trié)
                            const start = Math.min(lastSelectedIndex, index)
                            const end = Math.max(lastSelectedIndex, index)

                            console.log('[Shift+Click] Range selection:', {
                              lastIndex: lastSelectedIndex,
                              currentIndex: index,
                              start,
                              end,
                              rangeSize: end - start + 1
                            })

                            // Comportement standard: Shift+Clic = COCHER tous les éléments du range
                            for (let i = start; i <= end; i++) {
                              newSelected.add(sortedProducts[i].code_produit)
                              console.log(`  → Adding ${i}: ${sortedProducts[i].code_produit}`)
                            }

                            console.log('[Shift+Click] Total selected after range:', newSelected.size)
                          } else {
                            // Clic simple : toggle
                            if (newSelected.has(product.code_produit)) {
                              newSelected.delete(product.code_produit)
                              console.log('[Click] Removed:', product.code_produit)
                            } else {
                              newSelected.add(product.code_produit)
                              console.log('[Click] Added:', product.code_produit)
                            }
                          }

                          setSelectedProducts(newSelected)
                          setLastSelectedIndex(index)
                        }}
                        onChange={() => {}}
                        className="w-4 h-4"
                        data-version="v2-shift-fix"
                      />
                    </td>
                    <td className="px-4 py-3 text-sm">
                      <div className="flex items-center gap-2">
                        <input
                          type="number"
                          value={product.display_order || 0}
                          onChange={(e) => {
                            const newOrder = parseInt(e.target.value) || 0
                            const updated = catalogueAdmin.map(p =>
                              p.code_produit === product.code_produit
                                ? { ...p, display_order: newOrder }
                                : p
                            )
                            setCatalogueAdmin(updated)
                            setHasChanges(true)
                          }}
                          className={`w-20 border-2 rounded px-3 py-1 text-sm font-medium ${
                            searchQuery
                              ? 'border-blue-500 bg-blue-50 text-blue-900'
                              : 'border-gray-300'
                          }`}
                          title="Modifier la position - Cliquez pour changer l'ordre d'affichage"
                          placeholder="Position"
                        />
                        <div className="flex flex-col">
                          <button
                            onClick={() => {
                              if (index === 0) return
                              const updated = [...catalogueAdmin]
                              const temp = updated[index - 1].display_order
                              updated[index - 1].display_order = updated[index].display_order
                              updated[index].display_order = temp
                              setCatalogueAdmin(updated)
                              setHasChanges(true)
                            }}
                            disabled={index === 0}
                            className="text-gray-600 hover:text-blue-600 disabled:text-gray-300 text-xs"
                          >
                            ▲
                          </button>
                          <button
                            onClick={() => {
                              if (index === filteredProducts.length - 1) return
                              const updated = [...catalogueAdmin]
                              const temp = updated[index + 1].display_order
                              updated[index + 1].display_order = updated[index].display_order
                              updated[index].display_order = temp
                              setCatalogueAdmin(updated)
                              setHasChanges(true)
                            }}
                            disabled={index === filteredProducts.length - 1}
                            className="text-gray-600 hover:text-blue-600 disabled:text-gray-300 text-xs"
                          >
                            ▼
                          </button>
                        </div>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-sm font-medium text-gray-900">{product.code_produit}</td>
                    <td className="px-4 py-3 text-sm text-gray-700">{product.name}</td>
                    <td className="px-4 py-3 text-sm text-gray-700">{product.category}</td>
                    <td className="px-4 py-3 text-sm">
                      <span className={`px-2 py-1 rounded text-xs ${
                        !product.type_produit ? 'bg-gray-100 text-gray-500 italic' :
                        product.type_produit === 'service' ? 'bg-purple-100 text-purple-700' :
                        product.type_produit === 'fourniture' ? 'bg-orange-100 text-orange-700' :
                        'bg-green-100 text-green-700'
                      }`}>
                        {typeLabel}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-center text-sm">
                      {product.type_produit === 'fourniture' ? (
                        <span className="text-gray-400 text-xs">- (bloqué)</span>
                      ) : hasCommission ? (
                        <span className="text-green-600 font-medium">✅ 10%</span>
                      ) : (
                        <span className="text-gray-400">❌</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-700">
                      {product.variant_group && (
                        <div>
                          <strong>{product.variant_group}</strong>
                          {product.variant_label && ` (${product.variant_label})`}
                        </div>
                      )}
                    </td>
                    {TECHNICIENS.map(tech => {
                      const qty = product.quantities?.[tech.username] || 0
                      const feedbackKey = product.code_produit + tech.username
                      const hasFeedback = updateFeedback[feedbackKey]
                      
                      return (
                        <td key={tech.username} className="px-4 py-3 text-sm text-center">
                          <input
                            type="number"
                            min="0"
                            value={qty}
                            onChange={(e) => updateQuantity(product.code_produit, tech.username, e.target.value)}
                            onFocus={(e) => e.target.select()}
                            onClick={(e) => e.target.select()}
                            className={`w-20 px-2 py-1 text-center border rounded text-sm ${
                              hasFeedback ? 'bg-green-200 border-green-400' : 'border-gray-300'
                            }`}
                            style={hasFeedback ? { transition: 'background-color 0.3s' } : {}}
                          />
                        </td>
                      )
                    })}
                    <td className="px-4 py-3 text-sm">
                      <div className="flex gap-2">
                        <button
                          onClick={() => {
                            setEditingProduct({...product})
                            setShowEditModal(true)
                          }}
                          className="text-blue-600 hover:text-blue-800 font-medium text-xs"
                          title="Modifier le produit"
                        >
                          ✏️
                        </button>
                        <button
                          onClick={async () => {
                            try {
                              const response = await fetch(`${API_URL}/inventaire/catalogue/${product.code_produit}`, {
                                method: 'PUT',
                                headers: { 'Content-Type': 'application/json' },
                                body: JSON.stringify({
                                  is_active: !product.is_active
                                })
                              })
                              if (!response.ok) {
                                const errorData = await response.json().catch(() => ({ detail: 'Erreur inconnue' }))
                                throw new Error(errorData.detail || 'Erreur toggle')
                              }
                              await loadInventory()
                            } catch (err) {
                              alert('Erreur: ' + err.message)
                            }
                          }}
                          className={`font-medium text-xs ${
                            product.is_active ? 'text-orange-600 hover:text-orange-800' : 'text-green-600 hover:text-green-800'
                          }`}
                          title={product.is_active ? 'Masquer de l\'inventaire technicien (reste visible en Admin)' : 'Afficher dans l\'inventaire technicien'}
                        >
                          {product.is_active ? '🚫' : '✅'}
                        </button>
                        <button
                          onClick={async () => {
                            const isActive = product.is_active !== false
                            const newStatus = !isActive

                            if (!window.confirm(
                              isActive
                                ? `📦 Archiver "${product.name}" (${product.code_produit}) ?\n\nLe produit sera masqué de l'inventaire mais les données seront conservées.`
                                : `✅ Réactiver "${product.name}" (${product.code_produit}) ?\n\nLe produit redeviendra visible dans l'inventaire.`
                            )) {
                              return
                            }

                            try {
                              const response = await fetch(`${API_URL}/inventaire/catalogue`, {
                                method: 'POST',
                                headers: { 'Content-Type': 'application/json' },
                                body: JSON.stringify({
                                  code_produit: product.code_produit,
                                  is_active: newStatus
                                })
                              })

                              if (!response.ok) {
                                throw new Error('Erreur mise à jour statut')
                              }

                              alert(newStatus ? '✅ Produit réactivé' : '📦 Produit archivé')
                              await loadInventory()
                            } catch (err) {
                              alert('Erreur: ' + err.message)
                            }
                          }}
                          className={`font-medium text-lg ${
                            product.is_active !== false
                              ? 'text-red-600 hover:text-red-800'
                              : 'text-green-600 hover:text-green-800'
                          }`}
                          title={product.is_active !== false ? 'Archiver (masquer)' : 'Réactiver'}
                        >
                          {product.is_active !== false ? '🔴' : '✅'}
                        </button>
                      </div>
                    </td>
                  </tr>
                    )
                  })
                })()}
              </tbody>
            </table>
            {filteredProducts.length === 0 && (
              <div className="p-8 text-center text-gray-500">Aucun produit trouvé</div>
            )}
          </div>
        </div>
      )}

      {/* ONGLET SYNC GAZELLE (Mapping et fusion) */}
      {activeTab === 'sync' && currentUserIsAdmin && (
        <div>
          <div className="mb-6">
            <h2 className="text-2xl font-bold text-gray-800 mb-2">🔄 Synchronisation Gazelle</h2>
            <p className="text-sm text-gray-600">
              Associez vos produits locaux avec Gazelle Master Service Items et synchronisez les prix
            </p>
          </div>

          {/* Sub-tabs */}
          <div className="flex gap-2 mb-6 border-b border-gray-200">
            <button
              onClick={() => setSyncTab('duplicates')}
              className={`px-4 py-2 font-medium ${
                syncTab === 'duplicates'
                  ? 'border-b-2 border-purple-500 text-purple-600'
                  : 'text-gray-600 hover:text-gray-800'
              }`}
            >
              🔍 Doublons suggérés
            </button>
            <button
              onClick={() => setSyncTab('import')}
              className={`px-4 py-2 font-medium ${
                syncTab === 'import'
                  ? 'border-b-2 border-purple-500 text-purple-600'
                  : 'text-gray-600 hover:text-gray-800'
              }`}
            >
              📥 Catalogue Gazelle
            </button>
          </div>

          {/* Sub-tab: Doublons suggérés avec drag & drop */}
          {syncTab === 'duplicates' && (
            <div>
              <div className="mb-4 flex gap-3 flex-wrap">
                <button
                  onClick={async () => {
                    try {
                      setLoadingGazelle(true)
                      // Utiliser le endpoint optimisé qui ne synchronise que si nécessaire
                      const response = await fetch(`${API_URL}/inventaire/catalogue/sync-gazelle-smart?force=false&max_age_hours=24`, { method: 'POST' })
                      if (!response.ok) {
                        const errorData = await response.json().catch(() => ({ detail: 'Erreur inconnue' }))
                        throw new Error(errorData.detail || `Erreur ${response.status}`)
                      }
                      const data = await response.json()
                      alert(
                        `🔄 Synchronisation intelligente terminée!\n\n` +
                        `✅ ${data.updated} produits mis à jour\n` +
                        `⏭️ ${data.skipped || 0} produits déjà à jour (synchronisation non nécessaire)\n` +
                        `📦 ${data.total} produits associés à Gazelle\n` +
                        (data.errors ? `\n⚠️ ${data.errors.length} erreurs` : '')
                      )
                      await loadInventory()
                    } catch (err) {
                      alert('❌ Erreur: ' + err.message)
                    } finally {
                      setLoadingGazelle(false)
                    }
                  }}
                  disabled={loadingGazelle}
                  className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 font-semibold shadow-md"
                >
                  {loadingGazelle ? '⏳ Synchronisation...' : '🔄 Sync auto (produits déjà associés)'}
                </button>
                <button
                  onClick={async () => {
                    if (!confirm('⚠️ Importer TOUS les items du Master Service List (MSL) ?\n\nCela va créer/mettre à jour tous les produits dans le catalogue local.\nNécessaire pour le calcul des commissions et la mise à jour automatique.')) {
                      return
                    }
                    try {
                      setLoadingGazelle(true)
                      const response = await fetch(`${API_URL}/inventaire/catalogue/import-all-msl`, { method: 'POST' })
                      if (!response.ok) {
                        const errorData = await response.json().catch(() => ({ detail: 'Erreur inconnue' }))
                        throw new Error(errorData.detail || `Erreur ${response.status}`)
                      }
                      const data = await response.json()
                      alert(
                        `📥 Import MSL terminé!\n\n` +
                        `✨ ${data.created} nouveaux produits créés\n` +
                        `🔄 ${data.updated} produits mis à jour\n` +
                        `📦 ${data.total_msl} items dans le MSL\n` +
                        (data.errors ? `\n⚠️ ${data.errors.length} erreurs` : '')
                      )
                      await loadInventory()
                    } catch (err) {
                      alert('❌ Erreur: ' + err.message)
                    } finally {
                      setLoadingGazelle(false)
                    }
                  }}
                  disabled={loadingGazelle}
                  className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 font-semibold shadow-md"
                >
                  {loadingGazelle ? '⏳ Import...' : '📥 Importer tous les items MSL'}
                </button>
                <button
                  onClick={async () => {
                    try {
                      setLoadingGazelle(true)
                      const response = await fetch(`${API_URL}/inventaire/gazelle/find-duplicates?threshold=0.75`)
                      
                      if (!response.ok) {
                        const errorData = await response.json().catch(() => ({ detail: 'Erreur inconnue' }))
                        throw new Error(errorData.detail || `Erreur ${response.status}`)
                      }
                      
                      const data = await response.json()
                      const duplicatesList = data.duplicates || []
                      const count = data.count !== undefined ? data.count : duplicatesList.length
                      const gazelleAvailable = data.gazelle_available || false
                      
                      setDuplicates(duplicatesList)
                      
                      let message = ''
                      if (count > 0) {
                        message = `✅ ${count} doublon${count > 1 ? 's' : ''} potentiel${count > 1 ? 's' : ''} détecté${count > 1 ? 's' : ''}`
                        if (!gazelleAvailable) {
                          message += '\n(Comparaison uniquement dans le catalogue local - Gazelle non configuré)'
                        }
                      } else {
                        message = 'ℹ️ Aucun doublon détecté avec un seuil de similarité de 75%'
                        if (!gazelleAvailable) {
                          message += '\n(Comparaison uniquement dans le catalogue local - Gazelle non configuré)'
                        }
                      }
                      alert(message)
                    } catch (err) {
                      alert('Erreur: ' + err.message)
                    } finally {
                      setLoadingGazelle(false)
                    }
                  }}
                  disabled={loadingGazelle}
                  className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50"
                >
                  {loadingGazelle ? '⏳ Analyse...' : '🔍 Détecter nouveaux doublons'}
                </button>
                <span className="text-sm text-gray-600 self-center">
                  {duplicates.length > 0 && `${duplicates.length} doublons trouvés`}
                </span>
              </div>

              {duplicates.length === 0 ? (
                <div className="text-center py-12 text-gray-500">
                  Cliquez sur "Détecter les doublons" pour trouver les produits similaires entre votre catalogue et Gazelle
                </div>
              ) : (
                <div className="space-y-4">
                  <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-4">
                    <p className="text-sm text-blue-800">
                      💡 <strong>Glissez-déposez</strong> un produit Gazelle (violet) sur un produit local (bleu) pour les fusionner
                    </p>
                  </div>

                  {duplicates.map((dup, idx) => {
                    // Vérifier que c'est bien un doublon Gazelle (pas local-local)
                    if (!dup.gazelle_id) return null

                    return (
                    <div key={idx} className="border border-gray-300 rounded-lg p-4 bg-white">
                      <div className="grid grid-cols-2 gap-4">
                        {/* Produit LOCAL (drop zone) */}
                        <div
                          className="border-2 border-blue-300 bg-blue-50 rounded p-3 relative"
                          onDragOver={(e) => e.preventDefault()}
                          onDrop={async (e) => {
                            e.preventDefault()
                            if (draggedDuplicate && draggedDuplicate.gazelle_id) {
                              try {
                                const response = await fetch(`${API_URL}/inventaire/catalogue/map-gazelle`, {
                                  method: 'POST',
                                  headers: { 'Content-Type': 'application/json' },
                                  body: JSON.stringify({
                                    code_produit: dup.local_code,
                                    gazelle_product_id: draggedDuplicate.gazelle_id,
                                    update_prices: true
                                  })
                                })
                                if (!response.ok) throw new Error('Erreur association')

                                // Pas d'alert, juste supprimer de la liste
                                setDuplicates(duplicates.filter((_, i) => i !== idx))
                                await loadInventory()
                              } catch (err) {
                                alert('❌ Erreur: ' + err.message)
                              }
                              setDraggedDuplicate(null)
                            }
                          }}
                        >
                          <div className="flex items-center gap-2 mb-2">
                            <span className="px-2 py-1 bg-blue-600 text-white text-xs font-bold rounded">LOCAL</span>
                            <span className="font-mono text-xs text-gray-600">{dup.local_code}</span>
                          </div>
                          <p className="font-semibold text-gray-800 mb-1">{dup.local_nom}</p>
                          <p className="text-xs text-gray-600">Prix: {(dup.local_price || 0).toFixed(2)}$</p>
                        </div>

                        {/* Produit GAZELLE (draggable) */}
                        <div
                          draggable
                          onDragStart={() => setDraggedDuplicate(dup)}
                          onDragEnd={() => setDraggedDuplicate(null)}
                          className="border-2 border-purple-300 bg-purple-50 rounded p-3 cursor-move hover:shadow-lg transition-shadow"
                        >
                          <div className="flex items-center justify-between mb-2">
                            <div className="flex items-center gap-2">
                              <span className="px-2 py-1 bg-purple-600 text-white text-xs font-bold rounded">GAZELLE</span>
                              <span className="text-xs font-bold text-green-600">{(dup.similarity || 0).toFixed(1)}%</span>
                            </div>
                          </div>
                          <p className="font-semibold text-gray-800 mb-1">{dup.gazelle_nom || 'N/A'}</p>
                          <p className="text-xs text-gray-600">Prix: {(dup.gazelle_price || 0).toFixed(2)}$</p>
                          <p className="text-xs text-gray-600">Diff: {(dup.price_diff || 0).toFixed(2)}$</p>
                        </div>
                      </div>

                      <div className="mt-3 flex gap-2">
                        <button
                          onClick={async () => {
                            try {
                              const response = await fetch(`${API_URL}/inventaire/catalogue/map-gazelle`, {
                                method: 'POST',
                                headers: { 'Content-Type': 'application/json' },
                                body: JSON.stringify({
                                  code_produit: dup.local_code,
                                  gazelle_product_id: dup.gazelle_id,
                                  update_prices: true
                                })
                              })
                              if (!response.ok) throw new Error('Erreur')
                              // Pas d'alert, juste supprimer de la liste
                              setDuplicates(duplicates.filter((_, i) => i !== idx))
                              await loadInventory()
                            } catch (err) {
                              alert('❌ Erreur: ' + err.message)
                            }
                          }}
                          className="px-3 py-1 text-sm bg-green-600 text-white rounded hover:bg-green-700"
                        >
                          ✓ Associer
                        </button>
                        <button
                          onClick={() => setDuplicates(duplicates.filter((_, i) => i !== idx))}
                          className="px-3 py-1 text-sm bg-gray-300 text-gray-700 rounded hover:bg-gray-400"
                        >
                          ✕ Ignorer
                        </button>
                      </div>
                    </div>
                    )
                  })}
                </div>
              )}
            </div>
          )}

          {/* Sub-tab: Importer depuis Gazelle */}
          {syncTab === 'import' && (
            <div>
              <button
                onClick={async () => {
                  try {
                    setLoadingGazelle(true)
                    const response = await fetch(`${API_URL}/inventaire/gazelle/products`)
                    const data = await response.json()
                    setGazelleProducts(data.products || [])
                    alert(`${data.count} produits chargés`)
                  } catch (err) {
                    alert('Erreur: ' + err.message)
                  } finally {
                    setLoadingGazelle(false)
                  }
                }}
                disabled={loadingGazelle}
                className="mb-4 px-4 py-2 bg-purple-600 text-white rounded hover:bg-purple-700 disabled:opacity-50"
              >
                {loadingGazelle ? '⏳ Chargement...' : '📥 Charger Master Service Items'}
              </button>

              {gazelleProducts.length === 0 ? (
                <div className="text-center py-12 text-gray-500">
                  Chargez les Master Service Items pour voir tous les produits Gazelle
                </div>
              ) : (
                <div>
                  <div className="bg-blue-50 border border-blue-200 rounded p-3 mb-3 text-sm text-blue-800">
                    💡 <strong>Import automatique</strong> : L'ID Gazelle sera utilisé comme code produit (masqué dans l'interface)
                  </div>

                  {/* Configuration batch */}
                  <div className="bg-gray-50 border border-gray-300 rounded p-4 mb-4">
                    <div className="flex items-center gap-4 mb-3">
                      <span className="font-semibold text-sm">Configuration batch ({selectedGazelleIds.size} sélectionnés)</span>
                      <button
                        onClick={() => {
                          if (selectedGazelleIds.size === gazelleProducts.length) {
                            setSelectedGazelleIds(new Set())
                          } else {
                            setSelectedGazelleIds(new Set(gazelleProducts.map(gp => gp.id)))
                          }
                        }}
                        className="text-sm text-blue-600 hover:underline"
                      >
                        {selectedGazelleIds.size === gazelleProducts.length ? '❌ Tout désélectionner' : '✅ Tout sélectionner'}
                      </button>
                    </div>

                    <div className="flex gap-3 flex-wrap items-center">
                      <select
                        value={batchCategorie}
                        onChange={(e) => setBatchCategorie(e.target.value)}
                        className="px-3 py-2 border rounded"
                      >
                        <option value="Services">Services</option>
                        <option value="Pièces">Pièces</option>
                        <option value="Fournitures">Fournitures</option>
                        <option value="Accessoires">Accessoires</option>
                      </select>

                      <select
                        value={batchGazelleType}
                        onChange={(e) => setBatchGazelleType(e.target.value)}
                        className="px-3 py-2 border rounded"
                      >
                        <option value="service">Service (pas d'inventaire)</option>
                        <option value="produit">Produit (avec inventaire)</option>
                        <option value="fourniture">Fourniture (inventaire, pas commission)</option>
                      </select>

                      <label className="flex items-center gap-2">
                        <input
                          type="checkbox"
                          checked={batchHasCommission}
                          onChange={(e) => setBatchHasCommission(e.target.checked)}
                        />
                        <span className="text-sm">Commission</span>
                      </label>

                      <input
                        type="number"
                        value={batchCommissionRate}
                        onChange={(e) => setBatchCommissionRate(parseFloat(e.target.value) || 0)}
                        placeholder="Taux %"
                        min="0"
                        max="100"
                        step="0.1"
                        className="w-24 px-3 py-2 border rounded"
                      />

                      <button
                        onClick={async () => {
                          if (selectedGazelleIds.size === 0) {
                            alert('⚠️ Aucun produit sélectionné')
                            return
                          }

                          const selectedProducts = gazelleProducts.filter(gp => selectedGazelleIds.has(gp.id))
                          let imported = 0
                          let errors = []

                          for (const gp of selectedProducts) {
                            try {
                              const response = await fetch(`${API_URL}/inventaire/catalogue/import-gazelle`, {
                                method: 'POST',
                                headers: { 'Content-Type': 'application/json' },
                                body: JSON.stringify({
                                  gazelle_product_id: gp.id,
                                  has_commission: batchHasCommission,
                                  commission_rate: batchCommissionRate,
                                  categorie: batchCategorie,
                                  type_produit: batchGazelleType
                                })
                              })

                              if (response.ok) {
                                imported++
                              } else {
                                const errorData = await response.json().catch(() => ({ detail: 'Erreur inconnue' }))
                                errors.push(`${gp.name_fr}: ${errorData.detail}`)
                              }
                            } catch (err) {
                              errors.push(`${gp.name_fr}: ${err.message}`)
                            }
                          }

                          // Retirer les produits importés de la liste
                          setGazelleProducts(gazelleProducts.filter(gp => !selectedGazelleIds.has(gp.id)))
                          setSelectedGazelleIds(new Set())

                          alert(
                            `✅ Import terminé!\n\n` +
                            `${imported} produits importés\n` +
                            (errors.length > 0 ? `\n⚠️ ${errors.length} erreurs:\n${errors.slice(0, 5).join('\n')}` : '')
                          )

                          await loadInventory()
                        }}
                        disabled={selectedGazelleIds.size === 0}
                        className="ml-auto px-6 py-2 bg-green-600 text-white rounded hover:bg-green-700 font-semibold disabled:opacity-50"
                      >
                        ➕ Importer sélection ({selectedGazelleIds.size})
                      </button>
                    </div>
                  </div>

                  {/* Liste des produits */}
                  <div className="space-y-2 max-h-[500px] overflow-y-auto">
                    {gazelleProducts.map((gp, idx) => (
                      <div
                        key={idx}
                        className={`border rounded p-3 ${selectedGazelleIds.has(gp.id) ? 'bg-blue-50 border-blue-300' : 'bg-white'}`}
                      >
                        <div className="flex items-start gap-3">
                          <input
                            type="checkbox"
                            checked={selectedGazelleIds.has(gp.id)}
                            onChange={(e) => {
                              const newSet = new Set(selectedGazelleIds)
                              if (e.target.checked) {
                                newSet.add(gp.id)
                              } else {
                                newSet.delete(gp.id)
                              }
                              setSelectedGazelleIds(newSet)
                            }}
                            className="mt-1"
                          />

                          <div className="flex-1">
                            <p className="font-semibold text-gray-900">{gp.name_fr}</p>
                            {gp.description_fr && <p className="text-sm text-gray-600 mt-1">{gp.description_fr}</p>}
                            <div className="flex gap-3 mt-2 text-xs">
                              <span className="bg-green-100 text-green-800 px-2 py-1 rounded">Prix: {(parseFloat(gp.amount || 0) / 100).toFixed(2)}$</span>
                              <span className="bg-purple-100 text-purple-800 px-2 py-1 rounded">Groupe: {gp.group_name_fr || 'N/A'}</span>
                            </div>
                          </div>

                          <button
                            onClick={() => {
                              setGazelleProducts(gazelleProducts.filter((_, i) => i !== idx))
                              const newSet = new Set(selectedGazelleIds)
                              newSet.delete(gp.id)
                              setSelectedGazelleIds(newSet)
                            }}
                            className="px-2 py-1 text-gray-400 hover:text-red-600 text-lg"
                            title="Masquer de la liste"
                          >
                            ✕
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Modal d'édition (admin) */}
      {showEditModal && editingProduct && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-2xl w-full mx-4 max-h-[90vh] overflow-y-auto">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-lg font-semibold text-gray-800">
                Modifier: {editingProduct.code_produit}
              </h3>
              <button
                onClick={() => {
                  setShowEditModal(false)
                  setEditingProduct(null)
                }}
                className="text-gray-500 hover:text-gray-700 text-2xl"
              >
                ×
              </button>
            </div>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Nom du produit</label>
                <input
                  type="text"
                  value={editingProduct.name || ''}
                  onChange={(e) => setEditingProduct({...editingProduct, name: e.target.value})}
                  className="w-full border rounded px-3 py-2"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Catégorie</label>
                <select
                  value={editingProduct.category || ''}
                  onChange={(e) => setEditingProduct({...editingProduct, category: e.target.value})}
                  className="w-full border rounded px-3 py-2"
                >
                  <option value="Cordes">Cordes</option>
                  <option value="Feutres">Feutres</option>
                  <option value="Accessoire">Accessoire</option>
                  <option value="Service">Service</option>
                  <option value="Fourniture">Fourniture</option>
                  <option value="Produit">Produit</option>
                  <option value="Frais">Frais</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Prix unitaire ($)</label>
                <input
                  type="number"
                  step="0.01"
                  value={editingProduct.prix_unitaire || ''}
                  onChange={(e) => setEditingProduct({...editingProduct, prix_unitaire: parseFloat(e.target.value) || 0})}
                  className="w-full border rounded px-3 py-2"
                />
              </div>

              <div className="border-t pt-4">
                <div className="flex items-center gap-2 mb-2">
                  <input
                    type="checkbox"
                    id="has_commission"
                    checked={editingProduct.has_commission || false}
                    onChange={(e) => setEditingProduct({
                      ...editingProduct,
                      has_commission: e.target.checked,
                      commission_rate: e.target.checked ? (editingProduct.commission_rate || 15) : 0
                    })}
                    className="w-4 h-4"
                  />
                  <label htmlFor="has_commission" className="text-sm font-medium text-gray-700">
                    Activer la commission
                  </label>
                </div>

                {editingProduct.has_commission && (
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Taux de commission (%)
                    </label>
                    <input
                      type="number"
                      step="0.01"
                      value={editingProduct.commission_rate || 0}
                      onChange={(e) => setEditingProduct({...editingProduct, commission_rate: parseFloat(e.target.value) || 0})}
                      className="w-full border rounded px-3 py-2"
                    />
                  </div>
                )}
              </div>

              <div className="border-t pt-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Groupe de variantes
                  </label>
                  <input
                    type="text"
                    value={editingProduct.variant_group || ''}
                    onChange={(e) => setEditingProduct({...editingProduct, variant_group: e.target.value})}
                    placeholder="Ex: Cordes Piano"
                    className="w-full border rounded px-3 py-2"
                  />
                </div>

                <div className="mt-2">
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Label de variante
                  </label>
                  <input
                    type="text"
                    value={editingProduct.variant_label || ''}
                    onChange={(e) => setEditingProduct({...editingProduct, variant_label: e.target.value})}
                    placeholder="Ex: Do#3"
                    className="w-full border rounded px-3 py-2"
                  />
                </div>
              </div>

              <div className="border-t pt-4">
                <div className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    id="is_active"
                    checked={editingProduct.is_active !== false}
                    onChange={(e) => setEditingProduct({...editingProduct, is_active: e.target.checked})}
                    className="w-4 h-4"
                  />
                  <label htmlFor="is_active" className="text-sm font-medium text-gray-700">
                    Produit actif
                  </label>
                </div>
              </div>
            </div>

            <div className="mt-6 flex gap-3 justify-end">
              <button
                onClick={() => {
                  setShowEditModal(false)
                  setEditingProduct(null)
                }}
                className="px-4 py-2 border border-gray-300 rounded hover:bg-gray-50"
              >
                Annuler
              </button>
              <button
                onClick={async () => {
                  try {
                    const response = await fetch(`${API_URL}/inventaire/catalogue/${editingProduct.code_produit}`, {
                      method: 'PUT',
                      headers: { 'Content-Type': 'application/json' },
                      body: JSON.stringify({
                        nom: editingProduct.name,
                        categorie: editingProduct.category,
                        prix_unitaire: editingProduct.prix_unitaire,
                        has_commission: editingProduct.has_commission,
                        commission_rate: editingProduct.commission_rate,
                        variant_group: editingProduct.variant_group,
                        variant_label: editingProduct.variant_label,
                        is_active: editingProduct.is_active
                      })
                    })
                    if (!response.ok) throw new Error('Erreur lors de la sauvegarde')

                    setShowEditModal(false)
                    setEditingProduct(null)
                    await loadInventory()
                    alert('Produit mis à jour avec succès')
                  } catch (err) {
                    alert('Erreur: ' + err.message)
                  }
                }}
                className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
              >
                Enregistrer
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default InventaireDashboard
