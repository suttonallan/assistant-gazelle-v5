import { useState, useEffect } from 'react'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const ProductMappingInterface = () => {
  const [gazelleProducts, setGazelleProducts] = useState([])
  const [supabaseProducts, setSupabaseProducts] = useState([])
  const [mappings, setMappings] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [activeView, setActiveView] = useState('unmapped') // 'unmapped', 'all', 'mappings'
  const [searchGazelle, setSearchGazelle] = useState('')
  const [searchSupabase, setSearchSupabase] = useState('')
  const [selectedGazelle, setSelectedGazelle] = useState(null)
  const [selectedSupabase, setSelectedSupabase] = useState(null)

  // Charger les produits non mappés
  const loadUnmapped = async () => {
    try {
      setLoading(true)
      const [gazelleRes, supabaseRes] = await Promise.all([
        fetch(`${API_URL}/inventaire/mapping/unmapped-gazelle`),
        fetch(`${API_URL}/inventaire/mapping/unmapped-supabase`)
      ])
      
      if (!gazelleRes.ok || !supabaseRes.ok) throw new Error('Erreur lors du chargement')
      
      const gazelleData = await gazelleRes.json()
      const supabaseData = await supabaseRes.json()
      
      setGazelleProducts(gazelleData.products || [])
      setSupabaseProducts(supabaseData.products || [])
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  // Charger tous les mappings
  const loadMappings = async () => {
    try {
      const response = await fetch(`${API_URL}/inventaire/mapping/mappings`)
      if (!response.ok) throw new Error('Erreur lors du chargement')
      const data = await response.json()
      setMappings(data.mappings || [])
    } catch (err) {
      setError(err.message)
    }
  }

  // Créer un mapping
  const createMapping = async (gazelleId, codeProduit) => {
    try {
      const response = await fetch(`${API_URL}/inventaire/mapping/mappings`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          gazelle_product_id: gazelleId,
          code_produit: codeProduit,
          mapped_by: 'admin'
        })
      })
      
      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.detail || 'Erreur lors de la création')
      }
      
      // Recharger les données
      await loadUnmapped()
      await loadMappings()
      setSelectedGazelle(null)
      setSelectedSupabase(null)
      alert('Mapping créé avec succès!')
    } catch (err) {
      alert('Erreur: ' + err.message)
    }
  }

  // Supprimer un mapping
  const deleteMapping = async (gazelleId) => {
    if (!confirm('Voulez-vous vraiment supprimer ce mapping?')) return
    
    try {
      const response = await fetch(`${API_URL}/inventaire/mapping/mappings/${gazelleId}`, {
        method: 'DELETE'
      })
      
      if (!response.ok) throw new Error('Erreur lors de la suppression')
      
      await loadUnmapped()
      await loadMappings()
      alert('Mapping supprimé avec succès!')
    } catch (err) {
      alert('Erreur: ' + err.message)
    }
  }

  useEffect(() => {
    if (activeView === 'unmapped') {
      loadUnmapped()
    } else if (activeView === 'mappings') {
      loadMappings()
    }
  }, [activeView])

  // Filtrer les produits
  const filteredGazelle = gazelleProducts.filter(p => 
    !searchGazelle || 
    (p.name || '').toLowerCase().includes(searchGazelle.toLowerCase()) ||
    (p.sku || '').toLowerCase().includes(searchGazelle.toLowerCase())
  )

  const filteredSupabase = supabaseProducts.filter(p =>
    !searchSupabase ||
    (p.nom || '').toLowerCase().includes(searchSupabase.toLowerCase()) ||
    (p.code_produit || '').toLowerCase().includes(searchSupabase.toLowerCase())
  )

  if (loading && activeView === 'unmapped') {
    return <div className="p-8 text-center">Chargement...</div>
  }

  if (error) {
    return <div className="p-8 text-center text-red-600">Erreur: {error}</div>
  }

  return (
    <div className="p-6">
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-gray-800 mb-4">Mapping Produits Gazelle ↔ Supabase</h2>
        
        {/* Onglets */}
        <div className="flex gap-2 border-b">
          <button
            onClick={() => setActiveView('unmapped')}
            className={`px-4 py-2 font-medium ${
              activeView === 'unmapped'
                ? 'border-b-2 border-blue-500 text-blue-600'
                : 'text-gray-600 hover:text-gray-800'
            }`}
          >
            Non mappés ({gazelleProducts.length})
          </button>
          <button
            onClick={() => setActiveView('mappings')}
            className={`px-4 py-2 font-medium ${
              activeView === 'mappings'
                ? 'border-b-2 border-blue-500 text-blue-600'
                : 'text-gray-600 hover:text-gray-800'
            }`}
          >
            Mappings existants ({mappings.length})
          </button>
        </div>
      </div>

      {/* Vue: Produits non mappés */}
      {activeView === 'unmapped' && (
        <div>
          <div className="grid grid-cols-2 gap-6 mb-6">
            {/* Colonne Gazelle */}
            <div className="bg-white rounded-lg shadow p-4">
              <h3 className="text-lg font-semibold mb-4">Produits Gazelle (Non mappés)</h3>
              <input
                type="text"
                placeholder="🔍 Rechercher..."
                value={searchGazelle}
                onChange={(e) => setSearchGazelle(e.target.value)}
                className="w-full mb-4 px-3 py-2 border rounded"
              />
              <div className="space-y-2 max-h-96 overflow-y-auto">
                {filteredGazelle.map((product) => (
                  <div
                    key={product.id}
                    onClick={() => setSelectedGazelle(product.id)}
                    className={`p-3 border rounded cursor-pointer hover:bg-blue-50 ${
                      selectedGazelle === product.id ? 'bg-blue-100 border-blue-500' : ''
                    }`}
                  >
                    <div className="font-medium">{product.name || 'Sans nom'}</div>
                    <div className="text-sm text-gray-600">SKU: {product.sku || 'N/A'}</div>
                    <div className="text-sm text-gray-600">ID: {product.id}</div>
                    {product.unitCost && (
                      <div className="text-sm text-green-600">Prix: ${product.unitCost}</div>
                    )}
                  </div>
                ))}
                {filteredGazelle.length === 0 && (
                  <div className="text-center text-gray-500 py-8">
                    {searchGazelle ? 'Aucun résultat' : 'Tous les produits sont mappés!'}
                  </div>
                )}
              </div>
            </div>

            {/* Colonne Supabase */}
            <div className="bg-white rounded-lg shadow p-4">
              <h3 className="text-lg font-semibold mb-4">Produits Supabase (Sans mapping)</h3>
              <input
                type="text"
                placeholder="🔍 Rechercher..."
                value={searchSupabase}
                onChange={(e) => setSearchSupabase(e.target.value)}
                className="w-full mb-4 px-3 py-2 border rounded"
              />
              <div className="space-y-2 max-h-96 overflow-y-auto">
                {filteredSupabase.map((product) => (
                  <div
                    key={product.code_produit}
                    onClick={() => setSelectedSupabase(product.code_produit)}
                    className={`p-3 border rounded cursor-pointer hover:bg-green-50 ${
                      selectedSupabase === product.code_produit ? 'bg-green-100 border-green-500' : ''
                    }`}
                  >
                    <div className="font-medium">{product.nom || 'Sans nom'}</div>
                    <div className="text-sm text-gray-600">Code: {product.code_produit}</div>
                    <div className="text-sm text-gray-600">Catégorie: {product.categorie || 'N/A'}</div>
                    {product.prix_unitaire && (
                      <div className="text-sm text-green-600">Prix: ${product.prix_unitaire}</div>
                    )}
                  </div>
                ))}
                {filteredSupabase.length === 0 && (
                  <div className="text-center text-gray-500 py-8">
                    {searchSupabase ? 'Aucun résultat' : 'Tous les produits sont mappés!'}
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Bouton créer mapping */}
          {selectedGazelle && selectedSupabase && (
            <div className="text-center">
              <button
                onClick={() => createMapping(selectedGazelle, selectedSupabase)}
                className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-medium"
              >
                ✅ Créer Mapping
              </button>
              <p className="mt-2 text-sm text-gray-600">
                Mapping: {gazelleProducts.find(p => p.id === selectedGazelle)?.name} ↔ {supabaseProducts.find(p => p.code_produit === selectedSupabase)?.nom}
              </p>
            </div>
          )}
        </div>
      )}

      {/* Vue: Mappings existants */}
      {activeView === 'mappings' && (
        <div className="bg-white rounded-lg shadow">
          <div className="p-4">
            <button
              onClick={loadMappings}
              className="mb-4 px-4 py-2 bg-gray-200 rounded hover:bg-gray-300"
            >
              🔄 Actualiser
            </button>
          </div>
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Produit Gazelle</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Produit Supabase</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Statut</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Créé par</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Actions</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {mappings.map((mapping) => (
                <tr key={mapping.id}>
                  <td className="px-4 py-3 text-sm">
                    <div className="font-medium">{mapping.gazelle_name || 'N/A'}</div>
                    <div className="text-gray-600 text-xs">ID: {mapping.gazelle_product_id}</div>
                    {mapping.gazelle_sku && (
                      <div className="text-gray-600 text-xs">SKU: {mapping.gazelle_sku}</div>
                    )}
                  </td>
                  <td className="px-4 py-3 text-sm">
                    <div className="font-medium">{mapping.produit_nom || 'N/A'}</div>
                    <div className="text-gray-600 text-xs">Code: {mapping.code_produit}</div>
                    {mapping.produit_categorie && (
                      <div className="text-gray-600 text-xs">Cat: {mapping.produit_categorie}</div>
                    )}
                  </td>
                  <td className="px-4 py-3 text-sm">
                    <span className={`px-2 py-1 rounded text-xs ${
                      mapping.sync_status === 'synced' ? 'bg-green-100 text-green-800' :
                      mapping.sync_status === 'error' ? 'bg-red-100 text-red-800' :
                      'bg-yellow-100 text-yellow-800'
                    }`}>
                      {mapping.sync_status || 'pending'}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-600">
                    {mapping.mapped_by || 'system'}
                  </td>
                  <td className="px-4 py-3 text-sm">
                    <button
                      onClick={() => deleteMapping(mapping.gazelle_product_id)}
                      className="text-red-600 hover:text-red-800"
                    >
                      🗑️ Supprimer
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {mappings.length === 0 && (
            <div className="p-8 text-center text-gray-500">Aucun mapping existant</div>
          )}
        </div>
      )}
    </div>
  )
}

export default ProductMappingInterface
