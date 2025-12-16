# 🔧 AIDE - SYNC CONTACTS GAZELLE API

**Date:** 2025-12-15
**Pour:** Cursor Mac
**Priorité:** ⚠️ IMPORTANTE (pour recherche complète)

---

## 🚨 CONTEXTE

**Problème identifié par Allan:** Confusion entre "clients" et "contacts"

**Réalité:**
- ✅ `gazelle_clients` - 1,000 enregistrements synchronisés
- ⚠️ `gazelle_contacts` - **0 enregistrements** (table créée mais vide)

**Impact:**
- Recherche "Cherche Yannick" ✅ Fonctionne (client)
- Recherche "Cherche anne-marie" ❌ Ne fonctionne pas (probablement un contact)

**Correction appliquée:**
- ✅ Code modifié dans `modules/assistant/services/queries.py`
- ✅ Cherche maintenant dans `gazelle_clients` ET `gazelle_contacts`
- ⚠️ Mais `gazelle_contacts` est vide → besoin sync

---

## 📋 RÉFÉRENCE SCRIPT V4

### Dans `import_daily_update_v4_reference.py`:

Le script V4 importe clients ET contacts. Chercher la section contacts.

**Variables utilisées (similaires aux clients):**

```python
# Dans V4 (lignes à trouver):
contacts_query = "query($first: Int, $after: String) { ... }"
contacts_data = fetch_paginated_data(contacts_query, "allContacts")

for contact in contacts_data:
    contact_id = contact.get('id')
    client_id = (contact.get('client') or {}).get('id')
    first_name = contact.get('firstName')
    last_name = contact.get('lastName')
    email = contact.get('email')
    phone = contact.get('phone')
    role = contact.get('role')
    is_primary = contact.get('isPrimary')
```

---

## ✅ SOLUTION RECOMMANDÉE

### Option 1: Copier logique V4 (RECOMMANDÉ)

**Étapes:**

1. **Ouvrir `import_daily_update_v4_reference.py`**
   ```bash
   # Fichier déjà copié par Claude Windows
   modules/sync_gazelle/import_daily_update_v4_reference.py
   ```

2. **Chercher section contacts**
   - Rechercher `contact` dans le fichier
   - Identifier la query GraphQL utilisée
   - Noter les champs récupérés

3. **Copier dans `sync_to_supabase.py`**

   Ajouter fonction `sync_contacts()` (similaire à `sync_clients()`):

   ```python
   def sync_contacts(self):
       """Synchronise les contacts depuis Gazelle API vers Supabase"""
       print("\n📋 Synchronisation des contacts...")

       # 1. Récupérer depuis API Gazelle
       # COPIER EXACTEMENT LA LOGIQUE V4
       api_contacts = self.api_client.get_contacts(limit=2000)
       print(f"✅ {len(api_contacts)} contacts récupérés depuis l'API")

       # 2. Insérer dans Supabase
       for contact in api_contacts:
           contact_data = {
               'id': contact.get('id'),
               'client_id': contact.get('clientId'),  # FK vers gazelle_clients
               'first_name': contact.get('firstName'),
               'last_name': contact.get('lastName'),
               'email': contact.get('email'),
               'phone': contact.get('phone'),
               'role': contact.get('role'),
               'is_primary': contact.get('isPrimary', False)
           }

           # UPSERT dans Supabase
           self.supabase_client.upsert_contact(contact_data)

       print(f"✅ {len(api_contacts)} contacts synchronisés")
   ```

4. **Adapter seulement la DB**
   - V4 utilise: `pyodbc` → SQL Server
   - V5 utilise: `psycopg2` → PostgreSQL (Supabase)
   - Garder EXACTEMENT la même logique API

---

### Option 2: API GraphQL Direct

**Si vous ne trouvez pas la section contacts dans V4:**

**Query GraphQL:**

```graphql
query($first: Int, $after: String) {
  allContacts(first: $first, after: $after) {
    nodes {
      id
      client {
        id
      }
      firstName
      lastName
      email
      phone
      role
      isPrimary
      createdAt
      updatedAt
    }
    pageInfo {
      hasNextPage
      endCursor
    }
  }
}
```

**Variables:**

```python
variables = {
    "first": 100,
    "after": None  # Pour pagination
}
```

**Code complet:**

