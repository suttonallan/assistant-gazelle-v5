# 🎯 Instructions Cursor - Contexte Conversationnel avec Clients Cliquables

**Date:** 2025-12-16
**Objectif:** Permettre à l'utilisateur de cliquer sur un client dans les résultats de recherche et poser des questions contextuelles

---

## 📋 Vue d'Ensemble

### Flux Utilisateur Souhaité

1. **Recherche initiale:**
   ```
   User: "olivier"
   Assistant: 🔍 15 clients trouvés:
   - [Olivier Perot] (Rosemère)     ← CLIQUABLE
   - [Olivier Godin] (Montréal)      ← CLIQUABLE
   - [Olivier Asselin] (Montréal)    ← CLIQUABLE
   ...
   ```

2. **Sélection d'un client:**
   ```
   User: [Clique sur "Olivier Asselin"]
   Assistant: ✅ Client sélectionné: Olivier Asselin (Montréal)

   Vous pouvez maintenant poser des questions:
   - "ses pianos"
   - "ses derniers RV"
   - "son historique"
   - "frais de déplacement"
   ```

3. **Questions contextuelles:**
   ```
   User: "ses pianos"
   Assistant: 🎹 Pianos de Olivier Asselin:
   - Yamaha U1 (S/N: H 2803626)

   User: "frais de déplacement"
   Assistant: 💰 Frais de déplacement pour Olivier Asselin (H4B 2W1):
   - Allan: GRATUIT (12 km, 25 min)
   - Nicolas: 5.50$ (32 km, 40 min)
   - Jean-Philippe: 8.75$ (45 km, 55 min)
   ```

---

## 🏗️ Architecture Technique

### 1. Backend - Gestion de Session (API)

**Fichier à créer:** `api/session.py`

```python
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import uuid

# Store de sessions en mémoire (pour MVP - utiliser Redis en prod)
sessions: Dict[str, Dict[str, Any]] = {}

class SessionManager:
    """Gère les sessions utilisateur pour le contexte conversationnel."""

    @staticmethod
    def get_or_create_session(user_id: str) -> str:
        """Crée ou récupère une session pour un utilisateur."""
        # Chercher session existante
        for session_id, session in sessions.items():
            if session.get('user_id') == user_id:
                # Vérifier expiration (30 min)
                if datetime.now() - session['created_at'] < timedelta(minutes=30):
                    return session_id

        # Créer nouvelle session
        session_id = str(uuid.uuid4())
        sessions[session_id] = {
            'user_id': user_id,
            'created_at': datetime.now(),
            'context': {}
        }
        return session_id

    @staticmethod
    def set_context(session_id: str, key: str, value: Any):
        """Stocke une valeur dans le contexte de session."""
        if session_id in sessions:
            sessions[session_id]['context'][key] = value
            sessions[session_id]['updated_at'] = datetime.now()

    @staticmethod
    def get_context(session_id: str, key: str) -> Optional[Any]:
        """Récupère une valeur du contexte de session."""
        if session_id in sessions:
            return sessions[session_id]['context'].get(key)
        return None

    @staticmethod
    def clear_context(session_id: str, key: Optional[str] = None):
        """Efface le contexte (tout ou une clé spécifique)."""
        if session_id in sessions:
            if key:
                sessions[session_id]['context'].pop(key, None)
            else:
                sessions[session_id]['context'] = {}
```

### 2. Backend - Modification du Chat Endpoint

**Fichier à modifier:** `api/assistant.py`

**Modifications nécessaires:**

1. **Ajouter gestion de session:**

```python
from api.session import SessionManager

# Dans la fonction chat(), ajouter au début:
@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        question = request.question.strip()
        user_id = request.user_id or 'anonymous'

        # Gérer la session
        session_id = SessionManager.get_or_create_session(user_id)

        # Récupérer le contexte (client sélectionné)
        selected_client = SessionManager.get_context(session_id, 'selected_client')

        # ... reste du code
```

2. **Ajouter détection de sélection de client:**

