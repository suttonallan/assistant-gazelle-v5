# RÈGLE CRITIQUE : IDs Gazelle comme Source de Vérité

**Date création:** 2025-12-29
**Statut:** RÈGLE NON-NÉGOCIABLE

---

## 🎯 Principe Fondamental

**TOUS les identifiants (clients, pianos, techniciens, rendez-vous) doivent TOUJOURS utiliser les IDs de Gazelle.**

### Pourquoi ?

1. **Source Unique de Vérité**: Gazelle est le système maître
2. **Pas de Confusion**: Pas de mapping à maintenir entre plusieurs systèmes d'IDs
3. **Synchronisation Simple**: Import direct sans transformation d'IDs
4. **Traçabilité**: Possibilité de retrouver facilement les données dans Gazelle

---

## ❌ Ce Qu'il NE FAUT JAMAIS Faire

### 1. Créer des IDs Locaux

```python
# ❌ MAUVAIS - Créer nos propres IDs
user = {
    "id": 1,  # ID local
    "gazelle_id": "usr_ReUSmIJmBF86ilY1",  # ID Gazelle
    "name": "Nicolas"
}
```

### 2. Créer des Tables de Mapping

```sql
-- ❌ MAUVAIS - Table de mapping à éviter
CREATE TABLE user_mapping (
    local_id INT PRIMARY KEY,
    gazelle_id TEXT,
    name TEXT
);
```

**Problème:** Cette table devient une source de confusion et doit être maintenue manuellement.

### 3. Utiliser des Noms comme Identifiants

```python
# ❌ MAUVAIS - Utiliser le nom comme ID
query = {
    "technician_id": "Nicolas"  # Nom humain
}
```

**Problème:** Les noms peuvent changer, avoir des doublons, ou des variations (Nicolas/Nick/Nic).

---

## ✅ La Bonne Approche

### 1. Utiliser Directement les IDs Gazelle

```python
# ✅ BON - ID Gazelle directement
user = {
    "id": "usr_ReUSmIJmBF86ilY1",  # ID Gazelle
    "name": "Nicolas",  # Pour affichage seulement
    "email": "nlessard@piano-tek.com"
}
```

### 2. Stocker les IDs Gazelle dans les Configs

```javascript
// ✅ BON - Configuration avec IDs Gazelle
export const USERS = [
  {
    name: 'Allan',
    email: 'asutton@piano-tek.com',
    gazelleId: 'usr_xxxxxxxxxxxxx',  // ID Gazelle
    role: 'admin',
    pin: '6342'
  },
  {
    name: 'Nicolas',
    email: 'nlessard@piano-tek.com',
    gazelleId: 'usr_ReUSmIJmBF86ilY1',  // ID Gazelle
    role: 'technician',
    pin: '6344'
  },
  {
    name: 'JP',
    email: 'jpreny@gmail.com',
    gazelleId: 'usr_ofYggsCDt2JAVeNP',  // ID Gazelle
    role: 'technician',
    pin: '6345'
  }
]
```

### 3. Requêtes avec IDs Gazelle

```python
# ✅ BON - Filtrer par ID Gazelle
appointments = supabase.table('gazelle_appointments')\
    .select('*')\
    .eq('technicien', 'usr_ReUSmIJmBF86ilY1')\  # ID Gazelle
    .execute()
```

---

## 🔧 Implémentation Actuelle (V5)

### Frontend: LoginScreen.jsx

```javascript
const USERS = [
  {
    id: 1,
    name: 'Allan',
    email: 'asutton@piano-tek.com',
    gazelleId: 'usr_xxxxxxxxxxxxx',  // À remplir
    role: 'admin',
    pin: '6342',
    technicianName: 'Allan'  // DEPRECATED - utiliser gazelleId
  },
  {
    id: 2,
    name: 'Louise',
    email: 'info@piano-tek.com',
    gazelleId: null,  // Louise n'est pas technicien
    role: 'admin',
    pin: '6343'
  },
  {
    id: 3,
    name: 'Nicolas',
    email: 'nlessard@piano-tek.com',
    gazelleId: 'usr_ReUSmIJmBF86ilY1',
    role: 'technician',
    pin: '6344'
  },
  {
    id: 4,
    name: 'JP',
    email: 'jpreny@gmail.com',
    gazelleId: 'usr_ofYggsCDt2JAVeNP',
    role: 'technician',
    pin: '6345'
  }
]
```

### Backend: Chat Service

```python
# Au lieu de:
technician_id = "Nicolas"  # ❌ Nom humain

# Utiliser:
technician_id = "usr_ReUSmIJmBF86ilY1"  # ✅ ID Gazelle
```

---

## 📋 Migration V5 → V6

### Phase 1: Identifier les IDs Gazelle

**Action immédiate:** Remplir les IDs Gazelle dans la configuration frontend.

```bash
# Script pour récupérer les IDs des techniciens
python3 << 'EOF'
from core.supabase_storage import SupabaseStorage
from supabase import create_client

storage = SupabaseStorage()
supabase = create_client(storage.supabase_url, storage.supabase_key)

# Récupérer tous les techniciens uniques
result = supabase.table('gazelle_appointments')\
    .select('technicien')\
    .execute()

techs = set(r['technicien'] for r in result.data if r.get('technicien'))
print("IDs Gazelle des techniciens:")
for tech_id in sorted(techs):
    print(f"  - {tech_id}")
EOF
```

