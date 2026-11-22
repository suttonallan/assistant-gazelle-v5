import { useState, useEffect, useCallback } from 'react'
import { API_URL } from '../utils/apiConfig'

// 🔧 Suivi des outils et de l'équipement partagés : qui a pris quoi.
// Chaque outil porte une étiquette QR ; la scanner ouvre l'appli sur l'outil
// (paramètre ?o=<numéro>) avec deux gros boutons : « Je le prends » / « Je le rapporte ».

const MOI = { admin: 'allan', nick: 'nicolas', jeanphilippe: 'jean-philippe', margot: 'margot', louise: 'louise' }
const GESTION = ['admin', 'nick', 'louise']

async function appel(chemin, options = {}) {
  let derniere
  for (let essai = 0; essai < 4; essai++) {  // le serveur Render peut dormir au premier appel
    try {
      const r = await fetch(`${API_URL}/api/outils${chemin}`, {
        ...options,
        headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
      })
      if (r.ok) return chemin.endsWith('.svg') ? r.text() : r.json()
      const d = await r.json().catch(() => ({}))
      derniere = new Error(d.detail || `Erreur ${r.status}`)
      if (r.status < 500) break
    } catch (e) { derniere = e }
    await new Promise((ok) => setTimeout(ok, 2500 * (essai + 1)))
  }
  throw derniere
}

const depuis = (iso) => {
  if (!iso) return ''
  const d = new Date(iso)
  return d.toLocaleDateString('fr-CA', { day: 'numeric', month: 'short', timeZone: 'America/Montreal' }) +
    ' ' + d.toLocaleTimeString('fr-CA', { hour: '2-digit', minute: '2-digit', timeZone: 'America/Montreal' })
}

function telecharger(nom, texte) {
  const url = URL.createObjectURL(new Blob([texte], { type: 'image/svg+xml' }))
  const a = document.createElement('a')
  a.href = url; a.download = nom; a.click()
  setTimeout(() => URL.revokeObjectURL(url), 2000)
}

// ─── Fiche plein écran ouverte par le QR ─────────────────────────
export function OutilScan({ oid, role, onFermer }) {
  const [o, setO] = useState(null)
  const [erreur, setErreur] = useState(null)
  const [occupe, setOccupe] = useState(false)
  const [fait, setFait] = useState(null)
  const moi = MOI[role]

  useEffect(() => {
    appel(`/${oid}`).then(setO).catch((e) => setErreur(e.message))
  }, [oid])

  const agir = async (action) => {
    setOccupe(true); setErreur(null)
    try {
      const d = await appel(`/${oid}/${action}`, { method: 'POST', body: JSON.stringify({}) })
      setO(d)
      setFait(action === 'prendre' ? 'C’est noté : vous l’avez.' : 'C’est noté : rapporté à l’atelier.')
      setTimeout(onFermer, 1800)
    } catch (e) { setErreur(e.message) } finally { setOccupe(false) }
  }

  const aMoi = o && o.detenteur === moi
  return (
    <div className="fixed inset-0 z-[2000] bg-black/50 flex items-end sm:items-center justify-center">
      <div className="bg-white w-full sm:max-w-md rounded-t-2xl sm:rounded-2xl p-6 shadow-xl">
        <div className="flex justify-between items-start mb-4">
          <div className="text-xs text-gray-500">🔧 Outil PTM-{oid}</div>
          <button onClick={onFermer} className="text-gray-400 text-xl leading-none">×</button>
        </div>
        {!o && !erreur && <p className="text-gray-500 py-8 text-center">Chargement… (le serveur se réveille parfois)</p>}
        {o && (
          <>
            <h2 className="text-2xl font-semibold text-gray-900">{o.nom}</h2>
            <p className="text-sm text-gray-500 mb-4">{o.categorie}</p>
            <p className="mb-6">
              Actuellement : <b>{aMoi ? 'chez vous' : o.detenteur_nom}</b>
              <span className="text-gray-500 text-sm"> depuis le {depuis(o.depuis)}</span>
            </p>
            {fait ? (
              <p className="text-green-700 font-medium text-center text-lg py-4">✓ {fait}</p>
            ) : (
              <div className="space-y-3">
                {!aMoi && (
                  <button disabled={occupe} onClick={() => agir('prendre')}
                    className="w-full py-4 rounded-xl bg-blue-600 text-white text-lg font-semibold disabled:opacity-50">
                    Je le prends
                  </button>
                )}
                {o.detenteur !== 'atelier' && (
                  <button disabled={occupe} onClick={() => agir('rapporter')}
                    className={`w-full py-4 rounded-xl text-lg font-semibold disabled:opacity-50 ${aMoi ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-800'}`}>
                    Je le rapporte à l’atelier
                  </button>
                )}
              </div>
            )}
          </>
        )}
        {erreur && <p className="text-red-600 text-sm mt-4">{erreur}</p>}
      </div>
    </div>
  )
}

