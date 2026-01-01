# Test de compréhension: Relation Client ↔ Contact

## Pour Cursor Mac: Exécute ces queries pour vérifier ta compréhension

### Test 1: Trouver un contact avec son client

```python
from supabase import create_client
import os

supabase = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_KEY'))

# Chercher "Anne-Marie" et afficher son entreprise
result = supabase.table('gazelle_contacts')\
    .select('*, client:gazelle_clients(*)')\
    .ilike('full_name', '%Anne-Marie%')\
    .limit(5)\
    .execute()

for contact in result.data:
    print(f"Contact: {contact['full_name']}")
    print(f"  → Entreprise: {contact['client']['company_name']}")
    print(f"  → Client ID: {contact['client_id']}")
    print()
```

**Résultat attendu:**
```
Contact: Anne-Marie Denoncourt
  → Entreprise: École de musique Vincent-d'Indy
  → Client ID: cli_xyz...
```

---

### Test 2: Trouver tous les contacts d'un client

```python
# Chercher Vincent-d'Indy et lister tous ses contacts
result = supabase.table('gazelle_clients')\
    .select('*, contacts:gazelle_contacts(*)')\
    .ilike('company_name', '%Vincent%')\
    .execute()

for client in result.data:
    print(f"Client: {client['company_name']}")
    print(f"  Contacts ({len(client['contacts'])}):")
    for contact in client['contacts']:
        print(f"    - {contact['full_name']} ({contact.get('email', 'pas d\'email')})")
    print()
```

**Résultat attendu:**
```
Client: École de musique Vincent-d'Indy
  Contacts (3):
    - Anne-Marie Denoncourt (anne-marie@example.com)
    - Autre Contact (email@example.com)
    - Troisième Contact (pas d'email)
```

---

### Test 3: Recherche dans l'assistant conversationnel

**Scénario utilisateur:** "Trouve-moi les infos d'Anne-Marie"

**Code assistant:**

```python
def search_person(name: str):
    """Recherche une personne (contact) et retourne avec info client"""

    result = supabase.table('gazelle_contacts')\
        .select('''
            id,
            full_name,
            email,
            phone,
            client:gazelle_clients(
                id,
                company_name,
                address
            )
        ''')\
        .ilike('full_name', f'%{name}%')\
        .execute()

    if not result.data:
        return f"Aucun contact trouvé pour '{name}'"

    # Formater résultat pour l'utilisateur
    contacts_info = []
    for contact in result.data:
        info = f"**{contact['full_name']}**\n"
        info += f"- Entreprise: {contact['client']['company_name']}\n"
        if contact.get('email'):
            info += f"- Email: {contact['email']}\n"
        if contact.get('phone'):
            info += f"- Téléphone: {contact['phone']}\n"
        contacts_info.append(info)

    return "\n".join(contacts_info)

# Test
print(search_person("Anne-Marie"))
```

**Résultat attendu:**
```
**Anne-Marie Denoncourt**
- Entreprise: École de musique Vincent-d'Indy
- Email: anne-marie@vincentdindy.ca
- Téléphone: (514) 555-1234
```

---

## ✅ CHECKLIST DE VALIDATION

Cursor Mac, tu as compris si tu peux répondre OUI à ces questions:

- [ ] Je sais que `gazelle_contacts.client_id` pointe vers `gazelle_clients.id`
- [ ] Je sais utiliser `.select('*, client:gazelle_clients(*)')` pour joindre
- [ ] Je sais qu'un Contact a UN client, mais un Client a PLUSIEURS contacts
- [ ] Je n'essaie jamais de chercher `client_id` dans `gazelle_clients`
- [ ] Quand je cherche une personne, j'inclus toujours les infos du client associé

---

**Créé:** 2025-12-24
**Pour:** Cursor Mac - Compréhension de la relation Client ↔ Contact
**Par:** Claude Code (Windows)
