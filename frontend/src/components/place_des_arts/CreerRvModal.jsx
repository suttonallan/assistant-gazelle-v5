import { useEffect, useState } from 'react'
import { API_URL } from '../../utils/apiConfig'

// Fenêtre « Créer le RV dans Gazelle » pour une demande Place des Arts.
// On voit la journée de TOUS les techniciens ce jour-là (lue en direct dans Gazelle), on choisit qui le fait
// (clic sur sa colonne ou menu), on inscrit l'heure confirmée → un clic crée le RV.
const TECHS = [
  { id: 'usr_HcCiFk7o0vZ9xAI0', label: 'Nick' },
  { id: 'usr_ReUSmIJmBF86ilY1', label: 'JP' },
  { id: 'usr_bbt59aCUqUaDWA8n', label: 'Margot' },
  { id: 'usr_ofYggsCDt2JAVeNP', label: 'Allan' },
  { id: 'usr_HihJsEgkmpTEziJo', label: 'À attribuer' },
]

// Pré-remplit l'heure seulement si la demande donne une heure précise (« 18h », « à 13h30 »).
// « Avant 10h » reste vide : c'est à nous de fixer l'heure confirmée.
function heureProposee(texte) {
  const t = (texte || '').toLowerCase().trim()
  if (!t || t.startsWith('avant') || t.startsWith('before')) return ''
  const m = t.match(/(\d{1,2})\s*(?:h|:)\s*(\d{2})?/) || t.match(/(\d{1,2})\s*(am|pm)/)
  if (!m) return ''
  let h = parseInt(m[1], 10)
  if (m[2] === 'pm' && h < 12) h += 12
  const min = m[2] && /^\d{2}$/.test(m[2]) ? m[2] : '00'
  if (h > 23) return ''
  return `${String(h).padStart(2, '0')}:${min}`
}

const enMin = (hhmm) => { const [h, m] = (hhmm || '0:0').split(':').map(Number); return h * 60 + (m || 0) }

// Conflit si le nouveau RV [heure, heure+durée] chevauche un RV existant (journée entière = conflit).
function conflits(rvs, heure, duree) {
  if (!/^\d{2}:\d{2}$/.test(heure)) return []
  const a = enMin(heure), b = a + Number(duree || 60)
  return (rvs || []).filter((r) => r.journee || (enMin(r.heure) < b && a < enMin(r.heure) + Number(r.duree || 60)))
}

function JourneeTechniciens({ journee, tech, setTech, heure, duree }) {
  if (journee === 'chargement') return <div className="mt-3 text-xs text-gray-500">Chargement de la journée des techniciens…</div>
  if (!journee) return null
  if (journee.erreur) return <div className="mt-3 rounded bg-amber-50 p-2 text-xs text-amber-800">Journée des techniciens indisponible : {journee.erreur}</div>
  return (
    <div className="mt-3">
      <div className="mb-1 text-xs font-medium text-gray-700">Journée des techniciens — {journee.date} <span className="font-normal text-gray-500">(clic = choisir)</span></div>
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-5">
        {journee.techniciens.map((t) => {
          const choisi = t.id === tech
          const c = conflits(t.rendez_vous, heure, duree)
          return (
            <button type="button" key={t.id} onClick={() => setTech(t.id)}
              className={`rounded border p-1.5 text-left text-[11px] leading-tight ${choisi ? 'border-blue-500 bg-blue-50' : 'border-gray-200 bg-white hover:bg-gray-50'}`}>
              <div className="mb-1 flex items-center justify-between font-semibold text-gray-800">
                <span>{t.nom}</span>
                {heure && <span className={c.length ? 'text-red-600' : 'text-green-600'}>{c.length ? '⚠︎' : '✓'}</span>}
              </div>
              {t.rendez_vous.length === 0 && <div className="text-gray-400">Libre</div>}
              {t.rendez_vous.map((r) => (
                <div key={r.id} className={`mb-0.5 break-words ${c.includes(r) ? 'text-red-600' : r.perso ? 'text-gray-500 italic' : 'text-gray-700'}`} title={r.titre}>
                  {r.journee ? 'Journée' : `${r.heure}–${r.fin}`} {r.titre}
                </div>
              ))}
            </button>
          )
        })}
      </div>
    </div>
  )
}

