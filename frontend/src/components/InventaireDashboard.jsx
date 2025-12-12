import React, { useState, useEffect } from 'react'
import ExportButton from './ExportButton'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

// Configuration des techniciens (mappés depuis le guide V4)
const TECHNICIENS = [
  { id: 'usr_ofYggsCDt2JAVeNP', name: 'Allan', username: 'allan' },
  { id: 'usr_HcCiFk7o0vZ9xAI0', name: 'Nicolas', username: 'nicolas' },
  { id: 'usr_ReUSmIJmBF86ilY1', name: 'Jean-Philippe', username: 'jeanphilippe' }
]

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

      // Charger les stocks de chaque technicien
      const inventoryPromises = TECHNICIENS.map(tech =>
        fetch(`${API_URL}/inventaire/stock/${tech.name}`)
          .then(res => res.ok ? res.json() : { inventaire: [] })
      )
      const inventories = await Promise.all(inventoryPromises)

      // Fusionner dans le format V4: products avec quantities{allan, nicolas, jeanphilippe}
      const productsMap = {}

      catalogueData.produits.forEach(prod => {
        productsMap[prod.code_produit] = {
          id: prod.code_produit,
          code_produit: prod.code_produit,
          name: prod.nom,
          original_name: prod.nom,
          sku: prod.code_produit,
          category: prod.categorie || 'Sans catégorie',
          variant_group: prod.variant_group,
          variant_label: prod.variant_label,
          prix_unitaire: prod.prix_unitaire,
          has_commission: prod.has_commission,
          commission_rate: prod.commission_rate,
          display_order: prod.display_order || 0,
          is_active: prod.is_active !== false,
          quantities: {
            allan: 0,
            nicolas: 0,
            jeanphilippe: 0
          }
        }
      })

      // Remplir les quantités depuis les inventaires
      inventories.forEach((invData) => {
        // Utiliser le champ 'technicien' retourné par l'API plutôt que l'index
        const technicienName = invData.technicien
        const tech = TECHNICIENS.find(t => t.name === technicienName)

        if (!tech) {
          console.warn(`Technicien inconnu: ${technicienName}`)
          return
        }

        invData.inventaire?.forEach(item => {
          if (productsMap[item.code_produit]) {
            productsMap[item.code_produit].quantities[tech.username] = item.quantite_stock || 0
          }
        })
      })

      setProducts(Object.values(productsMap))
      setCatalogueAdmin(Object.values(productsMap))
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
    try {
      // TODO: Adapter endpoint pour mise à jour
      const response = await fetch(`${API_URL}/inventaire/stock`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          code_produit: productId,
          technicien: TECHNICIENS.find(t => t.username === techUsername)?.name || 'Allan',
          quantite_stock: parseInt(newQuantity) || 0,
          type_transaction: 'ajustement',
          motif: 'Ajustement manuel'
        })
      })

      if (!response.ok) throw new Error('Erreur mise à jour')

      // Feedback visuel vert 1 seconde
      setUpdateFeedback(prev => ({ ...prev, [productId + techUsername]: true }))
      setTimeout(() => {
        setUpdateFeedback(prev => {
          const newFeedback = { ...prev }
          delete newFeedback[productId + techUsername]
          return newFeedback
        })
      }, 1000)

      // Recharger l'inventaire
      await loadInventory()
    } catch (err) {
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

  // Grouper produits par catégorie
  const groupByCategory = () => {
    const groups = {}
    products
      .filter(p => p.is_active !== false)
      .forEach(product => {
        const cat = product.categorie || 'Sans catégorie'
        if (!groups[cat]) groups[cat] = []
        groups[cat].push(product)
      })

    // Trier chaque groupe par display_order puis nom
    Object.keys(groups).forEach(cat => {
      groups[cat].sort((a, b) => {
        if (a.display_order !== b.display_order) {
          return (a.display_order || 0) - (b.display_order || 0)
        }
        if (a.variant_group && b.variant_group && a.variant_group === b.variant_group) {
          return (a.variant_label || '').localeCompare(b.variant_label || '')
        }
        return (a.nom || '').localeCompare(b.nom || '')
      })
    })

    return groups
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

  const categoryGroups = groupByCategory()
  const currentUserIsAdmin = currentUser?.role === 'admin'
  const currentUsername = currentUser?.username || 'allan'

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
        {currentUserIsAdmin && (
          <button
            onClick={() => {
              setActiveTab('admin')
              setCatalogueAdmin([...products])
            }}
            className={`px-4 py-2 font-medium ${
              activeTab === 'admin'
                ? 'border-b-2 border-blue-500 text-blue-600'
                : 'text-gray-600 hover:text-gray-800'
            }`}
          >
            Admin
          </button>
        )}
      </div>

      {/* ONGLET INVENTAIRE (UI Technicien V4) */}
      {activeTab === 'inventaire' && (
        <div>
          {/* Zone commentaire rapide */}
          <div className="mb-4 bg-blue-50 border border-blue-200 rounded-lg p-4">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              💬 Commentaire rapide (notifie le CTO via Slack)
            </label>
            <div className="flex gap-2">
              <input
                type="text"
                value={comment}
                onChange={(e) => setComment(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && submitComment()}
                placeholder="Ex: Besoin urgent de coupelles brunes..."
                className="flex-1 border rounded px-3 py-2 text-sm"
              />
              <button
                onClick={submitComment}
                className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 font-medium"
              >
                Envoyer
              </button>
            </div>
          </div>

          {/* Tableau multi-colonnes avec sticky */}
          <div className="bg-white rounded-lg shadow overflow-auto" style={{ maxHeight: '70vh' }}>
            <table className="min-w-full border-collapse">
              <thead className="bg-gray-50 sticky top-0 z-10">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase border-b sticky left-0 bg-gray-50 z-20">
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
                        className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase border-b"
                      >
                        {tech.name}
                      </th>
                    )
                  })}
                </tr>
              </thead>
              <tbody>
                {Object.entries(categoryGroups).map(([category, categoryProducts]) => (
                  <React.Fragment key={category}>
                    {/* Ligne catégorie */}
                    <tr className="bg-gray-100 hover:bg-gray-200 cursor-pointer sticky" style={{ top: '48px', zIndex: 9 }}>
                      <td
                        colSpan={isMobile && !currentUserIsAdmin ? 2 : TECHNICIENS.length + 1}
                        className="px-4 py-2 font-bold text-gray-800 border-b"
                        onClick={() => toggleCategory(category)}
                      >
                        {collapsedCategories.has(category) ? '▶' : '▼'} {category}
                      </td>
                    </tr>

                    {/* Lignes produits */}
                    {!collapsedCategories.has(category) && categoryProducts.map(product => (
                      <tr key={product.code_produit} className="hover:bg-gray-50 border-b">
                        <td className="px-4 py-3 text-sm text-gray-900 sticky left-0 bg-white border-r font-medium" style={{ minWidth: '200px' }}>
                          <div>
                            {product.name}
                            {product.variant_label && (
                              <span className="text-xs text-gray-500 ml-2">
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
                              className="px-4 py-3 text-center"
                            >
                              <input
                                type="number"
                                min="0"
                                value={qty}
                                onChange={(e) => updateQuantity(product.code_produit, tech.username, e.target.value)}
                                onFocus={(e) => e.target.select()}
                                onClick={(e) => e.target.select()}
                                className={`w-20 px-2 py-1 text-center border rounded text-sm ${
                                  isMyColumn ? 'bg-green-50 border-green-300 font-bold' : 'border-gray-300'
                                } ${hasFeedback ? 'bg-green-200' : ''}`}
                                style={hasFeedback ? { transition: 'background-color 0.3s' } : {}}
                              />
                            </td>
                          )
                        })}
                      </tr>
                    ))}
                  </React.Fragment>
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

      {/* ONGLET ADMIN (UI Admin V4) */}
      {activeTab === 'admin' && currentUserIsAdmin && (
        <div>
          {/* Toolbar */}
          <div className="mb-4 flex justify-between items-center flex-wrap gap-4">
            <div className="flex gap-4 items-center flex-wrap">
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Rechercher: nom, code, catégorie, variante..."
                className="border rounded px-3 py-2 text-sm w-80"
              />
              <button
                onClick={() => loadInventory()}
                className="px-4 py-2 bg-gray-600 text-white rounded hover:bg-gray-700 font-medium"
              >
                🔄 Actualiser
              </button>
            </div>

            <div className="flex gap-2">
              <ExportButton
                data={catalogueAdmin}
                filename="catalogue_admin"
              />
              {hasChanges && (
                <button
                  onClick={saveOrder}
                  className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 font-medium"
                >
                  💾 Sauvegarder l'ordre
                </button>
              )}
            </div>
          </div>

          {/* Tableau admin avec drag&drop */}
          <div className="bg-white rounded-lg shadow overflow-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Ordre</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Code</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Nom</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Catégorie</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Variante</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Allan</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Nicolas</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">JP</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Actions</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {filteredProducts
                  .sort((a, b) => (a.display_order || 0) - (b.display_order || 0))
                  .map((product, index) => (
                  <tr
                    key={product.code_produit}
                    draggable
                    onDragStart={(e) => handleDragStart(e, product)}
                    onDragOver={handleDragOver}
                    onDrop={(e) => handleDrop(e, product)}
                    onDragEnd={handleDragEnd}
                    className={`hover:bg-gray-50 cursor-move ${
                      draggedItem?.code_produit === product.code_produit ? 'opacity-50' : ''
                    } ${!product.is_active ? 'bg-gray-100 line-through text-gray-400' : ''}`}
                  >
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
                          className="w-16 border rounded px-2 py-1 text-sm"
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
                    <td className="px-4 py-3 text-sm text-gray-700">
                      {product.variant_group && (
                        <div>
                          <strong>{product.variant_group}</strong>
                          {product.variant_label && ` (${product.variant_label})`}
                        </div>
                      )}
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-700 text-center">
                      {product.quantities?.allan || 0}
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-700 text-center">
                      {product.quantities?.nicolas || 0}
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-700 text-center">
                      {product.quantities?.jeanphilippe || 0}
                    </td>
                    <td className="px-4 py-3 text-sm">
                      <div className="flex gap-2">
                        <button
                          onClick={() => {
                            setEditingProduct({...product})
                            setShowEditModal(true)
                          }}
                          className="text-blue-600 hover:text-blue-800 font-medium text-xs"
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
                                  ...product,
                                  is_active: !product.is_active
                                })
                              })
                              if (!response.ok) throw new Error('Erreur toggle')
                              await loadInventory()
                            } catch (err) {
                              alert('Erreur: ' + err.message)
                            }
                          }}
                          className={`font-medium text-xs ${
                            product.is_active ? 'text-red-600 hover:text-red-800' : 'text-green-600 hover:text-green-800'
                          }`}
                        >
                          {product.is_active ? '🚫' : '✅'}
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {filteredProducts.length === 0 && (
              <div className="p-8 text-center text-gray-500">Aucun produit trouvé</div>
            )}
          </div>
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
