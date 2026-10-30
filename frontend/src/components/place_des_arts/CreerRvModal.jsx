import { useEffect, useState } from 'react'
import { API_URL } from '../../utils/apiConfig'

// Fenêtre « Créer le RV » / « Modifier le RV » pour une demande Place des Arts.
// 1. Vérifier : la demande telle que comprise par l'assistant, à côté de la ligne du courriel d'Isabelle.
// 2. Choisir : la journée de TOUS les techniciens (Gazelle en direct) — clic sur une colonne.
// 3. Confirmer : heure, durée, piano Gazelle → un clic crée (ou modifie) le RV dans Gazelle.
const TECHS = [
  { id: 'usr_HcCiFk7o0vZ9xAI0', label: 'Nick' },
  { id: 'usr_ReUSmIJmBF86ilY1', label: 'JP' },
  { id: 'usr_bbt59aCUqUaDWA8n', label: 'Margot' },
  { id: 'usr_ofYggsCDt2JAVeNP', label: 'Allan' },
  { id: 'usr_HihJsEgkmpTEziJo', label: 'À attribuer' },
]

const LIBELLES = { date: 'Date', salle: 'Salle', pour_qui: 'Pour qui', piano: 'Piano', diapason: 'Diapason', heure: 'Heure demandée' }

// Pré-remplit l'heure seulement si la demande donne une heure précise (« 18h », « à 13h30 »).
// « Avant 10h » reste vide : c'est à nous de fixer l'heure confirmée.
function heureProposee(texte) {
  const t = (texte || '').toLowerCase().trim()
  if (!t || t.startsWith('avant') || t.startsWith('before') || t.startsWith('entre')) return ''
  const m = t.match(/(\d{1,2})\s*(?:h|:)\s*(\d{2})?/) || t.match(/(\d{1,2})\s*(am|pm)/)
  if (!m) return ''
  let h = parseInt(m[1], 10)
  if (m[2] === 'pm' && h < 12) h += 12
  const min = m[2] && /^\d{2}$/.test(m[2]) ? m[2] : '00'
  if (h > 23) return ''
  return `${String(h).padStart(2, '0')}:${min}`
}

const enMin = (hhmm) => { const [h, m] = (hhmm || '0:0').split(':').map(Number); return h * 60 + (m || 0) }
const versHHMM = (min) => `${String(Math.floor(min / 60)).padStart(2, '0')}:${String(min % 60).padStart(2, '0')}`
const heuresDuTexte = (t) => [...(t || '').toLowerCase().matchAll(/(\d{1,2})\s*(?:h|:)\s*(\d{2})?/g)].map((m) => parseInt(m[1], 10) * 60 + (m[2] ? parseInt(m[2], 10) : 0))

// L'heure confirmée respecte-t-elle l'heure demandée ? (« avant 8h », « entre 13h et 14h », « à 18h »)
function verifierHeure(demandee, heure, duree) {
  if (!/^\d{2}:\d{2}$/.test(heure) || !demandee) return null
  const t = demandee.toLowerCase()
  const h = heuresDuTexte(t)
  if (!h.length) return null
  const debut = enMin(heure), fin = debut + Number(duree || 60)
  if (/avant|before/.test(t)) return fin <= h[0] ? { ok: true, txt: `fini à ${versHHMM(fin)}, avant ${versHHMM(h[0])}` } : { ok: false, txt: `finirait à ${versHHMM(fin)}, après ${versHHMM(h[0])} demandé` }
  if (/entre|between/.test(t) && h.length >= 2) return debut >= h[0] && debut <= h[1] ? { ok: true, txt: 'dans la plage demandée' } : { ok: false, txt: `hors de la plage ${versHHMM(h[0])}–${versHHMM(h[1])}` }
  if (/apres|après|after/.test(t)) return debut >= h[0] ? { ok: true, txt: `après ${versHHMM(h[0])}` } : { ok: false, txt: `avant ${versHHMM(h[0])} demandé` }
  return Math.abs(debut - h[0]) <= 15 ? { ok: true, txt: 'à l\'heure demandée' } : { ok: false, txt: `demandé à ${versHHMM(h[0])}` }
}

