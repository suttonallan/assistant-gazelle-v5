import { useEffect, useState, useCallback, useMemo, useRef } from 'react'

const API_URL = import.meta.env.VITE_API_URL || 'https://assistant-gazelle-v5-api.onrender.com'

export default function PlaceDesArtsDashboard() {
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [stats, setStats] = useState({ imported: 0, to_bill: 0, this_month: 0 })

  // Filtres
  const [statusFilter, setStatusFilter] = useState('')
  const [monthFilter, setMonthFilter] = useState('')
  const [search, setSearch] = useState('')
  const [technicianFilter, setTechnicianFilter] = useState('')
  const [roomFilter, setRoomFilter] = useState('')

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

  const handleStatusChange = async (newStatus) => {
    if (!newStatus || selectedIds.length === 0) return
    await callAction(`${API_URL}/place-des-arts/requests/update-status-batch`, {
      request_ids: selectedIds,
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
    await callAction(`${API_URL}/place-des-arts/requests/delete-duplicates`, {})
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

  const statusBadge = (status) => {
    const meta = statusMeta[status] || { label: status || 'N/A', cls: 'bg-gray-100 text-gray-800' }
    return <span className={`px-2 py-1 rounded text-xs font-medium ${meta.cls}`}>{meta.label}</span>
  }

  return (
    <div className="max-w-7xl mx-auto p-6 space-y-4">
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
            <div className="bg-gray-50 px-3 py-2 text-sm font-medium text-gray-700">
              Prévisualisation ({preview.length})
            </div>
            <div className="max-h-56 overflow-y-auto divide-y divide-gray-100">
              {preview.map((p, idx) => (
                <div key={idx} className="px-3 py-2 text-sm space-y-1">
                  <div className="text-gray-800">
                    <span className="font-medium">Date RDV:</span> {p.appointment_date || '—'}
                    {p.time && <span className="ml-2 text-gray-600">{p.time}</span>}
                  </div>
                  <div className="text-gray-700">
                    <span className="font-medium">Salle:</span> {p.room || '—'}
                  </div>
                  <div className="text-gray-700">
                    <span className="font-medium">Pour qui:</span> {p.for_who || '—'}
                  </div>
                  <div className="text-gray-700">
                    <span className="font-medium">Piano:</span> {p.piano || '—'}
                  </div>
                  {p.requester && (
                    <div className="text-gray-700">
                      <span className="font-medium">Demandeur:</span> {p.requester}
                    </div>
                  )}
                  {p.warnings && p.warnings.length > 0 && (
                    <div className="text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded px-2 py-1">
                      Avertissements: {p.warnings.join(' | ')}
                    </div>
                  )}
                </div>
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
                <th className="px-3 py-2 text-left font-medium text-gray-700">Date demande</th>
                <th className="px-3 py-2 text-left font-medium text-gray-700">Date RDV</th>
                <th className="px-3 py-2 text-left font-medium text-gray-700">Salle</th>
                <th className="px-3 py-2 text-left font-medium text-gray-700">Pour qui</th>
                <th className="px-3 py-2 text-left font-medium text-gray-700">Diapason</th>
                <th className="px-3 py-2 text-left font-medium text-gray-700">Demandeur</th>
                <th className="px-3 py-2 text-left font-medium text-gray-700">Piano</th>
                <th className="px-3 py-2 text-left font-medium text-gray-700">Heure</th>
                <th className="px-3 py-2 text-left font-medium text-gray-700">Qui le fait</th>
                <th className="px-3 py-2 text-left font-medium text-gray-700">Commentaire</th>
                <th className="px-3 py-2 text-left font-medium text-gray-700">Facturation</th>
                <th className="px-3 py-2 text-left font-medium text-gray-700">Stationnement</th>
                <th className="px-3 py-2 text-left font-medium text-gray-700">Statut</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 bg-white">
              {filteredItems.map((it) => (
                <tr key={it.id} className={selectedIds.includes(it.id) ? 'bg-blue-50' : ''}>
                  <td className="px-2 py-2">
                    <input
                      type="checkbox"
                      className="h-4 w-4"
                      checked={selectedIds.includes(it.id)}
                      onChange={() => toggleSelect(it.id)}
                    />
                  </td>
                  <td className="px-3 py-2 text-gray-800">{it.request_date ? it.request_date.slice(0, 10) : '—'}</td>
                  <td className="px-3 py-2 text-gray-800">{it.appointment_date ? it.appointment_date.slice(0, 10) : '—'}</td>
                  <td className="px-3 py-2 text-gray-800">{it.room}</td>
                  <td className="px-3 py-2 text-gray-800">{it.for_who}</td>
                  <td className="px-3 py-2 text-gray-800">{it.diapason || '—'}</td>
                  <td className="px-3 py-2 text-gray-800">{it.requester || '—'}</td>
                  <td className="px-3 py-2 text-gray-800">{it.piano}</td>
                  <td className="px-3 py-2 text-gray-800">{it.time || '—'}</td>
                  <td className="px-3 py-2 text-gray-800">
                    {(() => {
                      const techMap = {
                        'usr_U9E5bLxrFiXqTbE8': 'Nick',
                        'usr_allan': 'Allan',
                        'usr_louise': 'Louise',
                        'usr_jp': 'JP'
                      }
                      return techMap[it.technician_id] || it.technician_id || '—'
                    })()}
                  </td>
                  <td className="px-3 py-2 text-gray-800">{it.notes || '—'}</td>
                  <td className="px-3 py-2 text-gray-800">{it.billing_amount ?? '—'}</td>
                  <td className="px-3 py-2 text-gray-800">{it.parking || '—'}</td>
                  <td className="px-3 py-2">{statusBadge(it.status)}</td>
                </tr>
              ))}
              {filteredItems.length === 0 && (
                <tr>
                  <td colSpan={14} className="px-3 py-4 text-center text-gray-500">Aucune donnée</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