// ─── Volet « Outils » ───────────────────────────────────────────
export default function OutilsDashboard({ role }) {
  const [outils, setOutils] = useState([])
  const [personnes, setPersonnes] = useState({})
  const [filtre, setFiltre] = useState('tous')
  const [charge, setCharge] = useState(false)
  const [erreur, setErreur] = useState(null)
  const [ouvert, setOuvert] = useState(null)
  const [choisis, setChoisis] = useState(new Set())
  const [lot, setLot] = useState('')
  const [taille, setTaille] = useState(15)
  const [message, setMessage] = useState(null)
  const moi = MOI[role]
  const gestion = GESTION.includes(role)

  const charger = useCallback(() => {
    appel('').then((d) => { setOutils(d.outils || []); setPersonnes(d.personnes || {}); setCharge(true) })
      .catch((e) => { setErreur(e.message); setCharge(true) })
  }, [])
  useEffect(() => { charger() }, [charger])

  const visibles = outils.filter((o) =>
    filtre === 'tous' ? true : filtre === 'moi' ? o.detenteur === moi : o.detenteur === filtre)

  const ajouterLot = async () => {
    // Une ligne par outil : « Catégorie ; Nom » ou simplement « Nom »
    const liste = lot.split('\n').map((l) => l.trim()).filter(Boolean).map((l) => {
      const [a, b] = l.split(/[;\t]/).map((x) => x.trim())
      return b ? { categorie: a, nom: b } : { nom: a }
    })
    if (!liste.length) return
    try {
      const d = await appel('', { method: 'POST', body: JSON.stringify(liste) })
      setMessage(`${d.crees.length} outil(s) ajouté(s)${d.ignores ? `, ${d.ignores} déjà présent(s)` : ''}.`)
      setLot(''); charger()
    } catch (e) { setMessage(e.message) }
  }

  const etiquettes = async () => {
    const ids = [...choisis].join(',')
    try {
      const svg = await appel(`/etiquettes/planche.svg?taille_mm=${taille}${ids ? `&ids=${ids}` : ''}`)
      telecharger(`etiquettes-outils-${taille}mm.svg`, svg)
    } catch (e) { setMessage(e.message) }
  }

  const basculer = (id) => setChoisis((s) => { const n = new Set(s); n.has(id) ? n.delete(id) : n.add(id); return n })

  const parCategorie = visibles.reduce((acc, o) => { (acc[o.categorie] ||= []).push(o); return acc }, {})

  return (
    <div className="max-w-4xl mx-auto p-4">
      <div className="flex flex-wrap items-center justify-between gap-2 mb-4">
        <h1 className="text-xl font-semibold">🔧 Outils et équipement</h1>
        <select value={filtre} onChange={(e) => setFiltre(e.target.value)} className="border rounded-lg px-3 py-2 text-sm">
          <option value="tous">Tous ({outils.length})</option>
          {moi && <option value="moi">Chez moi ({outils.filter((o) => o.detenteur === moi).length})</option>}
          <option value="atelier">À l’atelier ({outils.filter((o) => o.detenteur === 'atelier').length})</option>
          {Object.entries(personnes).filter(([k]) => k !== moi).map(([k, v]) => (
            <option key={k} value={k}>Chez {v} ({outils.filter((o) => o.detenteur === k).length})</option>
          ))}
        </select>
      </div>
      <p className="text-sm text-gray-500 mb-4">Scannez l’étiquette QR d’un outil avec l’appareil photo du téléphone pour le prendre ou le rapporter.</p>

      {!charge && <p className="text-gray-500">Chargement…</p>}
      {erreur && <p className="text-red-600 text-sm mb-4">{erreur}</p>}
      {charge && !outils.length && !erreur && (
        <p className="text-gray-600 bg-gray-50 rounded-lg p-4 mb-4">Aucun outil suivi pour l’instant.{gestion ? ' Ajoutez-les ci-dessous.' : ''}</p>
      )}

      {Object.entries(parCategorie).map(([cat, liste]) => (
        <div key={cat} className="mb-5">
          <h2 className="text-sm font-semibold text-gray-500 uppercase mb-2">{cat}</h2>
          <div className="bg-white rounded-lg border divide-y">
            {liste.map((o) => (
              <div key={o.id} className="flex items-center gap-3 px-3 py-2">
                {gestion && <input type="checkbox" checked={choisis.has(o.id)} onChange={() => basculer(o.id)} title="Choisir pour les étiquettes" />}
                <button onClick={() => setOuvert(o.id)} className="flex-1 text-left">
                  <div className="font-medium">{o.nom} <span className="text-xs text-gray-400">PTM-{o.id}</span></div>
                  <div className="text-xs text-gray-500">
                    {o.detenteur === moi ? 'Chez moi' : o.detenteur_nom} · depuis le {depuis(o.depuis)}
                  </div>
                </button>
                <span className={`text-xs px-2 py-1 rounded-full ${o.detenteur === 'atelier' ? 'bg-green-50 text-green-700' : 'bg-amber-50 text-amber-700'}`}>
                  {o.detenteur === 'atelier' ? 'Atelier' : o.detenteur_nom}
                </span>
              </div>
            ))}
          </div>
        </div>
      ))}

      {gestion && (
        <div className="mt-8 grid gap-4 sm:grid-cols-2">
          <div className="bg-white border rounded-lg p-4">
            <h3 className="font-semibold mb-2">Ajouter des outils</h3>
            <p className="text-xs text-gray-500 mb-2">Une ligne par outil : « Catégorie ; Nom » (ou seulement le nom).</p>
            <textarea value={lot} onChange={(e) => setLot(e.target.value)} rows={5}
              placeholder={'Déménagement ; Lève-piano\nRéglage ; Jeu de gabarits Steinway'}
              className="w-full border rounded-lg p-2 text-sm font-mono" />
            <button onClick={ajouterLot} className="mt-2 px-4 py-2 rounded-lg bg-blue-600 text-white text-sm">Ajouter</button>
          </div>
          <div className="bg-white border rounded-lg p-4">
            <h3 className="font-semibold mb-2">Étiquettes QR pour le graveur laser</h3>
            <p className="text-xs text-gray-500 mb-2">
              Fichier SVG vectoriel, à la vraie taille (s’ouvre dans LightBurn).
              {choisis.size ? ` ${choisis.size} outil(s) coché(s).` : ' Cochez des outils, sinon tous.'}
            </p>
            <label className="text-sm">Taille du code : <input type="number" min="8" max="40" value={taille}
              onChange={(e) => setTaille(Number(e.target.value) || 15)} className="border rounded px-2 py-1 w-16" /> mm</label>
            <div><button onClick={etiquettes} className="mt-3 px-4 py-2 rounded-lg bg-gray-800 text-white text-sm">Télécharger les étiquettes</button></div>
          </div>
        </div>
      )}
      {message && <p className="text-sm text-gray-700 mt-3">{message}</p>}

      {ouvert && <OutilScan oid={ouvert} role={role} onFermer={() => { setOuvert(null); charger() }} />}
    </div>
  )
}
