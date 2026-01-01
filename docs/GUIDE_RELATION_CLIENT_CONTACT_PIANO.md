# Guide: Relation Client ↔ Contact ↔ Piano

**Date:** 2025-12-25
**Pour:** Cursor Mac
**Problème:** Confusion entre Client et Contact dans les queries

---

## 🎯 COMPRENDRE LA STRUCTURE

### Schéma de base:

```
CLIENT (Entreprise/Institution)
  └─ CONTACT (Personne physique) [1 à plusieurs]
  └─ PIANO (Instrument) [0 à plusieurs]
       └─ TIMELINE ENTRY (Historique) [0 à plusieurs]
```

### Tables Supabase:

1. **gazelle_clients** - Les entreprises/institutions
   - `id` (PK)
   - `company_name` (ex: "École de musique Vincent-d'Indy")
   - `address`, `phone`, etc.

2. **gazelle_contacts** - Les personnes physiques
   - `id` (PK)
   - `client_id` (FK → gazelle_clients.id) ← **CRITICAL**
   - `full_name` (ex: "Anne-Marie Denoncourt")
   - `email`, `phone`

3. **gazelle_pianos** - Les instruments
   - `id` (PK)
   - `client_id` (FK → gazelle_clients.id) ← **CRITICAL**
   - `make`, `model`, `serial_number`

4. **gazelle_timeline_entries** - L'historique
   - `id` (PK)
   - `piano_id` (FK → gazelle_pianos.id) ← **CRITICAL**
   - `user_id` (FK → users.gazelle_user_id)
   - `occurred_at`, `entry_type`, `title`, `description`

---

## 🔍 EXEMPLES CONCRETS

### Exemple 1: École de musique Vincent-d'Indy

```sql
-- CLIENT
SELECT * FROM gazelle_clients WHERE company_name ILIKE '%Vincent%';

-- Résultat:
-- id: cli_xyz123
-- company_name: École de musique Vincent-d'Indy
-- address: 628 Chemin de la Côte-Sainte-Catherine

-- CONTACTS de ce client
SELECT * FROM gazelle_contacts WHERE client_id = 'cli_xyz123';

-- Résultats:
-- id: con_abc456 | full_name: Anne-Marie Denoncourt | email: anne-marie@vincentdindy.ca
-- id: con_def789 | full_name: Autre Personne | email: autre@vincentdindy.ca

-- PIANOS de ce client
SELECT * FROM gazelle_pianos WHERE client_id = 'cli_xyz123';

-- Résultats:
-- id: pia_111 | make: Yamaha | model: C3 | serial_number: 1234567
-- id: pia_222 | make: Steinway | model: D | serial_number: 7654321

-- TIMELINE ENTRIES pour les pianos de ce client
SELECT * FROM gazelle_timeline_entries
WHERE piano_id IN ('pia_111', 'pia_222')
ORDER BY occurred_at DESC;
```

---

## ❌ ERREURS FRÉQUENTES

### Erreur 1: Chercher client_id dans gazelle_clients

```python
# ❌ FAUX - gazelle_clients n'a pas de colonne "client_id"
result = supabase.table('gazelle_clients')\
    .select('*')\
    .eq('client_id', 'cli_xyz')\
    .execute()
```

**Pourquoi c'est faux:** `gazelle_clients.id` EST déjà l'ID du client!

```python
# ✅ CORRECT
result = supabase.table('gazelle_clients')\
    .select('*')\
    .eq('id', 'cli_xyz')\
    .execute()
```

---

### Erreur 2: Chercher une personne sans joindre le client

```python
# ❌ INCOMPLET - Tu as le nom mais pas l'entreprise
result = supabase.table('gazelle_contacts')\
    .select('full_name, email')\
    .ilike('full_name', '%Anne-Marie%')\
    .execute()

# Résultat: Tu sais c'est "Anne-Marie" mais pas où elle travaille
```

```python
# ✅ CORRECT - Inclure le client
result = supabase.table('gazelle_contacts')\
    .select('*, client:gazelle_clients(*)')\
    .ilike('full_name', '%Anne-Marie%')\
    .execute()

# Résultat: Tu as Anne-Marie ET son entreprise (Vincent-d'Indy)
```

---

### Erreur 3: Chercher timeline d'un client directement

