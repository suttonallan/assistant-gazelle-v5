import React, { useState, useEffect } from 'react'
import { supabase } from '../lib/supabase'

const MSLFilterManager = () => {
  const [mslItems, setMslItems] = useState([])
  const [consumptionRules, setConsumptionRules] = useState([])
  const [inventoryItems, setInventoryItems] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  // Filtres
  const [filterExcluded, setFilterExcluded] = useState('all') // 'all', 'excluded', 'included'
  const [filterType, setFilterType] = useState('all') // 'all', 'commission', 'inventory'
  const [searchTerm, setSearchTerm] = useState('')

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    try {
      setLoading(true)
      setError(null)

      if (!supabase) {
        throw new Error('Supabase non configuré (VITE_SUPABASE_URL / VITE_SUPABASE_ANON_KEY manquants)')
      }

      // Charger tous les items MSL (ceux qui ont un gazelle_product_id)
      const { data: mslData, error: mslError } = await supabase
        .from('produits_catalogue')
        .select('*')
        .not('gazelle_product_id', 'is', null)
        .order('nom')

      if (mslError) throw mslError

      // Charger les règles de consommation
      const { data: rulesData, error: rulesError } = await supabase
        .from('service_inventory_consumption')
        .select('*')

      if (rulesError) throw rulesError

      // Charger les items d'inventaire
      const { data: inventoryData, error: inventoryError } = await supabase
        .from('produits_catalogue')
        .select('*')
        .eq('is_inventory_item', true)
        .order('nom')

      if (inventoryError) throw inventoryError

      setMslItems(mslData || [])
      setConsumptionRules(rulesData || [])
      setInventoryItems(inventoryData || [])

      console.log('📊 MSL Data loaded:', {
        mslItems: mslData?.length,
        rules: rulesData?.length,
        inventoryItems: inventoryData?.length
      })

    } catch (err) {
      console.error('Erreur chargement MSL:', err)
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  // Déterminer si un item est exclu
  const isExcluded = (item) => {
    // Un item est exclu s'il n'a PAS de règle de consommation ET n'est pas marqué comme affectant la commission
    const hasConsumptionRule = consumptionRules.some(
      rule => rule.service_gazelle_id === item.gazelle_product_id
    )
    const affectsCommission = item.affects_commission === true

    return !hasConsumptionRule && !affectsCommission
  }

  // Déterminer le type (commission ou inventaire)
  const getItemType = (item) => {
    const hasConsumptionRule = consumptionRules.some(
      rule => rule.service_gazelle_id === item.gazelle_product_id
    )

    if (hasConsumptionRule) return 'inventory'
    if (item.affects_commission === true) return 'commission'
    return 'none'
  }

  // Obtenir les associations d'inventaire pour un item
  const getInventoryAssociations = (item) => {
    const rules = consumptionRules.filter(
      rule => rule.service_gazelle_id === item.gazelle_product_id
    )

    return rules.map(rule => {
      const material = inventoryItems.find(
        inv => inv.code_produit === rule.material_code_produit
      )
      return {
        ...rule,
        material_name: material?.nom || rule.material_code_produit
      }
    })
  }

  // Filtrer les items
  const filteredItems = mslItems.filter(item => {
    // Filtre recherche
    if (searchTerm && !item.nom?.toLowerCase().includes(searchTerm.toLowerCase())) {
      return false
    }

    // Filtre exclu/inclus
    if (filterExcluded === 'excluded' && !isExcluded(item)) return false
    if (filterExcluded === 'included' && isExcluded(item)) return false

    // Filtre type
    if (filterType === 'commission' && getItemType(item) !== 'commission') return false
    if (filterType === 'inventory' && getItemType(item) !== 'inventory') return false

    return true
  })

  // Statistiques
  const stats = {
    total: mslItems.length,
    excluded: mslItems.filter(isExcluded).length,
    included: mslItems.filter(item => !isExcluded(item)).length,
    commission: mslItems.filter(item => getItemType(item) === 'commission').length,
    inventory: mslItems.filter(item => getItemType(item) === 'inventory').length,
    none: mslItems.filter(item => getItemType(item) === 'none').length
  }

  // Toggle affect commission
  const toggleAffectsCommission = async (item) => {
    try {
      const newValue = !item.affects_commission

      const { error } = await supabase
        .from('produits_catalogue')
        .update({ affects_commission: newValue })
        .eq('id', item.id)

      if (error) throw error

      // Recharger les données
      await loadData()

    } catch (err) {
      console.error('Erreur toggle commission:', err)
      alert('Erreur lors de la mise à jour')
    }
  }

  if (loading) {
    return (
      <div style={{ padding: '20px', textAlign: 'center' }}>
        <p>Chargement des items MSL...</p>
      </div>
    )
  }

  if (error) {
    return (
      <div style={{ padding: '20px', color: '#e74c3c' }}>
        <p>Erreur: {error}</p>
        <button onClick={loadData}>Réessayer</button>
      </div>
    )
  }

  return (
    <div style={{ padding: '20px', maxWidth: '1400px', margin: '0 auto' }}>
      {/* Header */}
      <div style={{ marginBottom: '20px' }}>
        <h2 style={{
          fontSize: '18px',
          fontWeight: '300',
          margin: '0 0 10px 0',
          color: '#2c3e50'
        }}>
          📋 Gestion des Items MSL Gazelle
        </h2>
        <p style={{
          fontSize: '13px',
          color: '#7f8c8d',
          margin: 0,
          fontWeight: '300'
        }}>
          Visualisez et filtrez tous les items de la Master Service List importés depuis Gazelle API
        </p>
      </div>

      {/* Statistiques */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))',
        gap: '10px',
        marginBottom: '20px'
      }}>
        <div style={{
          padding: '12px',
          backgroundColor: '#f8f9fa',
          borderRadius: '4px',
          border: '1px solid #e0e0e0'
        }}>
          <div style={{ fontSize: '11px', color: '#7f8c8d', marginBottom: '4px' }}>TOTAL MSL</div>
          <div style={{ fontSize: '20px', fontWeight: '300', color: '#2c3e50' }}>{stats.total}</div>
        </div>
        <div style={{
          padding: '12px',
          backgroundColor: '#f8f9fa',
          borderRadius: '4px',
          border: '1px solid #e0e0e0'
        }}>
          <div style={{ fontSize: '11px', color: '#7f8c8d', marginBottom: '4px' }}>INCLUS</div>
          <div style={{ fontSize: '20px', fontWeight: '300', color: '#27ae60' }}>{stats.included}</div>
        </div>
        <div style={{
          padding: '12px',
          backgroundColor: '#f8f9fa',
          borderRadius: '4px',
          border: '1px solid #e0e0e0'
        }}>
          <div style={{ fontSize: '11px', color: '#7f8c8d', marginBottom: '4px' }}>EXCLUS</div>
          <div style={{ fontSize: '20px', fontWeight: '300', color: '#95a5a6' }}>{stats.excluded}</div>
        </div>
        <div style={{
          padding: '12px',
          backgroundColor: '#f8f9fa',
          borderRadius: '4px',
          border: '1px solid #e0e0e0'
        }}>
          <div style={{ fontSize: '11px', color: '#7f8c8d', marginBottom: '4px' }}>COMMISSION</div>
          <div style={{ fontSize: '20px', fontWeight: '300', color: '#3498db' }}>{stats.commission}</div>
        </div>
        <div style={{
          padding: '12px',
          backgroundColor: '#f8f9fa',
          borderRadius: '4px',
          border: '1px solid #e0e0e0'
        }}>
          <div style={{ fontSize: '11px', color: '#7f8c8d', marginBottom: '4px' }}>INVENTAIRE</div>
          <div style={{ fontSize: '20px', fontWeight: '300', color: '#9b59b6' }}>{stats.inventory}</div>
        </div>
      </div>

      {/* Filtres */}
      <div style={{
        display: 'flex',
        gap: '10px',
        marginBottom: '20px',
        flexWrap: 'wrap',
        alignItems: 'center'
      }}>
        <input
          type="text"
          placeholder="Rechercher un item..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          style={{
            padding: '8px 12px',
            border: '1px solid #ddd',
            borderRadius: '4px',
            fontSize: '13px',
            flex: '1',
            minWidth: '200px'
          }}
        />

        <select
          value={filterExcluded}
          onChange={(e) => setFilterExcluded(e.target.value)}
          style={{
            padding: '8px 12px',
            border: '1px solid #ddd',
            borderRadius: '4px',
            fontSize: '13px',
            backgroundColor: 'white'
          }}
        >
          <option value="all">Tous les items</option>
          <option value="included">Inclus uniquement</option>
          <option value="excluded">Exclus uniquement</option>
        </select>

        <select
          value={filterType}
          onChange={(e) => setFilterType(e.target.value)}
          style={{
            padding: '8px 12px',
            border: '1px solid #ddd',
            borderRadius: '4px',
            fontSize: '13px',
            backgroundColor: 'white'
          }}
        >
          <option value="all">Tous les types</option>
          <option value="commission">Commission</option>
          <option value="inventory">Inventaire</option>
        </select>

        <button
          onClick={loadData}
          style={{
            padding: '8px 12px',
            backgroundColor: '#3498db',
            color: 'white',
            border: 'none',
            borderRadius: '4px',
            fontSize: '13px',
            cursor: 'pointer'
          }}
        >
          🔄 Actualiser
        </button>
      </div>

      {/* Résultats filtrés */}
      <div style={{ fontSize: '12px', color: '#7f8c8d', marginBottom: '10px' }}>
        {filteredItems.length} résultat{filteredItems.length > 1 ? 's' : ''}
      </div>

      {/* Table des items */}
      <div style={{
        backgroundColor: 'white',
        border: '1px solid #e0e0e0',
        borderRadius: '4px',
        overflow: 'hidden'
      }}>
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ backgroundColor: '#f8f9fa' }}>
              <th style={headerStyle}>Item MSL</th>
              <th style={headerStyle}>ID Gazelle</th>
              <th style={headerStyle}>Type</th>
              <th style={headerStyle}>Statut</th>
              <th style={headerStyle}>Commission</th>
              <th style={headerStyle}>Associations Inventaire</th>
            </tr>
          </thead>
          <tbody>
            {filteredItems.map((item) => {
              const itemType = getItemType(item)
              const excluded = isExcluded(item)
              const associations = getInventoryAssociations(item)

              return (
                <tr key={item.id} style={{ borderBottom: '1px solid #f0f0f0' }}>
                  <td style={cellStyle}>
                    <div style={{ fontWeight: '400', color: '#2c3e50' }}>{item.nom}</div>
                    {item.description && (
                      <div style={{ fontSize: '11px', color: '#95a5a6', marginTop: '2px' }}>
                        {item.description}
                      </div>
                    )}
                  </td>
                  <td style={cellStyle}>
                    <code style={{
                      fontSize: '11px',
                      backgroundColor: '#f8f9fa',
                      padding: '2px 6px',
                      borderRadius: '3px',
                      color: '#7f8c8d'
                    }}>
                      {item.gazelle_product_id}
                    </code>
                  </td>
                  <td style={cellStyle}>
                    <span style={{ fontSize: '12px', color: '#7f8c8d' }}>
                      {item.type_produit || 'N/A'}
                    </span>
                  </td>
                  <td style={cellStyle}>
                    {excluded ? (
                      <span style={{
                        display: 'inline-block',
                        padding: '3px 8px',
                        backgroundColor: '#ecf0f1',
                        color: '#7f8c8d',
                        borderRadius: '3px',
                        fontSize: '11px',
                        fontWeight: '400'
                      }}>
                        EXCLU
                      </span>
                    ) : (
                      <span style={{
                        display: 'inline-block',
                        padding: '3px 8px',
                        backgroundColor: '#d5f4e6',
                        color: '#27ae60',
                        borderRadius: '3px',
                        fontSize: '11px',
                        fontWeight: '400'
                      }}>
                        INCLUS
                      </span>
                    )}
                  </td>
                  <td style={cellStyle}>
                    <label style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '6px',
                      cursor: 'pointer',
                      fontSize: '12px'
                    }}>
                      <input
                        type="checkbox"
                        checked={item.affects_commission || false}
                        onChange={() => toggleAffectsCommission(item)}
                        style={{ cursor: 'pointer' }}
                      />
                      <span style={{ color: item.affects_commission ? '#3498db' : '#95a5a6' }}>
                        {item.affects_commission ? 'Oui' : 'Non'}
                      </span>
                    </label>
                  </td>
                  <td style={cellStyle}>
                    {associations.length > 0 ? (
                      <div style={{ fontSize: '12px' }}>
                        {associations.map((assoc, idx) => (
                          <div key={idx} style={{
                            marginBottom: '4px',
                            padding: '4px 8px',
                            backgroundColor: '#f8f9fa',
                            borderRadius: '3px',
                            display: 'inline-block',
                            marginRight: '4px'
                          }}>
                            <span style={{ color: '#2c3e50' }}>{assoc.material_name}</span>
                            <span style={{ color: '#7f8c8d', marginLeft: '4px' }}>
                              (×{assoc.quantity})
                            </span>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <span style={{ fontSize: '12px', color: '#95a5a6' }}>
                        Aucune association
                      </span>
                    )}
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>

        {filteredItems.length === 0 && (
          <div style={{
            padding: '40px',
            textAlign: 'center',
            color: '#95a5a6',
            fontSize: '13px'
          }}>
            Aucun item ne correspond aux filtres sélectionnés
          </div>
        )}
      </div>

      {/* Légende */}
      <div style={{
        marginTop: '20px',
        padding: '15px',
        backgroundColor: '#f8f9fa',
        borderRadius: '4px',
        fontSize: '12px',
        color: '#7f8c8d',
        lineHeight: '1.6'
      }}>
        <div style={{ fontWeight: '400', marginBottom: '8px', color: '#2c3e50' }}>
          📖 Légende
        </div>
        <div><strong>EXCLU:</strong> Item sans règle de consommation et sans impact commission</div>
        <div><strong>INCLUS:</strong> Item avec règle de consommation OU impact commission</div>
        <div><strong>Commission:</strong> Item marqué comme affectant la commission (ex: Grand entretien)</div>
        <div><strong>Inventaire:</strong> Item avec règles de consommation de matériaux (ex: Entretien annuel PLS)</div>
      </div>
    </div>
  )
}

const headerStyle = {
  padding: '12px',
  textAlign: 'left',
  fontSize: '11px',
  fontWeight: '400',
  color: '#7f8c8d',
  textTransform: 'uppercase',
  letterSpacing: '0.5px',
  borderBottom: '1px solid #e0e0e0'
}

const cellStyle = {
  padding: '12px',
  fontSize: '13px',
  color: '#2c3e50',
  verticalAlign: 'top'
}

export default MSLFilterManager