```python
# Après execute_query, vérifier si c'est une sélection de client
if query_type == QueryType.SEARCH_CLIENT:
    results = queries.execute_query(query_type, params, user_id=request.user_id)

    # Si un seul résultat, le sélectionner automatiquement
    if results['count'] == 1:
        client = results['data'][0]
        SessionManager.set_context(session_id, 'selected_client', {
            'external_id': client.get('external_id'),
            'name': client.get('company_name') or f"{client.get('first_name')} {client.get('last_name')}",
            'city': client.get('city'),
            'source': client.get('_source')
        })

        # Ajouter message de confirmation
        answer = _format_response(query_type, results)
        answer += f"\n\n✅ **Client sélectionné.** Vous pouvez maintenant poser des questions:\n"
        answer += "- \"ses pianos\"\n"
        answer += "- \"ses derniers RV\"\n"
        answer += "- \"son historique\"\n"
        answer += "- \"frais de déplacement\""
```

3. **Ajouter résolution de contexte pour questions:**

```python
# Avant le parsing, résoudre les pronoms possessifs
if selected_client and re.search(r'\b(ses|son|sa)\b', question, re.IGNORECASE):
    # Remplacer "ses pianos" par "pianos de [client]"
    # Remplacer "son historique" par "historique de [client]"
    question_resolved = question
    client_name = selected_client['name']

    replacements = {
        r'\bses pianos\b': f"pianos de {client_name}",
        r'\bses rv\b': f"rendez-vous de {client_name}",
        r'\bses rendez-vous\b': f"rendez-vous de {client_name}",
        r'\bson historique\b': f"historique de {client_name}",
        r'\bfrais de déplacement\b': f"frais de déplacement pour {client_name}"
    }

    for pattern, replacement in replacements.items():
        question_resolved = re.sub(pattern, replacement, question_resolved, flags=re.IGNORECASE)

    # Utiliser la question résolue pour le parsing
    question = question_resolved
```

### 3. Frontend - Rendre les Noms Cliquables

**Fichier à modifier:** `frontend/src/components/AssistantWidget.jsx`

**Modifications nécessaires:**

1. **Ajouter gestion de clic sur client:**

```jsx
// Ajouter state pour client sélectionné
const [selectedClient, setSelectedClient] = useState(null)

// Fonction pour gérer le clic sur un client
const handleClientClick = async (client) => {
  setSelectedClient(client)

  // Envoyer un message automatique pour sélectionner le client
  const clientName = client.company_name || `${client.first_name} ${client.last_name}`
  await sendMessage(clientName)
}
```

2. **Modifier le rendu des messages pour détecter les clients cliquables:**

```jsx
// Fonction pour parser et rendre les noms cliquables
const renderMessageWithClickableClients = (content, structuredData) => {
  // Si c'est un résultat de recherche client avec structured_data
  if (structuredData?.clients) {
    return (
      <div>
        <ReactMarkdown>{content.split('\n')[0]}</ReactMarkdown> {/* Titre */}

        <div className="mt-2 space-y-1">
          {structuredData.clients.map((client, idx) => {
            const displayName = client.company_name ||
                              `${client.first_name} ${client.last_name}`
            const city = client.city ? ` (${client.city})` : ''
            const badge = client._source === 'contact' ? ' [Contact]' : ''

            return (
              <div
                key={idx}
                onClick={() => handleClientClick(client)}
                className="cursor-pointer hover:bg-blue-50 p-2 rounded transition-colors"
              >
                <span className="font-semibold text-blue-600 hover:underline">
                  {displayName}
                </span>
                <span className="text-gray-600">{city}</span>
                {badge && <span className="text-xs text-gray-500">{badge}</span>}
              </div>
            )
          })}
        </div>
      </div>
    )
  }

  // Sinon, rendu markdown normal
  return <ReactMarkdown>{content}</ReactMarkdown>
}
```

3. **Modifier l'affichage des messages:**

```jsx
{messages.map((message, idx) => (
  <div key={idx} className={/* ... */}>
    {message.role === 'assistant' ? (
      renderMessageWithClickableClients(
        message.content,
        message.structured_data
      )
    ) : (
      <div>{message.content}</div>
    )}
  </div>
))}
```

### 4. Backend - Ajouter structured_data aux Résultats de Recherche

**Fichier à modifier:** `api/assistant.py`

**Dans la fonction `chat()`, après `execute_query`:**

```python
# 6. Préparer les données structurées pour l'interactivité frontend
structured_data = None

if query_type == QueryType.SEARCH_CLIENT:
    # Ajouter les clients comme données structurées cliquables
    clients_data = results.get('data', [])
    structured_data = {
        'clients': clients_data  # Liste complète des clients pour le frontend
    }

# Dans le return ChatResponse:
return ChatResponse(
    question=question,
    answer=answer,
    query_type=query_type.value,
    confidence=confidence,
    data=results,
    vector_search_used=False,
    structured_data=structured_data  # ← AJOUTER ICI
)
```

