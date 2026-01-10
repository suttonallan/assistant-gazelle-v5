import React, { useState, useEffect } from 'react'
import { API_URL } from '../utils/apiConfig'

/**
 * Configuration des Règles de Déduction d'Inventaire
 *
 * 3 systèmes de déduction intelligents:
 * 1. Règle globale automatique (fournitures/accessoires)
 * 2. Mapping de services (recettes)
 * 3. Détection par mots-clés dans les notes
 *
 * + Preview sécurisé avant validation
 */
export default function ConfigurationDeductions({ currentUser }) {
  // Onglets
  const [activeTab, setActiveTab] = useState('global') // global, services, keywords, preview

  // Règle globale
  const [globalRule, setGlobalRule] = useState({
    enabled: false,
    item_types: ['fourniture', 'accessoire']
  })
  const [loadingGlobal, setLoadingGlobal] = useState(true)

  // Règles de services (mapping)
  const [serviceRules, setServiceRules] = useState([])
  const [loadingServices, setLoadingServices] = useState(true)
  const [showServiceForm, setShowServiceForm] = useState(false)
  const [newServiceRule, setNewServiceRule] = useState({
    service_gazelle_id: '',
    service_code_produit: '',
    materials: [{ material_code_produit: '', quantity: 1.0, is_optional: false }]
  })

  // Règles de mots-clés
  const [keywordRules, setKeywordRules] = useState([])
  const [loadingKeywords, setLoadingKeywords] = useState(true)
  const [showKeywordForm, setShowKeywordForm] = useState(false)
  const [newKeywordRule, setNewKeywordRule] = useState({
    keyword: '',
    material_code_produit: '',
    quantity: 1.0,
    case_sensitive: false,
    notes: ''
  })

  // Preview
  const [previewData, setPreviewData] = useState(null)
  const [loadingPreview, setLoadingPreview] = useState(false)
  const [previewDays, setPreviewDays] = useState(7)

  const [error, setError] = useState(null)
  const [successMessage, setSuccessMessage] = useState(null)

  // Chargement initial
  useEffect(() => {
    if (activeTab === 'global') {
      loadGlobalRule()
    } else if (activeTab === 'services') {
      loadServiceRules()
    } else if (activeTab === 'keywords') {
      loadKeywordRules()
    }
  }, [activeTab])

  // ============================================================
  // RÈGLE GLOBALE
  // ============================================================

  const loadGlobalRule = async () => {
    try {
      setLoadingGlobal(true)
      const response = await fetch(`${API_URL}/api/inventaire/deduction-config/global-rule`)
      const data = await response.json()
      setGlobalRule(data.config)
      setError(null)
    } catch (err) {
      setError('Erreur chargement règle globale')
      console.error(err)
    } finally {
      setLoadingGlobal(false)
    }
  }

  const toggleGlobalRule = async () => {
    try {
      const newEnabled = !globalRule.enabled
      const response = await fetch(`${API_URL}/api/inventaire/deduction-config/global-rule`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          enabled: newEnabled,
          item_types: globalRule.item_types
        })
      })

      if (!response.ok) throw new Error('Erreur mise à jour')

      const data = await response.json()
      setGlobalRule(data.config)
      setSuccessMessage(`Règle globale ${newEnabled ? 'activée' : 'désactivée'}`)
      setTimeout(() => setSuccessMessage(null), 3000)
    } catch (err) {
      setError('Erreur mise à jour règle globale')
      console.error(err)
    }
  }

  // ============================================================
  // RÈGLES DE SERVICES
  // ============================================================

  const loadServiceRules = async () => {
    try {
      setLoadingServices(true)
      const response = await fetch(`${API_URL}/api/inventaire/service-consumption/rules?group_by_service=true`)
      const data = await response.json()
      setServiceRules(data.services || [])
      setError(null)
    } catch (err) {
      setError('Erreur chargement règles services')
      console.error(err)
    } finally {
      setLoadingServices(false)
    }
  }

  const addMaterialField = () => {
    setNewServiceRule({
      ...newServiceRule,
      materials: [...newServiceRule.materials, { material_code_produit: '', quantity: 1.0, is_optional: false }]
    })
  }

  const removeMaterialField = (index) => {
    const newMaterials = newServiceRule.materials.filter((_, i) => i !== index)
    setNewServiceRule({ ...newServiceRule, materials: newMaterials })
  }

  const updateMaterialField = (index, field, value) => {
    const newMaterials = [...newServiceRule.materials]
    newMaterials[index][field] = value
    setNewServiceRule({ ...newServiceRule, materials: newMaterials })
  }

  const saveServiceRule = async () => {
    try {
      const response = await fetch(`${API_URL}/api/inventaire/service-consumption/rules/batch`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newServiceRule)
      })

      if (!response.ok) throw new Error('Erreur création règle')

      const data = await response.json()
      setSuccessMessage(`${data.created} règle(s) créée(s)`)
      setTimeout(() => setSuccessMessage(null), 3000)

      // Réinitialiser le formulaire
      setNewServiceRule({
        service_gazelle_id: '',
        service_code_produit: '',
        materials: [{ material_code_produit: '', quantity: 1.0, is_optional: false }]
      })
      setShowServiceForm(false)
      loadServiceRules()
    } catch (err) {
      setError('Erreur création règle service')
      console.error(err)
    }
  }

  const deleteServiceRule = async (ruleId) => {
    if (!confirm('Supprimer cette règle?')) return

    try {
      const response = await fetch(`${API_URL}/api/inventaire/service-consumption/rules/${ruleId}`, {
        method: 'DELETE'
      })

      if (!response.ok) throw new Error('Erreur suppression')

      setSuccessMessage('Règle supprimée')
      setTimeout(() => setSuccessMessage(null), 3000)
      loadServiceRules()
    } catch (err) {
      setError('Erreur suppression règle')
      console.error(err)
    }
  }

  // ============================================================
  // RÈGLES DE MOTS-CLÉS
  // ============================================================

  const loadKeywordRules = async () => {
    try {
      setLoadingKeywords(true)
      const response = await fetch(`${API_URL}/api/inventaire/deduction-config/keyword-rules`)
      const data = await response.json()
      setKeywordRules(data.rules || [])
      setError(null)
    } catch (err) {
      setError('Erreur chargement règles mots-clés')
      console.error(err)
    } finally {
      setLoadingKeywords(false)
    }
  }

  const saveKeywordRule = async () => {
    try {
      const response = await fetch(`${API_URL}/api/inventaire/deduction-config/keyword-rules`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newKeywordRule)
      })

      if (!response.ok) throw new Error('Erreur création règle')

      setSuccessMessage('Règle créée')
      setTimeout(() => setSuccessMessage(null), 3000)

      // Réinitialiser
      setNewKeywordRule({
        keyword: '',
        material_code_produit: '',
        quantity: 1.0,
        case_sensitive: false,
        notes: ''
      })
      setShowKeywordForm(false)
      loadKeywordRules()
    } catch (err) {
      setError('Erreur création règle mot-clé')
      console.error(err)
    }
  }

  const deleteKeywordRule = async (ruleId) => {
    if (!confirm('Supprimer cette règle?')) return

    try {
      const response = await fetch(`${API_URL}/api/inventaire/deduction-config/keyword-rules/${ruleId}`, {
        method: 'DELETE'
      })

      if (!response.ok) throw new Error('Erreur suppression')

      setSuccessMessage('Règle supprimée')
      setTimeout(() => setSuccessMessage(null), 3000)
      loadKeywordRules()
    } catch (err) {
      setError('Erreur suppression règle')
      console.error(err)
    }
  }

  // ============================================================
  // PREVIEW SÉCURISÉ
  // ============================================================

  const loadPreview = async () => {
    try {
      setLoadingPreview(true)
      const response = await fetch(`${API_URL}/api/inventaire/deduction-config/preview?days=${previewDays}`, {
        method: 'POST'
      })

      if (!response.ok) throw new Error('Erreur génération preview')

      const data = await response.json()
      setPreviewData(data)
      setError(null)
    } catch (err) {
      setError('Erreur génération preview')
      console.error(err)
    } finally {
      setLoadingPreview(false)
    }
  }

  const applyDeductions = async () => {
    if (!confirm(`Confirmer l'application de ${previewData?.total_deductions || 0} déductions?`)) return

    try {
      const response = await fetch(`${API_URL}/api/inventaire/process-deductions?days=${previewDays}`, {
        method: 'POST'
      })

      if (!response.ok) throw new Error('Erreur application déductions')

      const data = await response.json()
      setSuccessMessage(`${data.stats.deductions_created} déductions appliquées!`)
      setTimeout(() => setSuccessMessage(null), 3000)

      // Recharger preview
      loadPreview()
    } catch (err) {
      setError('Erreur application déductions')
      console.error(err)
    }
  }

  // ============================================================
  // RENDER
  // ============================================================

  return (
    <div className="max-w-7xl mx-auto p-6">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">⚙️ Configuration des Déductions</h1>
        <p className="text-sm text-gray-600 mt-1">
          Gérez les règles de déduction automatique d'inventaire
        </p>
      </div>

      {/* Messages */}
      {error && (
        <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg text-red-800">
          ❌ {error}
        </div>
      )}
      {successMessage && (
        <div className="mb-4 p-4 bg-green-50 border border-green-200 rounded-lg text-green-800">
          ✅ {successMessage}
        </div>
      )}

      {/* Tabs */}
      <div className="mb-6 border-b border-gray-200">
        <nav className="flex space-x-8">
          {[
            { id: 'global', label: '🌐 Règle Globale', icon: '🌐' },
            { id: 'services', label: '🔧 Services (Recettes)', icon: '🔧' },
            { id: 'keywords', label: '🔍 Mots-Clés', icon: '🔍' },
            { id: 'preview', label: '👁️ Preview Sécurisé', icon: '👁️' }
          ].map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`py-4 px-1 border-b-2 font-medium text-sm transition-colors ${
                activeTab === tab.id
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </nav>
      </div>

      {/* Contenu des onglets */}
      <div className="bg-white rounded-lg shadow p-6">
        {/* ONGLET: RÈGLE GLOBALE */}
        {activeTab === 'global' && (
          <div>
            <h2 className="text-xl font-semibold mb-4">🌐 Règle Globale Automatique</h2>
            <p className="text-gray-600 mb-6">
              Active la déduction automatique pour toutes les fournitures et accessoires présents sur une facture.
            </p>

            {loadingGlobal ? (
              <div className="text-center py-8">⏳ Chargement...</div>
            ) : (
              <div>
                {/* Toggle */}
                <div className="flex items-center justify-between p-6 bg-gray-50 rounded-lg border-2 border-gray-200">
                  <div>
                    <h3 className="text-lg font-medium text-gray-900">
                      {globalRule.enabled ? '✅ Règle activée' : '❌ Règle désactivée'}
                    </h3>
                    <p className="text-sm text-gray-600 mt-1">
                      {globalRule.description || 'Toute fourniture ou accessoire sur facture déclenche une déduction automatique'}
                    </p>
                  </div>
                  <button
                    onClick={toggleGlobalRule}
                    className={`px-6 py-3 rounded-lg font-medium transition-colors ${
                      globalRule.enabled
                        ? 'bg-red-600 hover:bg-red-700 text-white'
                        : 'bg-green-600 hover:bg-green-700 text-white'
                    }`}
                  >
                    {globalRule.enabled ? 'Désactiver' : 'Activer'}
                  </button>
                </div>

                {/* Info */}
                <div className="mt-6 p-4 bg-blue-50 border border-blue-200 rounded-lg">
                  <p className="text-sm text-blue-800">
                    💡 <strong>Comment ça fonctionne:</strong> Lorsqu'activée, cette règle détecte automatiquement
                    tous les items de type "fourniture" ou "accessoire" sur les factures Gazelle et crée des déductions
                    dans l'inventaire du technicien concerné.
                  </p>
                </div>

                {/* Types d'items couverts */}
                <div className="mt-6">
                  <h4 className="font-medium text-gray-900 mb-3">Types d'items couverts:</h4>
                  <div className="flex gap-2">
                    {globalRule.item_types?.map(type => (
                      <span key={type} className="px-3 py-1 bg-blue-100 text-blue-800 rounded-full text-sm">
                        {type}
                      </span>
                    ))}
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* ONGLET: SERVICES (RECETTES) */}
        {activeTab === 'services' && (
          <div>
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-xl font-semibold">🔧 Mapping de Services (Recettes)</h2>
              <button
                onClick={() => setShowServiceForm(!showServiceForm)}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
              >
                {showServiceForm ? 'Annuler' : '+ Nouvelle Règle'}
              </button>
            </div>

            <p className="text-gray-600 mb-6">
              Définissez quels matériaux sont consommés pour chaque type de service.
            </p>

            {/* Formulaire nouveau service */}
            {showServiceForm && (
              <div className="mb-6 p-6 bg-gray-50 rounded-lg border border-gray-200">
                <h3 className="font-medium mb-4">Nouvelle Règle de Service</h3>

                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      ID Service Gazelle
                    </label>
                    <input
                      type="text"
                      value={newServiceRule.service_gazelle_id}
                      onChange={(e) => setNewServiceRule({ ...newServiceRule, service_gazelle_id: e.target.value })}
                      placeholder="mit_EntretienAnnuel"
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Code Produit (optionnel)
                    </label>
                    <input
                      type="text"
                      value={newServiceRule.service_code_produit}
                      onChange={(e) => setNewServiceRule({ ...newServiceRule, service_code_produit: e.target.value })}
                      placeholder="ENT-ANN"
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                    />
                  </div>

                  {/* Matériaux */}
                  <div>
                    <div className="flex justify-between items-center mb-2">
                      <label className="block text-sm font-medium text-gray-700">
                        Matériaux consommés
                      </label>
                      <button
                        onClick={addMaterialField}
                        className="text-sm text-blue-600 hover:text-blue-800"
                      >
                        + Ajouter matériau
                      </button>
                    </div>

                    {newServiceRule.materials.map((material, index) => (
                      <div key={index} className="flex gap-2 mb-2">
                        <input
                          type="text"
                          value={material.material_code_produit}
                          onChange={(e) => updateMaterialField(index, 'material_code_produit', e.target.value)}
                          placeholder="Code produit (ex: BUV-001)"
                          className="flex-1 px-3 py-2 border border-gray-300 rounded-lg"
                        />
                        <input
                          type="number"
                          value={material.quantity}
                          onChange={(e) => updateMaterialField(index, 'quantity', parseFloat(e.target.value))}
                          step="0.1"
                          min="0"
                          className="w-24 px-3 py-2 border border-gray-300 rounded-lg"
                        />
                        <label className="flex items-center gap-1 px-3 py-2 bg-gray-100 rounded-lg">
                          <input
                            type="checkbox"
                            checked={material.is_optional}
                            onChange={(e) => updateMaterialField(index, 'is_optional', e.target.checked)}
                          />
                          <span className="text-sm">Optionnel</span>
                        </label>
                        {newServiceRule.materials.length > 1 && (
                          <button
                            onClick={() => removeMaterialField(index)}
                            className="px-3 py-2 bg-red-100 text-red-700 rounded-lg hover:bg-red-200"
                          >
                            ✕
                          </button>
                        )}
                      </div>
                    ))}
                  </div>

                  <div className="flex gap-2">
                    <button
                      onClick={saveServiceRule}
                      className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700"
                    >
                      Enregistrer
                    </button>
                    <button
                      onClick={() => setShowServiceForm(false)}
                      className="px-4 py-2 bg-gray-300 text-gray-700 rounded-lg hover:bg-gray-400"
                    >
                      Annuler
                    </button>
                  </div>
                </div>
              </div>
            )}

            {/* Liste des règles */}
            {loadingServices ? (
              <div className="text-center py-8">⏳ Chargement...</div>
            ) : serviceRules.length === 0 ? (
              <div className="text-center py-8 text-gray-500">
                Aucune règle de service configurée
              </div>
            ) : (
              <div className="space-y-4">
                {serviceRules.map((rule, index) => (
                  <div key={index} className="p-4 border border-gray-200 rounded-lg">
                    <div className="flex justify-between items-start">
                      <div>
                        <h4 className="font-medium text-gray-900">{rule.service_gazelle_id}</h4>
                        {rule.service_code_produit && (
                          <p className="text-sm text-gray-600">Code: {rule.service_code_produit}</p>
                        )}
                      </div>
                      <button
                        onClick={() => deleteServiceRule(rule.service_gazelle_id)}
                        className="text-red-600 hover:text-red-800 text-sm"
                      >
                        Supprimer
                      </button>
                    </div>

                    <div className="mt-3">
                      <p className="text-sm font-medium text-gray-700 mb-2">Matériaux:</p>
                      <div className="flex flex-wrap gap-2">
                        {rule.materials?.map((mat, matIndex) => (
                          <span key={matIndex} className="px-3 py-1 bg-blue-100 text-blue-800 rounded-full text-sm">
                            {mat.material_code_produit} × {mat.quantity}
                            {mat.is_optional && ' (opt)'}
                          </span>
                        ))}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* ONGLET: MOTS-CLÉS */}
        {activeTab === 'keywords' && (
          <div>
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-xl font-semibold">🔍 Détection par Mots-Clés</h2>
              <button
                onClick={() => setShowKeywordForm(!showKeywordForm)}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
              >
                {showKeywordForm ? 'Annuler' : '+ Nouvelle Règle'}
              </button>
            </div>

            <p className="text-gray-600 mb-6">
              Scannez les notes des factures pour détecter automatiquement des consommations.
            </p>

            {/* Formulaire nouveau mot-clé */}
            {showKeywordForm && (
              <div className="mb-6 p-6 bg-gray-50 rounded-lg border border-gray-200">
                <h3 className="font-medium mb-4">Nouvelle Règle de Mot-Clé</h3>

                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Mot-clé à détecter
                    </label>
                    <input
                      type="text"
                      value={newKeywordRule.keyword}
                      onChange={(e) => setNewKeywordRule({ ...newKeywordRule, keyword: e.target.value })}
                      placeholder="Buvard remplacé"
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Code Produit à déduire
                    </label>
                    <input
                      type="text"
                      value={newKeywordRule.material_code_produit}
                      onChange={(e) => setNewKeywordRule({ ...newKeywordRule, material_code_produit: e.target.value })}
                      placeholder="BUV-001"
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Quantité
                    </label>
                    <input
                      type="number"
                      value={newKeywordRule.quantity}
                      onChange={(e) => setNewKeywordRule({ ...newKeywordRule, quantity: parseFloat(e.target.value) })}
                      step="0.1"
                      min="0"
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                    />
                  </div>

                  <div>
                    <label className="flex items-center gap-2">
                      <input
                        type="checkbox"
                        checked={newKeywordRule.case_sensitive}
                        onChange={(e) => setNewKeywordRule({ ...newKeywordRule, case_sensitive: e.target.checked })}
                      />
                      <span className="text-sm text-gray-700">Sensible à la casse</span>
                    </label>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Notes (optionnel)
                    </label>
                    <textarea
                      value={newKeywordRule.notes}
                      onChange={(e) => setNewKeywordRule({ ...newKeywordRule, notes: e.target.value })}
                      placeholder="Notes explicatives..."
                      rows="2"
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                    />
                  </div>

                  <div className="flex gap-2">
                    <button
                      onClick={saveKeywordRule}
                      className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700"
                    >
                      Enregistrer
                    </button>
                    <button
                      onClick={() => setShowKeywordForm(false)}
                      className="px-4 py-2 bg-gray-300 text-gray-700 rounded-lg hover:bg-gray-400"
                    >
                      Annuler
                    </button>
                  </div>
                </div>
              </div>
            )}

            {/* Liste des règles */}
            {loadingKeywords ? (
              <div className="text-center py-8">⏳ Chargement...</div>
            ) : keywordRules.length === 0 ? (
              <div className="text-center py-8 text-gray-500">
                Aucune règle de mot-clé configurée
              </div>
            ) : (
              <div className="space-y-3">
                {keywordRules.map((rule) => (
                  <div key={rule.id} className="flex justify-between items-center p-4 border border-gray-200 rounded-lg">
                    <div>
                      <p className="font-medium text-gray-900">
                        "{rule.keyword}" → {rule.material_code_produit} × {rule.quantity}
                      </p>
                      {rule.notes && <p className="text-sm text-gray-600 mt-1">{rule.notes}</p>}
                      {rule.case_sensitive && (
                        <span className="inline-block mt-1 px-2 py-0.5 bg-yellow-100 text-yellow-800 text-xs rounded">
                          Sensible à la casse
                        </span>
                      )}
                    </div>
                    <button
                      onClick={() => deleteKeywordRule(rule.id)}
                      className="text-red-600 hover:text-red-800"
                    >
                      Supprimer
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* ONGLET: PREVIEW SÉCURISÉ */}
        {activeTab === 'preview' && (
          <div>
            <h2 className="text-xl font-semibold mb-4">👁️ Preview Sécurisé</h2>
            <p className="text-gray-600 mb-6">
              Prévisualisez les déductions qui seront créées AVANT de les appliquer définitivement.
            </p>

            {/* Controls */}
            <div className="flex gap-4 mb-6">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Période d'analyse (jours)
                </label>
                <input
                  type="number"
                  value={previewDays}
                  onChange={(e) => setPreviewDays(parseInt(e.target.value))}
                  min="1"
                  max="30"
                  className="w-32 px-3 py-2 border border-gray-300 rounded-lg"
                />
              </div>

              <div className="flex-1 flex items-end gap-2">
                <button
                  onClick={loadPreview}
                  disabled={loadingPreview}
                  className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
                >
                  {loadingPreview ? '⏳ Chargement...' : '🔄 Générer Preview'}
                </button>

                {previewData && previewData.total_deductions > 0 && (
                  <button
                    onClick={applyDeductions}
                    className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700"
                  >
                    ✅ Appliquer ({previewData.total_deductions} déductions)
                  </button>
                )}
              </div>
            </div>

            {/* Preview Results */}
            {previewData && (
              <div className="space-y-4">
                {/* Stats */}
                <div className="grid grid-cols-3 gap-4">
                  <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg">
                    <p className="text-sm text-blue-700">Total Déductions</p>
                    <p className="text-2xl font-bold text-blue-900">{previewData.total_deductions}</p>
                  </div>
                  <div className="p-4 bg-green-50 border border-green-200 rounded-lg">
                    <p className="text-sm text-green-700">Factures Analysées</p>
                    <p className="text-2xl font-bold text-green-900">{previewData.period?.invoices_analyzed || 0}</p>
                  </div>
                  <div className="p-4 bg-purple-50 border border-purple-200 rounded-lg">
                    <p className="text-sm text-purple-700">Techniciens</p>
                    <p className="text-2xl font-bold text-purple-900">{Object.keys(previewData.by_technician || {}).length}</p>
                  </div>
                </div>

                {/* Par technicien */}
                <div>
                  <h3 className="font-medium text-gray-900 mb-3">Déductions par Technicien</h3>
                  {Object.entries(previewData.by_technician || {}).map(([tech, deductions]) => (
                    <div key={tech} className="mb-4">
                      <div className="flex items-center justify-between mb-2">
                        <h4 className="font-medium text-gray-800">
                          👤 {tech} ({deductions.length} déductions)
                        </h4>
                      </div>
                      <div className="bg-gray-50 rounded-lg p-4">
                        <table className="min-w-full text-sm">
                          <thead>
                            <tr className="text-left text-gray-600">
                              <th className="pb-2">Facture</th>
                              <th className="pb-2">Service</th>
                              <th className="pb-2">Matériel</th>
                              <th className="pb-2">Qté</th>
                            </tr>
                          </thead>
                          <tbody>
                            {deductions.map((ded, idx) => (
                              <tr key={idx} className="border-t border-gray-200">
                                <td className="py-2">{ded.invoice_number}</td>
                                <td className="py-2">{ded.service}</td>
                                <td className="py-2">
                                  <span className="px-2 py-0.5 bg-blue-100 text-blue-800 rounded text-xs">
                                    {ded.material_code}
                                  </span>
                                </td>
                                <td className="py-2 font-medium">{ded.quantity}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  ))}
                </div>

                {/* Warnings */}
                {previewData.warnings && previewData.warnings.length > 0 && (
                  <div className="p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
                    <h3 className="font-medium text-yellow-900 mb-2">⚠️ Avertissements</h3>
                    <ul className="list-disc list-inside text-sm text-yellow-800 space-y-1">
                      {previewData.warnings.map((warning, idx) => (
                        <li key={idx}>{warning}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
