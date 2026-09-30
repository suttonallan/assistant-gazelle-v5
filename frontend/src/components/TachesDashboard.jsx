import React, { useCallback, useEffect, useMemo, useState } from 'react'
import { API_URL } from '../utils/apiConfig'

/**
 * Tâches — maquette « Tâches Gazelle v7 »
 * Étage 1 : Campagnes (éléments rattachés + commentaires équipe Front)
 * Étage 2 : Tableau À faire / En cours / Fait
 */

const COLONNES = [
  { id: 'a_faire', nom: 'À faire', fond: '' },
  { id: 'en_cours', nom: 'En cours', fond: 'bg-amber-50' },
  { id: 'fait', nom: 'Fait', fond: 'bg-green-50' },
]
const SUIVANT = { a_faire: 'en_cours', en_cours: 'fait', fait: 'a_faire' }

const MEMBRES = {
  allan: { nom: 'Allan', couleur: 'bg-slate-600' },
  nicolas: { nom: 'Nicolas', couleur: 'bg-blue-700' },
  louise: { nom: 'Louise', couleur: 'bg-amber-600' },
  margot: { nom: 'Margot', couleur: 'bg-purple-600' },
  jp: { nom: 'JP', couleur: 'bg-green-700' },
  ilyan: { nom: 'Ilyan', couleur: 'bg-teal-600' },
}
// Couleur par client : Nicolas sait où il va avant de lire.
const CLIENTS = {
  pda: { nom: 'Place des Arts', bord: 'border-l-violet-500', puce: 'bg-violet-500', chip: 'bg-violet-100 text-violet-800', bande: 'from-violet-500 to-fuchsia-500' },
  vdi: { nom: "Vincent-d'Indy", bord: 'border-l-sky-500', puce: 'bg-sky-500', chip: 'bg-sky-100 text-sky-800', bande: 'from-sky-500 to-blue-600' },
  orford: { nom: 'Orford', bord: 'border-l-emerald-500', puce: 'bg-emerald-500', chip: 'bg-emerald-100 text-emerald-800', bande: 'from-emerald-500 to-teal-500' },
  prive: { nom: 'Privé', bord: 'border-l-amber-500', puce: 'bg-amber-500', chip: 'bg-amber-100 text-amber-800', bande: 'from-amber-400 to-orange-500' },
  interne: { nom: 'PTM', bord: 'border-l-slate-400', puce: 'bg-slate-400', chip: 'bg-slate-100 text-slate-700', bande: 'from-slate-400 to-slate-600' },
}
const CAMPAGNE_VERS_CLIENT = { 'place-des-arts': 'pda', orford: 'orford', 'vincent-dindy': 'vdi' }
const clientDe = (t) => {
  if (t.client && CLIENTS[t.client]) return t.client
  if (t.campagne && CAMPAGNE_VERS_CLIENT[t.campagne]) return CAMPAGNE_VERS_CLIENT[t.campagne]
  const txt = `${t.titre || ''} ${t.contexte || ''}`.toLowerCase()
  if (txt.includes("d'indy") || txt.includes('dindy') || txt.includes('vdi')) return 'vdi'
  if (txt.includes('place des arts') || txt.includes('pda') || /\btm\b|maisonneuve|wilfrid/.test(txt)) return 'pda'
  if (txt.includes('orford')) return 'orford'
  return null
}

// Bandes de l'échéancier, du plus pressé au moins pressé
const BANDES = [
  { id: 'retard', nom: 'En retard', emoji: '🔴', fond: 'bg-red-50', titre: 'text-red-700', filet: 'bg-red-500' },
  { id: 'auj', nom: "Aujourd'hui", emoji: '🟠', fond: 'bg-orange-50', titre: 'text-orange-700', filet: 'bg-orange-500' },
  { id: 'semaine', nom: 'Cette semaine', emoji: '🟡', fond: 'bg-yellow-50', titre: 'text-yellow-800', filet: 'bg-yellow-400' },
  { id: 'prochaine', nom: 'Semaine prochaine', emoji: '🟢', fond: 'bg-green-50', titre: 'text-green-700', filet: 'bg-green-500' },
  { id: 'plus_tard', nom: 'Plus tard', emoji: '🔵', fond: 'bg-sky-50', titre: 'text-sky-700', filet: 'bg-sky-400' },
  { id: 'sans_date', nom: 'Sans date', emoji: '⚪', fond: 'bg-gray-50', titre: 'text-gray-600', filet: 'bg-gray-300' },
]
const bandeDe = (t) => {
  const n = joursAvant(t.echeance)
  if (n === null) return 'sans_date'
  if (n < 0) return 'retard'
  if (n === 0) return 'auj'
  const auj = aujourdhui()
  const finSemaine = 7 - (auj.getDay() === 0 ? 7 : auj.getDay()) // jours jusqu'à dimanche
  if (n <= finSemaine) return 'semaine'
  if (n <= finSemaine + 7) return 'prochaine'
  return 'plus_tard'
}

const ROLE_VERS_MEMBRE = { admin: 'allan', nick: 'nicolas', louise: 'louise', margot: 'margot', jeanphilippe: 'jp' }

// Correspondance nom Front → membre (pour les avatars des commentaires)
const membreDepuisNom = (nom = '') => {
  const n = nom.toLowerCase()
  if (n.includes('allan')) return 'allan'
  if (n.includes('nicolas') || n.includes('nick')) return 'nicolas'
  if (n.includes('louise')) return 'louise'
  if (n.includes('margot')) return 'margot'
  return null
}

const aujourdhui = () => {
  const d = new Date()
  return new Date(d.getFullYear(), d.getMonth(), d.getDate())
}
const parseDate = (s) => {
  if (!s) return null
  const [y, m, j] = s.slice(0, 10).split('-').map(Number)
  return new Date(y, m - 1, j)
}
const joursAvant = (s) => {
  const d = parseDate(s)
  if (!d) return null
  return Math.round((d - aujourdhui()) / 86400000)
}
const formatEcheance = (s, statut) => {
  const d = parseDate(s)
  if (!d) return { texte: '', ton: '' }
  const n = joursAvant(s)
  const court = d.toLocaleDateString('fr-CA', { weekday: 'short', day: 'numeric', month: 'short' })
  if (statut === 'fait') return { texte: court, ton: '' }
  if (n < 0) return { texte: `en retard · ${-n} j`, ton: 'text-red-600 font-semibold' }
  if (n === 0) return { texte: "aujourd'hui", ton: 'text-amber-700 font-semibold' }
  if (n === 1) return { texte: 'demain', ton: 'text-amber-700' }
  return { texte: court, ton: 'text-gray-500' }
}
const formatQuand = (iso) => {
  if (!iso) return ''
  const d = new Date(iso)
  const n = Math.round((aujourdhui() - new Date(d.getFullYear(), d.getMonth(), d.getDate())) / 86400000)
  if (n === 0) return "aujourd'hui"
  if (n === 1) return 'hier'
  if (n === 2) return 'avant-hier'
  return d.toLocaleDateString('fr-CA', { day: 'numeric', month: 'short' })
}

