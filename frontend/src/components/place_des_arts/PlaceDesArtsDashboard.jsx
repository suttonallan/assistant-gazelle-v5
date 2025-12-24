import { useEffect, useState, useCallback, useMemo, useRef } from 'react'
import EditablePreviewItem from './EditablePreviewItem'

const API_URL = import.meta.env.VITE_API_URL || 'https://assistant-gazelle-v5-api.onrender.com'

export default function PlaceDesArtsDashboard({ currentUser }) {
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [stats, setStats] = useState({ imported: 0, to_bill: 0, this_month: 0 })
  const [isFullscreen, setIsFullscreen] = useState(false)
  const [editMode, setEditMode] = useState(false)
  const [batchYear, setBatchYear] = useState(new Date().getFullYear())

  // Filtres
  const [statusFilter, setStatusFilter] = useState('')
  const [monthFilter, setMonthFilter] = useState('')
  const [search, setSearch] = useState('')
  const [technicianFilter, setTechnicianFilter] = useState('')
  const [roomFilter, setRoomFilter] = useState('')
  const [sortField, setSortField] = useState('')
  const [sortDir, setSortDir] = useState('asc')

  // Sélection
  const [selectedIds, setSelectedIds] = useState([])

  // Import email
  const [rawText, setRawText] = useState('')
  const [preview, setPreview] = useState([])
  const [previewLoading, setPreviewLoading] = useState(false)
  const [importLoading, setImportLoading] = useState(false)
  const [infoMessage, setInfoMessage] = useState(null)
  const [csvLoading, setCsvLoading] = useState(false)
  const fileInputRef = useRef(null)

  const fetchData = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)
      const resp = await fetch(`${API_URL}/place-des-arts/requests?limit=200`)
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`)
      const data = await resp.json()
      setItems(data || [])
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [])

  const fetchStats = useCallback(async () => {
    try {
      const resp = await fetch(`${API_URL}/place-des-arts/stats`)
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`)
      const data = await resp.json()
      setStats(data || { imported: 0, to_bill: 0, this_month: 0 })
    } catch (err) {
      // stats non bloquantes
    }
  }, [])

  useEffect(() => {
    fetchData()
    fetchStats()
  }, [fetchData])

  const filteredItems = useMemo(() => {
    return items.filter((it) => {
      if (statusFilter && it.status !== statusFilter) return false
      if (monthFilter && it.appointment_date && !it.appointment_date.startsWith(monthFilter)) return false
      if (technicianFilter && it.technician_id !== technicianFilter) return false
      if (roomFilter && (it.room || '').toUpperCase() !== roomFilter.toUpperCase()) return false
      if (search) {
        const q = search.toLowerCase()
        const hay = [it.for_who, it.piano, it.room, it.requester, it.diapason, it.time].join(' ').toLowerCase()
        if (!hay.includes(q)) return false
      }
      return true
    })
  }, [items, statusFilter, monthFilter, technicianFilter, roomFilter, search])

  const sortedItems = useMemo(() => {
    if (!sortField) return filteredItems
    const dir = sortDir === 'desc' ? -1 : 1
    const compare = (a, b) => {
      const va = a?.[sortField] ?? ''
      const vb = b?.[sortField] ?? ''
      // Date strings first
      if (sortField === 'request_date' || sortField === 'appointment_date') {
        const da = va ? new Date(va).getTime() : 0
        const db = vb ? new Date(vb).getTime() : 0
        return (da - db) * dir
      }
      return String(va).localeCompare(String(vb)) * dir
    }
    return [...filteredItems].sort(compare)
  }, [filteredItems, sortField, sortDir])

  const toggleSort = (field) => {
    if (sortField === field) {
      setSortDir((prev) => (prev === 'asc' ? 'desc' : 'asc'))
    } else {
      setSortField(field)
      setSortDir('asc')
    }
  }

  const sortIndicator = (field) => {
    if (sortField !== field) return ''
    return sortDir === 'asc' ? '▲' : '▼'
  }

  const toggleSelect = (id) => {
    setSelectedIds((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]))
  }

  const toggleSelectAll = () => {
    if (selectedIds.length === filteredItems.length) {
      setSelectedIds([])
    } else {
      setSelectedIds(filteredItems.map((it) => it.id))
    }
  }

  const callAction = async (url, body) => {
    try {
      setError(null)
      const resp = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
      })
      if (!resp.ok) {
        const msg = await resp.text()
        throw new Error(msg || `HTTP ${resp.status}`)
      }
      await fetchData()
      await fetchStats()
      setInfoMessage('Action effectuée')
      setSelectedIds([])
    } catch (err) {
      setError(err.message)
    }
  }

  const handleStatusChange = async (newStatus, idsOverride = null) => {
    const ids = idsOverride || selectedIds
    if (!newStatus || ids.length === 0) return
    await callAction(`${API_URL}/place-des-arts/requests/update-status-batch`, {
      request_ids: ids,
      status: newStatus
    })
  }

  const handleBill = async () => {
    if (selectedIds.length === 0) return
    await callAction(`${API_URL}/place-des-arts/requests/bill`, {
      request_ids: selectedIds,
      status: 'BILLED'
    })
  }

  const handleDelete = async () => {
    if (selectedIds.length === 0) return
    await callAction(`${API_URL}/place-des-arts/requests/delete`, {
      request_ids: selectedIds
    })
  }

  const handleDeleteDuplicates = async () => {
    try {
      setError(null)
      setInfoMessage(null)

      // 1. Récupérer la liste des doublons
      const resp = await fetch(`${API_URL}/place-des-arts/requests/find-duplicates`)
      if (!resp.ok) {
        throw new Error(`Erreur lors de la recherche de doublons: ${resp.status}`)
      }

      const data = await resp.json()
      const duplicates = data.duplicates || []

      if (duplicates.length === 0) {
        setInfoMessage('Aucun doublon détecté')
        return
      }

      // 2. Afficher la liste et demander confirmation
      const duplicatesList = duplicates.map((dup, idx) =>
        `${idx + 1}. ${dup.appointment_date} - ${dup.room} - ${dup.for_who || '(sans nom)'} (ID: ${dup.id})`
      ).join('\n')

      const confirmMessage = `${duplicates.length} doublon(s) détecté(s):\n\n${duplicatesList}\n\nVoulez-vous vraiment supprimer ces doublons?`

      if (!window.confirm(confirmMessage)) {
        setInfoMessage('Suppression annulée')
        return
      }

      // 3. Supprimer seulement si confirmé
      await callAction(`${API_URL}/place-des-arts/requests/delete-duplicates`, {})

    } catch (err) {
      setError(err.message || 'Erreur lors de la suppression des doublons')
    }
  }

  const handleImportCsv = async (file) => {
    if (!file) return
    try {
      setCsvLoading(true)
      setError(null)
      setInfoMessage(null)
      const form = new FormData()
      form.append('file', file)
      form.append('dry_run', 'false')
      form.append('on_conflict', 'update')
      const resp = await fetch(`${API_URL}/place-des-arts/requests/import-csv`, {
        method: 'POST',
        body: form
      })
      if (!resp.ok) {
        const msg = await resp.text()
        throw new Error(msg || `HTTP ${resp.status}`)
      }
      const data = await resp.json()
      setInfoMessage(data.message || `Import CSV: ${data.inserted || 0}`)
      await fetchData()
    } catch (err) {
      setError(err.message)
    } finally {
      setCsvLoading(false)
      if (fileInputRef.current) fileInputRef.current.value = ''
    }
  }

  const handleExport = () => {
    window.open(`${API_URL}/place-des-arts/export`, '_blank')
  }

  const updateCellRaw = async (id, field, value) => {
    const resp = await fetch(`${API_URL}/place-des-arts/requests/update-cell`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ request_id: id, field, value })
    })
    if (!resp.ok) {
      const msg = await resp.text()
      throw new Error(msg || `HTTP ${resp.status}`)
    }
  }

  const handleCellUpdate = async (id, field, value) => {
    try {
      setError(null)
      await updateCellRaw(id, field, value)
      await fetchData()
      setInfoMessage('Champ mis à jour')
    } catch (err) {
      setError(err.message)
    }
  }

  const handleChangeYearBatch = async () => {
    if (!selectedIds.length) return
    try {
      setError(null)
      const targetYear = parseInt(batchYear, 10)
      if (!targetYear || targetYear < 2000 || targetYear > 2100) throw new Error('Année invalide')

      for (const id of selectedIds) {
        const it = items.find((x) => x.id === id)
        if (!it) continue

        const applyYear = (dateStr) => {
          if (!dateStr) return null
          const d = new Date(dateStr)
          if (Number.isNaN(d.getTime())) return null
          d.setFullYear(targetYear)
          // Renvoie date ISO sans fuseau (évite le "Z" qui casse le parse)
          return d.toISOString().slice(0, 10)
        }

        const newAppt = applyYear(it.appointment_date)
        const newReq = applyYear(it.request_date)
        if (newAppt) await updateCellRaw(id, 'appointment_date', newAppt)
        if (newReq) await updateCellRaw(id, 'request_date', newReq)
      }

      await fetchData()
      setInfoMessage(`Année mise à ${batchYear} pour ${selectedIds.length} élément(s)`)
      setSelectedIds([])
    } catch (err) {
      setError(err.message)
    }
  }

  const handlePreview = async () => {
    if (!rawText.trim()) return
    try {
      setPreviewLoading(true)
      setInfoMessage(null)
      const resp = await fetch(`${API_URL}/place-des-arts/preview`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ raw_text: rawText, source: 'email' })
      })
      if (!resp.ok) {
        const msg = await resp.text()
        throw new Error(msg || `HTTP ${resp.status}`)
      }
      const data = await resp.json()
      setPreview(data.preview || [])
    } catch (err) {
      setError(err.message)
    } finally {
      setPreviewLoading(false)
    }
  }

  const handleImport = async () => {
    if (!rawText.trim()) return
    try {
      setImportLoading(true)
      setError(null)
      setInfoMessage(null)
      const resp = await fetch(`${API_URL}/place-des-arts/import`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ raw_text: rawText, source: 'email' })
      })
      if (!resp.ok) {
        const msg = await resp.text()
        throw new Error(msg || `HTTP ${resp.status}`)
      }
      const data = await resp.json()
      setInfoMessage(data.message || `Importé: ${data.imported || 0}`)
      setPreview([])
      await fetchData()
    } catch (err) {
      setError(err.message)
    } finally {
      setImportLoading(false)
    }
  }

  const statusMeta = {
    PENDING: { label: 'Nouveau', cls: 'bg-yellow-100 text-yellow-800' },
    CREATED_IN_GAZELLE: { label: 'Créé Gazelle', cls: 'bg-blue-100 text-blue-800' },
    ASSIGN_OK: { label: 'Assigné', cls: 'bg-green-100 text-green-800' },
    COMPLETED: { label: 'Complété', cls: 'bg-gray-100 text-gray-800' },
    BILLED: { label: 'Facturé', cls: 'bg-purple-100 text-purple-800' }
  }

  const techMap = {
    'usr_U9E5bLxrFiXqTbE8': 'Nick',
    'usr_allan': 'Allan',
    'usr_jp': 'JP'
  }
  const techMapShort = {
    'usr_U9E5bLxrFiXqTbE8': 'N',
    'usr_allan': 'A',
    'usr_jp': 'JP'
  }
  const techLabelToId = {
    'nick': 'usr_U9E5bLxrFiXqTbE8',
    'allan': 'usr_allan',
    'jp': 'usr_jp'
  }
  const technicianOptions = useMemo(() => {
    return [
      { id: 'usr_U9E5bLxrFiXqTbE8', label: 'Nick' },
      { id: 'usr_allan', label: 'Allan' },
      { id: 'usr_jp', label: 'JP' }
    ]
  }, [])

  const statusBadge = (status) => {
    const meta = statusMeta[status] || { label: status || 'N/A', cls: 'bg-gray-100 text-gray-800' }
    return <span className={`px-2 py-1 rounded text-xs font-medium ${meta.cls}`}>{meta.label}</span>
  }

  return (
    <div className={`${isFullscreen ? 'fixed inset-0 z-50 bg-white overflow-auto' : 'max-w-7xl mx-auto'} p-6 space-y-4`}>
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold text-gray-800">Place des Arts</h2>
          <p className="text-sm text-gray-500">Demandes importées (limite 200, tri date RDV desc)</p>
        </div>
        <div className="flex gap-3">
          <div className="flex items-center gap-1 bg-gray-100 text-gray-700 px-3 py-1 rounded-md text-sm">
            <span className="font-semibold">{stats.imported ?? 0}</span>
            <span>nouvelles</span>
          </div>
          <div className="flex items-center gap-1 bg-gray-100 text-gray-700 px-3 py-1 rounded-md text-sm">
            <span className="font-semibold">{stats.to_bill ?? 0}</span>
            <span>à facturer</span>
          </div>
          <div className="flex items-center gap-1 bg-gray-100 text-gray-700 px-3 py-1 rounded-md text-sm">
            <span className="font-semibold">{stats.this_month ?? 0}</span>
            <span>ce mois</span>
          </div>
          <button
            onClick={() => {
              const next = !isFullscreen
              setIsFullscreen(next)
              try {
                if (next && document.documentElement.requestFullscreen) {
                  document.documentElement.requestFullscreen()
                } else if (!next && document.exitFullscreen) {
                  document.exitFullscreen()
                }
              } catch (e) {
                // fallback silencieux
              }
            }}
            className="px-3 py-2 text-sm bg-white border border-gray-300 rounded-md hover:bg-gray-50"
          >
            {isFullscreen ? 'Mode fenêtré' : 'Plein écran'}
          </button>
        </div>
      </div>

      <div className="bg-white border border-gray-200 rounded-lg p-4 space-y-3">
        <h3 className="text-sm font-semibold text-gray-700">Import depuis email (copier-coller)</h3>
        <textarea
          value={rawText}
          onChange={(e) => setRawText(e.target.value)}
          placeholder="Collez le texte de l'email ici..."
          className="w-full min-h-[140px] border border-gray-300 rounded-md p-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
        <div className="flex gap-2">
          <button
            onClick={handlePreview}
            disabled={!rawText.trim() || previewLoading}
            className="px-3 py-2 text-sm bg-gray-100 hover:bg-gray-200 rounded-md border border-gray-200 disabled:opacity-50"
          >
            {previewLoading ? 'Prévisualisation...' : 'Prévisualiser'}
          </button>
          <button
            onClick={handleImport}
            disabled={!rawText.trim() || importLoading}
            className="px-3 py-2 text-sm bg-blue-600 text-white hover:bg-blue-700 rounded-md disabled:opacity-50"
          >
            {importLoading ? 'Import...' : 'Importer'}
          </button>
          <button
            onClick={() => { setRawText(''); setPreview([]); setInfoMessage(null); setError(null) }}
            className="px-3 py-2 text-sm bg-white border border-gray-200 rounded-md hover:bg-gray-50"
          >
            Effacer
          </button>
        </div>

        {infoMessage && (
          <div className="text-sm text-green-700 bg-green-50 border border-green-200 px-3 py-2 rounded">
            {infoMessage}
          </div>
        )}

        {preview.length > 0 && (
          <div className="border border-gray-200 rounded-md">
            <div className="bg-gray-50 px-3 py-2 text-sm font-medium text-gray-700 flex items-center justify-between">
              <span>Prévisualisation ({preview.length})</span>
              <span className="text-xs text-gray-500">
                {preview.filter(p => p.confidence < 1.0).length > 0 && (
                  `${preview.filter(p => p.confidence < 1.0).length} item(s) nécessitent une vérification`
                )}
              </span>
            </div>
            <div className="max-h-96 overflow-y-auto divide-y divide-gray-100">
              {preview.map((p, idx) => (
                <EditablePreviewItem
                  key={idx}
                  item={p}
                  index={idx}
                  rawText={rawText}
                  currentUser={currentUser}
                  onCorrect={(index, correctedFields) => {
                    // Mettre à jour le preview avec les champs corrigés
                    setPreview(prev => prev.map((item, i) =>
                      i === index ? { ...item, ...correctedFields, confidence: 1.0 } : item
                    ))
                  }}
                />
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Toolbar actions */}
      <div className="bg-white border border-gray-200 rounded-lg p-4 flex flex-wrap items-center gap-2">
        <button
          onClick={() => fileInputRef.current?.click()}
          className="px-3 py-2 text-sm bg-white border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50"
          disabled={csvLoading}
        >
          📄 Importer CSV
        </button>
        <input
          type="file"
          accept=".csv,text/csv"
          className="hidden"
          ref={fileInputRef}
          onChange={(e) => handleImportCsv(e.target.files?.[0])}
        />
        <button
          onClick={handleDeleteDuplicates}
          className="px-3 py-2 text-sm bg-white border border-gray-300 rounded-md hover:bg-gray-50"
        >
          🗑️ Nettoyer doublons
        </button>
        <button
          onClick={handleExport}
          className="px-3 py-2 text-sm bg-white border border-gray-300 rounded-md hover:bg-gray-50"
        >
          📊 Export CSV
        </button>
        <button
          onClick={() => setEditMode((v) => !v)}
          className={`px-3 py-2 text-sm border rounded-md ${editMode ? 'bg-blue-600 text-white border-blue-600' : 'bg-white border-gray-300 hover:bg-gray-50'}`}
        >
          {editMode ? 'Mode édition activé' : 'Mode édition (toutes colonnes)'}
        </button>
        <button
          onClick={() => setInfoMessage("Ajout manuel: à implémenter")}
          className="px-3 py-2 text-sm bg-white border border-gray-300 rounded-md hover:bg-gray-50"
        >
          ➕ Ajouter
        </button>
        <button
          disabled
          title="Sync Gazelle (à venir)"
          className="px-3 py-2 text-sm bg-gray-100 border border-gray-300 rounded-md text-gray-400 cursor-not-allowed"
        >
          🔄 Sync Gazelle
        </button>

        <div className="flex items-center gap-2 ml-auto flex-wrap">
          <input
            type="month"
            value={monthFilter}
            onChange={(e) => setMonthFilter(e.target.value)}
            className="border border-gray-300 rounded-md px-2 py-1 text-sm"
          />
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="border border-gray-300 rounded-md px-2 py-1 text-sm"
          >
            <option value="">Tous statuts</option>
            <option value="PENDING">Nouveau</option>
            <option value="CREATED_IN_GAZELLE">Créé Gazelle</option>
            <option value="ASSIGN_OK">Assigné</option>
            <option value="COMPLETED">Complété</option>
            <option value="BILLED">Facturé</option>
          </select>
          <input
            type="text"
            value={roomFilter}
            onChange={(e) => setRoomFilter(e.target.value)}
            placeholder="Salle"
            className="border border-gray-300 rounded-md px-2 py-1 text-sm"
          />
          <input
            type="text"
            value={technicianFilter}
            onChange={(e) => setTechnicianFilter(e.target.value)}
            placeholder="Technicien id"
            className="border border-gray-300 rounded-md px-2 py-1 text-sm"
          />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Recherche (client/piano)"
            className="border border-gray-300 rounded-md px-2 py-1 text-sm"
          />
          <button
            onClick={() => { setStatusFilter(''); setMonthFilter(''); setRoomFilter(''); setTechnicianFilter(''); setSearch(''); }}
            className="px-3 py-1 text-sm bg-gray-100 border border-gray-200 rounded-md hover:bg-gray-200"
          >
            Réinitialiser
          </button>
        </div>
      </div>

      {/* Actions batch */}
      {selectedIds.length > 0 && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 flex flex-wrap gap-2 items-center">
          <span className="text-sm text-blue-800 font-medium">{selectedIds.length} sélectionné(s)</span>
          <div className="flex items-center gap-1 text-xs">
            <input
              type="number"
              value={batchYear}
              onChange={(e) => setBatchYear(e.target.value)}
              className="w-20 border border-gray-300 rounded px-2 py-1"
              min="2000"
              max="2100"
            />
            <button
              onClick={handleChangeYearBatch}
              className="px-2 py-1 text-xs bg-white border border-gray-300 rounded hover:bg-gray-50"
            >
              Changer l'année
            </button>
          </div>
          <select
            onChange={(e) => handleStatusChange(e.target.value)}
            defaultValue=""
            className="text-xs border border-gray-300 rounded px-2 py-1 bg-white"
          >
            <option value="">Changer statut...</option>
            <option value="PENDING">Nouveau</option>
            <option value="CREATED_IN_GAZELLE">Créé Gazelle</option>
            <option value="ASSIGN_OK">Assigné</option>
            <option value="COMPLETED">Complété</option>
            <option value="BILLED">Facturé</option>
          </select>
          <button onClick={() => handleStatusChange('PENDING')} className="px-2 py-1 text-xs bg-white border border-gray-300 rounded hover:bg-gray-50">Statut: Nouveau</button>
          <button onClick={() => handleStatusChange('CREATED_IN_GAZELLE')} className="px-2 py-1 text-xs bg-white border border-gray-300 rounded hover:bg-gray-50">Statut: Créé Gazelle</button>
          <button onClick={() => handleStatusChange('ASSIGN_OK')} className="px-2 py-1 text-xs bg-white border border-gray-300 rounded hover:bg-gray-50">Statut: Assigné</button>
          <button onClick={() => handleStatusChange('COMPLETED')} className="px-2 py-1 text-xs bg-white border border-gray-300 rounded hover:bg-gray-50">Statut: Complété</button>
          <button onClick={handleBill} className="px-2 py-1 text-xs bg-white border border-gray-300 rounded hover:bg-gray-50">Facturer</button>
          <button onClick={handleDelete} className="px-2 py-1 text-xs bg-red-50 border border-red-200 text-red-700 rounded hover:bg-red-100">Supprimer</button>
          <button onClick={() => setSelectedIds([])} className="ml-auto px-2 py-1 text-xs text-blue-800">Désélectionner</button>
        </div>
      )}

      {loading && (
        <div className="text-gray-600">Chargement...</div>
      )}

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-3 py-2 rounded">
          Erreur: {error}
        </div>
      )}

      {!loading && !error && (
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200 text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-2 py-2">
                  <input
                    type="checkbox"
                    className="h-4 w-4"
                    checked={selectedIds.length > 0 && selectedIds.length === filteredItems.length}
                    onChange={toggleSelectAll}
                  />
                </th>
                <th onClick={() => toggleSort('request_date')} className="px-3 py-2 text-left font-medium text-gray-700 cursor-pointer select-none">Date demande {sortIndicator('request_date')}</th>
                <th onClick={() => toggleSort('appointment_date')} className="px-3 py-2 text-left font-medium text-gray-700 cursor-pointer select-none">Date RDV {sortIndicator('appointment_date')}</th>
                <th onClick={() => toggleSort('room')} className="px-3 py-2 text-left font-medium text-gray-700 cursor-pointer select-none">Salle {sortIndicator('room')}</th>
                <th onClick={() => toggleSort('for_who')} className="px-3 py-2 text-left font-medium text-gray-700 cursor-pointer select-none">Pour qui {sortIndicator('for_who')}</th>
                <th onClick={() => toggleSort('diapason')} className="px-3 py-2 text-left font-medium text-gray-700 cursor-pointer select-none">Diapason {sortIndicator('diapason')}</th>
                <th onClick={() => toggleSort('requester')} className="px-3 py-2 text-left font-medium text-gray-700 cursor-pointer select-none">Demandeur {sortIndicator('requester')}</th>
                <th onClick={() => toggleSort('piano')} className="px-3 py-2 text-left font-medium text-gray-700 cursor-pointer select-none">Piano {sortIndicator('piano')}</th>
                <th onClick={() => toggleSort('time')} className="px-3 py-2 text-left font-medium text-gray-700 cursor-pointer select-none">Heure {sortIndicator('time')}</th>
                <th onClick={() => toggleSort('technician_id')} className="px-3 py-2 text-left font-medium text-gray-700 cursor-pointer select-none">Qui le fait {sortIndicator('technician_id')}</th>
                <th onClick={() => toggleSort('notes')} className="px-3 py-2 text-left font-medium text-gray-700 cursor-pointer select-none">Commentaire {sortIndicator('notes')}</th>
                <th onClick={() => toggleSort('billing_amount')} className="px-3 py-2 text-left font-medium text-gray-700 cursor-pointer select-none">Facturation {sortIndicator('billing_amount')}</th>
                <th onClick={() => toggleSort('parking')} className="px-3 py-2 text-left font-medium text-gray-700 cursor-pointer select-none">Stationnement {sortIndicator('parking')}</th>
                <th onClick={() => toggleSort('status')} className="px-3 py-2 text-left font-medium text-gray-700 cursor-pointer select-none">Statut {sortIndicator('status')}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 bg-white">
              {sortedItems.map((it) => {
                // Déterminer si l'événement est terminé (statut COMPLETED)
                const isCompleted = it.status === 'COMPLETED'
                const rowClass = selectedIds.includes(it.id)
                  ? 'bg-blue-50'
                  : isCompleted
                    ? 'bg-green-50'
                    : ''

                return (
                <tr key={it.id} className={rowClass}>
                  <td className="px-2 py-2">
                    <input
                      type="checkbox"
                      className="h-4 w-4"
                      checked={selectedIds.includes(it.id)}
                      onChange={() => toggleSelect(it.id)}
                    />
                  </td>
                  <td className="px-3 py-2 text-gray-800">
                    {editMode ? (
                      <input
                        type="date"
                        value={it.request_date ? it.request_date.slice(0, 10) : ''}
                        onChange={(e) => handleCellUpdate(it.id, 'request_date', e.target.value)}
                        className="w-full border border-gray-200 rounded px-2 py-1 text-xs"
                      />
                    ) : (it.request_date ? it.request_date.slice(0, 10) : '—')}
                  </td>
                  <td className="px-3 py-2 text-gray-800">
                    {editMode ? (
                      <input
                        type="date"
                        value={it.appointment_date ? it.appointment_date.slice(0, 10) : ''}
                        onChange={(e) => handleCellUpdate(it.id, 'appointment_date', e.target.value)}
                        className="w-full border border-gray-200 rounded px-2 py-1 text-xs"
                      />
                    ) : (it.appointment_date ? it.appointment_date.slice(0, 10) : '—')}
                  </td>
                  <td className="px-3 py-2 text-gray-800">
                    {editMode ? (
                      <input
                        type="text"
                        defaultValue={it.room || ''}
                        onBlur={(e) => handleCellUpdate(it.id, 'room', e.target.value)}
                        className="w-full border border-gray-200 rounded px-2 py-1 text-xs"
                      />
                    ) : it.room}
                  </td>
                  <td className="px-3 py-2 text-gray-800">
                    {editMode ? (
                      <input
                        type="text"
                        defaultValue={it.for_who || ''}
                        onBlur={(e) => handleCellUpdate(it.id, 'for_who', e.target.value)}
                        className="w-full border border-gray-200 rounded px-2 py-1 text-xs"
                      />
                    ) : it.for_who}
                  </td>
                  <td className="px-3 py-2 text-gray-800">
                    {editMode ? (
                      <input
                        type="text"
                        defaultValue={it.diapason || ''}
                        onBlur={(e) => handleCellUpdate(it.id, 'diapason', e.target.value)}
                        className="w-full border border-gray-200 rounded px-2 py-1 text-xs"
                      />
                    ) : (it.diapason || '—')}
                  </td>
                  <td className="px-3 py-2 text-gray-800">
                    {editMode ? (
                      <input
                        type="text"
                        defaultValue={it.requester || ''}
                        onBlur={(e) => handleCellUpdate(it.id, 'requester', e.target.value)}
                        className="w-full border border-gray-200 rounded px-2 py-1 text-xs"
                      />
                    ) : (it.requester || '—')}
                  </td>
                  <td className="px-3 py-2 text-gray-800">
                    {editMode ? (
                      <input
                        type="text"
                        defaultValue={it.piano || ''}
                        onBlur={(e) => handleCellUpdate(it.id, 'piano', e.target.value)}
                        className="w-full border border-gray-200 rounded px-2 py-1 text-xs"
                      />
                    ) : it.piano}
                  </td>
                  <td className="px-3 py-2 text-gray-800">
                    {editMode ? (
                      <input
                        type="text"
                        defaultValue={it.time || ''}
                        onBlur={(e) => handleCellUpdate(it.id, 'time', e.target.value)}
                        className="w-full border border-gray-200 rounded px-2 py-1 text-xs"
                      />
                    ) : (it.time || '—')}
                  </td>
                  <td className="px-3 py-2 text-gray-800">
                    <input
                      type="text"
                      defaultValue={techMap[it.technician_id] || it.technician || ''}
                      list="tech-options"
                      onBlur={(e) => {
                        const val = e.target.value.trim()
                        if (val === '') return handleCellUpdate(it.id, 'technician_id', '')
                        const mapped = techLabelToId[val.toLowerCase()] || (val.toLowerCase().startsWith('usr_') ? val : val)
                        handleCellUpdate(it.id, 'technician_id', mapped)
                      }}
                      className="w-full border border-gray-200 rounded px-2 py-1 text-xs"
                      placeholder="Technicien"
                      title="Saisir ou choisir le technicien"
                    />
                  </td>
                  <td className="px-3 py-2 text-gray-800">
                    {editMode ? (
                      <input
                        type="text"
                        defaultValue={it.notes || ''}
                        onBlur={(e) => handleCellUpdate(it.id, 'notes', e.target.value)}
                        className="w-full border border-gray-200 rounded px-2 py-1 text-xs"
                      />
                    ) : (it.notes || '—')}
                  </td>
                  <td className="px-3 py-2 text-gray-800">
                    {editMode ? (
                      <input
                        type="number"
                        step="0.01"
                        defaultValue={it.billing_amount ?? ''}
                        onBlur={(e) => handleCellUpdate(it.id, 'billing_amount', e.target.value)}
                        className="w-full border border-gray-200 rounded px-2 py-1 text-xs"
                      />
                    ) : (it.billing_amount ?? '—')}
                  </td>
                  <td className="px-3 py-2 text-gray-800">
                    {editMode ? (
                      <input
                        type="text"
                        defaultValue={it.parking || ''}
                        onBlur={(e) => handleCellUpdate(it.id, 'parking', e.target.value)}
                        className="w-full border border-gray-200 rounded px-2 py-1 text-xs"
                      />
                    ) : (it.parking || '—')}
                  </td>
                  <td className="px-3 py-2">
                    <select
                      value={it.status || ''}
                      onChange={(e) => handleStatusChange(e.target.value, [it.id])}
                      className="text-xs border border-gray-300 rounded px-2 py-1 bg-white"
                    >
                      <option value="PENDING">Nouveau</option>
                      <option value="CREATED_IN_GAZELLE">Créé Gazelle</option>
                      <option value="ASSIGN_OK">Assigné</option>
                      <option value="COMPLETED">Complété</option>
                      <option value="BILLED">Facturé</option>
                    </select>
                  </td>
                </tr>
                )
              })}
              {filteredItems.length === 0 && (
                <tr>
                  <td colSpan={14} className="px-3 py-4 text-center text-gray-500">Aucune donnée</td>
                </tr>
              )}
            </tbody>
          </table>
          <datalist id="tech-options">
            {technicianOptions.map((opt) => (
              <option key={opt.id} value={opt.id}>{opt.label}</option>
            ))}
          </datalist>
        </div>
      )}
    </div>
  )
}