```python
# ❌ FAUX - Timeline entries ne sont PAS liées directement au client
result = supabase.table('gazelle_timeline_entries')\
    .select('*')\
    .eq('client_id', 'cli_xyz')\
    .execute()
```

**Pourquoi c'est faux:** Timeline entries sont liées aux **PIANOS**, pas aux clients!

```python
# ✅ CORRECT - En 2 étapes
# 1. Récupérer les pianos du client
pianos = supabase.table('gazelle_pianos')\
    .select('id')\
    .eq('client_id', 'cli_xyz')\
    .execute()

piano_ids = [p['id'] for p in pianos.data]

# 2. Récupérer timeline entries de ces pianos
timeline = supabase.table('gazelle_timeline_entries')\
    .select('*, piano:gazelle_pianos(make, model, serial_number)')\
    .in_('piano_id', piano_ids)\
    .execute()
```

---

## 🎓 EXERCICES PRATIQUES

### Exercice 1: Trouver tous les contacts de Vincent-d'Indy

```python
# Étape 1: Trouver l'ID du client
client = supabase.table('gazelle_clients')\
    .select('id')\
    .ilike('company_name', '%Vincent%')\
    .execute()

client_id = client.data[0]['id']

# Étape 2: Trouver les contacts
contacts = supabase.table('gazelle_contacts')\
    .select('full_name, email, phone')\
    .eq('client_id', client_id)\
    .execute()

for contact in contacts.data:
    print(f"{contact['full_name']} - {contact['email']}")
```

**OU en 1 seule query avec jointure:**

```python
# Plus élégant: Joindre tout en 1 query
result = supabase.table('gazelle_clients')\
    .select('company_name, contacts:gazelle_contacts(full_name, email, phone)')\
    .ilike('company_name', '%Vincent%')\
    .execute()

client = result.data[0]
print(f"Client: {client['company_name']}")
for contact in client['contacts']:
    print(f"  - {contact['full_name']} ({contact['email']})")
```

---

### Exercice 2: Résumé complet d'un client (comme V4)

**Objectif:** Récupérer client + contacts + pianos + timeline entries

```python
def get_client_summary(client_id: str):
    """Résumé complet d'un client avec pianos et historique"""

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

    if not client.data:
        return None

    # 2. Timeline entries pour les pianos de ce client
    piano_ids = [p['id'] for p in client.data['pianos']]

    timeline = []
    if piano_ids:
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

    # 3. Assembler le résumé
    return {
        'client': client.data,
        'timeline': timeline.data if timeline else []
    }

# Utilisation
summary = get_client_summary('cli_xyz123')
print(f"Client: {summary['client']['company_name']}")
print(f"Contacts: {len(summary['client']['contacts'])}")
print(f"Pianos: {len(summary['client']['pianos'])}")
print(f"Timeline entries: {len(summary['timeline'])}")
```

---

## 📋 CHECKLIST DE VALIDATION

Cursor Mac, tu as compris si tu peux répondre OUI à ces questions:

- [ ] Je sais que `gazelle_clients.id` est la clé primaire (pas "client_id")
- [ ] Je sais que `gazelle_contacts.client_id` pointe vers `gazelle_clients.id`
- [ ] Je sais que `gazelle_pianos.client_id` pointe vers `gazelle_clients.id`
- [ ] Je sais que `gazelle_timeline_entries.piano_id` pointe vers `gazelle_pianos.id`
- [ ] Je sais que timeline entries ne sont PAS liées directement aux clients
- [ ] Je sais utiliser `.select('*, client:gazelle_clients(*)')` pour joindre
- [ ] Je sais qu'un client peut avoir plusieurs contacts ET plusieurs pianos
- [ ] Je sais qu'un piano peut avoir plusieurs timeline entries

---

## 🧪 QUERY DE TEST

**Exécute cette query pour vérifier ta compréhension:**

