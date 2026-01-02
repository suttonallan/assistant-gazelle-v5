/**
 * PDAInventoryTable - Inventaire Pianos Place des Arts
 * 
 * Réutilise exactement la même logique qu'InventoryTable de Vincent d'Indy
 * avec toutes les fonctionnalités:
 * - Shift+Clic range selection
 * - Inline toggle isHidden
 * - Tri + filtres
 * - Batch operations
 */

import { useState, useEffect, useMemo, useRef } from 'react'

import { API_URL } from '../utils/apiConfig'

// ==========================================
// HELPERS
// ==========================================

/**
 * Convert camelCase to snake_case
 */
function keysToSnakeCase(obj) {
  const result = {}
  for (const [key, value] of Object.entries(obj)) {
    const snakeKey = key.replace(/[A-Z]/g, letter => `_${letter.toLowerCase()}`)
    result[snakeKey] = value
  }
  return result
}

/**
 * Format date short
 */
function formatDateShort(date) {
  if (!date) return '—'
  try {
    return new Date(date).toLocaleDateString('fr-CA')
  } catch {
    return '—'
  }
}

/**
 * Get select all state (checked, indeterminate)
 */
function getSelectAllState(selectedCount, totalCount) {
  return {
    checked: selectedCount > 0 && selectedCount === totalCount,
    indeterminate: selectedCount > 0 && selectedCount < totalCount
  }
}

// ==========================================
// HOOKS (Simplified versions)
// ==========================================

/**
 * useRangeSelection - Shift+Click range selection
 */
function useRangeSelection(allIds) {
  const [selectedIds, setSelectedIds] = useState(new Set())
  const [lastClickedId, setLastClickedId] = useState(null)

  const getRangeBetween = (startId, endId) => {
    const startIndex = allIds.indexOf(startId)
    const endIndex = allIds.indexOf(endId)
    if (startIndex === -1 || endIndex === -1) return []
    const [min, max] = [Math.min(startIndex, endIndex), Math.max(startIndex, endIndex)]
    return allIds.slice(min, max + 1)
  }

  const handleClick = (id, shiftKey) => {
    setSelectedIds(prev => {
      const next = new Set(prev)
      if (shiftKey && lastClickedId) {
        // Range selection
        const range = getRangeBetween(lastClickedId, id)
        range.forEach(rangeId => next.add(rangeId))
      } else {
        // Toggle
        if (next.has(id)) next.delete(id)
        else next.add(id)
      }
      return next
    })
    if (!shiftKey) setLastClickedId(id)
  }

  const selectAll = () => setSelectedIds(new Set(allIds))
  const clearAll = () => {
    setSelectedIds(new Set())
    setLastClickedId(null)
  }
  const isSelected = (id) => selectedIds.has(id)
  const count = selectedIds.size

  return { selectedIds, handleClick, selectAll, clearAll, isSelected, count }
}

// ==========================================
// COMPONENT
// ==========================================

