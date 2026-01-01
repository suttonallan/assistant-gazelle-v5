# Types de Questions pour l'Assistant Conversationnel V5

**Date:** 2025-12-25
**Objectif:** Documenter TOUS les types de questions possibles et comment y répondre

---

## 📋 TABLE DES MATIÈRES

1. [Questions sur les clients](#1-questions-sur-les-clients)
2. [Questions sur les rendez-vous](#2-questions-sur-les-rendez-vous)
3. [Questions sur l'historique](#3-questions-sur-lhistorique)
4. [Questions sur les pianos](#4-questions-sur-les-pianos)
5. [Questions sur les factures](#5-questions-sur-les-factures)
6. [Questions techniques (notes, pièces, problèmes)](#6-questions-techniques)
7. [Questions sur l'humidité](#7-questions-sur-lhumidité)
8. [Questions de recherche sémantique](#8-questions-de-recherche-sémantique)
9. [Architecture de réponse](#9-architecture-de-réponse)

---

## 1. QUESTIONS SUR LES CLIENTS

### 1.1 Recherche de client par nom

**Exemples de questions:**
- "client Daniel Markwell"
- "qui est Anne-Marie"
- "trouve-moi les infos de Vincent-d'Indy"
- "École de musique"

**Intent détecté:** `client_search`

**Données nécessaires:**
```python
{
    "client": {
        "id": "cli_xyz",
        "company_name": "École de musique Vincent-d'Indy",
        "address": "628 Chemin de la Côte-Sainte-Catherine",
        "phone": "(514) 555-1234"
    },
    "contacts": [
        {
            "full_name": "Anne-Marie Denoncourt",
            "email": "anne-marie@vincentdindy.ca",
            "phone": "(514) 555-5678"
        }
    ],
    "pianos": [
        {
            "make": "Yamaha",
            "model": "C3",
            "serial_number": "1234567",
            "location": "Studio A"
        }
    ]
}
```

**Query Supabase:**
```python
# Chercher dans contacts (personnes) et clients (entreprises)
contacts = supabase.table('gazelle_contacts')\
    .select('*, client:gazelle_clients(*)')\
    .ilike('full_name', f'%{query}%')\
    .execute()

clients = supabase.table('gazelle_clients')\
    .select('*, contacts:gazelle_contacts(*), pianos:gazelle_pianos(*)')\
    .ilike('company_name', f'%{query}%')\
    .execute()
```

**Format de réponse:**
```
🏢 École de musique Vincent-d'Indy
📍 628 Chemin de la Côte-Sainte-Catherine
📞 (514) 555-1234

👥 Contacts:
  - Anne-Marie Denoncourt (anne-marie@vincentdindy.ca)

🎹 Pianos (3):
  - Yamaha C3 (#1234567) - Studio A
  - Steinway D (#7654321) - Salle de concert
  - Kawai GL-10 (#9876543) - Studio B
```

---

### 1.2 Résumé complet d'un client

**Exemples de questions:**
- "résumé pour Daniel Markwell"
- "donne-moi tout sur Vincent-d'Indy"
- "historique complet de ce client"

**Intent détecté:** `client_summary`

**Données nécessaires:**
- Client + Contacts + Pianos
- Timeline entries (50 dernières)
- Prochain rendez-vous
- Notes critiques

**Query Supabase:**
```python
# 1. Client avec contacts et pianos
client = supabase.table('gazelle_clients')\
    .select('''
        *,
        contacts:gazelle_contacts(*),
        pianos:gazelle_pianos(*)
    ''')\
    .eq('id', client_id)\
    .single()\
    .execute()

# 2. Timeline entries pour les pianos de ce client
piano_ids = [p['id'] for p in client.data['pianos']]

timeline = supabase.table('gazelle_timeline_entries')\
    .select('''
        *,
        piano:gazelle_pianos(make, model, serial_number),
        user:users(full_name)
    ''')\
    .in_('piano_id', piano_ids)\
    .order('occurred_at', desc=True)\
    .limit(50)\
    .execute()

# 3. Prochain rendez-vous
next_appt = supabase.table('gazelle_appointments')\
    .select('*, piano:gazelle_pianos(make, model)')\
    .eq('client_id', client_id)\
    .eq('status', 'ACTIVE')\
    .gte('start_at', 'now()')\
    .order('start_at')\
    .limit(1)\
    .execute()
```

**Format de réponse (selon FORMAT_RESUME_CLIENT.md):**
```
🎹 Piano
- Yamaha C3 (Série: 1234567)
- Studio A, rez-de-chaussée
- Acheté d'occasion en 2023

🧰 État mécanique / sonore
- Faux battements signalés (6 octobre, corde numéro X)
- Client insatisfait d'un accordeur précédent

💧 Humidité / entretien
- Aucune anomalie détectée

📅 Historique pertinent
- 2 avril 2025: Mesure (22°C, 37% humidité), facture #6334 payée
- 13 novembre 2024: Mesure (23°C, 42% humidité), facture #6071 payée

🔜 Points à surveiller
- Vérifier l'état des faux battements signalés
- Confirmer satisfaction client après intervention

⏭️ Détails supplémentaires
- Pour plus de détails, demandez: "Montre-moi les interventions 2024"
```

---

## 2. QUESTIONS SUR LES RENDEZ-VOUS

### 2.1 Mes rendez-vous (technicien actuel)

**Exemples de questions:**
- "mes rendez-vous aujourd'hui"
- "qu'est-ce que j'ai demain"
- "mes RV de la semaine"

**Intent détecté:** `my_appointments`

**Query Supabase:**
```python
# Récupérer l'utilisateur connecté
user = get_current_user()  # From JWT or session

# Récupérer ses rendez-vous
appointments = supabase.table('gazelle_appointments')\
    .select('''
        *,
        client:gazelle_clients(company_name, address),
        piano:gazelle_pianos(make, model, serial_number, location)
    ''')\
    .eq('user_id', user.gazelle_user_id)\
    .eq('status', 'ACTIVE')\
    .gte('start_at', start_date)\
    .lte('start_at', end_date)\
    .order('start_at')\
    .execute()
```

**Format de réponse:**
```
📅 Vos rendez-vous pour demain (25 décembre):

🕐 9h00 - 11h00
  🏢 École de musique Vincent-d'Indy
  🎹 Yamaha C3 (#1234567) - Studio A
  📍 628 Chemin de la Côte-Sainte-Catherine
  📝 Accord + mesure humidité

🕐 14h00 - 16h00
  🏢 Centre Pierre-Péladeau
  🎹 Steinway D (#7654321) - Salle de concert
  📍 300 Boulevard De Maisonneuve Est
  📝 Réparation mécanisme touche #52
```

---

### 2.2 Rendez-vous d'un autre technicien

**Exemples de questions:**
- "les rendez-vous de Nicolas cette semaine"
- "qu'est-ce que Jean-Philippe a demain"
- "agenda de Nicolas"

**Intent détecté:** `technician_appointments`

**Query Supabase:**
```python
# 1. Trouver le technicien par nom
tech = supabase.table('users')\
    .select('gazelle_user_id, full_name')\
    .ilike('full_name', f'%{tech_name}%')\
    .execute()

if not tech.data:
    return "Technicien non trouvé"

# 2. Récupérer ses rendez-vous
appointments = supabase.table('gazelle_appointments')\
    .select('''
        *,
        client:gazelle_clients(company_name),
        piano:gazelle_pianos(make, model)
    ''')\
    .eq('user_id', tech.data[0]['gazelle_user_id'])\
    .eq('status', 'ACTIVE')\
    .gte('start_at', start_date)\
    .lte('start_at', end_date)\
    .order('start_at')\
    .execute()
```

---

### 2.3 Rendez-vous non confirmés

**Exemples de questions:**
- "quels sont les rendez-vous non confirmés"
- "RV à confirmer"
- "liste des rendez-vous en attente"

**Intent détecté:** `unconfirmed_appointments`

**Query Supabase:**
```python
appointments = supabase.table('gazelle_appointments')\
    .select('''
        *,
        client:gazelle_clients(company_name),
        piano:gazelle_pianos(make, model)
    ''')\
    .eq('confirmation_status', 'PENDING')\
    .eq('status', 'ACTIVE')\
    .gte('start_at', 'now()')\
    .order('start_at')\
    .execute()
```

---

## 3. QUESTIONS SUR L'HISTORIQUE

### 3.1 Interventions récentes d'un client

**Exemples de questions:**
- "montre-moi les interventions 2024 pour Vincent-d'Indy"
- "historique récent de ce client"
- "dernières visites"

**Intent détecté:** `client_history`

**Query Supabase:**
```python
# 1. Trouver le client
client = supabase.table('gazelle_clients')\
    .select('id, pianos:gazelle_pianos(id)')\
    .ilike('company_name', f'%{client_name}%')\
    .single()\
    .execute()

piano_ids = [p['id'] for p in client.data['pianos']]

# 2. Récupérer timeline entries
timeline = supabase.table('gazelle_timeline_entries')\
    .select('''
        occurred_at,
        entry_type,
        title,
        description,
        piano:gazelle_pianos(make, model, serial_number),
        user:users(full_name)
    ''')\
    .in_('piano_id', piano_ids)\
    .gte('occurred_at', '2024-01-01')\
    .order('occurred_at', desc=True)\
    .execute()
```

**Format de réponse:**
```
📅 Interventions 2024 pour École de musique Vincent-d'Indy (138 entrées):

2024-12-15 | Yamaha C3 | Allan
  ✓ Accord complet - Diapason 440Hz
  💧 Humidité: 42% (normal)

2024-11-13 | Steinway D | Nicolas
  🔧 Réparation touche #52
  ⚠️ Problème récurrent - À surveiller

2024-10-06 | Kawai GL-10 | Jean-Philippe
  ✓ Accord + régulation
  💧 Humidité: 38% (un peu bas)
```

---

### 3.2 Recherche dans les notes

**Exemples de questions:**
- "trouve 'faux battements' dans les notes de ce client"
- "où est-ce que j'ai mentionné les cordes cassées ?"
- "recherche 'pédale' dans l'historique"

**Intent détecté:** `search_notes`

**Query Supabase:**
```python
# Full-text search dans description et title
timeline = supabase.table('gazelle_timeline_entries')\
    .select('''
        occurred_at,
        title,
        description,
        piano:gazelle_pianos(make, model),
        user:users(full_name)
    ''')\
    .in_('piano_id', piano_ids)\
    .or_(f'title.ilike.%{search_term}%,description.ilike.%{search_term}%')\
    .order('occurred_at', desc=True)\
    .limit(20)\
    .execute()
```

---

## 4. QUESTIONS SUR LES PIANOS

### 4.1 Recherche de piano par numéro de série

**Exemples de questions:**
- "piano 1234567"
- "trouve le piano avec série 7654321"
- "info sur numéro série 9876543"

**Intent détecté:** `piano_search`

**Query Supabase:**
```python
piano = supabase.table('gazelle_pianos')\
    .select('''
        *,
        client:gazelle_clients(company_name, address),
        timeline:gazelle_timeline_entries(
            occurred_at,
            entry_type,
            title,
            user:users(full_name)
        )
    ''')\
    .eq('serial_number', serial_number)\
    .single()\
    .execute()
```

**Format de réponse:**
```
🎹 Yamaha C3 (Série: 1234567)

📍 Emplacement:
  🏢 École de musique Vincent-d'Indy
  📌 Studio A

📊 Détails techniques:
  Année: 2015
  Type: Piano à queue
  Taille: 186 cm

📅 Dernières interventions (5):
  - 2024-12-15: Accord (Allan)
  - 2024-11-13: Mesure humidité (Nicolas)
  - 2024-10-06: Régulation (Jean-Philippe)
```

---

### 4.2 Liste des pianos d'un client

**Exemples de questions:**
- "combien de pianos a Vincent-d'Indy ?"
- "liste des pianos de ce client"
- "tous les instruments de cette école"

**Intent détecté:** `client_pianos`

**Query Supabase:**
```python
pianos = supabase.table('gazelle_pianos')\
    .select('*')\
    .eq('client_id', client_id)\
    .order('make, model')\
    .execute()
```

---

## 5. QUESTIONS SUR LES FACTURES

### 5.1 Factures d'un client

**Exemples de questions:**
- "factures de ce client"
- "combien Vincent-d'Indy nous doit ?"
- "dernières factures payées"

**Intent détecté:** `client_invoices`

**Query Supabase:**
```python
invoices = supabase.table('gazelle_invoices')\
    .select('''
        *,
        client:gazelle_clients(company_name)
    ''')\
    .eq('client_id', client_id)\
    .order('issued_at', desc=True)\
    .limit(10)\
    .execute()
```

**Format de réponse:**
```
💰 Factures récentes pour École de musique Vincent-d'Indy:

✅ #6334 - 250$ - Payée (2 avril 2025)
  Accord Yamaha C3

⏳ #6400 - 180$ - Non payée (15 décembre 2024)
  Mesure humidité (3 pianos)

✅ #6071 - 250$ - Payée (13 novembre 2024)
  Accord Steinway D

Total impayé: 180$
```

---

### 5.2 Factures non payées

**Exemples de questions:**
- "quelles factures ne sont pas payées ?"
- "créances en souffrance"
- "liste des impayés"

**Intent détecté:** `unpaid_invoices`

**Query Supabase:**
```python
unpaid = supabase.table('gazelle_invoices')\
    .select('''
        *,
        client:gazelle_clients(company_name, phone)
    ''')\
    .eq('payment_status', 'UNPAID')\
    .order('issued_at')\
    .execute()
```

---

## 6. QUESTIONS TECHNIQUES

### 6.1 Problèmes récurrents

**Exemples de questions:**
- "ce piano a-t-il des problèmes récurrents ?"
- "quels sont les défauts connus ?"
- "historique des réparations"

**Intent détecté:** `recurring_issues`

**Query Supabase:**
```python
# Chercher les entries avec mots-clés de problèmes
issues = supabase.table('gazelle_timeline_entries')\
    .select('''
        occurred_at,
        title,
        description,
        user:users(full_name)
    ''')\
    .eq('piano_id', piano_id)\
    .or_(
        'entry_type.eq.REPAIR,'
        'title.ilike.%problème%,'
        'title.ilike.%défaut%,'
        'title.ilike.%réparation%,'
        'description.ilike.%casser%,'
        'description.ilike.%réparer%'
    )\
    .order('occurred_at', desc=True)\
    .execute()
```

---

### 6.2 Pièces manquantes / à commander

**Exemples de questions:**
- "qu'est-ce qu'il me manque pour ce RV ?"
- "pièces à apporter"
- "matériel nécessaire"

**Intent détecté:** `parts_needed`

**Query Supabase:**
```python
# Chercher dans les notes du rendez-vous et timeline récente
appointment = supabase.table('gazelle_appointments')\
    .select('notes, piano_id')\
    .eq('id', appointment_id)\
    .single()\
    .execute()

# Chercher dans timeline pour mentions de pièces
parts_mentions = supabase.table('gazelle_timeline_entries')\
    .select('occurred_at, title, description')\
    .eq('piano_id', appointment.data['piano_id'])\
    .or_(
        'description.ilike.%manque%,'
        'description.ilike.%commander%,'
        'description.ilike.%apporter%,'
        'description.ilike.%prévoir%'
    )\
    .order('occurred_at', desc=True)\
    .limit(10)\
    .execute()
```

---

## 7. QUESTIONS SUR L'HUMIDITÉ

### 7.1 Mesures d'humidité récentes

**Exemples de questions:**
- "quel est le taux d'humidité de ce piano ?"
- "dernières mesures d'humidité"
- "historique humidité 2024"

**Intent détecté:** `humidity_readings`

**Query Supabase:**
```python
humidity = supabase.table('gazelle_timeline_entries')\
    .select('''
        occurred_at,
        description,
        user:users(full_name)
    ''')\
    .eq('piano_id', piano_id)\
    .eq('entry_type', 'PIANO_MEASUREMENT')\
    .order('occurred_at', desc=True)\
    .limit(10)\
    .execute()

# Parser les mesures depuis description
# Format attendu: "22°C, 37% humidité" ou similaire
```

**Format de réponse:**
```
💧 Mesures d'humidité pour Yamaha C3 (#1234567):

📅 2024-12-15 (Allan)
  🌡️ 22°C | 💧 42% | ✅ Normal

📅 2024-11-13 (Nicolas)
  🌡️ 23°C | 💧 38% | ⚠️ Un peu bas

📅 2024-10-06 (Jean-Philippe)
  🌡️ 21°C | 💧 45% | ✅ Normal

Tendance: Stable entre 38-45%
```

---

### 7.2 Alertes d'humidité

**Exemples de questions:**
- "y a-t-il des alertes d'humidité ?"
- "pianos à surveiller"
- "problèmes d'humidité non résolus"

**Intent détecté:** `humidity_alerts`

**Query Supabase:**
```python
alerts = supabase.table('humidity_alerts')\
    .select('''
        *,
        client:gazelle_clients(company_name),
        piano:gazelle_pianos(make, model, serial_number, location)
    ''')\
    .eq('resolved', False)\
    .order('observed_at', desc=True)\
    .execute()
```

---

## 8. QUESTIONS DE RECHERCHE SÉMANTIQUE

### 8.1 Recherche par similarité (embeddings)

**Exemples de questions:**
- "trouve-moi tous les cas similaires à celui-ci"
- "autres pianos avec le même problème"
- "clients qui ont eu ce type de réparation"

**Intent détecté:** `semantic_search`

**Implémentation:**
```python
from openai import OpenAI

# 1. Générer embedding de la requête
client = OpenAI()
query_embedding = client.embeddings.create(
    input=user_query,
    model="text-embedding-3-small"
).data[0].embedding

# 2. Recherche vectorielle dans Supabase (si pgvector activé)
results = supabase.rpc('match_timeline_entries', {
    'query_embedding': query_embedding,
    'match_threshold': 0.7,
    'match_count': 10
}).execute()

# Alternative: Recherche locale avec faiss/annoy si pas pgvector
```

---

## 9. ARCHITECTURE DE RÉPONSE

### 9.1 Flow de traitement d'une question

```
User Query
    ↓
[1] Intent Detection (OpenAI / regex)
    ↓
[2] Entity Extraction
    - Client name
    - Date range
    - Piano serial
    - Technician name
    ↓
[3] Database Query (Supabase)
    - Récupération des données
    - Jointures appropriées
    ↓
[4] Data Processing
    - Filtrage
    - Tri
    - Agrégation
    ↓
[5] Response Generation (OpenAI)
    - Format structuré
    - Selon FORMAT_RESUME_CLIENT.md
    ↓
[6] Return to User
```

---

### 9.2 Module Python pour V5

**Fichier: `modules/assistant/conversation_handler.py`**

```python
from typing import Dict, Any, List
from openai import OpenAI
from supabase import Client

class ConversationHandler:
    def __init__(self, supabase: Client, openai_client: OpenAI):
        self.supabase = supabase
        self.openai = openai_client

    async def process_query(self, query: str, user_id: str) -> Dict[str, Any]:
        """
        Point d'entrée principal pour traiter une question
        """
        # 1. Détecter l'intention
        intent = await self.detect_intent(query)

        # 2. Router vers le bon handler
        handlers = {
            'client_search': self.handle_client_search,
            'client_summary': self.handle_client_summary,
            'my_appointments': self.handle_my_appointments,
            'technician_appointments': self.handle_technician_appointments,
            'client_history': self.handle_client_history,
            'piano_search': self.handle_piano_search,
            # ... etc
        }

        handler = handlers.get(intent['type'], self.handle_generic)
        return await handler(query, intent, user_id)

    async def detect_intent(self, query: str) -> Dict[str, Any]:
        """
        Utilise OpenAI pour détecter l'intention de la requête
        """
        response = self.openai.chat.completions.create(
            model="gpt-4",
            messages=[
                {
                    "role": "system",
                    "content": """Tu es un système de détection d'intention.
                    Retourne un JSON avec:
                    - type: client_search | client_summary | my_appointments | etc.
                    - entities: {client_name, date_range, piano_serial, etc.}
                    """
                },
                {"role": "user", "content": query}
            ],
            response_format={"type": "json_object"}
        )

        return json.loads(response.choices[0].message.content)

    async def handle_client_summary(
        self,
        query: str,
        intent: Dict[str, Any],
        user_id: str
    ) -> Dict[str, Any]:
        """
        Génère un résumé complet d'un client
        """
        client_name = intent['entities'].get('client_name')

        # 1. Chercher le client
        client = self.supabase.table('gazelle_clients')\
            .select('''
                *,
                contacts:gazelle_contacts(*),
                pianos:gazelle_pianos(*)
            ''')\
            .ilike('company_name', f'%{client_name}%')\
            .single()\
            .execute()

        if not client.data:
            return {"error": "Client non trouvé"}

        # 2. Récupérer timeline
        piano_ids = [p['id'] for p in client.data['pianos']]

        timeline = self.supabase.table('gazelle_timeline_entries')\
            .select('''
                *,
                piano:gazelle_pianos(make, model, serial_number),
                user:users(full_name)
            ''')\
            .in_('piano_id', piano_ids)\
            .order('occurred_at', desc=True)\
            .limit(50)\
            .execute()

        # 3. Générer résumé structuré avec OpenAI
        summary = await self.generate_summary(client.data, timeline.data)

        return {
            "type": "client_summary",
            "client": client.data,
            "summary": summary
        }

    async def generate_summary(
        self,
        client_data: Dict,
        timeline_data: List[Dict]
    ) -> str:
        """
        Utilise OpenAI pour générer un résumé structuré
        """
        # Format selon FORMAT_RESUME_CLIENT.md
        prompt = f"""
        Génère un résumé structuré pour ce client selon ce format:

        🎹 Piano
        - [marque / modèle / série]
        - [localisation]
        - [particularités]

        🧰 État mécanique / sonore
        - [problèmes signalés]
        - [problèmes récurrents]

        💧 Humidité / entretien
        - [SEULEMENT anomalies]

        📅 Historique pertinent
        - [interventions importantes]

        🔜 Points à surveiller
        - [éléments à préparer]

        Données:
        {json.dumps(client_data, indent=2)}

        Timeline (50 dernières):
        {json.dumps(timeline_data, indent=2)}
        """

        response = self.openai.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "Tu es un assistant pour techniciens de piano."},
                {"role": "user", "content": prompt}
            ]
        )

        return response.choices[0].message.content
```

---

## 📋 CHECKLIST D'IMPLÉMENTATION POUR V5

### Phase 1: Core handlers
- [ ] `handle_client_search()` - Recherche de clients
- [ ] `handle_client_summary()` - Résumé complet
- [ ] `handle_my_appointments()` - Mes rendez-vous
- [ ] `handle_piano_search()` - Recherche de piano

### Phase 2: Advanced queries
- [ ] `handle_client_history()` - Historique d'interventions
- [ ] `handle_search_notes()` - Recherche dans les notes
- [ ] `handle_humidity_readings()` - Mesures d'humidité
- [ ] `handle_unpaid_invoices()` - Factures impayées

### Phase 3: Technician features
- [ ] `handle_technician_appointments()` - RV d'autres techs
- [ ] `handle_parts_needed()` - Pièces manquantes
- [ ] `handle_recurring_issues()` - Problèmes récurrents

### Phase 4: Analytics & AI
- [ ] `handle_semantic_search()` - Recherche sémantique
- [ ] `handle_trends_analysis()` - Analyse de tendances
- [ ] `handle_recommendations()` - Recommandations AI

---

## 🎯 RÉSUMÉ POUR CURSOR MAC

**Pour implémenter l'assistant conversationnel V5:**

1. **Créer `modules/assistant/conversation_handler.py`** avec la classe `ConversationHandler`

2. **Implémenter les 15 handlers de base** (voir checklist)

3. **Utiliser les queries Supabase** documentées dans ce guide

4. **Suivre le format de réponse** selon `FORMAT_RESUME_CLIENT.md`

5. **Intégrer OpenAI** pour:
   - Détection d'intention
   - Génération de résumés
   - Recherche sémantique (embeddings)

6. **Tester chaque type de question** avec des exemples réels

---

**Créé:** 2025-12-25
**Par:** Claude Code (Windows)
**Pour:** Cursor Mac - Implémentation assistant conversationnel V5