```python
def get_contacts(self, limit: int = 1000) -> List[Dict]:
    """
    Récupère les contacts depuis Gazelle API GraphQL
    """
    query = """
    query($first: Int, $after: String) {
      allContacts(first: $first, after: $after) {
        nodes {
          id
          client { id }
          firstName
          lastName
          email
          phone
          role
          isPrimary
        }
        pageInfo {
          hasNextPage
          endCursor
        }
      }
    }
    """

    all_contacts = []
    cursor = None
    page_size = min(100, limit)

    while len(all_contacts) < limit:
        variables = {"first": page_size, "after": cursor}
        result = self._execute_query(query, variables)

        connection = result.get('data', {}).get('allContacts', {})
        nodes = connection.get('nodes', [])

        if not nodes:
            break

        for node in nodes:
            all_contacts.append({
                'id': node.get('id'),
                'clientId': node.get('client', {}).get('id'),
                'firstName': node.get('firstName'),
                'lastName': node.get('lastName'),
                'email': node.get('email'),
                'phone': node.get('phone'),
                'role': node.get('role'),
                'isPrimary': node.get('isPrimary', False)
            })

        page_info = connection.get('pageInfo', {})
        if not page_info.get('hasNextPage'):
            break
        cursor = page_info.get('endCursor')

    return all_contacts[:limit]
```

---

## 📊 SCHÉMA TABLE `gazelle_contacts`

**Table Supabase (déjà créée):**

```sql
CREATE TABLE IF NOT EXISTS public.gazelle_contacts (
    id TEXT PRIMARY KEY,
    client_id TEXT REFERENCES gazelle_clients(id),  -- ← FK vers clients
    first_name TEXT,
    last_name TEXT,
    email TEXT,
    phone TEXT,
    role TEXT,
    is_primary BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

**Mapping API → Supabase:**

| Champ API Gazelle | Type | Colonne Supabase | Notes |
|-------------------|------|------------------|-------|
| `id` | String | `id` | Clé primaire |
| `client.id` | String | `client_id` | FK vers `gazelle_clients` |
| `firstName` | String | `first_name` | Prénom |
| `lastName` | String | `last_name` | Nom |
| `email` | String | `email` | Email |
| `phone` | String | `phone` | Téléphone |
| `role` | String | `role` | Rôle (assistant, secrétaire, etc.) |
| `isPrimary` | Boolean | `is_primary` | Contact principal? |

---

## 🔍 EXEMPLE DE DONNÉES

**API Response:**

```json
{
  "data": {
    "allContacts": {
      "nodes": [
        {
          "id": "con_abc123",
          "client": {
            "id": "cli_xyz789"
          },
          "firstName": "Anne-Marie",
          "lastName": "Tremblay",
          "email": "am.tremblay@example.com",
          "phone": "514-555-1234",
          "role": "Assistante personnelle",
          "isPrimary": true
        }
      ],
      "pageInfo": {
        "hasNextPage": false,
        "endCursor": null
      }
    }
  }
}
```

**Insertion Supabase:**

```python
contact_data = {
    'id': 'con_abc123',
    'client_id': 'cli_xyz789',  # → Lien vers gazelle_clients
    'first_name': 'Anne-Marie',
    'last_name': 'Tremblay',
    'email': 'am.tremblay@example.com',
    'phone': '514-555-1234',
    'role': 'Assistante personnelle',
    'is_primary': True
}

