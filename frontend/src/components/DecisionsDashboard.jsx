import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { API_URL } from '../utils/apiConfig'

/**
 * 🗳️ Décisions — points à trancher par Allan et Nicolas.
 * Même format que les anciens panneaux : avant/après, Approuver / À discuter / Refuser, note.
 * Unanimes → décision prise ; divergence ou « À discuter » → à discuter.
 * Le statut est calculé par le serveur ; la page ne fait qu'afficher et envoyer les votes.
 */

const NOMS = { allan: 'Allan', nicolas: 'Nicolas' }
const LIBELLE_VOTE = { ok: 'Approuvé', talk: 'À discuter', no: 'Refusé' }
const STATUT = {
  en_attente: { nom: 'En attente', cls: 'bg-gray-100 text-gray-700 border-gray-300' },
  a_discuter: { nom: 'À discuter', cls: 'bg-amber-50 text-amber-800 border-amber-400' },
  approuvee: { nom: 'Décision prise : approuvée', cls: 'bg-green-50 text-green-800 border-green-500' },
  refusee: { nom: 'Décision prise : refusée', cls: 'bg-red-50 text-red-800 border-red-400' },
}
const BTN = {
  ok: { nom: 'Approuver', actif: 'bg-green-50 border-green-600 text-green-700' },
  talk: { nom: 'À discuter', actif: 'bg-amber-50 border-amber-500 text-amber-800' },
  no: { nom: 'Refuser', actif: 'bg-red-50 border-red-500 text-red-700' },
}
const RETARD_JOURS = 7

const moiDe = (u) => {
  const e = (u?.email || '').toLowerCase()
  if (e.startsWith('asutton')) return 'allan'
  if (e.startsWith('nlessard')) return 'nicolas'
  return null
}
const joursDepuis = (iso) => {
  if (!iso) return null
  const t = Date.parse(iso)
  return Number.isNaN(t) ? null : Math.floor((Date.now() - t) / 86400000)
}
const dateCourte = (iso) => {
  if (!iso) return ''
  try { return new Date(iso).toLocaleDateString('fr-CA', { day: 'numeric', month: 'short' }) } catch { return '' }
}

function AvantApres({ avant, apres }) {
  return (
    <>
      {avant && (
        <p className="grid grid-cols-[52px_1fr] gap-2 mb-1">
          <span className="text-[11px] uppercase tracking-wide text-gray-500 font-semibold pt-0.5">Avant</span>
          <span className="text-gray-500 min-w-0 break-words whitespace-pre-line">{avant}</span>
        </p>
      )}
      {apres && (
        <p className="grid grid-cols-[52px_1fr] gap-2 mb-1">
          <span className="text-[11px] uppercase tracking-wide font-semibold pt-0.5" style={{ color: '#b8860b' }}>Après</span>
          <span className="min-w-0 break-words whitespace-pre-line">{apres}</span>
        </p>
      )}
    </>
  )
}