### Phase 2: Mettre à Jour le Code

1. **Frontend (`LoginScreen.jsx`):**
   - Ajouter champ `gazelleId` à chaque utilisateur
   - Utiliser `gazelleId` au lieu de `technicianName`

2. **Backend (`api/chat/service.py`):**
   - Accepter `gazelleId` au lieu de nom humain
   - Filtrer avec `gazelleId` directement

3. **Schémas (`api/chat/schemas.py`):**
   ```python
   class ChatRequest(BaseModel):
       query: str
       technician_gazelle_id: Optional[str] = Field(
           None,
           description="ID Gazelle du technicien",
           example="usr_ReUSmIJmBF86ilY1"
       )
       user_role: Optional[str] = None
   ```

### Phase 3: Validation

```python
# Test que les IDs fonctionnent
def test_gazelle_ids():
    """Valider que tous les IDs Gazelle sont corrects."""
    users = [
        ("Nicolas", "usr_ReUSmIJmBF86ilY1"),
        ("JP", "usr_ofYggsCDt2JAVeNP"),
    ]

    for name, gazelle_id in users:
        appointments = supabase.table('gazelle_appointments')\
            .select('external_id')\
            .eq('technicien', gazelle_id)\
            .limit(1)\
            .execute()

        if appointments.data:
            print(f"✅ {name} ({gazelle_id}): {len(appointments.data)} RV trouvés")
        else:
            print(f"⚠️  {name} ({gazelle_id}): Aucun RV trouvé")
```

---

## 🚨 V6 Architecture

### Tables V6 avec IDs Gazelle

```sql
-- ✅ BON - Toujours utiliser IDs Gazelle
CREATE TABLE gazelle_contacts (
    id TEXT PRIMARY KEY,  -- ID Gazelle (ex: cnt_xxxxx)
    name TEXT NOT NULL,
    email TEXT,
    phone TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE gazelle_appointments (
    id TEXT PRIMARY KEY,  -- ID Gazelle (ex: apt_xxxxx)
    contact_id TEXT REFERENCES gazelle_contacts(id),
    technician_id TEXT NOT NULL,  -- ID Gazelle (ex: usr_xxxxx)
    appointment_date DATE NOT NULL,
    appointment_time TIME NOT NULL
);
```

### Reconciler V6

```python
# ✅ BON - Utiliser IDs Gazelle directement
class ContactReconciler:
    def reconcile(self, gazelle_contact: Dict) -> str:
        """
        Retourne l'ID Gazelle du contact (source de vérité).

        Args:
            gazelle_contact: Contact depuis Gazelle API

        Returns:
            str: ID Gazelle (ex: "cnt_xxxxx")
        """
        gazelle_id = gazelle_contact["id"]  # ID Gazelle

        # Upsert avec ID Gazelle
        supabase.table('gazelle_contacts')\
            .upsert({
                "id": gazelle_id,  # PK = ID Gazelle
                "name": gazelle_contact["name"],
                "email": gazelle_contact["email"]
            })\
            .execute()

        return gazelle_id  # Retourner ID Gazelle
```

---

## 📊 Checklist de Conformité

Avant toute nouvelle fonctionnalité, vérifier:

- [ ] Les IDs utilisés sont-ils des IDs Gazelle ?
- [ ] Y a-t-il des conversions nom → ID ? (À ÉVITER)
- [ ] Y a-t-il une table de mapping ? (À SUPPRIMER)
- [ ] Les requêtes filtrent-elles avec des IDs Gazelle ?
- [ ] La documentation mentionne-t-elle l'utilisation d'IDs Gazelle ?

---

## 🔗 Documents Connexes

- [SYNC_STRATEGY.md](assistant-v6/docs/SYNC_STRATEGY.md) - Synchronisation Gazelle
- [DATA_DICTIONARY.md](assistant-v6/docs/DATA_DICTIONARY.md) - Schéma de données
- [ARCHITECTURE_MAP.md](assistant-v6/docs/ARCHITECTURE_MAP.md) - Architecture V6

---

## 📝 Historique des Décisions

### 2025-12-29: Décision Initiale

**Contexte:** Chat Intelligent utilisait des noms humains ("Nicolas") au lieu d'IDs Gazelle.

**Problème identifié:**
- Frontend envoyait `technician_id: "Nicolas"`
- Backend filtrait avec `technicien = "Nicolas"`
- Base de données contient `technicien = "usr_ReUSmIJmBF86ilY1"`
- Résultat: 0 rendez-vous trouvés

**Solution:**
- Utiliser TOUJOURS les IDs Gazelle
- Pas de mapping table
- Pas de conversion nom ↔ ID

**Impact:**
- V5: Mise à jour immédiate de `LoginScreen.jsx` et `api/chat/service.py`
- V6: Intégrer cette règle dès le début (Reconciler, Tables, API)

---

**Version:** 1.0
**Auteur:** Assistant Gazelle Team
**Statut:** RÈGLE NON-NÉGOCIABLE - À respecter pour toute future implémentation
