import React from 'react'

export default function ExportButton({ data, filename, label = "Exporter" }) {
  const handleExport = () => {
    // Logique d'export simple (CSV)
    if (!data || data.length === 0) {
      alert('Aucune donnée à exporter')
      return
    }
    
    // Convertir en CSV
    const headers = Object.keys(data[0])
    const csv = [
      headers.join(','),
      ...data.map(row => headers.map(header => row[header] || '').join(','))
    ].join('\n')
    
    // Télécharger
    const blob = new Blob([csv], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = filename || 'export.csv'
    a.click()
    URL.revokeObjectURL(url)
  }
  
  return (
    <button
      onClick={handleExport}
      className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
    >
      {label}
    </button>
  )
}