function Point({ d, num, moi, onVote, onNote, enCours }) {
  const votants = d.votants || []
  const monVote = d.votes?.[moi]?.s || ''
  const [note, setNote] = useState(d.votes?.[moi]?.note || '')
  const tape = useRef(false)
  const minuterie = useRef(null)
  // Une note qui arrive du serveur ne doit pas écraser ce que la personne est en train d'écrire.
  useEffect(() => { if (!tape.current) setNote(d.votes?.[moi]?.note || '') }, [d.votes, moi])
  const peutVoter = moi && votants.includes(moi)
  const seul = votants.length === 1 ? NOMS[votants[0]] : null
  const st0 = STATUT[d.statut] || STATUT.en_attente
  const st = seul && (d.statut === 'approuvee' || d.statut === 'refusee')
    ? { ...st0, nom: `${d.statut === 'approuvee' ? 'Approuvé' : 'Refusé'} par ${seul}` }
    : seul && d.statut === 'en_attente' ? { ...st0, nom: `À trancher par ${seul}` } : st0
  const attente = d.statut === 'en_attente' || d.statut === 'a_discuter' ? joursDepuis(d.created_at) : null
  const enRetard = attente !== null && attente >= RETARD_JOURS
  const autres = votants.filter((p) => p !== moi)

  const changerNote = (v) => {
    tape.current = true
    setNote(v)
    clearTimeout(minuterie.current)
    minuterie.current = setTimeout(() => { tape.current = false; onNote(d, v) }, 900)
  }

  return (
    <div className={`grid grid-cols-[30px_1fr] md:grid-cols-[34px_1fr_auto] gap-x-3.5 gap-y-1.5 py-3 border-b border-stone-200 ${d.question ? 'bg-amber-50/30' : ''}`}>
      <div className="text-gray-500 font-semibold tabular-nums pt-0.5">{num}</div>
      <div className="min-w-0">
        <p className="font-semibold mb-1">{d.titre}</p>
        {d.question && <p className="mb-1 text-[14px] font-semibold" style={{ color: '#b8860b' }}>Question : {d.question}</p>}
        {d.type === 'revision_wp' && Array.isArray(d.changements) && d.changements.length > 0 ? (
          d.changements.map((c, i) => (
            <div key={i} className={i ? 'border-t border-dashed border-stone-200 pt-1 mt-1' : ''}>
              <AvantApres avant={c[0]} apres={c[1]} />
            </div>
          ))
        ) : (
          <AvantApres avant={d.avant} apres={d.apres} />
        )}
        {d.info && <p className="mt-1 text-[13px] text-amber-800 whitespace-pre-line">{d.info}</p>}
        {d.consigne && <p className="mt-1 text-[13px] text-green-700 font-semibold">{d.consigne}</p>}
        {d.recommandation && <p className="mt-1 text-[13px] text-green-700 font-semibold">Recommandation : {d.recommandation}</p>}
        <div className="flex flex-wrap gap-x-2.5 gap-y-1 mt-1.5 text-[12.5px] text-gray-500">
          <span className={`px-1.5 py-0.5 rounded border text-[12px] font-semibold ${st.cls}`}>{st.nom}</span>
          {d.page && <span>{d.page}</span>}
          {attente !== null && attente > 0 && (
            <span className={enRetard ? 'text-red-700 font-semibold' : ''}>En attente depuis {attente} j</span>
          )}
          {d.decidee_le && (d.statut === 'approuvee' || d.statut === 'refusee') && <span>Décidée le {dateCourte(d.decidee_le)}</span>}
          {d.lien && <a className="font-semibold hover:underline" style={{ color: '#b8860b' }} href={d.lien} target="_blank" rel="noopener noreferrer">Voir sur le site ↗</a>}
        </div>
        {d.type === 'revision_wp' && d.lien_wp && (
          <a href={d.lien_wp} target="_blank" rel="noopener noreferrer"
             className="inline-block mt-2 text-[13.5px] font-semibold text-white px-3 py-1.5 rounded-md"
             style={{ background: '#b8860b' }}>
            Ouvrir dans WordPress{d.rid ? ` (révision ${d.rid})` : ''} ↗
          </a>
        )}
        {/* Votes de l'autre personne */}
        {autres.map((p) => {
          const v = d.votes?.[p]
          return (
            <p key={p} className="mt-1.5 text-[13px]">
              <span className="font-semibold">{NOMS[p]} :</span>{' '}
              {v?.s ? <span className={v.s === 'ok' ? 'text-green-700' : v.s === 'no' ? 'text-red-700' : 'text-amber-800'}>{LIBELLE_VOTE[v.s]}</span>
                : <span className="text-gray-500">pas encore voté</span>}
              {v?.note ? <span className="text-gray-700"> — « {v.note} »</span> : null}
            </p>
          )
        })}
        {d.suite && <p className="mt-1.5 text-[13px] text-gray-700"><span className="font-semibold">Suite :</span> {d.suite}{d.realisee_le ? ` (fait le ${dateCourte(d.realisee_le)})` : ''}</p>}
      </div>
      {peutVoter ? (
        <div className="col-start-2 md:col-start-auto flex flex-wrap md:flex-nowrap gap-1 self-start">
          {['ok', 'talk', 'no'].map((s) => (
            <button key={s} type="button" disabled={enCours}
              onClick={() => onVote(d, monVote === s ? '' : s)}
              aria-pressed={monVote === s}
              className={`text-[12.5px] font-semibold border rounded-md px-2.5 py-1.5 whitespace-nowrap disabled:opacity-50 ${
                monVote === s ? BTN[s].actif : 'bg-white border-stone-300 text-gray-500 hover:bg-stone-50'}`}>
              {monVote === s ? `✓ ${LIBELLE_VOTE[s]}` : BTN[s].nom}
            </button>
          ))}
        </div>
      ) : <div className="hidden md:block" />}
      {peutVoter && (
        <div className="col-start-2 md:col-span-2">
          <textarea rows={1} value={note} onChange={(e) => changerNote(e.target.value)}
            placeholder={d.question || 'Note (facultatif)'}
            className={`w-full text-[13.5px] border rounded-md px-2 py-1.5 resize-y min-h-[34px] bg-white ${d.question ? 'border-amber-500' : 'border-stone-300'}`} />
          {/* Une note seule ne tranche pas : le dire, sinon le point reste « à trancher » sans qu'on comprenne pourquoi. */}
          {note.trim() && !monVote && (d.statut === 'en_attente' || d.statut === 'a_discuter') && (
            <p className="mt-1 text-[12.5px] font-semibold text-amber-800">
              Note enregistrée — clique Approuver, À discuter ou Refuser pour trancher.
            </p>
          )}
        </div>
      )}
    </div>
  )
}