---

## 🎨 Cas d'Usage Détaillés

### Cas 1: Recherche Multiple → Sélection

**Étape 1 - Recherche:**
```
User: "olivier"
```

**Réponse API:**
```json
{
  "answer": "🔍 **15 clients trouvés:**\n\n...",
  "structured_data": {
    "clients": [
      {
        "external_id": "cli_ypRzYbZzj0APSle4",
        "company_name": "Olivier Asselin",
        "city": "Montréal",
        "_source": "client"
      },
      // ... 14 autres
    ]
  }
}
```

**Frontend:** Affiche les 15 noms en mode cliquable

**Étape 2 - Clic sur "Olivier Asselin":**

Frontend envoie automatiquement: `"olivier asselin"`

**Réponse API:**
```json
{
  "answer": "🔍 **1 clients trouvés:**\n\n- **Olivier Asselin** (Montréal)\n\n✅ **Client sélectionné.** Vous pouvez maintenant poser des questions:\n- \"ses pianos\"\n...",
  "structured_data": {
    "clients": [...]
  }
}
```

**Session backend:** Stocke `selected_client = {...}`

### Cas 2: Question Contextuelle

**User tape:** "ses pianos"

**Backend résout:** "pianos de Olivier Asselin"

**Parser détecte:** `QueryType.SEARCH_PIANO` avec `search_terms = ["pianos", "olivier", "asselin"]`

**Réponse:**
```
🎹 **Pianos de Olivier Asselin:**
- Yamaha U1 (S/N: H 2803626)
```

### Cas 3: Frais de Déplacement Contextuels

**User tape:** "frais de déplacement"

**Backend résout:** "frais de déplacement pour Olivier Asselin"

**Backend:**
1. Récupère le client sélectionné depuis la session
2. Extrait son code postal (H4B 2W1)
3. Appelle `TravelFeeCalculator`
4. Retourne les frais pour les 3 techniciens

---

## 📝 Modèle de Données

### ChatRequest (API)

```python
class ChatRequest(BaseModel):
    question: str
    user_id: Optional[str] = 'anonymous'
    session_id: Optional[str] = None  # ← AJOUTER
```

### ChatResponse (API)

```python
class ChatResponse(BaseModel):
    question: str
    answer: str
    query_type: str
    confidence: float
    data: Optional[Dict[str, Any]] = None
    vector_search_used: bool = False
    vector_results: Optional[List[Dict[str, Any]]] = None
    structured_data: Optional[Dict[str, Any]] = None  # DÉJÀ EXISTE
    session_id: Optional[str] = None  # ← AJOUTER
```

### Session Context Structure

```python
{
    'selected_client': {
        'external_id': 'cli_ypRzYbZzj0APSle4',
        'name': 'Olivier Asselin',
        'city': 'Montréal',
        'postal_code': 'H4B 2W1',  # Si disponible
        '_source': 'client'
    }
}
```

---

## 🧪 Tests à Effectuer

### Test 1: Sélection Client Unique
```bash
# Recherche précise → sélection auto
curl -X POST http://localhost:8000/assistant/chat \
  -H "Content-Type: application/json" \
  -d '{"question":"olivier asselin","user_id":"test@test.com"}'

# Vérifier que selected_client est stocké en session
```

### Test 2: Sélection Manuelle depuis Liste
```bash
# 1. Recherche large
curl -X POST http://localhost:8000/assistant/chat \
  -d '{"question":"olivier","user_id":"test@test.com"}'

# 2. Clic sur un client (frontend envoie le nom complet)
curl -X POST http://localhost:8000/assistant/chat \
  -d '{"question":"olivier asselin","user_id":"test@test.com"}'
```

### Test 3: Question Contextuelle
```bash
# Après sélection, poser question contextuelle
curl -X POST http://localhost:8000/assistant/chat \
  -d '{"question":"ses pianos","user_id":"test@test.com"}'

# Devrait retourner les pianos de Olivier Asselin
```

### Test 4: Frais de Déplacement Contextuels
```bash
curl -X POST http://localhost:8000/assistant/chat \
  -d '{"question":"frais de déplacement","user_id":"test@test.com"}'

# Devrait calculer les frais pour Olivier Asselin
```

