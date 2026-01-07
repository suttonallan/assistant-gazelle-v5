# API Assistant Conversationnel - Guide d'utilisation

**Date:** 2026-01-06
**Version:** Phase 1 + 2 (Core + Advanced Queries)

---

## 📋 APERÇU

L'API Conversationnelle permet de poser des questions en langage naturel et recevoir des réponses structurées avec données Supabase + formatage intelligent OpenAI.

**Endpoint principal:**
```
POST /api/conversation/query
```

**Handlers implémentés:**
- ✅ **Phase 1** (4 handlers core): client_search, client_summary, my_appointments, piano_search
- ✅ **Phase 2** (4 advanced queries): client_history, search_notes, humidity_readings, unpaid_invoices

---

## 🎯 PHASE 1: CORE HANDLERS

### 1. Recherche de Client (`client_search`)

**Exemples de questions:**
- "client Vincent-d'Indy"
- "qui est Anne-Marie Denoncourt"
- "trouve Daniel Markwell"
- "École de musique"

**Requête:**
```json
{
  "query": "client Vincent-d'Indy",
  "user_id": "user_abc123",
  "user_role": "technician"
}
```

**Réponse:**
```json
{
  "type": "client_search",
  "query": "client Vincent-d'Indy",
  "formatted_response": "🏢 École de musique Vincent-d'Indy\n📍 628 Chemin de la Côte-Sainte-Catherine\n📞 (514) 555-1234\n\n👥 Contacts:\n  - Anne-Marie Denoncourt (anne-marie@vincentdindy.ca)\n\n🎹 Pianos (138):\n  - Yamaha C3 (#1234567) - Studio A\n  - Steinway D (#7654321) - Salle de concert",
  "data": {
    "clients": [
      {
        "id": "cli_xyz",
        "company_name": "École de musique Vincent-d'Indy",
        "address": "628 Chemin de la Côte-Sainte-Catherine",
        "phone": "(514) 555-1234",
        "contacts": [...],
        "pianos": [...]
      }
    ]
  }
}
```

---

### 2. Résumé Complet Client (`client_summary`)

**Exemples de questions:**
- "résumé pour Vincent-d'Indy"
- "donne-moi tout sur Daniel Markwell"
- "historique complet de ce client"

**Requête:**
```json
{
  "query": "résumé pour Daniel Markwell",
  "user_id": "user_abc123",
  "user_role": "technician"
}
```

**Réponse:**
```json
{
  "type": "client_summary",
  "query": "résumé pour Daniel Markwell",
  "formatted_response": "🎹 Piano\n- Yamaha C3 (Série: 1234567)\n- Studio A, rez-de-chaussée\n\n🧰 État mécanique / sonore\n- Faux battements signalés (6 octobre)\n- Client insatisfait d'un accordeur précédent\n\n💧 Humidité / entretien\n- Aucune anomalie détectée\n\n📅 Historique pertinent\n- 2 avril 2025: Accord (Allan) - Facture #6334 payée\n- 13 novembre 2024: Mesure (Nicolas)\n\n🔜 Points à surveiller\n- Vérifier l'état des faux battements\n\n⏭️ Détails supplémentaires\n- Pour plus: \"Montre-moi les interventions 2024\"",
  "data": {
    "client": {...},
    "timeline_count": 45,
    "next_appointment": {...}
  }
}
```

---

### 3. Mes Rendez-vous (`my_appointments`)

**Exemples de questions:**
- "mes rendez-vous aujourd'hui"
- "qu'est-ce que j'ai demain"
- "mes RV de la semaine"
- "mon agenda du 15 janvier"

**Requête:**
```json
{
  "query": "mes rendez-vous demain",
  "user_id": "user_abc123",
  "user_role": "technician"
}
```

**Réponse:**
```json
{
  "type": "my_appointments",
  "query": "mes rendez-vous demain",
  "formatted_response": "📅 Vos rendez-vous pour 2026-01-07:\n\n🕐 9h00\n  🏢 École de musique Vincent-d'Indy\n  🎹 Yamaha C3 (#1234567) - Studio A\n  📍 628 Chemin de la Côte-Sainte-Catherine\n  📝 Accord + mesure humidité\n\n🕐 14h00\n  🏢 Centre Pierre-Péladeau\n  🎹 Steinway D (#7654321) - Salle de concert\n  📍 300 Boulevard De Maisonneuve Est",
  "data": {
    "appointments": [...],
    "date_range": {
      "start": "2026-01-07",
      "end": "2026-01-07"
    }
  }
}
```

---

### 4. Recherche de Piano (`piano_search`)

**Exemples de questions:**
- "piano 1234567"
- "trouve le piano série 7654321"
- "info sur numéro 9876543"

**Requête:**
```json
{
  "query": "piano 1234567",
  "user_id": "user_abc123",
  "user_role": "technician"
}
```

**Réponse:**
```json
{
  "type": "piano_search",
  "query": "piano 1234567",
  "formatted_response": "🎹 Yamaha C3 (Série: 1234567)\n\n📍 Emplacement:\n  🏢 École de musique Vincent-d'Indy\n  📌 Studio A\n\n📊 Détails techniques:\n  Année: 2015\n  Type: Piano à queue\n\n📅 Dernières interventions (5):\n  - 2024-12-15: Accord (Allan)\n  - 2024-11-13: Mesure humidité (Nicolas)",
  "data": {
    "piano": {
      "id": "ins_abc123",
      "make": "Yamaha",
      "model": "C3",
      "serial_number": "1234567",
      "client": {...},
      "timeline": [...]
    }
  }
}
```

---

## 🔧 DÉTECTION D'INTENTION

