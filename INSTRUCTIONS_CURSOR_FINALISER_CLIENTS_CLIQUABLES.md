# Instructions: Finaliser Clients Cliquables dans le Chat

## 🎯 Objectif
Rendre les noms de clients cliquables dans les réponses du chat assistant. Quand un utilisateur cherche un client (ex: "client michelle"), les noms affichés doivent être cliquables et ouvrir un modal avec tous les détails du client.

## 📋 État Actuel
- ✅ Backend retourne `structured_data.clickable_entities` dans les réponses
- ❌ Composants React `ClickableMessage` et `ClientDetailsModal` manquants
- ❌ `AssistantWidget.jsx` n'utilise pas les entités cliquables
- ❌ Endpoint `/assistant/client/{id}` manquant dans le backend

## 🔧 Tâches à Effectuer

### 1. Créer le Composant `ClickableMessage.jsx`

**Fichier:** `frontend/src/components/ClickableMessage.jsx`

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

### 2. Créer le Composant `ClientDetailsModal.jsx`

**Fichier:** `frontend/src/components/ClientDetailsModal.jsx`

```jsx
import { useState, useEffect } from 'react'

const API_URL = import.meta.env.VITE_API_URL || 'https://assistant-gazelle-v5-api.onrender.com'

export default function ClientDetailsModal({ clientId, onClose }) {
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [details, setDetails] = useState(null)

  useEffect(() => {
    const fetchDetails = async () => {
      try {
        setLoading(true)
        setError(null)
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

    if (clientId) {
      fetchDetails()
    }
  }, [clientId])

  return (
    <div 
      className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4"
      onClick={(e) => {
        if (e.target === e.currentTarget) {
          onClose()
        }
      }}
    >
      <div className="bg-white rounded-lg shadow-xl max-w-4xl w-full max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="sticky top-0 bg-white border-b px-6 py-4 flex justify-between items-center z-10">
          <h2 className="text-xl font-bold">Détails Client</h2>
          <button
            onClick={onClose}
            className="text-gray-500 hover:text-gray-700 text-2xl font-bold"
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
                  {details.type && (
                    <p>
                      <span className="font-medium">Type:</span>{' '}
                      <span className={`px-2 py-1 rounded text-xs ${
                        details.type === 'client' 
                          ? 'bg-blue-100 text-blue-800' 
                          : 'bg-green-100 text-green-800'
                      }`}>
                        {details.type === 'client' ? 'Client' : 'Contact'}
                      </span>
                    </p>
                  )}
                </div>
              </div>

              {/* Notes client */}
              {details.client_notes && (
                <div>
                  <h3 className="text-lg font-semibold mb-2">Notes Client</h3>
                  <div className="bg-yellow-50 p-4 rounded border-l-4 border-yellow-400">
                    <p className="text-sm text-gray-700 whitespace-pre-wrap">{details.client_notes}</p>
                  </div>
                </div>
              )}

              {/* Contacts associés */}
              {details.associated_contacts && details.associated_contacts.length > 0 && (
                <div>
                  <h3 className="text-lg font-semibold mb-2">Contacts Associés ({details.associated_contacts.length})</h3>
                  <div className="space-y-2">
                    {details.associated_contacts.map((contact, idx) => (
                      <div key={idx} className="bg-gray-50 p-3 rounded">
                        <p className="font-medium">{contact.name || 'N/A'}</p>
                        {contact.role && <p className="text-sm text-gray-600">{contact.role}</p>}
                        {contact.phone && <p className="text-sm">📞 {contact.phone}</p>}
                        {contact.email && <p className="text-sm">✉️ {contact.email}</p>}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Pianos */}
              {details.pianos && details.pianos.length > 0 && (
                <div>
                  <h3 className="text-lg font-semibold mb-2">🎹 Pianos ({details.pianos.length})</h3>
                  <div className="space-y-3">
                    {details.pianos.map((piano, idx) => (
                      <div key={idx} className="bg-gray-50 p-4 rounded border-l-4 border-blue-400">
                        <p className="font-medium">
                          {piano.make || ''} {piano.model || ''}
                          {piano.serial_number && <span className="text-gray-600 text-sm ml-2">(S/N: {piano.serial_number})</span>}
                        </p>
                        <div className="mt-2 space-y-1 text-sm">
                          {piano.year && <p className="text-gray-600">Année: {piano.year}</p>}
                          {piano.type && <p className="text-gray-600">Type: {piano.type}</p>}
                          {piano.location && <p className="text-gray-600">📍 {piano.location}</p>}
                          {piano.notes && (
                            <div className="mt-2 p-2 bg-blue-50 rounded">
                              <p className="text-xs text-gray-700 whitespace-pre-wrap">{piano.notes}</p>
                            </div>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Historique de service */}
              {details.service_history && details.service_history.length > 0 && (
                <div>
                  <h3 className="text-lg font-semibold mb-2">📝 Historique de Service ({details.service_history.length})</h3>
                  <div className="space-y-3 max-h-96 overflow-y-auto">
                    {details.service_history.map((note, idx) => (
                      <div key={idx} className="bg-blue-50 p-3 rounded border-l-4 border-blue-400">
                        <p className="text-sm text-gray-700 whitespace-pre-wrap">{note}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Prochains RV */}
              {details.upcoming_appointments && details.upcoming_appointments.length > 0 && (
                <div>
                  <h3 className="text-lg font-semibold mb-2">📅 Prochains Rendez-vous ({details.upcoming_appointments.length})</h3>
                  <div className="space-y-2">
                    {details.upcoming_appointments.map((appt, idx) => (
                      <div key={idx} className="bg-green-50 p-3 rounded border-l-4 border-green-400">
                        <p className="font-medium">{appt.date} à {appt.time}</p>
                        {appt.title && <p className="text-sm text-gray-600">{appt.title}</p>}
                        {appt.description && <p className="text-sm text-gray-600">{appt.description}</p>}
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

### 3. Modifier `AssistantWidget.jsx`

**Fichier:** `frontend/src/components/AssistantWidget.jsx`

**Modifications à apporter:**

1. **Ajouter l'import en haut du fichier:**
```jsx
import ClickableMessage from './ClickableMessage'
```

2. **Dans `handleSendMessage`, modifier la création de `assistantMessage` pour inclure `clickable_entities`:**
```jsx
const assistantMessage = {
  role: 'assistant',
  content: data.answer || "Désolé, je n'ai pas pu traiter votre demande.",
  metadata: {
    query_type: data.query_type,
    confidence: data.confidence,
    clickable_entities: data.structured_data?.clickable_entities || []
  },
  structured_data: data.structured_data || null
}
```

3. **Dans le rendu des messages, remplacer l'affichage du contenu pour utiliser `ClickableMessage` quand il y a des entités cliquables:**
```jsx
{msg.role === 'assistant' && msg.metadata?.clickable_entities && msg.metadata.clickable_entities.length > 0 ? (
  <ClickableMessage
    content={msg.content}
    entities={msg.metadata.clickable_entities}
  />
) : (
  <div className="text-sm whitespace-pre-wrap">{msg.content}</div>
)}
```

### 4. Ajouter l'Endpoint Backend `/assistant/client/{id}`

**Fichier:** `api/assistant.py`

**Ajouter ce nouvel endpoint après l'endpoint `/health` (vers la ligne 247):**

```python
@router.get("/client/{client_id}")
async def get_client_details(client_id: str):
    """
    Récupère les détails complets d'un client/contact pour affichage dans le modal.
    
    Utilise le même format que train_summaries.py (le plus fourni).
    Inclut: contacts associés, pianos avec notes, service history, prochains RV.
    """
    try:
        import requests
        queries = get_queries()
        
        # Rechercher le client/contact
        results = queries.search_clients([client_id])
        
        if not results or len(results) == 0:
            raise HTTPException(status_code=404, detail="Client non trouvé")
        
        entity = results[0]
        entity_id = entity.get('external_id') or entity.get('id') or client_id
        
        # Détecter par préfixe
        is_client = entity_id.startswith('cli_')
        is_contact = entity_id.startswith('con_')
        
        # Informations de base
        if is_contact:
            first = entity.get('first_name', '')
            last = entity.get('last_name', '')
            name = f"{first} {last}".strip() or entity.get('name', 'N/A')
        else:
            name = entity.get('company_name', 'N/A')
        
        details = {
            'id': entity_id,
            'type': 'client' if is_client else 'contact',
            'name': name,
            'address': entity.get('address', ''),
            'city': entity.get('city', ''),
            'postal_code': entity.get('postal_code', ''),
            'phone': entity.get('phone', '') or entity.get('telephone', ''),
            'email': entity.get('email', '')
        }
        
        # Pour les clients uniquement: enrichissement complet
        if is_client:
            # Notes client
            details['client_notes'] = entity.get('notes', '') or entity.get('note', '') or entity.get('description', '')
            
            # Pianos avec leurs notes
            try:
                pianos_url = f"{queries.storage.api_url}/gazelle_pianos?client_external_id=eq.{entity_id}&select=external_id,notes,make,model,serial_number,type,year,location&limit=10"
                pianos_response = requests.get(pianos_url, headers=queries.storage._get_headers())
                if pianos_response.status_code == 200:
                    pianos = pianos_response.json()
                    details['pianos'] = []
                    for piano in pianos:
                        piano_info = {
                            'external_id': piano.get('external_id', ''),
                            'make': piano.get('make', ''),
                            'model': piano.get('model', ''),
                            'serial_number': piano.get('serial_number', ''),
                            'type': piano.get('type', ''),
                            'year': piano.get('year', ''),
                            'location': piano.get('location', ''),
                            'notes': piano.get('notes', '')
                        }
                        if piano_info['make'] or piano_info['model'] or piano_info['notes']:
                            details['pianos'].append(piano_info)
            except Exception as e:
                print(f"⚠️ Erreur récupération pianos pour {entity_id}: {e}")
                details['pianos'] = []
            
            # Service history (timeline entries pour client + pianos)
            try:
                service_notes = []
                # Timeline pour le client
                timeline_entries_client = queries.get_timeline_entries(entity_id, entity_type='client', limit=20)
                
                # Timeline pour chaque piano
                timeline_entries_pianos = []
                for piano in details.get('pianos', []):
                    piano_id = piano.get('external_id')
                    if piano_id:
                        piano_timeline = queries.get_timeline_entries(piano_id, entity_type='piano', limit=10)
                        timeline_entries_pianos.extend(piano_timeline)
                
                # Combiner et extraire les notes
                all_timeline_entries = timeline_entries_client + timeline_entries_pianos
                for e in all_timeline_entries:
                    note = e.get('notes') or e.get('description') or e.get('content') or e.get('note') or e.get('text') or e.get('summary')
                    if note:
                        service_notes.append(str(note))
                
                details['service_history'] = service_notes[:20]  # Limiter à 20 pour éviter surcharge
            except Exception as e:
                print(f"⚠️ Erreur timeline pour {entity_id}: {e}")
                details['service_history'] = []
            
            # Contacts associés
            try:
                contacts_url = f"{queries.storage.api_url}/gazelle_contacts?client_external_id=eq.{entity_id}&limit=10"
                contacts_response = requests.get(contacts_url, headers=queries.storage._get_headers())
                if contacts_response.status_code == 200:
                    contacts = contacts_response.json()
                    if contacts:
                        details['associated_contacts'] = [
                            {
                                'name': f"{c.get('first_name', '')} {c.get('last_name', '')}".strip() or c.get('name', 'N/A'),
                                'role': c.get('role') or c.get('title') or '',
                                'phone': c.get('phone') or c.get('telephone') or '',
                                'email': c.get('email', '')
                            }
                            for c in contacts[:10]
                        ]
                    else:
                        details['associated_contacts'] = []
                else:
                    details['associated_contacts'] = []
            except Exception as e:
                print(f"⚠️ Erreur contacts associés pour {entity_id}: {e}")
                details['associated_contacts'] = []
            
            # Prochains rendez-vous
            try:
                from datetime import date
                today = date.today()
                appointments = queries.get_appointments(date=today, technicien=None)
                upcoming = []
                for appt in appointments:
                    if appt.get('client_external_id') == entity_id:
                        upcoming.append({
                            'date': appt.get('appointment_date', ''),
                            'time': _format_time(
                                appt.get('appointment_time', 'N/A'),
                                appt.get('appointment_date', '')
                            ),
                            'title': appt.get('title', ''),
                            'description': appt.get('description', ''),
                            'assigned_to': appt.get('technicien', '')
                        })
                details['upcoming_appointments'] = upcoming[:10]  # Limiter à 10
            except Exception as e:
                print(f"⚠️ Erreur prochains RV pour {entity_id}: {e}")
                details['upcoming_appointments'] = []
        else:
            # Pour les contacts: pas d'enrichissement
            details['client_notes'] = ''
            details['pianos'] = []
            details['service_history'] = []
            details['associated_contacts'] = []
            details['upcoming_appointments'] = []
        
        return details
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Erreur dans /assistant/client/{client_id}: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
```

## ✅ Tests à Effectuer

1. **Démarrer le backend:**
   ```bash
   python3 -m uvicorn api.main:app --reload
   ```

2. **Démarrer le frontend:**
   ```bash
   cd frontend && npm run dev
   ```

3. **Tester dans le chat:**
   - Taper: `client michelle`
   - Vérifier que les noms de clients sont affichés en gras
   - Vérifier que les noms sont cliquables (liens bleus soulignés)
   - Cliquer sur un nom
   - Vérifier que le modal s'ouvre avec les détails complets

4. **Vérifier le contenu du modal:**
   - Informations de base (nom, adresse, téléphone, email)
   - Notes client (si présentes)
   - Contacts associés (si présents)
   - Pianos avec leurs notes (si présents)
   - Historique de service (si présent)
   - Prochains rendez-vous (si présents)

## 📝 Notes Importantes

- Le backend retourne déjà `structured_data.clickable_entities` dans les réponses de recherche client
- Chaque entité contient: `id`, `name`, `type` (client/contact), `city`
- Le format des détails doit correspondre à celui de `train_summaries.py` (le plus fourni)
- Le modal est responsive et scrollable pour les longues listes
- Les erreurs sont gérées gracieusement avec des messages d'erreur dans le modal

## 🎯 Résultat Attendu

Quand un utilisateur tape `client michelle`, il devrait voir:
```
🔍 **2 clients trouvés:**

- **Michelle Alie** (Saint-Lambert)  ← cliquable (lien bleu)
- **Michelle Sutton** (Montréal)     ← cliquable (lien bleu)
```

En cliquant sur un nom, un modal s'ouvre avec TOUS les détails (même format que l'entraînement).
