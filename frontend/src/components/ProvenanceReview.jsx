import React, { useEffect, useState } from 'react'
import { API_URL } from '../utils/apiConfig'

/**
 * ProvenanceReview — « Comment nous ont-ils connus ? »
 * Propositions de « Référé par » déduites des indices (fiche, factures, historique, courriels).
 * Rien n'est écrit dans Gazelle sans « Approuver ».
 */
const ETIQUETTES = { a_decider: 'À décider', approuve: 'Approuvé', a_discuter: 'À discuter', refuse: 'Refusé' }
const COULEURS = { haute: 'bg-green-100 text-green-800', moyenne: 'bg-yellow-100 text-yellow-800', basse: 'bg-gray-100 text-gray-700' }

export default function ProvenanceReview() {
  const [etat, setEtat] = useState(null)
  const [filtre, setFiltre] = useState('a_decider')
  const [valeurs, setValeurs] = useState({})
  const [notes, setNotes] = useState({})
  const [enCours, setEnCours] = useState(null)
  const [erreur, setErreur] = useState('')

  const charger = async () => {
    try {
      const r = await fetch(`${API_URL}/api/provenance/survol`)
      if (r.ok) setEtat(await r.json())
    } catch (e) {
      setErreur('Impossible de charger le survol.')
    }
  }

  useEffect(() => {
    charger()
  }, [])

  useEffect(() => {
    if (etat?.statut !== 'en cours') return undefined
    const t = setInterval(charger, 10000)
    return () => clearInterval(t)
  }, [etat?.statut])

  const relancer = async () => {
    await fetch(`${API_URL}/api/provenance/survol`, { method: 'POST' })
    setEtat({ ...(etat || {}), statut: 'en cours' })
  }

  const decider = async (p, decision) => {
    setEnCours(p.client_id)
    setErreur('')
    try {
      const r = await fetch(`${API_URL}/api/provenance/decision`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          client_id: p.client_id,
          decision,
          note: notes[p.client_id] || '',
          valeur: valeurs[p.client_id] ?? p.refere_par,
        }),
      })
      if (!r.ok) {
        const d = await r.json().catch(() => ({}))
        setErreur(`${p.nom} : ${d.detail || 'erreur'}`)
      }
      await charger()
    } finally {
      setEnCours(null)
    }
  }

  const props = etat?.propositions || []
  const visibles = props.filter((p) => filtre === 'tous' || p.statut === filtre)
  const compte = (s) => props.filter((p) => p.statut === s).length

  return (
    <div className="max-w-5xl mx-auto p-4 space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h2 className="text-xl font-semibold">Comment nous ont-ils connus ?</h2>
          <p className="text-sm text-gray-600">
            {etat?.statut === 'en cours'
              ? 'Survol en cours… (quelques minutes)'
              : etat?.fin
                ? `${etat.sans_provenance} clients sans « Référé par » · ${etat.avec_indices} avec des indices · ${props.length} propositions`
                : 'Aucun survol encore.'}
          </p>
        </div>
        <button onClick={relancer} disabled={etat?.statut === 'en cours'}
          className="px-3 py-2 text-sm rounded-lg bg-gray-100 hover:bg-gray-200 disabled:opacity-50">
          Relancer le survol
        </button>
      </div>

      <div className="flex flex-wrap gap-2 text-sm">
        {['a_decider', 'a_discuter', 'approuve', 'refuse', 'tous'].map((s) => (
          <button key={s} onClick={() => setFiltre(s)}
            className={`px-3 py-1 rounded-full ${filtre === s ? 'bg-blue-600 text-white' : 'bg-gray-100'}`}>
            {s === 'tous' ? `Tous (${props.length})` : `${ETIQUETTES[s]} (${compte(s)})`}
          </button>
        ))}
      </div>

      {erreur && <div className="p-2 rounded bg-red-50 text-red-700 text-sm">{erreur}</div>}

      {visibles.map((p) => (
        <div key={p.client_id} className="border rounded-lg p-3 bg-white flex flex-col md:flex-row gap-3">
          <div className="flex-1 min-w-0 space-y-1">
            <div className="flex flex-wrap items-center gap-2">
              <span className="font-medium">{p.nom}</span>
              <span className={`text-xs px-2 py-0.5 rounded ${COULEURS[p.confiance] || COULEURS.basse}`}>
                confiance {p.confiance}
              </span>
              {p.statut !== 'a_decider' && <span className="text-xs text-gray-500">{ETIQUETTES[p.statut]}</span>}
            </div>
            <label className="text-sm text-gray-600 flex items-center gap-2">
              Référé par
              <input className="border rounded px-2 py-1 text-sm flex-1 min-w-0"
                value={valeurs[p.client_id] ?? p.refere_par}
                onChange={(e) => setValeurs({ ...valeurs, [p.client_id]: e.target.value })} />
            </label>
            {p.preuve && <p className="text-sm italic text-gray-700">« {p.preuve} »</p>}
            <details className="text-xs text-gray-500">
              <summary className="cursor-pointer">Indices ({p.indices?.length || 0})</summary>
              <ul className="list-disc ml-4 mt-1 space-y-1">
                {(p.indices || []).map((x, i) => <li key={i} className="break-words">{x}</li>)}
              </ul>
            </details>
          </div>
          <div className="md:w-56 flex flex-col gap-2">
            <button disabled={enCours === p.client_id || p.statut === 'approuve'} onClick={() => decider(p, 'approuver')}
              className="px-3 py-1.5 text-sm rounded bg-green-600 text-white disabled:opacity-50">Approuver</button>
            <button disabled={enCours === p.client_id} onClick={() => decider(p, 'discuter')}
              className="px-3 py-1.5 text-sm rounded bg-yellow-100 text-yellow-900 disabled:opacity-50">À discuter</button>
            <button disabled={enCours === p.client_id} onClick={() => decider(p, 'refuser')}
              className="px-3 py-1.5 text-sm rounded bg-gray-100 disabled:opacity-50">Refuser</button>
            <input placeholder="Note (facultatif)" className="border rounded px-2 py-1 text-sm"
              value={notes[p.client_id] ?? p.note ?? ''}
              onChange={(e) => setNotes({ ...notes, [p.client_id]: e.target.value })} />
          </div>
        </div>
      ))}
      {etat?.fin && visibles.length === 0 && <p className="text-sm text-gray-500">Rien dans cette catégorie.</p>}
    </div>
  )
}
