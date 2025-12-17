# Instructions pour Cursor: Clients Cliquables dans le Chat

## Contexte
L'API backend a été modifiée pour retourner des données structurées avec les IDs des clients dans `structured_data.clickable_entities`. Il faut maintenant rendre ces clients cliquables dans le frontend.

## Backend Déjà Implémenté ✅

### Modification dans `/api/assistant.py`
- Le endpoint `/assistant/chat` retourne maintenant `structured_data.clickable_entities` pour les recherches de clients
- Chaque entité contient: `id`, `name`, `type` (client/contact), `city`

### Exemple de réponse:
```json
{
  "answer": "🔍 **2 clients trouvés:**\n\n- **Michelle Alie** (Saint-Lambert)\n- **Michelle Sutton** (Montréal)",
  "structured_data": {
    "clickable_entities": [
      {
        "id": "cli_abc123",
        "name": "Michelle Alie",
        "type": "client",
        "city": "Saint-Lambert"
      },
      {
        "id": "cli_xyz789",
        "name": "Michelle Sutton",
        "type": "client",
        "city": "Montréal"
      }
    ]
  }
}
```

## Tâches Frontend pour Cursor

### 1. Modifier `AssistantWidget.jsx` pour Détecter les Entités Cliquables

**Fichier:** `frontend/src/components/AssistantWidget.jsx`

**Dans la fonction `handleSendMessage`**, après avoir reçu la réponse:

```jsx
const assistantMessage = {
  role: 'assistant',
  content: data.answer || "Désolé, je n'ai pas pu traiter votre demande.",
  metadata: {
    query_type: data.query_type,
    confidence: data.confidence,
    // AJOUTER ICI:
    clickable_entities: data.structured_data?.clickable_entities || []
  }
}
```

### 2. Créer un Composant pour Afficher les Messages avec Liens Cliquables

**Nouveau fichier:** `frontend/src/components/ClickableMessage.jsx`

```jsx
import { useState } from 'react'
import ClientDetailsModal from './ClientDetailsModal'

export default function ClickableMessage({ content, entities = [] }) {
  const [selectedClientId, setSelectedClientId] = useState(null)

  // Si pas d'entités, afficher le contenu normalement
  if (!entities || entities.length === 0) {
    return <div className="whitespace-pre-wrap">{content}</div>
  }

  // Remplacer les noms de clients par des liens cliquables
  let displayContent = content
  entities.forEach(entity => {
    const regex = new RegExp(`\\*\\*${entity.name.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}\\*\\*`, 'g')
    displayContent = displayContent.replace(
      regex,
      `<a href="#" data-client-id="${entity.id}" class="text-blue-600 hover:text-blue-800 font-bold underline cursor-pointer">${entity.name}</a>`
    )
  })

  const handleClick = (e) => {
    e.preventDefault()
    const clientId = e.target.getAttribute('data-client-id')
    if (clientId) {
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
        />
      )}
    </>
  )
}
```

### 3. Créer le Modal de Détails Client

**Nouveau fichier:** `frontend/src/components/ClientDetailsModal.jsx`