L'API utilise GPT-4o-mini pour détecter automatiquement le type de question:

**Flux:**
1. User Query → OpenAI Intent Detection
2. Extraction des entités (nom client, date, numéro série)
3. Routing vers le bon handler
4. Query Supabase avec jointures optimisées
5. Génération réponse formatée avec OpenAI

**Types détectés:**
- `client_search` - Mots-clés: "client", "qui est", "trouve"
- `client_summary` - Mots-clés: "résumé", "donne-moi tout", "historique complet"
- `my_appointments` - Mots-clés: "mes rendez-vous", "mon agenda", dates
- `piano_search` - Mots-clés: "piano", "série", numéros

---

## 📦 STRUCTURE DE RÉPONSE

Toutes les réponses suivent ce schéma:

```typescript
interface ConversationResponse {
  type: 'client_search' | 'client_summary' | 'my_appointments' | 'piano_search' | 'error' | 'not_found';
  query: string;  // Requête originale
  formatted_response: string;  // Texte formaté avec emojis pour affichage direct
  data?: {  // Données brutes pour UI avancée (optionnel)
    clients?: Array<Client>;
    client?: Client;
    appointments?: Array<Appointment>;
    piano?: Piano;
    // etc.
  };
}
```

---

## 🚀 EXEMPLES D'UTILISATION

### Frontend (Fetch API)

```javascript
const response = await fetch('/api/conversation/query', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    query: "résumé pour Vincent-d'Indy",
    user_id: currentUser.id,
    user_role: "technician"
  })
});

const result = await response.json();

// Affichage simple
console.log(result.formatted_response);

// Ou utiliser les données brutes
if (result.type === 'client_summary') {
  const client = result.data.client;
  const nextAppt = result.data.next_appointment;
  // ... render custom UI
}
```

### cURL

```bash
curl -X POST http://localhost:8000/api/conversation/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "mes rendez-vous demain",
    "user_id": "user_abc123",
    "user_role": "technician"
  }'
```

---

## ⚠️ GESTION D'ERREURS

### Erreur: Client non trouvé

```json
{
  "type": "not_found",
  "query": "client XXXXXX",
  "formatted_response": "Aucun client trouvé pour 'XXXXXX'",
  "data": null
}
```

### Erreur: Question non reconnue

```json
{
  "type": "generic",
  "query": "combien fait 2+2",
  "formatted_response": "Je n'ai pas compris votre question. Essayez:\n- 'client [nom]' pour chercher un client\n- 'résumé pour [nom]' pour un résumé complet\n- 'mes rendez-vous [date]' pour vos rendez-vous\n- 'piano [série]' pour chercher un piano"
}
```

### Erreur serveur

```json
{
  "detail": "Erreur: OPENAI_API_KEY not found in environment"
}
```

---

## 🔐 SÉCURITÉ & PERMISSIONS

- `user_id` requis pour associer les requêtes à un utilisateur
- `user_role` détermine les permissions (technician, admin, etc.)
- Les rendez-vous sont filtrés par `gazelle_user_id` du technicien
- Les clients/pianos sont accessibles à tous les techniciens

**TODO Phase 2:**
- Vérification JWT pour authentification
- Rate limiting par utilisateur
- Audit log des requêtes

---

## 📊 PERFORMANCES

**Temps de réponse moyens (estimés):**
- `client_search`: 800-1200ms
  - Query Supabase: 200ms
  - OpenAI intent: 300ms
  - Formatage: 300ms

- `client_summary`: 1500-2500ms
  - Query Supabase (jointures): 400ms
  - OpenAI intent: 300ms
  - OpenAI summary generation: 1000ms

- `my_appointments`: 600-900ms
- `piano_search`: 700-1000ms

**Optimisations appliquées:**
- Queries avec `select()` explicit (évite SELECT *)
- Jointures Supabase (évite N+1)
- Limit sur timeline (max 50 entrées)
- Cache OpenAI responses (TODO Phase 2)

---

## 🛠️ CONFIGURATION REQUISE

**Variables d'environnement:**
```bash
# Supabase
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_SERVICE_ROLE_KEY=xxx

# OpenAI
OPENAI_API_KEY=sk-xxx
```

**Tables Supabase nécessaires:**
- `gazelle_clients`
- `gazelle_contacts`
- `gazelle_pianos`
- `gazelle_timeline_entries`
- `gazelle_appointments`
- `users` (mapping gazelle_user_id)

---

## 🚧 ROADMAP

### Phase 2: Advanced Queries (à venir)
- `handle_client_history()` - Interventions avec filtres
- `handle_search_notes()` - Full-text search timeline
- `handle_humidity_readings()` - Mesures d'humidité
- `handle_unpaid_invoices()` - Factures impayées

### Phase 3: Technician Features
- `handle_technician_appointments()` - RV d'autres techs
- `handle_parts_needed()` - Pièces manquantes
- `handle_recurring_issues()` - Problèmes récurrents

### Phase 4: Analytics & AI
- `handle_semantic_search()` - Recherche vectorielle (embeddings)
- `handle_trends_analysis()` - Analyse de tendances
- `handle_recommendations()` - Recommandations AI

---

## 📖 RESSOURCES

- **Docs de référence:** `docs/TYPES_QUESTIONS_ASSISTANT_CONVERSATIONNEL.md`
- **Format des résumés:** `docs/FORMAT_RESUME_CLIENT.md`
- **Code source:** `modules/assistant/conversation_handler.py`
- **Routes API:** `api/conversation_routes.py`

---

**Créé:** 2026-01-06
**Auteur:** Claude Code
**Statut:** Phase 1 - Production Ready
