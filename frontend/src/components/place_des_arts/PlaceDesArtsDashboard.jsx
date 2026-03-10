import { useEffect, useState, useCallback, useMemo } from 'react'
import EditablePreviewItem from './EditablePreviewItem'
import PDAInventoryTable from './PDAInventoryTable'

import { API_URL } from '../../utils/apiConfig'

export default function PlaceDesArtsDashboard({ currentUser }) {
  // Onglets: 'demandes' ou 'inventaire-pianos' (Demandes en premier)
  const [currentView, setCurrentView] = useState('demandes')
  
  const isRestrictedUser = currentUser?.role === 'nick' // Louise a accès complet aux demandes
  const isAdmin = currentUser?.role === 'admin' // Seul l'admin peut nettoyer doublons et exporter CSV
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [stats, setStats] = useState({ imported: 0, to_bill: 0, this_month: 0 })
  const [isFullscreen, setIsFullscreen] = useState(false)
  const [editMode, setEditMode] = useState(false)
  const [creating, setCreating] = useState(false)
  const [createForm, setCreateForm] = useState({
    appointment_date: '',
    room: '',
    for_who: '',
    piano: '',
    time: '',
    diapason: '',
    requester: '',
    technician_id: '',
    notes: '',
    billing_amount: '',
    parking: ''
  })
  const [batchYear, setBatchYear] = useState(new Date().getFullYear())

  // Filtres
  const [statusFilter, setStatusFilter] = useState('')
  const [monthFilter, setMonthFilter] = useState('')
  const [search, setSearch] = useState('')
  const [technicianFilter, setTechnicianFilter] = useState('')
  const [roomFilter, setRoomFilter] = useState('')
  const [sortField, setSortField] = useState('')
  const [sortDir, setSortDir] = useState('asc')
  const [orphanServices, setOrphanServices] = useState([])
  const [addingOrphan, setAddingOrphan] = useState(null) // appointment_id en cours de sauvegarde
  const [orphanPreview, setOrphanPreview] = useState(null) // formulaire prévisualisation orphelin

  // Sélection
  const [selectedIds, setSelectedIds] = useState([])

  // Recherche concert
  const [concertSearch, setConcertSearch] = useState({}) // { [requestId]: { loading, data, error } }

  // Import email
  const [rawText, setRawText] = useState('')
  const [preview, setPreview] = useState([])
  const [previewLoading, setPreviewLoading] = useState(false)
  const [importLoading, setImportLoading] = useState(false)
  const [infoMessage, setInfoMessage] = useState(null)
  // plus de CSV direct ici

  const fetchData = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)
      const resp = await fetch(`${API_URL}/api/place-des-arts/requests?limit=200`)
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
      const resp = await fetch(`${API_URL}/api/place-des-arts/stats`)
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

  // Recherche de programme de concert pour une demande
  const handleConcertSearch = useCallback(async (item) => {
    if (!item.for_who) return
    const id = item.id
    setConcertSearch(prev => ({ ...prev, [id]: { loading: true, data: null, error: null } }))
    try {
      const params = new URLSearchParams({ for_who: item.for_who })
      if (item.appointment_date) params.append('date', item.appointment_date.slice(0, 10))
      if (item.room) params.append('room', item.room)
      const resp = await fetch(`${API_URL}/api/place-des-arts/concert-search?${params}`)
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`)
      const data = await resp.json()
      setConcertSearch(prev => ({ ...prev, [id]: { loading: false, data, error: null } }))
    } catch (err) {
      setConcertSearch(prev => ({ ...prev, [id]: { loading: false, data: null, error: err.message } }))
    }
  }, [])

  const closeConcertSearch = useCallback((id) => {
    setConcertSearch(prev => {
      const next = { ...prev }
      delete next[id]
      return next
    })
  }, [])

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

  // Générer une liste complète de mois (2 mois passés → 12 mois futurs)
  const availableMonths = useMemo(() => {
    const months = []
    const today = new Date()

    // Générer de -2 mois à +12 mois (ordre chronologique)
    for (let i = -2; i <= 12; i++) {
      const date = new Date(today.getFullYear(), today.getMonth() + i, 1)
      const monthStr = date.toISOString().substring(0, 7) // YYYY-MM
      months.push(monthStr)
    }

    return months // Ordre chronologique (octobre 2025 → décembre 2026)
  }, [])

  // Calculer le total mensuel (facturation + stationnement)
  const monthlyTotal = useMemo(() => {
    if (!monthFilter) return null

    let totalBilling = 0
    let totalParking = 0

    filteredItems.forEach(item => {
      // Additionner la facturation
      const billing = parseFloat(item.billing_amount) || 0
      totalBilling += billing

      // Additionner le stationnement (peut être texte ou nombre)
      const parking = parseFloat(item.parking) || 0
      totalParking += parking
    })

    return {
      billing: totalBilling,
      parking: totalParking,
      total: totalBilling + totalParking,
      count: filteredItems.length
    }
  }, [filteredItems, monthFilter])

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

    // Si on passe à "Assigné", demander d'abord de choisir un technicien
    if (newStatus === 'ASSIGN_OK') {
      const techChoice = prompt(
        `Assigné à quel technicien?\n\n` +
        `1 - Nick\n` +
        `2 - Allan\n` +
        `3 - JP\n` +
        `\nEntrez le numéro (1, 2 ou 3):`
      )

      if (!techChoice) return // Annulé

      const techMap = {
        '1': 'usr_HcCiFk7o0vZ9xAI0', // Nick (ID Gazelle)
        '2': 'usr_ofYggsCDt2JAVeNP', // Allan (ID Gazelle)
        '3': 'usr_ReUSmIJmBF86ilY1', // JP (ID Gazelle)
      }

      const techId = techMap[techChoice.trim()]
      if (!techId) {
        alert('Choix invalide. Veuillez entrer 1, 2 ou 3.')
        return
      }

      // Assigner le technicien (le statut ASSIGN_OK sera automatique via handleCellUpdate)
      try {
        console.log(`🚀 Assignation de ${ids.length} demande(s) au technicien ${techId}`)
        setError(null)
        setInfoMessage(null)

        for (const id of ids) {
          console.log(`  ⏳ Mise à jour demande ${id}...`)
          await updateCellRaw(id, 'technician_id', techId)
          await updateCellRaw(id, 'status', 'ASSIGN_OK')
          console.log(`  ✅ Demande ${id} mise à jour`)
        }

        console.log(`🔄 Rechargement des données...`)
        await fetchData()

        const message = `Technicien assigné pour ${ids.length} élément(s)`
        console.log(`✅ ${message}`)
        setInfoMessage(message)
        setSelectedIds([])
      } catch (err) {
        console.error(`❌ Erreur lors de l'assignation:`, err)
        setError(`Erreur: ${err.message}`)
      }
      return
    }

    // Si on passe à "Créé Gazelle", valider que le RV existe dans Gazelle
    if (newStatus === 'CREATED_IN_GAZELLE') {
      try {
        setError(null)
        setInfoMessage('🔍 Validation en cours...')

        // Vérifier chaque demande sélectionnée
        const warnings = []
        for (const id of ids) {
          const item = items.find(it => it.id === id)
          if (!item) continue

          // Appeler l'API de validation
          const resp = await fetch(`${API_URL}/api/place-des-arts/validate-gazelle-rv`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              request_id: id,
              appointment_date: item.appointment_date,
              room: item.room
            })
          })

          if (!resp.ok) {
            throw new Error(`Erreur validation: ${resp.status}`)
          }

          const data = await resp.json()
          if (!data.found) {
            warnings.push({
              date: item.appointment_date,
              room: item.room,
              for_who: item.for_who || '(sans nom)'
            })
          }
        }

        // Si des RV ne sont pas trouvés, afficher l'alerte en rouge
        if (warnings.length > 0) {
          const warningList = warnings.map(w =>
            `${w.date} - ${w.room} - ${w.for_who}`
          ).join('\n')

          setError(`❌ ALERTE: ${warnings.length} RV non trouvé(s) dans Gazelle:\n\n${warningList}\n\nVoulez-vous quand même marquer comme "Créé Gazelle"?`)

          // Demander confirmation
          if (!window.confirm(`❌ ALERTE: ${warnings.length} RV non trouvé(s) dans Gazelle:\n\n${warningList}\n\nVoulez-vous quand même marquer comme "Créé Gazelle"?`)) {
            setError(null)
            setInfoMessage(null)
            return // Annulé
          }
        }

        // Procéder avec le changement de statut
        await callAction(`${API_URL}/api/place-des-arts/requests/update-status-batch`, {
          request_ids: ids,
          status: newStatus
        })

        if (warnings.length === 0) {
          setInfoMessage(`✅ ${ids.length} demande(s) marquée(s) "Créé Gazelle" (RV validés)`)
        }

      } catch (err) {
        setError(err.message || 'Erreur lors de la validation')
      }
      return
    }

    // Pour les autres statuts, changement direct
    await callAction(`${API_URL}/api/place-des-arts/requests/update-status-batch`, {
      request_ids: ids,
      status: newStatus
    })
  }

  const handleBill = async () => {
    if (selectedIds.length === 0) return
    await callAction(`${API_URL}/api/place-des-arts/requests/bill`, {
      request_ids: selectedIds,
      status: 'BILLED'
    })
  }

  const handleDelete = async () => {
    if (selectedIds.length === 0) return
    await callAction(`${API_URL}/api/place-des-arts/requests/delete`, {
      request_ids: selectedIds
    })
  }

  const handleDeleteDuplicates = async () => {
    try {
      setError(null)
      setInfoMessage(null)

      // 1. Récupérer la liste des doublons
      const resp = await fetch(`${API_URL}/api/place-des-arts/requests/find-duplicates`)
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
      await callAction(`${API_URL}/api/place-des-arts/requests/delete-duplicates`, {})

    } catch (err) {
      setError(err.message || 'Erreur lors de la suppression des doublons')
    }
  }

  const handleSyncGazelle = async () => {
    // Synchronisation complète : lier les RV ET vérifier les complétés
    try {
      setError(null)
      setInfoMessage('🔄 Synchronisation complète en cours... (1/2)')

      // Étape 1: Synchroniser les demandes avec les RV Gazelle
      const allIds = filteredItems.map(item => item.id)
      const syncResp = await fetch(`${API_URL}/api/place-des-arts/sync-manual`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ request_ids: allIds })
      })

      if (!syncResp.ok) {
        throw new Error(`Erreur sync: ${syncResp.status}`)
      }

      const syncData = await syncResp.json()
      
      // Étape 2: Vérifier les RV complétés
      setInfoMessage('🔄 Vérification des RV complétés... (2/2)')
      
      const checkResp = await fetch(`${API_URL}/api/place-des-arts/check-completed`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      })

      if (!checkResp.ok) {
        throw new Error(`Erreur vérification complétés: ${checkResp.status}`)
      }

      const checkData = await checkResp.json()

      // Recharger les données
      await fetchData()

      // Afficher le résultat combiné
      const messages = []
      if (syncData.updated > 0) {
        messages.push(`${syncData.updated} demande(s) liée(s) à un RV Gazelle`)
      }
      if (checkData.updated > 0) {
        messages.push(`${checkData.updated} demande(s) marquée(s) comme complétée(s)`)
      }
      if (syncData.completed > 0) {
        messages.push(`${syncData.completed} demande(s) complétée(s) lors de la sync`)
      }

      if (messages.length > 0) {
        setInfoMessage(`✅ Synchronisation terminée: ${messages.join(', ')}`)
      } else {
        setInfoMessage('✅ Synchronisation terminée - Aucune mise à jour nécessaire')
      }

      // Afficher les warnings s'il y en a
      if (syncData.has_warnings && syncData.warnings && syncData.warnings.length > 0) {
        const warningList = syncData.warnings.map(w =>
          `⚠️ ${w.error_code || 'RV_NOT_FOUND'}\n   ${w.date} - ${w.room} - ${w.for_who || '(sans nom)'}`
        ).join('\n\n')
        setError(`⚠️ ${syncData.warnings.length} RV non trouvé(s) dans Gazelle:\n\n${warningList}`)
      }

      // Détecter les services Gazelle orphelins
      if (checkData.orphan_services?.length > 0) {
        setOrphanServices(checkData.orphan_services)
      } else {
        setOrphanServices([])
      }

    } catch (err) {
      setError(err.message || 'Erreur lors de la synchronisation')
    }
  }

  const handleExport = () => {
    const params = monthFilter ? `?month=${monthFilter}` : ''
    window.open(`${API_URL}/api/place-des-arts/export${params}`, '_blank')
  }

  const handleDismissOrphan = async (orphan) => {
    try {
      const resp = await fetch(`${API_URL}/api/place-des-arts/orphans/dismiss`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ appointment_id: orphan.appointment_id })
      })
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`)
      setOrphanServices(prev => prev.filter(o => o.appointment_id !== orphan.appointment_id))
    } catch (err) {
      alert(`Erreur: ${err.message}`)
    }
  }

  const handleAddOrphan = (orphan) => {
    // Ouvrir le formulaire de prévisualisation au lieu de créer directement
    const cleanTitle = (orphan.title || '')
      .replace(/^PLACE\s*DES\s*ARTS\s*[-–—:]\s*/i, '')
      .trim()
    setOrphanPreview({
      appointment_id: orphan.appointment_id,
      appointment_date: orphan.date || '',
      time: orphan.time || '',
      room: '',
      for_who: cleanTitle || orphan.title || '',
      technician_id: orphan.technician_id || null,
      notes: orphan.description || '',
      status: orphan.status === 'completed' ? 'COMPLETED' : 'CONFIRMED',
    })
  }

  const handleConfirmOrphan = async () => {
    if (!orphanPreview) return
    setAddingOrphan(orphanPreview.appointment_id)
    try {
      const resp = await fetch(`${API_URL}/api/place-des-arts/requests/create`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(orphanPreview)
      })
      if (!resp.ok) {
        const err = await resp.json().catch(() => ({}))
        throw new Error(err.detail || `Erreur ${resp.status}`)
      }
      // Retirer de la liste orpheline et fermer le formulaire
      setOrphanServices(prev => prev.filter(o => o.appointment_id !== orphanPreview.appointment_id))
      setOrphanPreview(null)
      await fetchData()
    } catch (err) {
      alert(`Erreur ajout: ${err.message}`)
    } finally {
      setAddingOrphan(null)
    }
  }

  const updateCellRaw = async (id, field, value, retries = 2) => {
    try {
      console.log(`🔧 updateCellRaw: id=${id}, field=${field}, value=${value}`)

      // Timeout de 30 secondes pour le cold start de Render
      const controller = new AbortController()
      const timeoutId = setTimeout(() => controller.abort(), 30000)

      try {
        const resp = await fetch(`${API_URL}/api/place-des-arts/requests/update-cell`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ request_id: id, field, value }),
          signal: controller.signal
        })
        clearTimeout(timeoutId)

        console.log(`✅ Response status: ${resp.status}`)
        if (!resp.ok) {
          const msg = await resp.text()
          console.error(`❌ Error response: ${msg}`)
          throw new Error(msg || `HTTP ${resp.status}`)
        }
        const data = await resp.json()
        console.log(`✅ Update successful:`, data)
        return data
      } catch (fetchErr) {
        clearTimeout(timeoutId)

        // Retry si c'est une erreur réseau et qu'il reste des tentatives
        if (retries > 0 && (fetchErr.name === 'AbortError' || fetchErr.message === 'Failed to fetch')) {
          console.log(`⏳ Retry ${3 - retries}/2 après erreur réseau...`)
          await new Promise(resolve => setTimeout(resolve, 2000)) // Wait 2s before retry
          return await updateCellRaw(id, field, value, retries - 1)
        }
        throw fetchErr
      }
    } catch (err) {
      console.error(`❌ updateCellRaw failed:`, err)
      if (err.name === 'AbortError') {
        throw new Error('Timeout: L\'API met trop de temps à répondre (peut-être en train de se réveiller)')
      }
      throw err
    }
  }

  const pushToGazelle = async (requestId, pianoGazelleId, technicianId, notes) => {
    try {
      if (!pianoGazelleId || !technicianId || !notes) {
        return null // Pas de push si données manquantes
      }

      const resp = await fetch(`${API_URL}/api/place-des-arts/requests/push-to-gazelle`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          request_id: requestId,
          piano_id: pianoGazelleId,
          technician_id: technicianId,
          summary: 'Accord', // Par défaut, on peut l'adapter selon le contexte
          comment: notes,
          update_last_tuned: true
        })
      })

      if (!resp.ok) {
        const errorText = await resp.text()
        throw new Error(errorText || `HTTP ${resp.status}`)
      }

      const data = await resp.json()
      return data
    } catch (err) {
      console.error('Erreur push vers Gazelle:', err)
      throw err
    }
  }

  const handleCellUpdate = async (id, field, value) => {
    try {
      setError(null)
      // Si plusieurs lignes sont cochées et incluent cette ligne, propager la même valeur
      const targetIds = selectedIds.includes(id) && selectedIds.length > 1 ? selectedIds : [id]
      let gazelleSuccess = false

      for (const targetId of targetIds) {
        const item = items.find(it => it.id === targetId)
        if (!item) continue

        // Si changement de technicien, vérifier dans Gazelle d'abord
        if (field === 'technician_id' && value && value !== A_ATTRIBUER_ID) {
          // Vérifier que le RV dans Gazelle a vraiment ce technicien
          if (item.appointment_id) {
            try {
              const verifyResp = await fetch(`${API_URL}/api/place-des-arts/requests/${targetId}/verify-technician`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ technician_id: value })
              })
              
              if (verifyResp.ok) {
                const verifyData = await verifyResp.json()
                if (!verifyData.confirmed) {
                  setError(`⚠️ Le RV dans Gazelle n'a pas encore ce technicien. Vérifiez dans Gazelle d'abord.`)
                  return
                }
              }
            } catch (err) {
              console.warn('Erreur vérification technicien dans Gazelle:', err)
              // Continuer quand même si l'endpoint n'existe pas encore
            }
          }
        }

        await updateCellRaw(targetId, field, value)
        
        if (field === 'technician_id' && value && value !== A_ATTRIBUER_ID) {
          // Auto: passer en "Assigné" dès qu'un vrai technicien est défini (pas "À attribuer")
          await updateCellRaw(targetId, 'status', 'ASSIGN_OK')
        }

        // Si on met à jour les notes ET qu'on a un technicien, pousser vers Gazelle
        if (field === 'notes' && value && item.technician_id) {
          try {
            // Récupérer le piano_id Gazelle depuis l'API
            const pianoIdResp = await fetch(`${API_URL}/api/place-des-arts/requests/${targetId}/gazelle-piano-id`)
            if (pianoIdResp.ok) {
              const pianoIdData = await pianoIdResp.json()
              const pianoGazelleId = pianoIdData.piano_id
              
              if (pianoGazelleId && item.technician_id) {
                const gazelleResult = await pushToGazelle(
                  targetId,
                  pianoGazelleId,
                  item.technician_id,
                  value
                )
                if (gazelleResult && gazelleResult.success) {
                  gazelleSuccess = true
                }
              } else {
                console.warn('Piano Gazelle ou technicien manquant pour push')
              }
            }
          } catch (gazelleErr) {
            console.warn('Push Gazelle échoué (non bloquant):', gazelleErr)
            // Ne pas bloquer la mise à jour locale si Gazelle échoue
          }
        }
      }
      
      await fetchData()
      
      let message = `Champ mis à jour pour ${targetIds.length} élément(s)`
      if (gazelleSuccess) {
        message += ' - Mis à jour dans Gazelle ✓'
      }
      setInfoMessage(message)
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
    console.log('🔍 handlePreview appelé', { rawText: rawText?.substring(0, 50), API_URL })
    if (!rawText.trim()) {
      console.log('⚠️ rawText vide, retour')
      return
    }
    try {
      setPreviewLoading(true)
      setInfoMessage(null)
      setError(null)
      console.log('📤 Envoi requête preview...', `${API_URL}/api/place-des-arts/preview`)
      console.log('📝 Texte envoyé (preview):', {
        length: rawText.length,
        first200: rawText.substring(0, 200),
        lines: rawText.split('\n').length,
        fullText: rawText
      })
      const resp = await fetch(`${API_URL}/api/place-des-arts/preview`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ raw_text: rawText, source: 'email' })
      })
      console.log('📥 Réponse reçue', resp.status, resp.statusText)
      if (!resp.ok) {
        const msg = await resp.text()
        console.error('❌ Erreur HTTP', resp.status, msg)
        throw new Error(msg || `HTTP ${resp.status}`)
      }
      const data = await resp.json()
      console.log('✅ Données reçues', { 
        success: data.success, 
        count: data.count, 
        previewLength: data.preview?.length,
        preview: data.preview,
        needs_validation: data.needs_validation,
        message: data.message,
        fullResponse: JSON.stringify(data, null, 2)
      })
      console.log('📝 Texte envoyé à l\'API:', rawText.substring(0, 200))
      
      // Mettre à jour le preview AVANT de reformater le texte
      const previewItems = data.preview || []
      console.log('📦 Mise à jour preview state', { previewItemsCount: previewItems.length })
      setPreview(previewItems)
      
      if (previewItems.length === 0) {
        // NOUVEAU: Créer un preview minimal pour permettre l'édition manuelle
        const emptyPreview = [{
          appointment_date: null,
          room: null,
          for_who: null,
          diapason: null,
          requester: null,
          piano: null,
          time: null,
          service: null,
          notes: null,
          confidence: 0.0,
          warnings: ['Aucun champ détecté automatiquement - Complétez manuellement'],
          needs_validation: true,
          learned: false,
          duplicate_of: []
        }]
        setPreview(emptyPreview)
        setInfoMessage('Aucun champ détecté automatiquement. Complétez les champs manuellement ci-dessous.')
        setError(null)
        console.log('⚠️ Aucun preview item détecté, création d\'un preview vide pour édition manuelle')
      } else {
        const infoMsg = `${previewItems.length} demande(s) détectée(s)${data.needs_validation ? ' - Vérification et complétion requises' : ''}`
        setInfoMessage(infoMsg)
        setError(null)
        console.log('✅ Preview items à afficher:', previewItems.length)
      }
      
      // Reformater le texte collé : chaque bloc (séparé par une nouvelle date) devient une ligne avec virgules
      // Pattern: une ligne qui commence par un nombre suivi d'un mois (ex: "30 janv", "31 janv")
      const datePattern = /^\s*\d{1,2}\s*(jan|fév|fev|mar|avr|mai|juin|juil|aoû|aou|sep|oct|nov|déc|dec)/i
      const lines = rawText.split('\n')
      const blocks = []
      let currentBlockLines = []

      for (const line of lines) {
        if (datePattern.test(line) && currentBlockLines.length > 0) {
          // Nouvelle date = nouveau bloc
          blocks.push(currentBlockLines.filter(l => l.trim()).join(', '))
          currentBlockLines = [line.trim()]
        } else if (line.trim()) {
          currentBlockLines.push(line.trim())
        }
      }
      // Dernier bloc
      if (currentBlockLines.length > 0) {
        blocks.push(currentBlockLines.filter(l => l.trim()).join(', '))
      }

      const formattedText = blocks.filter(b => b.length > 0).join('\n')
      if (formattedText !== rawText) {
        setRawText(formattedText)
        console.log('📝 Texte reformaté')
      }
      
      console.log('✅ Preview terminé', { previewCount: previewItems.length })
    } catch (err) {
      console.error('❌ Erreur handlePreview', err)
      setError(err.message)
    } finally {
      setPreviewLoading(false)
    }
  }

  const handleImport = async () => {
    if (!rawText.trim() && preview.length === 0) return
    try {
      setImportLoading(true)
      setError(null)
      setInfoMessage(null)

      let resp
      if (preview.length > 0) {
        // Utiliser les données de la preview (avec les corrections manuelles)
        resp = await fetch(`${API_URL}/api/place-des-arts/import-preview`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ items: preview })
        })
      } else {
        // Import direct sans preview
        resp = await fetch(`${API_URL}/api/place-des-arts/import`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ raw_text: rawText, source: 'email' })
        })
      }

      if (!resp.ok) {
        const msg = await resp.text()
        throw new Error(msg || `HTTP ${resp.status}`)
      }
      const data = await resp.json()
      setInfoMessage(data.message || `Importé: ${data.imported || 0}`)
      setPreview([])
      setRawText('')
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
    'usr_HcCiFk7o0vZ9xAI0': 'Nick',     // ID Gazelle pour Nicolas
    'usr_ofYggsCDt2JAVeNP': 'Allan',    // ID Gazelle pour Allan
    'usr_ReUSmIJmBF86ilY1': 'JP',       // ID Gazelle pour Jean-Philippe
    'usr_HihJsEgkmpTEziJo': 'À attribuer', // Placeholder "À attribuer" dans Gazelle
    'usr_QmEpdeM2xMgZVkDS': 'JP',       // ID alternatif pour JP (si différent dans Gazelle)
    // Anciens IDs pour compatibilité (ne devraient plus être utilisés)
    'usr_U9E5bLxrFiXqTbE8': 'Nick (ancien ID)',
    'usr_allan': 'Allan (ancien ID)',
    'usr_jp': 'JP (ancien ID)'
  }

  // IDs des vrais techniciens (pas "À attribuer")
  // Inclure aussi les IDs alternatifs qui correspondent aux mêmes techniciens
  const REAL_TECHNICIAN_IDS = new Set([
    'usr_HcCiFk7o0vZ9xAI0',  // Nick
    'usr_ofYggsCDt2JAVeNP',  // Allan
    'usr_ReUSmIJmBF86ilY1',  // JP
    'usr_QmEpdeM2xMgZVkDS',  // JP (ID alternatif si différent dans Gazelle)
  ])
  
  // Fonction pour normaliser l'ID technicien (convertir les IDs alternatifs)
  const normalizeTechnicianId = (techId) => {
    if (!techId) return null
    // Si c'est un ID alternatif de JP, convertir vers l'ID standard
    if (techId === 'usr_QmEpdeM2xMgZVkDS') {
      return 'usr_ReUSmIJmBF86ilY1'  // ID standard de JP
    }
    return techId
  }

  // ID du technicien "À attribuer" dans Gazelle
  const A_ATTRIBUER_ID = 'usr_HihJsEgkmpTEziJo'
  
  const technicianOptions = useMemo(() => {
    return [
      { id: 'usr_HcCiFk7o0vZ9xAI0', label: 'Nick' },
      { id: 'usr_ofYggsCDt2JAVeNP', label: 'Allan' },
      { id: 'usr_ReUSmIJmBF86ilY1', label: 'JP' }
    ]
  }, [])
  
  // Fonction pour vérifier si un technicien est "À attribuer"
  const isAAttribuer = (techId) => {
    return techId === A_ATTRIBUER_ID
  }

  const statusBadge = (status) => {
    const meta = statusMeta[status] || { label: status || 'N/A', cls: 'bg-gray-100 text-gray-800' }
    return <span className={`px-2 py-1 rounded text-xs font-medium ${meta.cls}`}>{meta.label}</span>
  }

  return (
    <div className={`${isFullscreen ? 'fixed inset-0 z-50 bg-white overflow-auto' : 'min-h-screen bg-gray-50'}`}>
      {/* Navigation Tabs - Structure identique à VDI */}
      <nav className="bg-white border-b border-gray-200 shadow-sm sticky top-[60px] z-40">
        <div className="max-w-7xl mx-auto px-6">
          <div className="flex space-x-1">
            <button
              onClick={() => setCurrentView('inventaire-pianos')}
              className={`
                px-6 py-3 text-sm font-medium transition-colors
                border-b-2
                ${
                  currentView === 'inventaire-pianos'
                    ? 'border-blue-600 text-blue-600 bg-blue-50'
                    : 'border-transparent text-gray-600 hover:text-gray-900 hover:border-gray-300'
                }
              `}
            >
              📦 Inventaire Pianos
            </button>
            <button
              onClick={() => setCurrentView('demandes')}
              className={`
                px-6 py-3 text-sm font-medium transition-colors
                border-b-2
                ${
                  currentView === 'demandes'
                    ? 'border-blue-600 text-blue-600 bg-blue-50'
                    : 'border-transparent text-gray-600 hover:text-gray-900 hover:border-gray-300'
                }
              `}
            >
              📋 Demandes
            </button>
          </div>
        </div>
      </nav>

      {/* Main Content - Structure identique à VDI */}
      <main className="max-w-7xl mx-auto px-6 py-8">

        {/* Contenu selon l'onglet */}
        {currentView === 'inventaire-pianos' && (
          <PDAInventoryTable />
        )}

        {currentView === 'demandes' && (
          <div className="space-y-4">
            {/* Stats pour Demandes */}
            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <h2 className="text-xl font-bold text-gray-900">Demandes Place des Arts</h2>
                  <p className="text-sm text-gray-500 mt-1">
                    Demandes importées (limite 200, tri date RDV desc)
                  </p>
                  {/* Description des couleurs pour Louise et Nick */}
                  <div className="mt-3 p-3 bg-gray-50 border border-gray-200 rounded-md text-xs">
                    <p className="font-semibold text-gray-700 mb-2">📋 Légende des couleurs (Louise & Nick) :</p>
                    <div className="flex flex-wrap gap-4">
                      <div className="flex items-center gap-2">
                        <div className="w-4 h-4 bg-red-50 border border-red-200 rounded"></div>
                        <span className="text-gray-600"><strong>Rouge</strong> : Nouveau ou RV créé avec "À attribuer" (action requise)</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <div className="w-4 h-4 bg-white border border-gray-200 rounded"></div>
                        <span className="text-gray-600"><strong>Blanc</strong> : RV assigné à un technicien actif (Nick, Allan, JP) - Tout OK</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <div className="w-4 h-4 bg-green-50 border border-green-200 rounded"></div>
                        <span className="text-gray-600"><strong>Vert</strong> : RV complété</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <div className="w-4 h-4 bg-blue-50 border border-blue-200 rounded"></div>
                        <span className="text-gray-600"><strong>Bleu</strong> : Ligne sélectionnée</span>
                      </div>
                    </div>
                    <p className="text-gray-500 mt-2 text-xs italic">
                      Flux : Rouge (nouveau) → Rouge (créé Gazelle "À attribuer") → Blanc (technicien assigné) → Vert (complété)
                    </p>
                  </div>
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
            </div>

      {creating && (
        <div className="bg-white border border-gray-200 rounded-lg p-4 space-y-3">
          <h3 className="text-sm font-semibold text-gray-700">Ajouter une demande</h3>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-3 text-sm">
            <div>
              <label className="text-xs text-gray-600">Date RDV</label>
              <input type="date" value={createForm.appointment_date} onChange={(e) => setCreateForm({ ...createForm, appointment_date: e.target.value })} className="w-full border border-gray-300 rounded px-2 py-1" />
            </div>
            <div>
              <label className="text-xs text-gray-600">Salle</label>
              <input list="pda-rooms-create" type="text" value={createForm.room} onChange={(e) => setCreateForm({ ...createForm, room: e.target.value })} className="w-full border border-gray-300 rounded px-2 py-1" placeholder="Ex: MS, WP, E..." />
              <datalist id="pda-rooms-create">
                <option value="WP">Wilfrid-Pelletier</option>
                <option value="TM">Théâtre Maisonneuve</option>
                <option value="MS">Maison Symphonique</option>
                <option value="SD">Salle D</option>
                <option value="E">Salle E</option>
                <option value="5E">Cinquième Salle</option>
                <option value="SCL">Studio Claude-Léveillée</option>
                <option value="TJD">Théâtre Jean-Duceppe</option>
              </datalist>
            </div>
            <div>
              <label className="text-xs text-gray-600">Pour qui</label>
              <input type="text" value={createForm.for_who} onChange={(e) => setCreateForm({ ...createForm, for_who: e.target.value })} className="w-full border border-gray-300 rounded px-2 py-1" />
            </div>
            <div className="md:col-span-2">
              <label className="text-xs text-gray-600">Piano</label>
              <input type="text" value={createForm.piano} onChange={(e) => setCreateForm({ ...createForm, piano: e.target.value })} className="w-full border border-gray-300 rounded px-2 py-1" />
            </div>
            <div>
              <label className="text-xs text-gray-600">Heure</label>
              <input type="text" value={createForm.time} onChange={(e) => setCreateForm({ ...createForm, time: e.target.value })} className="w-full border border-gray-300 rounded px-2 py-1" />
            </div>
            <div>
              <label className="text-xs text-gray-600">Diapason</label>
              <input type="text" value={createForm.diapason} onChange={(e) => setCreateForm({ ...createForm, diapason: e.target.value })} className="w-full border border-gray-300 rounded px-2 py-1" />
            </div>
            <div>
              <label className="text-xs text-gray-600">Demandeur</label>
              <input type="text" value={createForm.requester} onChange={(e) => setCreateForm({ ...createForm, requester: e.target.value })} className="w-full border border-gray-300 rounded px-2 py-1" />
            </div>
            <div>
              <label className="text-xs text-gray-600">Technicien</label>
              <select value={createForm.technician_id} onChange={(e) => setCreateForm({ ...createForm, technician_id: e.target.value })} className="w-full border border-gray-300 rounded px-2 py-1">
                <option value="">—</option>
                <option value="usr_U9E5bLxrFiXqTbE8">Nick</option>
                <option value="usr_allan">Allan</option>
                <option value="usr_jp">JP</option>
              </select>
            </div>
            <div>
              <label className="text-xs text-gray-600">Facturation</label>
              <input type="number" step="0.01" value={createForm.billing_amount} onChange={(e) => setCreateForm({ ...createForm, billing_amount: e.target.value })} className="w-full border border-gray-300 rounded px-2 py-1" />
            </div>
            <div>
              <label className="text-xs text-gray-600">Stationnement</label>
              <input type="text" value={createForm.parking} onChange={(e) => setCreateForm({ ...createForm, parking: e.target.value })} className="w-full border border-gray-300 rounded px-2 py-1" />
            </div>
            <div className="md:col-span-3">
              <label className="text-xs text-gray-600">Notes</label>
              <input type="text" value={createForm.notes} onChange={(e) => setCreateForm({ ...createForm, notes: e.target.value })} className="w-full border border-gray-300 rounded px-2 py-1" />
            </div>
          </div>
          <div className="flex gap-2">
            <button
              onClick={async () => {
                try {
                  setError(null)
                  setInfoMessage(null)
                  const resp = await fetch(`${API_URL}/api/place-des-arts/requests/create`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(createForm)
                  })
                  if (!resp.ok) {
                    const msg = await resp.text()
                    throw new Error(msg || `HTTP ${resp.status}`)
                  }
                  setInfoMessage('Demande ajoutée')
                  setCreating(false)
                  setCreateForm({
                    appointment_date: '',
                    room: '',
                    for_who: '',
                    piano: '',
                    time: '',
                    diapason: '',
                    requester: '',
                    technician_id: '',
                    notes: '',
                    billing_amount: '',
                    parking: ''
                  })
                  await fetchData()
                } catch (err) {
                  setError(err.message)
                }
              }}
              className="px-3 py-2 text-sm bg-blue-600 text-white rounded-md hover:bg-blue-700"
            >
              Enregistrer
            </button>
            <button onClick={() => setCreating(false)} className="px-3 py-2 text-sm bg-white border border-gray-300 rounded-md hover:bg-gray-50">
              Annuler
            </button>
          </div>
        </div>
      )}

      <div className="bg-white border border-gray-200 rounded-lg p-4 space-y-3">
        <h3 className="text-sm font-semibold text-gray-700">Import depuis email (copier-coller)</h3>
        <textarea
          value={rawText}
          onChange={(e) => setRawText(e.target.value)}
          placeholder="Collez le texte de l'email ici..."
          className="w-full min-h-[140px] border border-gray-300 rounded-md p-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
        <div className="flex gap-2 items-center">
          <button
            onClick={(e) => {
              e.preventDefault()
              e.stopPropagation()
              console.log('🖱️ Bouton Prévisualiser cliqué', { 
                rawTextLength: rawText?.length, 
                rawTextTrimmed: rawText?.trim().length,
                previewLoading,
                API_URL,
                isDisabled: !rawText.trim() || previewLoading
              })
              if (!rawText.trim()) {
                setError('Veuillez entrer du texte à prévisualiser')
                return
              }
              if (previewLoading) {
                console.log('⚠️ Preview déjà en cours, ignoré')
                return
              }
              handlePreview()
            }}
            disabled={!rawText.trim() || previewLoading}
            className="px-3 py-2 text-sm bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed disabled:bg-gray-400"
            type="button"
          >
            {previewLoading ? '⏳ Prévisualisation...' : '👁️ Prévisualiser'}
          </button>
          {!rawText.trim() && (
            <span className="text-xs text-gray-500">(Entrez du texte pour activer)</span>
          )}
          <button
            onClick={() => { setRawText(''); setPreview([]); setInfoMessage(null); setError(null) }}
            className="px-3 py-2 text-sm bg-white border border-gray-200 rounded-md hover:bg-gray-50"
          >
            Effacer
          </button>
        </div>

        {error && (
          <div className="text-sm text-red-700 bg-red-50 border border-red-200 px-3 py-2 rounded">
            ❌ Erreur: {error}
          </div>
        )}

        {infoMessage && (
          <div className="text-sm text-green-700 bg-green-50 border border-green-200 px-3 py-2 rounded">
            {infoMessage}
          </div>
        )}

        {orphanServices.length > 0 && (
          <div className="bg-amber-50 border border-amber-300 rounded-md px-4 py-3 mt-2">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium text-amber-800">
                ⚠️ {orphanServices.length} service(s) PDA dans Gazelle sans demande
              </span>
              <button
                onClick={() => setOrphanServices([])}
                className="text-amber-600 hover:text-amber-800 text-xs"
              >
                ✕ Fermer
              </button>
            </div>
            <div className="space-y-1">
              {orphanServices.map((o) => (
                <div key={o.appointment_id}>
                  <div className="flex items-center justify-between bg-white rounded px-3 py-2 text-sm border border-amber-200">
                    <span className="text-gray-800">
                      {o.date} — {o.title}{o.technician_id ? ` (${o.technician_id})` : ''}
                    </span>
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => handleDismissOrphan(o)}
                        className="text-xs px-2 py-1 bg-gray-200 text-gray-700 rounded hover:bg-gray-300"
                      >
                        Ignorer
                      </button>
                      <button
                        onClick={() => handleAddOrphan(o)}
                        disabled={addingOrphan === o.appointment_id}
                        className="text-xs px-2 py-1 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
                      >
                        {addingOrphan === o.appointment_id ? '...' : '+ Ajouter'}
                      </button>
                    </div>
                  </div>
                  {/* Formulaire de prévisualisation inline */}
                  {orphanPreview && orphanPreview.appointment_id === o.appointment_id && (
                    <div className="bg-blue-50 border border-blue-300 rounded-b px-4 py-3 -mt-0.5 space-y-3">
                      <div className="text-xs font-medium text-blue-800 mb-2">Prévisualisation — ajustez les champs avant de confirmer</div>
                      <div className="grid grid-cols-2 gap-3">
                        <div>
                          <label className="block text-xs font-medium text-gray-600 mb-1">Date du RV</label>
                          <input type="date" value={orphanPreview.appointment_date}
                            onChange={(e) => setOrphanPreview(p => ({ ...p, appointment_date: e.target.value }))}
                            className="w-full text-sm border border-gray-300 rounded px-2 py-1" />
                        </div>
                        <div>
                          <label className="block text-xs font-medium text-gray-600 mb-1">Heure</label>
                          <input type="text" value={orphanPreview.time} placeholder="ex: 09:00"
                            onChange={(e) => setOrphanPreview(p => ({ ...p, time: e.target.value }))}
                            className="w-full text-sm border border-gray-300 rounded px-2 py-1" />
                        </div>
                        <div>
                          <label className="block text-xs font-medium text-gray-600 mb-1">Pour qui</label>
                          <input type="text" value={orphanPreview.for_who}
                            onChange={(e) => setOrphanPreview(p => ({ ...p, for_who: e.target.value }))}
                            className="w-full text-sm border border-gray-300 rounded px-2 py-1" />
                        </div>
                        <div>
                          <label className="block text-xs font-medium text-gray-600 mb-1">Salle</label>
                          <input type="text" value={orphanPreview.room} placeholder="ex: Salle Wilfrid-Pelletier"
                            onChange={(e) => setOrphanPreview(p => ({ ...p, room: e.target.value }))}
                            className="w-full text-sm border border-gray-300 rounded px-2 py-1" />
                        </div>
                      </div>
                      <div>
                        <label className="block text-xs font-medium text-gray-600 mb-1">Notes</label>
                        <input type="text" value={orphanPreview.notes}
                          onChange={(e) => setOrphanPreview(p => ({ ...p, notes: e.target.value }))}
                          className="w-full text-sm border border-gray-300 rounded px-2 py-1" />
                      </div>
                      <div className="flex gap-2 pt-1">
                        <button
                          onClick={handleConfirmOrphan}
                          disabled={addingOrphan === orphanPreview.appointment_id}
                          className="text-xs px-3 py-1.5 bg-green-600 text-white rounded hover:bg-green-700 disabled:opacity-50"
                        >
                          {addingOrphan === orphanPreview.appointment_id ? 'Enregistrement...' : 'Confirmer'}
                        </button>
                        <button
                          onClick={() => setOrphanPreview(null)}
                          className="text-xs px-3 py-1.5 bg-gray-200 text-gray-700 rounded hover:bg-gray-300"
                        >
                          Annuler
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {previewLoading && (
          <div className="text-sm text-blue-700 bg-blue-50 border border-blue-200 px-3 py-2 rounded mt-3">
            ⏳ Prévisualisation en cours...
          </div>
        )}

        {preview.length > 0 && (
          <div className="border border-gray-200 rounded-md mt-3">
            <div className="bg-gray-50 px-3 py-2 text-sm font-medium text-gray-700 flex items-center justify-between">
              <span>
                {preview.some(p => p.confidence === 0.0) 
                  ? '📝 Prévisualisation (complétez manuellement)' 
                  : `✅ Prévisualisation (${preview.length} demande${preview.length > 1 ? 's' : ''})`}
              </span>
              <span className="text-xs text-gray-500">
                {preview.filter(p => p.confidence < 1.0 || p.needs_validation).length > 0 && (
                  `${preview.filter(p => p.confidence < 1.0 || p.needs_validation).length} item(s) nécessitent une vérification`
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
            <div className="bg-gray-50 px-3 py-3 border-t border-gray-200 flex justify-between items-center">
              <div className="text-xs text-gray-600">
                💡 <strong>Astuce:</strong> Complétez les champs manquants, puis cliquez sur "Valider et apprendre" pour améliorer le système, puis "Importer" pour enregistrer.
              </div>
              <button
                onClick={handleImport}
                disabled={importLoading}
                className="px-4 py-2 text-sm bg-blue-600 text-white hover:bg-blue-700 rounded-md disabled:opacity-50 font-medium"
              >
                {importLoading ? 'Import en cours...' : `💾 Importer ${preview.length} demande${preview.length > 1 ? 's' : ''}`}
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Toolbar actions */}
      <div className="bg-white border border-gray-200 rounded-lg p-4 flex flex-wrap items-center gap-2">
        {isAdmin && (
          <>
            <button
              onClick={handleDeleteDuplicates}
              className="px-3 py-2 text-sm bg-white border border-gray-300 rounded-md hover:bg-gray-50"
              title="Admin uniquement"
            >
              🗑️ Nettoyer doublons
            </button>
            <button
              onClick={handleExport}
              className="px-3 py-2 text-sm bg-white border border-gray-300 rounded-md hover:bg-gray-50"
              title="Admin uniquement"
            >
              📊 Export CSV
            </button>
          </>
        )}
        <button
          onClick={() => setEditMode((v) => !v)}
          className={`px-3 py-2 text-sm border rounded-md ${editMode ? 'bg-blue-600 text-white border-blue-600' : 'bg-white border-gray-300 hover:bg-gray-50'}`}
        >
          {editMode ? 'Mode édition activé' : 'Mode édition'}
        </button>
        <button
          onClick={() => setCreating((v) => !v)}
          className={`px-3 py-2 text-sm rounded-md ${
            creating
              ? 'bg-blue-600 text-white hover:bg-blue-700'
              : 'bg-white border border-gray-300 hover:bg-gray-50'
          }`}
        >
          {creating ? 'Fermer ajout' : '➕ Ajouter manuellement'}
        </button>
        {!isRestrictedUser && (
          <button
            onClick={handleSyncGazelle}
            className="px-4 py-2 text-sm bg-blue-600 text-white border border-blue-700 rounded-md hover:bg-blue-700 font-medium"
            title="Synchronise toutes les demandes avec Gazelle : lie les RV, met à jour les statuts et vérifie les complétés"
          >
            🔄 Synchroniser tout avec Gazelle
          </button>
        )}

        {/* Filtres - Sélecteur de mois accessible à tous */}
        <div className="flex items-center gap-2 ml-auto flex-wrap">
          <select
            value={monthFilter}
            onChange={(e) => setMonthFilter(e.target.value)}
            className="border border-gray-300 rounded-md px-2 py-1 text-sm"
          >
            <option value="">Toutes les dates</option>
            {availableMonths.map(month => {
              // Parser YYYY-MM pour éviter les problèmes de timezone
              const [year, monthNum] = month.split('-')
              const date = new Date(parseInt(year), parseInt(monthNum) - 1, 1)
              const monthName = date.toLocaleDateString('fr-FR', { year: 'numeric', month: 'long' })
              return (
                <option key={month} value={month}>
                  {monthName.charAt(0).toUpperCase() + monthName.slice(1)}
                </option>
              )
            })}
          </select>

          {monthlyTotal && (
            <div className="flex items-center gap-4 bg-blue-50 border border-blue-200 rounded-md px-3 py-1 text-sm">
              <div className="flex flex-col">
                <span className="text-xs text-gray-500">Facturation</span>
                <span className="font-semibold text-blue-700">{monthlyTotal.billing.toFixed(2)} $</span>
              </div>
              <div className="flex flex-col">
                <span className="text-xs text-gray-500">Stationnement</span>
                <span className="font-semibold text-blue-700">{monthlyTotal.parking.toFixed(2)} $</span>
              </div>
              <div className="flex flex-col border-l border-blue-300 pl-4">
                <span className="text-xs text-gray-500">Total</span>
                <span className="font-bold text-blue-900">{monthlyTotal.total.toFixed(2)} $</span>
              </div>
              <span className="text-xs text-gray-500">({monthlyTotal.count} élément{monthlyTotal.count > 1 ? 's' : ''})</span>
            </div>
          )}

          {/* Filtres avancés - Admin uniquement */}
          {!isRestrictedUser && (
            <>
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="border border-gray-300 rounded-md px-2 py-1 text-sm"
              >
                <option value="">Tous statuts</option>
                <option value="PENDING">Nouveau</option>
                <option value="ASSIGN_OK">Assigné</option>
                <option value="CREATED_IN_GAZELLE">Créé Gazelle</option>
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
            </>
          )}
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
            <option value="ASSIGN_OK">Assigné</option>
            <option value="CREATED_IN_GAZELLE">Créé Gazelle</option>
            <option value="COMPLETED">Complété</option>
            <option value="BILLED">Facturé</option>
          </select>
          <button onClick={() => handleStatusChange('PENDING')} className="px-2 py-1 text-xs bg-white border border-gray-300 rounded hover:bg-gray-50">Statut: Nouveau</button>
          <button onClick={() => handleStatusChange('ASSIGN_OK')} className="px-2 py-1 text-xs bg-white border border-gray-300 rounded hover:bg-gray-50">Statut: Assigné</button>
          <button onClick={() => handleStatusChange('CREATED_IN_GAZELLE')} className="px-2 py-1 text-xs bg-white border border-gray-300 rounded hover:bg-gray-50">Statut: Créé Gazelle</button>
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
                // Déterminer si l'événement est complété (statut COMPLETED)
                const isCompleted = it.status === 'COMPLETED'
                
                // FLUX DES COULEURS pour Louise et Nicolas (vue d'ensemble d'un coup d'œil) :
                // 1. 🔴 ROUGE : Nouveau (pas de RV) OU RV créé avec "À attribuer" → Action requise
                // 2. ⚪ BLANC : RV assigné à un technicien actif (Nick, Allan, JP) → Tout OK, en attente
                // 3. 🟢 VERT : RV complété → Terminé
                
                // Normaliser l'ID technicien (convertir les IDs alternatifs)
                const normalizedTechId = normalizeTechnicianId(it.technician_id)
                
                // Vérifier si un technicien actif est assigné (avec ID normalisé)
                const hasActiveTechnician = normalizedTechId && REAL_TECHNICIAN_IDS.has(normalizedTechId)
                const isAAttribuerTech = isAAttribuer(it.technician_id)
                
                // 🔴 ROUGE : Besoin d'attention (Louise voit d'un coup d'œil)
                // - Pas de appointment_id (nouveau, pas encore de RV dans Gazelle)
                // OU
                // - appointment_id existe mais technicien est "À attribuer" (Nicolas doit assigner un vrai technicien)
                // OU
                // - appointment_id existe mais pas de technicien actif assigné
                // ⚪ BLANC (pas de couleur) : RV créé + technicien actif assigné (Nick, Allan, JP) → Tout OK
                const needsAttention = !isCompleted && (
                  !it.appointment_id ||  // Étape 1: Nouveau (pas de RV)
                  (it.appointment_id && isAAttribuerTech) ||  // Étape 2: RV créé mais "À attribuer"
                  (it.appointment_id && !hasActiveTechnician)  // RV créé mais pas de technicien actif
                )
                
                const rowClass = selectedIds.includes(it.id)
                  ? 'bg-blue-50'
                  : isCompleted
                    ? 'bg-green-50'
                    : needsAttention
                      ? 'bg-red-50'
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
                        value={it.room || ''}
                        onChange={(e) => handleCellUpdate(it.id, 'room', e.target.value)}
                        className="w-full border border-gray-200 rounded px-2 py-1 text-xs"
                      />
                    ) : (it.room || '—')}
                  </td>
                  <td className="px-3 py-2 text-gray-800 relative">
                    {editMode ? (
                      <input
                        type="text"
                        defaultValue={it.for_who || ''}
                        onBlur={(e) => handleCellUpdate(it.id, 'for_who', e.target.value)}
                        className="w-full border border-gray-200 rounded px-2 py-1 text-xs"
                      />
                    ) : (
                      <div className="flex items-center gap-1">
                        <span>{it.for_who || '—'}</span>
                        {it.for_who && (
                          <button
                            onClick={() => (concertSearch[it.id]?.data || concertSearch[it.id]?.error) ? closeConcertSearch(it.id) : handleConcertSearch(it)}
                            className="text-blue-500 hover:text-blue-700 text-xs flex-shrink-0"
                            title="Rechercher le programme du concert"
                          >
                            {concertSearch[it.id]?.loading ? '...' : (concertSearch[it.id]?.data || concertSearch[it.id]?.error) ? '✕' : '🔍'}
                          </button>
                        )}
                        {concertSearch[it.id]?.data && (
                          <div className="absolute z-50 mt-8 bg-white border border-gray-300 rounded shadow-lg p-3 text-xs w-80">
                            <div className="font-semibold mb-1">
                              Programme — {concertSearch[it.id].data.query}
                            </div>
                            {concertSearch[it.id].data.found ? (
                              <ul className="space-y-1">
                                {concertSearch[it.id].data.results.map((r, idx) => (
                                  <li key={idx}>
                                    <a href={r.url} target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline">
                                      {r.titre}
                                    </a>
                                    {r.date_spectacle && <span className="text-gray-500 ml-1">({r.date_spectacle})</span>}
                                  </li>
                                ))}
                              </ul>
                            ) : (
                              <p className="text-gray-500">{concertSearch[it.id].data.message}</p>
                            )}
                            {concertSearch[it.id].data.search_url && (
                              <a
                                href={concertSearch[it.id].data.search_url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="block mt-2 text-blue-500 hover:underline"
                              >
                                Rechercher sur placedesarts.com
                              </a>
                            )}
                          </div>
                        )}
                        {concertSearch[it.id]?.error && !concertSearch[it.id]?.data && (
                          <span className="text-red-500 text-xs ml-1" title={concertSearch[it.id].error}>Erreur</span>
                        )}
                      </div>
                    )}
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
                    ) : (it.piano || '—')}
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
                    <div className="flex items-center gap-1">
                      <select
                        value={it.technician_id || ''}
                        onChange={(e) => handleCellUpdate(it.id, 'technician_id', e.target.value)}
                        className={`w-full border border-gray-200 rounded px-1 py-1 text-xs font-medium hover:bg-gray-50 cursor-pointer ${
                          isAAttribuer(it.technician_id) 
                            ? 'bg-yellow-50 border-yellow-300 text-yellow-700'  // Jaune pour attirer l'attention qu'il faut assigner un technicien
                            : it.technician_mismatch
                              ? 'bg-yellow-50 border-yellow-300 text-yellow-700'  // Jaune pour incohérence
                              : 'bg-white'
                        }`}
                        title={
                          it.technician_mismatch 
                            ? `⚠️ Incohérence: PDA=${techMap[it.technician_id] || it.technician_id}, Gazelle=${techMap[it.gazelle_technician_id] || it.gazelle_technician_id || 'À attribuer'}`
                            : techMap[it.technician_id] || 'Choisir technicien'
                        }
                        style={{ width: '90px' }}
                      >
                        <option value="">—</option>
                        {/* Afficher "À attribuer" seulement si c'est créé dans Gazelle (appointment_id existe) avec ce technicien */}
                        {it.appointment_id && (it.technician_id === A_ATTRIBUER_ID || (it.technician_from_gazelle && it.technician_id === A_ATTRIBUER_ID) || it.gazelle_technician_id === A_ATTRIBUER_ID) && (
                          <option value={A_ATTRIBUER_ID} className="text-yellow-700 font-medium">
                            ⚠️ À attribuer
                          </option>
                        )}
                        {technicianOptions.map(tech => (
                          <option key={tech.id} value={tech.id}>{tech.label}</option>
                        ))}
                      </select>
                      {/* Afficher un indicateur si c'est "À attribuer" */}
                      {isAAttribuer(it.technician_id) && it.appointment_id && (
                        <span className="text-xs text-yellow-600" title="RV créé dans Gazelle mais technicien à attribuer - Assignez un technicien dans Gazelle">
                          ⚠️
                        </span>
                      )}
                      {/* Afficher un avertissement si incohérence entre PDA et Gazelle */}
                      {it.technician_mismatch && it.gazelle_technician_id && (
                        <span 
                          className="text-xs text-yellow-600 cursor-help" 
                          title={`⚠️ Incohérence: Dans Gazelle, le technicien est "${techMap[it.gazelle_technician_id] || it.gazelle_technician_id || 'À attribuer'}" mais PDA a "${techMap[it.technician_id] || it.technician_id}". Cliquez pour synchroniser avec Gazelle.`}
                          onClick={async () => {
                            if (confirm(`Synchroniser avec Gazelle ? Le technicien sera changé pour "${techMap[it.gazelle_technician_id] || it.gazelle_technician_id || 'À attribuer'}"`)) {
                              await handleCellUpdate(it.id, 'technician_id', it.gazelle_technician_id)
                            }
                          }}
                        >
                          🔄
                        </span>
                      )}
                    </div>
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
                      onChange={(e) => {
                        const targetIds = selectedIds.includes(it.id) && selectedIds.length > 1 ? selectedIds : [it.id]
                        handleStatusChange(e.target.value, targetIds)
                      }}
                      className="text-xs border border-gray-300 rounded px-2 py-1 bg-white"
                    >
                      <option value="PENDING">Nouveau</option>
                      <option value="ASSIGN_OK">Assigné</option>
                      <option value="CREATED_IN_GAZELLE">Créé Gazelle</option>
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
        )}
      </main>
    </div>
  )
}