```jsx
import { useState, useEffect } from 'react'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export default function ClientDetailsModal({ clientId, onClose }) {
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [details, setDetails] = useState(null)

  useEffect(() => {
    const fetchDetails = async () => {
      try {
        setLoading(true)
        const response = await fetch(`${API_URL}/assistant/client/${clientId}`)

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`)
        }

        const data = await response.json()
        setDetails(data)
      } catch (err) {
        console.error('Erreur chargement détails client:', err)
        setError(err.message)
      } finally {
        setLoading(false)
      }
    }

    fetchDetails()
  }, [clientId])

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-xl max-w-4xl w-full max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="sticky top-0 bg-white border-b px-6 py-4 flex justify-between items-center">
          <h2 className="text-xl font-bold">Détails Client</h2>
          <button
            onClick={onClose}
            className="text-gray-500 hover:text-gray-700 text-2xl"
          >
            ×
          </button>
        </div>

        {/* Content */}
        <div className="p-6">
          {loading && (
            <div className="text-center py-8">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
              <p className="mt-4 text-gray-600">Chargement des détails...</p>
            </div>
          )}

          {error && (
            <div className="bg-red-50 border border-red-200 rounded p-4 text-red-800">
              ❌ Erreur: {error}
            </div>
          )}

          {details && (
            <div className="space-y-6">
              {/* Informations principales */}
              <div>
                <h3 className="text-lg font-semibold mb-2">Informations</h3>
                <div className="bg-gray-50 p-4 rounded space-y-2">
                  <p><span className="font-medium">Nom:</span> {details.name}</p>
                  {details.address && <p><span className="font-medium">Adresse:</span> {details.address}</p>}
                  {details.city && <p><span className="font-medium">Ville:</span> {details.city}</p>}
                  {details.postal_code && <p><span className="font-medium">Code postal:</span> {details.postal_code}</p>}
                  {details.phone && <p><span className="font-medium">Téléphone:</span> {details.phone}</p>}
                  {details.email && <p><span className="font-medium">Email:</span> {details.email}</p>}
                </div>
              </div>

              {/* Contacts associés */}
              {details.associated_contacts && details.associated_contacts.length > 0 && (
                <div>
                  <h3 className="text-lg font-semibold mb-2">Contacts Associés</h3>
                  <div className="space-y-2">
                    {details.associated_contacts.map((contact, idx) => (
                      <div key={idx} className="bg-gray-50 p-3 rounded">
                        <p className="font-medium">{contact.name}</p>
                        {contact.role && <p className="text-sm text-gray-600">{contact.role}</p>}
                        {contact.phone && <p className="text-sm">{contact.phone}</p>}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Pianos */}
              {details.pianos && details.pianos.length > 0 && (
                <div>
                  <h3 className="text-lg font-semibold mb-2">Pianos ({details.pianos.length})</h3>
                  <div className="space-y-2">
                    {details.pianos.map((piano, idx) => (
                      <div key={idx} className="bg-gray-50 p-3 rounded">
                        <p className="font-medium">{piano.brand} {piano.model}</p>
                        {piano.serial_number && <p className="text-sm text-gray-600">S/N: {piano.serial_number}</p>}
                        {piano.location && <p className="text-sm">{piano.location}</p>}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Historique de service */}
              {details.service_history && details.service_history.length > 0 && (
                <div>
                  <h3 className="text-lg font-semibold mb-2">Historique de Service ({details.service_history.length})</h3>
                  <div className="space-y-3 max-h-96 overflow-y-auto">
                    {details.service_history.map((note, idx) => (
                      <div key={idx} className="bg-blue-50 p-3 rounded border-l-4 border-blue-400">
                        <p className="text-sm text-gray-700">{note}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Prochains RV */}
              {details.upcoming_appointments && details.upcoming_appointments.length > 0 && (
                <div>
                  <h3 className="text-lg font-semibold mb-2">Prochains Rendez-vous</h3>
                  <div className="space-y-2">
                    {details.upcoming_appointments.map((appt, idx) => (
                      <div key={idx} className="bg-green-50 p-3 rounded">
                        <p className="font-medium">{appt.date} à {appt.time}</p>
                        <p className="text-sm text-gray-600">{appt.title}</p>
                        {appt.assigned_to && <p className="text-sm">Technicien: {appt.assigned_to}</p>}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
```

### 4. Utiliser le Nouveau Composant dans AssistantWidget

**Dans `AssistantWidget.jsx`**, modifier l'affichage des messages:

```jsx
import ClickableMessage from './ClickableMessage'

// Dans le rendu des messages:
{messages.map((message, idx) => (
  <div
    key={idx}
    className={`mb-4 ${message.role === 'user' ? 'text-right' : 'text-left'}`}
  >
    <div
      className={`inline-block max-w-[80%] p-3 rounded-lg ${
        message.role === 'user'
          ? 'bg-blue-600 text-white'
          : 'bg-gray-100 text-gray-900'
      }`}
    >
      {message.role === 'assistant' && message.metadata?.clickable_entities ? (
        <ClickableMessage
          content={message.content}
          entities={message.metadata.clickable_entities}
        />
      ) : (
        <div className="whitespace-pre-wrap">{message.content}</div>
      )}
    </div>
  </div>
))}
```

### 5. Backend - Créer l'Endpoint de Détails Client

**Fichier:** `api/assistant.py`

Ajouter ce nouveau endpoint après le `/chat`:

```python
@router.get("/client/{client_id}")
async def get_client_details(client_id: str):
    """
    Récupère les détails complets d'un client/contact pour affichage dans le modal.

    Utilise le même format que train_summaries.py (le plus fourni).
    """
    try:
        queries = get_queries()

        # Rechercher le client/contact
        results = queries.search_clients([client_id])

        if not results or len(results) == 0:
            raise HTTPException(status_code=404, detail="Client non trouvé")

        entity = results[0]
        source = entity.get('_source', 'client')

        # Informations de base
        details = {
            'id': entity.get('id'),
            'type': source,
            'name': entity.get('company_name') if source == 'client' else f"{entity.get('first_name', '')} {entity.get('last_name', '')}".strip(),
            'address': entity.get('address', ''),
            'city': entity.get('city', ''),
            'postal_code': entity.get('postal_code', ''),
            'phone': entity.get('phone', ''),
            'email': entity.get('email', '')
        }

        # Contacts associés (pour les clients uniquement)
        if source == 'client':
            details['associated_contacts'] = entity.get('associated_contacts', [])

        # Pianos
        details['pianos'] = entity.get('pianos', [])

        # Historique de service (toutes les notes)
        details['service_history'] = entity.get('service_history_notes', [])

        # Prochains rendez-vous
        details['upcoming_appointments'] = entity.get('upcoming_appointments', [])

        return details

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Erreur dans /assistant/client/{client_id}: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
```

## Résumé des Changements

### Backend ✅ (Déjà fait par Claude)
- Modifié `_format_response()` pour retourner dict avec `text` et `entities`
- Ajouté `structured_data.clickable_entities` dans la réponse du chat
- Besoin d'ajouter l'endpoint `/assistant/client/{id}`

### Frontend (À faire par Cursor)
1. ✅ Capturer `clickable_entities` dans les métadonnées des messages
2. ✅ Créer `ClickableMessage.jsx` pour rendre les noms cliquables
3. ✅ Créer `ClientDetailsModal.jsx` pour afficher les détails
4. ✅ Modifier `AssistantWidget.jsx` pour utiliser `ClickableMessage`

## Test
1. Démarrer le backend: `uvicorn api.main:app --reload`
2. Démarrer le frontend: `cd frontend && npm run dev`
3. Dans le chat, taper: `client michelle`
4. Les noms de clients devraient être cliquables (liens bleus soulignés)
5. Cliquer sur un nom devrait ouvrir le modal avec les détails complets

## Notes Importantes
- Le format des détails doit correspondre à celui de `train_summaries.py` (le plus fourni)
- Les détails incluent: contacts associés, pianos, service history complet, prochains RV
- Le modal est responsive et scrollable pour les longues listes
