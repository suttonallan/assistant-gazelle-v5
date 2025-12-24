import { useState } from 'react'
import ClientDetailsModal from './ClientDetailsModal'

export default function ClickableMessage({
  content,
  entities = [],
  currentUser,
  onAskQuestion,
  onSelectClient
}) {
  const [selectedClientId, setSelectedClientId] = useState(null)

  // Si pas d'entités, afficher le contenu normalement
  if (!entities || entities.length === 0) {
    return <div className="whitespace-pre-wrap">{content}</div>
  }

  // Remplacer les noms de clients par des liens cliquables
  let displayContent = content
  entities.forEach(entity => {
    // Échapper les caractères spéciaux pour la regex
    const escapedName = entity.name.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
    // Chercher le nom en gras (**nom**) ou juste le nom
    const regex = new RegExp(`\\*\\*${escapedName}\\*\\*`, 'g')
    displayContent = displayContent.replace(
      regex,
      `<a href="#" data-client-id="${entity.id}" class="text-blue-600 hover:text-blue-800 font-bold underline cursor-pointer">${entity.name}</a>`
    )
  })

  const handleClick = (e) => {
    e.preventDefault()
    const clientId = e.target.getAttribute('data-client-id')
    if (clientId) {
      // Définir le contexte client pour les questions de suivi
      if (onSelectClient) {
        const entity = entities.find(e => e.id === clientId)
        if (entity) {
          onSelectClient(entity)
        }
      }
      setSelectedClientId(clientId)
    }
  }

  return (
    <>
      <div
        className="whitespace-pre-wrap"
        dangerouslySetInnerHTML={{ __html: displayContent }}
        onClick={handleClick}
      />
      {selectedClientId && (
        <ClientDetailsModal
          clientId={selectedClientId}
          onClose={() => setSelectedClientId(null)}
          onAskQuestion={onAskQuestion}
        />
      )}
    </>
  )
}