# UPSERT (INSERT or UPDATE)
cursor.execute("""
    INSERT INTO gazelle_contacts
    (id, client_id, first_name, last_name, email, phone, role, is_primary)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    ON CONFLICT (id) DO UPDATE SET
        first_name = EXCLUDED.first_name,
        last_name = EXCLUDED.last_name,
        email = EXCLUDED.email,
        phone = EXCLUDED.phone,
        role = EXCLUDED.role,
        is_primary = EXCLUDED.is_primary,
        updated_at = NOW()
""", (
    contact_data['id'],
    contact_data['client_id'],
    contact_data['first_name'],
    contact_data['last_name'],
    contact_data['email'],
    contact_data['phone'],
    contact_data['role'],
    contact_data['is_primary']
))
```

---

## ✅ VALIDATION

### Tests après sync:

1. **Vérifier nombre de contacts:**
   ```sql
   SELECT COUNT(*) FROM gazelle_contacts;
   -- Devrait retourner > 0
   ```

2. **Vérifier exemples:**
   ```sql
   SELECT * FROM gazelle_contacts LIMIT 10;
   ```

3. **Vérifier liens clients:**
   ```sql
   SELECT
       c.first_name || ' ' || c.last_name AS contact_name,
       c.role,
       gc.company_name AS client_company,
       gc.first_name || ' ' || gc.last_name AS client_name
   FROM gazelle_contacts c
   LEFT JOIN gazelle_clients gc ON c.client_id = gc.id
   LIMIT 10;
   ```

4. **Tester recherche assistant:**
   ```bash
   curl -X POST http://localhost:8000/assistant/chat \
     -H "Content-Type: application/json" \
     -d '{"question": "Cherche anne-marie"}'
   ```

   **Résultat attendu:**
   ```json
   {
     "response": "J'ai trouvé Anne-Marie Tremblay, assistante personnelle de Yannick Nézet-Séguin",
     "data": {
       "first_name": "Anne-Marie",
       "last_name": "Tremblay",
       "role": "Assistante personnelle",
       "client_name": "Yannick Nézet-Séguin",
       "_source": "contact"
     }
   }
   ```

---

## 🎯 PLAN D'ACTION

### Étape 1: Lire script V4 ✅
```bash
# Fichier déjà disponible
modules/sync_gazelle/import_daily_update_v4_reference.py
```

### Étape 2: Identifier logique contacts
- Chercher `contact` dans le fichier
- Noter query GraphQL
- Noter parsing des données

### Étape 3: Implémenter dans V5
**Fichier:** `modules/sync_gazelle/sync_to_supabase.py`

**Fonction à ajouter:**
```python
def sync_contacts(self):
    # COPIER LOGIQUE V4
    # Adapter seulement: pyodbc → psycopg2
    pass
```

### Étape 4: Ajouter dans `sync_all()`
```python
def sync_all(self):
    self.sync_clients()  # ✅ Déjà fonctionnel
    self.sync_contacts()  # ← AJOUTER ICI
    self.sync_pianos()   # ✅ Déjà fonctionnel
    # self.sync_appointments()  # ⚠️ Bloqué
```

### Étape 5: Tester
```bash
python modules/sync_gazelle/sync_to_supabase.py
```

### Étape 6: Valider
```sql
SELECT COUNT(*) FROM gazelle_contacts;
```

### Étape 7: Tester recherche
```bash
curl -X POST http://localhost:8000/assistant/chat \
  -d '{"question": "Cherche anne-marie"}'
```

---

## 💡 NOTES IMPORTANTES

1. **Relation client_id:**
   - Chaque contact est lié à UN client
   - FK: `gazelle_contacts.client_id` → `gazelle_clients.id`
   - Vérifier que le client existe avant d'insérer le contact

2. **Contact primaire:**
   - `is_primary = true` indique le contact principal du client
   - Peut y avoir plusieurs contacts par client
   - Exemple: Secrétaire + Assistant + Conjoint

3. **Pagination:**
   - Utiliser même pattern que clients
   - 100 contacts par page recommandé
   - Boucle while + cursor jusqu'à `hasNextPage = false`

4. **Déduplication:**
   - Utiliser `ON CONFLICT (id) DO UPDATE`
   - Met à jour si contact existe déjà
   - Permet resync quotidien sans erreur

---

## 🔥 PRIORITÉ

**Urgence:** ⚠️ MOYENNE

**Bloqueurs:**
- Recherche de personnes comme "anne-marie" ne fonctionne pas
- Assistant incomplet sans contacts

**Temps estimé:** 1-2 heures

**Dépendances:**
- ✅ Table `gazelle_contacts` créée
- ✅ Code recherche modifié (`queries.py`)
- ⏳ Besoin sync API Gazelle → Supabase

**Après contacts synchronisés:**
- ✅ Recherche complète clients + contacts
- ✅ Assistant pleinement fonctionnel pour recherches personnes
- ⏳ Reste: sync appointments, timeline

---

**Créé:** 2025-12-15 10:45 EST
**Par:** Claude Code (Windows)
**Pour:** Cursor Mac
**Statut:** 📋 PRÊT POUR IMPLÉMENTATION
