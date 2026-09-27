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
  const da = joursAvant(a.echeance)
  const db = joursAvant(b.echeance)
  if (da === null && db === null) return (a.created_at || '').localeCompare(b.created_at || '')
  if (da === null) return 1
  if (db === null) return -1
  return da - db
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

/* ---------- Formulaire d'édition (modale) ---------- */
function ModaleTache({ tache, campagnes, onFermer, onEnregistrer, onSupprimer }) {
  const [f, setF] = useState(() => ({
    titre: tache.titre || '', contexte: tache.contexte || '', statut: tache.statut || 'a_faire',
    assigne: tache.assigne || '', echeance: tache.echeance || '', campagne: tache.campagne || '',
    note: tache.note || '', etapes: tache.etapes || [], liens: tache.liens || [],
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
        <input className={champ} placeholder="Note courte (ex. « +2 j », « facturé 7340 »)" value={f.note} onChange={(e) => maj('note', e.target.value)} />

        <div>
          <div className="text-xs font-bold uppercase tracking-wider text-gray-500 mb-1">Étapes</div>
          {f.etapes.map((et, i) => (
            <div key={i} className="flex items-center gap-2 mb-1">
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
function CarteCampagne({ campagne, elements, moi, onCycle, onOuvrir, onAjouter }) {
  const [ouverte, setOuverte] = useState(true)
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
    return ordre[a.statut] - ordre[b.statut] || trierUrgence(a, b)
  })

  return (
    <article className="bg-white border border-gray-200 rounded-2xl p-4 shadow-sm flex flex-col gap-3">
      <div className="flex justify-between items-start gap-3 cursor-pointer" onClick={() => setOuverte(!ouverte)}>
        <div>
          <h3 className="text-xl font-semibold text-gray-900 leading-tight">{campagne.nom}</h3>
          <div className="text-xs text-gray-500 mt-1">{campagne.sous_titre}</div>
          <div className="text-[11px] text-gray-400 mt-0.5">{campagne.contacts}</div>
        </div>
        <div className="text-right flex-shrink-0">
          <div className="text-lg font-bold tabular-nums">{faits} / {elements.length}</div>
          <div className="text-[10px] uppercase tracking-wider text-gray-400 font-bold">Faits {ouverte ? '▾' : '▸'}</div>
        </div>
      </div>

      {ouverte && (
        <>
          <div className="border-t border-gray-100">
            {tries.length === 0 && <div className="text-sm text-gray-400 py-2">Aucun élément pour l'instant.</div>}
            {tries.map((t) => {
              const ech = formatEcheance(t.echeance, t.statut)
              const meta = t.note || ech.texte
              return (
                <div key={t.id} className="grid grid-cols-[18px_1fr_auto] gap-2 items-center py-2 border-b border-gray-100 text-sm">
                  <PastilleEtat statut={t.statut} onClick={() => onCycle(t)} />
                  <button className={`text-left truncate ${t.statut === 'fait' ? 'line-through text-gray-400' : 'text-gray-900 font-medium'}`} onClick={() => onOuvrir(t)}>
                    {t.titre}
                    {t.source === 'auto' && <span className="ml-2 text-[9px] uppercase tracking-wider border border-dashed border-gray-300 text-gray-400 px-1 rounded">auto</span>}
                  </button>
                  <span className={`text-xs whitespace-nowrap flex items-center gap-2 ${t.note ? (t.statut === 'en_cours' ? 'text-amber-700 font-semibold' : 'text-gray-500') : ech.ton}`}>
                    {meta}
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
              <div key={c.id} className="grid grid-cols-[24px_1fr] gap-2 py-2 border-b border-gray-100 last:border-0">
                <Avatar membre={membreDepuisNom(c.author_name)} petit />
                <div className="min-w-0">
                  <div className="text-[11.5px] text-gray-500">
                    <span className="text-gray-900 font-semibold text-xs mr-2">{c.author_name}</span>
                    {formatQuand(c.posted_at)} · {c.conversation_subject}
                  </div>
                  <div className="text-[13px] text-gray-800 whitespace-pre-line line-clamp-3">{c.text}</div>
                </div>
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
    </article>
  )
}

/* ---------- Carte tâche ---------- */
function CarteTache({ tache, onOuvrir, onDeplacer, onEtape }) {
  const ech = formatEcheance(tache.echeance, tache.statut)
  const etapes = tache.etapes || []
  const nbFaites = etapes.filter((e) => e.fait).length
  const idx = COLONNES.findIndex((c) => c.id === tache.statut)
  const fait = tache.statut === 'fait'
  return (
    <article onClick={() => onOuvrir(tache)}
      className={`bg-white border border-gray-200 rounded-xl p-3.5 shadow-sm hover:shadow-md transition cursor-pointer flex flex-col gap-2.5 ${fait ? 'opacity-75' : ''}`}>
      <div className="flex justify-between items-start gap-2">
        <h4 className={`text-[15px] font-semibold leading-snug ${fait ? 'line-through text-gray-500' : 'text-gray-900'}`}>{tache.titre}</h4>
        {tache.source === 'auto' && <span className="text-[10px] uppercase tracking-wider border border-dashed border-gray-300 text-gray-400 px-1.5 rounded-full">Auto</span>}
      </div>
      {tache.contexte && <p className="text-[13px] text-gray-500">{tache.contexte}</p>}
      {etapes.length > 0 && (
        <div className="space-y-1.5">
          {etapes.length > 2 && (
            <div>
              <div className="flex justify-between text-[10.5px] uppercase tracking-wider text-gray-400 font-semibold"><span>Progression</span><span>{nbFaites} / {etapes.length}</span></div>
              <div className="h-1.5 bg-gray-100 rounded-full overflow-hidden"><div className="h-full bg-blue-600 rounded-full" style={{ width: `${(nbFaites / etapes.length) * 100}%` }} /></div>
            </div>
          )}
          {etapes.map((e, i) => (
            <label key={i} className="flex items-start gap-2 text-[13.5px]" onClick={(ev) => ev.stopPropagation()}>
              <input type="checkbox" className="mt-1" checked={!!e.fait} onChange={() => onEtape(tache, i)} />
              <span className={`flex-1 ${e.fait ? 'line-through text-gray-400' : 'text-gray-800'}`}>{e.texte}</span>
              {e.date && <span className="text-[11px] text-gray-400">{formatQuand(e.date + 'T12:00:00')}</span>}
            </label>
          ))}
        </div>
      )}
      {tache.liens?.length > 0 && <div className="flex flex-wrap gap-1.5">{tache.liens.map((l, i) => <Lien key={i} lien={l} />)}</div>}
      <div className="flex items-center justify-between gap-2">
        <Avatar membre={tache.assigne} />
        <div className="flex items-center gap-2">
          <span className={`text-[12.5px] ${ech.ton}`}>{ech.texte}</span>
          <div className="flex" onClick={(e) => e.stopPropagation()}>
            <button disabled={idx === 0} title="Reculer" onClick={() => onDeplacer(tache, COLONNES[idx - 1]?.id)}
              className="px-1.5 py-0.5 text-gray-400 hover:text-gray-800 disabled:opacity-20">◀</button>
            <button disabled={idx === COLONNES.length - 1} title="Avancer" onClick={() => onDeplacer(tache, COLONNES[idx + 1]?.id)}
              className="px-1.5 py-0.5 text-gray-400 hover:text-gray-800 disabled:opacity-20">▶</button>
          </div>
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
                onAjouter={creer} />
            ))}
          </section>
        </>
      )}

      <h3 className="text-xs font-bold uppercase tracking-wider text-gray-500 mb-3 flex items-center gap-2">
        Tâches <span className="bg-white border border-gray-200 rounded-full px-2 text-[11px]">{tableau.length}</span>
      </h3>

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
                  <CarteTache key={t.id} tache={t} onOuvrir={setEdition}
                    onDeplacer={(tt, statut) => statut && modifier(tt, { statut })}
                    onEtape={basculerEtape} />
                ))}
                {c.id === 'a_faire' && (
                  <button className="border-2 border-dashed border-gray-300 hover:border-blue-500 hover:text-blue-600 text-gray-400 rounded-xl py-3 text-sm font-medium"
                    onClick={() => setEdition({ statut: 'a_faire', assigne: moi })}>+ Ajouter une tâche</button>
                )}
              </div>
            </section>
          )
        })}
      </main>

      {edition && (
        <ModaleTache tache={edition} campagnes={campagnes}
          onFermer={() => setEdition(null)} onEnregistrer={enregistrer} onSupprimer={supprimer} />
      )}
    </div>
  )
}