export default function PDAInventoryTable() {
  // State
  const [pianos, setPianos] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [showHiddenOnly, setShowHiddenOnly] = useState(false)
  const [sortConfig, setSortConfig] = useState({ field: 'location', order: 'asc' })
  const [batchLoading, setBatchLoading] = useState(false)
  const selectAllCheckboxRef = useRef(null)

  // Range selection
  const allIds = useMemo(() => pianos.map(p => p.gazelleId || p.id), [pianos])
  const {
    selectedIds,
    handleClick,
    selectAll,
    clearAll,
    isSelected,
    count: selectedCount
  } = useRangeSelection(allIds)

  // Load pianos
  useEffect(() => {
    loadPianos()
  }, [])

  const loadPianos = async () => {
    try {
      setLoading(true)
      setError(null)
      const resp = await fetch(`${API_URL}/api/place-des-arts/pianos?include_inactive=true`)
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`)
      const data = await resp.json()
      
      // Transform data to match expected format
      const transformedPianos = (data.pianos || []).map(p => ({
        gazelleId: p.id || p.gazelleId,
        location: p.local || p.location || '',
        make: p.piano || p.make || '',
        model: p.modele || p.model || '',
        serialNumber: p.serie || p.serialNumber || '',
        type: p.type || 'U',
        lastTuned: p.dernierAccord ? new Date(p.dernierAccord) : null,
        status: p.status || 'normal',
        isHidden: p.hasNonTag || p.isHidden || false,
        notes: p.observations || p.notes || null,
        travail: p.travail || null,
        aFaire: p.aFaire || null
      }))
      
      setPianos(transformedPianos)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  // Filtered & sorted pianos
  const displayedPianos = useMemo(() => {
    let result = [...pianos]

    // Search filter
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase()
      result = result.filter(p =>
        (p.location || '').toLowerCase().includes(query) ||
        (p.make || '').toLowerCase().includes(query) ||
        (p.model || '').toLowerCase().includes(query) ||
        (p.serialNumber || '').toLowerCase().includes(query)
      )
    }

    // Hidden-only filter
    if (showHiddenOnly) {
      result = result.filter(p => p.isHidden)
    }

    // Sort
    result.sort((a, b) => {
      const aVal = a[sortConfig.field] || ''
      const bVal = b[sortConfig.field] || ''
      const dir = sortConfig.order === 'asc' ? 1 : -1
      
      // Special handling for dates
      if (sortConfig.field === 'lastTuned') {
        const aTime = a.lastTuned ? new Date(a.lastTuned).getTime() : 0
        const bTime = b.lastTuned ? new Date(b.lastTuned).getTime() : 0
        return (aTime - bTime) * dir
      }
      
      return String(aVal).localeCompare(String(bVal)) * dir
    })

    return result
  }, [pianos, searchQuery, showHiddenOnly, sortConfig])

  // Update select all checkbox state
  useEffect(() => {
    if (selectAllCheckboxRef.current) {
      const state = getSelectAllState(selectedCount, displayedPianos.length)
      selectAllCheckboxRef.current.checked = state.checked
      selectAllCheckboxRef.current.indeterminate = state.indeterminate
    }
  }, [selectedCount, displayedPianos.length])

  // Handlers
  const handleSort = (field) => {
    setSortConfig(prev => ({
      field,
      order: prev.field === field && prev.order === 'asc' ? 'desc' : 'asc'
    }))
  }

  const handleSelectAll = (e) => {
    if (e.target.checked) {
      selectAll()
    } else {
      clearAll()
    }
  }

  const handleToggleHidden = async (piano) => {
    try {
      const newIsHidden = !piano.isHidden
      
      // Optimistic update
      setPianos(prev => prev.map(p =>
        p.gazelleId === piano.gazelleId ? { ...p, isHidden: newIsHidden } : p
      ))

      // Update via API backend
      const resp = await fetch(`${API_URL}/api/vincent-dindy/pianos/${piano.gazelleId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          isHidden: newIsHidden
        })
      })

      if (!resp.ok) {
        const errorData = await resp.json().catch(() => ({ detail: 'Erreur HTTP ' + resp.status }))
        throw new Error(errorData.detail || 'Erreur lors de la mise à jour')
      }
    } catch (err) {
      console.error('Error toggling hidden:', err)
      // Rollback
      setPianos(prev => prev.map(p =>
        p.gazelleId === piano.gazelleId ? { ...p, isHidden: piano.isHidden } : p
      ))
      alert('Erreur lors de la mise à jour')
    }
  }

  const handleBatchShow = async () => {
    if (selectedCount === 0) return
    
    setBatchLoading(true)
    try {
      const updates = Array.from(selectedIds).map(pianoId => ({
        pianoId: pianoId,
        isHidden: false
      }))

      const resp = await fetch(`${API_URL}/api/vincent-dindy/pianos/batch`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updates)
      })

      if (!resp.ok) {
        const errorData = await resp.json().catch(() => ({ detail: 'Erreur HTTP ' + resp.status }))
        throw new Error(errorData.detail || 'Erreur batch show')
      }
      
      // Update local state
      setPianos(prev => prev.map(p =>
        selectedIds.has(p.gazelleId) ? { ...p, isHidden: false } : p
      ))
      
      clearAll()
      await loadPianos()
    } catch (err) {
      console.error('Error batch show:', err)
      alert('Erreur lors de l\'affichage groupé')
    } finally {
      setBatchLoading(false)
    }
  }

  const handleBatchHide = async () => {
    if (selectedCount === 0) return
    
    if (!confirm(`Masquer ${selectedCount} piano(s) de l'inventaire?`)) return
    
    setBatchLoading(true)
    try {
      const updates = Array.from(selectedIds).map(pianoId => ({
        pianoId: pianoId,
        isHidden: true
      }))

      const resp = await fetch(`${API_URL}/api/vincent-dindy/pianos/batch`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updates)
      })

      if (!resp.ok) {
        const errorData = await resp.json().catch(() => ({ detail: 'Erreur HTTP ' + resp.status }))
        throw new Error(errorData.detail || 'Erreur batch hide')
      }
      
      // Update local state
      setPianos(prev => prev.map(p =>
        selectedIds.has(p.gazelleId) ? { ...p, isHidden: true } : p
      ))
      
      clearAll()
      await loadPianos()
    } catch (err) {
      console.error('Error batch hide:', err)
      alert('Erreur lors du masquage groupé')
    } finally {
      setBatchLoading(false)
    }
  }

  // Loading state
  if (loading && pianos.length === 0) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Chargement des pianos Place des Arts...</p>
        </div>
      </div>
    )
  }

  // Error state
  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4">
        <h3 className="text-red-800 font-semibold mb-2">Erreur</h3>
        <p className="text-red-600">{error}</p>
        <button
          onClick={loadPianos}
          className="mt-3 px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700"
        >
          Réessayer
        </button>
      </div>
    )
  }

  // Select all state
  const selectAllState = getSelectAllState(selectedCount, displayedPianos.length)

  return (
    <div className="space-y-4">
      {/* HEADER & FILTERS - Style identique à VDI */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-xl font-bold text-gray-900">
              Inventaire Pianos
            </h2>
            <p className="text-sm text-gray-500 mt-1">
              {displayedPianos.length} piano(s) · {selectedCount} sélectionné(s)
            </p>
          </div>

          <button
            onClick={loadPianos}
            disabled={loading}
            className="px-4 py-2 text-sm bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors disabled:opacity-50"
          >
            🔄 Actualiser
          </button>
        </div>

        {/* Search & Filters */}
        <div className="flex gap-3">
          <input
            type="text"
            placeholder="Rechercher piano, local, série..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />

          <label className="flex items-center gap-2 px-4 py-2 bg-gray-50 rounded-lg cursor-pointer hover:bg-gray-100">
            <input
              type="checkbox"
              checked={showHiddenOnly}
              onChange={(e) => setShowHiddenOnly(e.target.checked)}
              className="w-4 h-4"
            />
            <span className="text-sm font-medium text-gray-700">
              Masqués uniquement
            </span>
          </label>
        </div>
      </div>

      {/* BATCH TOOLBAR */}
      {selectedCount > 0 && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
          <div className="flex items-center justify-between">
            <span className="text-blue-900 font-medium">
              {selectedCount} piano(s) sélectionné(s)
            </span>

            <div className="flex gap-2">
              <button
                onClick={handleBatchShow}
                disabled={batchLoading}
                className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors disabled:opacity-50 text-sm font-medium"
              >
                👁️ Afficher
              </button>

              <button
                onClick={handleBatchHide}
                disabled={batchLoading}
                className="px-4 py-2 bg-orange-600 text-white rounded-lg hover:bg-orange-700 transition-colors disabled:opacity-50 text-sm font-medium"
              >
                🚫 Masquer
              </button>

              <button
                onClick={clearAll}
                className="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition-colors text-sm font-medium"
              >
                Annuler
              </button>
            </div>
          </div>
        </div>
      )}

      {/* TABLE */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="px-4 py-3 text-left w-12">
                  <input
                    ref={selectAllCheckboxRef}
                    type="checkbox"
                    checked={selectAllState.checked}
                    onChange={handleSelectAll}
                    className="w-4 h-4 rounded cursor-pointer"
                    title="Sélectionner tout (Shift+Clic pour plage)"
                  />
                </th>

                <th
                  onClick={() => handleSort('location')}
                  className="px-4 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider cursor-pointer hover:bg-gray-100 transition-colors select-none"
                >
                  <div className="flex items-center gap-2">
                    <span>Local</span>
                    <span className="text-gray-400">
                      {sortConfig.field === 'location' ? (sortConfig.order === 'asc' ? '↑' : '↓') : '↕'}
                    </span>
                  </div>
                </th>

                <th
                  onClick={() => handleSort('make')}
                  className="px-4 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider cursor-pointer hover:bg-gray-100 transition-colors select-none"
                >
                  <div className="flex items-center gap-2">
                    <span>Piano</span>
                    <span className="text-gray-400">
                      {sortConfig.field === 'make' ? (sortConfig.order === 'asc' ? '↑' : '↓') : '↕'}
                    </span>
                  </div>
                </th>

                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider">
                  Type
                </th>

                <th
                  onClick={() => handleSort('lastTuned')}
                  className="px-4 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider cursor-pointer hover:bg-gray-100 transition-colors select-none"
                >
                  <div className="flex items-center gap-2">
                    <span>Dernier Accord</span>
                    <span className="text-gray-400">
                      {sortConfig.field === 'lastTuned' ? (sortConfig.order === 'asc' ? '↑' : '↓') : '↕'}
                    </span>
                  </div>
                </th>

                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider">
                  Statut
                </th>

                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider">
                  Visibilité
                </th>
              </tr>
            </thead>

            <tbody className="divide-y divide-gray-200">
              {displayedPianos.map((piano) => (
                <tr
                  key={piano.gazelleId}
                  className={`
                    bg-white
                    ${isSelected(piano.gazelleId) ? 'ring-2 ring-blue-500' : ''}
                    hover:shadow-sm transition-all duration-100
                  `}
                >
                  {/* Checkbox */}
                  <td className="px-4 py-3">
                    <input
                      type="checkbox"
                      checked={isSelected(piano.gazelleId)}
                      onChange={(e) => handleClick(piano.gazelleId, e.shiftKey)}
                      onClick={(e) => e.stopPropagation()}
                      className="w-4 h-4 rounded cursor-pointer"
                    />
                  </td>

                  {/* Local */}
                  <td className="px-4 py-3 text-sm font-medium text-gray-900">
                    {piano.location || '—'}
                  </td>

                  {/* Piano */}
                  <td className="px-4 py-3">
                    <div className="text-sm">
                      <div className="font-medium text-gray-900">{piano.make || '—'}</div>
                      {piano.model && (
                        <div className="text-gray-500 text-xs">{piano.model}</div>
                      )}
                      {piano.serialNumber && (
                        <div className="text-gray-400 text-xs mt-0.5">Série: {piano.serialNumber}</div>
                      )}
                    </div>
                  </td>

                  {/* Type */}
                  <td className="px-4 py-3">
                    <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-gray-100 text-gray-700">
                      {piano.type === 'G' ? 'Grand' : piano.type === 'U' ? 'Droit' : piano.type || '—'}
                    </span>
                  </td>

                  {/* Dernier Accord */}
                  <td className="px-4 py-3">
                    {piano.lastTuned ? (
                      <span className="text-sm text-gray-600">
                        {formatDateShort(piano.lastTuned)}
                      </span>
                    ) : (
                      <span className="text-sm text-gray-400">—</span>
                    )}
                  </td>

                  {/* Statut */}
                  <td className="px-4 py-3">
                    {piano.status === 'normal' && (
                      <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-gray-100 text-gray-700">
                        Normal
                      </span>
                    )}
                    {piano.status === 'proposed' && (
                      <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-yellow-100 text-yellow-700">
                        À faire
                      </span>
                    )}
                    {piano.status === 'completed' && (
                      <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-green-100 text-green-700">
                        Complété
                      </span>
                    )}
                    {piano.status === 'top' && (
                      <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-amber-100 text-amber-700">
                        Top
                      </span>
                    )}
                  </td>

                  {/* Visibilité Toggle */}
                  <td className="px-4 py-3">
                    <button
                      onClick={() => handleToggleHidden(piano)}
                      className={`
                        px-3 py-1 rounded-lg text-sm font-medium transition-colors
                        ${
                          piano.isHidden
                            ? 'bg-red-100 text-red-700 hover:bg-red-200'
                            : 'bg-green-100 text-green-700 hover:bg-green-200'
                        }
                      `}
                    >
                      {piano.isHidden ? '🚫 Masqué' : '👁️ Visible'}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          {displayedPianos.length === 0 && (
            <div className="text-center py-12">
              <p className="text-gray-500">Aucun piano trouvé</p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
