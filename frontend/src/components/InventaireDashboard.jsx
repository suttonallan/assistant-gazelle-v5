import { useState, useEffect } from 'react'
import ExportButton from './ExportButton'
import ProductMappingInterface from './ProductMappingInterface'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const InventaireDashboard = ({ currentUser }) => {
  const [catalogue, setCatalogue] = useState([])
  const [inventaire, setInventaire] = useState([])
  const [transactions, setTransactions] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [activeTab, setActiveTab] = useState('catalogue') // 'catalogue', 'stock', 'transactions', 'admin', 'mapping'
  const [selectedTechnicien, setSelectedTechnicien] = useState(currentUser?.name || 'Allan')
  const [selectedCategorie, setSelectedCategorie] = useState('')
  const [filterCommission, setFilterCommission] = useState('') // '', 'true', 'false'
  const [catalogueAdmin, setCatalogueAdmin] = useState([]) // Copie locale pour l'admin
  const [hasChanges, setHasChanges] = useState(false)
  const [editingProduct, setEditingProduct] = useState(null)
  const [showEditModal, setShowEditModal] = useState(false)

  // Charger le catalogue
  const loadCatalogue = async () => {
    try {
      const params = new URLSearchParams()
      if (selectedCategorie) params.append('categorie', selectedCategorie)
      if (filterCommission) params.append('has_commission', filterCommission)

      const url = `${API_URL}/inventaire/catalogue${params.toString() ? '?' + params.toString() : ''}`
      const response = await fetch(url)
      if (!response.ok) throw new Error('Erreur lors du chargement')
      const data = await response.json()
      setCatalogue(data.produits || [])
    } catch (err) {
      setError(err.message)
    }
  }

  // Charger l'inventaire du technicien
  const loadInventaire = async () => {
    try {
      const response = await fetch(`${API_URL}/inventaire/stock/${selectedTechnicien}`)
      if (!response.ok) throw new Error('Erreur lors du chargement')
      const data = await response.json()
      setInventaire(data.inventaire || [])
    } catch (err) {
      setError(err.message)
    }
  }

  // Charger les transactions
  const loadTransactions = async () => {
    try {
      const response = await fetch(`${API_URL}/inventaire/transactions?limit=50`)
      if (!response.ok) throw new Error('Erreur lors du chargement')
      const data = await response.json()
      setTransactions(data.transactions || [])
    } catch (err) {
      setError(err.message)
    }
  }

  useEffect(() => {
    setLoading(true)
    Promise.all([
      loadCatalogue(),
      loadInventaire(),
      loadTransactions()
    ]).finally(() => setLoading(false))
  }, [selectedTechnicien, selectedCategorie, filterCommission])

  // Synchroniser catalogueAdmin avec catalogue
  useEffect(() => {
    if (activeTab === 'admin' && catalogue.length > 0 && catalogueAdmin.length === 0) {
      setCatalogueAdmin([...catalogue])
    }
  }, [activeTab, catalogue])

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

  // Extraire les catégories uniques
  const categories = [...new Set(catalogue.map(p => p.categorie))].sort()

  return (
    <div className="max-w-7xl mx-auto px-4 py-6">
      <h1 className="text-2xl font-bold text-gray-800 mb-6">📦 Inventaire</h1>

      {/* Tabs */}
      <div className="flex gap-2 mb-6 border-b border-gray-200">
        <button
          onClick={() => setActiveTab('catalogue')}
          className={`px-4 py-2 font-medium ${
            activeTab === 'catalogue'
              ? 'border-b-2 border-blue-500 text-blue-600'
              : 'text-gray-600 hover:text-gray-800'
          }`}
        >
          Catalogue
        </button>
        <button
          onClick={() => setActiveTab('stock')}
          className={`px-4 py-2 font-medium ${
            activeTab === 'stock'
              ? 'border-b-2 border-blue-500 text-blue-600'
              : 'text-gray-600 hover:text-gray-800'
          }`}
        >
          Stock Technicien
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
        {currentUser?.role === 'admin' && (
          <>
            <button
              onClick={() => {
                setActiveTab('admin')
                setCatalogueAdmin([...catalogue])
              }}
              className={`px-4 py-2 font-medium ${
                activeTab === 'admin'
                  ? 'border-b-2 border-blue-500 text-blue-600'
                  : 'text-gray-600 hover:text-gray-800'
              }`}
            >
              Admin
            </button>
            <button
              onClick={() => setActiveTab('mapping')}
              className={`px-4 py-2 font-medium ${
                activeTab === 'mapping'
                  ? 'border-b-2 border-blue-500 text-blue-600'
                  : 'text-gray-600 hover:text-gray-800'
              }`}
            >
              Mapping Gazelle
            </button>
          </>
        )}
      </div>

      {/* Contenu selon l'onglet */}
      {activeTab === 'catalogue' && (
        <div>
          <div className="mb-4 flex gap-4 items-center flex-wrap justify-between">
            <div className="flex gap-4 items-center flex-wrap">
              <div className="flex items-center gap-2">
                <label className="text-sm font-medium text-gray-700">
                  Catégorie:
                </label>
                <select
                  value={selectedCategorie}
                  onChange={(e) => setSelectedCategorie(e.target.value)}
                  className="border rounded px-3 py-1 text-sm"
                >
                  <option value="">Toutes</option>
                  {categories.map(cat => (
                    <option key={cat} value={cat}>{cat}</option>
                  ))}
                </select>
              </div>

              <div className="flex items-center gap-2">
                <label className="text-sm font-medium text-gray-700">
                  Commission:
                </label>
                <select
                  value={filterCommission}
                  onChange={(e) => setFilterCommission(e.target.value)}
                  className="border rounded px-3 py-1 text-sm"
                >
                  <option value="">Tous les produits</option>
                  <option value="true">Avec commission</option>
                  <option value="false">Sans commission</option>
                </select>
              </div>
            </div>
            
            <ExportButton 
              data={catalogue} 
              filename="catalogue_produits"
            />
          </div>

          <div className="bg-white rounded-lg shadow overflow-hidden">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Code</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Nom</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Catégorie</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Unité</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Prix</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Commission</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Fournisseur</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {catalogue.map((produit) => (
                  <tr key={produit.code_produit}>
                    <td className="px-4 py-3 text-sm font-medium text-gray-900">{produit.code_produit}</td>
                    <td className="px-4 py-3 text-sm text-gray-700">{produit.nom}</td>
                    <td className="px-4 py-3 text-sm text-gray-700">{produit.categorie}</td>
                    <td className="px-4 py-3 text-sm text-gray-700">{produit.unite_mesure}</td>
                    <td className="px-4 py-3 text-sm text-gray-700">
                      {produit.prix_unitaire ? `$${produit.prix_unitaire.toFixed(2)}` : '-'}
                    </td>
                    <td className="px-4 py-3 text-sm">
                      {produit.has_commission ? (
                        <span className="text-green-600 font-medium">
                          {produit.commission_rate}%
                        </span>
                      ) : (
                        <span className="text-gray-400">-</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-700">{produit.fournisseur || '-'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            {catalogue.length === 0 && (
              <div className="p-8 text-center text-gray-500">Aucun produit dans le catalogue</div>
            )}
          </div>
        </div>
      )}

      {activeTab === 'stock' && (
        <div>
          <div className="mb-4">
            <label className="text-sm font-medium text-gray-700 mr-2">
              Technicien:
            </label>
            <select
              value={selectedTechnicien}
              onChange={(e) => setSelectedTechnicien(e.target.value)}
              className="border rounded px-3 py-1 text-sm"
            >
              <option value="Allan">Allan</option>
              <option value="Nicolas">Nicolas</option>
              <option value="Jean-Philippe">Jean-Philippe</option>
            </select>
          </div>

          <div className="bg-white rounded-lg shadow overflow-hidden">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Code</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Nom</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Quantité</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Emplacement</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Notes</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {inventaire.map((item) => (
                  <tr key={item.id}>
                    <td className="px-4 py-3 text-sm font-medium text-gray-900">{item.code_produit}</td>
                    <td className="px-4 py-3 text-sm text-gray-700">{item.nom || '-'}</td>
                    <td className="px-4 py-3 text-sm text-gray-700 font-medium">
                      {item.quantite_stock} {item.unite_mesure || 'unité'}
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-700">{item.emplacement || '-'}</td>
                    <td className="px-4 py-3 text-sm text-gray-700">{item.notes || '-'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            {inventaire.length === 0 && (
              <div className="p-8 text-center text-gray-500">
                Aucun stock pour {selectedTechnicien}
              </div>
            )}
          </div>
        </div>
      )}

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

      {activeTab === 'mapping' && currentUser?.role === 'admin' && (
        <ProductMappingInterface />
      )}

      {activeTab === 'admin' && currentUser?.role === 'admin' && (
        <div>
          <div className="mb-4 flex justify-between items-center flex-wrap gap-4">
            <h2 className="text-lg font-semibold text-gray-800">Administration du Catalogue</h2>
            <div className="flex gap-2">
              <ExportButton 
                data={catalogueAdmin} 
                filename="catalogue_admin"
              />
              {hasChanges && (
                <button
                  onClick={async () => {
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
                      if (!response.ok) throw new Error('Erreur lors de la sauvegarde')
                      setHasChanges(false)
                      await loadCatalogue()
                      alert('Ordre sauvegardé avec succès')
                    } catch (err) {
                      alert('Erreur: ' + err.message)
                    }
                  }}
                  className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 font-medium"
                >
                  Sauvegarder l'ordre
                </button>
              )}
            </div>
          </div>

          <div className="bg-white rounded-lg shadow overflow-hidden">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Ordre</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Code</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Nom</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Catégorie</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Prix</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Commission</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Actions</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {catalogueAdmin
                  .sort((a, b) => (a.display_order || 0) - (b.display_order || 0))
                  .map((produit, index) => (
                  <tr key={produit.code_produit}>
                    <td className="px-4 py-3 text-sm">
                      <div className="flex items-center gap-2">
                        <input
                          type="number"
                          value={produit.display_order || 0}
                          onChange={(e) => {
                            const newOrder = parseInt(e.target.value) || 0
                            const updated = catalogueAdmin.map(p =>
                              p.code_produit === produit.code_produit
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
                              const currentOrder = updated[index].display_order || 0
                              const prevOrder = updated[index - 1].display_order || 0
                              updated[index].display_order = prevOrder
                              updated[index - 1].display_order = currentOrder
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
                              if (index === catalogueAdmin.length - 1) return
                              const updated = [...catalogueAdmin]
                              const currentOrder = updated[index].display_order || 0
                              const nextOrder = updated[index + 1].display_order || 0
                              updated[index].display_order = nextOrder
                              updated[index + 1].display_order = currentOrder
                              setCatalogueAdmin(updated)
                              setHasChanges(true)
                            }}
                            disabled={index === catalogueAdmin.length - 1}
                            className="text-gray-600 hover:text-blue-600 disabled:text-gray-300 text-xs"
                          >
                            ▼
                          </button>
                        </div>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-sm font-medium text-gray-900">{produit.code_produit}</td>
                    <td className="px-4 py-3 text-sm text-gray-700">{produit.nom}</td>
                    <td className="px-4 py-3 text-sm text-gray-700">{produit.categorie}</td>
                    <td className="px-4 py-3 text-sm text-gray-700">
                      {produit.prix_unitaire ? `$${produit.prix_unitaire.toFixed(2)}` : '-'}
                    </td>
                    <td className="px-4 py-3 text-sm">
                      {produit.has_commission ? (
                        <span className="text-green-600 font-medium">
                          {produit.commission_rate}%
                        </span>
                      ) : (
                        <span className="text-gray-400">-</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-sm">
                      <button
                        onClick={() => {
                          setEditingProduct({...produit})
                          setShowEditModal(true)
                        }}
                        className="text-blue-600 hover:text-blue-800 font-medium"
                      >
                        ✏️ Modifier
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {catalogueAdmin.length === 0 && (
              <div className="p-8 text-center text-gray-500">Aucun produit dans le catalogue</div>
            )}
          </div>
        </div>
      )}

      {/* Modal de modification */}
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
              {/* Nom */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Nom du produit
                </label>
                <input
                  type="text"
                  value={editingProduct.nom || ''}
                  onChange={(e) => setEditingProduct({...editingProduct, nom: e.target.value})}
                  className="w-full border rounded px-3 py-2"
                />
              </div>

              {/* Catégorie */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Catégorie
                </label>
                <select
                  value={editingProduct.categorie || ''}
                  onChange={(e) => setEditingProduct({...editingProduct, categorie: e.target.value})}
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

              {/* Prix */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Prix unitaire ($)
                </label>
                <input
                  type="number"
                  step="0.01"
                  value={editingProduct.prix_unitaire || ''}
                  onChange={(e) => setEditingProduct({...editingProduct, prix_unitaire: parseFloat(e.target.value) || 0})}
                  className="w-full border rounded px-3 py-2"
                />
              </div>

              {/* Commission */}
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

              {/* Variantes */}
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

              {/* Actif/Inactif */}
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

            {/* Boutons */}
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
                        nom: editingProduct.nom,
                        categorie: editingProduct.categorie,
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
                    await loadCatalogue()
                    setCatalogueAdmin([...catalogue])
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



