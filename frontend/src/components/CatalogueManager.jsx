import React, { useState, useEffect } from 'react'
import { supabase } from '../lib/supabase'

import { API_URL } from '../utils/apiConfig'

/**
 * Interface simplifiée pour gérer TOUS les items du catalogue
 * 3 colonnes simples: is_active, has_commission, consumes_stock (is_inventory_item)
 * L'utilisateur décide manuellement ce qu'il veut activer
 */
const CatalogueManager = () => {
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [searchTerm, setSearchTerm] = useState('')
  const [selectedItem, setSelectedItem] = useState(null)
  const [showMaterialModal, setShowMaterialModal] = useState(false)
  const [editingId, setEditingId] = useState(null)
  const [editDraft, setEditDraft] = useState({})
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    try {
      setLoading(true)
      setError(null)

      // Charger TOUS les items depuis l'API backend (comme l'onglet Admin)
      const response = await fetch(`${API_URL}/api/inventaire/catalogue`)
      if (!response.ok) throw new Error('Erreur chargement catalogue')

      const data = await response.json()
      const allItems = data.produits || []

      setItems(allItems)

      console.log('📦 Tous les items chargés depuis API:', allItems.length)

    } catch (err) {
      console.error('Erreur chargement:', err)
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  // Toggle une propriété booléenne
  const toggleProperty = async (item, property) => {
    try {
      const newValue = !item[property]

      const { error } = await supabase
        .from('produits_catalogue')
        .update({ [property]: newValue })
        .eq('id', item.id)

      if (error) throw error

      // Mettre à jour localement
      setItems(items.map(i =>
        i.id === item.id ? { ...i, [property]: newValue } : i
      ))

    } catch (err) {
      console.error('Erreur toggle:', err)
      alert('Erreur: ' + err.message)
    }
  }

  // Édition en place (nom, unité, prix, description)
  const startEdit = (item) => {
    setEditingId(item.id)
    setEditDraft({
      nom: item.nom || '',
      unite_mesure: item.unite_mesure || '',
      prix_unitaire: item.prix_unitaire ?? '',
      description: item.description || ''
    })
  }

  const cancelEdit = () => {
    setEditingId(null)
    setEditDraft({})
  }

  const saveEdit = async (item) => {
    try {
      setSaving(true)
      const payload = {
        nom: editDraft.nom,
        unite_mesure: editDraft.unite_mesure,
        prix_unitaire: editDraft.prix_unitaire === '' ? null : parseFloat(editDraft.prix_unitaire),
        description: editDraft.description
      }

      const response = await fetch(`${API_URL}/api/inventaire/catalogue/${encodeURIComponent(item.code_produit)}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      })
      const result = await response.json()
      if (!response.ok || !result.success) {
        throw new Error(result.detail || result.message || 'Échec de la mise à jour')
      }

      setItems(items.map(i => (i.id === item.id ? { ...i, ...payload } : i)))
      setEditingId(null)
      setEditDraft({})
    } catch (err) {
      console.error('Erreur édition:', err)
      alert('Erreur: ' + err.message)
    } finally {
      setSaving(false)
    }
  }

  // Filtrer les items
  const filteredItems = items.filter(item => {
    if (!searchTerm) return true
    const search = searchTerm.toLowerCase()
    return (
      item.nom?.toLowerCase().includes(search) ||
      item.code_produit?.toLowerCase().includes(search) ||
      item.categorie?.toLowerCase().includes(search)
    )
  })

  // Statistiques
  const stats = {
    total: items.length,
    active: items.filter(i => i.is_active !== false).length,
    commission: items.filter(i => i.has_commission === true).length,
    stock: items.filter(i => i.is_inventory_item === true).length
  }

  if (loading) {
    return (
      <div style={{ padding: '20px', textAlign: 'center' }}>
        <p>Chargement du catalogue...</p>
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
    <div style={{ padding: '20px', maxWidth: '1600px', margin: '0 auto' }}>
      {/* Header */}
      <div style={{ marginBottom: '20px' }}>
        <h2 style={{
          fontSize: '18px',
          fontWeight: '300',
          margin: '0 0 10px 0',
          color: '#2c3e50'
        }}>
          📦 Gestion du Catalogue Complet
        </h2>
        <p style={{
          fontSize: '13px',
          color: '#7f8c8d',
          margin: 0,
          fontWeight: '300'
        }}>
          Tous les items - Tu décides ce qui est actif, commissionné, et suivi en stock
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
          <div style={{ fontSize: '11px', color: '#7f8c8d', marginBottom: '4px' }}>TOTAL</div>
          <div style={{ fontSize: '20px', fontWeight: '300', color: '#2c3e50' }}>{stats.total}</div>
        </div>
        <div style={{
          padding: '12px',
          backgroundColor: '#f8f9fa',
          borderRadius: '4px',
          border: '1px solid #e0e0e0'
        }}>
          <div style={{ fontSize: '11px', color: '#7f8c8d', marginBottom: '4px' }}>ACTIFS</div>
          <div style={{ fontSize: '20px', fontWeight: '300', color: '#27ae60' }}>{stats.active}</div>
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
          <div style={{ fontSize: '11px', color: '#7f8c8d', marginBottom: '4px' }}>SUIVI STOCK</div>
          <div style={{ fontSize: '20px', fontWeight: '300', color: '#9b59b6' }}>{stats.stock}</div>
        </div>
      </div>

      {/* Barre de recherche */}
      <div style={{
        display: 'flex',
        gap: '10px',
        marginBottom: '20px',
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
            flex: '1'
          }}
        />

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

      {/* Résultats */}
      <div style={{ fontSize: '12px', color: '#7f8c8d', marginBottom: '10px' }}>
        {filteredItems.length} résultat{filteredItems.length > 1 ? 's' : ''}
      </div>

      {/* Table */}
      <div style={{
        backgroundColor: 'white',
        border: '1px solid #e0e0e0',
        borderRadius: '4px',
        overflow: 'auto',
        maxHeight: '600px'
      }}>
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead style={{ position: 'sticky', top: 0, backgroundColor: '#f8f9fa', zIndex: 10 }}>
            <tr>
              <th style={headerStyle}>Item</th>
              <th style={headerStyle}>Code</th>
              <th style={headerStyle}>Catégorie</th>
              <th style={headerStyle}>Unité</th>
              <th style={headerStyle}>Prix</th>
              <th style={{ ...headerStyle, textAlign: 'center' }}>Actif</th>
              <th style={{ ...headerStyle, textAlign: 'center' }}>Commission</th>
              <th style={{ ...headerStyle, textAlign: 'center' }}>Suivi Stock</th>
              <th style={headerStyle}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {filteredItems.map((item) => {
              const isEditing = editingId === item.id
              return (
              <tr key={item.id} style={{ borderBottom: '1px solid #f0f0f0' }}>
                <td style={cellStyle}>
                  {isEditing ? (
                    <>
                      <input
                        type="text"
                        value={editDraft.nom}
                        onChange={(e) => setEditDraft({ ...editDraft, nom: e.target.value })}
                        style={editInputStyle}
                      />
                      <textarea
                        value={editDraft.description}
                        onChange={(e) => setEditDraft({ ...editDraft, description: e.target.value })}
                        placeholder="Description (usage interne)"
                        rows={2}
                        style={{ ...editInputStyle, marginTop: '4px', resize: 'vertical' }}
                      />
                    </>
                  ) : (
                    <>
                      <div style={{ fontWeight: '400', color: '#2c3e50' }}>{item.nom}</div>
                      {item.gazelle_product_id && (
                        <div style={{ fontSize: '10px', color: '#95a5a6', marginTop: '2px' }}>
                          MSL: {item.gazelle_product_id}
                        </div>
                      )}
                    </>
                  )}
                </td>
                <td style={cellStyle}>
                  <code style={{
                    fontSize: '11px',
                    backgroundColor: '#f8f9fa',
                    padding: '2px 6px',
                    borderRadius: '3px'
                  }}>
                    {item.code_produit}
                  </code>
                </td>
                <td style={cellStyle}>
                  <span style={{ fontSize: '12px', color: '#7f8c8d' }}>
                    {item.categorie || 'N/A'}
                  </span>
                </td>
                <td style={cellStyle}>
                  {isEditing ? (
                    <input
                      type="text"
                      value={editDraft.unite_mesure}
                      onChange={(e) => setEditDraft({ ...editDraft, unite_mesure: e.target.value })}
                      style={editInputStyle}
                    />
                  ) : (
                    <span style={{ fontSize: '12px', color: '#7f8c8d' }}>
                      {item.unite_mesure || '-'}
                    </span>
                  )}
                </td>
                <td style={cellStyle}>
                  {isEditing ? (
                    <input
                      type="number"
                      step="0.01"
                      value={editDraft.prix_unitaire}
                      onChange={(e) => setEditDraft({ ...editDraft, prix_unitaire: e.target.value })}
                      style={{ ...editInputStyle, width: '80px' }}
                    />
                  ) : (
                    <span style={{ fontSize: '12px', color: '#2c3e50' }}>
                      {item.prix_unitaire ? `${item.prix_unitaire.toFixed(2)} $` : '-'}
                    </span>
                  )}
                </td>

                {/* Checkbox Actif */}
                <td style={{ ...cellStyle, textAlign: 'center' }}>
                  <input
                    type="checkbox"
                    checked={item.is_active !== false}
                    onChange={() => toggleProperty(item, 'is_active')}
                    style={{ cursor: 'pointer', width: '16px', height: '16px' }}
                  />
                </td>

                {/* Checkbox Commission */}
                <td style={{ ...cellStyle, textAlign: 'center' }}>
                  <input
                    type="checkbox"
                    checked={item.has_commission === true}
                    onChange={() => toggleProperty(item, 'has_commission')}
                    style={{ cursor: 'pointer', width: '16px', height: '16px' }}
                  />
                </td>

                {/* Checkbox Suivi Stock */}
                <td style={{ ...cellStyle, textAlign: 'center' }}>
                  <input
                    type="checkbox"
                    checked={item.is_inventory_item === true}
                    onChange={() => toggleProperty(item, 'is_inventory_item')}
                    style={{ cursor: 'pointer', width: '16px', height: '16px' }}
                  />
                </td>

                {/* Actions */}
                <td style={cellStyle}>
                  <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
                    {isEditing ? (
                      <>
                        <button
                          onClick={() => saveEdit(item)}
                          disabled={saving}
                          style={actionButtonStyle('#27ae60')}
                        >
                          {saving ? '...' : '✓ Enregistrer'}
                        </button>
                        <button onClick={cancelEdit} style={actionButtonStyle('#95a5a6')}>
                          Annuler
                        </button>
                      </>
                    ) : (
                      <button onClick={() => startEdit(item)} style={actionButtonStyle('#3498db')}>
                        ✏️ Éditer
                      </button>
                    )}
                    {item.is_inventory_item && (
                      <button
                        onClick={() => {
                          setSelectedItem(item)
                          setShowMaterialModal(true)
                        }}
                        style={actionButtonStyle('#9b59b6')}
                      >
                        🔗 Matériaux
                      </button>
                    )}
                  </div>
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
            Aucun item trouvé
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
          📖 Guide
        </div>
        <div><strong>Actif:</strong> Item visible dans l'inventaire des techniciens</div>
        <div><strong>Commission:</strong> Génère une commission pour le technicien lors de la vente</div>
        <div><strong>Suivi Stock:</strong> Quantités suivies dans l'inventaire (permet liaison avec matériaux)</div>
        <div><strong>Matériaux:</strong> Bouton visible seulement si "Suivi Stock" est coché</div>
      </div>

      {/* Modal Matériaux (placeholder - à implémenter) */}
      {showMaterialModal && selectedItem && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundColor: 'rgba(0,0,0,0.5)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 1000
        }}>
          <div style={{
            backgroundColor: 'white',
            padding: '20px',
            borderRadius: '8px',
            maxWidth: '600px',
            width: '90%'
          }}>
            <h3 style={{ margin: '0 0 15px 0', fontSize: '16px', fontWeight: '400' }}>
              Matériaux pour: {selectedItem.nom}
            </h3>
            <p style={{ fontSize: '13px', color: '#7f8c8d' }}>
              Interface de liaison avec les matériaux à venir...
            </p>
            <button
              onClick={() => {
                setShowMaterialModal(false)
                setSelectedItem(null)
              }}
              style={{
                marginTop: '15px',
                padding: '8px 16px',
                backgroundColor: '#95a5a6',
                color: 'white',
                border: 'none',
                borderRadius: '4px',
                cursor: 'pointer'
              }}
            >
              Fermer
            </button>
          </div>
        </div>
      )}
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
  verticalAlign: 'middle'
}

const editInputStyle = {
  width: '100%',
  padding: '4px 6px',
  fontSize: '12px',
  border: '1px solid #3498db',
  borderRadius: '3px',
  boxSizing: 'border-box'
}

const actionButtonStyle = (color) => ({
  padding: '4px 8px',
  fontSize: '11px',
  backgroundColor: color,
  color: 'white',
  border: 'none',
  borderRadius: '3px',
  cursor: 'pointer'
})

export default CatalogueManager