---

## 🔧 Gestion des Cas Limites

### Cas 1: Session Expirée

Si `selected_client` n'existe plus:
```python
if selected_client is None and re.search(r'\b(ses|son|sa)\b', question):
    return ChatResponse(
        question=question,
        answer="❌ Aucun client sélectionné. Recherchez d'abord un client (ex: \"olivier asselin\")",
        query_type="error",
        confidence=0.0
    )
```

### Cas 2: Désélection

Permettre de désélectionner:
```python
if question.lower() in ['reset', 'clear', 'nouveau', 'nouvelle recherche']:
    SessionManager.clear_context(session_id, 'selected_client')
    return ChatResponse(
        question=question,
        answer="✅ Contexte effacé. Vous pouvez faire une nouvelle recherche.",
        query_type="system",
        confidence=1.0
    )
```

### Cas 3: Ambiguïté

Si "ses pianos" mais client non sélectionné:
```python
# Suggérer de sélectionner d'abord
answer = "Pour voir les pianos d'un client, sélectionnez d'abord le client:\n"
answer += "1. Tapez le nom du client (ex: \"olivier asselin\")\n"
answer += "2. Puis tapez \"ses pianos\""
```

---

## 📊 Améliorations Futures

### Phase 2: Cache Intelligent
- Cacher les données client (pianos, RV, timeline) lors de la sélection
- Réduire les requêtes DB pour questions successives

### Phase 3: Suggestions Contextuelles
Quand un client est sélectionné, afficher des boutons rapides:
```jsx
<div className="flex gap-2 mt-2">
  <button onClick={() => sendMessage("ses pianos")}>
    🎹 Pianos
  </button>
  <button onClick={() => sendMessage("ses derniers RV")}>
    📅 RV
  </button>
  <button onClick={() => sendMessage("frais de déplacement")}>
    💰 Frais
  </button>
</div>
```

### Phase 4: Historique Conversationnel
- Garder historique des 5 derniers clients sélectionnés
- Permettre de revenir en arrière: "client précédent"

---

## ✅ Checklist d'Implémentation

### Backend
- [ ] Créer `api/session.py` avec `SessionManager`
- [ ] Modifier `api/assistant.py`:
  - [ ] Ajouter gestion de session au début de `chat()`
  - [ ] Ajouter détection sélection client (count == 1)
  - [ ] Ajouter résolution pronoms possessifs (ses/son/sa)
  - [ ] Ajouter `structured_data` avec liste clients
  - [ ] Ajouter gestion cas limites (session expirée, reset)
- [ ] Créer tests backend (`scripts/test_context.py`)

### Frontend
- [ ] Modifier `AssistantWidget.jsx`:
  - [ ] Ajouter state `selectedClient`
  - [ ] Créer fonction `handleClientClick()`
  - [ ] Créer fonction `renderMessageWithClickableClients()`
  - [ ] Modifier rendu messages pour utiliser la nouvelle fonction
  - [ ] Ajouter styles hover pour noms cliquables
  - [ ] Ajouter indicateur visuel client sélectionné

### Tests
- [ ] Test sélection auto (1 résultat)
- [ ] Test sélection manuelle (clic sur liste)
- [ ] Test question contextuelle "ses pianos"
- [ ] Test "frais de déplacement" contextuel
- [ ] Test reset/clear
- [ ] Test session expirée

### Documentation
- [ ] Ajouter exemples dans README
- [ ] Créer guide utilisateur
- [ ] Documenter API session

---

## 🎯 Résultat Final Attendu

**UX Fluide:**
1. User tape "olivier" → voit 15 noms cliquables
2. User clique "Olivier Asselin" → message de confirmation
3. User tape "ses pianos" → voit les pianos d'Olivier
4. User tape "frais" → voit les frais de déplacement pour Olivier
5. User tape "reset" → peut chercher un nouveau client

**Performance:**
- Réponse < 500ms pour sélection
- Réponse < 1s pour questions contextuelles
- Session en mémoire (rapide, pas de DB)

**Robustesse:**
- Gestion sessions expirées
- Messages d'erreur clairs
- Fallback si contexte invalide

---

**Prêt à implémenter!** 🚀

Commence par le backend (`api/session.py` + modifications `api/assistant.py`), puis teste, puis fais le frontend.
