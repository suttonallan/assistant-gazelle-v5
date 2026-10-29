import { useEffect, useState } from 'react'
import { API_URL } from '../../utils/apiConfig'

// Fenêtre « Créer le RV dans Gazelle » pour une demande Place des Arts.
// On choisit le technicien, on voit sa journée (dispo), on confirme l'heure → un clic crée le RV.
const TECHS = [
  { id: 'usr_HcCiFk7o0vZ9xAI0', label: 'Nick' },
  { id: 'usr_ReUSmIJmBF86ilY1', label: 'JP' },
  { id: 'usr_bbt59aCUqUaDWA8n', label: 'Margot' },
  { id: 'usr_ofYggsCDt2JAVeNP', label: 'Allan' },
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

export default function CreerRvModal({ demande, onClose, onCreated }) {
  const techInitial = TECHS.some((t) => t.id === demande.technician_id) ? demande.technician_id : ''
  const [tech, setTech] = useState(techInitial)
  const [date, setDate] = useState((demande.appointment_date || '').slice(0, 10))
  const [heure, setHeure] = useState(heureProposee(demande.time))
  const [duree, setDuree] = useState(60)
  const [pianos, setPianos] = useState([])
  const [pianoId, setPianoId] = useState('')
  const [journee, setJournee] = useState(null)
  const [envoi, setEnvoi] = useState(false)
  const [erreur, setErreur] = useState(null)

  // Pianos PdA + piano suggéré pour cette demande
  useEffect(() => {
    fetch(`${API_URL}/api/place-des-arts/pianos`).then((r) => r.ok ? r.json() : null)
      .then((d) => setPianos((d && d.pianos) || [])).catch(() => {})
    fetch(`${API_URL}/api/place-des-arts/requests/${demande.id}/gazelle-piano-id`).then((r) => r.ok ? r.json() : null)
      .then((d) => { if (d && d.piano_id) setPianoId(d.piano_id) }).catch(() => {})
  }, [demande.id])

  // Journée du technicien choisi
  useEffect(() => {
    if (!tech || !date) { setJournee(null); return }
    setJournee('chargement')
    fetch(`${API_URL}/api/place-des-arts/journee-technicien?technicien=${tech}&date=${date}`)
      .then((r) => r.ok ? r.json() : null)
      .then((d) => setJournee(d ? d.rendez_vous : []))
      .catch(() => setJournee([]))
  }, [tech, date])

  const nomTech = (TECHS.find((t) => t.id === tech) || {}).label
  const pret = tech && date && /^\d{2}:\d{2}$/.test(heure) && duree > 0 && !envoi

  const creer = async () => {
    setEnvoi(true); setErreur(null)
    try {
      const resp = await fetch(`${API_URL}/api/place-des-arts/requests/${demande.id}/creer-rv-gazelle`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ technician_id: tech, date, heure, duree_min: Number(duree), piano_id: pianoId || null }),
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
      <div className="w-full max-w-md rounded-lg bg-white p-5 shadow-xl" onClick={(e) => e.stopPropagation()}>
        <h3 className="text-base font-semibold text-gray-900">Créer le RV dans Gazelle</h3>
        <div className="mt-2 rounded bg-gray-50 p-2 text-xs text-gray-700">
          <div><b>{demande.for_who || '—'}</b> · {demande.room || '—'}</div>
          <div>Demandé : {(demande.appointment_date || '').slice(0, 10)} — <b>{demande.time || 'heure non précisée'}</b></div>
          <div>Piano demandé : {demande.piano || '—'}{demande.diapason ? ` · ${demande.diapason}` : ''}</div>
        </div>

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

        {tech && date && (
          <div className="mt-3 rounded border border-gray-200 p-2 text-xs">
            <div className="mb-1 font-medium text-gray-700">Journée de {nomTech} le {date}</div>
            {journee === 'chargement' && <div className="text-gray-500">Chargement…</div>}
            {Array.isArray(journee) && journee.length === 0 && <div className="text-green-700">Rien au calendrier ce jour-là.</div>}
            {Array.isArray(journee) && journee.map((r) => (
              <div key={r.id} className="text-gray-700">
                {r.heure || '—'}{r.duree ? ` (${r.duree} min)` : ''} · {r.perso ? '🔒 ' : ''}{r.titre}
              </div>
            ))}
            <div className="mt-1 text-gray-400">Copie de Gazelle mise à jour chaque heure.</div>
          </div>
        )}

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
