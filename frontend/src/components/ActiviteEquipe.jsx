import React, { useEffect, useState } from 'react'
import { API_URL } from '../utils/apiConfig'

/** Qui utilise l'app, et comment (Google ou NIP). Visible par Allan seulement. */
const NOMS = { allan: 'Allan', nick: 'Nicolas', nicolas: 'Nicolas', louise: 'Louise', margot: 'Margot', jp: 'Jean-Philippe' }
const EQUIPE = ['allan', 'nick', 'louise', 'margot', 'jp']

export default function ActiviteEquipe() {
  const [ouvert, setOuvert] = useState(false)
  const [act, setAct] = useState(null)
  const [erreur, setErreur] = useState(null)

  useEffect(() => {
    if (!ouvert || act) return
    fetch(`${API_URL}/api/auth/activite`)
      .then(async (r) => { const d = await r.json(); if (!r.ok) throw new Error(d.detail || r.status); setAct(d.activite || {}) })
      .catch((e) => setErreur(String(e.message || e)))
  }, [ouvert, act])

  return (
    <div className="mb-6">
      <button type="button" onClick={() => setOuvert((v) => !v)}
        className="text-xs px-3 py-1.5 rounded-full bg-white border border-gray-300 text-gray-600 hover:bg-gray-100">
        👥 Connexions de l’équipe {ouvert ? '▲' : '▼'}
      </button>
      {ouvert && (
        <div className="mt-2 bg-white border border-gray-200 rounded-lg text-sm">
          {erreur && <div className="px-3 py-2 text-red-600">⚠️ {erreur}</div>}
          {!erreur && !act && <div className="px-3 py-2 text-gray-500">Chargement…</div>}
          {act && EQUIPE.map((k) => {
            const e = act[k] || (k === 'nick' ? act.nicolas : null)
            return (
              <div key={k} className="flex justify-between px-3 py-2 border-b border-gray-100 last:border-b-0">
                <span className="font-medium text-gray-800">{NOMS[k]}</span>
                <span className="text-right text-gray-600">
                  {!e ? <span className="text-gray-400">Aucune activité notée</span> : (
                    <>
                      {e.google_le ? <span className="text-emerald-700">✅ Google ({e.google_le})</span> : <span className="text-amber-700">Pas encore Google</span>}
                      {e.pin_le && <span className="text-gray-400"> · NIP {e.pin_le}</span>}
                    </>
                  )}
                </span>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