// Le piano Gazelle choisi ressemble-t-il au piano demandé ? (taille 7'/9', marque)
const normaliser = (t) => (t || '').toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '').replace(/[’′]/g, "'")
function jetonsPiano(t) {
  const n = normaliser(t)
  const tailles = [...n.matchAll(/(\d+)\s*'/g)].map((m) => `${m[1]}'`)
  const marques = [...n.matchAll(/steinway|baldwin|yamaha|fazioli|kawai|mason/g)].map((m) => m[0])
  const lm = n.match(/steinway\s*[-–(]?\s*(?:\d+\s*'\s*)?\(?\s*([bdmosk])\b/)
  return { tailles, marques, modele: lm ? lm[1] : null }
}
function verifierPiano(demande, libelle) {
  if (!demande || !libelle) return null
  const a = jetonsPiano(demande), b = jetonsPiano(libelle)
  const ecarts = []
  if (a.marques.length && b.marques.length && !a.marques.some((m) => b.marques.includes(m))) ecarts.push('marque')
  if (a.tailles.length && b.tailles.length && !a.tailles.some((m) => b.tailles.includes(m))) ecarts.push('taille')
  if (a.modele && b.modele && a.modele !== b.modele) ecarts.push(`modèle (${a.modele.toUpperCase()} demandé, ${b.modele.toUpperCase()} choisi)`)
  return ecarts.length ? `⚠︎ ${ecarts.join(', ')} : différent du piano demandé` : null
}

const jourLong = (iso) => {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(iso || '')) return iso || ''
  const d = new Date(`${iso}T12:00:00`)
  return d.toLocaleDateString('fr-CA', { weekday: 'short', day: 'numeric', month: 'short' })
}

// Conflit si le RV [heure, heure+durée] chevauche un RV existant (journée entière = conflit).
function conflits(rvs, heure, duree, ignorerId) {
  if (!/^\d{2}:\d{2}$/.test(heure)) return []
  const a = enMin(heure), b = a + Number(duree || 60)
  return (rvs || []).filter((r) => r.id !== ignorerId && (r.journee || (enMin(r.heure) < b && a < enMin(r.heure) + Number(r.duree || 60))))
}

function Icone({ statut }) {
  if (statut === 'ok') return <span className="text-green-600">✓</span>
  if (statut === 'ecart') return <span className="text-amber-600">⚠︎</span>
  if (statut === 'vide') return <span className="text-red-600">∅</span>
  return <span className="text-gray-400">?</span>
}

// Indicateur de chargement : roue + secondes écoulées, et un mot rassurant si Gazelle/Front est lent.
function Attente({ texte, lent = 8 }) {
  const [sec, setSec] = useState(0)
  useEffect(() => { const t = setInterval(() => setSec((s) => s + 1), 1000); return () => clearInterval(t) }, [])
  return (
    <span className="inline-flex items-center gap-2 text-xs text-gray-600">
      <span className="inline-block h-3.5 w-3.5 animate-spin rounded-full border-2 border-blue-500 border-t-transparent" />
      <span>{texte}… {sec > 0 && <span className="tabular-nums text-gray-400">{sec} s</span>}
        {sec >= lent && <span className="text-gray-500"> — ça vient, {sec >= 20 ? 'Gazelle est lent en ce moment' : 'encore quelques secondes'}.</span>}
      </span>
    </span>
  )
}

function Verification({ verif, demandeId }) {
  if (verif === 'chargement') return <div className="mt-3 rounded border border-gray-200 bg-gray-50 p-2"><Attente texte="1. Vérifier — recherche du courriel d'origine dans Front" /></div>
  if (!verif) return null
  if (verif.erreurReseau) return <div className="mt-3 rounded bg-amber-50 p-2 text-xs text-amber-800">Vérification indisponible : {verif.erreurReseau}</div>
  const champs = verif.champs || {}
  const nbEcarts = Object.values(champs).filter((c) => c.statut === 'ecart' || c.statut === 'vide').length
  const lignes = verif.lignes || []
  const nbAssistant = lignes.reduce((n, l) => n + (l.demandes || []).length, 0)
  return (
    <div className={`mt-3 rounded border p-2 text-xs ${!verif.trouve || nbEcarts || !verif.ligne ? 'border-amber-300 bg-amber-50' : 'border-green-300 bg-green-50'}`}>
      <div className="mb-1 flex items-center justify-between gap-2">
        <span className="font-semibold text-gray-800">
          1. Vérifier — {!verif.trouve ? 'courriel introuvable' : !verif.ligne ? 'aucune ligne du courriel à cette date' : nbEcarts ? `${nbEcarts} détail${nbEcarts > 1 ? 's' : ''} à vérifier` : 'tout concorde avec le courriel'}
        </span>
        {verif.front_url && <a href={verif.front_url} target="_blank" rel="noreferrer" className="whitespace-nowrap text-blue-700 underline">Ouvrir dans Front ↗</a>}
      </div>
      {!verif.trouve && <div className="text-amber-800">{verif.erreur} Compare avec le courriel dans Front avant de confirmer.</div>}
      {verif.trouve && (
        <>
          {verif.ligne && (
            <div className="mb-2 rounded bg-white p-1.5 text-gray-800">
              <span className="text-gray-500">Courriel{verif.origine === 'import' ? ' (texte collé)' : ''} : </span>
              <span className="font-mono text-[11px]">{verif.ligne.texte}</span>
            </div>
          )}
          <table className="w-full">
            <tbody>
              {Object.entries(LIBELLES).map(([cle, lib]) => {
                const c = champs[cle] || {}
                return (
                  <tr key={cle} className={c.statut === 'ecart' || c.statut === 'vide' ? 'bg-amber-100' : ''}>
                    <td className="w-5 py-0.5 text-center"><Icone statut={c.statut} /></td>
                    <td className="w-28 py-0.5 text-gray-500">{lib}</td>
                    <td className="py-0.5 font-medium text-gray-900">
                      {cle === 'date' ? jourLong(c.valeur) : (c.valeur || '—')}
                      {c.statut === 'ok' && c.ou === 'courriel' && <span className="ml-1 font-normal text-gray-500">(dit ailleurs dans le courriel)</span>}
                      {c.statut === 'ecart' && <span className="ml-1 font-normal text-amber-700">pas dans la ligne du courriel</span>}
                      {c.statut === 'vide' && <span className="ml-1 font-normal text-red-700">manquant</span>}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
          {verif.alerte_sujet && <div className="mt-1 text-amber-800">⚠︎ {verif.alerte_sujet}</div>}
          {lignes.length > 0 && (
            <div className="mt-2 border-t border-gray-200 pt-1">
              <div className={`font-medium ${nbAssistant !== lignes.length ? 'text-amber-800' : 'text-gray-700'}`}>
                Ce courriel : {lignes.length} piano{lignes.length > 1 ? 's' : ''} demandé{lignes.length > 1 ? 's' : ''} · dans l'assistant : {nbAssistant}
              </div>
              {lignes.map((l, i) => {
                const n = (l.demandes || []).length
                const ici = (l.demandes || []).some((d) => d.id === demandeId)
                return (
                  <div key={i} className={`flex gap-1 ${n === 0 || n > 1 ? 'text-amber-800' : 'text-gray-600'}`}>
                    <span className="w-4 shrink-0">{n === 1 ? '✓' : '⚠︎'}</span>
                    <span className="min-w-0 break-words">
                      {ici && <b>cette demande · </b>}{l.texte}
                      {n === 0 && <b> — absente de l'assistant</b>}
                      {n > 1 && <b> — {n} entrées dans l'assistant</b>}
                    </span>
                  </div>
                )
              })}
            </div>
          )}
        </>
      )}
    </div>
  )
}

function JourneeTechniciens({ journee, tech, setTech, heure, duree, rvActuelId }) {
  if (journee === 'chargement') return (
    <div className="mt-3">
      <div className="mb-1"><Attente texte="2. Choisir — lecture des calendriers de tous les techniciens dans Gazelle" /></div>
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-5">
        {TECHS.map((t) => (
          <div key={t.id} className="animate-pulse rounded border border-gray-200 bg-white p-1.5 text-[11px]">
            <div className="mb-1 font-semibold text-gray-400">{t.label}</div>
            <div className="mb-1 h-2 w-4/5 rounded bg-gray-200" />
            <div className="h-2 w-3/5 rounded bg-gray-200" />
          </div>
        ))}
      </div>
    </div>
  )
  if (!journee) return null
  if (journee.erreur) return <div className="mt-3 rounded bg-amber-50 p-2 text-xs text-amber-800">Journée des techniciens indisponible : {journee.erreur}</div>
  return (
    <div className="mt-3">
      <div className="mb-1 text-xs font-semibold text-gray-800">2. Choisir — journée des techniciens, {jourLong(journee.date)} <span className="font-normal text-gray-500">(clic = choisir)</span></div>
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-5">
        {journee.techniciens.map((t) => {
          const choisi = t.id === tech
          const c = conflits(t.rendez_vous, heure, duree, rvActuelId)
          return (
            <button type="button" key={t.id} onClick={() => setTech(t.id)}
              className={`rounded border p-1.5 text-left text-[11px] leading-tight ${choisi ? 'border-blue-500 bg-blue-50' : 'border-gray-200 bg-white hover:bg-gray-50'}`}>
              <div className="mb-1 flex items-center justify-between font-semibold text-gray-800">
                <span>{t.nom}</span>
                {heure && <span className={c.length ? 'text-red-600' : 'text-green-600'}>{c.length ? '⚠︎' : '✓'}</span>}
              </div>
              {t.rendez_vous.length === 0 && <div className="text-gray-400">Libre</div>}
              {t.rendez_vous.map((r) => (
                <div key={r.id} className={`mb-0.5 break-words ${r.id === rvActuelId ? 'font-semibold text-blue-700' : c.includes(r) ? 'text-red-600' : r.perso ? 'text-gray-500 italic' : 'text-gray-700'}`} title={r.titre}>
                  {r.journee ? 'Journée' : `${r.heure}–${r.fin}`} {r.id === rvActuelId ? '(ce RV) ' : ''}{r.titre}
                </div>
              ))}
            </button>
          )
        })}
      </div>
    </div>
  )
}

export default function CreerRvModal({ demande, onClose, onCreated, onReassigned, par }) {
  const modifier = Boolean(demande.appointment_id)
  const techInitial = TECHS.some((t) => t.id === demande.technician_id) ? demande.technician_id : ''
  const [tech, setTech] = useState(techInitial)
  const [date, setDate] = useState(modifier && demande.rv_date ? demande.rv_date : (demande.appointment_date || '').slice(0, 10))
  const [heure, setHeure] = useState(modifier && demande.rv_heure ? demande.rv_heure.slice(0, 5) : heureProposee(demande.time))
  const [duree, setDuree] = useState(60)
  const [pianos, setPianos] = useState([])
  const [pianoId, setPianoId] = useState('')
  const [envoi, setEnvoi] = useState(false)
  const [erreur, setErreur] = useState(null)
  const [journee, setJournee] = useState(null)
  const [verif, setVerif] = useState(null)
  const [rvActuel, setRvActuel] = useState(modifier ? 'chargement' : null)
  const [copie, setCopie] = useState(false)

  // Pianos PdA + piano suggéré (création seulement : en modification, les pianos du RV ne bougent pas)
  useEffect(() => {
    if (modifier) return
    fetch(`${API_URL}/api/place-des-arts/pianos`).then((r) => r.ok ? r.json() : null)
      .then((d) => setPianos((d && d.pianos) || [])).catch(() => {})
    fetch(`${API_URL}/api/place-des-arts/requests/${demande.id}/gazelle-piano-id`).then((r) => r.ok ? r.json() : null)
      .then((d) => { if (d && d.piano_id) setPianoId(d.piano_id) }).catch(() => {})
  }, [demande.id, modifier])

  // Modification : le RV tel qu'il est maintenant dans Gazelle
  useEffect(() => {
    if (!modifier) return
    fetch(`${API_URL}/api/place-des-arts/requests/${demande.id}/rv-actuel`)
      .then(async (r) => { const d = await r.json().catch(() => ({})); if (!r.ok) throw new Error(d.detail || `Erreur ${r.status}`); return d })
      .then((rv) => { setRvActuel(rv); setTech(rv.technician_id || ''); setDate(rv.date); setHeure(rv.heure); setDuree(rv.duree || 60) })
      .catch((e) => setRvActuel({ erreur: e.message }))
  }, [demande.id, modifier])

  // Contre-vérification contre le courriel d'origine
  useEffect(() => {
    let annule = false
    setVerif('chargement')
    fetch(`${API_URL}/api/place-des-arts/requests/${demande.id}/verification`)
      .then(async (r) => { const d = await r.json().catch(() => ({})); if (!r.ok) throw new Error(d.detail || `Erreur ${r.status}`); return d })
      .then((d) => { if (!annule) setVerif(d) })
      .catch((e) => { if (!annule) setVerif({ erreurReseau: e.message }) })
    return () => { annule = true }
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
  const rvPret = !modifier || (rvActuel && rvActuel !== 'chargement' && !rvActuel.erreur)
  const pret = tech && date && /^\d{2}:\d{2}$/.test(heure) && duree > 0 && !envoi && rvPret
  const libellePiano = (p) => `${p.local?.trim() || '?'} — ${p.piano || ''} ${p.modele || ''}`.trim()
  const pianoChoisi = pianos.find((p) => (p.gazelleId || p.id) === pianoId)
  const alertePiano = !modifier && pianoChoisi ? verifierPiano(demande.piano, libellePiano(pianoChoisi)) : null
  const controleHeure = verifierHeure(demande.time, heure, duree)
  const phrase = `C'est d'accord pour le ${jourLong(date)}, ${demande.room || ''}, ${demande.piano || ''}, ${demande.for_who || ''}${demande.time ? `, ${demande.time.charAt(0).toLowerCase()}${demande.time.slice(1)}` : ''}.`
    .replace(/,\s*,/g, ',').replace(/\s+/g, ' ')

  const copier = async () => {
    try { await navigator.clipboard.writeText(phrase); setCopie(true); setTimeout(() => setCopie(false), 2000) } catch { /* presse-papiers bloqué */ }
  }

  const envoyer = async () => {
    setEnvoi(true); setErreur(null)
    try {
      const url = modifier
        ? `${API_URL}/api/place-des-arts/requests/${demande.id}/reassigner-rv`
        : `${API_URL}/api/place-des-arts/requests/${demande.id}/creer-rv-gazelle`
      const resp = await fetch(url, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ technician_id: tech, date, heure, duree_min: Number(duree), piano_id: pianoId || null, par: par || null }),
      })
      const d = await resp.json().catch(() => ({}))
      if (!resp.ok) throw new Error(d.detail || `Erreur ${resp.status}`)
      if (modifier) (onReassigned || onClose)(d, nomTech)
      else onCreated(d, nomTech)
    } catch (e) {
      setErreur(e.message)
      setEnvoi(false)
    }
  }

  const libelleBouton = envoi
    ? (modifier ? 'Enregistrement…' : 'Création…')
    : nomTech && heure
      ? `${modifier ? 'Modifier' : 'Créer'} : ${jourLong(date)} · ${nomTech} · ${heure}`
      : (modifier ? 'Modifier le RV' : 'Créer le RV')

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-2 sm:p-4" onClick={onClose}>
      <div className="max-h-[94vh] w-full max-w-2xl overflow-y-auto rounded-lg bg-white p-4 shadow-xl sm:p-5" onClick={(e) => e.stopPropagation()}>
        <h3 className="text-base font-semibold text-gray-900">{modifier ? 'Modifier le RV dans Gazelle' : 'Créer le RV dans Gazelle'}</h3>
        <div className="mt-1 text-xs text-gray-600"><b>{demande.for_who || '—'}</b> · {demande.room || '—'} · {demande.piano || '—'}</div>

        {modifier && (
          <div className="mt-2 rounded bg-blue-50 p-2 text-xs text-blue-900">
            {rvActuel === 'chargement' && <Attente texte="Lecture du RV dans Gazelle" />}
            {rvActuel && rvActuel.erreur && <span className="text-red-700">RV illisible dans Gazelle : {rvActuel.erreur}</span>}
            {rvActuel && rvActuel.id && (
              <>
                RV actuel : <b>{(TECHS.find((t) => t.id === rvActuel.technician_id) || {}).label || rvActuel.technicien || '?'}</b>, {jourLong(rvActuel.date)} à {rvActuel.heure} ({rvActuel.duree} min).
                {rvActuel.nb_demandes > 1 && <> Ce RV couvre <b>{rvActuel.nb_demandes} demandes</b> : elles suivront toutes.</>}
                {' '}Les pianos du RV ne changent pas.
              </>
            )}
          </div>
        )}

        <Verification verif={verif} demandeId={demande.id} />

        <JourneeTechniciens journee={journee} tech={tech} setTech={setTech} heure={heure} duree={duree} rvActuelId={modifier && rvActuel ? rvActuel.id : null} />

        <div className="mt-3 text-xs font-semibold text-gray-800">3. Confirmer</div>
        <div className="mt-1 grid grid-cols-2 gap-3 text-sm">
          <label className="col-span-2 sm:col-span-1">
            <span className="text-xs text-gray-600">Technicien</span>
            <select value={tech} onChange={(e) => setTech(e.target.value)} className="mt-1 w-full rounded border border-gray-300 px-2 py-1">
              <option value="">— choisir —</option>
              {TECHS.map((t) => <option key={t.id} value={t.id}>{t.label}</option>)}
            </select>
          </label>
          <label className="col-span-2 sm:col-span-1">
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
          {controleHeure && (
            <div className={`col-span-2 -mt-1 text-xs ${controleHeure.ok ? 'text-green-700' : 'text-red-700'}`}>
              {controleHeure.ok ? '✓' : '⚠︎'} Demandé « {demande.time} » : {controleHeure.txt}
            </div>
          )}
          {!modifier && (
            <label className="col-span-2">
              <span className="text-xs text-gray-600">Piano dans Gazelle <span className="text-gray-400">(demandé : {demande.piano || '—'})</span></span>
              <select value={pianoId} onChange={(e) => setPianoId(e.target.value)} className="mt-1 w-full rounded border border-gray-300 px-2 py-1">
                <option value="">— aucun piano lié —</option>
                {pianos.map((p) => <option key={p.gazelleId || p.id} value={p.gazelleId || p.id}>{libellePiano(p)}</option>)}
              </select>
              {alertePiano && <div className="mt-0.5 text-xs text-red-700">{alertePiano}</div>}
            </label>
          )}
        </div>

        {!modifier && (
          <div className="mt-3 rounded border border-gray-200 bg-gray-50 p-2 text-xs">
            <div className="mb-1 flex items-center justify-between">
              <span className="text-gray-600">Phrase de confirmation pour la PdA (mêmes infos que le RV) :</span>
              <button type="button" onClick={copier} className="rounded border border-gray-300 bg-white px-2 py-0.5 hover:bg-gray-100">{copie ? 'Copié ✓' : 'Copier'}</button>
            </div>
            <div className="text-gray-900">{phrase}</div>
          </div>
        )}

        {erreur && <div className="mt-3 rounded bg-red-50 p-2 text-xs text-red-700">{erreur}</div>}

        <div className="mt-4 flex justify-end gap-2">
          <button onClick={onClose} className="rounded border border-gray-300 bg-white px-3 py-1.5 text-sm hover:bg-gray-50">Annuler</button>
          <button
            onClick={envoyer}
            disabled={!pret}
            className="rounded bg-blue-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {libelleBouton}
          </button>
        </div>
      </div>
    </div>
  )
}
