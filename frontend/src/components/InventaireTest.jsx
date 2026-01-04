import { useState, useEffect } from 'react'

import { API_URL } from '../utils/apiConfig'

function InventaireTest() {
  const [catalogue, setCatalogue] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    const fetchData = async () => {
      try {
        console.log('🔍 Fetching from:', `${API_URL}/inventaire/catalogue`)

        const response = await fetch(`${API_URL}/inventaire/catalogue`)

        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`)
        }

        const data = await response.json()
        console.log('✅ Data received:', data)

        setCatalogue(data.produits || [])
        setLoading(false)
      } catch (err) {
        console.error('❌ Error:', err)
        setError(err.message)
        setLoading(false)
      }
    }

    fetchData()
  }, [])

  if (loading) {
    return (
      <div style={{ padding: '20px', textAlign: 'center' }}>
        <h2>🔄 Chargement...</h2>
      </div>
    )
  }

  if (error) {
    return (
      <div style={{ padding: '20px', backgroundColor: '#fee', border: '2px solid #f00' }}>
        <h2>❌ Erreur</h2>
        <p>{error}</p>
        <p>API URL: {API_URL}</p>
      </div>
    )
  }

  return (
    <div style={{ padding: '20px', fontFamily: 'Arial, sans-serif' }}>
      <h1>📦 Test Inventaire Simplifié</h1>

      <div style={{ marginBottom: '20px', padding: '10px', backgroundColor: '#e8f5e9', border: '1px solid #4caf50' }}>
        <strong>✅ Connexion API réussie !</strong>
        <br />
        Total produits: {catalogue.length}
      </div>

      <table style={{ width: '100%', borderCollapse: 'collapse', border: '1px solid #ddd' }}>
        <thead style={{ backgroundColor: '#f5f5f5' }}>
          <tr>
            <th style={{ padding: '10px', border: '1px solid #ddd', textAlign: 'left' }}>Code</th>
            <th style={{ padding: '10px', border: '1px solid #ddd', textAlign: 'left' }}>Nom</th>
            <th style={{ padding: '10px', border: '1px solid #ddd', textAlign: 'left' }}>Catégorie</th>
            <th style={{ padding: '10px', border: '1px solid #ddd', textAlign: 'right' }}>Prix</th>
          </tr>
        </thead>
        <tbody>
          {catalogue.slice(0, 20).map((produit, index) => (
            <tr key={produit.id || index} style={{ backgroundColor: index % 2 === 0 ? '#fff' : '#f9f9f9' }}>
              <td style={{ padding: '8px', border: '1px solid #ddd' }}>{produit.code_produit}</td>
              <td style={{ padding: '8px', border: '1px solid #ddd' }}>{produit.nom}</td>
              <td style={{ padding: '8px', border: '1px solid #ddd' }}>{produit.categorie || 'N/A'}</td>
              <td style={{ padding: '8px', border: '1px solid #ddd', textAlign: 'right' }}>
                {produit.prix_unitaire?.toFixed(2) || '0.00'} $
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      {catalogue.length > 20 && (
        <p style={{ marginTop: '10px', color: '#666' }}>
          ... et {catalogue.length - 20} autres produits
        </p>
      )}
    </div>
  )
}

export default InventaireTest
