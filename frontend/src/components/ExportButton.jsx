/**
 * Composant React pour exporter les données du catalogue en CSV/Excel
 * 
 * Utilisation:
 *   <ExportButton 
 *     data={catalogue} 
 *     filename="catalogue_produits"
 *     columns={['code_produit', 'nom', 'categorie', 'prix_unitaire']}
 *   />
 */

import { useState } from 'react'

const ExportButton = ({ 
  data = [], 
  filename = 'export', 
  columns = null,
  className = '' 
}) => {
  const [exporting, setExporting] = useState(false)

  // Colonnes par défaut si non spécifiées
  const defaultColumns = [
    'code_produit',
    'nom',
    'categorie',
    'description',
    'unite_mesure',
    'prix_unitaire',
    'fournisseur',
    'has_commission',
    'commission_rate',
    'variant_group',
    'variant_label',
    'display_order',
    'is_active'
  ]

  const exportColumns = columns || defaultColumns

  /**
   * Convertit les données en CSV
   */
  const convertToCSV = (data, columns) => {
    if (!data || data.length === 0) {
      return ''
    }

    // En-têtes
    const headers = columns.map(col => {
      // Noms d'affichage plus lisibles
      const headerNames = {
        'code_produit': 'Code Produit',
        'nom': 'Nom',
        'categorie': 'Catégorie',
        'description': 'Description',
        'unite_mesure': 'Unité',
        'prix_unitaire': 'Prix Unitaire',
        'fournisseur': 'Fournisseur',
        'has_commission': 'Avec Commission',
        'commission_rate': 'Taux Commission (%)',
        'variant_group': 'Groupe Variantes',
        'variant_label': 'Label Variante',
        'display_order': 'Ordre Affichage',
        'is_active': 'Actif'
      }
      return headerNames[col] || col
    })

    // Lignes de données
    const rows = data.map(item => {
      return columns.map(col => {
        let value = item[col]
        
        // Formater les valeurs
        if (value === null || value === undefined) {
          value = ''
        } else if (typeof value === 'boolean') {
          value = value ? 'Oui' : 'Non'
        } else if (typeof value === 'number') {
          // Garder les nombres tels quels (Excel les reconnaîtra)
          value = value
        } else {
          // Échapper les guillemets et virgules dans les chaînes
          value = String(value).replace(/"/g, '""')
          if (value.includes(',') || value.includes('"') || value.includes('\n')) {
            value = `"${value}"`
          }
        }
        return value
      })
    })

    // Combiner en-têtes et données
    const csvContent = [
      headers.join(','),
      ...rows.map(row => row.join(','))
    ].join('\n')

    return csvContent
  }

  /**
   * Télécharge le fichier CSV
   */
  const downloadCSV = () => {
    if (!data || data.length === 0) {
      alert('Aucune donnée à exporter')
      return
    }

    setExporting(true)

    try {
      const csv = convertToCSV(data, exportColumns)
      
      // Créer un Blob avec BOM UTF-8 pour Excel
      const BOM = '\uFEFF'
      const blob = new Blob([BOM + csv], { type: 'text/csv;charset=utf-8;' })
      
      // Créer un lien de téléchargement
      const link = document.createElement('a')
      const url = URL.createObjectURL(blob)
      
      link.setAttribute('href', url)
      link.setAttribute('download', `${filename}_${new Date().toISOString().split('T')[0]}.csv`)
      link.style.visibility = 'hidden'
      
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      
      // Libérer l'URL
      setTimeout(() => URL.revokeObjectURL(url), 100)
      
    } catch (error) {
      console.error('Erreur lors de l\'export:', error)
      alert('Erreur lors de l\'export: ' + error.message)
    } finally {
      setExporting(false)
    }
  }

  return (
    <button
      onClick={downloadCSV}
      disabled={exporting || !data || data.length === 0}
      className={`
        px-4 py-2 rounded-lg font-medium transition-colors
        ${exporting || !data || data.length === 0
          ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
          : 'bg-green-600 text-white hover:bg-green-700 active:bg-green-800'
        }
        ${className}
      `}
      title={!data || data.length === 0 ? 'Aucune donnée à exporter' : 'Exporter en CSV'}
    >
      {exporting ? (
        <>
          <span className="inline-block animate-spin mr-2">⏳</span>
          Export en cours...
        </>
      ) : (
        <>
          📥 Exporter CSV ({data?.length || 0} produits)
        </>
      )}
    </button>
  )
}

export default ExportButton