export default function DecisionsDashboard({ currentUser }) {
  const moi = moiDe(currentUser)
  const [liste, setListe] = useState([])
  const [charge, setCharge] = useState(true)
  const [erreur, setErreur] = useState('')
  const [etat, setEtat] = useState('')
  const [filtre, setFiltre] = useState('moi')
  const [enCours, setEnCours] = useState(null)

  const charger = useCallback(async () => {
    try {
      const r = await fetch(`${API_URL}/api/decisions`)
      if (!r.ok) throw new Error((await r.json().catch(() => ({})))?.detail || `Erreur ${r.status}`)
      const d = await r.json()
      setListe(d.decisions || [])
      setErreur('')
    } catch (e) {
      setErreur(String(e.message || e))
    } finally {
      setCharge(false)
    }
  }, [])

  useEffect(() => {
    charger()
    const t = setInterval(charger, 30000) // voir arriver les votes de l'autre
    return () => clearInterval(t)
  }, [charger])

  const envoyer = async (d, corps) => {
    setEnCours(d.id)
    try {
      const r = await fetch(`${API_URL}/api/decisions/${d.id}/vote`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(corps),
      })
      if (!r.ok) throw new Error((await r.json().catch(() => ({})))?.detail || `Erreur ${r.status}`)
      const maj = await r.json()
      setListe((l) => l.map((x) => (x.id === d.id ? { ...x, ...maj } : x)))
      setEtat('Enregistré.')
    } catch (e) {
      setEtat(`Échec de l'enregistrement : ${e.message || e}. Réessaie.`)
    } finally {
      setEnCours(null)
    }
  }

  const comptes = useMemo(() => {
    const c = { moi: 0, autre: 0, a_discuter: 0, approuvee: 0, refusee: 0 }
    for (const d of liste) {
      if (d.mineur && !(d.votants || []).includes(moi)) continue
      const ouvert = d.statut === 'en_attente' || d.statut === 'a_discuter'
      if (ouvert && moi && (d.votants || []).includes(moi) && !d.votes?.[moi]?.s) c.moi++
      if (ouvert && moi && (d.votes?.[moi]?.s || !(d.votants || []).includes(moi))) c.autre++
      if (c[d.statut] !== undefined && d.statut !== 'en_attente') c[d.statut]++
    }
    return c
  }, [liste, moi])

  const visibles = useMemo(() => liste.filter((d) => {
    // Détail mineur (coquille, espace…) : seulement pour qui le tranche ; les autres le voient dans le rapport hebdo.
    if (d.mineur && !(d.votants || []).includes(moi)) return false
    if (filtre === 'tous') return true
    if (filtre === 'moi') return (d.statut === 'en_attente' || d.statut === 'a_discuter') && moi && (d.votants || []).includes(moi) && !d.votes?.[moi]?.s
    if (filtre === 'autre') return (d.statut === 'en_attente' || d.statut === 'a_discuter') && moi && (d.votes?.[moi]?.s || !(d.votants || []).includes(moi))
    return d.statut === filtre
  }), [liste, filtre, moi])

  // Regroupement : sujet → groupe, dans l'ordre reçu du serveur
  const sections = useMemo(() => {
    const out = []
    for (const d of visibles) {
      let s = out.find((x) => x.sujet === d.sujet)
      if (!s) { s = { sujet: d.sujet, groupes: [] }; out.push(s) }
      const g = d.type === 'revision_wp' ? 'Révisions WordPress à approuver' : (d.groupe || '')
      let gr = s.groupes.find((x) => x.nom === g)
      if (!gr) { gr = { nom: g, items: [] }; s.groupes.push(gr) }
      gr.items.push(d)
    }
    return out
  }, [visibles])

  const FILTRES = [
    ['moi', `À trancher par moi (${comptes.moi})`],
    ['autre', `En attente de l'autre (${comptes.autre})`],
    ['a_discuter', `À discuter (${comptes.a_discuter})`],
    ['approuvee', `Approuvées (${comptes.approuvee})`],
    ['refusee', `Refusées (${comptes.refusee})`],
    ['tous', 'Tous'],
  ]

  if (!moi) {
    return <div className="max-w-3xl mx-auto p-6 text-gray-600">Le volet Décisions est réservé à Allan et Nicolas.</div>
  }

  let num = 0
  return (
    <div className="max-w-5xl mx-auto px-4 py-6" style={{ fontSize: 15, lineHeight: 1.45 }}>
      <h1 className="text-2xl font-bold mb-1">🗳️ Décisions</h1>
      <p className="text-gray-600 mb-2 max-w-[70ch]">
        <b>Approuver</b> : on le fait. <b>À discuter</b> : on en parle avant de toucher à quoi que ce soit. <b>Refuser</b> : on n'y touche pas.
        Quand {moi === 'allan' ? 'Nicolas et toi' : 'Allan et toi'} êtes d'accord, la décision est prise. Si vos choix diffèrent, le point passe à « À discuter ».
      </p>
      <div className="sticky top-0 z-10 bg-white/95 backdrop-blur border-b border-stone-200 py-2.5 mb-2 flex flex-wrap gap-1">
        {FILTRES.map(([id, nom]) => (
          <button key={id} type="button" onClick={() => setFiltre(id)} aria-pressed={filtre === id}
            className={`text-[13px] border rounded-md px-2.5 py-1 ${filtre === id ? 'border-amber-600 bg-amber-50' : 'border-stone-300 bg-white hover:bg-stone-50'}`}>
            {nom}
          </button>
        ))}
      </div>
      <p className="text-[12px] text-gray-500 min-h-[1em]" aria-live="polite">{etat}</p>
      {charge && <p className="text-gray-500 py-5">Chargement…</p>}
      {erreur && <p className="text-red-700 py-3">Impossible de charger les décisions : {erreur}</p>}
      {!charge && !erreur && sections.length === 0 && (
        <p className="text-gray-500 py-5">{filtre === 'moi' ? 'Rien à trancher pour toi. 🎉' : 'Aucun point dans cette catégorie.'}</p>
      )}
      {sections.map((s) => (
        <section key={s.sujet} className="mb-6">
          <h2 className="text-lg font-bold mt-6 mb-1">{s.sujet}</h2>
          {s.groupes.map((g) => (
            <div key={g.nom || '_'}>
              {g.nom && <h3 className="text-[13px] uppercase tracking-wider font-semibold mt-5 mb-1" style={{ color: '#b8860b' }}>{g.nom}</h3>}
              {g.items.map((d) => {
                num += 1
                return (
                  <Point key={d.id} d={d} num={num} moi={moi} enCours={enCours === d.id}
                    onVote={(x, s2) => envoyer(x, { s: s2 })}
                    onNote={(x, n) => envoyer(x, { note: n })} />
                )
              })}
            </div>
          ))}
        </section>
      ))}
    </div>
  )
}