```python
# Test complet: Trouver Anne-Marie avec toutes les infos
result = supabase.table('gazelle_contacts')\
    .select('''
        id,
        full_name,
        email,
        phone,
        client:gazelle_clients(
            id,
            company_name,
            address,
            pianos:gazelle_pianos(
                id,
                make,
                model,
                serial_number
            )
        )
    ''')\
    .ilike('full_name', '%Anne-Marie%')\
    .execute()

# Affichage structuré
for contact in result.data:
    print(f"\n🧑 Contact: {contact['full_name']}")
    print(f"   Email: {contact['email']}")
    print(f"\n🏢 Entreprise: {contact['client']['company_name']}")
    print(f"   Adresse: {contact['client']['address']}")
    print(f"\n🎹 Pianos de cette entreprise:")
    for piano in contact['client']['pianos']:
        print(f"   - {piano['make']} {piano['model']} (#{piano['serial_number']})")
```

**Résultat attendu:**
```
🧑 Contact: Anne-Marie Denoncourt
   Email: anne-marie@vincentdindy.ca

🏢 Entreprise: École de musique Vincent-d'Indy
   Adresse: 628 Chemin de la Côte-Sainte-Catherine

🎹 Pianos de cette entreprise:
   - Yamaha C3 (#1234567)
   - Steinway D (#7654321)
   - Kawai GL-10 (#9876543)
```

---

## 🚀 APPLICATION: Résumé Client pour Assistant V5

**Fonction complète pour générer un résumé client:**

```python
async def generate_client_summary(client_id: str) -> str:
    """
    Génère un résumé structuré d'un client pour l'assistant conversationnel
    Équivalent V5 de la fonction V4 get_client_summary()
    """

    # 1. Récupérer client avec contacts et pianos
    client_result = supabase.table('gazelle_clients')\
        .select('''
            *,
            contacts:gazelle_contacts(full_name, email, phone),
            pianos:gazelle_pianos(id, make, model, serial_number, location)
        ''')\
        .eq('id', client_id)\
        .single()\
        .execute()

    if not client_result.data:
        return "Client non trouvé"

    client = client_result.data

    # 2. Récupérer timeline entries des pianos de ce client
    piano_ids = [p['id'] for p in client['pianos']]

    timeline_entries = []
    if piano_ids:
        timeline_result = supabase.table('gazelle_timeline_entries')\
            .select('''
                occurred_at,
                entry_type,
                title,
                description,
                piano:gazelle_pianos(make, model, serial_number),
                user:users(full_name)
            ''')\
            .in_('piano_id', piano_ids)\
            .order('occurred_at', desc=True)\
            .limit(50)\
            .execute()

        timeline_entries = timeline_result.data

    # 3. Formater le résumé selon FORMAT_RESUME_CLIENT.md
    summary = f"## 🏢 {client['company_name']}\n\n"

    # Contacts
    summary += "### 👥 Contacts\n"
    for contact in client['contacts']:
        summary += f"- {contact['full_name']}"
        if contact['email']:
            summary += f" ({contact['email']})"
        summary += "\n"

    # Pianos
    summary += f"\n### 🎹 Pianos ({len(client['pianos'])})\n"
    for piano in client['pianos']:
        summary += f"- {piano['make']} {piano['model']} (#{piano['serial_number']})"
        if piano.get('location'):
            summary += f" - {piano['location']}"
        summary += "\n"

    # Timeline récente
    summary += f"\n### 📅 Historique récent ({len(timeline_entries)} entrées)\n"
    for entry in timeline_entries[:10]:  # Top 10
        date = entry['occurred_at'][:10]  # YYYY-MM-DD
        piano_info = f"{entry['piano']['make']} {entry['piano']['model']}"
        tech = entry['user']['full_name'] if entry.get('user') else "N/A"
        summary += f"- {date} | {piano_info} | {tech}\n"
        if entry.get('title'):
            summary += f"  {entry['title']}\n"

    return summary
```

---

## 📝 RÉSUMÉ EN 3 POINTS

1. **CLIENT** = Entreprise (gazelle_clients.id)
2. **CONTACT** = Personne qui travaille pour le client (gazelle_contacts.client_id → gazelle_clients.id)
3. **TIMELINE** = Historique d'un PIANO, pas d'un client (gazelle_timeline_entries.piano_id → gazelle_pianos.id → gazelle_clients.id)

**Pour avoir la timeline d'un client:** Client → Pianos → Timeline Entries (2 jointures!)

---

**Créé:** 2025-12-25
**Par:** Claude Code (Windows)
**Pour:** Cursor Mac - Compréhension de la structure relationnelle
