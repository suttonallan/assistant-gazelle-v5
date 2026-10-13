import { useState } from 'react'
import { API_URL } from '../../utils/apiConfig'

/**
 * Frais partagés — tournée avec plusieurs clients éloignés.
 *
 * Trajet optimisé : domicile du technicien → clients dans le meilleur ordre → retour.
 * La zone gratuite s'applique une seule fois à la tournée ; le total est
 * réparti au prorata de ce que chaque client paierait seul.
 */
const TECHNICIENS = ['Allan', 'Nicolas', 'Jean-Philippe']

const emptyStop = () => ({ label: '', address: '', matches: [], searching: false })

export default function SharedTravelFeeCalculator() {
  const [technician, setTechnician] = useState('Nicolas')
  const [stops, setStops] = useState([emptyStop(), emptyStop()])
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)

  const updateStop = (i, patch) =>
    setStops(prev => prev.map((s, k) => (k === i ? { ...s, ...patch } : s)))

  const searchClient = async (i) => {
    const name = stops[i].label.trim()
    if (!name) return
    updateStop(i, { searching: true, matches: [] })
    try {
      const resp = await fetch(
        `${API_URL}/api/admin/travel-fees/search-client?client_name=${encodeURIComponent(name)}`
      )
      const data = await resp.json()
      const results = data.results || []
      if (results.length === 1) {
        pickClient(i, results[0])
      } else {
        updateStop(i, { searching: false, matches: results })
        if (results.length === 0) alert('Aucun client trouvé — entrez l’adresse à la main.')
      }
    } catch (err) {
      updateStop(i, { searching: false })
      alert('Erreur recherche client : ' + err.message)
    }
  }

  const pickClient = (i, c) =>
    updateStop(i, {
      label: c.client_name,
      address: c.address_full || c.address || c.postal_code || '',
      matches: [],
      searching: false,
    })

  const calculate = async () => {
    const valid = stops.filter(s => s.address.trim())
    if (valid.length < 2) {
      alert('Il faut au moins deux clients avec une adresse.')
      return
    }
    setLoading(true)
    setError(null)
    setResult(null)
    try {
      const resp = await fetch(`${API_URL}/api/admin/travel-fees/shared`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          technician,
          stops: valid.map(s => ({ label: s.label || null, address: s.address })),
        }),
      })
      const data = await resp.json()
      if (!resp.ok) throw new Error(data.detail || `Erreur ${resp.status}`)
      setResult(data)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const money = (v) => `${Number(v).toFixed(2)} $`

  return (
    <div id="frais-partages" className="max-w-3xl mx-auto bg-white rounded-xl shadow-sm border border-gray-200 p-6">
      <h2 className="text-xl font-bold text-gray-800 mb-1">🚗 Frais partagés — plusieurs clients sur la route</h2>
      <p className="text-sm text-gray-500 mb-5">
        Entrez les clients dans n’importe quel ordre : le calcul prend le trajet le plus court.
        La zone gratuite compte une seule fois, et le total est réparti selon ce que chaque
        client paierait seul.
      </p>

      <label className="block text-sm font-medium text-gray-700 mb-1">Technicien</label>
      <select
        value={technician}
        onChange={(e) => setTechnician(e.target.value)}
        className="mb-4 px-3 py-2 border border-gray-300 rounded-lg text-sm"
      >
        {TECHNICIENS.map(t => <option key={t} value={t}>{t}</option>)}
      </select>

      <div className="space-y-3">
        {stops.map((s, i) => (
          <div key={i} className="border border-gray-200 rounded-lg p-3">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-semibold text-gray-700">Client {i + 1}</span>
              {stops.length > 2 && (
                <button
                  type="button"
                  onClick={() => setStops(prev => prev.filter((_, k) => k !== i))}
                  className="text-xs text-gray-400 hover:text-red-600"
                >
                  Retirer ✕
                </button>
              )}
            </div>
            <div className="flex gap-2 mb-2">
              <input
                type="text"
                value={s.label}
                onChange={(e) => updateStop(i, { label: e.target.value })}
                onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); searchClient(i) } }}
                placeholder="Nom du client"
                className="flex-1 px-3 py-2 border border-gray-300 rounded-lg text-sm"
              />
              <button
                type="button"
                onClick={() => searchClient(i)}
                disabled={s.searching}
                className="px-3 py-2 text-sm bg-gray-100 hover:bg-gray-200 rounded-lg disabled:opacity-50"
              >
                {s.searching ? '…' : '🔍 Trouver l’adresse'}
              </button>
            </div>
            {s.matches.length > 0 && (
              <div className="mb-2 border border-gray-200 rounded-lg divide-y">
                {s.matches.map((c, k) => (
                  <button
                    key={k}
                    type="button"
                    onClick={() => pickClient(i, c)}
                    className="w-full text-left px-3 py-2 text-sm hover:bg-blue-50"
                  >
                    <span className="font-medium">{c.client_name}</span>
                    <span className="text-gray-500"> — {c.address_full || c.address || c.postal_code}</span>
                  </button>
                ))}
              </div>
            )}
            <input
              type="text"
              value={s.address}
              onChange={(e) => updateStop(i, { address: e.target.value })}
              placeholder="Adresse ou code postal"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
            />
          </div>
        ))}
      </div>

      <div className="flex gap-2 mt-4">
        <button
          type="button"
          onClick={() => setStops(prev => [...prev, emptyStop()])}
          className="px-4 py-2 text-sm bg-gray-100 hover:bg-gray-200 rounded-lg"
        >
          + Ajouter un client
        </button>
        <button
          type="button"
          onClick={calculate}
          disabled={loading}
          className="px-4 py-2 text-sm bg-blue-600 hover:bg-blue-700 text-white rounded-lg disabled:opacity-50"
        >
          {loading ? 'Calcul…' : 'Calculer le partage'}
        </button>
      </div>

      {error && (
        <div className="mt-4 bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">⚠️ {error}</div>
      )}

      {result && (
        <div className="mt-6">
          {result.degraded_mode && (
            <div className="mb-3 bg-amber-50 border border-amber-200 text-amber-800 px-3 py-2 rounded text-sm">
              ⚠️ Distances estimées (Google Maps indisponible) — vérifier avant de facturer.
            </div>
          )}
          <div className="mb-3 bg-blue-50 border border-blue-200 rounded-lg px-3 py-2 text-sm text-blue-900">
            <b>Trajet optimisé :</b> {result.technician_name} → {result.optimized_order.join(' → ')} → retour
            {result.order_changed && (
              <div className="text-xs text-blue-700 mt-1">
                Dans l’ordre entré, les frais auraient été de {money(result.entered_order_fee)}.
              </div>
            )}
          </div>
          <div className="text-sm text-gray-600 mb-3">
            Tournée de {result.technician_name} : <b>{result.total_km} km</b>, <b>{result.total_minutes} min</b> (aller-retour, tous arrêts).
            Total des frais : <b>{money(result.total_fee)}</b>
            {result.savings > 0 && <> — économie de {money(result.savings)} par rapport à des visites séparées.</>}
          </div>
          <table className="w-full text-sm border border-gray-200 rounded-lg overflow-hidden">
            <thead className="bg-gray-50 text-gray-600">
              <tr>
                <th className="text-left px-3 py-2">Client</th>
                <th className="text-right px-3 py-2">S’il était seul</th>
                <th className="text-right px-3 py-2">À facturer</th>
              </tr>
            </thead>
            <tbody>
              {result.clients.map((c, k) => (
                <tr key={k} className="border-t border-gray-100">
                  <td className="px-3 py-2">{c.label}</td>
                  <td className="px-3 py-2 text-right text-gray-500">{money(c.solo_fee)}</td>
                  <td className="px-3 py-2 text-right font-semibold">{money(c.share)}</td>
                </tr>
              ))}
              <tr className="border-t border-gray-200 bg-gray-50">
                <td className="px-3 py-2 font-medium">Total</td>
                <td className="px-3 py-2 text-right text-gray-500">{money(result.sum_solo_fees)}</td>
                <td className="px-3 py-2 text-right font-bold">{money(result.total_fee)}</td>
              </tr>
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
