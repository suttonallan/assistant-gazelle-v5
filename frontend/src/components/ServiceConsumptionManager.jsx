import React, { useState, useEffect } from 'react'

import { API_URL } from '../utils/apiConfig'

/**
 * Interface moderne "Industrial Clean" pour gérer les associations service → matériaux
 * Design: Beaucoup d'espace blanc, bordures fines, sans fioritures
 */
const ServiceConsumptionManager = () => {
  const [services, setServices] = useState([])
  const [materials, setMaterials] = useState([])
  const [rules, setRules] = useState([])
  const [selectedServiceCode, setSelectedServiceCode] = useState(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [materialSearch, setMaterialSearch] = useState('')
  const [showOnlyTracked, setShowOnlyTracked] = useState(false)
  const [favorites, setFavorites] = useState([])

  // Charger les données au montage
  useEffect(() => {
    loadData()
    loadFavorites()
  }, [])

  const loadData = async () => {
    try {
      setLoading(true)
      const currentSelectedCode = selectedServiceCode

      // Charger catalogue et règles en parallèle
      const [catalogueData, rulesData] = await Promise.all([
        (async () => {
          const res = await fetch(`${API_URL}/api/inventaire/catalogue`)
          if (!res.ok) throw new Error('Erreur chargement catalogue')
          return res.json()
        })(),
        (async () => {
          const res = await fetch(`${API_URL}/api/inventaire/service-consumption/rules`)
          if (res.ok) {
            return res.json()
          }
          return { rules: [] }
        })()
      ])

      const allProducts = catalogueData.produits || []

      // ============================================================
      // ULTRA SIMPLE: Pas de logique compliquée
      // ============================================================

      // GAUCHE: Services MSL marqués "suivi stock" (is_inventory_item = true)
      // "Suivi stock" sur un service = ce service CONSOMME des fournitures
      const servicesList = allProducts.filter(p =>
        p.gazelle_product_id != null &&
        p.is_inventory_item === true
      )

      // DROITE: TOUS les items d'inventaire interne (sans gazelle_product_id)
      // Ce sont les fournitures disponibles pour être associées aux services
      const materialsList = allProducts.filter(p =>
        !p.gazelle_product_id &&
        p.code_produit != null
      )

      console.log('📊 MSL Gazelle vs Inventaire:', {
        total: allProducts.length,
        msl_gauche: servicesList.length,
        inventaire_droite: materialsList.length
      })

      setServices(servicesList)
      setMaterials(materialsList)
      setRules(rulesData.rules || [])

      if (currentSelectedCode) {
        const exists = servicesList.some(s => s.code_produit === currentSelectedCode)
        if (exists) {
          setSelectedServiceCode(currentSelectedCode)
        } else if (servicesList.length > 0) {
          setSelectedServiceCode(servicesList[0].code_produit)
        } else {
          setSelectedServiceCode(null)
        }
      } else if (!selectedServiceCode && servicesList.length > 0) {
        // Auto-sélectionner le premier service si rien n'est sélectionné
        setSelectedServiceCode(servicesList[0].code_produit)
      }

    } catch (err) {
      console.error('Erreur chargement données:', err)
    } finally {
      setLoading(false)
    }
  }

  const loadFavorites = () => {
    // Charger favoris depuis localStorage
    const saved = localStorage.getItem('inventory_favorite_services')
    if (saved) {
      try {
        setFavorites(JSON.parse(saved))
      } catch (e) {
        setFavorites([])
      }
    }
  }

  const saveFavorites = (newFavorites) => {
    localStorage.setItem('inventory_favorite_services', JSON.stringify(newFavorites))
    setFavorites(newFavorites)
  }

  const toggleFavorite = (serviceId) => {
    const newFavorites = favorites.includes(serviceId)
      ? favorites.filter(id => id !== serviceId)
      : [...favorites, serviceId]
    saveFavorites(newFavorites)
  }

  // Toggle suivi inventaire pour un service
  const toggleInventoryTracking = async (service) => {
    try {
      setSaving(true)

      const newValue = !service.is_inventory_item

      const res = await fetch(`${API_URL}/api/inventaire/catalogue/${service.code_produit}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ...service,
          is_inventory_item: newValue,
          usage_type: newValue ? 'both' : (service.usage_type === 'both' ? 'commission' : service.usage_type)
        })
      })

      if (!res.ok) throw new Error('Erreur mise à jour')

      await loadData()

    } catch (err) {
      alert('Erreur: ' + err.message)
    } finally {
      setSaving(false)
    }
  }

  // Obtenir les règles pour un service donné
  const getRulesForService = (serviceId) => {
    return rules.filter(r =>
      r.service_gazelle_id === serviceId ||
      r.service_code_produit === serviceId
    )
  }

  // Ajouter un matériau à un service
  const addMaterialToService = async (materialCodeProduit, quantity = 1, isOptional = false) => {
    const selectedService = services.find(s => s.code_produit === selectedServiceCode)
    if (!selectedService) return

    try {
      setSaving(true)

      const payload = {
        service_gazelle_id: selectedService.gazelle_product_id || selectedService.code_produit,
        service_code_produit: selectedService.code_produit,
        material_code_produit: materialCodeProduit,
        quantity: parseFloat(quantity),
        is_optional: isOptional,
        notes: ''
      }

      const res = await fetch(`${API_URL}/api/inventaire/service-consumption/rules`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      })

      if (!res.ok) {
        const error = await res.json()
        throw new Error(error.detail || 'Erreur création règle')
      }

      await loadData()
      setMaterialSearch('')

    } catch (err) {
      alert('Erreur: ' + err.message)
    } finally {
      setSaving(false)
    }
  }

  // Supprimer une règle
  const deleteRule = async (ruleId) => {
    if (!confirm('Supprimer cette association?')) return

    try {
      setSaving(true)

      const res = await fetch(`${API_URL}/api/inventaire/service-consumption/rules/${ruleId}`, {
        method: 'DELETE'
      })

      if (!res.ok) throw new Error('Erreur suppression')

      await loadData()

    } catch (err) {
      alert('Erreur: ' + err.message)
    } finally {
      setSaving(false)
    }
  }

  // Mettre à jour la quantité
  const updateQuantity = async (ruleId, newQuantity) => {
    const rule = rules.find(r => r.id === ruleId)
    if (!rule) return

    try {
      setSaving(true)

      await fetch(`${API_URL}/api/inventaire/service-consumption/rules/${ruleId}`, {
        method: 'DELETE'
      })

      await addMaterialToService(
        rule.material_code_produit,
        newQuantity,
        rule.is_optional
      )

    } catch (err) {
      alert('Erreur: ' + err.message)
    } finally {
      setSaving(false)
    }
  }

  // Filtrer les services
  let filteredServices = services.filter(s => {
    const matchesSearch = s.nom?.toLowerCase().includes(searchQuery.toLowerCase())
    const matchesTracked = !showOnlyTracked || Boolean(s.is_inventory_item)
    return matchesSearch && matchesTracked
  })

  // Trier: favoris en premier
  filteredServices = filteredServices.sort((a, b) => {
    const aFav = favorites.includes(a.code_produit) ? 1 : 0
    const bFav = favorites.includes(b.code_produit) ? 1 : 0
    if (aFav !== bFav) return bFav - aFav
    return (a.nom || '').localeCompare(b.nom || '')
  })

  // Compter les items non configurés (sans règles)
  const unconfiguredCount = services.filter(s => {
    const hasRules = getRulesForService(s.gazelle_product_id || s.code_produit).length > 0
    return !hasRules
  }).length

  const selectedService = services.find(s => s.code_produit === selectedServiceCode) || null
  const serviceRules = selectedService ? getRulesForService(
    selectedService.gazelle_product_id || selectedService.code_produit
  ) : []

  // Filtrer matériaux pour la recherche
  const filteredMaterials = materials.filter(m => {
    if (!materialSearch) return true
    return m.nom?.toLowerCase().includes(materialSearch.toLowerCase()) ||
           m.code_produit?.toLowerCase().includes(materialSearch.toLowerCase())
  })

  if (loading) {
    return (
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        height: '400px',
        fontSize: '14px',
        color: '#999',
        fontWeight: '300'
      }}>
        Chargement...
      </div>
    )
  }

  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      gap: '24px',
      height: '100%',
      minHeight: '700px',
      fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif'
    }}>

      {/* Header avec contrôles */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        paddingBottom: '16px',
        borderBottom: '1px solid #e0e0e0'
      }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <h2 style={{
              margin: 0,
              fontSize: '20px',
              fontWeight: '400',
              color: '#1a1a1a',
              letterSpacing: '-0.02em'
            }}>
              Consommation de matériaux
            </h2>
            {unconfiguredCount > 0 && (
              <span style={{
                fontSize: '11px',
                fontWeight: '500',
                padding: '4px 10px',
                borderRadius: '4px',
                backgroundColor: '#ff9800',
                color: 'white',
                textTransform: 'uppercase',
                letterSpacing: '0.3px'
              }}>
                {unconfiguredCount} à configurer
              </span>
            )}
          </div>
          <p style={{
            margin: '4px 0 0 0',
            fontSize: '13px',
            color: '#666',
            fontWeight: '300'
          }}>
            Associez les services aux matériaux consommés
          </p>
        </div>

        <label style={{
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          fontSize: '13px',
          color: '#444',
          cursor: 'pointer',
          userSelect: 'none'
        }}>
          <input
            type="checkbox"
            checked={showOnlyTracked}
            onChange={(e) => setShowOnlyTracked(e.target.checked)}
            style={{ cursor: 'pointer' }}
          />
          Afficher uniquement les services suivis
        </label>
      </div>

      {/* Contenu principal */}
      <div style={{ display: 'flex', gap: '24px', flex: 1 }}>

        {/* Panneau gauche: Liste des services */}
        <div style={{
          flex: '0 0 420px',
          display: 'flex',
          flexDirection: 'column',
          gap: '12px'
        }}>

          {/* Barre de recherche */}
          <input
            type="text"
            placeholder="Rechercher un service..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            style={{
              padding: '10px 14px',
              border: '1px solid #d0d0d0',
              borderRadius: '4px',
              fontSize: '13px',
              fontWeight: '300',
              outline: 'none',
              transition: 'border-color 0.15s ease'
            }}
            onFocus={(e) => e.target.style.borderColor = '#2196F3'}
            onBlur={(e) => e.target.style.borderColor = '#d0d0d0'}
          />

          {/* Liste des services */}
          <div style={{
            flex: 1,
            overflowY: 'auto',
            border: '1px solid #e0e0e0',
            borderRadius: '4px',
            backgroundColor: '#fafafa'
          }}>
            {filteredServices.length === 0 ? (
              <div style={{
                padding: '18px',
                fontSize: '13px',
                color: '#999',
                textAlign: 'center',
                fontWeight: '300'
              }}>
                Aucun service {showOnlyTracked ? 'avec suivi activé' : 'trouvé'}
              </div>
            ) : (
              filteredServices.map(service => {
                const hasRules = getRulesForService(
                  service.gazelle_product_id || service.code_produit
                ).length > 0
                const isSelected = selectedServiceCode === service.code_produit
                const isFavorite = favorites.includes(service.code_produit)
                const isTracked = service.is_inventory_item === true

                // Item "Nouveau / Non configuré" = Aucune règle de consommation
                const isUnconfigured = !hasRules

                return (
                <div
                  key={service.code_produit}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '10px',
                    padding: '12px 14px',
                    borderBottom: '1px solid #e8e8e8',
                    backgroundColor: isSelected ? '#f0f7ff' : '#fff',
                    borderLeft: isSelected ? '2px solid #2196F3' : '2px solid transparent',
                    cursor: 'pointer',
                    transition: 'all 0.12s ease'
                  }}
                  onClick={() => {
                    console.log('👉 Sélection service', {
                      code_produit: service.code_produit,
                      nom: service.nom,
                      type_produit: service.type_produit,
                      categorie: service.categorie
                    })
                    setSelectedServiceCode(service.code_produit)
                  }}
                >
                    {/* Étoile favori */}
                    <button
                      onClick={(e) => {
                        e.stopPropagation()
                        toggleFavorite(service.code_produit)
                      }}
                      style={{
                        background: 'none',
                        border: 'none',
                        cursor: 'pointer',
                        fontSize: '16px',
                        padding: 0,
                        lineHeight: 1,
                        opacity: isFavorite ? 1 : 0.3,
                        transition: 'opacity 0.15s ease'
                      }}
                    >
                      ⭐
                    </button>

                    {/* Nom du service */}
                    <span style={{
                      fontSize: '13px',
                      fontWeight: isSelected ? '400' : '300',
                      flex: 1,
                      color: '#1a1a1a'
                    }}>
                      {service.nom}
                    </span>

                    {/* Badge "Nouveau / À configurer" si aucune règle */}
                    {isUnconfigured && (
                      <span style={{
                        fontSize: '10px',
                        fontWeight: '500',
                        padding: '3px 8px',
                        borderRadius: '3px',
                        backgroundColor: '#ff9800',
                        color: 'white',
                        textTransform: 'uppercase',
                        letterSpacing: '0.3px'
                      }}>
                        À configurer
                      </span>
                    )}

                    {/* Badge nombre de règles */}
                    {hasRules && (
                      <span style={{
                        backgroundColor: '#4CAF50',
                        color: '#fff',
                        padding: '2px 7px',
                        borderRadius: '10px',
                        fontSize: '10px',
                        fontWeight: '500',
                        lineHeight: 1.4
                      }}>
                        {getRulesForService(service.gazelle_product_id || service.code_produit).length}
                      </span>
                    )}

                    {/* Toggle suivi */}
                    <button
                      onClick={(e) => {
                        e.stopPropagation()
                        toggleInventoryTracking(service)
                      }}
                      disabled={saving}
                      style={{
                        width: '40px',
                        height: '20px',
                        borderRadius: '10px',
                        border: '1px solid #d0d0d0',
                        backgroundColor: isTracked ? '#4CAF50' : '#e0e0e0',
                        position: 'relative',
                        cursor: 'pointer',
                        transition: 'all 0.2s ease',
                        padding: 0
                      }}
                    >
                      <div style={{
                        width: '14px',
                        height: '14px',
                        borderRadius: '50%',
                        backgroundColor: '#fff',
                        position: 'absolute',
                        top: '2px',
                        left: isTracked ? '22px' : '2px',
                        transition: 'left 0.2s ease',
                        boxShadow: '0 1px 2px rgba(0,0,0,0.2)'
                      }} />
                    </button>
                  </div>
                )
              })
            )}
          </div>

          <div style={{ fontSize: '11px', color: '#999', fontWeight: '300', textAlign: 'center' }}>
            {filteredServices.length} service{filteredServices.length > 1 ? 's' : ''}
          </div>
        </div>

        {/* Panneau droit: Matériaux consommés */}
        <div style={{
          flex: 1,
          display: 'flex',
          flexDirection: 'column',
          gap: '16px',
          backgroundColor: '#fff',
          border: '1px solid #e0e0e0',
          borderRadius: '4px',
          padding: '24px'
        }}>
          {selectedService ? (
            <>
              {/* En-tête du service sélectionné */}
              <div style={{ borderBottom: '1px solid #f0f0f0', paddingBottom: '16px' }}>
                <h3 style={{
                  margin: '0 0 6px 0',
                  fontSize: '16px',
                  fontWeight: '400',
                  color: '#1a1a1a',
                  letterSpacing: '-0.01em'
                }}>
                  {selectedService.nom}
                </h3>
                <p style={{
                  margin: 0,
                  fontSize: '12px',
                  color: '#666',
                  fontWeight: '300'
                }}>
                  Matériaux consommés lors de ce service
                  {selectedService.prix_unitaire && (
                    <span style={{ marginLeft: '8px', color: '#999' }}>
                      • {selectedService.prix_unitaire.toFixed(2)} $
                    </span>
                  )}
                </p>
              </div>

              {/* Liste des matériaux associés */}
              <div style={{ flex: 1, overflowY: 'auto' }}>
                {serviceRules.length === 0 ? (
                  <div style={{
                    textAlign: 'center',
                    padding: '60px 20px',
                    color: '#bbb',
                    fontSize: '13px',
                    fontWeight: '300'
                  }}>
                    Aucun matériau associé
                    <div style={{ fontSize: '11px', marginTop: '6px', color: '#ddd' }}>
                      Ajoutez des matériaux ci-dessous
                    </div>
                  </div>
                ) : (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                    {serviceRules.map(rule => {
                      const material = materials.find(m => m.code_produit === rule.material_code_produit)

                      return (
                        <div
                          key={rule.id}
                          style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: '12px',
                            padding: '14px',
                            backgroundColor: '#fafafa',
                            borderRadius: '4px',
                            border: '1px solid #e8e8e8'
                          }}
                        >
                          <div style={{ flex: 1 }}>
                            <div style={{ fontWeight: '400', fontSize: '13px', color: '#1a1a1a' }}>
                              {material?.nom || rule.material_code_produit}
                            </div>
                            {material?.categorie && (
                              <div style={{ fontSize: '11px', color: '#999', marginTop: '2px', fontWeight: '300' }}>
                                {material.categorie}
                              </div>
                            )}
                            {rule.is_optional && (
                              <span style={{
                                fontSize: '10px',
                                color: '#666',
                                backgroundColor: '#f0f0f0',
                                padding: '2px 6px',
                                borderRadius: '3px',
                                marginTop: '4px',
                                display: 'inline-block',
                                fontWeight: '300'
                              }}>
                                Optionnel
                              </span>
                            )}
                          </div>

                          <input
                            type="number"
                            step="0.1"
                            min="0"
                            value={rule.quantity}
                            onChange={(e) => {
                              const newQty = parseFloat(e.target.value) || 0
                              updateQuantity(rule.id, newQty)
                            }}
                            disabled={saving}
                            style={{
                              width: '70px',
                              padding: '6px 8px',
                              border: '1px solid #d0d0d0',
                              borderRadius: '3px',
                              textAlign: 'center',
                              fontSize: '13px',
                              fontWeight: '300'
                            }}
                          />

                          <button
                            onClick={() => deleteRule(rule.id)}
                            disabled={saving}
                            style={{
                              padding: '6px 10px',
                              backgroundColor: '#fff',
                              border: '1px solid #d0d0d0',
                              borderRadius: '3px',
                              cursor: 'pointer',
                              fontSize: '16px',
                              color: '#f44336',
                              lineHeight: 1,
                              transition: 'all 0.15s ease'
                            }}
                            onMouseEnter={(e) => e.target.style.backgroundColor = '#ffebee'}
                            onMouseLeave={(e) => e.target.style.backgroundColor = '#fff'}
                          >
                            ×
                          </button>
                        </div>
                      )
                    })}
                  </div>
                )}
              </div>

              {/* Sélecteur pour ajouter un matériau avec recherche prédictive */}
              <div style={{
                padding: '16px',
                backgroundColor: '#f9f9f9',
                borderRadius: '4px',
                borderTop: '1px solid #e8e8e8'
              }}>
                <label style={{
                  display: 'block',
                  marginBottom: '8px',
                  fontSize: '12px',
                  fontWeight: '400',
                  color: '#444'
                }}>
                  Ajouter un matériau
                </label>

                {/* Recherche prédictive */}
                <input
                  type="text"
                  placeholder="Rechercher un matériau..."
                  value={materialSearch}
                  onChange={(e) => setMaterialSearch(e.target.value)}
                  style={{
                    width: '100%',
                    padding: '10px 12px',
                    border: '1px solid #d0d0d0',
                    borderRadius: '4px 4px 0 0',
                    fontSize: '13px',
                    fontWeight: '300',
                    outline: 'none'
                  }}
                />

                {/* Liste déroulante filtrée */}
                {materialSearch && (
                  <div style={{
                    maxHeight: '200px',
                    overflowY: 'auto',
                    border: '1px solid #d0d0d0',
                    borderTop: 'none',
                    borderRadius: '0 0 4px 4px',
                    backgroundColor: '#fff'
                  }}>
                    {filteredMaterials
                      .filter(m => !serviceRules.find(r => r.material_code_produit === m.code_produit))
                      .slice(0, 10)
                      .map(material => (
                        <div
                          key={material.code_produit}
                          onClick={() => {
                            addMaterialToService(material.code_produit, 1, false)
                          }}
                          style={{
                            padding: '10px 12px',
                            cursor: 'pointer',
                            fontSize: '13px',
                            borderBottom: '1px solid #f0f0f0',
                            transition: 'background-color 0.12s ease'
                          }}
                          onMouseEnter={(e) => e.target.style.backgroundColor = '#f5f5f5'}
                          onMouseLeave={(e) => e.target.style.backgroundColor = '#fff'}
                        >
                          <div style={{ fontWeight: '400', color: '#1a1a1a' }}>
                            {material.nom}
                          </div>
                          {material.categorie && (
                            <div style={{ fontSize: '11px', color: '#999', marginTop: '2px', fontWeight: '300' }}>
                              {material.categorie}
                            </div>
                          )}
                        </div>
                      ))
                    }
                    {filteredMaterials.filter(m => !serviceRules.find(r => r.material_code_produit === m.code_produit)).length === 0 && (
                      <div style={{ padding: '10px 12px', fontSize: '12px', color: '#999', fontWeight: '300' }}>
                        Aucun matériau trouvé
                      </div>
                    )}
                  </div>
                )}
              </div>

            </>
          ) : (
            <div style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              height: '100%',
              color: '#bbb',
              fontSize: '13px',
              fontWeight: '300'
            }}>
              Sélectionnez un service pour voir/modifier les matériaux consommés
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default ServiceConsumptionManager