// Urgent en haut : en retard, puis aujourd'hui, puis par échéance ; sans date à la fin.
const trierUrgence = (a, b) => {
  if (!!b.urgent - !!a.urgent) return !!b.urgent - !!a.urgent
  const da = joursAvant(a.echeance)
  const db = joursAvant(b.echeance)
  if (da === null && db === null) return (a.created_at || '').localeCompare(b.created_at || '')
  if (da === null) return 1
  if (db === null) return -1
  return da - db
}

// Ordre manuel (flèches ↑↓) d'abord ; sans ordre choisi → classement par urgence.
const trierOrdre = (a, b) => {
  const oa = a.ordre ?? null
  const ob = b.ordre ?? null
  if (oa === null && ob === null) return trierUrgence(a, b)
  if (oa === null) return -1
  if (ob === null) return 1
  return oa - ob
}

// Échange l'élément i avec son voisin (delta = -1 ou +1) dans une copie de la liste.
const echanger = (liste, i, delta) => {
  const j = i + delta
  if (j < 0 || j >= liste.length) return null
  const copie = [...liste]
  ;[copie[i], copie[j]] = [copie[j], copie[i]]
  return copie
}

function Fleches({ onMonter, onDescendre, className = '' }) {
  const btn = 'w-6 h-5 flex items-center justify-center rounded text-[11px] leading-none text-gray-400 hover:text-blue-700 hover:bg-blue-50 disabled:opacity-20 disabled:hover:bg-transparent'
  return (
    <span className={`inline-flex flex-col ${className}`} onClick={(e) => e.stopPropagation()}>
      <button type="button" title="Monter" className={btn} disabled={!onMonter} onClick={onMonter}>▲</button>
      <button type="button" title="Descendre" className={btn} disabled={!onDescendre} onClick={onDescendre}>▼</button>
    </span>
  )
}