export default function CreerRvModal({ demande, onClose, onCreated, par }) {
  const techInitial = TECHS.some((t) => t.id === demande.technician_id) ? demande.technician_id : ''
  const [tech, setTech] = useState(techInitial)
  const [date, setDate] = useState((demande.appointment_date || '').slice(0, 10))
  const [heure, setHeure] = useState(heureProposee(demande.time))
  const [duree, setDuree] = useState(60)
  const [pianos, setPianos] = useState([])
  const [pianoId, setPianoId] = useState('')
  const [envoi, setEnvoi] = useState(false)
  const [erreur, setErreur] = useState(null)
  const [journee, setJournee] = useState(null)

  // Pianos PdA + piano suggéré pour cette demande
  useEffect(() => {
    fetch(`${API_URL}/api/place-des-arts/pianos`).then((r) => r.ok ? r.json() : null)
      .then((d) => setPianos((d && d.pianos) || [])).catch(() => {})
    fetch(`${API_URL}/api/place-des-arts/requests/${demande.id}/gazelle-piano-id`).then((r) => r.ok ? r.json() : null)
      .then((d) => { if (d && d.piano_id) setPianoId(d.piano_id) }).catch(() => {})
  }, [demande.id])

  // Journée de tous les techniciens à la date choisie (Gazelle en direct)
  useEffect(() => {
    if (!/^\d{4}-\d{2}-\d{2}$/.test(date)) { setJournee(null); return }
    let annule = false
    setJournee('chargement')
    fetch(`${API_URL}/api/place-des-arts/journee-techniciens?date=${date}`)
      .then(async (r) => { const d = await r.json().catch(() => ({})); if (!r.ok) throw new Error(d.detail || `Erreur ${r.status}`); return d })
      .then((d) => { if (!annule) setJournee(d) })
      .catch((e) => { if (!annule) setJournee({ erreur: e.message }) })
    return () => { annule = true }
  }, [date])

  const nomTech = (TECHS.find((t) => t.id === tech) || {}).label
  const pret = tech && date && /^\d{2}:\d{2}$/.test(heure) && duree > 0 && !envoi

  const creer = async () => {
    setEnvoi(true); setErreur(null)
    try {
      const resp = await fetch(`${API_URL}/api/place-des-arts/requests/${demande.id}/creer-rv-gazelle`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ technician_id: tech, date, heure, duree_min: Number(duree), piano_id: pianoId || null, par: par || null }),
      })
      const d = await resp.json().catch(() => ({}))
      if (!resp.ok) throw new Error(d.detail || `Erreur ${resp.status}`)
      onCreated(d, nomTech)
    } catch (e) {
      setErreur(e.message)
      setEnvoi(false)
    }
  }

  const libellePiano = (p) => `${p.local?.trim() || '?'} — ${p.piano || ''} ${p.modele || ''}`.trim()

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" onClick={onClose}>
      <div className="w-full max-h-[92vh] max-w-2xl overflow-y-auto rounded-lg bg-white p-5 shadow-xl" onClick={(e) => e.stopPropagation()}>
        <h3 className="text-base font-semibold text-gray-900">Créer le RV dans Gazelle</h3>
        <div className="mt-2 rounded bg-gray-50 p-2 text-xs text-gray-700">
          <div><b>{demande.for_who || '—'}</b> · {demande.room || '—'}</div>
          <div>Demandé : {(demande.appointment_date || '').slice(0, 10)} — <b>{demande.time || 'heure non précisée'}</b></div>
          <div>Piano demandé : {demande.piano || '—'}{demande.diapason ? ` · ${demande.diapason}` : ''}</div>
        </div>

        <JourneeTechniciens journee={journee} tech={tech} setTech={setTech} heure={heure} duree={duree} />

        <div className="mt-3 grid grid-cols-2 gap-3 text-sm">
          <label className="col-span-2">
            <span className="text-xs text-gray-600">Technicien</span>
            <select value={tech} onChange={(e) => setTech(e.target.value)} className="mt-1 w-full rounded border border-gray-300 px-2 py-1">
              <option value="">— choisir —</option>
              {TECHS.map((t) => <option key={t.id} value={t.id}>{t.label}</option>)}
            </select>
          </label>
          <label>
            <span className="text-xs text-gray-600">Date</span>
            <input type="date" value={date} onChange={(e) => setDate(e.target.value)} className="mt-1 w-full rounded border border-gray-300 px-2 py-1" />
          </label>
          <label>
            <span className="text-xs text-gray-600">Heure confirmée</span>
            <input type="time" value={heure} onChange={(e) => setHeure(e.target.value)} className="mt-1 w-full rounded border border-gray-300 px-2 py-1" />
          </label>
          <label>
            <span className="text-xs text-gray-600">Durée (min)</span>
            <input type="number" min="15" step="15" value={duree} onChange={(e) => setDuree(e.target.value)} className="mt-1 w-full rounded border border-gray-300 px-2 py-1" />
          </label>
          <label className="col-span-2">
            <span className="text-xs text-gray-600">Piano dans Gazelle</span>
            <select value={pianoId} onChange={(e) => setPianoId(e.target.value)} className="mt-1 w-full rounded border border-gray-300 px-2 py-1">
              <option value="">— aucun piano lié —</option>
              {pianos.map((p) => <option key={p.gazelleId || p.id} value={p.gazelleId || p.id}>{libellePiano(p)}</option>)}
            </select>
          </label>
        </div>

        {erreur && <div className="mt-3 rounded bg-red-50 p-2 text-xs text-red-700">{erreur}</div>}

        <div className="mt-4 flex justify-end gap-2">
          <button onClick={onClose} className="rounded border border-gray-300 bg-white px-3 py-1.5 text-sm hover:bg-gray-50">Annuler</button>
          <button
            onClick={creer}
            disabled={!pret}
            className="rounded bg-blue-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {envoi ? 'Création…' : nomTech && heure ? `Créer pour ${nomTech} à ${heure}` : 'Créer le RV'}
          </button>
        </div>
      </div>
    </div>
  )
}
