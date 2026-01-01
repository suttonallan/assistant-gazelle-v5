# Corrections Basées sur le Schéma Réel Supabase

**Date:** 2025-12-25
**Source:** Informations vérifiées par Gemini sur la base Supabase réelle
**Status:** ✅ Corrections appliquées

---

## 🎯 Problème Initial

Claude devinait les noms de colonnes et la structure du schéma au lieu d'utiliser la structure **réelle et vérifiée** de Supabase.

## ✅ Informations Vérifiées par Gemini

### Tables (Schéma public)

```
public.gazelle_clients
public.gazelle_pianos
public.gazelle_contacts
public.gazelle_timeline_entries
```

**IMPORTANT:** Schéma `public.` (pas `gazelle.`)

### Exemple Réel: Monique Hallé

- **external_id:** `cli_Pc300Ybqvve64xcF`
- **ID interne:** `202`
- Apparaît comme 'contact' ET comme 'client'

### Jointures Critiques

#### 1. Piano → Client
```sql
-- CORRECT:
public.gazelle_pianos.client_external_id = public.gazelle_clients.external_id

-- INCORRECT (ce que je supposais):
pianos.client_id = clients.id
```

#### 2. Timeline → Piano (quand entity_type = 'Piano')
```sql
-- CORRECT:
timeline_entries.entity_id = pianos.id  -- ID numérique (INT)
AND timeline_entries.entity_type = 'Piano'

-- INCORRECT:
timeline_entries.piano_id = pianos.id
```

#### 3. Timeline → Client (quand entity_type = 'Client')
```sql
-- CORRECT:
timeline_entries.entity_id = clients.external_id  -- STRING
AND timeline_entries.entity_type = 'Client'

-- INCORRECT:
timeline_entries.client_id = clients.id
```

### Colonnes Spécifiques

#### Table: gazelle_pianos
```sql
-- CORRECT:
p.brand

-- INCORRECT:
p.make
```

#### Table: gazelle_clients
```sql
-- CORRECT:
c.company_name

-- INCORRECT:
c.first_name  -- N'existe PAS dans clients
```

#### Table: gazelle_contacts
```sql
-- CORRECT:
ct.first_name
ct.last_name
ct.first_name || ' ' || ct.last_name AS full_name

-- INCORRECT:
ct.full_name  -- N'existe PAS dans contacts
```

---

## 🛠️ Corrections Appliquées

### 1. Fichier: `sql/create_gazelle_views.sql`

#### Vue 1: gazelle_client_timeline

**Changements:**
```sql
-- AVANT:
FROM gazelle.timeline_entries t
INNER JOIN gazelle.pianos p ON t.piano_id = p.id
INNER JOIN gazelle.clients c ON p.client_id = c.id
LEFT JOIN gazelle.contacts ct ON ct.client_id = c.id

-- APRÈS:
FROM public.gazelle_timeline_entries t
INNER JOIN public.gazelle_pianos p ON (t.entity_id = p.id AND t.entity_type = 'Piano')
INNER JOIN public.gazelle_clients c ON p.client_external_id = c.external_id
LEFT JOIN public.gazelle_contacts ct ON ct.client_id = c.id
```

**Colonnes corrigées:**
```sql
-- Piano
p.brand as piano_brand  -- (pas p.make)

-- Contact
ct.first_name as contact_first_name
ct.last_name as contact_last_name
-- (pas ct.full_name)

-- Search text
COALESCE(ct.first_name || ' ' || ct.last_name, '') || ' ' || ...
-- (pas ct.full_name)
```

#### Vue 2: gazelle_client_search

**Changements:**
```sql
-- AVANT:
FROM gazelle.contacts ct
LEFT JOIN gazelle.clients c ON ct.client_id = c.id
(SELECT COUNT(*) FROM gazelle.pianos p WHERE p.client_id = c.id)

-- APRÈS:
FROM public.gazelle_contacts ct
LEFT JOIN public.gazelle_clients c ON ct.client_id = c.id
(SELECT COUNT(*) FROM public.gazelle_pianos p WHERE p.client_external_id = c.external_id)
```

**Colonnes corrigées:**
```sql
-- Contact
ct.first_name || ' ' || ct.last_name as display_name
-- (pas ct.full_name)

-- Client
c.external_id as client_external_id  -- AJOUTÉ
```

#### Vue 3: gazelle_piano_list

**Changements:**
```sql
-- AVANT:
FROM gazelle.pianos p
INNER JOIN gazelle.clients c ON p.client_id = c.id

-- APRÈS:
FROM public.gazelle_pianos p
INNER JOIN public.gazelle_clients c ON p.client_external_id = c.external_id
```

**Colonnes corrigées:**
```sql
-- Piano
p.brand  -- (pas p.make)

-- Contact
(SELECT ct.first_name || ' ' || ct.last_name FROM ...)
-- (pas ct.full_name)

-- Timeline count
(SELECT COUNT(*) FROM public.gazelle_timeline_entries t
 WHERE t.entity_id = p.id AND t.entity_type = 'Piano')
-- (pas t.piano_id = p.id)
```

### 2. Fichier: `modules/assistant/services/queries_v6_gazelle.py`

**Changements:**
```python
# AVANT:
print(f"Piano: {first.get('piano_make')} {first.get('piano_model')}")
print(f"- {piano.get('make')} {piano.get('model')}")

# APRÈS:
print(f"Piano: {first.get('piano_brand')} {first.get('piano_model')}")
print(f"- {piano.get('brand')} {piano.get('model')}")
```