async function api(chemin, options = {}) {
  const r = await fetch(`${API_URL}/api/taches${chemin}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  const texte = await r.text()
  const data = texte ? JSON.parse(texte) : null
  if (!r.ok) throw new Error(data?.detail || `Erreur ${r.status}`)
  return data
}

function Avatar({ membre, petit }) {
  const m = MEMBRES[membre]
  const taille = petit ? 'w-6 h-6 text-[10px]' : 'w-7 h-7 text-[11px]'
  if (!m) return <span className={`${taille} inline-flex items-center justify-center rounded-full bg-gray-300 text-white font-bold`}>?</span>
  return (
    <span title={m.nom} className={`${taille} ${m.couleur} inline-flex items-center justify-center rounded-full text-white font-bold flex-shrink-0`}>
      {m.nom[0]}
    </span>
  )
}

function Lien({ lien }) {
  const src = (lien.source || (lien.url?.includes('frontapp') ? 'front' : lien.url?.includes('google') ? 'drive' : 'lien')).toLowerCase()
  const tagCls = src === 'drive' ? 'bg-green-100 text-green-800' : src === 'front' ? 'bg-indigo-100 text-indigo-800' : 'bg-gray-100 text-gray-700'
  return (
    <a href={lien.url} target="_blank" rel="noreferrer" onClick={(e) => e.stopPropagation()}
      className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full border border-gray-200 bg-white hover:border-gray-400 text-xs max-w-full">
      <span className={`text-[9px] font-bold uppercase tracking-wider px-1 rounded ${tagCls}`}>{src}</span>
      <span className="truncate text-gray-800 font-medium">{lien.label || lien.url}</span>
    </a>
  )
}

function PastilleEtat({ statut, onClick }) {
  const cls = statut === 'fait' ? 'bg-green-600 border-green-600' : statut === 'en_cours' ? 'bg-amber-500 border-amber-500' : 'bg-transparent border-gray-400'
  return (
    <button type="button" onClick={onClick} title="Changer l'état (à faire → en cours → fait)"
      className={`w-3.5 h-3.5 rounded-full border-2 flex-shrink-0 flex items-center justify-center ${cls}`}>
      {statut === 'fait' && <span className="text-white text-[8px] leading-none">✓</span>}
    </button>
  )
}

function PastilleDate({ echeance, statut }) {
  const d = parseDate(echeance)
  if (!d) return null
  const n = joursAvant(echeance)
  const fait = statut === 'fait'
  const haut = fait ? 'bg-gray-400' : n < 0 ? 'bg-red-600' : n === 0 ? 'bg-orange-500' : n <= 3 ? 'bg-amber-500' : n <= 7 ? 'bg-yellow-500' : 'bg-emerald-600'
  return (
    <div className="w-12 flex-shrink-0 rounded-lg overflow-hidden border border-gray-200 bg-white text-center shadow-sm">
      <div className={`${haut} text-white text-[9px] font-bold uppercase tracking-wider py-0.5`}>
        {d.toLocaleDateString('fr-CA', { weekday: 'short' }).replace('.', '')}
      </div>
      <div className="text-xl font-extrabold text-gray-900 leading-tight tabular-nums">{d.getDate()}</div>
      <div className="text-[9px] font-semibold uppercase text-gray-500 pb-0.5">
        {d.toLocaleDateString('fr-CA', { month: 'short' }).replace('.', '')}
      </div>
    </div>
  )
}

function CompteRebours({ echeance, statut }) {
  const n = joursAvant(echeance)
  if (n === null || statut === 'fait') return null
  const cls = n < 0 ? 'bg-red-600 text-white' : n === 0 ? 'bg-orange-500 text-white' : n <= 3 ? 'bg-amber-400 text-amber-950' : n <= 7 ? 'bg-yellow-200 text-yellow-900' : 'bg-emerald-100 text-emerald-800'
  const txt = n < 0 ? `J+${-n}` : n === 0 ? "Auj." : `J-${n}`
  return <span className={`text-[11px] font-extrabold px-2 py-0.5 rounded-full tabular-nums ${cls}`}>{txt}</span>
}

function PuceClient({ client }) {
  const c = CLIENTS[client]
  if (!c) return null
  return <span className={`text-[10px] font-bold uppercase tracking-wide px-2 py-0.5 rounded-full ${c.chip}`}>{c.nom}</span>
}

/* ---------- Bande calendrier 14 jours ---------- */
function BandeCalendrier({ taches, jourChoisi, onChoisir }) {
  const jours = Array.from({ length: 14 }, (_, i) => { const d = aujourdhui(); d.setDate(d.getDate() + i); return d })
  const iso = (d) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
  const retard = taches.filter((t) => t.statut !== 'fait' && joursAvant(t.echeance) < 0).length
  return (
    <div className="flex gap-1.5 overflow-x-auto pb-2 mb-5 -mx-1 px-1">
      {retard > 0 && (
        <button onClick={() => onChoisir(jourChoisi === 'retard' ? null : 'retard')}
          className={`flex-shrink-0 w-16 rounded-xl py-2 text-center border-2 ${jourChoisi === 'retard' ? 'border-red-600 bg-red-600 text-white' : 'border-red-200 bg-red-50 text-red-700'}`}>
          <div className="text-[10px] font-bold uppercase">Retard</div>
          <div className="text-2xl font-extrabold leading-none mt-0.5">{retard}</div>
        </button>
      )}
      {jours.map((d, i) => {
        const k = iso(d)
        const du = taches.filter((t) => t.statut !== 'fait' && (t.echeance || '').slice(0, 10) === k)
        const weekend = d.getDay() === 0 || d.getDay() === 6
        const choisi = jourChoisi === k
        return (
          <button key={k} onClick={() => onChoisir(choisi ? null : k)}
            className={`flex-shrink-0 w-14 rounded-xl py-2 text-center border-2 transition ${choisi ? 'border-blue-600 bg-blue-600 text-white' : i === 0 ? 'border-orange-400 bg-orange-50' : weekend ? 'border-transparent bg-gray-100' : 'border-transparent bg-white shadow-sm'}`}>
            <div className={`text-[10px] font-bold uppercase ${choisi ? 'text-blue-100' : i === 0 ? 'text-orange-600' : 'text-gray-400'}`}>
              {i === 0 ? 'Auj.' : d.toLocaleDateString('fr-CA', { weekday: 'short' }).replace('.', '')}
            </div>
            <div className={`text-lg font-extrabold leading-tight ${choisi ? 'text-white' : 'text-gray-900'}`}>{d.getDate()}</div>
            <div className="flex justify-center gap-0.5 h-2 mt-0.5 flex-wrap px-1">
              {du.slice(0, 4).map((t) => (
                <span key={t.id} className={`w-1.5 h-1.5 rounded-full ${t.urgent ? 'bg-red-600' : CLIENTS[clientDe(t)]?.puce || 'bg-gray-400'} ${choisi ? 'ring-1 ring-white' : ''}`} />
              ))}
            </div>
          </button>
        )
      })}
    </div>
  )
}

/* ---------- Formulaire d'édition (modale) ---------- */
function ModaleTache({ tache, campagnes, onFermer, onEnregistrer, onSupprimer }) {
  const [f, setF] = useState(() => ({
    titre: tache.titre || '', contexte: tache.contexte || '', statut: tache.statut || 'a_faire',
    assigne: tache.assigne || '', echeance: tache.echeance || '', campagne: tache.campagne || '',
    note: tache.note || '', etapes: tache.etapes || [], liens: tache.liens || [],
    urgent: !!tache.urgent, client: tache.client || '',
  }))
  const maj = (k, v) => setF((x) => ({ ...x, [k]: v }))
  const champ = 'w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-blue-500'
  return (
    <div className="fixed inset-0 z-50 bg-black/40 flex items-start justify-center p-4 overflow-y-auto" onClick={onFermer}>
      <div className="bg-white rounded-xl shadow-xl w-full max-w-lg p-5 space-y-3 mt-8" onClick={(e) => e.stopPropagation()}>
        <div className="flex justify-between items-center">
          <h3 className="text-lg font-semibold">{tache.id ? 'Modifier la tâche' : 'Nouvelle tâche'}</h3>
          <button onClick={onFermer} className="text-gray-400 hover:text-gray-700 text-xl">×</button>
        </div>
        <input className={champ + ' font-semibold'} placeholder="Ce qu'il faut faire" value={f.titre} onChange={(e) => maj('titre', e.target.value)} autoFocus />
        <input className={champ} placeholder="Contexte (client, piano, soumission…)" value={f.contexte} onChange={(e) => maj('contexte', e.target.value)} />
        <div className="grid grid-cols-2 gap-2">
          <select className={champ} value={f.assigne} onChange={(e) => maj('assigne', e.target.value)}>
            <option value="">— Assigné —</option>
            {Object.entries(MEMBRES).map(([k, m]) => <option key={k} value={k}>{m.nom}</option>)}
          </select>
          <input type="date" className={champ} value={f.echeance || ''} onChange={(e) => maj('echeance', e.target.value)} />
          <select className={champ} value={f.statut} onChange={(e) => maj('statut', e.target.value)}>
            {COLONNES.map((c) => <option key={c.id} value={c.id}>{c.nom}</option>)}
          </select>
          <select className={champ} value={f.campagne} onChange={(e) => maj('campagne', e.target.value)}>
            <option value="">— Aucune campagne —</option>
            {campagnes.map((c) => <option key={c.slug} value={c.slug}>{c.nom}</option>)}
          </select>
        </div>
        <div className="grid grid-cols-2 gap-2">
          <select className={champ} value={f.client} onChange={(e) => maj('client', e.target.value)}>
            <option value="">— Client (couleur) —</option>
            {Object.entries(CLIENTS).map(([k, c]) => <option key={k} value={k}>{c.nom}</option>)}
          </select>
          <button type="button" onClick={() => maj('urgent', !f.urgent)}
            className={`rounded-lg px-3 py-2 text-sm font-bold border-2 ${f.urgent ? 'bg-red-600 border-red-600 text-white' : 'border-gray-300 text-gray-500'}`}>
            ⚡ {f.urgent ? 'Urgent' : 'Marquer urgent'}
          </button>
        </div>
        <input className={champ} placeholder="Note courte (ex. « +2 j », « facturé 7340 »)" value={f.note} onChange={(e) => maj('note', e.target.value)} />

        <div>
          <div className="text-xs font-bold uppercase tracking-wider text-gray-500 mb-1">Étapes</div>
          {f.etapes.map((et, i) => (
            <div key={i} className="flex items-center gap-2 mb-1">
              <Fleches
                onMonter={i > 0 ? () => maj('etapes', echanger(f.etapes, i, -1)) : null}
                onDescendre={i < f.etapes.length - 1 ? () => maj('etapes', echanger(f.etapes, i, 1)) : null} />
              <input type="checkbox" checked={!!et.fait} onChange={(e) => {
                const etapes = [...f.etapes]; etapes[i] = { ...et, fait: e.target.checked, date: e.target.checked ? new Date().toISOString().slice(0, 10) : null }; maj('etapes', etapes)
              }} />
              <input className="flex-1 border-b border-gray-200 text-sm py-1 focus:outline-none focus:border-blue-500" value={et.texte}
                onChange={(e) => { const etapes = [...f.etapes]; etapes[i] = { ...et, texte: e.target.value }; maj('etapes', etapes) }} />
              <button className="text-gray-400 hover:text-red-600" onClick={() => maj('etapes', f.etapes.filter((_, j) => j !== i))}>×</button>
            </div>
          ))}
          <button className="text-sm text-blue-600 hover:underline" onClick={() => maj('etapes', [...f.etapes, { texte: '', fait: false }])}>+ Ajouter une étape</button>
        </div>

        <div>
          <div className="text-xs font-bold uppercase tracking-wider text-gray-500 mb-1">Liens (Drive, Front…)</div>
          {f.liens.map((l, i) => (
            <div key={i} className="flex items-center gap-2 mb-1">
              <input className="w-1/3 border-b border-gray-200 text-sm py-1 focus:outline-none" placeholder="Nom" value={l.label || ''}
                onChange={(e) => { const liens = [...f.liens]; liens[i] = { ...l, label: e.target.value }; maj('liens', liens) }} />
              <input className="flex-1 border-b border-gray-200 text-sm py-1 focus:outline-none" placeholder="https://…" value={l.url || ''}
                onChange={(e) => { const liens = [...f.liens]; liens[i] = { ...l, url: e.target.value }; maj('liens', liens) }} />
              <button className="text-gray-400 hover:text-red-600" onClick={() => maj('liens', f.liens.filter((_, j) => j !== i))}>×</button>
            </div>
          ))}
          <button className="text-sm text-blue-600 hover:underline" onClick={() => maj('liens', [...f.liens, { label: '', url: '' }])}>+ Ajouter un lien</button>
        </div>

        <div className="flex justify-between pt-2">
          {tache.id ? (
            <button className="text-sm text-red-600 hover:underline" onClick={() => { if (window.confirm('Supprimer cette tâche ?')) onSupprimer(tache) }}>Supprimer</button>
          ) : <span />}
          <div className="flex gap-2">
            <button className="px-4 py-2 text-sm border border-gray-300 rounded-lg" onClick={onFermer}>Annuler</button>
            <button className="px-4 py-2 text-sm bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded-lg disabled:opacity-50"
              disabled={!f.titre.trim()}
              onClick={() => onEnregistrer({
                ...f,
                etapes: f.etapes.filter((e) => e.texte.trim()),
                liens: f.liens.filter((l) => (l.url || '').trim()),
              })}>
              Enregistrer
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

/* ---------- Carte campagne ---------- */
function CarteCampagne({ campagne, elements, moi, onCycle, onOuvrir, onAjouter, onReordonner }) {
  const [ouverte, setOuverte] = useState(false)
  const [front, setFront] = useState(null)
  const [ajout, setAjout] = useState(false)
  const [nouv, setNouv] = useState({ titre: '', note: '', assigne: moi || '' })

  useEffect(() => {
    let annule = false
    api(`/campagnes/${campagne.slug}/commentaires?limite=4`)
      .then((d) => { if (!annule) setFront(d) })
      .catch((e) => { if (!annule) setFront({ disponible: false, raison: e.message, commentaires: [], conversations: [] }) })
    return () => { annule = true }
  }, [campagne.slug])

  const faits = elements.filter((t) => t.statut === 'fait').length
  const tries = [...elements].sort((a, b) => {
    const ordre = { fait: 0, en_cours: 1, a_faire: 2 }
    return ordre[a.statut] - ordre[b.statut] || trierOrdre(a, b)
  })

  const client = CAMPAGNE_VERS_CLIENT[campagne.slug]
  const couleur = CLIENTS[client] || CLIENTS.interne
  const ouverts = elements.filter((t) => t.statut !== 'fait')
  const prochaine = [...ouverts].filter((t) => t.echeance).sort(trierUrgence)[0]
  const urgents = ouverts.filter((t) => t.urgent).length
  const pct = elements.length ? Math.round((faits / elements.length) * 100) : 0

  return (
    <article className="bg-white border border-gray-200 rounded-2xl shadow-sm overflow-hidden flex flex-col">
      <div className={`h-2 bg-gradient-to-r ${couleur.bande}`} />
      <div className="p-4 flex flex-col gap-3">
      <div className="flex justify-between items-start gap-3 cursor-pointer" onClick={() => setOuverte(!ouverte)}>
        <div className="min-w-0">
          <h3 className="text-xl font-bold text-gray-900 leading-tight flex items-center gap-2">
            {campagne.nom}
            {urgents > 0 && <span className="text-[10px] font-extrabold bg-red-600 text-white px-2 py-0.5 rounded-full">⚡ {urgents} urgent{urgents > 1 ? 's' : ''}</span>}
          </h3>
          <div className="text-xs text-gray-500 mt-1">{campagne.sous_titre}</div>
          <div className="text-[11px] text-gray-400 mt-0.5">{campagne.contacts}</div>
        </div>
        <div className="flex items-center gap-2 flex-shrink-0">
          {prochaine && <PastilleDate echeance={prochaine.echeance} statut={prochaine.statut} />}
          <span className="text-gray-400 text-lg">{ouverte ? '▾' : '▸'}</span>
        </div>
      </div>
      <div onClick={() => setOuverte(!ouverte)} className="cursor-pointer">
        <div className="flex justify-between text-[11px] font-bold text-gray-500 mb-1">
          <span>{faits} / {elements.length} faits</span>
          {prochaine && <span className="truncate ml-2">Prochaine : {prochaine.titre}</span>}
        </div>
        <div className="h-2.5 bg-gray-100 rounded-full overflow-hidden">
          <div className={`h-full bg-gradient-to-r ${couleur.bande} rounded-full transition-all`} style={{ width: `${pct}%` }} />
        </div>
      </div>

      {ouverte && (
        <>
          <div className="border-t border-gray-100">
            {tries.length === 0 && <div className="text-sm text-gray-400 py-2">Aucun élément pour l'instant.</div>}
            {tries.map((t, i) => {
              const ech = formatEcheance(t.echeance, t.statut)
              const meta = t.note || ech.texte
              // On ne déplace qu'entre voisins du même statut (les faits restent groupés)
              const voisin = (d) => tries[i + d] && tries[i + d].statut === t.statut
              return (
                <div key={t.id} className="grid grid-cols-[24px_18px_1fr_auto] gap-2 items-center py-2 border-b border-gray-100 text-sm">
                  <Fleches
                    onMonter={voisin(-1) ? () => onReordonner(echanger(tries, i, -1)) : null}
                    onDescendre={voisin(1) ? () => onReordonner(echanger(tries, i, 1)) : null} />
                  <PastilleEtat statut={t.statut} onClick={() => onCycle(t)} />
                  <button className={`text-left truncate ${t.statut === 'fait' ? 'line-through text-gray-400' : 'text-gray-900 font-medium'}`} onClick={() => onOuvrir(t)}>
                    {t.titre}
                    {t.source === 'auto' && <span className="ml-2 text-[9px] uppercase tracking-wider border border-dashed border-gray-300 text-gray-400 px-1 rounded">auto</span>}
                  </button>
                  <span className={`text-xs whitespace-nowrap flex items-center gap-2 ${t.note ? (t.statut === 'en_cours' ? 'text-amber-700 font-semibold' : 'text-gray-500') : ech.ton}`}>
                    {t.urgent && t.statut !== 'fait' && <span className="text-red-600 font-extrabold">⚡</span>}
                    <span className="hidden sm:inline">{t.note || (t.echeance ? '' : meta)}</span>
                    <CompteRebours echeance={t.echeance} statut={t.statut} />
                    {t.assigne && <Avatar membre={t.assigne} petit />}
                  </span>
                </div>
              )
            })}
            {!ajout ? (
              <button className="w-full text-left text-sm text-blue-600 font-semibold py-2 hover:bg-blue-50 rounded-lg px-1" onClick={() => setAjout(true)}>
                + Ajouter à cette campagne
              </button>
            ) : (
              <div className="bg-blue-50 border border-dashed border-blue-400 rounded-xl p-3 mt-2 space-y-2">
                <input className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm" placeholder="Ce qu'il faut faire" autoFocus
                  value={nouv.titre} onChange={(e) => setNouv({ ...nouv, titre: e.target.value })}
                  onKeyDown={(e) => { if (e.key === 'Enter' && nouv.titre.trim()) { onAjouter({ ...nouv, campagne: campagne.slug }); setNouv({ titre: '', note: '', assigne: moi || '' }); setAjout(false) } }} />
                <div className="grid grid-cols-2 gap-2">
                  <input className="border border-gray-200 rounded-lg px-3 py-2 text-sm" placeholder="Note (ex. +1/2 j)" value={nouv.note} onChange={(e) => setNouv({ ...nouv, note: e.target.value })} />
                  <select className="border border-gray-200 rounded-lg px-3 py-2 text-sm" value={nouv.assigne} onChange={(e) => setNouv({ ...nouv, assigne: e.target.value })}>
                    <option value="">— Assigné —</option>
                    {Object.entries(MEMBRES).map(([k, m]) => <option key={k} value={k}>{m.nom}</option>)}
                  </select>
                </div>
                <div className="flex gap-2">
                  <button className="px-3 py-1.5 bg-blue-600 text-white text-sm font-semibold rounded-lg disabled:opacity-50" disabled={!nouv.titre.trim()}
                    onClick={() => { onAjouter({ ...nouv, campagne: campagne.slug }); setNouv({ titre: '', note: '', assigne: moi || '' }); setAjout(false) }}>Ajouter</button>
                  <button className="px-3 py-1.5 border border-gray-300 text-sm rounded-lg" onClick={() => setAjout(false)}>Annuler</button>
                </div>
              </div>
            )}
          </div>

          <div className="border-t border-gray-100 pt-3">
            <div className="text-[10.5px] font-bold uppercase tracking-wider text-gray-500 mb-1">Commentaires équipe · via Front</div>
            {!front && <div className="text-xs text-gray-400">Chargement…</div>}
            {front && !front.disponible && <div className="text-xs text-gray-400">{front.raison}</div>}
            {front && front.disponible && front.commentaires.length === 0 && <div className="text-xs text-gray-400">Aucun commentaire récent.</div>}
            {front && front.commentaires.map((c) => (
              <div key={c.id} className="group grid grid-cols-[24px_1fr_auto] gap-2 py-2 border-b border-gray-100 last:border-0">
                <Avatar membre={membreDepuisNom(c.author_name)} petit />
                <div className="min-w-0">
                  <div className="text-[11.5px] text-gray-500">
                    <span className="text-gray-900 font-semibold text-xs mr-2">{c.author_name}</span>
                    {formatQuand(c.posted_at)} · {c.conversation_subject}
                  </div>
                  <div className="text-[13px] text-gray-800 whitespace-pre-line line-clamp-3">{c.text}</div>
                </div>
                <button title="Masquer ce commentaire de la carte (il reste dans Front)"
                  className="self-start text-gray-300 hover:text-red-600 px-1 text-lg leading-none md:opacity-0 md:group-hover:opacity-100"
                  onClick={() => {
                    setFront((f) => ({ ...f, commentaires: f.commentaires.filter((x) => x.id !== c.id) }))
                    api(`/commentaires/${c.id}/masquer`, { method: 'POST', body: JSON.stringify({ par: moi }) })
                      .catch((e) => alert(`Non masqué : ${e.message}`))
                  }}>×</button>
              </div>
            ))}
          </div>

          {(campagne.liens?.length > 0 || front?.conversations?.length > 0) && (
            <div className="flex flex-wrap gap-1.5">
              {campagne.liens?.map((l, i) => <Lien key={i} lien={l} />)}
              {front?.conversations?.slice(0, 4).map((c) => <Lien key={c.id} lien={{ label: c.sujet, url: c.url, source: 'front' }} />)}
            </div>
          )}
        </>
      )}
      </div>
    </article>
  )
}

/* ---------- Carte tâche ---------- */
function CarteTache({ tache, onOuvrir, onDeplacer, onEtape, onEtapes, campagnes = [] }) {
  const etapes = tache.etapes || []
  const nbFaites = etapes.filter((e) => e.fait).length
  const idx = COLONNES.findIndex((c) => c.id === tache.statut)
  const fait = tache.statut === 'fait'
  const client = clientDe(tache)
  const couleur = CLIENTS[client]
  const camp = campagnes.find((c) => c.slug === tache.campagne)
  const urgent = tache.urgent && !fait
  return (
    <article onClick={() => onOuvrir(tache)}
      className={`relative bg-white border border-gray-200 border-l-[6px] ${couleur ? couleur.bord : 'border-l-gray-300'} rounded-xl p-3.5 shadow-sm hover:shadow-md transition cursor-pointer flex flex-col gap-2.5 ${fait ? 'opacity-70' : ''} ${urgent ? 'bg-red-50 ring-2 ring-red-500' : ''}`}>
      <div className="flex gap-3 items-start">
        <PastilleDate echeance={tache.echeance} statut={tache.statut} />
        <div className="flex-1 min-w-0">
          <div className="flex flex-wrap items-center gap-1.5 mb-1">
            {urgent && <span className="text-[10px] font-extrabold bg-red-600 text-white px-2 py-0.5 rounded-full">⚡ URGENT</span>}
            <CompteRebours echeance={tache.echeance} statut={tache.statut} />
            <PuceClient client={client} />
            {camp && !client && <span className="text-[10px] font-bold uppercase px-2 py-0.5 rounded-full bg-gray-100 text-gray-600">{camp.nom}</span>}
            {tache.source === 'auto' && <span className="text-[10px] uppercase tracking-wider border border-dashed border-gray-300 text-gray-400 px-1.5 rounded-full">Auto</span>}
          </div>
          <h4 className={`text-[15px] font-bold leading-snug ${fait ? 'line-through text-gray-500' : 'text-gray-900'}`}>{tache.titre}</h4>
          {tache.contexte && <p className="text-[13px] text-gray-500 mt-0.5 line-clamp-2">{tache.contexte}</p>}
        </div>
      </div>
      {etapes.length > 0 && (
        <div className="space-y-1.5">
          <div className="flex items-center gap-2">
            <div className="flex-1 h-2 bg-gray-100 rounded-full overflow-hidden">
              <div className={`h-full rounded-full ${nbFaites === etapes.length ? 'bg-emerald-500' : 'bg-gradient-to-r from-blue-500 to-violet-500'}`} style={{ width: `${(nbFaites / etapes.length) * 100}%` }} />
            </div>
            <span className="text-[11px] font-bold text-gray-500 tabular-nums">{nbFaites}/{etapes.length}</span>
          </div>
          {etapes.map((e, i) => (
            <label key={i} className="group/etape flex items-start gap-2.5 text-[13.5px] py-0.5" onClick={(ev) => ev.stopPropagation()}>
              {onEtapes && (
                <Fleches className="hidden md:inline-flex -my-1 -ml-1 opacity-0 group-hover/etape:opacity-100"
                  onMonter={i > 0 ? (ev) => { ev.preventDefault(); onEtapes(tache, echanger(etapes, i, -1)) } : null}
                  onDescendre={i < etapes.length - 1 ? (ev) => { ev.preventDefault(); onEtapes(tache, echanger(etapes, i, 1)) } : null} />
              )}
              <input type="checkbox" className="mt-0.5 w-4 h-4 accent-emerald-600" checked={!!e.fait} onChange={() => onEtape(tache, i)} />
              <span className={`flex-1 ${e.fait ? 'line-through text-gray-400' : 'text-gray-800'}`}>{e.texte}</span>
              {e.date && <span className="text-[11px] text-gray-400">{formatQuand(e.date + 'T12:00:00')}</span>}
            </label>
          ))}
        </div>
      )}
      {tache.liens?.length > 0 && <div className="flex flex-wrap gap-1.5">{tache.liens.map((l, i) => <Lien key={i} lien={l} />)}</div>}
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <Avatar membre={tache.assigne} />
          {tache.note && <span className="text-[12px] font-semibold text-gray-600">{tache.note}</span>}
        </div>
        <div className="flex items-center gap-1" onClick={(e) => e.stopPropagation()}>
          {tache.statut !== 'fait' ? (
            <button onClick={() => onDeplacer(tache, 'fait')}
              className="text-xs font-bold px-3 py-1.5 rounded-full bg-emerald-600 hover:bg-emerald-700 text-white">✓ Fait</button>
          ) : (
            <button onClick={() => onDeplacer(tache, 'a_faire')} className="text-xs font-semibold px-3 py-1.5 rounded-full border border-gray-300 text-gray-500">Rouvrir</button>
          )}
          {tache.statut === 'a_faire' && (
            <button onClick={() => onDeplacer(tache, 'en_cours')} className="text-xs font-semibold px-3 py-1.5 rounded-full bg-amber-100 text-amber-800 hover:bg-amber-200">En cours</button>
          )}
        </div>
      </div>
    </article>
  )
}

/* ---------- Vue principale ---------- */
export default function TachesDashboard({ currentUser, role }) {
  const moi = ROLE_VERS_MEMBRE[role] || null
  const [taches, setTaches] = useState([])
  const [campagnes, setCampagnes] = useState([])
  const [chargement, setChargement] = useState(true)
  const [erreur, setErreur] = useState(null)
  const [filtre, setFiltre] = useState(() => {
    try { return localStorage.getItem('taches_filtre') || (moi ? 'moi' : 'equipe') } catch { return 'equipe' }
  })
  const [recherche, setRecherche] = useState('')
  const [colMobile, setColMobile] = useState('a_faire')
  const [edition, setEdition] = useState(null)
  const [vue, setVue] = useState(() => { try { return localStorage.getItem('taches_vue') || 'echeancier' } catch { return 'echeancier' } })
  const [jourChoisi, setJourChoisi] = useState(null)
  const [voirFaits, setVoirFaits] = useState(false)
  useEffect(() => { try { localStorage.setItem('taches_vue', vue) } catch {} }, [vue])

  useEffect(() => { try { localStorage.setItem('taches_filtre', filtre) } catch {} }, [filtre])

  const charger = useCallback(async () => {
    try {
      const [t, c] = await Promise.all([api(''), api('/campagnes')])
      setTaches(t.taches || [])
      setCampagnes(c.campagnes || [])
      setErreur(null)
    } catch (e) {
      setErreur(e.message)
    } finally {
      setChargement(false)
    }
  }, [])
  useEffect(() => { charger() }, [charger])

  const remplacer = (t) => setTaches((xs) => xs.map((x) => (x.id === t.id ? t : x)))

  const modifier = async (tache, changements) => {
    const avant = tache
    remplacer({ ...tache, ...changements })
    try {
      remplacer(await api(`/${tache.id}`, { method: 'PATCH', body: JSON.stringify(changements) }))
    } catch (e) {
      remplacer(avant)
      alert(`Modification non enregistrée : ${e.message}`)
    }
  }
  const creer = async (data) => {
    try {
      const t = await api('', { method: 'POST', body: JSON.stringify({ assigne: moi, ...data, cree_par: moi }) })
      setTaches((xs) => [...xs, t])
    } catch (e) {
      alert(`Tâche non créée : ${e.message}`)
    }
  }
  const supprimer = async (tache) => {
    setTaches((xs) => xs.filter((x) => x.id !== tache.id))
    setEdition(null)
    try { await api(`/${tache.id}`, { method: 'DELETE' }) } catch (e) { alert(`Suppression échouée : ${e.message}`); charger() }
  }
  const enregistrer = async (f) => {
    if (edition.id) {
      const changements = { ...f }
      if (changements.statut === edition.statut) delete changements.statut  // ne pas réinitialiser fait_le
      await modifier(edition, changements)
    } else {
      await creer(f)
    }
    setEdition(null)
  }
  const reordonner = async (liste) => {
    const ordres = Object.fromEntries(liste.map((t, k) => [t.id, (k + 1) * 10]))
    setTaches((xs) => xs.map((x) => (x.id in ordres ? { ...x, ordre: ordres[x.id] } : x)))
    try {
      await api('/ordre', { method: 'POST', body: JSON.stringify({ ids: liste.map((t) => t.id) }) })
    } catch (e) {
      alert(`Ordre non enregistré : ${e.message}`)
      charger()
    }
  }
  const basculerEtape = (tache, i) => {
    const etapes = (tache.etapes || []).map((e, j) => (j === i ? { ...e, fait: !e.fait, date: !e.fait ? new Date().toISOString().slice(0, 10) : null } : e))
    modifier(tache, { etapes })
  }

  const correspond = (t) => {
    if (!recherche.trim()) return true
    const q = recherche.toLowerCase()
    return [t.titre, t.contexte, t.note, ...(t.etapes || []).map((e) => e.texte)].some((s) => (s || '').toLowerCase().includes(q))
  }
  const slugs = useMemo(() => new Set(campagnes.map((c) => c.slug)), [campagnes])
  const tableau = taches.filter((t) => !(t.campagne && slugs.has(t.campagne)))
    .filter((t) => filtre === 'equipe' || !moi || t.assigne === moi)
    .filter(correspond)
  // Échéancier : toutes les tâches (campagnes comprises), classées par urgence de date
  const pourMoi = taches.filter((t) => filtre === 'equipe' || !moi || t.assigne === moi).filter(correspond)
  const ouvertes = pourMoi.filter((t) => t.statut !== 'fait')
    .filter((t) => !jourChoisi || (jourChoisi === 'retard' ? joursAvant(t.echeance) < 0 : (t.echeance || '').slice(0, 10) === jourChoisi))
  const parBande = (id) => ouvertes.filter((t) => bandeDe(t) === id).sort(trierUrgence)
  const faitesRecentes = pourMoi.filter((t) => t.statut === 'fait').sort((a, b) => (b.fait_le || '').localeCompare(a.fait_le || '')).slice(0, 12)
  const nbRetard = ouvertes.filter((t) => bandeDe(t) === 'retard').length
  const nbUrgent = ouvertes.filter((t) => t.urgent).length
  const nbSemaine = ouvertes.filter((t) => ['auj', 'semaine'].includes(bandeDe(t))).length

  const parColonne = (id) => {
    const xs = tableau.filter((t) => t.statut === id)
    return id === 'fait' ? xs.sort((a, b) => (b.fait_le || '').localeCompare(a.fait_le || '')) : xs.sort(trierUrgence)
  }

  if (chargement) return <div className="p-8 text-gray-500">Chargement des tâches…</div>

  return (
    <div className="max-w-7xl mx-auto px-4 py-5">
      <header className="flex flex-wrap items-center justify-between gap-3 mb-5">
        <div>
          <h2 className="text-3xl font-semibold text-gray-900 tracking-tight">Tâches</h2>
          <div className="text-[11px] uppercase tracking-widest text-gray-400 font-semibold mt-1">Piano Technique Montréal</div>
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          <input className="border border-gray-200 rounded-full px-4 py-2 text-sm w-48 focus:outline-none focus:border-blue-500" placeholder="Rechercher…"
            value={recherche} onChange={(e) => setRecherche(e.target.value)} />
          {moi && (
            <div className="flex bg-white border border-gray-200 rounded-full p-0.5">
              {[['moi', 'Mes tâches'], ['equipe', "Toute l'équipe"]].map(([k, l]) => (
                <button key={k} onClick={() => setFiltre(k)}
                  className={`px-3.5 py-1.5 rounded-full text-sm font-medium ${filtre === k ? 'bg-blue-600 text-white' : 'text-gray-500'}`}>{l}</button>
              ))}
            </div>
          )}
          <button className="bg-blue-600 hover:bg-blue-700 text-white font-semibold text-sm px-4 py-2 rounded-lg"
            onClick={() => setEdition({ statut: 'a_faire', assigne: moi })}>+ Nouvelle tâche</button>
        </div>
      </header>

      {erreur && (
        <div className="mb-4 p-3 rounded-lg bg-red-50 text-red-700 text-sm flex justify-between">
          <span>{erreur}</span>
          <button className="underline" onClick={charger}>Réessayer</button>
        </div>
      )}

      {campagnes.length > 0 && (
        <>
          <h3 className="text-xs font-bold uppercase tracking-wider text-gray-500 mb-3 flex items-center gap-2">
            Campagnes <span className="bg-white border border-gray-200 rounded-full px-2 text-[11px]">{campagnes.length}</span>
          </h3>
          <section className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-7 items-start">
            {campagnes.map((c) => (
              <CarteCampagne key={c.slug} campagne={c} moi={moi}
                elements={taches.filter((t) => t.campagne === c.slug).filter(correspond)}
                onCycle={(t) => modifier(t, { statut: SUIVANT[t.statut] })}
                onOuvrir={setEdition}
                onAjouter={creer}
                onReordonner={reordonner} />
            ))}
          </section>
        </>
      )}

      <div className="flex flex-wrap items-center justify-between gap-3 mb-3">
        <div className="flex bg-white border border-gray-200 rounded-xl p-1 shadow-sm">
          {[['echeancier', '📅 Échéancier'], ['statut', '🗂️ Par statut']].map(([k, l]) => (
            <button key={k} onClick={() => setVue(k)}
              className={`px-4 py-2 rounded-lg text-sm font-bold ${vue === k ? 'bg-gradient-to-r from-blue-600 to-violet-600 text-white shadow' : 'text-gray-500'}`}>{l}</button>
          ))}
        </div>
        <div className="flex gap-2 text-xs font-bold">
          {nbRetard > 0 && <span className="px-3 py-1.5 rounded-full bg-red-600 text-white">🔴 {nbRetard} en retard</span>}
          {nbUrgent > 0 && <span className="px-3 py-1.5 rounded-full bg-red-100 text-red-700">⚡ {nbUrgent} urgent{nbUrgent > 1 ? 's' : ''}</span>}
          <span className="px-3 py-1.5 rounded-full bg-yellow-100 text-yellow-800">🟡 {nbSemaine} cette semaine</span>
        </div>
      </div>

      {vue === 'echeancier' ? (
        <>
          <BandeCalendrier taches={pourMoi} jourChoisi={jourChoisi} onChoisir={setJourChoisi} />
          {jourChoisi && (
            <button onClick={() => setJourChoisi(null)} className="mb-3 text-sm font-semibold text-blue-700 bg-blue-50 px-3 py-1.5 rounded-full">
              ✕ {jourChoisi === 'retard' ? 'Tâches en retard seulement' : `Tâches du ${parseDate(jourChoisi).toLocaleDateString('fr-CA', { weekday: 'long', day: 'numeric', month: 'long' })}`} — tout afficher
            </button>
          )}
          <div className="space-y-5">
            {BANDES.map((b) => {
              const cartes = parBande(b.id)
              if (cartes.length === 0) return null
              return (
                <section key={b.id} className={`${b.fond} rounded-2xl p-3 md:p-4`}>
                  <div className="flex items-center gap-2 mb-3 px-1">
                    <span className={`w-1.5 h-6 rounded-full ${b.filet}`} />
                    <span className={`text-base font-extrabold ${b.titre}`}>{b.emoji} {b.nom}</span>
                    <span className="text-xs font-bold bg-white rounded-full px-2.5 py-0.5 text-gray-600 shadow-sm">{cartes.length}</span>
                  </div>
                  <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
                    {cartes.map((t) => (
                      <CarteTache key={t.id} tache={t} campagnes={campagnes} onOuvrir={setEdition}
                        onDeplacer={(tt, statut) => statut && modifier(tt, { statut })} onEtape={basculerEtape} onEtapes={(tt, etapes) => modifier(tt, { etapes })} />
                    ))}
                  </div>
                </section>
              )
            })}
            {ouvertes.length === 0 && (
              <div className="text-center py-10 text-gray-400">
                <div className="text-4xl mb-2">🎉</div>Rien à faire {jourChoisi ? 'ce jour-là' : 'pour l\'instant'}.
              </div>
            )}
            <button className="w-full border-2 border-dashed border-gray-300 hover:border-blue-500 hover:text-blue-600 text-gray-400 rounded-xl py-3 text-sm font-semibold"
              onClick={() => setEdition({ statut: 'a_faire', assigne: moi, echeance: jourChoisi && jourChoisi !== 'retard' ? jourChoisi : '' })}>+ Ajouter une tâche</button>
            {faitesRecentes.length > 0 && (
              <section>
                <button onClick={() => setVoirFaits(!voirFaits)} className="text-sm font-bold text-emerald-700 mb-2">
                  {voirFaits ? '▾' : '▸'} ✅ Fait récemment ({faitesRecentes.length})
                </button>
                {voirFaits && (
                  <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
                    {faitesRecentes.map((t) => (
                      <CarteTache key={t.id} tache={t} campagnes={campagnes} onOuvrir={setEdition}
                        onDeplacer={(tt, statut) => statut && modifier(tt, { statut })} onEtape={basculerEtape} onEtapes={(tt, etapes) => modifier(tt, { etapes })} />
                    ))}
                  </div>
                )}
              </section>
            )}
          </div>
        </>
      ) : (
        <>
          <div className="flex md:hidden gap-1 mb-3 bg-white border border-gray-200 rounded-xl p-1">
            {COLONNES.map((c) => (
              <button key={c.id} onClick={() => setColMobile(c.id)}
                className={`flex-1 py-2.5 rounded-lg text-sm font-semibold ${colMobile === c.id ? 'bg-blue-50 text-blue-700' : 'text-gray-500'}`}>
                {c.nom} · {parColonne(c.id).length}
              </button>
            ))}
          </div>
          <main className="grid grid-cols-1 md:grid-cols-3 gap-4 items-start">
            {COLONNES.map((c) => {
              const cartes = parColonne(c.id)
              return (
                <section key={c.id} className={`${c.fond} rounded-2xl p-3 min-h-[200px] ${colMobile === c.id ? 'block' : 'hidden'} md:block`}>
                  <div className="flex items-center gap-2 px-1 pb-3">
                    <span className="text-[13px] font-bold uppercase tracking-wider text-gray-900">{c.nom}</span>
                    <span className="text-xs bg-white border border-gray-200 rounded-full px-2 font-semibold text-gray-500">{cartes.length}</span>
                  </div>
                  <div className="flex flex-col gap-2.5">
                    {cartes.map((t) => (
                      <CarteTache key={t.id} tache={t} campagnes={campagnes} onOuvrir={setEdition}
                        onDeplacer={(tt, statut) => statut && modifier(tt, { statut })} onEtape={basculerEtape} onEtapes={(tt, etapes) => modifier(tt, { etapes })} />
                    ))}
                  </div>
                </section>
              )
            })}
          </main>
        </>
      )}

      {edition && (
        <ModaleTache tache={edition} campagnes={campagnes}
          onFermer={() => setEdition(null)} onEnregistrer={enregistrer} onSupprimer={supprimer} />
      )}
    </div>
  )
}
