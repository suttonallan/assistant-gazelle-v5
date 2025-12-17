# 🚀 Prompt Cursor - Contexte Conversationnel (Démarrage Rapide)

Implémente un système de contexte conversationnel pour permettre aux utilisateurs de:
1. Cliquer sur un client dans les résultats de recherche
2. Poser des questions contextuelles ("ses pianos", "frais de déplacement")

---

## 📋 Ce qu'il faut faire

### 1. Backend - Session Manager

**Créer:** `api/session.py`

```python
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import uuid

sessions: Dict[str, Dict[str, Any]] = {}

class SessionManager:
    @staticmethod
    def get_or_create_session(user_id: str) -> str:
        for session_id, session in sessions.items():
            if session.get('user_id') == user_id:
                if datetime.now() - session['created_at'] < timedelta(minutes=30):
                    return session_id

        session_id = str(uuid.uuid4())
        sessions[session_id] = {
            'user_id': user_id,
            'created_at': datetime.now(),
            'context': {}
        }
        return session_id

    @staticmethod
    def set_context(session_id: str, key: str, value: Any):
        if session_id in sessions:
            sessions[session_id]['context'][key] = value

    @staticmethod
    def get_context(session_id: str, key: str) -> Optional[Any]:
        if session_id in sessions:
            return sessions[session_id]['context'].get(key)
        return None

    @staticmethod
    def clear_context(session_id: str, key: Optional[str] = None):
        if session_id in sessions:
            if key:
                sessions[session_id]['context'].pop(key, None)
            else:
                sessions[session_id]['context'] = {}
```

### 2. Backend - Modifier Chat Endpoint

**Fichier:** `api/assistant.py`

**Au début de `chat()`:**
```python
from api.session import SessionManager
import re

# Dans chat():
session_id = SessionManager.get_or_create_session(user_id)
selected_client = SessionManager.get_context(session_id, 'selected_client')

# Résoudre pronoms possessifs
if selected_client and re.search(r'\b(ses|son|sa)\b', question, re.IGNORECASE):
    client_name = selected_client['name']
    replacements = {
        r'\bses pianos\b': f"pianos de {client_name}",
        r'\bses rv\b': f"rendez-vous de {client_name}",
        r'\bson historique\b': f"historique de {client_name}",
        r'\bfrais de déplacement\b': f"frais de déplacement pour {client_name}"
    }
    for pattern, replacement in replacements.items():
        question = re.sub(pattern, replacement, question, flags=re.IGNORECASE)
```

**Après `execute_query` pour SEARCH_CLIENT:**
```python
if query_type == QueryType.SEARCH_CLIENT:
    results = queries.execute_query(query_type, params, user_id=request.user_id)

    # Sélection auto si 1 seul résultat
    if results['count'] == 1:
        client = results['data'][0]
        SessionManager.set_context(session_id, 'selected_client', {
            'external_id': client.get('external_id'),
            'name': client.get('company_name') or f"{client.get('first_name')} {client.get('last_name')}",
            'city': client.get('city'),
            'postal_code': client.get('postal_code'),
            '_source': client.get('_source')
        })

        answer = _format_response(query_type, results)
        answer += "\n\n✅ **Client sélectionné.** Posez des questions:\n"
        answer += "- \"ses pianos\"\n- \"ses derniers RV\"\n- \"frais de déplacement\""
    else:
        answer = _format_response(query_type, results)

    # Ajouter structured_data pour frontend
    structured_data = {'clients': results.get('data', [])}
```

**Dans le return:**
```python
return ChatResponse(
    # ... autres champs
    structured_data=structured_data,
    session_id=session_id  # Nouveau champ
)
```

### 3. Frontend - Clients Cliquables

**Fichier:** `frontend/src/components/AssistantWidget.jsx`

**Ajouter state:**
```jsx
const [selectedClient, setSelectedClient] = useState(null)
```

**Fonction clic:**
```jsx
const handleClientClick = async (client) => {
  const clientName = client.company_name || `${client.first_name} ${client.last_name}`
  setInputValue(clientName)
  await handleSend(clientName)
}
```

**Rendu cliquable:**
```jsx
const renderMessageWithClickableClients = (content, structuredData) => {
  if (structuredData?.clients) {
    return (
      <div>
        <div className="font-semibold mb-2">
          {content.split('\n')[0]} {/* Titre */}
        </div>
        <div className="space-y-1">
          {structuredData.clients.map((client, idx) => {
            const name = client.company_name ||
                        `${client.first_name} ${client.last_name}`
            const city = client.city ? ` (${client.city})` : ''

            return (
              <div
                key={idx}
                onClick={() => handleClientClick(client)}
                className="cursor-pointer hover:bg-blue-50 p-2 rounded transition-colors border-l-2 border-transparent hover:border-blue-500"
              >
                <span className="font-medium text-blue-600 hover:underline">
                  {name}
                </span>
                <span className="text-gray-600 text-sm">{city}</span>
              </div>
            )
          })}
        </div>
      </div>
    )
  }

  return <ReactMarkdown>{content}</ReactMarkdown>
}
```

**Utiliser dans le rendu des messages:**
```jsx
{messages.map((msg, idx) => (
  <div key={idx}>
    {msg.role === 'assistant' ?
      renderMessageWithClickableClients(msg.content, msg.structured_data) :
      <div>{msg.content}</div>
    }
  </div>
))}
```

---

## 🧪 Tests Rapides

```bash
# Test 1: Sélection auto
curl -X POST http://localhost:8000/assistant/chat \
  -H "Content-Type: application/json" \
  -d '{"question":"olivier asselin","user_id":"test@test.com"}'

# Test 2: Question contextuelle
curl -X POST http://localhost:8000/assistant/chat \
  -H "Content-Type: application/json" \
  -d '{"question":"ses pianos","user_id":"test@test.com"}'

# Test 3: Recherche multiple
curl -X POST http://localhost:8000/assistant/chat \
  -H "Content-Type: application/json" \
  -d '{"question":"olivier","user_id":"test@test.com"}'
```

---

## ✅ Checklist

- [ ] Créer `api/session.py`
- [ ] Modifier `api/assistant.py` (session + résolution pronoms)
- [ ] Ajouter `structured_data` aux réponses SEARCH_CLIENT
- [ ] Modifier frontend pour rendre clients cliquables
- [ ] Tester sélection auto (1 résultat)
- [ ] Tester clic sur liste (multiple résultats)
- [ ] Tester question contextuelle

---

**Référence complète:** Voir [CURSOR_INSTRUCTIONS_CONTEXTE_CONVERSATIONNEL.md](CURSOR_INSTRUCTIONS_CONTEXTE_CONVERSATIONNEL.md)

**Commence par le backend, puis teste avec curl, puis fais le frontend!** 🚀