---

## 📊 Structure entity_type Expliquée

La table `gazelle_timeline_entries` utilise un pattern **polymorphique**:

```sql
timeline_entries:
  - entity_id   (VARIANT - peut être INT ou STRING)
  - entity_type (ENUM - 'Piano', 'Client', 'Contact', etc.)
```

### Logique:

```sql
IF entity_type = 'Piano'
  THEN entity_id → pianos.id (INT)

IF entity_type = 'Client'
  THEN entity_id → clients.external_id (STRING)

IF entity_type = 'Contact'
  THEN entity_id → contacts.id (INT)
```

### Requête Correcte pour Timeline Complète:

```sql
-- Timeline via Pianos
SELECT ... FROM public.gazelle_timeline_entries t
INNER JOIN public.gazelle_pianos p ON (t.entity_id = p.id AND t.entity_type = 'Piano')
INNER JOIN public.gazelle_clients c ON p.client_external_id = c.external_id
WHERE c.external_id = 'cli_Pc300Ybqvve64xcF'

UNION ALL

-- Timeline directement liée au client
SELECT ... FROM public.gazelle_timeline_entries t
WHERE t.entity_type = 'Client'
  AND t.entity_id = 'cli_Pc300Ybqvve64xcF'

ORDER BY created_at DESC;
```

---

## 🧪 Test SQL Créé

**Fichier:** `sql/test_monique_halle.sql`

Contient des requêtes de test pour:
1. Vérifier que Monique Hallé existe (clients + contacts)
2. Trouver ses pianos (via client_external_id)
3. Trouver la timeline de ses pianos (via entity_id + entity_type)
4. Compter les entrées de timeline
5. Vérifier les autres types d'entity_type
6. Vue complète unifiée (Piano + Client timeline)

**Utilisation:**
```bash
# Dans Supabase SQL Editor, exécuter les requêtes de test_monique_halle.sql
# Devrait retourner:
# - Monique Hallé dans clients/contacts
# - Ses pianos
# - Sa timeline complète
```

---

## ✅ Checklist de Validation

### Structure SQL
- [x] Schéma `public.` utilisé (pas `gazelle.`)
- [x] Jointure Piano→Client via `client_external_id = external_id`
- [x] Jointure Timeline→Piano via `entity_id + entity_type`
- [x] Colonne `brand` utilisée (pas `make`)
- [x] Colonnes `first_name + last_name` utilisées (pas `full_name`)
- [x] `client_external_id` ajouté dans toutes les vues

### Code Python
- [x] `piano_brand` utilisé (pas `piano_make`)
- [x] `brand` utilisé dans affichage piano (pas `make`)

### Tests
- [x] Fichier test SQL créé pour Monique Hallé
- [ ] Tests exécutés dans Supabase (à faire par l'utilisateur)
- [ ] Vues créées dans Supabase (à faire par l'utilisateur)
- [ ] Code v6 activé et testé (à faire par l'utilisateur)

---

## 🚀 Prochaines Étapes

### 1. Créer les vues dans Supabase (10 min)

```bash
# Ouvrir Supabase Dashboard → SQL Editor
# Exécuter: assistant-v6/sql/create_gazelle_views.sql
```

### 2. Tester avec Monique Hallé (5 min)

```bash
# Dans Supabase SQL Editor
# Exécuter: assistant-v6/sql/test_monique_halle.sql
# Vérifier que les résultats apparaissent
```

### 3. Activer v6 (2 min)

```python
# Dans assistant-v6/api/assistant_v6.py
from modules.assistant.services.queries_v6_gazelle import (
    QueriesServiceV6Gazelle as QueriesServiceV6
)
```

### 4. Tester l'API (5 min)

```bash
cd assistant-v6/api
python3 assistant_v6.py

# Dans un autre terminal:
curl -X POST 'http://localhost:8001/v6/assistant/chat' \
  -H 'Content-Type: application/json' \
  -d '{"question":"montre-moi l'\''historique de Monique Hallé"}'
```

**Résultat attendu:**
- ✅ Monique Hallé trouvée
- ✅ Ses pianos listés
- ✅ Timeline complète affichée (via pianos)
- ✅ Aucune erreur de colonne manquante

---

## 📝 Leçons Apprises

### ❌ Ne JAMAIS deviner:
- Noms de colonnes
- Structure de jointure
- Schéma des tables

### ✅ TOUJOURS vérifier:
- Structure réelle dans Supabase
- Tester avec des données réelles
- Utiliser des external_id quand ils existent
- Comprendre le pattern polymorphique (entity_id + entity_type)

### 🎯 Approche Correcte:
1. Demander/vérifier la structure réelle
2. Tester avec un cas concret (Monique Hallé)
3. Documenter les corrections
4. Créer des tests SQL reproductibles

---

**Fichiers Modifiés:**
1. `sql/create_gazelle_views.sql` - Vues SQL corrigées
2. `modules/assistant/services/queries_v6_gazelle.py` - Code Python corrigé
3. `sql/test_monique_halle.sql` - Tests SQL créés
4. `CORRECTIONS_SCHEMA_REEL.md` - Ce document

**Status:** ✅ Prêt pour déploiement avec schéma réel vérifié
